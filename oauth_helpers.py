import crypto_helpers
import globals
import urllib.parse
import http_helpers
import json
from response import Response
from exceptions import *


def start_authorization(cls, session_id, client_id, uri, additional_params={}, redirect_path="oauth_authenticate"):
    if session_id == '':
        raise MashupAccessException("You need to be logged in to perform this operation")

    api_requests = None
    try:
        api_requests = cls.oauth_api_requests
    except AttributeError:
        cls.oauth_api_requests = {}
        api_requests = cls.oauth_api_requests

    csrf_token = crypto_helpers.generate_token(api_requests, 32)
    api_requests[csrf_token] = {'session_id': session_id}

    url_params = additional_params
    url_params['client_id'] =  client_id
    url_params['response_type'] = 'code'
    url_params['redirect_uri'] = globals.get_resourse("modules").clouds_manager.get_cloud_uri(cls) + "/" + redirect_path
    url_params['state'] = csrf_token

    uri = uri + '?' + urllib.parse.urlencode(url_params)

    result = {}
    result['authorize_uri'] = uri
    api_requests[csrf_token]['redirect_uri'] = url_params['redirect_uri']
    return Response.from_dictionary(result)

def finish_authorization(cls, oauth_token_link, code, client_id, client_secret, csrf_token):
    try:
        if csrf_token in cls.oauth_api_requests:
            session_id = cls.oauth_api_requests[csrf_token]['session_id']
            redirect_uri = cls.oauth_api_requests[csrf_token]['redirect_uri']

            params = {
                'code': code,
                'grant_type': 'authorization_code',
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': redirect_uri
            }
            url_parsed = urllib.parse.urlparse(oauth_token_link)
            auth_data = json.loads(http_helpers.http_req(url_parsed.scheme + "://" + url_parsed.netloc,
                                                         'post', url_parsed.path, params))
            auth_data['mashup_session_id'] = session_id
            del cls.oauth_api_requests[csrf_token]
            return auth_data
        else:
            raise MashupAccessException()
    except AttributeError:
        raise MashupAccessException("Session is not valid anymore")