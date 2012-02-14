.. _Python: http://python.org/
.. _SQLite: http://www.sqlite.org/
.. _Bottle: http://bottlepy.org/

=====================
 Macaron: O/R Mapper 
=====================

Overview
========

*Macaron* is a small and simple object-relational mapper (ORM) for SQLite_ and Python_. It is distributed as a single file module which has no dependencies other than the `Python Standard Library <http://docs.python.org/library/>`_.

*Macaron* provides provides easy access methods to SQLite database. And it supports Bottle_ web framework through plugin mechanism.

Example::

    >>> import macaron
    >>> macaron.macaronage(dbfile="members.db")
    >>> team = Team.create(name="Houkago Tea Time")
    >>> team.members.append(first_name="Ritsu", last_name="Tainaka", part="Dr")
    <Member object 1>
    >>> mio = team.members.append(first_name="Mio", last_name="Akiyama", part="Ba")
    >>> print mio
    <Member 'Mio Akiyama : Ba'>
    >>> for member in team.members: print member
    ...
    <Member 'Ritsu Tainaka : Dr'>
    <Member 'Mio Akiyama : Ba'>

*Macaron* supports **many to one** relationships and reverse reference. Many to many relationships have not been supported yet. To realize simple implementation, *Macaron* does not provide methods for creation of tables.

MacaronPlugin class for Bottle_ web framework is implemented.


Installation and Dependencies
=============================

::

    tar zxvf macaron-0.1.dev.tar.gz
    cd macaron-0.1.dev
    python setup.py

or using easy_install::

    easy_install macaron


Web application
===============

Bottle is lightweight web framework for Python. *Macaron* can be used with Bottle through MacaronPlugin. The MacaronPlugin is tested with Bottle 0.10.9.

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


MacaronPlugin create lazy connection. So the sqlite3.Connection object is create at call *Macaron* methods. In case of no use the methods in *route*, any connection is created.

