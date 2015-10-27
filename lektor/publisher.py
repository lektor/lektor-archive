import os
import errno
import hashlib
import posixpath
import subprocess
from cStringIO import StringIO

from werkzeug import urls

from lektor.utils import portable_popen


class Publisher(object):

    def __init__(self, env, output_path):
        self.env = env
        self.output_path = os.path.abspath(output_path)

    def publish(self, target_url):
        raise NotImplementedError()


class ExternalPublisher(Publisher):

    def get_command_line(self, target_url):
        raise NotImplementedError()

    def publish(self, target_url):
        argline = self.get_command_line(target_url)
        cmd = portable_popen(argline, stdout=subprocess.PIPE)
        try:
            while 1:
                line = cmd.stdout.readline()
                if not line:
                    break
                yield line.rstrip().decode('utf-8', 'replace')
        finally:
            cmd.wait()


class RsyncPublisher(ExternalPublisher):

    def get_command_line(self, target_url):
        argline = ['rsync', '-azv']
        target = []

        if target_url.port is not None:
            argline.append('-e')
            argline.append('ssh -p ' + str(target_url.port))

        if target_url.username is not None:
            target.append(target_url.username.encode('utf-8') + '@')
        target.append(target_url.ascii_host)
        target.append(':' + target_url.path.encode('utf-8').rstrip('/') + '/')

        argline.append(self.output_path.rstrip('/\\') + '/')
        argline.append(''.join(target))
        return argline


class FtpConnection(object):

    def __init__(self, url):
        self.con = self.make_connection()
        self.url = url
        self.log_buffer = []
        self._known_folders = set()

    def make_connection(self):
        from ftplib import FTP
        return FTP()

    def drain_log(self):
        log = self.log_buffer[:]
        del self.log_buffer[:]
        for chunk in log:
            for line in chunk.splitlines():
                if isinstance(line, str):
                    line = line.decode('utf-8', 'replace')
                yield line.rstrip()

    def connect(self):
        options = self.url.decode_query()

        log = self.log_buffer
        log.append('000 Connecting to server ...')
        try:
            log.append(self.con.connect(self.url.ascii_host,
                                        self.url.port or 21))
        except Exception as e:
            log.append('000 Could not connect.')
            log.append(str(e))
            return False

        try:
            log.append(self.con.login(self.url.username.encode('utf-8'),
                                      self.url.password.encode('utf-8')))
        except Exception as e:
            log.append('000 Could not authenticate.')
            log.append(str(e))
            return False

        passive = options.get('passive') in ('on', 'yes', 'true', '1', None)
        log.append('000 Using passive mode: %s' % (passive and 'yes' or 'no'))
        self.con.set_pasv(passive)

        try:
            log.append(self.con.cwd(self.url.path.encode('utf-8')))
        except Exception as e:
            log.append(str(e))
            return False

        log.append('000 Connected!')
        return True

    def mkdir(self, path, recursive=True):
        if isinstance(path, unicode):
            path = path.encode('utf-8')
        if path in self._known_folders:
            return
        dirname, basename = posixpath.split(path)
        if dirname and recursive:
            self.mkdir(dirname)
        try:
            self.con.mkd(path)
        except Exception as e:
            msg = str(e)
            if msg[:4] != '550 ':
                self.log_buffer.append(e)
                return
        self._known_folders.add(path)

    def append(self, filename, data):
        if isinstance(filename, unicode):
            filename = filename.encode('utf-8')
        input = StringIO(data)
        try:
            self.con.storbinary('APPE ' + filename, input)
        except Exception as e:
            self.log_buffer.append(str(e))
            return False
        return True

    def get_file(self, filename, out=None):
        if isinstance(filename, unicode):
            filename = filename.encode('utf-8')
        getvalue = False
        if out is None:
            out = StringIO()
            getvalue = True
        try:
            self.con.retrbinary('RETR ' + filename, out.write)
        except Exception as e:
            msg = str(e)
            if msg[:4] != '550 ':
                self.log_buffer.append(e)
            return None
        if getvalue:
            return out.getvalue()
        return out

    def upload_file(self, filename, src, mkdir=False):
        if isinstance(src, basestring):
            src = StringIO(src)
        if mkdir:
            directory = posixpath.dirname(filename)
            if directory:
                self.mkdir(directory, recursive=True)
        if isinstance(filename, unicode):
            filename = filename.encode('utf-8')
        try:
            self.con.storbinary('STOR ' + filename, src,
                                blocksize=32768)
        except Exception as e:
            self.log_buffer.append(str(e))
            return False
        return True

    def rename_file(self, src, dst):
        try:
            self.con.rename(src, dst)
        except Exception as e:
            self.log_buffer.append(str(e))
            try:
                self.con.delete(dst)
            except Exception as e:
                self.log_buffer.append(str(e))
            try:
                self.con.rename(src, dst)
            except Exception as e:
                self.log_buffer.append(str(e))

    def delete_file(self, filename):
        if isinstance(filename, unicode):
            filename = filename.encode('utf-8')
        try:
            self.con.delete(filename)
        except Exception as e:
            self.log_buffer.append(str(e))

    def delete_folder(self, filename):
        if isinstance(filename, unicode):
            filename = filename.encode('utf-8')
        try:
            self.con.rmd(filename)
        except Exception as e:
            self.log_buffer.append(str(e))
        self._known_folders.discard(filename)


