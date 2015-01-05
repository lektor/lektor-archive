import os, time
import posixpath
from ftplib import FTP
import collections

FtpDir = collections.namedtuple("FtpDir", "name tree")
FtpFile = collections.namedtuple("FtpFile", "name size modify")

class FtpDirectory(object):

    def __init__(self, path=''):
        self.path = path
        self.directories = []
        self.files = []
    
    def build_tree(self, ftp):
        ftp.retrlines('MLSD', self.add_leaf)
        
    def add_leaf(self, leaf):
        payload, name = leaf.split('; ')
        #TODO check if the split has worked, could be that there are no facts and just '  name' ('<space><space>name')
        facts = payload.split(';')
        for fact in facts:
            fact_name, fact_value = fact.split('=')
            fact_name = fact_name.lower()
            if fact_name == 'size':
                size = int(fact_value)
            elif fact_name == 'modify':
                #TODO is time format always this way? RFC 3659 says nothing about the modifiy format
                modify = time.mktime(time.strptime(fact_value, "%Y%m%d%H%M%S"))
            elif fact_name == 'type':
                type_target = None
                if fact_value == 'dir':
                    type_target = self.directories
                elif fact_value == 'file':
                    type_target = self.files
        if type_target is self.directories:
            #TODO check if FTP always has posix path format or can handle windows path too
            type_target.append(FtpDir(name, self.__class__(posixpath.join(self.path, name))))
        elif type_target is self.files:
            type_target.append(FtpFile(name, size, modify))
            
    def walk(self):
        for ftp_file in self.files:
            yield self.path, ftp_file
        for ftp_dir in self.directories:
            for path, ftp_file in ftp_dir.tree.walk():
                yield path, ftp_file
    
    def walk_dirs(self):
        for ftp_dir in self.directories:
            yield self.path, ftp_dir
        for ftp_dir in self.directories:
            for path, ftp_dir in ftp_dir.tree.walk_dirs():
                yield path, ftp_dir
                
class FtpTree(FtpDirectory):

    def build_tree(self, ftp):
        super(FtpTree, self).build_tree(ftp)
        for dir in self.directories:
            ftp.cwd(dir.name)
            dir.tree.build_tree(ftp)
            ftp.cwd('..')

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


'''
for path, item in root.walk_dirs():
    print "PATH: "+path
    print "DIR: "+item.name
'''
    
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