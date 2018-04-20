from __future__ import print_function
import os,glob,pickle
import datetime
import Tkinter as tk
import ttk
import tkFont as tF
import CalendarDialog as cald

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

import httplib2

import nagdefs as nd

def _daysinmonth(month,year=None):
    _MONTHS = {"January":31,
               "March":31,
               "April":30,
               "May":31,
               "June":30,
               "July":31,
               "August":31,
               "September":30,
               "October":31,
               "November":30,
               "December":31}
    #year is required if month is February
    if month=="February":
        if not year:
            return 28
        else:
            if ((year%4==0) and (year%100!=0)) or (year%1000==0):
                return 29
            else:
                return 28
    else:
        return _MONTHS[month]

_ALL = tk.N+tk.S+tk.E+tk.W

class ProgressBar:
    def __init__(self,parent,mode='indeterminate'):
        self.mode=mode
        self.parent=parent
    def show(self):
        self.top = tk.Toplevel()
        self.top.transient(master=self.parent)
        self.top.overrideredirect(True)
        #print("We should have a progress bar now")
        self.bar = ttk.Progressbar(self.top,mode=self.mode)
        self.bar.pack()
        self.top.grab_set()
    def start(self,interval=50):
        self.bar.start(interval)
    def stop(self):
        self.bar.stop()
    def step(self,increment):
        self.bar.step(increment)
    def close(self):
        self.top.grab_release()
        self.bar.destroy()
        self.top.destroy()

