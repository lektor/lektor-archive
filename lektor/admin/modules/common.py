import posixpath

from flask import Blueprint, g, request, current_app
from werkzeug.utils import cached_property

from lektor.db import Database


bp = Blueprint('common', __name__)


class LektorInfo(object):

    def __init__(self):
        self.admin_root = request.script_root
        self.site_root = posixpath.dirname(self.admin_root)

    @cached_property
    def pad(self):
        db = Database(current_app.lektor_env)
        return db.new_pad()


@bp.before_app_request
def find_common_info():
    g.lektor_info = LektorInfo()
