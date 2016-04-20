import unittest
import datetime
from oaipmh_simulator.repository import Repository, Item, Record, Datestamp, OAI_PMH_Exception, BadArgument, BadVerb, BadResumptionToken, IdDoesNotExist, NoMetadataFormats, CannotDisseminateFormat, NoRecordsMatch, NoSetHierarchy

# Some test data
CFG1 = {
          "repositoryName": "myname",
          "protocolVersion": "2.0",
          "adminEmail": [ "someone@example.com", "another@example.com" ],
          "earliestDatestamp": "1999-01-01",
          "deletedRecord": "yes",
          "granularity": "YYYY-MM-DD",
          "records": [
              { "identifier": "item1",
                "datestamp": "2001-01-01",
                "metadataPrefix": "oai_dc",
                "metadata": "<md>item1_oai_dc</md>",
                "sets": [ "a" ]
              },
              { "identifier": "item1",
                "datestamp": "2001-01-02",
                "metadataPrefix": "xxx",
                "metadata": "<md>item1_xxx</md>"
              },
              { "identifier": "item2",
                "datestamp": "2002-02-02",
                "metadataPrefix": "oai_dc",
                "metadata": "<md>item2_oai_dc</md>",
                "sets": [ "a:b:c" ]
              },
              { "identifier": "item3",
                "datestamp": "2003-03-03",
                "metadataPrefix": "oai_dc",
                "status": "deleted",
                "sets": [ "d" ]
              }
          ]
       }

class TestRepository(unittest.TestCase):

    def test01_repository_init(self):
        r = Repository()
        self.assertEqual( r.cfg, None )
        r = Repository( cfg=CFG1 )
        self.assertEqual( r.repository_name, 'myname' )
        self.assertEqual( r.protocol_version, '2.0' )

    def test01_add_select_item(self):
        r = Repository()
        i1 = Item('item1')
        i2 = Item('item2')
        self.assertEqual( len(r.items), 0 )
        r.add_item(i1)
        self.assertEqual( len(r.items), 1 )
        r.add_item(i1)
        self.assertEqual( len(r.items), 1 )
        r.add_item(i2)
        self.assertEqual( len(r.items), 2 )
        i = r.select_item( 'item1' )
        self.assertEqual( i.identifier, 'item1' )
        self.assertRaises( IdDoesNotExist, r.select_item, None )
        self.assertRaises( IdDoesNotExist, r.select_item, 'item3' )

    def test02_select_record(self):
        repo = Repository( cfg=CFG1 )
        r = repo.select_record( 'item1', 'oai_dc' )
        self.assertEqual( r.metadataPrefix, 'oai_dc' )
        self.assertRaises( IdDoesNotExist, repo.select_record )
        self.assertRaises( IdDoesNotExist, repo.select_record, 'x' )
        self.assertRaises( CannotDisseminateFormat, repo.select_record, 'item1' )
        self.assertRaises( CannotDisseminateFormat, repo.select_record, 'item1', 'y' )

    def test03_select_records(self):
        repo = Repository( cfg=CFG1 )
        r = repo.select_records( metadataPrefix='oai_dc' )
        self.assertEqual( len(r), 3 )
        r = repo.select_records( metadataPrefix='oai_dc', set='a' )
        self.assertEqual( len(r), 2 )
        # NOTE - hacks to use "from" as arg name
        # mismatching granularities
        self.assertRaises( BadArgument, repo.select_records, **{"from": "2000-01-01", "until": "2001-01-01T00:00:00Z"} )
        # negative timespan
        self.assertRaises( NoRecordsMatch, repo.select_records, **{"from": "2000-01-01", "until": "1999-01-01"} )
        # to early
        self.assertRaises( NoRecordsMatch, repo.select_records, until="1900-01-01" )

    def test04_metadata_formats(self):
        repo = Repository()
        mf = repo.metadata_formats()
        self.assertEqual( mf, [] )
        repo = Repository( cfg=CFG1 )
        mf = repo.metadata_formats()
        self.assertEqual( mf, ['oai_dc','xxx'] )

    def test05_set_specs(self):
        repo = Repository()
        self.assertRaises( NoSetHierarchy, repo.set_specs )
        repo = Repository( cfg=CFG1 )
        ss = repo.set_specs()
        self.assertEqual( ss, ['a','a:b','a:b:c','d'] )

    def test10_item_init(self):
        i = Item('item1')

    def test20_record_init(self):
        r = Record('item1')

    def test30_datestamp_init(self):
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
        self.assertRaises( BadArgument, Datestamp, '2000-01-01T00:00:00' )
        self.assertRaises( BadArgument, Datestamp, '2000-01-01T25:00:00Z' )
        self.assertRaises( BadArgument, Datestamp, '2000-01-01T24:00:00Z' )
        self.assertRaises( BadArgument, Datestamp, '2000-01-01T00:60:00Z' )
        self.assertRaises( BadArgument, Datestamp, '2000-01-01T00:00:60Z' )
        self.assertRaises( BadArgument, Datestamp, '2000-01-01T00:00:00.1Z' )
        # Wrong granularity
        self.assertRaises( BadArgument, Datestamp, '2000-01-01', 'seconds' )
        self.assertRaises( BadArgument, Datestamp, '2000-01-01T00:00:00Z', 'days' )

    def test31_datestamp_comparison(self):
        # Comparison -- all comparison operators look just
        # at the parsed datetime values
        d1 = Datestamp('1969-01-01')
        d2 = Datestamp('1970-01-06T00:00:01Z')
        self.assertTrue( d1 < d2 )
        self.assertTrue( d1.datetime <= d2.datetime )
        self.assertFalse( d2 < d1 )
        self.assertFalse( d2 <= d1 )
        self.assertTrue( d2 > d1 )
        self.assertTrue( d2 >= d1 )
        self.assertFalse( d1 > d2 )
        self.assertFalse( d1 >= d2 )
        # equal things are <= and >=
        self.assertTrue( d1 <= d1 )
        self.assertTrue( d1 >= d1 )
        # bad..
        not_init = Datestamp()
        self.assertRaises( TypeError, d1.__ge__, not_init )
        self.assertRaises( TypeError, not_init.__ge__, d1 )
        self.assertRaises( TypeError, d1.__gt__, not_init )
        self.assertRaises( TypeError, not_init.__gt__, d1 )
        self.assertRaises( TypeError, d1.__le__, not_init )
        self.assertRaises( TypeError, not_init.__le__, d1 )
        self.assertRaises( TypeError, d1.__lt__, not_init )
        self.assertRaises( TypeError, not_init.__lt__, d1 )

    def test40_exceptions(self):
        e = OAI_PMH_Exception()
        e.msg = 'abcdef'
        self.assertEqual( str(e), 'abcdef' )
        e = BadArgument('buffalo')
        self.assertEqual( e.code, 'badArgument' )
        self.assertTrue( 'buffalo' in str(e) )
        e = BadVerb()
        self.assertEqual( e.code, 'badVerb' )
        e = BadVerb('shrew')
        self.assertEqual( e.code, 'badVerb' )
        e = BadVerb(verb='<alert>')
        self.assertEqual( e.code, 'badVerb' )
        self.assertTrue( '(%3Calert%3E)' in str(e) )
        e = BadResumptionToken('')
        e = CannotDisseminateFormat('')
        e = IdDoesNotExist('')
        e = NoRecordsMatch('')
        e = NoMetadataFormats()
        e = NoSetHierarchy()

if __name__ == '__main__':
    unittest.main()
