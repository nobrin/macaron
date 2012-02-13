.. _Python: http://python.org/
.. _SQLite: http://www.sqlite.org/
.. _Bottle: http://bottlepy.org/

====================
 Macaron: O/R Mapper
====================

Overview
========

*Macaron* is a small and simple object-relational mapper (ORM) for SQLite_ and Python_. It is distributed as a single file module which has no dependencies other than the `Python Standard Library <http://docs.python.org/library/>`_.

*Macaron* provides provides easy access methods to SQLite database. And it supports Bottle_ web framework through plugin mechanism.

Code example::

    >>> import macaron
    >>> macaron.macaronage(dbfile="members.db")
    >>> team = Team.create(name="Houkago Tea Time")
    >>> team.members.append(first_name="Ritsu", last_name="Tainaka", part="Dr")
    <Member object 1>
    >>> mio = team.members.append(first_name="Mio", last_name="Akiyama", part="Ba")
    >>> print mio
    <Member 'Mio Akiyama : Ba'>
    >>> for member in team.members: print member
    ...
    <Member 'Ritsu Tainaka : Dr'>
    <Member 'Mio Akiyama : Ba'>


Usage
=====

Definition of models
--------------------

*Macaron* needs tables in SQLite database. *Macaron* does not provides methods for creating tables and have simple Model class. In this section, table creation SQL and definition is below.

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

Model definition in Python code::

    import macaron
    
    class Team(macaron.Model):
        """Definition of Team table"""
        _table_name = "team"
        def __str__(self):
            return "<Team '%s'>" % self.name
    
    class Member(macaron.Model):
        """Definition of Member table
        team is a class property and accessor for parent 'Team' object.
        """
        _table_name = "member"
        team = macaron.ManyToOne("team_id", Team, "id", "members")

Basic usage
-----------

Okay, we have created some tables and defined model classes. Team class is the model related to team table in database and Member class is to member. After that, we will create a new team called "Houkago Tea Time" and append starting members.

::

    import macaron
    macaron.macaronage(dbfile="members.db")
    new_team = Team.create(name="Houkago Tea Time")
    member1 = new_team.members.append(first_name="Ritsu", last_name="Tainaka", part="Dr")
    member2 = new_team.members.append(first_name="Mio", last_name="Akiyama", part="Ba")
    macaron.bake()

This is very important and simple usage. Call **macaron.macaronage()** at starting use of macaron. This method connect to **members.db** database file. And a new team will be created with *ModelClass*.create() method. The **create()** is a class method and is called with key word arguments which consist field name and value pairs. It returns created Team object.

A new team has come, let's join new members to the team. The Team object is into a variable named *new_team*, you will call new_team.members.append(). The **append()** object method can be used with key word arguments like **create()** method and returns a new created Member object.

Where the *members* propery is defined? The property is defined automatically in Member class definition. The *team* property of Member is set as an instance of *ManyToOne* and it works as accessor to many to one relationship. The ManyToOne add a property for accessing reverse relationship to Team class. In this case, the property is named *members*.

At last, we have created a team with initial members and should commit it. Call **macaron.bake()** which is very wrapper to call sqlite3.Connection#commit().


In a web application (EXPERIMENTAL)
-----------------------------------
*Macaron* has a plugin for Bottle_ wab framework, which is MacaronPlugin class. It is tested on Bottle 0.10.9.

Example
-------

::

    #!/usr/bin/env python
    from bottle import *
    import macaron
    
    install(macaron.MacaronPlugin(dbfile="address.db"))
    
    class Address(macaron.Model):
        _table_name = "address"
    
    @route("/hello")
    def index():
        addr = Address.get(1)
        return "<h1>Hello!!</h1>My address is %s" % addr.address
    
    run(host="0.0.0.0", port=8080)

Implementation
--------------

MacaronPlugin create lazy connection. So the sqlite3.Connection object is create at call *Macaron* methods. In case of no use the methods in *route*, any connection is created.

