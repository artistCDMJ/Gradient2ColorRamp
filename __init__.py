import bpy

bl_info = {
    "name": "Gradient2ColorRamp",
    "author": "CDMJ",
    "version": (1, 1, 0),
    "blender": (3, 0, 0),
    "location": "Toolbar > Paint > Gradient2ColorRamp",
    "description": "Hack to use ColorRamps in materials to make Gradients and RGB Curve Nodes to hold Falloff",
    "warning": "",
    "category": "Material"
}

from bpy.types import Panel, Operator, PropertyGroup
from bpy.props import PointerProperty, FloatVectorProperty, StringProperty, CollectionProperty, BoolProperty, EnumProperty

# Property groups
class RGBCurveItem(PropertyGroup):
    name: StringProperty(name="Curve Name", default="")
    active: BoolProperty(name="Active", default=False)

    @property
    def locked(self):
        return not self.active

    @locked.setter
    def locked(self, value):
        self.active = not value

class ColorRampItem(PropertyGroup):
    name: StringProperty(name="Ramp Name", default="")
    active: BoolProperty(name="Active", default=False)

from bpy.types import PropertyGroup
from bpy.props import StringProperty, CollectionProperty, EnumProperty

def get_active_horcrux(context):
    """Retrieve the currently selected horcrux object based on the UI selection."""
    color_ramp_manager = context.scene.color_ramp_manager
    horcrux_name = color_ramp_manager.selected_horcrux
    return bpy.data.objects.get(horcrux_name)


class ColorRampManagerProperties(PropertyGroup):
    ramp_list: CollectionProperty(type=ColorRampItem)
    curve_list: CollectionProperty(type=RGBCurveItem)
    material_name: StringProperty(name="Material Name", default="")
    curve_material_name: StringProperty(name="Curve Material Name", default="")

    def get_materials(self, context):
        horcrux_object = bpy.data.objects.get(self.selected_horcrux)
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
        horcrux_object = bpy.data.objects.get(self.selected_horcrux)
        
        if horcrux_object:
            # Clear existing lists
            self.ramp_list.clear()
            self.curve_list.clear()
            
            # Populate ramp_list and curve_list with the appropriate nodes
            if horcrux_object.data.materials:
                for material in horcrux_object.data.materials:
                    node_tree = material.node_tree
                    
                    if node_tree:
                        # Populate ramp_list with color ramps
                        for node in node_tree.nodes:
                            if node.type == 'VALTORGB':
                                new_ramp = self.ramp_list.add()
                                new_ramp.name = node.name
                                new_ramp.active = False  # Default inactive

                        # Populate curve_list with RGB curves
                        for node in node_tree.nodes:
                            if node.type == 'CURVE_RGB':
                                new_curve = self.curve_list.add()
                                new_curve.name = node.name
                                new_curve.active = False  # Default inactive
                                
            # Update the selected material and curve material properties only if there are materials
            materials = [(mat.name, mat.name, "") for mat in horcrux_object.data.materials]
            if materials:
                self.selected_material = materials[0][0] if materials else ""
                self.selected_curve_material = materials[0][0] if materials else ""
        
        else:
            # Avoid setting to None; reset to empty string if no horcrux is selected
            self.selected_material = ""
            self.selected_curve_material = ""

        # Force UI refresh
        if context.area:
            context.area.tag_redraw()

    def get_horcrux_objects(self, context):
        objects = [(obj.name, obj.name, "") for obj in bpy.data.objects if "horcrux" in obj.name.lower() and obj.type == 'MESH']
        return objects if objects else [("NONE", "No Horcrux Found", "")]

    def update_material_selection(self, context):
        self.update_materials(context)

    selected_horcrux: EnumProperty(
        name="Horcrux Object",
        description="Select Horcrux Object",
        items=get_horcrux_objects,
        update=update_material_selection
    )


class ColorRampPalette(PropertyGroup):
    color_ramp_name: StringProperty()


