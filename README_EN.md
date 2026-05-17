<div align="center">
  <img src="https://github.com/MoLeiVFX/AxisGradientMaskTool/blob/main/IMG/AxisGradientMaskTool_Light.png" width="80%">
</div>

<div align="center">

# Axis Gradient Mask Tool User Manual

</div>

- [中文](./README.md) | English

## Table of Contents

1. [Plugin Introduction](#plugin-introduction)
2. [Installation and Activation](#installation-and-activation)
3. [Interface Guide](#interface-guide)
   - [Gradient Direction](#gradient-direction)
   - [Output Resolution](#output-resolution)
   - [Precision Settings](#precision-settings)
   - [Export Settings](#export-settings)
   - [Action Buttons](#action-buttons)
   - [Version Information](#version-information)
4. [Usage Workflow](#usage-workflow)
5. [Frequently Asked Questions](#frequently-asked-questions)
6. [Technical Support](#technical-support)

---

## Plugin Introduction

**Axis Gradient Mask Tool** is a Blender add-on for generating axis-based gradient masks. It creates a black-to-white gradient from the selected object's **world-space** position along the X, Y, or Z axis, lets you preview the result directly in the viewport, then bakes the gradient to the object's UVs and exports it as a PNG mask image.

It is useful for directional dissolve masks, top-to-bottom height masks, left-to-right scan masks, environment height masks, and local transition masks for real-time materials or offline rendering.

### Key Features

- ✅ Generate gradient masks along the X, Y, or Z world axis
- ✅ Invert the black/white gradient direction with one toggle
- ✅ Adjust black/white points, colors, and interpolation through Blender's ColorRamp
- ✅ Preview the current gradient mask material in the 3D viewport
- ✅ Bake the gradient result to UVs and export it as a PNG image
- ✅ Customize output resolution from 64 to 16384 pixels
- ✅ Export 8-bit or 16-bit PNG masks
- ✅ Use float buffer and anti-aliasing for smoother gradients
- ✅ Customize export file name and save directory

---

## Installation and Activation

### Installation Steps

1. Download the add-on package, for example `AxisGradientMaskTool-v1.0.0.zip`
2. Open Blender and go to `Edit` > `Preferences` > `Add-ons`
3. Click `Install...`
4. Select the add-on ZIP file
5. Search for **Axis Gradient Mask Tool** in the add-on list
6. Enable the add-on by checking the box next to its name

### Accessing the Add-on

After enabling the add-on, press `N` in the 3D Viewport to open the right sidebar, then switch to the **AGMT** tab. The panel is named **Axis Gradient Mask Tool**.

> Version note: regular add-on installation supports Blender 3.6+. For Blender 4.2+ extension packages, follow `blender_manifest.toml`.

---

## Interface Guide

### Gradient Direction

This section controls the world axis used for the mask and the visible gradient appearance.

#### Axis

- **Function**: Selects the world-space axis used to calculate the gradient
- **Options**:
  - **X Axis**: Generates the gradient along the X axis
  - **Y Axis**: Generates the gradient along the Y axis
  - **Z Axis**: Generates the gradient along the Z axis, commonly used for bottom-to-top height masks
- **Default**: Z Axis

#### Invert Black/White Gradient

- **Function**: Reverses the black/white direction of the selected axis
- **Example**: A bottom-black/top-white gradient becomes bottom-white/top-black

#### Gradient Color Ramp

- **Function**: Adjusts the black/white positions, colors, and interpolation
- **Description**:
  - Click **Preview Current Mask** first to create the gradient material node for the selected object
  - Once created, the ColorRamp appears in the panel and can be edited directly
  - The ColorRamp settings are preserved and reused for previewing and exporting

---

### Output Resolution

This section controls the pixel size of the exported mask image.

#### Width / Height

- **Function**: Sets the exported PNG resolution
- **Default**: 512 x 512
- **Range**: 64 to 16384
- **Usage Tips**:
  - Use 512 or 1024 for typical real-time projects
  - Use 2048 or 4096 when the UV bake needs more detail
  - Higher resolution increases bake time and file size

---

### Precision Settings

This section controls bake quality, color precision, and gradient smoothness.

#### Color Depth

- **Function**: Sets the exported PNG color depth
- **Options**:
  - **8-bit (256 levels)**: Standard PNG, smaller file size, suitable for most masks
  - **16-bit (65536 levels)**: Smoother gradients, useful when banding must be avoided
- **Default**: 8-bit

#### Bake Samples

- **Function**: Sets the Cycles bake sample count
- **Default**: 16
- **Range**: 16 to 4096
- **Usage Tips**:
  - For simple gradient masks, 16 or 32 samples are usually enough
  - Increase samples if complex UV areas or edges show artifacts

#### Use Float Buffer

- **Function**: Creates the bake image with a float buffer for smoother gradient data
- **Default**: Enabled
- **Usage Tips**: Keep it enabled, especially when exporting 16-bit masks

#### Enable Anti-Aliasing

- **Function**: Enables bake anti-aliasing for smoother UV edges and transitions
- **Default**: Enabled

---

### Export Settings

This section controls the file name and save location.

#### File Name

- **Function**: Sets a custom export file name without the `.png` extension
- **Default**: Empty
- **Description**:
  - If left empty, the add-on uses the default name: `ObjectName_AxisGradientMask.png`
  - Invalid file-name characters are automatically replaced with `_`

#### Save Location

- **Function**: Sets the save directory for the mask image
- **Default**: Empty
- **Description**:
  - If the current Blender file is saved, an empty path exports to the `.blend` file directory
  - If the current Blender file has not been saved, an empty path exports to the user home directory
  - If a full file path is provided and it does not end with `.png`, the add-on appends `.png`

---

### Action Buttons

#### Preview Current Mask

- **Function**: Creates or updates the gradient material on the selected mesh object and switches the viewport to material preview
- **Prerequisite**: A mesh object must be selected
- **Description**:
  - The add-on builds a material node setup from the current axis, invert state, and ColorRamp
  - Preview fails with an error if the model has no vertices
  - The generated gradient material is placed in the object's first material slot

#### Generate and Export Mask

- **Function**: Generates the gradient material, bakes it to UVs, and exports the result as a PNG
- **Prerequisites**:
  - A mesh object must be selected
  - The model must have a UV layer
- **Description**:
  - The add-on temporarily switches to Cycles and uses Emit baking
  - After baking, it saves the PNG file to the configured location
  - When finished, it restores the original render engine, sample count, denoising state, active object, and selection state

---

### Version Information

The bottom of the panel displays add-on version and author information.

- **Add-on Version**: v1.0
- **Author**: MoLei
- **Website**: https://www.kiiiii.com

---

## Usage Workflow

### Quick Start

1. Select a mesh object that already has UVs
2. Press `N` in the 3D Viewport to open the right sidebar
3. Open the **AGMT** tab
4. Choose X, Y, or Z in **Gradient Direction**
5. Enable or disable **Invert Black/White Gradient** as needed
6. Click **Preview Current Mask**
7. Fine-tune the black/white positions or colors in **Gradient Color Ramp**
8. Set output resolution, color depth, bake samples, and save location
9. Click **Generate and Export Mask**
10. Check the exported PNG mask in the save directory

### Recommended Workflow

Start with a 512 resolution and the default sample count for the first preview. Check the selected X / Y / Z direction and the black-white relationship before spending time on higher-quality exports. If the direction is reversed, toggle **Invert Black/White Gradient** first.

Once the direction is correct, adjust the ColorRamp to shape the transition. Move the two stops closer for a harder edge, or keep a wider range for a softer height-style mask.

Raise the resolution and color depth only for the final export. Use 16-bit when the mask will be pushed with contrast in a material; 8-bit is enough for quick previews and simpler masks.

---

## Frequently Asked Questions

### Q1: Why are the buttons disabled?

Make sure the active selection is a mesh object. The add-on only processes `MESH` objects, so curves, lights, cameras, and other object types will disable the preview and export buttons.

### Q2: Why do I get “This model has no UV layer” when exporting?

Exporting requires baking the gradient result to UVs. Unwrap the model first, then click **Generate and Export Mask** again.

### Q3: Why can't I see the ColorRamp control?

Click **Preview Current Mask** first. The add-on creates a `GradientMask_ColorRamp` node, and then the editable ColorRamp appears in the panel.

### Q4: Why is the exported mask direction wrong?

Check these settings:

- Whether the selected axis is correct, for example Z is usually used for height masks
- Whether **Invert Black/White Gradient** should be enabled
- Whether the object's world position and scale are what you expect
- Whether the ColorRamp was adjusted after previewing

### Q5: Should I use 8-bit or 16-bit?

Use 8-bit for most regular black-and-white masks. Use 16-bit if the gradient covers a wide area, if you plan to increase contrast later, or if visible banding appears.

### Q6: Should I keep Float Buffer enabled?

Yes, it is recommended. It improves precision during the bake image calculation stage and is especially useful for smooth gradients.

### Q7: Where is the exported file saved?

If **Save Location** is set, the image is saved there. If it is empty and the `.blend` file is saved, the image is saved next to the current Blender file. If the `.blend` file is unsaved, the image is saved to the user home directory.

### Q8: Does the add-on modify my material?

During preview and export, the add-on creates or reuses a material named `GradientMask_Material_ObjectName` and places it in the object's first material slot. If you need to preserve the original material, duplicate the object or back it up before baking.

---

## Technical Support

For questions or suggestions, please visit:

- **Website**: https://www.kiiiii.com
- **Author**: MoLei_VFX

---

**Document Version**: 1.0  
**Last Updated**: 2026  
**Add-on Version**: v1.0.0
