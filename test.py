import fastf1
fastf1.Cache.enable_cache('cache')

schedule = fastf1.get_event_schedule(2023)
print(schedule[["RoundNumber", "EventName", "EventDate"]])