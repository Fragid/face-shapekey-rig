"""표정 프리셋 뷰포트 컨트롤러.

세로 목록 틀(프리셋 이름 라벨) + 손잡이. 손잡이를 위아래로 끌어 어느 줄에
놓으면 그 표정이 바로 적용된다. 자동 키(Blender 자동 키 또는 '선택하면 키
삽입')가 켜져 있으면 현재 프레임에 표정 키가 들어간다.

값의 기준은 리그 프로퍼티 fskr_pre_<uid> (지금 표정 번호, Constant 키).
손잡이는 그 값을 따라다니는 표시/입력 장치일 뿐이라 렌더에는 영향이 없다.
손잡이에 직접 찍힌 키는 프로퍼티 키로 옮기고 지운다.
"""

import bpy
from .core import app_handler_add, draw_add, draw_remove
import json
from math import floor

from mathutils import Matrix, Vector

from .core import (
    TGL,
    _EN,
    _JA,
    _ZH,
    _action_fcurves,
    _ensure_root,
    _next_position,
    _redraw_ui,
    _to_object_mode,
    _tr,
)

_EN.update({
    "표정 컨트롤러 만들기": "Create expression controller",
    "표정": "Expression",
    "뷰포트 컨트롤러 (표정 목록)": "Viewport controller (expression list)",
    "뷰포트에 표정 이름 목록과 노란 손잡이를 만듭니다":
        "Adds a list of expression names with a yellow handle to the viewport",
    "손잡이를 위아래로 끌어 줄에 놓으면 그 표정으로 바뀝니다":
        "Drag the handle up/down onto a row to switch to that expression",
    "자동 키(●)가 켜져 있으면 현재 프레임에 키가 들어갑니다":
        "With auto keying on, a key is inserted at the current frame",
    "프리셋을 먼저 저장하세요": "Save a preset first",
    "표정 컨트롤러": "Expression controller",
})
_JA.update({"표정 컨트롤러 만들기": "表情コントローラー作成", "표정": "表情"})
_ZH.update({"표정 컨트롤러 만들기": "创建表情控制器", "표정": "表情"})

STEP = 0.032        # 줄 간격
WID = 0.20          # 목록 폭
_GRID_COLOR = (0.30, 0.42, 0.55)
_SEL_COLOR = (1.00, 0.86, 0.10)
_SEL_WIRE = 2.5

_LAST = {}          # uid -> 마지막으로 맞춘 표정 번호
_BUSY = [False]
_AUTO = {"pending": set(), "tried": {}}


def _base(st):
    return "FP_pre_" + st.uid


def _lbl(st):
    return "FPLBL_pre_" + st.uid


def prop_name(st):
    return getattr(st, "pkey", "") or ("fskr_pre_" + st.uid)


def _own(name, base):
    return name == base or name.startswith(base + "_")


def _canvas(s):
    try:
        from .face_ui import _canvas as cv
        return cv(s)
    except Exception:
        return s.eyes[0] if len(s.eyes) else None


def pre_exists(rig, st):
    return (rig is not None and st is not None
            and _base(st) in rig.data.bones)


def _meta(rig, st):
    fb = rig.pose.bones.get(_base(st) + "_frame") if rig else None
    if fb is None:
        return None
    try:
        return json.loads(fb.get("fskr_pre", "") or "{}") or None
    except Exception:
        return None


def _names(st):
    return [p.name for p in st.presets]


def pre_stale(rig, st):
    m = _meta(rig, st)
    return m is not None and int(m.get("n", -1)) != len(st.presets)


def _clamp(v, n):
    return max(0, min(int(n) - 1, int(v)))


def _loc_index(y, n):
    return _clamp(floor(-y / STEP + 0.5), n)


# ------------------------------------------------------------------
# 위젯
# ------------------------------------------------------------------

