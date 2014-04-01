#!flask/bin/python
from haggle import db
import os.path
print "creating databases"
db.create_all()
print "DB creation completed.."
