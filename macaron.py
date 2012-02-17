# -*- coding: utf-8 -*-
"""
*Macaron* is a small and simple object-relational mapper (ORM) for SQLite and
Python. It is distributed as a single file module which has no dependencies
other than the Python Standard Library.

*Macaron* provides easy access methods to SQLite database. And it supports
Bottle web framework through plugin mechanism.

Example::

    >>> import macaron
    >>> macaron.macaronage("members.db")
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
    >>> macaron.bake()
    >>> macaron.cleanup()
"""
__author__ = "Nobuo Okazaki"
__version__ = "0.2.1-dev"
__license__ = "MIT License"

import sqlite3, re
import copy
import logging
import datetime

# --- Exceptions
class ObjectDoesNotExist(Exception): pass
class ValidationError(Exception): pass      # TODO: fix behavior

# --- Module global attributes
_m = None       # Macaron object
history = None  #: Returns history of SQL execution. You can get history like a list (index:0 is latest).

# --- Module methods
def macaronage(dbfile=":memory:", lazy=False, autocommit=False, logger=None, history=-1):
    """
    :param dbfile: SQLite database file name.
    :param lazy: Uses :class:`LazyConnection`.
    :param autocommit: Commits automatically when closing database.
    :param logger: Uses for logging SQL execution.
    :param history: Set max count of SQL execution history (0 is unlimited, -1 is disabled).
                    Default: disabled
    :type logger: :class:`logging.Logger`

    Initializes macaron.
    This sets Macaron instance to module global variable *_m* (don't access directly).
    If *lazy* is ``True``, :class:`LazyConnection` object is used for connection, which
    will connect to the DB when using. If *autocommit* is ``True``, this will commits
    when this object will be unloaded.
    """
    globals()["_m"] = Macaron()
    globals()["history"] = ListHandler(-1)
    conn = None
    if history >= 0: # enable history logger
        logger = logger or logging.getLogger()
        logger.setLevel(logging.DEBUG)
        globals()["history"].set_max_count(history)
        logger.addHandler(globals()["history"])
    if lazy: conn = LazyConnection(dbfile, factory=_create_wrapper(logger))
    else: conn = sqlite3.connect(dbfile, factory=_create_wrapper(logger))
    if not conn: raise Exception("Can't create connection.")
    _m.connection["default"] = conn
    _m.autocommit = autocommit

def execute(*args, **kw):
    """Wrapper for ``Cursor#execute()``."""
    return _m.connection["default"].cursor().execute(*args, **kw)

def bake():
    """Commits the database."""
    _m.connection["default"].commit()

def rollback():
    """Rollbacks the database."""
    _m.connection["default"].rollback()

def cleanup():
    """Closes database and tidies up Macaron"""
    _m = None

# --- Classes
class Macaron(object):
    """Macaron controller class. Do not instance this class by user."""
    def __init__(self):
        #: ``dict`` object holds :class:`sqlite3.Connection`
        self.connection = {}
        self.used_by = []
        self.sql_logger = None

    def __del__(self):
        """Closing the connections"""
        while len(self.used_by):
            # Removes reference pointer from TableMetaClassProperty.
            # If the pointer leaved, closing connection causes mismatch
            # between TableMetaClassProperty#table_meta and Macaron#connection,
            # like test cases.
            self.used_by.pop(0).table_meta = None

        for k in self.connection.keys():
            if self.autocommit: self.connection[k].commit()
            self.connection[k].close()

    def get_connection(self, meta_obj):
        self.used_by.append(meta_obj)
        return self.connection[meta_obj.conn_name]

# --- Connection wrappers
def _create_wrapper(logger):
    class ConnectionWrapper(sqlite3.Connection):
        def cursor(self):
            self.logger = logger
            return super(ConnectionWrapper, self).cursor(CursorWrapper)
    return ConnectionWrapper

