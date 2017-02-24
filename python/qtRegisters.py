import padeCommon

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
        self.disconnect(self.button,QtCore.SIGNAL('clicked()'),self, QtCore.SLOT('self.padeConnect'))
        self.f = padeFactory('superpaderegs.xml')
        self.f.verifyCb = self.connected
        c = reactor.connectTCP('', 5001, self.f)


    def connected(self):
        self.button.setText("Connected")

    def create_main_frame(self):        
        page = QWidget()        


        
        self.button = QPushButton('Connect', page)

        self.pullDown = QComboBox()
        self.rValue = QLCDNumber()


         
        vbox1 = QVBoxLayout()
        vbox1.addWidget(self.button)
        vbox1.addWidget(self.pullDown)
        vbox1.addWidget(self.rValue)
        self.pullDown.addItems(self.registers.keys())
        self.pullDown.currentIndexChanged.connect(self.selectionchange)

        self.connect(self.button,
                     QtCore.SIGNAL('clicked()'),
                     self.padeConnect)
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
            self.f.readRegisters()
            

if __name__ == "__main__":
    import sys
    form = regWindow()
    form.show()
    reactor.run()
