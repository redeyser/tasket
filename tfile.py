#!/usr/bin/python
# -*- coding: utf-8 -*-
import os,sys
from simfiles import *
import time
import json
import logging
import md5
from uuid import uuid1 as uid
from copy import copy

RSIZE = 144
PREFIX_IDX = 'idx_'       

HD_RECORDS = 1

HD_FILE     = 0
HD_SIZE     = 1
HD_TMFL     = 2
HD_TMDT     = 3
HD_COUNT    = 4

R_UUID      = 0
R_HASH      = 1
R_TM        = 2
R_START     = 3
R_RSIZE     = 4
R_MSIZE     = 5
R_STATUS    = 6

R_ORDER     = ["R_UUID","R_HASH","R_TM","R_START","R_RSIZE","R_MSIZE","R_STATUS"]

TAG_UUID    = "UUID"
TAG_END     = "END"
TAG_DEL     = "DEL"
TAG_ID      = "ID"
TAG_TYPE    = "TYPE"
TAG_HEAD    = "HEAD"
TAG_TEXT    = "TEXT"
TAG_ORDER   = [TAG_ID,TAG_UUID,TAG_HEAD,TAG_TYPE,TAG_TEXT]

ST_EMPTY    = 'empty'
ST_FULL     = 'full'
ST_PART     = 'part'

def getcurtime():
    return time.strftime("%Y-%m-%d %H:%M:%S")

def getfiletime(f):
    tm = time.localtime(os.stat(f).st_mtime)
    return time.strftime("%Y-%m-%d %H:%M:%S",tm)

def taglist(tags):
    return sorted(tags,key=lambda x: x if x not in TAG_ORDER else TAG_ORDER.index(x))

class RFileTask(RFile):
    """ Объект индексов для таск-файла"""
    def __init__(self, filename, rsize, tfile, logger):
        """ Привязываемся к основному файлу """
        self.logger = logger
        self.tfile = tfile
        super(RFileTask, self).__init__(PREFIX_IDX+self.tfile.basename, rsize)

    def _calc_head_data(self):
        tmfile = getfiletime(self.tfile.filename)
        tmcur = getcurtime()
        fl = self.tfile.basename
        sz = len(self.tfile)
        return [fl,sz,tmfile,tmcur]

    def create(self):
        """ Создаем файл индекса """
        if super(RFileTask, self).create():
            self._writeHead(new=True)   
            self.logger.info('created new rfile')
            return True
        return False

    def _writeHead(self,new=False):
        """ Выводим заголовок """
        self.head_data = self._calc_head_data()
        if new:
            self.head_data[HD_SIZE] = 0
        data = json.dumps(self.head_data)
        self.first()
        self.write(data)

    def _readHead(self):
        """ Читаем заголовок """
        self.first()
        if self.read():
            try:
                self.head_data = json.loads(self.data)
                return len(self.head_data) == HD_COUNT
            except:
                self.head_data = [0,"","",""]
                return False

    def verifyHead(self):
        """ Проверяем заголовок """
        if not self._readHead():
            return False
        data = self._calc_head_data()
        self.logger.info("head store: %s" % str(self.head_data))
        self.logger.info("head current: %s" % str(data))
        return reduce(lambda x,y: x and y, map(lambda i: data[i]==self.head_data[i] ,xrange(HD_COUNT-1)))

    def open(self, mode='rb+'):
        """ Открываем или создаем """
        if super(RFileTask, self).open(mode):
            self.logger.info('opened rfile count: %s' % self.count())
            return True
        else:
            return self.create()

