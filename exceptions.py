# Class purely for classification purposes
class MashupException(Exception):
    def __init__(self, message, error_status_code):
        super().__init__(message)
        self.error_status_code = error_status_code
        self.message = message


class MashupNameException(MashupException):
    def __init__(self, message=""):
        super().__init__(message, "404 Not Found")


class MashupBadRequestException(MashupException):
    def __init__(self, message=""):
        super().__init__(message, "400 Bad Request")


class MashupMethodException(MashupException):
    def __init__(self, message=""):
        super().__init__(message, '405 Method Not Allowed')

class MashupAccessException(MashupException):
    def __init__(self, message="", log_message = None):
        super().__init__(message, '403 Forbidden')
        self.log_message = log_message or message

class MashupCloudOperationException(MashupException):
    def __init__(self, message="", log_message = None):
        super().__init__(message, '500 Internal Server Error')
        self.log_message = log_message or message