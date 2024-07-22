# Gradient2ColorRamp
Hacky way to manage gradients for Paint via Compositor Color Ramps displayed in 3d View N Panel

*Add Color Ramp*
This will add a new Color Ramp in the Compositor, and any changes you make in the Gradient2ColorRamp panel will affect it.
To use the Color Ramp, hover over it and press Ctrl-C to copy, then hover over the tool panel brush using Gradient and press Ctrl-V.

This is a hack because the Paint Brushes share a single Gradient to use, so we are storing our options in the Compositor.

*Remove Color Ramp*
To remove, first please click the lock above the color ramp you want to delete, then press Remove Color Ramp and the color ramp will 
delete from the the panel and the Compositor. What I prefer to do is make a few and if one isn't needed, change it. 

I want to add this to Draw2Paint as is, but still need to figure out if the process of tagging the name will allow me to circumvent the 
already existing clearance of the compositor when using the Flattener option in the Compositor.


![main_view_panel_to_tool](https://github.com/user-attachments/assets/e9d0cc2a-623d-457d-84fd-e43e8aa2540a)
![compositor](https://github.com/user-attachments/assets/647c2196-a2b0-4f9b-ae39-967472869f86)
