import posixpath

from flask import Blueprint, jsonify, request, g


bp = Blueprint('api', __name__)


def get_record_and_parent(path):
    pad = g.lektor_info.pad
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
            'label': record.record_label,
            'exists': True
        }

    if record is not None:
        segments.append(_make_segment(record))
    else:
        segments.append({
            'id': posixpath.basename(path),
            'path': path,
            'label': None,
            'exists': False,
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

    if record is None:
        can_have_children = False
        can_have_attachments = False
        is_attachment = False
    else:
        can_have_children = hasattr(record, 'real_children')
        can_have_attachments = hasattr(record, 'attachments')
        is_attachment = record.is_attachment

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
                   is_attachment=is_attachment)


@bp.route('/api/previewinfo')
def get_preview_info():
    record = g.lektor_info.pad.get(request.args['path'])
    if record is None:
        return jsonify(exists=False, url=None, is_hidden=True)
    return jsonify(
        exists=True,
        url=record.url_path,
        is_hidden=record.is_hidden
    )


@bp.route('/api/matchurl')
def match_url():
    record = g.lektor_info.pad.resolve_url_path(request.args['url_path'])
    if record is None:
        return jsonify(exists=False, path=None)
    return jsonify(exists=True, path=record['_path'])


@bp.route('/api/record')
def get_record():
    ts = g.lektor_info.pad.edit(request.args['path'])
    return jsonify(ts.to_json())
