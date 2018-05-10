#!/usr/bin/python
# -*- coding: utf-8 -*-
from tfile import *
f = TaskFiles('mem.txt')
f.open()
print f.deleteRec_NUM(0)
print f.deleteRec_NUM(6)
print f.deleteRec_UUID('04ec92edcf8311e796eae0cb4e458e4f')
print f.deleteRec_NUM(56)
f.close()

