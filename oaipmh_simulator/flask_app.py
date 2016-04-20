"""Flask application to implement simulator."""

from flask import Flask, request, render_template, flash, session, redirect, url_for, logging, make_response
import json
import logging
import optparse
import os.path
import re
import sys
from xml.etree.ElementTree import ElementTree, Element, SubElement
try: #python2, must try this first as a different io exists in python2
    import StringIO as io
except ImportError: #python3
    import io

from oaipmh_simulator._version import __version__
from oaipmh_simulator.repository import Repository, OAI_PMH_Exception, BadVerb, BadArgument, BadResumptionToken, sanitize

app = Flask(__name__)

def get_flask_app():
    """Get app object."""
    return(app) # FIXME - make this actually create app

def index_handler():
    """Render index page for server."""
    return render_template('index.html',
                           base_url=app.config['base_url'])

def oaipmh_baseurl_handler():
    """Support requests for OAI-PMH baseURL."""
    if (request.method == 'GET'):
        args = request.args
    elif (app.config['no_post']):
        alert(405) # Method Not Allowed
    else:
        args = request.form
    handler = OAI_PMH_Handler( app )
    try:
        # Now get the params
        verb = args.get('verb')
        if (verb is None):
            raise BadVerb(verb=verb)
        arguments = {}
        for arg in ['identifier','metadataPrefix','from',
                    'until','set','resumptionToken']:
            if (arg in args):
                arguments[arg] = args.get(arg)
        if (len(arguments)+1 != len(args)):
            raise BadArgument("Extra illegal arguments given.")
        # What to do?
        if (verb == 'Identify'):
            handler.check_args( verb, arguments )
            return handler.identify()
        elif (verb == 'GetRecord'):
            handler.check_args( verb, arguments,
                                required=['identifier', 'metadataPrefix'] )
            return handler.get_record( **arguments )
        elif (verb == 'ListIdentifiers'):
            handler.check_args( verb, arguments,
                                optional=['from','until','set'],
                                required=['metadataPrefix'],
                                exclusive='resumptionToken' )
            return handler.list_either( False, **arguments )
        elif (verb == 'ListRecords'):
            handler.check_args( verb, arguments,
                                optional=['from','until','set'],
                                required=['metadataPrefix'],
                                exclusive='resumptionToken' )
            return handler.list_either( True, **arguments )
        elif (verb == 'ListMetadataFormats'):
            handler.check_args( verb, arguments,
                                optional=['identifier'] )
            return handler.list_metadata_formats( **arguments )
        elif (verb == 'ListSets'):
            handler.check_args( verb, arguments, 
                                exclusive='resumptionToken' )
            return handler.list_sets( **arguments )
        else:
            bad_verb=verb
            verb=None
            raise BadVerb(verb=bad_verb)
    except OAI_PMH_Exception as e:
        return( handler.error(e, verb) )


def TextSubElement( parent, tag, text=None ):
    """Add element named tag with content text iff text not None."""
    #FIXME - make handle multiple elements if text is iterable
    if (text is not None):
       SubElement( parent, tag).text = text


