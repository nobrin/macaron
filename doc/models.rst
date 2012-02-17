======
Models
======

.. module:: macaron

A model corresponds to the table of your database. It contains relationships and behaviors of the data.

The basics:

- Each model is a Python class that subclasses :class:`macaron.Model`.
- Each database field is represented into attribute of the model.
- Macaron defines attributes of the model from the table information automatically.
- Macaron's model likes Django's one.


Model definition
================

Basic usage
-----------

This example model defines a ``Member``, which has a ``first_name`` and ``last_name``:

::

    import macaron
    class Member(macaron.Model): pass

The above ``Member`` model corrensponds to a database table like this:

::

    CREATE TABLE member (
        id          INTEGER PRIMARY KEY,
        first_name  TEXT,
        last_name   TEXT,
        joined      TIMESTAMP
    );

Macaron does not create a table for simplified implementation, so attributes of the model is defined according to the table definition. In generally use, you need not modify the class definition of the model when the database table is modified.

Technical notes:

- The name of the table, ``member``, is automatically derived from class name, ``Member``, but can be specified with ``_table_name`` property.
- You need ``CREATE TABLE`` manually.

Auto updating (EXPERIMENTAL)
----------------------------

.. warning::

   This function is experimental implementation. It may be changed in future release.

You can specify fields which need to update at ``INSERT`` or ``UPDATE``. For example, the member table in above has ``joined`` field which means created time. In the situation, you define ``Member`` like this.

::

    class Member(macaron.Model):
        joined = macaron.NowAtCreate()

When you create a new member, *Macaron* set the created time to ``joined`` field. In addition, you can specified :class:`NowAtSave` for ``UPDATE``.


Using models
============

Relationships
-------------

If you use a single table which has no relationship is very simple, which is described above. However, it is not a thing you hope. Macaron supports "Many-to-One" relationships and needs the field information in the class definition. See below.

::

    class Team(macaron.Model): pass
    
    class Member(macaron.Model):
        team = macaron.ManyToOne(Team, related_name="members", fkey="team_id", key="id", related_name="members")

These Team and Member are defined as database tables in SQL.

::

    CREATE TABLE team (
        id          INTEGER PRIMARY KEY,
        name        TEXT
    );
    
    CREATE TABLE member (
        id          INTEGER PRIMARY KEY,
        team_id     INTEGER NOT NULL,
        first_name  TEXT,
        last_name   TEXT,
        age         INT
    );

Technical notes:

- The parameters ``related_name``, ``fkey`` (foreign key), and ``key`` of :class:`macaron.ManyToOne` can be omitted. Then, parameters are specified as below.

  - The ``related_name`` is derived from ``Team`` and '_set', i.e. 'team_set'.
  - The ``fkey`` is specified as ``Team``'s table name and '_id', i.e. 'team_id'.
  - The ``key`` is specified as ``Team``'s primary key name, i.e. 'id'.

In this example, a Many-to-One relationship which represents that a ``Member`` has a ``Team`` -- means a ``Member`` belongs to a ``Team`` but each ``Member`` only belongs to one ``Team`` -- is defined as above.

Tha attribute ``team`` of ``Member`` class relate the ``Member`` and ``Team``. This definition also create *recursive relationships* (an object with a Many-to-One relationship to itself), automatically. If you want to call the field to another name, you can it.

::

    class Member(macaron.Model):
        belongs_to = macaron.ManyToOne(Team, fkey="team_id", key="id", related_name="members")


Hooks
=====

- before_create
- before_save

