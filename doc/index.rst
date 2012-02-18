.. highlight:: python
.. currentmodule:: macaron

.. _SQLite: http://www.sqlite.org/
.. _Bottle: http://bottlepy.org/

==========================
Macaron: Python O/R Mapper
==========================

*Macaron* is a small and simple object-relational mapper (ORM) for SQLite_. It is distributed as a single file module which has no dependencies other than the `Python Standard Library <http://docs.python.org/library/>`_.

*Macaron* provides provides easy access methods to SQLite database. And it supports Bottle_ web framework through plugin mechanism.

Example::

    >>> import macaron
    >>> macaron.macaronage(dbfile="members.db")
    >>> team = Team.create(name="Houkago Tea Time")
    >>> team.members.append(name="Azusa", part="Gt2")
    <Member object 1>
    >>> macaron.bake()
    >>> azu = Member.get("part=?", ["Gt2"])
    >>> print azu
    <Member 'Azusa : Gt2'>
    >>> macaron.db_close()


User's Guide
============

.. toctree::
   :maxdepth: 2

   overview
   tutorial
   bottle
   models
   module
   class/model
   class/queryset
   class/macaron

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
