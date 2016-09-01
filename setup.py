from distutils.core import setup

setup(
    name='Glider Database - Mongo',
    version='1.0',
    author='Michael Lindemuth',
    author_email='mlindemu@usf.edu',
    packages=['gdbmongo'],
    scripts=[
        'gdbmongo/gdam.py',
    ]
)
