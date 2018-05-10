#!/usr/bin/python
# -*- coding: utf-8 -*-
from tfile import *
f = TaskFiles('mem.txt')
def read(n):
    r = open("txt"+str(n),"rb")
    d=r.read().rstrip("\n")
    r.close()
    return d
f.open()
data = read(0)
print f.writeRec_NUM(data,0)
data = read(6)
print f.writeRec_NUM(data,6)
data = read(13)
print f.writeRec_UUID(data,'04ec92edcf8311e796eae0cb4e458e4f')
data = read(56)
print f.writeRec_NUM(data,56)
f.close()
