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

    slug = ''
    if g.source.parent:
        slug = g.source.parent.datamodel.get_default_child_slug(g.source)

    return render_template('edit.html',
        raw_record=editor.load_raw_record(g.source),
        default_slug=slug,
        default_template=g.source.datamodel.get_default_template_name(),
    )


@bp.route('/delete', methods=['GET', 'POST'])
def delete():
    pad = get_pad()
    editor = Editor(pad)

    parent = g.source.parent
    if parent is None:
        return redirect(action_url('panel.edit'))

    if request.method == 'POST':
        if 'yes' in request.form:
            editor.delete_record(g.source)
            return redirect(action_url('panel.edit', source=parent))
        return redirect(action_url('panel.edit'))
    return render_template('delete.html')


@bp.route('/add', methods=['GET', 'POST'])
def add_child():
    pad = get_pad()
    dm = g.source.datamodel
    editor = Editor(pad)

    models = []
    if dm.child_config.model:
        forced_model = dm.child_config.model
        default_model = forced_model
        models = [forced_model]
    else:
        forced_model = None
        default_model = 'page' in pad.db.datamodels and 'page' or 'none'
        models = pad.db.datamodels.keys()

    if request.method == 'POST' and request.form['_id']:
        editor.add_page_record(g.source, {
            '_id': request.form['_id'],
            '_model': forced_model or request.form['_model'],
            '_hidden': 'yes',
        })
        new_url = g.source.url_path.rstrip('/') + '/' + request.form['_id']
        return redirect(action_url('panel.edit', source=new_url))

    for idx, model in enumerate(models):
        models[idx] = (model, pad.db.datamodels[model].name)

    return render_template('add.html', forced_model=forced_model,
                           default_model=default_model,
                           models=models)
