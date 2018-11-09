#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='supervisor-monitor',
    version='0.0.1',
    description='Supervisor monitor',
    author='Paul Kolesnyk',
    author_email='kolesnyk.paul99@gmail.com',
    url='https://github.com/kolesnykpaul/supervisor-monitor',
    keywords='',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'supervisor-monitor=supervisor-monitor.monitor:main'
        ]
    }
)