class FtpTlsConnection(FtpConnection):

    def make_connection(self):
        from ftplib import FTP_TLS
        return FTP_TLS()


class FtpPublisher(Publisher):
    connection_class = FtpConnection

    def read_existing_artifacts(self, con):
        contents = con.get_file('.lektor/listing')
        if not contents:
            return {}, set()
        duplicates = set()
        rv = {}
        # Later records override earlier ones.  There can be duplicate
        # entries if the file was not compressed.
        for line in contents.splitlines():
            items = line.split('|')
            if len(items) == 2:
                artifact_name = items[0].decode('utf-8')
                if artifact_name in rv:
                    duplicates.add(artifact_name)
                rv[artifact_name] = items[1]
        return rv, duplicates

    def iter_artifacts(self):
        """Iterates over all artifacts in the build folder and yields the
        artifacts.
        """
        for dirpath, dirnames, filenames in os.walk(self.output_path):
            dirnames[:] = [x for x in dirnames
                           if not self.env.is_ignored_artifact(x)]
            for filename in filenames:
                if self.env.is_ignored_artifact(filename):
                    continue
                full_path = os.path.join(self.output_path, dirpath, filename)
                local_path = full_path[len(self.output_path):] \
                    .lstrip(os.path.sep)
                if os.path.altsep:
                    local_path = local_path.lstrip(os.path.altsep)
                h = hashlib.sha1()
                try:
                    with open(full_path, 'rb') as f:
                        item = f.read(4096)
                        if not item:
                            break
                        h.update(item)
                except IOError as e:
                    if e.errno != errno.ENOENT:
                        raise
                yield (
                    local_path.replace(os.path.sep, '/'),
                    full_path,
                    h.hexdigest(),
                )

    def get_temp_filename(self, filename):
        dirname, basename = posixpath.split(filename)
        return posixpath.join(dirname, '.' + basename + '.tmp')

    def upload_artifact(self, con, artifact_name, source_file, checksum):
        with open(source_file, 'rb') as source:
            tmp_dst = self.get_temp_filename(artifact_name)
            con.log_buffer.append('000 Updating %s' % artifact_name)
            con.upload_file(tmp_dst, source, mkdir=True)
            con.rename_file(tmp_dst, artifact_name)
            con.append('.lektor/listing', '%s|%s\n' % (
                artifact_name.encode('utf-8'), checksum
            ))

    def consolidate_listing(self, con, current_artifacts):
        server_artifacts, duplicates = self.read_existing_artifacts(con)
        known_folders = set()
        for artifact_name in current_artifacts.iterkeys():
            known_folders.add(posixpath.dirname(artifact_name))

        for artifact_name, checksum in server_artifacts.iteritems():
            if artifact_name not in current_artifacts:
                con.log_buffer.append('000 Deleting %s' % artifact_name)
                con.delete_file(artifact_name)
                folder = posixpath.dirname(artifact_name)
                if folder not in known_folders:
                    con.log_buffer.append('000 Deleting %s' % folder)
                    con.delete_folder(folder)

        if duplicates or server_artifacts != current_artifacts:
            listing = []
            for artifact_name, checksum in current_artifacts.iteritems():
                listing.append('%s|%s\n' % (artifact_name, checksum))
            listing.sort()
            con.upload_file('.lektor/.listing.tmp', ''.join(listing))
            con.rename_file('.lektor/.listing.tmp', '.lektor/listing')

    def publish(self, target_url):
        con = self.connection_class(target_url)
        connected = con.connect()
        for event in con.drain_log():
            yield event
        if not connected:
            return

        yield '000 Reading server state ...'
        con.mkdir('.lektor')
        committed_artifacts, _ = self.read_existing_artifacts(con)
        for event in con.drain_log():
            yield event

        yield '000 Begin sync ...'
        current_artifacts = {}
        for artifact_name, filename, checksum in self.iter_artifacts():
            current_artifacts[artifact_name] = checksum
            if checksum != committed_artifacts.get(artifact_name):
                self.upload_artifact(con, artifact_name, filename, checksum)
                for event in con.drain_log():
                    yield event
        yield '000 Sync done!'

        yield '000 Consolidating server state ...'
        self.consolidate_listing(con, current_artifacts)
        for event in con.drain_log():
            yield event

        yield '000 All done!'


class FtpTlsPublisher(FtpPublisher):
    connection_class = FtpTlsConnection


publishers = {
    'rsync': RsyncPublisher,
    'ftp': FtpPublisher,
    'ftps': FtpTlsPublisher,
}


def publish(env, target, output_path):
    url = urls.url_parse(unicode(target))
    publisher = publishers.get(url.scheme)
    if publisher is not None:
        return publisher(env, output_path).publish(url)
