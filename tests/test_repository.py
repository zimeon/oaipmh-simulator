import unittest
from oaipmh_simulator.repository import Repository, Item, Record

class TestRepository(unittest.TestCase):

    def test01_repository_init(self):
        r = Repository()

    def test10_item_init(self):
        i = Item('item1')

    def test20_record_init(self):
        r = Record('item1')

if __name__ == '__main__':
    unittest.main()
