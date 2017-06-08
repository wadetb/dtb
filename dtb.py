import re
import typing
import bpy
from mathutils import Matrix, Vector

class ParserError(Exception):
    pass

class Parser:
    """A simple Recursive Descent Parser which supports the basic elements of the
    DumpToBlender data description syntax."""

    WHITESPACE_OR_COMMENT = re.compile(r'(\s+)|(#.*$)', re.MULTILINE)
    LPAREN = re.compile(r'\(')
    RPAREN = re.compile(r'\)')
    STRING = re.compile(r'(\'(?P<value>[^\']*)\')')
    FLOAT = re.compile(
        r'(?P<value>[+-]?\ *(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)')
    IDENT = re.compile(r'(?P<value>\w+|{|})')

    def __init__(self, source: str, filename=None):
        self.filename = filename or '<source>'
        self.source = source
        self.pos = 0
        self.line_pos = 0
        self.line = 1
        self.col = 1
        self.skip_whitespace_and_comments()

    def error(self, message):
        raise ParserError("{}:{},{}: {}".format(self.filename, self.line, self.col, message))

    def at_end(self) -> bool:
        """Returns True if the cursor has reached the end of the source."""
        return self.pos >= len(self.source)

    def cursor(self) -> memoryview:
        """Returns the text at the current parsing cursor, e.g. the remaining source."""
        return self.source[self.pos:]

    def advance(self, num: int) -> None:
        """Advances the parsing cursor by the given number of characters."""
        self.pos += num

        while True:
            line_pos = self.source.find('\n', self.line_pos, self.pos)
            if line_pos == -1:
                break
            self.line_pos = line_pos + 1
            self.line += 1
        self.col = self.pos - self.line_pos + 1

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
            self.error('expected {}'.format(description))
        return result

    def expect_ident(self) -> str:
        """Parses and returns the identifier at the cursor."""
        return self.expect(Parser.IDENT, 'an identifier')

    def expect_enum(self, options) -> str:
        """Parses and returns an enumeration at the cursor, given the list of options."""
        value = self.expect(Parser.IDENT, 'one of {}'.format(options))
        if not value in options:
            self.error('{} is not one of {}'.format(value, options))
        return value

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

    def create(self, context, parent=None):
        mesh = bpy.data.meshes.new(context.label + ' mesh')

        obj = bpy.data.objects.new(context.label, mesh)
        obj.parent = parent
        obj.show_name = True

        scene = bpy.context.scene
        scene.objects.link(obj)
        scene.objects.active = obj
        obj.select = True

        self.context = context
        self.verts = []
        self.edges = []
        self.faces = []

        for primitive in context.primitives:
            primitive.create(self)

        if self.verts:
            verts_min = Vector((
                min([Vector(v).x for v in self.verts]), \
                min([Vector(v).y for v in self.verts]), \
                min([Vector(v).z for v in self.verts])))
            verts_max = Vector((
                max([Vector(v).x for v in self.verts]), \
                max([Vector(v).y for v in self.verts]), \
                max([Vector(v).z for v in self.verts])))
            verts_center = (verts_min + verts_max) * 0.5

            parent_center = Vector((0, 0, 0))
            search_parent = parent
            while search_parent:
                parent_center += Vector(search_parent.location)
                search_parent = search_parent.parent

            if parent:
                obj.matrix_parent_inverse = Matrix()
                obj.location = verts_center - parent_center
            else:
                obj.location = verts_center

            self.verts = [(Vector(v) - verts_center) for v in self.verts]

        mesh.from_pydata(self.verts, self.edges, self.faces)
        mesh.update()

            # label_mesh = bpy.data.meshes.new(context.label + ' label mesh')
            # label_mesh.from_pydata([(0, 0, 0)], [], [])
            # label_mesh.update()
            # label_obj = bpy.data.objects.new(context.label + ' label', label_mesh)
            # label_obj.parent = obj
            # label_obj.show_name = True
            # label_obj.location = center.to_tuple()

        del self.verts
        del self.edges
        del self.faces

        for child in context.children:
            self.create(child, obj)

    def add_point(self, position):
        index = len(self.verts)
        position = Vector(position)
        point_size = float(self.context.style.get('point_size', 1.0))
        self.verts.extend([
            position + Vector((0, 0, -point_size)), \
            position + Vector((-point_size, -point_size, 0)), \
            position + Vector((point_size, -point_size, 0)), \
            position + Vector((point_size, point_size, 0)), \
            position + Vector((-point_size, point_size, 0)), \
            position + Vector((0, 0, point_size))
        ])
        self.faces.extend([
            (index, index + 1, index + 2), \
            (index, index + 2, index + 3), \
            (index, index + 3, index + 4), \
            (index, index + 4, index + 1), \
            (index +5, index + 1, index + 4), \
            (index + 5, index + 4, index + 3), \
            (index + 5, index + 3, index + 2),
            (index + 5, index + 2, index + 1)])

    def add_line(self, from_position, to_position):
        index = len(self.verts)
        self.verts.append(from_position)
        self.verts.append(to_position)
        self.edges.append((index, index + 1))

    def add_vector(self, position, direction):
        index = len(self.verts)
        self.verts.append(position)
        self.verts.append(Vector(position) + Vector(direction))
        self.edges.append((index, index + 1))

    def _clip_face(self, verts, clip_planes, clip_side='negative'):
        for clip in clip_planes:
            clip_normal = Vector(clip.normal)
            clip_distance = clip.distance

            if clip_side == 'positive':
                clip_normal = -clip_normal
                clip_distance = -clip_distance

            new_verts = []
            for cur_index, cur_vert in enumerate(verts):
                prev_index = (cur_index + len(verts) - 1) % len(verts)
                prev_vert = verts[prev_index]

                dist_cur = clip_normal.dot(cur_vert) + clip_distance
                dist_prev = clip_normal.dot(prev_vert) + clip_distance

                if dist_cur >= 0 and dist_prev >= 0:
                    new_verts.append(cur_vert)
                elif dist_cur >= 0 and dist_prev < 0:
                    lerp = -dist_prev / (dist_cur - dist_prev)
                    new_verts.append(prev_vert + lerp * (cur_vert - prev_vert))
                    new_verts.append(cur_vert)
                elif dist_cur < 0 and dist_prev >= 0:
                    lerp = -dist_prev / (dist_cur - dist_prev)
                    new_verts.append(prev_vert + lerp * (cur_vert - prev_vert))

            verts = new_verts

        return verts

    def add_plane(self, normal, distance):
        normal = Vector(normal)
        x_axis = normal.cross(Vector((0, 0, 1)))
        if x_axis.length < 0.001:
            x_axis = normal.cross(Vector((1, 0, 0)))
        x_axis = x_axis.normalized()
        y_axis = normal.cross(x_axis)

        plane_size = float(self.context.style.get('plane_size', 1000))
        x_axis = x_axis * plane_size
        y_axis = y_axis * plane_size

        origin = normal * -distance

        verts = [
            origin - x_axis - y_axis, origin + x_axis - y_axis,
            origin + x_axis + y_axis, origin - x_axis + y_axis
        ]

        clip_side = self.context.style.get('clip_side', 'negative')
        clip_planes = [
            p for p in self.context.clip_planes
            if Vector(p.normal).dot(normal) < 0.999 or
            abs(p.distance - distance) > 0.001
        ]
        verts = self._clip_face(verts, clip_planes, clip_side)

        if verts:
            index = len(self.verts)
            self.verts.extend(verts)
            self.faces.append(tuple([index + i for i in range(len(verts))]))

    def add_aabb(self, aabb_min, aabb_max):
        index = len(self.verts)
        aabb_min = Vector(aabb_min)
        aabb_max = Vector(aabb_max)
        self.verts.extend([
            (aabb_min.x, aabb_min.y, aabb_min.z), \
            (aabb_max.x, aabb_min.y, aabb_min.z), \
            (aabb_max.x, aabb_max.y, aabb_min.z), \
            (aabb_min.x, aabb_max.y, aabb_min.z), \
            (aabb_min.x, aabb_min.y, aabb_max.z), \
            (aabb_max.x, aabb_min.y, aabb_max.z), \
            (aabb_max.x, aabb_max.y, aabb_max.z), \
            (aabb_min.x, aabb_max.y, aabb_max.z) \
        ])
        self.edges.extend([
            (index + 0, index + 1), (index + 1, index + 2), \
            (index + 2, index + 3), (index + 3, index + 0), \
            (index + 4, index + 5), (index + 5, index + 6), \
            (index + 6, index + 7), (index + 7, index + 4), \
            (index + 0, index + 4), (index + 1, index + 5), \
            (index + 2, index + 6), (index + 3, index + 7) \
        ])

    def add_projection(self, matrix):
        col0 = Vector((matrix[0], matrix[4], matrix[8], matrix[12]))
        col1 = Vector((matrix[1], matrix[5], matrix[9], matrix[13]))
        col2 = Vector((matrix[2], matrix[6], matrix[10], matrix[14]))
        col3 = Vector((matrix[3], matrix[7], matrix[11], matrix[15]))

        planes = [
            col0 - col3, -col0 - col3, col1 - col3, -col1 - col3, col2 - col3,
            -col2 - col3
        ]


