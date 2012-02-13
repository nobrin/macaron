#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Testing for basic usage.
"""
import sys, os
sys.path.insert(0, "../")
import unittest
import macaron

DB_FILE = ":memory:"

sql_t_team = """CREATE TABLE IF NOT EXISTS team (
    id          INTEGER PRIMARY KEY,
    name        TEXT
)"""
sql_t_member = """CREATE TABLE IF NOT EXISTS member (
    id          INTEGER PRIMARY KEY,
    team_id     INTEGER REFERENCES team (id),
    first_name  TEXT,
    last_name   TEXT,
    part        TEXT
)"""

class Team(macaron.Model):
    _table_name = "team"
    def __str__(self):
        return "<Team '%s'>" % self.name

class Member(macaron.Model):
    _table_name = "member"
    team = macaron.ManyToOne("team_id", Team, "id", "members")

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
        macaron.macaronage(dbfile=DB_FILE)
        macaron.execute(sql_t_team)
        macaron.execute(sql_t_member)

    def tearDown(self):
        macaron.bake()

    def testCRUD(self):
        # create team
        name = "Houkago Tea Time"
        team = Team.create(name=name)
        self.assertEqual(str(team), "<Team '%s'>" % name)

        # create members
        for idx, n in enumerate(self.names):
            member = Member.create(team_id=team.get_id(), first_name=n[0], last_name=n[1], part=n[2])
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
        yui = Member.select_one("first_name=? AND last_name=?", ["Yui", "Hirasawa"])
        yui.part = "Castanets"
        yui.save()

        # re-fetch Yui
        member = Member.get(3)
        self.assertEqual(member.part, "Castanets")

        # cancel the changes
        macaron.rollback()

        # Add another member 'Sawako' as Gt1
        team = Team.get(1)
        Member.create(team_id=team.get_id(), first_name="Sawako", last_name="Yamanaka", part="Gt1")

        # re-fetch Sawako with index
        sawako = team.members[4]
        self.assertEqual(str(sawako), "<Member 'Sawako Yamanaka : Gt1'>")

        # but Sawako is not a member of the team
        sawako.delete()

        # Add another member Azusa through reverse relation of ManyToOne
        team.members.append(first_name="Azusa", last_name="Nakano", part="Gt2")

        azu = Member.select_one("first_name=? AND last_name=?", ["Azusa", "Nakano"])
        self.assertEqual(str(azu), "<Member 'Azusa Nakano : Gt2'>")

        # Okay, Yui changes part to Gt1
        yui = Member.select_one("first_name=? AND last_name=?", ["Yui", "Hirasawa"])
        yui.part = "Gt1"
        yui.save()

        # At last, there are five menbers
        nm = self.names[:]
        nm[2] = ("Yui", "Hirasawa", "Gt1", "Yui Hirasawa : Gt1")
        nm.append(("Azusa", "Nakano", "Gt2", "Azusa Nakano : Gt2"))
        for idx, m in enumerate(team.members):
            self.assertEqual(str(m), "<Member '%s'>" % nm[idx][3])

if __name__ == "__main__":
    if os.path.isfile(DB_FILE): os.unlink(DB_FILE)
    unittest.main()
    macaron.db_close()
