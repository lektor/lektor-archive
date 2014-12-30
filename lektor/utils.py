def slugify(value):
    # XXX: not good enough
    return u'-'.join(value.strip().split()).lower()
