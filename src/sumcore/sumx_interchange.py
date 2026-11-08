#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#pylint:disable=W0301
#
#  Copyright 2018-2026 William Martinez Bas <metfar@gmail.com>
#  GPL-2.0-or-later
#
"""SUMTAB / native sumX SQLite bridge; no dependency on either frontend.""";

from datetime import date, datetime, time;
from decimal import Decimal;
from pathlib import Path;
import re;
import sqlite3;

from sumcore.sumtab import SumColumn, SumIndex, SumTable, read_sumtab, write_sumtab;


def quote(name):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", str(name)):
        raise ValueError("Invalid sumX identifier: {}".format(name));
    if str(name).startswith("__"):
        raise ValueError("Reserved sumX identifier: {}".format(name));
    return '"{}"'.format(name);


def is_sumx_database(path):
    if not Path(path).is_file():
        return False;
    with sqlite3.connect(path) as db:
        return bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='__sumx_columns'").fetchone());


def _meta_rows(db, table):
    return db.execute("SELECT * FROM __sumx_columns WHERE table_name=? ORDER BY ordinal", (table,)).fetchall();


def _db_tables(db):
    return {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE '__sumx_%' AND name NOT LIKE 'sqlite_%'")};


def load_table(path, table):
    quote(table);
    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row;
        if table not in _db_tables(db):
            raise ValueError("sumX table not found: {}".format(table));
        meta = _meta_rows(db, table);
        if not meta:
            raise ValueError("sumX metadata missing for table: {}".format(table));
        columns = [];
        for row in meta:
            ref = None;
            if row['references_table'] and row['references_column']:
                ref = '{}({})'.format(row['references_table'], row['references_column']);
            columns.append(SumColumn(name=row['name'], logical_type=row['logical_type'],
                declared_type=row['declared_type'], length=row['length'],
                precision=row['precision_value'], scale=row['scale_value'],
                nullable=bool(row['nullable']), primary_key=bool(row['primary_key']),
                unique=bool(row['unique_value']), autoinum=bool(row['autoinum']),
                default=row['default_sql'], references=ref));
        rows = [];
        names = ','.join(quote(c.name) for c in columns);
        for record in db.execute('SELECT {} FROM {}'.format(names, quote(table))):
            values = [];
            for value, col in zip(record, columns):
                if value is None:
                    values.append(None);
                elif col.logical_type == 'NUMERIC':
                    values.append(Decimal(int(value)) / (10 ** int(col.scale or 0)));
                elif col.logical_type == 'LOGICAL':
                    values.append(bool(value));
                elif col.logical_type == 'DATE':
                    values.append(date.fromisoformat(value));
                elif col.logical_type == 'TIME':
                    values.append(time.fromisoformat(value));
                elif col.logical_type == 'DATETIME':
                    values.append(datetime.fromisoformat(value));
                else:
                    values.append(value);
            rows.append(tuple(values));
        indexes = [];
        for record in db.execute('PRAGMA index_list({})'.format(quote(table))):
            name = record[1]; unique = bool(record[2]); origin = record[3];
            if origin in ('pk', 'u'):
                continue;
            details = db.execute('PRAGMA index_info("{}")'.format(name.replace('"','""'))).fetchall();
            names = tuple(item[2] for item in details if item[2] is not None);
            expression = None;
            if len(names) != len(details):
                sql_row = db.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name=?", (name,)).fetchone();
                sql = sql_row[0] if sql_row else '';
                expression = sql[sql.find('(')+1:sql.rfind(')')] if '(' in sql else None;
            indexes.append(SumIndex(name=name, columns=names, unique=unique,
                                    expression=expression, origin="user" if origin == "c" else origin));
        return SumTable(columns=columns, rows=rows, indexes=indexes,
                        metadata={'table': table, 'source_format': 'sumX'});


def _definition(col):
    quote(col.name);
    kind = col.declared_type or col.logical_type;
    logical = col.logical_type;
    if logical == 'NUMERIC':
        kind = 'NUMERIC({},{})'.format(col.precision or 18, col.scale or 0);
    elif logical in ('CHARACTER', 'VARCHAR'):
        kind = '{}({})'.format(logical, col.length or (1 if logical == 'CHARACTER' else 255));
    elif logical == 'MEMO':
        kind = 'MEMO';
    elif logical in ('TEXT', 'INTEGER', 'FLOAT', 'LOGICAL', 'DATE', 'TIME', 'DATETIME', 'BLOB', 'UUID', 'JSON'):
        kind = logical;
    else:
        raise ValueError('Unsupported sumX logical type: {}'.format(logical));
    suffix = '';
    if col.autoinum:
        kind = 'AUTONUM';
    elif col.primary_key:
        suffix += ' PRIMARY KEY';
    if not col.nullable and not col.primary_key and not col.autoinum:
        suffix += ' NOT NULL';
    if col.unique and not col.primary_key:
        suffix += ' UNIQUE';
    if col.default is not None:
        suffix += ' DEFAULT {}'.format(col.default);
    # Reference DDL is only safe when target column exists; preserve in SUMTAB instead of guessing.
    if col.references:
        raise ValueError('Foreign-key metadata import requires an existing target: {}'.format(col.references));
    return '{} {}{}'.format(col.name, kind, suffix);


def import_table(path, table, source):
    """Import a SUMTAB into a sumX database; refuse overwrite or partial success.""";
    from sumx.database import SumXDatabase;
    model = read_sumtab(source);
    quote(table);
    if not model.columns:
        raise ValueError('SUMTAB has no columns');
    names = [c.name.casefold() for c in model.columns];
    if len(set(names)) != len(names):
        raise ValueError('Duplicate column names');
    db = SumXDatabase(path);
    try:
        if db.table_exists(table):
            raise ValueError('Table already exists: {}'.format(table));
        definitions = [_definition(c) for c in model.columns];
        # Validate all values and index names before creating a table.
        parsed = [db.parse_column(d) for d in definitions];
        prepared = [];
        for row in model.rows:
            prepared.append(tuple(c.encode(v) for c,v in zip(parsed,row)));
        for idx in model.indexes:
            quote(idx.name);
            if idx.expression:
                raise ValueError('Expression indexes require explicit review: {}'.format(idx.name));
            if any(n.casefold() not in names for n in idx.columns):
                raise ValueError('Unknown index columns: {}'.format(idx.name));
        db.create_table(table, definitions);
        try:
            cols = ','.join(quote(c.name) for c in parsed);
            marks = ','.join('?' for _ in parsed);
            if prepared:
                db.connection.executemany('INSERT INTO {} ({}) VALUES ({})'.format(quote(table),cols,marks),prepared);
            for idx in model.indexes:
                if idx.origin in ('pk','u'):
                    continue;
                db.connection.execute('CREATE {}INDEX {} ON {} ({})'.format(
                    'UNIQUE ' if idx.unique else '', quote(idx.name), quote(table),
                    ','.join(quote(c) for c in idx.columns)));
            db.connection.commit();
        except Exception:
            db.connection.rollback();
            db.connection.execute('DROP TABLE IF EXISTS {}'.format(quote(table)));
            db.connection.execute('DELETE FROM __sumx_columns WHERE table_name=?',(table,));
            db.connection.commit();
            raise;
    finally:
        db.close();
    return len(prepared);


def export_table(path, table, target):
    model = load_table(path, table);
    write_sumtab(model, target);
    return len(model.rows);
