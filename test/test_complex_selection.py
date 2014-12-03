#!/usr/bin/env python
import unittest
from datetime import datetime
import macaron

class Series(macaron.Model): name = macaron.CharField(max_length=20)
class Movie(macaron.Model): title = macaron.CharField(max_length=20)

class Group(macaron.Model):
    name     = macaron.CharField(max_length=20)
    series   = macaron.ManyToOne(Series, related_name="groups")

class Member(macaron.Model):
    curename = macaron.CharField(max_length=30)
    mygroup  = macaron.ManyToOne(Group, related_name="mymembers")
    subgroup = macaron.ManyToOne(Group, related_name="submembers")
    movies   = macaron.ManyToManyField(Movie, related_name="members")
    joined   = macaron.DateField()

class SubTitle(macaron.Model):
    title = macaron.CharField(max_length=30)
    movie = macaron.ManyToOne(Movie, related_name="subtitles")

class ComplexSelectionTestCase(unittest.TestCase):
    def setUp(self):
        macaron.macaronage(":memory:")
        macaron.create_table(Series)
        macaron.create_table(Group)
        macaron.create_table(Movie)
        macaron.create_table(Member)
        macaron.create_table(SubTitle)
        macaron.create_link_tables(Member)

        series = Series.create(name="Smile Precure")
        group1 = Group.create(name="Smile", series=series)
        group2 = Group.create(name="Pink", series=series)
        member = Member.create(curename="Happy", mygroup=group1, subgroup=group2, joined=datetime(2012, 2, 6))
        movie = Movie.create(title="NewStage2")
        subtitle = SubTitle.create(title="Mirai no tomodachi", movie=movie)
        member.movies.append(movie)

    def tearDown(self):
        macaron.bake()
        macaron.cleanup()

    def test_basic_selection(self):
        sql = 'SELECT "member".* FROM "member"\nWHERE ("member"."curename" = ?)'
        qs = Member.select(curename="Happy")
        self.assertEqual(qs.sql, sql)
        self.assertEqual(qs.count(), 1)
        for rec in qs: self.assertEqual(rec.curename, "Happy")

        sql  = 'SELECT "member".* FROM "member"\n'
        sql += 'INNER JOIN "group" AS "member.mygroup" ON "member"."mygroup_id" = "member.mygroup"."id"\n'
        sql += 'WHERE ("member.mygroup"."id" = ?)'
        group = Group.get(name="Smile")
        qs = Member.select(mygroup=group)
        self.assertEqual(qs.sql, sql)
        self.assertEqual(qs.count(), 1)
        for rec in qs: self.assertEqual(rec.curename, "Happy")

        sql  = 'SELECT "member".* FROM "member"\n'
        sql += 'WHERE ("member"."joined" = ?)'
        qs = Member.select(joined=datetime(2012, 2, 6))
        self.assertEqual(qs.sql, sql)
        self.assertEqual(qs.count(), 1)
        for rec in qs: self.assertEqual(rec.curename, "Happy")

    def test_selection_with_many2one(self):
        sql  = 'SELECT "member".* FROM "member"\n'
        sql += 'INNER JOIN "group" AS "member.mygroup" ON "member"."mygroup_id" = "member.mygroup"."id"\n'
        sql += 'WHERE ("member.mygroup"."name" = ?)'
        qs = Member.select(mygroup__name="Smile")
        self.assertEqual(qs.sql, sql)
        self.assertEqual(qs.count(), 1)
        for rec in qs: self.assertEqual(rec.curename, "Happy")

        sql  = 'SELECT "member".* FROM "member"\n'
        sql += 'INNER JOIN "group" AS "member.subgroup" ON "member"."subgroup_id" = "member.subgroup"."id"\n'
        sql += 'WHERE ("member.subgroup"."name" = ?)'
        qs = Member.select(subgroup__name="Pink")
        self.assertEqual(qs.sql, sql)
        self.assertEqual(qs.count(), 1)
        for rec in qs: self.assertEqual(rec.curename, "Happy")

        sql  = 'SELECT "member".* FROM "member"\n'
        sql += 'INNER JOIN "group" AS "member.mygroup" ON "member"."mygroup_id" = "member.mygroup"."id"\n'
        sql += 'INNER JOIN "group" AS "member.subgroup" ON "member"."subgroup_id" = "member.subgroup"."id"\n'
        sql += 'WHERE ("member.mygroup"."name" = ?) AND ("member.subgroup"."name" = ?)'
        qs = Member.select(mygroup__name="Smile", subgroup__name="Pink")
        self.assertEqual(qs.sql, sql)
        self.assertEqual(qs.count(), 1)
        for rec in qs: self.assertEqual(rec.curename, "Happy")

    def test_selection_with_many2one_deeply(self):
        sql  = 'SELECT "member".* FROM "member"\n'
        sql += 'INNER JOIN "group" AS "member.mygroup" ON "member"."mygroup_id" = "member.mygroup"."id"\n'
        sql += 'INNER JOIN "series" AS "member.mygroup.series" ON "member.mygroup"."series_id" = "member.mygroup.series"."id"\n'
        sql += 'WHERE ("member.mygroup.series"."name" = ?)'
        qs = Member.select(mygroup__series__name="Smile Precure")
        self.assertEqual(qs.sql, sql)
        self.assertEqual(qs.count(), 1)
        for rec in qs: self.assertEqual(rec.curename, "Happy")

    def test_selection_with_m2m(self):
        sql  = 'SELECT "member".* FROM "member"\n'
        sql += 'INNER JOIN "membermovielink" AS "member.movies.lnk" ON "member"."id" = "member.movies.lnk"."member_id"\n'
        sql += 'INNER JOIN "movie" AS "member.movies" ON "member.movies.lnk"."movie_id" = "member.movies"."id"\n'
        sql += 'WHERE ("member.movies"."title" IN (?))'
        qs = Member.select(movies__title__in=["NewStage2"])
        self.assertEqual(qs.sql, sql)
        self.assertEqual(qs.count(), 1)
        for rec in qs: self.assertEqual(rec.curename, "Happy")

    def test_delete_with_m2m(self):
        sql  = 'SELECT "member".* FROM "member"\n'
        sql += 'INNER JOIN "membermovielink" AS "member.movies.lnk" ON "member"."id" = "member.movies.lnk"."member_id"\n'
        sql += 'INNER JOIN "movie" AS "member.movies" ON "member.movies.lnk"."movie_id" = "member.movies"."id"\n'
        sql += 'WHERE ("member.movies"."title" IN (?))'
        Member.select(movies__title__in=["NewStage2"]).delete()
        #self.assertEqual(qs.sql, sql)
        #self.assertEqual(qs.count(), 1)
        #for rec in qs: self.assertEqual(rec.curename, "Happy")

    def test_selection_with_m2m_deeply(self):
        sql  = 'SELECT "group".* FROM "group"\n'
        sql += 'INNER JOIN "member" AS "group.mymembers" ON "group"."id" = "group.mymembers"."mygroup_id"\n'
        sql += 'INNER JOIN "membermovielink" AS "group.mymembers.movies.lnk" ON "group.mymembers"."id" = "group.mymembers.movies.lnk"."member_id"\n'
        sql += 'INNER JOIN "movie" AS "group.mymembers.movies" ON "group.mymembers.movies.lnk"."movie_id" = "group.mymembers.movies"."id"\n'
        sql += 'WHERE ("group.mymembers.movies"."title" IN (?))'
        qs = Group.select(mymembers__movies__title__in=["NewStage2"])
        self.assertEqual(qs.sql, sql)
        self.assertEqual(qs.count(), 1)
        for rec in qs: self.assertEqual(rec.name, "Smile")

if __name__ == "__main__":
    unittest.main()

