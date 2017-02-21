import twisted
import time
import threading

import xml 
import xml.etree.ElementTree as etree


import argparse 
from twisted.internet import reactor, protocol, defer
from twisted.internet.protocol import Protocol
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


class padeClient(Protocol):
    writeBase = 'wr {0} {1}\r\n'
    readBase = 'rd {0} \r\n'
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

        
        fpgaOffset = fpga*padecomm.fpgaOffsetMultiplier
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
                    upperRead = padecomm.readBase.format(self.hexFormatter(int(reg.UpperAddress)+fpgaOffset))
                lowerRead = padecomm.readBase.format(self.hexFormatter(int(reg.Address)+fpgaOffset))
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
                    upperWrite = padecomm.writeBase.format(self.hexFormatter(reg.UpperAddress+fpgaOffset), hexFormatter(value & 0xFFFF0000))
                    # & 0x0000FFFF grab lower 16-bit, could just use
                    # 0xFFFF, but wanted it be clear 
                lowerWrite = padecomm.writeBase.format(self.hexFormatter(reg.Address+fpgaOffset), self.hexFormatter(value & 0x0000FFFF))
                if upperWrite:
                    return [upperWrite, lowerWrite]
                else:
                    return [lowerWrite]

        except Exception as e:
            print 'Failed to generate register read/write commands: {0}'.format(e)
            return (None, None)


    # def readRegister(self, name):
    #     try:
    #         r = self.registers[name]
    #         readMsg = self.genregCmd(r)

        
            
    def connectionMade(self):
        print('Connected to server!')
        print('Registers that I know about\n-----------')
        for reg in self.getRegisterNames():
            print reg
        print 'Factory name....{0}'.format(self.factory.name)
        self.checking = True
        print(self.transport.write('rd 0 \r\n'))
        

    def dataReceived(self, data):
        print ('Server said:', data)
        if self.checking and data.find('\r\n') != -1:
            self.checking = False 
            print 'Verified Connection'

            

        

    def connectionLost(self, reason):
        print ('connection lost')


class padeFactory(protocol.ClientFactory):
    protocol = padeClient
    name = 'King Factory!'

    def __init__(self, registerFile):
        self.registerFile = registerFile
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



parser = argparse.ArgumentParser(description='Pade Tester')
parser.add_argument('--host', type=str, default = '127.0.0.1',
                    help='Host name to use')
parser.add_argument('-p', '--port', type=int, default = 5001,
                    help='Port to use')

args = parser.parse_args()

f = padeFactory('superpaderegs.xml')

c = reactor.connectTCP(args.host, args.port, f)






