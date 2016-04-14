"""Repository for OAI-PMH simulator."""

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

    """Repository for OAI-PMH simulator.

    Within OAI-PMH, there are items with identifiers. Each item may
    have metadata available in zero or more formats/
    """

    def __init__(self, cfg=None):
        """Create Repository object.
        """
        self.items = dict() #index by identifier
        self.repository_name = None
        self.protocol_version = None
        self.admin_email = []
        self.earliest_datestamp = None
        self.deleted_record = 'no'
        self.granularity = 'YYYY-MM-DD'
        # Used internally only:
        self.logger = logging.getLogger('oaipmh_simulator')
        self.compiled_exclude_files = []
        # Do we have config?
        self.cfg = cfg
        if (cfg):
            self.repository_name = cfg.get('repositoryName')
            self.protocol_version = cfg.get('protocolVersion')
            self.admin_email = cfg.get('adminEmail')
            self.earliest_datestamp = cfg.get('earliestDatestamp')
            self.deleted_record = cfg.get('deletedRecord')
            self.granularity = cfg.get('granularity')
            for r in cfg.get('records',[]):
                # Make for find Item
                identifier = r.get('identifier')
                self.logger.warn( "Adding %s" % (identifier) )
                if (identifier in self.items):
                    item = self.items[identifier]
                    # fixme, check other data
                else:
                    item = Item( identifier=identifier, sets=r.get('sets') )
                    self.add_item(item)
                # Now add the Record data
                record = Record( identifier=identifier,
                                 metadataPrefix=r.get('metadataPrefix'),
                                 datestamp=r.get('datestamp'),
                                 status=r.get('status'),
                                 metadata=r.get('metadata'),
                                 about=r.get('about') )
                item.add_record( record )
            # Stats...
            self.logger.warn("Repository initialized: %d items" % (len(self.items)))

    def add_item(self, item):
        """Add an Item to the repository."""
        self.items[item.identifier] = item

    def select_record( self, identifier=None, metadataPrefix=None ):
        """Select record based on identifier and metadataPrefix.

        Raise appropriate exception if the specified record is not
        available.
        """
        self.logger.warn("id=%s mp=%s %s" % (identifier,metadataPrefix,str(self.items)) )
        if (identifier not in self.items):
            raise IdDoesNotExist(identifier)
        item = self.items[identifier]
        if (metadataPrefix not in item.records):
            raise CannotDisseminateFormat(metadataPrefix)
        return( item.records[metadataPrefix] )

    def select_records( self, sfrom=None, suntil=None, smetadataPrefix=None, sset=None ):
        records = []
        for i in self.items.values():
            for r in i.records.values():
                records.append(r)
        return( records )


class Item(object):

    def __init__(self, identifier, sets=None):
        """Create Item object.

        An item has zero or more records which must each be in a 
        different format. Stored as dict indexed by metadataPrefix.

        An item may be in zero or more sets.
        """
        self.identifier = identifier
        self.records = {}
        self.sets = set() if sets is None else sets

    def add_record(self, record ):
        """Add Record in specific metadataPrefix format to this Item."""
        self.records[record.metadataPrefix] = record


class Record(object):

    def __init__(self, identifier, metadataPrefix='oai_dc', datestamp=None, status=None, metadata=None, about=None):
        """Create a Record object."""
        self.identifier = identifier
        self.metadataPrefix = metadataPrefix
        self.datestamp = datestamp
        self.status = status
        self.metadata = metadata
        self.about = set() if about is None else about


class CannotDisseminateFormat(Exception):

    def __init__(self, metadataPrefix=''):
        pass

class IdDoesNotExist(Exception):

    def __init__(self, identifier=''):
        pass

