from setuptools import setup, find_packages
setup (
    name = 'telecorpo',
    version = '0.1',
    packages = find_packages(),
    install_requires = ['docopt', 'flask', 'flask-restful', 'requests'],
    # entry_points = {
    #     'console_scripts': ['tc = tc.cli:main']
    #     }
)
