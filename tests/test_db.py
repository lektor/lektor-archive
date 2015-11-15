def test_root(pad):
    record = pad.root

    assert record is not None
    assert record['title'] == 'Welcome'
    assert record['_template'] == 'page.html'
    assert record['_alt'] == '_primary'
    assert record['_slug'] == ''
    assert record['_id'] == ''
    assert record['_path'] == '/'


def test_paginated_children(pad):
    page1 = pad.get('/projects', page_num=1)

    assert page1 is not None
    assert page1['_model'] == 'projects'
    assert page1['_template'] == 'projects.html'

    assert page1.datamodel.pagination_config.per_page == 4

    assert page1.children.count() == 7
    assert page1.page_num == 1
    assert page1.paginated_children.count() == 4

    children = page1.paginated_children.all()
    assert len(children) == 4
    assert [x['name'] for x in children] == [
        u'Bagpipe',
        u'Coffee',
        u'Master',
        u'Oven',
    ]

    assert '/projects@1' in pad.cache.persistent
    assert '/projects@2' not in pad.cache.persistent

    page2 = pad.get('/projects', page_num=2)

    assert page2.children.count() == 7
    assert page2.page_num == 2
    assert page2.paginated_children.count() == 3

    children = page2.paginated_children.all()
    assert len(children) == 3
    assert [x['name'] for x in children] == [
        u'Postage',
        u'Slave',
        u'Wolf',
    ]

    assert '/projects@2' in pad.cache.persistent


def test_unpaginated_children(pad):
    page_all = pad.get('/projects')

    assert page_all.paginated_children.count() == 7
    assert page_all.page_num is None

    children = page_all.paginated_children.all()
    assert len(children) == 7
    assert [x['name'] for x in children] == [
        u'Bagpipe',
        u'Coffee',
        u'Master',
        u'Oven',
        u'Postage',
        u'Slave',
        u'Wolf',
    ]


def test_url_matching_for_pagination(pad):
    page1 = pad.resolve_url_path('/projects/')
    assert page1.page_num == 1

    page2 = pad.resolve_url_path('/projects/page/2/')
    assert page2.page_num == 2

    page1_explicit = pad.resolve_url_path('/projects/page/1/')
    assert page1_explicit is None


def test_project_implied_model(pad):
    project = pad.query('/projects').first()
    assert project is not None
    assert project['_model'] == 'project'
