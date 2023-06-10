from datetime import date, datetime, timedelta, timezone

today = datetime.now(timezone.utc) #date.today() #datetime(2023, 2, 1)
print(today)
friday = today + timedelta( (3-today.weekday()) % 7+1 )
print(f"The date is : {friday.strftime(f'{friday.day}%b%y').upper()}")
print(f"The weekday : {today.weekday() == 4}")
print(friday.timestamp())