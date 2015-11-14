import os
import json

from lektor.pluginsystem import Plugin
from lektor.assets import Asset
from lektor.build_programs import BuildProgram
from lektor.context import get_ctx
from lektor.utils import portable_popen
from lektor.reporter import reporter


class LessFile(Asset):
    """Represents a less asset that needs converting into css."""
    source_extension = '.less'
    artifact_extension = '.css'


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

        cmdline = ['lessc', '--no-js', '--include-path=%s' % here,
                   '--source-map=%s' % map_out,
                   self.source.source_filename,
                   source_out]

        reporter.report_debug_info('lessc cmd line', cmdline)

        proc = portable_popen(cmdline)
        if proc.wait() != 0:
            raise RuntimeError('lessc failed')

        with open(map_out) as f:
            dep_base = os.path.dirname(map_out)
            for dep in json.load(f).get('sources') or ():
                ctx.record_dependency(os.path.join(dep_base, dep))

        artifact.replace_with_file(source_out)


class LessPlugin(Plugin):
    name = 'Less'
    description = 'Built-in less support as demo plugin'

    def on_setup_env(self, **kwargs):
        self.env.add_asset_type(LessFile, LessFileAssetBuildProgram)