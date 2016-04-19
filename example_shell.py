import code
from datetime import datetime, timedelta

from db_core import VerboseDatabase
from summary_scheduler import SummaryScheduler
from db_functions import create_product, modify_product, delete_product, buy, create_summary

current_time = datetime(year=1970, month=1, day=1).timestamp()

db = VerboseDatabase(timefunc=lambda: current_time)
scheduler = SummaryScheduler(db, first_summary_time=current_time + timedelta(days=1))


def next_day():
    """
    Use to test the scheduler.
    """
    global current_time
    current_time += timedelta(days=1).total_seconds()
    scheduler.wake_up()

code.interact(local=locals())

scheduler.stop()
db.stop()
