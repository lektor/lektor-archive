from flask import Blueprint, render_template, redirect, g

from lektor.admin.utils import action_url, get_pad


bp = Blueprint('panel', __name__)


@bp.route('/')
def index():
    return redirect(action_url('panel.view'))


@bp.route('/view')
def view():
    """This view shows the admin panel next to the page the admin is loaded
    for.
    """
    return render_template('view.html')


@bp.route('/edit')
def edit():
    pad = get_pad()
    raw_record = pad.db.load_raw_data(
        g.source['_path'], g.source.record_classification)
    return render_template('edit.html',
        raw_record=raw_record,
        default_slug=pad.db.get_default_record_slug(g.source),
        default_template=pad.db.get_default_record_template(g.source),
    )


@bp.route('/delete')
def delete():
    return 'Delete'
