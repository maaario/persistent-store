from datetime import timedelta
from threading import Condition, Event, Thread

from db_functions import create_summary


class SummaryScheduler:
    """
    Run create_summary function every day at summary_time.
    Scheduler waits passively until the next planned event comes or until `wake_up` is called.
    """
    def __init__(self, db, first_summary_time, interval=timedelta(days=1).total_seconds()):
        self.db = db
        self.interval = interval
        self.next_summary_time = first_summary_time

        self.__waiting = Condition()
        self.__stop = Event()

        Thread(target=self.run).start()

    def run(self):
        with self.__waiting:
            while not self.__stop.is_set():
                if self.db.time() >= self.next_summary_time:
                    self.next_summary_time += self.interval
                    create_summary(self.db)
                self.__waiting.wait(self.next_summary_time - self.db.time())

    def stop(self):
        with self.__waiting:
            self.__stop.set()
            self.__waiting.notify()

    def wake_up(self):
        """
        Used at testing when db.time() changes unpredictably.
        """
        with self.__waiting:
            self.__waiting.notify()
