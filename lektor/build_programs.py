import os
import sys
import json
import shutil
import posixpath
import subprocess

from itertools import chain

from lektor.db import Page, Attachment
from lektor.assets import File, Directory, LessFile
from lektor.reporter import reporter
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

        # Step one is building the artifacts that this build program
        # knows about.
        for artifact in self.artifacts:
            _build(artifact, self.build_artifact)

        # For as long as our ctx keeps producing sub artifacts, we
        # want to process them as well.
        try:
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
            source_obj=self.source
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

    def produce_artifacts(self):
        if self.source.is_visible:
            self.declare_artifact(
                posixpath.join(self.source.url_path, 'index.html'),
                sources=[self.source.source_filename])

    def build_artifact(self, artifact):
        with artifact.open('wb') as f:
            rv = self.build_state.env.render_template(
                self.source['_template'], self.build_state.pad,
                this=self.source)
            f.write(rv.encode('utf-8') + b'\n')

    def iter_child_sources(self):
        return chain(self.source.real_children, self.source.attachments)


@buildprogram(Attachment)
class AttachmentBuildProgram(BuildProgram):

    def produce_artifacts(self):
        if self.source.is_visible:
            self.declare_artifact(
                self.source.url_path,
                sources=[self.source.source_filename,
                         self.source.attachment_filename])

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

        exe = self.build_state.env.config['LESSC_EXECUTABLE']
        if exe is None:
            exe = 'lessc'
        #    if sys.platform.startswith('win'):
        #        exe = 'lessc.cmd'
        #    else:
        #        exe = 'lessc'

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
