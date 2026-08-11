class NotFoundExRFyError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message

    def __str__(self):
        if self.message:
            return self.message
        return ""

class NotFoundBuiltTargetError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message

    def __str__(self):
        if self.message:
            return self.message
        return ""