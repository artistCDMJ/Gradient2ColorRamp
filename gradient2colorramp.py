
bl_info = {
    "name": "Gradient2ColorRamp",
    "author": "CDMJ",
    "version": (1, 0, 5),
    "blender": (3, 0, 0),
    "location": "Toolbar > Paint > Gradient2ColorRamp",
    "description": "Hack to use ColorRamps in materials to make Gradients and RGB Curve Nodes to hold Falloff",
    "warning": "",
    "category": "Material"
}

import bpy
from bpy.types import Panel, Operator, PropertyGroup
from bpy.props import PointerProperty, FloatVectorProperty, StringProperty, CollectionProperty, BoolProperty, EnumProperty

### Property groups to hold the color ramps and their names
class RGBCurveItem(bpy.types.PropertyGroup):
    name: StringProperty(name="Curve Name", default="")
    active: BoolProperty(name="Active", default=False)

    @property
    def locked(self):
        return not self.active

    @locked.setter
    def locked(self, value):
        self.active = not value

class ColorRampItem(bpy.types.PropertyGroup):
    name: StringProperty(name="Ramp Name", default="")
    active: BoolProperty(name="Active", default=False)


class ColorRampManagerProperties(bpy.types.PropertyGroup):
    ramp_list: CollectionProperty(type=ColorRampItem)
    curve_list: CollectionProperty(type=RGBCurveItem)
    material_name: StringProperty(name="Material Name", default="")
    curve_material_name: StringProperty(name="Curve Material Name", default="")

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

    selected_curve_material: EnumProperty(
        name="Curve Material",
        description="Select Curve Material",
        items=get_materials,
    )

    def update_materials(self, context):
        materials = self.get_materials(context)
        if materials:
            self.selected_material = materials[0][0]
            self.selected_curve_material = materials[0][0]
        else:
            self.selected_material = ""
            self.selected_curve_material = ""

class ColorRampPalette(PropertyGroup):
    color_ramp_name: StringProperty()

# Function to get color ramp from object
def get_active_color_ramp(object_name):
    obj = bpy.data.objects.get(object_name)
    if not obj:
        return None

    material = obj.active_material
    if not material or not material.use_nodes:
        return None

    color_ramp_manager = bpy.context.scene.color_ramp_manager

    # Find the active color ramp
    for ramp in color_ramp_manager.ramp_list:
        if ramp.active:
            node_tree = material.node_tree
            if ramp.name in node_tree.nodes:
                node = node_tree.nodes[ramp.name]
                if node.type == 'VALTORGB':
                    return node.color_ramp

    return None

# Operator to set the brush palette from the active color ramp
def set_brush_palette(colors):
    palette_name = "ColorRampPalette"
    palette = bpy.data.palettes.get(palette_name)

    if not palette:
        palette = bpy.data.palettes.new(palette_name)

    # Clear existing palette colors
    palette.colors.clear()

    for color in colors:
        palette_color = palette.colors.new()
        palette_color.color = color[:3]  # Use only RGB (ignore Alpha)

class OT_GetColorRampPalette(Operator):
    bl_idname = "paint.get_color_ramp_palette"
    bl_label = "Get Color Ramp Palette"

    def execute(self, context):
        object_name = "horcrux"
        color_ramp = get_active_color_ramp(object_name)
        if not color_ramp:
            self.report({'WARNING'}, f"No active Color Ramp found in {object_name}")
            return {'CANCELLED'}

        colors = [element.color for element in color_ramp.elements]
        set_brush_palette(colors)
        context.scene.color_ramp_palette.color_ramp_name = color_ramp.id_data.name
        self.report({'INFO'}, "Palette set from Color Ramp")
        return {'FINISHED'}


