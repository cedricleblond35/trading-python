from datetime import datetime, timedelta
import pytz

j = datetime.today().weekday()
print(j)
h = datetime.utcnow()
print(h)
today = datetime.now()
todayPlus2Hours = today + datetime.timedelta(hours=2)

print(todayPlus2Hours)

print(todayPlus2Hours.hour)
print(todayPlus2Hours.minute)
print(todayPlus2Hours.second)


paris_tz = pytz.timezone('Europe/Paris')
naive_summer_time = datetime(2021, 10, 30)
# Localisation de date à partir de datetime
summer_time = naive_summer_time.astimezone(paris_tz)
# Localisation de date à partir de pytz
summer_time = paris_tz.localize(naive_summer_time)