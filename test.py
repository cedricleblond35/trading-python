import datetime

j = datetime.datetime.today().weekday()
print(j)
h = datetime.datetime.utcnow()
print(h)
today = datetime.datetime.now()
todayPlus2Hours = today + datetime.timedelta(hours=2)

print(todayPlus2Hours)

print(todayPlus2Hours.hour)
print(todayPlus2Hours.minute)
print(todayPlus2Hours.second)