def copy_brush_gradient_to_color_ramp(context):
    brush = context.tool_settings.image_paint.brush
    color_ramp_manager = context.scene.color_ramp_manager
    
    if not brush or brush.color_type != 'GRADIENT':
        print("No valid brush gradient found.")
        return None

    # Retrieve the active color ramp node
    color_ramp_node = get_active_color_ramp(context)
    if not color_ramp_node:
        print("No active color ramp found.")
        return None

    # Access the color ramp elements
    color_ramp = color_ramp_node.color_ramp
    brush_gradient = brush.gradient

    # Copy the points from the brush gradient to the color ramp
    new_elements = [(elem.position, elem.color) for elem in brush_gradient.elements]

    # Ensure there are enough elements in the color ramp
    while len(color_ramp.elements) < len(new_elements):
        color_ramp.elements.new(0)

    # Update the color ramp elements
    for i, (pos, color) in enumerate(new_elements):
        color_ramp.elements[i].position = pos
        color_ramp.elements[i].color = color

    # Remove extra elements from the color ramp if necessary
    while len(color_ramp.elements) > len(new_elements):
        color_ramp.elements.remove(color_ramp.elements[-1])

    return color_ramp


def copy_brush_falloff_to_rgb_curve(context):
    brush = context.tool_settings.image_paint.brush
    color_ramp_manager = context.scene.color_ramp_manager
    
    if not brush or not hasattr(brush, 'curve'):
        print("No valid brush falloff curve found.")
        return None

    rgb_curve_node = get_active_rgb_curve(color_ramp_manager.selected_horcrux, color_ramp_manager.selected_curve_material)
    if not rgb_curve_node:
        print("No active RGB curve found.")
        return None

    brush_curve = brush.curve.curves[0]
    rgb_curve = rgb_curve_node.mapping.curves[3]

    # Copy the points from the brush falloff to the RGB curve
    for point in brush_curve.points:
        new_point = rgb_curve.points.new(point.location[0], point.location[1])

    # Set handle types, if necessary
    for point in rgb_curve.points:
        point.handle_type = 'AUTO'

    rgb_curve_node.mapping.update()

    return rgb_curve_node


def get_active_color_ramp(context):
    horcrux_object = get_active_horcrux(context)
    if not horcrux_object:
        return None

    material = horcrux_object.active_material
    if not material or not material.use_nodes:
        return None

    color_ramp_manager = context.scene.color_ramp_manager

    for ramp in color_ramp_manager.ramp_list:
        if ramp.active:
            node_tree = material.node_tree
            if ramp.name in node_tree.nodes:
                node = node_tree.nodes[ramp.name]
                if node.type == 'VALTORGB':
                    return node  # Return the ShaderNodeValToRGB node itself

    return None


def get_active_rgb_curve(horcrux_name, selected_curve_material):
    """Retrieve the active RGB curve node from the Horcrux object."""
    obj = bpy.data.objects.get(horcrux_name) #line 153
    if not obj:
        return None
    
    # Assuming selected_curve_material is the name of a material
    material = obj.material_slots.get(selected_curve_material).material if obj.material_slots else None
    if not material:
        return None
    
    # Assuming the RGB curve is within a specific node group
    for node in material.node_tree.nodes:
        if node.type == 'CURVE_RGB':
            return node
    
    return None




def set_brush_palette(colors, color_ramp_node_name):
    # Create the palette name using the color ramp's node name
    palette_name = f"{color_ramp_node_name}_Palette"
    
    # Check if a palette with that name already exists
    palette = bpy.data.palettes.get(palette_name)

    # If it doesn't exist, create a new palette
    if not palette:
        palette = bpy.data.palettes.new(palette_name)

    # Clear any existing colors in the palette
    palette.colors.clear()

    # Add the new colors to the palette
    for color in colors:
        palette_color = palette.colors.new()
        palette_color.color = color[:3]
    
    return palette_name



class G2C_OT_GetColorRampPalette(Operator):
    """Create Palette from Active Color Ramp"""
    bl_idname = "paint.get_color_ramp_palette"
    bl_label = "Get Color Ramp Palette"

    def execute(self, context):
        # Retrieve the active color ramp node (must be a ShaderNodeValToRGB node)
        color_ramp_node = get_active_color_ramp(context)
        if not color_ramp_node or color_ramp_node.type != 'VALTORGB':
            self.report({'WARNING'}, "No active Color Ramp found in the selected horcrux.")
            return {'CANCELLED'}

        # Extract colors from the color ramp within the ShaderNodeValToRGB node
        color_ramp = color_ramp_node.color_ramp
        colors = [element.color for element in color_ramp.elements]
        
        # Use the node's name for the palette
        color_ramp_node_name = color_ramp_node.name
        palette_name = set_brush_palette(colors, color_ramp_node_name)
        
        # Store the palette name in the scene's property
        context.scene.color_ramp_palette.color_ramp_name = palette_name
        
        # Report success
        self.report({'INFO'}, f"Palette '{palette_name}' set from Color Ramp")
        return {'FINISHED'}