### Operator to create the 'horcrux' mesh grid object and add a material
class OBJECT_OT_create_horcrux(bpy.types.Operator):
    bl_idname = "object.create_horcrux"
    bl_label = "Create Horcrux"
    bl_description = "Create a horcrux mesh grid object and add materials for color ramps and RGB curves"

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

        # Create a new material for color ramps
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

        # Create a new material for RGB curves
        curve_material_name = scene.color_ramp_manager.curve_material_name
        if curve_material_name:
            if curve_material_name not in bpy.data.materials:
                curve_material = bpy.data.materials.new(name=curve_material_name)
                curve_material.use_nodes = True  # Enable nodes
            else:
                curve_material = bpy.data.materials[curve_material_name]
                curve_material.use_nodes = True  # Ensure nodes are enabled

            horcrux_object.data.materials.append(curve_material)

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
        color_ramp_manager = scene.color_ramp_manager
        horcrux_object = bpy.data.objects.get("horcrux")

        if horcrux_object:
            # Add or update the Ramp Material
            ramp_material_name = color_ramp_manager.material_name
            if ramp_material_name:
                if ramp_material_name not in bpy.data.materials:
                    ramp_material = bpy.data.materials.new(name=ramp_material_name)
                    ramp_material.use_nodes = True  # Enable nodes
                else:
                    ramp_material = bpy.data.materials[ramp_material_name]
                    ramp_material.use_nodes = True  # Ensure nodes are enabled

                if ramp_material_name not in horcrux_object.data.materials.keys():
                    horcrux_object.data.materials.append(ramp_material)

            # Add or update the Curve Material
            curve_material_name = color_ramp_manager.curve_material_name
            if curve_material_name:
                if curve_material_name not in bpy.data.materials:
                    curve_material = bpy.data.materials.new(name=curve_material_name)
                    curve_material.use_nodes = True  # Enable nodes
                else:
                    curve_material = bpy.data.materials[curve_material_name]
                    curve_material.use_nodes = True  # Ensure nodes are enabled

                if curve_material_name not in horcrux_object.data.materials.keys():
                    horcrux_object.data.materials.append(curve_material)

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
                color_ramp_node.name = f"{material.name}_Gradient {len(node_tree.nodes) - 2}"

                new_ramp = color_ramp_manager.ramp_list.add()
                new_ramp.name = color_ramp_node.name

        return {'FINISHED'}

### Operator to add an RGB Curve to the active material
class MATERIAL_OT_add_rgb_curve(bpy.types.Operator):
    bl_idname = "material.add_rgb_curve"
    bl_label = "Add RGB Curve"
    bl_description = "Add a new RGB Curve node to the selected curve material"

    def execute(self, context):
        scene = context.scene
        color_ramp_manager = scene.color_ramp_manager
        horcrux_object = bpy.data.objects.get("horcrux")

        if horcrux_object and horcrux_object.data.materials:
            material = bpy.data.materials.get(color_ramp_manager.selected_curve_material)

            if material and material.use_nodes:
                node_tree = material.node_tree
                rgb_curve_node = node_tree.nodes.new(type='ShaderNodeRGBCurve')
                rgb_curve_node.location = (0, 0)
                rgb_curve_node.name = f"{material.name}_Curve_{len(node_tree.nodes)-2}"

                new_curve = color_ramp_manager.curve_list.add()
                new_curve.name = rgb_curve_node.name
                new_curve.locked = True

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

### Operator to remove the active RGB curve from the selected material
class MATERIAL_OT_remove_rgb_curve(bpy.types.Operator):
    bl_idname = "material.remove_rgb_curve"
    bl_label = "Remove RGB Curve"
    bl_description = "Remove the selected RGB Curve node from the selected curve material"

    def execute(self, context):
        scene = context.scene
        color_ramp_manager = scene.color_ramp_manager
        horcrux_object = bpy.data.objects.get("horcrux")
        curve_list = color_ramp_manager.curve_list

        if horcrux_object and horcrux_object.data.materials:
            material = bpy.data.materials.get(color_ramp_manager.selected_curve_material)

            if material and material.use_nodes:
                node_tree = material.node_tree

                # Find the active RGB curve
                active_curve = None
                for curve in curve_list:
                    if curve.active:
                        active_curve = curve
                        break

                # Ensure the curve node exists and is not locked before removal
                if active_curve:
                    if active_curve.name in node_tree.nodes:
                        node_tree.nodes.remove(node_tree.nodes[active_curve.name])
                        curve_list.remove(curve_list.find(active_curve.name))
                        self.report({'INFO'}, f"Removed RGB Curve: {active_curve.name}")
                    else:
                        self.report({'WARNING'}, "Active RGB Curve node not found in node tree.")
                else:
                    self.report({'WARNING'}, "No active RGB Curve to remove.")

        return {'FINISHED'}



