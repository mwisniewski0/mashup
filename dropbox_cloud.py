import cloud_account
import dropbox
import oauth_helpers
import http_helpers
import globals
from response import Response
import random
import base64
from exceptions import *


class Dropbox(cloud_account.CloudAccount):
    @classmethod
    def start_authorization(cls, session_id):
        return oauth_helpers.start_authorization(cls, session_id, globals.get_constant("DROPBOX_PUBLIC"),
                                                 'https://www.dropbox.com/1/oauth2/authorize')

    @classmethod
    def accept_connection(cls, session_id, method, path_segments, query_params, body, headers):
        response = super().accept_connection(session_id, method, path_segments, query_params, body, headers)
        if response is not None:
            return response
        if len(path_segments) == 1 and path_segments[0] == 'oauth_authenticate':
            auth_data = oauth_helpers.finish_authorization(cls, 'https://api.dropbox.com/1/oauth2/token',
                  query_params['code'], globals.get_constant('DROPBOX_PUBLIC'),
                  globals.get_constant('DROPBOX_PRIVATE'), query_params['state'])
            globals.get_resource("modules").clouds_manager.add_cloud_authentication(cls, auth_data['mashup_session_id'],
                                                                                    auth_data['access_token'].encode('utf-8'))
            return Response.from_text("This Dropbox account has been added to your MashUp")
        else:
            raise MashupNameException("Cloud resource not found")

    def __init__(self):
        self.mashup_catalog = "/__mashup__files__"

    def get_mashup_path(self, path):
        return self.mashup_catalog + "/" + path

    def authenticate(self, authentication_data):
        self.account_token = authentication_data.decode('utf-8')
        self.dbx = dropbox.Dropbox(self.account_token)

        # API V1 is required for range retrieval
        self.dbx_v1 = dropbox.client.DropboxClient(self.account_token)
        try:
            user_data = self.dbx.users_get_current_account()
            print('Authenticated on Dropbox: ', user_data)
        except dropbox.exceptions.AuthError as e:
            print('Authentication failed')
            raise MashupAccessException("Authentication for Dropbox failed")

    def download(self, file_path):
        try:
            meta, response = self.dbx.files_download(self.get_mashup_path(file_path))
            return response.raw.read()
        except dropbox.exceptions.AuthError as e:
            print('Authentication failed')
            raise MashupAccessException("Authentication for Dropbox failed")
        except Exception as e:
            raise MashupCloudOperationException("Download from Dropbox has failed")

    def download_part(self, file_path, offset=0, length=None):
        try:
            with self.dbx_v1.get_file(self.get_mashup_path(file_path), start=offset, length=length) as f:
                return f.read()
        except Exception as e:
            raise MashupCloudOperationException("Download from Dropbox has failed")

    def upload(self, file_path, file_data):
        try:
            self.dbx.files_upload(file_data, self.get_mashup_path(file_path), dropbox.files.WriteMode('overwrite', None))
        except dropbox.exceptions.AuthError as e:
            print('Authentication failed')
            raise MashupAccessException("Authentication for Dropbox failed")
        except Exception as e:
            raise MashupCloudOperationException("Upload to Dropbox has failed")

    def remove(self, file_path):
        try:
            self.dbx.files_delete(self.get_mashup_path(file_path))
        except dropbox.exceptions.AuthError as e:
            print('Authentication failed')
            raise MashupAccessException("Authentication for Dropbox failed")
        except Exception as e:
            raise MashupCloudOperationException("Removal from Dropbox has failed")

    def exists(self, file_path):
        try:
            self.dbx.files_get_metadata(self.get_mashup_path(file_path))
            return True
        except:
            return False

    def prepare_mashup(self):
        try:
            self.dbx.files_create_folder(self.mashup_catalog)
        except dropbox.exceptions.AuthError as e:
            print('Authentication failed')
            raise MashupAccessException("Authentication for Dropbox failed")
        except Exception as e:
            raise MashupCloudOperationException("Preparing Dropbox for service use has failed.\n"
                                                "Did you use this cloud account for MashUp before?\n"
                                                "If so, try to remove __mashup__files__ from your Dropbox")

    def clean_mashup(self):
        try:
            self.dbx.files_delete(self.mashup_catalog)
        except dropbox.exceptions.AuthError as e:
            print('Authentication failed')
            raise MashupAccessException("Authentication for Dropbox failed")
        except Exception as e:
            raise MashupCloudOperationException("Cleaning Dropbox from service files has failed")