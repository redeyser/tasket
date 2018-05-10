#!/usr/bin/python
# -*- coding: utf-8 -*-
import os,sys
CH_REC_START = "\n%%\n"
CH_TAG_START = "\n%"
MAX_BUF_READ = 1024

class File(object):
    """ Объект для работы с файлом """
    def __init__(self, filename):
        self.filename = filename
        self.basename = os.path.basename(filename)
        self.dirname = os.path.dirname(filename)
        self.handle = None
        self.__len__()

    def __len__(self):
        """ Размер имеет значение """
        try:
            self.size = os.stat(self.filename).st_size
        except:
            self.size = 0
        return self.size

    def _setcursor(self):
        """ Находим и запоминаем позицию курсора """
        self.cursor=self.handle.tell()

    def _seekLast(self):
        self.handle.seek(0,2)

    def _seekFirst(self):
        self.handle.seek(0,0)

    def _seekCur(self,size):
        self.handle.seek(size,1)

    def _seekAbs(self,size):
        self.handle.seek(size,0)

    def create(self):
        """ Создаем файл """
        try:
            self.handle = open(self.filename,"wb+")
        except:
            return False
        self.size = 0
        return True


    def open(self,mode="rb+"):
        """ Открываем файл, по умолчанию, для чтения и как бинарный
            Получаем размер. Указатель.
        """
        if not os.path.isfile(self.filename):
            return False
        try:
            self.handle = open(self.filename,mode)
        except:
            return False
        self.__len__()
        return True

    def close(self):
        if self.handle:
            self.handle.close()

    def read(self,size = 1):
        try:
            self.data = self.handle.read(size)
            self.data_size = len(self.data)
            if self.data_size ==0:
                return False
            return True
        except:
            return False

    def write(self, data):
        try:
            self.handle.write(data)
            return True
        except:
            return False

    def append(self, data):
        self._seekLast()
        return self.write(data)

    def close(self):
        if self.handle:
            self.handle.close()

class RFile(File):
    """ Файл со строгой длинной записи """
    def __init__(self, filename, recsize = 64, withEndLine = True):
        super(RFile, self).__init__(filename)
        self.recSize = recsize
        self.withEndLine = withEndLine
   
    def open(self, mode='rb+'):
        """ Открываем и считаем записи """
        if super(RFile, self).open(mode):
            self.cursor = 0
            return True
        else:
            return False

    def count(self):
        """ Считаем записи """
        return self.__len__()/self.recSize

    def _seek(self):
        """ Реальная установка курсора """
        self._seekAbs(self.cursor*self.recSize)
        return True

    def setRec(self, nrec):
        """ Установка курсора записи """
        if nrec > self.count()-1 or nrec < 0:
            return False
        else:
            self.cursor = nrec
            return True

    def first(self):
        self.cursor = 0

    def last(self):
        self.cursor = self.count() - 1

    def next(self):
        return self.setRec(self.cursor + 1)

    def prior(self):
        return self.setRec(self.cursor - 1)

    def read(self):
        """ *Читаем запись """
        self._seek()
        return super(RFile, self).read(self.recSize)

    def readRec(self, nrec):
        """ Читаем N запись """
        if self.setRec(nrec):
            return self.read()
        return False

    def _prepare(self, data):
        d = data.ljust(self.recSize)
        if self.withEndLine:
            d = d[:-1] + "\n"
        return d
        
    def _write(self, data):
        """ Записываем запись, выравниваем по размеру"""
        if len(data) > self.recSize:
            return False
        d = self._prepare(data)
        return super(RFile, self).write(d)

    def write(self, data):
        """ *Записываем """
        self._seek()
        return self._write(data)

    def append(self, data):
        """ Добавляем """
        self._seekLast()
        return self._write(data)

class TFile(File):
    """ Объект для работы с файлом с разделителем записи и тега """
    def __init__(self, filename, ch_rec = CH_REC_START, ch_tag = CH_TAG_START):
        super(TFile, self).__init__(filename)
        # В файле первая строка должна быть не записью
        self.ch_rec = ch_rec
        self.ch_tag = ch_tag
        self.maxbuf = MAX_BUF_READ
        self.size_ch_rec = len(self.ch_rec)
        self.recordData = ""

    def setData(self, data):
        self.recordData = data
        self.data_size = len(data)

    def findRecord(self):
        """ Поиск вперед, пока не встретится тег записи. Указатель ставится в началало тела записи 
            Содержимое предыдущей записи будет считано, указатель переместится на следующую
        """
        self.recordData = ""
        self.deltapos = 0
        while True:
            if self.read(self.maxbuf):
                found = self.data.find(self.ch_rec)
                if found != -1:
                    pos = self.size_ch_rec + found - self.data_size
                    self.recordData = self.ch_rec + self.recordData +  self.data[:found]
                    self._seekCur(pos)
                    self.deltapos = -self.size_ch_rec
                    self.data_size = len(self.recordData)
                    return True
                else:
                    self.recordData += self.data
            else:
                self.deltapos = 0
                if self.recordData == "":
                    self.data_size = 0
                    return False
                self.recordData = self.ch_rec + self.recordData
                self.data_size = len(self.recordData)
                return True

    def findTags(self):
        """ Поиск тегов """
        idx = []
        cur = 2
        self.data_size = len(self.recordData)
        while cur < self.data_size-1:
            found = self.recordData[cur:].find(self.ch_tag)
            if found != -1:
                found_end = self.recordData[cur+found+1:].find("\n")
                if found_end == -1:
                    found_end = len(self.recordData)
                else:
                    found_end = cur+found+found_end
                idx.append((cur+found,found_end,self.recordData[cur+found:found_end+1]))
                cur = found_end+1
            else:
                break

        idx.append((len(self.recordData),len(self.recordData),''))
        self.tags={}
        self.tags_idx={}
        for i in xrange(len(idx)-1):
            (start,end,tag) = idx[i]
            tag = tag[2:-1]
            self.tags_idx[tag] = start
            start = end+2
            end = idx[i+1][0]
            content = self.recordData[start:end]
            if content and content[-1]=='\n':
                content = content[:-1]
            self.tags[tag] = content

    def PosRecord(self):
        self._setcursor()
        return self.cursor + self.deltapos

    def ReadFirst(self):
        """ Встаем на первую запись. Читаем все, что до первой записи. """
        self._seekFirst()
        return self.findRecord()

    def Read(self):
        """ Встаем на следующую запись, Читаем содержимое текущей """
        return self.findRecord()

    def sortTags(self,order):
        """ Пересортировываем тэги и формируем запись по новому """
        self.recordData = "\n%%"
        for t in order:
            self.recordData += self.ch_tag + t + "%\n" + self.tags[t]
            



