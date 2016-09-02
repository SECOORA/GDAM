#!/usr/bin/env python

from distutils.core import setup

setup(
    name='gdbmongo',
    version='1.0',
    author='Michael Lindemuth',
    author_email='mlindemu@usf.edu',
    packages=['gdbmongo'],
    install_requires=[
        'gbdr',
        'pyinotify',
        'pymongo',
        'pyzmq',
    ],
    scripts=[
        'gdbmongo/gdam.py',
    ]
)