class G2C_OT_CopyRGBCurveToBrushFalloff(Operator):
    """Copy Active RGB Curve to Brush Falloff"""
    bl_idname = "paint.copy_rgb_curve_to_brush_falloff"
    bl_label = "Copy RGB Curve to Brush Falloff"
    bl_description = "Copy the active RGB curve from the selected horcrux object to the active brush falloff"

    def execute(self, context):
        color_ramp_manager = context.scene.color_ramp_manager
        horcrux_name = color_ramp_manager.selected_horcrux
        selected_curve_material = color_ramp_manager.selected_curve_material

        
        rgb_curve_node = get_active_rgb_curve(horcrux_name, selected_curve_material)
        if not rgb_curve_node:
            self.report({'WARNING'}, "No active RGB Curve node found in the selected horcrux object.")
            return {'CANCELLED'}
        
        brush = context.tool_settings.image_paint.brush
        if not brush:
            self.report({'WARNING'}, "No active brush found.")
            return {'CANCELLED'}

        brush.curve_preset = 'CUSTOM'

        if not hasattr(brush, 'curve'):
            self.report({'WARNING'}, "The active brush does not have a falloff curve.")
            return {'CANCELLED'}

        curve_mapping = brush.curve
        curve = curve_mapping.curves[0]
        composite_curve = rgb_curve_node.mapping.curves[3]

        points_list = [(point.location[0], point.location[1]) for point in composite_curve.points]

        while len(curve.points) < len(points_list):
            curve.points.new(0, 0)

        for i, (x, y) in enumerate(points_list):
            curve.points[i].location = (x, y)

        curve_mapping.update()
        context.area.tag_redraw()

        self.report({'INFO'}, "Copied RGB Curve to Brush Falloff Curve successfully.")
        return {'FINISHED'}


class G2C_OT_CopyRGBCurveToCavityMask(bpy.types.Operator):
    """Copy Active RGB Curve to Cavity Mask Curve"""
    bl_idname = "paint.copy_rgb_curve_to_cavity_mask"
    bl_label = "Copy RGB Curve to Cavity Mask"
    bl_description = "Copy the active RGB curve from the Horcrux object to the cavity mask"

    def enable_cavity_masking(self):
        bpy.context.scene.tool_settings.image_paint.use_cavity = True
        print("Cavity masking enabled in image paint settings.")

    def print_curve_points(self, label, curve):
        print(f"{label} Points:")
        for i, point in enumerate(curve.points):
            print(f"  Point {i}: {point.location}")

    def copy_rgb_curve_to_cavity_mask(self, context):
        obj = get_active_horcrux(context)
        if not obj:
            self.report({'WARNING'}, "No Horcrux object found.")
            return {'CANCELLED'}

        color_ramp_manager = context.scene.color_ramp_manager
        rgb_curve_node = get_active_rgb_curve(obj.name, color_ramp_manager.selected_curve_material)
        if not rgb_curve_node:
            self.report({'WARNING'}, "No active RGB Curve node found in the selected Horcrux object.")
            return {'CANCELLED'}

        self.enable_cavity_masking()

        cavity_curve = context.scene.tool_settings.image_paint.cavity_curve.curves[0]
        composite_curve = rgb_curve_node.mapping.curves[3]

        if not composite_curve.points:
            self.report({'WARNING'}, "RGB Curve has no points.")
            return {'CANCELLED'}

        if not cavity_curve.points:
            self.report({'WARNING'}, "Cavity Curve has no points.")
            return {'CANCELLED'}

        points_list = [(point.location[0], point.location[1]) for point in composite_curve.points]

        self.print_curve_points("RGB Curve", composite_curve)

        while len(cavity_curve.points) < len(points_list):
            cavity_curve.points.new(0, 0)

        self.print_curve_points("Cavity Curve Before Update", cavity_curve)

        for i, (x, y) in enumerate(points_list):
            cavity_curve.points[i].location = (x, y)

        self.print_curve_points("Cavity Curve After Update", cavity_curve)

        while len(cavity_curve.points) > len(points_list):
            cavity_curve.points.remove(cavity_curve.points[-1])

        self.print_curve_points("Cavity Curve After Removing Excess", cavity_curve)

        for point in cavity_curve.points:
            point.handle_type = 'AUTO'

        context.scene.tool_settings.image_paint.cavity_curve.update()

        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

        self.print_curve_points("Cavity Curve After Forcing Update", cavity_curve)
        self.report({'INFO'}, "Copied RGB Curve to Cavity Mask Curve successfully.")
        return {'FINISHED'}

    def execute(self, context):
        return self.copy_rgb_curve_to_cavity_mask(context)


