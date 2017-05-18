"""DumpToBlender tests"""
import sys
import unittest
import unittest.mock

sys.modules['bpy'] = unittest.mock.Mock()
sys.modules['mathutils'] = unittest.mock.Mock()
import dtb

TEST = '''
# comment
{
    origin 45 35 1
    color blue # property change persists until overridden or the end of the object
    point 1.0 5.3 3.1
    line (10 11 12) (13 14 15)
    { name 'normal'; color red; vector (10 10 10) (0 1 0) }
    face (0 0 0) (1 0 0) (1 1 0) (0 0 1)

    vertex 2 0.5 0.5 0.5
    vnormal 2 1 0 0 
    vcolor 2 1 1 1 1
    vface 2 3 4
    { label='irregular 45'; vedge 2 3 }
}

<script>
def intersectPlanes(scene):
    
'''


class TestParser(unittest.TestCase):
    def test_ident(self):
        self.assertEqual(dtb.Parser('abc').expect_ident(), 'abc')
        self.assertEqual(dtb.Parser('abc#comment').expect_ident(), 'abc')
        self.assertEqual(dtb.Parser('xyz_abc').expect_ident(), 'xyz_abc')
        self.assertEqual(dtb.Parser('a 2').expect_ident(), 'a')
        self.assertEqual(dtb.Parser('a2').expect_ident(), 'a2')
        with self.assertRaises(SyntaxError):
            dtb.Parser('$ident').expect_ident()

    def test_string(self):
        self.assertEqual(dtb.Parser('\'abc\'').expect_string(), 'abc')
        self.assertEqual(dtb.Parser('\'abc\'#comment').expect_string(), 'abc')
        self.assertEqual(dtb.Parser('\'\'').expect_string(), '')
        with self.assertRaises(SyntaxError):
            dtb.Parser('"abc\'').expect_string()
        with self.assertRaises(SyntaxError):
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
        with self.assertRaises(SyntaxError):
            dtb.Parser('++1234').expect_float()
        with self.assertRaises(SyntaxError):
            dtb.Parser('-').expect_float()
        with self.assertRaises(SyntaxError):
            dtb.Parser('a1').expect_float()
        with self.assertRaises(SyntaxError):
            dtb.Parser('').expect_float()

    def test_vector(self):
        self.assertEqual(dtb.Parser('1').expect_vector(1), (1.0,))
        self.assertEqual(dtb.Parser('1#comment').expect_vector(1), (1.0,))
        self.assertEqual(dtb.Parser('0 1').expect_vector(2), (0.0, 1.0))
        self.assertEqual(dtb.Parser('0 0 1').expect_vector(3), (0.0, 0.0, 1.0))
        self.assertEqual(dtb.Parser('(0 0 1)').expect_vector(3), (0.0, 0.0, 1.0))
        self.assertEqual(dtb.Parser('(0 0 1)#comment').expect_vector(3), (0.0, 0.0, 1.0))
        with self.assertRaises(SyntaxError):
            dtb.Parser('(0 0 1').expect_vector(3)
        with self.assertRaises(SyntaxError):
            dtb.Parser('0 x y').expect_vector(3)
        with self.assertRaises(SyntaxError):
            dtb.Parser('0 1').expect_vector(3)


class TestDumpToBlender(unittest.TestCase):
    def test_basic(self):
        dtb.parse("point 1.0 5.3 3.1")
        dtb.parse("# comment")


if __name__ == '__main__':
    unittest.main()