class NagGui(ttk.Frame):
    def __init__(self, master=None, demo=False):
        
        
        tzh = int(round((datetime.datetime.utcnow()
                        -datetime.datetime.now()).total_seconds()/3600.0))
        if tzh>0:
            self.dtz = datetime.datetime(1970,1,1,0,0,0)-datetime.datetime(1970,1,1,abs(tzh),0,0)
        else:
            self.dtz = datetime.datetime(1970,1,1,abs(tzh),0,0)-datetime.datetime(1970,1,1,0,0,0)
        
        
        
        ttk.Frame.__init__(self, master)
        self.grid(sticky=_ALL)
        self.top=self.winfo_toplevel() 
        self.top.rowconfigure(0, weight=1) 
        self.top.columnconfigure(0, weight=1)
        
        self.demo=demo
        
        self.uservar = tk.StringVar()
        self.userlvar = tk.StringVar()
        self.tasknamevar = tk.StringVar()
        
        self.agendavar = tk.Variable()
        
        self.deadlinevar = tk.StringVar()
        self.leadtimevar = tk.StringVar()
        self.notice_in_days = tk.IntVar()
        self.morningvar = tk.IntVar()
        self.workdayvar = tk.IntVar()
        self.eveningvar = tk.IntVar()
        self.weekdayvar = tk.IntVar()
        self.weekendvar = tk.IntVar()
        self.schedvar = tk.IntVar()
        self.daemonvar = tk.IntVar()
        
        self.acal_listvar = tk.Variable()
        self.scal_listvar = tk.Variable()
        
        self.rarrow = tk.BitmapImage(file="rightarrow.xbm")
        self.larrow = tk.BitmapImage(file="leftarrow.xbm")
        
        self.rowconfigure(0, weight=1) 
        self.columnconfigure(0, weight=1)
        self.HeaderFont = tF.Font(family='Arial',size=18)
        self.title = ttk.Label(self,font=self.HeaderFont,text="NagMe Desktop Client\n",
                               justify=tk.CENTER,anchor=tk.CENTER)
        self.title.grid(row=0,column=0,columnspan=2,sticky=_ALL)
        if self.demo:
            self.user = "Tommy Thompson"
            self.createWidgets()
        else:
            #try:
            self.user = pickle.load(open(".user","rb"))
            self.loadUser(self.user)
            self.createWidgets()
            #except:
                #self.newuserframe = ttk.LabelFrame(self,text="New User")
                #self.newusersubtt = ttk.Label(self.newuserframe,text="Welcome to NagMe! \nTo get started, create a username.")
                #self.userlabel = ttk.Label(self.newuserframe,text="Name: ")
                #self.userentry = ttk.Entry(self.newuserframe,textvariable=self.uservar)
                #self.userbutton = ttk.Button(self.newuserframe,text="Go!",command=self.createuser)
                #self.newuserframe.grid(row=1,sticky=_ALL)
                #self.newusersubtt.grid(row=0,column=0,columnspan=2,sticky=_ALL)
                #self.userlabel.grid(row=1,column=0,sticky=_ALL)
                #self.userentry.grid(row=1,column=1,sticky=_ALL)
                #self.userbutton.grid(row=2,column=1,sticky=_ALL)
        
    def createuser(self):
        self.user = self.uservar.get()
        if self.user!='':
            self.loadUser(self.user)
            self.newuserframe.grid_remove()
            self.newusersubtt.grid_remove()
            self.userlabel.grid_remove()
            self.userentry.grid_remove()
            self.userbutton.grid_remove()
            self.createWidgets()
        
        
    def createWidgets(self):
        
        try:
            fp = open(".profiles","r")
            self.profiles = fp.read().split('\n')
            fp.close()
        except:
            self.profiles = [self.user,]
            
        while '' in self.profiles:
            self.profiles.remove('')
        
        self.userframe = ttk.LabelFrame(self,text="Current User")
        self.userlist = ttk.Combobox(self.userframe,textvariable=self.userlvar,
                                     values=self.profiles)
        self.userlist.set(self.user)
        self.userlist.state(['!disabled','readonly'])
        self.userbutton = ttk.Button(self.userframe,text="Reload",command=self._ui_user)
        
        self.calframe = ttk.LabelFrame(self.userframe,text="Calendars")
        self.avlabel = ttk.Label(self.calframe,text="Available")
        self.sclabel = ttk.Label(self.calframe,text="Watching")
        
        self.acalx = ttk.Scrollbar(self.calframe,orient=tk.HORIZONTAL)
        self.acaly = ttk.Scrollbar(self.calframe,orient=tk.VERTICAL)
        self.acallist = tk.Listbox(self.calframe,listvariable=self.acal_listvar,
                                     xscrollcommand=self.acalx.set,yscrollcommand=self.acaly.set,
                                     selectmode=tk.MULTIPLE)
        self.acalx['command'] = self.acallist.xview
        self.acaly['command'] = self.acallist.yview
        
        self.addcallbutton = ttk.Button(self.calframe,image=self.rarrow,command=self.addcals)
        self.delcallbutton = ttk.Button(self.calframe,image=self.larrow,command=self.delcals)
        
        
        self.scalx = ttk.Scrollbar(self.calframe,orient=tk.HORIZONTAL)
        self.scaly = ttk.Scrollbar(self.calframe,orient=tk.VERTICAL)
        self.scallist = tk.Listbox(self.calframe,listvariable=self.scal_listvar,
                                     xscrollcommand=self.scalx.set,yscrollcommand=self.scaly.set,
                                     selectmode=tk.MULTIPLE)
        self.scalx['command'] = self.scallist.xview
        self.scaly['command'] = self.scallist.yview
        
        self.newtaskframe = ttk.LabelFrame(self,text="New Task")
        self.taskname_label = ttk.Label(self.newtaskframe,text="Name: ")
        self.taskname_entry = ttk.Entry(self.newtaskframe,textvariable=self.tasknamevar,validate='key')
        self.taskname_entry['validatecommand']=(self.taskname_entry.register(self._changingName),'%P')
        self.task_datelabel = ttk.Label(self.newtaskframe,text="Deadline: ")
        self.task_dateentry = ttk.Entry(self.newtaskframe,textvariable=self.deadlinevar)
        self.task_dateentry.state(['readonly',])
        self.deadlinevar.set("YYYY-MM-DD")
        self.task_datepickb = ttk.Button(self.newtaskframe,text="Pick",command=self.calendard)
        self.task_timef = ttk.Frame(self.newtaskframe)
        self.task_timehl = ttk.Label(self.task_timef,text="Hour:")
        self.task_timehs = tk.Spinbox(self.task_timef,state='readonly',from_=0,to=23,width=3)
        self.task_timeml = ttk.Label(self.task_timef,text="Minutes:")
        self.task_timems = tk.Spinbox(self.task_timef,state='readonly',from_=0,to=59,width=3)
        self.task_timesl = ttk.Label(self.task_timef,text="Seconds:")
        self.task_timess = tk.Spinbox(self.task_timef,state='readonly',from_=0,to=59,width=3)
        
        self.task_leadl = ttk.Label(self.newtaskframe,text="Advance notice:")
        self.task_leadt = ttk.Entry(self.newtaskframe,textvariable=self.leadtimevar,justify=tk.RIGHT,
                                    validate='key')
        self.task_leadt['validatecommand']=(self.task_leadt.register(self._validInt_strict),'%P')
        self.leadtimevar.set('30')
        self.task_dwf = ttk.Frame(self.newtaskframe)
        self.task_weekr = ttk.Radiobutton(self.task_dwf,text="Weeks",value=0,
                                          variable=self.notice_in_days)
        self.task_dayr  = ttk.Radiobutton(self.task_dwf,text="Days",value=1,
                                          variable=self.notice_in_days)
        self.notice_in_days.set(1)
        
        self.userframe.grid(row=1,column=0,sticky=_ALL)
        self.userlist.grid(row=0,column=0,sticky=_ALL)
        self.userbutton.grid(row=0,column=1,sticky=_ALL)
        
        self.calframe.grid(row=1,column=0,columnspan=2,sticky=_ALL)
        self.avlabel.grid(row=0,column=0,sticky=_ALL)
        self.sclabel.grid(row=0,column=3,sticky=_ALL)
        self.acallist.grid(row=1,column=0,rowspan=2,sticky=_ALL)
        self.acalx.grid(row=3,column=0,sticky=_ALL)
        self.acaly.grid(row=1,column=1,rowspan=2,sticky=_ALL)
        self.addcallbutton.grid(row=1,column=2,sticky=tk.S)
        self.delcallbutton.grid(row=2,column=2,sticky=tk.N)
        self.scallist.grid(row=1,column=3,rowspan=2,sticky=_ALL)
        self.scalx.grid(row=3,column=3,sticky=_ALL)
        self.scaly.grid(row=1,column=4,rowspan=2,sticky=_ALL)
        
        self.newtaskframe.grid(row=2,column=0,sticky=_ALL)
        self.taskname_label.grid(row=0,column=0,sticky=_ALL)
        self.taskname_entry.grid(row=0,column=1,columnspan=2,sticky=_ALL)
        self.task_datelabel.grid(row=1,column=0,sticky=_ALL)
        self.task_dateentry.grid(row=1,column=1,sticky=_ALL)
        self.task_datepickb.grid(row=1,column=2,sticky=_ALL)
        self.task_timef.grid(row=2,column=1,columnspan=2,sticky=_ALL)
        self.task_timehl.grid(row=0,column=0,sticky=tk.W)
        self.task_timehs.grid(row=0,column=1,sticky=tk.W)
        self.task_timeml.grid(row=0,column=2,sticky=_ALL)
        self.task_timems.grid(row=0,column=3,sticky=_ALL)
        self.task_timesl.grid(row=0,column=4,sticky=tk.E)
        self.task_timess.grid(row=0,column=5,sticky=tk.E)
        
        self.task_leadl.grid(row=3,column=0,sticky=_ALL)
        self.task_leadt.grid(row=3,column=1,sticky=_ALL)
        self.task_dwf.grid(row=3,column=2,sticky=_ALL)
        self.task_dayr.grid(row=0,column=0,sticky=_ALL)
        self.task_weekr.grid(row=0,column=1,sticky=_ALL)
        
        self.notificationf = ttk.LabelFrame(self.newtaskframe,text="Notification Settings")
        self.notilabel = ttk.Label(self.notificationf,text="Time of Day:")
        self.noti_todf = ttk.Frame(self.notificationf)
        self.noti_morn = ttk.Checkbutton(self.noti_todf,text="Mornings",command=self._tmorning,
                                      variable=self.morningvar)
        self.noti_wday = ttk.Checkbutton(self.noti_todf,text="Workdays",command=self._tworkday,
                                      variable=self.workdayvar)
        self.noti_even = ttk.Checkbutton(self.noti_todf,text="Evenings",command=self._tevening,
                                      variable=self.eveningvar)
        self.morningvar.set(0)
        self.taskmorning = False
        self.workdayvar.set(1)
        self.taskworkday = True
        self.eveningvar.set(0)
        self.taskevening = False
        
        self.notilabel2 = ttk.Label(self.notificationf,text="Weekdays/Weekends: ")
        self.noti_dow = ttk.Frame(self.notificationf)
        self.noti_weekd = ttk.Checkbutton(self.noti_dow,text="Weekdays",command=self._tweekday,
                                      variable=self.weekdayvar)
        self.noti_weeke = ttk.Checkbutton(self.noti_dow,text="Weekends",command=self._tweekend,
                                      variable=self.weekendvar)
        self.weekdayvar.set(1)
        self.taskweekdays = True
        self.weekendvar.set(0)
        self.taskweekend = False
        self.notperweekl = ttk.Label(self.notificationf,text="Notifications per week: ")
        self.notiperweek = tk.Spinbox(self.notificationf,from_=1,to=35,width=6,validate='key')
        self.notiperweek['validatecommand']=(self.notiperweek.register(self._validSpin_strict),'%P')
        
        
        self.notificationf.grid(row=4,column=0,columnspan=3,sticky=_ALL)
        self.notilabel.grid(row=0,column=0,sticky=_ALL)
        self.noti_todf.grid(row=0,column=1,sticky=_ALL)
        self.noti_morn.grid(row=0,column=0,sticky=_ALL)
        self.noti_wday.grid(row=0,column=1,sticky=_ALL)
        self.noti_even.grid(row=0,column=2,sticky=_ALL)
        self.notilabel2.grid(row=1,column=0,sticky=_ALL)
        self.noti_dow.grid(row=1,column=1,sticky=_ALL)
        self.noti_weekd.grid(row=0,column=0,sticky=_ALL)
        self.noti_weeke.grid(row=0,column=1,sticky=_ALL)
        self.notperweekl.grid(row=2,column=0,sticky=_ALL)
        self.notiperweek.grid(row=2,column=1,sticky=_ALL)
        
        self.assignbutton = ttk.Button(self.newtaskframe,text="Add Task",command=self.addtask)
        self.assignbutton.state(['disabled',])
        self.assignbutton.grid(row=5,column=2,sticky=_ALL)
        
        self.agendaframe = ttk.LabelFrame(self,text="Current Tasks")
        self.agendax = ttk.Scrollbar(self.agendaframe,orient=tk.HORIZONTAL)
        self.agenday = ttk.Scrollbar(self.agendaframe,orient=tk.VERTICAL)
        self.agendalist = tk.Listbox(self.agendaframe,listvariable=self.agendavar,height=24,
                                     xscrollcommand=self.agendax.set,yscrollcommand=self.agenday.set,
                                     selectmode=tk.MULTIPLE)
        self.agendax['command'] = self.agendalist.xview
        self.agenday['command'] = self.agendalist.yview
        self.agenda_assign = ttk.Button(self.agendaframe,text="Schedule Reminders",
                                        command=self.bulkassign)
        self.agenda_delete = ttk.Button(self.agendaframe,text="Delete Selected Tasks",
                                        command=self.bulkdelete)
        self.agschedframe = ttk.Frame(self.agendaframe)
        self.todayrdb = ttk.Radiobutton(self.agschedframe,text="Today",value=0,
                                          variable=self.schedvar)
        self.tweekrdb = ttk.Radiobutton(self.agschedframe,text="This Week",value=1,
                                          variable=self.schedvar)
        self.talltrdb = ttk.Radiobutton(self.agschedframe,text="All Reminders",value=2,
                                          variable=self.schedvar)
        self.schedvar.set(0)
        
        self.agendaframe.grid(row=1,column=1,rowspan=3,sticky=_ALL)
        self.agendalist.grid(row=0,column=0,columnspan=2,sticky=_ALL)
        self.agendax.grid(row=1,column=0,columnspan=2,sticky=_ALL)
        self.agenday.grid(row=0,column=2,sticky=_ALL)
        self.agenda_assign.grid(row=2,column=0,sticky=tk.S+tk.E+tk.W)
        self.agenda_delete.grid(row=2,column=1,sticky=tk.S+tk.E+tk.W)
        self.agschedframe.grid(row=3,column=0,columnspan=2,sticky=_ALL)
        self.todayrdb.grid(row=0,column=0,sticky=_ALL)
        self.tweekrdb.grid(row=0,column=1,sticky=_ALL)
        self.talltrdb.grid(row=0,column=2,sticky=_ALL)
        
        self.daemonframe = ttk.LabelFrame(self,text="Automated Reminders")
        self.daemonlabel = ttk.Label(self.daemonframe,text="You can configure NagMe to automatically run on a daily or weekly basis.")
        self.daemondailyrdb = ttk.Radiobutton(self.daemonframe,text="Daily",value=0,
                                              variable=self.daemonvar)
        self.daemonweeklyrdb = ttk.Radiobutton(self.daemonframe,text="Weekly",value=1,
                                               variable=self.daemonvar)
        self.daemonactivate = ttk.Button(self.daemonframe,text="Activate",command=self.activatedaemon)
        self.daemondeactivt = ttk.Button(self.daemonframe,text="Deactivate",command=self.killdaemon)
        if not self.demo:
            if self.profile.activated:
                self.daemonactivate.state(['disabled',])
                self.daemondeactivt.state(['!disabled',])
            else:
                self.daemonactivate.state(['!disabled',])
                self.daemondeactivt.state(['disabled',])
        else:
            self.daemondeactivt.state(['disabled',])
        
        self.daemonframe.grid(row=3,column=0,columnspan=2,sticky=_ALL)
        self.daemonlabel.grid(row=0,column=0,columnspan=4,sticky=_ALL)
        self.daemondailyrdb.grid(row=1,column=0,sticky=_ALL)
        self.daemonweeklyrdb.grid(row=1,column=1,sticky=_ALL)
        self.daemonactivate.grid(row=1,column=2,sticky=_ALL)
        self.daemondeactivt.grid(row=1,column=3,sticky=_ALL)
        
        #self.quit = ttk.Button(self, text='Quit', command=self.quit)
        #self.quit.grid(row=0, column=1, sticky=tk.N+tk.S+tk.E+tk.W)
        
    def _oktaskbutton(self):
        daytime = self.taskmorning + self.taskworkday + self.taskevening
        weektime = self.taskweekdays + self.taskweekend
        if self.deadlinevar.get()=="YYYY-MM-DD":
            dateset = False
        else:
            dateset = True
        leadyn = self._validInt()
        nperwyn = self._validSpin()
        
        if (daytime*weektime*dateset*leadyn*nperwyn):
            self.assignbutton.state(['!disabled',])
        else:
            self.assignbutton.state(['disabled',])
        
    def _validInt(self):
        try:
            x=int(self.leadtimevar.get())
            return True
        except:
            return False
        
    def _validSpin(self):
        try:
            x=int(self.notiperweek.get())
            return True
        except:
            return False
                
    def _validInt_strict(self,inStr):
        if inStr=='':
            return True
        try:
            x=int(inStr)
            return True
        except:
            return False
        
    def _validSpin_strict(self,inStr):
        if inStr=='':
            return True
        try:
            x=int(inStr)
            return True
        except:
            return False
        
    def _changingName(self,inStr):
        if inStr=='':
            self.assignbutton.state(['disabled',])
        self._oktaskbutton()
        return True
        
    def addcals(self):
        seln = self.acallist.curselection()
        #print(seln)
        if len(seln)>0:
            if self.selcalendarnames[0]=='':
                self.selcalendarnames=[]
            nuscals = []
            nuscalnames = []
            for sn in seln:
                nuscalnames.append(self.calendarnames[sn])
                for c in self.calendarlist:
                    if c["summary"]==nuscalnames[-1]:
                        nuscals.append(c)
                        break
                #print(nuscals[-1])
                self.selectedcalendars.append(nuscals[-1])
                self.profile.scals.append(nuscals[-1])
                self.selcalendarnames.append(nuscalnames[-1])
            for n in range(0,len(nuscals)):
                self.calendarlist.remove(nuscals[n])
                self.calendarnames.remove(nuscalnames[n])
            if len(self.selcalendarnames)==0:
                self.selcalendarnames=['',]
            if len(self.calendarnames)==0:
                self.calendarnames=['',]
            self.calendarnames = sorted(self.calendarnames)
            self.selcalendarnames = sorted(self.selcalendarnames)
            self.acal_listvar.set(tuple(self.calendarnames))
            self.scal_listvar.set(tuple(self.selcalendarnames))
            self.profile.save()
    
    def delcals(self):
        seln = self.scallist.curselection()
        if len(seln)>0:
            if self.calendarnames[0]=='':
                self.calendarnames=[]
            nuacals = []
            nuacalnames = []
            for sn in seln:
                nuacalnames.append(self.selcalendarnames[sn])
                for c in self.selectedcalendars:
                    if c["summary"]==nuacalnames[-1]:
                        nuacals.append(c)
                        break
                self.calendarlist.append(nuacals[-1])
                self.calendarnames.append(nuacalnames[-1])
            for n in range(0,len(nuacals)):
                self.selectedcalendars.remove(nuacals[n])
                self.profile.scals.remove(nuacals[n])
                self.selcalendarnames.remove(nuacalnames[n])
            if len(self.selcalendarnames)==0:
                self.selcalendarnames=['',]
            if len(self.calendarnames)==0:
                self.calendarnames=['',]
            self.calendarnames = sorted(self.calendarnames)
            self.selcalendarnames = sorted(self.selcalendarnames)
            self.acal_listvar.set(tuple(self.calendarnames))
            self.scal_listvar.set(tuple(self.selcalendarnames))
            self.profile.save()
        
    def _tmorning(self):
        if self.morningvar.get()==0:
            self.taskmorning=False
        else:
            self.taskmorning=True
        self._oktaskbutton()
            
    def _tworkday(self):
        if self.workdayvar.get()==0:
            self.taskworkday=False
        else:
            self.taskworkday=True
        self._oktaskbutton()
            
    def _tevening(self):
        if self.eveningvar.get()==0:
            self.taskevening=False
        else:
            self.taskevening=True
        self._oktaskbutton()
            
    def _tweekday(self):
        if self.weekdayvar.get()==0:
            self.taskweekdays=False
        else:
            self.taskweekdays=True
        self._oktaskbutton()
            
    def _tweekend(self):
        if self.weekendvar.get()==0:
            self.taskweekend=False
        else:
            self.taskweekend=True
        self._oktaskbutton()
        
    def calendard(self):
        #Many thanks to stackoverflow user Moshe Kaplan (https://github.com/moshekaplan)
        date=cald.CalendarDialog(self.top)
        if date.result:
            self.deadline = date.result
            self.deadlinevar.set(self.deadline.date())
        self._oktaskbutton()
        
    def _ui_user(self):
        self.user = self.userlvar.get()
        if not self.demo:
            self.loadUser(self.user)
        else:
            self.agendavar.set(("4/18/2018      TESS Launch!","4/20/2018      Friday; Go Home"))
        
    def loadUser(self,user):
        self.calendar = nd.getCalendar(user=user)
        bar = ProgressBar(self.top)
        bar.show()
        bar.start()
        try:
            self.profile = pickle.load(open("."+user,"rb"))
            self.profile.mycal = self.calendar
            self.profile.save()
            newuser = False
        except:
            self.profile = nd.Profile(user,self.calendar)
            os.system("echo "+user+">>.profiles")
            newuser = True
        
        self._credentials = nd.get_credentials(user=user)
        http = self._credentials.authorize(httplib2.Http())
        self._service = discovery.build('calendar','v3',http=http)
        self.calendarlist = self._service.calendarList().list().execute()['items']
        for nc in self.calendarlist:
            if nc["id"]==self.calendar["id"]:
                self.calendarlist.remove(nc)
                
        self.user=user
        fu = open(".user","wb")
        pickle.dump(self.user,fu,1)
        fu.close()
        
        tasklist=[]
        for t in self.profile.tasks:
            tasklist.append((t.deadline+self.dtz).date().isoformat()+'      '+t.name)
        if len(tasklist)==0:
            tasklist=['',]
        self.agendavar.set(tuple(tasklist))
        
        self.calendarnames = []
        for c in self.calendarlist:
            self.calendarnames.append(c["summary"].encode('utf-8'))
        
        self.selectedcalendars = self.profile.scals[:]
        self.selcalendarnames = []
        for c in self.selectedcalendars:
            self.selcalendarnames.append(c['summary'].encode('utf-8'))
        if len(self.selcalendarnames)==0:
            self.selcalendarnames=['',]
            
        for n in range(0,len(self.selectedcalendars)):
            cal = self.selectedcalendars[n]
            cname = self.selcalendarnames[n]
            try:
                self.calendarlist.remove(cal)
            except:
                pass
            try:
                self.calendarnames.remove(cname)
            except:
                pass
            
        self.calendarnames = sorted(self.calendarnames)
        self.selcalendarnames = sorted(self.selcalendarnames)
        self.acal_listvar.set(tuple(self.calendarnames))
        self.scal_listvar.set(tuple(self.selcalendarnames))
        
        self.updatetaskpane()
        bar.stop()
        bar.close()
        
    def updatetaskpane(self):
        tasklines = []
        for tsk in self.profile.tasks:
            day = (tsk.deadline+self.dtz).date().strftime("%m/%d/%Y")
            name = tsk.name
            tasklines.append(day+"      "+name)
        if len(tasklines)==0:
            tasklines=['',]
        self.agendavar.set(tuple(sorted(tasklines)))
        
    def addtask(self):
        hrs = int(self.task_timehs.get())
        mns = int(self.task_timems.get())
        sec = int(self.task_timess.get())
        ddln = self.deadline+datetime.timedelta(0,sec,0,0,mns,hrs,0)-self.dtz
        nadv = int(self.leadtimevar.get())
        if self.notice_in_days.get()==0:
            nid=False
        else:
            nid=True
        bar = ProgressBar(self.top)
        bar.show()
        bar.start()
        self.profile.tasks.append(nd.Task(self.tasknamevar.get(),ddln,nadv,
                                          workweek=self.taskweekdays,weekend=self.taskweekend,
                                          workday=self.taskworkday,morning=self.taskmorning,
                                          evening=self.taskevening,
                                          frequency_per_week=int(self.notiperweek.get()),
                                          notice_in_days=nid,cals=self.profile.scals,
                                          calendarId=self.profile.mycal["id"],
                                          user=self.user))
        self.profile.save()
        self.updatetaskpane()
        self._taskreset()
        bar.stop()
        bar.close()
        
    def _taskreset(self):
        self.tasknamevar.set('')
        self.deadlinevar.set('YYYY-MM-DD')
        #self.task_timehs.selection('range',0,tk.END)
        #self.task_timehs.selection_clear()
        #self.task_timehs.insert(0,'0')
        #self.task_timems.selection('range',0,tk.END)
        #self.task_timems.selection_clear()
        #self.task_timems.insert(0,'0')
        #self.task_timess.selection('range',0,tk.END)
        #self.task_timess.selection_clear()
        #self.task_timess.insert(0,'0')
        self.leadtimevar.set('30')
        self.notice_in_days.set(1)
        self.morningvar.set(0)
        self.workdayvar.set(1)
        self.eveningvar.set(0)
        self.weekdayvar.set(1)
        self.weekendvar.set(0)
        #self.notiperweek.selection('range',0,tk.END)
        #self.notiperweek.selection_clear()
        #self.notiperweek.insert(0,'1')
        self.assignbutton.state(['disabled',])
        
    def bulkassign(self):
        if self.demo:
            pass
        else:
            seln = self.agendalist.curselection()
            if len(seln)>0:
                bar = ProgressBar(self.top,mode='determinate')
                bar.show()
                howmany = self.schedvar.get()
                if howmany==0:
                    today=True
                    thisweek=False
                elif howmany==1:
                    today=False
                    thisweek=True
                elif howmany==2:
                    today=False
                    thisweek=False
                for sn in seln:
                    tn=self.agendalist.get(sn)[16:]
                    for ct in self.profile.tasks:
                        if ct.name==tn:
                            ct.assign(today=today,thisweek=thisweek,progressbar=bar,
                                      proginc = 100.0/len(seln))
                            break
                bar.close()
                self.profile.save()
            
    def bulkdelete(self):
        if self.demo:
            pass
        else:
            seln = self.agendalist.curselection()
            if len(seln)>0:
                for sn in seln:
                    tn=self.agendalist.get(sn)[16:] #First 16 characters are always date+spaces
                    for ct in self.profile.tasks:
                        #print(ct.name,tn[16:])
                        if ct.name==tn:
                            ct.markdone()
                            self.profile.tasks.remove(ct)
                            break
                self.updatetaskpane()
                self.profile.save()
                
    def activatedaemon(self):
        self.daemondeactivt.state(['!disabled',])
        self.daemonactivate.state(["disabled",])
        self.profile.activated=True
        self.profile.save()
        if self.daemonvar.get()==0:
            nd.startdaemon(daily=True)
        else:
            nd.startdaemon(daily=False)
    
    def killdaemon(self):
        self.daemondeactivt.state(['disabled',])
        self.daemonactivate.state(["!disabled",])
        self.profile.activated=False
        self.profile.save()
        nd.stopdaemon()
     
                
if __name__=="__main__":

    try:
        hf = open(".home","r")
        home = hf.read()
        hf.close()
    except:
        hf = open(".home","w")
        home = os.getcwd().replace('\n','')
        hf.write(home)

    nsf = open("nagshell","r")
    ns = nsf.read().split('\n')
    nsf.close()
    ns[2] = ns[2].split()
    ns[2][1] = home
    ns[2] = ' '.join(ns[2])
    ns = '\n'.join(ns)
    nsf = open("nagshell","w")
    nsf.write(ns)
    nsf.close()

    app = NagGui(demo=False)
    app.master.title("NagMe")
    app.mainloop()