.. highlight:: python
.. currentmodule:: macaron

===========================
 Release Notes and Changes
===========================

Release 0.3.1
=============

.. rubric:: Foreign key constraints support

* Set ``PRAGMA foreign_keys=ON`` when opening a connection to SQLite.
Only SQLite(>=3.6.19) supports foreign key constraints.
So in lower versions, this does not have any effect.

.. rubric:: Exceptions

* :exc:`MultipleObjectsReturned` for :meth:`Model.get()
  when it does not return a single object.
* :exc:`NotUniqueForeignKey` for Many-To-One relationships
  related with multiple parents.

.. rubric:: Constant name

* :attr:`Field.TYPENAMES` -> :attr:`Field.TYPE_NAMES`


Release 0.3.0
=============

.. rubric:: Most stable release