def _list_widget(coll, n):
    """원점 = 맨 윗줄 가운데. 아래(-Y)로 줄."""
    from .atlas_vp import _mesh_obj
    x0, x1 = -WID / 2, WID / 2
    y0 = STEP / 2
    v, e = [], []

    def line(a, b):
        v.extend([a, b])
        e.append((len(v) - 2, len(v) - 1))
    for j in range(n + 1):
        y = y0 - j * STEP
        line((x0, y, 0.0), (x1, y, 0.0))
    y1 = y0 - n * STEP
    line((x0, y0, 0.0), (x0, y1, 0.0))
    line((x1, y0, 0.0), (x1, y1, 0.0))
    return _mesh_obj(coll, "WGT_FP_pre_list_%d" % n, v, e)


# ------------------------------------------------------------------
# 생성 / 삭제
# ------------------------------------------------------------------

def pre_remove(context, rig, st):
    """본/라벨/위젯 제거 (표정 프로퍼티와 그 키는 유지)."""
    if rig is None or st is None:
        return
    from .atlas_vp import _remove_fcurves
    base = _base(st)
    for ob in list(bpy.data.objects):
        if _own(ob.name, _lbl(st)):
            bpy.data.objects.remove(ob)
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
    _LAST.pop(st.uid, None)


def pre_build(context, s, st):
    """표정 목록 컨트롤러를 (다시) 만든다. 다시 만들 땐 자리를 유지."""
    from .atlas_vp import (_bone_setup, _drv, _hide_bone, _label, _limit,
                           _none_widget, _sel_widget, _widget_coll)
    from .eye import _ensure_prop
    rig = s.rig
    if rig is None:
        return _tr("리그를 먼저 지정하세요")
    n = len(st.presets)
    if n == 0:
        pre_remove(context, rig, st)
        return _tr("프리셋을 먼저 저장하세요")
    base = _base(st)
    fname, hname, sname = base + "_frame", base, base + "_sel"
    from .layer_vp import _cur_col, set_vcol
    keep = None
    if fname in rig.data.bones:
        fb0 = rig.pose.bones[fname]
        hb0 = rig.pose.bones.get(hname)
        keep = (rig.data.bones[fname].head_local.copy(),
                fb0.location.copy(), fb0.scale.copy(),
                _cur_col(fb0, _GRID_COLOR),
                _cur_col(hb0, _SEL_COLOR) if hb0 else _SEL_COLOR)
    prev = context.view_layer.objects.active
    prev_mode = context.mode
    pre_remove(context, rig, st)
    _to_object_mode(context, rig)
    _ensure_root(context, s, rig)
    H = n * STEP
    if keep is not None:
        origin = keep[0]
    else:
        origin = _next_position(rig, H + 0.05)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = rig.data.edit_bones

    def new(name, parent):
        b = eb.new(name)
        b.head = origin
        b.tail = origin + Vector((0, 0, 0.02))
        b.roll = 0.0
        b.use_deform = False
        b.parent = eb[parent]
        return b
    new(fname, "FP_root")
    new(sname, fname)
    new(hname, fname)
    bpy.ops.object.mode_set(mode='OBJECT')

    coll = _widget_coll(context)
    pbs = rig.pose.bones
    fb, hb, sb = pbs[fname], pbs[hname], pbs[sname]
    _bone_setup(rig, fb, _list_widget(coll, n), (1.0, 1.0, 1.0))
    _bone_setup(rig, sb, _none_widget(coll), (1.0, 1.0, 1.0))
    _bone_setup(rig, hb, _sel_widget(coll), (WID / 0.92 * 0.97,
                                             STEP, 1.0))
    if hasattr(hb, "custom_shape_wire_width"):
        hb.custom_shape_wire_width = _SEL_WIRE
    hb.custom_shape_transform = sb
    hb.location = (0.0, 0.0, 0.0)
    _limit(hb, (0.0, 0.0), (-(n - 1) * STEP, 0.0))
    set_vcol(fb, keep[3] if keep else _GRID_COLOR)
    set_vcol(hb, keep[4] if keep else _SEL_COLOR, [sname])
    if keep is not None:
        fb.location = keep[1]
        fb.scale = keep[2]
    fb["fskr_pre"] = json.dumps({"n": n, "uid": st.uid,
                                 "names": _names(st)}, ensure_ascii=False)
    fb["fskr_spr_top"] = STEP / 2 + 0.036

    # 손잡이 모양은 줄 단위로 끊어 따라가는 숨은 본 위치에 그림
    hp = 'pose.bones["%s"].location[1]' % hname
    _drv(rig, 'pose.bones["%s"].location' % sname,
         ["0.0",
          "-min(max(floor(-y/%r+0.5),0),%d)*%r" % (STEP, n - 1, STEP),
          "0.0"],
         {"y": (rig, hp)})
    if "FP_toggle" in rig.data.bones:
        TH = TGL / 2
        tv = {"t": (rig, 'pose.bones["FP_toggle"].location[0]')}
        _drv(rig, 'pose.bones["%s"].custom_shape_scale_xyz' % fname,
             ["1.0*(t<%s)" % TH] * 3, tv)
        for n9 in (hname, sname):
            _drv(rig, 'pose.bones["%s"].scale' % n9, "t<%s" % TH, tv)

    from .core import arrange_for
    arr = arrange_for(s, fname)
    rig.data.bones[fname].hide_select = not arr
    rig.data.bones[hname].hide_select = arr
    _hide_bone(rig, sname)
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

    _label(context, rig, _lbl(st), "", 0.020, fname,
           at((0.0, STEP / 2 + 0.018, 0.0)),
           src=[(st.name + " · ", False), ("표정", True)])
    for i, nm in enumerate(_names(st)):
        ob = _label(context, rig, "%s_%d" % (_lbl(st), i), nm or "-",
                    0.0135, fname,
                    at((-WID / 2 + 0.012, -i * STEP, 0.0)))
        ob.data.align_x = 'LEFT'
    context.view_layer.update()
    fit_labels(rig, st, force=True)

    # 현재 표정 번호 프로퍼티
    P = prop_name(st)
    if P not in rig.keys():
        rig[P] = _clamp(st.preset_index, n)
    _ensure_prop(rig, P, n)
    _LAST.pop(st.uid, None)
    _sync(context.scene, from_frame=True)

    if prev_mode == 'POSE' or prev is rig:
        context.view_layer.objects.active = rig
        try:
            bpy.ops.object.mode_set(mode='POSE')
        except Exception:
            pass
    elif prev is not None:
        context.view_layer.objects.active = prev
    _redraw_ui(context)
    return ""


