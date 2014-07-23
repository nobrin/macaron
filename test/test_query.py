#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Project: Macaron O/R Mapper
# Module:  Tests
"""
Testing for basic usage.
"""
import unittest, warnings
import macaron
from models import Team, Member, Song

DB_FILE = ":memory:"

class TestQueryOperation(unittest.TestCase):
    names = [
        ("Ritsu"  , "Tainaka" , "Dr" , 17),
        ("Mio"    , "Akiyama" , "Ba" , 17),
        ("Yui"    , "Hirasawa", "Gt1", 17),
        ("Tsumugi", "Kotobuki", "Kb" , 17),
        ("Azusa"  , "Nakano"  , "Gt2", 16),
    ]

    def setUp(self):
        macaron.macaronage(DB_FILE, lazy=True)
        macaron.create_table(Team)
        macaron.create_table(Member)
        macaron.create_table(Song)
        macaron.create_link_tables(Song)

    def tearDown(self):
        macaron.SQL_TRACE_OUT = None
        macaron.bake()
        macaron.cleanup()

    def testBorderValues(self):
        azusa = Member.create(first_name="Azusa", last_name="Nakano", part="Gt2", age=16)
        self.assert_(azusa)

        def _age_exceeded(): azusa.age = 19
        def _age_underrun(): azusa.age = 14
        self.assertRaises(macaron.ValidationError, _age_exceeded)
        self.assertRaises(macaron.ValidationError, _age_underrun)

        def _too_long_part_name(): azusa.part = "1234567890A"
        self.assertRaises(macaron.ValidationError, _too_long_part_name)

        def _name_is_not_set(): Member.create(first_name="Azusa")
        self.assertRaises(macaron.ValidationError, _name_is_not_set)

    def testManyToManyOperation(self):
        team = Team.create(name="Houkago Tea Time")
        for name in self.names:
            team.members.append(first_name=name[0], last_name=name[1], part=name[2], age=name[3])
        song1 = Song.create(name="Utauyo!! MIRACLE")
        song2 = Song.create(name="Tenshi ni Fureta yo!")

        for m in Member.all(): song1.members.append(m)
        for m in Member.select(age=17): song2.members.append(m)

        members = song1.members
        self.assertEqual(members.count(), 5)

        members = song2.members
        self.assertEqual(members.count(), 4)

        azusa = Member.get(first_name="Azusa")
        songs = azusa.songs
        self.assertEqual(songs.count(), 1)
        self.assertEqual(songs[0].name, "Utauyo!! MIRACLE")

    def testLimitOffset(self):
        team = Team.create(name="Houkago Tea Time")
        for name in self.names:
            team.members.append(first_name=name[0], last_name=name[1], part=name[2], age=name[3])

        # OFFSET 2
        qs = Member.all().offset(2).order_by("id")
        self.assertEqual(qs[0].first_name, "Yui")
        self.assertEqual(qs[1].first_name, "Tsumugi")
        self.assertEqual(qs.count(), 3)

        # LIMIT 1 OFFSET 2
        qs = Member.all().offset(2).limit(1).order_by("id")
        self.assertEqual(qs[0].first_name, "Yui")
        self.assertEqual(qs.count(), 1)
