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
__version__ = "0.2.0"
__license__ = "MIT License"

import sqlite3
import re
import copy

# --- Exceptions
class ObjectDoesNotExist(Exception): pass

# --- Module methods
def macaronage(dbfile=":memory:", lazy=False, connection=None, autocommit=False):
    """Initializes macaron.
    This sets Macaron instance to module global variable *_m* (don't access directly).
    If *lazy* is ``True``, :class:`LazyConnection` object is used for connection, which
    will connect to the DB when using. If *autocommit* is ``True``, this will
    commits when this object will be unloaded.
    """
    globals()["_m"] = Macaron()
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
    """Executes ``sqlite3.Cursor#execute()``.
    This calls ``sqlite3.Cursor#execute()``.
    """
    return _m.connection["default"].cursor().execute(*args, **kw)

def bake():
    """Commits the database."""
    _m.connection["default"].commit()

def rollback(): _m.connection["default"].rollback()
def db_close(): _m.connection["default"].close()

# Classes
class Macaron(object):
    """Macaron controller class. Do not instance this class by user."""
    def __init__(self):
        #: ``dict`` object holds :class:`sqlite3.Connection`
        self.connection = {}
        self.used_by = []

    def __del__(self):
        """Closing the connections"""
        while len(self.used_by):
            # Removes reference pointer from TableMetaClassProperty.
            # If the pointer leaved, closing connection causes mismatch
            # between TableMetaClassProperty#table_meta and Macaron#connection,
            # like test cases.
            self.used_by.pop(0).table_meta = None

        for k in self.connection.keys():
            self.connection[k].close()

    def get_connection(self, meta_obj):
        self.used_by.append(meta_obj)
        return self.connection[meta_obj.conn_name]

class LazyConnection(object):
    """Lazy connection wrapper"""
    def __init__(self, *args, **kw):
        self.args = args
        self.kwargs = kw
        self._conn = None

    def __getattr__(self, name):
        self._conn = self._conn or sqlite3.connect(*self.args, **self.kwargs)
        return getattr(self._conn, name)

    def commit(self):   return
    def rollback(self): return
    def close(self):    return

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

class AggregateFunction(object):
    def __init__(self, field_name): self.field_name = field_name
class Avg(AggregateFunction):   name = "AVG"
class Max(AggregateFunction):   name = "MAX"
class Min(AggregateFunction):   name = "MIN"
class Sum(AggregateFunction):   name = "SUM"
class Count(AggregateFunction): name = "COUNT"

class ClassProperty(property):
    """Using class property wrapper class"""
    def __get__(self, owner_obj, cls):
        return self.fget.__get__(owner_obj, cls)()

class TableMetaClassProperty(property):
    """Using TableMetaInfo class property wrapper class"""
    def __init__(self):
        super(TableMetaClassProperty, self).__init__()
        self.table_meta = None
        self.table_name = None
        self.conn_name = "default"  #: for future use. multiple databases?

    def __get__(self, owner_obj, cls):
        if not self.table_meta:
            conn = _m.get_connection(self)
            self.table_meta = TableMetaInfo(conn, self.table_name)
#            self.table_meta = TableMetaInfo(_m.connection[self.conn_name], self.table_name)
        return self.table_meta

