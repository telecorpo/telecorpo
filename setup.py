from setuptools import setup, find_packages

setup(
    name='telecorpo',
    version='0.13',
    packages=find_packages(),
    package_data={
        'tc': ['main.glade', 'producer.glade', 'viewer.glade']
    },
    data_files=[
        ('/usr/share/applications', ['data/telecorpo.desktop']),
        ('/usr/share/gir-1.0', ['data/GstRtspServer-1.0.gir']),
        ('/usr/lib', ['data/libgstrtspserver-1.0.so.0.400.0',
                 'data/libgstrtspserver-1.0.so.0',
                 'data/libgstrtspserver-1.0.so']),
        ('/usr/lib/girepository-1.0', ['data/GstRtspServer-1.0.typelib'])
    ],
    entry_points={
        'console_scripts': ['telecorpo=tc.application:main']
    }
)    
