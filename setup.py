from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

setup(
    name='py_ilp_virtual_plugin',
    version='0.0.0',
    description='A Pythonic plugin to the Interledger Protocol',
    author='Steven Truong',
    author_email='truong@ripple.com',
    license='MIT',

    classifiers=[
        'Development Status :: 1 - Planning',

        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],

    keywords='ILP interledger protocol payments',
    packages=['model', 'util', 'plugin'],
    install_requires=['pymitter', 'dotmap', 'coloredlogs', 'paho-mqtt', 'promise'],
    entry_points={
        'console_scripts': [
            'sample=sample:main',
        ],
    },
)