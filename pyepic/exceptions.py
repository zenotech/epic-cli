

class ConfigurationException(Exception):
    """Exception raised for errors with the client configuration.
    """

    def __init__(self, msg):
        self.msg = msg


class ResponseError(Exception):
    """Exception raised for errors with the response from EPIC
    """

    def __init__(self, msg):
        self.msg = msg