# ------------------------------------------------------------------
# 표정 적용 (목록 클릭 / 🔑 / 손잡이 공용)
# ------------------------------------------------------------------

def _autokey(st):
    if getattr(st, "preset_edit", False):
        return False
    try:
        ts = bpy.context.scene.tool_settings
        return bool(st.autokey or ts.use_keyframe_insert_auto)
    except Exception:
        return bool(getattr(st, "autokey", False))


def note(s, st, idx, key):
    """표정 번호를 프로퍼티(+키)와 손잡이에 반영 (표정 자체는 이미 적용됨)."""
    rig = s.rig
    if rig is None or st is None:
        return
    from .eye import _ensure_prop
    n = len(st.presets)
    if n == 0:
        return
    P = prop_name(st)
    _ensure_prop(rig, P, n)
    rig[P] = _clamp(idx, n)
    if key:
        try:
            from .atlas import _key
            _key(rig, P)
        except Exception:
            pass
    hb = rig.pose.bones.get(_base(st))
    if hb is not None and _loc_index(hb.location[1], n) != rig[P]:
        hb.location[1] = -rig[P] * STEP
    _LAST[st.uid] = int(rig[P])


def _pick(s, st, idx, key):
    from .face_ui import preset_apply
    from . import eye as EY
    if not (0 <= idx < len(st.presets)):
        return
    groups = None    # 항상 전체 적용
    preset_apply(s, st, st.presets[idx], groups, key)
    if st.preset_index != idx:
        EY._PRESET_MUTE["on"] = True
        try:
            st.preset_index = idx
        finally:
            EY._PRESET_MUTE["on"] = False
    note(s, st, idx, key)


# ------------------------------------------------------------------
# 손잡이 <-> 표정 번호 동기화
# ------------------------------------------------------------------

