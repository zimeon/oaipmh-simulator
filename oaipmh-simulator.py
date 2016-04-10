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

import optparse
import os.path
import sys
from xml.etree.ElementTree import ElementTree, Element, SubElement
try: #python2, must try this first as a different io exists in python2
    import StringIO as io
except ImportError: #python3
    import io

from oaipmh_simulator._version import __version__

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
    p.add_option('--datadir', action='store', default='data',
                 help='directory in which to look for data (default %default)')
    p.add_option('--no-post', action='store_true',
                 help="do not support POST requests (part of OAI-PMH v2)")
    p.add_option('--debug', '-d', action='store_true',
                 help="set debugging mode")

    (options, args) = p.parse_args()
    if (len(args)>0):
        p.print_help()
        return

    app.config['datadir'] = options.datadir
    app.config['no_post'] = options.no_post
    app.config['base_url'] = 'http://127.0.0.1:5555/oai'

    app.config['repository_name'] = 'repo-name'
    app.config['protocol_version'] = '2.0'
    app.config['admin_email'] = [ 'someone@example.com' ]
    app.config['earliest_datestamp'] = '1999-01-01'
    app.config['deleted_record'] = 'no'
    app.config['granularity'] = 'YYYY-MM-DD'
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


def identify():
    identify_response = os.path.join(app.config['datadir'],'Identify.xml')
    if (os.path.exists(identify_response)):
        logging.info("Override for Identify")
        alert(555)
    else:
        # Make a simple response
        root = base_tree(verb='Identify', base_url=app.config['base_url'])
        resp = SubElement( root, 'Identify' )
        SubElement( resp, 'repositoryName').text=app.config['repository_name']
        SubElement( resp, 'baseURL').text=app.config['base_url']
        SubElement( resp, 'protocolVersion').text=app.config['protocol_version']
        for ae in app.config['admin_email']:
            SubElement( resp, 'adminEmail' ).text=ae
        SubElement( resp, 'earliestDatestamp').text=app.config['earliest_datestamp']
        SubElement( resp, 'deletedRecord').text=app.config['deleted_record']
        SubElement( resp, 'granularity').text=app.config['granularity']
        response = make_response( serialize_tree(root) )
        response.headers['Content-type'] = 'application/xml'
        return(response)

@app.route("/")
def index():
    return render_template("index.html",
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
    # What to do?
    if (verb == 'Identify'):
        return identify()
    return render_template("bad_request.xml",
                           verb=verb,
                           code='BadRequest',
                           message='oops')

if __name__ == "__main__":
    main()
