#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for class attributes.
"""
import unittest
import macaron
from models import Team, Member, Song

DB_FILE = ":memory:"

class TestClassAttributes(unittest.TestCase):
    def setUp(self):
        macaron.macaronage(DB_FILE)
        macaron.create_table(Team)
        macaron.create_table(Member)
        macaron.create_table(Song)

    def tearDown(self):
        macaron.bake()
        macaron.cleanup()

    def testTableMetaInfo(self):
        # TableMetaInfo object from Team class
        prop = Team.__dict__["_meta"]
        self.assertEqual(type(prop), macaron.TableMetaClassProperty)
        self.assert_(isinstance(prop.table_meta, macaron.TableMetaInfo))
        self.assertEqual(prop.table_name, "team")
        team = Team.create(name="Houkago Tea Time")
        self.assertEqual(type(prop.table_meta), macaron.TableMetaInfo)
        self.assertEqual(prop.table_name, "team")

    def testReferencedTableFields(self):
        # tests attributes of class properties
        # 'id' field which is automatically added in ModelMeta.__init__()
        fld = Team.__dict__["id"]
        self.assertEqual(type(fld), macaron.SerialKeyField)
        self.assertEqual(fld.null, True)
        self.assertEqual(fld.default, None)
        self.assertEqual(fld.is_primary_key, True)
        self.assertEqual(fld.is_user_defined, False)

        fld = Team.__dict__["created"]
        self.assert_(type(fld) is macaron.TimestampAtCreate)
        self.assertEqual(fld.null, True, "AtCreate accepted None value.")
        self.assertEqual(fld.default, None)
        self.assertEqual(fld.is_primary_key, False)
        self.assertEqual(fld.is_user_defined, True)

        fld = Team.__dict__["start_date"]
        self.assert_(type(fld) is macaron.DateAtCreate)
        self.assertEqual(fld.null, True, "AtCreate accepted None value.")
        self.assertEqual(fld.default, None)
        self.assertEqual(fld.is_primary_key, False)
        self.assertEqual(fld.is_user_defined, True)

        # tests ManyToOne relationship
        # _ManyToOne_Rev is a class which should not be initialized by user.
        # It is initialized by ManyToOne object.
        fld = Team.__dict__["members"]
        self.assertEqual(type(fld), macaron._ManyToOne_Rev)
        self.assertEqual(fld.ref, Team)             # Referenced table ie. Team table
        self.assertEqual(fld.ref_key, "id")         # PK of the referenced table ie. Team#id
        self.assertEqual(fld.rev, Member)           # Base table ie. Member table
        self.assertEqual(fld.rev_fkey, "band_id")   # Foreign key of the base table ie. Member#band_id

        # ManyToOneRevSet is a subclass of QuerySet
        team = Team.create(name="Houkago Tea Time")
        member_set = team.members  # this triggers setting for ref_key and rev_fkey
        self.assertEqual(type(member_set), macaron.ManyToOneRevSet)
        self.assert_(member_set.parent is team)
        self.assertEqual(member_set.parent_key, "id", "parent_key == fld.ref_key")
        self.assertEqual(member_set.cls_fkey, "band_id", "cls_fkey == fld.rev_fkey")

    def testBaseTableFields(self):
        # tests Member
        fld = Member.__dict__["id"]
        self.assertEqual(type(fld), macaron.SerialKeyField)
        self.assertEqual(fld.null, True)
        self.assertEqual(fld.default, None)
        self.assertEqual(fld.is_primary_key, True)
        self.assertEqual(fld.is_user_defined, False)

        for k in ["first_name", "last_name"]:
            fld = Member.__dict__[k]
            self.assertEqual(type(fld), macaron.CharField)
            self.assertEqual(fld.max_length, 20)
            self.assertEqual(fld.min_length, None)
            self.assertEqual(fld.length, None)
            self.assertEqual(fld.null, False)
            self.assertEqual(fld.default, None)
            self.assertEqual(fld.is_primary_key, False)
            self.assertEqual(fld.is_user_defined, True)

        fld = Member.__dict__["age"]
        self.assertEqual(type(fld), macaron.IntegerField)
        self.assertEqual(fld.max, 18)
        self.assertEqual(fld.min, 15)
        self.assertEqual(fld.null, False)
        self.assertEqual(fld.default, 16)
        self.assertEqual(fld.is_primary_key, False)
        self.assertEqual(fld.is_user_defined, True)

        fld = Member.__dict__["created"]
        self.assertEqual(type(fld), macaron.TimestampAtCreate)
        self.assertEqual(fld.null, True, "AtCreate accepts None value.")
        self.assertEqual(fld.default, None)
        self.assertEqual(fld.is_primary_key, False)
        self.assertEqual(fld.is_user_defined, True)

        fld = Member.__dict__["joined"]
        self.assert_(type(fld) is macaron.DateAtCreate)
        self.assertEqual(fld.null, True, "AtCreate accepts None value.")
        self.assertEqual(fld.default, None)
        self.assertEqual(fld.is_primary_key, False)
        self.assertEqual(fld.is_user_defined, True)

        fld = Member.__dict__["modified"]
        self.assertEqual(type(fld), macaron.TimestampAtSave)
        self.assertEqual(fld.null, True, "AtSave accepts None value.")
        self.assertEqual(fld.default, None)
        self.assertEqual(fld.is_primary_key, False)
        self.assertEqual(fld.is_user_defined, True)

        FLDS = ("id", "band_id", "first_name", "last_name", "part", "code", "age", "created", "joined", "modified")
        self.assertEqual(len(Member._meta.fields), len(FLDS))
        for fld in Member._meta.fields: self.assert_(fld.name in FLDS)

    def testManyToManyRelationship(self):
        # Song class
        fld = Song.__dict__["id"]
        self.assertEqual(type(fld), macaron.SerialKeyField)
        self.assertEqual(fld.null, True)
        self.assertEqual(fld.default, None)
        self.assertEqual(fld.is_primary_key, True)
        self.assertEqual(fld.is_user_defined, False)

        fld = Song.__dict__["name"]
        self.assertEqual(type(fld), macaron.CharField)
        self.assertEqual(fld.null, False)
        self.assertEqual(fld.default, None)
        self.assertEqual(fld.is_primary_key, False)
        self.assertEqual(fld.is_user_defined, True)
        self.assertEqual(fld.max_length, 50)
        self.assertEqual(fld.min_length, None)
        self.assertEqual(fld.length, None)

        # ManyToManyField in Song side
        fld1 = Song.__dict__["members"]
        self.assertEqual(type(fld1), macaron.ManyToMany)
        self.assertEqual(fld1.name, "members")
        self.assertEqual(fld1.related_name, "songs")
        self.assertEqual(fld1.cls, Song)
        self.assertEqual(fld1.ref, Member)
        self.assertEqual(fld1.lnk.__name__, "SongMemberLink")

        FLDS = ("id", "name")
        self.assertEqual(len(Song._meta.fields), len(FLDS))
        for fld in Song._meta.fields: self.assert_(fld.name in FLDS)

        # Member class
        # ManyToMany in Member side
        fld2 = Member.__dict__["songs"]
        self.assertEqual(type(fld2), macaron._ManyToManyBase)
        self.assertEqual(fld2.name, "songs")
        self.assertEqual(fld2.cls, Member)
        self.assertEqual(fld2.ref, Song)
        self.assertEqual(fld2.lnk.__name__, "SongMemberLink")

        self.assertEqual(fld1.lnk, fld2.lnk)

if __name__ == "__main__":
    import os
    if os.path.isfile(DB_FILE): os.unlink(DB_FILE)
    unittest.main()
    macaron.cleanup()
