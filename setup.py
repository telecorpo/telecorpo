from setuptools import setup, find_packages

setup(
    name = 'telecorpo',
    version = '0.1',

    author = 'Pedro Lacerda',
    author_email = 'pslacerda+tc@gmail.com',
    url = 'www.poeticatecnologica.ufba.br',
    description = 'software suite for telematic dance',

    packages = find_packages(),
    scripts = ['bin/tc'],
    install_requires = ['pyzmq', 'colorlog', 'docopt'],

    classifiers = [
        "Development Status :: 2 - Pre-Alpha",
        "License :: Other/Proprietary License"
        "Operating System :: POSIX :: Linux",

        "Programming Language :: Python",
        "Programming Language :: Python :: 2",

        "Topic :: Artistic Software",
        "Topic :: Multimedia :: Video",
        "Topic :: Multimedia :: Video :: Capture",
        "Topic :: Multimedia :: Video :: Display",
        ],
)
