.. _Bottle: http://bottlepy.org/

===================================
 Macaron with Bottle web framework 
===================================

.. currentmodule:: macaron

*Macaron* can be used with Bottle_ web framework. *Macaron* provides a plugin for Bottle framework.


Example
=======

::

    #!/usr/bin/env python
    from bottle import *
    import macaron
    
    DB_FILE = "bookmark.db"
    install(macaron.MacaronPlugin(DB_FILE))
    
    class Bookmark(macaron.Model): pass
    
    @route("/hello")
    def index():
        bm = Bookmark.get(1)
        return "<h1>Hello world!!</h1>%s" % bm.title
    
    run(host="0.0.0.0", port=8080)
