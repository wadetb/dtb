"""DumpToBlender tests"""
import sys
import unittest
import unittest.mock

sys.modules['bpy'] = unittest.mock.Mock()
import dtb

class TestParser(unittest.TestCase):
    def test_ident(self):
        self.assertEqual(dtb.Parser('abc').expect_ident(), 'abc')
        self.assertEqual(dtb.Parser('abc#comment').expect_ident(), 'abc')
        self.assertEqual(dtb.Parser('xyz_abc').expect_ident(), 'xyz_abc')
        self.assertEqual(dtb.Parser('a 2').expect_ident(), 'a')
        self.assertEqual(dtb.Parser('a2').expect_ident(), 'a2')
        with self.assertRaises(dtb.ParserError):
            dtb.Parser('$ident').expect_ident()

    def test_string(self):
        self.assertEqual(dtb.Parser('\'abc\'').expect_string(), 'abc')
        self.assertEqual(dtb.Parser('\'abc\'#comment').expect_string(), 'abc')
        self.assertEqual(dtb.Parser('\'\'').expect_string(), '')
        with self.assertRaises(dtb.ParserError):
            dtb.Parser('"abc\'').expect_string()
        with self.assertRaises(dtb.ParserError):
            dtb.Parser('').expect_string()

    def test_float(self):
        self.assertEqual(dtb.Parser('1').expect_float(), 1.0)
        self.assertEqual(dtb.Parser('1#comment').expect_float(), 1.0)
        self.assertEqual(dtb.Parser('-1').expect_float(), -1.0)
        self.assertEqual(dtb.Parser('+1').expect_float(), 1.0)
        self.assertEqual(dtb.Parser('123.456').expect_float(), 123.456)
        self.assertEqual(dtb.Parser('.001').expect_float(), 0.001)
        self.assertEqual(dtb.Parser('-.001').expect_float(), -0.001)
        self.assertEqual(dtb.Parser('+.001').expect_float(), 0.001)
        self.assertEqual(dtb.Parser('1.0e6').expect_float(), 1000000)
        self.assertEqual(dtb.Parser('1.0e-6').expect_float(), 0.000001)
        self.assertEqual(dtb.Parser('1.0E+6').expect_float(), 1000000)
        self.assertEqual(dtb.Parser('1234 5678').expect_float(), 1234)
        self.assertEqual(dtb.Parser('123..456').expect_float(), 123)
        with self.assertRaises(dtb.ParserError):
            dtb.Parser('++1234').expect_float()
        with self.assertRaises(dtb.ParserError):
            dtb.Parser('-').expect_float()
        with self.assertRaises(dtb.ParserError):
            dtb.Parser('a1').expect_float()
        with self.assertRaises(dtb.ParserError):
            dtb.Parser('').expect_float()

    def test_vector(self):
        self.assertEqual(dtb.Parser('1').expect_vector(1), (1.0, ))
        self.assertEqual(dtb.Parser('1#comment').expect_vector(1), (1.0, ))
        self.assertEqual(dtb.Parser('0 1').expect_vector(2), (0.0, 1.0))
        self.assertEqual(dtb.Parser('0 0 1').expect_vector(3), (0.0, 0.0, 1.0))
        self.assertEqual(
            dtb.Parser('(0 0 1)').expect_vector(3), (0.0, 0.0, 1.0))
        self.assertEqual(
            dtb.Parser('(0 0 1)#comment').expect_vector(3), (0.0, 0.0, 1.0))
        with self.assertRaises(dtb.ParserError):
            dtb.Parser('(0 0 1').expect_vector(3)
        with self.assertRaises(dtb.ParserError):
            dtb.Parser('0 x y').expect_vector(3)
        with self.assertRaises(dtb.ParserError):
            dtb.Parser('0 1').expect_vector(3)

    def test_enum(self):
        self.assertEqual(dtb.Parser('foo').expect_enum(['foo']), 'foo')
        with self.assertRaises(dtb.ParserError):
            dtb.Parser('bar').expect_enum(['foo'])

    def test_line_col(self):
        parser = dtb.Parser('xyz')
        self.assertEqual(parser.line, 1)
        self.assertEqual(parser.col, 1)
        parser = dtb.Parser('xyz')
        parser.expect_ident()
        self.assertEqual(parser.line, 1)
        self.assertEqual(parser.col, 4)
        parser = dtb.Parser('xyz\nabcdef')
        parser.expect_ident()
        parser.expect_ident()
        self.assertEqual(parser.line, 2)
        self.assertEqual(parser.col, 7)
        parser = dtb.Parser('\n\n\n#comment\nabc')
        parser.expect_ident()
        self.assertEqual(parser.line, 5)
        self.assertEqual(parser.col, 4)


class TestDumpToBlender(unittest.TestCase):
    def test_basic(self):
        dtb.loads("point 1.0 5.3 3.1")
        dtb.loads("# comment")

    def test_context(self):
        with self.assertRaises(dtb.ParserError):
            dtb.loads("}")
        with self.assertRaises(dtb.ParserError):
            dtb.loads("{}}")
        with self.assertRaises(dtb.ParserError):
            dtb.loads("{")
        with self.assertRaises(dtb.ParserError):
            dtb.loads("{{}")
        dtb.loads("{}")
        dtb.loads("{{}}")
        dtb.loads("{{{}}}")

    def test_clip_planes(self):
        dtb.loads('''
            plane_size 100
            { label 'testcube'
            clip_plane (-1 0 0)  10
            clip_plane ( 1 0 0)  10
            clip_plane (0 -1 0)  10
            clip_plane (0  1 0)  10
            clip_plane (0 0 -1)  10
            clip_plane (0 0  1)  10
            plane (-1 0 0) 10
            plane ( 1 0 0) 10
            plane (0 -1 0) 10
            plane (0  1 0) 10
            plane (0 0 -1) 10
            plane (0 0  1) 10
            }
            ''')

    def test_parent_translation(self):
        dtb.loads('''
            { label 'cube1' 
              point (10 0 0)
              { label 'cube2' 
                point (10 0 0)
                { label 'cube3' 
                  point (10 0 0)
                }
              }
            }
            ''')

    def test_misc(self):
        dtb.loads('''
            label 'scene'
            { label 'right' plane (0.867572546 -0.292311847 0.402332813) -75.9123993 }
            { label 'left' plane (-0.867572546 -0.292311966 0.402332753) 144.576431 }
            { label 'top' plane (0 0.577145100 0.816641569) -116.847626 }
            { label 'bottom' plane (0 -0.955019951 -0.296541661) 161.229019 }
            { label 'back' plane (0.000000000 0.584618986 -0.811308026) -118.460983 }
            { label 'front' plane (-0.000000000 -0.587785304 0.809016943) 68.9353638 }
            { label 'corners'
            point (-127.129562 -159.335098 -30.5549698)
            point (-127.129555 -159.280167 -30.5150490)
            point (-127.014938 -159.335098 -30.5549622)
            point (-127.014931 -159.280167 -30.5150452)
            point (-98.4489670 -175.003845 19.9066238)
            point (-98.3729172 -202.544495 0.0611495972)
            point (-155.695526 -175.003845 19.9066315)
            point (-155.771622 -202.544495 0.0611572266)
            }
            { label 'center' point (-127.072250 -174.040894 -10.2755585) }
            ''')


if __name__ == '__main__':
    unittest.main()
