
from __future__ import print_function
import httplib2
import os

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

import datetime

import glob,pickle,random,sys

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/calendar-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/calendar'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'NagMe'


def initCalendar(user=None):
    creds = get_credentials(user=user)
    http = creds.authorize(httplib2.Http())
    serv = discovery.build('calendar','v3',http=http)
    cal1 = serv.calendars().insert(body={"summary":"NagMe",
                                         "description":("Timely and responsible reminders "+
                                                             "to do those pesky tasks you'd "+
                                                             "otherwise let slide, like sending "+
                                                             "that email, making that appointment, "+
                                                             "or writing that application.")}).execute()
    newcal = serv.calendarList().insert(body={"defaultReminders": [{"minutes": 0,
                                                                    "method": "popup"},],
                                              "selected":True,
                                              "id":cal1['id']}).execute()
    fc=open(".nagme_calendar_"+user,"wb")
    pickle.dump(newcal,fc,1)
    fc.close()
    return newcal

def getCalendar(user=None):
    try:
        fc=open(".nagme_calendar_"+user,"rb")
        cal = pickle.load(fc)
        fc.close()
    except:
        print("Can't seem to open calendar file; creating a new one.")
        cal = initCalendar(user=user)
    return cal


class Profile:
    def __init__(self,username,nagcal):
        self.name=username
        self.mycal = nagcal
        self.tasks=[]
        self.scals=[]
        self.activated=False
    def save(self):
        pickle.dump(self,open("."+self.name,"wb"),1)

def startdaemon(daily=True):
    if sys.platform.startswith('linux'):
        if daily:
            #nsf = open("nagshell","r")
            #ns = nsf.read().split('\n')
            #nsf.close()
            #ns[4] = ns[4].split()
            #ns[4][3] = "today"
            #ns[4] = ' '.join(ns[4])
            #ns = '\n'.join(ns)
            #nsf = open("nagshell","w")
            #nsf.write(ns)
            #nsf.close()
            
            nsf = open("nagdaemon.py","r")
            ns = nsf.read().split('\n')
            nsf.close()
            ns[0]="today=True"
            ns[1]="thisweek=False"
            ns = '\n'.join(ns)
            nsf = open("nagdaemon.py","w")
            nsf.write(ns)
            nsf.close()
            
            os.system("gksudo cp nagshell /etc/cron.daily/nagshell")
        else:
            #nsf = open("nagshell","r")
            #ns = nsf.read().split('\n')
            #nsf.close()
            #ns[4] = ns[4].split()
            #ns[4][3] = "week"
            #ns[4] = ' '.join(ns[4])
            #ns = '\n'.join(ns)
            #nsf = open("nagshell","w")
            #nsf.write(ns)
            #nsf.close()  
            
            nsf = open("nagdaemon.py","r")
            ns = nsf.read().split('\n')
            nsf.close()
            ns[0]="today=False"
            ns[1]="thisweek=True"
            ns = '\n'.join(ns)
            nsf = open("nagdaemon.py","w")
            nsf.write(ns)
            nsf.close()
            
            os.system("gksudo cp nagshell /etc/cron.weekly/nagshell")
            
    elif sys.platform.startswith('darwin'):
        print("OS X not yet supported. Womp womp.")
    else:
        print("Automatic scheduling not yet supported on this OS. Womp womp.")
        
def stopdaemon():
    if sys.platform.startswith('linux'):
        daily = os.path.isfile("/etc/cron.daily/nagshell")
        if daily:
            os.system("gksudo rm /etc/cron.daily/nagshell")
        weekly = os.path.isfile("/etc/cron.weekly/nagshell")
        if weekly:
            os.system("gksudo rm /etc/cron.weekly/nagshell")
    elif sys.platform.startswith('darwin'):
        print("OS X not  yet supported. Womp womp.")
    else:
        print("Automatic scheduling not yet supported on this OS. Womp womp.")
    

