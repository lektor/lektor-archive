import time
import os
import ftplib
import gzip
from inifile import IniFile
from lektor.utils import to_posix_path, to_os_path
from lektor.exceptions import FTPException, FileNotFound, \
                              ConnectionFailed, IncorrectLogin, \
                              TVFSNotSupported, RootNotFound



class FileInfo(object):
    """A file info object holds metainformation of a file so that changes
    can be detected easily.
    """
    #TODO cleanup and make simpler since we know everything at this point
    def __init__(self, filename, mtime=None, size=None, checksum=None):
        self.filename = filename
        if mtime is not None and size is not None:
            self._stat = (mtime, size)
        else:
            self._stat = None
        self._checksum = checksum

    def _get_stat(self):
        return self._stat

    @property
    def mtime(self):
        """The timestamp of the last modification."""
        return self._get_stat()[0]

    @property
    def size(self):
        """The size of the file in bytes.  If the file is actually a
        dictionary then the size is actually the number of files in it.
        """
        return self._get_stat()[1]

    @property
    def exists(self):
        return self.size >= 0

    @property
    def checksum(self):
        """The checksum of the file or directory."""
        return self._checksum

    def __eq__(self, other):
        if type(other) is not FileInfo:
            return False

        # If mtime and size match, we skip the checksum comparison which
        # might require a file read which we do not want in those cases.
        if self.mtime == other.mtime and self.size == other.size:
            return True

        return self.checksum == other.checksum

    def __ne__(self, other):
        return not self.__eq__(other)


class FTPConnection(object):
    '''Currently assumes that the server has TVFS'''
    #TODO Fallback from TVFS
    def __init__(self, server):
        self._server = server
        self._ftp = None
        #self._tvfs = False
    
    def __del__(self):
        if self._ftp:
            try:
                self._ftp.quit()
            except Exception:
                pass
    
<<<<<<< HEAD
    def _connect(self):
        #TODO if not default port, TLS, etc
        try:
            host = ftplib.FTP(self._server['host'])
        except ftplib.all_errors:
            # Mostly socket.gaierror(Errno 11004) and socket.error (10060)
            raise ConnectionFailed('Connection to host failed!')
        try:
            host.login(self._server['user'], self._server['pw'])
        except ftplib.error_perm:
            raise IncorrectLogin('Login or password incorrect!')
        try:
            #TODO set _tvfs
            if 'tvfs' not in host.sendcmd('FEAT').lower():
                raise TVFSNotSupported('Host does not support TVFS!')
        except ftplib.all_errors:
            raise FTPException
        try:
            host.cwd(self._server['root'])
        except ftplib.error_perm as e:
            if e.message.startswith('550 Can\'t change directory'):
                raise RootNotFound('Root directory \"' \
                                    + self._server['root'] + '\" not found!')
            raise FTPException(e.message)
        return host
    
    def _connection(self):
    
        if self._ftp is None:
            self._ftp = self._connect()
        else:
            try:
                self._ftp.voidcmd('NOOP')
                return self._ftp
            except ftplib.all_errors as e:
                print 'Host timeout, reconnecting...'
                self._ftp = self._connect()
        return self._ftp
    
    def retrbinary(self, filename, dst):
        file = None
        try:
            local_filename = os.path.split(to_os_path(filename))[1]
            f = open(os.path.join(dst, local_filename), 'wb')
            self._connection().retrbinary('RETR ' + filename, f.write)
            f.close()
            file = open(os.path.join(dst, local_filename), 'rb')
        except ftplib.error_perm as e:
            if e.message.startswith('550 Can\'t open'):
                raise FileNotFound('File \"' + filename + '\" not found!')
            raise FTPException(e.message)
        return file
            
class FTPHost(object):

    def __init__(self, server, dst):
        self._server = server
        self._dst = dst
        self._con = FTPConnection(server)
        
    def __del__(self):
        del self._con
        
    def get_file(self, filename):
        return self._con.retrbinary(filename, self._dst)
        
    def put_file(self, src, dst):
        return dst


class Publisher(object):
    
    def __init__(self, src, srv_name, force=False):
        self._src = src
        self._tmp = os.path.join(self._src, '.lektor', 'tmp')
        self._force = force
        self._server = {}
        i = IniFile(os.path.join(os.path.dirname(src), 
                                 'publish.ini')).to_dict()
        self._server['host'] = i[srv_name+'.host']
        self._server['port'] = i[srv_name+'.port']
        self._server['user'] = i[srv_name+'.user']
        self._server['pw']   = i[srv_name+'.pw']
        self._server['root']   = i[srv_name+'.root']
        self._artifacts = {}
    
    def _decode_artifacts_file(self, file, dict):
        f = gzip.GzipFile(fileobj=file)
        for line in f:
            line = line.decode('utf-8').strip().split('\t')
            dict[line[0]] = FileInfo(
                filename=line[0],
                mtime=int(line[1]),
                size=int(line[2]),
                checksum=line[3],
            )
               
    '''def update(self, iterable):
        changed = False
        old_artifacts = set(self.artifacts)

        for artifact_name, info in iterable:
            old_info = self.artifacts.get(artifact_name)
            if old_info != info:
                self.artifacts[artifact_name] = info
                changed = True
            old_artifacts.discard(artifact_name)

        if old_artifacts:
            changed = True
            for artifact_name in old_artifacts:
                self.artifacts.pop(artifact_name, None)

        return changed'''
    
    def _get_remote_artifacts_file(self):
        '''Returns the artifacts file or None if not found.'''
        #TODO some preemptive checks that artifacts.gz is what we except?
        ftp = FTPHost(self._server, self._tmp)
        try:
            return ftp.get_file('.lektor/artifacts.gz')
        except FileNotFound:
            return None
        
    def calculate_change_list(self):
        #TODO handling if artifacts.gz was not found 
        #-> Root dir manipulated?
        #-> Fresh directory / Initial sync?
        f = self._get_remote_artifacts_file()
        if f:
            self._decode_artifacts_file(f, self._artifacts)
            del f
            for item in self._artifacts.items():
                print item
        else:
            print "No file found."


    def publish(self):
        try:
            change_list = self.calculate_change_list()
        except FTPException as e:
            print e
            exit()
        
        print "Publish finished without errors."
            
