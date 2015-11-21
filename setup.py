from distutils.core import setup

version = open('VERSION').readline().strip()

setup(
    name = 'telecorpo',
    version = version,
    packages = ['tc'],
    scripts = ['telecorpo'],
)
