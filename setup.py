try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'description'     : 'Python bindings for libCHIRP',
    'author'          : 'Johannes Bergmann',
    'url'             : 'http://www.johannes-bergmann.de/',
    'download_url'    : 'http://www.johannes-bergmann.de/',
    'author_email'    : 'mail@johannes-bergmann.de',
    'version'         : '0.0.1',
    'install_requires': [],
    'packages'        : ['pychirp'],
    'scripts'         : [],
    'name'            : 'pychirp'
}

setup(**config)
