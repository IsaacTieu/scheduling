import requests
from ics import Calendar
from config import *

url = SLING_CALENDAR_URL
c = Calendar(requests.get(url).text)

for event in c.events:
    print(event.name, event.begin, event.end)
