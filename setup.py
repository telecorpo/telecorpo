from setuptools import setup, find_packages
from setuptools.command.install import install

import os
import shutil


class CustomInstallCommand(install):

    def run(self):
        install.run(self)
        etcdir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'etc')

        copies = [('/usr/share/gir-1.0', 'GstRtspServer-1.0.gir'),
                  ('/usr/lib/girepository-1.0', 'GstRtspServer-1.0.typelib'),
                  ('/usr/lib/', 'libgstrtspserver-1.0.so.0.203.0')]

        for dst, src in copies:
            src = os.path.join(etcdir, src)
            if not os.path.isfile(dst):
                print('cp {} {}'.format(src, dst))
                shutil.copy(src, dst)
        
        links = ['libgstrtspserver-1.0.so.0',
                 'libgstrtspserver-1.0.so']
        for link in links: 
            src = '/usr/lib/libgstrtspserver-1.0.so.0.203.0'
            dst = os.path.join('/usr/lib', link)
            if not os.path.isfile(dst):
                print('ln -s {} {}'.format(src, dst))
                os.symlink(src, dst)


setup(
    name = 'telecorpo',
    version = '0.8',
    
    cmdclass = {
        'install': CustomInstallCommand,
    },
    packages = find_packages(),
)
