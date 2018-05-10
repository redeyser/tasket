#!/usr/bin/python
# -*- coding: utf-8 -*-
import locale
from curses import wrapper
import curses
#import configparser
from iniparse import INIConfig
import re
from optparse import OptionParser;
import shutil
import os,sys
from subprocess import Popen, PIPE, STDOUT,call
from libncurs import KEY_Q, KEY_F1, KEY_F2, KEY_F5, KEY_ESC, keycompare, Window, rawinput
import logging

VERSION = '1.0.1'
CONFFILE = '.tasket.conf'
DEFAULT = 'default'
DEFAULT_PROFILE = { 'bgcolor'   : 16,   'fgcolor': 7, 
                    'bghicolor' : 4,    'fghicolor':7,
                    'bgfoot'    : 4,    'fgfoot': 14,
                    'bgcur'     : 6,    'fgcur': 16,
                    'bgsub'     : 5,    'fgsub': 7,
                    'editor':'vim',
                    'file': 'work/mem.txt', 'tasket': 'work/tasket.py', 
                    'default_tag':'TYPE',
                    'keyslist_0': 'TYPE:ID:HEAD:TAGS'}
DELIM = ':'
ESC = "\\"
PDELIM = '_delim_'

COLOR_BASE      = 1
COLOR_HI        = 2 
COLOR_BORDER    = 3 
COLOR_CURSOR    = 4 
COLOR_SUB       = 5

SIZE_TOP        = 1
SIZE_BOTTOM     = 3

TIMEOUT = 5

def get_options():
    parser = OptionParser()
    parser.add_option("-p", "--profile")
    (options, args) = parser.parse_args()
    return options

def run_subprocess(cmd):
    process= Popen(cmd, stdout=PIPE, stdin=PIPE, stderr=STDOUT)
    return process.communicate()[0]