class Task:
    def __init__(self,name,deadline,advance_notice,workweek=True,weekend=False,workday=True,
                 morning=False,evening=False,frequency_per_week=2,notice_in_days=False,cals=None,
                 calendarId='primary',user=None):
        self.name=name
        self.deadline=deadline
        self.leadtime=advance_notice
        self.timeframe=0
        self.timeofday=0
        self.calendarId=calendarId
        self.user=user
        ndays = 0.0
        if workweek:
            self.timeframe+=1
            ndays+=5.0
        if weekend:
            self.timeframe+=10
            ndays+=2.0
        if ndays==0:
            ndays=7 #Default to notifications every day. Serves you right for inputting nonsense.
        if workday:
            self.timeofday+=1
        if morning:
            self.timeofday+=30
        if evening:
            self.timeofday+=100
        self._day = datetime.timedelta(1) #1 day in timedelta format
        self._week = datetime.timedelta(0,0,0,0,0,0,1) #1 week in timedelta format
        self.frequency = frequency_per_week/ndays #If frequency_per_week is 7 or more, you'll get 1+/day
        if notice_in_days:
            self.firstday = deadline - self.leadtime*self._day
        else:
            self.firstday = deadline - self.leadtime*self._week
        self.fperweek = frequency_per_week
    #Need to be able to schedule reminders for a given day--maybe give it a day, fetch events
    #for that day, and then slot in the right number of notifications?
    #
    #We'll also have to keep track of how many have been done for that week. Not sure how best to do
    #that.
        
        self.calendar = Calendar(self.firstday,self.deadline,cals=cals,user=self.user)
        self.reminders = []
        for w in self.calendar.weeks:
            self.reminders.append([])
        self.event=self.reminder(self.deadline)
        
    def markdone(self):
        credentials = get_credentials(user=self.user)
        http = credentials.authorize(httplib2.Http())
        serv = discovery.build('calendar', 'v3', http=http) 
        for w in self.reminders:
            for r in w:
                try:
                    serv.events().delete(calendarId=self.calendarId,eventId=r[1]['id']).execute()
                except:
                    print("Deletion error for event ",r[1]['summary'])
        try:
            serv.events().delete(calendarId=self.calendarId,eventId=self.event[1]['id']).execute()
        except:
            print("Deletion error for event ",self.event[1]["summary"])
    
    def assign(self,today=False,thisweek=False,progressbar=None,proginc=1.0): #Default is to schedule ALL the reminders
        if today: #nuance needed: if we've already met the quota of reminders for the week, stop.
            now = datetime.datetime.now()
            if now<self.firstday:
                return False
            if now.weekday > 4 and self.timeframe<10: #Weekdays only, and it's a weekend
                return False
            elif now.weekday <=4 and (self.timeframe%10)==0: #Weekends only, and it's a weekday
                return False
            else:
                ntoday = self.calendar.whatdayisit(now)
                kweek = self.calendar.whatweekisit(now)
                if self.frequency>=1:
                    nsofar = 0
                    while nsofar<self.frequency:
                        if (self.timeofday%2)==0: #Not during the day
                            morn=False
                            even=False
                            if (self.timeofday%100)==30: #Morning
                                start = datetime.datetime(now.year,now.month,now.day,7,0,0)
                                end = datetime.datetime(now.year,now.month,now.day,9,0,0)
                                morning=(start,end)
                                trange = morning
                                morn=True
                            if self.timeofday>=100: #Evening
                                start = datetime.datetime(now.year,now.month,now.day,18,0,0)
                                end = datetime.datetime(now.year,now.month,now.day,23,0,0)
                                evening=(start,end)
                                trange=evening
                                even=True
                            if morn and even:
                                trange = random.choice((morn,even))
                        else:
                            end = datetime.datetime(now.year,now.month,now.day,17,0,0)
                            start = datetime.datetime(now.year,now.month,now.day,10,0,0)
                            if self.timeofday>=100: #Evening
                                end = datetime.datetime(now.year,now.month,now.day,23,0,0)
                            if (self.timeofday%100)>=30: #morning
                                start = datetime.datetime(now.year,now.month,now.day,7,0,0)
                            trange = (start,end)
                        if progressbar:
                            progressbar.step(0.5*proginc/self.frequency)
                        if trange[0]>=self.deadline:
                            break
                        timeslot=datetime.datetime(2999,1,1,0,0,0)
                        while timeslot>=self.deadline:
                            timeslot,err = self.calendar.propose(ntoday,tmin=trange[0],tmax=trange[1])
                        self.reminders[kweek].append(self.reminder(timeslot))
                        if progressbar:
                            progressbar.step(0.5*proginc/self.frequency)
                        nsofar+=1
                        if self.frequency-nsofar<1:
                            flip = random.random()
                            if flip>(self.frequency-nsofar):
                                break
                    return True
                else: #We don't do it every day
                    nsofar = len(self.reminders[kweek])
                    if nsofar < min(self.fperweek, len(self.calendar.weeks[kweek])):  #Need more this week
                        flip = random.random()
                        if flip<=self.frequency:  #Figure out if today's the day
                            if (self.timeofday%2)==0: #Not during the day
                                morn=False
                                even=False
                                if (self.timeofday%100)==30: #Morning
                                    start = datetime.datetime(now.year,now.month,now.day,7,0,0)
                                    end = datetime.datetime(now.year,now.month,now.day,9,0,0)
                                    morning=(start,end)
                                    trange = morning
                                    morn=True
                                if self.timeofday>=100: #Evening
                                    start = datetime.datetime(now.year,now.month,now.day,18,0,0)
                                    end = datetime.datetime(now.year,now.month,now.day,23,0,0)
                                    evening=(start,end)
                                    trange=evening
                                    even=False
                                if morn and even:
                                    trange = random.choice((morn,even))
                            else:
                                end = datetime.datetime(now.year,now.month,now.day,17,0,0)
                                start = datetime.datetime(now.year,now.month,now.day,10,0,0)
                                if self.timeofday>=100: #Evening
                                    end = datetime.datetime(now.year,now.month,now.day,23,0,0)
                                if (self.timeofday%100)>=30: #morning
                                    start = datetime.datetime(now.year,now.month,now.day,7,0,0)
                                trange = (start,end)
                            if trange[0]>=self.deadline:
                                return False
                            timeslot=datetime.datetime(2999,1,1,0,0,0)
                            while timeslot>=self.deadline:
                                timeslot,err = self.calendar.propose(ntoday,tmin=trange[0],tmax=trange[1])
                            self.reminders[kweek].append(self.reminder(timeslot))
                            if progressbar:
                                progressbar.step(proginc)
                            nsofar+=1
                        #Todo: if days left in the week <= number of reminders left, do a reminder
                        elif self.calendar.daysleftinweek(now)<=(self.fperweek-len(self.reminders[kweek])):
                            if (self.timeofday%2)==0: #Not during the day
                                morn=False
                                even=False
                                if (self.timeofday%100)==30: #Morning
                                    start = datetime.datetime(now.year,now.month,now.day,7,0,0)
                                    end = datetime.datetime(now.year,now.month,now.day,9,0,0)
                                    morning=(start,end)
                                    trange = morning
                                    morn=True
                                if self.timeofday>=100: #Evening
                                    start = datetime.datetime(now.year,now.month,now.day,18,0,0)
                                    end = datetime.datetime(now.year,now.month,now.day,23,0,0)
                                    evening=(start,end)
                                    trange=evening
                                    even=False
                                if morn and even:
                                    trange = random.choice((morn,even))
                            else:
                                end = datetime.datetime(now.year,now.month,now.day,17,0,0)
                                start = datetime.datetime(now.year,now.month,now.day,10,0,0)
                                if self.timeofday>=100: #Evening
                                    end = datetime.datetime(now.year,now.month,now.day,23,0,0)
                                if (self.timeofday%100)>=30: #morning
                                    start = datetime.datetime(now.year,now.month,now.day,7,0,0)
                                trange = (start,end)
                            if trange[0]>=self.deadline:
                                return False
                            timeslot=datetime.datetime(2999,1,1,0,0,0)
                            while timeslot>=self.deadline:
                                timeslot,err = self.calendar.propose(ntoday,tmin=trange[0],tmax=trange[1])
                            self.reminders[kweek].append(self.reminder(timeslot))
                            if progressbar:
                                progressbar.step(proginc)
                            nsofar+=1
        elif not thisweek: #Go through week by week from the start time and add an  number of reminders
            if self.frequency>=1:
                ndays = int((self.deadline-self.firstday).total_seconds()/86400.0)
                for n in range(0,ndays):
                    day = self.firstday+n*self._day
                    if day.weekday > 4 and self.timeframe<10:
                        pass
                    elif day.weekday <=4 and self.timeframe%10==0:
                        pass
                    else:
                        kweek = self.calendar.whatweekisit(day)
                        nsofar = 0
                        while nsofar<self.frequency:
                            if (self.timeofday%2)==0: #Not during the day
                                morn=False
                                even=False
                                if (self.timeofday%100)==30: #Morning
                                    start = datetime.datetime(day.year,day.month,day.day,7,0,0)
                                    end = datetime.datetime(day.year,day.month,day.day,9,0,0)
                                    morning=(start,end)
                                    trange = morning
                                    morn=True
                                if self.timeofday>=100: #Evening
                                    start = datetime.datetime(day.year,day.month,day.day,18,0,0)
                                    end = datetime.datetime(day.year,day.month,day.day,23,0,0)
                                    evening=(start,end)
                                    trange=evening
                                    even=False
                                if morn and even:
                                    trange = random.choice((morn,even))
                            else:
                                end = datetime.datetime(day.year,day.month,day.day,17,0,0)
                                start = datetime.datetime(day.year,day.month,day.day,10,0,0)
                                if self.timeofday>=100: #Evening
                                    end = datetime.datetime(day.year,day.month,day.day,23,0,0)
                                if (self.timeofday%100)>=30: #morning
                                    start = datetime.datetime(day.year,day.month,day.day,7,0,0)
                                trange = (start,end)
                            if progressbar:
                                progressbar.step(0.5*proginc/(ndays*self.frequency))
                            if trange[0]>=self.deadline:
                                break
                            timeslot=datetime.datetime(2999,1,1,0,0,0)
                            while timeslot>=self.deadline:
                                timeslot,err = self.calendar.propose(n,tmin=trange[0],tmax=trange[1])
                            
                            self.reminders[kweek].append(self.reminder(timeslot))
                            if progressbar:
                                progressbar.step(0.5*proginc/(ndays*self.frequency))
                            nsofar+=1
                            if self.frequency-nsofar<1:
                                flip=random.random()
                                if flip>(self.frequency-nsofar):
                                    break
            else: #We don't do a reminder every day, so we have to go by weeks
                for k in range(0,len(self.calendar.weeks)):
                    days = []
                    week = []
                    palette = []
                    j=0
                    for d in self.calendar.weeks[k]:
                        days.append(d[1]) #day of week numeral
                        week.append(d)
                        palette.append(j)
                        j+=1
                    check=True
                    if self.timeframe<10: #Reminders only on weekdays
                        check=False
                        for d in days:
                            if d<=4: #Weekday
                                check=True
                                break
                    elif self.timeframe%10==0: #Reminders only on weekends
                        check=False
                        for d in days:
                            if d>4: #Weekend
                                check=True
                                break
                    if check: #There are days this week on which we can assign reminders
                        nsofar = 0
                        nerr=0
                        errs = []
                        while nsofar<min(self.fperweek,len(days)):
                            nday = random.choice(palette)
                            palette.remove(nday)
                            day = week[nday]
                            if (self.timeofday%2)==0: #Not during the day
                                morn=False
                                even=False
                                if (self.timeofday%100)==30: #Morning
                                    start = datetime.datetime(day[0].year,day[0].month,
                                                              day[0].day,7,0,0)
                                    end = datetime.datetime(day[0].year,day[0].month,
                                                            day[0].day,9,0,0)
                                    morning=(start,end)
                                    trange = morning
                                    morn=True
                                if self.timeofday>=100: #Evening
                                    start = datetime.datetime(day[0].year,day[0].month,
                                                              day[0].day,18,0,0)
                                    end = datetime.datetime(day[0].year,day[0].month,
                                                            day[0].day,23,0,0)
                                    evening=(start,end)
                                    trange=evening
                                    even=False
                                if morn and even:
                                    trange = random.choice((morn,even))
                            else:
                                end = datetime.datetime(day[0].year,day[0].month,day[0].day,17,0,0)
                                start = datetime.datetime(day[0].year,day[0].month,day[0].day,10,0,0)
                                if self.timeofday>=100: #Evening
                                    end = datetime.datetime(day[0].year,day[0].month,
                                                            day[0].day,23,0,0)
                                if (self.timeofday%100)>=30: #morning
                                    start = datetime.datetime(day[0].year,day[0].month,
                                                              day[0].day,7,0,0)
                                trange = (start,end)
                            if trange[0]>=self.deadline:
                                break
                            timeslot=datetime.datetime(2999,1,1,0,0,0)
                            if progressbar:
                                progressbar.step(0.5*proginc/(self.fperweek*len(self.calendar.weeks)))
                            while timeslot>=self.deadline:
                                timeslot,err = self.calendar.propose(day[-1],trange[0],trange[1])
                            if not err:
                                self.reminders[k].append(self.reminder(timeslot))
                                nsofar+=1
                            else:
                                nerr+=1
                                errs.append(timeslot)
                                if (nsofar+nerr)>=len(week):
                                    for ts in errs:
                                        self.reminders[k].append(self.reminder(ts))
                                        nsofar+=1
                            
                            if progressbar:
                                progressbar.step(0.5*proginc/(self.fperweek*len(self.calendar.weeks)))
                            if self.fperweek-nsofar<1:
                                flip=random.random()
                                if flip>self.fperweek-nsofar:
                                    break
                return True
        else: #Only schedule this week
            now = datetime.datetime.now()
            k = self.calendar.whatweekisit(now)
            if self.frequency>=1:
                for dd in self.calendar.weeks[k]:
                    day = dd[0]
                    if day.weekday > 4 and self.timeframe<10:
                        pass
                    elif day.weekday <=4 and self.timeframe%10==0:
                        pass
                    else:
                        kweek = k
                        nsofar = 0
                        while nsofar<self.frequency:
                            if (self.timeofday%2)==0: #Not during the day
                                morn=False
                                even=False
                                if (self.timeofday%100)==30: #Morning
                                    start = datetime.datetime(day.year,day.month,day.day,7,0,0)
                                    end = datetime.datetime(day.year,day.month,day.day,9,0,0)
                                    morning=(start,end)
                                    trange = morning
                                    morn=True
                                if self.timeofday>=100: #Evening
                                    start = datetime.datetime(day.year,day.month,day.day,18,0,0)
                                    end = datetime.datetime(day.year,day.month,day.day,23,0,0)
                                    evening=(start,end)
                                    trange=evening
                                    even=False
                                if morn and even:
                                    trange = random.choice((morn,even))
                            else:
                                end = datetime.datetime(day.year,day.month,day.day,17,0,0)
                                start = datetime.datetime(day.year,day.month,day.day,10,0,0)
                                if self.timeofday>=100: #Evening
                                    end = datetime.datetime(day.year,day.month,day.day,23,0,0)
                                if (self.timeofday%100)>=30: #morning
                                    start = datetime.datetime(day.year,day.month,day.day,7,0,0)
                                trange = (start,end)
                            if progressbar:
                                progressbar.step(0.5*proginc/(ndays*self.frequency))
                            if trange[0]>=self.deadline:
                                break
                            timeslot=datetime.datetime(2999,1,1,0,0,0)
                            while timeslot>=self.deadline:
                                timeslot,err = self.calendar.propose(n,tmin=trange[0],tmax=trange[1])
                            
                            self.reminders[kweek].append(self.reminder(timeslot))
                            if progressbar:
                                progressbar.step(0.5*proginc/(ndays*self.frequency))
                            nsofar+=1
                            if self.frequency-nsofar<1:
                                flip=random.random()
                                if flip>(self.frequency-nsofar):
                                    break
            else: #We don't do it every day of the week
                days = []
                week = []
                palette = []
                j=0
                for d in self.calendar.weeks[k]:
                    days.append(d[1]) #day of week numeral
                    week.append(d)
                    palette.append(j)
                    j+=1
                check=True
                if self.timeframe<10: #Reminders only on weekdays
                    check=False
                    for d in days:
                        if d<=4: #Weekday
                            check=True
                            break
                elif self.timeframe%10==0: #Reminders only on weekends
                    check=False
                    for d in days:
                        if d>4: #Weekend
                            check=True
                            break
                if check: #There are days this week on which we can assign reminders
                    nsofar = 0
                    nerr=0
                    errs = []
                    while nsofar<min(self.fperweek,len(days)):
                        nday = random.choice(palette)
                        palette.remove(nday)
                        day = week[nday]
                        if (self.timeofday%2)==0: #Not during the day
                            morn=False
                            even=False
                            if (self.timeofday%100)==30: #Morning
                                start = datetime.datetime(day[0].year,day[0].month,
                                                        day[0].day,7,0,0)
                                end = datetime.datetime(day[0].year,day[0].month,
                                                        day[0].day,9,0,0)
                                morning=(start,end)
                                trange = morning
                                morn=True
                            if self.timeofday>=100: #Evening
                                start = datetime.datetime(day[0].year,day[0].month,
                                                        day[0].day,18,0,0)
                                end = datetime.datetime(day[0].year,day[0].month,
                                                        day[0].day,23,0,0)
                                evening=(start,end)
                                trange=evening
                                even=False
                            if morn and even:
                                trange = random.choice((morn,even))
                        else:
                            end = datetime.datetime(day[0].year,day[0].month,day[0].day,17,0,0)
                            start = datetime.datetime(day[0].year,day[0].month,day[0].day,10,0,0)
                            if self.timeofday>=100: #Evening
                                end = datetime.datetime(day[0].year,day[0].month,
                                                        day[0].day,23,0,0)
                            if (self.timeofday%100)>=30: #morning
                                start = datetime.datetime(day[0].year,day[0].month,
                                                        day[0].day,7,0,0)
                            trange = (start,end)
                        if trange[0]>=self.deadline:
                            break
                        timeslot=datetime.datetime(2999,1,1,0,0,0)
                        if progressbar:
                            progressbar.step(0.5*proginc/(self.fperweek))
                        while timeslot>=self.deadline:
                            timeslot,err = self.calendar.propose(day[-1],trange[0],trange[1])
                        if not err:
                            self.reminders[k].append(self.reminder(timeslot))
                            nsofar+=1
                        else:
                            nerr+=1
                            errs.append(timeslot)
                            if (nsofar+nerr)>=len(week):
                                for ts in errs:
                                    self.reminders[k].append(self.reminder(ts))
                                    nsofar+=1
                        
                        if progressbar:
                            progressbar.step(0.5*proginc/(self.fperweek))
                        if self.fperweek-nsofar<1:
                            flip=random.random()
                            if flip>self.fperweek-nsofar:
                                break
        
    def reminder(self,timeslot): #Create a Reminder object and use it to create a calendar event.
        obj = Reminder(timeslot,self.name,self.deadline)
        credentials = get_credentials(user=self.user)
        http = credentials.authorize(httplib2.Http())
        serv = discovery.build('calendar', 'v3', http=http) 
        event = serv.events().insert(calendarId=self.calendarId,body=obj.body).execute()
        #event = 'placeholder'
        return (obj,event)
        
        
