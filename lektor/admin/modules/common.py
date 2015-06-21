import os
import posixpath

from flask import Blueprint, g, request, current_app
from werkzeug.utils import cached_property


bp = Blueprint('common', __name__)


class AdminContext(object):

    def __init__(self):
        self.admin_root = request.script_root
        self.site_root = posixpath.dirname(self.admin_root)
        self.info = current_app.lektor_info

    def get_temp_path(self, name=None):
        if name is None:
            name = os.urandom(20).encode('hex')
        dirname = self.info.env.temp_path
        try:
            os.makedirs(dirname)
        except OSError:
            pass
        return os.path.join(dirname, name)

    @cached_property
    def pad(self):
        return current_app.lektor_info.get_pad()


@bp.before_app_request
def find_common_info():
    g.admin_context = AdminContext()
