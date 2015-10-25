import os
import sys
import json
import shutil
import posixpath

from itertools import chain

from werkzeug.debug.tbtools import Traceback

from lektor.db import Page, Attachment
from lektor.assets import File, Directory, LessFile
from lektor.reporter import reporter
from lektor.environment import PRIMARY_ALT
from lektor.context import get_ctx
from lektor.utils import portable_popen


build_programs = []


def buildprogram(source_cls):
    def decorator(builder_cls):
        build_programs.append((source_cls, builder_cls))
        return builder_cls
    return decorator


def get_build_program(source, build_state):
    for cls, builder in reversed(build_programs):
        if isinstance(source, cls):
            return builder(source, build_state)


class SourceInfo(object):
    """Holds some information about a source file for indexing into the
    build state.
    """

    def __init__(self, path, filename, alt=PRIMARY_ALT,
                 type='unknown', title_i18n=None):
        self.path = path
        self.alt = alt
        self.filename = filename
        self.type = type
        self.title_i18n = {}

        en_title = self.path
        if 'en' in title_i18n:
            en_title = title_i18n['en']
        for key, value in title_i18n.iteritems():
            if key == 'en':
                continue
            if value != en_title:
                self.title_i18n[key] = value
        self.title_i18n['en'] = en_title


class BuildProgram(object):

    def __init__(self, source, build_state):
        self.source = source
        self.build_state = build_state
        self.artifacts = []
        self._built = False

    @property
    def primary_artifact(self):
        """Returns the primary artifact for this build program.  By
        default this is the first artifact produced.  This needs to be the
        one that corresponds to the URL of the source if it has one.
        """
        try:
            return self.artifacts[0]
        except IndexError:
            return None

    def describe_source_record(self):
        """Can be used to describe the source info by returning a
        :class:`SourceInfo` object.  This is indexed by the builder into
        the build state so that the UI can quickly find files without
        having to scan the file system.
        """
        pass

    def build(self):
        """Invokes the build program."""
        if self._built:
            raise RuntimeError('This build program was already used.')
        self._built = True

        self.produce_artifacts()

        sub_artifacts = []

        gen = self.build_state.builder
        def _build(artifact, build_func):
            ctx = gen.build_artifact(artifact, build_func)
            if ctx is not None:
                sub_artifacts.extend(ctx.sub_artifacts)

        try:
            # Step one is building the artifacts that this build program
            # knows about.
            for artifact in self.artifacts:
                _build(artifact, self.build_artifact)

            # For as long as our ctx keeps producing sub artifacts, we
            # want to process them as well.
            while sub_artifacts:
                artifact, build_func = sub_artifacts.pop()
                _build(artifact, build_func)
        except:
            # If we fail here, we want to mark the sources of our own
            # artifacts as dirty so that we do not miss out on that next
            # time.
            self.build_state.mark_artifact_sources_dirty(self.artifacts)
            raise

    def produce_artifacts(self):
        """This produces the artifacts for building.  Usually this only
        produces a single artifact.
        """

    def declare_artifact(self, artifact_name, sources=None, extra=None):
        """This declares an artifact to be built in this program."""
        self.artifacts.append(self.build_state.new_artifact(
            artifact_name=artifact_name,
            sources=sources,
            source_obj=self.source,
            extra=extra,
        ))

    def build_artifact(self, artifact):
        """This is invoked for each artifact declared."""

    def iter_child_sources(self):
        """This allows a build program to produce children that also need
        building.  An individual build never recurses down to this, but
        a `build_all` will use this.
        """
        return iter(())


