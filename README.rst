====================
 Macaron O/R Mapper
====================

Overview
========

Very small object-relational(O/R) mapper for SQLite3 in small applications.

*Macaron* is a O/R mapper, which provides easy access methods to SQLite.

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


Homepage: http://github.com/nobrin/macaron
License: MIT (see LICENSE.txt)


Installation and Dependencies
=============================

::

    tar zxvf macaron-0.1.dev.tar.gz
    cd macaron-0.1.dev
    python setup.py


Example
=======

::

    import macaron
    
    macaron.macaronage(dbfile="members.db")
    team = Team.get(1)
    Member.create(name="Azusa Nakano", part="Gt.2", team=team.get_id())

To be implemented::

    team = Team.get(1)
    team.append(Member.create(name="Azusa Nakano", part="Gt.2"))
