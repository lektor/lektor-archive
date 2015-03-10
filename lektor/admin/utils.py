def fs_path_to_url_path(path):
    segments = path.strip('/').split('/')
    if segments == ['']:
        segments = []
    segments.insert(0, 'root')
    return ':'.join(segments)
