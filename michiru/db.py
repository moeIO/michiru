#!/usr/bin/env python3
# Database stuff for modules to store their stuff in.
import time
import datetime
import sqlite3

import version as michiru
import config

DB_FILE = 'db.sqlite3'
# SQLite 3 data definitions for abstraction.
INT = 'integer'
UINT = 'unsigned integer'
BOOL = 'tinyint(1)'
STRING = 'text'
DATE = 'date'
DATETIME = 'datetime'
# Attributes.
PRIMARY = 'PRIMARY KEY AUTOINCREMENT'
ID = (INT, PRIMARY)
UNIQUE = 'UNIQUE'
INDEX = '<index>'
DEFAULT = lambda x: 'DEFAULT(' + val2db(x, escape=True) + ')'

handle = None

config.ensure_file(DB_FILE, writable=True)

def ensure(name, structure):
    """ Ensure a data entry with given structure exists. """
    global handle
    query  = 'CREATE TABLE IF NOT EXISTS `{name}` ('.format(name=name)

    struct = []
    # Set up structure.
    for name, val in structure.items():
        if isinstance(val, tuple):
            type, attributes = val[0], val[1:]
        else:
            type = val
            attributes = ''
        struct.append((name, type, attributes))

    query += ', '.join('`{}` {} {}'.format(name, type, ' '.join(attributes)) for name, type, attributes in struct)
    query += ')'

    cursor = handle.cursor()
    cursor.execute(query)
    handle.commit()


def connect():
    """ Connect to the database. """
    global handle

    handle = sqlite3.connect(config.filename(DB_FILE, writable=True))
    handle.row_factory = sqlite3.Row

def disconnect():
    """ Disconnect from the database. """
    global handle
    handle.close()


class Query:
    def __init__(self, handle, table):
        self.handle = handle
        self.table = table
        self.constraints = []
        self.limit_ = None
        self.order_ = None

    def where(self, name, val, or_=False):
        if isinstance(val, tuple):
            comparator, value = val
        else:
            comparator = '='
            value = val

        if val is None and comparator == '=':
            comparator = 'is'
        self.constraints.append((name, comparator, val, 'or' if or_ else 'and'))
        return self

    def or_(self, name, val):
        return self.where(name, val, or_=True)

    def and_(self, name, val):
        return self.where(name, val)

    def limit(self, limit):
        self.limit_ = limit
        return self

    def random(self):
        self.order_ = 'RANDOM()'
        return self

    def get(self, *fields):
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

        cursor = self.handle.cursor()
        cursor.execute(query, tuple(vals))
        return cursor.fetchall()
    
    def single(self, *fields):
        result = self.get(*fields)
        if result:
            return result[0]
        return None

    def add(self, values):
        # Build query.
        query = 'INSERT INTO `{table}` '.format(table=self.table)
        query += '(`' + '`, `'.join(values.keys()) + '`) '
        query += 'VALUES (' + ', '.join(['?'] * len(values.keys())) + ')'

        cursor = self.handle.cursor()
        cursor.execute(query, tuple(val2db(x) for x in values.values()))
        self.handle.commit()

    def delete(self):
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
        cursor = self.handle.cursor()
        cursor.execute(query, tuple(vals))
        self.handle.commit()



def on(table):
    """ Start a query on given data. """
    global handle
    return Query(handle, table)


def val2db(val, raw=True):
    if isinstance(val, str):
        if not raw:
            return '"' + val.replace('"', '\\"') + '"'
        return val
    elif isinstance(val, bool) and raw:
        return '1' if val else '0'
    elif isinstance(val, int) and raw:
        return str(val)
    elif isinstance(val, datetime.datetime):
        if not raw:
            return "'" + val.strftime('%Y-%m-%d %H:%M:%S') + "'"
        return val.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(val, datetime.time):
        if not raw:
            return "'" + val.strftime('%H:%M:%S') + "'"
        return val.strftime('%H:%M:%S')
    elif isinstance(val, datetime.date):
        if not raw:
            return "'" + val.strftime('%Y-%m-%d') + "'"
        return val.strftime('%Y-%m-%d')
    return str(val)
