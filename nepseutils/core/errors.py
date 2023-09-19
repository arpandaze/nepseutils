class LocalException(Exception):
    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return self.message


class GlobalError(Exception):
    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return self.message
