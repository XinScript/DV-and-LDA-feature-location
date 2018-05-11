class GitNotFoundError(FileNotFoundError):
    def __init__(self,*args):
        super().__init__(*args)

class NotGitProjectError(Exception):
    def __init__(self, *args):
        super().__init__(*args)

class InstantiationError(Exception):
    def __init__(self, *args):
        super().__init__(*args)
