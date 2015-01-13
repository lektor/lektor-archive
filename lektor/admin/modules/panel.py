from flask import Blueprint, abort, render_template

from lektor.admin.utils import get_frontend_source


bp = Blueprint('panel', __name__)


@bp.route('/')
def view():
    """This view shows the admin panel next to the page the admin is loaded
    for.
    """
    source = get_frontend_source()
    if source is None:
        abort(404)
    return render_template('view.html', source=source)


@bp.route('/edit')
def edit():
    return 'Edit'


@bp.route('/delete')
def delete():
    return 'Delete'
