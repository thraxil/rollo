#!/usr/bin/env python

import sys
import os
import re
import shutil
import optparse
import logging
import urllib2
import urlparse
try:
    import setuptools
    import pkg_resources
except ImportError:
    setuptools = pkg_resources = None
import distutils.sysconfig
try:
    import subprocess
except ImportError:
    print "ERROR: You must have the subprocess module available to use"
    print "       workingenv.py"
    raise

__version__ = '0.6.6'

class BadCommand(Exception):
    pass


ez_setup_url = 'http://kang.ccnmtl.columbia.edu/eggs/ez_setup.py'
python_version = '%s.%s' % (sys.version_info[0], sys.version_info[1])

help = """\
This script builds a 'working environment', which is a directory set
up for isolated installation of Python scripts, libraries, and
applications.

To activate an installation, you must add the lib/python directory
to your $PYTHONPATH; after you do that the import path will be
adjusted, as will be installation locations.  Or use
"source bin/activate" in a Bash shell.

This may be reapplied to update or refresh an existing environment;
it will by default pick up the settings originally used.
"""

class DefaultTrackingParser(optparse.OptionParser):

    """
    Version of OptionParser that returns an options argument that has
    a ``._set_vars`` attribute, that shows which options were
    explicitly set (not just picked up from defaults)
    """

    def get_default_values(self):
        values = optparse.OptionParser.get_default_values(self)
        values = DefaultTrackingValues(values)
        return values

class DefaultTrackingValues(optparse.Values):

    def __init__(self, defaults=None):
        self.__dict__['_set_vars'] = []
        self.__dict__['_defaults_done'] = False
        self.__dict__['_values'] = {}
        if isinstance(defaults, optparse.Values):
            defaults = defaults.__dict__
        optparse.Values.__init__(self, defaults)
        self.__dict__['_defaults_done'] = True

    def __setattr__(self, attr, value):
        if self._defaults_done:
            self._set_vars.append(attr)
        self._values[attr] = value

    def __getattr__(self, attr):
        return self._values[attr]

parser = DefaultTrackingParser(
    version=__version__,
    usage='%%prog [OPTIONS] NEW_DIRECTORY\n\n%s' % help)

parser.add_option('-v', '--verbose',
                  action="count",
                  dest="verbose",
                  default=0,
                  help="Be verbose (use multiple times for more effect)")

parser.add_option('-q', '--quiet',
                  action="count",
                  dest="quiet",
                  default=0,
                  help="Be more and more quiet")

parser.add_option('--log-file',
                  dest="log_file",
                  default=None,
                  metavar="FILENAME",
                  help="Save a verbose log of what happens in this log file")

parser.add_option('-n', '--simulate',
                  action="store_true",
                  dest="simulate",
                  help="Simulate (just pretend to do things)")

parser.add_option('--force',
                  action="store_false",
                  dest="interactive",
                  default=True,
                  help="Overwrite files without asking")

parser.add_option('-f', '--find-links',
                  action="append",
                  dest="find_links",
                  default=[],
                  metavar="URL",
                  help="Extra locations/URLs where packages can be found (sets up your distutils.cfg for future installs)")

parser.add_option('-Z', '--always-unzip',
                  action="store_true",
                  dest="always_unzip",
                  help="Don't install zipfiles, no matter what (sets up your distutils.cfg for future installs)")

parser.add_option('--home',
                  dest='install_as_home',
                  action='store_true',
                  default=False,
                  help="If given, then packages will be installed with the distutils --home option instead of --prefix.  Zope requires this kind of installation")

parser.add_option('--site-packages',
                  action="store_true",
                  dest="include_site_packages",
                  help="Include the global site-packages (not included by default)")

parser.add_option('--no-extra',
                  action="store_false",
                  dest="install_extra",
                  default=True,
                  help="Don't create non-essential directories (like src/)")

parser.add_option('--env',
                  action='append',
                  dest='envs',
                  metavar='VAR:VALUE',
                  default=[],
                  help="Add the environmental variable assignments to the activate script")

parser.add_option('-r', '--requirements',
                  dest="requirements",
                  action="append",
                  metavar="FILE/URL",
                  help="A file or URL listing requirements that should be installed in the new environment (one requirement per line, optionally with -e for editable packages).  This file can also contain lines starting with -Z, -f, and -r")

parser.add_option('--confirm',
                  dest='confirm',
                  action='store_true',
                  help="Confirm that the requirements have been installed, but don't do anything else (don't set up environment, don't install packages)")

parser.add_option('--cross-platform-activate',
                  dest='cross_platform_activate',
                  action='store_true',
                  help="If given, then both Posix shell files and Windows bat activation scripts will be created (otherwise only the current platform's script will be created)")



class Logger(object):

    """
    Logging object for use in command-line script.  Allows ranges of
    levels, to avoid some redundancy of displayed information.
    """

    DEBUG = logging.DEBUG
    INFO = logging.INFO
    NOTIFY = (logging.INFO+logging.WARN)/2
    WARN = WARNING = logging.WARN
    ERROR = logging.ERROR
    FATAL = logging.FATAL

    LEVELS = [DEBUG, INFO, NOTIFY, WARN, ERROR, FATAL]

    def __init__(self, consumers):
        self.consumers = consumers
        self.indent = 0
        self.in_progress = None
        self.in_progress_hanging = False

    def debug(self, msg, *args, **kw):
        self.log(self.DEBUG, msg, *args, **kw)
    def info(self, msg, *args, **kw):
        self.log(self.INFO, msg, *args, **kw)
    def notify(self, msg, *args, **kw):
        self.log(self.NOTIFY, msg, *args, **kw)
    def warn(self, msg, *args, **kw):
        self.log(self.WARN, msg, *args, **kw)
    def error(self, msg, *args, **kw):
        self.log(self.WARN, msg, *args, **kw)
    def fatal(self, msg, *args, **kw):
        self.log(self.FATAL, msg, *args, **kw)
    def log(self, level, msg, *args, **kw):
        if args:
            if kw:
                raise TypeError(
                    "You may give positional or keyword arguments, not both")
        args = args or kw
        rendered = None
        for consumer_level, consumer in self.consumers:
            if self.level_matches(level, consumer_level):
                if (self.in_progress_hanging
                    and consumer in (sys.stdout, sys.stderr)):
                    self.in_progress_hanging = False
                    sys.stdout.write('\n')
                    sys.stdout.flush()
                if rendered is None:
                    if args:
                        rendered = msg % args
                    else:
                        rendered = msg
                    rendered = ' '*self.indent + rendered
                if hasattr(consumer, 'write'):
                    consumer.write(rendered+'\n')
                else:
                    consumer(rendered)

    def start_progress(self, msg):
        assert not self.in_progress, (
            "Tried to start_progress(%r) while in_progress %r"
            % (msg, self.in_progress))
        if self.level_matches(self.NOTIFY, self._stdout_level()):
            sys.stdout.write(msg)
            sys.stdout.flush()
            self.in_progress_hanging = True
        else:
            self.in_progress_hanging = False
        self.in_progress = msg

    def end_progress(self, msg='done.'):
        assert self.in_progress, (
            "Tried to end_progress without start_progress")
        if self.stdout_level_matches(self.NOTIFY):
            if not self.in_progress_hanging:
                # Some message has been printed out since start_progress
                sys.stdout.write('...' + self.in_progress + msg + '\n')
                sys.stdout.flush()
            else:
                sys.stdout.write(msg + '\n')
                sys.stdout.flush()
        self.in_progress = None
        self.in_progress_hanging = False

    def show_progress(self):
        """If we are in a progress scope, and no log messages have been
        shown, write out another '.'"""
        if self.in_progress_hanging:
            sys.stdout.write('.')
            sys.stdout.flush()

    def stdout_level_matches(self, level):
        """Returns true if a message at this level will go to stdout"""
        return self.level_matches(level, self._stdout_level())

    def _stdout_level(self):
        """Returns the level that stdout runs at"""
        for level, consumer in self.consumers:
            if consumer is sys.stdout:
                return level
        return self.FATAL

    def level_matches(self, level, consumer_level):
        """
        >>> l = Logger()
        >>> l.level_matches(3, 4)
        False
        >>> l.level_matches(3, 2)
        True
        >>> l.level_matches(slice(None, 3), 3)
        False
        >>> l.level_matches(slice(None, 3), 2)
        True
        >>> l.level_matches(slice(1, 3), 1)
        True
        >>> l.level_matches(slice(2, 3), 1)
        False
        """
        if isinstance(level, slice):
            start, stop = level.start, level.stop
            if start is not None and start > consumer_level:
                return False
            if stop is not None or stop <= consumer_level:
                return False
            return True
        else:
            return level >= consumer_level

    #@classmethod
    def level_for_integer(cls, level):
        levels = cls.LEVELS
        if level < 0:
            return levels[0]
        if level >= len(levels):
            return levels[-1]
        return levels[level]

    level_for_integer = classmethod(level_for_integer)

