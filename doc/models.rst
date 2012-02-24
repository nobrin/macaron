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

The above ``Member`` model corresponds to a database table like this:

::

    CREATE TABLE member (
        id          INTEGER PRIMARY KEY,
        first_name  TEXT DEFAULT 'unknown',
        last_name   TEXT,
        joined      TIMESTAMP
    );

Macaron does not create a table for simplified implementation, so attributes of the model is defined according to the table definition. In generally use, you need not modify the class definition of the model when the database table is modified.

.. note::

   - The name of the table, ``member``, is automatically derived from class name, ``Member``, but can be specified with ``_table_name`` property.
   - You need ``CREATE TABLE`` manually.
   - DEFAULT property is auto-detected.


Field definition
----------------

Most simple case, you do not define your :class:`Model` classes except class definition. But you should define fields on your :class:`Model`\ s, the fields have validation and conversion mechanism. Field definition example is below.

::

    class Member(macaron.Model):
        name = macaron.CharField(max_length=20)
        joined = macaon.TimestampAtCreate()
        modified = macaron.TimestampAtSave()
        point = macaron.IntegerField(min=0, max=20)

In the code, the :class:`NowAtCreate`, :class:`NowAtSave`, `IntegerField`, and `CharField`. The former two classes differs from the latter two ones. Built-in classes are described below.

.. class:: TimestampAtCreate()

   This sets time created when ``INSERT`` is conducted.

.. class:: TimestampAtSave()

   This sets time modified when ``UPDATE`` is conducted.

.. class:: FloatField([min, max])

   :param min: minimum value
   :param max: maximum value
   
   This is for number field. The minimum and maximum values can be specified.

.. class:: IntegerField([min, max])

   This is for integer field.

.. class:: CharField([min_length, max_length])

   :param min_length: minimum length
   :param max_length: maximum length
   
   This is for text field. If you want to check the text length, you can specified ``min_length`` and ``max_length``.


Relationships
-------------

If you use a single table which has no relationship is very simple, which is described above. However, it is not a thing you hope. Macaron supports "Many-to-One" relationships and needs the field information in the class definition. See below.

::

    class Team(macaron.Model): pass
    
    class Member(macaron.Model):
        team = macaron.ManyToOne(Team, related_name="members", fkey="team_id", key="id")

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

.. note::

   - The parameters ``related_name``, ``fkey`` (foreign key), and ``key`` of :class:`macaron.ManyToOne` can be omitted. Then, parameters are specified as below.

     - The ``related_name`` is derived from ``Team`` and '_set', i.e. 'team_set'.
     - The ``fkey`` is specified as ``Team``'s table name and '_id', i.e. 'team_id'.
     - The ``key`` is specified as ``Team``'s primary key name, i.e. 'id'.

In this example, a Many-to-One relationship which represents that a ``Member`` has a ``Team`` -- means a ``Member`` belongs to a ``Team`` but each ``Member`` only belongs to one ``Team`` -- is defined as above.

The attribute ``team`` of ``Member`` class relate the ``Member`` and ``Team``. This definition also create *recursive relationships* (an object with a Many-to-One relationship to itself), automatically. If you want to call the field to another name, you can it.

::

    class Member(macaron.Model):
        belongs_to = macaron.ManyToOne(Team, fkey="team_id", key="id", related_name="members")


Using models
============


Customizing fields and behaviors of models
==========================================

Macaron's model class is designed flexible. You can customize field types and before and after ``INSERT`` and ``UPDATE``.

Field types
-----------

Field definition section describes how to use field classes. This section describes how to customize fields. Field type classes are derived from base class :class:`Field` or subclasses of :class:`Field`. Now there are :class:`AtCreate` and :class:`AtSave` subclasses derived from :class:`Field`. For example, :class:`NowAtCreate` is a subclass of :class:`AtCreate` (i.e. it is a subclass of :class:`Field`, too).

For example, :class:`NowAtCreate` is implemented as below.::

    class NowAtCreate(AtCreate):
        def set(self, obj, value):
            return datetime.datetime.now()

The :meth:`NowAtCreate.set` is called when object is inserted to database. In this way, implementing some callback methods and you can control behaviors of model objects.

These methods are called in below sequence.

- In ``INSERT`` and ``UPDATE``

  1. The :meth:`Field.set` is called at ``INSERT`` or ``UPDATE``.
  2. The :meth:`Field.validate` is called for validation.
  3. The :meth:`Model.before_create` or :meth:`Model.before_save` is called (see next section).
  4. The :meth:`Field.to_database` is called.
  5. SQL is conducted.
  6. The :meth:`Field.to_object` is called with new record from database.
  7. The :meth:`Model.after_create` or :meth:`Model.after_save` is called (see next section).

- In ``SELECT``

  1. SQL is conducted.
  2. The :meth:`Field.to_object` is called with selected record.


Hooks in model
--------------

- :meth:`Model.before_create()`
- :meth:`Model.before_save()`
- :meth:`Model.after_create()`
- :meth:`Model.after_save()`
