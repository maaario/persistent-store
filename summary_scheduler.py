import logging
from datetime import timedelta
from threading import Condition, Event, Thread

from db_functions import create_summary

logger = logging.getLogger("scheduler")


class SummaryScheduler:
    """
    Run create_summary function every day at summary_time.
    Scheduler waits passively until the next planned event comes or until `wake_up` is called.
    """
    def __init__(self, db, first_summary_time, interval=timedelta(days=1).total_seconds()):
        self.__db = db
        self.__interval = interval
        self.__next_summary_time = first_summary_time

        self.__waiting = Condition()
        self.__stop = Event()

        Thread(target=self.run).start()

    def run(self):
        logger.debug("starting scheduler thread")
        with self.__waiting:
            while not self.__stop.is_set():
                if self.__db.time() >= self.__next_summary_time:
                    self.__next_summary_time += self.__interval
                    logger.info("daily summary will be created")
                    logger.debug("next summary scheduled to {}".format(self.__next_summary_time))
                    create_summary(self.__db)
                self.__waiting.wait(self.__next_summary_time - self.__db.time())
        logger.debug("stopping scheduler thread")

    def stop(self):
        logger.debug("sending signal to stop")
        with self.__waiting:
            self.__stop.set()
            self.__waiting.notify()

    def wake_up(self):
        """
        Used at testing when db.time() changes unpredictably to interrupt scheduled waiting.
        """
        logger.debug("sending signal to wake up")
        with self.__waiting:
            self.__waiting.notify()