class Writer(object):

    """
    File-writing class.  This writes all its files to a
    subdirectory, and respects simulate and interactive
    options.
    """

    def __init__(self, base_dir, logger, simulate,
                 interactive, python_dir=None):
        self.base_dir = os.path.abspath(base_dir)
        self.simulate = simulate
        self.interactive = interactive
        self.logger = logger
        if python_dir is None:
            python_dir = os.path.join('lib', 'python%s' % python_version)
        self.python_dir = python_dir

    def ensure_dir(self, dir):
        dir = dir.replace('__PYDIR__', self.python_dir)
        if os.path.exists(self.path(dir)):
            self.logger.debug('Directory %s exists', dir)
            return
        self.logger.info('Creating %s', dir)
        if not self.simulate:
            os.makedirs(self.path(dir))

    def ensure_file(self, filename, content,
                    force=False, binary=False):
        """
        Make sure a file exists, with the given content.  If --force
        was given, this will overwrite the file unconditionally;
        otherwise the user is queried (unless ``force=True`` is given
        to override this).  If --simulate was given, this will never
        write the file.
        """
        content = content.replace('__PYDIR__', self.python_dir)
        filename = filename.replace('__PYDIR__', self.python_dir)
        path = self.path(filename)
        if os.path.exists(path):
            c = self.read_file(path, binary=binary)
            if c == content:
                self.logger.debug('File %s already exists (same content)',
                                  filename)
                return
            elif self.interactive:
                if self.simulate:
                    self.logger.warn('Would overwrite %s (if confirmed)',
                                     filename)
                else:
                    def show_diff():
                        self.show_diff(filename, content, c)
                    if not force:
                        response = self.get_response(
                            'Overwrite file %s?' % filename,
                            other_ops=[('d', show_diff)])
                        if not response:
                            return
            else:
                self.logger.warn('Overwriting file %s', filename)
        else:
            self.logger.info('Creating file %s', filename)
        if not self.simulate:
            if binary:
                mode = 'wb'
            else:
                mode = 'w'
            f = open(path, mode)
            f.write(content)
            f.close()

    def show_diff(self, filename, content1, content2):
        from difflib import unified_diff
        u_diff = list(unified_diff(
            content2.splitlines(),
            content1.splitlines(),
            filename))
        print '\n'.join(u_diff)                            

    def path(self, path):
        return os.path.join(self.base_dir, path)

    def read_file(self, path, binary=False):
        if binary:
            mode = 'rb'
        else:
            mode = 'r'
        f = open(path, mode)
        try:
            c = f.read()
        finally:
            f.close()
        return c

    def add_pythonpath(self):
        """
        Add the working Python path to $PYTHONPATH
        """
        writer_path = os.path.normpath(
            os.path.abspath(self.path(self.python_dir)))
        cur_path = os.environ.get('PYTHONPATH', None)
        if cur_path is None:
            cur_path = []
        else:
            cur_path = cur_path.split(os.pathsep)
        cur_path = [os.path.normpath(os.path.abspath(p))
                    for p in cur_path]
        if writer_path in cur_path:
            return
        cur_path.insert(0, writer_path)
        os.environ['PYTHONPATH'] = os.pathsep.join(cur_path)

    def get_response(self, msg, default=None,
                     other_ops=()):
        """
        Ask the user about something.  An empty response will return
        default (default=None means an empty response will ask again)
        
        If you give other_ops, it should be a list of [('k', func)], where
        if the user enters 'k' then func will be run (and it will not be
        treated as an answer)
        """
        if default is None:
            prompt = '[y/n'
        elif default:
            prompt = '[Y/n'
        else:
            prompt = '[y/N'
        ops_by_key = {}
        for key, func in other_ops:
            prompt += '/'+key
            ops_by_key[key] = func
        prompt += '] '
        while 1:
            response = raw_input(msg + ' ' + prompt).strip().lower()
            if not response:
                if default is None:
                    print 'Please enter Y or N'
                    continue
                return default
            if response[0] in ('y', 'n'):
                return response[0] == 'y'
            if response[0] in ops_by_key:
                ops_by_key[response[0]]()
                continue
            print 'Y or N please'

    def ensure_symlink(self, src, dest):
        src = self.path(src)
        dest = self.path(dest)
        if os.path.exists(dest):
            actual_src = os.path.realpath(dest)
            if os.path.abspath(actual_src) == os.path.abspath(dest):
                self.logger.warn('%s should be a symlink to %s, but is an actual file/directory '
                                 '(leaving as-is)' % (dest, src))
            elif os.path.abspath(actual_src) != os.path.abspath(src):
                self.logger.warn('%s should be symlinked to %s, but is actually symlinked '
                                 'to %s (leaving as-is)'
                                 % (dest, src, actual_src))
            else:
                self.logger.debug('%s already symlinked to %s' % (dest, src))
            return
        self.logger.info('Symlinking %s to %s' % (dest, src))
        if not self.simulate:
            os.symlink(src, dest)

basic_layout = [
    '__PYDIR__',
    '__PYDIR__/distutils',
    '__PYDIR__/setuptools',
    'bin',
    '.workingenv',
    ]

extra_layout = [
    'src',
    ]

files_to_write = {}

