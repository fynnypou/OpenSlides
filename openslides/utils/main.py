#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    openslides.utils.main
    ~~~~~~~~~~~~~~~~~~~~~

    Some functions for OpenSlides.

    :copyright: 2011–2013 by OpenSlides team, see AUTHORS.
    :license: GNU GPL, see LICENSE for more details.
"""

import ctypes
import os
import socket
import sys
import tempfile
import threading
import time
import webbrowser

from base64 import b64encode
from django.core.exceptions import ImproperlyConfigured
from django.conf import ENVIRONMENT_VARIABLE


UNIX_VERSION = 'Unix Version'
WINDOWS_VERSION = 'Windows Version'
WINDOWS_PORTABLE_VERSION = 'Windows Portable Version'


class PortableDirNotWritable(Exception):
    pass


class DatabaseInSettingsError(Exception):
    pass


def filesystem2unicode(path):
    """
    Transforms a path string to unicode according to the filesystem's encoding.
    """
    # TODO: Delete this function after switch to Python 3.
    if not isinstance(path, unicode):
        filesystem_encoding = sys.getfilesystemencoding() or sys.getdefaultencoding()
        path = path.decode(filesystem_encoding)
    return path


def detect_openslides_type():
    """
    Returns the type of this OpenSlides version.
    """
    if sys.platform == 'win32':
        if os.path.basename(sys.executable).lower() == 'openslides.exe':
            # Note: sys.executable is the path of the *interpreter*
            #       the portable version embeds python so it *is* the interpreter.
            #       The wrappers generated by pip and co. will spawn the usual
            #       python(w).exe, so there is no danger of mistaking them
            #       for the portable even though they may also be called
            #       openslides.exe
            openslides_type = WINDOWS_PORTABLE_VERSION
        else:
            openslides_type = WINDOWS_VERSION
    else:
        openslides_type = UNIX_VERSION
    return openslides_type


def get_default_settings_path(openslides_type):
    """
    Returns the default settings path according to the OpenSlides type.

    The argument 'openslides_type' has to be one of the three types mentioned in
    openslides.utils.main.
    """
    if openslides_type == UNIX_VERSION:
        parent_directory = filesystem2unicode(os.environ.get(
            'XDG_CONFIG_HOME', os.path.join(os.path.expanduser('~'), '.config')))
    elif openslides_type == WINDOWS_VERSION:
        parent_directory = get_win32_app_data_path()
    elif openslides_type == WINDOWS_PORTABLE_VERSION:
        parent_directory = get_win32_portable_path()
    else:
        raise TypeError('%s is not a valid OpenSlides type.' % openslides_type)
    return os.path.join(parent_directory, 'openslides', 'settings.py')


def setup_django_settings_module(settings_path):
    """
    Sets the environment variable ENVIRONMENT_VARIABLE, that means
    'DJANGO_SETTINGS_MODULE', to the given settings.
    """
    settings_file = os.path.basename(settings_path)
    settings_module_name = ".".join(settings_file.split('.')[:-1])
    if '.' in settings_module_name:
        raise ImproperlyConfigured("'.' is not an allowed character in the settings-file")
    settings_module_dir = os.path.dirname(settings_path)  # TODO: Use absolute path here or not?
    sys.path.insert(0, settings_module_dir)
    os.environ[ENVIRONMENT_VARIABLE] = '%s' % settings_module_name


def ensure_settings(settings, args):
    """
    Create settings if a settings path is given and this file still does not exist.
    """
    if settings and not os.path.exists(settings):
        if not hasattr(args, 'user_data_path'):
            context = get_default_settings_context()
        else:
            context = get_default_settings_context(args.user_data_path)
        write_settings(settings, **context)
        print('Settings file at %s successfully created.' % settings)


def get_default_settings_context(user_data_path=None):
    """
    Returns the default context values for the settings template.

    The argument 'user_data_path' is a given path for user specific data or None.
    """
    # Setup path for user specific data (SQLite3 database, media, search index, ...):
    # Take it either from command line or get default path
    if user_data_path:
        default_context = get_user_data_path_values(
            user_data_path=user_data_path,
            default=False)
    else:
        openslides_type = detect_openslides_type()
        user_data_path = get_default_user_data_path(openslides_type)
        default_context = get_user_data_path_values(
            user_data_path=user_data_path,
            default=True,
            openslides_type=openslides_type)
    default_context['debug'] = 'False'
    return default_context


def get_default_user_data_path(openslides_type):
    """
    Returns the default path for user specific data according to the OpenSlides
    type.

    The argument 'openslides_type' has to be one of the three types mentioned
    in openslides.utils.main.
    """
    if openslides_type == UNIX_VERSION:
        default_user_data_path = filesystem2unicode(os.environ.get(
            'XDG_DATA_HOME', os.path.join(os.path.expanduser('~'), '.local', 'share')))
    elif openslides_type == WINDOWS_VERSION:
        default_user_data_path = get_win32_app_data_path()
    elif openslides_type == WINDOWS_PORTABLE_VERSION:
        default_user_data_path = get_win32_portable_path()
    else:
        raise TypeError('%s is not a valid OpenSlides type.' % openslides_type)
    return default_user_data_path


def get_win32_app_data_path():
    """
    Returns the path to Windows' AppData directory.
    """
    shell32 = ctypes.WinDLL("shell32.dll")
    SHGetFolderPath = shell32.SHGetFolderPathW
    SHGetFolderPath.argtypes = (
        ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32,
        ctypes.c_wchar_p)
    SHGetFolderPath.restype = ctypes.c_uint32

    CSIDL_LOCAL_APPDATA = 0x001c
    MAX_PATH = 260

    buf = ctypes.create_unicode_buffer(MAX_PATH)
    res = SHGetFolderPath(0, CSIDL_LOCAL_APPDATA, 0, 0, buf)
    if res != 0:
        raise Exception("Could not determine Windows' APPDATA path")

    return buf.value


def get_win32_portable_path():
    """
    Returns the path to the Windows portable version.
    """
    # NOTE: sys.executable will be the path to openslides.exe
    #       since it is essentially a small wrapper that embeds the
    #       python interpreter
    portable_path = filesystem2unicode(os.path.dirname(os.path.abspath(sys.executable)))
    try:
        fd, test_file = tempfile.mkstemp(dir=portable_path)
    except OSError:
        raise PortableDirNotWritable(
            'Portable directory is not writeable. '
            'Please choose another directory for settings and data files.')
    else:
        os.close(fd)
        os.unlink(test_file)
    return portable_path


def get_user_data_path_values(user_data_path, default=False, openslides_type=None):
    """
    Returns a dictionary of the user specific data path values for the new
    settings file.

    The argument 'user_data_path' is a path to the directory where OpenSlides
    should store the user specific data like SQLite3 database, media and search
    index.

    The argument 'default' is a simple flag. If it is True and the OpenSlides
    type is the Windows portable version, the returned dictionary contains
    strings of callable functions for the settings file, else it contains
    string paths.

    The argument 'openslides_type' can to be one of the three types mentioned in
    openslides.utils.main.
    """
    if default and openslides_type == WINDOWS_PORTABLE_VERSION:
        user_data_path_values = {}
        user_data_path_values['import_function'] = 'from openslides.utils.main import get_portable_paths'
        user_data_path_values['database_path_value'] = "get_portable_paths('database')"
        user_data_path_values['media_path_value'] = "get_portable_paths('media')"
        user_data_path_values['whoosh_index_path_value'] = "get_portable_paths('whoosh_index')"
    else:
        user_data_path_values = get_user_data_path_values_with_path(user_data_path, 'openslides')
    return user_data_path_values


def get_user_data_path_values_with_path(*paths):
    """
    Returns a dictionary of the user specific data path values for the new
    settings file. Therefor it uses the given arguments as parts of the path.
    """
    final_path = os.path.abspath(os.path.join(*paths))
    user_data_path_values = {}
    user_data_path_values['import_function'] = ''
    variables = (('database_path_value', 'database.sqlite'),
                 ('media_path_value', 'media'),
                 ('whoosh_index_path_value', 'whoosh_index'))
    for key, value in variables:
        path_list = [final_path, value]
        if '.' not in value:
            path_list.append('')
        user_data_path_values[key] = repr(
            filesystem2unicode(os.path.join(*path_list)))
    return user_data_path_values


def write_settings(settings_path, template=None, **context):
    """
    Creates the settings file at the given path using the given values for the
    file template.
    """
    if template is None:
        with open(os.path.join(os.path.dirname(__file__), 'settings.py.tpl')) as template_file:
            template = template_file.read()
    context.setdefault('secret_key', b64encode(os.urandom(30)))
    content = template % context
    settings_module = os.path.realpath(os.path.dirname(settings_path))
    if not os.path.exists(settings_module):
        os.makedirs(settings_module)
    with open(settings_path, 'w') as settings_file:
        settings_file.write(content)


def get_portable_paths(name):
    """
    Returns the paths for the Windows portable version on runtime for the
    SQLite3 database, the media directory and the search index. The argument
    'name' can be 'database', 'media' or 'whoosh_index'.
    """
    if name == 'database':
        path = os.path.join(get_win32_portable_path(), 'openslides', 'database.sqlite')
    elif name == 'media':
        path = os.path.join(get_win32_portable_path(), 'openslides', 'media', '')
    elif name == 'whoosh_index':
        path = os.path.join(get_win32_portable_path(), 'openslides', 'whoosh_index', '')
    else:
        raise TypeError('Unknown type %s' % name)
    return path


def get_port(address, port):
    """
    Returns the port for the server. If port 80 is given, checks if it is
    available. If not returns port 8000.

    The argument 'address' should be an IP address. The argument 'port' should
    be an integer.
    """
    if port == 80:
        # test if we can use port 80
        s = socket.socket()
        try:
            s.bind((address, port))
            s.listen(-1)
        except socket.error:
            port = 8000
        finally:
            s.close()
    return port


def get_browser_url(address, port):
    """
    Returns the url to open the web browser.

    The argument 'address' should be an IP address. The argument 'port' should
    be an integer.
    """
    browser_url = 'http://'
    if address == '0.0.0.0':
        browser_url += 'localhost'
    else:
        browser_url += address
    if not port == 80:
        browser_url += ":%d" % port
    return browser_url


def start_browser(browser_url):
    """
    Launches the default web browser at the given url and opens the
    webinterface.
    """
    browser = webbrowser.get()

    def function():
        # TODO: Use a nonblocking sleep event here. Tornado has such features.
        time.sleep(1)
        browser.open(browser_url)

    thread = threading.Thread(target=function)
    thread.start()


def get_database_path_from_settings():
    """
    Retrieves the database path out of the settings file. Returns None,
    if it is not a SQLite3 database.
    """
    from django.conf import settings as django_settings
    from django.db import DEFAULT_DB_ALIAS

    db_settings = django_settings.DATABASES
    default = db_settings.get(DEFAULT_DB_ALIAS)
    if not default:
        raise DatabaseInSettingsError("Default databases is not configured")
    database_path = default.get('NAME')
    if not database_path:
        raise DatabaseInSettingsError('No path specified for default database.')
    if default.get('ENGINE') != 'django.db.backends.sqlite3':
        database_path = None
    return database_path
