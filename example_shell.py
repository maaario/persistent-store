import code

from db_core import VerboseDatabase
from summary_scheduler import SummaryScheduler
from db_functions import *

current_time = 0

db = VerboseDatabase(timefunc=lambda: current_time)
scheduler = SummaryScheduler(db)

def next_day():
    global current_time
    current_time += timedelta(days=1).total_seconds()
    scheduler.wake_up()

code.interact(local=locals())

scheduler.stop()
db.stop()
