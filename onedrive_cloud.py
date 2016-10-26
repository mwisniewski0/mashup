import cloud_account
import http_helpers
import oauth_helpers
import json
from response import Response
import globals
from exceptions import *
import traceback


class OneDrive(cloud_account.CloudAccount):
    @classmethod
    def start_authorization(cls, session):
        return oauth_helpers.start_authorization(cls, session, globals.get_constant("ONEDRIVE_PUBLIC"),
                                                 'https://login.live.com/oauth20_authorize.srf',
                                                 {'scope':'onedrive.readwrite offline_access'})

    @classmethod
    def accept_connection(cls, session_id, method, path_segments, query_params, body, headers):
        response = super().accept_connection(session_id, method, path_segments, query_params, body, headers)
        if response is not None:
            return response
        if len(path_segments) == 1 and path_segments[0] == 'oauth_authenticate':
            auth_data = oauth_helpers.finish_authorization(cls, 'https://login.live.com/oauth20_token.srf',
                  query_params['code'], globals.get_constant('ONEDRIVE_PUBLIC'),
                  globals.get_constant('ONEDRIVE_PRIVATE'), query_params['state'])
            globals.get_resource("modules").clouds_manager.add_cloud_authentication(cls, auth_data['mashup_session_id'],
                                                                                    auth_data['refresh_token'].encode('utf-8'))
            return Response.from_text("This OneDrive account has been added to your MashUp")
        else:
            raise MashupNameException("Cloud resource not found")

    def http_req(self, method, path, query = {}, body = None, headers = {}, return_full_response = False):
        headers['Authorization'] = "bearer {}".format(self.access_token)
        return http_helpers.http_req(self.connection,method,self.api_path + path, body, query, headers, return_full_response)

    def reauthenticate(self):
        clouds_manager = globals.get_resource("modules").clouds_manager
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        params = {'client_id': globals.get_constant("ONEDRIVE_PUBLIC"),
                  'redirect_uri': clouds_manager.get_cloud_uri(OneDrive)+'/oauth_authenticate',
                  'client_secret': globals.get_constant("ONEDRIVE_PRIVATE"),
                  'refresh_token': self.refresh_token,
                  'grant_type': 'refresh_token'}
        response = http_helpers.http_req('https://login.live.com', 'POST', '/oauth20_token.srf', params, {})
        response = json.loads(response)
        self.access_token = response['access_token']

    def authenticate(self, authentication_data):
        # create connection for manual http requests (onedrivesdk turns out to be insufficient)
        self.api_server = 'https://api.onedrive.com'
        self.api_path = '/v1.0/'
        self.refresh_token = authentication_data.decode('utf-8')
        self.reconnect()
        self.reauthenticate()

    def reconnect(self):
        self.connection = http_helpers.start_connection(self.api_server)

    def request_template(self, action):
        trials = 0
        while trials < 8:
            try:
                trials += 1
                return action()
            # find the actual exception name for lack of access
            except MashupException as e:
                raise e
            except Exception as e:
                traceback.print_exc()
                self.reconnect()
                self.reauthenticate()
        raise MashupCloudOperationException("OneDrive request failed")

    def upload(self, file_path, file_data):
        def action():
            return self.http_req("PUT", 'drive/special/approot:/'+file_path+':/content', {}, file_data)
        self.request_template(action)

    def download(self, file_path):
        def action():
            data, full_response = self.http_req("GET", 'drive/special/approot:/'+file_path+':/content',return_full_response=True)
            if full_response.status == 302:
                location = full_response.getheader('Location')
                data, response = http_helpers.direct_http_req(location, "GET", return_full_response=True)
                if response.status >= 300:
                    raise MashupCloudOperationException('Download failed')
                return data
            else:
                raise MashupCloudOperationException('Download failed')
        return self.request_template(action)

    def remove(self, file_path):
        def action():
            return self.http_req("DELETE", 'drive/special/approot:/'+file_path)
        self.request_template(action)

    def exists(self, file_path):
        def action():
            data, full_response = self.http_req("GET", 'drive/special/approot:/'+file_path+':/content',return_full_response=True)
            if full_response.status == 302:
                return True
            elif full_response.status == 404:
                return False
            else:
                raise MashupCloudOperationException('Check failed')
        return self.request_template(action)

    def prepare_mashup(self):
        def action():
            # this will create the approot
            return self.http_req('GET', 'drive/special/approot')
        self.request_template(action)

    def clean_mashup(self):
        def action():
            return self.http_req("DELETE", 'drive/special/approot')
        self.request_template(action)