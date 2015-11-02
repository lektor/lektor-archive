# Lektor

Lektor is a static website generator.  It builds out an entire project
from static files into many individual HTML pages and has a built-in
admin UI.

To see how it works look at the ``example`` folder.

This is work in progress.

## How do I use this?

This is experimental stuff.  If you really want to use it, here is
what you need:

* virtualenv
* node

To run:

    virtualenv venv
    . venv/bin/activate
    pip install --editable .

Since the repo does not contain any pre-built admin UI stuff, if you want
the admin UI you need to run it once in dev mode:

    cd example;
    LEKTOR_DEV=1 lektor devserver

To build projects:

    lektor build

To open up the admin ui and dev server:

    lektor devserver --browse
