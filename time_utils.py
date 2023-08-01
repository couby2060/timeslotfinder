from datetime import timezone, timedelta

def convert_to_local_time(dt):
    # Convert to Berlin time
    berlin_tz = timezone(timedelta(hours=2))
    return dt.replace(tzinfo=timezone.utc).astimezone(tz=berlin_tz)
