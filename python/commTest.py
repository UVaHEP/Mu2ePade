import twisted
import time
import threading
import functools
from functools import partial

import xml 
import xml.etree.ElementTree as etree


import argparse 
from twisted.internet import reactor, protocol, defer
from twisted.internet.protocol import Protocol
from twisted.protocols.basic import LineReceiver
from twisted.internet.endpoints import TCP4ClientEndpoint, connectProtocol
from sys import stdout


class register:
    def __init__(self, Comment, PrefHex, FPGAOffsetMultiplier, BitComments,
                 Name, UpperAddress, LowerAddress, Width, Address):
        
        self.Comment = Comment
        self.PrefHex = PrefHex
        self.FPGAOffsetMultiplier = FPGAOffsetMultiplier
        self.BitComments = BitComments
        self.Name = Name
        self.UpperAddress = UpperAddress
        self.LowerAddress = LowerAddress
        self.Width = Width
        self.Address = Address
        self.fpgaOffset = 0x400
        self.Status = 0


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

    
    def genregCmd(self, name, value = None, fpga = 0):
        #As of now Lower Address is the same as Address
        #so I'm using that for everything 

        
        fpgaOffset = fpga*self.fpgaOffsetMultiplier
        cmds = []
        try:
            reg = self.registers[name]
                
            if not value:
                #Read Mode
                upperRead = None
                lowerRead = None 
                if int(reg.Width) == 32:
                    #32-bit registers require 2 read commands,
                    #one to access the upper bits in the register
                    #and one to access the lower bits
                    upperRead = self.readBase.format(self.hexFormatter(int(reg.UpperAddress)+fpgaOffset))
                lowerRead = self.readBase.format(self.hexFormatter(int(reg.Address)+fpgaOffset))
                if upperRead:
                    return [upperRead, lowerRead]
                else:
                    return [lowerRead]
            else:
                #Write Mode
                upperWrite = None
                lowerWrite = None 
                if int(reg.Width) == 32:
                    #Similar to read, we require 2 writes if we have
                    #a 32-bit register
                    # & -- BitAnd just grab the upper 16-bits
                    upperWrite = self.writeBase.format(self.hexFormatter(reg.UpperAddress+fpgaOffset), hexFormatter(value & 0xFFFF0000))
                    # & 0x0000FFFF grab lower 16-bit, could just use
                    # 0xFFFF, but wanted it be clear 
                lowerWrite = self.writeBase.format(self.hexFormatter(reg.Address+fpgaOffset), self.hexFormatter(value & 0x0000FFFF))
                if upperWrite:
                    return [upperWrite, lowerWrite]
                else:
                    return [lowerWrite]

        except Exception as e:
            print 'Failed to generate register read/write commands: {0}'.format(e)
            return (None, None)


    def connectionMade(self):
        print('Connected to server!')
#        print('Registers that I know about\n-----------')
#        for reg in self.getRegisterNames():
#            print reg
#        print 'Factory name....{0}'.format(self.factory.name)
        self.factory.handle_verification(self)


    def generic_receive(self, line):
        print 'Line Received: {0}'.format(line)

    def lineReceived(self, line):
        self.handle_msg(line)

    def connectionLost(self, reason):
        pass


        


class padeFactory(protocol.ClientFactory):
    protocol = padeClient
    name = 'King Factory!'

    def __init__(self, registerFile):
        self.registerFile = registerFile
        self.verified = False 
        try:
            self.registers = {}
            tree = etree.parse(registerFile)
            root = tree.getroot()
            for c in root:
                Comment = c.get('Comment')
                PrefHex = c.get('PrefHex')
                FPGAOffsetMultiplier = c.get('FPGAOffsetMultiplier')
                BitComments = c.get('BitComments')
                Name = c.get('Name')
                UpperAddress = c.get('UpperAddress')
                LowerAddress = c.get('LowerAddress')
                Width = c.get('Width')
                Address = c.get('Address')
                r = register(Comment, PrefHex, FPGAOffsetMultiplier, BitComments,
                        Name, UpperAddress, LowerAddress, Width, Address)
                self.registers[r.Name] = r

        except Exception as e:
            print 'Error reading from {0}, {1}'.format(registerFile, e)

    
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
        reactor.callLater(1, self.readRegisters)
        print 'Verified Connection.'
        
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
        


    def printRegisterStatus(self):
        print 'Registers\n---------'
        for name in self.registers:
            print '{0}:{1}'.format(name, self.registers[name].Status)
        
    def readRegisterBase(self, name, upper, line ):
#        print 'Name: {0}, Value: {1}'.format(name, line)
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
            cmds = self.client.genregCmd(regName)
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
        
        reactor.callLater(3, self.client.transport.loseConnection)

def connected(connectedProto):
    print 'Protocol has successfully connected'


        
parser = argparse.ArgumentParser(description='Pade Tester')
parser.add_argument('--host', type=str, default = '127.0.0.1',
                    help='Host name to use')
parser.add_argument('-p', '--port', type=int, default = 5001,
                    help='Port to use')

args = parser.parse_args()

f = padeFactory('superpaderegs.xml')

c = reactor.connectTCP(args.host, args.port, f)

reactor.run()