class Context:
    def __init__(self):
        self.label = ''
        self.style = {}
        self.primitives = []
        self.clip_planes = []
        self.parent = None
        self.children = []

    def new_child(self):
        new_context = Context()
        new_context.parent = self
        self.children.append(new_context)
        return new_context

    def add_primitive(self, primitive):
        self.primitives.append(primitive)

    def add_clip_plane(self, clip_plane):
        self.clip_planes.append(clip_plane)

    def propagate(self):
        for child in self.children:
            for key, value in self.style.items():
                if not key in child.style:
                    child.style[key] = value

            for clip_plane in self.clip_planes:
                child.clip_planes.append(clip_plane)

            child.propagate()


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


class VectorPrimitive:
    def __init__(self, context, position, direction):
        self.context = context
        self.position = position
        self.direction = direction

    def create(self, creator):
        creator.add_vector(self.position, self.direction)


class PlanePrimitive:
    def __init__(self, context, normal, distance):
        self.context = context
        self.normal = normal
        self.distance = distance

    def create(self, creator):
        creator.add_plane(self.normal, self.distance)


class AABBPrimitive:
    def __init__(self, context, aabb_min, aabb_max):
        self.context = context
        self.aabb_min = aabb_min
        self.aabb_max = aabb_max

    def create(self, creator):
        creator.add_aabb(self.aabb_min, self.aabb_max)