class Client:
    def __init__(self,stdscr,params):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        logfile = logging.FileHandler('ncurstask.log')
        logfile.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s \t %(name)s \t %(levelname)s \t %(message)s')
        logfile.setFormatter(formatter)
        self.logger.addHandler(logfile)
        self.logger.info('Start')
        def read_keyfunct_pair(name):
            h = {}
            for k in self.profile.keys():
                if k.find(name)!=-1:
                    key = k[-1]
                    h[key] = self.profile[k]
            return h
        self.tlist=[]
        if params.profile:
            profname = params.profile
        else:
            profname = DEFAULT
        self.conffile = os.environ['HOME'] + '/' + CONFFILE
        self.config={}
        if os.path.exists(self.conffile):
            self.config = INIConfig(open(self.conffile))
            #self.config.read(self.conffile)
        self.profile = DEFAULT_PROFILE
        if profname in self.config:
            self.config =  dict([ (p,int(self.config[profname][p])) \
                if self.config[profname][p].isdigit() else \
                (p,self.config[profname][p]) for p in self.config[profname] ] )
            self.profile.update( self.config )
        self.taskprog = os.environ['HOME'] + '/' + self.profile['tasket']
        self.taskfile = os.environ['HOME'] + '/' + self.profile['file']
        self.keys_list = read_keyfunct_pair("keyslist")
        self.keys_filter = read_keyfunct_pair("filter")
        self.keys_search = read_keyfunct_pair("search")
        self.keys_run = read_keyfunct_pair("run")
        if not os.path.exists(self.taskfile):
            raise Exception("file not exists %s" % self.taskfile)
        if not os.path.exists(self.taskprog):
            raise Exception("tasket.py not exists")
        self.stdscr = stdscr
        self.__init_scr(stdscr)
        #stdscr.addstr(str(self.keys_list))

    def __init_scr(self,stdscr):
        curses.init_pair(COLOR_BASE, self.profile['fgcolor'], self.profile['bgcolor'])
        curses.init_pair(COLOR_HI, self.profile['fghicolor'], self.profile['bghicolor'])
        curses.init_pair(COLOR_BORDER, self.profile['fgfoot'], self.profile['bgfoot'])
        curses.init_pair(COLOR_CURSOR, self.profile['fgcur'], self.profile['bgcur'])
        curses.init_pair(COLOR_SUB, self.profile['fgsub'], self.profile['bgsub'])
        curses.noecho() 
        curses.curs_set(0)
        stdscr.clear()
        stdscr.refresh()
        self.mx,self.my = stdscr.getmaxyx()
        self.__initbase_win()

    def __initbase_win(self):
        self.winbase = Window(None,COLOR_BASE,COLOR_CURSOR,[self.mx-SIZE_BOTTOM, self.my],[SIZE_TOP,0])
        self.winfoot = Window(None,COLOR_BORDER,COLOR_CURSOR,[self.mx, self.my],[self.mx-SIZE_BOTTOM+1,0])
        self.winhead = Window(None,COLOR_BORDER,COLOR_CURSOR,[SIZE_TOP, self.my],[0,0],self._winhead_refresh)
        self.winsub  = Window(None,COLOR_SUB,COLOR_CURSOR,[self.mx/2, self.my/4],[self.mx/4,self.my/3],None)
        self.winbase.clear()
        self.winhead.clear()
        self.winfoot.clear()
        self.winbase.win.timeout(TIMEOUT)
        self.winsub.win.timeout(TIMEOUT)

    def _winhead_refresh(self):
        self.winhead.clear()
        self.winhead.win.addstr(0,1,"TASKET "+VERSION+" "+self.taskfile,curses.color_pair(COLOR_BORDER))
        count = "["+str(str(self.winbase.pos_cursor+self.winbase.pos_page+1)+":"+str(len(self.winbase.tlist)))+"]"
        self.winhead.win.addstr(0,self.my-13,count.rjust(12),curses.color_pair(COLOR_BORDER))
        self.winhead.win.refresh()
        self._winfoot_refresh()

    def _winfoot_refresh(self):
        if self.winbase.tlist:
            self.winfoot.clear()
            self.winfoot.win.move(0,0)
            self.winfoot.win.clrtoeol()
            self.winfoot.win.addstr(0,0,self.winbase.pos_data[-1],curses.color_pair(COLOR_BORDER))
            self.winfoot.win.refresh()

    def tasklist(self,keys,filters):
        self.curfilters = filters
        if keys == None:
            keys = self.curkeys
        else:
            self.curkeys = keys
        self.keyslist = ['#'] + keys.split(':')
        filt = "-i " + filters if filters != None else ""
        if not 'TAGS' in self.keyslist:
            self.keyslist.append('TAGS')
            keys+=':TAGS'
        #cmd = "%s -f %s -l list -k %s %s" % (self.taskprog,self.taskfile,keys,filt)
        #self.logger.info(cmd)
        res = run_subprocess(("%s -f %s -l line -k %s %s" % (self.taskprog,self.taskfile,keys,filt)).split(' '))
        lines = res.split("\n")
        if lines[-1] == '':
            del lines[-1]
        self.tlist = [map(lambda x: x.replace(PDELIM,DELIM),l.replace(ESC+DELIM,PDELIM).split(DELIM)) for l in lines]

    def tasklist_n(self,key):
        keys = self.keys_list[key]
        filt = self.keys_filter.get(key)
        self.tasklist(keys,filt)
        return True

    def runcmd(self,cmd):
        cmd = cmd.replace("%number%",self.winbase.pos_data[0])
        m = re.findall("%tag_(.*?)%",cmd)
        if len(m):
            for n in m:
                tag = self.winbase.pos_data[self.winbase.columns.index(n)]
                cmd = cmd.replace("%tag_"+n+"%",tag)
        call([cmd],shell=True) 
    
    def menu_base_process(self,press):
        for key in self.keys_list.keys():
            if keycompare(press,[ord(key)]):
                if self.tasklist_n(key):
                    self.showlist()
                    return [0],True,True
                else:
                    break

        for key in self.keys_search.keys():
            if keycompare(press,[ord(key)]):
                search = rawinput(self.winfoot.win,1,0,"Enter string for searching:")
                if search:
                    self.tasklist(None,"%s%s" % (self.keys_search[key],search.decode('utf8')))
                    self.showlist()
                    return [0],True,True

        for key in self.keys_run.keys():
            if keycompare(press,[ord(key)]):
                self.runcmd(self.keys_run[key])
                return [0],True,False


        if keycompare(press,KEY_F2):
            dtag = self.profile.get('default_tag')
            val = rawinput(self.winfoot.win,1,0,"Enter value for tag [%s]:" % dtag)
            if val:
                self.settag(self.winbase.pos_data[0],dtag,val)
                press=[0]

        if keycompare(press,KEY_F5):
            self.tasklist(None,filters=self.curfilters)
            self.winbase.refreshdata(self.tlist)
            return [0],True,True
            
        return press,False,False

    def menu_sub_process(self,press):
        if keycompare(press,KEY_F1):
            val = rawinput(self.winfoot.win,1,0,"Enter new tag :")
            if val:
                self.settag(self.winbase.pos_data[0],val,"")
                self.winsub.tlist.append([val])
                self.winsub.menu_show()
                press=[0]

        if keycompare(press,KEY_F2):
            val = rawinput(self.winfoot.win,1,0,"Enter value for tag [%s]:" % self.winsub.pos_data[0])
            if val:
                self.settag(self.winbase.pos_data[0],self.winsub.pos_data[0],val)
                press=[0]
        return press,False,False
        

    def showlist(self):
        self.winbase.menu_init(columns=self.keyslist,tlist=self.tlist,exitcode=KEY_Q,headcolor=COLOR_HI,
                                funct_refresh=self._winhead_refresh,funct_process=self.menu_base_process)
        self.winbase.win.clear()
        return
    
    def showtags(self):
        self.winsub.win.clear()
        self.winsub.clear()
        self.curtags = self.winbase.pos_data[-1].split(';')
        data = sorted([ [x] for x in self.curtags ],key=lambda x: x[0])
        self.winsub.menu_init(tlist=data,columns=['TAG'],exitcode=KEY_ESC,
                                headcolor=COLOR_HI,funct_process = self.menu_sub_process)
        return

    def edit(self,number=1,tag="TEXT",encode=False):
        tmp = "/tmp/nctask_%s_%s" % (number,tag)
        if encode:
            _pass = rawinput(self.winfoot.win,1,0,"Enter password:",echo=False)
            cmd = "%s -f %s -n %s -o True -k %s | openssl enc -aes-256-cbc -a -d -pass pass:%s > %s" % (self.taskprog,self.taskfile,number,tag,_pass,tmp)
        else:
            cmd = "%s -f %s -n %s -o True -k %s > %s" % (self.taskprog,self.taskfile,number,tag,tmp)
        os.system(cmd)    
        curses.savetty()
        cmd = "%s %s" % (self.profile['editor'], tmp)
        os.system(cmd)    
        curses.resetty()
        self.winbase.win.clear()
        self.winbase.menu_show()
        self.winsub.win.clear()
        self.winsub.menu_show()
        answer = rawinput(self.winfoot.win,1,0,"Do you want to save this tag [%s] (y/n) " % tag)
        if answer.lower()=='n':
            os.remove(tmp)
            return False
        else:
            if encode:
                cmd = "cat %s | openssl enc -aes-256-cbc -a -pass pass:%s | %s -f %s -n %s -u id -o True -k %s -r -" % (tmp,_pass,self.taskprog,self.taskfile,number,tag)
            else:
                cmd = "cat %s | %s -f %s -n %s -o True -u id -k %s -r -" % (tmp,self.taskprog,self.taskfile,number,tag)
            self.logger.info(cmd)
            os.system(cmd)     
            os.remove(tmp)
            return True

    def appendtag(self,number,tag):
        cmd = "echo '' | %s -f %s -n %s -o True -u id -k %s -r -" % (self.taskprog,self.taskfile,number,tag)
        os.system(cmd)     
        return True    

    def settag(self,number,tag,text):
        cmd = "echo '%s' | %s -f %s -n %s -o True -u id -k %s -r -" % (text,self.taskprog,self.taskfile,number,tag)
        os.system(cmd)     
        return True    

    def run(self):
        self.tasklist(self.profile.get('keyslist_0'),self.profile.get('filter_0'))
        self.showlist()
        choose = True
        while choose:
            choose = self.winbase.menu_run()
            if not choose:
                break
            self.showtags()
            while choose:
                choose = self.winsub.menu_run()
                if not choose:
                    break
                crypt = True if "CRYPT" in self.curtags else False
                self.edit(self.winbase.pos_data[0],self.winsub.pos_data[0],crypt)
            self.winbase.win.clear()
            choose = True

        self.stdscr.clear()
        self.stdscr.refresh()

def main(stdscr):
    options = get_options()
    Cl = Client(stdscr, options)
    Cl.run()

locale.setlocale(locale.LC_ALL, '')
wrapper(main)

