"""Repositoty for OAI-PMH simulator."""

import os
import os.path
import re
import time
import logging
try: #python3
    from urllib.request import URLopener
except ImportError: #python2
    from urllib import URLopener
from defusedxml.ElementTree import parse


class Repository(object):

    """Repositoty for OAI-PMH simulator.

    Within OAI-PMH, there are items with identifiers. Each item may
    have metadata available in zero or more formats/
    """

    def __init__(self):
        """Create Repository object.
        """
        self.items = set()
        # Config
        self.set_path = set_path
        self.exclude_files = ['.*.json']
        self.exclude_dirs = ['CVS','.git']
        self.include_symlinks = False
        # Used internally only:
        self.logger = logging.getLogger('oaipmh_simulator')
        self.compiled_exclude_files = []

    def add(self, item):
        """Add and Item to the repository."""
        self.items.add(item)

    def add_exclude_files(self, exclude_patterns):
        """Add more patterns of files to exclude while building resource_list."""
        for pattern in exclude_patterns:
            self.exclude_files.append(pattern)

    def compile_excludes(self):
        """Compile a set of regexps for files to be exlcuded from scans."""
        self.compiled_exclude_files = []
        for pattern in self.exclude_files:
            try:
                self.compiled_exclude_files.append(re.compile(pattern))
            except re.error as e:
                raise ValueError("Bad python regex in exclude '%s': %s" % (pattern,str(e)))

    def exclude_file(self, file):
        """True if file should be exclude based on name pattern."""
        for pattern in self.compiled_exclude_files:
            if (pattern.match(file)):
                return(True)
        return(False)

    def from_disk(self, path='data'):
        """Fill repositoty from disk.

        Scans files under path looking for records with which to
        build the repository.
        """
        # Compile exclude pattern matches
        self.compile_excludes()
        # is path a directory or a file? for each file: create Resource object, 
        # add, increment counter
        if os.path.isdir(path):
            num_files=0
            for dirpath, dirs, files in os.walk(path,topdown=True):
                for file_in_dirpath in files:
                    num_files+=1
                    if (num_files%50000 == 0):
                        self.logger.info("Repository.from_disk: %d files..." % (num_files))
                    self.add_file(dir=dirpath,file=file_in_dirpath)
                    # prune list of dirs based on self.exclude_dirs
                    for exclude in self.exclude_dirs:
                        if exclude in dirs:
                            self.logger.debug("Excluding dir %s" % (exclude))
                            dirs.remove(exclude)
        else:
            # single file
            self.add_file(file=path)

    def add_file(self, dir=None, file=None):
        """Add a single file to this Repository.
        
        Follows object settings of set_path.
        """
        try:
            if self.exclude_file(file):
                self.logger.debug("Excluding file %s" % (file))
                return
            # get abs filename and also URL
            if (dir is not None):
                file = os.path.join(dir,file)
            if (not os.path.isfile(file) or not (self.include_symlinks or not os.path.islink(file))):
                return
            file_stat=os.stat(file)
        except OSError as e:
            sys.stderr.write("Ignoring file %s (error: %s)" % (file,str(e)))
            return
        r = Resource(uri=uri)
        if (self.set_path):
            # add full local path
            r.path=file
        self.add(r)


class Item(object):

    def __init__(self):
        """Create Item object.

        An item has zero or more records which must each be in a 
        different format. Stored as dict indexed by metadataPrefix.

        An item may be in zero or more sets.
        """
        self.id = None
        self.records = {}
        self.sets = set()

class Record(object):

    def __init__(self):
        """Create a Record object."""
        self.datestamp = None
        self.status = None
        self.metadata = None
        self.about = set()
