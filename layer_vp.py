"""스프라이트 방식 뷰포트 컨트롤러 (파츠 레이어 격자 + 전체 관리).

구성 (위 → 아래)
* 입: 입 시트 격자 + 시퀀스 목록 + 말하기 슬라이더 (atlas_vp, 맨 위)
* 파츠 레이어 격자: ④ 레이어의 '뷰포트 컨트롤러'를 켠 파츠마다 시트 그림이
  깔린 격자. 노란 테두리(손잡이)를 끌면 그 파츠의 칸이 바뀐다.
* 표정 프리셋 목록 (preset_vp)
* 시선 패드 (eye, 맨 아래)

값의 기준은 리그 프로퍼티(fskr_ey_<캔버스>_<레이어>, 칸 번호)다. 손잡이는
입력/표시 장치일 뿐이라 렌더에는 영향이 없다. 손잡이에 찍힌 키는 칸 키로
옮기고 지운다. 이동·색 변경은 드라이버 방식 컨트롤러와 같은 배치 모드
(G/Ctrl 스냅)로 한다. 시트 격자는 크기를 바꿀 수 없다.
"""

import bpy
from .core import app_handler_add, draw_add, draw_remove
import json
from math import floor

from mathutils import Vector

from .core import (
    TGL,
    _EN,
    _JA,
    _ZH,
    _action_fcurves,
    _ensure_root,
    _next_position,
    _redraw_ui,
    _set_color,
    _to_object_mode,
    _tr,
)

_EN.update({
    "뷰포트 컨트롤러": "Viewport controllers",
    "뷰포트 컨트롤러 만들기": "Create viewport controllers",
    "뷰포트 컨트롤러 갱신": "Update viewport controllers",
    "기본 배치로 정렬": "Arrange to default layout",
    "컨트롤러 전부 지우기": "Remove all controllers",
    "파츠 격자": "Part grids",
    "틀": "Frame", "손잡이": "Handle",
    "④ 레이어 속성의 '뷰포트 컨트롤러'를 켠 파츠만 격자가 생깁니다":
        "Only parts with 'Viewport controller' on (④ layer) get a grid",
    "칸이 2개 이상인 파츠만 표시할 수 있습니다":
        "Only parts with 2+ cells can be shown",
    "배치 모드에서 G로 옮기고 Ctrl로 다른 틀에 붙입니다. 시트 격자는 크기 고정":
        "In arrange mode: G to move, Ctrl to snap. Sheet grids keep their size",
    "자동 정렬": "Auto arrange",
    "다른 버전의 이 애드온이 함께 켜져 있습니다":
        "Another copy of this add-on is also enabled",
    "안내 글자·표시가 겹쳐 보이는 원인입니다. 하나만 켜 두세요":
        "That's why overlays draw twice. Keep only one enabled",
    "끄기": "Disable", "다른 사본 끄기": "Disable other copy",
    "다른 사본을 껐습니다: ": "Disabled other copy: ",
    "클립보드에서 이름 붙여넣기": "Paste name from clipboard",
    "클립보드가 비어 있습니다": "Clipboard is empty",
})
_JA.update({"뷰포트 컨트롤러": "ビューポートコントローラー",
            "기본 배치로 정렬": "標準配置に整列", "틀": "枠", "손잡이": "ハンドル"})
_ZH.update({"뷰포트 컨트롤러": "视口控制器",
            "기본 배치로 정렬": "按默认布局排列", "틀": "框", "손잡이": "手柄"})

_PAD_MAX = 0.22
_GRID_COLOR = (0.30, 0.42, 0.55)
_SEL_COLOR = (1.00, 0.86, 0.10)
_SEL_WIRE = 2.5
_GAP = 0.022         # 컨트롤러 사이 간격
_ROW_MAX = 4         # 파츠 격자 한 줄에 놓을 개수

_LAST = {}
_BUSY = [False]
LAYOUT_V = 3         # 기본 배치 규칙이 바뀌면 올림 → 예전 배치 자동 재정렬
_AUTO = {"pending": set(), "tried": {}, "one": set()}


# ------------------------------------------------------------------
# 이름 / 대상
# ------------------------------------------------------------------

def _names(st, L):
    b = "FP_lay_%s_%s" % (st.uid, L.lid)
    return {"h": b, "f": b + "_frame", "hs": b + "_sel",
            "img": "FPSPR_lay_%s_%s" % (st.uid, L.lid),
            "lbl": "FPLBL_lay_%s_%s" % (st.uid, L.lid),
            "wg": "WGT_FP_lay_%s_%s" % (st.uid, L.lid)}


def _own(name, base):
    return name == base or name.startswith(base + "_")


def _canvas(s):
    try:
        from .face_ui import _canvas as cv
        return cv(s)
    except Exception:
        return s.eyes[0] if len(s.eyes) else None


def eligible(s, L):
    """뷰포트 컨트롤러를 띄울 수 있는 파츠: 입 파츠만 (시퀀스 목록·말하기).

    파츠 시트 격자는 1.0.154부터 쓰지 않는다 (표정 프리셋·시선만 남김).
    """
    from .eye import _layer_atlas
    if getattr(L, "kind", 'PART') == 'MOUTH':
        return _layer_atlas(s, L) is not None
    return False


def wanted(s, L):
    return bool(getattr(L, "show_vp", True)) and eligible(s, L)


def lay_exists(rig, st, L):
    return rig is not None and _names(st, L)["h"] in rig.data.bones


def _sig(L):
    return json.dumps([int(L.rows), int(L.cols), L.image, L.name, _PAD_MAX])


def _meta(rig, st, L):
    fb = rig.pose.bones.get(_names(st, L)["f"]) if rig else None
    if fb is None:
        return None
    try:
        return json.loads(fb.get("fskr_lay", "") or "{}") or None
    except Exception:
        return None


def lay_stale(rig, st, L):
    m = _meta(rig, st, L)
    return m is not None and m.get("sig") != _sig(L)


def _geom(L):
    cols, rows = max(1, int(L.cols)), max(1, int(L.rows))
    aspect = 1.0
    img = bpy.data.images.get(L.image) if L.image else None
    try:
        if img is not None and img.size[0] == 0:
            img.pixels[0]
    except Exception:
        pass
    try:
        if img is not None and img.size[0] > 0 and img.size[1] > 0:
            aspect = (img.size[0] / cols) / (img.size[1] / rows)
    except Exception:
        pass
    ch = _PAD_MAX / max(cols * aspect, rows)
    cw = ch * aspect
    return cols, rows, cw, ch


# ------------------------------------------------------------------
# 색 (틀 / 손잡이) — 드라이버 방식처럼 N패널에서 바꿈
# ------------------------------------------------------------------

