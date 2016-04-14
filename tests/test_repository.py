import unittest
from oaipmh_simulator.repository import Repository

class TestUtill(unittest.TestCase):

    def test01_init(self):
        r = Repository()

if __name__ == '__main__':
    unittest.main()
