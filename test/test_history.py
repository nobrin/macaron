#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for HistoryLogger.
"""
import unittest
import macaron
import sqlite3
import logging

DB_FILE = ":memory:"
SQL_TEST = """CREATE TABLE IF NOT EXISTS t_test (
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
        conn.execute(SQL_TEST)
        self.assertEqual(sql_logger[0], "%s\nparams: []" % SQL_TEST)
        conn.close()

    def testLogger_content(self):
        macaron.macaronage(DB_FILE, history=10)
        macaron.execute(SQL_TEST)
        self.assertEqual(macaron.history[0], "%s\nparams: []" % SQL_TEST)
        macaron.cleanup()

    def testMacaronOption_disabled(self):
        macaron.macaronage(DB_FILE)
        def _history_is_disabled(): macaron.history[0]
        self.assertRaises(RuntimeError, _history_is_disabled)
        macaron.cleanup()

    def testMacaronOption_index(self):
        macaron.macaronage(DB_FILE, history=10)
        def _index_error(): macaron.history[1]
        self.assertRaises(IndexError, _index_error)
        macaron.cleanup()

if __name__ == "__main__":
    unittest.main()
