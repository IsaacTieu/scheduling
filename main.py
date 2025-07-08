import requests
from ics import Calendar
from config import *

import os
import pickle

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request


import arrow

# Google Calendar API scopes
SCOPES = ['https://www.googleapis.com/auth/calendar.events']
TOKEN_PATH = 'token.pickle'

def get_calendar_service():
    creds = None

    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)

    #  if no valid credentials are available, prompt login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())  # silently refresh token
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save credentials for the next run
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)

    return build('calendar', 'v3', credentials=creds)

def create_shift_event(title: str, location: str, \
                       description: str, start,
                        end, attendees_emails: list):
    '''
    start and end are Arrow.arrow format
    TODO describe args
    '''
    service = get_calendar_service()

    event = {
        'summary': title,
        'location': location,
        'description': description,
        'start': {
            'dateTime': start.isoformat(),
            'timeZone': 'America/Los_Angeles',
        },
        'end': {
            'dateTime': end.isoformat(),
            'timeZone': 'America/Los_Angeles',
        },
        'attendees': [{'email': email} for email in attendees_emails],
        'reminders': {
            'useDefault': True,
        },
    }

    # create event
    event = service.events().insert(
        calendarId='primary',
        body=event,
        sendUpdates='all'  # send email invites
    ).execute()

if __name__ == "__main__":
    url = SLING_CALENDAR_URL
    c = Calendar(requests.get(url).text)

    # Don't want to make repeat calendar invites
    first_month = int(input("Enter the starting month (1-12): "))
    first_day = int(input("Enter the starting day (1-31): "))
    first_year = int(input("Enter the starting year: "))

    compare_date = arrow.get(first_year, first_month, first_day)

    # TODO Make capability for detecting a timestamp as opening/closing

    for event in c.events:
        if event.begin < compare_date:
            continue
        
        # +3 is a hardcoded fix for some weird time reading error
        # start_hour without +3 is 3 hours behind for some reason
        begin = event.begin.shift(hours=+3)
        end = event.end.shift(hours=+3)

        shift_type = ''

        start_hour = begin.to('America/Los_Angeles').hour
        end_hour = end.to('America/Los_Angeles').hour
        # start_hour = begin.hour
        # end_hour = end.hour

        if start_hour <= 10:
            shift_type = 'Opening Shift'
        elif end_hour >= 16:
            shift_type = 'Closing Shift'

        name = event.name.split(" - ", 1)[0].strip()
        location = event.name.split(" - ")[-1].strip()
        role = event.name.split(" - ")[1].strip()

        # Temp bypass for testing
        if not name == "Xiang Meng":
            continue

        if shift_type:
            title = '[' + location.upper() + ']' +  ' ' + role + ' - ' + name + ' - ' + shift_type
        else:
            title = '[' + location.upper() + ']' +  ' ' + role + ' - ' + name

        description = event.description
        #print(event.name)
        # print(title)
        # print(f"begin: {event.begin}")
        # print(f"begin hour: {start_hour}")
        # print(f"end: {event.end}")
        # print(f"end hour: {end_hour}")


        emails = []
        emails.append(EMAILS[name])
        emails.append(JASON)

        try:
            create_shift_event(title, location, description, begin, end, emails)
        except Exception as e:
            print(f'Error sending schedule to {event.name} at {event.begin}: {e}')

