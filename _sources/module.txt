The *macaron* module content
============================

.. module:: macaron
    :platform: Unix, Windows
    :synopsis: SQLite O/R mapper
.. moduleauthor:: Nobuo Okazaki <nobrin@biokids.org>

.. autofunction:: macaronage

    This is called at starting use of Macaron.

    The basic connection parameters are:
    
    - **dbfile** -- The database file name
    - **lazy** -- Use LazyConnection class
    - **connection** -- sqlite3.Connection object

.. autofunction:: bake

.. autofunction:: rollback

.. autofunction:: execute

.. autofunction:: db_close

