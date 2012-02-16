=======================
 Model class reference 
=======================

.. warning::

    The reference for APIs is under construction.

.. module:: macaron

.. class:: Model

Class attributes
================

``convert``
-----------

.. warning::

    This has been not implemented yet.

.. classmethod:: Module.convert(cursor, row)

Called when converting the raw record to object, vice versa.

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


Class methods
=============

``all``
-------

.. classmethod:: Model.all()

``create``
----------

.. classmethod:: Model.create(**kwargs)

``get``
-------

.. classmethod:: Model.get(value[, parameters])

   :param value: WHERE clause or value of primary key
   :param parameters: Parameters for placeholders if WHERE clause is specified.
   :type parameters: list
   :rtype: Model instance

``select``
----------

.. classmethod:: Model.select(where_clause[, paramters])

   :param where_clause: WHERE clause for SELECT
   :param parameters: Parameters for placeholders
   :type parameters: list
   :rtype: :class:`QuerySet` instance


Instance properties
===================

``pk``
------

.. attribute:: Model.pk

Instance methods
================

``delete``
----------

.. method:: Model.delete()


``save``
--------

.. method:: Model.save()

.. .. autoclass:: Model
..    :members:
..    :undoc-members:


Code example
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
