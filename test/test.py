#!/usr/bin/python
# -*- coding: utf-8 -*-
#from simfiles import RFile
from tfile import *


f = TaskFiles('mem.txt')
f.open()

#for i in f.indexList():
#    f.read()
#    f.tfile.findTags()
#    print "%s\t%s\t%s" % (f.getCursor(),f.tfile.tags.get("ID"),f.tfile.tags.get("HEAD"))

#print f.prior()
#print f.rfdata
#f.setRec(23)
#f.readRec(13)
#print "["+f.tfile.recordData+"]"

print f.deleteRec(13)
r = open("txt","r+b")
data = r.read(1143).rstrip("\n")
print "["+data+"]"
r.close()
print f.appendRec(data)
"""
"""
f.readRec(13)
#print "["+f.tfile.recordData+"]"
#uuid = "04ec92f7cf8311e796eae0cb4e458e4f"
#f.find(uuid)
#f.read()
#print f.tfile.recordData
#print f.getCursor()

#print f.deleteRec(12)
#print f.deleteRec(13)
#print f.readRec(12)
#print f.tfile.recordData
#print f.readRec(13)
#print "["+f.tfile.recordData+"]"




#f.tfile.findTags()
#print f.tfile.tags_idx

#f.Write("furst record")
#f.Write("second record")
#f.readRec(13)
#print  f.tfile.recordData
#f.tfile.findTags()
#print f.tfile.tags['UUID']
#print f.tfile.tags
#print f.tfile.tags['ID']
#f.close()
