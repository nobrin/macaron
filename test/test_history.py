#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for HistoryLogger.
"""
import sys, os
sys.path.insert(0, "../")
import unittest
import macaron
import sqlite3
import logging

DB_FILE = ":memory:"

sql_t_test = """CREATE TABLE IF NOT EXISTS t_test (
    id          INTEGER PRIMARY KEY,
    name        TEXT,
    value       TEXT
)"""

class TestHistoryLogger(unittest.TestCase):
    def setUp(self): pass
    def tearDown(self): pass

    def testLogger(self):
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        sql_logger = macaron.ListHandler(10)
        logger.addHandler(sql_logger)

        conn = sqlite3.connect(DB_FILE, factory=macaron._create_wrapper(logger))
        conn.execute(sql_t_test)
        self.assertEqual(sql_logger[0], "%s\nparams: []" % sql_t_test)
        conn.close()

    def testMacaronOption_disabled(self):
        macaron.macaronage(DB_FILE)
        chk = False
        try: macaron.history[0]
        except RuntimeError: chk = True
        self.assert_(chk, "'SQL history is disabled' error has not raised")
        macaron.cleanup()

    def testMacaronOption_index(self):
        macaron.macaronage(DB_FILE, history=10)
        chk = False
        try: macaron.history[0]
        except IndexError: chk = True
        self.assert_(chk, "Index Error is not raised.")
        macaron.cleanup()

if __name__ == "__main__":
    unittest.main()