class CursorWrapper(sqlite3.Cursor):
    """Subclass of sqlite3.Cursor for logging"""
    def execute(self, sql, parameters=[]):
        if self.connection.logger:
            self.connection.logger.debug("%s\nparams: %s" % (sql, str(parameters)))
        if(isinstance(history, ListHandler)):
            history.lastsql = sql
            history.lastparams = parameters
        return super(CursorWrapper, self).execute(sql, parameters)

class LazyConnection(object):
    """Lazy connection wrapper"""
    def __init__(self, *args, **kw):
        self.args = args
        self.kwargs = kw
        self._conn = None

    def __getattr__(self, name):
        if not self._conn and (name in ["commit", "rollback", "close"]): return self.noop
        self._conn = self._conn or sqlite3.connect(*self.args, **self.kwargs)
        return getattr(self._conn, name)

    def noop(self): return

# --- Logging
class ListHandler(logging.Handler):
    """SQL history listing handler for ``logging``.

       :param max_count: max count of SQL history (0 is unlimited, -1 is disabled)
    """
    def __init__(self, max_count=100):
        logging.Handler.__init__(self, logging.DEBUG)
        self.lastsql = None
        self.lastparams = None
        self._max_count = max_count
        self._list = []

    def emit(self, record):
        if self._max_count < 0: return
        if self._max_count > 0:
            while len(self._list) >= self._max_count: self._list.pop()
        self._list.insert(0, record.getMessage())

    def _get_max_count(self): return self._max_count

    def set_max_count(self, max_count):
        self._max_count = max_count
        if max_count > 0:
            while len(self._list) > self._max_count: self._list.pop()
    max_count = property(_get_max_count)

    def count(self): return len(self._list)
    def __getitem__(self, idx):
        if self._max_count < 0:
            raise RuntimeError("SQL history is disabled. Use macaronage() with 'history' parameter.")
        if len(self._list) <= idx: raise IndexError("SQL history max_count is %d." % len(self._list))
        return self._list.__getitem__(idx)

# --- Table and field information
class FieldInfoCollection(list):
    """FieldInfo collection"""
    def __init__(self):
        self._field_dict = {}

    def append(self, fld):
        super(FieldInfoCollection, self).append(fld)
        self._field_dict[fld.name] = fld

    def __getitem__(self, name): return self._field_dict[name]

class FieldInfo(object):
    """Field information class

       :param row: tuple got from 'PRAGMA table_info(``table_name``)'
       :type row: tuple

       .. attribute:: cid
                      name
                      type
                      not_null
                      default
                      is_primary_key
    """
    def __init__(self, row):
        self.cid, self.name, self.type, \
            self.not_null, self.default, self.is_primary_key = row
        self.converter = None
        if re.match(r"^BOOLEAN$", self.type, re.I):
            self.default = bool(re.match(r"^TRUE$", self.default, re.I))

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
            self.table_meta = TableMetaInfo(_m.get_connection(self), self.table_name)
        return self.table_meta

class TableMetaInfo(object):
    """Table information class.
    This object has table information, which is set to ModelClass._meta by
    :class:`ModelMeta`. If you use ``Bookmark`` class, you can access the
    table information with ``Bookmark._meta``.
    """
    def __init__(self, conn, table_name):
        self._conn = conn   # Connection for the table
        #: Table fields collection
        self.fields = FieldInfoCollection()
        #: Primary key :class:`Field`
        self.primary_key = None
        #: Table name
        self.table_name = table_name
        cur = conn.cursor()
        rows = cur.execute("PRAGMA table_info(%s)" % table_name).fetchall()
        for row in rows:
            fld = FieldInfo(row)
            self.fields.append(FieldInfo(row))
            if fld.is_primary_key: self.primary_key = fld

