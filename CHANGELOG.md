# Changelog

## v1.0.244

### Fixed
- Moving a mesh part past the edge of the face canvas pulled the outside
  points into a single spot, stretching the drawing like a black hole. Points
  that fall outside the canvas UV are now removed, so the drawing is simply
  cut at the canvas edge. Existing files are upgraded in place when the
  canvas rebuilds.

## v1.0.243

### Fixed
- Mirror-side bones (including the part root controller) could not be
  selected, because they lived in a second armature that wasn't in Pose Mode.
  Mirror bones now live in the same armature with a `.R` suffix. The mirror
  mesh is a copy of the original whose vertex groups point at the `.R` bones,
  and it re-syncs automatically after Edit Mode or weight painting on the
  original. "Create Mirror Mesh" converts parts made with v1.0.241–242.

## v1.0.242

### Fixed
- Auto weights fell off too sharply (1/d³), so large pin moves tore the
  drawing between pins. Weights now use 1/d² and are smoothed between bones
  after each recalculation. Press "Auto Weights" once on parts made earlier.

## v1.0.241

### Added
- Symmetric mesh parts: converting a part with symmetry copy now also creates
  the opposite-side mesh (sharing mesh data and weights) and a mirrored bone
  set in a second armature with the same bone names. Pins, IK, mesh edits
  and weights are done once on the original side.
- Mirror / Separate control per part (keyable rig property `<Part>_MirrorPose`):
  the copy side bones mirror the original bones, or move independently.
  Switching to Separate copies the current mirrored pose so nothing jumps.
- "Create Mirror Mesh" converts symmetric mesh parts made before this version.

## v1.0.240

### Added
- Mesh Edit locks the view to an orthographic front view of the mesh plane
  and turns on X-Ray so hidden points are visible. Rotating the view or
  switching to perspective ends Edit Mode and restores X-Ray.
- Chained pins (Shift+click) show an orange arrow from the parent pin to the
  child pin.
- Smooth Weights: blends weights between neighboring points (strength and
  repeat adjustable), normalized per point.

## v1.0.239

### Fixed
- Right after "Convert to Mesh" the part stayed behind the canvas in the
  viewport until something else forced a refresh. Changing a mesh part's
  depth now tags it for update immediately.

### Changed
- Puppet bones use their own shapes so they don't look like the character
  rig: pins are yellow rings, part roots are blue squares with a cross, IK
  controllers are red diamonds. Shapes keep a fixed size along pin chains.

## v1.0.238

### Fixed
- Mesh parts were sent behind the whole canvas whenever any canvas part sat
  above them in the list, so an eyelid ended up behind the eye white. Depth
  is now chosen by overlap: in front if the mesh part overlaps a canvas part
  below it, behind if it only overlaps parts above. A per-part
  Auto / In Front / Behind option overrides it.
- Mesh parts ignored the color overlay (and parent HSV / overlay), so they
  rendered in the wrong color. They now use the same chain as the canvas and
  update live from the panel.
- Pin placement gave no feedback. The tool now shows a status bar, help text
  and a crosshair cursor, and marks existing pins.

## v1.0.237

### Added
- Mesh Parts (experimental), in the style of Spine / Live2D: convert a part
  into a real mesh object that sticks to the face canvas (follows shape keys
  and head motion via Sample UV Surface).
  - A triangle mesh is generated where the drawing is; edit it freely in
    Edit Mode (new points get the right drawing position automatically).
  - Place pins in the viewport; each pin is a bone in one puppet armature
    per canvas. Shift+click chains pins. Weights are computed from distance
    and can be painted in Weight Paint mode.
  - Create IK controllers for pin chains (Blender IK constraint).
  - Cell switching, keyable opacity / visibility and symmetry copy carry
    over. Mesh parts sit behind the canvas when canvas parts are above them
    in the list, otherwise in front.

### Changed
- The shader-based Puppet Pins from v1.0.236 are replaced by Mesh Parts.

## v1.0.236

### Changed
- Warp Shape (3×3 numeric grid) is replaced by Puppet Pins (experimental),
  modeled on After Effects' Puppet Pin tool.

### Added
- Puppet Pin tool in the viewport: click the drawing to place a pin, drag
  pins to bend it, Shift-click to select several, X/Delete to remove,
  Ctrl+Z to undo inside the tool. Up to 8 pins per part.
