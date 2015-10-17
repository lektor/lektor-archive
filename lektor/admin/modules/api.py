import posixpath

from flask import Blueprint, jsonify, request, g, current_app

from lektor.utils import is_valid_id
from lektor.admin.utils import eventstream
from lektor.publisher import publish


bp = Blueprint('api', __name__)


def get_record_and_parent(path):
    pad = g.admin_context.pad
    record = pad.get(path)
    if record is None:
        parent = pad.get(posixpath.dirname(path))
    else:
        parent = record.parent
    return record, parent


@bp.route('/api/pathinfo')
def get_path_info():
    """Returns the path segment information for a record."""
    path = request.args['path']
    record, parent = get_record_and_parent(path)
    segments = []

    def _make_segment(record):
        return {
            'id': record['_id'],
            'path': record['_path'],
            'url_path': record.url_path,
            'label': record.record_label,
            'exists': True,
            'can_have_children': record.datamodel.has_own_children,
        }

    if record is not None:
        segments.append(_make_segment(record))
    else:
        segments.append({
            'id': posixpath.basename(path),
            'path': path,
            'label': None,
            'exists': False,
            'can_have_children': False,
        })

    while parent is not None:
        segments.append(_make_segment(parent))
        parent = parent.parent

    segments.reverse()
    return jsonify(segments=segments)


@bp.route('/api/recordinfo')
def get_record_info():
    record, parent = get_record_and_parent(request.args['path'])

    children = []
    attachments = []
    can_be_deleted = False

    if record is None:
        can_have_children = False
        can_have_attachments = False
        is_attachment = False
    else:
        can_have_children = record.datamodel.has_own_children
        can_have_attachments = record.datamodel.has_own_attachments
        is_attachment = record.is_attachment
        can_be_deleted = parent is not None and not record.datamodel.protected

        if can_have_children:
            children = [{
                '_id': x['_id'],
                'path': x['_path'],
                'label': x.record_label,
                'visible': x.is_visible
            } for x in record.real_children]

        if can_have_attachments:
            attachments = [{
                '_id': x['_id'],
                'type': x['_attachment_type'],
                'path': x['_path'],
            } for x in record.attachments]

    return jsonify(attachments=attachments,
                   can_have_attachments=can_have_attachments,
                   children=children,
                   can_have_children=can_have_children,
                   is_attachment=is_attachment,
                   can_be_deleted=can_be_deleted,
                   exists=record is not None)


@bp.route('/api/previewinfo')
def get_preview_info():
    record = g.admin_context.pad.get(request.args['path'])
    if record is None:
        return jsonify(exists=False, url=None, is_hidden=True)
    return jsonify(
        exists=True,
        url=record.url_path,
        is_hidden=record.is_hidden
    )


@bp.route('/api/matchurl')
def match_url():
    record = g.admin_context.pad.resolve_url_path(request.args['url_path'])
    if record is None:
        return jsonify(exists=False, path=None)
    return jsonify(exists=True, path=record['_path'])


@bp.route('/api/rawrecord')
def get_raw_record():
    ts = g.admin_context.pad.edit(request.args['path'])
    return jsonify(ts.to_json())


@bp.route('/api/newrecord')
def get_new_record_info():
    pad = g.admin_context.pad
    ts = pad.edit(request.args['path'])
    if ts.is_attachment:
        can_have_children = False
    elif ts.datamodel.child_config.replaced_with is not None:
        can_have_children = False
    else:
        can_have_children = True
    implied = ts.datamodel.child_config.model

    def describe_model(model):
        primary_field = None
        if model.primary_field is not None:
            f = model.field_map.get(model.primary_field)
            if f is not None:
                primary_field = f.to_json(pad)
        return {
            'id': model.id,
            'name': model.name,
            'primary_field': primary_field
        }

    return jsonify({
        'label': ts.record and ts.record.record_label or ts.id,
        'can_have_children': can_have_children,
        'implied_model': implied,
        'available_models': dict(
            (k, describe_model(v)) for k, v in pad.db.datamodels.iteritems()
            if not v.hidden or k == implied)
    })


