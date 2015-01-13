from flask import Blueprint, render_template, redirect, g, request

from lektor.admin.utils import action_url, get_pad
from lektor.editor import Editor


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


@bp.route('/edit', methods=['GET', 'POST'])
def edit():
    pad = get_pad()
    editor = Editor(pad)

    if request.method == 'POST':
        # Because our url path might change, we need to update this here
        # properly.
        editor.update_raw_record(g.source, request.form)
        new_source = get_pad(refresh=True).get(g.source['_path'])
        return redirect(action_url('panel.view', source=new_source.url_path))

    return render_template('edit.html',
        raw_record=editor.load_raw_record(g.source),
        default_slug=pad.db.get_default_record_slug(g.source),
        default_template=pad.db.get_default_record_template(g.source),
    )


@bp.route('/delete')
def delete():
    return 'Delete'
