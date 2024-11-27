import mysql.connector
from flask import g
from core.settings import get_conf

def get_db():
    if 'db' not in g:
        try:
            g.db = mysql.connector.connect(
                host=get_conf()["database"]["host"],
                user=get_conf()["database"]["username"],
                password=get_conf()["database"]["password"],
                database=get_conf()["database"]["database"],
                charset='utf8mb4',
                collation='utf8mb4_general_ci',
                pool_name="mypool",
                pool_size=5,               # Maximum number of connections in the pool
                pool_reset_session=True    # Reset session variables when connection is returned to pool
            )
            g.cursor = g.db.cursor(dictionary=True)
        except mysql.connector.Error as err:
            # If connection fails, try to reconnect
            if 'db' in g:
                g.pop('db', None)
            if 'cursor' in g:
                g.pop('cursor', None)
            # Attempt reconnection
            g.db = mysql.connector.connect(
                host=get_conf()["database"]["host"],
                user=get_conf()["database"]["username"],
                password=get_conf()["database"]["password"],
                database=get_conf()["database"]["database"],
                charset='utf8mb4',
                collation='utf8mb4_general_ci',
                pool_name="mypool",
                pool_size=5,
                pool_reset_session=True
            )
            g.cursor = g.db.cursor(dictionary=True)
            
    # Verify connection is still alive
    try:
        g.db.ping(reconnect=True, attempts=1, delay=0)
    except mysql.connector.Error:
        # If ping fails, close old connection and create new one
        close_db()
        return get_db()
        
    return g.db, g.cursor

def close_db(e=None):
    cursor = g.pop('cursor', None)
    db = g.pop('db', None)
    
    if cursor is not None:
        try:
            cursor.close()
        except mysql.connector.Error:
            pass
            
    if db is not None:
        try:
            db.close()
        except mysql.connector.Error:
            pass

# Make sure to register close_db with your Flask app
def init_app(app):
    app.teardown_appcontext(close_db)