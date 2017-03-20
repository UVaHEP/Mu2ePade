import padeCommon
from padeCommon import encode, event

import pyqtgraph
import numpy as np
from PyQt4 import QtCore
from PyQt4.QtGui import *
import sys
app = QApplication(sys.argv)
import qtreactor.pyqt4reactor
qtreactor.pyqt4reactor.install()

from twisted.internet import reactor, task
from commLayer import padeClient, padeFactory

class regWindow(QMainWindow):
    def __init__(self, parent=None):
        self.f = padeFactory('superpaderegs.xml')
        self.registers = self.f.registers
        QMainWindow.__init__(self, parent)
        self.create_main_frame()



    def padeConnect(self):
        self.button.setText("Connecting")
        self.disconnect(self.button, QtCore.SIGNAL('clicked()'), self.padeConnect)
        
        self.f.verifyCb = self.connected
        c = reactor.connectTCP('128.143.196.217', 5001, self.f)

    def padeDisconnect(self):
        self.f.client.transport.loseConnection()

    def padePlotData(self, data):

        events = padeCommon.buildDataEvents(data)
        ## Grab first event and attempt to plot it
        firstEvent = events[0]
        for ch in firstEvent.chs.keys(): 
            print ch
            self.pg.plot(firstEvent.chs[ch][1:], pen=(ch,len(firstEvent.chs.keys())))
        
    def padeReadData(self):
        self.f.readData(self.padePlotData)
        

    def checkReg(self, text):
        value = self.f.registers[str(text)].Status
        self.rLabel.setText(hex(value))
        print 'Reg {0}, current value: {1}'.format (text, hex(self.f.registers[str(text)].Status))

        
    def closeEvent(self, event):
        print 'Shutting down and disconnecting'
        if self.f and self.f.client: 
            self.f.client.transport.loseConnection()

        if reactor.running:
            reactor.stop()



    def connected(self):
        self.button.setText("Connected -- Press to Disconnect")
        self.connect(self.button, QtCore.SIGNAL('clicked()'), self.padeDisconnect)

    def create_main_frame(self):        
        self.page = QWidget()        

        self.button = QPushButton('Connect', self.page)
        self.dataBtn = QPushButton('Read Data', self.page)
        self.registersBtn = QPushButton('Read All Registers', self.page)
        self.pullDown = QComboBox()
        self.rLabel = QLabel()
        self.pg = pyqtgraph.PlotWidget()        
        self.vbutton = QPushButton('Read Voltage', self.page)
        self.wbutton = QPushButton('Write Voltage',self.page)
        
        vbox1 = QVBoxLayout()
        vbox1.addWidget(self.button)
        vbox1.addWidget(self.dataBtn)
        vbox1.addWidget(self.pullDown)
        vbox1.addWidget(self.rLabel)
        vbox1.addWidget(self.registersBtn)
        vbox1.addWidget(self.vbutton)
        vbox1.addWidget(self.wbutton)
        vbox1.addWidget(self.pg)
        self.pullDown.addItems(self.registers.keys())
        self.pullDown.currentIndexChanged.connect(self.selectionchange)

        self.connect(self.button,
                     QtCore.SIGNAL('clicked()'),
                     self.padeConnect)

        self.connect(self.dataBtn,
                     QtCore.SIGNAL('clicked()'),
                     self.padeReadData)

        self.connect(self.vbutton,
                     QtCore.SIGNAL('clicked()'),
                     self.padeReadVoltage)

        self.connect(self.wbutton,
                     QtCore.SIGNAL('clicked()'),
                     self.padeWriteVoltage)
        
        self.page.setLayout(vbox1)
        self.setCentralWidget(self.page)


        self._timer = QtCore.QTimer()
        self._timer.setSingleShot(False)


        self._timer.setInterval(1000)
        self._timer.start()


    def padeWriteVoltage(self):
        #Test write 1 V
        v = int(self.adcVoltage(10.0))
        self.f.writeRegister('BIAS_BUS_DAC0', v)
        
    def padeReadVoltage(self):
        self.f.readRegister('BIAS_BUS_DAC0', lambda: sys.stdout.write(str(self.parseVoltage(self.registers['BIAS_BUS_DAC0'].Status))+'\n'))
        
    def parseVoltage(self, v):
        return (v*5.38)/256

    def adcVoltage(self, v):
        return round(v*256/5.38)

    
    def selectionchange(self, index):
        print 'Chose: {0}'.format(self.pullDown.currentText())
        if self.f and self.f.verified:
            #Connected and verified 
            self.f.readRegister(self.pullDown.currentText(), lambda : self.checkReg(self.pullDown.currentText()))
            

if __name__ == "__main__":
    import sys
    form = regWindow()
    form.show()
    reactor.run()
