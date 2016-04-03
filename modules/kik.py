""" KIK module to interact with the emulator"""
from subprocess import call
import os
import sqlite3
import io
import config
from modules import database
#TODO put it in a database the bot config
lurker_mode = True



def check_if_admin(group=None, user_id=None):
    """Returns true or false based if the user is an admin in the group"""
    cursor = database.get_db().cursor()
    data = cursor.execute('SELECT DISTINCT m.member_jid from memberTable as m, KIKcontactsTable as c where m.is_admin = 1 and m.group_id = ? and m.member_jid = ?', (group, user_id, )).fetchone()
    if data:
        return True
    return False

def pull_db(app=None):
    """Pulls the database from the phone and merges it with our own database"""
    global last_pull
    with app.app_context():
        cursor = database.get_db().cursor()
        group = '1100136938971_g@groups.kik.com'
        last_pull = int(cursor.execute('SELECT MAX(m.timestamp) FROM messagesTable as m, KIKcontactsTable as c  where m.bin_id = ?  and m.partner_jid = c.jid order BY m.timestamp ASC;', (group, )).fetchone()[0])
        print ("PULLING DATA")
        call(["adb", "pull", "/data/data/kik.pikek/databases/kikDatabase.db", "./databases"])
        db_con = sqlite3.connect('databases/kikDatabase.db')
        with io.open(config.DATA_BASE_DIR + 'dump.sql', 'w', encoding='utf8') as f:
            for line in db_con.iterdump():
                if 'CREATE TABLE' in line:
                    line = line.replace('CREATE TABLE', 'CREATE TABLE IF NOT EXISTS')
                if 'INSERT INTO' in line:
                    line = line.replace('INSERT INTO', 'INSERT OR IGNORE INTO ')
                f.write('%s\n' % line)
        db_con.close()
        f = io.open(config.DATA_BASE_DIR + 'dump.sql','r', encoding='utf8')
        command = f.read()
        f.close()
        cursor.executescript(command)
        os.remove(config.DATA_BASE_DIR + 'kikDatabase.db')
        read_new_messages(app)

def read_new_messages(app=None):
    """Reads new messages based on latest timestamp and checks for commands"""
    global last_pull, lurker_mode
    with app.app_context():
        cursor = database.get_db().cursor()
        group = '1100136938971_g@groups.kik.com'
        data = cursor.execute('SELECT c.display_name, m.body, m.timestamp, m.partner_jid  FROM messagesTable as m, KIKcontactsTable as c  where m.bin_id = ?  and m.partner_jid = c.jid and m.timestamp > ? order BY m.timestamp ASC;', (group, int(last_pull), )).fetchall()
        for line in data:
            if not line[1] is None:
                command = line[1].lower()
                result = get_command(command)
                if result and not lurker_mode:
                    if not result[1]:
                        send_message(result[2])
                    elif check_if_admin(group, line[3]):
                        send_message(result[2])
                if check_if_admin(group, line[3]):
                    if '!add' in command:
                        new_command = command.split(' ')[1]
                        admin_only = command.split(' ')[2]
                        response = " ".join(command.split(' ')[3:])
                        query = add_command(new_command, response, admin_only)
                        send_message(query)
                    elif '!remove' in command:
                        remove = command.split(' ')[1]
                        response = remove_command(remove)
                        if response:
                            send_message(response)
                    elif '!show' in command:
                        send_message(show_commands())
                    if command == "!lurk":
                        lurker_mode = not lurker_mode
                        if lurker_mode:
                            send_message("Lurking mode enabled")
                        else:
                            send_message("Lurking mode disabled")


def add_command(command, response, admin_only):
    """Adds a command to the database"""
    if not get_command(command):
        cursor = database.get_db().cursor()
        cursor.execute("INSERT INTO commands (command, response, admin_only) VALUES (?, ?, ?)", (command, response, admin_only, ))
        database.get_db().commit()
        return "Command {} has been added".format(command)
    return "Command already exists"

def remove_command(command):
    """Removes command from the database"""
    if get_command(command):
        cursor = database.get_db().cursor()
        cursor.execute("DELETE from commands where command = ?", (command, ))
        database.get_db().commit()
        return "Command {} has been removed".format(command)
    return False

def show_commands():
    """Shows all the available commands"""
    cursor = database.get_db().cursor()
    result = ""
    data = cursor.execute('SELECT * from commands').fetchall()
    result = "Commands that are available: \n"
    for command in data:
        result += "{} {} {} \n".format(command[1], command[2], command[3])
    return result;

def get_command(command):
    """returns a single command"""
    cursor = database.get_db().cursor()
    return cursor.execute('SELECT command, admin_only, response FROM commands where command = ?', (command, )).fetchone()

def send_message(message):
    """Sends input event to the emulator and taps the send button"""
    click_cord = (1006, 916)
    call(["adb", "shell", "input", "text", '"'+message.replace(' ', '%s')+'"'])
    call(["adb", "shell", "input", "tap", str(click_cord[0]), str(click_cord[1])])
