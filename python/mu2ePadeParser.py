import argparse



class spillHeader:
    def __init__(self, data):
        if len(data) != 16:
            print 'Error, bad spill header passed'

        self.spillWordCount = int(data[0:4].encode('hex'), 16)
        self.triggerCount = int(data[4:8].encode('hex'), 16)
        self.spillCounter = int(data[8:10].encode('hex'), 16)
        self.mask = int(data[10:12].encode('hex'), 16)
        self.boardID = int(data[12:14].encode('hex'), 16)
        self.spillStatus = int(data[14:16].encode('hex'), 16)


    def __str__(self):
        return 'spill word count: {0}, trigger count: {1}, spill counter: {2}, mask: {3}, board id: {4}, spill status: {5}'.format(self.spillWordCount,
                                                                                                                                  self.triggerCount,
                                                                                                                                  self.spillCounter,
                                                                                                                                  self.mask,
                                                                                                                                  self.boardID,
                                                                                                                                  self.spillStatus)
    


def encode(l):
    return int(l.encode('hex'), 16)




class event:
    def __init__(self, tS, trigCount, trigType, status, chs):
        self.tS = tS
        self.trigCount = trigCount
        self.trigType = trigType
        self.status = status
        self.chs = chs
        

                                    
        
    
parser = argparse.ArgumentParser(description='Parse data from a PADE')
parser.add_argument('-f', '--file', type=str, default='out.hex', help='file to parse')


args = parser.parse_args()

data = None
try:
    f = open(args.file, 'rb')
    data = f.read()
    f.close()
except Exception as e:
    print e


sH = spillHeader(data[0:16])
print sH
#skip past the spillHeader
eventData = data[16:]


#Now we process the first event Header





events = []
trigCount = 0
start = 16
for i in range(0, sH.triggerCount):
    #Parse Events
    #We start by parsing the event header
    print 'Processing Trigger Count: {0} of {1}'.format(i+1, sH.triggerCount)
    wordCount = encode(eventData[0:2])
    timestamp = encode(eventData[2:6])
    triggerCount = encode(eventData[6:10])/2
    samples = encode(eventData[10:12])
    triggerType = encode(eventData[12:14])
    status = encode(eventData[14:16])
    print 'Samples: {0}'.format(samples)
    start = 16
    end = start+samples*2
    chData = eventData[start:(start+samples*2)]


    
#    print chData.encode('hex')
    chNum = 0
    chs = {}
    while True:
        chStart = encode(chData[0:2])
        sampleLst = []
        if (chStart &0x8000) == 0x8000 :
            print 'Found Channel {0}'.format(chStart&0xfff)
        else:
            break
        for j in range(0, len(chData)/2):
            
            e = encode(chData[j*2:j*2+2])
            if (e & 0x8000) == 0x8000:
                # Channel Number
                chNum = e&0xfff;
            if e > 0x7ff:
                e -= 0xfff
            sampleLst.append(e)
        chs[chNum] = sampleLst
        chData = eventData[end:end+samples*2]
        if len(chData) < samples*2:
            #Missing channels?
            break

        end += samples*2

        
    evt = event(timestamp, triggerCount, triggerType, status, chs)
    start = end-samples*2
    eventData = eventData[start:]
    events.append(evt)
    if len(chData) < samples*2:
        #Missing channels?
        print 'We may be missing some channels'
        break



for e in events: 
    print e.chs.keys()
    for key in e.chs.keys():
        print e.chs[key]
    