def call_subprocess(cmd, writer, show_stdout=True,
                    filter_stdout=None, in_workingenv=False, cwd=None,
                    raise_on_returncode=True):
    cmd_parts = []
    for part in cmd:
        if ' ' in part or '\n' in part or '"' in part or "'" in part:
            part = '"%s"' % part.replace('"', '\\"')
        cmd_parts.append(part)
    cmd_desc = ' '.join(cmd_parts)
    if in_workingenv:
        env = os.environ.copy()
        env['PYTHONPATH'] = writer.path(writer.python_dir)
    else:
        env = None
    if show_stdout:
        stdout = None
    else:
        stdout = subprocess.PIPE
    writer.logger.debug("Running command %s" % cmd_desc)
    try:
        proc = subprocess.Popen(
            cmd, stderr=subprocess.STDOUT, stdin=None, stdout=stdout,
            cwd=cwd, env=env)
    except Exception, e:
        writer.logger.fatal(
            "Error %s while executing command %s" % (e, cmd_desc))
        raise
    if stdout is not None:
        stdout = proc.stdout
        while 1:
            line = stdout.readline()
            if not line:
                break
            line = line.rstrip()
            if filter_stdout:
                level = filter_stdout(line)
                if isinstance(level, tuple):
                    level, line = level
                writer.logger.log(level, line)
                if not writer.logger.stdout_level_matches(level):
                    writer.logger.show_progress()
            else:
                writer.logger.info(line)
    else:
        proc.communicate()
    proc.wait()
    if proc.returncode:
        if raise_on_returncode:
            raise OSError(
                "Command %s failed with error code %s"
                % (cmd_desc, proc.returncode))
        else:
            writer.logger.warn(
                "Command %s had error code %s"
                % (cmd_desc, proc.returncode))

def make_working_environment(
    writer, logger, find_links, always_unzip,
    include_site_packages, install_extra,
    # Deprecated but allowed in signature:
    force_install_setuptools=True,
    cross_platform_activate=False,
    install_as_home=False,
    envs=()):
    settings = Settings(
        find_links=find_links,
        always_unzip=always_unzip,
        include_site_packages=include_site_packages,
        install_extra=install_extra,
        cross_platform_activate=cross_platform_activate,
        install_as_home=install_as_home,
        envs=envs)
    make_environment(writer, logger, settings)

def make_environment(writer, logger, settings):
    """
    Create a working environment.  ``writer`` is a ``Writer``
    instance, ``logger`` a ``Logger`` instance.

    ``find_links`` and ``always_unzip`` are used to create
    ``distutils.cfg``, which controls later installations.

    ``include_site_packages``, if true, will cause the environment
    to pick up system-wide packages (besides the standard library).

    ``install_extra``, if true, puts in some directories like
    ``src/``

    ``force_install_setuptools`` will install setuptools even if it is
    already installed elsewhere on the system.  (If it isn't found, it
    will always be installed)

    ``install_as_home`` will install so that distutils will install
    packages like ``--home=WORKINGENV`` was given, not
    ``--prefix=WORKINGENV``

    ``envs`` is a list of ``(var, value)`` of environmental variables
    that should be set when activating this environment.
    """
    if os.path.exists(writer.base_dir):
        logger.notify('Updating working environment in %s' % writer.base_dir)
    else:
        logger.notify('Making working environment in %s' % writer.base_dir)
    layout = basic_layout[:]
    if settings.install_extra:
        layout.extend(extra_layout)
    for dir in layout:
        writer.ensure_dir(dir)
    to_write = files_to_write.copy()
    if not settings.cross_platform_activate:
        if sys.platform == 'win32':
            # remove shell scripts
            del to_write['bin/activate']
        else:
            # remove bat files
            del to_write['bin/activate.bat']
            del to_write['bin/deactivate.bat']
    cfg = distutils_cfg
    if settings.install_as_home:
        prefix_option = 'home = __WORKING__'
    else:
        prefix_option = 'prefix = __WORKING__'
    cfg = cfg.replace('__PREFIX__', prefix_option)
    if settings.find_links:
        first = True
        for find_link in settings.find_links:
            if first:
                find_link = 'find_links = %s' % find_link
                first = False
            else:
                find_link = '             %s' % find_link
            cfg += find_link + '\n'
    if settings.always_unzip:
        cfg += 'zip_ok = false\n'
    to_write[writer.python_dir+'/distutils/distutils.cfg'] = cfg
    install_setuptools(writer, logger)
    add_setuptools_to_path(writer, logger)
    vars = dict(
        env_name=os.path.basename(writer.base_dir),
        working_env=os.path.abspath(writer.base_dir),
        python_version=python_version)
    vars.update(env_assignments(settings.envs))
    for path, content in to_write.items():
        content = content % vars
        writer.ensure_file(path, content)
    writer.ensure_file(writer.python_dir+'/site.py',
                       site_py(settings.include_site_packages))
    fix_lib64(writer, logger)
    fix_cli_exe(writer, logger)
    settings.write(writer)

def install_setuptools(writer, logger):
    """
    Install setuptools into a new working environment
    """
    for fn in os.listdir(writer.path(writer.python_dir)):
        if fn.startswith('setuptools-'):
            logger.notify('Setuptools already installed; not updating '
                          '(remove %s to force installation)'
                          % os.path.join(writer.python_dir, fn))
            return
    if writer.simulate:
        logger.notify('Would have installed local setuptools')
        return
    logger.start_progress('Installing local setuptools...')
    logger.indent += 2
    f_in = urllib2.urlopen(ez_setup_url)
    tmp_dir = os.path.join(writer.path('tmp'))
    tmp_exists = os.path.exists(tmp_dir)
    if not tmp_exists:
        os.mkdir(tmp_dir)
    ez_setup_path = writer.path('tmp/ez_setup.py')
    f_out = open(ez_setup_path, 'w')
    shutil.copyfileobj(f_in, f_out)
    f_in.close()
    f_out.close()
    writer.add_pythonpath()
    # Make sure there's no leftover site.py's:
    site_py = writer.path(os.path.join(writer.python_dir, 'site.py'))
    if os.path.exists(site_py):
        os.unlink(site_py)
    call_subprocess(
        [sys.executable, ez_setup_path,
         '--always-unzip',
         '--install-dir', writer.path(writer.python_dir),
         '--script-dir', writer.path('bin'),
         '--always-copy', '--upgrade', 'setuptools'],
        writer, show_stdout=False, filter_stdout=filter_ez_setup)
    os.unlink(ez_setup_path)
    if not tmp_exists:
        os.rmdir(tmp_dir)
    # Get rid of the site.py that setuptools adds:
    if os.path.exists(site_py):
        os.unlink(site_py)
    easy_install_dir = writer.path('bin')
    for fn in os.listdir(easy_install_dir):
        if fn.startswith('easy_install'):
            fix_easy_install_script(
                os.path.join(easy_install_dir, fn), logger)
    fix_easy_install_pth(writer, logger)
    logger.indent -= 2
    logger.end_progress()

def filter_ez_setup(line):
    if not line.strip():
        return Logger.DEBUG
    for prefix in ['Reading ', 'Best match', 'Processing setuptools',
                   'Copying setuptools', 'Adding setuptools',
                   'Installing ', 'Installed ']:
        if line.startswith(prefix):
            return Logger.DEBUG
    return Logger.INFO

def add_setuptools_to_path(writer, logger):
    setuptools_pth_file = os.path.join(
        writer.path(writer.python_dir), 'setuptools.pth')
    f = open(setuptools_pth_file)
    setuptools_pth = os.path.join(
        writer.path(writer.python_dir), f.read().strip())
    f.close()
    sys.path.append(setuptools_pth)
            
