"""Flask application to implement simulator."""

from flask import Flask, request, render_template, flash, session, redirect, url_for, logging, make_response
import json
import logging
import optparse
import os.path
import sys
from xml.etree.ElementTree import ElementTree, Element, SubElement
try: #python2, must try this first as a different io exists in python2
    import StringIO as io
except ImportError: #python3
    import io

from oaipmh_simulator._version import __version__
from oaipmh_simulator.repository import Repository, OAI_PMH_Exception, BadArgument, sanitize

app = Flask(__name__)

def get_flask_app():
    return(app) # FIXME - make this actually create app

def base_tree(verb, base_url):
    """Create start of XML tree for OAI-PMH response.

    This format applies to all OAI-PMH responses. Note that although
    OAI-PMH responses are XML, there are a number of rather more specific
    stipulations about namespaces that _MUST_ be used and such. See:
    https://www.openarchives.org/OAI/openarchivesprotocol.html#XMLResponse
    """
    root = Element('OAI-PMH', 
                   {'xmlns': 'http://www.openarchives.org/OAI/2.0/',
                    'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                    'xsi:schemaLocation': 'http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd'
                    } )
    TextSubElement( root, 'responseDate', '2002-02-08T12:00:01Z')
    req = SubElement( root, 'request', {} if verb is None else {'verb': verb} )
    req.text = base_url
    return(root)

def add_header(parent, record):
    """Add OAI-PMH <header> block under parent in XML."""
    header = SubElement( parent, 'header' )
    TextSubElement( header, 'identifier', record.identifier )
    TextSubElement( header, 'datestamp', record.datestamp )

def add_metadata(parent, record):
    """Add OAI-PMH <metadata> block under parent in XML."""
    metadata = SubElement( parent, 'metadata' )
    #TextSubElement( header, 'identifier', record.identifier )
  
def serialize_tree(root):
    """Serialize XML tree from root."""
    tree = ElementTree(root);
    xml_buf=io.StringIO()
    if (sys.version_info < (2,7)):
        tree.write(xml_buf,encoding='UTF-8')
    elif (sys.version_info < (3,0)):
        tree.write(xml_buf,encoding='UTF-8',xml_declaration=True,method='xml')
    else:
        tree.write(xml_buf,encoding="unicode",xml_declaration=True,method='xml')
    return(xml_buf.getvalue())

def make_xml_response(root):
    """Make Flask Response for XML tree."""
    response = make_response( serialize_tree(root) )
    response.headers['Content-type'] = 'application/xml'
    return( response )

def TextSubElement( parent, tag, text=None ):
    """Add element named tag with content text iff text not None."""
    #FIXME - make handle multiple elements if text is iterable
    if (text is not None):
       SubElement( parent, tag).text = text

def identify(repo):
    """Make Identify response.

    http://www.openarchives.org/OAI/openarchivesprotocol.html#Identify
    """
    root = base_tree(verb='Identify', base_url=app.config['base_url'])
    resp = SubElement( root, 'Identify' )
    TextSubElement( resp, 'repositoryName', repo.repository_name )
    TextSubElement( resp, 'baseURL', app.config['base_url'] )
    TextSubElement( resp, 'protocolVersion', repo.protocol_version )
    for ae in repo.admin_email:
        TextSubElement( resp, 'adminEmail', ae )
    TextSubElement( resp, 'earliestDatestamp', repo.earliest_datestamp )
    TextSubElement( resp, 'deletedRecord', repo.deleted_record )
    TextSubElement( resp, 'granularity', repo.granularity )
    return make_xml_response( root )

def get_record(repo, identifier, metadataPrefix):
    """Mage GetRecord response.

    http://www.openarchives.org/OAI/openarchivesprotocol.html#GetRecord
    """
    record = repo.select_record( identifier, metadataPrefix )
    root = base_tree( verb='GetRecord', base_url=app.config['base_url'] )
    resp = SubElement( root, 'GetRecord' )
    add_header( resp, record )
    add_metadata( resp, record )
    return make_xml_response( root )

