import pyqtgraph
import numpy as np
import PyQt4
from PyQt4 import QtCore, uic, QtGui
from PyQt4.QtGui import *
from PyQt4.QtCore import QTimer
import padeCommon
from padeCommon import encode, event

import sys
import functools
from collections import deque

import padeUi

app = QApplication(sys.argv)
import qtreactor.pyqt4reactor
qtreactor.pyqt4reactor.install()

from twisted.internet import reactor, task, defer
import commLayer
from commLayer import padeClient, padeFactory

class padeInterface(QMainWindow):
    def __init__(self, parent=None):
        QMainWindow.__init__(self,parent)


        #Setup interface
        self.ui = uic.loadUi('interface.ui')
        self.channels = padeUi.channels(self)
        self.chLst =  self.channels.activeChannels()

        self.connect(self.ui.connectBtn,
                     QtCore.SIGNAL('clicked()'),
                     self.netConnect)

        self.connect(self.ui.regBtn,
                     QtCore.SIGNAL('clicked()'),
                     self.readAllRegisters)

        self.connect(self.ui.channelBtn,
                     QtCore.SIGNAL('clicked()'),
                     self.showChBox)

        self.connect(self.ui.chSpinBox,
                     QtCore.SIGNAL('valueChanged(int)'),
                     self.readCh)
        
        self.regFile = 'superpaderegs.xml'
        
        self.registers = padeCommon.readRegisters(self.regFile)
        self.regEntryHash = {} 
        rTbl = self.ui.registerTbl
        i = 0
        for r in self.registers.keys():
            rTbl.insertRow(i)
            name = QTableWidgetItem(r)
            value = QTableWidgetItem(0)
            self.regEntryHash[r] = (name, value)
            rTbl.setItem(i,0,name)
            rTbl.setItem(i,1,value)
            i += 1
        rTbl.setSortingEnabled(True)
        #Sort in Ascending Order
        rTbl.sortByColumn(0, QtCore.Qt.AscendingOrder)
        
        self.ui.show()


    def showChBox(self):
        self.channels.ui.show()
        
    def connected(self):
        self.ui.connectBtn.setText("Disconnect")
        self.ui.statlbl.setText('Connected')
        self.connect(self.ui.connectBtn, QtCore.SIGNAL('clicked()'), self.netDisconnect)
        self.client = self.f.client


    def netConnect(self):
        print 'Connect Button!'
        print 'I read {0} as the host.'.format(self.ui.hostBox.text())
        host = str(self.ui.hostBox.text())
        
        try:
            self.f = padeFactory(self.regFile)
            self.f.verifyCb = self.connected
            self.reactor = reactor.connectTCP(host, 5001, self.f)
        except Exception as e:
            print e
            
    def netDisconnect(self):
        print 'Disconnecting'
        if self.f and self.client:
            self.client.transport.loseConnection()

    def refreshRegisterList(self, name):
#        print 'Refreshing Register List: {0}'.format(name)
        print '{0} : {1}'.format(name, self.f.registers[name].Status)
        value = self.regEntryHash[name][1]
        value.setText(hex(self.f.registers[name].Status))
        if self.regCBs:
            self.regCBs.popleft().callback(int(self.ui.fpgaBox.value()))
        
            
    def readAllRegisters(self):
        print 'Reading all registers'
        self.regCBs = deque()

        for r in self.registers.keys():
            d = defer.Deferred()
            cb = functools.partial(self.refreshRegisterList, r)
            fn = functools.partial(self.f.readRegister, r, cb)
            
            d.addCallback(fn)
            self.regCBs.append(d)

        l = self.regCBs.popleft()
        l.callback(int(self.ui.fpgaBox.value()))


    def readCh(self, ch):
        #Lock the widget until we get a response
        self.ui.chSpinBox.enabled = False

        #Time out incase we don't get a response 
        self.chTimer = QTimer()
        self.chTimer.setSingleShot(True)
        self.chTimer.setInterval(1000)
        self.connect(self.chTimer,
                     QtCore.SIGNAL('timeout()'),
                     functools.partial(self.timeout, 'chSpinBox'))
        self.chTimer.start()
        print 'Reading Channel: {0}'.format(ch)
#        print 'Delim: {0}'.format(repr(self.f.client.delimiter))
        cb = functools.partial(self.readChUpdate, int(ch))
        self.f.readA0(ch,cb, int(self.ui.fpgaBox.value()))
        
    def readChUpdate(self, ch, chVal):
        self.ui.chSpinBox.enabled = True
        self.chTimer.stop()
        self.chTimer = None
        

        print('Channel: {0}, Current: {1}'.format(ch, padeCommon.parseA0(chVal)))
        
        
    def timeout(self, kind):
        if kind == 'chSpinBox':
            print 'Timed out reading channel voltage and current'
            self.ui.chSpinBox.enabled = True
            
        

window = padeInterface()

sys.exit(app.exec_())
