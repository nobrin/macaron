.. currentmodule:: macaron

====================
 Field reference
====================

Instance methods
================

``initialize_after_meta``
-------------------------

.. method:: Field.initialize_after_meta()

``set``
-------

.. method:: Field.set(obj, value)

   :param obj: current model object
   :param value: current value
   :returns: new value

``to_database``
---------------

.. method:: to_database(obj, value)

   :returns: value which is stored into database

``to_object``
-------------

.. method:: to_object(row, value)

   :param row: raw record from database
   :param value: current value from database
   :returns: value which is set into field of model

``validate``
------------

.. method:: validate(obj, value)

   :raises: :exc:`ValidationError` when validation failed
   :returns: ``True`` when validation succeeded

