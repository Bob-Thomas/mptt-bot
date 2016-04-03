import sqlite3
import config
from flask import g


def get_db():
    """Simple function that connects to the db and returns it"""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(config.DATABASE)
    return db
