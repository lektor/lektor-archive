import os
import sys
import tempfile

from urlparse import urlparse

from contextlib import contextmanager


def slugify(value):
    # XXX: not good enough
    return u'-'.join(value.strip().split()).lower()


@contextmanager
def atomic_open(filename, mode='wb'):
    fd, tmp_filename = tempfile.mkstemp(
        dir=os.path.dirname(filename), prefix='.__atomic-write')
    try:
        with os.fdopen(fd, 'wb') as f:
            yield f
    except:
        exc_info = sys.exc_info()
        try:
            os.remove(tmp_filename)
        except OSError:
            pass
        raise exc_info[0], exc_info[1], exc_info[2]

    os.rename(tmp_filename, filename)


class Url(object):

    def __init__(self, value):
        self.url = value
        self.host = urlparse(value).netloc

    def __unicode__(self):
        return self.url

    def __str__(self):
        return self.url
