from __future__ import unicode_literals
from wsgiref.simple_server import make_server
import multiprocessing
import gunicorn.app.base
import sys
import sqlite3
import server
import traceback
import globals
from clouds import CloudsManager
from authentication import Authenticator
from dispatcher import Dispatcher
from file_system import FileSystem


def number_of_workers():
    return (multiprocessing.cpu_count() * 2) + 1


class GunicornProgram(gunicorn.app.base.BaseApplication):
    def __init__(self, server, options=None):
        self.options = options or {}
        self.server = server
        super().__init__()

    def load_config(self):
        config = dict([(key, value) for key, value in self.options.items()
                       if key in self.cfg.settings and value is not None])
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.server.get_handle_http()


class WSGIProgram():
    def __init__(self, server, port):
        self.server = server
        self.port = port

    def run(self):
        server = make_server('', self.port, self.server.get_handle_http())
        print("Serving on port " + str(self.port) + "...")
        server.serve_forever()

def parse_args(arguments):
    result = {}

    key_for_next = None
    index = 0
    for argument in arguments:
        if key_for_next is not None:
            result[key_for_next] = argument
            key_for_next = None
        else:
            if argument[0] == '-':
                key_for_next = argument[1:]
            else:
                result[index] = argument
                index += 1
    if key_for_next is not None:
        result[key_for_next] = ''
    return result

class ProgramModules:
    def __init__(self, authenticator, clouds_manager, file_system):
        self.authenticator = authenticator
        self.clouds_manager = clouds_manager
        self.file_system = file_system

if __name__ == '__main__':
    options = parse_args(sys.argv)
    sql_db = sqlite3.connect(options['sqlfile'])

    # c = sql_db.cursor()
    # print(c.execute("SELECT * FROM fs_items").fetchall())
    # print(c.execute("INSERT INTO fs_items VALUES (NULL, ?, ?, ?, ?)", (None, 'name', 'root','file')).fetchall())
    # print(c.execute("SELECT * FROM fs_items").fetchall())
    # c.close()
    # sql_db.rollback()

    authenticator = Authenticator(sql_db)
    cloud_manager = CloudsManager(sql_db)
    file_system = FileSystem(sql_db)
    dispatcher = Dispatcher()

    modules = ProgramModules(authenticator, cloud_manager, file_system)
    globals.add_resource('modules', modules)

    try:
        authenticator.add_user("root", "password", [{'user': 'all', 'privilege': 'all'}])
        authenticator.add_user("mike", "password2", [{'user': 'mike', 'privilege': 'all'}])
    except Exception as e:
        sql_db.rollback()
        traceback.print_exc()
        print(e.args)

    server = server.RESTServer(dispatcher)

    mode = 'gunicorn'
    if len(sys.argv) > 1 and sys.argv[1] == 'simple':
        mode = 'simple'

    if mode == 'gunicorn':
        options = {
            'bind': '%s:%s' % ('127.0.0.1', '8080'),
            'workers': 1,#number_of_workers(),
            'certfile': options['certfile'],
            'keyfile': options['keyfile']
        }
        GunicornProgram(server, options).run()
    else:
        WSGIProgram(server, 8000).run()