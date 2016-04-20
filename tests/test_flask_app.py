"""Test code to Flask app implementing OAI-PMH simulator.

See http://flask.pocoo.org/docs/0.10/testing/#testing for testing intro.
"""
import unittest
from xml.etree.ElementTree import Element, dump
try:
    import unittest.mock as mock
except:
    import mock

from oaipmh_simulator.flask_app import get_flask_app, index_handler, oaipmh_baseurl_handler, OAI_PMH_Handler 

class TestFlaskApp(unittest.TestCase):

    def setUp(self):
        app = get_flask_app()
        app.add_url_rule('/', view_func=index_handler)
        app.add_url_rule('/oai' , view_func=oaipmh_baseurl_handler)
        app.config['TESTING'] = True
        app.config['no_post'] = False
        app.config['base_url'] = 'http://example.org/oai'
        self.app = app.test_client()

    def test01_base_tree(self):
        config = { 'base_url': 'http://example.org/abc',
                   'repo': None }
        app = mock.Mock( config=config )
        h = OAI_PMH_Handler( app )
        h.base_tree( 'VerbyVerb' )
        self.assertEqual( h.root.findtext('request'), 'http://example.org/abc' )
        self.assertEqual( h.root.find('request').attrib['verb'], 'VerbyVerb' )
        app.config['base_url'] = 'http://example.org/ab1'
        h.base_tree( None )
        self.assertEqual( h.root.findtext('request'), 'http://example.org/ab1' )
        self.assertFalse( 'verb' in h.root.find('request').attrib )

    def test02_add_header(self):
        h = OAI_PMH_Handler()
        h.root = Element('root')
        r1 = mock.Mock( identifier='item1', datestamp="1999-01-01",
                        set_specs=[], status=None )
        h.add_header( h.root, r1 )
        h1 = h.root.find('header')
        self.assertEqual( h1.findtext('identifier'), 'item1' )
        self.assertEqual( h1.findtext('setSpec'), None )
        self.assertEqual( h1.findtext('status'), None )
        # More complete
        h.root = Element('root')
        r2 = mock.Mock( identifier='item2', datestamp="1999-01-02",
                        set_specs=['a','b'], status='deleted' )
        h.add_header( h.root, r2 )
        h2 = h.root.find('header')
        self.assertEqual( h2.findtext('identifier'), 'item2' )
        self.assertEqual( h2.findtext('setSpec'), 'a' )
        self.assertEqual( h2.findtext('status'), 'deleted' )

    def test03_add_metadata(self):
        h = OAI_PMH_Handler()
        h.root = Element('root')
        r1 = mock.Mock( metadata="<x:y>something</x:y>" )
        h.add_metadata( h.root, r1 ) 
        m1 = h.root.find('metadata')
        self.assertEqual( m1.text, '#-#-#-#-#--SUB--1--#-#-#-#-#' )

    def test10_homepage(self):
        rv = self.app.get('/')
        assert b'<a href="http://example.org/oai">' in rv.data

if __name__ == '__main__':
    unittest.main()
