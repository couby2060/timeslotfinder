from dateutil.parser import parse
import pytz

from pytz import timezone
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime
from time_utils import convert_to_local_time
from datetime import time



def create_service(credentials):
    try:
        service = build('calendar', 'v3', credentials=credentials)
        return service
    except HttpError as error:
        print(f'An error occurred: {error}')

def get_calendars(service, email):
    page_token = None
    calendar_list = []
    while True:
        calendar_list_entry = service.calendarList().list(pageToken=page_token).execute()
        for calendar_list_entry in calendar_list_entry['items']:
            if calendar_list_entry['id'] == email:
                calendar_list.append(calendar_list_entry)
        page_token = calendar_list_entry.get('nextPageToken')
        if not page_token:
            break
    return calendar_list

def get_freebusy_info(service, emails, start_date, end_date):
    # Convert the start and end dates to datetime objects and set the time
    #start_date = datetime.strptime(start_date, "%d.%m.%Y")
    #end_date = datetime.strptime(end_date, "%d.%m.%Y")

    if start_date.date() == datetime.today().date():
        # If the start date is today, set the start time to the current time
        start_date = datetime.combine(start_date, datetime.now().time())
    else:
        # Otherwise, set the start time to 00:00
        start_date = datetime.combine(start_date, time.min)

    # Set the end time to 23:59:59
    end_date = datetime.combine(end_date, time.max)
    
    body = {
        "timeMin": start_date.isoformat()+'Z',  # 'Z' indicates UTC time
        "timeMax": end_date.isoformat()+'Z',
        "items": [{"id": email} for email in emails]
    }

    events_result = service.freebusy().query(body=body).execute()
    calendars = events_result[u'calendars']

# Note: Here, we need to convert the time to the local timezone if needed
#    for email, calendar in calendars.items():
#        for slot in calendar['busy']:
#            slot['start'] = convert_to_local_time(parse(slot['start']))
#            slot['end'] = convert_to_local_time(parse(slot['end']))

    return calendars


if __name__ == '__main__':
    credentials = '...'
    service = create_service(credentials)
    calendars = get_calendars(service)
    freebusy_info = get_freebusy_info(service, calendars, '1.1.2023', '2.1.2023')
    print(freebusy_info)
