.. _Bottle: http://bottlepy.org/

============================
 Macaron in Web Application 
============================

.. currentmodule:: macaron

*Macaron* provides a plugin which simplifies the use of Bottle_ in your web application. Bottle is a micro web framework for Python. To use it, simply, you just call :func:`bottle.install` with :class:`MacaronPlugin` instance. After that you use it the way you've always done it.


Example
=======

This is sample of using :class:`MacaronPlugin` in Bottle web application.

::

    #!/usr/bin/env python
    from bottle import *
    import macaron
    
    # install MacaronPlugin instance
    DB_FILE = "bookmark.db"
    install(macaron.MacaronPlugin(DB_FILE))
    
    # Class definition
    class Bookmark(macaron.Model): pass
    
    # Route definition
    @route("/hello")
    def index():
        html = "<html>\n<head><title>My Bookmarks</title></head>\n"
        html += "<body>\n<h1>My Bookmarks</h1>\n<ul>\n"
        for bookmark in Bookmark.all():
            html += '<li><a href="%s">%s</a></li>\n' % (bookmark.url, bookmark.title)
        html += "</ul>\n</body>\n</html>\n"
        return html
    
    if __name__ == "__main__":
        run(host="0.0.0.0", port=8080)


MacaronPlugin class
===================

.. class:: MacaronPlugin(dbfile[, autocommit=True])

   :param dbfile: database file name.
   :param autocommit: Macaron will be commit automatically after execution of bottle.Route.

   In this plugin, Macaron opens connection when :class:`Model` class is used.