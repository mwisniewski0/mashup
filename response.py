import copy
import json


class Response:
    def __init__(self, status, headers, body):
        self.status = status
        self.headers = headers
        self.body = body

    def send(self, start_response, encoding, print_error_code = True):
        submittable_headers = copy.deepcopy(self.headers)

        if isinstance(self.body, str):
            # find content-type and charset to it
            if 'Content-type' in submittable_headers:
                new_value = submittable_headers['Content-type'] + '; charset='+encoding
                submittable_headers['Content-type'] = new_value
            else:
                submittable_headers.append({'Content-type': 'text/plain; charset='+encoding})

            start_response(self.status, [(k, v) for k,v in submittable_headers.items()])

            status_code = int(self.status.split(' ')[0])
            return [((self.status + "\n" if status_code >= 300 and print_error_code else '') + self.body).encode(encoding)]
        else:
            start_response(self.status, [(k, v) for k,v in submittable_headers.items()])
            return [self.body]

    @staticmethod
    def from_binary(binary):
        return Response("200 OK", {'Content-type': 'application/octet-stream'}, binary)

    @staticmethod
    def from_text(text):
        return Response("200 OK", {'Content-type': 'text/plain'}, text)

    @staticmethod
    def from_json(dict):
        return Response("200 OK", {'Content-type': 'application/json'}, json.dumps(dict))

    @staticmethod
    def bad_request(message = ''):
        return Response("400 Bad Request", {'Content-type': 'text/plain'},
                        message)

    @staticmethod
    def error_response(message, error_status_code):
        return Response(error_status_code, {'Content-type': 'text/plain'},
                        message)

    @staticmethod
    def internal_error():
        return Response("500 Internal Server Error", {'Content-type': 'text/plain'},
                        "Internal Server Error")

    @staticmethod
    def ok():
        return Response("200 OK", {'Content-type': 'text/plain'}, '')