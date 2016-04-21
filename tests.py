import unittest
import random
import logging
from time import sleep
from datetime import datetime, timedelta

from pyrsistent import m, v, freeze

from db_functions import create_product, modify_product, delete_product, buy, create_summary
from db_core import Database, FunctionsTestingDatabase, Product, Transaction, Summary
from summary_scheduler import SummaryScheduler

logging.disable(logging.CRITICAL)


class TestProductFunctions(unittest.TestCase):
    """
    Test creation, modification, deletion of product on simple database.
    """
    def setUp(self):
        self.db = FunctionsTestingDatabase()

    def test_create_product(self):
        create_product(self.db, 0, "car", 1000)
        self.assertEqual(self.db.snapshot().products[0], Product(name="car", price=1000))

        create_product(self.db, 84, "car", 1000)
        self.assertEqual(self.db.snapshot().products[84], Product(name="car", price=1000))

        create_product(self.db, 1225, "new object", 10)
        self.assertEqual(self.db.snapshot().products[1225], Product(name="new object", price=10))

    def test_create_existing_product(self):
        create_product(self.db, 0, "prod", 100)

        create_product(self.db, 0, "new prod", 452)
        self.assertEqual(self.db.snapshot().products[0], Product(name="prod", price=100))

    def test_modify_product(self):
        create_product(self.db, 1, "car", 1000)
        modify_product(self.db, 1, new_name="auto")
        self.assertEqual(self.db.snapshot().products[1], Product(name="auto", price=1000))

        create_product(self.db, 2, "car", 1000)
        modify_product(self.db, 2, new_price=200)
        self.assertEqual(self.db.snapshot().products[2], Product(name="car", price=200))

        create_product(self.db, 3, "car", 1000)
        modify_product(self.db, 3, new_name="bmw", new_price=10000)
        self.assertEqual(self.db.snapshot().products[3], Product(name="bmw", price=10000))

        create_product(self.db, 4, "car", 1000)
        modify_product(self.db, 4)
        self.assertEqual(self.db.snapshot().products[4], Product(name="car", price=1000))

    def test_modify_nonexistent_product(self):
        create_product(self.db, 4, "car", 1000)
        products = self.db.snapshot().products

        modify_product(self.db, 0, "new name")
        self.assertEqual(self.db.snapshot().products, products)

    def test_delete_product(self):
        create_product(self.db, 0, "car", 1000)
        delete_product(self.db, 0)
        self.assertEqual(self.db.snapshot().products, m())

    def test_delete_nonexistent_product(self):
        create_product(self.db, 0, "car", 1000)
        products = self.db.snapshot().products

        delete_product(self.db, 1)
        self.assertEqual(self.db.snapshot().products, products)


class TestCalculationFunctions(unittest.TestCase):
    def setUp(self):
        self.time = 0
        self.db = FunctionsTestingDatabase(timefunc=lambda: self.time)
        self.products = {}
        for i in range(10):
            self.products[i] = Product(name='item' + str(i), price=i * 100)
            create_product(self.db, i, 'item' + str(i), i * 100)

    def test_buy(self):
        def test_list(t, l):
            buy(self.db, l)
            self.assertEqual(
                self.db.snapshot().transactions[t].products,
                freeze([self.products[i] for i in l if i in self.products])
            )

        test_list(0, [1, 5, 4])
        test_list(1, [1, 1, 1])
        test_list(2, [])
        test_list(3, [1, 13, 2])

    def test_buy_preserves_original_objects(self):
        buy(self.db, [0, 1])

        modify_product(self.db, 0, new_name='new object name')
        self.assertEqual(self.db.snapshot().transactions[0].products[0].name, 'item0')

        modify_product(self.db, 1, new_price=42)
        self.assertEqual(self.db.snapshot().transactions[0].products[1].price, 100)

    def test_create_summary_one_transaction(self):
        buy(self.db, [0, 1, 3])

        self.time += timedelta(days=1).total_seconds()
        create_summary(self.db)

        sleep(0.5)
        self.assertEqual(self.db.snapshot().summaries[0].money_spent, 400)

    def test_create_summary_more_transactions(self):
        buy(self.db, [0, 9, 9])
        buy(self.db, [1, 1, 0, 4])
        buy(self.db, [2])

        self.time += timedelta(days=1).total_seconds()
        create_summary(self.db)

        sleep(1)
        self.assertEqual(self.db.snapshot().summaries[0].money_spent, 2600)


