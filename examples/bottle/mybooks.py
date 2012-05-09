#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Macaron Web Application Sample with Bottle Framework.
This is a simple web application sample with using Macaron and Bottle.

Usage:
First, you initialize database file.
 ./mybooks.py init

After that, you can start server.
 ./mybooks.py

Initially, the server will run on the 'localhost'.
If you want to access the server from other places, you run the server as below.
 ./mybooks.py 0.0.0.0

"""
import sys, os
from bottle import *
import macaron

SQL_T_TAG = """CREATE TABLE IF NOT EXISTS tag (
    id          INTEGER PRIMARY KEY,
    name        VARCHAR(20)
)"""

SQL_T_BOOK = """CREATE TABLE IF NOT EXISTS book (
    id          INTEGER PRIMARY KEY,
    tag_id     INTEGER REFERENCES tag (id),
    title       VARCHAR(50),
    description VARCHAR(200),
    rating      INT
)"""

# Installs MacaronPlugin for working in the Bottle.
install(macaron.MacaronPlugin("books.db"))

# --- Model definitions
class Tag(macaron.Model): pass
class Book(macaron.Model):
    # Defines Many-To-One relationship to Tag
    tag = macaron.ManyToOne(Tag, related_name="books")
    # Rating must be set between 0 and 5.
    rating = macaron.IntegerField(min=0, max=5)

def initialize():
    """Initializes database file"""
    # Deletes database file if exists.
    if os.path.isfile("books.db"): os.unlink("books.db")

    # Initializes Macaron
    macaron.macaronage("books.db")

    # Creates tables
    macaron.execute(SQL_T_TAG)
    macaron.execute(SQL_T_BOOK)

    # Initial data
    tag1 = Tag.create(name="Python")
    tag1.books.append(title="Learning Python", description="Powerful Object-Oriented Programming", rating=5)
    tag1.books.append(title="Expert Python Programming", description="Python best practice for experts.", rating=4)
    tag2 = Tag.create(name="Japanese")
    tag2.books.append(title="K-ON!", description="Highschool band cartoon.", rating=5)

    # Commits
    macaron.bake()

@get("/")
@view("index.html")
def index():
    """Shows book titles and descriptions"""
    tagid = request.query.tagid
    books = []
    if tagid:
        try:
            tag = Tag.get(tagid)
            books = tag.books.all()
        except Tag.DoesNotExist: pass
    if not books: books = Book.all().order_by("title")
    return dict(books=books)

@post("/")
@view("index.html")
def register():
    """Registers new book record"""
    tagset = Tag.select("name=?", [request.forms.tag])

    # if there is tag matched with tag name, creating it.
    if tagset.count(): tag = tagset[0]
    else: tag = Tag.create(name=request.forms.tag)
    tag.books.append(
        title=request.forms.title,
        description=request.forms.desc,
        rating=int(request.forms.rating)
    )
    books = Book.all().order_by("title")
    return dict(books=books)

@route("/delete/<id:int>")
@view("index.html")
def delete_book(id):
    """Delete registered book"""
    try:
        book = Book.get(id)
        book.delete()
    except Book.DoesNotExist: pass
    return dict(books=Book.all().order_by("title"))

if __name__ == "__main__":
    host = "localhost"
    if len(sys.argv) == 2:
        if sys.argv[1] == "init":
            initialize()
            sys.exit(0)
        else: host = sys.argv[1]
    debug(True)
    run(host=host, port=8080, reloader=True)

