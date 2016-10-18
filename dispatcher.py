from response import Response
import globals
import traceback
from exceptions import *


class Dispatcher:
    def __init__(self):
        super().__init__()

    def dispatch(self, request_info):
        modules = globals.get_resource("modules")

        session_id = request_info['HTTP_X_SESSION_ID'] if 'HTTP_X_SESSION_ID' in request_info else ""

        uri_parts = request_info['PATH_INFO'].split('/')
        uri_parts = list(filter(None, uri_parts))
        try:
            if session_id != '' and not modules.authenticator.is_valid_session(session_id):
                raise MashupAccessException("Invalid session id")

            params = request_info['QUERY_PARAMS']
            if len(uri_parts) == 0:
                # root request
                raise MashupBadRequestException('There are no actions on the root resource')
            else:
                resource_name = uri_parts[0]
                uri_parts = uri_parts[1:]
                if resource_name == 'clouds':
                    return modules.clouds_manager.handle_cloud_request(session_id, uri_parts,request_info['REQUEST_METHOD'],
                                                          params, request_info['HTTP_BODY'], request_info['HEADERS'])
                elif resource_name == 'files':
                    return modules.file_system.accept_request(session_id, request_info['REQUEST_METHOD'], uri_parts,
                                                              params, request_info['HTTP_BODY'], request_info['HEADERS'])
                elif resource_name == 'login':
                    return modules.authenticator.accept_login_connection(
                        request_info['REQUEST_METHOD'], request_info['HTTP_BODY'])
                else:
                    raise MashupNameException('The selected resource does not exist')
        except MashupException as e:
            return Response.error_response(e.message, e.error_status_code)
        except Exception as e:
            traceback.print_exc()
            print(e.args)
            return Response.internal_error()