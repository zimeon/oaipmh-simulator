#!/usr/bin/env python
"""OAI-PMH Simulator oaipmh_simulator.

Copyright 2016 Simeon Warner

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License
"""

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
from oaipmh_simulator.repository import Repository

app = Flask(__name__)
cfg = {}

def main():

    if (sys.version_info < (2,6)):
        sys.exit("This program requires python version 2.6 or later")
    
    # Options and arguments
    p = optparse.OptionParser(description='OAI-PMH simulator',
                              usage='usage: %prog [options]   (-h for help)',
                              version='%prog '+__version__ )

    p.add_option('--port', '-p', action='store', type='int', default=5555,
                 help='port to run on (default %default)')
    p.add_option('--path', action='store', default='oai',
                 help='path to run at (default %default)')
    p.add_option('--repo-json', '-r', action='store', default='data/repo1.json',
                 help='JSON file describing repository (default %default)')
    p.add_option('--no-post', action='store_true',
                 help="do not support POST requests (part of OAI-PMH v2)")
    p.add_option('--debug', '-d', action='store_true',
                 help="set debugging mode")

    (options, args) = p.parse_args()
    if (len(args)>0):
        p.print_help()
        return

    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%dT%H:%M:%S', level=logging.INFO)

    app.config['no_post'] = options.no_post
    app.config['base_url'] = 'http://127.0.0.1:5555/oai'

    app.config['repo_json'] = options.repo_json
    with open(app.config['repo_json'], 'r') as fh:
        cfg = json.load(fh)
        app.config['repo'] = Repository( cfg=cfg )

    # to make externally visible set host='0.0.0.0'
    app.run(port=options.port, debug=options.debug)

def base_tree(verb, base_url):
    root = Element('OAI-PMH', 
                   {'xmlns': 'http://www.openarchives.org/OAI/2.0/',
                    'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                    'xsi:schemaLocation': 'http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd'
                    } )
    root.append(Element('responseDate',text='2002-02-08T12:00:01Z')) #FIXME
    root.append(Element('request', {'verb': verb}, text=base_url ))
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
    # have tree, now serialize
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
    """Make Flash Response for XML tree."""
    response = make_response( serialize_tree(root) )
    response.headers['Content-type'] = 'application/xml'
    return( response )

def TextSubElement( parent, tag, text=None ):
    """Add element named tag with content text iff text not None."""
    #FIXME - make handle multiple elements if text is iterable
    if (text is not None):
       SubElement( parent, tag).text = text

def identify(repo):
    """Make a Identify response

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

@app.route("/")
def index():
    return render_template('index.html',
                           base_url=app.config['base_url'])

@app.route("/give404")
def give404():
    alert(404)

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
    repo = app.config['repo']
    if (verb == 'Identify'):
        return identify(repo)
    elif (verb == 'GetRecord'):
        return get_record(repo, identifier, metadataPrefix)
    elif (verb == 'ListIdentifiers'):
        return list_identifiers(repo)
    elif (verb == 'ListRecords'):
        return list_records(repo)
    return render_template("bad_request.xml",
                           verb=verb,
                           code='BadRequest',
                           message='oops')

if __name__ == "__main__":
    main()
