from IPython.config import Configurable
from IPython.utils.traitlets import Unicode, Bool, link
from IPython.utils.path import get_ipython_dir

from textwrap import dedent


class LinkedConfig(Configurable):
    """A config class whose traits are linked to its parent's traits"""

    def __init__(self, **kwargs):
        super(LinkedConfig, self).__init__(**kwargs)

        # link the trait values between the parent and the config
        for trait in self.traits(config=True):
            link((self, trait), (self.parent, trait))

        # link the parent's config with our config
        link((self.parent, 'config'), (self, 'config'))


class BasicConfig(LinkedConfig):
    """Config options that inherited from IPython."""

    profile = Unicode(
        'nbgrader',
        config=True,
        help="Default IPython profile to use")

    overwrite = Bool(
        False,
        config=True,
        help="Whether to overwrite existing config files when copying")

    auto_create = Bool(
        True,
        config=True,
        help="Whether to automatically generate the profile")

    extra_config_file = Unicode(
        config=True,
        help=dedent(
            """
            Path to an extra config file to load. If specified, load this config
            file in addition to any other IPython config.
            """
        )
    )

    copy_config_files = Bool(
        False,
        config=True,
        help=dedent(
            """
            Whether to install the default config files into the profile dir.
            If a new profile is being created, and IPython contains config files
            for that profile, then they will be staged into the new directory.
            Otherwise, default config files will be automatically generated.
            """
        )
    )

    ipython_dir = Unicode(
        get_ipython_dir(),
        config=True,
        help=dedent(
            """
            The name of the IPython directory. This directory is used for logging
            configuration (through profiles), history storage, etc. The default
            is usually $HOME/.ipython. This option can also be specified through
            the environment variable IPYTHONDIR.
            """
        )
    )

    log_datefmt = Unicode(
        "%Y-%m-%d %H:%M:%S",
        config=True,
        help="The date format used by logging formatters for %(asctime)s"
    )


class NbGraderConfig(LinkedConfig):
    """Config options that are common across nbgrader apps"""

    db_url = Unicode("sqlite:///gradebook.db", config=True, help="URL to the database")

    student_id = Unicode(
        "*",
        config=True,
        help=dedent(
            """
            File glob to match student IDs. This can be changed to filter by
            student. Note: this is always changed to '.' when running `nbgrader
            assign`, as the assign step doesn't have any student ID associated
            with it.
            """
        )
    )

    assignment_id = Unicode(
        "",
        config=True,
        help=dedent(
            """
            The assignment name. This MUST be specified, either by setting the
            config option, passing an argument on the command line, or using the
            --assignment option on the command line.
            """
        )
    )

    notebook_id = Unicode(
        "*",
        config=True,
        help=dedent(
            """
            File glob to match notebook names, excluding the '.ipynb' extension.
            This can be changed to filter by notebook.
            """
        )
    )

    directory_structure = Unicode(
        "{nbgrader_step}/{student_id}/{assignment_id}",
        config=True,
        help=dedent(
            """
            Format string for the directory structure that nbgrader works
            over during the grading process. This MUST contain named keys for
            'nbgrader_step', 'student_id', and 'assignment_id'. It SHOULD NOT
            contain a key for 'notebook_id', as this will be automatically joined
            with the rest of the path.
            """
        )
    )
