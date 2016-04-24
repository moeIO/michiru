# Database stuff for modules to store their stuff in.
import time
import datetime
import sqlite3
import threading

from . import version as michiru, \
              config

config.item('db_file', 'db.sqlite3')

DB_FILE = config.get('db_file')
# SQLite 3 data definitions for abstraction.
INT = 'integer'
UINT = 'unsigned integer'
BOOL = 'tinyint(1)'
STRING = 'text'
DATE = 'date'
DATETIME = 'datetime'
BINARY = 'blob'
# Attributes.
PRIMARY = 'PRIMARY KEY AUTOINCREMENT'
ID = (INT, PRIMARY)
UNIQUE = '<uindex>'
INDEX = '<index>'
DEFAULT = lambda x: 'DEFAULT(' + val2db(x, raw=False) + ')'
# Misc.
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DATE_FORMAT = '%Y-%m-%d'
TIME_FORMAT = '%H:%M:%S'

handle = None
mutex = threading.RLock()

config.ensure_file(DB_FILE, writable=True)


def table(name, structure):
    """ Ensure a data entry with given structure exists. """
    global handle, INDEX, UNIQUE

    # Base query.
    query  = 'CREATE TABLE IF NOT EXISTS `{name}` ('.format(name=name)

    struct = []
    indices = []
    unique_indices = []
    # Set up structure.
    for n, val in structure.items():
        if isinstance(val, tuple):
            type, attributes = val[0], list(val[1:])
        else:
            type = val
            attributes = []

        # Store indices for later use.
        if UNIQUE in attributes:
            attributes.remove(UNIQUE)
            unique_indices.append(n)
        if INDEX in attributes:
            attributes.remove(INDEX)
            indices.append(n)
        struct.append((n, type, attributes))

    # Add structure to query and finalize it.
    query += ', '.join('`{}` {} {}'.format(n, type, ' '.join(attributes)) for n, type, attributes in struct)
    query += ')'

    # Create table.
    cursor = handle.cursor()
    cursor.execute(query)

    # Create indices.
    for idx in indices:
        cursor.execute('CREATE INDEX IF NOT EXISTS `{name}` ON `{table}` (`{name}`)'.format(table=name, name=idx))
    for idx in unique_indices:
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS `{name}` ON `{table}` (`{name}`)'.format(table=name, name=idx))
    handle.commit()


def connect():
    """ Connect to the database. """
    global handle

    handle = sqlite3.connect(config.filename(DB_FILE, writable=True), check_same_thread=False)
    handle.row_factory = sqlite3.Row

def disconnect():
    """ Disconnect from the database. """
    global handle
    handle.close()


