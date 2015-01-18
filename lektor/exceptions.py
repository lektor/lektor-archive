class LektorException(RuntimeError):
    pass
    

class FTPException(LektorException):
    pass


class RootNotFound(FTPException):
    pass
    
    
class FileNotFound(FTPException):
    pass

    
class ConnectionFailed(FTPException):
    pass
    

class IncorrectLogin(FTPException):
    pass
    
    
class TVFSNotSupported(FTPException):
    pass
    
    
