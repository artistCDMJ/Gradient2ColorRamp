# -*- coding: utf8 -*-
# python
# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# NON <pep8 compliant>
###############################################################################

bl_info = {"name": "Gradient2ColorRamp",
           "author": "CDMJ",
           "version": (1, 00, 0),
           "blender": (3, 0, 0),
           "location": "Toolbar > Paint > Gradient2ColorRamp",
           "description": "Hack to use ColorRamps in Compositor to make Gradients",
           "warning": "",
           "category": "Compositor"}


import bpy


### To get setup for MAKING one Active to be deleted - previous we deleted wrong because we can't see
### the Active node in the Compositor
class ColorRampItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Ramp Name", default="")
    active: bpy.props.BoolProperty(name="Active", default=False)

### Establish a list to work from of the generated numeric names
class ColorRampManagerProperties(bpy.types.PropertyGroup):
    ramp_list: bpy.props.CollectionProperty(type=ColorRampItem)
    
### Add and Name a Compositor Editor Disconnected Color Ramp for Manipulation
class COMPOSITOR_OT_add_color_ramp(bpy.types.Operator):
    bl_idname = "compositor.add_color_ramp"
    bl_label = "Add Color Ramp"
    bl_description = "Add a new Color Ramp node to the compositor"

    def execute(self, context):
        scene = context.scene
        scene.use_nodes = True
        tree = scene.node_tree
        color_ramp_node = tree.nodes.new(type='CompositorNodeValToRGB')
        color_ramp_node.location = (0, 0)
        color_ramp_node.name = "Gradient %d" % (len(tree.nodes) - 2)
        color_ramp_node["is_gradient_ramp"] = True  # Custom property to tag the node

        new_ramp = context.scene.color_ramp_manager.ramp_list.add()
        new_ramp.name = color_ramp_node.name
        return {'FINISHED'}

### Remove the Active Color Ramp from the Compositor
class COMPOSITOR_OT_remove_color_ramp(bpy.types.Operator):
    bl_idname = "compositor.remove_color_ramp"
    bl_label = "Remove Color Ramp"
    bl_description = "Remove the selected Color Ramp node from the compositor"

    def execute(self, context):
        scene = context.scene
        tree = scene.node_tree
        ramp_list = context.scene.color_ramp_manager.ramp_list

        # Find the active color ramp
        active_ramp = None
        for ramp in ramp_list:
            if ramp.active:
                active_ramp = ramp
                break

        if active_ramp and active_ramp.name in tree.nodes:
            tree.nodes.remove(tree.nodes[active_ramp.name])
            ramp_list.remove(ramp_list.find(active_ramp.name))

        return {'FINISHED'}

### This is a Hack to Dispaly the Compositor Color Ramps in the Paint Panel of the 3d View by using same UI
### that was used in the Compositor
class COMPOSITOR_PT_color_ramp_manager(bpy.types.Panel):
    bl_idname = "COMPOSITOR_PT_color_ramp_manager"
    bl_label = "Gradient2ColorRamp"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Paint'

    def draw(self, context):
        layout = self.layout
        color_ramp_manager = context.scene.color_ramp_manager

        row = layout.row()
        row.operator("compositor.add_color_ramp", text="Add Color Ramp")
        row.operator("compositor.remove_color_ramp", text="Remove Color Ramp")

        tree = context.scene.node_tree

        # Display only nodes tagged with "is_gradient_ramp"
        if color_ramp_manager.ramp_list:
            for ramp in color_ramp_manager.ramp_list:
                if ramp.name in tree.nodes and "is_gradient_ramp" in tree.nodes[ramp.name]:
                    color_ramp_node = tree.nodes[ramp.name]
                    box = layout.box()
                    row = box.row()
                    row.prop(ramp, "active", text="", icon='VIEW_UNLOCKED' if ramp.active else 'VIEW_LOCKED')
                    row.label(text=ramp.name)
                    box.template_color_ramp(color_ramp_node, "color_ramp", expand=True)
        else:
            layout.label(text="No Color Ramps Added", icon='INFO')

def register():
    bpy.utils.register_class(ColorRampItem)
    bpy.utils.register_class(ColorRampManagerProperties)
    bpy.utils.register_class(COMPOSITOR_OT_add_color_ramp)
    bpy.utils.register_class(COMPOSITOR_OT_remove_color_ramp)
    bpy.utils.register_class(COMPOSITOR_PT_color_ramp_manager)
    bpy.types.Scene.color_ramp_manager = bpy.props.PointerProperty(type=ColorRampManagerProperties)

def unregister():
    bpy.utils.unregister_class(ColorRampItem)
    bpy.utils.unregister_class(ColorRampManagerProperties)
    bpy.utils.unregister_class(COMPOSITOR_OT_add_color_ramp)
    bpy.utils.unregister_class(COMPOSITOR_OT_remove_color_ramp)
    bpy.utils.unregister_class(COMPOSITOR_PT_color_ramp_manager)
    del bpy.types.Scene.color_ramp_manager

if __name__ == "__main__":
    register()