def _vcol_update(self, context):
    rig = self.id_data
    col = tuple(self.fskr_vcol)
    _set_color(self, True, col)
    try:
        for n in json.loads(self.get("fskr_vgroup", "[]") or "[]"):
            b = rig.pose.bones.get(n)
            if b is not None:
                _set_color(b, True, col)
    except Exception:
        pass


def set_vcol(pb, col, group=()):
    """색 지정 + 같이 칠할 본 목록 기록."""
    pb["fskr_vgroup"] = json.dumps(list(group))
    pb["fskr_vc"] = 1        # 색을 지정한 컨트롤러 표시 (Blender 5는 등록
    pb.fskr_vcol = col       # 프로퍼티가 keys()에 안 보임)


def _cur_col(pb, default):
    try:
        if "fskr_vc" in pb.keys():
            return tuple(pb.fskr_vcol)
        c = pb.color
        if c.palette == 'CUSTOM':
            return tuple(c.custom.normal)
    except Exception:
        pass
    return default


# ------------------------------------------------------------------
# 파츠 격자 생성 / 삭제
# ------------------------------------------------------------------

def lay_remove(context, rig, st, L=None, base=None):
    from .atlas_vp import _remove_fcurves
    if rig is None:
        return
    if base is None:
        base = _names(st, L)["h"]
    lid_part = base[len("FP_lay_"):]
    for ob in list(bpy.data.objects):
        if ob.name == "FPSPR_lay_" + lid_part or \
                _own(ob.name, "FPLBL_lay_" + lid_part):
            bpy.data.objects.remove(ob)
    wg = bpy.data.objects.get("WGT_FP_lay_" + lid_part)
    if wg is not None:
        me = wg.data
        bpy.data.objects.remove(wg)
        if me is not None and me.users == 0:
            bpy.data.meshes.remove(me)
    bones = [b.name for b in rig.data.bones if _own(b.name, base)]
    ad = rig.animation_data
    if ad is not None:
        for fc in list(ad.drivers):
            if any(('"%s"' % b) in fc.data_path for b in bones):
                try:
                    ad.drivers.remove(fc)
                except Exception:
                    pass
        _remove_fcurves(ad, [fc for fc in _action_fcurves(ad)
                             if any(('"%s"' % b) in fc.data_path
                                    for b in bones)])
    if bones:
        prev = context.view_layer.objects.active
        mode = context.mode
        _to_object_mode(context, rig)
        bpy.ops.object.mode_set(mode='EDIT')
        eb = rig.data.edit_bones
        for b in bones:
            if b in eb:
                eb.remove(eb[b])
        bpy.ops.object.mode_set(mode='OBJECT')
        if mode == 'POSE':
            bpy.ops.object.mode_set(mode='POSE')
        elif prev is not None and prev is not rig:
            context.view_layer.objects.active = prev
    _LAST.pop(base, None)


def lay_build(context, s, st, L):
    """파츠 격자 생성/갱신 (있으면 자리·색 유지). 오류 문자열 반환."""
    from .atlas_vp import (_bone_setup, _drv, _grid_widget, _hide_bone,
                           _label, _limit, _none_widget, _sel_widget,
                           _widget_coll)
    from .eye import _ensure_prop, _ncells, _prop_cell
    from mathutils import Matrix
    rig = s.rig
    if rig is None or rig.type != 'ARMATURE':
        return _tr("리그를 먼저 지정하세요")
    if not eligible(s, L) or getattr(L, "kind", 'PART') == 'MOUTH':
        return _tr("칸이 2개 이상인 파츠만 표시할 수 있습니다")
    nm = _names(st, L)
    cols, rows, cw, ch = _geom(L)
    W, H = cols * cw, rows * ch
    keep = None
    if nm["f"] in rig.data.bones:
        fb0 = rig.pose.bones[nm["f"]]
        hb0 = rig.pose.bones.get(nm["h"])
        keep = (rig.data.bones[nm["f"]].head_local.copy(),
                fb0.location.copy(),
                _cur_col(fb0, _GRID_COLOR),
                _cur_col(hb0, _SEL_COLOR) if hb0 else _SEL_COLOR)
    prev = context.view_layer.objects.active
    prev_mode = context.mode
    lay_remove(context, rig, st, L)
    _to_object_mode(context, rig)
    _ensure_root(context, s, rig)
    if keep is not None:
        origin = keep[0].copy()
    else:
        top = _next_position(rig, 0.06 + H - ch / 2)
        rootb = rig.data.bones["FP_root"]
        origin = Vector((rootb.head_local.x - W / 2 + cw / 2, top.y,
                         top.z - 0.035))
    bpy.ops.object.mode_set(mode='EDIT')
    eb = rig.data.edit_bones

    def new(n, parent):
        b = eb.new(n)
        b.head = origin
        b.tail = origin + Vector((0, 0, 0.02))
        b.roll = 0.0
        b.use_deform = False
        b.parent = eb[parent]
    new(nm["f"], "FP_root")
    new(nm["hs"], nm["f"])
    new(nm["h"], nm["f"])
    bpy.ops.object.mode_set(mode='OBJECT')

    coll = _widget_coll(context)
    pbs = rig.pose.bones
    fb, hb, hs = pbs[nm["f"]], pbs[nm["h"]], pbs[nm["hs"]]
    _bone_setup(rig, fb, _grid_widget(coll, nm["wg"], cols, rows, cw, ch),
                (1.0, 1.0, 1.0))
    _bone_setup(rig, hs, _none_widget(coll), (1.0, 1.0, 1.0))
    _bone_setup(rig, hb, _sel_widget(coll), (cw, ch, 1.0))
    if hasattr(hb, "custom_shape_wire_width"):
        hb.custom_shape_wire_width = _SEL_WIRE
    hb.custom_shape_transform = hs
    hb.location = (0.0, 0.0, 0.0)
    _limit(hb, (0.0, (cols - 1) * cw), (-(rows - 1) * ch, 0.0))
    set_vcol(fb, keep[2] if keep else _GRID_COLOR)
    set_vcol(hb, keep[3] if keep else _SEL_COLOR, [nm["hs"]])
    if keep is not None:
        fb.location = keep[1]
    fb["fskr_lay"] = json.dumps({"cols": cols, "rows": rows, "cw": cw,
                                 "ch": ch, "sig": _sig(L), "st": st.uid,
                                 "lid": L.lid})
    fb["fskr_spr_top"] = ch / 2 + 0.034
    fb["fskr_fixed"] = 1            # 시트 격자: 크기 고정

    hx = 'pose.bones["%s"].location' % nm["h"]
    _drv(rig, 'pose.bones["%s"].location' % nm["hs"],
         ["min(max(floor(x/%r+0.5),0),%d)*%r" % (cw, cols - 1, cw),
          "-min(max(floor(-y/%r+0.5),0),%d)*%r" % (ch, rows - 1, ch),
          "0.0"],
         {"x": (rig, hx + "[0]"), "y": (rig, hx + "[1]")})
    if "FP_toggle" in rig.data.bones:
        TH = TGL / 2
        tv = {"t": (rig, 'pose.bones["FP_toggle"].location[0]')}
        _drv(rig, 'pose.bones["%s"].custom_shape_scale_xyz' % nm["f"],
             ["1.0*(t<%s)" % TH] * 3, tv)
        for n9 in (nm["h"], nm["hs"]):
            _drv(rig, 'pose.bones["%s"].scale' % n9, "t<%s" % TH, tv)
    else:
        tv = None
        TH = 0
    from .core import arrange_for
    arr = arrange_for(s, nm["f"])
    rig.data.bones[nm["f"]].hide_select = not arr
    rig.data.bones[nm["h"]].hide_select = arr
    _hide_bone(rig, nm["hs"])
    try:
        from .core import _fskr_apply_locks
        _fskr_apply_locks(rig, arr)
    except Exception:
        pass
    context.view_layer.update()

    fmw = rig.matrix_world @ fb.matrix
    rmw = rig.matrix_world.inverted()

    def at(local):
        return rmw @ (fmw @ Vector(local))

    img = bpy.data.images.get(L.image)
    if img is not None:
        emp = bpy.data.objects.new(nm["img"], None)
        emp.empty_display_type = 'IMAGE'
        emp.data = img
        emp.empty_display_size = max(W, H)
        emp.empty_image_offset = (-0.5, -0.5)
        emp.use_empty_image_alpha = True
        emp.color = (1.0, 1.0, 1.0, 0.85)
        emp.hide_render = True
        emp.hide_select = True
        context.scene.collection.objects.link(emp)
        emp.parent = rig
        emp.parent_type = 'BONE'
        emp.parent_bone = nm["f"]
        context.view_layer.update()
        c_loc = Vector((W / 2 - cw / 2, ch / 2 - H / 2, -0.002))
        emp.matrix_world = fmw @ Matrix.Translation(c_loc)
        if tv is not None:
            _drv(emp, "hide_viewport", "t>%s" % TH, tv)
    _label(context, rig, nm["lbl"], L.name or L.lid, 0.02, nm["f"],
           at((W / 2 - cw / 2, ch / 2 + 0.016, 0.0)))

    p = _prop_cell(st, L)
    _ensure_prop(rig, p, _ncells(L))
    _LAST.pop(nm["h"], None)
    _sync_one(context.scene, s, rig, st, L, from_frame=True)
    if prev_mode == 'POSE' or prev is rig:
        context.view_layer.objects.active = rig
        try:
            bpy.ops.object.mode_set(mode='POSE')
        except Exception:
            pass
    elif prev is not None:
        context.view_layer.objects.active = prev
    return ""