def fix_easy_install_script(filename, logger):
    """
    The easy_install script needs to import setuptools before doing
    the requirement which forces setuptools to be used directly.
    Without importing setuptools, the monkeypatch to keep setuptools
    to stop complaining about site.py won't be installed.
    """
    f = open(filename, 'rb')
    c = f.read()
    f.close()
    if not c.startswith('#!'):
        if not filename.endswith('.exe'):
            # Only in this case is it really a problem, since for
            # easy_install.exe files there are easy_install-script.py
            # files that *will* be updated
            logger.warn(
                'Cannot fix import path in script %s' % filename)
        return
    lines = c.splitlines(True)
    if not lines[0].rstrip().endswith('-S'):
        # The standard path fixup wasn't applied
        logger.debug('Fixing up path in easy_install because of global setuptools installation')
        lines[0] = lines[0].rstrip() + ' -S\n'
        lines[1:1] = [
            "import os, sys\n",
            "join, dirname, abspath = os.path.join, os.path.dirname, os.path.abspath\n",
            "site_dirs = [join(dirname(dirname(abspath(__file__))), 'lib', 'python%s.%s' % tuple(sys.version_info[:2])), join(dirname(dirname(abspath(__file__))), 'lib', 'python')]\n",
            "sys.path[0:0] = site_dirs\n",
            "import site\n",
            "[site.addsitedir(d) for d in site_dirs]\n",
            ]
    for i, line in enumerate(lines):
        if line.startswith('from pkg_resources'):
            lines[i:i] = ['import setuptools\n']
            break
    else:
        logger.warn('Could not find line "import sys" in %s' % filename)
        return
    logger.info('Fixing easy_install script %s' % filename)
    f = open(filename, 'wb')
    f.write(''.join(lines))
    f.close()

def fix_easy_install_pth(writer, logger):
    """
    easy-install.pth starts with an explicit reference to the
    installed setuptools, which shouldn't be first on the path.
    Because it is already in setuptools.pth, we can simply comment out
    the line in easy-install.pth
    """
    easy_install_pth = os.path.join(
        writer.python_dir, 'easy-install.pth')
    f = open(writer.path(easy_install_pth))
    lines = f.readlines(True)
    f.close()
    new_lines = []
    for line in lines:
        if (not line.startswith('#')
            and os.path.basename(line).startswith('setuptools-')):
            logger.debug('Commenting out line %r in %s'
                         % (line, easy_install_pth))
            line = '#'+line
        new_lines.append(line)
    new_content = ''.join(new_lines)
    writer.ensure_file(easy_install_pth, new_content, force=True)

def fix_lib64(writer, logger):
    """
    Some platforms (particularly Gentoo on x64) put things in lib64/pythonX.Y
    instead of lib/pythonX.Y.  If this is such a platform we'll just create a
    symlink so lib64 points to lib
    """
    if [ (i,j) for (i,j) in distutils.sysconfig.get_config_vars().items() 
         if isinstance(j, basestring) and 'lib64' in j ]:
        logger.debug('This system uses lib64; symlinking lib64 to lib')
        writer.ensure_symlink('lib', 'lib64')

def fix_cli_exe(writer, logger):
    """
    Setuptools has the files cli.exe and gui.exe in its egg, but our
    setuptools monkeypatch will keep it from finding these files.  We'll
    simply copy these files to fix that.
    """
    if writer.simulate:
        logger.debug('Would have tried to copy over cli.exe and gui.exe')
        return
    python_path = writer.path(writer.python_dir)
    setuptools_egg = None
    for filename in os.listdir(python_path):
        if (filename.lower().startswith('setuptools')
            and filename.lower().endswith('.egg')):
            setuptools_egg = filename
            break
    if not setuptools_egg:
        logger.error('No setuptools egg found in %r' % python_path)
        return
    for base in ['cli.exe', 'gui.exe']:
        filename = os.path.join(python_path, setuptools_egg,
                                'setuptools', base)
        if not os.path.exists(filename):
            if sys.platform == 'win32':
                # Well, we *should* have it, why don't we?
                logger.error('No %r file found in the setuptools egg (%r)'
                             % (base, filename))
            continue
        f = open(filename, 'rb')
        c = f.read()
        f.close()
        new_filename = os.path.join(python_path, 'setuptools', base)
        writer.ensure_file(new_filename, c, binary=True)
    
def read_requirements(logger, requirements):
    """
    Read all the lines from the requirement files, including recursive
    reads.
    """
    lines = []
    req_re = re.compile(r'^(?:-r|--requirements)\s+')
    for fn in requirements:
        logger.info('Reading requirement %s' % fn)
        for line in get_lines(fn):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            match = req_re.search(line)
            if match:
                sub_fn = line[match.end():]
                sub_fn = join_filename(fn, sub_fn)
                lines.extend(read_requirements(logger, [sub_fn]))
                continue
            lines.append((line, fn))
    return lines

def join_filename(base, sub, only_req_uri=False):
    if only_req_uri and '#' not in sub:
        return sub
    if re.search(r'^https?://', base) or re.search(r'^https?://', sub):
        return urlparse.urljoin(base, sub)
    else:
        base = os.path.dirname(os.path.abspath(base))
        return os.path.join(base, sub)

def parse_requirements(logger, requirement_lines, settings):
    """
    Parse all the lines of requirements.  Can override options.
    Returns a list of requirements to be installed.
    """
    options_re = re.compile(r'^--?([a-zA-Z0-9_-]*)\s+')
    plan = []
    for line, uri in requirement_lines:
        match = options_re.search(line)
        if match:
            option = match.group(1)
            value = line[match.end():]
            if option in ('f', 'find-links'):
                value = join_filename(uri, value)
                if value not in settings.find_links:
                    settings.find_links.append(value)
            elif option in ('Z', 'always-unzip'):
                settings.always_unzip = True
            elif option in ('e', 'editable'):
                plan.append(
                    ('--editable', join_filename(uri, value, only_req_uri=True)))
            else:
                logger.error("Bad option override in requirement: %s" % line)
            continue
        plan.append(join_filename(uri, line, only_req_uri=True))
    return plan

def install_requirements(writer, logger, plan):
    """
    Install all the requirements found in the list of filenames
    """
    writer.add_pythonpath()
    import pkg_resources
    immediate = []
    editable = []
    for req in plan:
        if req[0] == '--editable':
            editable.append(req[1])
        else:
            immediate.append(req)
    if immediate:
        args = ', '.join([
            '"%s"' % req.replace('"', '').replace("'", '') for req in immediate])
        logger.start_progress('Installing %s ...' % ', '.join(immediate))
        logger.indent += 2
        os.chdir(writer.path('.'))
        if not writer.simulate:
            call_subprocess(
                [sys.executable, '-c',
                 "import setuptools.command.easy_install; "
                 "setuptools.command.easy_install.main([\"-q\", %s])"
                 % args], writer,
                in_workingenv=True, show_stdout=False,
                filter_stdout=make_filter_easy_install())
        logger.indent -= 2
        logger.end_progress()
    for req in editable:
        logger.debug('Changing to directory %s'
                     % writer.path('src'))
        os.chdir(writer.path('src'))
        req = req.replace('"', '').replace("'", '')
        dist_req = pkg_resources.Requirement.parse(req)
        dir = writer.path(
            os.path.join('src', dist_req.project_name.lower()))
        dir_exists = os.path.exists(dir)
        if dir_exists:
            logger.info('Package %s already installed in editable form'
                        % req)
        else:
            logger.start_progress('Installing editable %s to %s...' % (req, dir))
            logger.indent += 2
            cmd = [sys.executable, '-c',
                   "import setuptools.command.easy_install; "
                   "setuptools.command.easy_install.main("
                   "[\"-q\", \"-b\", \".\", \"-e\", \"%s\"])"
                   % req]
            call_subprocess(
                cmd, writer, in_workingenv=True,
                show_stdout=False, filter_stdout=make_filter_easy_install())
        os.chdir(dir)
        call_subprocess(
            [sys.executable, '-c',
             "import setuptools; execfile(\"setup.py\")",
             "develop"], writer, in_workingenv=True,
            show_stdout=False, filter_stdout=make_filter_develop())
        if not dir_exists:
            logger.indent -= 2
            logger.end_progress()

