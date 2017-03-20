import twisted
import time
import threading
import functools
from functools import partial

import padeCommon 
from padeCommon import register
from collections import deque

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
        print 'Line Received: {0}'.format(line)
        self.handle_msg(line)

    def rawDataReceived(self, packet):
        self.handle_raw(packet)

    def connectionLost(self, reason):
        pass


        


class padeFactory(protocol.ClientFactory):
    protocol = padeClient
    name = 'PadeComm Factory'

    def __init__(self, registerFile):
        self.registerFile = registerFile
        self.verified = False 
        self.registers = padeCommon.readRegisters(registerFile)
        self.verifyCb = None
        self.client = None
    
    def buildProtocol(self, addr):
        p = padeClient()
        p.factory = self
        p.registers = self.registers
        return p

    def clientConnectionFailed(self, connector, reason):
        print('Connection failed ....')


    def clientConnectionLost(self, connector, reason):
        print ('Connection Lost ....')


    def chkRegister(self, name, value):
        status = self.registers[str(name)].Status
        if int(status) != int(value):
            print "Write Register Failed! Values don't Match."
            print "Read: {0} != Sent: {1}".format (status, value)
        
    def handle_verification(self, client):
        self.client = client
        self.client.handle_msg = self.verification_cb
        client.sendLine("rd 0")


    def handle_register(self, line):
        cb = self.cbs.popleft()
        cb.callback(line)
        if len (self.cbs) == 0:
            #Done
#            print 'Finished Reading Register'
            self.client.handle_msg = self.client.generic_receive
            self.readcb()
        

    def printRegisterStatus(self):
        print 'Registers\n---------'
        for name in self.registers:
            if name.find( 'BIAS_BUS_DAC0') != -1:
                print '{0}, Voltage: {1}'.format(name, self.parseVoltage(self.registers[name].Status))
            else:
                print '{0}:{1}'.format(name, self.registers[name].Status)


    def readRegister(self, name, cb, fpga=0):
        # I don't like this idiom, I'll have to see if I can come up with
        # a clearer way of expressing it
        self.client.handle_msg = self.handle_register
        cmds = padeCommon.regCmd(self.registers[str(name)], None, fpga)
        self.readcb = cb
        self.cbs = deque()
        
        upper = False
        for cmd in cmds:
            # We'll only have two cmds, in an n>2 case this won't work correctly
            d = defer.Deferred()
            d.addCallback(functools.partial(self.readRegisterBase, str(name), upper))
            self.cbs.append(d)
            upper = True 
        
        for cmd in cmds:
            self.client.sendLine(cmd)
            
    def readRegisterBase(self, name, upper, line ):
        if upper:
            print 'upper: {0}'.format(line)
            self.registers[name].Status |= (int(line, 16)<<16)
        else:
            self.registers[name].Status = 0
            print 'lower: {0}'.format(line)
            if self.registers[name].Width == 32:
                self.registers[name].Status += int(line, 16)
            else:
                self.registers[name].Status = int(line, 16)


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

    def writeRegister(self, name, value, fpga=0):
        cmds = padeCommon.regCmd(self.registers[str(name)], value, fpga)
        for cmd in cmds:
            self.client.sendLine(cmd)

        chkfn = lambda : self.chkRegister(name, value)
        self.readRegister(name, chkfn,fpga)

    def writeMessage(self,msg):
        self.client.sendLine(msg)


    def processData(self, packet):
        ### Note add a time out for this
        
        self.lastData += packet
        
        if (self.firstPacket):
            self.firstPacket = False
            #First 4 bytes should be the spillWordCount
            scHeader = packet[0:4]
            spillWordCount = int(scHeader.encode('hex'), 16)*2
            print 'spill word count: {0}'.format(spillWordCount)
            #+2 restores header to count
            self.remaining = (spillWordCount+2)-len(packet)
        else:
            self.remaining -= len(packet)

        print 'Remaining: {0}'.format(self.remaining)

        if (self.remaining == 0):
            self.client.setLineMode()
            self.client.handle_msg = self.client.generic_receive
            if self.readcb:
                self.readcb(self.lastData)
        
    def outputData(self):
        for packet in self.lastData:
            print packet
        
    def readData(self, cb=None):
        self.readcb = cb
        self.client.setRawMode()
        self.firstPacket = True
        self.client.handle_raw = self.processData
        self.lastData = ''
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


