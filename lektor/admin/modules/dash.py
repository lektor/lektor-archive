from flask import Blueprint, render_template, abort, redirect, request, \
     g, url_for

from lektor.admin.utils import fs_path_to_url_path


bp = Blueprint('dash', __name__)


endpoints = [
    ('/', 'index'),
    ('/<path>/edit', 'edit'),
    ('/<path>/delete', 'delete'),
    ('/<path>/preview', 'preview'),
    ('/<path>/add-child', 'add_child'),
]


@bp.route('/edit')
def edit_redirect():
    # XXX: the path here only works if the website is on the root.
    record = g.lektor_info.pad.resolve_url_path(request.args.get('path', '/'))
    if record is None:
        abort(404)
    return redirect(url_for('dash.edit', path=fs_path_to_url_path(record.url_path)))


def generic_endpoint(**kwargs):
    """This function is invoked by all dash endpoints."""
    return render_template('dash.html')


for path, endpoint in endpoints:
    bp.add_url_rule(path, endpoint, generic_endpoint)
