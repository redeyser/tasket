#!/usr/bin/python
# -*- coding: utf-8 -*-

import re,sys,os;
from optparse import OptionParser;
import shutil
from tfile import *

ERR_NOT_OPEN_MAIN_FILE  = 1
ERR_NOT_OPEN_READ_FILE  = 2
ERR_NOT_OPEN_WRITE_FILE = 3
ERR_NOT_READ            = 4
ERR_NOT_WRITE           = 5

TAG_UUID = 'UUID'
TAG_HASH = 'HASH'

TL_LINE     = 'line'
TL_PART     = 'part'
TL_INDEX    = 'index'

UP_ADD      = 'add'
UP_ID       = 'id'
UP_CONT     = 'cont'
UP_PART     = 'part'
UP_DELETE   = 'delete'

ZN = ['=','^','~','/']

def get_options():
    if len(sys.argv)<2:
        sys.exit(1)
    parser = OptionParser()

    # Файл с разметкой tasket
    parser.add_option("-f", "--file", metavar="FILE")
    # Файл со входными данными
    parser.add_option("-r", "--record", metavar="FILE")
    # Действие: выборка. Два варианта list, part
    # list: Результат список. первое поле номер записи. можно добавить поле TAGS
    # part: Результат файлтаск с полями keys. Если поля не указаны, то записи полностью
    parser.add_option("-l", "--list")
    # Поля для выборки. Через :
    parser.add_option("-k", "--keys",default=None)
    # Условия выборки. Через ,
    parser.add_option("-i", "--id",default=None)
    # Указание на номер записи или uuid при выборке или записи
    parser.add_option("-n", "--number",default=None)
    # Выводит part без значков тэгов, только содержимое. При записи, добавляет нужные значки
    parser.add_option("-o", "--only_content",default=None)

    # Действие: запись изменений. Варианты add id cont
    # Добавление, запись по (n) запись по uuid из содержимого
    parser.add_option("-u", "--update",default=None)
    # Опция - наложения тэгов на существующую запись
    parser.add_option("-m", "--merge",default=False)
    # Выводит part без значков тэгов, только содержимое. При записи, добавляет нужные значки
    parser.add_option("-P", "--repack",default=None)
    #parser.add_option("-t", "--text",default=None)

    (options, args) = parser.parse_args()
    return options

# быстрое изменение тега, удаление тега, удаление записи

def pars_if(s):
    zn = '='
    for _if in s.split(','):
        for z in ZN:
            if _if.find(z)!=-1:
                zn = z
                break
    a = tuple(map(lambda x: x.split(zn)+[zn], s.split(",")))
    return dict([ (x[0],x[1:]) for x in a])


