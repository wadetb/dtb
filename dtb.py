import bpy
import mathutils
from mathutils import Vector
import re
import typing

class Parser:
    """A simple Recursive Descent Parser which supports the basic elements of the
    DumpToBlender data description syntax."""

    WHITESPACE_OR_COMMENT = re.compile(rb'(\s+)|(#.*$)', re.MULTILINE)
    LPAREN = re.compile(rb'\(')
    RPAREN = re.compile(rb'\)')
    STRING = re.compile(rb'(\'(?P<value>[^\']*)\')')
    FLOAT = re.compile(rb'(?P<value>[+-]?\ *(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)')
    IDENT = re.compile(rb'(?P<value>\w+)')

    def __init__(self, source: str):
        self.source = memoryview(source.encode('ascii'))
        self.pos = 0

    def at_end(self) -> bool:
        """Returns True if the cursor has reached the end of the source."""
        return self.pos >= len(self.source)

    def cursor(self) -> memoryview:
        """Returns the text at the current parsing cursor, e.g. the remaining source."""
        return self.source[self.pos:]

    def advance(self, num: int) -> None:
        """Advances the parsing cursor by the given number of characters."""
        self.pos += num

    def skip_whitespace_and_comments(self) -> None:
        """Skips all whitespace and comments at the cursor."""
        while True:
            ws_match = Parser.WHITESPACE_OR_COMMENT.match(self.cursor())
            if not ws_match:
                break
            self.advance(ws_match.end())

    def accept(self, pattern) -> typing.Optional[str]:
        """Matches and returns the value at the cursor, using the given regex.
        The return value is the regex's named group 'value' if present, otherwise
        it's the entire match, or None if there is no match."""
        match = re.match(pattern, self.cursor())
        if not match:
            return None

        self.advance(match.end())
        self.skip_whitespace_and_comments()

        if 'value' in match.groupdict():
            return match.group('value').decode('ascii')
        else:
            return match.group(0).decode('ascii')

    def expect(self, pattern, description=None) -> str:
        """Matches and returns the value at the cursor, using the given regex which
        extracts a named group 'value'."""
        result = self.accept(pattern)
        if result is None:
            raise SyntaxError('expected {}'.format(description))
        return result

    def expect_ident(self) -> str:
        """Parses and returns the identifier at the cursor."""
        return self.expect(Parser.IDENT, 'an identifier')

    def expect_string(self) -> str:
        """Parses and returns the single-quoted string at the cursor."""
        return self.expect(Parser.STRING, 'a string')

    def expect_float(self) -> float:
        """Parses and returns the float at the cursor."""
        return float(self.expect(Parser.FLOAT, 'a floating point number'))

    def expect_vector(self, dim=3) -> tuple:
        """Parses and returns the N-dimensional vector at the cursor."""
        paren = self.accept(Parser.LPAREN)
        vector = tuple([self.expect_float() for _ in range(dim)])
        if paren is not None:
            self.expect(Parser.RPAREN, ')')
        return vector

def _point_primitive(p: Parser):
    origin = p.expect_vector(3)


_PRIMITIVE_HANDLERS = {
    'point': _point_primitive
}

class Context:
    def __init__(self):
        pass

class DumpToBlender:
    def __init__(self):
        self.root = None

    def loads(self, source: str):
        p = Parser(source)

        self.root = Context()

        p.skip_whitespace_and_comments()
        while not p.at_end():
            prim = p.expect_ident()

            if prim == '{':

            handler = _PRIMITIVE_HANDLERS.get(prim)
            if not handler:
                raise SyntaxError('unknown primitive {}'.format(prim))

            handler(p)

    def load(self, filename: str):
        with open(filename, 'r') as source_file:
            source = source_file.read()
        self.loads(source)

    def create(self):
        pass

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