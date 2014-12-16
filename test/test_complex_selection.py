#!/usr/bin/env python
import unittest
import re
from datetime import datetime
import macaron

class Series(macaron.Model): name = macaron.CharField(max_length=30)
class Movie(macaron.Model): title = macaron.CharField(max_length=20)

class Group(macaron.Model):
    name     = macaron.CharField(max_length=20)
    series   = macaron.ManyToOne(Series, related_name="groups")

class Member(macaron.Model):
    curename = macaron.CharField(max_length=30)
    mygroup  = macaron.ManyToOne(Group, related_name="mymembers")
    subgroup = macaron.ManyToOne(Group, related_name="submembers")
    movies   = macaron.ManyToMany(Movie, related_name="members")
    joined   = macaron.DateField()

class SubTitle(macaron.Model):
    title = macaron.CharField(max_length=30)
    movie = macaron.ManyToOne(Movie, related_name="subtitles", on_delete="CASCADE")

class ComplexSelectionTestCase(unittest.TestCase):
    def setUp(self):
        macaron.macaronage(":memory:")
        macaron.create_table(Series)
        macaron.create_table(Group)
        macaron.create_table(Movie)
        macaron.create_table(Member)
        macaron.create_table(SubTitle)

        series1 = Series.create(name="Smile Precure")
        group1 = Group.create(name="Smile", series=series1)
        group2 = Group.create(name="Pink", series=series1)
        member1 = Member.create(curename="Happy", mygroup=group1, subgroup=group2, joined=datetime(2012, 2, 6))
        movie1 = Movie.create(title="NewStage")
        subtitle = SubTitle.create(title="Mirai no tomodachi", movie=movie1)
        member1.movies.append(movie1)

        series2 = Series.create(name="Happiness Charge Precure")
        group3 = Group.create(name="Happiness Charge", series=series2)
        group4 = Group.create(name="Purple", series=series2)
        member2 = Member.create(curename="Fortune", mygroup=group3, subgroup=group4, joined=datetime(2014, 2, 9))
        movie2 = Movie.create(title="NewStage2")
        subtitle2 = SubTitle.create(title="Eien no tomodachi", movie=movie2)
        member2.movies.append(movie2)

    def tearDown(self):
        macaron.bake()
        macaron.cleanup()

    def test_basic_selection(self):
        sql  = 'SELECT "member".* FROM "member"\n'
        sql += 'WHERE ((("member"."curename" = ?)))'
        qs = Member.select(curename="Happy")
        self.assertEqual(qs.sql, sql)
        self.assertEqual(qs.count(), 1)
        for rec in qs: self.assertEqual(rec.curename, "Happy")

        sql  = 'SELECT "member".* FROM "member"\n'
        sql += 'INNER JOIN "group" AS "member.mygroup" ON "member"."mygroup_id" = "member.mygroup"."id"\n'
        sql += 'WHERE ((("member.mygroup"."id" = ?)))'
        group = Group.get(name="Smile")
        qs = Member.select(mygroup=group)
        self.assertEqual(qs.sql, sql)
        self.assertEqual(qs.count(), 1)
        for rec in qs: self.assertEqual(rec.curename, "Happy")

        sql  = 'SELECT "member".* FROM "member"\n'
        sql += 'WHERE ((("member"."joined" = ?)))'
        qs = Member.select(joined=datetime(2012, 2, 6))
        self.assertEqual(qs.sql, sql)
        self.assertEqual(qs.count(), 1)
        for rec in qs: self.assertEqual(rec.curename, "Happy")

    def test_regexp(self):
        sql  = 'SELECT "member".* FROM "member"\n'
        sql += 'INNER JOIN "membermovielink" AS "member.movies.lnk" ON "member"."id" = "member.movies.lnk"."member_id"\n'
        sql += 'INNER JOIN "movie" AS "member.movies" ON "member.movies.lnk"."movie_id" = "member.movies"."id"\n'
        sql += 'WHERE ((("member.movies"."title" REGEXP ?)))'
        qs = Member.select(movies__title__regexp="New.+")
        self.assertEqual(qs.sql, sql)
        self.assertEqual(qs.count(), 2)
        self.assertEqual(qs[0].curename, "Happy")
        self.assertEqual(qs[1].curename, "Fortune")

    def test_in(self):
        sql  = 'SELECT "member".* FROM "member"\n'
        sql += 'INNER JOIN "membermovielink" AS "member.movies.lnk" ON "member"."id" = "member.movies.lnk"."member_id"\n'
        sql += 'INNER JOIN "movie" AS "member.movies" ON "member.movies.lnk"."movie_id" = "member.movies"."id"\n'
        sql += 'WHERE ((("member.movies"."title" IN (?,?,?))))'
        qs = Member.select(movies__title__in=("NewStage", "NewStage2", "Deluxe"))
        self.assertEqual(qs.sql, sql)
        self.assertEqual(qs.count(), 2)
        self.assertEqual(qs[0].curename, "Happy")
        self.assertEqual(qs[1].curename, "Fortune")

    def test_not_in(self):
        sql  = 'SELECT "member".* FROM "member"\n'
        sql += 'INNER JOIN "membermovielink" AS "member.movies.lnk" ON "member"."id" = "member.movies.lnk"."member_id"\n'
        sql += 'INNER JOIN "movie" AS "member.movies" ON "member.movies.lnk"."movie_id" = "member.movies"."id"\n'
        sql += 'WHERE ((("member.movies"."title" NOT IN (?,?,?))))'
        qs = Member.select(movies__title__not_in=("NewStage", "NewStage2", "Deluxe"))
        self.assertEqual(qs.sql, sql)
        self.assertEqual(qs.count(), 0)

    def test_between(self):
        sql  = 'SELECT "member".* FROM "member"\n'
        sql += 'WHERE ((("member"."joined" BETWEEN ? AND ?)))'
        qs = Member.select(joined__between=(datetime(2012, 1, 1), datetime(2012, 4, 1)))
        self.assertEqual(qs.sql, sql)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs[0].curename, "Happy")

        self.assertRaises(ValueError, lambda: Member.select(joined__between=(1, 2, 3)))
        self.assertRaises(TypeError, lambda: Member.select(joined__between=12))

    def test_not_between(self):
        sql  = 'SELECT "member".* FROM "member"\n'
        sql += 'WHERE ((("member"."joined" NOT BETWEEN ? AND ?)))'
        qs = Member.select(joined__not_between=(datetime(2012, 1, 1), datetime(2012, 4, 1)))
        self.assertEqual(qs.sql, sql)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs[0].curename, "Fortune")

    def test_selection_with_many2one(self):
        sql  = 'SELECT "member".* FROM "member"\n'
        sql += 'INNER JOIN "group" AS "member.mygroup" ON "member"."mygroup_id" = "member.mygroup"."id"\n'
        sql += 'WHERE ((("member.mygroup"."name" = ?)))'
        qs = Member.select(mygroup__name="Smile")
        self.assertEqual(qs.sql, sql)
        self.assertEqual(qs.count(), 1)
        for rec in qs: self.assertEqual(rec.curename, "Happy")

        sql  = 'SELECT "member".* FROM "member"\n'
        sql += 'INNER JOIN "group" AS "member.subgroup" ON "member"."subgroup_id" = "member.subgroup"."id"\n'
        sql += 'WHERE ((("member.subgroup"."name" = ?)))'
        qs = Member.select(subgroup__name="Pink")
        self.assertEqual(qs.sql, sql)
        self.assertEqual(qs.count(), 1)
        for rec in qs: self.assertEqual(rec.curename, "Happy")

        sql  = 'SELECT "member".* FROM "member"\n'
        sql += 'INNER JOIN "group" AS "member.subgroup" ON "member"."subgroup_id" = "member.subgroup"."id"\n'
        sql += 'INNER JOIN "group" AS "member.mygroup" ON "member"."mygroup_id" = "member.mygroup"."id"\n'
        sql += 'WHERE ((("member.mygroup"."name" = ? AND "member.subgroup"."name" = ?)))'
        qs = Member.select(mygroup__name="Smile", subgroup__name="Pink")
        self.assertEqual(qs.sql, sql)
        self.assertEqual(qs.count(), 1)
        for rec in qs: self.assertEqual(rec.curename, "Happy")

    def test_selection_with_many2one_deeply(self):
        sql  = 'SELECT "member".* FROM "member"\n'
        sql += 'INNER JOIN "group" AS "member.mygroup" ON "member"."mygroup_id" = "member.mygroup"."id"\n'
        sql += 'INNER JOIN "series" AS "member.mygroup.series" ON "member.mygroup"."series_id" = "member.mygroup.series"."id"\n'
        sql += 'WHERE ((("member.mygroup.series"."name" = ?)))'
        qs = Member.select(mygroup__series__name="Smile Precure")
        self.assertEqual(qs.sql, sql)
        self.assertEqual(qs.count(), 1)
        for rec in qs: self.assertEqual(rec.curename, "Happy")

    def test_selection_with_m2m(self):
        sql  = 'SELECT "member".* FROM "member"\n'
        sql += 'INNER JOIN "membermovielink" AS "member.movies.lnk" ON "member"."id" = "member.movies.lnk"."member_id"\n'
        sql += 'INNER JOIN "movie" AS "member.movies" ON "member.movies.lnk"."movie_id" = "member.movies"."id"\n'
        sql += 'WHERE ((("member.movies"."title" IN (?))))'
        qs = Member.select(movies__title__in=["NewStage"])
        self.assertEqual(qs.sql, sql)
        self.assertEqual(qs.count(), 1)
        for rec in qs: self.assertEqual(rec.curename, "Happy")

    def test_delete_with_m2m(self):
        sql  = 'SELECT "member".* FROM "member"\n'
        sql += 'INNER JOIN "membermovielink" AS "member.movies.lnk" ON "member"."id" = "member.movies.lnk"."member_id"\n'
        sql += 'INNER JOIN "movie" AS "member.movies" ON "member.movies.lnk"."movie_id" = "member.movies"."id"\n'
        sql += 'WHERE ("member.movies"."title" IN (?))'
        Member.select(movies__title__in=["NewStage"]).delete()

        qs = Member.all()
        self.assertEqual(qs.count(), 1) # Only Fortune is remained
        for rec in qs: self.assertEqual(rec.curename, "Fortune")

    def test_selection_with_m2m_deeply(self):
        sql  = 'SELECT "group".* FROM "group"\n'
        sql += 'INNER JOIN "member" AS "group.mymembers" ON "group"."id" = "group.mymembers"."mygroup_id"\n'
        sql += 'INNER JOIN "membermovielink" AS "group.mymembers.movies.lnk" ON "group.mymembers"."id" = "group.mymembers.movies.lnk"."member_id"\n'
        sql += 'INNER JOIN "movie" AS "group.mymembers.movies" ON "group.mymembers.movies.lnk"."movie_id" = "group.mymembers.movies"."id"\n'
        sql += 'WHERE ((("group.mymembers.movies"."title" IN (?))))'
        qs = Group.select(mymembers__movies__title__in=["NewStage"])
        self.assertEqual(qs.sql, sql)
        self.assertEqual(qs.count(), 1)
        for rec in qs: self.assertEqual(rec.name, "Smile")

    def test_m2m_deletion(self):
        members = Member.select(movies__title__glob="NewStage*")
        self.assertEqual(members.count(), 2)
        Movie.select(title="NewStage").delete()

        members = Member.select(movies__title__glob="NewStage*")
        self.assertEqual(members.count(), 1)
        self.assertEqual(members[0].curename, "Fortune")

    def test_m2m_append_duplicatedly(self):
        # Appending the same object to the parent will add link twice.
        movie = Movie.get(title="NewStage2")
        member = Member.get(curename="Fortune")
        member.movies.append(movie)

        fortune = Member.get(curename="Fortune")
        self.assertEqual(fortune.movies.count(), 2)

    def test_select_from(self):
        members = Member.select_from("SELECT * FROM member WHERE id = 1")
        self.assertTrue(isinstance(members, list))
        self.assertEqual(len(members), 1)
        self.assertEqual(members[0].curename, "Happy")

        members = Member.select_from("SELECT * FROM member WHERE curename = ?", ("Fortune",))
        self.assertTrue(isinstance(members, list))
        self.assertEqual(len(members), 1)
        self.assertEqual(members[0].curename, "Fortune")

    def test_get_specified_fields_m2o_m2m(self):
        sql  = 'SELECT "member"."curename", "member.mygroup".*, "member.subgroup".*, "member.movies".* FROM "member"\n'
        sql += 'INNER JOIN "group" AS "member.subgroup" ON "member"."subgroup_id" = "member.subgroup"."id"\n'
        sql += 'INNER JOIN "group" AS "member.mygroup" ON "member"."mygroup_id" = "member.mygroup"."id"\n'
        sql += 'INNER JOIN "membermovielink" AS "member.movies.lnk" ON "member"."id" = "member.movies.lnk"."member_id"\n'
        sql += 'INNER JOIN "movie" AS "member.movies" ON "member.movies.lnk"."movie_id" = "member.movies"."id"'
        qs = Member.all().fields("curename", "mygroup", "subgroup", "movies")
        self.assertEqual(qs.sql, sql)
        self.assertEqual(qs.count(), 2)
        self.assertTrue(isinstance(qs[0], tuple))
        self.assertEqual(qs[0], (u"Happy", Group.get(1), Group.get(2), Movie.get(1)))
        self.assertEqual(qs[1], (u"Fortune", Group.get(3), Group.get(4), Movie.get(2)))

    def test_get_specified_fields_m2orev(self):
        sql  = 'SELECT "series"."name", "series.groups".* FROM "series"\n'
        sql += 'INNER JOIN "group" AS "series.groups" ON "series"."id" = "series.groups"."series_id"\n'
        sql += 'ORDER BY "series.groups"."id"'
        qs = Series.all().fields("name", "groups").order_by("groups")
        self.assertEqual(qs.sql, sql)
        self.assertTrue(isinstance(qs[0], tuple))
        self.assertEqual(qs[0], (u"Smile Precure", Group.get(1)))
        self.assertEqual(qs[1], (u"Smile Precure", Group.get(2)))
        self.assertEqual(qs[2], (u"Happiness Charge Precure", Group.get(3)))
        self.assertEqual(qs[3], (u"Happiness Charge Precure", Group.get(4)))

    def test_get_specified_fields_m2mrev(self):
        sql  = 'SELECT "movie"."title", "movie.members".* FROM "movie"\n'
        sql += 'INNER JOIN "membermovielink" AS "movie.members.lnk" ON "movie"."id" = "movie.members.lnk"."movie_id"\n'
        sql += 'INNER JOIN "member" AS "movie.members" ON "movie.members.lnk"."member_id" = "movie.members"."id"'
        qs = Movie.all().fields("title", "members")
        self.assertEqual(qs.sql, sql)
        self.assertEqual(qs[0], (u"NewStage", Member.get(1)))
        self.assertEqual(qs[1], (u"NewStage2", Member.get(2)))

    def test_get_single_field_m2o_m2m(self):
        qs = Member.all().field("curename")
        self.assertEqual(qs.count(), 2)
        self.assertEqual(qs[0], u"Happy")
        self.assertEqual(qs[1], u"Fortune")

        qs = Member.all().field("mygroup")
        self.assertEqual(qs.count(), 2)
        self.assertEqual(qs[0], Group.get(1))
        self.assertEqual(qs[1], Group.get(3))

    def test_get_single_field_m2orev(self):
        qs = Series.all().field("name")
        self.assertEqual(qs.count(), 2)
        self.assertEqual(qs[0], u"Smile Precure")
        self.assertEqual(qs[1], u"Happiness Charge Precure")

        qs = Series.all().field("groups")
        self.assertEqual(qs.count(), 4)
        self.assertEqual(qs[0], Group.get(1))
        self.assertEqual(qs[1], Group.get(2))
        self.assertEqual(qs[2], Group.get(3))
        self.assertEqual(qs[3], Group.get(4))

    def test_get_single_field_m2mrev(self):
        qs = Movie.all().field("title")
        self.assertEqual(qs[0], u"NewStage")
        self.assertEqual(qs[1], u"NewStage2")

        qs = Movie.all().field("members")
        self.assertEqual(qs[0], Member.get(1))
        self.assertEqual(qs[1], Member.get(2))

    def test_get_single_field_m2o_m2m_with_getitem(self):
        qs = Member.all()["curename"]
        self.assertEqual(qs.count(), 2)
        self.assertEqual(qs[0], u"Happy")
        self.assertEqual(qs[1], u"Fortune")

        qs = Member.all()["mygroup"]
        self.assertEqual(qs.count(), 2)
        self.assertEqual(qs[0], Group.get(1))
        self.assertEqual(qs[1], Group.get(3))

if __name__ == "__main__":
    unittest.main()

