
from __future__ import print_function
import httplib2
import os

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

import datetime

import glob,pickle

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/calendar-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Google Calendar API Python Quickstart'

class Task:
    def __init__(self,name,deadline,advance_notice,workweek=True,weekend=False,workday=True,
                 morning=False,evening=False,frequency_per_week=2):
        self.name=name
        self.deadline=deadline
        self.leadtime=advance_notice
        self.timeofweek=0
        self.timeofday=0
        if workweek:
            self.timeframe+=1
        if weekend:
            self.timeframe+=10
        if workday:
            self.timeofday+=1
        if morning:
            self.timeofday+=10
        if evening:
            self.timeofday+=100
        self.frequency = frequency_per_week/7.0 #If frequency_per_week is 7 or more, you'll get 1+/day
    #Need to be able to schedule reminders for a given day--maybe give it a day, fetch events
    #for that day, and then slot in the right number of notifications?
    #
    #We'll also have to keep track of how many have been done for that week. Not sure how best to do
    #that.

def get_credentials():
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
    credential_path = os.path.join(credential_dir,
                                   'calendar-python-quickstart.json')

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

def main():
    """Shows basic usage of the Google Calendar API.

    Creates a Google Calendar API service object and outputs a list of the next
    10 events on the user's calendar.
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
    print('Getting the upcoming 10 events')
    eventsResult = service.events().list(
        calendarId='primary', timeMin=now, maxResults=10, singleEvents=True,
        orderBy='startTime').execute()
    events = eventsResult.get('items', [])

    if not events:
        print('No upcoming events found.')
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(start, event['summary'])


def schedule():
    tasks = glob.glob("tasks/*.nag")
    
#Calendar list: c=service.calendarList().list().execute(), and then c['summary'] etc
'''
calendars = service.calendarList().list().execute()
events=[]
for cal in calendars[0][1]:
  eventlist = service.events().list(calendarId=cal['id'],timeMin=t1,timeMax=t2,singleEvents=True,
'''

if __name__ == '__main__':
    main()