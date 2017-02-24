import unittest
import padeCommon
import argparse

parser = argparse.ArgumentParser(description='Register file to run tests with')
parser.add_argument('-f', '--file', type=str, default='superpaderegs.xml')

args = parser.parse_args()

regFile = args.file

class padeTests(unittest.TestCase):
    def setUp(self):
        self.registers = padeCommon.readRegisters(regFile)

    def test_simple_reg_read(self):
        cmds = padeCommon.regCmd(self.registers['SDRAM_read'])
        self.assertEqual(cmds, ['rd 7'])

    def test_complex_reg_read(self):
        cmds = padeCommon.regCmd(self.registers['SDRAM_WritePointer'])
        self.assertEqual(cmds, ['rd 2', 'rd 3'])


if __name__ == '__main__':
    unittest.main()
    