class TestSeparateThreadDatabase(unittest.TestCase):
    def setUp(self):
        self.time = datetime(year=1970, month=1, day=1).timestamp()
        self.db = Database(timefunc=lambda: self.time)
        for i in range(10):
            create_product(self.db, i, 'item' + str(i), i * 100)
        sleep(0.1)

    def test_create_summary_even_if_new_buys_come(self):
        buy(self.db, [0, 7, 8])
        buy(self.db, [1, 4])
        sleep(0.1)

        self.time += timedelta(days=1).total_seconds()
        create_summary(self.db)

        buy(self.db, [2, 4])
        buy(self.db, [1, 3])
        sleep(0.1)

        self.time += timedelta(days=1).total_seconds()
        create_summary(self.db)

        buy(self.db, [9, 8, 7])

        sleep(2)                # summaries calculation
        sums = self.db.snapshot().summaries
        self.assertEqual(sums[0].money_spent, 2000)
        self.assertEqual(sums[1].money_spent, 1000)

    def tearDown(self):
        self.db.stop()


class TestDatabaseAgainstFunctionTestingDatabase(unittest.TestCase):
    def setUp(self):
        self.db1 = Database()
        self.db2 = FunctionsTestingDatabase()

    def compare_databases(self):
        self.assertEqual(self.db1.snapshot().products, self.db2.snapshot().products)

        transactions_products = lambda db: [t.products for t in db.snapshot().transactions]
        self.assertEqual(transactions_products(self.db1), transactions_products(self.db2))

        summaries_moneys = lambda db: [s.money_spent for s in db.snapshot().summaries]
        self.assertEqual(summaries_moneys(self.db1), summaries_moneys(self.db2))

    def test_random_operations_on_both_databases(self):
        products = set()
        randnum = lambda: random.randint(0, 1000000)
        randstr = lambda: ''.join(random.choice("abcdefgh ") for i in range(random.randint(1, 10)))
        randid  = lambda: random.choice(list(products))

        def t_create():
            id, n, p = randnum(), randstr(), randnum()
            create_product(self.db1, id, n, p)
            create_product(self.db2, id, n, p)
            products.add(id)

        def t_modify():
            id, n, p = randid(), randstr(), randnum()
            modify_product(self.db1, id, new_name=n, new_price=p)
            modify_product(self.db2, id, new_name=n, new_price=p)

        def t_delete():
            if len(products) == 1:
                return
            id = randid()
            delete_product(self.db1, id)
            delete_product(self.db2, id)
            products.remove(id)

        def t_buy():
            ids = [randid() for i in range(random.randint(1, 5))]
            buy(self.db1, ids)
            buy(self.db2, ids)

        for i in range(30):
            t_create()
        for i in range(1000):
            random.choice((t_create, t_modify, t_delete, t_buy))()

        sleep(1)
        self.compare_databases()

    def tearDown(self):
        self.db1.stop()


class TestSummaryScheduler(unittest.TestCase):
    def setUp(self):
        self.time = datetime(year=1970, month=1, day=1).timestamp()
        self.db = Database(timefunc=lambda: self.time)
        self.scheduler = None
        for i in range(10):
            create_product(self.db, i, 'item' + str(i), i * 100)

    def change_time(self, days=0, hours=0, minutes=0):
        self.time += timedelta(days=days, hours=hours, minutes=minutes).total_seconds()
        self.scheduler.wake_up()

    def test_one_day(self):
        summary_time = datetime(year=1970, month=1, day=2).timestamp()
        self.scheduler = SummaryScheduler(self.db, first_summary_time=summary_time)

        buy(self.db, [0, 1, 2])
        buy(self.db, [0, 3, 4])
        self.change_time(hours=23, minutes=59)

        sleep(1)
        self.assertEqual(self.db.snapshot().summaries, v())

        self.change_time(minutes=1)
        sleep(1)
        self.assertEqual(self.db.snapshot().summaries[0], Summary(timestamp=summary_time, money_spent=1000))

    def test_more_days(self):
        next_summary_time = datetime(year=1970, month=1, day=2, hour=17, minute=45).timestamp()
        day = timedelta(days=1).total_seconds()
        self.scheduler = SummaryScheduler(self.db, first_summary_time=next_summary_time)

        def simulate_one_day(buy_lists):
            nonlocal next_summary_time

            # buy items
            for items in buy_lists:
                buy(self.db, items)

            # transactions written into database
            sleep(0.1)

            # move to next day and wait for summary creation
            self.change_time(days=1)
            sleep(0.1 * sum(map(len, buy_lists)) + 0.2)

            # assert
            expected_summary = Summary(timestamp=next_summary_time,
                                       money_spent=100 * sum(map(sum, buy_lists)))
            self.assertEqual(self.db.snapshot().summaries[-1], expected_summary)

            # change date of next expected summary
            next_summary_time += day

        self.change_time(hours=17, minutes=45)
        simulate_one_day([[5]])
        simulate_one_day([[5, 1], [8, 6]])
        simulate_one_day([[]])
        simulate_one_day([])
        simulate_one_day([[1, 2], [0, 3]])

    def tearDown(self):
        self.scheduler.stop()
        self.db.stop()

if __name__ == '__main__':
    unittest.main()
