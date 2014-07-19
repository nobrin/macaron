#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test custom field
"""
import unittest, time
try: import simplejson as json
except ImportError: import json
import macaron

DB_FILE = ":memory:"

class StoreJSONField(macaron.CharField):
    def to_database(self, obj, value): return json.dumps(value)
    def to_object(self, row, value): return json.loads(value)

class MyRecord(macaron.Model):
    name        = macaron.CharField(max_length=20)
    value       = StoreJSONField()
    created     = macaron.TimestampAtCreate()
    modified    = macaron.TimestampAtSave()
    def __str__(self): return "<MyRecord '%s' is '%s'>" % (self.name, str(self.value))

class TestCustomField(unittest.TestCase):
    def setUp(self):
        macaron.macaronage(dbfile=DB_FILE, lazy=True)
        macaron.create_table(MyRecord)

    def tearDown(self):
        macaron.bake()
        macaron.cleanup()

    def _compare_schema(self, tbl_name, sql_lines):
        cur = macaron.execute("SELECT sql FROM sqlite_master WHERE name = ?", [tbl_name])
        tbl_lines = cur.fetchone()[0].splitlines()
        self.assertEqual(len(tbl_lines), len(sql_lines))
        cnt = 0
        for line in tbl_lines:
            self.assertEqual(line, sql_lines.pop(0))
            cnt += 1
        self.assertEqual(cnt, len(tbl_lines))
        self.assertEqual(len(sql_lines), 0)

    def testTableDefinition(self):
        sql_lines = [
            'CREATE TABLE "myrecord" (',
            '  "id" INTEGER PRIMARY KEY NOT NULL,',
            '  "name" VARCHAR(20) NOT NULL,',
            '  "value" TEXT NOT NULL,',
            '  "created" TIMESTAMP,',
            '  "modified" TIMESTAMP',
            ')'
        ]
        self._compare_schema("myrecord", sql_lines)

    def testJSONCustomField(self):
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

        rect = MyRecord.get(1)
        self.assertEqual(rec.value["Macaron"], "Excellent!!")

if __name__ == "__main__":
    if os.path.isfile(DB_FILE): os.unlink(DB_FILE)
    unittest.main()
