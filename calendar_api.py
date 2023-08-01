from dateutil.parser import parse
import pytz

from pytz import timezone
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime
from time_utils import convert_to_local_time

def create_service(credentials):
    try:
        service = build('calendar', 'v3', credentials=credentials)
        return service
    except HttpError as error:
        print(f'An error occurred: {error}')

def get_calendars(service):
    try:
        calendar_list = service.calendarList().list().execute()
        return calendar_list.get('items', [])
    except HttpError as error:
        print(f'An error occurred: {error}')

def get_freebusy_info(service, emails, start_date, end_date):
    # Convert the start and end dates to datetime objects
    start_date = datetime.strptime(start_date, "%d.%m.%Y")
    end_date = datetime.strptime(end_date, "%d.%m.%Y")
    
    body = {
        "timeMin": start_date.isoformat()+'Z',  # 'Z' indicates UTC time
        "timeMax": end_date.isoformat()+'Z',
        "items": [{"id": email} for email in emails]
    }

    events_result = service.freebusy().query(body=body).execute()
    calendars = events_result[u'calendars']

    for email, calendar in calendars.items():
        for slot in calendar['busy']:
            slot['start'] = convert_to_local_time(parse(slot['start']))
            slot['end'] = convert_to_local_time(parse(slot['end']))

    return calendars


if __name__ == '__main__':
    credentials = '...'
    service = create_service(credentials)
    calendars = get_calendars(service)
    freebusy_info = get_freebusy_info(service, calendars, '1.1.2023', '2.1.2023')
    print(freebusy_info)
