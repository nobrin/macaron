#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Testing for basic usage.
"""
import unittest
import macaron

DB_FILE = ":memory:"

SQL_TEAM = """CREATE TABLE IF NOT EXISTS team (
    id          INTEGER PRIMARY KEY,
    name        TEXT
)"""
SQL_MEMBER = """CREATE TABLE IF NOT EXISTS member (
    id          INTEGER PRIMARY KEY,
    team_id     INTEGER REFERENCES team (id),
    first_name  TEXT,
    last_name   TEXT,
    part        TEXT,
    age         INT
)"""

class Team(macaron.Model):
    def __str__(self):
        return "<Team '%s'>" % self.name

class Member(macaron.Model):
    team = macaron.ManyToOne(Team, related_name="members")

    def __str__(self):
        return "<Member '%s %s : %s'>" % (self.first_name, self.last_name, self.part)

class TestMacaron(unittest.TestCase):
    names = [
        ("Ritsu", "Tainaka", "Dr", "Ritsu Tainaka : Dr"),
        ("Mio", "Akiyama", "Ba", "Mio Akiyama : Ba"),
        ("Yui", "Hirasawa", "Gt", "Yui Hirasawa : Gt"),
        ("Tsumugi", "Kotobuki", "Kb", "Tsumugi Kotobuki : Kb"),
    ]

    def setUp(self):
        macaron.macaronage(DB_FILE, lazy=True)
        macaron.execute(SQL_TEAM)
        macaron.execute(SQL_MEMBER)

    def tearDown(self):
        macaron.bake()

    def testCRUD(self):
        # create team
        name = "Houkago Tea Time"
        team = Team.create(name=name)
        self.assertEqual(str(team), "<Team '%s'>" % name)

        # create members
        for idx, n in enumerate(self.names):
            member = Member.create(team_id=team.pk, first_name=n[0], last_name=n[1], part=n[2])
            self.assertEqual(str(member), "<Member '%s'>" % n[3])
            self.assertEqual(member.id, idx + 1)

        # get member with id
        ritsu = Member.get(1)
        self.assertEqual(str(ritsu), "<Member 'Ritsu Tainaka : Dr'>")

        # get team the member Ritsu belongs to is Houkago Tea Time
        team = member.team
        self.assertEqual(str(team), "<Team 'Houkago Tea Time'>")

        # get members with iterator
        for idx, m in enumerate(team.members):
            self.assertEqual(str(m), "<Member '%s'>" % self.names[idx][3])
        macaron.bake()

        # Yui changes instrument to castanets
        yui = Member.get("first_name=? AND last_name=?", ["Yui", "Hirasawa"])
        yui.part = "Castanets"
        yui.save()

        # re-fetch Yui
        member = Member.get(3)
        self.assertEqual(member.part, "Castanets")

        # Delete all members
        self.assertEqual(team.members.count(), 4)
        team.members.select("first_name=?", ["Ritsu"]).delete()
        self.assertEqual(team.members.count(), 3)
        team.members.delete()
        self.assertEqual(team.members.count(), 0)

        # cancel the changes
        macaron.rollback()

        # Add another member 'Sawako' as Gt1
        team = Team.get(1)
        Member.create(team_id=team.pk, first_name="Sawako", last_name="Yamanaka", part="Gt1")

        # re-fetch Sawako with index
        sawako = team.members[4]
        self.assertEqual(str(sawako), "<Member 'Sawako Yamanaka : Gt1'>")

        # but Sawako is not a member of the team
        sawako.delete()

        # Add another member Azusa through reverse relation of ManyToOne
        team.members.append(first_name="Azusa", last_name="Nakano", part="Gt2")

        azu = Member.get("first_name=? AND last_name=?", ["Azusa", "Nakano"])
        self.assertEqual(str(azu), "<Member 'Azusa Nakano : Gt2'>")

        # Okay, Yui changes part to Gt1
        yui = Member.get("first_name=? AND last_name=?", ["Yui", "Hirasawa"])
        yui.part = "Gt1"
        yui.save()

        # At last, there are five menbers
        nm = self.names[:]
        nm[2] = ("Yui", "Hirasawa", "Gt1", "Yui Hirasawa : Gt1")
        nm.append(("Azusa", "Nakano", "Gt2", "Azusa Nakano : Gt2"))
        for idx, m in enumerate(team.members):
            self.assertEqual(str(m), "<Member '%s'>" % nm[idx][3])

    def testAggregation(self):
        team = Team.create(name="Houkago Tea Time")
        team.members.append(first_name="Ritsu"  , last_name="Tainaka" , part="Dr" , age=17)
        team.members.append(first_name="Mio"    , last_name="Akiyama" , part="Ba" , age=17)
        team.members.append(first_name="Yui"    , last_name="Hirasawa", part="Gt1", age=17)
        team.members.append(first_name="Tsumugi", last_name="Kotobuki", part="Kb" , age=16)
        team.members.append(first_name="Azusa"  , last_name="Nakano"  , part="Gt2", age=17)

        a = ("Akiyama", "Hirasawa", "Kotobuki", "Nakano", "Tainaka")
        for i, m in enumerate(Team.get(1).members.order_by("last_name")):
            self.assertEqual(m.last_name, a[i])

        cnt = team.members.all().count()
        self.assertEqual(cnt, 5)

        sum_of_ages = team.members.all().aggregate(macaron.Sum("age"))
        self.assertEqual(sum_of_ages, 84)

        # sorry, I can't imagene what situation the distinct is used in.
        qs = Member.all().distinct()
        self.assertEqual(qs.sql, "SELECT DISTINCT * FROM member")

if __name__ == "__main__":
    import os
    if os.path.isfile(DB_FILE): os.unlink(DB_FILE)
    unittest.main()
    macaron.cleanup()
