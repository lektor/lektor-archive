import os
import subprocess

from lektor.operationlog import Operation, Result, get_dependent_url


def get_suffix(width, height):
    suffix = str(width)
    if height is not None:
        suffix += 'x%s' % height
    return suffix


def make_thumbnail(oplog, source_image, source_url_path, width, height=None):
    suffix = get_suffix(width, height)
    dst_url_path = get_dependent_url(source_url_path, suffix)

    op = ThumbnailOperation(oplog.env, dst_url_path, source_image, width, height)
    oplog.record_operation(op)
    oplog.record_path_usage(op.source_filename)

    return Thumbnail(dst_url_path, width, height)


class ThumbnailOperation(Operation):

    def __init__(self, env, url_path, source_filename, width, height=None):
        self.env = env
        self.url_path = url_path
        self.source_filename = source_filename
        self.width = width
        self.height = height

    def find_imagemagick(self):
        im = self.env.config['IMAGEMAGICK_PATH']
        if im is None:
            return 'convert'
        return os.path.join(im, 'convert')

    def get_unique_key(self):
        return self.url_path

    def execute(self, builder, oplog):
        dst_filename = builder.get_fs_path(
            builder.get_destination_path(self.url_path), make_folder=True)
        oplog.record_artifact(dst_filename)

        # If our thumbnail is still active there really is no point in
        # building it, however we must do this after the recorded the
        # artifact or it would get deleted.
        if not builder.should_build_sourcefile(self.source_filename):
            return

        im = self.find_imagemagick()

        def producer():
            resize_key = str(self.width)
            if self.height is not None:
                resize_key += 'x' + str(self.height)
            subprocess.Popen([im, self.source_filename,
                              '-resize', resize_key,
                              dst_filename]).wait()

        yield Result(dst_filename, producer, concurrent=True)


class Thumbnail(object):

    def __init__(self, url_path, width, height=None):
        self.width = width
        self.height = height
        self.url_path = url_path

    def __unicode__(self):
        return self.url_path
