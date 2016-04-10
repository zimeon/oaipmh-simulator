"""Setup for OAI-PMH simulator."""
from setuptools import setup, Command
import os
# setuptools used instead of distutils.core so that 
# dependencies can be handled automatically

# Extract version number from _version.py. Here we are very strict
# about the format of the version string as an extra sanity check.
# (thanks for comments in 
# http://stackoverflow.com/questions/458550/standard-way-to-embed-version-into-python-package )
import re
VERSIONFILE="oaipmh-simulator/_version.py"
verfilestr = open(VERSIONFILE, "rt").read()
match = re.search(r"^__version__ = '(\d\.\d.\d+(\.\d+)?)'", verfilestr, re.MULTILINE)
if match:
    version = match.group(1)
else:
    raise RuntimeError("Unable to find version string in %s." % (VERSIONFILE))

class Coverage(Command):
    """Class to allow coverage run from setup."""

    description = "run coverage"
    user_options = []

    def initialize_options(self):
        """Empty initialize_options."""
        pass

    def finalize_options(self):
        """Empty finalize_options."""
        pass

    def run(self):
        """Run coverage program."""
        os.system("coverage run --source=xxx setup.py test")
        os.system("coverage report")
        os.system("coverage html")
        print("See htmlcov/index.html for details.")

setup(
    name='oaipmh-validation-service',
    version=version,
    author='Simeon Warner',
    author_email='simeon.warner@cornell.edu',
    packages=[],
    scripts=[],
    classifiers=["Development Status :: 3 - Alpha",
                 "Intended Audience :: Developers",
                 "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
                 "Operating System :: OS Independent", #is this true? know Linux & OS X ok
                 "Programming Language :: Python",
                 "Programming Language :: Python :: 2.7",
                 "Topic :: Internet :: WWW/HTTP",
                 "Topic :: Software Development :: Libraries :: Python Modules",
                 "Environment :: Web Environment"],
    url='https://github.com/zimeon/oaipmh-simulator',
    license='LICENSE.txt',
    description='OAI-PMH Simulator',
    long_description=open('README').read(),
    install_requires=[
        "Flask",
        "Flask-WTF",
        "wtforms",
    ],
    test_suite="tests",
    tests_require=[
        "testfixtures",
    ],
    cmdclass={
        'coverage': Coverage,
    },
)