def make_filter_easy_install():
    context = []
    def filter_easy_install(line):
        adjust = 0
        level = Logger.NOTIFY
        prefix = 'Processing dependencies for '
        if line.startswith(prefix):
            requirement = line[len(prefix):].strip()
            context.append(requirement)
            adjust = -2
        prefix = 'Finished installing '
        if line.startswith(prefix):
            requirement = line[len(prefix):].strip()
            if not context or context[-1] != requirement:
                # For some reason the top-level context is often None from
                # easy_install.process_distribution; so we shouldn't worry
                # about inconsistency in that case
                if len(context) != 1 or requirement != 'None':
                    print 'Error: Got unexpected "%s%s"' % (prefix, requirement)
                    print '       Context: %s' % context
            context.pop()
        if not line.strip():
            level = Logger.DEBUG
        for regex in [r'references __(file|path)__$',
                      r'^zip_safe flag not set; analyzing',
                      r'MAY be using inspect.[a-zA-Z0-9_]+$',
                      r'^Extracting .*to',
                      r'^creating .*\.egg$',
                      ]:
            if re.search(regex, line.strip()):
                level = Logger.DEBUG
        indent = len(context)*2 + adjust
        return (level, ' '*indent + line)
    return filter_easy_install

def make_filter_develop():
    easy_filter = make_filter_easy_install()
    def filter_develop(line):
        for regex in [r'^writing.*egg-info']:
            if re.search(regex, line.strip()):
                return Logger.DEBUG
        return easy_filter(line)
    return filter_develop
    
def check_requirements(writer, logger, plan):
    """
    Check all the requirements found in the list of filenames
    """
    writer.add_pythonpath()
    import pkg_resources
    for req in plan:
        if '#egg=' in req:
            req = req.split('#egg=')[-1]
        try:
            dist = pkg_resources.get_distribution(req)
            logger.notify("Found: %s" % dist)
            logger.info("  in location: %s" % dist.location)
        except pkg_resources.DistributionNotFound:
            logger.warn("Not Found: %s" % req)
        except ValueError, e:
            logger.warn("Cannot confirm %s" % req)
    
def get_lines(fn_or_url):
    scheme = urlparse.urlparse(fn_or_url)[0]
    if not scheme:
        # Must be filename
        f = open(fn_or_url)
    else:
        f = urllib2.urlopen(fn_or_url)
    try:
        return f.readlines()
    finally:
        f.close()

def env_assignments(envs):
    """
    Return the shell code to assign an unassign variables, as a
    dictionary of variable substitutions
    """
    vars = {
        'unix_set_env': [],
        'unix_unset_env': [],
        'windows_set_env': [],
        'windows_unset_env': [],
        }
    for name, value in envs:
        vars['unix_set_env'].append(
            '%s="%s"' % (name, value.replace('"', '\\"')))
        vars['unix_set_env'].append(
            'export %s' % name)
        vars['unix_unset_env'].append(
            'unset %s' % name)
        vars['windows_set_env'].append(
            'set %s=%s' % (name, value))
        vars['windows_unset_env'].append(
            'set %s=' % name)
    for name, value in vars.items():
        vars[name] = '\n'.join(value)
    return vars

class Settings(object):

    """
    Object to store all the settings for the working environment (this
    does not store transient options like verbosity).
    """
    
    def __init__(
        self, find_links=None, envs=None,
        always_unzip=True,
        include_site_packages=False,
        install_extra=True,
        cross_platform_activate=False,
        install_as_home=False,
        requirements=None):
        self.find_links = find_links or []
        self.envs = envs or []
        self.always_unzip = always_unzip
        self.include_site_packages = include_site_packages
        self.install_extra = install_extra
        self.cross_platform_activate = cross_platform_activate
        self.install_as_home = install_as_home
        self.requirements = requirements or []

    def write(self, writer):
        writer.ensure_file(
            '.workingenv/find_links.txt',
            '\n'.join(self.find_links), force=True)
        writer.ensure_file(
            '.workingenv/envs.txt',
            '\n'.join(['%s:%s' % (n, v) for n, v in self.envs]), force=True)
        writer.ensure_file(
            '.workingenv/requirements.txt',
            '\n'.join(self.requirements), force=True)
        settings = []
        settings.append(self.make_setting_line(
            'always_unzip', self.always_unzip))
        settings.append(self.make_setting_line(
            'include_site_packages',
            self.include_site_packages))
        settings.append(self.make_setting_line(
            'install_extra', self.install_extra))
        settings.append(self.make_setting_line(
            'cross_platform_activate',
            self.cross_platform_activate))
        settings.append(self.make_setting_line(
            'install_as_home', self.install_as_home))
        writer.ensure_file(
            '.workingenv/settings.txt',
            '\n'.join(settings)+'\n', force=True)

    #@staticmethod
    def make_setting_line(name, value):
        if value:
            value = 'True'
        else:
            value = 'False'
        return '%s = %s' % (name, value)

    make_setting_line = staticmethod(make_setting_line)

    #@classmethod
    def read(cls, base_dir):
        dir = os.path.join(base_dir, '.workingenv')
        find_links = cls.read_lines(
            os.path.join(dir, 'find_links.txt'))
        find_links = cls.unique_lines(find_links)
        envs = [line.split(':', 1)
                for line in cls.read_lines(os.path.join(dir, 'envs.txt'))]
        requirements = cls.read_lines(
            os.path.join(dir, 'requirements.txt'))
        # defaults:
        args = dict(
            always_unzip=False,
            include_site_packages=False,
            install_extra=True,
            cross_platform_activate=False,
            install_as_home=False)
        for line in cls.read_lines(
            os.path.join(dir, 'settings.txt')):
            if '=' not in line:
                raise ValueError(
                    'Badly formatted line: %r' % line)
            name, value = line.split('=', 1)
            name = name.strip()
            value = cls.make_bool(value.strip())
            args[name] = value
        return cls(find_links=find_links,
                   envs=envs,
                   requirements=requirements,
                   **args)

    read = classmethod(read)

    #@staticmethod
    def read_lines(filename):
        if not os.path.exists(filename):
            return []
        f = open(filename)
        result = []
        for line in f:
            if not line.strip() or line.strip().startswith('#'):
                continue
            result.append(line.strip())
        f.close()
        return result

    read_lines = staticmethod(read_lines)

    #@staticmethod
    def unique_lines(lines):
        result = []
        for line in lines:
            if line not in result:
                result.append(line)
        return result

    unique_lines = staticmethod(unique_lines)
    
    #@staticmethod
    def make_bool(value):
        value = value.strip().lower()
        if value in ('1', 'true', 't', 'yes', 'y', 'on'):
            return True
        elif value in ('0', 'false', 'f', 'no', 'n', 'off'):
            return False
        raise ValueError(
            'Cannot convert to boolean: %r' % value)

    make_bool = staticmethod(make_bool)


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    options, args = parser.parse_args(args)
    if not args or len(args) > 1:
        raise BadCommand("You must provide a single output directory")
    output_dir = args[0]
    level = 1 # Notify
    level += options.verbose
    level -= options.quiet
    if options.simulate and not options.verbose:
        level += 1
    level = Logger.level_for_integer(3-level)
    logger = Logger(
        [(level, sys.stdout)])
    if options.log_file:
        dir = os.path.dirname(os.path.abspath(options.log_file))
        if not os.path.exists(dir):
            os.makedirs(dir)
        f = open(options.log_file, 'a')
        logger.consumers.append((Logger.DEBUG, f))
    if options.install_as_home:
        python_dir = os.path.join('lib', 'python')
    else:
        python_dir = os.path.join('lib', 'python%s' % python_version)
    writer = Writer(output_dir, logger, simulate=options.simulate,
                    interactive=options.interactive,
                    python_dir=python_dir)
    envs = []
    for assignment in options.envs:
        if ':' not in assignment:
            raise BadCommand(
                "--env=%s should be --env=VAR:VALUE" % assignment)
        var, value = assignment.split(':', 1)
        envs.append((var, value))
    if os.path.exists(os.path.join(output_dir, '.workingenv')):
        logger.info('Reading settings from environment')
        settings = Settings.read(output_dir)
    else:
        settings = Settings()
    for var in options._set_vars:
        setattr(settings, var, getattr(options, var))
    if envs:
        settings.envs = envs
    requirements = settings.requirements
    requirement_lines = read_requirements(logger, requirements)
    plan = parse_requirements(logger, requirement_lines, settings)
    if not options.confirm:
        make_environment(writer, logger, settings)
    if options.confirm:
        check_requirements(writer, logger, plan)
        return
    if plan:
        install_requirements(writer, logger, plan)

