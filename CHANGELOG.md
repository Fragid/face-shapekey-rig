# Changelog

## v1.0.225

### Fixed
- Selecting everything in Pose Mode and pressing **Alt+R / Alt+G / Alt+S** to
  reset the body pose also reset the Face Rig controllers. The panel layout
  fell apart, and the expression list handle jumped to the first item and
  applied that expression, throwing parts out of place. Controllers (`FP_…`
  bones) selected together with character bones are now left untouched.
  Selecting only controllers still clears them as usual.

## v1.0.224

### Fixed
- In Sprite mode the panel and viewport controllers could be left behind when
  the character moved. **Follow character** is now also in the Controllers tab
  (Viewport controllers box). Turning it on fills in the current rig and its
  root bone automatically (`c_pos` for Auto-Rig Pro, `root` for Rigify) and
  keeps the current relative position.

## v1.0.223

> 🎬 **Demo video:** https://youtu.be/tEcgZZRDbjc
>
> **Requires Blender 5.2 or newer.**
>
> This is a large update since v1.0.42. The headline is the new **Sprite mode**:
> a 2D face built from sprite-sheet parts, drawn on a canvas that follows your
> 3D face mesh. The shape-key **Driver mode** is still there; switch between the
> two at the top of the Face Rig tab. Your data for both modes is kept.

### New — Sprite mode
- **Face canvas**: pick the eye/mouth area on your face mesh and the add-on
  builds a separate canvas mesh that follows the face's final shape (armature,
  shape keys) through Surface Deform. No extra weights or binding needed.
  Use **Edit selection area** later to grow or move the area.
- **Multiple canvases per character** (e.g. a second face on a hat). Selecting
  a canvas in the viewport switches the N-panel to it automatically.
- **Position markers**: click on the face from the front to place anchor points
  (eyes, brows, mouth…) that parts are positioned against.
- **Sprite sheets**: load a grid image and slice it into cells. Transparent-edge
  white fringes from Clip Studio and similar apps are cleaned automatically.
- **Canvas layers**, like a Photoshop layer panel: add parts from sheet cells,
  group them with tags, reorder, duplicate, hide, and choose from 17 blend modes.
  - Per part: position, size, rotation, opacity, crop, flip, mirrored copy,
    pivot (marker or part center), hue/saturation/value, color overlay,
    clipping mask, depth (parallax), and **Over hair** (stays visible through
    bangs, with its own opacity).
  - **Per-cell placement**: every cell of a part can have its own offset, size,
    rotation, opacity and crop, with a batch-adjust panel.
  - **Parenting**: children follow the parent's position, rotation, scale,
    opacity, gaze, visibility and crop. Following the parent's HSV and color
    overlay can be toggled per child. Assigning or clearing a parent keeps the
    drawing in place.
  - **Part folders**: switch between whole part setups (e.g. "Normal" and
    "Laughing"). Each folder remembers its own cells, transforms and visibility.
  - **Free transform (Ctrl+T)** in the viewport, like Photoshop: move, scale and
    rotate with handles. Drag the pivot, use arrow keys to nudge, Shift to snap
    45° / 15°, and undo/redo inside the transform.
  - **Color match**: pick a source and target color and the add-on computes
    the HSV shift for you.
  - Keying: **Key this part**, auto-key on change, and Constant / Linear /
    Spline interpolation stored per tag. Edit mode lets you pin a cell while
    ignoring keyframes. Channels have readable names in the Dope Sheet and
    Graph Editor.
- **Expression presets**: save the current layout as an expression and apply
  it as keys. Edit presets in place.
- **Mouth**: sequences (closed / half / open) with per-step size and offset,
  plus **audio lipsync** (analyze, then generate keys).
- **Gaze**: eye movement with separate left/right and up/down ranges, a 3×3
  preview grid, and a per-part follow multiplier (e.g. highlights moving a bit
  more for parallax).
- **Viewport controllers**: mouth sequence list with talk slider, expression
  list, and gaze pad. They have a layout mode for moving and resizing, and
  stack per canvas without overlapping.
- **Emotion plane**: a separate billboard plane for manga-style effects (sweat,
  anger marks) that can extend beyond the head.
- **Head flatten**: flattens the head toward the camera for a 2D look, driven
  from rig properties.
- **Canvas export / import**: save a canvas with its sprite sheets (at original
  resolution) and all settings to a zip, then load it onto another canvas.
- **CJK input window**: a small input window for Korean / Japanese / Chinese
  when Blender's text fields can't compose them (right-click a field or press
  Ctrl+Shift+Space).
- **Performance profiler** that writes `fskr_perf.txt` next to the blend file
  to find what is slowing the viewport.

### Changed
- The whole UI, including tooltips, messages, dropdowns and viewport help, is
  now translated into **English, Japanese and Chinese**. User-named parts and
  tags are left as-is.
- Sprite-mode panels are split into tabs (Setup / Parts / Expressions / Mouth /
  Gaze / Controllers) to cut down scrolling.
- Mouth step size and offset now scale the whole part instead of zooming inside
  the cell, so going above 100% no longer clips at the cell edge.

### Fixed
- Viewport stutter while orbiting when "Over hair" parts were present.
- Skin showing through the canvas as stripes at grazing angles. The surface
  offset is now in real distance and is migrated on load.
- Mirrored copies only updating one side when per-cell values changed.
- Text appearing twice (Korean and English) after updating, or when two copies
  of the add-on were enabled. A warning with a **Disable** button is shown now.
- Relative image paths failing when picking a sheet from disk.
- Re-selecting the same rig (or picking a rig for the first time) no longer
  brings back the settings saved inside the rig at the last save. Clearing
  everything and picking the rig again now really starts empty. Switching
  between different characters still restores each one's own settings.
- A Python error ("the return value must be None") when toggling a mouth
  sequence's single-mouth option or restoring settings that include it.

### Upgrading from older versions
- Files are migrated automatically on open and look the same as before.
- Parented parts now inherit rotation, scale, opacity and HSV as well as
  position. If a parent has keyframes on those, its children will now follow
  them too.
- Files saved with this version and opened in an older version may show
  children not following a rotated or scaled parent.

## v1.0.42

### New
- **Panel position (grab bar)** in Settings: read and edit the panel root's
  X/Y/Z directly, and turn on **Follow character** to pick a bone (usually the
  head) so the panel keeps its position beside the character as it moves. It
  follows position only, so the panel never tilts. A **Pin at current position**
  button re-binds if things ever drift.
- **Playback audio (Spacebar)**: choose which sound you hear when playing back
  in Blender — any sequencer strip or speaker in the scene. Only the chosen one
  plays; everything else is muted automatically, and switching back to "none"
  restores just what this muted. Volume, mute and start frame are adjusted here
  without touching the lipsync analysis audio.

### Fixed
- Attaching the panel to a bone no longer throws it off to a wrong position;
  the current position is now measured and preserved exactly, like Child Of's
  Set Inverse.
- With several characters in one file, working on one no longer reverts to the
  previous character's lipsync clusters. Character auto-switching now only
  reacts to an actual selection change, never while the lipsync editor is open,
  and picking a rig from the dropdown properly switches its presets, mocap and
  lipsync too.
- The mute / unmute icons were the wrong way round.
- Removed the duplicate "attach to bone" button next to Set Panel Position.