class Query:
    """ An object representing a query for easy method chaining. """
    def __init__(self, handle, table):
        self.handle = handle
        self.table = table
        self.constraints = []
        self.limit_ = None
        self.order_ = None

    def where(self, name, val, or_=False):
        """ Add filter to query. """
        if isinstance(val, tuple):
            comparator, value = val
        else:
            comparator = '='
            value = val

        # Special case since None never compares to None using '='.
        if val is None and comparator == '=':
            comparator = 'is'
        self.constraints.append((name, comparator, val, 'or' if or_ else 'and'))
        return self

    def or_(self, name, val):
        """ Add OR filter to query. """
        return self.where(name, val, or_=True)

    def and_(self, name, val):
        """ Add filter to query. """
        return self.where(name, val)

    def limit(self, limit):
        """ Limit query results. """
        self.limit_ = limit
        return self

    def random(self):
        """ Return the results in random order. """
        self.order_ = 'RANDOM()'
        return self

    def get(self, *fields):
        """ Perform data retrieval query for `fields`. """
        global mutex

        # Build query.
        query  = 'SELECT {fields} FROM `{table}`'.format(fields='`' + '`, `'.join(fields) + '`' if fields else '*', table=self.table)

        # Build where.
        vals = []
        if self.constraints:
            query += ' WHERE '
            first = True
            constraint_statements = []

            for name, comparator, value, connector in self.constraints:
                constraint_statements.append('{conn} `{field}` {cmp} ?'.format(field=name, cmp=comparator, conn='' if first else connector))
                vals.append(val2db(value))
                first = False
            query += ' '.join(constraint_statements)

        # Build order.
        if self.order_ is not None:
            query += ' ORDER BY ' + self.order_
        # Build limit.
        if self.limit_ is not None:
            query += ' LIMIT ' + str(self.limit_)

        # Perform query.
        mutex.acquire()
        cursor = self.handle.cursor()
        cursor.execute(query, tuple(vals))
        data = cursor.fetchall()
        mutex.release()

        return data

    def single(self, *fields):
        """ Perform data retrieval query for `fields` and return single row, or None. """
        result = self.get(*fields)
        if result:
            return result[0]
        return None

    def add(self, values):
        """ Perform data insertion query. """
        global mutex

        # Build query, nothing particularly special.
        query = 'INSERT INTO `{table}` '.format(table=self.table)
        query += '(`' + '`, `'.join(values.keys()) + '`) '
        query += 'VALUES (' + ', '.join(['?'] * len(values.keys())) + ')'

        # Execute query.
        mutex.acquire()
        cursor = self.handle.cursor()
        cursor.execute(query, tuple(val2db(x) for x in values.values()))
        self.handle.commit()
        mutex.release()

        # Return inserted ID.
        return cursor.lastrowid

    def delete(self):
        """ Perform data removal query. """
        global mutex
        query = 'DELETE FROM `{table}`'.format(table=self.table)

        # Build where.
        vals = []
        if self.constraints:
            query += ' WHERE '
            first = True
            constraint_statements = []

            for name, comparator, value, connector in self.constraints:
                constraint_statements.append('{conn} `{field}` {cmp} ?'.format(field=name, cmp=comparator, conn='' if first else connector))
                vals.append(val2db(value))
                first = False
            query += ' '.join(constraint_statements)

        # Execute.
        mutex.acquire()
        cursor = self.handle.cursor()
        cursor.execute(query, tuple(vals))
        self.handle.commit()
        mutex.release()

def on(table):
    """ Start a query on given data. """
    global handle
    return Query(handle, table)

def in_(table):
    """ Start a query on given data. """
    return on(table)

def from_(table):
    """ Start a query on given data. """
    return on(table)

def to(table):
    """ Start a query on given data. """
    return on(table)

def query(table, query, *vals):
    """ Perform a raw query on data. """
    global handle, mutex

    # Perform query, commit results, receive data.
    mutex.acquire()
    cursor = handle.cursor()
    cursor.execute(query, tuple(vals))
    data = cursur.fetchall()
    cursor.commit()
    mutex.release()

    return data


def val2db(val, raw=True):
    """
    Convert value to database native value.
    Set `raw` to True if you're using prepared statements,
    False if you're directly inserting things into query strings.
    """
    global DATETIME_FORMAT, DATE_FORMAT, TIME_FORMAT

    if isinstance(val, str):
        if not raw:
            return '"' + val.replace('"', '\\"') + '"'
        return val

    elif isinstance(val, bytes):
        if not raw:
            return b'"' + val.replace(b'"', b'\\"') + b'"'
        return val

    elif val is None:
        return val

    elif isinstance(val, bool) and not raw:
        return '1' if val else '0'

    elif isinstance(val, int) and not raw:
        return str(val)

    elif isinstance(val, datetime.datetime):
        if not raw:
            return "'" + val.strftime(DATETIME_FORMAT) + "'"
        return val.strftime(DATETIME_FORMAT)

    elif isinstance(val, datetime.time):
        if not raw:
            return "'" + val.strftime(TIME_FORMAT) + "'"
        return val.strftime(TIME_FORMAT)

    elif isinstance(val, datetime.date):
        if not raw:
            return "'" + val.strftime(DATE_FORMAT) + "'"
        return val.strftime(DATE_FORMAT)

    return str(val)
