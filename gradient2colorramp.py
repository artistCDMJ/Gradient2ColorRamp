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
bl_info = {
    "name": "Gradient2ColorRamp",
    "author": "CDMJ",
    "version": (1, 0, 3),
    "blender": (3, 0, 0),
    "location": "Toolbar > Paint > Gradient2ColorRamp",
    "description": "Hack to use ColorRamps in materials to make Gradients",
    "warning": "",
    "category": "Material"
}

import bpy
from bpy.props import StringProperty, BoolProperty, CollectionProperty, PointerProperty, EnumProperty

### Property groups to hold the color ramps and their names
class ColorRampItem(bpy.types.PropertyGroup):
    name: StringProperty(name="Ramp Name", default="")
    active: BoolProperty(name="Active", default=False)

class ColorRampManagerProperties(bpy.types.PropertyGroup):
    ramp_list: CollectionProperty(type=ColorRampItem)
    material_name: StringProperty(name="Material Name", default="")

    def get_materials(self, context):
        horcrux_object = bpy.data.objects.get("horcrux")
        if horcrux_object and horcrux_object.data.materials:
            return [(mat.name, mat.name, "") for mat in horcrux_object.data.materials]
        return []

    selected_material: EnumProperty(
        name="Material",
        description="Select Material",
        items=get_materials,
    )

    def update_materials(self, context):
        materials = self.get_materials(context)
        if materials:
            self.selected_material = materials[0][0]
        else:
            self.selected_material = ""

### Operator to create the 'horcrux' mesh grid object and add a material
class OBJECT_OT_create_horcrux(bpy.types.Operator):
    bl_idname = "object.create_horcrux"
    bl_label = "Create Horcrux"
    bl_description = "Create a horcrux mesh grid object and add a material for color ramps"

    def execute(self, context):
        scene = context.scene

        # Create a new collection if it doesn't exist
        if "Gradients and Curves" not in bpy.data.collections:
            new_collection = bpy.data.collections.new("Gradients and Curves")
            bpy.context.scene.collection.children.link(new_collection)
        else:
            new_collection = bpy.data.collections["Gradients and Curves"]

        # Create the horcrux mesh grid object
        if "horcrux" not in bpy.data.objects:
            bpy.ops.mesh.primitive_grid_add(x_subdivisions=10, y_subdivisions=10, size=2)
            horcrux_object = bpy.context.active_object
            horcrux_object.name = "horcrux"
            # Unlink from the current collection(s) before linking to the new collection
            for collection in horcrux_object.users_collection:
                collection.objects.unlink(horcrux_object)
            new_collection.objects.link(horcrux_object)
            bpy.context.view_layer.objects.active = horcrux_object
        else:
            horcrux_object = bpy.data.objects["horcrux"]
            # Unlink from the current collection(s) before linking to the new collection
            for collection in horcrux_object.users_collection:
                collection.objects.unlink(horcrux_object)
            new_collection.objects.link(horcrux_object)

        # Create a new material
        material_name = scene.color_ramp_manager.material_name
        if material_name:
            if material_name not in bpy.data.materials:
                material = bpy.data.materials.new(name=material_name)
                material.use_nodes = True  # Enable nodes
            else:
                material = bpy.data.materials[material_name]
                material.use_nodes = True  # Ensure nodes are enabled

            if horcrux_object.data.materials:
                horcrux_object.data.materials[0] = material
            else:
                horcrux_object.data.materials.append(material)

        # Update the material list in the UI
        context.scene.color_ramp_manager.update_materials(context)
        
        # Exclude the "Gradients and Curves" collection from the view layer to prevent it from rendering
        view_layer = context.view_layer
        layer_collection = view_layer.layer_collection.children.get(new_collection.name)
        if layer_collection:
            layer_collection.exclude = True

        return {'FINISHED'}

### Operator to add a new material to the horcrux object
class OBJECT_OT_add_material(bpy.types.Operator):
    bl_idname = "object.add_material"
    bl_label = "Add Material"
    bl_description = "Add a new material to the horcrux object"

    def execute(self, context):
        scene = context.scene
        horcrux_object = bpy.data.objects["horcrux"]
        material_name = scene.color_ramp_manager.material_name

        if material_name:
            if material_name not in bpy.data.materials:
                material = bpy.data.materials.new(name=material_name)
                material.use_nodes = True  # Enable nodes
            else:
                material = bpy.data.materials[material_name]
                material.use_nodes = True  # Ensure nodes are enabled

            horcrux_object.data.materials.append(material)

        # Update the material list in the UI
        context.scene.color_ramp_manager.update_materials(context)
        return {'FINISHED'}