class Reminder: #Basically a Python object wrapper for the dictionary used to create an event
    def __init__(self,time,name,deadline,duration=15):
        self.time = time
        self.name = name
        self._duration = duration*datetime.timedelta(0,0,0,0,1) #minutes
        self.deadline = deadline
        self.body = {"creator": { "self": False,
                                  "displayName": "NagMe"},
                     "summary": self.name, # Title of the event.
                     "start": {"dateTime": self.time.isoformat()+'Z'},
                     "description": "Deadline: "+self.deadline.isoformat()+'Z',
                     "visibility": "private", 
                     "end": {"dateTime": (self.time+self._duration).isoformat()+'Z'},
                     "reminders": {"overrides": [{"minutes": 0,
                                                  "method": "popup"},],
                                   "useDefault": False},}

    
class Calendar: #Almost a wrapper for the Schedule class--basically a collection of Schedules,
                #organized into days and weeks, with some awareness of larger timeframes.
    def __init__(self,dayMin,dayMax,cals=None,leadtime=15,user=None):
        '''dayMin and dayMax in YYYY-MM-DD format'''
        self.epoch = datetime.datetime(1970,1,1,0,0,0)
        self.tzh = int(round((datetime.datetime.utcnow()
                              -datetime.datetime.now()).total_seconds()/3600.0))
        if self.tzh>0:
            self.dtz = datetime.datetime(1970,1,1,0,0,0)-datetime.datetime(1970,1,1,abs(self.tzh),0,0)
        else:
            self.dtz = datetime.datetime(1970,1,1,abs(self.tzh),0,0)-datetime.datetime(1970,1,1,0,0,0)

        self._oneday = datetime.datetime(1970,1,2,0,0,0)-datetime.datetime(1970,1,1,0,0,0)

        #y,m,d = dayMin.split('-')
        self.dayi = dayMin
        #y,m,d = dayMax.split('-')
        self.dayf = dayMax + self._oneday
        
        ndays = int(round((self.dayf-self.dayi).total_seconds()/86400.0))
        
        self.user=user
        
        self.days = []
        for n in range(0,ndays):
            cday = self.dayi+n*self._oneday + self.dtz
            self.days.append([cday,cday.weekday(),
                              Schedule(self.dayi+n*self._oneday,
                                       self.dayi+(n+1)*self._oneday,
                                       cals=cals,leadtime=leadtime,user=user)])
        self.cals = cals
        
        #Organize days into weeks, starting on Mondays
        self.weeks = [[]]
        wkd1 = self.days[0][1]
        n=0
        while n<min(7-wkd1,len(self.days)):
            self.weeks[0].append(self.days[n]+[n,])
            n+=1
        while n<len(self.days):
            self.weeks.append([])
            k=0
            margin = len(self.days)-n
            while k<min(7,margin):
                self.weeks[-1].append(self.days[n]+[n,])
                k+=1
                n+=1
        
    def whatdayisit(self,today):
        return int((today-self.dayi).total_seconds()/86400.0)
        
    def whatweekisit(self,today):
        lwk1 = 7 - min(7-self.days[0][1],len(self.days)) #e.g. if we start on Sat, +5 means day 3 is a new week
        return int(((today-self.dayi).total_seconds()/86400.0 + lwk1)/7)
        
    def daysleftinweek(self,today,weekend=True):
        kweek = self.whatweekisit(today)
        daytyp = today.weekday()
        if weekend:
            return (min(self.weeks[kweek][-1][1],6)-daytyp+1) #Sunday is last day of the week
        else:
            return (min(self.weeks[kweek][-1][1],4)-daytyp+1) #Friday is last day of the week
        
    def propose(self,nday,tmin=None,tmax=None):
        ut,lt,err = self.days[nday][2].proposetime(tmin=tmin-self.dtz,tmax=tmax-self.dtz)
        if err:
            print("Warning, schedule is full for day "+str(nday))
        return ut,err
        
    
