"""Test code to Flask app implementing OAI-PMH simulator.

See http://flask.pocoo.org/docs/0.10/testing/#testing for testing intro.
"""
import unittest

from oaipmh_simulator.flask_app import get_flask_app


class TestFlaskApp(unittest.TestCase):

    def setUp(self):
        app = get_flask_app()
        app.config['TESTING'] = True
        app.config['no_post'] = False
        app.config['base_url'] = 'http://example.org/oai'
        self.app = app.test_client()

    def test01_homepage(self):
        rv = self.app.get('/')
        assert b'<a href="http://example.org/oai">' in rv.data

if __name__ == '__main__':
    unittest.main()
