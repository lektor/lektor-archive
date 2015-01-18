import ftplib
import posixpath
from inifile import IniFile
from lektor.db import to_posix_path
from lektor.exceptions import FileNotFound, ConnectionFailed, \
                              IncorrectLogin, TVFSNotSupported

import time
import os

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
    
    def _connect(self):
        try:
            host = ftplib.FTP(self._server['host'])
        except ftplib.all_errors as e:
            # Mostly socket.gaierror(Errno 11004) and socket.error (10060)
            #print "Connection to host failed!"
            raise ConnectionFailed("Connection to host failed!")
            #exit()
        try:
            host.login(self._server['user'], self._server['pw'])
        except ftplib.error_perm as e:
            #print "Login or password incorrect!"
            # XXX: raise other error instead of exit?
            raise IncorrectLogin('Login or password incorrect!')
            #exit()
        try:
            if 'tvfs' not in host.sendcmd('FEAT').lower():
                raise TVFSNotSupported('Host does not support TVFS!')
        except ftplib.all_errors as e:
            # XXX: raise other error instead of exit?
            print e
            exit()
        return host
    
    def _connection(self):
    #TODO if not default port, TLS, etc
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
        
    def retrbinary(self, filename):
        file = None
        try:
            file = self._connection.retrbinary(filename)
        except ftplib.all_errors as e:
            print e
        return file
            
class FTPHost(object):

    def __init__(self, server):
        self._server = server
        self._con = FTPConnection(server)
        
    def __del__(self):
        del self._con
        
    def get_file(filename):
        file = self._con.retrbinary(filename)
        
    def put_file(src, dst):
        return dst


class Publisher(object):
    
    def __init__(self, src, dst, srv_name, force=False):
        self._src = src
        self._dst = to_posix_path(dst)
        self._force = force
        self._server = {}
        i = IniFile(os.path.join(os.path.dirname(source), 'publish.ini')).to_dict()
        self._server['host'] = i[srv_name+'.host']
        self._server['port'] = i[srv_name+'.port']
        self._server['user'] = i[srv_name+'.user']
        self._server['pw']   = i[srv_name+'.pw']
        self._server['root']   = i[srv_name+'.root']
          
    def get_ftp_root(self, root):
        ftp_root = os.path.join(*root.split(self.source)[1::])
        #remove preceding slash
        ftp_root = ftp_root.replace(os.path.sep, '', 1)
        ftp_root = ftp_root.replace(os.path.sep, self.ftp.host.sep)
        # XXX: ftp_root is now unicode!
        ftp_root = self.ftp.host.path.join(self.destination, ftp_root)
        return ftp_root
    
    def initial_upload(self):
        try:
            orig_root = self.source
            for root, dirs, files in os.walk(self.source):
                ftp_root = self.get_ftp_root(root)
                # XXX: use self.chdir
                self.ftp.host.chdir(ftp_root)
                
                for dir in dirs:
                    # XXX: use self.mkdir
                    self.ftp.host.mkdir(dir)
                    
                for file in files:
                    src = os.path.join(root, file)
                    tgt = self.ftp.host.path.join(ftp_root, unicode(file))
                    # XXX: use self.upload
                    print "Uploading: " + file
                    self.ftp.host.upload(src, tgt)
        except FTPError as e:
            print e.strerror
            # XXX: raise error
            exit()
    
    def _get_artifact_listing(self):
        ftp = FTPHost(server)
        listing = ftp.get_file(posixpath.join(dst, 'artifacts.gz'))
        return listing
        
    def calculate_change_list(self):
        artifacts = self._get_artifact_listing()
        
    
    def publish(self):

        change_list = self.calculate_change_list()
        
        
        
        #print con.ftp.pwd()
        #time.sleep(5)
        #print con.ftp.pwd()
        #time.sleep(12)
        #print con.ftp.pwd()
        #self.ftp.connect()
        #self.ftp.chdir(self.destination)
        #TODO if destination is empty:
        #self.initial_upload()
        print "Publish finished without errors."
            






'''
class FtpConnection(object):

    def __init__(self, server_url, user, pw)
        self._server_url = server_url
        self._user = user
        self._pw = pw
        self._ftp = None
        
    @property
    def ftp(self):
        if self.ftp is None:
            self._ftp = FTP(self._server_url, self._user, self._pw)
        return self._ftp
        
    def connect(self):
        self._ftp = FTP(self._server_url, self._user, self._pw)
    
        
            
            
server_url = "127.0.0.1"
user = "Tester"
pw = "tester"

wd = 'deleteTest_2_2_2'

ftp = FTP(server_url, user, pw)
ftp.cwd(wd)
root = FtpTree()
root.build_tree(ftp)

#delete root folder (with all folders and files in it)
for path, file in root.walk():
    ftp.delete(posixpath.join(path, file.name))
dirs = []
for path, dir in root.walk_dirs():
    dirs.append(posixpath.join(path, dir.name))    
for dir in dirs[::-1]:
    ftp.rmd(dir)
ftp.rmd(ftp.pwd())


    
######################################
#old
######################################


class Publisher():

    def __init__(self, root_path, remote_path):
        self.root_path = root_path
        self.remote_path = remote_path

def abspatha(*paths):
    filename = os.path.join(*(paths or ('',)))
    if not os.path.isabs(filename):
        filename = os.path.join(self.remote_path, filename)        
    return filename

root_dir = "/Client1"
    
def abspath(*paths):
    filepath = posixpath.join(*(paths or ('',)))
    if not posixpath.isabs(filepath):
        filepath = posixpath.join(root_dir, filepath)
    return filepath
        
def parse_remote_files(ftp, directory=''): 

    wd = abspath(directory)

    #TODO make function for this
    if ftp.pwd() != wd:
        ftp.cwd(wd)

    rdict = {}
    rlist = []
    ftp.retrlines('MLSD', rlist.append)

    #TODO look at every fact to determine what it is
    for f in rlist:
        unpack = f.split(';')
        type = unpack[0]
        data = unpack[1:]
        if type.startswith("type="):
            type = type.split('=')[1]
            if type == 'dir':
                folder = posixpath.join(wd, data[1].strip())
                #TODO directory dict to create or delete dicts before updating files later
                rdict[folder] = 'd'
                rdict.update(parse_remote_files(ftp, folder))
            elif type == 'file':
                rdict[posixpath.join(wd, data[2].strip())] = (data[0].split('=')[1], data[1].split('=')[1])
            else:
                continue #throw MLSD error
            
        else:
            continue #throw MLSD error
    return rdict

    
#TODO connect to absolute path of cwd and check it
#server_url = "127.0.0.1"
#root_dir = "/Client1"
#ftp = FTP(server_url, "Tester", "tester")

#rdict = parse_remote_files(ftp, root_dir)
    
#print rdict

#['type=file;modify=20150103222118;size=0; asdf.txt', 'type=dir;modify=20150103222126; testsasdf']

'''