def list_identifiers(repo, resumptionToken=None, **select_args):
    """Make ListIdentifiers response.

    http://www.openarchives.org/OAI/openarchivesprotocol.html#ListIdentifiers
    """
    if (resumptionToken is not None):
        alert(400) # don't support yet
    else:
        records = repo.select_records(select_args)
        root = base_tree(verb='ListIdentifiers', base_url=app.config['base_url'])
        resp = SubElement( root, 'ListIdentifiers' )
        for r in records:
            add_header( resp, r )
        return make_xml_response( root )

def list_records(repo, resumptionToken=None, **select_args):
    """Make ListRecords response.

    http://www.openarchives.org/OAI/openarchivesprotocol.html#ListRecords
    """
    if (resumptionToken is not None):
        alert(400) # don't support yet
    else:
        records = repo.select_records(select_args)
        root = base_tree(verb='ListIdentifiers', base_url=app.config['base_url'])
        resp = SubElement( root, 'ListIdentifiers' )
        for r in records:
            add_header( resp, r )
            add_metadata( resp, r )
        return make_xml_response( root )

def list_metadata_formats(repo, identifier=None):
    """Make ListMetadataFormats response.

    https://www.openarchives.org/OAI/openarchivesprotocol.html#ListMetadataFormats
    """
    if (identifier is not None):
        metadata_formats = repo.select_item( identifier ).metadata_formats()
    else:
        metadata_formats = repo.metadata_formats()
    root = base_tree(verb='ListMetadataFormats', base_url=app.config['base_url'])
    resp = SubElement( root, 'ListMetadataFormats' )
    for m in metadata_formats:
        mf = SubElement( resp, 'metadataFormat' )
        TextSubElement( mf, 'metadataPrefix', m )
        # FIXME - add other data
    return make_xml_response( root )

def list_sets(repo):
    """Make ListSets response.

    https://www.openarchives.org/OAI/openarchivesprotocol.html#ListSets

    Technically, this request can have a resumptionToken but this
    is not implemented here.
    """
    root = base_tree(verb='ListSets', base_url=app.config['base_url'])
    resp = SubElement( root, 'ListSets' )
    for set_spec in repo.set_specs():
        set_element = SubElement( resp, 'set' )
        TextSubElement( set_element, 'setSpec', set_spec )
        # FIXME - add other data
    return make_xml_response( root )

@app.route("/")
def index():
    """Render index page for server."""
    return render_template('index.html',
                           base_url=app.config['base_url'])

@app.route("/oai", methods=("GET","POST")) #fixme - should be set
def oaisrv():
    """Support requests for OAI-PMH baseURL."""
    if (request.method == 'GET'):
        args = request.args
    elif (app.config['no_post']):
        alert(405) # Method Not Allowed
    else:
        args = request.form
    # Now get the params
    verb = args.get('verb')
    identifier = args.get('identifier')
    metadataPrefix = args.get('metadataPrefix')
    # What to do?
    try:
        repo = app.config['repo']
        if (verb == 'Identify'):
            return identify(repo)
        elif (verb == 'GetRecord'):
            return get_record(repo, identifier, metadataPrefix)
        elif (verb == 'ListIdentifiers'):
            return list_identifiers(repo)
        elif (verb == 'ListRecords'):
            return list_records(repo)
        elif (verb == 'ListMetadataFormats'):
            return list_metadata_formats(repo, identifier)
        elif (verb == 'ListSets'):
            return list_sets(repo)
        else:
            bad_verb=verb
            verb=None
            raise BadArgument(verb=bad_verb)
    except OAI_PMH_Exception as e:
        root = base_tree(verb=verb, base_url=app.config['base_url'])
        err = SubElement( root, 'error', {'code': e.code} )
        err.text = str(e)
        return make_xml_response( root )
