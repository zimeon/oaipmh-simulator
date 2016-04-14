#!/usr/bin/env python
"""OAI-PMH Simulator oaipmh-simulator.

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

import json
import logging
import optparse
import sys

from oaipmh_simulator._version import __version__
from oaipmh_simulator.flask_app import get_flask_app
from oaipmh_simulator.repository import Repository, OAI_PMH_Exception, BadArgument, sanitize

def main():
    """Command line simulator setup."""
    if (sys.version_info < (2,7)):
        sys.exit("This program requires python version 2.7 or later")
    
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

    app = get_flask_app()
    app.config['no_post'] = options.no_post
    app.config['base_url'] = 'http://127.0.0.1:5555/oai'

    with open(options.repo_json, 'r') as fh:
        app.config['repo'] = Repository( cfg=json.load(fh) )

    # to make externally visible set host='0.0.0.0'
    app.run(port=options.port, debug=options.debug)

if __name__ == "__main__":
    main()
