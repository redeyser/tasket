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
print f.pack()
f.close()
