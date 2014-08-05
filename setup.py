from distutils.core import setup

setup(
    name='Glider Database Alternative with Mongo',
    version='1.0',
    author='Michael Lindemuth',
    author_email='mlindemu@usf.edu',
    packages=['glider_database_alternative_mongo'],
    scripts=[
        'glider_database_alternative_mongo/gdam.py',
    ]
)