# ------------------------------------------------------------------
# 손잡이 <-> 칸 동기화
# ------------------------------------------------------------------

def _clamp(v, n):
    return max(0, min(int(n) - 1, int(v)))


def _loc_cell(m, x, y):
    c = _clamp(floor(x / m["cw"] + 0.5), m["cols"])
    r = _clamp(floor(-y / m["ch"] + 0.5), m["rows"])
    return r, c


def _autokey(st):
    try:
        ts = bpy.context.scene.tool_settings
        return bool(st.autokey or ts.use_keyframe_insert_auto)
    except Exception:
        return bool(getattr(st, "autokey", False))


def _tag(rig, st):
    try:
        rig.update_tag()
        ob = bpy.data.objects.get(st.target)
        if ob is not None:
            ob.update_tag()
    except Exception:
        pass


def _absorb(scene, rig, st, L, m, prop):
    from .atlas import _key
    from .atlas_vp import _remove_fcurves
    ad = rig.animation_data
    if ad is None:
        return False
    pre = 'pose.bones["%s"].' % _names(st, L)["h"]
    mine = [fc for fc in _action_fcurves(ad) if fc.data_path.startswith(pre)]
    if not mine:
        return False
    lx = {fc.array_index: fc for fc in mine
          if fc.data_path == pre + "location"}
    frames = sorted({int(round(kp.co[0])) for fc in lx.values()
                     for kp in fc.keyframe_points})

    def ev(i, f):
        fc = lx.get(i)
        return fc.evaluate(f) if fc is not None else 0.0
    cols = int(m["cols"])
    for f in frames:
        r, c = _loc_cell(m, ev(0, f), ev(1, f))
        rig[prop] = r * cols + c
        _key(rig, prop, f)
    keep = None
    if lx:
        r, c = _loc_cell(m, ev(0, scene.frame_current),
                         ev(1, scene.frame_current))
        keep = r * cols + c
    _remove_fcurves(ad, mine)
    if keep is not None:
        rig[prop] = keep
    return True