class G2C_OT_create_horcrux(Operator):
    """Create Horcrux to Hold All Curves and Color Ramps in User Defined Material Categories"""
    bl_idname = "object.create_horcrux"
    bl_label = "Create Horcrux"
    bl_description = "Create a horcrux mesh grid object and add materials for color ramps and RGB curves"
    
    @classmethod
    def poll(cls, context):
        # Check if any object in the scene has 'horcrux' in its name
        return not any("horcrux" in obj.name for obj in bpy.data.objects)

    def execute(self, context):
        scene = context.scene

        # Ensure the "Gradients and Curves" collection exists
        collection_name = "Gradients and Curves"
        if collection_name not in bpy.data.collections:
            new_collection = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(new_collection)
        else:
            new_collection = bpy.data.collections[collection_name]

        # Create the horcrux object if it doesn't exist
        if "horcrux" not in bpy.data.objects:
            bpy.ops.mesh.primitive_grid_add(x_subdivisions=10, y_subdivisions=10, size=2)
            horcrux_object = bpy.context.active_object
            horcrux_object.name = "horcrux"
            # Remove from the default collection and add to the custom collection
            for collection in horcrux_object.users_collection:
                collection.objects.unlink(horcrux_object)
            new_collection.objects.link(horcrux_object)
            bpy.context.view_layer.objects.active = horcrux_object
        else:
            # If a horcrux object already exists, manage its collections
            horcrux_object = bpy.data.objects["horcrux"]
            for collection in horcrux_object.users_collection:
                collection.objects.unlink(horcrux_object)
            new_collection.objects.link(horcrux_object)

        # Dynamically assign materials
        self.assign_material_to_object(horcrux_object, scene.color_ramp_manager.material_name)
        self.assign_material_to_object(horcrux_object, scene.color_ramp_manager.curve_material_name)

        # Update materials in the manager
        context.scene.color_ramp_manager.update_materials(context)
        
        # Optionally, exclude the new collection from the current view layer
        view_layer = context.view_layer
        layer_collection = view_layer.layer_collection.children.get(new_collection.name)
        if layer_collection:
            layer_collection.exclude = True

        self.report({'INFO'}, "Horcrux created successfully.")
        return {'FINISHED'}

    def assign_material_to_object(self, obj, material_name):
        """Helper function to assign a material to the object."""
        if material_name:
            if material_name not in bpy.data.materials:
                material = bpy.data.materials.new(name=material_name)
                material.use_nodes = True
            else:
                material = bpy.data.materials[material_name]
                material.use_nodes = True

            if obj.data.materials:
                if material not in obj.data.materials:
                    obj.data.materials.append(material)
                else:
                    obj.data.materials[0] = material
            else:
                obj.data.materials.append(material)


class G2C_OT_add_material(Operator):
    """Add a New Material to the Horcrux to Act as a New Category of Curve or Colorramp"""
    bl_idname = "object.add_material"
    bl_label = "Add Material"
    bl_description = "Add a new material to the horcrux object"

    def execute(self, context):
        scene = context.scene
        color_ramp_manager = scene.color_ramp_manager
        horcrux_object = get_active_horcrux(context)

        if horcrux_object:
            # Add or get the ramp material and assign it to the horcrux object
            self.assign_material_to_object(horcrux_object, color_ramp_manager.material_name) 
            # Add or get the curve material and assign it to the horcrux object
            self.assign_material_to_object(horcrux_object, color_ramp_manager.curve_material_name)

            # Update the materials in the color ramp manager
            color_ramp_manager.update_materials(context)

        return {'FINISHED'}

    def assign_material_to_object(self, obj, material_name):
        """Helper function to assign a material to the object."""
        if material_name:
            # Check if the material already exists in bpy.data.materials
            if material_name not in bpy.data.materials:
                # Create the material if it doesn't exist
                material = bpy.data.materials.new(name=material_name)
                material.use_nodes = True
            else:
                # Get the existing material
                material = bpy.data.materials[material_name]
                material.use_nodes = True

            # Add the material to the object if it isn't already present
            if material.name not in obj.data.materials:
                obj.data.materials.append(material)


