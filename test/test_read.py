#!/usr/bin/python
# -*- coding: utf-8 -*-
from tfile import *
f = TaskFiles('mem.txt')

def read(n):
    if f.readRec(n):
        r = open("txt"+str(n),"wb")
        r.write(f.tfile.recordData)
        r.close()
    else:
        print "error"

f.open()

read(0)
read(6)
read(13)
read(56)
uuid = "04ec92f7cf8311e796eae0cb4e458e4f"
#if f.readUUID(uuid):
    #print "["+f.tfile.recordData+"]"
#    print f.getCursor()
#else:
#    print "error find "+uuid


f.close()
