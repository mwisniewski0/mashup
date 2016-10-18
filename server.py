from response import Response
import urllib.parse
from pprint import pprint


class RESTServer:
    def __init__(self, dispatcher):
        self.dispatcher = dispatcher

    def is_encoding_supported(self, encoding):
        encoding_lower = encoding.lower()
        return encoding_lower == 'ascii' or encoding_lower == 'utf-8' or encoding_lower == 'utf-16'

    def get_handle_http(self):
        def handle_http(environ, start_response):
            environ['REQUEST_METHOD'] = environ['REQUEST_METHOD'].lower()
            environ['CONTENT_LENGTH'] = environ['CONTENT_LENGTH'] if 'CONTENT_LENGTH' in environ else "0"
            environ['QUERY_PARAMS'] = dict(urllib.parse.parse_qsl(environ['QUERY_STRING']))
            environ['HEADERS'] = {key[5:]: value for key, value in environ.items() if key.startswith('HTTP_')}

            # making sure that content-length is convertible to int
            if environ['CONTENT_LENGTH'].strip() == '':
                environ['CONTENT_LENGTH'] = 0
            else:
                environ['CONTENT_LENGTH'] = int(environ['CONTENT_LENGTH'])

            # default encoding is UTF-8
            encoding = 'utf-8'

            # read the charset if it is available
            if 'HTTP_CHARSET' in environ:
                encoding = environ['HTTP_CHARSET'].lower()

            if self.is_encoding_supported(encoding):
                # decode the body of the request
                environ['HTTP_BODY'] = environ['wsgi.input'].read(environ['CONTENT_LENGTH'])
                if 'CONTENT_TYPE' in environ and environ['CONTENT_TYPE'].lower() != 'application/octet-stream':
                    try:
                        environ['HTTP_BODY'] = environ['HTTP_BODY'].decode(encoding)
                    except Exception:
                        return Response.bad_request('Body is not encoded as expected')
                response = self.dispatcher.dispatch(environ)
                return response.send(start_response, encoding)
            else:
                return Response('415 Unsupported Media Type', [('Content-type', 'text/plain')],
                                'Selected encoding is not supported').send(start_response, 'utf-8')
        return handle_http