class G2C_OT_add_color_ramp(Operator):
    """Add a New Color Ramp Node to the Horcrux Color Ramp Category Material"""
    bl_idname = "material.add_color_ramp"
    bl_label = "Add Color Ramp"
    bl_description = "Add a new Color Ramp node to the selected material"

    def execute(self, context):
        scene = context.scene
        color_ramp_manager = scene.color_ramp_manager
        horcrux_object = get_active_horcrux(context)

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

class G2C_OT_add_rgb_curve(Operator):
    """Add a New RGB Curve Node to the Horcrux Material Category"""
    bl_idname = "material.add_rgb_curve"
    bl_label = "Add RGB Curve"
    bl_description = "Add a new RGB Curve node to the selected curve material"

    def execute(self, context):
        scene = context.scene
        color_ramp_manager = scene.color_ramp_manager
        horcrux_object = get_active_horcrux(context)

        if horcrux_object and horcrux_object.data.materials:
            material = bpy.data.materials.get(color_ramp_manager.selected_curve_material)
            if not material:
                self.report({'WARNING'}, "Selected curve material not found.")
                return {'CANCELLED'}

            print(f"Using material: {material.name}")

            if material.use_nodes:
                node_tree = material.node_tree
                rgb_curve_node = node_tree.nodes.new(type='ShaderNodeRGBCurve')
                rgb_curve_node.location = (0, 0)
                rgb_curve_node.name = f"{material.name}_Curve_{len(node_tree.nodes)-2}"
                
                print(f"Added RGB Curve node: {rgb_curve_node.name}")

                new_curve = color_ramp_manager.curve_list.add()
                new_curve.name = rgb_curve_node.name
                new_curve.locked = True
                new_curve.active = True

                for curve in color_ramp_manager.curve_list:
                    if curve.name != new_curve.name:
                        curve.active = False

                # Print updated node tree for debugging
                print("Updated nodes in the material's node tree:")
                for node in node_tree.nodes:
                    print(f"Node: {node.name}, Type: {node.type}")

        return {'FINISHED'}


class G2C_OT_remove_color_ramp(Operator):
    """Remove the Active Color Ramp specified via the Unlock Icon"""
    bl_idname = "material.remove_color_ramp"
    bl_label = "Remove Color Ramp"
    bl_description = "Remove the selected Color Ramp node from the selected material"

    def execute(self, context):
        scene = context.scene
        color_ramp_manager = scene.color_ramp_manager
        horcrux_object = get_active_horcrux(context)
        ramp_list = color_ramp_manager.ramp_list

        if horcrux_object and horcrux_object.data.materials:
            material = bpy.data.materials.get(color_ramp_manager.selected_material)

            if material and material.use_nodes:
                node_tree = material.node_tree

                active_ramp = None
                for ramp in ramp_list:
                    if ramp.active:
                        active_ramp = ramp
                        break

                if active_ramp and active_ramp.name in node_tree.nodes:
                    node_tree.nodes.remove(node_tree.nodes[active_ramp.name])
                    ramp_list.remove(ramp_list.find(active_ramp.name))

        return {'FINISHED'}

class G2C_OT_remove_rgb_curve(Operator):
    """Remove the Active RGB Curve specified via the Unlock Icon"""
    bl_idname = "material.remove_rgb_curve"
    bl_label = "Remove RGB Curve"
    bl_description = "Remove the selected RGB Curve node from the selected curve material"

    def execute(self, context):
        scene = context.scene
        color_ramp_manager = scene.color_ramp_manager
        horcrux_object = get_active_horcrux(context)
        curve_list = color_ramp_manager.curve_list

        if horcrux_object and horcrux_object.data.materials:
            material = bpy.data.materials.get(color_ramp_manager.selected_curve_material)

            if material and material.use_nodes:
                node_tree = material.node_tree

                active_curve = None
                for curve in curve_list:
                    if curve.active:
                        active_curve = curve
                        break

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

