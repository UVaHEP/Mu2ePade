import pyqtgraph
import numpy as np
import PyQt4
from PyQt4 import QtCore, uic, QtGui
from PyQt4.QtGui import *

import padeCommon 
import sys
import commLayer


class padeInterface(QMainWindow):
    def __init__(self, parent=None):
        QMainWindow.__init__(self,parent)


        #Setup interface
        self.ui = uic.loadUi('interface.ui')
        self.connect(self.ui.connectBtn,
                     QtCore.SIGNAL('clicked()'),
                     self.netConnect)

        self.connect(self.ui.regBtn,
                     QtCore.SIGNAL('clicked()'),
                     self.readAllRegisters)

        self.registers = padeCommon.readRegisters('superpaderegs.xml')
        rTbl = self.ui.registerTbl
        i = 0
        for r in self.registers.keys():
            rTbl.insertRow(i)
            item = QTableWidgetItem(r)
            rTbl.setItem(i,0,item)
            i += 1
        rTbl.setSortingEnabled(True)
        #Sort in Ascending Order
        rTbl.sortByColumn(0, QtCore.Qt.AscendingOrder)
        
        self.ui.show()

    def netConnect(self):
        print 'Connect Button!'
        print 'I read {0} as the host.'.format(self.ui.hostBox.text())

    def readAllRegisters(self):
        print 'Reading all registers'
        
app = QtGui.QApplication(sys.argv)
window = padeInterface()

sys.exit(app.exec_())
