import socket
import asyncore 
import time
import xml 
import xml.etree.ElementTree as etree
import threading


class padecomm(asyncore.dispatcher):
    writeBase = 'wr {0} {1}\r\n'
    readBase = 'rd {0} \r\n'
    fpgaOffsetMultiplier = 0x400
    def __init__(self, host, port, registerFile):


        self.cbTable = {}
        self.items = []
        asyncore.dispatcher.__init__(self)
        try:
            self.host = host
            self.port = port
            self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
            self.connect((host, port))
            self.connected = True
        except Exception as serror:
            print 'Error connecting to {0}:{1}, {2}'.format(host, port, serror)
            self.connection = None
            self.connected = False 

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
                r = reg(Comment, PrefHex, FPGAOffsetMultiplier, BitComments,
                        Name, UpperAddress, LowerAddress, Width, Address)
                self.registers[r.Name] = r

        except Exception as e:
            print 'Error reading from {0}, {1}'.format(registerFile, e)

    def handle_connect(self):
        print 'Connected to {0}:{1} successfully'.format(self.host, self.port)

    def handle_close(self):
        print 'Disconnected from {0}:{1}'.format(self.host, self.port)
        self.close()

    def handle_read(self):
        print 'read {0}'.format(self.recv(256))

    def handle_write(self):
        if len(self.items) > 0:
            print 'Items: {0}'.format(self.items)
                    
            nextItem = self.items.pop()
            print 'writing {0}'.format(nextItem)
            self.buffer = nextItem
            sent = self.send(self.buffer)
            self.buffer = self.buffer[sent:]
            

            
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

    def parseVoltage(self, v):
        return (int(v, 16)*5.38)/256

    def readVoltage(self, fpga = 0):
        if (fpga > 3):
            print 'Error! Bad fpga value in read voltage, using first fpga'
            fpga = 0
        readCmd = self.genregCmd('BIAS_BUS_DAC0')
        
        if (self.connected):
            print 'Reading Voltage'
            map(self.items.append, readCmd)
            
            
        else:
            print 'Not connected! Cannot read voltage'

        #Add Fns: Read all registers, read register list

class reg:
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



pade = padecomm('', 5001, 'superpaderegs.xml')
tr = threading.Thread(target=asyncore.loop, args=(0.1,))
tr.start()
pade.readVoltage()

print 'Press any key to quit'
raw_input()
for s,v in asyncore.socket_map.items():
    print '{0},{1}'.format(s,v)
    v.close()

tr.join()

