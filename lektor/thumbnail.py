import os
import subprocess

from lektor.operationlog import get_dependent_url


def get_suffix(width, height):
    suffix = str(width)
    if height is not None:
        suffix += 'x%s' % height
    return suffix


def find_imagemagick(env):
    im = env.config['IMAGEMAGICK_PATH']
    if im is None:
        return 'convert'
    return os.path.join(im, 'convert')


def make_thumbnail(oplog, source_image, source_url_path, width, height=None):
    suffix = get_suffix(width, height)
    dst_url_path = get_dependent_url(source_url_path, suffix)

    im = find_imagemagick(oplog.env)

    def build_func(artifact):
        resize_key = str(width)
        if height is not None:
            resize_key += 'x' + str(height)
        artifact.ensure_dir()
        subprocess.Popen([im, source_image,
                          '-resize', resize_key,
                          artifact.dst_filename]).wait()

    oplog.add_sub_artifact(artifact_name=dst_url_path,
                           sources=[source_image],
                           build_func=build_func)

    return Thumbnail(dst_url_path, width, height)


class Thumbnail(object):

    def __init__(self, url_path, width, height=None):
        self.width = width
        self.height = height
        self.url_path = url_path

    def __unicode__(self):
        return self.url_path
