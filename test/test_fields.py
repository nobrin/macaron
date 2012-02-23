#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import time
import macaron

DB_FILE = ":memory:"

SQL_TEAM = """CREATE TABLE team (
    id          INTEGER PRIMARY KEY,
    name        VARCHAR(40) NOT NULL,
    created     TIMESTAMP NOT NULL
)"""

SQL_MEMBER = """CREATE TABLE member (
    id          INTEGER PRIMARY KEY,
    team_id     INTEGER REFERENCES team (id) NOT DEFERRABLE INITIALLY IMMEDIATE,
    first_name  TEXT,
    last_name   TEXT,
    age         INT DEFAULT 16,
    part        VARCHAR(10) NOT NULL,
    joined      TIMESTAMP,
    modified    TIMESTAMP
)"""

class Team(macaron.Model):
    created = macaron.TimestampAtCreate()
    def __str__(self): return "<Team '%s'>" % self.name

class Member(macaron.Model):
    team = macaron.ManyToOne(Team, "members")
    joined = macaron.TimestampAtCreate()
    modified = macaron.TimestampAtSave()
    age = macaron.IntegerField(max=18, min=15)

class TestMacaron(unittest.TestCase):
    def setUp(self):
        macaron.macaronage(dbfile=DB_FILE, lazy=True)
        macaron.execute(SQL_TEAM)
        macaron.execute(SQL_MEMBER)

    def tearDown(self):
        macaron.bake()

    def testProperties(self):
        chks = (
            {"name":"id", "default":None, "null":True},
            {"name":"name", "default":None, "null":False, "max_length":40},
            {"name":"created", "default":None, "null":False},
        )
        clss = (macaron.IntegerField, macaron.CharField, macaron.TimestampAtCreate)
        for idx in range(0, len(Team._meta.fields)):
            fld = Team._meta.fields[idx]
            for n in chks[idx].keys():
                self.assertEqual(getattr(fld, n), chks[idx][n])
            self.assert_(fld.__class__ is clss[idx], \
                "Field '%s' is %s not %s" % (fld.name, fld.__class__.__name__, clss[idx].__name__))
        team1 = Team.create(name="Houkago Tea Time")
        team2 = Team.get(1)
        for n in ("id", "name", "created"):
            self.assertEqual(getattr(team1, n), getattr(team2, n))

        def _part_is_not_set():
            team1.members.append(first_name="Azusa", last_name="Nakano")
        self.assertRaises(macaron.ValidationError, _part_is_not_set)

        member1 = team1.members.append(first_name="Azusa", last_name="Nakano", part="Gt")
        member2 = Member.get(1)
        for n in("id", "team_id", "first_name", "last_name", "age", "joined", "modified"):
            self.assertEqual(getattr(member1, n), getattr(member2, n))
        self.assertEqual(member1.id, 1)
        self.assertEqual(member1.team_id, 1)
        self.assertEqual(member1.first_name, "Azusa")
        self.assertEqual(member1.last_name, "Nakano")
        self.assertEqual(member1.age, 16)
        self.assert_(member1.joined)
        self.assert_(member1.modified)

        member1.age += 1
        time.sleep(2)
        member1.save()

        self.assertNotEqual(member1.modified, member2.modified)

        def _age_exceeded(): member1.age = 19
        def _age_underrun(): member1.age = 14
        self.assertRaises(macaron.ValidationError, _age_exceeded)
        self.assertRaises(macaron.ValidationError, _age_underrun)

        def _too_long_part_name(): member1.part = "1234567890A"
        self.assertRaises(macaron.ValidationError, _too_long_part_name)

if __name__ == "__main__":
#    if os.path.isfile(DB_FILE): os.unlink(DB_FILE)
    unittest.main()
    macaron.db_close()

