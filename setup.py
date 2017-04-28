#!/usr/bin/env python

from setuptools import setup


def readme():
    with open('README.md') as f:
        return f.read()


def version():
    with open('VERSION') as f:
        return f.read().strip()


reqs = [line.strip() for line in open('requirements.txt') if not line.startswith('#')]


setup(
    name='gdam',
    version=version(),
    description='Watches a directory for new *db flight/science files and '
                'inserts the data into a MongoDB instance and publishes the '
                'data to a ZeroMQ socket.',
    long_description=readme(),
    license='MIT',
    author='Kyle Wilcox',
    author_email='kyle@axiomdatascience.com',
    install_requires=reqs,
    url='https://github.com/axiom-data-science/GDAM',
    packages=['gdam'],
    entry_points = {
        'console_scripts': [
            'gdam-cli=gdam.cli:main',
            'gdam2nc=gdam.nc:main',
            'nc2ftp=gdam.ftp:main'
        ],
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering'
    ],
)
