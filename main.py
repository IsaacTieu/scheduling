import requests
from ics import Calendar
from config import *

from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Google Calendar API scopes
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def get_calendar_service():
    # start OAuth2 flow
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
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

    # TODO Make capability for detecting a timestamp as opening/closing

    for event in c.events:
        name = event.name.split(" - ", 1)[0].strip()
        location = event.name.split(" - ")[-1].strip()
        title = location + ' - ' + name

        begin = event.begin
        end = event.end
        description = event.description

        emails = []
        emails.append(EMAILS[name])
        emails.append(JASON)

        try:
            create_shift_event(title, location, description, begin, end, emails)
        except Exception as e:
            print(f'Error sending schedule to {event.name} at {event.begin}: {e}')