class ProjectionPrimitive:
    def __init__(self, context, matrix):
        self.context = context
        self.matrix = matrix

    def create(self, creator):
        creator.add_projection(self.matrix)


def _parse_label(parser: Parser, context: Context) -> None:
    context.label = parser.expect_string()


def _parse_point_size(parser: Parser, context: Context) -> None:
    point_size = parser.expect_float()
    context.style['point_size'] = point_size


def _parse_plane_size(parser: Parser, context: Context) -> None:
    plane_size = parser.expect_float()
    context.style['plane_size'] = plane_size


def _parse_clip_side(parser: Parser, context: Context) -> None:
    clip_side = parser.expect_enum(['positive', 'negative'])
    context.style['clip_side'] = clip_side


def _parse_clip_plane(parser: Parser, context: Context) -> None:
    normal = parser.expect_vector(3)
    distance = parser.expect_float()
    context.add_clip_plane(PlanePrimitive(context, normal, distance))


def _parse_point(parser: Parser, context: Context) -> None:
    position = parser.expect_vector(3)
    context.add_primitive(PointPrimitive(context, position))


def _parse_line(parser: Parser, context: Context) -> None:
    from_position = parser.expect_vector(3)
    to_position = parser.expect_vector(3)
    context.add_primitive(LinePrimitive(context, from_position, to_position))


def _parse_vector(parser: Parser, context: Context) -> None:
    position = parser.expect_vector(3)
    direction = parser.expect_vector(3)
    context.add_primitive(VectorPrimitive(context, position, direction))


def _parse_plane(parser: Parser, context: Context) -> None:
    normal = parser.expect_vector(3)
    distance = parser.expect_float()
    context.add_primitive(PlanePrimitive(context, normal, distance))


def _parse_aabb(parser: Parser, context: Context) -> None:
    aabb_min = parser.expect_vector(3)
    aabb_max = parser.expect_vector(3)
    context.add_primitive(AABBPrimitive(context, aabb_min, aabb_max))


def _parse_projection(parser: Parser, context: Context) -> None:
    matrix = parser.expect_vector(16)
    context.add_primitive(ProjectionPrimitive(context, matrix))


def loads(source: str, filename=None) -> Context:
    parser = Parser(source, filename)

    stack = []
    context = Context()

    parser.skip_whitespace_and_comments()

    while not parser.at_end():
        token = parser.expect_ident()

        if token == '{':
            stack.append((context, (parser.filename, parser.line, parser.col)))
            context = context.new_child()

        elif token == '}':
            if not stack:
                parser.error('unbalanced }')
            context = stack.pop()[0]

        else:
            try:
                func = globals()["_parse_{}".format(token)]
            except KeyError:
                parser.error('unknown primitive {}'.format(token))
            func(parser, context)

    if stack:
        filename, line, col = stack[0][1]
        raise parser.error('unbalanced {{ from {}:{},{}'.format(filename, line, col))

    context.propagate()

    return context


def load(filename: str) -> None:
    with open(filename, 'r') as source_file:
        source = source_file.read()
    return loads(source, filename)


def create(context) -> None:
    creator = BlenderCreator()
    creator.create(context)


create(load('c:\\users\\wbrainerd.nbe\\desktop\\dtb.txt'))