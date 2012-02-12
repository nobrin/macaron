====================
 Macaron O/R Mapper
====================

Overview
========

Very small object-relational(O/R) mapper for SQLite3 in small applications.

*Macaron* is a single-file O/R mapper and small size(10KB), which provides easy access methods to SQLite.
And it supports Bottle_ web framework through plugin mechanism.

For example::

    >>> macaron.macaronage(dbfile="members.db")
    >>> member = Member.select_one("name=?", ["Azusa Nakano"])
    >>> print member
    Member [Azusa Nakano]
    >>> team = member.belong_to
    >>> print team
    Team [Houkago Tea Time]
    >>> for m in band.members: print m
    ...
    Member [Yui Hirasawa]
    Member [Mio Akiyama]
    Member [Tsumugi Kotobuki]
    Member [Ritsu Tainaka]
    Member [Azusa Nakano]

*Macaron* supports **many to one** relationships and reverse reference.
Many to many relationships have not been supported yet.

MacaronPlugin class for *Bottle* micro web-framework is implemented.

- Homepage: http://github.com/nobrin/macaron
- License: MIT (see LICENSE.txt)

.. _Bottle: http://bottlepy.org/


Installation and Dependencies
=============================

::

    tar zxvf macaron-0.1.dev.tar.gz
    cd macaron-0.1.dev
    python setup.py

MacaronPlugin is tested on Bottle 0.10.9.

Example
=======

::

    import macaron
    
    macaron.macaronage(dbfile="members.db")
    team = Team.get(1)
    Member.create(name="Azusa Nakano", part="Gt.2", team=team.get_id())

To be implemented
-----------------

::

    team = Team.get(1)
    team.append(Member.create(name="Azusa Nakano", part="Gt.2"))


Web application
===============

Bottle is lightweight web framework for Python. *Macaron* can be used with Bottle through MacaronPlugin.

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

In MacaronPlugin, connection object for sqlite3 is lazy.
The sqlite3.Connection object is create at call *Macaron* methods. If not called, any connection is created.
