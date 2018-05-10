#!/usr/bin/python
# -*- coding: utf-8 -*-
from curses import wrapper
import curses

X = 0
Y = 1

KEY_ESC     = [27]
KEY_Q       = [ord('q')]
KEY_F       = [102]
KEY_ENTER   = [10]
KEY_UP      = [27,91,65]
KEY_DOWN    = [27,91,66]
KEY_PGUP    = [27,91,53,126]
KEY_PGDOWN  = [27,91,54,126]
KEY_END     = [27,79,70]
KEY_HOME    = [27,79,72]
KEY_F1      = [27,79,80]
KEY_F2      = [27,79,81]
KEY_F3      = [27,79,82]
KEY_F4      = [27,79,83]
KEY_F5      = [27,91,49,53,126]
KEY_F6      = [27,91,49,55,126]
KEY_F7      = [27,91,49,56,126]
KEY_F8      = [27,91,49,57,126]
KEY_F9      = [27,91,49,58,126]
KEY_F10     = [27,91,49,59,126]

KEYS_FUNCT = [KEY_F1,KEY_F2,KEY_F3,KEY_F4,KEY_F5,KEY_F6,KEY_F7,KEY_F8,KEY_F9,KEY_F10]

def ulen(s):
    return len(s.decode('utf8'))

def keycompare(press,key):
    if len(press)!=len(key):
        return False
    for n,code in enumerate(press):
        if key[n] != code:
            return False
    return True

def rawinput(win, x, y, prompt_string,echo=True):
    win.addstr(x, y, prompt_string)
    if echo:
        curses.echo() 
        curses.curs_set(1)
    win.refresh()
    input = win.getstr(x, y+len(prompt_string))
    win.addstr(x,y," "*(len(prompt_string)+len(input)))
    if echo:
        curses.noecho() 
        curses.curs_set(0)
    win.refresh()
    return input

