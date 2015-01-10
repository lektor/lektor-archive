import shutil
import posixpath

from lektor.db import Page, Attachment


build_programs = []


def buildprogram(source_cls):
    def decorator(builder_cls):
        build_programs.append((source_cls, builder_cls))
        return builder_cls
    return decorator


class BuildProgram(object):

    def __init__(self, source, build_state):
        self.source = source
        self.build_state = build_state
        self.artifacts = []
        self._built = False

    def build(self):
        """Invokes the build program."""
        if self._built:
            raise RuntimeError('This build program was already used.')
        self._built = True

        self.produce_artifacts()

        sub_artifacts = []

        gen = self.build_state.builder
        def _build(artifact, build_func):
            oplog = gen.build_artifact(artifact, build_func)
            if oplog is not None:
                sub_artifacts.extend(oplog.sub_artifacts)

        # XXX: if we fail building on sub artifacts and we crash, we
        # forget that this went wrong.  The solution there would be
        # something like a nested transaction for the whole thing, but
        # we do not support that yet.

        # Step one is building the artifacts that this build program
        # knows about.
        for artifact in self.artifacts:
            _build(artifact, self.build_artifact)

        # For as long as our oplog keeps producing sub artifacts, we
        # want to process them as well.
        while sub_artifacts:
            artifact, build_func = sub_artifacts.pop()
            _build(artifact, build_func)

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
        if self.source.is_exposed:
            self.declare_artifact(
                posixpath.join(self.source.url_path, 'index.html'),
                sources=[self.source.source_filename])

    def build_artifact(self, artifact):
        with artifact.open('wb', ensure_dir=True) as f:
            rv = self.build_state.env.render_template(
                self.source['_template'], self.build_state.pad,
                this=self.source)
            f.write(rv.encode('utf-8') + b'\n')

    def iter_child_sources(self):
        if self.source.datamodel.has_own_children:
            for child in self.source.children:
                yield child
        if self.source.datamodel.has_own_attachments:
            for attachment in self.source.attachments:
                yield attachment


@buildprogram(Attachment)
class AttachmentBuildProgram(BuildProgram):

    def produce_artifacts(self):
        if self.source.is_exposed:
            self.declare_artifact(
                self.source.url_path,
                sources=[self.source.source_filename,
                         self.source.attachment_filename])

    def build_artifact(self, artifact):
        with artifact.open('wb', ensure_dir=True) as df:
            with open(self.source.attachment_filename) as sf:
                shutil.copyfileobj(sf, df)
