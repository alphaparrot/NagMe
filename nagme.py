
from __future__ import print_function
import httplib2
import os

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

import datetime

import glob,pickle,random

import nagdefs as nd

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/calendar-python-quickstart.json
#SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
SCOPES = 'https://www.googleapis.com/auth/calendar'
CLIENT_SECRET_FILE = 'client_secret.json'
#APPLICATION_NAME = 'Google Calendar API Python Quickstart'
APPLICATION_NAME = 'NagMe'

class Profile:
    def __init__(self,username,nagcal):
        self.name=username
        self.mycal = nagcal
        self.tasks=[]
        self.scals=[]
    def save(self):
        pickle.dump(self,open("."+self.name,"wb"),1)


def initCalendar(user=None):
    creds = nd.get_credentials(user=user)
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
    

def cli():
    
    print("Welcome to the NagMe Command Line Interface.\n")
    
    try:
        user=pickle.load(open(".user","rb"))
        print("Current user: "+user)
    except:
        user=raw_input("Enter a username: ")
        fu = open(".user","wb")
        pickle.dump(user,fu,1)
        fu.close()
    
    nagcal = getCalendar(user=user)
    
    creds = nd.get_credentials(user=user)
    http = creds.authorize(httplib2.Http())
    serv = discovery.build('calendar','v3',http=http)
    cals = serv.calendarList().list().execute()['items']
    for nc in cals:
        if nc["id"]==nagcal["id"]:
            cals.remove(nc)
    
    try:
        userprof = pickle.load(open("."+user,"rb"))
    except:
        userprof = Profile(user,nagcal)
    
    while True:
        print("\nEnter one of the following commands:\n\n"+
              "l : List all available calendars \n"+
              "c : List currently-selected calendars \n"+
              "s : Select calendars \n"+
              "a : Add task \n"+
              "u : Switch user \n"+
              "q : Quit \n\n")
        command = raw_input("Command: ")
        
        if command=="c":
            listscals(userprof.scals)
        elif command=="l":
            listcals(cals)
        elif command=="s":
            userprof.scals=selectcals(userprof.scals,cals)
            userprof.save()
        elif command=="a":
            userprof.tasks.append(addtask(userprof.scals,nagcal,user))
            userprof.save()
        elif command=="u":
            user = raw_input("Enter username: ")
            fu = open(".user","wb")
            pickle.dump(user,fu,1)
            fu.close()
            nagcal = getCalendar(user=user)
            creds = nd.get_credentials(user=user)
            http = creds.authorize(httplib2.Http())
            serv = discovery.build('calendar','v3',http=http)
            cals = serv.calendarList().list().execute()['items']
            for nc in cals:
                if nc["id"]==nagcal["id"]:
                    cals.remove(nc)
            print("\nWelcome, "+user)
            try:
                userprof = pickle.load(open("."+user,"rb"))
            except:
                userprof = Profile(user,nagcal)
        elif command=="q":
            break
        else:
            print("I'm sorry, I didn't get that.")
    
def listcals(cals):
    print("\nAvailable calendars:\n")
    for n in range(0,len(cals)):
        print('[%02d]'%n,cals[n]["summary"])
    
def listscals(scals):
    print("\n")
    if len(scals)>0:
        print("Currently-selected calendars:")
        for nc in scals:
            print(nc["summary"])
    else:
        print("No calendars currently selected.")
    
def selectcals(scals,cals):
    listcals(cals)
    listscals(scals)
    while True:
        okstat = raw_input("Enter the number of the calendar you would"+
                           " like to add to the watch list, or hit 'Enter' to continue: ")
        if okstat=='':
            if len(scals)>0:
                break
            else:
                print("You must select at least one calendar to continue.")
        try:
            ncal = int(okstat)
            scals.append(cals[ncal])
            listscals(scals)
            print("\n")
        except:
            print("Invalid number entered. Please try again.")
    return scals

def addtask(scals,nagcal,user):
    
    tzh = int(round((datetime.datetime.utcnow()
                    -datetime.datetime.now()).total_seconds()/3600.0))
    if tzh>0:
        dtz = datetime.datetime(1970,1,1,0,0,0)-datetime.datetime(1970,1,1,abs(tzh),0,0)
    else:
        dtz = datetime.datetime(1970,1,1,abs(tzh),0,0)-datetime.datetime(1970,1,1,0,0,0)

    name=raw_input("\nEnter a name for the task: ")
    
    deadline = cliDialogT("Enter a deadline in the format YYYY-MM-DD/HH:MM:SS : ",dtz)
            
    nid = cliDialogAB("Will advance notice be given in weeks (w) or days (d)? ","d","w")
            
    nadv = cliDialogN("How many weeks or days in advance would you like to be notified?")
            
    workweek = cliDialogAB("Weekdays okay? (y/n): ","y","n")
    
    weekend = cliDialogAB("Weekends okay? (y/n): ","y","n")
    
    if not workweek and not weekend:
        print("You have to do it SOMETIME asshole, so you're getting weekend notifications.")
        weekend=True
    
    morns = cliDialogAB("Mornings okay? (y/n): ","y","n")
    
    eves = cliDialogAB("Evenings okay? (y/n): ","y","n")
    
    days = cliDialogAB("During the day okay? (y/n): ","y","n")
    
    if not morns and not eves and not days:
        print("You have to do it SOMETIME asshole, so you're getting evening notifications.")
        eves=True
        
    nfreq = cliDialogN("How many notifications per week would you like?")
    
    print("Working....")
    task = nd.Task(name,deadline,nadv,workweek=workweek,weekend=weekend,workday=days,
                   morning=morns,evening=eves,frequency_per_week=nfreq,notice_in_days=nid,
                   cals = scals,calendarId=nagcal["id"],user=user)
    print("Filling your schedule.....")
    task.assign()
    print("Done!")
    
    return task
    
def cliDialogAB(prompt,optionA,optionB):
    ans = raw_input(prompt)
    while True:
        if ans==optionA:
            outcome=True
            break
        elif ans==optionB:
            outcome=False
            break
        else:
            ans = raw_input("Please enter either "+optionA+" or "+optionB+": ")
    return outcome

def cliDialogN(prompt):
    print(prompt)
    ans = raw_input("Enter a number: ")
    while True:
        try:
            num = int(ans)
            break
        except:
            ans = raw_input("Please enter a number: ")
    return num

def cliDialogT(prompt,dtz):
    timestring = raw_input(prompt)
    while True:
        try:
            time = readinput(timestring,utcoffset=dtz)
            break
        except:
            timestring = raw_input("Please enter a date in the correct format: ")
    return time
    
def readinput(timestring,utcoffset=None):
    date,time=timestring.split('/')
    year,month,day = date.split('-')
    hour,minute,sec = time.split(':')
    year = int(year)
    month = int(month)
    day = int(day)
    hour = int(hour)
    minute = int(minute)
    sec = int(sec)
    dt = datetime.datetime(year,month,day,hour,minute,sec)
    if utcoffset:
        dt -= utcoffset
    return dt


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

def schedule():
    tasks = glob.glob("tasks/*.nag")
    


if __name__ == '__main__':
    cli()
    #s=Schedule(datetime.datetime(2018,4,13,12,0,0),datetime.datetime(2018,4,13,21,0,0))