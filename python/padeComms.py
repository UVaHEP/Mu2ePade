import telnetlib
import time
import xml 
import xml.etree.ElementTree as etree
import struct

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


def readA0(ch, fpga=0):
    if (fpga > 3):
        print 'Error! Bad fpga value in read voltage, using first fpga'
        fpga = 0
    fpgaConv = hexFormatter(fpga*4)
    cmd = 'wr {0} {1}\r\n'
    cmds = [cmd.format(fpgaConv+'20','1'+hexFormatter(ch)), 'gain 8\r\n', 'A0 2\r\n',
            cmd.format(fpgaConv+'20', '00')]
    return cmds
    

def readVoltage(fpga = 0):
    if (fpga > 3):
        print 'Error! Bad fpga value in read voltage, using first fpga'
        fpga = 0
    cmd = 'rd {0}\r\n'
    return cmd.format(hexFormatter(4*fpga)+'44')

    
def parseVoltage(v):
    return (int(v, 16)*5.38)/256

def parseA0(a):

    try:
        adc = float(a)
        if (adc > 4.096):
            adc = 8.192 - adc

        return (adc/8)*250

    except Exception as e:
        print e
        
        
    

def writeVoltage(v, fpga=0):
    cmds = []
    if (fpga > 3):
        print 'Error! Bad fpga value in read voltage, using first fpga'
        fpga = 0
    adcVal = round((v/5.38) * 256)
    vcmd = 'wr {0} {1}\r\n'
    cmds.append(vcmd.format(hexFormatter(fpga*4)+'44', hexFormatter(adcVal)))
    cmds.append(vcmd.format(hexFormatter(fpga*4)+'45', hexFormatter(adcVal)))
    return cmds
    
def writeRegisterCmd(r, value, fpga = 0):
    if (fpga > 3):
        print 'Error! Bad fpga value in read voltage, using first fpga'
        fpga = 0

    cmd = 'wr {0} {1}\r\n'
    fpgaOffset = fpga*0x400
    cmds = [] 
    if int(r.Width) == 32:
        cmds.append(cmd.format(hexFormatter(r.UpperAddress+fpgaOffset), hexFormatter(value & 0xFFFF0000)))
    cmds.append(cmd.format(hexFormatter(r.LowerAddress+fpgaOffset), hexFormatter(value &0xFFFF)))
    return cmds
    
def readRegisterCmd(r, fpga=0):
    if (fpga > 3):
        print 'Error! Bad fpga value in read voltage, using first fpga'
        fpga = 0
    cmd = 'rd {0} \r\n'
    fpgaOffset = int(fpga*0x400)
    cmds = []
    if int(r.Width) == 32:
        cmds.append(cmd.format(hexFormatter(int(r.UpperAddress)+fpgaOffset)))
    cmds.append(cmd.format(hexFormatter(int(r.LowerAddress)+fpgaOffset)))
    return cmds


def readOutRegisters(connection, Registers):
    for name, register in Registers.items():
        cmds = readRegisterCmd(register)
        resp = []
        for c in cmds:
            connection.write(c)
            resp.append(connection.read_until('\r\n').strip())
        print resp




tree = etree.parse('superpaderegs.xml')
root = tree.getroot()

regs = []
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

    regs.append(r)
    

Registers = dict(map(lambda r: (r.Name, r), regs))
hexFormatter = lambda x: format(int(x), '2x').strip()


connection = telnetlib.Telnet('', 5001)



readOutRegisters(connection, Registers)

A0Cmds = readA0(0)
connection.write(A0Cmds[0])
connection.write(A0Cmds[1])
connection.write(A0Cmds[2])
adc = connection.read_until('avg').split('\n\r')[-1].split('avg')[0]
connection.write(A0Cmds[3])
print parseA0(adc)
    
s = connection.get_socket()
s.sendall('rdb \r\n')


#Grab the spill word count header 
scHeader = s.recv(4)
spillWordCount = int(scHeader.encode('hex'), 16)*2
print '# of bytes we need to recieve: {0}'.format(spillWordCount-4)
time.sleep(0.1)
data = s.recv(spillWordCount-4)
count = 0 
while len(data) < spillWordCount-4 and (count < 10):
    time.sleep(0.05)
    print '{0}, {1}'.format(len(data), spillWordCount)
    data += s.recv(spillWordCount-4-len(data))
    count += 1
    
    
print 'data length: {0}, expected: {1}'.format(len(data), spillWordCount-4)


f = open('out.hex','wb')

f.write(scHeader)
for c in data:
    f.write(c)

f.close()



connection.close()