class G2C_OT_copy_color_ramp_to_brush(Operator):
    """Copy the Active Color Ramp to the Active Brush Gradient Color"""
    bl_idname = "object.copy_color_ramp_to_brush"
    bl_label = "Copy Color Ramp to Brush"

    def execute(self, context):
        color_ramp_node = get_active_color_ramp(context)
        if not color_ramp_node:
            self.report({'WARNING'}, "No active Color Ramp found in the selected horcrux object.")
            return {'CANCELLED'}
        
        brush = context.tool_settings.image_paint.brush

        if brush and color_ramp_node:
            brush.color_type = 'GRADIENT'
            brush_gradient = brush.gradient

            # Correctly access the elements through the color_ramp property
            new_elements = [(elem.position, elem.color) for elem in color_ramp_node.color_ramp.elements]

            while len(brush_gradient.elements) < len(new_elements):
                brush_gradient.elements.new(position=0)

            for i, (pos, color) in enumerate(new_elements):
                brush_gradient.elements[i].position = pos
                brush_gradient.elements[i].color = color

            while len(brush_gradient.elements) > len(new_elements):
                brush_gradient.elements.remove(brush_gradient.elements[-1])

            self.report({'INFO'}, "Color ramp copied to brush gradient.")
        else:
            if not color_ramp_node:
                self.report({'WARNING'}, "Active color ramp not found.")
            if not brush:
                self.report({'WARNING'}, "Active brush not found.")

        return {'FINISHED'}


class G2C_OT_CopyBrushGradientToColorRamp(Operator):
    """Copy Brush Gradient to Color Ramp Node"""
    bl_idname = "paint.copy_brush_gradient_to_color_ramp"
    bl_label = "Copy Brush Gradient to Color Ramp"
    
    def execute(self, context):
        color_ramp_node = copy_brush_gradient_to_color_ramp(context)
        if not color_ramp_node:
            self.report({'WARNING'}, "Failed to copy brush gradient to color ramp.")
            return {'CANCELLED'}
        
        self.report({'INFO'}, "Brush gradient copied to color ramp node successfully.")
        return {'FINISHED'}


class G2C_OT_CopyBrushFalloffToRGBCurve(Operator):
    """Copy Brush Falloff Curve to RGB Curve Node"""
    bl_idname = "paint.copy_brush_falloff_to_rgb_curve"
    bl_label = "Copy Brush Falloff to RGB Curve"
    
    def execute(self, context):
        rgb_curve_node = copy_brush_falloff_to_rgb_curve(context)
        if not rgb_curve_node:
            self.report({'WARNING'}, "Failed to copy brush falloff to RGB curve.")
            return {'CANCELLED'}
        
        self.report({'INFO'}, "Brush falloff curve copied to RGB curve node successfully.")
        return {'FINISHED'}



