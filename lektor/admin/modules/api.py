import posixpath

from flask import Blueprint, jsonify, request, g


bp = Blueprint('api', __name__)


@bp.route('/api/pathinfo')
def get_path_info():
    """Returns the path segment information for a record."""
    path = request.args['path']
    pad = g.lektor_info.pad
    segments = []

    record = pad.get(path)
    if record is None:
        parent = pad.get(posixpath.dirname(path))
    else:
        parent = record.parent

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


@bp.route('/api/record')
def get_record():
    ts = g.lektor_info.pad.edit(request.args['path'])
    return jsonify(ts.to_json())
