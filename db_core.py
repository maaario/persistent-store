import logging
from threading import Thread, Condition, Event
from queue import Queue
import time

from pyrsistent import PRecord, field, PVector, m, v

logger = logging.getLogger("queue")


class Product(PRecord):
    name = field(type=str)
    price = field()


class Transaction(PRecord):
    timestamp = field()
    products = field(type=PVector)


class Summary(PRecord):
    timestamp = field()
    money_spent = field()


class Database:
    def __init__(self, timefunc=time.time):
        self.__data = m(products=m(), transactions=v(), summaries=v())

        self.__event_queue = Queue()    # sequential query execution
        self.__lock = Condition()       # passive waiting only
        self.__stop = Event()

        self.time = timefunc

        Thread(target=self.__run).start()

    def snapshot(self):
        """
        Returns copy of persistent database.
        """
        return self.__data

    def query(self, fn):
        """
        Pushes database query function to event_queue.
        fn should take no arguments, should quickly alter the database and return its new state.
        Queries will be executed in strict sequential order.
        """
        with self.__lock:
            self.__event_queue.put(fn)
            self.__lock.notify()

    def __process_query(self):
        fn = self.__event_queue.get()
        logger.info("removing from queue and processing function {}".format(fn))
        self.__data = fn()

        data = self.snapshot()
        logger.debug("DB products    : {}".format(data.products))
        logger.debug("DB transactions: {}".format(data.transactions))
        logger.debug("DB summaries   : {}".format(data.summaries))

    def __run(self):
        """
        Execute queries from queue. If there is no query, the thread waits.
        """
        while not self.__stop.is_set():
            with self.__lock:
                while not self.__event_queue.empty():
                    self.__process_query()
                self.__lock.wait()

    def stop(self):
        """
        Stops the query-processing thread.
        """
        with self.__lock:
            self.__stop.set()
            self.__lock.notify()


class FunctionsTestingDatabase:
    """
    Database without queue, where all queries are executed right away.
    """
    def __init__(self, timefunc=time.time):
        self.__data = m(products=m(), transactions=v(), summaries=v())
        self.time = timefunc

    def snapshot(self):
        return self.__data

    def query(self, fn):
        self.__data = fn()

    def stop(self):
        pass
