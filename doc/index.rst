.. highlight:: python
.. currentmodule:: macaron

.. _SQLite: http://www.sqlite.org/
.. _Bottle: http://bottlepy.org/

==========================
Macaron: Python O/R Mapper
==========================

Documentation in Japanese is available at
`BioKids <http://biokids.org/?Macaron>`_.

*Macaron* is a small and simple object-relational mapper (ORM) for SQLite_.
It is distributed as a single file module which has no dependencies
other than the `Python Standard Library <http://docs.python.org/library/>`_.

*Macaron* provides easy access methods to your SQLite database.
And it supports the Bottle_ web framework through a plugin mechanism.
See :doc:`webapp`.

Example::

    >>> import macaron
    >>> macaron.macaronage(dbfile="members.db")
    >>> team = Team.create(name="Houkago Tea Time")
    >>> team.members.append(name="Azusa", part="Gt2")
    <Member object 1>
    >>> macaron.bake()
    >>> azu = Member.get(part="Gt2")
    >>> print azu
    <Member 'Azusa : Gt2'>
    >>> macaron.cleanup()


Features
========

Macaron aims to make the use of databases easy for small applications.

* An object-relational mapper (ORM) for SQLite.
* There are no dependencies except Python Standard Library.
* Many-To-One relationships are supported.
* Many-To-Many relationships are supported (New in 0.4).
* Pre-defined and user-defined validators can be used.
* Includes a plugin for Bottle, which is a micro-sized web framework.
* The module consists of only a single file.


User's Guide
============

.. toctree::
   :maxdepth: 2

   overview
   tutorial
   webapp
   models


Reference Guide
===============

.. toctree::
   :maxdepth: 2

   module
   class/model
   class/field
   class/queryset
   class/macaron

Release Notes
=============

.. toctree::
   :maxdepth: 2
   
   changes

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