# --- Relationships
class ManyToOne(property):
    """Many to one relation ship definition class"""
    def __init__(self, ref, related_name=None, fkey=None, ref_key=None):
        # in this state, db has been not connected!
        self.ref = ref                      #: reference table ('one' side)
        self.fkey = fkey                    #: foreign key name ('many' side)
        self.ref_key = ref_key              #: reference key ('one' side)
        self.related_name = related_name    #: accessor name for one to many relation

    def __get__(self, owner, cls):
        reftbl = self.ref._meta.table_name
        clstbl = cls._meta.table_name
        self.fkey = self.fkey or "%s_id" % self.ref._meta.table_name
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
        self.related_name = self.related_name or "%s_set" % rev_cls.__name__.lower()
        setattr(self.ref, self.related_name, _ManyToOne_Rev(self.ref, self.ref_key, rev_cls, self.fkey))

class _ManyToOne_Rev(property):
    """The reverse of many to one relationship."""
    def __init__(self, ref, ref_key, rev, rev_fkey):
        self.ref = ref              # Reference table (parent)
        self.ref_key = ref_key      # Key column name of parent
        self.rev = rev              # Child table (many side)
        self.rev_fkey = rev_fkey    # Foreign key name of child

    def __get__(self, owner, cls):
        self.rev_fkey = self.rev_fkey or "%s_id" % self.ref._meta.table_name
        self.ref_key = self.ref_key or self.ref._meta.primary_key.name
        qs = self.rev.select("%s = ?" % self.rev_fkey, [getattr(owner, self.ref_key)])
        return ManyToOneRevSet(qs, owner, self)

# --- QuerySet
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
        except StopIteration:
            raise self.cls.DoesNotExist("%s object is not found." % cls.__name__)
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

# --- BaseModel
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
        """Convert raw values to object"""
        h = dict([[d[0], row[i]] for i, d in enumerate(cur.description)])
        for fld in cls._meta.fields:
            if hasattr(cls, fld.name) and isinstance(getattr(cls, fld.name), Field):
                h[fld.name] = getattr(cls, fld.name).to_object(sqlite3.Row(cur, row), h[fld.name])
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
        Model._before_before_store(obj, "set", AtCreate)            # set value
        obj.before_create()
        obj.validate()
        Model._before_before_store(obj, "to_database", Field)   # convert object to database
        values = [getattr(obj, n) for n in names]
        holder = ", ".join(["?"] * len(names))
        sql = "INSERT INTO %s (%s) VALUES (%s)" % (cls._meta.table_name, ", ".join(names), holder)
        cls._save_and_update_object(obj, sql, values)
        obj.after_create()
        return obj

    def save(self):
        """Updating the record"""
        cls = self.__class__
        names = []
        for fld in cls._meta.fields:
            if fld.is_primary_key: continue
            names.append(fld.name)
        holder = ", ".join(["%s = ?" % n for n in names])
        Model._before_before_store(self, "set", AtSave) # set value
        self.validate()
        self.before_save()
        Model._before_before_store(self, "to_database", Field)  # convert object to database
        values = [getattr(self, n) for n in names]
        sql = "UPDATE %s SET %s WHERE %s = ?" % (cls._meta.table_name, holder, cls._meta.primary_key.name)
        cls._save_and_update_object(self, sql, values + [self.pk])
        self.after_save()

    @staticmethod
    def _save_and_update_object(obj, sql, values):
        cls = obj.__class__
        cur = cls._meta._conn.cursor().execute(sql, values)
        if obj.pk == None: current_id = cur.lastrowid
        else: current_id = obj.pk
        newobj = cls.get(current_id)
        for fld in cls._meta.fields: setattr(obj, fld.name, getattr(newobj, fld.name))

    def delete(self):
        """Deleting the record"""
        cls = self.__class__
        sql = "DELETE FROM %s WHERE %s = ?" % (cls._meta.table_name, cls._meta.primary_key.name)
        cls._meta._conn.cursor().execute(sql, [self.pk])

    @staticmethod
    def _before_before_store(obj, meth_name, at_cls):
        cls = obj.__class__
        # set value with at_cls object
        for fld in filter(lambda f: hasattr(cls, f.name), cls._meta.fields):
            if isinstance(getattr(cls, fld.name), at_cls):
                converter = getattr(getattr(cls, fld.name), meth_name)
                setattr(obj, fld.name, converter(cls, getattr(obj, fld.name)))

    def validate(self):
        cls = self.__class__
        for fld in filter(lambda f: hasattr(cls, f.name), cls._meta.fields):
            if isinstance(getattr(cls, fld.name), Field):
                value = getattr(self, fld.name)
                if not getattr(cls, fld.name).validate(self, value):
                    raise ValidationError("%s.%s is invalid value. '%s'" % (cls.__name__, fld.name, str(value)))

    # These hooks are triggered at Model.create() and Model#save().
    # Model.create(): before_create -> INSERT -> after_create
    # Model#save()  : bofore_save -> UPDATE -> after_save
    def before_create(self): pass   # Called before INSERT
    def before_save(self): pass     # Called before UPDATE
    def after_create(self): pass    # Called after INSERT
    def after_save(self): pass      # Called after UPDATE

    def __repr__(self):
        return "<%s object %s>" % (self.__class__.__name__, self.pk)

