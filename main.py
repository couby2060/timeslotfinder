from slot_calculation import calculate_free_slots
from ui import gather_info
from config import load_config


def group_consecutive_slots(slots):
    if not slots:
        return []

    slots.sort(key=lambda slot: slot[0])

    grouped_slots = [list(slots[0])]
    for current_slot in slots[1:]:
        last_grouped_slot = grouped_slots[-1]
        if current_slot[0] <= last_grouped_slot[1]:
            last_grouped_slot[1] = max(last_grouped_slot[1], current_slot[1])
        else:
            grouped_slots.append(list(current_slot))

    grouped_slots = [tuple(slot) for slot in grouped_slots]
    return grouped_slots

def main():
    print("Welcome to the Easy Appointment Finder app! This application helps you find common free slots in Google Calendars for easier scheduling.")

    try:
        emails, start_date, end_date, duration = gather_info()
        config = load_config()  # Load the config data
        free_slots = calculate_free_slots(emails, start_date, end_date, duration, config)  # Pass config to the function
        grouped_slots = group_consecutive_slots(free_slots)

        if not free_slots:
            print("No free slots available in the given time range.")
        else:
            print("Free slots available:")
            for slot in grouped_slots:
                start_str = slot[0].strftime('%d.%m %H:%M')
                end_str = slot[1].strftime('%H:%M')
                print(f'{start_str} – {end_str}')
    except KeyboardInterrupt:
        print("\nYou have exited the program.")
        return

    print("\nThank you for using the Easy Appointment Finder App!")

if __name__ == "__main__":
    main()