class Tasket:
    def __init__(self, options):
        self.options = options
        if options.keys:
            self.keys = options.keys.split(":")
        else:
            self.keys=None
        if options.id:
            self.id = pars_if(options.id)
        else:
            self.id = None

    def openfiles(self):
        try:
            self.record_data = None
            if self.options.record:
                if self.options.record == '-':
                    self.record_data = sys.stdin.read()
                elif os.path.isfile(self.options.record):
                    frecord = open(self.options.record,"rt")
                    self.record_data = frecord.read()
                    frecord.close()
                else:
                    self.record_data = self.options.record
        except Exception as ex:
            return ERR_NOT_OPEN_WRITE_FILE

        self.task = TaskFiles(self.options.file)
        r = self.task.open()
        if not r:
            return ERR_NOT_OPEN_MAIN_FILE
        return 0

    def verif(self):
        for k,v in self.id.items():
            if k in self.tags:
                val = v[0]
                typ = v[1] 
                if typ == '=':
                    if self.tags[k] == val or val == '*':
                        continue
                elif typ == '~':
                    if self.tags[k].lower().find(val.lower()) != -1:
                        continue
                elif typ == '^':
                    if self.tags[k] != val:
                        continue
                elif typ == '/':
                    if self.tags[k].find(val) == -1:
                        continue
                return False
            else:
                return False
        return True

    def List(self):
        a = [str(self.number)]
        t = [ k for k in self.tags.keys()]
        t = ";".join(t)
        self.tags['TAGS'] = t

        for k in self.keys:
            if k in self.tags:
                if len(self.keys) == 1:
                    a.append(self.tags[k])
                else:
                    a.append(self.tags[k].replace("\\", "\\\\").replace(":", "\\:"))
            else:
                a.append("")
        return ":".join(a)

    def Index(self):
        a = [str(self.number)] + self.task.rfdata
        return ":".join([str(x) for x in a])

    def Part(self):
        if self.keys == None:
            return self.task.tfile.recordData
        else:
            t = '' if self.options.only_content else "\n%%"
            for k in self.keys:
                if k in self.tags:
                    tag = "" if self.options.only_content else "\n%" + k + "%\n"
                    t += tag + self.tags[k]
            return t
        return ""

    def Split(self):
        """ Генератор рарсинга входных данных для массового изменения """
        self.curfrom = self.record_data.find("\n%%\n")
        while self.curfrom != -1 and self.curfrom < len(self.record_data):
            self.curto = self.record_data[self.curfrom + 4:].find("\n%%\n")
            self.curto = len(self.record_data) if self.curto == -1 else self.curfrom + self.curto + 4 
            rpart = self.record_data[self.curfrom:self.curto]
            self.curfrom = self.curto
            yield rpart

    def run(self):
        ret = self.openfiles()
        if ret != 0:
            return ret

        """ Переупаковка """
        if self.options.repack:
            print "REPACK"
            self.task.pack()
            return 0

        """ Список """
        if self.options.list == TL_LINE:
            self.number = -1
            for i in self.task.indexList():
                self.number += 1
                if i[R_STATUS] == ST_EMPTY:
                    continue
                self.task.read(True)
                self.tags = self.task.tfile.tags
                self.tags['HASH'] = i[R_HASH].encode("utf8")
                if TAG_UUID not in self.tags:
                    self.tags[TAG_UUID] = i[R_UUID].encode("utf8")
                if not self.id or self.verif():
                    print self.List()
            return 0

        """ Выборка """
        if self.options.list == TL_PART:
            self.number = -1
            for i in self.task.indexList():
                self.number += 1
                if i[R_STATUS] == ST_EMPTY:
                    continue
                self.task.read(True)
                self.tags = self.task.tfile.tags
                if TAG_UUID not in self.tags:
                    self.tags[TAG_UUID] = i[R_UUID].encode("utf8")
                if not self.id or self.verif():
                    print self.Part()
            return 0

        """ Выборка по индексам """
        if self.options.list == TL_INDEX:
            self.number = -1
            for i in self.task.indexList():
                self.number += 1
                self.tags = dict(zip(R_ORDER,self.task.rfdata))
                self.tags["R_ID"] = str(self.number)
                if not self.id or self.verif():
                    print self.Index()
            return 0

        """ Чтение конкретной записи """
        if self.options.number and not self.options.record and not self.options.update:
            if len(self.options.number) < 10:
                if not self.task.readRec(int(self.options.number)):
                    return ERR_NOT_READ
            else:
                if not self.task.readUUID(self.options.number):
                    return ERR_NOT_READ
            self.tags = self.task.tfile.tags
            if TAG_UUID not in self.tags:
                self.tags[TAG_UUID] = self.task.rfdata[R_UUID].encode("utf8")
            if not self.id or self.verif():
                print self.Part()
            return 0

        """ Добавление новой записи """
        if self.options.update == UP_ADD:
            if not self.task.appendRec(self.record_data):
                return ERR_NOT_WRITE
            print self.task.rfdata[R_UUID]
            return 0 

        """ Изменение записи по контенту + частичная перезапись """
        if self.options.update == UP_CONT:
            if not self.task.writeRec(self.record_data,self.options.merge):
                return ERR_NOT_WRITE
            print self.task.rfdata[R_UUID]
            return 0 

        """ Изменение записи по номеру или uuid + частичная перезапись """
        if self.options.update == UP_ID:
            if self.options.only_content:
                if not self.keys:
                    return ERR_NOT_WRITE
                self.record_data = CH_REC_START + "%" + self.keys[0] + "%\n" + self.record_data
                self.options.merge = True
            if len(self.options.number) < 10:
                if not self.task.writeRec_NUM (self.record_data,int(self.options.number),self.options.merge):
                    return ERR_NOT_WRITE
            else:
                if not self.task.writeRec_UUID (self.record_data,self.options.number,self.options.merge):
                    return ERR_NOT_WRITE
            print self.task.rfdata[R_UUID]
            return 0 

        """ Удаление записи по номеру или uuid """
        if self.options.update == UP_DELETE:
            if len(self.options.number) < 10:
                if not self.task.deleteRec_NUM(int(self.options.number)):
                    return ERR_NOT_WRITE
            else:
                if not self.task.deleteRec_UUID(int(self.options.number)):
                    return ERR_NOT_WRITE
            return 0 

        """ Слияние. Массовое изменение записей по контенту """
        if self.options.update == UP_PART:
            for rdata in self.Split():
                if not self.task.writeRec(rdata,self.options.merge):
                    return ERR_NOT_WRITE
                print self.task.rfdata[R_UUID]
            return 0 

        self.task.close()
        return 0

tasket = Tasket(get_options())
err = tasket.run()
sys.exit(err)

