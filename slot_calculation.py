from auth import authenticate
from calendar_api import create_service, get_calendars, get_freebusy_info
from config import load_config
from datetime import datetime, timedelta
from dateutil.parser import parse
from operator import itemgetter
from time_utils import convert_to_local_time


def calculate_free_slots(emails, start_date, end_date, duration, config):
    credentials = get_credentials()
    service = create_service(credentials)

    calendar_ids = []
    for email in emails:
        calendar_list = get_calendars(service, email)
        calendar_ids += [calendar['id'] for calendar in calendar_list]

    freebusy_info = get_freebusy_info(service, calendar_ids, start_date, end_date)
    print("Free/Busy Info:", freebusy_info)

    busy_times = {}
    for email, calendar in freebusy_info.items():
        busy_times[email] = [{'start': slot['start'], 'end': slot['end']} for slot in calendar['busy']]

    print("Busy Times:", busy_times)

    all_slots = generate_all_slots(start_date, end_date, config)
    print("All Slots:", all_slots)

    free_slots = remove_busy_slots(all_slots, busy_times, duration)
    print("Free Slots:", free_slots)

    return free_slots


def get_calendar_id(service, email):
    calendars = get_calendars(service)
    for calendar in calendars:
        if calendar['summary'] == email:
            return calendar['id']
    return None

def calculate_slots(freebusy_info, start_date, end_date, duration, config):
    # Convert the start and end dates to datetime objects
    start_datetime = datetime.strptime(start_date, '%d.%m.%Y')
    end_datetime = datetime.strptime(end_date, '%d.%m.%Y')

    # Create a list of all possible time slots between the start and end dates
    all_slots = generate_all_slots(start_datetime, end_datetime, duration)

    # Remove the time slots that fall outside the user's working hours or on non-working days
    all_slots = remove_non_working_hours(all_slots, config)

    # Remove the time slots that overlap with busy times on any of the calendars
    all_slots = remove_busy_slots(all_slots, freebusy_info)

    # Remove the time slots that are shorter than the desired meeting duration
    free_slots = filter_slots_by_duration(all_slots, duration)

    return free_slots

def generate_all_slots(start_datetime_str, end_datetime_str, config):
    # Convert the strings to datetime objects
    start_datetime = datetime.strptime(start_datetime_str, "%d.%m.%Y")
    end_datetime = datetime.strptime(end_datetime_str, "%d.%m.%Y")
    
    # Extract working hours from config
    working_hours_start = datetime.strptime(config['working_hours']['start'], '%H:%M').time()
    working_hours_end = datetime.strptime(config['working_hours']['end'], '%H:%M').time()

    # Initialize the start of the first slot
    slot_start = start_datetime.replace(hour=working_hours_start.hour, minute=working_hours_start.minute)

    all_slots = []

    while slot_start < end_datetime:
        slot_end = slot_start + timedelta(minutes=30)

        # If the slot ends after the working hours, move to the next day
        if slot_end.time() > working_hours_end or slot_end.date() > slot_start.date():
            slot_start = slot_start.replace(hour=working_hours_start.hour, minute=working_hours_start.minute) + timedelta(days=1)
            continue

        # If the slot is not on a working day, move to the next day
        if slot_start.weekday() not in config['working_days']:
            slot_start = slot_start.replace(hour=working_hours_start.hour, minute=working_hours_start.minute) + timedelta(days=1)
            continue

        all_slots.append((slot_start, slot_end))
        slot_start = slot_end

    return all_slots


def remove_non_working_hours(all_slots, config):
    working_slots = []

    for slot in all_slots:
        start_time, end_time = slot
        # Check if the slot falls on a working day
        if start_time.weekday() not in config['working_days']:
            continue

        # Convert the working hours to time objects
        working_hours_start = datetime.strptime(config['working_hours']['start'], '%H:%M').time()
        working_hours_

def remove_busy_slots(all_slots, busy_times, duration):
    free_slots = []
    for slot in all_slots:
        slot_start, slot_end = slot
        slot_duration = slot_end - slot_start
        if slot_duration >= timedelta(minutes=duration):
            is_free = True
            for email, email_busy_info in busy_times.items():
                email_busy_times = email_busy_info['busy']
                for busy_time in email_busy_times:
                    busy_start = busy_time['start']
                    busy_end = busy_time['end']
                    # If the slot overlaps with a busy time or its duration is less than the meeting duration, it's not free
                    if slot_start < busy_end and slot_end > busy_start or (slot_end - slot_start) < timedelta(minutes=duration):
                        is_free = False
                        break
                if not is_free:
                    break
            if is_free:
                free_slots.append(slot)
    return free_slots
