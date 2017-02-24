import twisted
import time
import threading
import functools
from functools import partial

import xml 
import xml.etree.ElementTree as etree

import padeCommon 
from padeCommon import register

import argparse 
from twisted.internet import reactor, protocol, defer
from twisted.internet.protocol import Protocol
from twisted.protocols.basic import LineReceiver
from twisted.internet.endpoints import TCP4ClientEndpoint, connectProtocol
from sys import stdout




class padeClient(LineReceiver):
    writeBase = 'wr {0} {1}'
    readBase = 'rd {0} '
    fpgaOffsetMultiplier = 0x400
    

    def hexFormatter(self, x):
        #Simple utility to convert to hex values
        #that match what the Pade requires
        return format(int(x), '2x').strip()


    def getRegisterNames(self):
        return self.registers.keys()


    def connectionMade(self):
        print('Connected to server!')
        self.factory.handle_verification(self)


    def generic_receive(self, line):
        print 'Line Received: {0}'.format(line)

    def lineReceived(self, line):
        self.handle_msg(line)

    def rawDataReceived(self, packet):
        self.handle_raw(packet)

    def connectionLost(self, reason):
        pass


        


class padeFactory(protocol.ClientFactory):
    protocol = padeClient
    name = 'King Factory!'

    def __init__(self, registerFile):
        self.registerFile = registerFile
        self.verified = False 
        self.registers = padeCommon.readRegisters(registerFile)
        self.verifyCb = None
    
    def buildProtocol(self, addr):
        p = padeClient()
        p.factory = self
        p.registers = self.registers
        return p

    def clientConnectionFailed(self, connector, reason):
        print('Connection failed ....')
        reactor.stop()

    def clientConnectionLost(self, connector, reason):
        print ('Connection Lost ....')
        reactor.stop()

    def verification_cb(self, line):
        try:
            v = int(line, 16)
        except Exception as e:
            print 'Could not verify connection, line: {0}....disconnecting'.format(line)
            self.client.transport.loseConnection()
        self.client.handle_msg = self.client.generic_receive
        self.verified = True
        print 'Verified Connection.'
        if (self.verifyCb):
            self.verifyCb()

        
    def handle_verification(self, client):
        self.client = client
        self.client.handle_msg = self.verification_cb
        client.sendLine("rd 0")

    def handle_registers(self, line):
        self.fns[self.i].callback(line)
        self.i += 1
        if (self.i >= len(self.fns)):
            #We're done
            print 'Finished Reading Registers'
            reactor.callLater(0.1, self.printRegisterStatus)
            self.client.handle_msg = self.client.generic_receive
        
    def parseVoltage(self, v):
        return (v*5.38)/256

    def printRegisterStatus(self):
        print 'Registers\n---------'
        for name in self.registers:
            if name.find( 'BIAS_BUS_DAC0') != -1:
                print '{0}, Voltage: {1}'.format(name, self.parseVoltage(self.registers[name].Status))
            else:
                print '{0}:{1}'.format(name, self.registers[name].Status)
        
    def readRegisterBase(self, name, upper, line ):
        if upper:
            self.registers[name].Status += (int(line, 16)<<16)
        else:
            self.registers[name].Status += int(line, 16)

        
    def readRegisters(self):
        print 'Now I will read registers from the superPade'
        self.cmdsum = 0
        self.fns = []
        self.i = 0        
        self.dlst = defer.DeferredList(self.fns)
        for regName in self.registers.keys():
            cmds = padeCommon.regCmd(self.registers[regName])
            self.cmdsum += len(cmds)
            if len(cmds)>1:
                #Upper and lower messages, should rethink this approach
                #For now add an extra callback
                d = defer.Deferred()
                d.addCallback(functools.partial(self.readRegisterBase, regName, True))
                self.fns.append(d)

            d = defer.Deferred()
            d.addCallback(functools.partial(self.readRegisterBase, regName, False))
            self.fns.append(d)

            self.client.handle_msg = self.handle_registers

            for cmd in cmds:
                self.client.sendLine(cmd)


    def processData(self, packet):
        self.lastData.append(packet)

        if (self.firstPacket):
            self.firstPacket = False
            #First 4 bytes should be the spillWordCount
            print len(packet)
            scHeader = packet[0:4]
            spillWordCount = int(scHeader.encode('hex'), 16)*2
            print 'spill word count: {0}'.format(spillWordCount)
            #+2 restores header to count
            self.remaining = (spillWordCount+2)-len(packet)
        else:
            self.remaining -= len(packet)

        print 'Remaining: {0}'.format(self.remaining)

        if (self.remaining == 0):
            reactor.callLater(1, self.outputData)
        
    def outputData(self):
        for packet in self.lastData:
            print packet
        
    def readData(self):
        self.client.setRawMode()
        self.firstPacket = True
        self.client.handle_raw = self.processData
        self.lastData = []
        self.client.sendLine('rdb \r\n')
        
    



if __name__ == '__main__':        
     parser = argparse.ArgumentParser(description='Pade Tester')
     parser.add_argument('--host', type=str, default = '127.0.0.1',
                     help='Host name to use')
     parser.add_argument('-p', '--port', type=int, default = 5001,
                     help='Port to use')

     args = parser.parse_args()

     f = padeFactory('superpaderegs.xml')

     c = reactor.connectTCP(args.host, args.port, f)

     reactor.run()