class OBJECT_PT_horcrux_manager(bpy.types.Panel):
    bl_idname = "OBJECT_PT_horcrux_manager"
    bl_label = "Gradient and Falloff Manager"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Paint'

    def draw(self, context):
        layout = self.layout
        color_ramp_manager = context.scene.color_ramp_manager
        palette = context.scene.color_ramp_palette
        material = context.object.active_material

        layout.prop(color_ramp_manager, "material_name", text="Gradient Category Name")
        layout.prop(color_ramp_manager, "curve_material_name", text="Falloff Category Name")
        layout.operator("object.create_horcrux", text="Create Horcrux")
        layout.operator("object.add_material", text="Add Material")

        horcrux_object = bpy.data.objects.get("horcrux")
        if horcrux_object and horcrux_object.data.materials:
            layout.prop(color_ramp_manager, "selected_material", text="Gradients")
            layout.prop(color_ramp_manager, "selected_curve_material", text="Falloffs")

            row = layout.row()
            row.operator("material.add_color_ramp", text="Add ColorRamp")
            row.operator("material.remove_color_ramp", text="Remove ColorRamp")

            row = layout.row()
            row.operator("material.add_rgb_curve", text="Add Falloff")
            row.operator("material.remove_rgb_curve", text="Remove Falloff")
            
            row = layout.row()
            if palette.color_ramp_name and material and material.use_nodes:
                node_tree = material.node_tree
                color_ramp_node = node_tree.nodes.get(palette.color_ramp_name)
                if color_ramp_node and color_ramp_node.type == 'VALTORGB':
                    row.template_color_ramp(color_ramp_node, "color_ramp", expand=True)
                else:
                    row.label(text="No Color Ramp Available")
            else:
                row.label(text="No Color Ramp Available")

        layout.operator(OT_GetColorRampPalette.bl_idname, text="Get Color Ramp Palette")
            

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

            selected_curve_material = bpy.data.materials.get(color_ramp_manager.selected_curve_material)
            if selected_curve_material and selected_curve_material.use_nodes:
                node_tree = selected_curve_material.node_tree

                if color_ramp_manager.curve_list:
                    for curve in color_ramp_manager.curve_list:
                        if curve.name in node_tree.nodes:
                            rgb_curve_node = node_tree.nodes[curve.name]
                            box = layout.box()
                            row = box.row()
                            row.prop(curve, "active", text="", icon='VIEW_UNLOCKED' if curve.active else 'VIEW_LOCKED')
                            row.label(text=curve.name)
                            box.template_curve_mapping(data=rgb_curve_node, property="mapping", type='COLOR')
                else:
                    layout.label(text="No RGB Curves Added", icon='INFO')

class AddColorToPalette(Operator):
    bl_idname = "palette.add_color"
    bl_label = "Add Color to Palette"

    color: FloatVectorProperty(
        name="Color",
        subtype='COLOR',
        min=0.0, max=1.0,
        default=(1.0, 1.0, 1.0, 1.0)
    )

    def execute(self, context):
        material = context.object.active_material
        if not material or not material.use_nodes:
            self.report({'WARNING'}, "No active material with nodes found")
            return {'CANCELLED'}

        color_ramp_name = context.scene.color_ramp_palette.color_ramp_name
        node_tree = material.node_tree
        color_ramp_node = node_tree.nodes.get(color_ramp_name)

        if color_ramp_node and color_ramp_node.type == 'VALTORGB':
            new_element = color_ramp_node.color_ramp.elements.new(0.5)
            new_element.color = self.color
            self.report({'INFO'}, "Color added to active Color Ramp")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "No active Color Ramp found")
            return {'CANCELLED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)




### Register and unregister functions
def register():
    
    bpy.utils.register_class(RGBCurveItem)
    bpy.utils.register_class(ColorRampItem)
    bpy.utils.register_class(ColorRampManagerProperties)
    bpy.utils.register_class(ColorRampPalette)
    bpy.utils.register_class(OT_GetColorRampPalette)
    bpy.utils.register_class(OBJECT_OT_create_horcrux)
    bpy.utils.register_class(OBJECT_OT_add_material)
    bpy.utils.register_class(MATERIAL_OT_add_color_ramp)
    bpy.utils.register_class(MATERIAL_OT_add_rgb_curve)
    bpy.utils.register_class(MATERIAL_OT_remove_color_ramp)
    bpy.utils.register_class(MATERIAL_OT_remove_rgb_curve)
    bpy.utils.register_class(OBJECT_PT_horcrux_manager)    
    bpy.utils.register_class(AddColorToPalette)
    
    bpy.types.Scene.color_ramp_palette = PointerProperty(type=ColorRampPalette)
    bpy.types.Scene.color_ramp_manager = PointerProperty(type=ColorRampManagerProperties)

def unregister():
    bpy.utils.unregister_class(RGBCurveItem)
    bpy.utils.unregister_class(ColorRampItem)
    bpy.utils.unregister_class(ColorRampManagerProperties)
    bpy.utils.unregister_class(ColorRampPalette)
    bpy.utils.unregister_class(OBJECT_OT_create_horcrux)
    bpy.utils.unregister_class(OBJECT_OT_add_material)
    bpy.utils.unregister_class(MATERIAL_OT_add_color_ramp)
    bpy.utils.unregister_class(MATERIAL_OT_add_rgb_curve)
    bpy.utils.unregister_class(MATERIAL_OT_remove_color_ramp)
    bpy.utils.unregister_class(MATERIAL_OT_remove_rgb_curve)
    bpy.utils.unregister_class(OBJECT_PT_horcrux_manager)    
    bpy.utils.unregister_class(AddColorToPalette)
    bpy.utils.unregister_class(OT_GetColorRampPalette)
    del bpy.types.Scene.color_ramp_palette
    del bpy.types.Scene.color_ramp_manager

if __name__ == "__main__":
    register()
