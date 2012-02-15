# -*- coding: utf-8 -*-
"""
*Macaron* is a small and simple object-relational mapper (ORM) for SQLite and
Python. It is distributed as a single file module which has no dependencies
other than the Python Standard Library.

*Macaron* provides provides easy access methods to SQLite database. And it
supports Bottle web framework through plugin mechanism.

Example::

    >>> import macaron
    >>> macaron.macaronage(dbfile="members.db")
    >>> team = Team.create(name="Houkago Tea Time")
    >>> team.members.append(name="Ritsu", part="Dr")
    <Member object 1>
    >>> mio = team.members.append(name="Mio", part="Ba")
    >>> print mio
    <Member 'Mio : Ba'>
    >>> for member in team.members: print member
    ...
    <Member 'Ritsu : Dr'>
    <Member 'Mio : Ba'>
"""
__author__ = "Nobuo Okazaki"
__version__ = "0.2.0-dev"
__license__ = "MIT License"

import sqlite3
import re
import copy

def macaronage(dbfile=":memory:", lazy=False, connection=None, autocommit=False):
    """Initializing macaron"""
    conn = None
    if connection:
        conn = connection
    else:
        if lazy: conn = LazyConnection(dbfile)
        else: conn = sqlite3.connect(dbfile)
    if not conn: raise Exception("Can't create connection.")
    _m.connection["default"] = conn
    _m.autocommit = autocommit

def execute(*args, **kw):
    """Wrapper for connection"""
    return _m.connection["default"].cursor().execute(*args, **kw)

def bake():
    """Committing the database."""
    _m.connection["default"].commit()

def rollback(): _m.connection["default"].rollback()
def db_close(): _m.connection["default"].close()

class LazyConnection(object):
    """Lazy connection wrapper"""
    def __init__(self, *args, **kw):
        self.args = args
        self.kwargs = kw
        self._conn = None

    def __getattr__(self, name):
        if name in ["commit", "rollback", "close"] and not self._conn: return True
        self._conn = self._conn or sqlite3.connect(*self.args, **self.kwargs)
        return getattr(self._conn, name)

#    def commit(self): return True
#    def rollback(self): return True
#    def close(self): return True

class Macaron(object):
    """Macaron controller class. Do not instance this class by user."""
    def __init__(self):
        self.connection = {}

class Fields(list):
    """Field collection"""
    def __init__(self):
        self._field_dict = {}

    def append(self, fld):
        super(Fields, self).append(fld)
        self._field_dict[fld.name] = fld

    def __getitem__(self, name): return self._field_dict[name]

class Field(object):
    """Field information class"""
    def __init__(self, row):
        """
        @type  row: tuple
        @param row: tuple got from 'PRAGMA table_info(table_name)'
        """
        self.cid, self.name, self.type, \
            self.not_null, self.default, self.is_primary_key = row
        if re.match(r"^BOOLEAN$", self.type, re.I):
            self.default = bool(re.match(r"^TRUE$", self.default, re.I))

class ClassProperty(property):
    """Using class property wrapper class"""
    def __get__(self, owner_obj, cls):
        return self.fget.__get__(owner_obj, cls)()

class TableMeta(object):
    """Table information class"""
    def __init__(self, conn, table_name):
        self.fields = Fields()
        self.primary_key = None
        self.conn = conn
        cur = conn.cursor()
        rows = cur.execute("PRAGMA table_info(%s)" % table_name).fetchall()
        for row in rows:
            fld = Field(row)
            self.fields.append(Field(row))
            if fld.is_primary_key: self.primary_key = fld

class ManyToOne(property):
    """Many to one relation ship definition class"""
    def __init__(self, fkey, ref, ref_key=None, reverse_name=None):
        # in this state, db has been not connected!
        self.fkey = fkey                    #: foreign key name ('many' side)
        self.ref = ref                      #: reference table ('one' side)
        self.ref_key = ref_key              #: reference key ('one' side)
        self.reverse_name = reverse_name    #: accessor name for one to many relation

    def __get__(self, owner, cls):
        ref = self.ref._table_name
        self.ref_key = self.ref_key or self.ref._meta.primary_key.name
        sql = "SELECT %s.* FROM %s LEFT JOIN %s ON %s = %s.%s WHERE %s.%s = ?" \
            % (ref, cls._table_name, ref, self.fkey, ref, self.ref_key, \
               cls._table_name, cls._meta.primary_key.name)
        cur = cls._meta.conn.cursor()
        cur = cur.execute(sql, [owner.get_id()])
        row = cur.fetchone()
        if cur.fetchone(): raise ValueError()
        return self.ref._factory(cur, row)

    def set_reverse(self, rev_cls):
        """Setting up one to many definition method
        This method will be called in MetaModel#__init__.
        To inform the model class to ManyToOne and _ManyToOne_Rev classes.

        @type  rev_cls: class
        @param rev_cls: 'many' side class
        """
        self.reverse_name = self.reverse_name or "%s_set" % rev_cls.__name__.lower()
        setattr(self.ref, self.reverse_name, _ManyToOne_Rev(self.ref, self.ref_key, rev_cls, self.fkey))