@buildprogram(Page)
class PageBuildProgram(BuildProgram):

    def describe_source_record(self):
        # When we describe the source record we need to consider that a
        # page has multiple source file names but only one will actually
        # be used.  The order of the source iter is in order the files are
        # attempted to be read.  So we go with the first that actually
        # exists and then return that.
        for filename in self.source.iter_source_filenames():
            if os.path.isfile(filename):
                return SourceInfo(
                    path=self.source.path,
                    alt=self.source['_source_alt'],
                    filename=filename,
                    type='page',
                    title_i18n=self.source.get_record_label_i18n()
                )

    def produce_artifacts(self):
        if self.source.is_visible:
            self.declare_artifact(
                posixpath.join(self.source.url_path, 'index.html'),
                sources=list(self.source.iter_source_filenames()))

    def render_failure(self, exc_info):
        tb = Traceback(*exc_info)
        return tb.render_full()

    def build_artifact(self, artifact):
        with artifact.open('wb') as f:
            try:
                rv = self.build_state.env.render_template(
                    self.source['_template'], self.build_state.pad,
                    this=self.source)
            except Exception:
                rv = self.render_failure(sys.exc_info())
                self.build_state.mark_artifact_sources_dirty(self.artifacts)
            f.write(rv.encode('utf-8') + b'\n')

    def _iter_paginated_children(self):
        total = self.source.datamodel.pagination_config.count_pages(self.source)
        for page_num in xrange(2, total + 1):
            yield Page(self.source.pad, self.source._data,
                       page_num=page_num)

    def iter_child_sources(self):
        pagination_enabled = self.source.datamodel.pagination_config.enabled
        child_sources = []

        if pagination_enabled:
            child_sources.append(self.source.paginated_children)
            if self.source.page_num == 1:
                child_sources.append(self._iter_paginated_children())
        else:
            child_sources.append(self.source.children)
        child_sources.append(self.source.attachments)

        return chain(*child_sources)


@buildprogram(Attachment)
class AttachmentBuildProgram(BuildProgram):

    def describe_source_record(self):
        return SourceInfo(
            path=self.source.path,
            alt=self.source.alt,
            filename=self.source.attachment_filename,
            type='attachment',
            title_i18n={'en': self.source['_id']}
        )

    def produce_artifacts(self):
        if self.source.is_visible:
            self.declare_artifact(
                self.source.url_path,
                sources=list(self.source.iter_source_filenames()))

    def build_artifact(self, artifact):
        with artifact.open('wb') as df:
            with open(self.source.attachment_filename) as sf:
                shutil.copyfileobj(sf, df)


@buildprogram(File)
class FileAssetBuildProgram(BuildProgram):

    def produce_artifacts(self):
        self.declare_artifact(
            self.source.artifact_name,
            sources=[self.source.source_filename])

    def build_artifact(self, artifact):
        with artifact.open('wb') as df:
            with open(self.source.source_filename, 'rb') as sf:
                shutil.copyfileobj(sf, df)


@buildprogram(Directory)
class DirectoryAssetBuildProgram(BuildProgram):

    def iter_child_sources(self):
        return self.source.children


@buildprogram(LessFile)
class LessFileAssetBuildProgram(BuildProgram):
    """This build program produces css files out of less files."""

    def produce_artifacts(self):
        self.declare_artifact(
            self.source.artifact_name,
            sources=[self.source.source_filename])

    def build_artifact(self, artifact):
        ctx = get_ctx()
        source_out = self.build_state.make_named_temporary('less')
        map_out = self.build_state.make_named_temporary('less-sourcemap')
        here = os.path.dirname(self.source.source_filename)

        exe = self.build_state.config['LESSC_EXECUTABLE']
        if exe is None:
            exe = 'lessc'

        cmdline = [exe, '--no-js', '--include-path=%s' % here,
                   '--source-map=%s' % map_out,
                   self.source.source_filename,
                   source_out]

        reporter.report_debug_info('lessc cmd line', cmdline)

        proc = portable_popen(cmdline)
        if proc.wait() != 0:
            raise RuntimeError('lessc failed')

        with open(map_out) as f:
            for dep in json.load(f).get('sources') or ():
                ctx.record_dependency(os.path.join(here, dep))

        artifact.replace_with_file(source_out)

        @ctx.sub_artifact(artifact_name=artifact.artifact_name + '.map',
                          sources=[self.source.source_filename])
        def build_less_sourcemap_artifact(artifact):
            artifact.replace_with_file(map_out)