class TableMetaInfo(object):
    """Table information class.
    This object has table information, which is set to ModelClass._meta by
    :class:`ModelMeta`. If you use ``Bookmark`` class, you can access the
    table information with ``Bookmark._meta``.
    """
    def __init__(self, conn, table_name):
        self._conn = conn   #: Connection for the table
        #: Table fields collection
        self.fields = Fields()
        #: Primary key :class:`Field`
        self.primary_key = None
        #: Table name
        self.table_name = table_name
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
        reftbl = self.ref._meta.table_name
        clstbl = cls._meta.table_name
        self.ref_key = self.ref_key or self.ref._meta.primary_key.name
        sql = "SELECT %s.* FROM %s LEFT JOIN %s ON %s = %s.%s WHERE %s.%s = ?" \
            % (reftbl, clstbl, reftbl, self.fkey, reftbl, self.ref_key, \
               clstbl, cls._meta.primary_key.name)
        cur = cls._meta._conn.cursor()
        cur = cur.execute(sql, [owner.pk])
        row = cur.fetchone()
        if cur.fetchone(): raise ValueError()
        return self.ref._factory(cur, row)

    def set_reverse(self, rev_cls):
        """Sets up one to many definition method.
        This method will be called in ``ModelMeta#__init__``. To inform the
        model class to ManyToOne and _ManyToOne_Rev classes. The *rev_class*
        means **'many(child)' side class**.
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
            self.clauses = {"where": [], "order_by": [], "values": [], "distinct": False}
        self.clauses["offset"] = 0
        self.clauses["limit"] = 0
        self.clauses["select_fields"] = "*"
        self.factory = self.cls._factory    # Factory method converting record to object
        self._initialize_cursor()

    def _initialize_cursor(self):
        """Cleaning cache and state"""
        self.cur = None     # cursor
        self._index = -1    # pointer
        self._cache = []    # cache list

    def _generate_sql(self):
        if self.clauses["distinct"]: distinct = "DISTINCT "
        else: distinct = ""
        sqls = ["SELECT %s%s FROM %s" % (distinct, self.clauses["select_fields"], self.cls._meta.table_name)]
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
        self.cur = self.cls._meta._conn.cursor().execute(self.sql, self.clauses["values"])

    def __iter__(self):
        self._execute()
        return self

    def next(self):
        if not self.cur: self._execute()
        row = self.cur.fetchone()
        self._index += 1
        if not row: raise StopIteration()
        self._cache.append(self.factory(self.cur, row))
        return self._cache[-1]

    def get(self, where, values=None):
        if values == None:
            values = [where]
            where = "%s = ?" % self.cls._meta.primary_key.name
        qs = self.select(where, values)
        try: obj = qs.next()
        except StopIteration: raise self.cls.DoesNotExist()
        try: qs.next()
        except StopIteration: return obj
        raise ValueError("Returns more rows.")

    def select(self, where=None, values=[]):
        newset = self.__class__(self)
        if where: newset.clauses["where"].append(where)
        if values: newset.clauses["values"] += values
        return newset

    def all(self):
        return self.select()

    def distinct(self):
        """EXPERIMENTAL:
        I don't know what situation this distinct method is used in.
        """
        newset = self.__class__(self)
        newset.clauses["distinct"] = True
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

    # Aggregation methods
    def aggregate(self, agg):
        def single_value(cur, row): return row[0]
        newset = self.__class__(self)
        newset.clauses["select_fields"] = "%s(%s)" % (agg.name, agg.field_name)
        newset.factory = single_value   # Change factory method for single value
        return newset.next()

    def count(self):
        return self.aggregate(Count("*"))

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

class ModelMeta(type):
    """Meta class for Model class"""
    def __new__(cls, name, bases, dict):
        dict["DoesNotExist"] = type("DoesNotExist", (ObjectDoesNotExist,), {})
        dict["_meta"] = TableMetaClassProperty()
        dict["_meta"].table_name = dict.pop("_table_name", name.lower())
        return type.__new__(cls, name, bases, dict)

    def __init__(instance, name, bases, dict):
        for k in dict.keys():
            if isinstance(dict[k], ManyToOne):
                dict[k].set_reverse(instance)

class Model(object):
    """Base model class.
    Models inherit the class.
    """
    __metaclass__ = ModelMeta
    _table_name = None  #: Database table name (the property will be deleted in ModelMeta)
    _meta = None        #: accessor for TableMetaInfo (set in ModelMeta)

    def __init__(self, **kw):
        cls = self.__class__
        for fld in cls._meta.fields: setattr(self, fld.name, fld.default)
        for k in kw.keys():
            if not hasattr(self, k): ValueError("Invalid column name '%s'." % k)
            setattr(self, k, kw[k])

    def get_key_value(self):
        """Getting value of primary key field"""
        return getattr(self, self.__class__._meta.primary_key.name)
    pk = property(get_key_value)    #: accessor for primary key value

    @classmethod
    def _factory(cls, cur, row):
        h = dict([[d[0], row[i]] for i, d in enumerate(cur.description)])
        return cls(**h)

    @classmethod
    def get(cls, where, values=None):
        """Getting single result by ID"""
        return QuerySet(cls).get(where, values)

    @classmethod
    def all(cls):
        return QuerySet(cls).select()

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
        sql = "INSERT INTO %s (%s) VALUES (%s)" % (cls._meta.table_name, ", ".join(names), holder)
        cur = cls._meta._conn.cursor().execute(sql, values)
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
        sql = "UPDATE %s SET %s WHERE %s = ?" % (cls._meta.table_name, holder, cls._meta.primary_key.name)
        cls._meta._conn.cursor().execute(sql, values + [self.pk])

    def delete(self):
        """Deleting the record"""
        cls = self.__class__
        sql = "DELETE FROM %s WHERE %s = ?" % (cls._meta.table_name, cls._meta.primary_key.name)
        cls._meta._conn.cursor().execute(sql, [self.pk])

    # These hooks are triggered at INSERT and UPDATE.
    # INSERT: before_create -> before_save -> INSERT
    # UPDATE: bofore_save -> UPDATE
    def before_create(self):
        """Hook for before INSERT"""
        pass

    def before_save(self):
        """Hook for before INSERT and UPDATE"""
        pass

    def __repr__(self):
        return "<%s object %s>" % (self.__class__.__name__, self.pk)

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
_m = None
