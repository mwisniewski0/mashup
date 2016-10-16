import copy
import json


class Response:
    def __init__(self, status, headers, body):
        self.status = status
        self.headers = headers
        self.body = body

    def send(self, start_response, encoding, print_error_code = True):
        submittable_headers = copy.deepcopy(self.headers)

        # find content-type and charset to it
        appended = False
        for i in range(len(submittable_headers)):
            if submittable_headers[i][0].lower() == 'content-type':
                new_value = submittable_headers[i][1] + '; charset='+encoding
                submittable_headers[i] = ('Content-type', new_value)
                appended = True
                break
        if not appended:
            submittable_headers.append(('Content-type', 'text/plain; charset='+encoding))

        start_response(self.status, submittable_headers)

        status_code = int(self.status.split(' ')[0])
        return [((self.status + "\n" if status_code >= 300 and print_error_code else '') + self.body).encode(encoding)]

    @staticmethod
    def from_text(text):
        return Response("200 OK", [('Content-type', 'text/plain')], text)

    @staticmethod
    def from_dictionary(dict):
        return Response("200 OK", [('Content-type', 'application/json')], json.dumps(dict))

    @staticmethod
    def bad_request(message = ''):
        return Response("400 Bad Request", [('Content-type', 'text/plain')],
                        message)

    @staticmethod
    def error_response(message, error_status_code):
        return Response(error_status_code, [('Content-type', 'text/plain')],
                        message)

    @staticmethod
    def internal_error():
        return Response("500 Internal Server Error", [('Content-type', 'text/plain')],
                        "Internal Server Error")

    @staticmethod
    def ok():
        return Response("200 OK", [('Content-type', 'text/plain')], '')