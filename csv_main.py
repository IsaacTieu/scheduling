import csv
import re
from datetime import datetime, timedelta
import os
import pickle

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import arrow

from config import *

# Google Calendar API scopes
SCOPES = ['https://www.googleapis.com/auth/calendar.events']
TOKEN_PATH = 'token.pickle'

def get_calendar_service():
    creds = None

    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials are available, prompt login
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

def create_shift_event(title: str, location: str, 
                       description: str, start,
                        end, attendees_emails: list):
    '''
    start and end are Arrow.arrow objects
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
        calendarId=SHARED_CALENDAR_ID,
        body=event,
        sendUpdates='all'  # send email invites
    ).execute()

def parse_time_string(time_str):
    """Parse time string like '12:00 AM - 1:00 PM • 13h' into start and end times"""
    # Extract the time range part (before the bullet point)
    time_part = time_str.split(' • ')[0]
    start_str, end_str = time_part.split(' - ')
    
    # Parse start time
    start_time = datetime.strptime(start_str.strip(), '%I:%M %p').time()
    
    # Parse end time
    end_time = datetime.strptime(end_str.strip(), '%I:%M %p').time()
    
    return start_time, end_time

def parse_shift_details(shift_text):
    """Parse shift details to extract role, location, and description"""
    lines = shift_text.strip().split('\n')
    
    role = None
    location = None
    description = ""
    
    for line in lines:
        line = line.strip()
        if 'Proctor' in line and '•' in line:
            # Extract role and location from lines like "Proctor A • Sutardja Dai 200"
            parts = line.split(' • ')
            if len(parts) >= 2:
                role = parts[0].strip()
                location = parts[1].strip()
        elif line and not line.startswith('Unavailable') and not re.match(r'^\d+:\d+', line):
            # This is likely the event description
            if description:
                description += " " + line
            else:
                description = line
    
    return role, location, description

def parse_csv_schedule(csv_file_path):
    """Parse the CSV schedule file and extract shift information"""
    shifts = []
    
    with open(csv_file_path, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        rows = list(reader)
    
    # Find header row (first row)
    header = rows[0]
    dates = [col.strip() for col in header[1:] if col.strip()]  # Skip first empty column
    
    # Find where "Scheduled shifts" section starts
    scheduled_start = -1
    for i, row in enumerate(rows):
        if row and "Scheduled shifts" in row[0]:
            scheduled_start = i + 1
            break
    
    if scheduled_start == -1:
        print("Could not find 'Scheduled shifts' section")
        return shifts
    
    # Process each person's schedule starting from scheduled_start
    for i in range(scheduled_start, len(rows)):
        row = rows[i]
        
        # Skip empty rows
        if not row or not row[0].strip():
            continue
            
        name = row[0].strip()
        if not name:
            continue
            
        print(f"Processing person: {name}")
        
        # Process each day's schedule for this person
        for j, cell in enumerate(row[1:], 0):
            if j >= len(dates) or not cell.strip():
                continue
                
            date_str = dates[j]
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                print(f"Could not parse date: {date_str}")
                continue
            
            # Parse the cell content for shifts
            shifts_for_day = parse_day_schedule(cell, name, date_obj)
            shifts.extend(shifts_for_day)
    
    return shifts

def parse_day_schedule(cell_content, name, date_obj):
    """Parse a single day's schedule for a person"""
    shifts = []
    
    if not cell_content or not cell_content.strip():
        return shifts
    
    # Skip if only contains "Unavailable" or "All day Unavailable"
    # This portion is hardcoded and may need to be changed later
    if cell_content.strip() == "Unavailable" or cell_content.strip() == "All day\nUnavailable":
        return shifts
    
    # Split by lines and look for actual shifts (not unavailable blocks)
    lines = cell_content.strip().split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip unavailable blocks
        if 'Unavailable' in line:
            i += 1
            continue
            
        # Check if this line contains a time range for a shift
        if re.match(r'^\d+:\d+', line) and ' - ' in line and '•' in line and 'Proctor' not in line:
            # This is a shift time line
            try:
                start_time, end_time = parse_time_string(line)
                
                # Look ahead for shift details (should be in next few lines)
                role = None
                location = None
                description = ""
                
                # Check next few lines for proctor info and description
                j = i + 1
                while j < len(lines):
                    detail_line = lines[j].strip()
                    
                    # Stop if we hit another time or unavailable block
                    if re.match(r'^\d+:\d+', detail_line) or 'Unavailable' in detail_line:
                        break
                        
                    if 'Proctor' in detail_line and '•' in detail_line:
                        parts = detail_line.split(' • ')
                        if len(parts) >= 2:
                            role = parts[0].strip()
                            location = parts[1].strip()
                    elif detail_line and detail_line != '':
                        # This is likely the event description
                        if description:
                            description += " " + detail_line
                        else:
                            description = detail_line
                    j += 1
                
                # Only create shift if we have actual shift info (not just unavailable time)
                if role and location:
                    start_datetime = datetime.combine(date_obj, start_time)
                    end_datetime = datetime.combine(date_obj, end_time)
                    
                    # Handle midnight crossover
                    if end_time < start_time:
                        end_datetime += timedelta(days=1)
                    
                    # Convert to Arrow objects in Pacific timezone
                    start_arrow = arrow.get(start_datetime, 'America/Los_Angeles')
                    end_arrow = arrow.get(end_datetime, 'America/Los_Angeles')
                    
                    shift = {
                        'name': name,
                        'start': start_arrow,
                        'end': end_arrow,
                        'role': role,
                        'location': location,
                        'description': description
                    }
                    shifts.append(shift)
                    print(f"  Found shift: {role} at {location} on {date_obj}")
                
                i = j - 1  # Skip the lines we've processed
                
            except Exception as e:
                print(f"Error parsing shift for {name} on {date_obj}: {e}")
                print(f"Problematic line: {line}")
        
        i += 1
    
    return shifts

def determine_shift_type(description):
    """Determine if this is an opening or closing shift"""
    if not description:
        return ""
    
    description_lower = description.lower()
    if "closing" in description_lower:
        return "Closing Shift"
    elif "opening" in description_lower:
        return "Opening Shift"
    else:
        return ""

def create_title(name, role, location, shift_type):
    """Create the event title in the same format as the original"""
    if shift_type:
        return f'[{location.upper()}] {role} - {name} - {shift_type}'
    else:
        return f'[{location.upper()}] {role} - {name}'

def main():
    csv_file_path = 'shifts-export.csv' 
    shifts = parse_csv_schedule(csv_file_path)
    
    for shift in shifts:
        shift_type = determine_shift_type(shift['description'])
        title = create_title(shift['name'], shift['role'], shift['location'], shift_type)
        
        if shift['name'] not in EMAILS:
            print(f"Warning: No email found for {shift['name']}")
            continue
        
        emails = [EMAILS[shift['name']]]
        
        try:
            create_shift_event(
                title=title,
                location=shift['location'],
                description=shift['description'],
                start=shift['start'],
                end=shift['end'],
                attendees_emails=emails
            )
            print(f"Created event: {title}")
        except Exception as e:
            print(f"Error creating event for {shift['name']} at {shift['start']}: {e}")

if __name__ == "__main__":
    main()