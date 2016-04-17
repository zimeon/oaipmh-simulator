"""Repository for OAI-PMH simulator."""

from datetime import datetime
from dateutil import parser as dateutil_parser
import os
import os.path
import re
import time
import logging
try: #python3
    from urllib.request import URLopener
    from urllib.parse import quote
except ImportError: #python2
    from urllib import URLopener, quote
from defusedxml.ElementTree import parse


class Repository(object):
    """Repository for OAI-PMH simulator.

    Within OAI-PMH, there are items with identifiers. Each item may
    have metadata available in zero or more formats/
    """

    def __init__(self, cfg=None):
        """Initialize Repository object, taking settings from cfg."""
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
                # Now make and add the Record data
                record = Record( metadataPrefix=r.get('metadataPrefix'),
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

    def select_item( self, identifier=None ):
        """Select item based on identifier.

        Raise appropriate exception if the specified item is not
        available.
        """
        if (identifier not in self.items):
            raise IdDoesNotExist(identifier)
        return self.items[identifier]

    def select_record( self, identifier=None, metadataPrefix=None ):
        """Select record based on identifier and metadataPrefix.

        Raise appropriate exception if the specified record is not
        available.
        """
        self.logger.warn("id=%s mp=%s %s" % (identifier,metadataPrefix,str(self.items)) )
        item = self.select_item( identifier )
        if (metadataPrefix not in item.records):
            raise CannotDisseminateFormat(metadataPrefix)
        return( item.records[metadataPrefix] )

    def select_records( self, metadataPrefix=None, **args ):
        """Select records that match parameters.

        Used to implement ListIdentifiers and ListRecords.

        WARNING - using **args to deal with 'from' that
        can't be used as an argument name. Also do the same
        for 'until' and 'set'.
        """
        from_ds = Datestamp(args['from']) if 'from' in args else None
        until_ds = Datestamp(args['until']) if 'until' in args else None
        set_spec = args['set'] if 'set' in args else None
        records = []
        for item in self.items.values():
            for record in item.records.values():
                records.append(record) # FIXME - no selection yet!
        return( records )

    def metadata_formats(self):
        """List all metdata formats used in this repository.

        Simply does a brute force taversal of the repository aggregating
        all metadata formats.
        """
        metadata_formats = set()
        for i in self.items.values():
            for m in i.metadata_formats():
                if (m not in metadata_formats):
                    metadata_formats.add(m)
        return( sorted(metadata_formats) )

    def set_specs(self):
        """List all setSpec values used in this repository.

        Simply does a brute force taversal of the repository aggregating
        all sets defined.
        """
        set_specs = set()
        for item in self.items.values():
            for m in item.set_specs():
                if (m not in set_specs):
                    set_specs.add(m)
        if (len(set_specs)==0):
            raise NoSetHierarchy()
        return( sorted(set_specs) )


class Item(object):
    """Item in OAI-PMH."""

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
        record.item = self

    def metadata_formats(self):
        """List metadataFormats for this item."""
        return( sorted(self.records.keys()) )

    def set_specs(self):
        """List setSpecs for this item."""
        return( sorted(self.sets) )


class Record(object):
    """Record in OAI-PMH."""

    def __init__(self, metadataPrefix='oai_dc', datestamp=None, status=None, metadata=None, about=None, item=None):
        """Create a Record object."""
        self.metadataPrefix = metadataPrefix
        self.datestamp = datestamp
        self.status = status
        self.metadata = metadata
        self.about = set() if about is None else about
        # Link up to item this record is part of
        self.item = item

    @property
    def identifier(self):
        """Identifier of parent item."""
        return( self.item.identifier )

    @property
    def set_specs(self):
        """The setSpecs for parent item."""
        return( self.item.set_specs() )


class Datestamp(object):
    """OAI-PMH specific datastamps."""

    def __init__(self, date_str=None, granularity=None):
        self.date_str = date_str
        self.granularity = granularity
        self.datetime = None # parsed value
        if (self.date_str is not None):
            self.parse_date_str()

    def parse_date_str(self):
        """Parse the date string.

        Will raise BadArgument for any error condition. If 
        self.granularity is set then checks that the date_str
        matches that.
        """
        date_str = self.date_str
        m = re.match(r'\d\d\d\d-\d\d-\d\d(T\d\d:\d\d:\d\dZ)?$', date_str)
        if (m):
            if (m.group(1)):
                granularity = 'seconds'
            else:
                date_str += 'T00:00:00Z'
                granularity = 'days'
            try:
                self.datetime = dateutil_parser.parse(date_str)
            except ValueError as e:
                raise BadArgument("Bad datetime %s: %s." % (sanitize(self.date_str), str(e)))
        else:
            raise BadArgument("Bad datetime %s, must have either YYYY-MM-DD or YYYY-MM-DDThh:mm:ssZ form." % (sanitize(date_str)))
        if (self.granularity and self.granularity!=granularity):
            raise BadArgument("Bad datetime, expected %s granularity and got %s granularity" % (self.granularity,granularity))
        self.granularity = granularity

class OAI_PMH_Exception(Exception):
    """Superclass for all OAI-PMH Exceptions.

    See documentation for error conditions in:
    https://www.openarchives.org/OAI/openarchivesprotocol.html#ErrorConditions
    """

    def __str__(self):
        """Helpful message to be used as content of <error> element."""
        return self.msg

class BadArgument(OAI_PMH_Exception):
    """badArgument error."""

    def __init__(self, msg=None):
        """Initialize BadArgument."""
        self.code = "badArgument"
        self.msg = "The request includes illegal arguments, is missing required arguments, includes a repeated argument, or values for arguments have an illegal syntax."
        if (msg is not None):
            self.msg += " " + msg


class BadVerb(OAI_PMH_Exception):
    """badVerb error."""

    def __init__(self, msg=None, verb=None):
        """Initialize BadVerb, record verb in message if given."""
        self.code = "badVerb"
        self.msg = "Value of the verb argument is not a legal OAI-PMH verb, the verb argument is missing, or the verb argument is repeated."
        if (verb is None):
            self.msg += " Missing verb." 
        else:
            self.msg += " Bad verb (%s)." % sanitize(verb)
        if (msg is not None):
            self.msg += " " + msg
       

class BadResumptionToken(OAI_PMH_Exception):
    """badResumptionToken error."""

    def __init__(self, resumptionToken=None):
        """Initialize BadResumptionToken, record value of resumptionToken."""
        self.code = "badResumptionToken"
        self.msg = "The value of the resumptionToken argument (%s) is invalid or expired." % sanitize(resumptionToken)

class CannotDisseminateFormat(OAI_PMH_Exception):
    """cannotDisseminateFormat error."""

    def __init__(self):
        """Initialize CannotDisseminateFormat."""
        self.code = "cannotDisseminateFormat"
        self.msg = "The metadata format identified by the value given for the metadataPrefix argument is not supported by the item or by the repository."

class IdDoesNotExist(OAI_PMH_Exception):
    """idDoesNotExist error."""

    def __init__(self, identifier=''):
        """Initialize IdDoesNotExist, record identifier in message."""
        self.code = "idDoesNotExist"
        self.msg = "The value of the identifier argument (%s) is unknown or illegal in this repository." % sanitize(identifier)

class NoRecordsMatch(OAI_PMH_Exception):
    """noRecordsMatch error."""

    def __init__(self):
        """Initialize NoRecordsMatch."""
        self.code = "noRecordsMatch"
        self.msg = "The combination of the values of the from, until, set and metadataPrefix arguments results in an empty list."

class NoMetadataFormats(OAI_PMH_Exception):
    """noMetadataFormats error."""

    def __init__(self):
        """Initialize NoMetadataFormats."""
        self.code = "noMetadataFormats"
        self.msg = "There are no metadata formats available for the specified item."

class NoSetHierarchy(OAI_PMH_Exception):
    """noSetHierarchy error."""

    def __init__(self):
        """Initialize NoSetHierarchy."""
        self.code = "noSetHierarchy"
        self.msg = "The repository does not support sets."

def sanitize(fanged):
    """Sanitize input string for safe use in helpful error messages."""
    defanged = quote(str(fanged)) #perhaps too brutal to be readable
    defanged = (defanged[:40] + '...') if len(defanged) > 40 else defanged
    return(defanged)