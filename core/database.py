import mysql.connector
from flask import g
from dotenv import load_dotenv
import os

load_dotenv()


def get_db():
    if "db" not in g:
        g.db = mysql.connector.connect(
            host=os.getenv("PLG_HOST"),
            user=os.getenv("PLG_USERNAME"),
            password=os.getenv("PLG_PASSWORD"),
            database=os.getenv("PLG_DATABASE"),
            port=os.getenv("PLG_PORT"),
            charset="utf8mb4",
            collation="utf8mb4_general_ci",
            pool_size=8,
            pool_reset_session=False,
        )
        g.cursor = g.db.cursor(dictionary=True)
    return g.db, g.cursor


def close_db(e=None):
    db = g.pop("db", None)
    cursor = g.pop("cursor", None)
    if cursor is not None:
        cursor.close()
    if db is not None:
        db.close()
