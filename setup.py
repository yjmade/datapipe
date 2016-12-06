#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
import sys

if 'bdist_wheel' in sys.argv:
    from pypandoc import convert
    long_description = convert('README.md', 'rst')
VERSION = "0.0.23"

setup(
    name='datapipe',
    version=VERSION,
    description='Data Processing Framework that allow you to processing data like building blocks',
    url="https://github.com/yjmade/datapipe",
    long_description=long_description,
    author='Jay Young(yjmade)',
    author_email='dev@yjmade.net',
    packages=find_packages(),
    install_requires=["django-errorlog", "celery<4.0", "django-celery"],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    license='MIT',
    keywords='data processing pipeline',

)