def _absorb(scene, s, rig, st, n):
    """손잡이에 찍힌 키를 표정 번호 키로 옮기고 손잡이 키는 지운다."""
    ad = rig.animation_data
    if ad is None:
        return False
    pre = 'pose.bones["%s"].' % _base(st)
    mine = [fc for fc in _action_fcurves(ad) if fc.data_path.startswith(pre)]
    if not mine:
        return False
    from .atlas import _key
    from .atlas_vp import _remove_fcurves
    from .eye import _ensure_prop
    P = prop_name(st)
    _ensure_prop(rig, P, n)
    ly = next((fc for fc in mine if fc.data_path == pre + "location"
               and fc.array_index == 1), None)
    cur = scene.frame_current
    keep = None
    if ly is not None:
        for kp in list(ly.keyframe_points):
            f = int(round(kp.co[0]))
            i = _loc_index(kp.co[1], n)
            if f == cur:
                keep = i
                continue
            rig[P] = i
            _key(rig, P, f)
        if keep is None:
            keep = _loc_index(ly.evaluate(cur), n)
    _remove_fcurves(ad, mine)
    if keep is not None:
        # 현재 프레임 키 = 표정 전체를 이 프레임에 키
        _pick(s, st, keep, True)
    return True


def relabel(rig, st, m=None):
    """프리셋 이름이 바뀌면 뷰포트 라벨 글자만 바로 고친다."""
    if rig is None or st is None:
        return
    if m is None:
        m = _meta(rig, st)
    if not m or int(m.get("n", -1)) != len(st.presets):
        return
    names = _names(st)
    if m.get("names") == names:
        return
    m["names"] = names
    fb = rig.pose.bones.get(_base(st) + "_frame")
    if fb is not None:
        fb["fskr_pre"] = json.dumps(m, ensure_ascii=False)
    fit_labels(rig, st, force=True)


_FIT = {}   # 캔버스 uid -> 마지막으로 맞춘 (크기·이름) 서명


def fit_labels(rig, st, force=False):
    """목록 틀 크기에 맞춰 이름 라벨을 찌그러짐 없이, 넘치면 '...'로."""
    from .atlas_vp import fit_label, _lbl_body
    fb = rig.pose.bones.get(_base(st) + "_frame")
    if fb is None:
        return
    fw = rig.matrix_world @ fb.matrix
    sx = Vector(fw.col[0][:3]).length
    names = _names(st)
    # 제목 (언어를 바꾸면 글자가 바뀌므로 원문을 매번 다시 만듦)
    tob = bpy.data.objects.get(_lbl(st))
    title = ""
    if tob is not None:
        try:
            title = _lbl_body(json.loads(tob.get("fskr_lbl", "[]")))
        except Exception:
            title = ""
        title = title or tob.data.body
    sig = (round(sx, 6), round(Vector(fw.col[1][:3]).length, 6),
           tuple(names), title, tob.data.body if tob else "")
    if not force and _FIT.get(st.uid) == sig:
        return
    if tob is not None:
        fit_label(tob, title, (WID + 0.02) * sx)
    sig = sig[:4] + (tob.data.body if tob else "",)
    _FIT[st.uid] = sig
    avail = (WID - 0.024) * sx
    for i, nm in enumerate(names):
        ob = bpy.data.objects.get("%s_%d" % (_lbl(st), i))
        fit_label(ob, nm or "-", avail)


def name_cb(preset, context):
    """FSKR_FacePreset.name 업데이트 콜백."""
    try:
        s = context.scene.fskr
        for st in s.eyes:
            if any(p == preset for p in st.presets):
                relabel(s.rig, st)
                break
    except Exception as e:
        print("FSKR preset relabel:", e)


