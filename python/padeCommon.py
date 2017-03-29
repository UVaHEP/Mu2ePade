import xml 
import xml.etree.ElementTree as etree


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




def readRegisters(xmlFile):
    registers = {}
    try:
        tree = etree.parse(xmlFile)
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
            r = register(Comment, PrefHex, FPGAOffsetMultiplier, BitComments,Name, UpperAddress, LowerAddress, Width, Address)
            registers[r.Name] = r
        return registers
    except Exception as e:
        print 'Failed reading registers from file: {0}, Reason: {1}'.format(xmlFile, e)
        return None 

        
def hexFormatter(x):
    #Simple utility to convert to hex values
    #that match what the Pade requires
    return format(int(x), '2x').strip()


writeBase = 'wr {0} {1}'
readBase = 'rd {0}'
fpgaOffsetMultiplier = 0x400
def regCmd(reg, value = None, fpga = 0):
    #As of now Lower Address is the same as Address
    #so I'm using that for everything 
    
    fpgaOffset = fpga*fpgaOffsetMultiplier
    cmds = []
    try:
        if not value:
            #Read Mode
            upperRead = None
            lowerRead = None 
            if int(reg.Width) == 32:
                #32-bit registers require 2 read commands,
                #one to access the upper bits in the register
                #and one to access the lower bits
                upperRead = readBase.format(hexFormatter(int(reg.UpperAddress)+fpgaOffset))
            lowerRead = readBase.format(hexFormatter(int(reg.Address)+fpgaOffset))
            if upperRead:
                return [lowerRead, upperRead]
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
                upperWrite = writeBase.format(hexFormatter(int(reg.UpperAddress)+fpgaOffset), hexFormatter(value & 0xFFFF0000))
                # & 0x0000FFFF grab lower 16-bit, could just use
                # 0xFFFF, but wanted it be clear 
            lowerWrite = writeBase.format(hexFormatter(int(reg.Address)+fpgaOffset), hexFormatter(value & 0x0000FFFF))
            if upperWrite:
                return [lowerWrite, upperWrite]
            else:
                return [lowerWrite]

    except Exception as e:
        print 'Failed to generate register read/write commands: {0}'.format(e)
        return (None, None)


def parseA0(a):

    try:
        adc = float(a)
        if (adc > 4.096):
            adc = 8.192 - adc

        return (adc/8)*250

    except Exception as e:
        print e

    
#    cmds = regCmd("HISTO_COUNT0", int('1'+hexFormatter(ch), 16))
def readA0(ch, fpga=0):
    if (fpga > 3):
        print 'Error! Bad fpga value in read voltage, using first fpga'
        fpga = 0


    cmd = writeBase
    fpgaConv = hexFormatter(fpga*4)
    cmds = [cmd.format(fpgaConv+'20','1'+hexFormatter(ch)), 'gain 8\r\n', 'A0 2\r\n',
            cmd.format(fpgaConv+'20', '00')]
    return cmds



### Parser will get rearranged

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
        




def buildDataEvents(data):
    print 'Length Received: {0}'.format(len(data))
    sH = spillHeader(data[0:16])
    print sH
    eventData = data[16:]
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
        return events

        