class Window:
    def __init__(self,win=None,textcolor=0,curcolor=1,sizes=[10,10],startxy=[0,0],refresh=None):
        if win != None:
            self.win = win
        else:
            self.win = curses.newwin(*(sizes + startxy))
        self.startxy = startxy
        self.sizes = self.win.getmaxyx()
        self.textcolor = textcolor
        self.curcolor = curcolor
        self.refresh = refresh
        self.tlist=[]
        self.pos_cursor=0
        self.pos_page=0
        self.pos_data=[]
                
    def clear(self):
        self.win.bkgd(' ',curses.color_pair(self.textcolor))
        #self.win.erase()
        #if self.refresh != None:
        #    self.refresh()
        self.win.refresh()

    def _print_empline(self,x,y,color):
        self.win.addstr(x,y,' '*(self.sizes[Y]-2), curses.color_pair(color))

    def refreshdata(self,tlist):
        self.tlist = tlist
        self.set_cursor()
        
    def menu_init(self, tlist = [], columns = [], exitcode = KEY_ESC, funct_refresh = None, headcolor = None, funct_process = None):
        self.tlist = tlist
        if len(columns) == 0 and len(tlist) > 0:
            columns = [ str(n) for n,t in enumerate(tlist[0]) ]
        if columns[-1] == 'TAGS':
            self.columns = columns[:-1]
        else:
            self.columns = columns
        self.exitcode = exitcode
        self.funct_menu_process = funct_process
        self.headcolor = headcolor if headcolor!=None else self.textcolor
        self.pagesize = self.sizes[X] - 2
        self.set_cursor(0,0)
        self.funct_menu_refresh = funct_refresh


    def _menu_calc_cols_sizes(self):
        self.columns_sizes = [ ulen(col) for col in self.columns ]
        for t in self.tlist:
            for i,s in enumerate(self.columns):
                s = t[i]
                self.columns_sizes[i] = max(ulen(s)+2,self.columns_sizes[i])

    def _menu_print_head(self):
        for col in xrange(len(self.columns)):
            margin = 0 if col == 0 else sum(self.columns_sizes[:col])
            if margin>self.sizes[Y]+2:
                continue
            self.win.addstr(0,margin+1, self.columns[col],curses.color_pair(self.headcolor))

    def _menu_print_list(self):
        for line,text in enumerate(self.tlist[self.pos_page:self.pos_page+self.pagesize+1]):
            self._menu_print_line(line)

    def _menu_print_line(self,line):
        color = self.curcolor if line == self.pos_cursor else self.textcolor
        curtext = self.tlist[self.pos_page + line] 
        self._print_empline(line+1,1,color)
        for col in xrange(len(self.columns)):
            margin = 0 if col == 0 else sum(self.columns_sizes[:col])
            if margin>self.sizes[Y]+2:
                continue
            lentext = ulen(curtext[col])
            rightpos = lentext + margin + 2
            if rightpos > self.sizes[Y]:
                delta = lentext - (rightpos-self.sizes[Y])
                text = curtext[col].decode('utf8')[:delta].encode('utf8')
            else:
                text = curtext[col]
            self.win.addstr(line+1, margin+1, text, curses.color_pair(color))

    def menu_show(self):
        self._menu_calc_cols_sizes()
        #self.win.clear()
        self._print_empline(0,1,self.headcolor)
        self._menu_print_head()
        self._menu_print_list()
        if self.funct_menu_refresh != None:
            self.funct_menu_refresh()
        self.reshow = True

    def cursor_down(self,nlines):
        if self.pos_page + self.pos_cursor + nlines > len(self.tlist)-1:
            nlines = len(self.tlist)-1-self.pos_page-self.pos_cursor
        if self.pos_cursor + nlines > self.pagesize:
            self.set_cursor(page = min(self.pos_page + nlines, len(self.tlist)-self.sizes[X]+1))
            self.menu_show()
            return
        ncur = self.pos_cursor
        self.set_cursor(cursor = self.pos_cursor + nlines)
        self._menu_print_line(ncur)
        self._menu_print_line(self.pos_cursor)

    def cursor_up(self,nlines):
        if self.pos_page + self.pos_cursor - nlines < 0:
            nlines = self.pos_cursor + self.pos_page
        if self.pos_cursor - nlines < 0:
            self.set_cursor(page=max(self.pos_page - nlines,0))
            self.menu_show()
            return
        ncur = self.pos_cursor
        self.set_cursor(cursor = self.pos_cursor - nlines)
        self._menu_print_line(ncur)
        self._menu_print_line(self.pos_cursor)

    def set_cursor(self,page=None,cursor=None):
        self.keypress = True
        if page != None:
            self.pos_page = page
        if cursor != None:
            self.pos_cursor = cursor
        if len(self.tlist)>self.pos_cursor+self.pos_page:
            self.pos_data = self.tlist[self.pos_cursor+self.pos_page]
        else:
            self.pos_data = []

    def key_press(self):
        press=[]
        c = self.win.getch()
        if c == -1:
            return press
        while c!=-1:
            press.append(c)
            c = self.win.getch()
        return press

    def menu_run(self):
        self.menu_show()
        while True:
            self.keypress = False
            self.reshow = False
            press = self.key_press()
            if self.funct_menu_process != None:
                key,keypress,reshow = self.funct_menu_process(press)
                if keypress:
                    self.keypress = self.keypress or keypress
                    press = key
                if reshow:
                    self.menu_show()
                    continue
            if keycompare(press, self.exitcode):
                return False
            elif keycompare(press, KEY_ENTER):
                return True
            elif keycompare( press, KEY_DOWN):
                self.cursor_down(1)
            elif keycompare(press, KEY_UP):
                self.cursor_up(1)
            elif keycompare(press, KEY_PGDOWN):
                self.cursor_down(self.pagesize)
            elif keycompare(press, KEY_PGUP):
                self.cursor_up(self.pagesize)
            elif keycompare(press, KEY_HOME):
                self.cursor_up(len(self.tlist))
            elif keycompare(press, KEY_END):
                self.cursor_down(len(self.tlist))
            if self.keypress and not self.reshow:
                if self.funct_menu_refresh != None:
                    self.funct_menu_refresh()
                self.keypress = False


