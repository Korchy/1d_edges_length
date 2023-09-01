# Nikita Akimov
# interplanety@interplanety.org
#
# GitHub
#    https://github.com/Korchy/1d_we_crease_from_seam

import bmesh
import bpy
from bpy.props import FloatProperty
from bpy.types import Operator, Panel, Scene
from bpy.utils import register_class, unregister_class

bl_info = {
    "name": "Edges Length",
    "description": "Selects all vertices on the edge loop which do not fit into the given edge length",
    "author": "Nikita Akimov, Paul Kotelevets",
    "version": (1, 0, 0),
    "blender": (2, 79, 0),
    "location": "View3D > Tool panel > 1D > Edges Length",
    "doc_url": "https://github.com/Korchy/1d_edges_length",
    "tracker_url": "https://github.com/Korchy/1d_edges_length",
    "category": "All"
}


# MAIN CLASS

class EdgesLength:

    @classmethod
    def select_unsuitable_vertices(cls, context, edge_length):
        # select unsuitable vertices
        # works in Edit mode
        if context.active_object.mode != 'EDIT':
            return
        # switch to Object mode
        bpy.ops.object.mode_set(mode='OBJECT')
        # use bmesh
        bm = bmesh.new()
        bm.from_mesh(context.object.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        # get loops by selection
        loops = []
        selected_vertices = [vertex for vertex in bm.verts if vertex.select and 0 < len(vertex.link_edges) <= 2]
        err_point = len(selected_vertices)
        # non-closed loops
        non_start_end_vertices = [vert for vert in selected_vertices if
                                  len(vert.link_edges) == 2
                                  and (vert.link_edges[0].other_vert(vert).select
                                       and vert.link_edges[1].other_vert(vert).select)
                                  ]
        start_end_vertices = set(selected_vertices).difference(set(non_start_end_vertices))
        # try to start from each start/end vertex to get vertices loop
        for vertex in start_end_vertices:
            # get vertex as start vertex
            if vertex not in (loop[-1] for loop in loops):   # not to process again from end vertices
                loop = [vertex, ]
                next_vertex = cls._next_vert(vertex, loop)
                while next_vertex:
                    loop.append(next_vertex)
                    next_vertex = cls._next_vert(next_vertex, loop)
                    if len(loop) > err_point:
                        print('ERR counting vertices loop started from ', vertex)
                        break
                loops.append(loop)
        # try to process with closed loops
        processed_vertices = sum(loops, [])     # get vertices from already created loops
        # get not processed, but still selected loops
        possible_closed_loops = list(set(selected_vertices) - set(processed_vertices))
        while possible_closed_loops:
            loop = [possible_closed_loops[0], ]
            next_vertex = cls._next_vert(possible_closed_loops[0], loop)
            while next_vertex:
                loop.append(next_vertex)
                next_vertex = cls._next_vert(next_vertex, loop)
                if len(loop) > len(possible_closed_loops):
                    print('ERR counting vertices loop started from ', possible_closed_loops[0])
                    break
            loops.append(loop)
            possible_closed_loops = list(set(possible_closed_loops) - set(loop))
        # show loops
        # for loop in loops:
        #     print('loop')
        #     print(loop)
        # deselect all
        cls._deselect_all(bm=bm)
        # for each loop - control summary edge length
        for loop in loops:
            control_length = 0.0
            prev_vertex = loop[0]
            for vertex in loop[1:]:
                control_length += (vertex.co - prev_vertex.co).length
                if control_length < edge_length:
                    vertex.select = True
                else:
                    control_length = 0.0
                prev_vertex = vertex
        # save changed selection to the source mesh
        bm.to_mesh(context.object.data)
        # return to Edit mode
        bpy.ops.object.mode_set(mode='EDIT')

    @staticmethod
    def _deselect_all(bm):
        # remove all selection from edges and vertices
        for edge in bm.edges:
            edge.select = False
        for vertex in bm.verts:
            vertex.select = False

    @staticmethod
    def _next_vert(vertex, loop):
        # get next vertex for vertex loop
        next_vertex = None
        if len(vertex.link_edges) == 1:
            next_vertex = vertex.link_edges[0].other_vert(vertex)
            next_vertex = next_vertex if next_vertex not in loop else None
        elif len(vertex.link_edges) == 2:
            next_vertex = vertex.link_edges[0].other_vert(vertex)
            next_vertex = next_vertex if next_vertex.select and next_vertex not in loop else None
            if not next_vertex:
                next_vertex = vertex.link_edges[1].other_vert(vertex)
                next_vertex = next_vertex if next_vertex.select and next_vertex not in loop else None
        return next_vertex if next_vertex and next_vertex.select else None


# OPERATORS

class EdgesLength_OT_unsuitable_verts(Operator):
    bl_idname = 'edgeslength.unsutable_verts'
    bl_label = 'Select Verts'
    bl_options = {'REGISTER', 'UNDO'}

    edge_length = FloatProperty(
        name='Edges Length',
        default=3.0,
        min=0.0001,
        subtype='UNSIGNED'
    )

    def execute(self, context):
        EdgesLength.select_unsuitable_vertices(
            context=context,
            edge_length=self.edge_length
        )
        return {'FINISHED'}


# PANELS

class EdgesLength_PT_panel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_label = "Edges Length"
    bl_category = '1D'

    def draw(self, context):
        layout = self.layout
        layout.prop(
            data=context.scene,
            property='edges_length_length'
        )
        op = layout.operator(
            operator='edgeslength.unsutable_verts',
            icon='PARTICLE_POINT'
        )
        op.edge_length = context.scene.edges_length_length


# REGISTER

def register():
    Scene.edges_length_length = FloatProperty(
        name='Edges Length',
        default=3.0,
        min=0.0001,
        subtype='UNSIGNED'
    )
    register_class(EdgesLength_OT_unsuitable_verts)
    register_class(EdgesLength_PT_panel)


def unregister():
    unregister_class(EdgesLength_PT_panel)
    unregister_class(EdgesLength_OT_unsuitable_verts)
    del Scene.edges_length_length


if __name__ == "__main__":
    register()
