import subprocess
from werkzeug import urls
from lektor.utils import portable_popen


class Publisher(object):

    def __init__(self, env, output_path):
        self.env = env
        self.output_path = output_path

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


publishers = {
    'rsync': RsyncPublisher,
}


def publish(env, target, output_path):
    url = urls.url_parse(unicode(target))
    publisher = publishers.get(url.scheme)
    if publisher is not None:
        return publisher(env, output_path).publish(url)
