import abc


class CloudAccount(metaclass=abc.ABCMeta):
    @classmethod
    def accept_connection(cls, session_id, method, path, query_params, body, headers):
        """
        Called when an incoming request to the cloud is received. Returns a response to the request.
        """
        if len(path) == 1 and path[0] == 'auth_info':
            return cls.start_authorization(session_id)
        return None

    @classmethod
    @abc.abstractmethod
    def start_authorization(cls, session_id):
        """
        Begins authorization for a given cloud
        :param session_id: id of a session which requested to add the cloud
        :return: redirection response
        :raise MashupCloudOperationException: if operation failed
        """
        return

    @abc.abstractmethod
    def authenticate(self, authentication_data):
        """
        Using the authentication_data from the cloud database, authenticates the cloud.
        :param authentication_data: Authentication data from the cloud database
        :raise MashupAccessException: if authentication failed
        """
        return

    @abc.abstractmethod
    def download(self, file_path):
        """
        Downloads a file from the cloud's mashup catalog.
        :param file_path: Path to the file in the cloud's mashup catalog
        :return: File contents in a binary form
        :raise MashupAccessException: if authentication failed
        :raise MashupCloudOperationException: if download failed
        """
        return

    @abc.abstractmethod
    def upload(self, file_path, file_data):
        """
        Downloads a file from the cloud's mashup catalog.
        :param file_path: Path to the file in the cloud's mashup catalog
        :param file_data: File contents in a binary form
        :raise MashupAccessException: if authentication failed
        :raise MashupCloudOperationException: if upload failed
        """
        return

    @abc.abstractmethod
    def remove(self, file_path):
        """
        Removes a file from the cloud's mashup catalog.
        :param file_path: Path to the file in the cloud's mashup catalog
        :raise MashupAccessException: if authentication failed
        :raise MashupCloudOperationException: if removal failed
        """
        return

    @abc.abstractmethod
    def prepare_mashup(self):
        """
        Prepares the cloud to be used with mashup
        :param file_path: Path to the file in the cloud
        :raise MashupAccessException: if authentication failed
        :raise MashupCloudOperationException: if preparation failed
        """
        return

    @abc.abstractmethod
    def clean_mashup(self):
        """
        Removes all mashup related files from the cloud.
        :raise MashupAccessException: if authentication failed
        :raise MashupCloudOperationException: if cleaning failed
        """
        return