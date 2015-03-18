import os
import subprocess as sp
import socket

from textwrap import dedent

from IPython.config.loader import Config
from IPython.utils.traitlets import Unicode, Integer, List, Dict, Bool

from IPython.nbconvert.exporters import HTMLExporter
from IPython.config.application import catch_config_error

from nbgrader.apps.baseapp import BaseNbGraderApp, nbgrader_aliases, nbgrader_flags
from nbgrader.html.formgrade import app
from nbgrader.api import Gradebook

aliases = {}
aliases.update(nbgrader_aliases)
aliases.update({
    'ip': 'FormgradeApp.ip',
    'port': 'FormgradeApp.port',
    'db': 'FormgradeApp.db_url'
})

flags = {}
flags.update(nbgrader_flags)
flags.update({
})

def random_port():
    """get a single random port"""
    sock = socket.socket()
    sock.bind(('', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port

class FormgradeApp(BaseNbGraderApp):

    name = Unicode(u'nbgrader-formgrade')
    description = Unicode(u'Grade a notebook using an HTML form')
    aliases = Dict(aliases)
    flags = Dict(flags)

    examples = Unicode(dedent(
        """
        nbgrader formgrade .
        nbgrader formgrade autograded/
        nbgrader formgrade --ip=0.0.0.0 --port=80
        """
    ))

    db_url = Unicode("sqlite:///gradebook.db", config=True, help="URL to database")
    ip = Unicode("localhost", config=True, help="IP address for the server")
    port = Integer(5000, config=True, help="Port for the server")
    base_directory = Unicode('.', config=True, help="Root server directory")
    directory_format = Unicode('{notebook_id}.ipynb', config=True, help="Format string for the directory structure of the autograded notebooks")
    start_nbserver = Bool(True, config=True, help="Start a single notebook server that allows submissions to be viewed.")

    def _classes_default(self):
        classes = super(FormgradeApp, self)._classes_default()
        classes.append(HTMLExporter)
        return classes

    def init_server_root(self):
        # Specifying notebooks on the command-line overrides (rather than adds)
        # the notebook list
        if self.extra_args:
            patterns = self.extra_args
        else:
            patterns = [self.base_directory]

        if len(patterns) == 0:
            self.base_directory = '.'

        elif len(patterns) == 1:
            self.base_directory = patterns[0]

        else:
            raise ValueError("Multiple files not supported")

        self.base_directory = os.path.abspath(self.base_directory)

        if not os.path.isdir(self.base_directory):
            raise ValueError("Path is not a directory: {}".format(self.base_directory))

        self.log.info("Server root is: {}".format(self.base_directory))

    def build_extra_config(self):
        self.extra_config = Config()
        self.extra_config.Exporter.template_file = 'formgrade'
        self.extra_config.Exporter.template_path = [os.path.join(app.root_path, app.template_folder)]
        self.config.merge(self.extra_config)

    @catch_config_error
    def initialize(self, argv=None):
        super(FormgradeApp, self).initialize(argv)
        self.init_server_root()

    def start(self):
        super(FormgradeApp, self).start()

        # first launch a notebook server
        if self.start_nbserver:
            app.notebook_server_ip = self.ip
            app.notebook_server_port = str(random_port())
            app.notebook_server = sp.Popen(
                [
                    "python", os.path.join(os.path.dirname(__file__), "notebookapp.py"),
                    "--ip", app.notebook_server_ip,
                    "--port", app.notebook_server_port
                ],
                cwd=self.base_directory)
            app.notebook_server_exists = True
        else:
            app.notebook_server_exists = False

        # now launch the formgrader
        app.notebook_dir = self.base_directory
        app.notebook_dir_format = self.directory_format
        app.exporter = HTMLExporter(config=self.config)

        url = "http://{:s}:{:d}/".format(self.ip, self.port)
        self.log.info("Form grader running at {}".format(url))
        self.log.info("Use Control-C to stop this server")

        app.gradebook = Gradebook(self.db_url)
        app.run(host=self.ip, port=self.port, debug=True, use_reloader=False)