# persistent-store

Homework for course: Princilples of software development

- In memory database consisting of **persistent data structures** (pyrsistent).
- Database is accessed directly only by one thread, other threads make queries via **thread-safe queue**.
- Focused on practicing **functional design & persistent DS**, **multithreading** (python threading), **testing** (python unittest) and **logging** (python logging)


Supported operations:
``` python
create_product(id, name, price)
modify_product(id, new_name = None, new_price = None)
delete product (id)
buy(ids)
calculate_summary()
```
