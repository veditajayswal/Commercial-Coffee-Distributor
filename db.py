import mysql.connector
from flask import current_app, g


def get_db():
    if "db" not in g:
        cfg = current_app.config
        g.db = mysql.connector.connect(
            host=cfg["DB_HOST"],
            port=cfg["DB_PORT"],
            user=cfg["DB_USER"],
            password=cfg["DB_PASSWORD"],
            database=cfg["DB_NAME"],
            charset="utf8mb4",
            connection_timeout=10,
        )
    return g.db


def close_db(error=None):
    conn = g.pop("db", None)
    if conn is not None:
        try:
            conn.close()
        except mysql.connector.Error:
            pass


def query_all(sql, params=None):
    cur = get_db().cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        cur.close()


def query_one(sql, params=None):
    cur = get_db().cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        return cur.fetchone()
    finally:
        cur.close()


def scalar(sql, params=None):
    row = query_one(sql, params)
    if row is None:
        return None
    return next(iter(row.values()))


def execute(sql, params=None):
    """Run INSERT/UPDATE/DELETE without committing. Returns affected row count."""
    cur = get_db().cursor()
    try:
        cur.execute(sql, params)
        return cur.rowcount
    finally:
        cur.close()


def insert(sql, params=None):
    """Run INSERT without committing. Returns the new AUTO_INCREMENT id."""
    cur = get_db().cursor()
    try:
        cur.execute(sql, params)
        return cur.lastrowid
    finally:
        cur.close()


def commit():
    get_db().commit()


def rollback():
    get_db().rollback()


def insert_row(table, data):
    """Table and column names come from entities.py (trusted); values are parameterized."""
    columns = list(data.keys())
    sql = "INSERT INTO `{}` ({}) VALUES ({})".format(
        table,
        ", ".join("`{}`".format(c) for c in columns),
        ", ".join(["%s"] * len(columns)),
    )
    return insert(sql, [data[c] for c in columns])


def update_row(table, pk, pk_value, data):
    columns = list(data.keys())
    sql = "UPDATE `{}` SET {} WHERE `{}` = %s".format(
        table,
        ", ".join("`{}` = %s".format(c) for c in columns),
        pk,
    )
    return execute(sql, [data[c] for c in columns] + [pk_value])


def delete_row(table, pk, pk_value):
    sql = "DELETE FROM `{}` WHERE `{}` = %s".format(table, pk)
    return execute(sql, [pk_value])