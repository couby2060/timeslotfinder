from auth import get_credentials
from datetime import datetime, timedelta
from slot_calculation import calculate_free_slots

print("Getting credentials...")
credentials = get_credentials()
print(f"Credentials obtained: {credentials is not None}")

# Define the input parameters
emails = ["johannes.wilhelm@twt.de"]
start_date = datetime.now()
end_date = start_date + timedelta(days=3)
duration = 60  # Minimum duration in minutes

print("Starting calculation...")
print(f"Emails: {emails}")
print(f"Start date: {start_date}")
print(f"End date: {end_date}")
print(f"Duration: {duration}")

# Call the calculate_free_slots function
free_slots = calculate_free_slots(emails, start_date, end_date, duration, credentials)

# Print the result
if free_slots:
    for slot in free_slots:
        print(f"Free Slot from {slot[0]} to {slot[1]}")
else:
    print("No free slots found.")