# --- Field converting and validation
class Field(object):
    def set(self, obj, value): return value         # sets value
    def to_database(self, obj, value): return value # convert object to database
    def to_object(self, row, value): return value   # convert object from database
    def validate(self, obj, value): return True     # validate

    def __add__(self, other):
        def chain(a, b):
            def _chain(*args, **kw): return b(a(*args, **kw))
            return _chain
        def sequential_validation(a, b):
            def _sequential(obj, value):
                if a.validate(obj, value) and b.validate(obj, value): return True
                raise ValidationError(obj, value)
            return _sequential
        self.set = other.set
        self.to_database = chain(self.to_database, other.to_database)
        self.to_object = chain(self.to_object, other.to_object)
        self.validate = sequential_validation(self, other)

class AtCreate(Field): pass
class AtSave(Field): pass
class NowAtCreate(AtCreate):
    def set(self, obj, value): return datetime.datetime.now()
class NowAtSave(AtCreate, AtSave):
    def set(self, obj, value): return datetime.datetime.now()

class NumberField(Field):
    def __init__(self, max=None, min=None):
        self.max, self.min = max, min
    def validate(self, obj, value):
        if self.max != None and value > self.max: raise ValidationError("Max value is exceeded.")
        if self.min != None and value < self.min: raise ValidationError("Min value is underrun.")
        return True

class IntegerField(Field):
    def validate(self, obj, value):
        if not isinstance(value, (int, long)): raise ValidationError("Not integer.")
        return super(IntegerField, self).validate(obj, value)

class CharField(Field):
    def __init__(self, max_length=None):
        self.max_length = max_length
    def validate(self, obj, value):
        if self.max_length and len(value) > self.max_length: raise ValidationError("Text is too long.")
        if self.min_length and len(value) < self.min_length: raise ValidationError("Text is too short.")

# --- Aggregation functions
class AggregateFunction(object):
    def __init__(self, field_name): self.field_name = field_name
class Avg(AggregateFunction):   name = "AVG"
class Max(AggregateFunction):   name = "MAX"
class Min(AggregateFunction):   name = "MIN"
class Sum(AggregateFunction):   name = "SUM"
class Count(AggregateFunction): name = "COUNT"

# --- Plugin for Bottle web framework
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

        import traceback as tb
        def wrapper(*args, **kwargs):
            macaronage(dbfile, lazy=True)
            try:
                ret_value = callback(*args, **kwargs)
                if autocommit: bake()   # commit
            except sqlite3.IntegrityError, e:
                rollback()
                try:
                    import bottle
                    traceback = None
                    if bottle.DEBUG:
                        traceback = (history.lastsql, history.lastparams)
                        sqllog = "[Macaron]LastSQL: %s\n[Macaron]Params : %s\n" % traceback
                        bottle.request.environ["wsgi.errors"].write(sqllog)
                    raise bottle.HTTPError(500, "Database Error", e, tb.format_exc())
                except ImportError:
                    raise e
            return ret_value
        return wrapper

