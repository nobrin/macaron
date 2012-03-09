#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Testing for CREATE TABLE clauses.
"""
import unittest
import macaron

DB_FILE = ":memory:"

class Team(macaron.Model):
    name = macaron.CharField(max_length=20)

class Member(macaron.Model):
    team = macaron.ManyToOne(Team, null=True, related_name="members", on_delete="SET NULL", on_update="CASCADE")
    first_name = macaron.CharField(max_length=20, default="unknown")
    last_name = macaron.CharField(max_length=20, default="noname")
    part = macaron.CharField(max_length=10)
    age = macaron.IntegerField(max=18, min=15, default=16)

class TestMacaron(unittest.TestCase):
    def setUp(self):
        macaron.macaronage(DB_FILE, lazy=True, history=10)

    def tearDown(self):
        macaron.bake()

    def testCreateTables(self):
        sql1 = "CREATE TABLE team (\n  id INTEGER PRIMARY KEY NOT NULL,\n  name VARCHAR(20) NOT NULL\n)"
        sql2 = \
"""CREATE TABLE member (
  id INTEGER PRIMARY KEY NOT NULL,
  team_id INTEGER REFERENCES team(id) ON DELETE SET NULL ON UPDATE CASCADE,
  first_name VARCHAR(20) NOT NULL DEFAULT 'unknown',
  last_name VARCHAR(20) NOT NULL DEFAULT 'noname',
  part VARCHAR(10) NOT NULL,
  age INTEGER NOT NULL DEFAULT '16'
)"""
        macaron.create_table(Team)
        self.assertEqual(macaron.history.lastsql, sql1)
        self.assert_(len(macaron.history.lastparams) == 0)
        macaron.create_table(Member)
        self.assertEqual(macaron.history.lastsql, sql2)
        self.assert_(len(macaron.history.lastparams) == 0)

        team = Team.create(name="Houkago Tea Time")

        # test for default values
        member = team.members.append(part="Vo")
        self.assertEqual(member.first_name, "unknown")
        self.assertEqual(member.last_name, "noname")
        self.assertEqual(member.part, "Vo")
        self.assertEqual(member.age, 16)

        # test for ON DELETE SET NULL
        team.delete()
        member = member.get(member.pk)
        self.assertEqual(member.team_id, None)
        self.assertEqual(member.team, None)

        team = Team.create(name="Houkago Tea Time")
        member.team_id = team.pk
        member.save()
        self.assertEqual(member.team_id, team.pk)

if __name__ == "__main__":
    import os
    if os.path.isfile(DB_FILE): os.unlink(DB_FILE)
    unittest.main()
    macaron.cleanup()