class _ManyToOne_Rev(property):
    """The reverse of many to one relationship."""
    def __init__(self, ref, ref_key, rev, rev_fkey):
        self.ref = ref              # Reference table (parent)
        self.ref_key = ref_key      # Key column name of parent
        self.rev = rev              # Child table (many side)
        self.rev_fkey = rev_fkey    # Foreign key name of child

    def __get__(self, owner, cls):
        self.ref_key = self.ref_key or self.ref._meta.primary_key.name
        qs = self.rev.select("%s = ?" % self.rev_fkey, [getattr(owner, self.ref_key)])
        return ManyToOneRevSet(qs, owner, self)

class QuerySet(object):
    """This class generates SQL which like QuerySet in Django"""
    def __init__(self, parent):
        if isinstance(parent, QuerySet):
            self.cls = parent.cls
            self.clauses = copy.deepcopy(parent.clauses)
        else:
            self.cls = parent
            self.clauses = {"where": [], "order_by": [], "values": []}
        self.clauses["offset"] = 0
        self.clauses["limit"] = 0
        self.clauses["distinct"] = False
        self._initialize_cursor()

    def _initialize_cursor(self):
        """Cleaning cache and state"""
        self.cur = None     # cursor
        self._index = -1    # pointer
        self._cache = []    # cache list

    def _generate_sql(self):
        sqls = ["SELECT * FROM %s" % self.cls._table_name]
        if len(self.clauses["where"]):
            sqls.append("WHERE %s" % " AND ".join(["(%s)" % c for c in self.clauses["where"]]))
        if len(self.clauses["order_by"]):
            sqls.append("ORDER BY %s" % ", ".join(self.clauses["order_by"]))
        if self.clauses["offset"]: sqls.append("OFFSET %d" % self.clauses["offset"])
        if self.clauses["limit"]: sqls.append("LIMIT %d" % self.clauses["limit"])
        return "\n".join(sqls)
    sql = property(_generate_sql)   #: Generating SQL

    def _execute(self):
        """Getting and setting a new cursor"""
        self._initialize_cursor()
        self.cur = self.cls._meta.conn.cursor().execute(self.sql, self.clauses["values"])

    def __iter__(self):
        self._execute()
        return self

    def next(self):
        if not self.cur: self._execute()
        row = self.cur.fetchone()
        self._index += 1
        if not row: raise StopIteration()
        self._cache.append(self.cls._factory(self.cur, row))
        return self._cache[-1]

    def get(self, where, values=None):
        if values == None:
            values = [where]
            where = "%s = ?" % self.cls._meta.primary_key.name
        qs = self.select(where, values)
        try: obj = qs.next()
        except StopIteration: raise self.cls.DoesNotFound()
        try: qs.next()
        except StopIteration: return obj
        raise ValueError("Returns more rows.")

    def select(self, where, values):
        newset = self.__class__(self)
        newset.clauses["where"].append(where)
        newset.clauses["values"] += values
        return newset

    def order_by(self, *args):
        newset = self.__class__(self)
        newset.clauses["order_by"] += [re.sub(r"^-(.+)$", r"\1 DESC", n) for n in args]
        return newset

    def __getitem__(self, index):
        newset = self.__class__(self)
        if isinstance(index, slice):
            start, stop = index.start or 0, index.stop or 0
            newset.clauses["offset"], newset.clauses["limit"] = start, stop - start
            return newset
        elif self._index >= index: return self._cache[index]
        for obj in self:
            if self._index >= index: return obj

    def __str__(self):
        objs = self._cache + [obj for obj in self]
        return str(objs)

class ManyToOneRevSet(QuerySet):
    """Reverse relationship of ManyToOne"""
    def __init__(self, parent_query, parent_object=None, rel=None):
        super(ManyToOneRevSet, self).__init__(parent_query)
        if parent_object and rel:
            self.parent = parent_object
            self.parent_key = rel.ref_key
            self.cls_fkey = rel.rev_fkey

    def append(self, *args, **kw):
        """Append new member"""
        kw[self.cls_fkey] = getattr(self.parent, self.parent_key)
        return self.cls.create(*args, **kw)

