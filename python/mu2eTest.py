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


reg16bit = []
reg32bit = []
print 'Register List\n-----------------'
for r in regs:
    if int(r.Width) == 16:
        reg16bit.append(r)
    elif int(r.Width) == 32:
        reg32bit.append(r)



            
        
    
for r in reg16bit:
    print r.Name


print '\n\nRegister List 32-bit \n-----------------'
for r in reg32bit:
    print r.Name
    
connection = telnetlib.Telnet('', 5001)


for key in Registers.keys():
    r = Registers[key]
    cmds = readRegisterCmd(r)
    resp = []
    for c in cmds:
        connection.write(c)
        resp.append(connection.read_until('\r\n').strip())
    print resp


# s = 'rd {0} {1}\r\n'
# for r in reg16bit:
#     connection.write(s.format(hexFormatter(r.Address), 0))
#     print 'Reading: {0}'.format(hexFormatter(r.Address))
#     msg = connection.read_until('\r\n')
#     print 'For Register {0}, Value: {1}'.format(r.Name, msg)

resp = []
cmds = readRegisterCmd(Registers['SPILL_TRIG_COUNT'])
for c in cmds:
    connection.write(c)
    resp.append(connection.read_until('\r\n').strip())

print 'Trigger: {0}'.format(resp)

# trigHigh = 0
# trigLow = 0
# for r in reg32bit:

#     sHigh = 'rd {0} 0\r\n'
#     sLow = 'rd {0} 0\r\n'
#     connection.write(sHigh.format(hexFormatter(r.UpperAddress)))
#     print 'Reading High: {0}'.format(hexFormatter(r.UpperAddress))
#     msgHigh = connection.read_until('\r\n').strip()
#     print 'Reading Low: {0}'.format(hexFormatter(r.LowerAddress))
#     connection.write(sLow.format(hexFormatter(r.LowerAddress)))
#     msgLow = connection.read_until('\r\n').strip()
#     print 'Reading {0}, High: {1}, Low: {2}'.format(r.Name, msgHigh, msgLow)
#     if r.Name.find('SPILL_TRIG_COUNT') != -1:
#         trigHigh = int(msgHigh, 16)
#         trigLow = int(msgLow, 16)

# print 'We have {0} triggers available, trying to get them'.format(trigLow)
exit()
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
