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

class TestBasicDefinitionAndOperation(unittest.TestCase):
    names = [
        ("Ritsu", "Tainaka", "Dr", "Ritsu Tainaka : Dr"),
        ("Mio", "Akiyama", "Ba", "Mio Akiyama : Ba"),
        ("Yui", "Hirasawa", "Gt", "Yui Hirasawa : Gt"),
        ("Tsumugi", "Kotobuki", "Kb", "Tsumugi Kotobuki : Kb"),
    ]

    def setUp(self):
        macaron.macaronage(DB_FILE, lazy=True)
        macaron.create_table(Team)
        macaron.create_table(Member)
        macaron.create_table(Song)

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

    def testTableSchema(self):
        # Assert table schemas
        # Team table
        sql_lines = [
            'CREATE TABLE "team" (',
            '  "id" INTEGER PRIMARY KEY NOT NULL,',
            '  "name" VARCHAR(20) NOT NULL,',
            '  "created" TIMESTAMP,',
            '  "start_date" DATE',
            ')',
        ]
        self._compare_schema("team", sql_lines)

        # Member table
        sql_lines = [
            'CREATE TABLE "member" (',
            '  "id" INTEGER PRIMARY KEY NOT NULL,',
            '  "band_id" INTEGER REFERENCES "team"("id") ON DELETE SET NULL ON UPDATE CASCADE,',
            '  "first_name" VARCHAR(20) NOT NULL,',
            '  "last_name" VARCHAR(20) NOT NULL,',
            '  "part" VARCHAR(10),',
            '  "code" CHAR(6),',
            '  "age" INTEGER NOT NULL DEFAULT 16,',
            '  "created" TIMESTAMP,',
            '  "joined" DATE,',
            '  "modified" TIMESTAMP',
            ')',
        ]
        self._compare_schema("member", sql_lines)

        # Song table
        sql_lines = [
            'CREATE TABLE "song" (',
            '  "id" INTEGER PRIMARY KEY NOT NULL,',
            '  "name" VARCHAR(50) NOT NULL',
            ')',
        ]
        self._compare_schema("song", sql_lines)

    def testLinkTable(self):
        # SongMemberLink table
        rel = Song.__dict__["members"]
        self.assertEqual(rel.__dict__["_lnk"].__name__, "SongMemberLink")
        tbl_name = rel._lnk._meta.table_name
        self.assertEqual(tbl_name, "songmemberlink")
        sql_lines = [
            'CREATE TABLE "songmemberlink" (',
            '  "id" INTEGER PRIMARY KEY NOT NULL,',
            '  "song_id" INTEGER NOT NULL REFERENCES "song"("id") ON DELETE CASCADE ON UPDATE CASCADE,',
            '  "member_id" INTEGER NOT NULL REFERENCES "member"("id") ON DELETE CASCADE ON UPDATE CASCADE',
            ')',
        ]
        self._compare_schema(tbl_name, sql_lines)

    def testCRUDObject(self):
        # Test for creating, reading, updating, deleteing
        # Create team
        name = "Houkago Tea Time"
        team = Team.create(name=name)
        self.assertEqual(str(team), "<Team '%s'>" % name)
        self.assertEqual(team.id, 1)

        # Create members
        for idx, n in enumerate(self.names):
            member = Member.create(band=team, first_name=n[0], last_name=n[1], part=n[2])
            self.assertEqual(str(member), "<Member '%s'>" % n[3])
            self.assertEqual(member.id, idx + 1)

        # Get member with primary key
        ritsu = Member.get(1)
        self.assertEqual(str(ritsu), "<Member 'Ritsu Tainaka : Dr'>")

        # Get team the member Ritsu belongs to is Houkago Tea Time
        team = ritsu.band
        self.assertEqual(str(team), "<Team 'Houkago Tea Time'>")

        # Get members with iterator
        for idx, m in enumerate(team.members):
            self.assertEqual(str(m), "<Member '%s'>" % self.names[idx][3])

        # Yui changes instrument to castanets
        macaron.bake()  # Commit before changes
        yui = Member.get(first_name="Yui", last_name="Hirasawa")
        self.assert_(yui)
        yui.part = "Castanets"
        self.assertEqual(yui.part, "Castanets")
        yui.save()

        # Re-fetch Yui
        member = Member.get(3)
        self.assertEqual(member.part, "Castanets")

        # Delete all members
        self.assertEqual(team.members.count(), 4)
        team.members.select(first_name="Ritsu").delete()
        self.assertEqual(team.members.count(), 3)
        team.members.delete()
        self.assertEqual(team.members.count(), 0)

        # Test for rollback
        # Cancel the changes
        macaron.rollback()
        team = Team.get(1)
        self.assertEqual(team.members.count(), 4)

        # Add another member 'Sawako' as Gt1
        member = Member.create(band=team, first_name="Sawako", last_name="Yamanaka", part="Gt1")
        self.assertEqual(str(member), "<Member 'Sawako Yamanaka : Gt1'>")

        # Re-fetch Sawako with index
        sawako = team.members[4]
        self.assertEqual(str(sawako), "<Member 'Sawako Yamanaka : Gt1'>")

        # But, Sawako is not a member of the team
        sawako.delete()

        # Add another member Azusa through reverse relation of ManyToOne
        team.members.append(first_name="Azusa", last_name="Nakano", part="Gt2")
        azu = Member.get(first_name="Azusa")
        self.assertEqual(str(azu), "<Member 'Azusa Nakano : Gt2'>")

        # Okay, Yui changes part to Gt1
        yui = Member.get(first_name="Yui")
        yui.part = "Gt1"
        yui.save()
        self.assertEqual(yui.part, "Gt1")

        # At last, there are five menbers
        nm = self.names[:]
        nm[2] = ("Yui", "Hirasawa", "Gt1", "Yui Hirasawa : Gt1")
        nm.append(("Azusa", "Nakano", "Gt2", "Azusa Nakano : Gt2"))
        for idx, m in enumerate(team.members):
            self.assertEqual(str(m), "<Member '%s'>" % nm[idx][3])

        # Foreign key constraint works on sqlite3 >= 3.6.19
        ver = macaron.sqlite_version_info
        if ver >= (3, 6, 19):
            # Test for ON CASCADE
            team = Team.get(1)
            team.id = 2
            team.save()
            cnt = 0
            for member in Member.all():
                cnt += 1
                self.assertEqual(member.band_id, 2)
            self.assertEqual(cnt, Member.all().count())

            # Test for ON DELETE
            team.delete()
            cnt = 0
            for member in Member.all():
                self.assertEqual(member.band, None)
                cnt += 1
            self.assertEqual(cnt, Member.all().count())
        else:
            msg = "Foreign key constraint works on SQLite(3.6.19) > Current(%s). Skip."
            warnings.warn(msg % ".".join([str(x) for x in ver]))

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

        cnt = team.members.count()
        self.assertEqual(cnt, 5)

        sum_of_ages = team.members.all().aggregate(macaron.Sum("age"))
        self.assertEqual(sum_of_ages, 84)

if __name__ == "__main__":
    import os
    if os.path.isfile(DB_FILE): os.unlink(DB_FILE)
    unittest.main()
    macaron.cleanup()
