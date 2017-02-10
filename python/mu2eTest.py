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
   # Addresses = map(hexFormatter, [r.UpperAddress, r.LowerAddress, r.Address])
   # print '{0}, {1}, {2}, {3}, {4}'.format(r.Name, Addresses[2], Addresses[1], Addresses[0], r.Width)


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


### Attempt to parse data 
# First 4 bytes is the trigger Count / 2
# Next 2 bytes Spill Counter
# Then mask which should tell us the number of channels
# Then 2 bytes for Board id
# Then 2 bytes for Spill Status
triggerCount = int(data[0:4].encode('hex'), 16)*2
spillCounter = int(data[4:6].encode('hex'), 16)
mask = int(data[6:8].encode('hex'), 16)
boardID = int(data[8:10].encode('hex'), 16)
spillStatus = int(data[10:12].encode('hex'), 16)

# Now we've handled the spill header next are the events


print 'TC: {0}, SpillCount: {1}, mask: {2}, board: {3}, spillStatus: {4}'.format(triggerCount,
                                                                         spillCounter,
                                                                         bin(mask),
                                                                         boardID,
                                                                         spillStatus)
                                                                         

#Process the First Event Header
eventWordCount = int(data[12:14].encode('hex'), 16)
print 'eventWordCount: {0}'.format(eventWordCount)

eventTimeStamp = int(data[14:18].encode('hex'), 16)
eventTrigCounter = int(data[18:22].encode('hex'),16)
eventSamples = int(data[22:24].encode('hex'), 16)
eventTrigType = int(data[24:26].encode('hex'), 16)
eventStatus = int(data[26:28].encode('hex'), 16)

print 'TimeStamp: {0}, TrigCounter: {1}, Samples: {2}, TrigType: {3}, Status: {4}'.format(eventTimeStamp, eventTrigCounter, eventSamples, eventTrigType, eventStatus)

#Begin Event Data

channelCount = eventWordCount / eventSamples
print 'Channel Count should be: {0}'.format(channelCount)

# Get data for First Channel

chNum = 0
samples = []
chTable = {}
chData = data[28:(28+eventSamples*2)]
end = 28+eventSamples*2



#Rather than reading it this way, let's just read until we don't find anymore channels.....
ch = 0
while True:
    print 'ch: {0}'.format(ch)
    chTable[ch] = []
    chStart = int(chData[0:2].encode('hex'),16)
    if (chStart &0x8000) == 0x8000 :
        print 'Found Channel {0}'.format(chStart&0xfff)
    else:
        break
    for j in range(0, len(chData)/2):
        e = int(chData[j*2:j*2+2].encode('hex'), 16)
        if (e & 0x8000) == 0x8000:
            # Channel Number
            chNum = e&0xfff;
            print 'Channel Number: {0}'.format(chNum)
        if e > 0x7ff:
            e -= 0xfff
        chTable[ch].append(e)
    print '{0}:{1}'.format(end, end+eventSamples*2)
    chData = data[end:end+eventSamples*2]
    end += eventSamples*2
    ch += 1

end -= eventSamples*2
#print chTable
print end

#print data[end:].encode('hex')

# nextData = data[end:]

# # Process Second Header
# eventWordCount = int(nextData[0:2].encode('hex'), 16)
# print 'eventWordCount: {0}'.format(eventWordCount)

# eventTimeStamp = int(nextData[2:6].encode('hex'), 16)
# eventTrigCounter = int(nextData[6:10].encode('hex'),16)
# eventSamples = int(nextData[10:12].encode('hex'), 16)
# eventTrigType = int(nextData[12:14].encode('hex'), 16)
# eventStatus = int(nextData[14:16].encode('hex'), 16)

# print 'TimeStamp: {0}, TrigCounter: {1}, Samples: {2}, TrigType: {3}, Status: {4}'.format(eventTimeStamp, eventTrigCounter, eventSamples, eventTrigType, eventStatus)

# #Begin Event Data

# channelCount = eventWordCount / eventSamples
# print 'Channel Count should be: {0}'.format(channelCount)
# secondchTable = {}

# chData = nextData[16:(16+eventSamples*2)]
# end = 16+eventSamples*2
# ch = 0
# while True:
#     print 'ch: {0}'.format(ch)
#     secondchTable[ch] = []
#     chStart = int(chData[0:2].encode('hex'),16)
#     if (chStart &0x8000) == 0x8000 :
#         print 'Found Channel {0}'.format(chStart&0xfff)
#     else:
#         break
#     for j in range(0, len(chData)/2):
#         e = int(chData[j*2:j*2+2].encode('hex'), 16)
#         if (e & 0x8000) == 0x8000:
#             # Channel Number
#             chNum = e&0xfff;
#             print 'Channel Number: {0}'.format(chNum)
#         if e > 0x7ff:
#             e -= 0xfff
#         secondchTable[ch].append(e)
#     print '{0}:{1}'.format(end, end+eventSamples*2)
#     chData = nextData[end:end+eventSamples*2]
#     end += eventSamples*2
#     ch += 1

# end -= eventSamples*2
# print secondchTable
# print end
# print nextData[end:]



connection.close()