- Pin offsets are keyable rig properties (`<Part>_Pin1_X`, …) and are saved
  in keys, expression presets and part folders. Change frames with the arrow
  keys while the tool is open and press I (or use auto key) to animate.
- Deformation is rigid moving least squares computed in the shader, so the
  drawing bends and rotates between pins without stretching. Moving pins only
  updates driver values; the material is not rebuilt.
- With Puppet Pins off, the material is identical to v1.0.234.

## v1.0.235

### Added
- Warp Shape (experimental): bend a part's drawing with a 3×3 grid, similar
  to a Live2D warp deformer. Turn it on in the part's placement box, enter
  X/Y offsets for the 9 grid points, and drive the amount with the keyable
  rig property `<Part>_Warp` (0–1). The amount is saved in keys, expression
  presets and part folders.
- The grid works in on-screen part space: flipping keeps the bend, symmetry
  copies bend as a mirror, and crop follows the bent drawing.
- Editing the grid only rewrites driver expressions; the material is not
  rebuilt. An inverse-error readout and a fold-over warning are shown.
- With Warp Shape off, the material is identical to v1.0.234; with the
  amount at 0, renders match pixel for pixel.

## v1.0.234

### Fixed
- Viewport controller text (titles and list labels) showed up in renders.
  Controller labels are now hidden from rendering; existing files are fixed
  when opened.

## v1.0.233

### Fixed
- Expressions keyed on the timeline did not change during playback. Preset
  editing mutes the add-on's channels while you edit, and ending the edit
  could leave them muted, so the expression number and all part values
  ignored their keys. Ending a preset edit now unmutes all add-on channels,
  even when a save fails. Files with channels left muted are repaired
  automatically when opened.
- Only location / rotation / scale keys on the expression handle are turned
  into expression keys; other keys on the handle are left alone.

## v1.0.232

### Fixed
- Keys put on the expression list handle at frames other than the current one
  only keyed the expression number, so the parts did not change there. Each
  handle key now becomes a full expression key (number + all part values) at
  its own frame.
- With several canvases, only the canvas shown in the N-panel had a working
  expression handle. All canvases' handles now sync.

## v1.0.231

### Fixed
- Keys on viewport controller handles could silently fail when Blender's
  **Only Insert Available** preference was on ("Could not create F-Curves"),
  so moving a handle and keying it did nothing on playback. The controller
  boxes now show a warning with a **Turn off Only Insert Available** button.
  Keys the add-on inserts itself are never blocked by Only Insert Available /
  Only Insert Needed.

## v1.0.230

### Changed
- **Symmetry copy is now a keyable rig property** (`<part>_Mirror`, always
  Constant). It is keyed and saved in expression presets and part folders, so
  each expression can turn the mirrored copy on or off. A part that has had
  Symmetry copy on keeps its copy built and only toggles its visibility, so
  switching updates live during playback. Presets saved before this version
  have no symmetry value and leave it unchanged.

## v1.0.229

### New
- **Save and key at this frame** while editing a preset: saves the preset,
  restores the paused keyframes, then keys the edited expression at the
  current frame.

### Changed
- **Save and finish** now warns when the frame goes back to a different
  keyed expression. Previously the edited expression seemed to vanish,
  because the restored keyframes showed the expression keyed at that frame.

## v1.0.228

### New
- **Symmetry copy: show side.** With Symmetry copy on, choose **Both /
  Original only / Copy only**. Use one mirrored part for a wink (a closed
  eyelid on one eye only) and it stays perfectly symmetric with the other
  side. The panel shows which side is the original on screen. It is a rig
  property (`<part>_Side`, always Constant), so it is keyed and saved in
  expression presets and part folders.

## v1.0.227

### Fixed
- Editing an expression preset changed other expressions too. For parts with
  several cells, the placement box edits the **cell offset**, which applies to
  every expression that uses that cell, so moving the eyelid or cropping the
  eye white while editing one preset also changed the others. While a preset
  is being edited, the placement box (position, size, rotation, opacity, crop)
  and Ctrl+T free transform now change **that expression's own values** and
  leave cell offsets alone. The box title shows "This expression" while
  editing.

## v1.0.226

### Changed
- **Flip H is now a keyable rig property** (`<part>_Flip`, always Constant).
  It is keyed with *Key this part* and auto-key, and saved in expression
  presets and part folders.

### Fixed
- Switching expressions left a part's Flip H as it was, because presets did
  not store it. Presets saved before this version have no flip value and
  leave it unchanged; re-save them once if they need a different flip.

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
