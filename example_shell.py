import code

from db_core import VerboseDatabase
from db_functions import *

db = VerboseDatabase()

code.interact(local=locals())

db.stop()