class G2C_PT_horcrux_manager(Panel):
    """UI for the Gradient and Falloff Manager"""
    bl_idname = "G2C_PT_horcrux_manager"
    bl_label = "Gradient and Falloff Manager"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Paint'

    def draw(self, context):
        layout = self.layout
        color_ramp_manager = context.scene.color_ramp_manager

        # Dropdown to select the horcrux object
        layout = self.layout
        split = layout.split(factor=0.5)

        col = split.column()
        col.label(text="Active Horcrux", icon='DOCUMENTS')

        col = split.column()
        col.prop(color_ramp_manager, "selected_horcrux", text="")
        
        # The selected horcrux object
        horcrux_object = bpy.data.objects.get(color_ramp_manager.selected_horcrux)
        
        # Show the "Create Horcrux" button regardless of whether a horcrux is selected
        layout.operator("object.create_horcrux", text="Create Horcrux", icon='NEWFOLDER')
        
        if horcrux_object:
            layout = self.layout
            split = layout.split(factor=0.525)

            col = split.column()
            col.label(text="Gradient Category", icon='NODE_TEXTURE')

            col = split.column()
            col.prop(color_ramp_manager, "material_name", text="")
            
            layout = self.layout
            split = layout.split(factor=0.525)

            col = split.column()
            col.label(text="Falloff Category", icon='RNDCURVE')

            col = split.column()
            col.prop(color_ramp_manager, "curve_material_name", text="")
            
            row=layout.row()    
            row.operator("object.add_material", text="Add Categories", icon='LINENUMBERS_ON')
            row.operator(G2C_OT_GetColorRampPalette.bl_idname, text="Extract Palette", icon='EYEDROPPER')

            # Dropdowns to select the materials
            if horcrux_object.data.materials:
                
                layout = self.layout
                split = layout.split(factor=0.4)

                col = split.column()
                col.label(text="Display", icon='NODE_TEXTURE')

                col = split.column()
                col.prop(color_ramp_manager, "selected_material", text="")

                layout = self.layout
                split = layout.split(factor=0.4)

                col = split.column()
                col.label(text="Display", icon='RNDCURVE')

                col = split.column()
                col.prop(color_ramp_manager, "selected_curve_material", text="")
                
                row = layout.row()
                row.label(text="Gradient Add/Remove")
                row.operator("material.add_color_ramp", text="", icon='PLUS')
                row.operator("material.remove_color_ramp", text="", icon='TRASH')

                row = layout.row()
                row.label(text="Falloff Add/Remove")
                row.operator("material.add_rgb_curve", text="", icon='PLUS')
                row.operator("material.remove_rgb_curve", text="", icon='TRASH')

                # Show color ramps
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
                                row.operator(G2C_OT_copy_color_ramp_to_brush.bl_idname, text="", icon='BRUSH_DATA')
                                row.operator(G2C_OT_CopyBrushGradientToColorRamp.bl_idname, text="", icon='IMPORT')
                                
                                box.template_color_ramp(color_ramp_node, "color_ramp", expand=True)
                    else:
                        layout.label(text="No Color Ramps Added", icon='INFO')

                # Show RGB curves
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
                                row.operator(G2C_OT_CopyRGBCurveToBrushFalloff.bl_idname, text="", icon='BRUSH_DATA')
                                row.operator(G2C_OT_CopyBrushFalloffToRGBCurve.bl_idname, text="", icon='IMPORT')
                                row.operator(G2C_OT_CopyRGBCurveToCavityMask.bl_idname, text="", icon='SCREEN_BACK')
                                
                                box.template_curve_mapping(data=rgb_curve_node, property="mapping", type='COLOR')
                    else:
                        layout.label(text="No RGB Curves Added", icon='INFO')

            else:
                layout.label(text="No materials found on the selected horcrux.", icon='INFO')

        else:
            layout.label(text="No horcrux object selected", icon='ERROR')


class G2C_AddColorToPalette(Operator):
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

        # Use the actual ColorRamp node's name, not the palette name
        color_ramp_node_name = context.scene.color_ramp_palette.color_ramp_name.replace("_Palette", "")
        node_tree = material.node_tree
        color_ramp_node = node_tree.nodes.get(color_ramp_node_name)

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

class G2C_OT_GenerateGradientFromPalette(Operator):
    """Generate Gradient in Active Brush from Active Palette"""
    bl_idname = "brush.generate_gradient_from_palette"
    bl_label = "Generate Gradient from Palette"
    bl_description = "Create a gradient in the active brush based on the active color palette"

    def execute(self, context):
        brush = context.tool_settings.image_paint.brush
        
        if not brush:
            self.report({'WARNING'}, "No active brush found.")
            return {'CANCELLED'}

        # Access the active palette from the scene or tool settings
        palette = context.tool_settings.image_paint.palette
        if not palette:
            palette = context.scene.tool_settings.palette
        if not palette:
            self.report({'WARNING'}, "No active palette found.")
            return {'CANCELLED'}

        # Retrieve the gradient from the brush
        brush_gradient = brush.gradient
        
        # Get the number of colors in the palette
        num_colors = len(palette.colors)
        if num_colors == 0:
            self.report({'WARNING'}, "No colors in the active palette.")
            return {'CANCELLED'}

        # Ensure there are enough gradient points, add new if necessary
        while len(brush_gradient.elements) < num_colors:
            brush_gradient.elements.new(0)

        # Update the existing gradient points with the palette colors
        for i, color in enumerate(palette.colors):
            position = i / (num_colors - 1) if num_colors > 1 else 0.5
            
            # Ensure the color has 4 components (RGBA)
            rgba_color = list(color.color)[:3] + [1.0]  # Add alpha = 1.0 if it's not present
            brush_gradient.elements[i].position = position
            brush_gradient.elements[i].color = rgba_color

        # If there are extra gradient points, remove them
        while len(brush_gradient.elements) > num_colors:
            brush_gradient.elements.remove(brush_gradient.elements[-1])

        self.report({'INFO'}, "Gradient created from the active palette.")
        return {'FINISHED'}