def site_py(include_site_packages):
    s = """\
# Duplicating setuptools' site.py...
def __boot():
    PYTHONPATH = os.environ.get('PYTHONPATH')
    if PYTHONPATH is None or (sys.platform=='win32' and not PYTHONPATH):
        PYTHONPATH = []
    else:
        PYTHONPATH = PYTHONPATH.split(os.pathsep)
    pic = getattr(sys,'path_importer_cache',{})
    stdpath = sys.path[len(PYTHONPATH):]
    mydir = os.path.dirname(__file__)
    known_paths = dict([(makepath(item)[1],1) for item in sys.path]) # 2.2 comp

    oldpos = getattr(sys,'__egginsert',0)   # save old insertion position
    sys.__egginsert = 0                     # and reset the current one

    for item in PYTHONPATH:
        addsitedir(item)
        item_site_packages = os.path.join(item, 'site-packages')
        if os.path.exists(item_site_packages):
            addsitedir(item_site_packages)

    sys.__egginsert += oldpos           # restore effective old position

    d,nd = makepath(stdpath[0])
    insert_at = None
    new_path = []

    for item in sys.path:
        p,np = makepath(item)

        if np==nd and insert_at is None:
            # We've hit the first 'system' path entry, so added entries go here
            insert_at = len(new_path)

        if np in known_paths or insert_at is None:
            new_path.append(item)
        else:
            # new path after the insert point, back-insert it
            new_path.insert(insert_at, item)
            insert_at += 1

    sys.path[:] = new_path
    
import sys
import os
import __builtin__

def makepath(*paths):
    dir = os.path.abspath(os.path.join(*paths))
    return dir, os.path.normcase(dir)

def abs__file__():
    \"\"\"Set all module' __file__ attribute to an absolute path\"\"\"
    for m in sys.modules.values():
        try:
            m.__file__ = os.path.abspath(m.__file__)
        except AttributeError:
            continue

try:
    set
except NameError:
    class set:
        def __init__(self, args=()):
            self.d = {}
            for v in args:
                self.d[v] = None
        def __contains__(self, key):
            return key in self.d
        def add(self, key):
            self.d[key] = None

def removeduppaths():
    \"\"\" Remove duplicate entries from sys.path along with making them
    absolute\"\"\"
    # This ensures that the initial path provided by the interpreter contains
    # only absolute pathnames, even if we're running from the build directory.
    L = []
    known_paths = set()
    for dir in sys.path:
        # Filter out duplicate paths (on case-insensitive file systems also
        # if they only differ in case); turn relative paths into absolute
        # paths.
        dir, dircase = makepath(dir)
        if not dircase in known_paths:
            L.append(dir)
            known_paths.add(dircase)
    sys.path[:] = L
    return known_paths

def _init_pathinfo():
    \"\"\"Return a set containing all existing directory entries from sys.path\"\"\"
    d = set()
    for dir in sys.path:
        try:
            if os.path.isdir(dir):
                dir, dircase = makepath(dir)
                d.add(dircase)
        except TypeError:
            continue
    return d

def addpackage(sitedir, name, known_paths, exclude_packages=()):
    \"\"\"Add a new path to known_paths by combining sitedir and 'name' or execute
    sitedir if it starts with 'import'\"\"\"
    import fnmatch
    if known_paths is None:
        _init_pathinfo()
        reset = 1
    else:
        reset = 0
    fullname = os.path.join(sitedir, name)
    try:
        f = open(fullname, "rU")
    except IOError:
        return
    try:
        for line in f:
            if line.startswith(\"#\"):
                continue
            found_exclude = False
            for exclude in exclude_packages:
                if exclude(line):
                    found_exclude = True
                    break
            if found_exclude:
                continue
            if line.startswith("import"):
                exec line
                continue
            line = line.rstrip()
            dir, dircase = makepath(sitedir, line)
            if not dircase in known_paths and os.path.exists(dir):
                sys.path.append(dir)
                known_paths.add(dircase)
    finally:
        f.close()
    if reset:
        known_paths = None
    return known_paths

def addsitedir(sitedir, known_paths=None, exclude_packages=()):
    \"\"\"Add 'sitedir' argument to sys.path if missing and handle .pth files in
    'sitedir'\"\"\"
    if known_paths is None:
        known_paths = _init_pathinfo()
        reset = 1
    else:
        reset = 0
    sitedir, sitedircase = makepath(sitedir)
    if not sitedircase in known_paths:
        sys.path.append(sitedir)        # Add path component
    try:
        names = os.listdir(sitedir)
    except os.error:
        return
    names.sort()
    for name in names:
        if name.endswith(os.extsep + "pth"):
            addpackage(sitedir, name, known_paths,
                       exclude_packages=exclude_packages)
    if reset:
        known_paths = None
    return known_paths

def addsitepackages(known_paths):
    \"\"\"Add site-packages (and possibly site-python) to sys.path\"\"\"
    prefixes = [os.path.join(sys.prefix, "local"), sys.prefix]
    if sys.exec_prefix != sys.prefix:
        prefixes.append(os.path.join(sys.exec_prefix, "local"))
    for prefix in prefixes:
        if prefix:
            if sys.platform in ('os2emx', 'riscos'):
                sitedirs = [os.path.join(prefix, "Lib", "site-packages")]
            elif os.sep == '/':
                sitedirs = [os.path.join(prefix,
                                         "lib",
                                         "python" + sys.version[:3],
                                         "site-packages"),
                            os.path.join(prefix, "lib", "site-python")]
                try:
                    # sys.getobjects only available in --with-pydebug build
                    sys.getobjects
                    sitedirs.insert(0, os.path.join(sitedirs[0], 'debug'))
                except AttributeError:
                    pass
            else:
                sitedirs = [prefix, os.path.join(prefix, "lib", "site-packages")]
            if sys.platform == 'darwin':
                sitedirs.append( os.path.join('/opt/local', 'lib', 'python' + sys.version[:3], 'site-packages') )
                # for framework builds *only* we add the standard Apple
                # locations. Currently only per-user, but /Library and
                # /Network/Library could be added too
                if 'Python.framework' in prefix:
                    home = os.environ.get('HOME')
                    if home:
                        sitedirs.append(
                            os.path.join(home,
                                         'Library',
                                         'Python',
                                         sys.version[:3],
                                         'site-packages'))
            for sitedir in sitedirs:
                if os.path.isdir(sitedir):
                    addsitedir(sitedir, known_paths,
                               exclude_packages=[lambda line: 'setuptools' in line])
    return None

def setquit():
    \"\"\"Define new built-ins 'quit' and 'exit'.
    These are simply strings that display a hint on how to exit.

    \"\"\"
    if os.sep == ':':
        exit = 'Use Cmd-Q to quit.'
    elif os.sep == '\\\\':
        exit = 'Use Ctrl-Z plus Return to exit.'
    else:
        exit = 'Use Ctrl-D (i.e. EOF) to exit.'
    __builtin__.quit = __builtin__.exit = exit


class _Printer(object):
    \"\"\"interactive prompt objects for printing the license text, a list of
    contributors and the copyright notice.\"\"\"

    MAXLINES = 23

    def __init__(self, name, data, files=(), dirs=()):
        self.__name = name
        self.__data = data
        self.__files = files
        self.__dirs = dirs
        self.__lines = None

    def __setup(self):
        if self.__lines:
            return
        data = None
        for dir in self.__dirs:
            for filename in self.__files:
                filename = os.path.join(dir, filename)
                try:
                    fp = file(filename, "rU")
                    data = fp.read()
                    fp.close()
                    break
                except IOError:
                    pass
            if data:
                break
        if not data:
            data = self.__data
        self.__lines = data.split('\\n')
        self.__linecnt = len(self.__lines)

    def __repr__(self):
        self.__setup()
        if len(self.__lines) <= self.MAXLINES:
            return "\\n".join(self.__lines)
        else:
            return "Type %s() to see the full %s text" % ((self.__name,)*2)

    def __call__(self):
        self.__setup()
        prompt = 'Hit Return for more, or q (and Return) to quit: '
        lineno = 0
        while 1:
            try:
                for i in range(lineno, lineno + self.MAXLINES):
                    print self.__lines[i]
            except IndexError:
                break
            else:
                lineno += self.MAXLINES
                key = None
                while key is None:
                    key = raw_input(prompt)
                    if key not in ('', 'q'):
                        key = None
                if key == 'q':
                    break

def setcopyright():
    \"\"\"Set 'copyright' and 'credits' in __builtin__\"\"\"
    __builtin__.copyright = _Printer("copyright", sys.copyright)
    if sys.platform[:4] == 'java':
        __builtin__.credits = _Printer(
            "credits",
            "Jython is maintained by the Jython developers (www.jython.org).")
    else:
        __builtin__.credits = _Printer("credits", \"\"\"\\
    Thanks to CWI, CNRI, BeOpen.com, Zope Corporation and a cast of thousands
    for supporting Python development.  See www.python.org for more information.\"\"\")
    here = os.path.dirname(os.__file__)
    __builtin__.license = _Printer(
        "license", "See http://www.python.org/%.3s/license.html" % sys.version,
        ["LICENSE.txt", "LICENSE"],
        [os.path.join(here, os.pardir), here, os.curdir])


class _Helper(object):
    \"\"\"Define the built-in 'help'.
    This is a wrapper around pydoc.help (with a twist).

    \"\"\"

    def __repr__(self):
        return "Type help() for interactive help, " \\
               "or help(object) for help about object."
    def __call__(self, *args, **kwds):
        import pydoc
        return pydoc.help(*args, **kwds)

def sethelper():
    __builtin__.help = _Helper()

def aliasmbcs():
    \"\"\"On Windows, some default encodings are not provided by Python,
    while they are always available as "mbcs" in each locale. Make
    them usable by aliasing to "mbcs" in such a case.\"\"\"
    if sys.platform == 'win32':
        import locale, codecs
        enc = locale.getdefaultlocale()[1]
        if enc.startswith('cp'):            # "cp***" ?
            try:
                codecs.lookup(enc)
            except LookupError:
                import encodings
                encodings._cache[enc] = encodings._unknown
                encodings.aliases.aliases[enc] = 'mbcs'

def setencoding():
    \"\"\"Set the string encoding used by the Unicode implementation.  The
    default is 'ascii', but if you're willing to experiment, you can
    change this.\"\"\"
    encoding = "ascii" # Default value set by _PyUnicode_Init()
    if 0:
        # Enable to support locale aware default string encodings.
        import locale
        loc = locale.getdefaultlocale()
        if loc[1]:
            encoding = loc[1]
    if 0:
        # Enable to switch off string to Unicode coercion and implicit
        # Unicode to string conversion.
        encoding = "undefined"
    if encoding != "ascii":
        # On Non-Unicode builds this will raise an AttributeError...
        sys.setdefaultencoding(encoding) # Needs Python Unicode build !


def execsitecustomize():
    \"\"\"Run custom site specific code, if available.\"\"\"
    try:
        import sitecustomize
    except ImportError:
        pass

def fixup_setuptools():
    \"\"\"Make sure our setuptools monkeypatch is in place\"\"\"
    for i in range(len(sys.path)):
        if sys.path[i].find('setuptools') != -1:
            path = sys.path[i]
            del sys.path[i]
            sys.path.append(path)

def main():
    abs__file__()
    paths_in_sys = removeduppaths()
    if include_site_packages:
        paths_in_sys = addsitepackages(paths_in_sys)
    setquit()
    setcopyright()
    sethelper()
    aliasmbcs()
    setencoding()
    execsitecustomize()
    # Remove sys.setdefaultencoding() so that users cannot change the
    # encoding after initialization.  The test for presence is needed when
    # this module is run as a script, because this code is executed twice.
    if hasattr(sys, "setdefaultencoding"):
        del sys.setdefaultencoding
    __boot()
    fixup_setuptools()
    
"""
    s += '\n\ninclude_site_packages = %r\n\n' % include_site_packages
    s += "\n\nmain()\n"
    return s

