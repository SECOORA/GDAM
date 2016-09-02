#!/usr/bin/env python

from distutils.core import setup

setup(
    name='gdam',
    version='1.0',
    author='Michael Lindemuth',
    author_email='mlindemu@usf.edu',
    packages=['gdam'],
    install_requires=[
        'gbdr',
        'pyinotify',
        'pymongo',
        'pyzmq',
    ],
    scripts=[
        'gdam/cli.py',
    ]
)
