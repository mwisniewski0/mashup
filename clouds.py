from dropbox_cloud import Dropbox
from onedrive_cloud import OneDrive
from exceptions import *
from response import Response
import globals
import random


class CloudsManager:
    def __init__(self, db):
        self.session_clouds = {}

        self.db = db
        c = self.db.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS cloud_accounts (cloud_id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, cloud_type TEXT, authentication_data BLOB, quota INTEGER, name TEXT)")
        c.close()
        self.db.commit()

    def get_max_authorization_data_size(self):
        return 4096

    type_to_cloud = {'dropbox': Dropbox, 'onedrive': OneDrive}
    def get_cloud_class_from_type(self, type):
        type_to_cloud = CloudsManager.type_to_cloud

        if type in type_to_cloud:
            return type_to_cloud[type]
        return None

    def get_type_from_cloud_class(self, cloud_class):
        class_to_type = {v: k for k, v in CloudsManager.type_to_cloud.items()}
        if cloud_class in class_to_type:
            return class_to_type[cloud_class]
        return None

    def get_cloud_uri(self, cloud_class):
        cloud_type = self.get_type_from_cloud_class(cloud_class)
        if (cloud_type == None):
            raise Exception("Invalid cloud class")
        return globals.get_constant("SERVICE_ADDRESS")+"/clouds/"+cloud_type

    def handle_cloud_request(self, session_id, path_segments, method, query_params, body, headers):
        if len(path_segments) > 0:
            if path_segments[0] == 'list':
                return Response.from_json(self.list_clouds(session_id))
            else:
                cloud = self.get_cloud_class_from_type(path_segments[0])
                if cloud is None:
                    raise MashupNameException("Cloud type not found")
                path_segments_to_pass = path_segments[1:]
                return cloud.accept_connection(session_id, method, path_segments_to_pass, query_params, body, headers)
        else:
            raise MashupBadRequestException("No calls are allowed on root cloud resource")

    def upload_anywhere(self, session_id, cloud_id, chunk):
        cloud = self.session_clouds[session_id][cloud_id]
        def generate_name(allowed_chars, length):
            name = ""
            for i in range(length):
                name += random.choice(allowed_chars)
            if cloud.exists(name):
                return generate_name(allowed_chars, length)
            else:
                return name

        name = generate_name("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890", 16)
        cloud.upload(name, chunk)
        return name

    def list_clouds(self, session_id, fetch_taken_space=True):
        authenticator = globals.get_resource("modules").authenticator
        fs = globals.get_resource("modules").file_system
        username = authenticator.derive_username_from_session_id(session_id)

        c = self.db.cursor()
        # try to merge the taken space to below query
        c.execute("SELECT cloud_id, quota, name, cloud_type FROM cloud_accounts WHERE username=?", (username,))
        clouds = [{'id': result[0], 'quota': result[1], 'name': result[2], 'provider': result[3]} for result in c]
        c.close()
        self.db.commit()

        if fetch_taken_space:
            for cloud in clouds:
                cloud['taken'] = fs.get_cloud_taken_space(username, cloud['id'])

        return clouds

    def add_cloud_to_session(self, session_id, cloud_account_id, cloud_class, authentication_data):
        if session_id in self.session_clouds:
            cloud = cloud_class()
            cloud.authenticate(authentication_data)
            self.session_clouds[session_id][cloud_account_id] = cloud
        else:
            raise MashupAccessException("Session is not available")

    def get_cloud(self, session_id, cloud_id):
        if session_id in self.session_clouds:
            if cloud_id in self.session_clouds[session_id]:
                return self.session_clouds[session_id][cloud_id]
            else:
                raise MashupCloudOperationException('Cloud not in the database')
        else:
            raise MashupAccessException("Invalid session id")

    def store_file(self, session_id, cloud_id, path, content):
        self.get_cloud(session_id, cloud_id).upload(path, content)

    def retrieve_file(self, session_id, cloud_id, path):
        return self.get_cloud(session_id, cloud_id).download(path)

    def remove_file(self, session_id, cloud_id, path):
        self.get_cloud(session_id, cloud_id).remove(path)

    def load_session(self, session_id):
        authenticator = globals.get_resource("modules").authenticator
        username = authenticator.derive_username_from_session_id(session_id)

        c = self.db.cursor()
        c.execute("SELECT cloud_id, cloud_type, authentication_data FROM cloud_accounts WHERE username=?", (username,))
        clouds = c.fetchall()
        c.close()
        self.db.commit()

        self.session_clouds[session_id] = {}

        for cloud in clouds:
            authentication_data = authenticator.session_decrypt(session_id, cloud[2])
            self.add_cloud_to_session(session_id, cloud[0], self.get_cloud_class_from_type(cloud[1]), authentication_data)

    def add_cloud_authentication(self, cloud_class, session_id, authentication_data):
        authenticator = globals.get_resource("modules").authenticator
        encrypted_authentication_data = authenticator.session_encrypt(session_id, authentication_data)
        username = authenticator.derive_username_from_session_id(session_id)

        if (cloud_class == None):
            raise MashupBadRequestException("Selected cloud type is not supported")

        if len(encrypted_authentication_data) > self.get_max_authorization_data_size():
            raise MashupBadRequestException("Authorization data is too large")

        cloud_type = self.get_type_from_cloud_class(cloud_class)
        if (cloud_type == None):
            raise Exception("Invalid cloud class")

        # initialize the cloud
        cloud = cloud_class()
        cloud.authenticate(authentication_data)
        cloud.prepare_mashup()

        c = self.db.cursor()
        c.execute("INSERT INTO cloud_accounts VALUES (NULL, ?, ?, ?, ?, ?)",
                  (username, cloud_type, encrypted_authentication_data, globals.get_constant("DEFAULT_QUOTA"),
                   globals.get_constant("DEFAULT_CLOUD_NAME")))
        cloud_id = c.lastrowid
        c.close()
        self.db.commit()

        self.add_cloud_to_session(session_id, cloud_id, cloud_class, authentication_data)