class TaskFiles():
    """ Объект для работы с task+idx файлами """
    def __init_log__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        logfile = logging.FileHandler('taskfiles.log')
        logfile.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s \t %(name)s \t %(levelname)s \t %(message)s')
        logfile.setFormatter(formatter)
        self.logger.addHandler(logfile)
        self.logger.info('Task: Start')

    def __init__(self, filename):
        self.__init_log__()
        self.tfile = TFile(filename)
        self.rfile = RFileTask(filename, RSIZE, self.tfile, self.logger)

    def _set_rfdata(self, arr):
        self.rfdata = arr
           
    def _isempty(self):
        return self.rfdata[R_RSIZE] == 0 or self.rfdata[R_STATUS] == ST_EMPTY

    def _find_empty(self, size):
        """ Поиск свободной записи """
        for i in self.indexList():
            if self._isempty() and self.rfdata[R_MSIZE] >= size:
                return True
        return False

    def _gen_tag_uuid(self):
        """ Генерируем запись тега UUID """
        return "\n%" + TAG_UUID +"%\n" + uid().hex

    def _gen_rfdata(self, first = None):
        """ Формируем индексную запись по контенту """
        if first == None:
            first = self.rfdata[R_START]
            msize = self.rfdata[R_MSIZE]
        else:
            msize = self.tfile.data_size
        tm = getcurtime()
        mhash = md5.md5(self.tfile.recordData).hexdigest()
        uuid = self.tfile.tags.get(TAG_UUID)
        end  = self.tfile.tags.get(TAG_END)
        if uuid==None:
            uuid = uid().hex
        rsize = self.tfile.tags_idx[TAG_END] if end != None else self.tfile.data_size
        status = ST_PART if msize > rsize else ST_FULL
        if self.tfile.tags.get(TAG_DEL) != None:
            rsize = 0
            status = ST_EMPTY 
        self._set_rfdata([uuid,mhash,tm,first,rsize,msize,status])

    def _recreate_rfile(self):
        """ Переиндексация """
        self.rfile.close()
        self.rfile.create()
        self.tfile.ReadFirst()
        first = self.tfile.PosRecord()
        count = 0
        while self.tfile.Read():
            last = self.tfile.PosRecord()
            self.tfile.findTags()
            self._gen_rfdata(first)
            self.rfile.append(json.dumps(self.rfdata))
            first = last
            count += 1
        self.rfile.close()
        self.rfile.open()
        self.rfile._writeHead()
        count = self.rfile.count()-1
        self.logger.info('Task: recreated rfile: %s records' % count)
        return True

    def _writeHead(self):
        try:
            self.tfile.close()
            self.rfile._writeHead()
            self.tfile.open()
        except:
            return False
        return True

    def open(self):
        """ Открытие файлов. Создание если нужно """
        if not self.tfile.open():
            self.logger.error('Task: not exists file %s' % self.tfile.filename)
            return False
        if not self.rfile.open():
            self.logger.error('Task: not exists file  and create %s' % self.rfile.filename)
            return False
        if not self.rfile.verifyHead():
            self.logger.warning('Task: rfile old, need recreate')
            self._recreate_rfile()
        return True

    def close(self):
        """ Закрываем все файлы """
        self.tfile.close()
        self.rfile.close()

    def _readIndex(self):
        """ Чтение навигационных данных """
        if not self.rfile.read():
            return False
        self.rfdata = json.loads(self.rfile.data)
        return True

    def _writeIndex(self):
        """ Запись навигационных данных """
        data = json.dumps(self.rfile.data)
        if not self.rfile.write(data):
            return False
        return True

    def getCursor(self):
        """ Курсор записи """
        return self.rfile.cursor - HD_RECORDS

    def first(self):
        """ Читаем навигационные данные первой записи """
        if not self.rfile.setRec(HD_RECORDS):
            return False
        return self._readIndex()

    def last(self):
        """ Читаем навигационные данные последней записи """
        self.rfile.last()
        return self._readIndex()

    def next(self):
        """ Читаем следующие навигационные данные """
        if not self.rfile.next():
            return False
        return self._readIndex()

    def prior(self):
        """ Читаем предыдущие навигационные данные """
        if not self.rfile.prior():
            return False
        return self._readIndex()

    def setRec(self, nrec):
        """ Читаем навигационные данные конкретной записи """
        if not self.rfile.setRec(nrec + HD_RECORDS):
            return False
        return self._readIndex()

    def indexList(self):
        """ Генератор списка индексов """
        if self.first():
            yield self.rfdata
        while self.next():
            yield self.rfdata

    def sortTags(self):
        self.tfile.sortTags(taglist(self.tfile.tags))

    def read(self,sort=False):
        """ Чтение содержимого текущей записи """
        if self.rfdata[R_RSIZE] == 0:
            self.tfile.setData(CH_REC_START)
            return True
        self.tfile._seekAbs(self.rfdata[R_START])
        if self.tfile.read(self.rfdata[R_RSIZE]):
            self.tfile.setData(self.tfile.data)
            if sort:
                self.tfile.findTags()
                self.sortTags()
            return True
        else:
            return False

    def find(self, uuid):
        """ Поиск записи по UUID """
        for i in self.indexList():
            if self.rfdata[R_UUID] == uuid.rstrip("\n").lower():
                return True
        return False

    def readRec(self, nrec, sort=True):
        """ Читаем запись по номеру """
        if not self.setRec(nrec):
            return False
        return self.read(sort)

    def readUUID(self, uuid, sort=True):
        """ Читаем запись по uuid """
        if not self.find(uuid):
            return False
        return self.read(sort)

    def __write(self):
        """ Выводим текущую запись в файл и индекс """
        # Вычисляем размеры
        self.rfdata[R_RSIZE] = self.tfile.data_size
        dsize = self.rfdata[R_MSIZE] - self.rfdata[R_RSIZE]
        # Записываем измененный контент
        self.tfile._seekAbs(self.rfdata[R_START])
        if not self.tfile.write(self.tfile.recordData):
            self.logger.error('_task: error write data %s bytes' % self.tfile.data_size)
            return False
        # Дописываем тэг конца если он влазиет
        if dsize > 0:
            tagend = "\n%" + TAG_END + "%\n"
            tagend = tagend + ' '*(dsize-len(tagend))
            if dsize < len(tagend):
                tagend = ''
            if not self.tfile.write(tagend):
                self.logger.error('_task: error write tag [end]')
                return False
        # Записываем измененный индекс
        if self.rfdata[R_STATUS] == ST_EMPTY:
            self.rfdata[R_RSIZE] = 0
        self.logger.info('_task: write record %s' % (self.rfdata))
        return self.rfile.write( json.dumps(self.rfdata) )

    def _append(self):
        """ Добавление записи в пустое место или в конец """
        # Ищем пустую
        if self._find_empty(self.tfile.data_size):
            self.logger.info('_task: find_empty and write record %s' % (self.getCursor()))
            self._gen_rfdata()
            return self.__write()
        self._gen_rfdata(len(self.tfile))
        # Добавляем в конец    
        self.logger.info('_task: append record %s' % (self.rfdata))
        if not self.tfile.append(self.tfile.recordData):
            return False
        # Добавляем индекс
        if not self.rfile.append(json.dumps(self.rfdata)):
            return False
        return True


    def _delete(self, nrec = None):
        """ Помечаем запись как удаленную """
        if nrec != None:
            self.setRec(nrec)
        self.rfdata[R_UUID] = ''
        self.rfdata[R_HASH] = ''
        self.rfdata[R_TM] = getcurtime()
        self.rfdata[R_STATUS] = ST_EMPTY
        self.rfdata[R_RSIZE] = 0
        self.tfile.setData(CH_REC_START + "%" + TAG_DEL + "%\n")
        if self.__write():
            self.logger.info('_task: delete record [%s]' % (nrec))
            return self.rfile.write(json.dumps(self.rfdata))
        else:
            return False

    def _rewrite(self):
        """ Перезапись контента """
        # Если запись влезает
        if self.rfdata[R_MSIZE] >= self.tfile.data_size:
            self._gen_rfdata()
            return self.__write()
        # Если запись не влезает
        else:
            cur = self.getCursor()
            if not self._append():
                return False
            self._delete(cur)
            self.last()
            return True
                
    def _prepare(self, data):
        """ Подготовка перед записью """
        rdata = copy(data)
        self.tfile.setData(rdata)
        self.tfile.findTags()

    def _savetags(self):
        self.tfile.findTags()
        return copy(self.tfile.tags)

    def _merge(self):
        """ Совмещаем измененные теги с оригиналом """
        changedData = self._savetags()
        self.read(True)
        self.tfile.tags.update(changedData)
        self.sortTags()
        self.tfile.setData(self.tfile.recordData)

    def writeRec_NUM(self, data, nrec, merge=False):
        """ Перезапись по номеру """
        if self.setRec(nrec):
            self._prepare(data)
            if merge:
                self._merge()
            if self._rewrite():
                return self._writeHead()
        return False

    def writeRec_UUID(self, data, uuid = None, merge=False):
        """ Перезапись по UUID указанному прямо или в тэге, если такой есть в файле"""
        self._prepare(data)
        if uuid == None:
            uuid = self.tfile.tags.get(TAG_UUID)
        if uuid != None and self.find(uuid):
            if merge:
                self._merge()
            if self._rewrite():
                return self._writeHead()
        return False

    def writeRec(self, data, merge=False):
        """ Запись целого контента по его UUID из тела """
        if self.writeRec_UUID(data, uuid = None, merge = merge):
            return True
        else:
            return self.appendRec(data)

    def appendRec(self, data):
        """ Добавление новой записи с добавлением UUID """
        self._prepare(data)
        # Генерируем и добавляем UUID
        if TAG_UUID not in self.tfile.tags:
            self.tfile.setData( self.tfile.recordData + self._gen_tag_uuid() )
        if self._append():
            return self._writeHead()
        else:
            return False

    def deleteRec_NUM(self, nrec):
        """ Удаление записи NREC"""
        if self._delete(nrec):
            return self._writeHead()
        else:
            self.logger.error('Task: error delete data')
            return False

    def deleteRec_UUID(self, uuid):
        """ Удаление записи по UUID"""
        if not self.find(uuid):
            self.logger.warning('Task: not find uuid for delete record [%s]' % uuid)
            return False
        if self._delete():
            return self._writeHead()
        else:
            self.logger.error('Task: error delete data %s' % uuid)
            return False

    def pack(self):
        """ Переупаковка основного файла и пересоздание индекса """
        tfile = TFile(self.tfile.filename+'.bak')
        tfile.create()
        for i in self.indexList():
            self.read(True)
            if not self._isempty():
                tfile.write(self.tfile.recordData)
        tfile.close()
        self.close()
        if os.path.isfile(self.tfile.filename+".back"):
            os.remove(self.tfile.filename+'.back')
        os.rename(self.tfile.filename,self.tfile.filename+'.back')
        os.rename(tfile.filename,self.tfile.filename)
        self.logger.error('Task: packed file %s ' % self.tfile.filename)
        return self.open()
