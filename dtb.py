import bpy
from mathutils import Vector
import re
import typing


class Parser:
    """A simple Recursive Descent Parser which supports the basic elements of the
    DumpToBlender data description syntax."""

    WHITESPACE_OR_COMMENT = re.compile(r'(\s+)|(#.*$)', re.MULTILINE)
    LPAREN = re.compile(r'\(')
    RPAREN = re.compile(r'\)')
    STRING = re.compile(r'(\'(?P<value>[^\']*)\')')
    FLOAT = re.compile(
        r'(?P<value>[+-]?\ *(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)')
    IDENT = re.compile(r'(?P<value>\w+)')

    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.col = 0

    def at_end(self) -> bool:
        """Returns True if the cursor has reached the end of the source."""
        return self.pos >= len(self.source)

    def cursor(self) -> memoryview:
        """Returns the text at the current parsing cursor, e.g. the remaining source."""
        return self.source[self.pos:]

    def advance(self, num: int) -> None:
        """Advances the parsing cursor by the given number of characters."""
        text = self.source[self.pos:self.pos + num]
        self.line += text.count('\n')
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
            return match.group('value')
        return match.group(0)

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


class BlenderCreator:
    def __init__(self):
        pass

    def create(self, context):
        mesh = bpy.data.meshes.new(context.label + ' mesh')

        obj = bpy.data.objects.new(context.label, mesh)
        obj.location = Vector((0, 0, 0))
        obj.show_name = True

        scene = bpy.context.scene
        scene.objects.link(obj)
        scene.objects.active = obj
        obj.select = True

        self.verts = []
        self.edges = []
        self.faces = []

        for primitive in context.primitives:
            primitive.create(self)

        mesh.from_pydata(self.verts, self.edges, self.faces)
        mesh.update()

        del self.verts
        del self.edges
        del self.faces

        for child in context.children:
            self.create(child)

    def add_point(self, position):
        self.verts.append(position)

    def add_line(self, from_position, to_position):
        index = len(self.verts)
        self.verts.append(from_position)
        self.verts.append(to_position)
        self.edges.append((index, index + 1))


class Context:
    def __init__(self):
        self.label = ''
        self.style = 'white'
        self.primitives = []
        self.parent = None
        self.children = []

    def new_child(self):
        new_context = Context()
        new_context.style = self.style
        new_context.parent = self
        self.children.append(new_context)
        return new_context

    def add_primitive(self, primitive):
        self.primitives.append(primitive)


class PointPrimitive:
    def __init__(self, context, position):
        self.context = context
        self.position = position

    def create(self, creator):
        creator.add_point(self.position)


class LinePrimitive:
    def __init__(self, context, from_position, to_position):
        self.context = context
        self.from_position = from_position
        self.to_position = to_position

    def create(self, creator):
        creator.add_line(self.from_position, self.to_position)


def _load_label(parser: Parser, context: Context) -> None:
    context.label = parser.expect_string()


def _load_style(parser: Parser, context: Context) -> None:
    context.style = parser.expect_string()


def _load_point(parser: Parser, context: Context) -> None:
    position = parser.expect_vector(3)
    context.add_primitive(PointPrimitive(context, position))


def _load_line(parser: Parser, context: Context) -> None:
    from_position = parser.expect_vector(3)
    to_position = parser.expect_vector(3)
    context.add_primitive(LinePrimitive(context, from_position, to_position))


def loads(source: str) -> Context:
    parser = Parser(source)

    stack = []
    context = Context()

    parser.skip_whitespace_and_comments()

    while not parser.at_end():
        prim = parser.expect_ident()

        if prim == '{':
            stack.append(context)
            context = context.new_child()

        elif prim == '}':
            if not stack:
                raise SyntaxError('unbalanced }')
            context = stack.pop()

        else:
            try:
                func = globals()["_load_{}".format(prim)]
            except AttributeError:
                raise SyntaxError('unknown primitive {}'.format(prim))
            func(parser, context)

    if stack:
        raise SyntaxError('unbalanced {')

    return context


def load(filename: str) -> None:
    with open(filename, 'r') as source_file:
        source = source_file.read()
    return loads(source)


def create(context) -> None:
    creator = BlenderCreator()
    creator.create(context)

create(loads('''
label 'test'
line (0 0 0) (0 1 0)
line (0 0 0) (1 0 0)
line (0 0 0) (0 0 1)
'''))
