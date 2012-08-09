# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
import os

version = open('stxnext/scheduler/version.txt').read()

setup(name='stxnext.scheduler',
      version=version,
      author='STX Next Sp. z o.o, Tomasz Maćkowiak',
      author_email='info@stxnext.pl',
      description="Schedules actions queue to be executed on given time",
      long_description=open("README.md").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from
      # http://pypi.python.org/pypi?:action=list_classifiers
      keywords='plone schedule',
      url='http://www.stxnext.pl/',
      license='Zope Public License, Version 2.1 (ZPL)',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['stxnext'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'Plone',
          'setuptools',
          'collective.autopermission==1.0b1',
          'simplejson',
      ],
      extras_require={
          'test': ['plone.app.testing',],
      },
      entry_points="""
      # -*- Entry points: -*-

      [z3c.autoinclude.plugin]
      target = plone
      """,
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Framework :: Zope2',
          'Framework :: Plone',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: Zope Public License',
          'Natural Language :: English',
          'Programming Language :: Python',
          ]
      )
