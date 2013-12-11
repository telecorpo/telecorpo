from setuptools import setup, find_packages
setup (
    name = 'telecorpo',
    version = '0.1',
    packages = find_packages(),
    install_requires = ['docopt', 'flask', 'flask-restful', 'requests', 'colorlog'],
    classifiers = [
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Topic :: Multimedia :: Video",
        "Topic :: Multimedia :: Video :: Capture",
        "Topic :: Multimedia :: Video :: Display",
        "License :: Other/Proprietary License"
        ],
)
