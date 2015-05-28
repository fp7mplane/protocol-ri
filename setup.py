#!/usr/bin/env python3

from distutils.core import setup

with open('README.md') as file:
    long_description = file.read()

setup(name='mplane-sdk',
      version='0.9.0',
      description='mPlane Software Development Kit for Python 3',
      long_description = long_description,
      author='Brian Trammell',
      author_email='brian@trammell.ch',
      url='http://github.com/fp7mplane/protocol-ri',
      packages=['mplane'],
      package_data={'mplane': ['registry.json']},
      scripts=['scripts/mpcli', 'scripts/mpcom'],
      classifiers=["Development Status :: 3 - Alpha",
                   "Intended Audience :: Developers",
                   "License :: OSI Approved :: "
                   "GNU Lesser General Public License v3 or later (LGPLv3+)",
                   "Operating System :: OS Independent",
                   "Programming Language :: Python :: 3.3",
                   "Topic :: System :: Networking"]
      )
