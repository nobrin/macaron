# -*- coding: utf-8 -*-
# Project: Macaron O/R Mapper
# Module:  Test models
import macaron

class Team(macaron.Model):
    name        = macaron.CharField(max_length=20)
    created     = macaron.TimestampAtCreate()
    start_date  = macaron.DateAtCreate()
    def __str__(self):
        return "<Team '%s'>" % self.name

class Member(macaron.Model):
    band        = macaron.ManyToOne(Team, null=True, related_name="members", on_delete="SET NULL", on_update="CASCADE")
    first_name  = macaron.CharField(max_length=20)
    last_name   = macaron.CharField(max_length=20)
    part        = macaron.CharField(max_length=10, null=True)
    code        = macaron.CharField(length=6, null=True)
    age         = macaron.IntegerField(max=18, min=15, default=16)
    created     = macaron.TimestampAtCreate()
    joined      = macaron.DateAtCreate()
    modified    = macaron.TimestampAtSave()

    def __str__(self):
        return "<Member '%s %s : %s'>" % (self.first_name, self.last_name, self.part)

class Song(macaron.Model):
    name        = macaron.CharField(max_length=50)
    members     = macaron.ManyToManyField(Member, related_name="songs")
