# Face Shape Key Rig

A Blender add-on for animating faces on 3D characters, in two ways:

- **Sprite mode**: build a 2D face (eyes, brows, mouth, blush, effects) from
  sprite-sheet parts and draw it on a canvas that follows your 3D face mesh.
  Parts are laid out like Photoshop layers, keyed like any other property, and
  driven by presets, audio lipsync and viewport controllers.
- **Driver mode**: in-viewport slider and pad controllers for shape keys, with
  iFacialMocap capture.

Switch between the two at the top of the **Face Rig** tab. Both keep their data.

**Requires Blender 5.2 or newer.**
UI languages: English, 日本語, 中文, 한국어.

---

## Install

1. Download the latest release zip (or get it from Blender Extensions).
2. In Blender: `Edit → Preferences → Get Extensions → ▼ (top right) → Install from Disk…`
   and pick the zip. If an older version is installed, remove it first.
3. In the 3D Viewport, press **N** and open the **Face Rig** tab.

## Sprite mode at a glance

```
① Face canvas      Select the face area on your mesh → a canvas mesh is built
② Markers          Click anchor points (eyes, brows, mouth…) from the front
③ Sprite sheets    Load grid images and slice them into cells
④ Canvas layers    Add parts from cells, tag them, arrange and style them
⑤ Presets          Save layouts as expressions, apply them as keys
⑥ Mouth            Sequences (closed / half / open) and audio lipsync
   Gaze            Eye movement driven by a pad
   Controllers     Mouth, expression list and gaze pad in the viewport
```

The panels are split into tabs (Setup / Parts / Expressions / Mouth / Gaze /
Controllers), so you only see one stage at a time.

### ① Face canvas
- Set the **Face axis** first (Blender's front view is `-Y`).
- On the face mesh, enter Edit Mode, select the front faces (brows to chin),
  and press **Create face canvas**. Half meshes with a Mirror modifier are
  expanded automatically.
- The canvas follows the face's final shape (armature, shape keys) through
  Surface Deform and sits slightly above the skin. **Don't bind the canvas to
  your rig.** Bind only the face mesh; the canvas follows it.
- **Edit selection area** lets you grow or move the canvas area later.
- Several canvases per character are supported (e.g. a second face on a hat).
  Selecting a canvas in the viewport switches the panel to it.
- Extras: an **Emotion plane** for manga-style effects beyond the head,
  **Head flatten** for a flatter 2D look toward the camera, and
  **Export / Import** of a whole canvas (sheets at original resolution plus all
  settings) as a zip.

### ② Markers
Anchor points that parts are positioned against. Name them freely and click
them on the face from the front view.

### ③ Sprite sheets
Load a grid image and set rows and columns. Transparent-edge white fringes
(common with Clip Studio exports) are cleaned automatically.

### ④ Canvas layers
- **+** adds a part from a sheet cell. Parts are grouped with **tags** and
  stacked like layers, with 17 blend modes.
- Per part: cell, position, size, rotation, opacity, crop, flip, mirrored copy,
  pivot, hue/saturation/value, color overlay, color match, clipping mask,
  depth (parallax), and **Over hair** (stays visible through bangs).
- **Per-cell placement**: each cell of a part can have its own offset, size,
  rotation, opacity and crop. A batch-adjust panel edits several cells at once.
- **Parenting**: children follow the parent's position, rotation, scale,
  opacity, gaze, visibility and crop. Following the parent's HSV or color
  overlay is a per-child toggle (turn HSV off for highlights that must stay
  white). Assigning or clearing a parent keeps the drawing in place.
- **Folders**: switch between whole part setups (e.g. "Normal" / "Laughing").
  Each folder remembers its own cells, transforms and visibility.
- **Free transform (Ctrl+T)** in the viewport:

  | Input | Action |
  |---|---|
  | Drag inside the box | Move (**Shift** = horizontal / vertical / 45°) |
  | Drag a corner or edge | Scale from the opposite side (**Alt** = from pivot, **Shift** on corners = toggle aspect lock) |
  | Drag outside the box / the top handle | Rotate (**Shift** = 15° steps) |
  | Drag the white ⊕ | Move the pivot (snaps to corners, edge midpoints and center) |
  | Arrow keys | Nudge 1 px (**Shift** = 10 px) |
  | Ctrl+Z / Ctrl+Shift+Z | Undo / redo inside the transform |
  | Enter / ✓ · Esc / right-click / ✕ | Confirm · cancel |

  The view switches to front orthographic. Orbiting into perspective confirms
  the transform.
- **Keying**: *Key this part*, auto-key on change, and Constant / Linear /
  Spline interpolation stored per tag. *Edit mode* pins a cell while ignoring
  keyframes. Keys live on the rig object and show readable channel names in
  the Dope Sheet and Graph Editor.

### ⑤ Expression presets
Save the current layout as an expression and apply it as keys. Presets can be
edited in place and shown as a list controller in the viewport.

### ⑥ Mouth
- **Sequences**: closed / half / open steps from the mouth sheet, with per-step
  size and offset, and a *talk* slider.
- **Audio lipsync**: analyze a sound, then generate mouth keys.

### Gaze
A pad moves the eyes, with separate left/right and up/down ranges and a 3×3
preview grid. Each part has a follow multiplier (e.g. highlights moving a bit
more for parallax).

### Viewport controllers
Mouth sequence list with talk slider, expression list and gaze pad. Use layout
mode to move and resize them. Each canvas gets its own column.

## Driver mode

| Action | How |
|---|---|
| Move a controller | Select it in Pose Mode, then **G** |
| Edit type / keys / label | Pencil icon |
| Create the opposite side | Mirror icon |
| Free layout | Layout mode ON → G / R / S (**Ctrl** while moving = snap to edges) |
| Pad range −1 … 1 | Put the same key on up and down |
| Two-way slider | Use a negative minimum (center = 0) |
| Bone pad | The handle's XY moves a bone (e.g. an eye target) |
| Move the whole panel | Move the `FP_root` bone, or set a follow bone in Settings |

**iFacialMocap**: receives capture data over local Wi-Fi (UDP 49983).

## Other tools
- **CJK input window**: when Blender's text fields can't compose Korean,
  Japanese or Chinese, a small input window opens instead (right-click a field,
  or Ctrl+Shift+Space over it).
- **Performance profiler**: writes `fskr_perf.txt` next to the blend file to
  find what slows the viewport.

## Troubleshooting
- **Eyes or mouth distort when the head turns**: some face vertices probably
  have no weights. In Edit Mode on the face mesh:
  `Select → Select All by Trait → Ungrouped Verts`, then assign them to the head
  bone with weight 1.0.
- **Skin shows through the canvas at grazing angles**: raise *Lift from face*
  under the canvas name, and keep the `FSKR_Canvas_Wrap` modifier visible in
  the viewport.
- **The canvas got its own weights after rigging**: press *Re-attach to face
  motion* (shown in red) under the canvas name.

## Permissions
- **Network**: iFacialMocap over local Wi-Fi, and a localhost-only server for
  the lipsync editor and CJK input windows.
- **Files**: canvas export / import and loading sprite sheet images.

## Support
Bug reports and requests: [Issues](https://github.com/Fragid/face-shapekey-rig/issues).
See [CHANGELOG.md](CHANGELOG.md) for release notes.

## License
GPL-3.0-or-later. See [LICENSE](LICENSE).
