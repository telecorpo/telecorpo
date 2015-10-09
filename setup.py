from setuptools import setup, find_packages
from setuptools.command.install import install


setup(
    name = 'telecorpo',
    version = '0.99',
    
    packages = find_packages(),
    scripts = ['telecorpo'],
)
