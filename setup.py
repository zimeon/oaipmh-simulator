"""Setup for oaipmh-simulator."""
from setuptools import setup, Command
import os
# setuptools used instead of distutils.core so that 
# dependencies can be handled automatically

# Extract version number from _version.py. Here we 
# are very strict about the format of the version string 
# as an extra sanity check. (Thanks for comments in 
# http://stackoverflow.com/questions/458550/standard-way-to-embed-version-into-python-package )
import re
VERSIONFILE="oaipmh_simulator/_version.py"
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
        os.system("coverage run --source=oaipmh-simulator.py,oaipmh_simulator setup.py test")
        os.system("coverage report")
        os.system("coverage html")
        print("See htmlcov/index.html for details.")

setup(
    name='oaipmh-simulator',
    version=version,
    packages=['oaipmh_simulator'],
    scripts=['oaipmh-simulator.py'],
    classifiers=["Development Status :: 4 - Beta",
                 "Intended Audience :: Developers",
                 "License :: OSI Approved :: Apache Software License",
                 "Operating System :: OS Independent", #is this true? know Linux & OS X ok
                 "Programming Language :: Python",
                 "Programming Language :: Python :: 2.7",
                 "Programming Language :: Python :: 3.3",
                 "Programming Language :: Python :: 3.4",
                 "Programming Language :: Python :: 3.5",
                 "Topic :: Internet :: WWW/HTTP",
                 "Topic :: Software Development :: Libraries :: Python Modules",
                 "Environment :: Web Environment"],
    author='Simeon Warner',
    author_email='simeon.warner@cornell.edu',
    description='OAI-PMH Simulator',
    long_description=open('README').read(),
    url='http://github.com/zimeon/oaipmh-simulator',
    install_requires=[
        "defusedxml>=0.4.1",
        "flask>=0.10.1",
    ],
    test_suite="tests",
    cmdclass={
        'coverage': Coverage,
    },
)
