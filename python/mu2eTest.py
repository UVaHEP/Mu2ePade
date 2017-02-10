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
#    print r.Name
    regs.append(r)

hexFormatter = lambda x: format(int(x), '2x')


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

s = 'rd {0} {1}\r\n'
for r in reg16bit:
    connection.write(s.format(hexFormatter(r.Address), 0))
    print 'Reading: {0}'.format(hexFormatter(r.Address))
    msg = connection.read_until('\r\n')
    print 'For Register {0}, Value: {1}'.format(r.Name, msg)


trigHigh = 0
trigLow = 0
for r in reg32bit:

    sHigh = 'rd {0} 0\r\n'
    sLow = 'rd {0} 0\r\n'
    connection.write(sHigh.format(hexFormatter(r.UpperAddress)))
    print 'Reading High: {0}'.format(hexFormatter(r.UpperAddress))
    msgHigh = connection.read_until('\r\n').strip()
    print 'Reading Low: {0}'.format(hexFormatter(r.LowerAddress))
    connection.write(sLow.format(hexFormatter(r.LowerAddress)))
    msgLow = connection.read_until('\r\n').strip()
    print 'Reading {0}, High: {1}, Low: {2}'.format(r.Name, msgHigh, msgLow)
    if r.Name.find('SPILL_TRIG_COUNT') != -1:
        trigHigh = int(msgHigh, 16)
        trigLow = int(msgLow, 16)

print 'We have {0} triggers available, trying to get them'.format(trigLow)

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
