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
'''
# attrs:
# style <str> - per object, per face, per edge, per vertex, ???)
# label <str> - for UI display
#
# modifiers:
# translate <vec3> - adds to positions
#
# prims:
# point <pos>
# line <from> <to>
# vector <origin> <vec>
# axis <origin> <x> <y> <z>
# aabb <origin> <w> <h> <d>
# obb <origin> <x> <y> <z>
# sphere <origin> <radius>
# tri <p0> <p1> <p2>
# quad <p0> <p1> <p2> <p3>
# poly <n> <p0...>
#
# context:
# { - copy and create new context
# } - pop context
#
# future attrs:
# id <ident> - for reference by script or backref
# script <source> - for processing of the dom?
 
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
        dtb.loads("point 1.0 5.3 3.1")
        dtb.loads("# comment")


if __name__ == '__main__':
    unittest.main()

#def createMeshFromData(name, origin, verts, faces):
#    # Create mesh and object
#    me = bpy.data.meshes.new(name + 'Mesh')
#    ob = bpy.data.objects.new(name, me)
#    ob.location = origin
#    ob.show_name = True
#
#    # Link object to scene and make active
#    scn = bpy.context.scene
#    scn.objects.link(ob)
#    scn.objects.active = ob
#    ob.select = True
#
#    # Create mesh from given verts, faces.
#    me.from_pydata(verts, [], faces)
#    # Update mesh with new data
#    me.update()
#    return ob
#
#
#def run(origo):
#    origin = Vector(origo)
#    (x, y, z) = (0.707107, 0.258819, 0.965926)
#    verts = ((x, x, -1), (x, -x, -1), (-x, -x, -1), (-x, x, -1), (0, 0, 1))
#    faces = ((1, 0, 4), (4, 2, 1), (4, 3, 2), (4, 0, 3), (0, 1, 2, 3))
#
#    cone1 = createMeshFromData('DataCone', origin, verts, faces)
#
#
#if __name__ == "__main__":
#    run((0, 0, 0))
#
