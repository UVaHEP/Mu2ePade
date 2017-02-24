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
                upperWrite = writeBase.format(hexFormatter(int(reg.UpperAddress)+fpgaOffset), hexFormatter(value & 0xFFFF0000))
                # & 0x0000FFFF grab lower 16-bit, could just use
                # 0xFFFF, but wanted it be clear 
            lowerWrite = writeBase.format(hexFormatter(reg.Address+fpgaOffset), hexFormatter(value & 0x0000FFFF))
            if upperWrite:
                return [upperWrite, lowerWrite]
            else:
                return [lowerWrite]

    except Exception as e:
        print 'Failed to generate register read/write commands: {0}'.format(e)
        return (None, None)




