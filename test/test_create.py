#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Testing for CREATE TABLE clauses.
"""
#import sys, os
#test_root = os.path.dirname(os.path.abspath(__file__))
#os.chdir(test_root)
#sys.path.insert(0, os.path.dirname(test_root))

import unittest
import macaron
import sqlite3, sys, re
#macaron.SQL_TRACE_OUT = sys.stderr
DB_FILE = ":memory:"

class Team(macaron.Model):
    name = macaron.CharField(max_length=20)

class Member(macaron.Model):
    _unique_together = ["first_name", "last_name"]
    _ordering = ["-id"]
    team = macaron.ManyToOne(Team, null=True, related_name="members", on_delete="SET NULL", on_update="CASCADE")
    first_name = macaron.CharField(max_length=20, default="unknown")
    last_name = macaron.CharField(max_length=20, default="noname")
    part = macaron.CharField(max_length=10)
    age = macaron.IntegerField(max=18, min=15, default=16)

class TestMacaron(unittest.TestCase):
    def setUp(self):
        macaron.macaronage(DB_FILE, autocommit=True, lazy=True, history=10)

    def tearDown(self):
        macaron.bake()

    def testCreateTables(self):
        sql1 = 'CREATE TABLE "team" (\n  "id" INTEGER PRIMARY KEY NOT NULL,\n  "name" VARCHAR(20) NOT NULL\n)'
        sql2 = \
"""CREATE TABLE "member" (
  "id" INTEGER PRIMARY KEY NOT NULL,
  "team_id" INTEGER REFERENCES "team"("id") ON DELETE SET NULL ON UPDATE CASCADE,
  "first_name" VARCHAR(20) NOT NULL DEFAULT 'unknown',
  "last_name" VARCHAR(20) NOT NULL DEFAULT 'noname',
  "part" VARCHAR(10) NOT NULL,
  "age" INTEGER NOT NULL DEFAULT '16',
  UNIQUE ("first_name", "last_name")
)"""
        macaron.create_table(Team)
        self.assertEqual(macaron.history.lastsql, 'PRAGMA table_info("team")')
        self.assertEqual(macaron.history[1].sql, sql1)
        self.assertEqual(macaron.history[1].param_str, "[]")
        macaron.create_table(Member)
        self.assertEqual(macaron.history.lastsql, 'PRAGMA table_info("member")')
        self.assertEqual(macaron.history[1].sql, sql2)
        self.assertEqual(macaron.history[1].param_str, "[]")

        team = Team.create(name="Houkago Tea Time")

        # test for default values
        member = team.members.append(part="Vo")
        self.assertEqual(member.first_name, "unknown")
        self.assertEqual(member.last_name, "noname")
        self.assertEqual(member.part, "Vo")
        self.assertEqual(member.age, 16)

        # test for ordering
        team.members.append(first_name="Test1", part="Dr")
        team.members.append(first_name="Test2", part="Gt")
        ids = [3, 2, 1]
        for m in team.members: self.assertEqual(m.id, ids.pop(0))
        self.assertEqual(len(ids), 0)

        # test for ON DELETE SET NULL
        # This can work on sqlite3 >= 3.6.19
        team.delete()
        member = member.get(member.pk)
        if sqlite3.sqlite_version_info >= (3, 6, 19):
            self.assertEqual(member.team_id, None)
            self.assertEqual(member.team, None)
        else:
            print "Foreign key constraint works SQLite >= 3.6.19. Skip."

        team = Team.create(name="Houkago Tea Time")
        member.team_id = team.pk
        member.save()
        self.assertEqual(member.team_id, team.pk)

if __name__ == "__main__":
    import os
    if os.path.isfile(DB_FILE): os.unlink(DB_FILE)
    unittest.main()
    macaron.cleanup()
