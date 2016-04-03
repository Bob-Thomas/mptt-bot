import sqlite3
import os
import io
import shutil
from time import strftime, time
from datetime import datetime
from flask import Flask, render_template, g
from apscheduler.schedulers.blocking import BlockingScheduler
from subprocess import call
import threading
import atexit
from modules import kik, database
import config
yourThread = threading.Thread()
click_cord = (1006, 916)
last_pull = time()

#TODO FIX THIS SHIT WITH CELERY <3
def create_app():
    app = Flask(__name__)

    def interrupt():
        global yourThread
        yourThread.cancel()

    def doStuff():
        global yourThread
        yourThread = threading.Timer(config.POOL_TIME, doStuff, ())
        with app.app_context():
            kik.pull_db(app)
        yourThread.start()

    def doStuffStart():
        # Do initialisation stuff here
        global yourThread
        # Create your thread
        yourThread = threading.Timer(config.POOL_TIME, doStuff, ())
        yourThread.start()

    # Initiate
    doStuffStart()
    # When you kill Flask (SIGTERM), clear the trigger for the next thread
    atexit.register(interrupt)
    return app

app = create_app()

@app.template_filter('ctime')
def timectime(s):
    return datetime.fromtimestamp(int(s)/1000).strftime('%Y-%m-%d %H:%M:%S')

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.route('/')
def home():
    c = database.get_db().cursor()
    data = c.execute('select display_name, jid FROM KIKcontactsTable WHERE jid like "%groups.kik.com%" and display_name != "none"').fetchall()
    # data =  c.execute('SELECT c.display_name, m.body, m.timestamp  FROM messagesTable as m, KIKcontactsTable as c  where m.bin_id = "1100039970161_g@groups.kik.com"  and m.partner_jid = c.jid order BY m.timestamp ASC;').fetchall()
    return render_template('home.html' , data=data)

@app.route('/<group>')
def group_chat(group=None):
    c = database.get_db().cursor()
    # data = c.execute('select display_name, jid FROM KIKcontactsTable WHERE jid like "%groups.kik.com%"').fetchall()
    data = c.execute('SELECT c.display_name, m.body, m.timestamp  FROM messagesTable as m, KIKcontactsTable as c  where m.bin_id = ?  and m.partner_jid = c.jid order BY m.timestamp ASC;', (group, )).fetchall()
    return render_template('group.html' , data=data)


if __name__ == '__main__':
    app.run(host='0.0.0.0')