class MetaModel(type):
    """Meta class for Model class"""
    def __new__(cls, name, bases, dict):
        if not dict.has_key("_table_name"):
            dict["_table_name"] = name.lower()
#            raise Exception("'%s._table_name' is not set." % name)
        return type.__new__(cls, name, bases, dict)

    def __init__(instance, name, bases, dict):
        for k in dict.keys():
            if isinstance(dict[k], ManyToOne):
                dict[k].set_reverse(instance)

class Model(object):
    """Base model class

    Models inherit the class.
    """
    __metaclass__ = MetaModel
    _table_name = None                  #: Database table name
    _table_meta = None                  #: Table information

    class DoesNotFound(Exception): pass

    @classmethod
    def _get_meta(cls):
        if not cls._table_meta:
            cls._table_meta = TableMeta(_m.connection["default"], cls._table_name)
        return cls._table_meta
    _meta = ClassProperty(_get_meta)    #: Table information

    def __init__(self, **kw):
        cls = self.__class__
        if not cls._meta:
            cls._meta = TableMeta(_m.connection["default"], cls._table_name)
        for fld in cls._meta.fields: setattr(self, fld.name, fld.default)
        for k in kw.keys():
            if not hasattr(self, k): ValueError("Invalid column name '%s'." % k)
            setattr(self, k, kw[k])

    @classmethod
    def _factory(cls, cur, row):
        h = dict([[d[0], row[i]] for i, d in enumerate(cur.description)])
        return cls(**h)

    @classmethod
    def get(cls, where, values=None):
        """Getting single result by ID"""
        return QuerySet(cls).get(where, values)

    @classmethod
    def select(cls, where, values):
        """Getting QuerySet instance by WHERE clause"""
        return QuerySet(cls).select(where, values)

    @classmethod
    def create(cls, **kw):
        """Creating new record"""
        names = []
        obj = cls(**kw)
        for fld in cls._meta.fields:
            if fld.is_primary_key and not getattr(obj, fld.name): continue
            names.append(fld.name)
        obj.before_create()
        obj.before_save()
        values = [getattr(obj, n) for n in names]
        holder = ", ".join(["?"] * len(names))
        sql = "INSERT INTO %s (%s) VALUES (%s)" % (cls._table_name, ", ".join(names), holder)
        cur = cls._meta.conn.cursor().execute(sql, values)
        newobj = cls.get(cur.lastrowid)
        for fld in cls._meta.fields: setattr(obj, fld.name, getattr(newobj, fld.name))
        return obj

    def save(self):
        """Updating the record"""
        cls = self.__class__
        names = []
        for fld in cls._meta.fields:
            if fld.is_primary_key: continue
            names.append(fld.name)
        holder = ", ".join(["%s = ?" % n for n in names])
        self.before_save()
        values = [getattr(self, n) for n in names]
        sql = "UPDATE %s SET %s WHERE %s = ?" % (cls._table_name, holder, cls._meta.primary_key.name)
        cls._meta.conn.cursor().execute(sql, values + [self.get_id()])

    def delete(self):
        """Deleting the record"""
        cls = self.__class__
        sql = "DELETE FROM %s WHERE %s = ?" % (cls._table_name, cls._meta.primary_key.name)
        cls._meta.conn.cursor().execute(sql, [self.get_id()])

    def get_id(self):
        """Getting value of primary key field"""
        return getattr(self, self.__class__._meta.primary_key.name)

    def before_create(self): pass
    def before_save(self): pass

    def __repr__(self):
        return "<%s object %s>" % (self.__class__.__name__, self.get_id())

class MacaronPlugin(object):
    """Macaron plugin for Bottle web framework
    This plugin handled Macaron.
    """
    name = "macaron"
    api = 2

    def __init__(self, dbfile=":memory:", autocommit=True):
        self.dbfile = dbfile
        self.autocommit = autocommit

    def setup(self, app): pass

    def apply(self, callback, ctx):
        conf = ctx.config.get("macaron") or {}
        dbfile = conf.get("dbfile", self.dbfile)
        autocommit = conf.get("autocommit", self.autocommit)

        def wrapper(*args, **kwargs):
            macaronage(dbfile=dbfile, lazy=True)
            try:
                ret_value = callback(*args, **kwargs)
                if autocommit: bake()   # commit
            except sqlite3.IntegrityError, e:
                rollback()
                raise HTTPError(500, "Database Error", e)
            finally:
                db_close()
            return ret_value
        return wrapper

# This is a module global variable '_m' having Macaron object.
_m = Macaron()