def _sync(scene, from_frame=False):
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
    if getattr(st, "preset_edit", False):
        return       # 프리셋 편집 중: 고른 프리셋 고정 (프레임을 옮겨도)
    hb = rig.pose.bones.get(_base(st))
    if hb is None:
        return
    n = len(st.presets)
    m = _meta(rig, st) or {}
    if n == 0 or int(m.get("n", -1)) != n:
        sig = n
        if _AUTO["tried"].get(st.uid) != sig:
            _AUTO["tried"][st.uid] = sig
            schedule(st.uid)
        return
    # 이름만 바뀌면 라벨 글자만 고친다
    relabel(rig, st, m)
    fit_labels(rig, st)   # 틀 크기를 바꾸면 글자 비율 유지 + 넘치면 '...'

    if _absorb(scene, s, rig, st, n):
        from_frame = True
    P = prop_name(st)
    try:
        cur = _clamp(int(round(float(rig.get(P, st.preset_index)))), n)
    except Exception:
        cur = _clamp(st.preset_index, n)
    loc = _loc_index(hb.location[1], n)
    last = _LAST.get(st.uid)
    if loc != cur:
        if not from_frame and last is not None and loc != last:
            _pick(s, st, loc, _autokey(st))   # 사용자가 손잡이를 옮김
            cur = loc
        else:
            hb.location[1] = -cur * STEP      # 값(키)이 바뀜 → 손잡이가 따라감
    if from_frame and st.preset_index != cur:
        from . import eye as EY
        EY._PRESET_MUTE["on"] = True
        try:
            st.preset_index = cur
        finally:
            EY._PRESET_MUTE["on"] = False
    _LAST[st.uid] = cur


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
        print("FSKR preset vp:", e)
    finally:
        _BUSY[0] = False


@bpy.app.handlers.persistent
def _on_depsgraph(scene, depsgraph=None):
    _sync_safe(scene, False)


@bpy.app.handlers.persistent
def _on_frame(scene, depsgraph=None):
    _sync_safe(scene, True)


# ------------------------------------------------------------------
# 예약 실행 (UI 콜백/핸들러 밖에서 본 편집)
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
            if st is not None and st.uid in pend and \
                    pre_exists(s.rig, st):
                pre_build(c2, s, st)
                from .layer_vp import auto_layout
                auto_layout(c2)
    except Exception as e:
        print("FSKR preset vp rebuild:", e)
    return None


def schedule(uid):
    _AUTO["pending"].add(uid)
    try:
        if not bpy.app.timers.is_registered(_auto_tick):
            bpy.app.timers.register(_auto_tick, first_interval=0.05)
    except Exception:
        pass


@bpy.app.handlers.persistent
def _on_load(*_a):
    _LAST.clear()
    _AUTO["tried"].clear()


# ------------------------------------------------------------------
# 오퍼레이터
# ------------------------------------------------------------------

class FSKR_OT_preset_vp(bpy.types.Operator):
    bl_idname = "fskr.preset_vp"
    bl_label = "표정 컨트롤러"
    bl_description = ("뷰포트에 표정 목록 컨트롤러를 만들거나 다시 만들거나 "
                      "지웁니다. 손잡이를 끌어 표정을 고릅니다")
    bl_options = {'REGISTER', 'UNDO'}

    action: bpy.props.EnumProperty(items=(('BUILD', "만들기", ""),
                                          ('REMOVE', "지우기", "")),
                                   options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        return context.scene.fskr.rig is not None

    def execute(self, context):
        s = context.scene.fskr
        st = _canvas(s)
        if st is None:
            return {'CANCELLED'}
        if self.action == 'REMOVE':
            pre_remove(context, s.rig, st)
        else:
            err = pre_build(context, s, st)
            if err:
                self.report({'ERROR'}, err)
                return {'CANCELLED'}
            try:
                from .layer_vp import auto_layout
                auto_layout(context)   # 자동 정렬이 켜져 있으면 다른 컨트롤러와 맞춤
            except Exception:
                pass
        _redraw_ui(context)
        return {'FINISHED'}


pvp_classes = (FSKR_OT_preset_vp,)


def pvp_register():
    h = bpy.app.handlers
    app_handler_add(h.depsgraph_update_post, _on_depsgraph)
    app_handler_add(h.frame_change_post, _on_frame)
    app_handler_add(h.load_post, _on_load)


def pvp_unregister():
    h = bpy.app.handlers
    for lst, fn in ((h.depsgraph_update_post, _on_depsgraph),
                    (h.frame_change_post, _on_frame),
                    (h.load_post, _on_load)):
        if fn in lst:
            lst.remove(fn)
