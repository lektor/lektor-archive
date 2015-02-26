import os
import sys
import exifread
import posixpath
import subprocess

from datetime import datetime
from jinja2 import Undefined
from PIL import Image

from lektor.utils import get_dependent_url
from lektor.reporter import reporter


# yay shitty library
datetime.strptime('', '')


class EXIFInfo(object):

    def __init__(self, d):
        self._mapping = d

    def __getitem__(self, name):
        key = name.replace('.', ' ').replace('_', ' ')
        try:
            rv = self._mapping[key]
        except KeyError:
            try:
                rv = self._mapping['EXIF ' + key]
            except KeyError:
                raise KeyError(name)

        if isinstance(rv, basestring):
            return rv
        return rv.printable

    @property
    def artist(self):
        """Returns the artist of the image."""
        try:
            return self['Image.Artist'].decode('utf-8', 'replace')
        except KeyError:
            return Undefined('The exif data does not contain an artist.')

    @property
    def copyright(self):
        """Returns the copyright of image."""
        try:
            return self['Image.Copyright'].decode('utf-8', 'replace')
        except KeyError:
            return Undefined('The exif data does not contain copyright info.')

    @property
    def make(self):
        """The make of the image."""
        try:
            return self['Image.Make'].decode('utf-8', 'replace')
        except KeyError:
            return Undefined('The exif data does not contain a make.')

    @property
    def software(self):
        """The software used for processing the image."""
        try:
            return self['Image.Software'].decode('utf-8', 'replace')
        except KeyError:
            return Undefined('The exif data does not contain software info.')

    @property
    def created_at(self):
        """Date the image was created."""
        try:
            return datetime.strptime(self['Image.DateTime'], '%Y:%m:%d %H:%M:%S')
        except KeyError:
            return Undefined('The exif data does not contain a creation date.')


def get_suffix(width, height):
    suffix = str(width)
    if height is not None:
        suffix += 'x%s' % height
    return suffix


def get_image_info(fp):
    """Reads some image info from a file descriptor."""
    try:
        img = Image.open(fp)
    except Exception:
        return {
            'size': (None, None),
            'mode': None,
            'format': None,
            'format_description': None,
        }
    return {
        'size': img.size,
        'mode': img.mode,
        'format': img.format,
        'format_description': img.format_description,
    }


def read_exif(fp):
    """Reads exif data from a file pointer of an image and returns it."""
    exif = exifread.process_file(fp)
    return EXIFInfo(exif)


def find_default_imagemagick():
    if not sys.platform.startswith('win'):
        return 'convert'

    for key in 'ProgramFiles', 'ProgramW6432', 'ProgramFiles(x86)':
        value = os.environ.get(key)
        if not value:
            continue
        try:
            for filename in os.listdir(value):
                if filename.lower().startswith('imagemagick-'):
                    return os.path.join(value, filename, 'convert.exe')
        except OSError:
            continue

    return 'convert.exe'


def find_imagemagick(env):
    im = env.config['IMAGEMAGICK_EXECUTABLE']
    if im is None:
        return find_default_imagemagick()
    return im


def make_thumbnail(ctx, source_image, source_url_path, width, height=None):
    suffix = get_suffix(width, height)
    dst_url_path = get_dependent_url(source_url_path, suffix)

    im = find_imagemagick(ctx.env)

    @ctx.sub_artifact(artifact_name=dst_url_path, sources=[source_image])
    def build_thumbnail_artifact(artifact):
        resize_key = str(width)
        if height is not None:
            resize_key += 'x' + str(height)
        artifact.ensure_dir()

        cmdline = [im, source_image, '-resize', resize_key,
                   artifact.dst_filename]

        reporter.report_debug_info('imagemagick cmd line', cmdline)
        # XXX: this is super annoying but it looks like windows wants
        # shell invocation :(
        subprocess.Popen(cmdline, shell=sys.platform.startswith('win')).wait()

    return Thumbnail(dst_url_path, width, height)


class Thumbnail(object):

    def __init__(self, url_path, width, height=None):
        self.width = width
        self.height = height
        self.url_path = url_path

    def __unicode__(self):
        return posixpath.basename(self.url_path)
