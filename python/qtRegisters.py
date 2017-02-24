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
from commTest import padeClient, padeFactory

class regWindow(QMainWindow):
    def __init__(self, parent=None):
        self.registers = padeCommon.readRegisters('superpaderegs.xml')
        QMainWindow.__init__(self, parent)
        self.create_main_frame()
        self.f = None


    def padeConnect(self):
        self.button.setText("Connecting")
        self.disconnect(self.button, QtCore.SIGNAL('clicked()'), self.padeConnect)
        
        self.f = padeFactory('superpaderegs.xml')
        self.f.verifyCb = self.connected
        c = reactor.connectTCP('128.143.196.217', 5001, self.f)

    def padeDisconnect(self):
        self.f.client.transport.loseConnection()

    def padePlotData(self, data):
        print 'Length Received: {0}'.format(len(data))
        sH = padeCommon.spillHeader(data[0:16])
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
        page = QWidget()        

        self.button = QPushButton('Connect', page)
        self.dataBtn = QPushButton('Read Data', page)
        self.registersBtn = QPushButton('Read All Registers', page)
        self.pullDown = QComboBox()
        self.rLabel = QLabel()
        self.pg = pyqtgraph.PlotWidget()        

        
        vbox1 = QVBoxLayout()
        vbox1.addWidget(self.button)
        vbox1.addWidget(self.dataBtn)
        vbox1.addWidget(self.pullDown)
        vbox1.addWidget(self.rLabel)
        vbox1.addWidget(self.registersBtn)
        vbox1.addWidget(self.pg)
        self.pullDown.addItems(self.registers.keys())
        self.pullDown.currentIndexChanged.connect(self.selectionchange)

        self.connect(self.button,
                     QtCore.SIGNAL('clicked()'),
                     self.padeConnect)

        self.connect(self.dataBtn,
                     QtCore.SIGNAL('clicked()'),
                     self.padeReadData)

        page.setLayout(vbox1)
        self.setCentralWidget(page)


        self._timer = QtCore.QTimer()
        self._timer.setSingleShot(False)


        self._timer.setInterval(1000)
        self._timer.start()

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