files_to_write['__PYDIR__/distutils/__init__.py'] = """\
import os

dirname = os.path.dirname
lib_dir = dirname(dirname(__file__))
working_env = dirname(dirname(lib_dir))

# This way we run first, but distutils still gets imported:
distutils_path = os.path.join(os.path.dirname(os.__file__), 'distutils')
__path__.insert(0, distutils_path)
exec open(os.path.join(distutils_path, '__init__.py')).read()

import dist
def make_repl(v):
    if isinstance(v, basestring):
        return v.replace('__WORKING__', working_env)
    else:
        return v
    
old_parse_config_files = dist.Distribution.parse_config_files
def parse_config_files(self, filenames=None):
    old_parse_config_files(self, filenames)
    for d in self.command_options.values():
        for name, value in d.items():
            if isinstance(value, list):
                value = [make_repl(v) for v in value]
            elif isinstance(value, tuple):
                value = tuple([make_repl(v) for v in value])
            elif isinstance(value, basestring):
                value = make_repl(value)
            else:
                print "unknown: %%s=%%r" %% (name, value)
            d[name] = value
dist.Distribution.parse_config_files = parse_config_files

old_find_config_files = dist.Distribution.find_config_files
def find_config_files(self):
    found = old_find_config_files(self)
    system_distutils = os.path.join(distutils_path, 'distutils.cfg')
    if os.path.exists(system_distutils):
        found.insert(0, system_distutils)
    return found
dist.Distribution.find_config_files = find_config_files
"""