def draw_gradient_button(self, context):
    layout = self.layout
    settings = context.tool_settings.image_paint

    # Debugging print to check if the function is being called
    print("Attempting to draw the gradient button...")

    if settings and settings.palette:
        layout.operator("brush.generate_gradient_from_palette", text="Gradient from Palette")





### Register and Unregister Functions

def register():
    bpy.utils.register_class(RGBCurveItem)
    bpy.utils.register_class(ColorRampItem)
    bpy.utils.register_class(ColorRampManagerProperties)
    bpy.utils.register_class(ColorRampPalette)
    bpy.utils.register_class(G2C_OT_GetColorRampPalette)
    bpy.utils.register_class(G2C_OT_CopyRGBCurveToBrushFalloff)
    bpy.utils.register_class(G2C_OT_CopyRGBCurveToCavityMask)
    bpy.utils.register_class(G2C_OT_create_horcrux)
    bpy.utils.register_class(G2C_OT_add_material)
    bpy.utils.register_class(G2C_OT_add_color_ramp)
    bpy.utils.register_class(G2C_OT_add_rgb_curve)
    bpy.utils.register_class(G2C_OT_remove_color_ramp)
    bpy.utils.register_class(G2C_OT_remove_rgb_curve)
    bpy.utils.register_class(G2C_PT_horcrux_manager)
    bpy.utils.register_class(G2C_AddColorToPalette)
    bpy.utils.register_class(G2C_OT_copy_color_ramp_to_brush)
    bpy.utils.register_class(G2C_OT_CopyBrushGradientToColorRamp)
    bpy.utils.register_class(G2C_OT_CopyBrushFalloffToRGBCurve)
    bpy.utils.register_class(G2C_OT_GenerateGradientFromPalette)
    # Assuming we identified the correct panel, let's append the button there
    bpy.types.VIEW3D_PT_tools_brush_settings.append(draw_gradient_button)
    
    bpy.types.Scene.color_ramp_palette = PointerProperty(type=ColorRampPalette)
    bpy.types.Scene.color_ramp_manager = PointerProperty(type=ColorRampManagerProperties)
    

def unregister():
    bpy.utils.unregister_class(RGBCurveItem)
    bpy.utils.unregister_class(ColorRampItem)
    bpy.utils.unregister_class(ColorRampManagerProperties)
    bpy.utils.unregister_class(ColorRampPalette)
    bpy.utils.unregister_class(G2C_OT_GetColorRampPalette)
    bpy.utils.unregister_class(G2C_OT_CopyRGBCurveToBrushFalloff)
    bpy.utils.unregister_class(G2C_OT_CopyRGBCurveToCavityMask)
    bpy.utils.unregister_class(G2C_OT_create_horcrux)
    bpy.utils.unregister_class(G2C_OT_add_material)
    bpy.utils.unregister_class(G2C_OT_add_color_ramp)
    bpy.utils.unregister_class(G2C_OT_add_rgb_curve)
    bpy.utils.unregister_class(G2C_OT_remove_color_ramp)
    bpy.utils.unregister_class(G2C_OT_remove_rgb_curve)
    bpy.utils.unregister_class(G2C_PT_horcrux_manager)
    bpy.utils.unregister_class(G2C_AddColorToPalette)
    bpy.utils.unregister_class(G2C_OT_copy_color_ramp_to_brush)
    bpy.utils.unregister_class(G2C_OT_CopyBrushGradientToColorRamp)
    bpy.utils.unregister_class(G2C_OT_CopyBrushFalloffToRGBCurve)
    bpy.utils.unregister_class(G2C_OT_GenerateGradientFromPalette)
    bpy.types.IMAGE_PT_paint_stroke.remove(draw_gradient_button)
    # Remove the draw function from the existing ColorPalettePanel
    bpy.types.VIEW3D_PT_tools_brush_settings.remove(draw_gradient_button)
    
    del bpy.types.Scene.color_ramp_palette
    del bpy.types.Scene.color_ramp_manager

if __name__ == "__main__":
    register()
