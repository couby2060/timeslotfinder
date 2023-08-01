from datetime import datetime, time, timedelta
from calendar_api import create_service, get_freebusy_info
from config import load_config

def calculate_free_slots(emails, start_date, end_date, duration, credentials):
    print("In calculate_free_slots...")
    service = create_service(credentials)
    freebusy_info = get_freebusy_info(service, emails, start_date, end_date)
    
    print(f"Freebusy info: {freebusy_info}")

    config = load_config()
    weekdays = [datetime.strptime(day, "%A").weekday() for day in config["working_days"]]
    working_hours = config["working_hours"]

    free_slots = []
    current_date = start_date

    while current_date <= end_date:
        if current_date.weekday() in weekdays:
            working_start_time = datetime.combine(current_date, datetime.strptime(working_hours["start"], "%H:%M").time())
            working_end_time = datetime.combine(current_date, datetime.strptime(working_hours["end"], "%H:%M").time())
            busy_slots = []

            for email in emails:
                busy_slots += freebusy_info[email]['busy']

            busy_slots.sort(key=lambda x: x['start'])
            current_time = working_start_time

            for busy_slot in busy_slots:
                busy_start = datetime.fromisoformat(busy_slot['start'])
                busy_end = datetime.fromisoformat(busy_slot['end'])

                if busy_start > current_time:
                    free_slot_duration = busy_start - current_time
                    if free_slot_duration.total_seconds() >= duration * 60:
                        free_slots.append((current_time, busy_start))

                current_time = max(current_time, busy_end)

            if current_time < working_end_time:
                free_slots.append((current_time, working_end_time))

        current_date += timedelta(days=1)

    print(f"Free slots: {free_slots}")
    return free_slots
