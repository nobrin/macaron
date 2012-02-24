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

Macaron supports **Many-To-One** relationships and reverse reference. Many-To-Many relationships have not been supported yet. To realize simple implementation, Macaron does not provide methods for creation of tables.

MacaronPlugin class for Bottle_ web framework is implemented.


External resources
==================

- Homepage and documentation: http://nobrin.github.com/macaron/

  - Documentation in Japanese: http://biokids.org/?Macaron

- Python Package Index (PyPI): http://pypi.python.org/pypi/macaron
- GitHub: https://github.com/nobrin/macaron


Installation and Dependencies
=============================

::

    tar zxvf macaron-0.3.0.tar.gz
    cd macaron-0.3.0
    python setup.py

or using easy_install::

    easy_install macaron


Use for Web Applications
========================

Macaron in the Bottle
---------------------

Bottle_ is a lightweight web framework for Python. Macaron can be used with Bottle through :class:`MacaronPlugin`, which is tested with Bottle 0.10.9.

Example
-------

::

    #!/usr/bin/env python
    from bottle import *
    import macaron
    
    install(macaron.MacaronPlugin("address.db"))
    
    class Address(macaron.Model):
        _table_name = "address"
    
    @route("/hello")
    def index():
        addr = Address.get(1)
        return "<h1>Hello!!</h1>My address is %s" % addr.address
    
    run(host="localhost", port=8080)

Implementation
--------------

:class:`MacaronPlugin` create lazy connection. So the :class:`sqlite3.Connection` object is create at call Macaron methods. In case of no use the methods in :meth:`bottle.route`, any connection is created.
