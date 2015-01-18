class LektorException(RuntimeError):
    pass
    
    
class FileNotFound(LektorException):
    pass

    
class ConnectionFailed(LektorException):
    pass
    

class IncorrectLogin(LektorException):
    pass
    
class TVFSNotSupported(LektorException):
    pass