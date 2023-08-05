#test comment
from datetime import datetime, timedelta

def calculate_free_slots(emails, start_date, end_date, duration, config):
    busy_times = {}
    for email in emails:
        busy_info = get_busy_info(email, start_date, end_date)
        busy_times[email] = busy_info['busy']

    all_slots = generate_all_slots(start_date, end_date, duration, busy_times, config)
    free_slots = remove_busy_slots(all_slots, busy_times)

    return free_slots

def generate_all_slots(start_date, end_date, duration, busy_times, config):
    all_slots = []
    time_interval = timedelta(minutes=duration)
    working_days = config['working_days']
    current_time = start_date
    end_time = end_date

    # Get the timezone from the busy times
    first_busy_time = next((value for value in busy_times.values() if value), [])
    tzinfo = first_busy_time[0]['start'].tzinfo if first_busy_time else None

    while current_time < end_time:
        if current_time.weekday() in working_days:
            working_hours_start = current_time.replace(hour=config['working_hours_start'], minute=0, second=0, microsecond=0, tzinfo=tzinfo)
            working_hours_end = current_time.replace(hour=config['working_hours_end'], minute=0, second=0, microsecond=0, tzinfo=tzinfo)
            if working_hours_start <= current_time < working_hours_end:
                all_slots.append(current_time)
        current_time += time_interval

    return all_slots

def remove_busy_slots(all_slots, busy_times):
    free_slots = []
    busy_intervals = [item for sublist in busy_times.values() for item in sublist]

    for slot in all_slots:
        for busy_interval in busy_intervals:
            if slot >= busy_interval['start'] and slot < busy_interval['end']:
                break
        else:
            free_slots.append(slot)

    return free_slots

def get_busy_info(email, start_date, end_date):
    # Mocked function: Replace with actual logic to fetch busy info from the calendar
    return {'busy': []}
