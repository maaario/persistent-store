from datetime import datetime, date, time
from time import sleep
from threading import Thread

from pyrsistent import freeze

from db_core import Product, Transaction, Summary


def create_product(db, id, name, price):
    """Creates the record describing a new product."""
    def fn():
        data = db.snapshot()
        if id not in data.products:
            data = data.transform(("products", id), Product(name=name, price=price))
        return data

    db.query(fn)


def modify_product(db, id, new_name=None, new_price=None):
    """Modifies existing product, name and/or price may change."""
    def fn():
        data = db.snapshot()
        if id in data.products:
            product = data.products[id]
            if new_name:
                product = product.set("name", new_name)
            if new_price:
                product = product.set("price", new_price)
            data = data.transform(("products", id), product)
        return data

    db.query(fn)


def delete_product(db, id):
    """Deletes existing product."""
    def fn():
        data = db.snapshot()
        if id in data.products:
            products = data.products.remove(id)
            data = data.set("products", products)
        return data

    db.query(fn)


def buy(db, ids):
    """
    Creates the record describing the transaction in which customer buys products with given ids.
    Captures the actual price and name of the product, no matter how these change later.
    """

    def fn():
        data = db.snapshot()
        products = []
        for id in ids:
            if id in data.products:
                products.append(data.products[id])
        trans = Transaction(timestamp=datetime.now(), products=freeze(products))
        transactions = data.transactions.append(trans)
        return data.set("transactions", transactions)

    db.query(fn)


def create_summary(db):
    """
    Sums up, how much money the customers spent in the given day.
    This is computed asynchronously, (in the separate thread) and then atomically written into the DB.
    To simulate that summary takes a long time, function sleeps 0.1s after processing each buy record.
    """
    data = db.snapshot()
    start_time = datetime.now()

    def separate_thread():
        today_min = datetime.combine(date.today(), time.min)
        today_max = datetime.combine(date.today(), time.max)
        transactions = filter(lambda t: today_min <= t.timestamp <= today_max, data.transactions)

        money_spent = 0
        for t in transactions:
            money_spent += sum(map(lambda p: p.price, t.products))
            sleep(0.1)

        summary = Summary(timestamp=start_time, money_spent=money_spent)

        def fn():
            summaries = db.snapshot().summaries.append(summary)
            return db.snapshot().set("summaries", summaries)

        db.query(fn)

    Thread(target=separate_thread).start()
