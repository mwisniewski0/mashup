from exceptions import *
import globals
from response import Response


class FileSystem:
    class UploadSession:
        def __init__(self, chunk_size, session_id, db, parent_id, name):
            self.db = db
            self.session_id = session_id
            self.id = self.get_file_entry(session_id, parent_id, name)

            self.current_last_byte = 0
            self.chunk_size = chunk_size
            self.queued_data = b''

        def get_file_entry(self, session_id, parent_id, name):
            authenticator = globals.get_resource("modules").authenticator
            username = authenticator.derive_username_from_session_id(session_id)

            c = self.db.cursor()
            c.execute("SELECT id, type FROM fs_items WHERE parent=? AND name=? AND username=?", (parent_id, name, username))
            previous_file = c.fetchall()
            if (len(previous_file) == 0):
                c.execute("INSERT INTO fs_items VALUES (NULL, ?, ?, ?, \"file\")", (parent_id, name, username))
                file_id = c.lastrowid
            else:
                if previous_file[0][1] == 'folder':
                    raise MashupBadRequestException("Requested item is not a file")
                file_id = previous_file[0][0]
            c.close()
            self.db.commit()

            return file_id

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
            modules = globals.get_resource("modules")
            clouds_manager = modules.clouds_manager
            fs = modules.file_system

            clouds = clouds_manager.list_clouds(self.session_id, True)
            smallest_ratio = 2.0
            id_of_smallest = None
            for cloud in clouds:
                ratio = cloud['taken'] / cloud['quota']
                if ratio < smallest_ratio:
                    smallest_ratio = ratio
                    id_of_smallest = cloud['id']

            path = clouds_manager.upload_anywhere(self.session_id, id_of_smallest, chunk)
            c = self.db.cursor()
            c.execute("INSERT INTO fs_disassembly VALUES (?, ?, ?, ?, ?)",
                      (self.id, self.current_last_byte, len(chunk), id_of_smallest, path))
            c.close()
            self.db.commit()

            self.current_last_byte += len(chunk)

    def __init__(self, sql):
        self.db = sql
        self.upload_sessions = {}

        c = self.db.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS fs_items (id INTEGER PRIMARY KEY AUTOINCREMENT, parent INTEGER, name TEXT, username TEXT, type TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS fs_disassembly (file_id, offset INTEGER, len INTEGER, cloud_id INTEGER, path TEXT)")
        c.close()
        self.db.commit()

    def get_root_id(self):
        return -1

    def accept_request(self, session_id, method, path_segments, query_params, body, headers):
        if method == 'get':
            byte_start = query_params['start'] if 'start' in query_params else 0
            length = query_params['length'] if 'length' in query_params else -1 # -1 means infinity
            try:
                byte_start = int(byte_start)
                length = int(length)
            except Exception:
                raise MashupBadRequestException("byte_start and length need to be integers")
            return self.retrieve(session_id, path_segments, byte_start, length)
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
                self.create_catalog(session_id, path_segments[:len(path_segments)-1], False)
                if 'session_action' not in query_params:
                    raise MashupBadRequestException("You need to specify session_action")
                if query_params['session_action'] not in ['add','end','cancel']:
                    raise MashupBadRequestException("session_action needs to be either add, end or cancel")

                self.start_upload_session_if_absent(session_id, path_segments)
                if body is not None:
                    self.add_to_upload_session(session_id, path_segments, body)

                if query_params['session_action'] == 'end':
                    self.end_upload_session(session_id, path_segments)
                elif query_params['session_action'] == 'cancel':
                    self.cancel_upload_session(session_id, path_segments)
            return Response.ok()
        elif method == 'delete':
            self.remove(session_id, path_segments)
            return Response.ok()
        else:
            raise MashupBadRequestException("This method is not supported for file system calls")

    def list_folder(self, folder_id):
        c = self.db.cursor()
        c.execute("SELECT name, type FROM fs_items WHERE parent=? ORDER BY name", (folder_id,))
        children = c.fetchall()
        c.close()
        self.db.commit()

        result = { 'children': [] }
        for child in children:
            result['children'].append({'name': child[0], 'type': child[1]})
        return result

    def retrieve_file_fragment(self, session_id, file_id, byte_start, length):
        if length == -1:
            length = float('inf')
        byte_end = byte_start + length
        clouds_manager = globals.get_resource("modules").clouds_manager

        if byte_start == byte_end:
            return b''

        c = self.db.cursor()
        c.execute("SELECT cloud_id, path, offset, offset+len FROM fs_disassembly WHERE file_id=? AND offset < ? AND offset+len >= ? ORDER BY offset",
                  (file_id, byte_end, byte_start))
        fragments = c.fetchall()
        c.close()
        self.db.commit()

        file_contents = b''
        for fragment in fragments:
            cloud_id = fragment[0]
            path = fragment[1]
            start = fragment[2]
            original_start = start
            end = fragment[3]
            original_end = end
            frag_content = clouds_manager.retrieve_file(session_id, cloud_id, path)

            if start < byte_start:
                start = byte_start
            if end > byte_end:
                end = byte_end

            file_contents += frag_content[(start - original_start):(end - original_start)]
        return file_contents

    def get_file_size(self, file_id):
        c = self.db.cursor()
        c.execute("SELECT TOTAL(len) FROM fs_items INNER JOIN fs_disassembly ON id=file_id WHERE file_id=?", (file_id,))
        size = c.fetchall()[0][0]
        c.close()
        self.db.commit()

        return int(size)

    def retrieve(self, session_id, path, byte_start = 0, length = float('inf')):
        result = self.get_item(session_id, path)
        if result['is_folder']:
            return Response.from_json(self.list_folder(result['id']))
        else:
            r = Response.from_binary(self.retrieve_file_fragment(session_id, result['id'], byte_start, length))
            r.headers['X_FILE_SIZE'] = str(self.get_file_size(result['id']))
            return r

    def get_item(self, session_id, path, root_id=None, throw_on_not_found = True):
        if root_id is None:
            root_id = self.get_root_id()

        if len(path) == 0:
            return {'id': root_id, 'is_folder': True}

        authenticator = globals.get_resource("modules").authenticator
        username = authenticator.derive_username_from_session_id(session_id)

        c = self.db.cursor()
        c.execute("SELECT id, type FROM fs_items WHERE name=? AND parent=? AND username=?", (path[0], root_id, username))
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
            if len(path) > 1:
                raise MashupBadRequestException(str(path[0]) + " is a file")
            else:
                return {'id': item_id, 'is_folder': False}
        else:
            return self.get_item(session_id, path[1:], item_id)

    def create_catalog(self, session_id, path, throw_on_existing = True):
        parent_id = self.get_root_id()
        folders_to_create = []

        authenticator = globals.get_resource("modules").authenticator
        username = authenticator.derive_username_from_session_id(session_id)

        for i in range(len(path)):
            segment = path[i]
            result = self.get_item(session_id, [segment], parent_id, False)
            if result is None:
                folders_to_create = path[i:]
                break
            else:
                if result['is_folder']:
                    parent_id = result['id']
                else:
                    raise MashupBadRequestException('Path contains a file in it')

        if len(folders_to_create) == 0:
            if throw_on_existing:
                raise MashupBadRequestException('This folder already exists')
            else:
                return None

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

    def get_cloud_taken_space(self, username, cloud_id):
        c = self.db.cursor()
        c.execute("SELECT TOTAL(len) FROM fs_items INNER JOIN fs_disassembly ON id = file_id WHERE username=? AND cloud_id=?",
            (username, cloud_id))
        size = c.fetchall()[0][0]
        c.close()
        self.db.commit()

        return size

    def start_upload_session_if_absent(self, session_id, path):
        upload_session_id = self.upload_session_id_from_path(path)
        if session_id in self.upload_sessions and upload_session_id in self.upload_sessions[session_id]:
            return None
        parent_id = self.get_item(session_id, path[:len(path) - 1])['id']
        name = path[len(path)-1]
        if session_id not in self.upload_sessions:
            self.upload_sessions[session_id] = {}
        self.upload_sessions[session_id][upload_session_id] = \
            FileSystem.UploadSession(globals.get_constant("CHUNK_SIZE"), session_id, self.db, parent_id, name)

    def add_to_upload_session(self, session_id, path, data):
        try:
            session = self.upload_sessions[session_id][self.upload_session_id_from_path(path)]
        except KeyError:
            raise MashupBadRequestException("This upload session does not exist")
        session.add_data(data)

    def cancel_upload_session(self, session_id, path):
        upload_session_id = self.upload_session_id_from_path(path)
        try:
            session = self.upload_sessions[session_id][upload_session_id]
        except KeyError:
            raise MashupBadRequestException("This upload session does not exist")

        session.close(False)
        del self.upload_sessions[session_id][upload_session_id]
        self.remove(session_id, path)

    def end_upload_session(self, session_id, path):
        upload_session_id = self.upload_session_id_from_path(path)
        try:
            session = self.upload_sessions[session_id][upload_session_id]
        except KeyError:
            raise MashupBadRequestException("This upload session does not exist")

        session.close()
        del self.upload_sessions[session_id][upload_session_id]

    def remove_catalog(self, session_id, catalog_id):
        c = self.db.cursor()
        c.execute('SELECT id, type FROM fs_items WHERE parent=?', (catalog_id,))
        children = c.fetchall()

        for child in children:
            id = child[0]
            type = child[1]
            if type == 'file':
                self.remove_file(session_id, id)
            else:
                self.remove_catalog(session_id, id)

        c.execute('DELETE FROM fs_items WHERE id=?', (catalog_id,))
        c.close()
        self.db.commit()

    def remove_file(self, session_id, file_id):
        clouds_manager = globals.get_resource("modules").clouds_manager

        c = self.db.cursor()
        c.execute('SELECT cloud_id, path FROM fs_disassembly WHERE file_id=?', (file_id,))
        parts_to_remove = c.fetchall()
        c.execute('DELETE FROM fs_disassembly WHERE file_id=?', (file_id,))
        c.execute('DELETE FROM fs_items WHERE id=?', (file_id,))
        c.close()
        self.db.commit()

        for part in parts_to_remove:
            clouds_manager.remove_file(session_id, part[0], part[1])
        
    def remove_item(self, session_id, is_folder, id):
        if is_folder:
            self.remove_catalog(session_id, id)
        else:
            self.remove_file(session_id, id)

    def remove(self, session_id, path):
        result = self.get_item(session_id, path)
        self.remove_item(session_id, result['is_folder'], result['id'])