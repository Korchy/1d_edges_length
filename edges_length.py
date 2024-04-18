# Nikita Akimov
# interplanety@interplanety.org
#
# GitHub
#    https://github.com/Korchy/1d_edges_length

import bmesh
import bpy
from bpy.props import FloatProperty
from bpy.types import Operator, Panel, Scene
from bpy.utils import register_class, unregister_class
from math import radians, degrees

bl_info = {
    "name": "Edges Length",
    "description": "Selects all vertices on the edge loop which do not fit into the given edge length",
    "author": "Nikita Akimov, Paul Kotelevets",
    "version": (1, 1, 4),
    "blender": (2, 79, 0),
    "location": "View3D > Tool panel > 1D > Edges Length",
    "doc_url": "https://github.com/Korchy/1d_edges_length",
    "tracker_url": "https://github.com/Korchy/1d_edges_length",
    "category": "All"
}


# MAIN CLASS

class EdgesLength:

    @classmethod
    def select_unsuitable_vertices(cls, context, edge_length, gradual_angle, deselect_angle):
        # select unsuitable vertices
        # gradual_angle - in degrees
        # deselect_angle - in degrees
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
        # optimize start-end loops for more convenient processing: all from left to right by X axis
        for loop in loops:
            if loop[0].co.x > loop[-1].co.x:
                loop.reverse()
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
        # for each loop - control summary edge length and gradual angle
        for loop in loops:
            control_length = 0.0            # summary edges length
            control_gradual_angle = 0.0     # summary angle between edges (deg)
            prev_vertex = loop[0]
            for vertex in loop[1:]:
                control_length += (vertex.co - prev_vertex.co).length
                control_gradual_angle += degrees(vertex.calc_edge_angle(0.0))
                if control_length < edge_length and control_gradual_angle < gradual_angle:
                    vertex.select = True
                else:
                    control_length = 0.0
                    control_gradual_angle = 0.0
                prev_vertex = vertex
            # deselect first and last vertices of the loop
            loop[0].select = False
            loop[-1].select = False
        # deselect vertices with angle less than deselect_angle
        for vertex in (_vertex for _vertex in bm.verts
                       if _vertex.select
                           and len(_vertex.link_edges) == 2):
            edge0 = vertex.link_edges[0]
            edge1 = vertex.link_edges[1]
            if cls._edges_angle(edge0=edge0, edge1=edge1) < radians(deselect_angle):
                vertex.select = False
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

    @staticmethod
    def _edges_angle(edge0, edge1):
        # find angle between two linked edges
        # edge0, edge1 - bmesh edges
        vert0 = edge0.verts[0] if edge0.verts[0] in edge1.verts else edge0.verts[1]     # common vertex
        vert1 = edge0.other_vert(vert0)
        vert2 = edge1.other_vert(vert0)
        vec0 = vert0.co - vert1.co
        vec1 = vert0.co - vert2.co
        # return angle in radians
        angle = vec0.angle(vec1)
        angle = angle if angle < radians(180) else (radians(360) - angle)
        return angle

    @staticmethod
    def ui(layout, context):
        # ui panel
        layout.prop(
            data=context.scene,
            property='edges_length_length'
        )
        layout.prop(
            data=context.scene,
            property='edges_length_gradual_angle'
        )
        layout.prop(
            data=context.scene,
            property='edges_length_deselect_angle'
        )
        op = layout.operator(
            operator='edgeslength.unsutable_verts',
            icon='PARTICLE_POINT'
        )
        op.edge_length = context.scene.edges_length_length
        op.gradual_angle = context.scene.edges_length_gradual_angle
        op.deselect_angle = context.scene.edges_length_deselect_angle


# OPERATORS

class EdgesLength_OT_unsuitable_verts(Operator):
    bl_idname = 'edgeslength.unsutable_verts'
    bl_label = 'Deselect Verts'
    bl_description = 'Deselect Vertices on selected wire loops to split the selection by distance and angle'
    bl_options = {'REGISTER', 'UNDO'}

    edge_length = FloatProperty(
        name='Edges Length',
        default=3.0,
        min=0.0001,
        subtype='UNSIGNED'
    )

    gradual_angle = FloatProperty(
        name='Gradual Angle (deg)',
        default=110.0,
        min=0.0,
        subtype='UNSIGNED'
    )

    deselect_angle = FloatProperty(
        name='Deselect angle (deg)',
        default=110,
        min=0,
        max=360,
        subtype='UNSIGNED'
    )

    def execute(self, context):
        EdgesLength.select_unsuitable_vertices(
            context=context,
            edge_length=self.edge_length,
            gradual_angle=self.gradual_angle,
            deselect_angle=self.deselect_angle
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
        EdgesLength.ui(
            layout=layout,
            context=context
        )


# REGISTER

def register(ui=True):
    Scene.edges_length_length = FloatProperty(
        name='Edges Length',
        description='Distance to split with vertex deselection',
        default=3.0,
        min=0.0001,
        subtype='UNSIGNED'
    )
    Scene.edges_length_gradual_angle = FloatProperty(
        name='Gradual Angle (deg)',
        default=110.0,
        min=0.0,
        subtype='UNSIGNED'
    )
    Scene.edges_length_deselect_angle = FloatProperty(
        name='Deselect angle (deg)',
        description='Angle between edges to split with vertex deselection',
        default=110,
        min=0,
        max=360,
        subtype='UNSIGNED'
    )
    register_class(EdgesLength_OT_unsuitable_verts)
    if ui:
        register_class(EdgesLength_PT_panel)


def unregister(ui=True):
    if ui:
        unregister_class(EdgesLength_PT_panel)
    unregister_class(EdgesLength_OT_unsuitable_verts)
    del Scene.edges_length_deselect_angle
    del Scene.edges_length_gradual_angle
    del Scene.edges_length_length


if __name__ == "__main__":
    register()