class OAI_PMH_Handler(object):
    """Class to handle request against OAI-PMH baseURL in a Flask app."""

    def __init__(self, app=None ):
        """Initialize OAI-PMH baseURL handler."""
        self.app = app
        self.repo = app.config['repo'] if app else None
        self.root = None
        # Record substitutions we need to make in XML output
        self.sub_num = 0
        self.subs = {}

    def sub(self, xml):
        """Set up substitution of xml, return match string to insert."""
        self.sub_num += 1
        match = "#-#-#-#-#--SUB--%d--#-#-#-#-#" % (self.sub_num)
        self.subs[match] = xml
        return( match )

    def base_tree(self, verb):
        """Create start of XML tree for OAI-PMH response.

        This format applies to all OAI-PMH responses. Note that although
        OAI-PMH responses are XML, there are a number of rather more specific
        stipulations about namespaces that _MUST_ be used and such. See:
        https://www.openarchives.org/OAI/openarchivesprotocol.html#XMLResponse
        """
        base_url = self.app.config['base_url']
        root = Element('OAI-PMH',
                       {'xmlns': 'http://www.openarchives.org/OAI/2.0/',
                        'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                        'xsi:schemaLocation': 'http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd'
                        } )
        TextSubElement( root, 'responseDate', '2002-02-08T12:00:01Z')
        req = SubElement( root, 'request', {} if verb is None else {'verb': verb} )
        req.text = base_url
        self.root = root

    def add_header(self, parent, record):
        """Add OAI-PMH <header> block under parent in XML."""
        header = SubElement( parent, 'header' )
        TextSubElement( header, 'identifier', record.identifier )
        TextSubElement( header, 'datestamp', record.datestamp )
        for set_spec in record.set_specs:
            TextSubElement( header, 'setSpec', set_spec )
        if (record.status is not None):
            TextSubElement( header, 'status', record.status )

    def add_metadata(self, parent, record):
        """Add OAI-PMH <metadata> block under parent in XML.

        Support both inclusion of XML defined by the structured
        data in record.metadataow can we include some XML in here?
        """
        TextSubElement( parent, 'metadata', self.sub(record.metadata) )

    def serialize_tree(self):
        """Serialize XML tree from root."""
        tree = ElementTree(self.root);
        xml_buf=io.StringIO()
        if (sys.version_info < (2,7)):
            tree.write(xml_buf,encoding='UTF-8')
        elif (sys.version_info < (3,0)):
            tree.write(xml_buf,encoding='UTF-8',xml_declaration=True,method='xml')
        else:
            tree.write(xml_buf,encoding="unicode",xml_declaration=True,method='xml')
        xml = xml_buf.getvalue()
        # Now if we have XML chunks to indert for the records, do that
        # by string sustitution...
        for match in self.subs:
            xml = re.sub(match, self.subs[match], xml)
        return(xml)

    def make_xml_response(self):
        """Make Flask Response for XML tree."""
        response = make_response( self.serialize_tree() )
        response.headers['Content-type'] = 'application/xml'
        return( response )

    def identify(self):
        """Make Identify response.

        http://www.openarchives.org/OAI/openarchivesprotocol.html#Identify
        """
        repo = self.repo
        self.base_tree(verb='Identify')
        resp = SubElement( self.root, 'Identify' )
        TextSubElement( resp, 'repositoryName', repo.repository_name )
        TextSubElement( resp, 'baseURL', app.config['base_url'] )
        TextSubElement( resp, 'protocolVersion', repo.protocol_version )
        for ae in repo.admin_email:
            TextSubElement( resp, 'adminEmail', ae )
        TextSubElement( resp, 'earliestDatestamp', repo.earliest_datestamp )
        TextSubElement( resp, 'deletedRecord', repo.deleted_record )
        TextSubElement( resp, 'granularity', repo.granularity )
        return self.make_xml_response()

    def get_record(self, identifier, metadataPrefix):
        """Mage GetRecord response.

        http://www.openarchives.org/OAI/openarchivesprotocol.html#GetRecord
        """
        repo = self.repo
        record = repo.select_record( identifier, metadataPrefix )
        self.base_tree( verb='GetRecord' )
        resp = SubElement( self.root, 'GetRecord' )
        self.add_header( resp, record )
        self.add_metadata( resp, record )
        return self.make_xml_response()

    def list_either(self, include_records=True, resumptionToken=None, **select_args):
        """Make ListRecords or ListIdentifiers response."""
        repo = self.repo
        if (resumptionToken is not None):
            raise BadResumptionToken() # don't support yet
        else:
            records = repo.select_records(**select_args)
            self.base_tree( verb='ListIdentifiers' )
            resp = SubElement( self.root, 'ListIdentifiers' )
            for record in records:
                self.add_header( resp, record )
                if (include_records):
                    self.add_metadata( resp, record )
            return self.make_xml_response()

    def list_metadata_formats(self, identifier=None):
        """Make ListMetadataFormats response.

        https://www.openarchives.org/OAI/openarchivesprotocol.html#ListMetadataFormats
        """
        repo = self.repo
        if (identifier is not None):
            metadata_formats = repo.select_item( identifier ).metadata_formats()
        else:
            metadata_formats = repo.metadata_formats()
        self.base_tree( verb='ListMetadataFormats' )
        resp = SubElement( self.root, 'ListMetadataFormats' )
        for m in metadata_formats:
            mf = SubElement( resp, 'metadataFormat' )
            TextSubElement( mf, 'metadataPrefix', m )
            # FIXME - add other data
        return self.make_xml_response()

    def list_sets(self):
        """Make ListSets response.

        https://www.openarchives.org/OAI/openarchivesprotocol.html#ListSets

        Technically, this request can have a resumptionToken but this
        is not implemented here.
        """
        repo = self.repo
        self.base_tree(verb='ListSets' )
        resp = SubElement( self.root, 'ListSets' )
        for set_spec in repo.set_specs():
            set_element = SubElement( resp, 'set' )
            TextSubElement( set_element, 'setSpec', set_spec )
            (name, description) = repo.set_name_description(set_spec)
            if (name is not None):
                TextSubElement( set_element, 'setName', name )
            if (description is not None):
                # Description is XML, add placeholder and sub later
                TextSubElement( set_element, 'setDescription',
                                self.sub(description) )
        return self.make_xml_response()

    def check_args(self, verb, arguments, optional=None, required=None, exclusive=None):
        """Check that only arguments allowed are not others are present.

        Will raise BadArgument exception if errors present.
        """
        optional = [] if optional is None else optional
        required = [] if required is None else required
        # Check exclusive first, if there is an exclusive argument
        # allowed and it is present, then there must not be any others
        if (exclusive is not None and exclusive in arguments):
            if (len(arguments)>1):
                raise BadArgument("Exclusive argument (%s) present in addition to other arguments (%s) in %s request" % (exclusive,','.join(sorted(arguments.keys())),verb))
            else:
                return # done, just the exclusive argument
        # Now check nothing except option amd required args
        allowed = optional+required
        bad = set()
        for arg in arguments:
            if (arg not in allowed):
                bad.add(arg)
        if (len(bad)>0):
            raise BadArgument("Illegal arguments (%s) in %s request" % (','.join(sorted(bad)),verb))
        # Now check all required args present
        missing = set()
        for arg in required:
            if (arg not in arguments):
                missing.add(arg)
        if (len(missing)>0):
            raise BadArgument("Arguments (%s) required but missing in %s request" % (','.join(sorted(missing)),verb))

    def error(self, e, verb ):
        """Generate OAI-PMH XML error response for exception e."""
        self.base_tree( verb=verb )
        err = SubElement( self.root, 'error', {'code': e.code} )
        err.text = str(e)
        return self.make_xml_response()

