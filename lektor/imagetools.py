import os
import exifread
import posixpath

from datetime import datetime
from jinja2 import Undefined
from PIL import Image

from lektor.utils import get_dependent_url, portable_popen, locate_executable
from lektor.reporter import reporter
from lektor.uilink import BUNDLE_BIN_PATH


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


def find_imagemagick(im=None):
    """Finds imagemagick and returns the path to it."""
    # If it's provided explicitly and it's valid, we go with that one.
    if im is not None and os.path.isfile(im):
        return im

    # If we have a shipped imagemagick, then we used this one.
    if BUNDLE_BIN_PATH is not None:
        executable = os.path.join(BUNDLE_BIN_PATH, 'convert')
        if os.name == 'nt':
            executable += '.exe'
        if os.path.isfile(executable):
            return executable

    # If we're not on windows, we locate the executable like we would
    # do normally.
    if os.name != 'nt':
        return locate_executable('convert')

    # On windows, we only scan the program files for an image magick
    # installation, because this is where this usually goes.  We do
    # this because the convert executable is otherwise the system
    # one which can convert file systems and stuff like this.
    for key in 'ProgramFiles', 'ProgramW6432', 'ProgramFiles(x86)':
        value = os.environ.get(key)
        if not value:
            continue
        try:
            for filename in os.listdir(value):
                if filename.lower().startswith('imagemagick-'):
                    exe = os.path.join(value, filename, 'convert.exe')
                    if os.path.isfile(exe):
                        return exe
        except OSError:
            continue

    # Give up.
    raise RuntimeError('Could not locate imagemagick.')


def get_thumbnail_ext(source_filename):
    ext = source_filename.rsplit('.', 1)[-1].lower()
    # if the extension is already of a format that a browser understands
    # we will roll with it.
    if ext.lower() in ('png', 'jpg', 'jpeg', 'gif'):
        return None
    # Otherwise we roll with JPEG as default.
    return '.jpeg'


def get_quality(source_filename):
    ext = source_filename.rsplit('.', 1)[-1].lower()
    if ext.lower() == 'png':
        return 75
    return 85


def make_thumbnail(ctx, source_image, source_url_path, width, height=None):
    suffix = get_suffix(width, height)
    dst_url_path = get_dependent_url(source_url_path, suffix,
                                     ext=get_thumbnail_ext(source_image))
    quality = get_quality(source_image)

    im = find_imagemagick(
        ctx.build_state.config['IMAGEMAGICK_EXECUTABLE'])

    @ctx.sub_artifact(artifact_name=dst_url_path, sources=[source_image])
    def build_thumbnail_artifact(artifact):
        resize_key = str(width)
        if height is not None:
            resize_key += 'x' + str(height)
        artifact.ensure_dir()

        cmdline = [im, source_image, '-resize', resize_key,
                   '-quality', str(quality), artifact.dst_filename]

        reporter.report_debug_info('imagemagick cmd line', cmdline)
        portable_popen(cmdline).wait()

    return Thumbnail(dst_url_path, width, height)


class Thumbnail(object):
    """Holds information about a thumbnail."""

    def __init__(self, url_path, width, height=None):
        #: the `width` of the thumbnail in pixels.
        self.width = width
        #: the `height` of the thumbnail in pixels.
        self.height = height
        #: the URL path of the image.
        self.url_path = url_path

    def __unicode__(self):
        return posixpath.basename(self.url_path)
