.. _Python: http://python.org/
.. _SQLite: http://www.sqlite.org/
.. _Bottle: http://bottlepy.org/

==========
 Tutorial
==========

Here is a tutorial for *Macaron*. *Macaron* is a simplified ORM, so there are few things you need to learn.


Definition of models
====================

*Macaron* needs tables in SQLite database. To make it simple, *Macaron* does not provides methods for creating tables. In this section, table creation SQL and definition is below.

SQL::

    CREATE TABLE team (
        id      INTEGER PRIMARY KEY,
        name    TEXT
    );
    
    CREATE TABLE member (
        id          INTEGER PRIMARY KEY,
        table_id    INTEGER REFERENCES team (id),
        first_name  TEXT,
        last_name   TEXT,
        part        TEXT
    );

You need creating tables into *members.db* file with the SQL.

Model definition in Python code::

    import macaron
    
    class Team(macaron.Model):
        """Definition of Team table"""
        def __str__(self):
            return "<Team '%s'>" % self.name
    
    class Member(macaron.Model):
        """Definition of Member table
        team is a class property and accessor for parent 'Team' object.
        """
        team = macaron.ManyToOne("team_id", Team, "id", "members")
        
        def __str__(self):
            return "<Member '%s %s : %s'>" % (self.first_name, self.last_name, self.part)

In these case, Team and Member classes correspond to 'team' and 'member' tables, respectively. So *Macaron* uses uncapitalized class names as table name. If not so, define ``_table_name`` for corresponding table name as a class property. Like this,

::

    class MyTest(macaron.Model):
        _table_name = "my_profile"

The class property of ``_table_name`` is removed when initializing in Meta-class ModelMeta.


Creating new records
====================

Okay, we have created some tables and defined model classes. Team class is the model related to team table in database and Member class is to member. After that, we will create a new team called "Houkago Tea Time" and append starting members.

::

    import macaron
    
    # A macaron needs 'macaronage' process.
    # The macaronage() initializes db connection with file name.
    macaron.macaronage("members.db")
    
    # Create a new team named 'Houkago Tea Time'.
    # Model.create() execute INSERT statement.
    new_team = Team.create(name="Houkago Tea Time")
    
    # Append new members to the team.
    # new_team.members is an accessor for Member table.
    member1 = new_team.members.append(first_name="Ritsu", last_name="Tainaka", part="Dr")
    member2 = new_team.members.append(first_name="Mio", last_name="Akiyama", part="Ba")
    
    # Yeah, all tasks has been done. Let's bake the macaron.
    # Commit this changes to database.
    macaron.bake()

Call **macaron.macaronage()** to initialize macaron. This method connect to **members.db** SQLite database file. And a new team will be created with *ModelClass*.create() method. The **create()** is a class method and is called with key word arguments which consist field name and value pairs. It returns created Team object.

A new team has come, let's join new members to the team. The Team object is into a variable named *new_team*, you will call new_team.members.append(). The **append()** object method can be used with key word arguments like **create()** method and returns a new created Member object.

Where the *members* propery is defined? The property is defined automatically in Member class definition. The *team* property of Member is set as an instance of *ManyToOne* and it works as accessor to many to one relationship. The ManyToOne add a property for accessing reverse relationship to Team class. In this case, the property is named *members*.

At last, we have created a team with initial members and should commit it. Call **macaron.bake()** which is a very wrapper to call sqlite3.Connection#commit().


Fetching records and updating
=============================

Now, we have a small database *members.db*. In this section, we try fetching records.

::

    import macaron
    
    macaron.macaronage(dbfile="members.db")
    
    # The simplest way is get() with record ID.
    ritsu = Member.get(1)
    # <Member 'Ritsu Tainaka : Dr'>
    
    # Fetching Team object Ritsu belongs to.
    ourband = ritsu.team
    # <Team 'Houkago Tea Time'>
    
    # And listing members who belongs to the team.
    for member in ourband.members:
        print members
    # <Member 'Ritsu Tainaka : Dr'>
    # <Member 'Mio Akiyama : Ba'>
    
    # You can get the member with index.
    mio = ourband.members[1]
    # <Member 'Mio Akiyama : Ba'>
    
    # Of course, you can SELECT with WHERE clause.
    # The get() returns a single object and select() returns generator.
    mio = Member.get("last_name=?", ["Akiyama"])
    
    members = Member.select("team_id=?", [ourband.pk])
    # [<Member object 1>, <Member object 2>]
    
    # Oops, Mio desides to sing the song.
    mio.part = "Vo"
    mio.save()
    
    print "Mio's part is %s." % mio.part
    # Mio's part is Vo.
    
    # But she canceled it.
    macaron.rollback()
    
    # Done.
    macaron.db_close()


Aggregation
===========

These are how to use aggregation methods. Aggregation is conducted with aggregate() method. The aggregate method takes single argument which is sub class of AggregateFunction. Currently, there are Sum(), Ave(), Max(), and Min(). The constructor of AggregateFunction class takes column name as argument.

::

    # Count
    count = Team.get(1).members.all().count()
    
    # Sum
    sum_of_ages = Team.get(1).members.all().aggregate(macaron.Sum("age"))
    
    # And you can use: average, max, and min are Ave(), Max(), Min(), respectively.
