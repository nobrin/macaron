#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Project:
# Module:
try: from setuptools import setup # for development to use 'setup.py develop' command
except ImportError: from distutils.core import setup
import sys
if sys.version_info < (2, 5):
    raise NotImplementedError("Sorry, you need at least Python 2.5 to use Macaron.")

import macaron

setup(
    name             = "macaron",
    version          = macaron.__version__,
    description      = "A simple O/R mapper for SQLite3",
    long_description = macaron.__doc__,
    author           = macaron.__author__,
    url              = "http://nobrin.github.com/macaron",
    py_modules       = ["macaron"],
    scripts          = ["macaron.py"],
    license          = "MIT",
    platforms        = "any",
    classifiers      = [
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Topic :: Database",
        "Topic :: Database :: Front-Ends",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 2.5",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
    ],
)
