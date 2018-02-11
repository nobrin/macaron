.. _Python: http://python.org/
.. _SQLite: http://www.sqlite.org/
.. _Bottle: http://bottlepy.org/

==========
 Tutorial
==========

Here is a tutorial for *Macaron*.
*Macaron* is a simplified ORM, but there are a few things you need to learn.


Definition of models
====================

*Macaron* needs tables in an SQLite database.
To make it simple,
*Macaron* does not provides methods for creating tables.
In this section, table creation SQL and definition is explained.

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
        part        TEXT,
        age         INT
    );

You need to create tables into the *members.db* file with SQL.

The corresponding model definition in Python code::

    import macaron
    
    class Team(macaron.Model):
        """Definition of Team table"""
        def __str__(self):
            return "<Team '%s'>" % self.name
    
    class Member(macaron.Model):
        """Definition of Member table
        team is a class property and accessor for parent 'Team' object.
        Macaron detects some field types, but if you want to validate,
	define those criteria.
        """
        team = macaron.ManyToOne(Team)
        age = macaron.IntegerField(min=15, max=18)

        def __str__(self):
            return "<Member '%s %s : %s'>" % (self.first_name, self.last_name, self.part)

In these cases, Team and Member classes correspond to 'team' and 'member'
tables, respectively.
So *Macaron* uses the uncapitalized class names as the table name.
To override this, define ``_table_name`` with the corresponding table name
as a class property.
Like this,

::

    class MyTest(macaron.Model):
        _table_name = "my_profile"

The class property of ``_table_name`` is removed when initializing
in the metaclass ModelMeta.


Creating new records
====================

Okay, we have created some tables and defined model classes.
The Team class is the model related to the ``team`` table in the database,
and simiarly, the Member class corresponds to the ``member`` table.
Now, we can create a new team called "Houkago Tea Time" and populate it with
some members.

::

    import macaron
    
    # A macaron needs 'macaronage' process.
    # First of all, call macaron.macaronage() to initialize macaron.
    # This method connects to the 'members.db' SQLite database file.
    macaron.macaronage("members.db")
    
    # Create a new team named 'Houkago Tea Time'.
    # A new team is created with Model.create().
    # The create() is a class method and is called with keyword arguments
    # which consist of field name and value pairs.
    # It returns the created Team object.
    new_team = Team.create(name="Houkago Tea Time")
    
    # Append new members to the team.
    # The Team object is held in a variable named 'new_team',
    # and we can now call new_team.members.append().
    # 'new_team.members' is an accessor for Members.
    # append() can be used with key word arguments like the create() method
    # and returns the newly created Member object.
    member1 = new_team.members.append(first_name="Ritsu", last_name="Tainaka", part="Dr")
    member2 = new_team.members.append(first_name="Mio", last_name="Akiyama", part="Ba")
    
    # Yeah, all tasks has been done. Let's bake the macaron.
    # At last, we have created a team with initial members
    # and should commit it.
    # Call macaron.bake() which is a very simple wrapper
    # to call sqlite3.Connection#commit().
    macaron.bake()

Where is the *members* propery defined?
The property is defined automatically in the Member class definition.
The *team* property of Member is set as an instance of *ManyToOne*
and it works as accessor to a many-to-one relationship.
The ManyToOne adds a property for accessing
the reverse relationship to the Team class.
In this case, the property is named *members*.


Fetching records and updating
=============================

Now, we have a small database *members.db*.
In this section, we try fetching records.

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

Aggregation is conducted with the ``aggregate()`` method.
The aggregate method takes single argument which is a member of a subclass of
AggregateFunction.
Currently, there are ``Sum()``, ``Ave()``, ``Max()``, and ``Min()``.
The constructor of the AggregateFunction class takes a column name as its
argument.

::

    # Count
    count = Team.get(1).members.all().count()
    
    # Sum
    sum_of_ages = Team.get(1).members.all().aggregate(macaron.Sum("age"))
    
    # And you can use: average, max, and min are Ave(), Max(), Min(), respectively.
