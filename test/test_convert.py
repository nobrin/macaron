#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test converter
"""
import sys, os
sys.path.insert(0, "../")
import unittest, time
try: import simplejson as json
except ImportError: import json
import macaron

DB_FILE = ":memory:"

sql_t_myrecord = """CREATE TABLE IF NOT EXISTS myrecord (
    id          INTEGER PRIMARY KEY,
    name        TEXT,
    value       TEXT,
    created     TIMESTAMP,
    modified    TIMESTAMP
)"""

class StoreJSON(macaron.Field):
    def to_database(self, obj, value): return json.dumps(value)
    def to_object(self, row, value): return json.loads(value)

class MyRecord(macaron.Model):
    value = StoreJSON()
    created = macaron.TimestampAtCreate()
    modified = macaron.TimestampAtSave()
    def __str__(self): return "<MyRecord '%s' is '%s'>" % (self.name, str(self.value))

class TestConverter(unittest.TestCase):
    def setUp(self):
        macaron.macaronage(dbfile=DB_FILE, lazy=True)
        macaron.execute(sql_t_myrecord)

    def tearDown(self):
        macaron.bake()
        macaron.cleanup()

    def testCRUD(self):
        newrec = MyRecord.create(name="My test", value={"Macaron":"Good!"})
        self.assert_(newrec.created)
        self.assert_(newrec.modified)
        created = newrec.created
        modified = newrec.modified
        time.sleep(2)   # wait for changing time
        rec = MyRecord.get(1)
        self.assertEqual(rec.value["Macaron"], "Good!")
        rec.value = {"Macaron":"Excellent!!"}
        rec.save()
        self.assertEqual(rec.created, created, "When saving, created time is not changed")
        self.assertNotEqual(rec.modified, modified, "When saving, modified time is updated")

if __name__ == "__main__":
    if os.path.isfile(DB_FILE): os.unlink(DB_FILE)
    unittest.main()
