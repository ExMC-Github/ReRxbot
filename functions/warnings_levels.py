# 这玩意是警告等级，其实看文件名就能看出来了

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