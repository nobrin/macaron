.. currentmodule:: macaron

====================
 QuerySet reference
====================

Example
=======

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


Instance methods
================

``aggregate``
-------------

.. method:: QuerySet.aggregate(agg_func)

   :param agg_func: aggregation method

``all``
-------

.. method:: QuerySet.all()

   Returns all objects which corresponds to ``SELECT * FROM table``.

``count``
---------

.. method:: QuerySet.count()

   Returns number of query result.

``distinct``
------------

.. method:: QuerySet.distinct()

   EXPERIMENTAL.
   I don't know what situation this distinct method is used in.

``get``
-------

.. method:: QuerySet.get(key_value[ or where_clause, parameters])

   :param key_value: primary key value
   :param where_clause: ``WHERE`` clause
   :param parameters: values for place holders
   
   Returns single :class:`Model` object. If it gets multiple results, :exc:`ValueError` raises.

``order_by``
------------

.. method:: QuerySet.order_by(*args)

   :param args: field names
   
   Sets ``ORDER BY`` clause. Field names are specified. If you want to use ``DESC``, add hyphen before the field name.
   
   Example::
   
       Members.all().order_by("-name")

``select``
----------

.. method:: QuerySet.select([where_clause, parameters])

   Sets ``WHERE`` clause.

``__getitem__``
---------------

.. method:: QuerySet.__getitem__(self, index)

   The :class:`QuerySet` objects acts iterators. You can specify index or slice.