@bp.route('/api/newattachment')
def get_new_attachment_info():
    pad = g.admin_context.pad
    ts = pad.edit(request.args['path'])
    return jsonify({
        'can_upload': ts.exists and not ts.is_attachment,
        'label': ts.record and ts.record.record_label or ts.id,
    })


@bp.route('/api/newattachment', methods=['POST'])
def upload_new_attachments():
    ts = g.admin_context.pad.edit(request.values['path'])
    if not ts.exists or ts.is_attachment:
        return jsonify({
            'bad_upload': True
        })

    buckets = []

    for file in request.files.getlist('file'):
        buckets.append({
            'original_filename': file.filename,
            'stored_filename': ts.add_attachment(file.filename, file),
        })

    return jsonify({
        'bad_upload': False,
        'path': request.form['path'],
        'buckets': buckets,
    })


@bp.route('/api/newrecord', methods=['POST'])
def add_new_record():
    values = request.get_json()
    exists = False

    if not is_valid_id(values['id']):
        return jsonify(valid_id=False, exists=False, path=None)

    path = posixpath.join(values['path'], values['id'])

    ts = g.admin_context.pad.edit(path, datamodel=values.get('model'))
    with ts:
        if ts.exists:
            exists = True
        else:
            ts.update(values.get('data') or {})

    return jsonify({
        'valid_id': True,
        'exists': exists,
        'path': path
    })


@bp.route('/api/deleterecord')
def get_delete_info():
    path = request.args['path']
    record = g.admin_context.pad.get(path)
    children = []
    child_count = 0

    if record is None:
        can_be_deleted = True
        is_attachment = False
        label = posixpath.basename(path)
    else:
        can_be_deleted = record['_path'] != '/' and not record.datamodel.protected
        is_attachment = record.is_attachment
        label = record.record_label
        if not is_attachment:
            children = [{
                'id': x['_id'],
                'label': x.record_label,
            } for x in record.real_children.limit(10)]
            child_count = record.real_children.count()

    return jsonify(
        record_info={
            'id': posixpath.basename(path),
            'path': path,
            'exists': record is not None,
            'label': label,
            'can_be_deleted': can_be_deleted,
            'is_attachment': is_attachment,
            'attachments': [{
                'id': x['_id'],
                'type': x['_attachment_type']
            } for x in getattr(record, 'attachments', ())],
            'children': children,
            'child_count': child_count,
        },
    )


@bp.route('/api/deleterecord', methods=['POST'])
def delete_record():
    if request.values['path'] != '/':
        ts = g.admin_context.pad.edit(request.values['path'])
        with ts:
            ts.delete()
    return jsonify(okay=True)


@bp.route('/api/rawrecord', methods=['PUT'])
def update_raw_record():
    values = request.get_json()
    data = values['data']
    ts = g.admin_context.pad.edit(values['path'])
    with ts:
        ts.update(data)
    return jsonify(path=ts.path)


@bp.route('/api/servers')
def get_servers():
    db = g.admin_context.pad.db
    config = db.env.load_config()
    servers = config.get_servers(lang=db.lang)
    return jsonify(servers=sorted([x.to_json() for x in servers.values()],
                                  key=lambda x: x['name'].lower()))


@bp.route('/api/build', methods=['POST'])
def trigger_build():
    builder = current_app.lektor_info.get_builder()
    builder.build_all()
    return jsonify(okay=True)


@bp.route('/api/publish')
def publish_build():
    target = request.values['target']
    info = current_app.lektor_info
    @eventstream
    def generator():
        event_iter = publish(info.env, target, info.output_path) or ()
        for event in event_iter:
            yield {'msg': event}
    return generator()
