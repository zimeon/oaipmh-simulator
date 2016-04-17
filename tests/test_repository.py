import unittest
import datetime
from oaipmh_simulator.repository import Repository, Item, Record, Datestamp, BadArgument

class TestRepository(unittest.TestCase):

    def test01_repository_init(self):
        r = Repository()

    def test10_item_init(self):
        i = Item('item1')

    def test20_record_init(self):
        r = Record('item1')

    def test30_datestamp(self):
        d = Datestamp()
        assert d.datetime is None
        d1 = Datestamp('1969-01-01')
        assert d1.granularity == 'days'
        d2 = Datestamp('1969-01-01T00:00:00Z')
        assert d2.granularity == 'seconds'
        assert d1.datetime == d2.datetime
        # Many bad cases...
        self.assertRaises( BadArgument, Datestamp, '' )
        self.assertRaises( BadArgument, Datestamp, '2001' )
        self.assertRaises( BadArgument, Datestamp, '2000-13-01' )
        self.assertRaises( BadArgument, Datestamp, '2000-01-32' )
        self.assertRaises( BadArgument, Datestamp, '2000-01-01', 'seconds' )
        self.assertRaises( BadArgument, Datestamp, '2000-01-01T00:00:00Z', 'days' )
 
if __name__ == '__main__':
    unittest.main()
