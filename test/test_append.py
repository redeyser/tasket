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
print f.appendRec(data)
data = read(6)
print f.appendRec(data)
data = read(13)
print f.appendRec(data)
data = read(56)
print f.appendRec(data)
f.close()
