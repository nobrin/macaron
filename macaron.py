# -*- coding: utf-8 -*-
"""
Macaron is a small object-relational mapper (ORM) for SQLite on Python.
It is distributed as a single file module which has no dependencies other
than the Python Standard Library.

Macaron provides easy access way to SQLite database as standalone. And also
it can work in Bottle web framework through the plugin mechanism.

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
__version__ = "0.4.0-dev"
__license__ = "MIT License"

import sqlite3, re, sys
import copy, warnings
import logging
import collections
from datetime import datetime

PY3K = sys.version_info.major >= 3

# --- Exceptions
class ObjectDoesNotExist(Exception): pass
class ValidationError(Exception): pass      # TODO: fix behavior
class DefaultValueValidationError(ValidationError): pass
class MultipleObjectsReturned(Exception): pass
class NotUniqueForeignKey(Exception): pass
class DataTableDoesNotExist(Exception): pass
class DataTableAlreadyExists(Exception): pass

# for NOT NULL query
class NotNull(object): pass

# for LIKE query
class Like(object):
    def __init__(self, s):
        self.likestr = s

# --- Module global attributes
_m = None               # Macaron object
_pre_field_order = []   # Created order of Model field object
history = None          #: Returns history of SQL execution. You can get history like a list (index:0 is latest).
SQL_TRACE_OUT = None    # In case of tracing SQL and parameters on CursorWrapper, set output stream(ex. sys.stderr)
sqlite_version_info = sqlite3.sqlite_version_info

#_callbacks_when_connect = [] # TEMPORARY BUG FIX: see the comment of ModelMeta.__init__()

# --- Module methods
def macaronage(dbfile=":memory:", lazy=False, autocommit=False, logger=None, history=-1, keep=False, threading=False, regexp=None):
    """
    :param dbfile: SQLite database file name.
    :param lazy: Uses :class:`LazyConnection`.
    :param autocommit: Commits automatically when closing database.
    :param logger: Uses for logging SQL execution.
    :param history: Sets max count of SQL execution history (0 is unlimited, -1 is disabled).
                    Default: disabled
    :param keep: keep previous object and connection (EXPERIMENTAL)
    :type logger: :class:`logging.Logger`

    Initializes macaron.
    This sets Macaron instance to module global variable *_m* (don't access directly).
    If ``lazy`` is ``True``, :class:`LazyConnection` object is used for connection, which
    will connect to the DB when using. If ``autocommit`` is ``True``, this will commits
    when this object will be unloaded.
    """
    if keep and globals()["_m"]: return
    globals()["_m"] = Macaron()
    globals()["history"] = ListHandler(-1)
    conn = None
    if history >= 0: # enable history logger
        logger = logger or logging.getLogger()
        logger.setLevel(logging.DEBUG)
        globals()["history"].set_max_count(history)
        logger.addHandler(globals()["history"])
    # To avoid sqlite3.ProgrammingError in checking same thread, specify 'check_same_thread' False.
    # This suppress the message when apache2 is shuting down, below.
    #   Exception sqlite3.ProgrammingError: 'SQLite objects created in a thread can only be used
    #   in that same thread.The object was created in thread id -1249404048 and this is thread
    #   id -1221678384' in <bound method Macaron.__del__ of <macaron.Macaron object at 0xb4a93eec>> ignored
    # But this is NOT a fundamental solution...Maybe.
    # About threadsafety of sqlite3: http://www.sqlite.org/threadsafe.html
    if lazy: conn = LazyConnection(dbfile, factory=_create_wrapper(logger), check_same_thread=(not threading))
    else: conn = sqlite3.connect(dbfile, factory=_create_wrapper(logger), check_same_thread=(not threading))
    if not conn: raise Exception("Can't create connection.")

    # Set REGEXP function
    if regexp is None:
        def _regexp(expr, item):
            try: return re.search(expr, item) is not None
            except Exception as e: raise
    elif callable(regexp):
        _regexp = regexp
    else:
        raise ValueError("regexp must be 'default' or function.")
    conn.create_function("REGEXP", 2, _regexp)

    _m.connection["default"] = conn
    _m.autocommit = autocommit

    # TEMPORARY BUG FIX: see the comment of ModelMeta.__init__()
    # For fetching column info only.
#    for callback in _callbacks_when_connect:
#        try: callback()
#        except: pass

def execute(*args, **kw):
    """Wrapper for ``Cursor#execute()``."""
    return _m.connection["default"].cursor().execute(*args, **kw)

def bake():     _m.connection["default"].commit()   # Commits
def rollback(): _m.connection["default"].rollback() # Rollback
def cleanup():
    """Closes database and tidies up the Macaron object"""
    _m.connection["default"].close()
    globals()["_m"] = None

def create_table(cls, cascade=False, link_tables=True):
    """Create table from Model class"""
    if not issubclass(cls, Model): raise TypeError("The first arg must be Model class, not '%s'." % cls.__name__)

    # Check if table exists.
    table_name = cls.__dict__["_meta"].table_name
    cur = execute("SELECT * FROM sqlite_master WHERE type = 'table' AND name = ?", [table_name])
    if cur.fetchall():
        raise cls.TableAlreadyExists("Table '%s' already exists in database." % cls._meta.table_name)

    # Process Field and ManyToOne objects, which are defined by user
    cdic = cls.__dict__ # for direct access to property objects
    field_order = {}
    has_primary_key = False
    # 2021-05-29: ManyToOne to self object causes 'RuntimeError: dictionary changed size during iteration'
    # To avoid it, list the iteration before loop.
    for k, fld in list(filter(lambda x: isinstance(x[1], Field), cdic.items())):
        if not fld.is_user_defined: continue
        if isinstance(fld, ManyToOne):
            meta = None
            # The reference table exists or not.
            while not meta:
                try: meta = fld.ref._meta; break
                except fld.ref.TableDoesNotExist as e:
                    if not cascade: raise e
                    else: create_table(fld.ref)
            # Generate REFERENCES clause
            refkey = fld.ref_key or meta.primary_key.name
            sql  = 'REFERENCES "%s"("%s")' % (meta.table_name, refkey)
            if fld.on_delete: sql += " ON DELETE %s" % fld.on_delete
            if fld.on_update: sql += " ON UPDATE %s" % fld.on_update
            fld.name = fld.fkey or "%s_id" % meta.table_name
            fld.type = meta.fields[refkey].type
            fld.extra_sql = sql
        else:
            fld.name = k
            if fld.is_primary_key: has_primary_key = True
        field_order[_pre_field_order.index(fld)] = fld

    # Create primary key field if not exists
    field_clauses = []
    if not has_primary_key:
        fld = IntegerField(primary_key=True)
        fld.name = "id"
        field_clauses.append(fld.field_clause())

    # Generate CREATE TABLE clause and execute
    for k in sorted(field_order.keys()): field_clauses.append(field_order[k].field_clause())
    sql  = 'CREATE TABLE "%s" (\n  %s' % (cdic["_meta"].table_name, ",\n  ".join(field_clauses))
    if cdic["_meta"].unique_together: sql += ',\n  UNIQUE ("%s")' % '", "'.join(cdic["_meta"].unique_together)
    sql += "\n)"
    execute(sql)
    _m.connection["default"].cache_table_info(cdic["_meta"].table_name, warn=False)

    if link_tables:
        create_link_tables(cls)

def create_link_tables(cls):
    cdic = cls.__dict__ # for direct access to property objects
    # Avoid for RuntimeError: dictionary changed size during iteration,
    # convert cdic.items() to list
    for k, fld in filter(lambda x: isinstance(x[1], ManyToMany), list(cdic.items())):
        create_table(fld.lnk)

# --- Classes
class Macaron(object):
    """Macaron controller class. Do not instantiate this class by user."""
    def __init__(self):
        #: ``dict`` object holds :class:`sqlite3.Connection`
        self.connection = {}
        self.used_by = []
        self.sql_logger = None

    def __del__(self):
        """Closing the connections"""
        while len(self.used_by):
            # Removes references from TableMetaClassProperty.
            # If the pointer leaved, closing connection causes status mismatch
            # between TableMetaClassProperty#table_meta and Macaron#connection.
            self.used_by.pop(0).table_meta = None

        for k in self.connection.keys():
            if self.autocommit: self.connection[k].commit()
            self.connection[k].close()

        _field_order = []

    def get_connection(self, meta_obj):
        """Returns Connection and adds reference to the object which uses it."""
        self.used_by.append(meta_obj)
        return self.connection[meta_obj.conn_name]

# --- Connection wrappers
def _create_wrapper(logger):
    """Returns ConnectionWrapper class"""
    class ConnectionWrapper(sqlite3.Connection):
        def __init__(self, *args, **kw):
            super(ConnectionWrapper, self).__init__(*args, **kw)
            self.execute("PRAGMA foreign_keys = ON")    # fkey support ON (SQLite>=3.6.19)
            self.warn_pragma = True

            # Cache results of PRAGMA table_info() for TRANSACTION
            self.table_info = {}
            cur = self.execute("SELECT * FROM sqlite_master WHERE type = 'table'")
            for rec in cur:
                self.cache_table_info(rec[2], warn=False)

        def cursor(self):
            self.logger = logger
            return super(ConnectionWrapper, self).cursor(CursorWrapper)

        def cache_table_info(self, table_name, warn=True):
            if self.warn_pragma and warn:
                raise UserWarning("Execution of PRAGMA table_info(%s) will break TRANSACTION." % table_name)
#            else:
#                print 'PRAGMA table_info("%s")' % table_name
            cur = self.execute('PRAGMA table_info("%s")' % table_name)
            self.table_info[table_name] = cur.fetchall()
            return self.table_info[table_name][:]

        def get_table_info(self, table_name):
            if table_name in self.table_info: return self.table_info[table_name][:]
            return self.cache_table_info(table_name)

    return ConnectionWrapper

class CursorWrapper(sqlite3.Cursor):
    """Subclass of sqlite3.Cursor for logging"""
    def execute(self, sql, parameters=[]):
        if self.connection.logger:
            self.connection.logger.debug("%s\nparams: %s" % (sql, str(parameters)))
        if(isinstance(history, ListHandler)):
            history.lastsql = sql
            history.lastparams = parameters
        if SQL_TRACE_OUT:
            SQL_TRACE_OUT.write("[macaron:SQL  ]:%s\n" % sql)
            SQL_TRACE_OUT.write("[macaron:PARAM]:%s\n" % str(parameters))
        try:
            return super(CursorWrapper, self).execute(sql, parameters)
        except:
            sys.stderr.write("[macaron:Error in SQL  ]\n%s\n" % sql)
            sys.stderr.write("[macaron:Error in PARAM]\n%s\n" % str(parameters))
            raise

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

    def noop(self): return  # NO-OP for commit, rollback, close

# --- Logging
class ListHandler(logging.Handler):
    """SQL history listing handler for ``logging``.

       :param max_count: max count of SQL history (0 is unlimited, -1 is disabled)
    """
    class _SQLParamTracer(object):
        def __init__(self, msg):
            m = re.match(r"(?P<sql>.+)\nparams: (?P<params>.+)", msg, re.MULTILINE + re.DOTALL)
            if not m: raise RuntimeError("Invalid message format. '%s'" % msg)
            self.sql = m.group("sql")
            self.param_str = m.group("params")
        def __str__(self): return "%s\nparams: %s" % (self.sql, self.param_str)
        def __unicode__(self): return u"%s\nparams: %s" % (self.sql, self.param_str)

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
        self._list.insert(0, self._SQLParamTracer(record.getMessage()))

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
    def __init__(self): self._field_dict = {}

    def append(self, fld):
        super(FieldInfoCollection, self).append(fld)
        self._field_dict[fld.name] = fld

    def __getitem__(self, name):
        if isinstance(name, int):
            return super(FieldInfoCollection, self).__getitem__(name)
        return self._field_dict[name]

    def keys(self): return self._field_dict.keys()

    def __in__(self, name): return name in self._field_dict

class ClassProperty(property):
    """Using class property wrapper class"""
    def __get__(self, owner_obj, cls): return self.fget.__get__(owner_obj, cls)()

class FieldFactory(object):
    @staticmethod
    def create(row, cls):
        rec = dict(zip(["cid", "name", "type", "not_null", "default", "is_primary_key"], row))
        cdict = cls.__dict__
        if rec["name"] in cdict and not isinstance(cdict[rec["name"]], Field):
            raise TypeError("Fields must be Field objects.")
        if rec["name"] in cdict and cdict[rec["name"]].is_user_defined:
            fld = cls.__dict__[rec["name"]]
        else:
            fldkw = {"null": not rec["not_null"], "primary_key": rec["is_primary_key"]}
            use_field_class = Field
            for fldcls in TYPE_FIELDS:
                if filter(lambda s:re.search(s, row[2]), fldcls.TYPE_NAMES):
                    use_field_class = fldcls
                    break
            fld = use_field_class(**fldkw)
        fld.cid, fld.name, fld.type = row[0:3]
        fld.initialize_after_meta()
        # convert default from 'PRAGMA table_info()'.
        if fld.default == None and rec["default"] != None:
            fld.default = fld.cast(rec["default"])
        setattr(cls, rec["name"], fld)
        return fld

class TableMetaClassProperty(property):
    """Using TableMetaInfo class property wrapper class"""
    def __init__(self):
        super(TableMetaClassProperty, self).__init__()
        self.table_meta = None
        self.table_name = None
        self.conn_name = "default"  #: for future use. multiple databases?

    def __get__(self, owner_obj, cls):
        if not self.table_meta:
            self.table_meta = TableMetaInfo(_m.get_connection(self), self.table_name, cls)
        return self.table_meta

class TableMetaInfo(object):
    """Table information class.
    This object has table information, which is set to ModelClass._meta by
    :class:`ModelMeta`. If you use ``Bookmark`` class, you can access the
    table information with ``Bookmark._meta``.
    This mechanism is for collecting information after initialization of all of models.
    """
    def __init__(self, conn, table_name, cls):
        self._conn = conn                   #: Connection for the table
        self.fields = FieldInfoCollection() #: Table fields collection
        self.primary_key = None             #: Primary key :class:`Field`
        self.table_name = table_name        #: Table name

        # To avoid duplicated definition of class field.
        # Initial fields are specified in _meta.initial_field
        field_order = {}
#        for name, fld in cls.__dict__.items():
#            if not isinstance(fld, Field): continue
        for name, fld in cls.__dict__["_meta"].initial_field.items():
            field_order[_pre_field_order.index(fld)] = fld
            fld.name = name

        # --- TEMPORARY BUG FIX ---
        for idx in sorted(field_order.keys()):
            fld = field_order[idx]
            if isinstance(fld, ManyToOne):
                # In case of ManyToOne field, the actual field of the one is set into the class.
                # ex. author ManyToOne field corresponds to author_id IntegerField.
                if fld.fkey not in cls.__dict__:
                    reffld = None
                    for f in filter(lambda v:isinstance(v, Field), fld.ref.__dict__.values()):
                        if f.is_primary_key: reffld = f
                    if isinstance(reffld, IntegerField): fkey = IntegerField(null=fld.null)
                    assert fkey, "Foreign key must be Integer"
                    setattr(cls, fld.fkey, fkey)
                else:
                    fkey = cls.__dict__[fld.fkey]
                fkey.name = fld.fkey
                self.fields.append(fkey)
                if not isinstance(cls.__dict__[fld.fkey], Field):
                    fmt = "%s.%s will be used for ManyToOne foreign key field. You must use other name."
                    raise TypeError(fmt % (self.__class__.__name__, fld.fkey))
            else:
                self.fields.append(fld)
            if fld.is_primary_key: self.primary_key = fld

#        cur = conn.cursor()
#        rows = conn.get_table_info(table_name)
#        if not len(rows): raise cls.TableDoesNotExist()
#        for row in rows:
#            fld = FieldFactory.create(row, cls)
#            self.fields.append(fld)
#            if fld.is_primary_key: self.primary_key = fld

# --- Field converting and validation
class Field(property):
    SQL_TYPE = "UNKNOWN"
    VALUE_TYPE = "CHAR" # CHAR or NUM for quotation
    is_user_defined = False

    def __init__(self, null=False, default=None, primary_key=False, unique=False, extra_sql=""):
        self.name, self.type = None, self.SQL_TYPE
        self.null, self.default, self.unique = null, default, unique
        self.is_primary_key = primary_key
        self.extra_sql = extra_sql
        _pre_field_order.append(self)

    def cast(self, value): return value
    def set(self, obj, value): return value
    def to_database(self, obj, value): return value
    def to_object(self, row, value): return value
    def initialize_after_meta(self): pass

    def validate(self, obj, value):
        if not self.null and value == None:
            raise ValidationError("Field '%s' does not accept None value." % self.name)
        return True

    def __get__(self, owner_obj, cls): return owner_obj._data.get(self.name, None)
    def __set__(self, owner_obj, value):
        self.validate(self, value)
        owner_obj._data[self.name] = self.cast(value)

    def field_clause(self):
        if self.type == Field.SQL_TYPE:
            warnings.warn("'%s'.type is '%s'." % (self.__class__.__name__, Field.SQL_TYPE))
        a = ['"%s"' % self.name, self.type]
        if self.is_primary_key: a.append("PRIMARY KEY")
        if not self.null: a.append("NOT NULL")
        if self.unique: a.append("UNIQUE")
        if self.default is not None:
            try: self.validate(None, self.default)
            except ValidationError as e:
                raise DefaultValueValidationError("Invalid default value: %s" % e)
            if self.VALUE_TYPE == "CHAR": a.append("DEFAULT '%s'" % str(self.default).replace("'", "''"))
            elif self.VALUE_TYPE == "NUM": a.append("DEFAULT %s" % self.default)
            else: raise ValueError("%s.VALUE_TYPE must be 'CHAR' or 'NUM'." % self.__class__.__name__)
        if self.extra_sql: a.append(self.extra_sql)
        return " ".join(a)

class AtCreate(Field): pass
class AtSave(Field): pass

class TimestampField(Field):
    TYPE_NAMES = (r"^TIMESTAMP$", r"^DATETIME$")
    SQL_TYPE = "TIMESTAMP"
    def to_database(self, obj, value):
        if value is None: return None
        return value.strftime("%Y-%m-%d %H:%M:%S")
    def to_object(self, row, value):
        if value is None: return None
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")

class DateField(Field):
    TYPE_NAMES = (r"^DATE$",)
    SQL_TYPE = "DATE"
    def to_database(self, obj, value):
        if value is None: return None
        return value.strftime("%Y-%m-%d")
    def to_object(self, row, value):
        if value is None: return None
        return datetime.strptime(value, "%Y-%m-%d").date()

class TimeField(Field):
    TYPE_NAMES = (r"^TIME$",)
    SQL_TYPE = "TIME"
    def to_database(self, obj, value):
        if value is None: return None
        return value.strftime("%H:%M:%S")
    def to_object(self, row, value):
        if value is None: return None
        return datetime.strptime(value, "%H:%M:%S").time()

class TimestampAtCreate(TimestampField, AtCreate):
    def __init__(self, **kw):
        kw["null"] = True
        super(TimestampAtCreate, self).__init__(**kw)
    def set(self, obj, value): return datetime.now()

class DateAtCreate(DateField, AtCreate):
    def __init__(self, **kw):
        kw["null"] = True
        super(DateAtCreate, self).__init__(**kw)
    def set(self, obj, value): return datetime.now().date()

class TimeAtCreate(TimeField, AtCreate):
    def __init__(self, **kw):
        kw["null"] = True
        super(TimeAtCreate, self).__init__(**kw)
    def set(self, obj, value): return datetime.now().time()

class TimestampAtSave(TimestampAtCreate, AtSave): pass
class DateAtSave(DateAtCreate, AtSave): pass
class TimeAtSave(TimeAtCreate, AtSave): pass

class FloatField(Field):
    TYPE_NAMES = ("REAL", "FLOA", "DOUB")
    SQL_TYPE = "FLOAT"
    VALUE_TYPE = "NUM"

    def __init__(self, max=None, min=None, **kw):
        super(FloatField, self).__init__(**kw)
        self.max, self.min = max, min
        self.type = self.SQL_TYPE

    def cast(self, value):
        if value == None: return None
        return float(value)

    def validate(self, obj, value):
        super(FloatField, self).validate(obj, value)
        if value == None: return True
        try: self.cast(value)
        except (ValueError, TypeError):
            raise ValidationError("Field '%s': Value must be a number, not '%s' [%s]." % (self.name, type(value).__name__, value))
        if self.max != None and value > self.max:
            raise ValidationError("Field '%s': Max value is exceeded. [%d]" % (self.name, value))
        if self.min != None and value < self.min:
            raise ValidationError("Field '%s': Min value is underrun. [%d]" % (self.name, value))
        return True

class IntegerField(FloatField):
    TYPE_NAMES = ("INT",)
    SQL_TYPE = "INTEGER"

#    def initialize_after_meta(self):
#        if re.match(r"^INTEGER$", self.type, re.I) and self.is_primary_key: self.null = True

    def cast(self, value):
        if value == None: return None
        return int(value)

    def validate(self, obj, value):
        super(IntegerField, self).validate(obj, value)
        if value == None: return True
        try: self.cast(value)
        except (ValueError, TypeError):
            raise ValidationError("Field '%s': Value must be an integer, not '%s' [%s]." % (type(value).__name__, value))
        return True

class SerialKeyField(IntegerField):
    def __init__(self, primary_key=True, null=True, **kw):
        super(SerialKeyField, self).__init__(primary_key=primary_key, null=null, **kw)

class CharField(Field):
    TYPE_NAMES = ("CHAR", "CLOB", "TEXT")
    def __init__(self, max_length=None, min_length=None, length=None, **kw):
        super(CharField, self).__init__(**kw)
        self.max_length, self.min_length = max_length, min_length
        self.length = length
        if self.length and not self.max_length: self.max_length = self.length
        self._type = None

    def _get_sql_type(self):
        if self._type: return self._type
        if self.length: return "CHAR(%d)" % self.length
        if self.max_length: return "VARCHAR(%d)" % self.max_length
        return "TEXT"
    def _set_sql_type(self, value): self._type = value
    type = property(_get_sql_type, _set_sql_type)

    def initialize_after_meta(self):
        m = re.search(r"CHAR\s*\((\d+)\)", self.type, re.I)
        if m and (not self.max_length or self.max_length > int(m.group(1))):
            self.max_length = int(m.group(1))

    def validate(self, obj, value):
        super(CharField, self).validate(obj, value)
        if value == None: return True
        if self.max_length and len(value) > self.max_length:
            raise ValidationError("Field '%s': Text is too long, max_length=%d [%s]." % (self.name, self.max_length, value))
        if self.min_length and len(value) < self.min_length:
            raise ValidationError("Field '%s': Text is too short, min_length=%d [%s]." % (self.name, self.min_length, value))
        return True

class MatchingField(CharField):
    def __init__(self, pattern, **kw):
        super(MatchingField, self).__init__(**kw)
        self.pattern = pattern

    def validate(self, obj, value):
        super(MatchingField, self).validate(obj, value)
        if value == None: return True
        if not re.match(self.pattern, value):
            raise ValidationError("Field '%s': Text does not match patern." % self.name)
        return True

# --- Relationships
class ManyToOne(Field):
    """Many to one relation ship definition class"""
    def __init__(self, ref, related_name=None, fkey=None, ref_key=None, on_delete=None, on_update=None, **kw):
        # in this state, db has been not connected!
        super(ManyToOne, self).__init__(**kw)
        self.ref = ref                      #: reference table ('one' side)
        self.fkey = fkey                    #: foreign key name ('many' side)
        self._ref_key = ref_key             #: primary key of reference table ('one' side)
        self.related_name = related_name    #: accessor name for one to many relation
        self.on_delete = on_delete
        self.on_update = on_update
        _pre_field_order.append(self)

    def set_query(self, query_set, tblname, name):
        h = {
            "reftbl": self.ref._meta.table_name,
            "refkey": self.ref_key,
            "clstbl": tblname,
            "clskey": self.fkey,
            "fldname": "%s.%s" % (tblname, name)
        }
        tmpl = 'INNER JOIN "%(reftbl)s" AS "%(fldname)s" ON "%(clstbl)s"."%(clskey)s" = "%(fldname)s"."%(refkey)s"'
        query_set.clauses["joins"].append(tmpl % h)
        return self.ref, h["fldname"]

    def _get_ref_key(self):
        self._ref_key = self._ref_key or self.ref._meta.primary_key.name
        assert self._ref_key, "Primary key name of '%s' can't be specified." % self.ref.__name__
        return self._ref_key
    ref_key = property(_get_ref_key)

    def __get__(self, owner, cls):
        if getattr(owner, self.fkey) is None: return None
        reftbl = self.ref._meta.table_name
        clstbl = cls._meta.table_name
#        sql = 'SELECT "%s".* FROM "%s" LEFT JOIN "%s" ON "%s" = "%s"."%s" WHERE "%s"."%s" = ?' \
#            % (reftbl, clstbl, reftbl, self.fkey, reftbl, self.ref_key, \
#               clstbl, cls._meta.primary_key.name)
        sql = 'SELECT * FROM "%s" WHERE "%s" = ?' % (reftbl, self.ref_key)
        cur = cls._meta._conn.cursor()
#        cur = cur.execute(sql, [owner.pk])
        cur = cur.execute(sql, [getattr(owner, self.fkey)])
        row = cur.fetchone()
        if cur.fetchone(): raise NotUniqueForeignKey("Reference key '%s.%s' is not unique." % (reftbl, self.ref_key))
        return self.ref._factory(cur, row)

    def __set__(self, owner, value):
        if value and not isinstance(value, self.ref):
            raise TypeError("This is related to '%s', not '%s'." % (self.ref.__name__, value.__class__.__name__))
        if value is None: v = None
        else: v = getattr(value, self.ref_key)
        setattr(owner, self.fkey, v)

    def _called_in_modelmeta_init(self, rev_cls, fld_name):
        """Sets up one-to-many definition method.
        This method will be called in ``ModelMeta#__init__``. To inform the
        model class to ManyToOne and _ManyToOne_Rev classes. The *rev_class*
        means **'many(child)' side class**.
        """
        # If self.ref is string and the class have not been initialized,
        # initializing the relationship is suspended.
        if isinstance(self.ref, str):
            if not hasattr(sys.modules[rev_cls.__module__], self.ref):
                type(rev_cls).suspended[self.ref] = (self, rev_cls, fld_name)
                return
            self.ref = getattr(sys.modules[rev_cls.__module__], self.ref)

        self.name = fld_name    # set field name
        if not self.fkey: self.fkey = "%s_id" % self.name
        assert self.name, "ManyToOne#name couldn't be specified."
        assert self.fkey, "ManyToOne#fkey couldn't be specified."
        self.related_name = self.related_name or "%s_set" % rev_cls.__name__.lower()

        setattr(self.ref, self.related_name, _ManyToOne_Rev(self.ref, self._ref_key, rev_cls, self.fkey))

class _ManyToOne_Rev(property):
    """The reverse of many-to-one relationship (i.e. 'one' side)."""
    def __init__(self, ref, ref_key, rev, rev_fkey):
        self.ref = ref              # Reference table (parent)
        self._ref_key = ref_key     # Key column name of parent
        self.rev = rev              # Child table (many side)
        self.rev_fkey = rev_fkey    # Foreign key name of child
        assert self.rev_fkey, "Foreign key was not specified in ManyToOne#_called_in_modelmeta_init"

    def set_query(self, query_set, tblname, name):
        # Generate INNER JOIN-ed clause
        h = {
            "revtbl": self.rev._meta.table_name,
            "revkey": self.rev_fkey,
            "reftbl": tblname,
            "refkey": self.ref_key,
            "fldname": "%s.%s" % (tblname, name),
        }
        tmpl = 'INNER JOIN "%(revtbl)s" AS "%(fldname)s" ON "%(reftbl)s"."%(refkey)s" = "%(fldname)s"."%(revkey)s"'
        query_set.clauses["joins"].append(tmpl % h)
        return self.rev, h["fldname"]

    def _get_ref_key(self):
        self._ref_key = self._ref_key or self.ref._meta.primary_key.name
        assert self._ref_key, "Primary key name of '%s' can't be specified." % self.ref.__name__
        return self._ref_key
    ref_key = property(_get_ref_key)

    def __get__(self, owner, cls):
        qs = self.rev.select("%s = ?" % self.rev_fkey, [getattr(owner, self.ref_key)])
        return ManyToOneRevSet(qs, owner, self)

# --- Many-to-many relationship
class _ManyToManyBase(property):
    def __init__(self, ref, name=None, lnk=None, cls=None):
        self.ref = ref
        self.lnk = lnk
        self.cls = cls
        self.name = name

    def _get_link_class(self):
        if (PY3K and isinstance(self._lnk, (str, bytes))) or (not PY3K and isinstance(self._lnk, basestring)):
            self._lnk = getattr(sys.modules[self.cls.__module__], self._lnk)
        return self._lnk
    def _set_link_class(self, value): self._lnk = value
    lnk = property(_get_link_class, _set_link_class)

    def __get__(self, owner, cls):
        qs = cls.select('"%s"."%s"=?' % (cls._meta.table_name, cls._meta.primary_key.name), [owner.pk])
        return ManyToManySet(qs, owner, self.ref, self.lnk)

class ManyToMany(_ManyToManyBase):
    def __init__(self, ref, related_name=None, lnk=None):
        super(ManyToMany, self).__init__(ref, lnk=lnk)
        self.related_name = related_name

    def set_query(self, query_set, tblname, name):
        h = {
            "clstbl": tblname,
            "clskey": self.cls._meta.primary_key.name,
            "reftbl": self.ref._meta.table_name,
            "refkey": self.ref._meta.primary_key.name,
            "lnktbl": self.lnk._meta.table_name,
            "fldname": "%s.%s" % (tblname, name),
        }
        h["lnkclskey"] = "%s_id" % self.cls._meta.table_name
        h["lnkrefkey"] = "%s_id" % h["reftbl"]
        query_set.clauses["joins"].append(
            'INNER JOIN "%(lnktbl)s" AS "%(fldname)s.lnk" ON "%(clstbl)s"."%(clskey)s" = "%(fldname)s.lnk"."%(lnkclskey)s"' % h
        )
        query_set.clauses["joins"].append(
            'INNER JOIN "%(reftbl)s" AS "%(fldname)s" ON "%(fldname)s.lnk"."%(lnkrefkey)s" = "%(fldname)s"."%(refkey)s"' % h
        )
        return self.ref, h["fldname"]

    def _called_in_modelmeta_init(self, cls, fld_name):
        # This method will be called in ModelMeta#__init__().
        # When called, module have not been initialized completely.
        # For that we may not get class, self._lnk has class name as string.
        self.cls = cls
        self.name = fld_name
        if self._lnk is None: self._lnk = self.generate_link_class()
        self.related_name = self.related_name or "%s_set" % cls.__name__.lower()
        setattr(self.ref, self.related_name, _ManyToManyBase(cls, name=self.related_name, lnk=self._lnk, cls=self.ref))

    def generate_link_class(self):
        name = "%s%sLink" % (self.cls.__name__, self.ref.__name__)
        h = {
            self.cls.__name__.lower(): ManyToOne(self.cls, on_delete="CASCADE", on_update="CASCADE"),
            self.ref.__name__.lower(): ManyToOne(self.ref, on_delete="CASCADE", on_update="CASCADE"),
        }
        cls = type(name, (Model,), h)
        return type(name, (Model,), h)

# --- QuerySet
class QuerySet(object):
    """This class generates SQL which like QuerySet in Django"""
    def __init__(self, parent):
        if isinstance(parent, QuerySet):
            self.cls = parent.cls
            self.clauses = copy.deepcopy(parent.clauses)
            self.factory = parent.factory   # Factory method converting record to object
            self.wrapper_clause = parent.wrapper_clause
        else:
            self.cls = parent
            self.clauses = {"type":"SELECT", "joins":[], "where":[], "order_by":[], "values":[], "distinct":False}
            self.clauses["offset"] = None
            self.clauses["limit"] = None
            self.clauses["order_by"] = self._convert_order_fields(parent.__dict__["_meta"].ordering)
            self.factory = self.cls._factory
            self.clauses["select_fields"] = '"%s".*' % self.cls.__dict__["_meta"].table_name
            self.wrapper_clause = None
        self.parent = parent
        self._initialize_cursor()

    def _initialize_cursor(self):
        """Cleaning cache and state"""
        self.cur = None     # cursor
        self._index = -1    # pointer
        self._cache = []    # cache list

    def _generate_sql(self):
        # To delete: wrapper_clause is set to DELETE...
        if self.clauses["distinct"]: distinct = "DISTINCT "
        else: distinct = ""

        sqls = ['SELECT %s%s FROM "%s"' % (distinct, self.clauses["select_fields"], self.cls._meta.table_name)]

        if len(self.clauses["joins"]): sqls += self.clauses["joins"]

        if len(self.clauses["where"]):
            sqls.append("WHERE %s" % " AND ".join(["(%s)" % c for c in self.clauses["where"]]))

        if len(self.clauses["order_by"]):
            sqls.append('ORDER BY %s' % ', '.join(self.clauses["order_by"]))
        if self.clauses["limit"] is not None: sqls.append("LIMIT %d" % self.clauses["limit"])
        if self.clauses["offset"] is not None: sqls.append("OFFSET %d" % self.clauses["offset"])

        if self.wrapper_clause:
            return self.wrapper_clause % "\n".join(sqls)

        return "\n".join(sqls)

    sql = property(_generate_sql)   #: Generating SQL

    def _execute(self):
        """Getting and setting a new cursor"""
        self._initialize_cursor()
        self.cur = self.cls._meta._conn.cursor().execute(self.sql, self.clauses["values"])

    def _convert_order_fields(self, fields):
        """Convert order ['-id', 'name'] to ['"id" DESC', '"name"']"""
        def conv(m):
            fldname = m.group(1)
            res = '"%s"."%s"' % (m.group(1), m.group(2))
            fld = self.cls.__dict__.get(fldname, "None")
            if not fld: return res
#            h = {"as":fldname, "me":self.cls._meta.table_name, "me_key":self.cls._meta.primary_key.name}
            h = {"as":fldname, "me":self.cls._meta.table_name, "me_key":fld.fkey}
            if isinstance(fld, ManyToOne):
                h["ref"] = fld.ref._meta.table_name
                h["refkey"] = fld.ref_key
            elif isinstance(fld, _ManyToOne_Rev):
                self.clauses["distinct"] = True
                h["ref"] = fld.rev._meta.table_name
                h["refkey"] = fld.rev_fkey
            else: return res
            fmt = 'INNER JOIN "%(ref)s" AS "%(as)s" ON "%(me)s"."%(me_key)s" = "%(as)s"."%(refkey)s"'
            self.clauses["joins"].append(fmt % h)
            return res

        res = []
        for n in fields:
            desc = ""
            if n.startswith("-"): n, desc = n[1:], " DESC"
            if re.match(r"(\w+)\.(\w+)", n): n = re.sub(r"(\w+)\.(\w+)", conv, n)
            else: n = '"%s"' % n
            res.append('%s%s' % (n, desc))
        return res

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
    __next__ = next

    def get(self, *args, **kw):
        if len(args) == 1:
            args = ('"%s" = ?' % self.cls._meta.primary_key.name, args[0])
        qs = self.select(*args, **kw)
        try: obj = qs.next()
        except StopIteration: raise self.cls.DoesNotExist("%s object is not found." % self.cls.__name__)
        try: qs.next()
        except StopIteration: return obj
        raise MultipleObjectsReturned("The 'get()' requires single result.")

    def select(self, *args, **kw):
        newset = self.__class__(self)
        if len(args) == 1:
            newset.clauses["where"].append(args[0])
        elif len(args) == 2:
            newset.clauses["where"].append(args[0])
            if isinstance(args[1], (list, tuple)): newset.clauses["values"] += list(args[1])
            else: newset.clauses["values"].append(args[1])
        elif len(args) > 2:
            raise RuntimeError("arg1 must be primary key value or arg1, arg2 must be where and values.")

        # Parse keywords
        for k, v in kw.items():
            curmdl = self.cls
            curname = self.cls._meta.table_name

            if isinstance(v, Model):
                # Specified with Model object
                k += "__%s" % v._meta.primary_key.name
                v = v.pk

            items = k.split("__")
            while items:
                item = items.pop(0)
                fld = curmdl.__dict__[item]
                if callable(getattr(fld, "set_query", None)):
                    # Fields of ManyToOne, _ManyToOne_Rev, ManyToMany
                    curmdl, curname = fld.set_query(newset, curname, item)
                elif isinstance(fld, Field):
                    break
                else:
                    raise RuntimeError("Invalid column name. '%s(%s)'" % (item, fld.__class__.__name__))

            # Convert field name and value
            if len(items) >= 2:
                raise RuntimeError("Invalid operand name. '%s'" % "__".join(items))

            # Parsing inline operator
            opc = OpConverter(curname)
            whr, prm = opc.get_clause(items[0] if items else None, fld, v)
            newset.clauses["where"].append(whr)
            if prm is not None:
                if isinstance(prm, (list, tuple)): newset.clauses["values"] += list(prm)
                else: newset.clauses["values"].append(prm)

        return newset

    def all(self):
        return self.select()

    def delete(self):
        self.clauses["type"] = "DELETE"
        h = {"tbl": self.cls._meta.table_name, "pk": self.cls._meta.primary_key.name}
        self.wrapper_clause = 'DELETE FROM "%(tbl)s" WHERE "%(pk)s" IN (SELECT "%(pk)s" FROM (\n%%s\n))' % h
        self._execute()

    def distinct(self):
        newset = self.__class__(self)
        newset.clauses["distinct"] = True
        return newset

    def order_by(self, *args):
        newset = self.__class__(self)
#        newset.clauses["order_by"] += [re.sub(r"^-(.+)$", r"\1 DESC", n) for n in args]
        newset.clauses["order_by"] += newset._convert_order_fields(args)
        return newset

    def limit(self, limit):
        newset = self.__class__(self)
        newset.clauses["limit"] = int(limit)
        return newset

    def offset(self, offset):
        newset = self.__class__(self)
        newset.clauses["offset"] = int(offset)
        newset.clauses["limit"] = -1    # When only offset is set, SQL syntax error is caused.
        return newset

    def __getitem__(self, index):
        newset = self.__class__(self)
        if isinstance(index, slice):
            if index.step != 1 and index.step is not None:
                raise ValueError("Step of slice except 1 is not supported.")
            start, stop = index.start or 0, index.stop
            newset.clauses["offset"] = (newset.clauses["offset"] or 0) + start
            if stop is None:
                newset.clauses["limit"] = -1
            else:
                if stop < start:
                    raise ValueError("Slice stop must be larger than start value.[start:%d,stop:%d]" % (start, stop))
                else: newset.clauses["limit"] = stop - start
            return newset
        elif self._index >= index: return self._cache[index]
        for obj in self:
            if self._index >= index: return obj

    # Aggregation methods
    def aggregate(self, agg):
        """Aggregation

        Aggregate use 'wrapper_clause':
            SELECT COUNT("*") FROM (
            [original clause]
            )
        """
        def single_value(cur, row): return row[0]
        newset = self.__class__(self)
#        newset.clauses["select_fields"] = '%s("%s")' % (agg.name, agg.field_name)
        newset.wrapper_clause = 'SELECT %s("%s") FROM (\n%%s\n)' % (agg.name, agg.field_name)
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
        """Append a new member"""
        kw[self.cls_fkey] = getattr(self.parent, self.parent_key)
        return self.cls.create(*args, **kw)

class ManyToManySet(QuerySet):
    def __init__(self, parent_query, parent_object=None, ref=None, lnk=None):
        super(ManyToManySet, self).__init__(parent_query)
        # When call on slice procedure of QuerySet, return
        if not(parent_object and ref and lnk): return

        self.parent = parent_object
        self.ref = ref
        self.lnk = lnk
        clstbl, cls_id = self.cls._meta.table_name, self.cls._meta.primary_key.name
        reftbl, ref_id = ref._meta.table_name, ref._meta.primary_key.name
        lnktbl, lnkcls_id, lnkref_id = lnk._meta.table_name, "%s_id" % clstbl, "%s_id" % reftbl
        self.clauses["select_fields"] = '"%s".*' % reftbl
        self.clauses["joins"] = [
            'INNER JOIN "%s" ON "%s"."%s" = "%s"' % (lnktbl, clstbl, cls_id, lnkcls_id),
            'INNER JOIN "%s" ON "%s" = "%s"."%s"' % (reftbl, lnkref_id, reftbl, ref_id),
        ]
        self.factory = ref._factory

    def append(self, *args, **kw):
        if len(args):
            if not isinstance(args[0], self.ref):
                raise TypeError("Object must be '%s', not '%s'." % (self.ref.__name__, type(args[0]).__name__))
            h = {
                "%s_id" % self.cls.__name__.lower(): self.parent.pk,
                "%s_id" % self.ref.__name__.lower(): args[0].pk,
            }
            self.lnk.create(**h)
            return args[0]
        obj = self.ref.create(**kw)
        return self.append(obj)

    def pop(self, refobj):
        """Pop many-to-many link object"""
        h = {
            "%s_id" % self.cls.__name__.lower(): self.parent.pk,
            "%s_id" % self.ref.__name__.lower(): refobj.pk,
        }
        self.lnk.select(**h).delete()
        return refobj

    def clear(self):
        self.lnk.select(**{"%s_id" % self.cls.__name__.lower(): self.parent.pk}).delete()

# --- BaseModel and Model class
class ModelMeta(type):
    """Meta class for Model class"""
    suspended = {}
    def __new__(cls, name, bases, dict):
        dict["DoesNotExist"] = type("DoesNotExist", (ObjectDoesNotExist,), {})
        dict["TableDoesNotExist"] = type("TableDoesNotExist", (DataTableDoesNotExist,), {})
        dict["TableAlreadyExists"] = type("TableAlreadyExists", (DataTableAlreadyExists,), {})
        dict["_meta"] = TableMetaClassProperty()
        dict["_meta"].table_name = dict.pop("_table_name", name.lower())
        dict["_meta"].unique_together = dict.pop("_unique_together", [])
        dict["_meta"].ordering = dict.pop("_ordering", [])
        dict["_meta"].initial_field = {}
        for k, v in dict.items():
            if isinstance(v, Field): dict["_meta"].initial_field[k] = v
        return type.__new__(cls, name, bases, dict)

    def __init__(cls, name, bases, dict):
        # Process suspended initializing
        # 2021-05-29: This process shoud be conducted after next block
        """
        if cls.__name__ in ModelMeta.suspended:
            p = ModelMeta.suspended.pop(cls.__name__)
            p[0].ref = cls
            p[0]._called_in_modelmeta_init(p[1], p[2])
        """

        has_primary_key = False
        for k in dict.keys():
            if isinstance(dict[k], ManyToMany): dict[k]._called_in_modelmeta_init(cls, k)
            if isinstance(dict[k], ManyToOne): dict[k]._called_in_modelmeta_init(cls, k)
            if isinstance(dict[k], Field): dict[k].is_user_defined = True
            if isinstance(dict[k], Field) and dict[k].is_primary_key: has_primary_key = True

        # 2021-05-29
        # move to here.
        if cls.__name__ in ModelMeta.suspended:
            p = ModelMeta.suspended.pop(cls.__name__)
            p[0].ref = cls
            p[0]._called_in_modelmeta_init(p[1], p[2])

        if not has_primary_key:
            fld = SerialKeyField() # for Serial key
            cls.id = fld
            _pre_field_order.pop(_pre_field_order.index(fld))
            _pre_field_order.insert(0, fld)
            dict["_meta"].initial_field["id"] = fld

        # TEMPORARY BUG FIX:
        # 'PRAGMA' is used in a transaction, it brakes the transaction.
        # PRAGMA is used in the constructor of TableMetaInfo class for fetching table column info
        # to generate Model columns. To detect auto-generated columns (ex. id) may need the
        # mechanism.
        # Now, to put a band-aid on that stuff, generate cls._meta immediately after connect.
#        if cls.__dict__["_meta"].table_name:
#            if not _m: _callbacks_when_connect.append(lambda: cls._meta)
#            else: raise UserWarning("PRAGMA will brake the transaction.")

# This hack is use metaclass in both py2 and py3.
# - ref. https://qiita.com/podhmo/items/c601050b20f70d27aa07
HasModelMeta = ModelMeta("Model", (object,), {"__doc__": ModelMeta.__doc__})

class Model(HasModelMeta):
    """Base model class. Models must inherit this class."""
#    __metaclass__ = ModelMeta
    _table_name = None  #: Database table name (the property will be deleted in ModelMeta)
    _meta = None        #: accessor for TableMetaInfo (set in ModelMeta)
                        #  Accessing to _meta triggers initializing TableMetaInfo and Class attributes.
    def __init__(self, **kw):
        self._data = {}
        for fld in self.__class__._meta.fields: self._data[fld.name] = fld.default
        for k in kw.keys():
            if (k not in self.__class__._meta.fields.keys()) \
                    and not isinstance(self.__class__.__dict__[k], Field):
                raise ValueError("Invalid column name '%s'." % k)
            setattr(self, k, kw[k])
        self._orig_pk = self.pk # Preserve original primary key value for modifing key value

    def __eq__(self, other): return self.pk == other.pk

    def get_key_value(self):
        """Getting value of primary key field"""
        return getattr(self, self.__class__._meta.primary_key.name)
    pk = property(get_key_value)    #: accessor for primary key value

    @classmethod
    def _factory(cls, cur, row):
        """Convert raw values to object"""
        h1 = dict([[d[0], row[i]] for i, d in enumerate(cur.description)])
        h2 = {} # for create a new model object
        for fld in cls._meta.fields:
            h2[fld.name] = fld.to_object(sqlite3.Row(cur, row), h1[fld.name])
        return cls(**h2)

    @classmethod
    def select_from(cls, sql, params=()):
        objs = []
        cur = execute(sql, params)
        for row in cur.fetchall(): objs.append(cls._factory(cur, row))
        return objs

    @classmethod
    def get(cls, *args, **kw): return QuerySet(cls).get(*args, **kw)

    @classmethod
    def all(cls): return QuerySet(cls).select()

    @classmethod
    def select(cls, *args, **kw): return QuerySet(cls).select(*args, **kw)

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
        sql = 'INSERT INTO "%s" ("%s") VALUES (%s)' % (cls._meta.table_name, '", "'.join(names), holder)
        cls._save_and_update_object(obj, sql, values)
        obj.after_create()
        return obj

    def save(self):
        """Updating the record"""
        cls = self.__class__
        names = []
        for fld in cls._meta.fields:
#            if fld.is_primary_key: continue
            names.append(fld.name)
        holder = ", ".join(['"%s" = ?' % n for n in names])
        Model._before_before_store(self, "set", AtSave) # set value
        self.validate()
        self.before_save()
        Model._before_before_store(self, "to_database", Field)  # convert object to database
        values = [getattr(self, n) for n in names]
        sql = 'UPDATE "%s" SET %s WHERE "%s" = ?' % (cls._meta.table_name, holder, cls._meta.primary_key.name)
        cls._save_and_update_object(self, sql, values + [self._orig_pk]) # '_orig_pk' is preserved key value (see __init__)
        self.after_save()

    @staticmethod
    def _save_and_update_object(obj, sql, values):
        cls = obj.__class__
        cur = cls._meta._conn.cursor().execute(sql, values)
        if obj.pk == None: current_id = cur.lastrowid
        else: current_id = obj.pk
        newobj = cls.get(current_id)
        for fld in cls._meta.fields: setattr(obj, fld.name, getattr(newobj, fld.name))
        obj._orig_pk = obj.pk

    def delete(self):
        """Deleting the record"""
        cls = self.__class__
        sql = 'DELETE FROM "%s" WHERE "%s" = ?' % (cls._meta.table_name, cls._meta.primary_key.name)
        cls._meta._conn.cursor().execute(sql, [self.pk])

    @staticmethod
    def _before_before_store(obj, meth_name, at_cls):
        cls = obj.__class__
        # set value with at_cls object
        for fld in cls._meta.fields:
            if isinstance(fld, at_cls):
                converter = getattr(fld, meth_name)
                setattr(obj, fld.name, converter(obj, getattr(obj, fld.name)))

    def validate(self):
        cls = self.__class__
        for fld in cls._meta.fields:
            value = getattr(self, fld.name)
            if not fld.validate(self, value):
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

    def __unicode__(self): return u"<%s object %s>" % (self.__class__.__name__, self.pk)
    def __str__(self):
        if PY3K: return "<%s object %s>" % (self.__class__.__name__, self.pk)
        return unicode(self).encode("utf-8")

# --- Aggregation functions
class AggregateFunction(object):
    def __init__(self, field_name): self.field_name = field_name
class Avg(AggregateFunction):   name = "AVG"
class Max(AggregateFunction):   name = "MAX"
class Min(AggregateFunction):   name = "MIN"
class Sum(AggregateFunction):   name = "SUM"
class Total(AggregateFunction): name = "TOTAL"
class Count(AggregateFunction): name = "COUNT"

# --- Converter for operators
class OpConverter(object):
    CONV = {
        "lt": "<", "le": "<=", "ge": ">=", "gt": ">",
        "like": "LIKE", "glob": "GLOB", "regexp": "REGEXP",
    }
    def __init__(self, tblname): self.tblname = tblname

    def get_clause(self, op, fld, value):
        if op:
            if hasattr(self, "_OP_%s" % op): sqltmpl, value = getattr(self, "_OP_%s" % op)(value)
            elif op in self.CONV: sqltmpl, value = "%%s %s ?" % self.CONV[op], value
            else: raise ValueError("Operator '%s' is not supported." % op)
        else:
            sqltmpl, value = self._convert(fld, value)
        return sqltmpl % '"%s"."%s"' % (self.tblname, fld.name), value

    def _base_in(self, op, value): return "%%s %s (%s)" % (op, ",".join(["?"] * len(value))), value
    def _OP_in(self, value): return self._base_in("IN", value)
    def _OP_not_in(self, value): return self._base_in("NOT IN", value)

    def _base_between(self, op, value):
        if not isinstance(value, collections.Iterable): raise TypeError("Between operator requires a list")
        if len(value) != 2: raise ValueError("Between operator requires a list which consists of 2 values.")
        return "%%s %s ? AND ?" % op, value
    def _OP_between(self, value): return self._base_between("BETWEEN", value)
    def _OP_not_between(self, value): return self._base_between("NOT BETWEEN", value)

    def _convert(self, fld, value):
        if value is None:           return "%s IS NULL", None
        if value is NotNull:        return "%s IS NOT NULL", None
        if isinstance(value, Like): return "%s LIKE ?", value.likestr
        return "%s = ?", fld.to_database(None, value)

# --- Plugin for Bottle web framework
class MacaronPlugin(object):
    """Bottle plugin for Macaron"""
    name = "macaron"
    api = 2

    def __init__(self, dbfile=":memory:", commit_on_success=True):
        self.dbfile = dbfile
        self.commit_on_success = commit_on_success

    def setup(self, app):
        # 'macaronage' when MacaronPlugin is installed
        macaronage(self.dbfile, lazy=True, autocommit=False)

    def apply(self, callback, ctx):
        conf = ctx.config.get("macaron") or {}
#       dbfile = conf.get("dbfile", self.dbfile)
#       commit_on_success = conf.get("commit_on_success", self.commit_on_success)
        import traceback as tb
        import bottle
        def wrapper(*args, **kwargs):
#           macaronage(dbfile, lazy=True, autocommit=False, keep=True)
            try:
                ret_value = callback(*args, **kwargs)
                if self.commit_on_success: bake()   # commit
            except sqlite3.IntegrityError as e:
                rollback()
                traceback = None
                if bottle.DEBUG:
                    traceback = (history.lastsql, history.lastparams)
                    sqllog = "[Macaron]LastSQL: %s\n[Macaron]Params : %s\n" % traceback
                    bottle.request.environ["wsgi.errors"].write(sqllog)
                raise bottle.HTTPError(500, "Database Error", e, tb.format_exc())
            except bottle.HTTPResponse as e:
                if self.commit_on_success: bake()   # commit on HTTP response (ex. redirect())
                raise e
            except:
                rollback()
                raise
            return ret_value
        return wrapper

TYPE_FIELDS = [IntegerField, FloatField, CharField]