class Schedule: #List of events in a range of time, along with a comprehensive view of 
                #when a user is free or busy based on the calendars indicated, and the 
                #ability to propose a time based on that availability.
    def __init__(self,timeMin,timeMax,cals=None,leadtime=15,user=None):
        
        self.epoch = datetime.datetime(1970,1,1,0,0,0)
        ts1 = (timeMin-self.epoch).total_seconds()
        ts2 = (timeMax-self.epoch).total_seconds()
        self.dt = ts2-ts1
        self.tstart = timeMin
        self.tend = timeMax
        
        self.dtm = int(self.dt/60.0)
        self.nt = self.dtm/5           #5-minute intervals
        self.ldt = leadtime/5
        
        self.agenda = []
        self.times = []
        self.user=user
        self._5min = datetime.datetime(1970,1,1,0,5,0)-datetime.datetime(1970,1,1,0,0,0)
        for t in range(0,self.nt):
            self.agenda.append(0)
            self.times.append(timeMin+t*self._5min)
        
        credentials = get_credentials(user=self.user)
        http = credentials.authorize(httplib2.Http())
        self.serv = discovery.build('calendar', 'v3', http=http)
        
        if not cals:
            cals = {'id':'primary'} #self.serv.calendarList().list().execute()['items']
        self.events = []
        for c in cals:
            evsr = self.serv.events().list(calendarId=c['id'],timeMin=timeMin.isoformat()+'Z',
                                          timeMax=timeMax.isoformat()+'Z',singleEvents=True,
                                          orderBy='startTime').execute()
            evs = evsr.get('items',[])
            if evs:
                for e in evs:
                    if "end" in e.keys() and 'dateTime' in e['start'].keys():
                        #print(e['start'],e['end'])
                        self.events.append((e['start']['dateTime'],
                                            e['end']['dateTime'],e))
                        t0 = unpackTime(e['start']['dateTime'])
                        t1 = unpackTime(e['end']['dateTime'])
                        dt0 = int((t0-timeMin).total_seconds()/60)
                        n0 = dt0/5
                        dt1 = int((t1-timeMin).total_seconds()/60)
                        n1 = dt1/5
                        for n in range(max(0,n0-self.ldt),min(self.nt,n1)):
                            self.agenda[n] = 1
        
        #print("UTC Times:")
        #for n in range(0,self.nt):
            #print(self.times[n].isoformat(),self.agenda[n])
                        
        self.localtimes = []
        self.tzh = int(round((datetime.datetime.utcnow()
                              -datetime.datetime.now()).total_seconds()/3600.0))
        if self.tzh>0:
            self.dtz = datetime.datetime(1970,1,1,0,0,0)-datetime.datetime(1970,1,1,abs(self.tzh),0,0)
        else:
            self.dtz = datetime.datetime(1970,1,1,abs(self.tzh),0,0)-datetime.datetime(1970,1,1,0,0,0)

        #print("\nLocal Times:")
        for n in range(0,self.nt):
            self.localtimes.append(self.times[n]+self.dtz)
            #print(self.localtimes[-1].isoformat(),self.agenda[n])

    def proposetime(self,tmin=None,tmax=None):
        n0=0
        n1=self.nt-1
        if tmin:
            n0 = max(int((tmin-self.tstart).total_seconds()/60)/5,0)
        if tmax:
            n1 = min(int((tmax-self.tstart).total_seconds()/60)/5,self.nt) - 1
        if 0 in self.agenda:
            while True:
                nt = random.randint(n0,n1)
                if self.agenda[nt]==0:
                    err=False
                    self.agenda[nt]=1
                    break
            utime = self.times[nt]
            ltime = self.localtimes[nt]
        else:
            err=True
            utime = self.times[-1]+self._5min
            ltime = self.localtimes[-1]+self._5min
        return utime,ltime,err
            
            

def get_credentials(user=None):
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    if not user:
        cpath = 'calendar-nagme.json'
    else:
        cpath = 'calendar-nagme-'+user+'.json'
    credential_path = os.path.join(credential_dir,cpath)

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials




def unpackTime(timestring):
    ts = timestring.split('T')
    t0 = datetime.datetime(1970,1,1,0,0,0)
    if len(ts[1].split('-'))>1:
        tz = ts[1].split('-')[1].split(':')[0]
        ts[1] = ts[1].split('-')[0]
        t1 = datetime.datetime(1970,1,1,int(tz))
        dtz = t0-t1
    elif len(ts[1].split('+'))>1:
        tz = ts[1].split('+')[1].split(':')[0]
        ts[1] = ts[1].split('+')[0]
        t1 = datetime.datetime(1970,1,1,int(tz))
        dtz = t1-t0
    else:
        tz = '00'
        t1 = t0
        dtz = t1-t0
    
    ts = 'T'.join(ts)
    
    ndt = datetime.datetime.strptime(ts,"%Y-%m-%dT%H:%M:%S") - dtz #Go from local to UTC
    return ndt