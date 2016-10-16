from exceptions import *
import globals
from response import Response


class FileSystem:
    class UploadSession:
        def __init__(self, chunk_size, session_id, db, parent_id, name):
            self.db = db
            self.id = self.generate_file_entry(session_id, parent_id, name)

            self.current_last_byte = 0
            self.chunk_size = chunk_size
            self.queued_data = b''

        def generate_file_entry(self, data):
            # TODO:
            pass

        def add_data(self, data):
            self.queued_data += data
            if len(self.queued_data) >= self.chunk_size:
                chunk = self.queued_data[:self.chunk_size]
                self.queued_data = self.queued_data[self.chunk_size:]
                self.commit_chunk(chunk)

        def close(self, upload_last_chunk=True):
            self.commit_chunk(self.queued_data)
            self.queued_data = b''

        def commit_chunk(self, chunk):
            # TODO:
            self.current_last_byte += len(chunk)

    def __init__(self, sql):
        self.db = sql
        self.upload_sessions = {}

        c = self.db.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS fs_items VALUES (id INTEGER PRIMARY KEY AUTOINCREMENT, parent INTEGER, name TEXT, username TEXT, type TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS fs_disassembly VALUES (file_id INTEGER PRIMARY KEY AUTOINCREMENT, offset INTEGER, len INTEGER, cloud_id INTEGER, path TEXT)")
        c.close()
        self.db.commit()

    def accept_request(self, session_id, method, path_segments, query_params, body, headers):
        if method == 'get':
            byte_start = query_params['start'] if 'start' in query_params else 0
            byte_end = query_params['end'] if 'end' in query_params else None
            return self.retrieve(session_id, path_segments, byte_start, byte_end)
        elif method == 'put':
            if 'item_type' not in query_params:
                raise MashupBadRequestException("You need to specify item_type")
            is_folder = query_params['item_type'] == 'folder'
            # make sure proper parameter was specified
            if not is_folder and query_params['item_type'] != 'file':
                raise MashupBadRequestException("Incorrect item_type")

            if is_folder:
                self.create_catalog(session_id, path_segments)
            else:
                if 'session_action' not in query_params:
                    raise MashupBadRequestException("You need to specify session_action")
                if query_params['session_action'] not in ['add','end','cancel']:
                    raise MashupBadRequestException("session_action needs to be either add, end or cancel")

                self.start_upload_session(session_id, path_segments)
                if body is not None:
                    self.add_to_upload_session(session_id, path_segments, body)

                if query_params['session_action'] == 'end':
                    self.end_upload_session(session_id, path_segments)
                elif query_params['session_action'] == 'cancel':
                    self.cancel_upload_session(session_id, path_segments)
        elif method == 'delete':
            self.remove(session_id, path_segments)
            return Response.ok()
        else:
            raise MashupBadRequestException("This method is not supported for file system calls")

    def retrieve(self, session_id, path, byte_start = 0, byte_end = None):
        pass

    def get_item(self, session_id, path, root_id = None, throw_on_not_found = True):
        if len(path):
            return {'id': root_id, 'is_folder': True}

        authenticator = globals.get_resourse("modules").authenticator
        username = authenticator.derive_username_from_session_id(session_id)

        c = self.db.cursor()
        c.execute("SELECT id, type FROM fs_item WHERE name=? AND parent=? AND username=?", (path[0], root_id, username))
        rows = c.fetchall()
        if len(rows) == 0:
            if throw_on_not_found:
                raise MashupNameException("Item does not exist")
            else:
                return None
        item_id = rows[0][0]
        c.close()
        self.db.commit()

        if rows[0][1] == 'file':
            if len(path) > 0:
                raise MashupBadRequestException(str(path[0]) + " is a file")
            else:
                return {'id': item_id, 'is_folder': False}
        else:
            return self.get_item(session_id, path[1:], item_id)

    def create_catalog(self, session_id, path):
        parent_id = None
        folders_to_create = []

        authenticator = globals.get_resourse("modules").authenticator
        username = authenticator.derive_username_from_session_id(session_id)

        for i in range(len(path)):
            segment = path[i]
            result = self.get_item(session_id, [segment], parent_id)
            if result is None:
                folders_to_create = path[i:]
            else:
                if result['is_folder']:
                    parent_id = result['id']
                else:
                    raise MashupBadRequestException('Path contains a file in it')

        if len(folders_to_create) == 0:
            raise MashupBadRequestException('This folder already exists')

        c = self.db.cursor()
        for folder in folders_to_create:
            c.execute("INSERT INTO fs_items VALUES (NULL, ?, ?, ?, \"folder\")", (parent_id, folder, username))
            parent_id = c.lastrowid
        c.close()
        self.db.commit()

    def upload_session_id_from_path(self, path):
        result = ""
        for part in path:
            result += part.replace('/','//')
            result += '/:'
        return result

    def start_upload_session(self, session_id, path):
        upload_session_id = self.upload_session_id_from_path(path)
        if session_id in self.upload_sessions and upload_session_id in self.upload_sessions[session_id]:
            raise MashupBadRequestException("There is already an upload session for this file")
        self.upload_sessions[session_id][upload_session_id] = \
            FileSystem.UploadSession(globals.get_constant("CHUNK_SIZE"))

    def add_to_upload_session(self, session_id, path, data):
        try:
            session = self.upload_sessions['session_id'][self.upload_session_id_from_path(path)]
        except KeyError:
            raise MashupBadRequestException("This upload session does not exist")
        session.add_data(data)

    def cancel_upload_session(self, session_id, path):
        upload_session_id = self.upload_session_id_from_path(path)
        try:
            session = self.upload_sessions['session_id'][upload_session_id]
        except KeyError:
            raise MashupBadRequestException("This upload session does not exist")

        session.close(False)
        del self.upload_sessions['session_id'][upload_session_id]
        self.remove(session_id, path)

    def end_upload_session(self, session_id, path):
        upload_session_id = self.upload_session_id_from_path(path)
        try:
            session = self.upload_sessions['session_id'][upload_session_id]
        except KeyError:
            raise MashupBadRequestException("This upload session does not exist")

        session.close()
        del self.upload_sessions['session_id'][upload_session_id]

    def remove(self, session_id, path):
        # TODO:
        pass