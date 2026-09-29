=============
launch-editor
=============

.. image:: https://img.shields.io/github/actions/workflow/status/adamchainz/launch-editor/main.yml.svg?branch=main&style=for-the-badge
   :target: https://github.com/adamchainz/launch-editor/actions?workflow=CI

.. image:: https://img.shields.io/badge/Coverage-100%25-success?style=for-the-badge
   :target: https://github.com/adamchainz/launch-editor/actions?workflow=CI

.. image:: https://img.shields.io/pypi/v/launch-editor.svg?style=for-the-badge
   :target: https://pypi.org/project/launch-editor/

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge
   :target: https://github.com/psf/black

.. image:: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white&style=for-the-badge
   :target: https://github.com/pre-commit/pre-commit
   :alt: pre-commit

----

Open files in the user’s editor, at a given line and column.

A Python port of the `launch-editor <https://github.com/vitejs/launch-editor>`__ npm package, as used by Vite to open files from the browser.
It detects which editor is running, and knows how to pass a line and column to many editors.

----

**Get better at command line Git** with my book `Boost Your Git DX <https://adamchainz.gumroad.com/l/bygdx>`__.

----

Requirements
------------

Python 3.10 to 3.15 supported.

Installation
------------

1. Install with **pip**:

   .. code-block:: sh

       python -m pip install launch-editor

Usage
-----

Call ``launch_editor()`` with a filename, and optionally a line and column:

.. code-block:: python

    from launch_editor import LaunchEditorError, launch_editor

    try:
        launch_editor("src/example.py", line=12, column=4)
    except LaunchEditorError as exc:
        print(f"Could not open editor: {exc}")

API
---

``launch_editor(filename, line=None, column=None, *, editor=None)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Open ``filename`` in the user’s editor, at ``line`` and ``column`` if given, and return the editor’s ``subprocess.Popen`` object.

The editor is picked by ``guess_editor()``, passing it ``editor``.

GUI editors start in the background, and the function returns immediately.
If a GUI editor exits with an error, a warning is logged to the ``launch_editor`` logger.

Terminal editors, like Vim, take over the current terminal until they exit.
While one is open, further attempts to open a terminal editor raise ``LaunchEditorError``.
(The npm package kills the open editor instead, which can lose unsaved changes.)

Raises ``LaunchEditorError`` if the file does not exist, no editor is found, or the editor cannot be run.

``guess_editor(editor=None)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Return the command for the user’s editor, as a list of strings, or an empty list if none is found.
The editor is chosen from, in order:

1. The ``editor`` argument, as a command string like ``"code --new-window"`` or a list of arguments.
2. The ``LAUNCH_EDITOR`` environment variable.
3. A supported editor that is currently running, on macOS, Linux, and Windows.
4. The ``VISUAL`` environment variable.
5. The ``EDITOR`` environment variable.

``LAUNCH_EDITOR`` is shared with the npm package, so you can set it once for both.
Like there, it’s treated as a single command, not split into arguments.
It may name a script, which is passed the file, line, and column as separate arguments, unless it’s a supported editor.

``position_args(editor, filename, line, column=None)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Return the arguments that open ``filename`` at ``line`` and ``column`` in the given ``editor`` command.
Unsupported editors get only the filename, since passing a position incorrectly can cause errors or confusing behaviour.

``LaunchEditorError``
~~~~~~~~~~~~~~~~~~~~~

Raised when the editor cannot be launched.

Supported editors
-----------------

Opening at a line and column is supported for:

* VS Code and its forks: Antigravity, Cursor, Trae, VSCodium
* JetBrains IDEs: AppCode, CLion, GoLand, IntelliJ IDEA, PhpStorm, PyCharm, Rider, RubyMine, WebStorm
* Atom, Emacs, Helix, joe, micro, nano, Neovim, Notepad++, Sublime Text, TextMate, Vim, Zed

Command line
------------

Run ``python -m launch_editor`` to open a file from the command line, or check which editor would be used:

.. code-block:: console

    $ python -m launch_editor --guess
    code
    $ python -m launch_editor src/example.py:12:4

Full help:

.. [[[cog
.. import cog
.. import subprocess
.. import sys
.. result = subprocess.run(
..     [sys.executable, "-m", "launch_editor", "--help"],
..     capture_output=True,
..     text=True,
.. )
.. cog.outl("")
.. cog.outl(".. code-block:: console")
.. cog.outl("")
.. for line in result.stdout.splitlines():
..     if line.strip() == "":
..         cog.outl("")
..     else:
..         cog.outl("   " + line.rstrip())
.. cog.outl("")
.. ]]]

.. code-block:: console

   usage: python -m launch_editor [-h] [--editor EDITOR] [--guess] [FILE]

   Open a file in your editor.

   positional arguments:
     FILE             The file to open, optionally followed by :LINE or
                      :LINE:COLUMN, like example.py:12:4.

   options:
     -h, --help       show this help message and exit
     --editor EDITOR  The editor command to use, instead of guessing.
     --guess          Print the editor command that would be used, and exit.

.. [[[end]]]

Security
--------

Web applications often use this package to open files from a browser, via an endpoint on a local development server.
Such an endpoint runs a program, so protect it:

* Accept an identifier for a file the application already knows about, rather than an arbitrary path.
* Only accept POST requests, and check the ``Sec-Fetch-Site`` and ``Origin`` headers to reject cross-origin requests.
  Any website the user visits can send requests to ``localhost``.
* Check the ``Host`` header is a local name, like ``localhost`` or ``127.0.0.1``, to prevent DNS rebinding attacks.

On Windows, editors launched through batch files, such as VS Code’s ``code.cmd``, run through ``cmd.exe``, which has its own command line parsing.
To prevent command injection, launch-editor quotes every argument and refuses to pass arguments containing ``"``, ``%``, ``!``, or line breaks to them.
UNC paths are also refused on Windows, like the npm package.

License
-------

MIT.
This package is a port of the launch-editor npm package, Copyright (c) 2017-present Yuxi (Evan) You, which in turn derives from code in create-react-app, Copyright (c) 2015-present Facebook, Inc., both MIT licensed.
See the ``LICENSE`` file for details.
