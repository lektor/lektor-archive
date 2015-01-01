import subprocess

from lektor.operationlog import Operation, get_dependent_path


def make_thumbnail(oplog, source_image, source_url_path, width, height=None):
    suffix = unicode(width)
    if height is not None:
        suffix += 'x%s' % height
    dst_path, dst_url_path = get_dependent_path(source_image,
                                                source_url_path,
                                                suffix)
    op = ThumbnailOperation(dst_path, source_image, width, height)
    oplog.record_operation(op)

    return Thumbnail(dst_path, dst_url_path, width, height)


class ThumbnailOperation(Operation):

    def __init__(self, destination_filename, source_filename,
                 width, height=None):
        self.destination_filename = destination_filename
        self.source_filename = source_filename
        self.width = width
        self.height = height

    def get_unique_key(self):
        return self.destination_filename

    def execute(self, builder):
        resize_key = str(self.width)
        if self.height is not None:
            resize_key += 'x' + str(self.height)
        subprocess.Popen(['convert', self.source_filename,
                          '-resize', resize_key,
                          self.destination_filename]).wait()


class Thumbnail(object):

    def __init__(self, filename, url_path, width, height=None):
        self.filename = filename
        self.width = width
        self.height = height
        self.url_path = url_path

    def __unicode__(self):
        return self.url_path