def _sync_one(scene, s, rig, st, L, from_frame=False):
    from .atlas import _key
    from .eye import _get, _prop_cell
    nm = _names(st, L)
    hb = rig.pose.bones.get(nm["h"])
    if hb is None:
        return
    m = _meta(rig, st, L)
    if not m:
        return
    p = _prop_cell(st, L)
    if _absorb(scene, rig, st, L, m, p):
        from_frame = True
    cols, rows = int(m["cols"]), int(m["rows"])
    cur = _clamp(_get(rig, p), cols * rows)
    cur_rc = (cur // cols, cur % cols)
    loc = _loc_cell(m, hb.location[0], hb.location[1])
    last = _LAST.get(nm["h"])
    if loc != cur_rc:
        if not from_frame and last is not None and loc != last:
            rig[p] = loc[0] * cols + loc[1]
            if _autokey(st):
                _key(rig, p)
            _tag(rig, st)
            cur_rc = loc
        else:
            hb.location[0] = cur_rc[1] * m["cw"]
            hb.location[1] = -cur_rc[0] * m["ch"]
    _LAST[nm["h"]] = cur_rc


def _sync(scene, from_frame):
    try:
        s = scene.fskr
        rig = s.rig
    except Exception:
        return
    if rig is None or rig.type != 'ARMATURE':
        return
    st = _canvas(s)
    if st is None:
        return
    have = set()
    for L in st.layers:
        nm = _names(st, L)
        if nm["h"] not in rig.data.bones:
            continue
        have.add(nm["h"])
        if not from_frame:
            bad = (not wanted(s, L)) or lay_stale(rig, st, L)
            if bad:
                sg = (_sig(L), wanted(s, L))
                if _AUTO["tried"].get(nm["h"]) != sg:
                    _AUTO["tried"][nm["h"]] = sg
                    schedule(st.uid)
                continue
        try:
            _sync_one(scene, s, rig, st, L, from_frame)
        except Exception as e:
            print("FSKR layer vp:", e)
    if not from_frame:
        init_gaze_colors(rig, st)
        if built(s, st) and st.vp_autolayout:
            sg = _layout_sig(s, st)
            if st.get("vp_layout_v", 0) != LAYOUT_V or \
                    sg != st.get("vp_layout_sig", ""):
                if getattr(s, "arrange", False) and \
                        st.get("vp_layout_v", 0) == LAYOUT_V:
                    # 배치 모드에서 직접 옮김 → 그 자리를 지키도록 자동 정렬 끔
                    st.vp_autolayout = False
                elif _AUTO["tried"].get("layout") != sg:
                    _AUTO["tried"]["layout"] = sg
                    schedule(st.uid)
        # 지워진 레이어의 격자 정리
        pre = "FP_lay_%s_" % st.uid
        orphan = [b.name for b in rig.data.bones
                  if b.name.startswith(pre) and b.name.endswith("_frame")
                  and b.name[:-6] not in have]
        if orphan and _AUTO["tried"].get("orphan") != tuple(orphan):
            _AUTO["tried"]["orphan"] = tuple(orphan)
            schedule(st.uid)


def _sync_safe(scene, from_frame):
    if _BUSY[0]:
        return
    try:
        if bpy.app.is_job_running('RENDER'):
            return
    except Exception:
        pass
    _BUSY[0] = True
    try:
        _sync(scene, from_frame)
    except Exception as e:
        print("FSKR layer vp sync:", e)
    finally:
        _BUSY[0] = False


@bpy.app.handlers.persistent
def _on_depsgraph(scene, depsgraph=None):
    _sync_safe(scene, False)
    try:
        _arrange_redirect(scene)
    except Exception:
        pass
    try:
        fit_gaze_labels(scene)
    except Exception:
        pass


_GFIT = {}


def fit_gaze_labels(scene):
    """시선 패드 제목: 틀을 늘여도 글자는 그대로(가운데), 좁으면 '...'."""
    s = scene.fskr
    rig = s.rig
    if rig is None or rig.type != 'ARMATURE':
        return
    from mathutils import Vector
    from .atlas_vp import fit_label, _lbl_body
    from .eye import _BONE_PREFIX
    for st in s.eyes:
        lb = bpy.data.objects.get("FPLBL_eye_" + st.uid)
        fb = rig.pose.bones.get(_BONE_PREFIX + st.uid + "_frame")
        if lb is None or fb is None or fb.custom_shape is None:
            continue
        fw = rig.matrix_world @ fb.matrix
        try:
            xs = [v.co.x for v in fb.custom_shape.data.vertices]
            wl = (max(xs) - min(xs)) * float(fb.custom_shape_scale_xyz[0])
        except Exception:
            continue
        width = wl * Vector(fw.col[0][:3]).length
        try:
            full = _lbl_body(json.loads(lb.get("fskr_lbl", "[]")))
        except Exception:
            full = ""
        full = full or lb.data.body
        sig = (round(width, 6), round(Vector(fw.col[1][:3]).length, 6),
               full, lb.data.body)
        if _GFIT.get(st.uid) == sig or width <= 1e-6:
            continue
        fit_label(lb, full, width + 0.12)   # 제목은 틀보다 조금 넓어도 됨
        _GFIT[st.uid] = sig[:3] + (lb.data.body,)


def _arrange_redirect(scene):
    """배치 모드: 컨트롤러 안쪽 틀(입 시퀀스 목록·말하기 슬라이더 등)을
    누르면 그 컨트롤러의 바깥 틀이 선택되게 (안쪽 틀은 따로 못 움직임)."""
    s = scene.fskr
    rig = s.rig
    if rig is None or not getattr(s, "arrange", False) or \
            rig.type != 'ARMATURE':
        return
    from .core import _VP_PREFIX
    pbs = rig.pose.bones
    act = rig.data.bones.active
    moved = False
    for pb in pbs:
        n = pb.name
        if not (getattr(pb, "select", False) and n.endswith("_frame")
                and n.startswith(_VP_PREFIX) and pb.parent is not None
                and pb.parent.name != "FP_root"):
            continue
        top = pb.parent
        while top.parent is not None and top.parent.name != "FP_root":
            top = top.parent
        pb.select = False
        top.select = True
        if act is not None and act.name == n:
            rig.data.bones.active = rig.data.bones[top.name]
        moved = True
    if moved:
        try:
            rig.update_tag()
        except Exception:
            pass


@bpy.app.handlers.persistent
def _on_frame(scene, depsgraph=None):
    _sync_safe(scene, True)


# ------------------------------------------------------------------
# 전체 관리 (만들기 / 갱신 / 정렬 / 지우기)
# ------------------------------------------------------------------

def built(s, st):
    """이 캔버스의 컨트롤러가 있는지 (예전 버전에서 따로 만든 표정 목록·
    입 격자·시선 패드도 포함 → 함께 자동 정렬 대상)."""
    if st.get("vp_on", False):
        return True
    try:
        return bool(controllers(s, st))
    except Exception:
        return False


def apply_layers(context, s, st):
    """레이어 체크 상태대로 파츠/입 격자를 만들거나 지운다 (자리 유지)."""
    from . import atlas_vp as AV
    from .eye import _layer_atlas
    rig = s.rig
    done_atlas = set()
    for L in list(st.layers):
        lid = L.lid
        L = next((x for x in st.layers if x.lid == lid), None)
        if L is None:
            continue
        if getattr(L, "kind", 'PART') == 'MOUTH':
            it = _layer_atlas(s, L)
            if it is None:
                continue
            if wanted(s, L):
                done_atlas.add(it.uid)
                if not AV.vp_exists(rig, it) or AV.vp_stale(rig, it):
                    AV.vp_build(context, s, it)
            continue
        if lay_exists(rig, st, L):        # 예전 파츠 격자 정리
            lay_remove(context, rig, st, L)
    # 체크를 끈 입 레이어의 시트 컨트롤러
    for it in s.atlases:
        if it.uid in done_atlas or not AV.vp_exists(rig, it):
            continue
        if any(getattr(L, "kind", 'PART') == 'MOUTH' and L.atlas == it.uid
               for L in st.layers):
            AV.vp_remove(context, rig, it)
    # 지워진 레이어
    lids = {L.lid for L in st.layers}
    pre = "FP_lay_%s_" % st.uid
    for b in [b.name for b in rig.data.bones
              if b.name.startswith(pre) and b.name.endswith("_frame")]:
        base = b[:-6]
        if base[len(pre):] not in lids:
            lay_remove(context, rig, st, base=base)


def build_all(context, s, st, relayout=False):
    from .eye import _pad_build
    from . import preset_vp as PV
    rig = s.rig
    first = not built(s, st)
    prev = context.view_layer.objects.active
    prev_mode = context.mode
    apply_layers(context, s, st)
    if len(st.presets):
        if not PV.pre_exists(rig, st) or PV.pre_stale(rig, st):
            PV.pre_build(context, s, st)
    if not st.follow and EY_pad(rig, st) is None:
        _pad_build(context, s, st)
    init_gaze_colors(rig, st)
    st["vp_on"] = True
    if first or relayout or st.vp_autolayout:
        layout(context, s, st)
    if prev_mode == 'POSE' or prev is rig:
        context.view_layer.objects.active = rig
        try:
            bpy.ops.object.mode_set(mode='POSE')
        except Exception:
            pass
    elif prev is not None:
        context.view_layer.objects.active = prev
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except Exception:
            pass


def remove_all(context, s, st):
    from . import atlas_vp as AV
    from . import preset_vp as PV
    from .eye import _pad_remove
    rig = s.rig
    for L in st.layers:
        if lay_exists(rig, st, L):
            lay_remove(context, rig, st, L)
    for it in s.atlases:
        if AV.vp_exists(rig, it):
            AV.vp_remove(context, rig, it)
    PV.pre_remove(context, rig, st)
    _pad_remove(context, rig, st)
    st["vp_on"] = False


def EY_pad(rig, st):
    from .eye import _pad_name
    return rig.pose.bones.get(_pad_name(st) + "_frame") if rig else None


def init_gaze_colors(rig, st):
    from .eye import _pad_name
    base = _pad_name(st)
    fb = rig.pose.bones.get(base + "_frame")
    hb = rig.pose.bones.get(base)
    if fb is not None and "fskr_vc" not in fb.keys():
        set_vcol(fb, _cur_col(fb, (0.30, 0.42, 0.55)))
    if hb is not None and "fskr_vc" not in hb.keys():
        set_vcol(hb, _cur_col(hb, (0.55, 0.85, 1.0)))
    lb = bpy.data.objects.get("FPLBL_eye_" + st.uid)
    if lb is not None and "fskr_lbl" not in lb.keys():
        lb["fskr_lbl"] = json.dumps([[st.name + " · ", False],
                                     ["시선", True]], ensure_ascii=False)


def controllers(s, st):
    """[(이름, 틀 본, 손잡이 본)] 위 → 아래 순서 (UI/정렬 공용)."""
    from . import atlas_vp as AV
    from . import preset_vp as PV
    from .eye import _layer_atlas, _pad_name
    rig = s.rig
    out = []
    if rig is None:
        return out
    pbs = rig.pose.bones
    for L in st.layers:
        if getattr(L, "kind", 'PART') == 'MOUTH':
            it = _layer_atlas(s, L)
            if it is not None and AV.vp_exists(rig, it):
                nm = AV._names(it)
                out.append(("mouth", L.name or it.name, pbs.get(nm["f"]),
                            pbs.get(nm["h"])))
            continue
        nm = _names(st, L)
        if nm["f"] in pbs:
            out.append(("layer", L.name or L.lid, pbs.get(nm["f"]),
                        pbs.get(nm["h"])))
    b = PV._base(st)
    if b + "_frame" in pbs:
        out.append(("preset", _tr("표정"), pbs.get(b + "_frame"),
                    pbs.get(b)))
    b = _pad_name(st)
    if b + "_frame" in pbs:
        out.append(("gaze", _tr("시선"), pbs.get(b + "_frame"),
                    pbs.get(b)))
    return [o for o in out if o[2] is not None]


def _bounds(pb):
    """틀의 패널 공간 경계 (x0, x1, z0, z1): 위젯 + 위 라벨 + 아래 슬라이더."""
    from .core import _frame_corners, _panel_space
    R, Rinv = _panel_space(pb.id_data)
    cs = [Rinv @ c for c in _frame_corners(pb)]
    x0, x1 = min(c.x for c in cs), max(c.x for c in cs)
    z0, z1 = min(c.z for c in cs), max(c.z for c in cs)
    o = Rinv @ pb.matrix.translation
    sc = pb.matrix.to_scale()[1] or 1.0
    top = float(pb.get("fskr_spr_top", 0.0))
    if top:
        z1 = max(z1, o.z + top * sc)
    try:
        m = json.loads(pb.get("fskr_spr", "") or "{}")
        if m.get("foot") is not None:
            z0 = min(z0, o.z - float(m["foot"]) * sc)
        if m.get("xr") is not None:     # 말하기 슬라이더 이름 오른쪽 끝
            x1 = max(x1, o.x + float(m["xr"]) * sc)
    except Exception:
        pass
    return x0, x1, z0, z1


def _shift(pb, dx, dz):
    from .core import _panel_space
    R, Rinv = _panel_space(pb.id_data)
    m = pb.matrix.copy()
    m.translation = m.translation + R.to_3x3() @ Vector((dx, 0.0, dz))
    pb.matrix = m


def _layout_sig(s, st):
    """컨트롤러 구성·위치 서명 (자동 정렬 뒤 누가 옮겼는지/늘었는지 확인)."""
    out = []
    root = s.rig.pose.bones.get("FP_root") if s.rig else None
    r0 = root.matrix.translation if root is not None else Vector()
    for kind, _n, fb, _h in controllers(s, st):
        t = fb.matrix.translation - r0
        sc = fb.matrix.to_scale()
        out.append("%s:%.4f,%.4f,%.4f:%.3f" % (fb.name, t.x, t.y, t.z, sc.y))
    return "|".join(out)


def _norm_tops(ctl):
    """예전 버전에서 만든 컨트롤러의 위 여백(라벨 자리)을 지금 값으로."""
    from . import preset_vp as PV
    from .eye import PAD
    for kind, _n, fb, _h in ctl:
        try:
            if kind == "gaze":
                fb["fskr_spr_top"] = PAD + 0.04
            elif kind == "preset":
                fb["fskr_spr_top"] = PV.STEP / 2 + 0.036
            elif kind == "layer":
                m = json.loads(fb.get("fskr_lay", "") or "{}")
                fb["fskr_spr_top"] = float(m["ch"]) / 2 + 0.034
            elif kind == "mouth":
                m = json.loads(fb.get("fskr_spr", "") or "{}")
                fb["fskr_spr_top"] = float(m["ch"]) / 2 + 0.04
        except Exception:
            pass


def layout(context, s, st, _chain=True):
    """기본 배치: 맨 아래 시선, 그 위 표정 목록, 그 위 파츠 격자, 맨 위 입.

    시선 패드(없으면 FP_root) 왼쪽 아래를 기준으로 왼쪽 맞춤해 위로 쌓는다.
    파츠 격자는 한 줄에 최대 4개씩, 레이어 목록 순서대로 위에서부터.
    캔버스가 여러 개면 캔버스마다 한 열씩, 앞 캔버스 열의 오른쪽에 쌓는다.
    """
    from .core import _frame_corners, _panel_space
    rig = s.rig
    ctl = controllers(s, st)
    st["vp_layout_v"] = LAYOUT_V
    if not ctl:
        return
    _norm_tops(ctl)
    context.view_layer.update()
    gaze = [c for c in ctl if c[0] == "gaze"]
    pre = [c for c in ctl if c[0] == "preset"]
    grids = [c for c in ctl if c[0] == "layer"]
    mouth = [c for c in ctl if c[0] == "mouth"]
    # 기준: 패널 바닥(그랩 바·토글·드라이버 방식 컨트롤러)의 윗변
    R, Rinv = _panel_space(rig)
    root = rig.pose.bones.get("FP_root")
    cs = [Rinv @ c for c in _frame_corners(root)]
    x_left = min(c.x for c in cs)
    z_top = max(c.z for c in cs)
    mine = {c[2].name for c in ctl}
    for pb in rig.pose.bones:
        n = pb.name
        if n in mine or not n.endswith("_frame") or n == "FP_root":
            continue
        if not (n.startswith("FP_ctl") or n == "FP_toggle_frame"):
            continue
        try:
            z_top = max(z_top, max((Rinv @ c).z for c in _frame_corners(pb)))
        except Exception:
            pass
    # 앞 캔버스들의 컨트롤러 열 오른쪽으로 (겹치지 않게)
    idx = next((i for i, e in enumerate(s.eyes) if e == st), 0)
    for e in list(s.eyes)[:idx]:
        try:
            for c in controllers(s, e):
                x_left = max(x_left, _bounds(c[2])[1] + _GAP * 2)
        except Exception:
            pass
    z = z_top + _GAP
    for c in gaze:      # 맨 아래 시선
        x0, x1, z0, z1 = _bounds(c[2])
        _shift(c[2], x_left - x0, z - z0)
        context.view_layer.update()
        z += (z1 - z0) + _GAP
    for c in pre:
        x0, x1, z0, z1 = _bounds(c[2])
        _shift(c[2], x_left - x0, z - z0)
        context.view_layer.update()
        z += (z1 - z0) + _GAP
    rows = [grids[i:i + _ROW_MAX] for i in range(0, len(grids), _ROW_MAX)]
    # 입(시퀀스 목록 + 말하기)은 맨 위 한 줄
    rows = [[c] for c in mouth] + rows
    for row in reversed(rows):
        bs = [_bounds(c[2]) for c in row]
        hmax = max(b[3] - b[2] for b in bs)
        x = x_left
        for c, b in zip(row, bs):
            x0, x1, z0, z1 = b
            # 줄 안에서는 윗변을 맞춤
            _shift(c[2], x - x0, (z + hmax) - z1)
            x += (x1 - x0) + _GAP
        context.view_layer.update()
        z += hmax + _GAP
    context.view_layer.update()
    st["vp_layout_sig"] = _layout_sig(s, st)
    if _chain:   # 뒤 캔버스 열도 다시 맞춤 (앞 열 폭이 바뀌었을 수 있음)
        for e in list(s.eyes)[idx + 1:]:
            try:
                if e.vp_autolayout and built(s, e):
                    layout(context, s, e, _chain=False)
            except Exception as ex:
                print("FSKR layout chain:", ex)


# ------------------------------------------------------------------
# 예약 실행
# ------------------------------------------------------------------

def _ctx_kw():
    ctx = bpy.context
    kw = {}
    try:
        win = ctx.window_manager.windows[0]
        kw["window"] = win
        area = next((a for a in win.screen.areas if a.type == 'VIEW_3D'),
                    None)
        if area is not None:
            kw["area"] = area
            kw["region"] = next((r for r in area.regions
                                 if r.type == 'WINDOW'), None)
    except Exception:
        pass
    return kw


def _auto_tick():
    pend = list(_AUTO["pending"])
    _AUTO["pending"].clear()
    if not pend:
        return None
    try:
        with bpy.context.temp_override(**_ctx_kw()):
            c2 = bpy.context
            s = c2.scene.fskr
            st = _canvas(s)
            if st is None or st.uid not in pend or s.rig is None:
                return None
            prev = c2.view_layer.objects.active
            prev_mode = c2.mode
            purge_grids(c2, s, st)
            if st.get("vp_on", False):
                # 파츠 격자는 '뷰포트 컨트롤러 만들기'를 쓴 뒤에만 자동 관리
                apply_layers(c2, s, st)
            else:
                # 레이어 체크를 직접 바꾼 파츠만 만들거나 지움
                for lid in list(_AUTO["one"]):
                    L = next((x for x in st.layers if x.lid == lid), None)
                    if L is not None:
                        _apply_one(c2, s, st, L)
            _AUTO["one"].clear()
            if st.vp_autolayout and built(s, st):
                layout(c2, s, st)
            if prev_mode == 'POSE' or prev is s.rig:
                c2.view_layer.objects.active = s.rig
                try:
                    bpy.ops.object.mode_set(mode='POSE')
                except Exception:
                    pass
            elif prev is not None:
                c2.view_layer.objects.active = prev
                try:
                    bpy.ops.object.mode_set(mode='OBJECT')
                except Exception:
                    pass
    except Exception as e:
        print("FSKR layer vp rebuild:", e)
    _redraw_ui(bpy.context)
    return None


def auto_layout(context):
    """다른 컨트롤러가 자동으로 다시 만들어진 뒤: 자동 정렬이 켜져 있으면 정렬."""
    try:
        s = context.scene.fskr
        st = _canvas(s)
        if st is not None and s.rig is not None and built(s, st) and \
                st.vp_autolayout:
            layout(context, s, st)
    except Exception as e:
        print("FSKR auto layout:", e)


def schedule(uid):
    _AUTO["pending"].add(uid)
    try:
        if not bpy.app.timers.is_registered(_auto_tick):
            bpy.app.timers.register(_auto_tick, first_interval=0.05)
    except Exception:
        pass


def _apply_one(context, s, st, L):
    """파츠 하나의 격자(입이면 입 컨트롤러)를 체크 상태대로."""
    from . import atlas_vp as AV
    from .eye import _layer_atlas
    rig = s.rig
    if getattr(L, "kind", 'PART') == 'MOUTH':
        it = _layer_atlas(s, L)
        if it is None:
            return
        if wanted(s, L):
            if not AV.vp_exists(rig, it):
                AV.vp_build(context, s, it)
        elif AV.vp_exists(rig, it):
            AV.vp_remove(context, rig, it)
        return
    if lay_exists(rig, st, L):
        lay_remove(context, rig, st, L)


def purge_grids(context, s, st):
    """예전 버전의 파츠 시트 격자를 모두 지운다 (컨트롤러는 입·표정·시선만)."""
    rig = s.rig
    if rig is None:
        return 0
    bases = sorted({b.name[:-len("_frame")] for b in rig.data.bones
                    if b.name.startswith("FP_lay_")
                    and b.name.endswith("_frame")})
    for base in bases:
        lay_remove(context, rig, st, base=base)
    return len(bases)


def show_vp_cb(self, context):
    """레이어의 '뷰포트 컨트롤러' 체크를 바꾸면 그 격자를 바로 만들거나 지움."""
    try:
        from .eye import _owner
        st = _owner(self)
        if st is not None and context.scene.fskr.rig is not None:
            _AUTO["one"].add(self.lid)
            schedule(st.uid)
    except Exception as e:
        print("FSKR show_vp:", e)


@bpy.app.handlers.persistent
def _on_load(*_a):
    _LAST.clear()
    _AUTO["tried"].clear()


# ------------------------------------------------------------------
# 오퍼레이터
# ------------------------------------------------------------------

class FSKR_OT_sprite_vp(bpy.types.Operator):
    bl_idname = "fskr.sprite_vp"
    bl_label = "뷰포트 컨트롤러"
    bl_description = ("파츠 격자·입·표정 목록·시선 패드를 뷰포트에 만들거나 "
                      "갱신하거나 정렬하거나 지웁니다")
    bl_options = {'REGISTER', 'UNDO'}

    action: bpy.props.EnumProperty(
        items=(('BUILD', "만들기/갱신", ""), ('LAYOUT', "정렬", ""),
               ('REMOVE', "지우기", "")), options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        s = context.scene.fskr
        return s.rig is not None and _canvas(s) is not None

    def execute(self, context):
        s = context.scene.fskr
        st = _canvas(s)
        if self.action == 'REMOVE':
            remove_all(context, s, st)
        elif self.action == 'LAYOUT':
            # 낡은 컨트롤러는 먼저 다시 만들고(자리·색 유지) 정렬
            build_all(context, s, st, relayout=True)
        else:
            build_all(context, s, st)
        _redraw_ui(context)
        return {'FINISHED'}


def paste_btn(layout, owner, attr="name"):
    """이름 칸 옆 '가' 버튼 (한중일 입력 창)."""
    from .ime import ime_btn
    ime_btn(layout, owner, attr)


def draw_panel(layout, s, st):
    """뷰포트 컨트롤러 관리 UI (색·정렬·만들기)."""
    from .face_ui import _guide, _step
    rig = s.rig
    on = built(s, st)
    col = _step(layout, "", _tr("뷰포트 컨트롤러"), on, 'ARMATURE_DATA')
    _guide(col, [_tr("입 시퀀스 · 표정 목록 · 시선 패드를 뷰포트에 만듭니다"),
                 _tr("배치 모드에서 G로 옮기고 Ctrl로 다른 틀에 붙입니다. "
                     "시트 격자는 크기 고정")])
    r = col.row(align=True)
    r.scale_y = 1.3
    r.operator("fskr.sprite_vp",
               text=_tr("뷰포트 컨트롤러 갱신") if on
               else _tr("뷰포트 컨트롤러 만들기"),
               icon='FILE_REFRESH' if on else 'ADD').action = 'BUILD'
    if not on:
        return
    r = col.row(align=True)
    r.operator("fskr.sprite_vp", text=_tr("기본 배치로 정렬"),
               icon='ALIGN_TOP').action = 'LAYOUT'
    r.operator("fskr.sprite_vp", text="", icon='TRASH').action = 'REMOVE'
    col.prop(st, "vp_autolayout", icon='ALIGN_TOP')
    if hasattr(s, "arrange"):
        from .operators import arrange_button
        arrange_button(col, s, "")
    if hasattr(s, "show_no_overlay"):
        col.prop(s, "show_no_overlay", toggle=True, icon='OVERLAY')
    from .core import draw_panel_follow
    draw_panel_follow(col, s)
    ctl = controllers(s, st)
    if ctl:
        b = col.box().column(align=True)
        hr = b.row()
        hr.label(text="")
        sub = hr.row(align=True)
        sub.alignment = 'RIGHT'
        sub.label(text=_tr("틀"))
        sub.label(text=_tr("손잡이"))
        for kind, name, fb, hb in ctl:
            rr = b.row(align=True)
            ic = {'layer': 'IMAGE_DATA', 'mouth': 'SPEAKER',
                  'preset': 'SHAPEKEY_DATA',
                  'gaze': 'ORIENTATION_VIEW'}.get(kind, 'DOT')
            rr.label(text=name, icon=ic)
            sub = rr.row(align=True)
            sub.scale_x = 0.6
            if "fskr_vc" in fb.keys():
                sub.prop(fb, "fskr_vcol", text="")
            else:
                sub.label(text="-")
            if hb is not None and "fskr_vc" in hb.keys():
                sub.prop(hb, "fskr_vcol", text="")
            else:
                sub.label(text="-")
    col.prop(st, "autokey", icon='REC')


class FSKR_OT_disable_copy(bpy.types.Operator):
    """함께 켜진 다른 버전의 이 애드온을 끈다 (화면 글자가 겹쳐 보이는 원인)."""
    bl_idname = "fskr.disable_copy"
    bl_label = "다른 사본 끄기"
    bl_description = ("함께 켜져 있는 다른 버전의 Face Shape Key Rig를 끕니다. "
                      "두 개가 켜져 있으면 안내 글자·표시가 겹쳐 그려집니다")
    bl_options = {'REGISTER', 'INTERNAL'}

    module: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        import addon_utils
        try:
            addon_utils.disable(self.module, default_set=True)
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        try:
            bpy.ops.wm.save_userpref()
        except Exception:
            pass
        self.report({'INFO'}, _tr("다른 사본을 껐습니다: ") + self.module)
        _redraw_ui(context)
        return {'FINISHED'}


def draw_copy_warning(layout):
    from .core import other_copies
    oc = other_copies()
    if not oc:
        return
    b = layout.box().column(align=True)
    b.alert = True
    b.label(text=_tr("다른 버전의 이 애드온이 함께 켜져 있습니다"),
            icon='ERROR')
    b.label(text=_tr("안내 글자·표시가 겹쳐 보이는 원인입니다. "
                     "하나만 켜 두세요"))
    for m in oc:
        r = b.row(align=True)
        r.label(text=m)
        r.operator("fskr.disable_copy", text=_tr("끄기"),
                   icon='CANCEL').module = m




# ------------------------------------------------------------------
# 성능 측정: 몇 초 동안 이 애드온(과 Blender의 모든 파이썬)이 쓴 시간을
# 함수별로 모아 보고서로 남긴다. 사용자가 렉이 나는 동작을 하는 동안 측정.
# ------------------------------------------------------------------

_PROF = {"p": None, "t0": 0.0, "win": 0, "ui": 0, "hs": [], "summary": []}


def _prof_count_win():
    _PROF["win"] += 1


def _prof_count_ui():
    _PROF["ui"] += 1


def _perf_end():
    import io
    import pstats
    import time
    pr = _PROF.get("p")
    if pr is None:
        return None
    pr.disable()
    _PROF["p"] = None
    for sp, h, rg in _PROF["hs"]:
        try:
            sp.draw_handler_remove(h, rg)
        except Exception:
            pass
    _PROF["hs"] = []
    el = max(1e-6, time.perf_counter() - _PROF["t0"])
    out = io.StringIO()
    st = pstats.Stats(pr, stream=out)
    tot = sum(v[2] for v in st.stats.values())   # 파이썬 자체 시간 합
    out.write("Face Rig perf  elapsed %.1fs  python self-time %.3fs "
              "(%.1f%%)  viewport redraws %d (%.0f/s)  sidebar redraws %d "
              "(%.0f/s)\n\n" % (el, tot, tot / el * 100, _PROF["win"],
                                  _PROF["win"] / el, _PROF["ui"],
                                  _PROF["ui"] / el))
    st.sort_stats("cumulative").print_stats(45)
    st.sort_stats("tottime").print_stats(30)
    out.write("\n==== callers (누가 불렀는지) ====\n")
    st.sort_stats("cumulative").print_callers(12)
    txt = out.getvalue()
    # 짧은 요약 (패널 표시용): 이 애드온 함수 중 누적 시간 상위
    rows = []
    for (fn, ln, name), v in st.stats.items():
        if "face_shapekey_rig" in fn.replace("\\", "/"):
            rows.append((v[3], v[1], name, fn.replace("\\", "/")
                         .rsplit("/", 1)[-1], ln))
    rows.sort(reverse=True)
    summ = ["%.0f%%  python %.2fs / %.1fs  ·  %s %.0f/s · %s %.0f/s" % (
        tot / el * 100, tot, el, _tr("화면"), _PROF["win"] / el,
        _tr("N패널"), _PROF["ui"] / el)]
    for ct, nc, name, f, ln in rows[:8]:
        summ.append("%.3fs  x%d  %s (%s:%d)" % (ct, nc, name, f, ln))
    _PROF["summary"] = summ
    t = bpy.data.texts.get("FSKR_perf.txt") or bpy.data.texts.new(
        "FSKR_perf.txt")
    t.from_string(txt)
    path = ""
    try:
        if bpy.data.filepath:
            import os
            path = os.path.join(os.path.dirname(bpy.data.filepath),
                                "fskr_perf.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(txt)
    except Exception:
        path = ""
    _PROF["path"] = path
    print(txt)
    _redraw_ui(bpy.context)
    return None


class FSKR_OT_perf_profile(bpy.types.Operator):
    bl_idname = "fskr.perf_profile"
    bl_label = "성능 측정"
    bl_description = ("몇 초 동안 애드온이 쓰는 시간을 함수별로 잽니다. 누른 뒤 "
                      "렉이 나는 동작(화면 돌리기·재생·컨트롤러 끌기 등)을 "
                      "평소처럼 하세요. 결과는 블렌드 파일 옆 fskr_perf.txt와 "
                      "텍스트 편집기의 FSKR_perf.txt에 저장됩니다")
    bl_options = {'REGISTER'}

    seconds: bpy.props.IntProperty(name="초", default=8, min=3, max=60)

    def execute(self, context):
        import cProfile
        import time
        if _PROF.get("p") is not None:
            return {'CANCELLED'}
        _PROF.update(win=0, ui=0, summary=[], path="")
        sp = bpy.types.SpaceView3D
        _PROF["hs"] = [
            (sp, sp.draw_handler_add(_prof_count_win, (), 'WINDOW',
                                     'POST_PIXEL'), 'WINDOW'),
            (sp, sp.draw_handler_add(_prof_count_ui, (), 'UI',
                                     'POST_PIXEL'), 'UI')]
        pr = cProfile.Profile()
        _PROF["p"] = pr
        _PROF["t0"] = time.perf_counter()
        pr.enable()
        bpy.app.timers.register(_perf_end, first_interval=float(self.seconds))
        self.report({'INFO'}, _tr("측정 중 (%d초) — 렉이 나는 동작을 해 주세요")
                    % self.seconds)
        return {'FINISHED'}


def draw_perf(layout):
    """작업 방식 패널 아래: 성능 측정 버튼과 마지막 결과 요약."""
    row = layout.row(align=True)
    row.scale_y = 0.9
    busy = _PROF.get("p") is not None
    row.enabled = not busy
    row.operator("fskr.perf_profile",
                 text=_tr("측정 중…") if busy else _tr("성능 측정 (8초)"),
                 icon='TIME')
    summ = _PROF.get("summary") or []
    if summ and not busy:
        b = layout.box().column(align=True)
        b.scale_y = 0.75
        for i, ln in enumerate(summ):
            b.label(text=ln, icon='INFO' if i == 0 else 'BLANK1')
        if _PROF.get("path"):
            b.label(text=_PROF["path"], icon='FILE_TEXT')


lvp_classes = (FSKR_OT_sprite_vp, FSKR_OT_disable_copy, FSKR_OT_perf_profile)


def lvp_register():
    bpy.types.PoseBone.fskr_vcol = bpy.props.FloatVectorProperty(
        name="색", subtype='COLOR', size=3, min=0.0, max=1.0,
        default=(1.0, 0.86, 0.1), update=_vcol_update)
    h = bpy.app.handlers
    app_handler_add(h.depsgraph_update_post, _on_depsgraph)
    app_handler_add(h.frame_change_post, _on_frame)
    app_handler_add(h.load_post, _on_load)


def lvp_unregister():
    h = bpy.app.handlers
    for lst, fn in ((h.depsgraph_update_post, _on_depsgraph),
                    (h.frame_change_post, _on_frame),
                    (h.load_post, _on_load)):
        if fn in lst:
            lst.remove(fn)
    try:
        del bpy.types.PoseBone.fskr_vcol
    except Exception:
        pass
