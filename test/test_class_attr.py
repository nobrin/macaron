#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for class attributes.
"""
import unittest
import macaron

DB_FILE = ":memory:"

SQL_TEAM = """CREATE TABLE team (
    id          INTEGER PRIMARY KEY NOT NULL,
    name        TEXT NOT NULL,
    created     TIMESTAMP NOT NULL,
    start_date  DATE NOT NULL
)"""

SQL_MEMBER = """CREATE TABLE member (
    id          INTEGER PRIMARY KEY NOT NULL,
    team_id     INTEGER REFERENCES team (id) ON DELETE SET NULL,
    first_name  VARCHAR(20),
    last_name   VARCHAR(20),
    part        VARCHAR(10),
    age         INT DEFAULT 16 NOT NULL CHECK (15 <= age and age <= 18),
    created     TIMESTAMP,
    joined      DATE,
    modified    TIMESTAMP
)"""

class Team(macaron.Model):
    created = macaron.TimestampAtCreate()
    start_date = macaron.DateAtCreate()
    def __str__(self): return "<Team '%s'>" % self.name

class Member(macaron.Model):
    team = macaron.ManyToOne(Team, related_name="members")
    age = macaron.IntegerField(max=18, min=15)
    created = macaron.TimestampAtCreate()
    joined = macaron.DateAtCreate()
    modified = macaron.TimestampAtSave()

class TestMacaron(unittest.TestCase):
    names = [
        ("Ritsu", "Tainaka", "Dr", 17, "Ritsu Tainaka : Dr"),
        ("Mio", "Akiyama", "Ba", 17, "Mio Akiyama : Ba"),
        ("Yui", "Hirasawa", "Gt", 17, "Yui Hirasawa : Gt"),
        ("Tsumugi", "Kotobuki", "Kb", 17, "Tsumugi Kotobuki : Kb"),
    ]

    def setUp(self):
        macaron.macaronage(DB_FILE)
        macaron.execute(SQL_TEAM)
        macaron.execute(SQL_MEMBER)

    def tearDown(self):
        macaron.bake()

    def testClassProperties(self):
        # initializes Team class
        prop = Team.__dict__["_meta"]
        self.assertEqual(type(prop), macaron.TableMetaClassProperty)
        self.assertEqual(prop.table_meta, None)
        self.assertEqual(prop.table_name, "team")
        team = Team.create(name="Houkago Tea Time")
        self.assertEqual(type(prop.table_meta), macaron.TableMetaInfo)
        self.assertEqual(prop.table_name, "team")

        # tests attributes of class properties
        prop = Team.__dict__["id"]
        self.assertEqual(type(prop), macaron.IntegerField)
        self.assertEqual(prop.null, True)
        self.assertEqual(prop.default, None)
        self.assertEqual(prop.is_primary_key, True)

        prop = Team.__dict__["created"]
        self.assert_(type(prop) is macaron.TimestampAtCreate)
        self.assertEqual(prop.null, True, "AtCreate accepted None value.")
        self.assertEqual(prop.default, None)
        self.assertEqual(prop.is_primary_key, False)

        prop = Team.__dict__["start_date"]
        self.assert_(type(prop) is macaron.DateAtCreate)
        self.assertEqual(prop.null, True, "AtCreate accepted None value.")
        self.assertEqual(prop.default, None)
        self.assertEqual(prop.is_primary_key, False)

        # tests ManyToOne relationship
        # _ManyToOne_Rev is a class which should not be initialized by user.
        # It is initialized by ManyToOne object.
        prop = Team.__dict__["members"]
        self.assertEqual(type(prop), macaron._ManyToOne_Rev)
        self.assertEqual(prop.ref, Team)
        self.assertEqual(prop.ref_key, None, "This is None for setting at delay (in _ManyToOne_Rev#__get__).")
        self.assertEqual(prop.rev, Member)
        self.assertEqual(prop.rev_fkey, None, "This is None for setting at delay (in _ManyToOne_Rev#__get__).")

        members = team.members  # this triggers setting for ref_key and rev_fkey
        self.assertEqual(type(members), macaron.ManyToOneRevSet)
        self.assert_(members.parent is team)
        self.assertEqual(members.parent_key, "id", "parent_key == prop.ref_key")
        self.assertEqual(members.cls_fkey, "team_id", "cls_fkey == prop.rev_fkey")
        self.assertEqual(prop.ref_key, "id")
        self.assertEqual(prop.rev_fkey, "team_id")

        # tests Member
        member = team.members.append(first_name="Azusa", last_name="Nakano", part="Gt2", age=16)
        self.assertEqual(member.team_id, team.pk)
        for k in ["first_name", "last_name"]:
            prop = Member.__dict__[k]
            self.assertEqual(type(prop), macaron.CharField)
            self.assertEqual(prop.max_length, 20)
            self.assertEqual(prop.min_length, None)
            self.assertEqual(prop.null, True)
            self.assertEqual(prop.default, None)
            self.assertEqual(prop.is_primary_key, False)

        prop = Member.__dict__["age"]
        self.assertEqual(type(prop), macaron.IntegerField)
        self.assertEqual(prop.max, 18)
        self.assertEqual(prop.min, 15)
        self.assertEqual(prop.null, False)
        self.assertEqual(prop.default, 16)
        self.assertEqual(prop.is_primary_key, False)

        prop = Member.__dict__["created"]
        self.assertEqual(type(prop), macaron.TimestampAtCreate)
        self.assertEqual(prop.null, True, "AtCreate accepts None value.")
        self.assertEqual(prop.default, None)
        self.assertEqual(prop.is_primary_key, False)

        prop = Member.__dict__["joined"]
        self.assert_(type(prop) is macaron.DateAtCreate)
        self.assertEqual(prop.null, True, "AtCreate accepts None value.")
        self.assertEqual(prop.default, None)
        self.assertEqual(prop.is_primary_key, False)

        prop = Member.__dict__["modified"]
        self.assertEqual(type(prop), macaron.TimestampAtSave)
        self.assertEqual(prop.null, True, "AtSave accepts None value.")
        self.assertEqual(prop.default, None)
        self.assertEqual(prop.is_primary_key, False)

if __name__ == "__main__":
    import os
    if os.path.isfile(DB_FILE): os.unlink(DB_FILE)
    unittest.main()
    macaron.cleanup()
