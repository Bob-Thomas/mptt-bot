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
POOL_TIME = 5 #Seconds
yourThread = threading.Thread()
click_cord = (1006, 916)
last_pull = time()

def pull_kik_db():
    global last_pull
    with app.app_context():
        c = get_db().cursor()
        group = '1100039970161_g@groups.kik.com'
        last_pull = int(c.execute('SELECT MAX(m.timestamp) FROM messagesTable as m, KIKcontactsTable as c  where m.bin_id = ?  and m.partner_jid = c.jid order BY m.timestamp ASC;', (group, )).fetchone()[0])
        print ("PULLING DATA")
        call(["adb", "pull", "/data/data/kik.pikek/databases/kikDatabase.db", "./databases"])
        db_con = sqlite3.connect('databases/kikDatabase.db')
        with io.open(DATA_BASE_DIR + 'dump.sql', 'w', encoding='utf8') as f:
            for line in db_con.iterdump():
                if 'CREATE TABLE' in line:
                    line = line.replace('CREATE TABLE', 'CREATE TABLE IF NOT EXISTS')
                if 'INSERT INTO' in line:
                    line = line.replace('INSERT INTO', 'INSERT OR IGNORE INTO')
                f.write('%s\n' % line)
        db_con.close()
        f = io.open(DATA_BASE_DIR + 'dump.sql','r', encoding='utf8')
        command = f.read()
        f.close()
        c.executescript(command)
        os.remove(DATA_BASE_DIR + 'kikDatabase.db')
        read_new_messages()

def read_new_messages():
    global last_pull
    with app.app_context():
        c = get_db().cursor()
        group = '1100039970161_g@groups.kik.com'
        data = c.execute('SELECT c.display_name, m.body, m.timestamp  FROM messagesTable as m, KIKcontactsTable as c  where m.bin_id = ?  and m.partner_jid = c.jid and m.timestamp > ? order BY m.timestamp ASC;', (group, int(last_pull), )).fetchall()
        for line in data:
            if not line[1] is None:
                print(line[1])
                command = line[1].lower()
                if "welcome endbot" in command:
                    send_message("Hya thanks for having me {}".format(line[0]))

def send_message(message):
    click_cord = (1006, 916)
    call(["adb", "shell", "input", "text", '"'+message.replace(' ', '%s')+'"'])
    call(["adb", "shell", "input", "tap", str(click_cord[0]), str(click_cord[1])])

def create_app():
    app = Flask(__name__)

    def interrupt():
        global yourThread
        yourThread.cancel()

    def doStuff():
        global yourThread
        yourThread = threading.Timer(POOL_TIME, doStuff, ())
        pull_kik_db()
        yourThread.start()

    def doStuffStart():
        # Do initialisation stuff here
        global yourThread
        # Create your thread
        yourThread = threading.Timer(POOL_TIME, doStuff, ())
        yourThread.start()

    # Initiate
    doStuffStart()
    # When you kill Flask (SIGTERM), clear the trigger for the next thread
    atexit.register(interrupt)
    return app

DATA_BASE_DIR = os.path.join(os.getcwd(), 'databases/')
DATABASE = DATA_BASE_DIR + 'kik.db'
app = create_app()

@app.template_filter('ctime')
def timectime(s):
    return datetime.fromtimestamp(int(s)/1000).strftime('%Y-%m-%d %H:%M:%S')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.route('/')
def home():
    c = get_db().cursor()
    data = c.execute('select display_name, jid FROM KIKcontactsTable WHERE jid like "%groups.kik.com%" and display_name != "none"').fetchall()
    # data =  c.execute('SELECT c.display_name, m.body, m.timestamp  FROM messagesTable as m, KIKcontactsTable as c  where m.bin_id = "1100039970161_g@groups.kik.com"  and m.partner_jid = c.jid order BY m.timestamp ASC;').fetchall()
    return render_template('home.html' , data=data)

@app.route('/<group>')
def group_chat(group=None):
    c = get_db().cursor()
    # data = c.execute('select display_name, jid FROM KIKcontactsTable WHERE jid like "%groups.kik.com%"').fetchall()
    data = c.execute('SELECT c.display_name, m.body, m.timestamp  FROM messagesTable as m, KIKcontactsTable as c  where m.bin_id = ?  and m.partner_jid = c.jid order BY m.timestamp ASC;', (group, )).fetchall()
    return render_template('group.html' , data=data)


if __name__ == '__main__':
    app.run()