### Operator to add a color ramp to the active material
class MATERIAL_OT_add_color_ramp(bpy.types.Operator):
    bl_idname = "material.add_color_ramp"
    bl_label = "Add Color Ramp"
    bl_description = "Add a new Color Ramp node to the selected material"

    def execute(self, context):
        scene = context.scene
        color_ramp_manager = scene.color_ramp_manager
        horcrux_object = bpy.data.objects.get("horcrux")

        if horcrux_object and horcrux_object.data.materials:
            material = bpy.data.materials.get(color_ramp_manager.selected_material)

            if material and material.use_nodes:
                node_tree = material.node_tree
                color_ramp_node = node_tree.nodes.new(type='ShaderNodeValToRGB')
                color_ramp_node.location = (0, 0)
                color_ramp_node.name = f"{material.name}_Gradient {len(node_tree.nodes) -2}"

                new_ramp = color_ramp_manager.ramp_list.add()
                new_ramp.name = color_ramp_node.name

        return {'FINISHED'}

### Operator to remove the active color ramp from the selected material
class MATERIAL_OT_remove_color_ramp(bpy.types.Operator):
    bl_idname = "material.remove_color_ramp"
    bl_label = "Remove Color Ramp"
    bl_description = "Remove the selected Color Ramp node from the selected material"

    def execute(self, context):
        scene = context.scene
        color_ramp_manager = scene.color_ramp_manager
        horcrux_object = bpy.data.objects.get("horcrux")
        ramp_list = color_ramp_manager.ramp_list

        if horcrux_object and horcrux_object.data.materials:
            material = bpy.data.materials.get(color_ramp_manager.selected_material)

            if material and material.use_nodes:
                node_tree = material.node_tree

                # Find the active color ramp
                active_ramp = None
                for ramp in ramp_list:
                    if ramp.active:
                        active_ramp = ramp
                        break

                if active_ramp and active_ramp.name in node_tree.nodes:
                    node_tree.nodes.remove(node_tree.nodes[active_ramp.name])
                    ramp_list.remove(ramp_list.find(active_ramp.name))

        return {'FINISHED'}

### UI Panel for managing the horcrux and materials
class OBJECT_PT_horcrux_manager(bpy.types.Panel):
    bl_idname = "OBJECT_PT_horcrux_manager"
    bl_label = "Gradient Manager"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Paint'

    def draw(self, context):
        layout = self.layout
        color_ramp_manager = context.scene.color_ramp_manager

        layout.prop(color_ramp_manager, "material_name")
        layout.operator("object.create_horcrux", text="Create Horcrux")
        layout.operator("object.add_material", text="Add Material")

        horcrux_object = bpy.data.objects.get("horcrux")
        if horcrux_object and horcrux_object.data.materials:
            layout.prop(color_ramp_manager, "selected_material", text="Select Material")

            row = layout.row()
            row.operator("material.add_color_ramp", text="Add Color Ramp")
            row.operator("material.remove_color_ramp", text="Remove Color Ramp")

            selected_material = bpy.data.materials.get(color_ramp_manager.selected_material)
            if selected_material and selected_material.use_nodes:
                node_tree = selected_material.node_tree

                if color_ramp_manager.ramp_list:
                    for ramp in color_ramp_manager.ramp_list:
                        if ramp.name in node_tree.nodes:
                            color_ramp_node = node_tree.nodes[ramp.name]
                            box = layout.box()
                            row = box.row()
                            row.prop(ramp, "active", text="", icon='VIEW_UNLOCKED' if ramp.active else 'VIEW_LOCKED')
                            row.label(text=ramp.name)
                            box.template_color_ramp(color_ramp_node, "color_ramp", expand=True)
                else:
                    layout.label(text="No Color Ramps Added", icon='INFO')

### Register and unregister functions
def register():
    bpy.utils.register_class(ColorRampItem)
    bpy.utils.register_class(ColorRampManagerProperties)
    bpy.utils.register_class(OBJECT_OT_create_horcrux)
    bpy.utils.register_class(OBJECT_OT_add_material)
    bpy.utils.register_class(MATERIAL_OT_add_color_ramp)
    bpy.utils.register_class(MATERIAL_OT_remove_color_ramp)
    bpy.utils.register_class(OBJECT_PT_horcrux_manager)
    bpy.types.Scene.color_ramp_manager = PointerProperty(type=ColorRampManagerProperties)

def unregister():
    bpy.utils.unregister_class(ColorRampItem)
    bpy.utils.unregister_class(ColorRampManagerProperties)
    bpy.utils.unregister_class(OBJECT_OT_create_horcrux)
    bpy.utils.unregister_class(OBJECT_OT_add_material)
    bpy.utils.unregister_class(MATERIAL_OT_add_color_ramp)
    bpy.utils.unregister_class(MATERIAL_OT_remove_color_ramp)
    bpy.utils.unregister_class(OBJECT_PT_horcrux_manager)
    del bpy.types.Scene.color_ramp_manager

if __name__ == "__main__":
    register()