files_to_write['__PYDIR__/setuptools/__init__.py'] = """\
import os, sys
from distutils import log
# setuptools should be on sys.path already from a .pth file

for path in sys.path:
    if 'setuptools' in path:
        setuptools_path = os.path.join(path, 'setuptools')
        __path__.insert(0, setuptools_path)
        break
else:
    raise ImportError(
        'Cannot find setuptools on sys.path; is setuptools.pth missing?')

execfile(os.path.join(setuptools_path, '__init__.py'))
import setuptools.command.easy_install as easy_install

def get_script_header(script_text, executable=easy_install.sys_executable,
                      wininst=False):
    from distutils.command.build_scripts import first_line_re
    first, rest = (script_text+'\\n').split('\\n',1)
    match = first_line_re.match(first)
    options = ''
    if match:
        script_text = rest
        options = match.group(1) or ''
        if options:
            options = ' '+options
    if wininst:
        executable = "python.exe"
    else:
        executable = easy_install.nt_quote_arg(executable)
    if options.find('-S') == -1:
        options += ' -S'
    shbang = \"#!%%(executable)s%%(options)s\\n\" %% locals()
    shbang += ("import sys, os\\n"
               "join, dirname, abspath = os.path.join, os.path.dirname, os.path.abspath\\n"
               "site_dirs = [join(dirname(dirname(abspath(__file__))), 'lib', 'python%%s.%%s' %% tuple(sys.version_info[:2])), join(dirname(dirname(abspath(__file__))), 'lib', 'python')]\\n"
               "sys.path[0:0] = site_dirs\\n"
               "import site\\n"
               "[site.addsitedir(d) for d in site_dirs]\\n")
    return shbang

def install_site_py(self):
    # to heck with this, we gots our own site.py and we'd like
    # to keep it, thank you
    pass

old_process_distribution = easy_install.easy_install.process_distribution

def process_distribution(self, requirement, dist, deps=True, *info):
    old_process_distribution(self, requirement, dist, deps, *info)
    log.info('Finished installing %%s', requirement)

easy_install.get_script_header = get_script_header
easy_install.easy_install.install_site_py = install_site_py
easy_install.easy_install.process_distribution = process_distribution
"""

distutils_cfg = """\
[install]
__PREFIX__

[easy_install]
install_dir = __WORKING__/__PYDIR__
site_dirs = __WORKING__/__PYDIR__
script_dir = __WORKING__/bin/
always_copy = True
"""

files_to_write['bin/activate'] = """\
# This file must be used with "source bin/activate" *from bash*
# you cannot run it directly

deactivate () {
    if [ -n "$_WE_OLD_WORKING_PATH" ] ; then
        PATH="$_WE_OLD_WORKING_PATH"
        export PATH
        unset _WE_OLD_WORKING_PATH
    fi
    if [ -n "$_WE_OLD_PYTHONPATH" ] ; then
        if [ "$_WE_OLD_PYTHONPATH" = "__none__" ] ; then
            unset PYTHONPATH
        else
            PYTHONPATH="$_WE_OLD_PYTHONPATH"
        fi
        export PYTHONPATH
        unset _WE_OLD_PYTHONPATH
    fi
    if [ -n "$_WE_OLD_PS1" ] ; then
        PS1="$_WE_OLD_PS1"
        export PS1
        unset _WE_OLD_PS1
    fi


    unset WORKING_ENV
    %(unix_unset_env)s

    if [ ! "$1" = "nondestructive" ] ; then
    # Self destruct!
        unset deactivate
    fi
}

# unset irrelavent variables
deactivate nondestructive

export WORKING_ENV="%(working_env)s"

_WE_OLD_WORKING_PATH="$PATH"
PATH="$WORKING_ENV/bin:$PATH"
export PATH
export _WE_OLD_WORKING_PATH

_WE_OLD_PS1="$PS1"
PS1="(`basename $WORKING_ENV`)$PS1"
export PS1
export _WE_OLD_PS1

if [ -z "$PYTHONPATH" ] ; then
    _WE_OLD_PYTHONPATH="__none__"
    PYTHONPATH="$WORKING_ENV/__PYDIR__"
else
    _WE_OLD_PYTHONPATH="$PYTHONPATH"
    PYTHONPATH="$WORKING_ENV/__PYDIR__:$PYTHONPATH"
fi
export PYTHONPATH
export _WE_OLD_PYTHONPATH
%(unix_set_env)s

# This should detect bash, which has a hash command that must
# be called to get it to forget past commands.  Without
# forgetting past commands the $PATH changes we made may not
# be respected
if [ -n "$BASH" ] ; then
    hash -r
fi

"""

files_to_write['bin/activate.bat'] = """\
@echo off
set WORKING_ENV=%(working_env)s

if not defined PROMPT (
    set PROMPT=$P$G
)

if defined _WE_OLD_PROMPT (
    set PROMPT=%%_WE_OLD_PROMPT%%
)

set _WE_OLD_PROMPT=%%PROMPT%%
set PROMPT=(%(env_name)s) %%PROMPT%%

if defined _WE_OLD_WORKING_PATH (
    set PATH=%%_WE_OLD_WORKING_PATH%%
    goto SKIP1
)
set _WE_OLD_WORKING_PATH=%%PATH%%

:SKIP1
set PATH=%%WORKING_ENV%%\\bin;%%PATH%%

if defined _WE_OLD_PYTHONPATH (
    if %%_WE_OLD_PYTHONPATH%%+X==__none__+X (
        set PYTHONPATH=
        goto SKIP2
    )
    set PYTHONPATH=%%_WE_OLD_PYTHONPATH%%
)

:SKIP2
if defined PYTHONPATH (
    set _WE_OLD_PYTHONPATH=%%PYTHONPATH%%
    set PYTHONPATH=%%WORKING_ENV%%\\__PYDIR__;%%PYTHONPATH%%
    goto END
)
set _WE_OLD_PYTHONPATH=__none__
set PYTHONPATH=%%WORKING_ENV%%\\__PYDIR__
%(windows_set_env)s

:END
"""

files_to_write['bin/deactivate.bat'] = """\
@echo off

if defined _WE_OLD_PROMPT (
    set PROMPT=%%_WE_OLD_PROMPT%%
)
set _WE_OLD_PROMPT=

if defined _WE_OLD_WORKING_PATH (
    set PATH=%%_WE_OLD_WORKING_PATH%%
)
set _WE_OLD_WORKING_PATH=

if defined _WE_OLD_PYTHONPATH (
    if %%_WE_OLD_PYTHONPATH%%+X==__none__+X (
        set PYTHONPATH=
        goto SKIP1
    )
    set PYTHONPATH=%%_WE_OLD_PYTHONPATH%%
)

:SKIP1
set _WE_OLD_PYTHONPATH=
%(windows_unset_env)s

:END
"""

if __name__ == '__main__':
    try:
        main()
    except BadCommand, e:
        print e
        sys.exit(2)
    


