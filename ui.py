from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from datetime import datetime
from dateutil.relativedelta import relativedelta, SU

def load_emails():
    # Read the email addresses from the file
    with open('emails.txt', 'r') as f:
        emails = f.read().splitlines()

    return emails

def get_emails():
    # Load the email addresses for autocompletion
    email_completer = WordCompleter(load_emails())

    emails = []

    while True:
        # Get the input from the user
        email_input = prompt('Please enter an email address (or \'n\' to finish): ', completer=email_completer)
        
        # Check if the user wants to finish entering emails
        if email_input.lower() == 'n':
            break

        emails.append(email_input)

    return emails

def get_dates():
    # Get the current date
    now = datetime.now()
    current_year = now.year

    # Get the start date from the user
    start_date = prompt('Please enter the start date (DD.MM or \'t\' for today): ')
    if start_date.lower() == 't':
        start_date = now
    else:
        try:
            start_date = datetime.strptime(f'{start_date}.{current_year}', '%d.%m.%Y')
        except ValueError:
            print('The start date is not in the correct format. Please enter a date in the format DD.MM.')
            return

    # Get the end date from the user
    end_date = prompt('Please enter the end date (DD.MM or \'e\' for end of this week): ')
    if end_date.lower() == 'e':
        end_of_week = now + relativedelta(weekday=SU)  # SU indicates Sunday
        end_date = end_of_week
    else:
        try:
            end_date = datetime.strptime(f'{end_date}.{current_year}', '%d.%m.%Y')
        except ValueError:
            print('The end date is not in the correct format. Please enter a date in the format DD.MM.')
            return

    # Check if the start date is before the end date
    if start_date > end_date:
        print('The start date must be before the end date.')
        return

    # Convert the datetime objects to strings in the format 'dd.mm.yyyy'
    start_date_str = start_date.strftime('%d.%m.%Y')
    end_date_str = end_date.strftime('%d.%m.%Y')

    return start_date_str, end_date_str

def get_duration():
    # Get the duration from the user
    duration = prompt('Please enter the duration of the meeting (in minutes): ')

    return int(duration)

def gather_info():
    emails = get_emails()
    start_date, end_date = get_dates()
    duration = get_duration()

    return emails, start_date, end_date, duration
