import mysql.connector
from flask import g
from core.settings import get_conf

def get_db():
    if 'db' not in g:
        g.db = mysql.connector.connect(
            host=get_conf()["database"]["host"],
            user=get_conf()["database"]["username"],
            password=get_conf()["database"]["password"],
            database=get_conf()["database"]["database"],
            charset='utf8mb4',
            collation='utf8mb4_general_ci',
        )
        g.cursor = g.db.cursor(dictionary=True)
    return g.db, g.cursor

def close_db(e=None):
    db = g.pop('db', None)
    cursor = g.pop('cursor', None)
    if cursor is not None:
        cursor.close()
    if db is not None:
        db.close()
