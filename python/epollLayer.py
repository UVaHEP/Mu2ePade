import select
import socket
import random 
import threading
import thread 
import sys
import functools
from functools import partial
import padeCommon
from padeCommon import register 
import collections


def connectReadAllSec(host, port, regs):
    s = socket.create_connection((host, port))
    fd = s.fileno()

    ep = select.epoll()
    ep.register(fd, select.EPOLLIN )
    resps = {}
    msgid = 0
    for name, reg in regs.iteritems():
        cmd = padeCommon.regCmd(reg)
        resps[name] = []
        for c in cmd:
            written = s.send(c+'\r\n')
            events = ep.poll(1)
            for fileno, ev in events: 
                if ev & select.EPOLLIN:
                    buf = s.recv(128)
                    resps[name].append(buf.strip())
            if len(events) == 0:
                print 'Failed to read: {0}'.format(name)

    for name,resp in resps.iteritems():
        print '{0}: {1}'.format(name, resp)

    s.close()
        

def commLayer(host, port, msgs, lock):
    
    s = socket.create_connection((host, port))
    fd = s.fileno()

    ep = select.epoll()
    ep.register(fd, select.EPOLLIN )
    run = True
    while run:
            
        events = ep.poll(1)
        for fileno, ev in events:
            if ev & select.EPOLLIN:
                ep.modify(fd, select.EPOLLOUT)
                buf = s.recv(1024)
                print buf.strip()
            elif ev & select.EPOLLOUT:
                written = s.send(msg+'\n')
                ep.modify(fd, 0)
                ep.modify(fd, select.EPOLLIN)
    s.close()


host = '128.143.196.217'
port = 5001
msg_lock = thread.allocate_lock()
registerFile = 'superpaderegs.xml'
registers = padeCommon.readRegisters(registerFile)
t = threading.Thread(None, connectReadAllSec, args=(host, port, registers))
t.start()
#t = threading.Thread(None, commLayer, args=(host, port, msgs, msg_lock))


while t.isAlive():
    pass
#    with msg_lock:
#        msgs.append(m.strip())
    

            
