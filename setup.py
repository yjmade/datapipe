#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
import sys

if 'sdist' in sys.argv:
    from pypandoc import convert
    long_description = convert('README.md', 'rst')
else:
    long_description = None
VERSION = "0.1.0"

setup(
    name='datapipe',
    version=VERSION,
    description='Data Processing Framework that allow you to processing data like building blocks',
    url="https://github.com/yjmade/datapipe",
    long_description=long_description,
    author='Jay Young(yjmade)',
    author_email='dev@yjmade.net',
    packages=find_packages(),
    install_requires=["django-errorlog", "celery<4.0", "django-celery", "django-pgjsonb"],
    classifiers=[
        'Intended Audience :: Developers',
    ],
    license='MIT',
    keywords='data processing pipeline',

)
