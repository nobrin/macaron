=======================
 Model class reference 
=======================

.. module:: macaron

.. class:: Model(**kwargs)

   The *kwargs* are parameters which are pairs of field names and values. Constructing a :class:`Model` object is not enough to create a new record. You must call :meth:`Model.save`. In general, you should use :meth:`Model.create` or :meth:`QuerySet.append`.


Example
============

::

    # Creating new team and appending members
    new_team = Team.create(name="Houkago Tea Time")
    new_team.members.append(first_name="Azusa", last_name="Nakano", part="Gt2", age=16)
    new_team.members.append(first_name="Sawako", last_name="Yamanaka", part="Gt1", age=28)
    
    # Retrieving member, updating
    azusa = Member.get("first_name=?", ["Azusa"])
    sawako = Member.get(2)  # Getting with ID
    sawako.part = "Vo"
    sawako.save()       # Reflecting to database
    
    # Deleting
    azusa.delete()
    sawako.delete()


Class attributes
================

``_table_name``
---------------

.. attribute:: Model._table_name

If you want to use specified table name, define this. Macaron specifies database table name from class name (ex. Member -> member), automatically.


Class properties
================

``_meta``
---------

.. attribute:: Model._meta

   :rtype: :class:`TableMetaInfo` instance

   :class:`TableMetaInfo` is constructed when you access this property first.

Class methods
=============

``all``
-------

.. classmethod:: Model.all()

   Returns all records.

``create``
----------

.. classmethod:: Model.create(**kwargs)

   Creates a new object. This insert a new record to the database and returns the new :class:`Model` object.

``get``
-------

.. classmethod:: Model.get(value[, parameters])

   :param value: WHERE clause or value of primary key
   :param parameters: Parameters for placeholders if WHERE clause is specified.
   :type parameters: list
   :rtype: Model instance

   If you set WHERE clause into ``value`` with parameters, you must use place holders for security reasons. As this::
   
       member = Member.get("name=?", ["Azusa"])
   
   Or, you can specify primary key value::
   
       member = Member.get(1)
   
   The :meth:`Model.get` expects the single record. If multiple results are returned, :exc:`MultipleObjectsReturned` is raised.


``select``
----------

.. classmethod:: Model.select(where_clause[, paramters])

   :param where_clause: WHERE clause for SELECT
   :param parameters: Parameters for placeholders
   :type parameters: list
   :rtype: :class:`QuerySet` instance

   This likes :meth:`Model.get`, but returns :class:`QuerySet`.

Instance properties
===================

``pk``
------

.. attribute:: Model.pk

   Shortcut of primary key.

Instance methods
================

``after_create``
----------------

.. method:: Model.after_create()

``after_save``
--------------

.. method:: Model.after_save()

``before_create``
-----------------

.. method:: Model.before_create()

``before_save``
---------------

.. method:: Model.before_save()

``delete``
----------

.. method:: Model.delete()

   Deletes the object from the database.

``save``
--------

.. method:: Model.save()

   Saves the object to the database.

``validate``
------------

.. method:: Model.validate()

   Validates the fields of the object. This method should not be called manually.
