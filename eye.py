"""스프라이트 방식 — 눈 (파츠 레이어 합성).

눈 데칼 하나에 전용 머티리얼을 만들고, 그 안에서 파츠 레이어(흰자,
눈동자, 하이라이트, 속눈썹, 눈썹 ...)를 Order(목록 순서, 위가 앞)대로
합성한다.

* 레이어마다 스프라이트 시트 한 장 (칸 = 그 파츠의 상태: 깜빡임 단계 등)
* 마스크: 레이어마다 "어느 레이어 안에서만 보일지" 지정. 마스크 레이어의
  지금 칸 모양을 그대로 따라가므로, 흰자 칸이 깜빡임으로 바뀌면 눈동자가
  잘리는 모양도 같이 바뀐다.
* 시선: 뷰포트 패드(FP_eye_*)를 움직이면 '시선 따라 이동'이 켜진
  레이어만 상하좌우로 움직인다. 칸 밖으로 나간 부분은 옆 칸이 비치지 않게
  잘린다.
* 오른쪽 눈 데칼이 왼쪽 눈의 시선/칸을 따라가게 연결 가능 (좌우 반전 옵션).

칸 값은 리그 커스텀 프로퍼티(Constant 키), 시선은 패드 본 위치(일반 키).
드라이버는 모두 Simple Expression이라 Python 자동 실행이 꺼져 있어도 동작.
"""
import bpy
from .core import app_handler_add, draw_add, draw_remove
import json
import re
from mathutils import Matrix, Vector
from math import radians

from .core import (
    FSKR_Settings,
    PAD,
    TGL,
    _EN,
    _JA,
    _ZH,
    _ensure_root,
    _next_position,
    _redraw_ui,
    _set_color,
    _stable_items,
    _text_toggle_driver,
    _to_object_mode,
    _tr,
)
from . import atlas as AT


_EN.update({
    "눈 (파츠 레이어)": "Eyes (part layers)",
    "눈 추가": "Add eye",
    "선택한 눈 데칼 메시에 파츠 레이어 합성 머티리얼을 만듭니다": "Creates a part-layer compositing material on the selected eye decal mesh",
    "눈 삭제": "Remove eye",
    "눈 머티리얼·시선 패드를 지우고 원래 머티리얼로 되돌립니다 (키는 유지)": "Removes the eye material and gaze pad and restores the original materials (keys are kept)",
    "파츠 추가": "Add part", "파츠 삭제": "Remove part",
    "앞으로": "Forward", "뒤로": "Backward",
    "위가 앞 (위에 있을수록 앞에 그려짐)": "Top is front (higher = drawn in front)",
    "마스크": "Mask", "없음": "None",
    "이 레이어 안에서만 보이기": "Visible only inside this layer",
    "시선 따라 이동": "Follow gaze", "이동 배율": "Gaze multiplier",
    "칸 따라가기": "Follow cell of",
    "시선": "Gaze", "가로 범위": "X range", "세로 범위": "Y range",
    "다른 눈 따라가기": "Follow other eye",
    "따라갈 때 좌우 반전": "Mirror X when following",
    "시선 패드: 뷰포트에서 핸들을 끌어 눈동자를 움직입니다": "Gaze pad: drag the handle in the viewport to move the irises",
    "눈 데칼(메시)을 선택하고 + 를 누르세요": "Select an eye decal mesh and press +",
    "파츠가 없습니다. + 로 흰자부터 추가하세요": "No parts. Add the eye white first with +",
    "적용 (머티리얼 재구성)": "Apply (rebuild material)",
    "시선 키": "Key gaze", "칸 키": "Key cell",
    "시선 초기화": "Reset gaze",
    "이미지를 고르세요": "Pick an image",
    "자체 칸": "Own cell",
    "합성 모드": "Blend mode", "불투명도": "Opacity",
    "얼굴 캔버스 (눈·입 파츠)": "Face canvas (eye & mouth parts)",
    "얼굴 캔버스 만들기": "Create face canvas", "얼굴 캔버스": "Face canvas",
    "얼굴 메시 편집 모드에서 눈~입 면을 고르고 누르세요": "Select the eye-to-mouth faces in Edit Mode of the face mesh, then press",
    "기존 메시를 캔버스로": "Use existing mesh as canvas",
    "얼굴 면을 먼저 선택하세요": "Select face polygons first",
    "얼굴 메시를 먼저 선택하세요.": "Select the face mesh first.",
    "1. 얼굴 메시 선택 → Tab(편집 모드)": "1. Select the face mesh → Tab (Edit Mode)",
    "2. 눈썹 위~턱까지 얼굴 앞면을 면 선택": "2. Select the front faces from above the brows to the chin",
    "3. 얼굴 캔버스 만들기": "3. Create face canvas",
    "얼굴 영역이 지정되지 않았습니다.": "No face area specified.",
    "Tab으로 편집 모드에 들어가 캔버스로 쓸 얼굴 앞면(눈썹 위~턱)을 면 선택한 뒤 다시 누르세요.": "Enter Edit Mode (Tab), select the front faces for the canvas (brows to chin), then press again.",
    "선택된 면이 없습니다.": "No faces selected.",
    "캔버스로 쓸 얼굴 앞면(눈썹 위~턱)을 면 선택한 뒤 다시 누르세요. (점·선만 선택하면 면이 잡히지 않습니다)": "Select the front faces for the canvas (brows to chin) and press again. (Selecting only vertices/edges does not select faces)",
    "선택된 면이 없습니다. 얼굴 앞면을 면 선택하세요": "No faces selected. Select the front faces of the face",
    "캔버스를 만들지 못했습니다": "Could not create the canvas",
    "얼굴 캔버스를 만들었습니다: ": "Face canvas created: ",
    "띄우기": "Offset", "UV 여백": "UV margin",
    "종류": "Type", "파츠": "Part", "입 (스프라이트 시트)": "Mouth (sprite sheet)",
    "입 시트": "Mouth sheet",
    "칸은 입 시트(시퀀스·립싱크·뷰포트 컨트롤러)로 바뀝니다": "Cells are driven by the mouth sheet (sequences, lip sync, viewport controller)",
    "배치": "Placement", "회전": "Rotation", "배치 초기화": "Reset placement",
    "데칼 UV를 0~1로 펴기": "Fit decal UV to 0-1",
    "데칼 UV를 0~1로 폈습니다": "Decal UV fitted to 0-1",
    "클리핑 마스크": "Clipping mask", "대칭 복사": "Symmetry copy",
    "색조/채도/명도": "Hue/Saturation/Lightness",
    "색조": "Hue", "채도": "Saturation", "명도": "Lightness",
    "파츠: ": "Parts: ",
    " 파츠 전체를 좌우 반전해서 사용": " parts, all mirrored",
    "따라가는 눈의 파츠를 전부 좌우 반전해서 사용": "Use the followed eye's parts, mirrored",
    "일반": "Normal", "곱하기": "Multiply", "스크린": "Screen",
    "오버레이": "Overlay", "소프트 라이트": "Soft Light",
    "선형 라이트": "Linear Light", "더하기 (선형 닷지)": "Add (Linear Dodge)",
    "빼기": "Subtract", "어둡게": "Darken", "밝게": "Lighten",
    "닷지": "Color Dodge", "번": "Color Burn", "차이": "Difference",
    "색상": "Color",
})
_JA.update({
    "눈 (파츠 레이어)": "目 (パーツレイヤー)",
    "눈 추가": "目を追加", "파츠 추가": "パーツ追加",
    "시선 따라 이동": "視線に追従", "마스크": "マスク",
})
_ZH.update({
    "눈 (파츠 레이어)": "眼睛 (部件图层)",
    "눈 추가": "添加眼睛", "파츠 추가": "添加部件",
})


_MAT_PREFIX = "FSKR_EYE_"
_BONE_PREFIX = "FP_eye_"
_EPS = 1e-4


# ------------------------------------------------------------------
# 데이터
# ------------------------------------------------------------------

def _rig():
    try:
        return bpy.context.scene.fskr.rig
    except Exception:
        return None


def _owner(layer):
    """레이어가 속한 눈 스택."""
    try:
        for st in bpy.context.scene.fskr.eyes:
            for L in st.layers:
                if L == layer:
                    return st
    except Exception:
        pass
    return None


def _find(s, uid):
    return next((e for e in s.eyes if e.uid == uid), None)


def _layer(st, lid):
    return next((L for L in st.layers if L.lid == lid), None) if lid else None


def _pk(L):
    return getattr(L, "pkey", "") or ""


def _prop_cell(st, L):
    k = _pk(L)
    return (k + "_Cell") if k else "fskr_ey_%s_%s" % (st.uid, L.lid)


def preset_editing(s=None):
    """프리셋 편집 중이면 키를 넣지 않는다 (키프레임과 충돌 방지)."""
    try:
        s = s or bpy.context.scene.fskr
        return any(getattr(st, "preset_edit", False) for st in s.eyes)
    except Exception:
        return False


def _prop_cell_pv(cp):
    """편집 모드용 고정 칸 (키 없음, -1 = 꺼짐 → 키프레임 값 사용)."""
    return cp + ("_pv" if cp.startswith("fskr_ey_") else "_Edit")


def _pv_cell_ensure(rig, cp, n):
    p = _prop_cell_pv(cp)
    if p not in rig.keys():
        rig[p] = -1
    try:
        rig.id_properties_ui(p).update(min=-1, max=max(0, n - 1))
    except Exception:
        pass


def part_cell_now(rig, st, L):
    """지금 보이는 칸 번호 (편집 모드면 고정해 둔 칸)."""
    cp = _prop_cell(st, L)
    pv = rig.get(_prop_cell_pv(cp), -1) if rig is not None else -1
    try:
        pv = int(round(float(pv)))
    except Exception:
        pv = -1
    if L.edit_on and pv >= 0:
        return max(0, min(_ncells(L) - 1, pv))
    return max(0, min(_ncells(L) - 1, _get(rig, cp)))


def part_edit_show(st, L, v):
    """편집 모드: 키프레임과 상관없이 v 칸을 고정해서 보여 줌 (키 없음)."""
    rig = _rig()
    if rig is None:
        return
    cp = _prop_cell(st, L)
    _pv_cell_ensure(rig, cp, _ncells(L))
    rig[_prop_cell_pv(cp)] = max(0, min(_ncells(L) - 1, int(v)))
    try:
        rig.update_tag()
        ob = bpy.data.objects.get(st.target)
        if ob is not None:
            ob.update_tag()
    except Exception:
        pass


def _pv_wired_or_build(s, st, cp):
    """예전 머티리얼(편집 모드 변수 없음)이면 한 번 다시 만든다."""
    dp = '["%s"]' % _prop_cell_pv(cp)
    for m in bpy.data.materials:
        nt = m.node_tree
        ad = nt.animation_data if nt else None
        if ad is None:
            continue
        for fc in ad.drivers:
            for v in fc.driver.variables:
                if v.targets[0].data_path == dp:
                    return
    for st9 in s.eyes:
        if st9.built:
            try:
                eye_build(s, st9)
            except Exception as e:
                print("FSKR edit mode rebuild:", e)


def _part_edit_cb(self, context):
    st = _owner(self)
    rig = _rig()
    if st is None or rig is None:
        return
    cp = _prop_cell(st, self)
    if self.edit_on:
        part_edit_show(st, self, _get(rig, cp))
        _pv_wired_or_build(context.scene.fskr, st, cp)
    else:
        _pv_cell_ensure(rig, cp, _ncells(self))
        rig[_prop_cell_pv(cp)] = -1
        try:
            rig.update_tag()
        except Exception:
            pass
    _redraw_ui(context)


def _pad_name(st):
    return _BONE_PREFIX + st.uid


def _ncells(L):
    return max(1, int(L.cols)) * max(1, int(L.rows))


def _get(rig, prop):
    try:
        return int(round(float(rig.get(prop, 0))))
    except Exception:
        return 0


def _show_vp_cb(self, context):
    from .layer_vp import show_vp_cb
    show_vp_cb(self, context)


_MUTE_REBUILD = {"on": False}


def _rebuild_cb(self, context):
    if _MUTE_REBUILD["on"]:
        return
    st = _owner(self) if isinstance(self, FSKR_EyeLayer) else self
    if st is not None and st.built:
        try:
            eye_build(context.scene.fskr, st)
        except Exception as e:
            print("FSKR eye rebuild:", e)
    _redraw_ui(context)


# ----- 썸네일 (스프라이트 시트 코드 재사용) -----

class _Duck:
    """atlas._thumbs_build가 요구하는 최소 속성."""
    def __init__(self, uid, L):
        self.uid = uid
        self.image = L.image
        self.cols = L.cols
        self.rows = L.rows
        self.cells = ()


_TH_PENDING = {}


def _thumb_uid(st, L):
    return "EY_%s_%s" % (st.uid, L.lid)


def _thumbs_ready(st, L):
    u = _thumb_uid(st, L)
    return (u in AT._PREV_ICONS
            and AT._PREV_SIG.get(u) == AT._thumb_sig(_Duck(u, L)))


def _thumbs_tick():
    try:
        s = bpy.context.scene.fskr
        for u, (suid, lid) in list(_TH_PENDING.items()):
            st = _find(s, suid)
            L = _layer(st, lid) if st else None
            if L is not None and L.image:
                try:
                    AT._thumbs_build(_Duck(u, L))
                except Exception:
                    pass
        _redraw_ui(bpy.context)
    except Exception:
        pass
    _TH_PENDING.clear()
    return None


def _thumbs_request(st, L):
    u = _thumb_uid(st, L)
    if u in _TH_PENDING:
        return
    _TH_PENDING[u] = (st.uid, L.lid)
    try:
        if not bpy.app.timers.is_registered(_thumbs_tick):
            bpy.app.timers.register(_thumbs_tick, first_interval=0.05)
    except Exception:
        pass


# ----- 칸 피커 -----

def _cell_items(self, context):
    st = _owner(self)
    cols, rows = max(1, int(self.cols)), max(1, int(self.rows))
    u = _thumb_uid(st, self) if st else "EY_x"
    icons = AT._PREV_ICONS.get(u, {})
    items = []
    for r in range(rows):
        for c in range(cols):
            i = r * cols + c
            items.append((str(i), "%d-%d" % (r, c), "",
                          icons.get((r, c), 0), i))
    return _stable_items("eyc_" + u, items)


def _cell_get(self):
    st = _owner(self)
    rig = _rig()
    if st is None or rig is None:
        return 0
    return part_cell_now(rig, st, self)


def _cell_set(self, v):
    st = _owner(self)
    rig = _rig()
    if st is None or rig is None:
        return
    if self.edit_on and not preset_editing():
        part_edit_show(st, self, v)
        return
    _set_cell(st, self, v)


def _set_cell(st, L, v, key=None):
    rig = _rig()
    if rig is None:
        return
    p = _prop_cell(st, L)
    _ensure_prop(rig, p, _ncells(L))
    rig[p] = max(0, min(_ncells(L) - 1, int(v)))
    if key is None:
        try:
            key = bool(st.autokey or bpy.context.scene.tool_settings
                       .use_keyframe_insert_auto)
        except Exception:
            key = bool(st.autokey)
    if preset_editing():
        key = False
    if key:
        AT._key(rig, p)
    try:
        rig.update_tag()
        ob = bpy.data.objects.get(st.target)
        if ob is not None:
            ob.update_tag()
    except Exception:
        pass


def _ensure_prop(rig, prop, n):
    if prop not in rig.keys():
        rig[prop] = 0
    try:
        rig.id_properties_ui(prop).update(min=0, max=max(0, n - 1),
                                          soft_min=0, soft_max=max(0, n - 1),
                                          step=1)
    except Exception:
        pass


# ----- 레이어 선택지 (마스크 / 칸 따라가기) -----

def _other_layer_items(self, context, none_label):
    st = _owner(self)
    items = [("NONE", none_label, "", 0)]
    if st is not None:
        for i, L in enumerate(st.layers):
            if L.lid != self.lid:
                items.append((L.lid, L.name or L.lid, "", i + 1))
    key = "eyl_%s_%s_%s" % (st.uid if st else "x", self.lid, none_label)
    return _stable_items(key, items)


# ----- 부모 (페어런팅) -----

def layer_parent(st, L):
    """L의 부모 레이어 (없거나 잘못됐으면 None)."""
    if not getattr(L, "parent", ""):
        return None
    P = _layer(st, L.parent)
    return P if P is not None and P is not L else None


def layer_ancestors(st, L):
    out, seen = [], {L.lid}
    P = layer_parent(st, L)
    while P is not None and P.lid not in seen:
        out.append(P)
        seen.add(P.lid)
        P = layer_parent(st, P)
    return out


def _vis_prop(L):
    st = _owner(L)
    rig = _rig()
    if st is None or rig is None:
        return None, None
    try:
        s = bpy.context.scene.fskr
        ast, aL = _anim_source(s, st, L)
    except Exception:
        ast, aL = st, L
    return rig, _p_vis(ast, aL)


def _vis_raw(rig, L, v):
    try:
        s = bpy.context.scene.fskr
        ast, aL = _anim_source(s, _owner(L), L)
        rig[_p_vis(ast, aL)] = 1.0 if v else 0.0
        L["show"] = bool(v)
    except Exception:
        pass


def _vis_get(L):
    rig, p = _vis_prop(L)
    if rig is None or p not in rig.keys():
        try:
            return bool(L.get("show", True))
        except Exception:
            return True
    try:
        return float(rig[p]) >= 0.5
    except Exception:
        return True


def folder_group(st, F):
    """F와 함께 전환되는 폴더들 (같은 부모·같은 태그의 폴더, F 제외)."""
    return [G for G in st.layers if G.lid != F.lid
            and getattr(G, "kind", 'PART') == 'FOLDER'
            and G.parent == F.parent and G.tag == F.tag]


def _vis_set(L, v):
    rig, p = _vis_prop(L)
    L["show"] = bool(v)      # 예전 버전 호환용 값도 맞춤
    if rig is None:
        return
    if v and getattr(L, "kind", 'PART') == 'FOLDER':
        st9 = _owner(L)
        for G in (folder_group(st9, L) if st9 else ()):
            _vis_raw(rig, G, False)      # 폴더 하나만 켜기 (전환)
    new = p not in rig.keys()
    rig[p] = 1.0 if v else 0.0
    try:
        rig.id_properties_ui(p).update(min=0.0, max=1.0, soft_min=0.0,
                                       soft_max=1.0)
    except Exception:
        pass
    try:
        rig.update_tag()
        st = _owner(L)
        ob = bpy.data.objects.get(st.target) if st else None
        if ob is not None:
            ob.update_tag()
    except Exception:
        pass
    if new:     # 예전 머티리얼: 보이기 값을 쓰도록 한 번 다시 만들기
        try:
            st = _owner(L)
            if st is not None and st.built:
                eye_build(bpy.context.scene.fskr, st)
        except Exception as e:
            print("FSKR vis rebuild:", e)


def layer_visible(st, L):
    """실제로 보이는지: 자기 👁가 켜져 있고 부모(조상)도 모두 켜져 있을 때."""
    return bool(L.show) and all(A.show for A in layer_ancestors(st, L))


def layer_children(st, L):
    return [c for c in st.layers if c.lid != L.lid and c.parent == L.lid]


def layer_descendants(st, L):
    out, todo, seen = [], [L], {L.lid}
    while todo:
        n = todo.pop()
        for c in layer_children(st, n):
            if c.lid not in seen:
                seen.add(c.lid)
                out.append(c)
                todo.append(c)
    return out


def clip_chain(st, L):
    """이 레이어에 걸리는 클리핑 마스크들: 자기 것 + 부모·조상의 것 (상속).

    자기 자신이나 자기 자손을 마스크로 쓰는 경우(순환)는 뺀다.
    """
    bad = {L.lid} | {d.lid for d in layer_descendants(st, L)}
    out = []
    for n in [L] + layer_ancestors(st, L):
        if n.clip and n.clip not in bad and n.clip not in out:
            out.append(n.clip)
    return out


def layer_depth(st, L):
    return len(layer_ancestors(st, L))


def _parent_items(self, context):
    st = _owner(self)
    items = [("NONE", _tr("없음"), "", 0)]
    if st is not None:
        bad = {self.lid} | {d.lid for d in layer_descendants(st, self)}
        for i, L in enumerate(st.layers):
            if L.lid not in bad:
                items.append((L.lid, L.name or L.lid, "", i + 1))
    key = "eyp_%s_%s" % (st.uid if st else "x", self.lid)
    return _stable_items(key, items)


def _parent_get(self):
    v = self.parent or "NONE"
    for t in _parent_items(self, None):
        if t[0] == v:
            return t[3]
    return 0


def _parent_set(self, n):
    lid = ""
    for t in _parent_items(self, None):
        if t[3] == n:
            lid = "" if t[0] == "NONE" else t[0]
            break
    st = _owner(self)
    if st is None:
        self["parent"] = lid
        return
    try:
        set_parent(bpy.context.scene.fskr, st, self, lid)
    except Exception as e:
        print("FSKR parent:", e)


def _chain_offset(s, st, L):
    """조상들의 위치 X/Y 합 (시선 제외)."""
    rig = s.rig
    ox = oy = 0.0
    if rig is None:
        return ox, oy
    for A in layer_ancestors(st, L):
        ast, aL = _anim_source(s, st, A)
        ox += float(rig.get(_p_px(ast, aL), 0.0))
        oy += float(rig.get(_p_py(ast, aL), 0.0))
    return ox, oy


def _shift_prop(rig, prop, d):
    if abs(d) < 1e-9:
        return
    rig[prop] = float(rig.get(prop, 0.0)) + d
    for fc in AT._fcurves_for(rig, '["%s"]' % prop):
        for kp in fc.keyframe_points:
            kp.co.y += d
            kp.handle_left.y += d
            kp.handle_right.y += d
        fc.update()


# ----- 부모 상속 (위치·회전·크기): 2D 아핀 x' = [[a,b],[c,d]]·x + (tx,ty) -----
#   자식의 최종 배치 = 부모의 '지금' 월드 배치 ∘ (묶을 때의 부모 월드 배치)^-1
#                      ∘ 자식 자체 배치   (Child Of 의 Set Inverse 와 같음)
#   묶을 때의 부모 배치(bind)는 레이어에 저장 → 지정 순간 그림이 제자리

_AFF_I = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def aff_mul(A, B):
    """A∘B (B 먼저)."""
    a, b, c, d, tx, ty = A
    e, f, g, h, ux, uy = B
    return (a * e + b * g, a * f + b * h, c * e + d * g, c * f + d * h,
            a * ux + b * uy + tx, c * ux + d * uy + ty)


def aff_inv(A):
    a, b, c, d, tx, ty = A
    det = a * d - b * c
    if abs(det) < 1e-12:
        det = 1e-12
    ia, ib, ic, id_ = d / det, -b / det, -c / det, a / det
    return (ia, ib, ic, id_, -(ia * tx + ib * ty), -(ic * tx + id_ * ty))


def aff_apply(A, x, y):
    a, b, c, d, tx, ty = A
    return a * x + b * y + tx, c * x + d * y + ty


def aff_rs(rot_deg, kx, ky, tx=0.0, ty=0.0):
    """R(rot)·diag(kx,ky) + t."""
    import math as _m
    t = _m.radians(rot_deg)
    co, si = _m.cos(t), _m.sin(t)
    return (co * kx, -si * ky, si * kx, co * ky, tx, ty)


def aff_svd(A):
    """A의 2x2 = R(al)·diag(s1,s2)·R(be) 로 분해 (Mapping 노드 두 개용).
    반환 (al, s1, s2, be) — 각은 라디안, s2는 음수일 수 있음(반전)."""
    import math as _m
    a, b, c, d = A[:4]
    E, F = (a + d) / 2.0, (a - d) / 2.0
    G, H = (c + b) / 2.0, (c - b) / 2.0
    Q, R = _m.hypot(E, H), _m.hypot(F, G)
    s1, s2 = Q + R, Q - R
    a1, a2 = _m.atan2(G, F), _m.atan2(H, E)
    th, ph = (a2 - a1) / 2.0, (a2 + a1) / 2.0
    return ph, s1, s2, th


def _cell_vals(s, st, L):
    """지금 칸의 칸별 보정 (lpx, lpy, lrot, lkx, lky). 일반 파츠만."""
    if _px_tab(s, st, L) is None:
        return 0.0, 0.0, 0.0, 1.0, 1.0
    try:
        x = cell_table(s, st, L)
        e = x.entry(*x.cur) if x is not None else None
    except Exception:
        e = None
    if e is None:
        return 0.0, 0.0, 0.0, 1.0, 1.0
    return (float(e.lpx), float(e.lpy), float(e.lrot),
            max(abs(float(e.lkx)), 1e-3), max(abs(float(e.lky)), 1e-3))


def layer_local_aff(s, st, L):
    """L 자체 배치: 파츠 공간 q(반전 전) → 데칼 UV (시선 제외)."""
    rig = s.rig
    ast, aL = _anim_source(s, st, L)
    if rig is not None:
        _ensure_anim_props(rig, ast, aL)
        g = rig.get
    else:
        def g(k, d=0.0):
            return d
    sx = max(float(g(_p_sx(ast, aL), 1.0)), 1e-3)
    sy = sx * float(L.aspect or 1.0) if L.scale_lock \
        else max(float(g(_p_sy(ast, aL), 1.0)), 1e-3)
    rot = float(g(_p_rot(ast, aL), 0.0))
    px = float(g(_p_px(ast, aL), 0.0))
    py = float(g(_p_py(ast, aL), 0.0))
    lpx, lpy, lr, lkx, lky = _cell_vals(s, st, L)
    mu, mv = marker_uv(st, L.tag)
    pcu, pcv = _pivot_eff(L)
    M = aff_rs(rot + lr, sx * lkx, sy * lky)
    tx = mu + pcu - 0.5 + px + lpx
    ty = mv + pcv - 0.5 + py + lpy
    # q → T + M(q - pc)
    return aff_mul((1.0, 0.0, 0.0, 1.0, tx, ty),
                   aff_mul(M, (1.0, 0.0, 0.0, 1.0, -pcu, -pcv)))


def _legacy_inh(s, st, L):
    """1.0.218까지: 조상의 위치(+칸별 위치)만 더해 따라감."""
    rig = s.rig
    ox = oy = 0.0
    for A in layer_ancestors(st, L):
        ast, aL = _anim_source(s, st, A)
        if rig is not None:
            ox += float(rig.get(_p_px(ast, aL), 0.0))
            oy += float(rig.get(_p_py(ast, aL), 0.0))
        c = _cell_vals(s, st, A)
        ox += c[0]
        oy += c[1]
    return (1.0, 0.0, 0.0, 1.0, ox, oy)


def layer_bind(L):
    b = tuple(float(v) for v in L.bind)
    return b if len(b) == 6 else _AFF_I


def layer_inh_aff(s, st, L, _seen=None):
    """부모에게서 물려받는 배치 (데칼 → 데칼)."""
    P = layer_parent(st, L)
    if P is None:
        return _AFF_I
    _seen = (_seen or set()) | {L.lid}
    if P.lid in _seen:
        return _AFF_I
    if not L.bind_ok:
        return _legacy_inh(s, st, L)
    return aff_mul(layer_world_aff(s, st, P, _seen), aff_inv(layer_bind(L)))


def layer_world_aff(s, st, L, _seen=None):
    """L의 최종 배치: 파츠 공간 q → 데칼 UV (부모 상속 포함, 시선 제외)."""
    return aff_mul(layer_inh_aff(s, st, L, _seen), layer_local_aff(s, st, L))


def bind_migrate(s, st):
    """예전 자식(묶음 정보 없음)을 지금 보이는 그대로 새 방식으로 옮김.
    바뀐 레이어 수."""
    n = 0
    todo = [L for L in st.layers if layer_parent(st, L) is not None
            and not L.bind_ok]
    todo.sort(key=lambda L: len(layer_ancestors(st, L)))   # 위 → 아래
    for L in todo:
        inh = _legacy_inh(s, st, L)
        P = layer_parent(st, L)
        w = layer_world_aff(s, st, P)
        L.bind = aff_mul(aff_inv(inh), w)
        L.bind_ok = True
        n += 1
    return n


def _scale_prop(rig, prop, k):
    if abs(k - 1.0) < 1e-9:
        return
    rig[prop] = float(rig.get(prop, 1.0)) * k
    for fc in AT._fcurves_for(rig, '["%s"]' % prop):
        for kp in fc.keyframe_points:
            kp.co.y *= k
            kp.handle_left.y *= k
            kp.handle_right.y *= k
        fc.update()


def _bake_inh(s, st, L, inh):
    """부모를 풀 때: 물려받던 배치를 L 자체 값(위치·회전·크기)에 굽기."""
    import math as _m
    rig = s.rig
    if rig is None:
        return
    ast, aL = _anim_source(s, st, L)
    _ensure_anim_props(rig, ast, aL)
    W = layer_local_aff(s, st, L)
    pcu, pcv = _pivot_eff(L)
    # 기준점 위치 T, 선형부 M 은 바뀌고, 칸별 보정은 그대로 둠
    T0 = aff_apply(W, pcu, pcv)
    T1 = aff_apply(inh, *T0)
    W1 = aff_mul(inh, W)
    a, b, c, d = W1[:4]
    a0, b0, c0, d0 = W[:4]
    th1 = _m.atan2(c, a)
    th0 = _m.atan2(c0, a0)
    kx1, kx0 = _m.hypot(a, c), _m.hypot(a0, c0)
    det1, det0 = a * d - b * c, a0 * d0 - b0 * c0
    ky1, ky0 = det1 / max(kx1, 1e-9), det0 / max(kx0, 1e-9)
    _shift_prop(rig, _p_px(ast, aL), T1[0] - T0[0])
    _shift_prop(rig, _p_py(ast, aL), T1[1] - T0[1])
    dr = _m.degrees(th1 - th0)
    dr = (dr + 180.0) % 360.0 - 180.0
    _shift_prop(rig, _p_rot(ast, aL), dr)
    _scale_prop(rig, _p_sx(ast, aL), kx1 / max(kx0, 1e-9))
    if not L.scale_lock and ky0 * ky1 > 0:
        _scale_prop(rig, _p_sy(ast, aL), ky1 / ky0)


def set_parent(s, st, L, lid, build=True):
    """부모 지정/해제. 그림이 제자리에 있도록 보정 (Keep Transform)."""
    if lid == L.lid or lid in {d.lid for d in layer_descendants(st, L)}:
        return
    if (L.parent or "") == (lid or ""):
        return
    # 위에서부터 예전 방식 자식을 먼저 옮겨 둠 (계산이 같은 기준이 되게)
    try:
        bind_migrate(s, st)
    except Exception as e:
        print("FSKR bind migrate:", e)
    inh0 = layer_inh_aff(s, st, L)
    L["parent"] = lid
    P = layer_parent(st, L)
    if P is not None:
        # 새 부모 아래에서도 지금 보이는 그대로: bind = inh0^-1 ∘ 부모 월드
        L.bind = aff_mul(aff_inv(inh0), layer_world_aff(s, st, P))
        L.bind_ok = True
    else:
        L.bind_ok = False
        L.bind = _AFF_I
        try:
            _bake_inh(s, st, L, inh0)
        except Exception as e:
            print("FSKR unparent bake:", e)
    # 부모(조상)가 이미 시선을 따라가면 자식의 시선은 끔 (두 번 움직이지 않게)
    if lid and L.look and any(A.look for A in layer_ancestors(st, L)):
        L["look"] = False
    tree_normalize(st)
    if build:
        eye_build(s, st)


def _tree_order(st, key):
    """트리 순서의 레이어 lid 목록 (위 = 앞). 자식 묶음은 부모 바로 위."""
    roots = [L for L in st.layers if layer_parent(st, L) is None
             or L.lid in {a.lid for a in layer_descendants(st, L)}]
    seen = set()

    def block(n):
        if n.lid in seen:
            return []
        seen.add(n.lid)
        seq = []
        for c in sorted(layer_children(st, n), key=key):
            seq += block(c)
        return seq + [n.lid]
    out = []
    for r in sorted(roots, key=key):
        out += block(r)
    for L in st.layers:          # 혹시 빠진 것 (순환 등)
        if L.lid not in seen:
            out.append(L.lid)
    return out


def _apply_order(st, order):
    sel = st.layers[st.layer_index].lid \
        if 0 <= st.layer_index < len(st.layers) else ""
    for i, lid in enumerate(order):
        cur = next(k for k, x in enumerate(st.layers) if x.lid == lid)
        if cur != i:
            st.layers.move(cur, i)
    if sel:
        st.layer_index = next((k for k, x in enumerate(st.layers)
                               if x.lid == sel), st.layer_index)


def tree_normalize(st):
    """자식(과 그 자손)을 부모 바로 위로 모은다. 형제끼리 순서는 유지."""
    if not any(L.parent for L in st.layers):
        return
    idx = {L.lid: k for k, L in enumerate(st.layers)}
    _apply_order(st, _tree_order(st, lambda n: idx[n.lid]))


def tree_move(st, L, direction):
    """형제끼리 한 칸 이동 (자식이 있으면 묶음째)."""
    idx = {x.lid: k for k, x in enumerate(st.layers)}
    P = layer_parent(st, L)
    sibs = layer_children(st, P) if P is not None else \
        [x for x in st.layers if layer_parent(st, x) is None]
    sibs.sort(key=lambda n: idx[n.lid])
    i = next(k for k, x in enumerate(sibs) if x.lid == L.lid)
    j = i + direction
    if not (0 <= j < len(sibs)):
        return False
    key = {x.lid: idx[x.lid] for x in st.layers}
    key[sibs[i].lid], key[sibs[j].lid] = key[sibs[j].lid], key[sibs[i].lid]
    _apply_order(st, _tree_order(st, lambda n: key[n.lid]))
    return True



def _clip_items(self, context):
    return _other_layer_items(self, context, _tr("없음"))


def _link_items(self, context):
    return _other_layer_items(self, context, _tr("자체 칸"))


def _mk_pick(field, items_fn):
    def get(self):
        v = getattr(self, field) or "NONE"
        for t in items_fn(self, None):
            if t[0] == v:
                return t[3]
        return 0

    def set_(self, n):
        for t in items_fn(self, None):
            if t[3] == n:
                setattr(self, field, "" if t[0] == "NONE" else t[0])
                return
        setattr(self, field, "")
    return get, set_


# ----- 시선 (패드 본 위치 프록시) -----

def _gaze_bone(st):
    rig = _rig()
    if rig is None:
        return None
    return rig.pose.bones.get(_pad_name(st))


def _mk_gaze(i):
    def get(self):
        pb = _gaze_bone(self)
        return float(pb.location[i] / PAD) if pb is not None else 0.0

    def set_(self, v):
        pb = _gaze_bone(self)
        if pb is None:
            return
        pb.location[i] = max(-1.0, min(1.0, v)) * PAD
        try:
            ts = bpy.context.scene.tool_settings
            if self.autokey or ts.use_keyframe_insert_auto:
                pb.keyframe_insert("location", index=i, group="Eye Gaze")
        except Exception:
            pass
    return get, set_


def _stack_items(self, context):
    items = [("NONE", _tr("없음"), "", 0)]
    try:
        for i, st in enumerate(bpy.context.scene.fskr.eyes):
            if st.uid != self.uid:
                items.append((st.uid, st.name, "", i + 1))
    except Exception:
        pass
    return _stable_items("eys_" + self.uid, items)


def _stack_pick_get(self):
    for t in _stack_items(self, None):
        if t[0] == (self.follow or "NONE"):
            return t[3]
    return 0


def _stack_pick_set(self, n):
    for t in _stack_items(self, None):
        if t[3] == n:
            self.follow = "" if t[0] == "NONE" else t[0]
            break
    _rebuild_cb(self, bpy.context)
    _pads_schedule()


def _pads_tick():
    """따라가는 눈은 시선 패드 제거, 혼자인 눈은 패드 생성 (UI 콜백 밖)."""
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
    try:
        with ctx.temp_override(**kw):
            c2 = bpy.context
            s = c2.scene.fskr
            rig = s.rig
            if rig is None:
                return None
            prev = c2.view_layer.objects.active
            for st in s.eyes:
                has = _pad_name(st) in rig.data.bones
                if _src_stack(s, st) is not st and has:
                    _pad_remove(c2, rig, st)
                elif not st.follow and not has:
                    _pad_build(c2, s, st)
            if prev is not None:
                try:
                    c2.view_layer.objects.active = prev
                except Exception:
                    pass
    except Exception as e:
        print("FSKR eye pads:", e)
    return None


def _pads_schedule():
    try:
        if not bpy.app.timers.is_registered(_pads_tick):
            bpy.app.timers.register(_pads_tick, first_interval=0.05)
    except Exception:
        pass


# ----- 마커 / 태그 (사용자 정의) -----

def _st_of_coll_item(item, attr):
    try:
        for st in bpy.context.scene.fskr.eyes:
            for x in getattr(st, attr):
                if x == item:
                    return st
    except Exception:
        pass
    return None


def find_marker(st, uid):
    return next((m for m in st.markers if m.uid == uid), None) if uid \
        else None


def find_tag(st, uid):
    return next((g for g in st.tags if g.uid == uid), None) if uid else None


def _marker_items(self, context):
    st = _st_of_coll_item(self, "tags")
    items = [("NONE", _tr("얼굴 가운데"), "마커 없이 캔버스 가운데 기준", 0)]
    if st is not None:
        for i, m in enumerate(st.markers):
            items.append((m.uid, m.name, "", i + 1))
    return _stable_items("emk_%s" % self.uid, items)


def _tag_marker_get(self):
    for it in _marker_items(self, None):
        if it[0] == (self.marker or "NONE"):
            return it[3]
    return 0


def _tag_marker_set(self, v):
    for it in _marker_items(self, None):
        if it[3] == v:
            self.marker = "" if it[0] == "NONE" else it[0]
            break
    st = _st_of_coll_item(self, "tags")
    if st is not None and st.built:
        try:
            eye_build(bpy.context.scene.fskr, st)
        except Exception as e:
            print("FSKR tag marker:", e)


def _tag_clip_items(self, context):
    st = _st_of_coll_item(self, "tags")
    items = [("NONE", _tr("없음"), "", 0)]
    if st is not None:
        for i, g in enumerate(st.tags):
            if g.uid != self.uid:
                items.append((g.uid, g.name, "", i + 1))
    return _stable_items("etc_%s" % self.uid, items)


def _tag_clip_get(self):
    for it in _tag_clip_items(self, None):
        if it[0] == (self.clip_tag or "NONE"):
            return it[3]
    return 0


def _tag_clip_set(self, v):
    for it in _tag_clip_items(self, None):
        if it[3] == v:
            self.clip_tag = "" if it[0] == "NONE" else it[0]
            break


def _marker_update(self, context):
    st = _st_of_coll_item(self, "markers")
    if st is not None and st.built:
        try:
            eye_build(context.scene.fskr, st)
        except Exception as e:
            print("FSKR marker rebuild:", e)


class FSKR_FaceMarker(bpy.types.PropertyGroup):
    """위치 마커: 이 태그들의 파츠가 놓일 기준점 (캔버스 UV)."""
    uid: bpy.props.StringProperty(default="")
    name: bpy.props.StringProperty(name="이름", default="마커")
    uv: bpy.props.FloatVectorProperty(
        name="위치", size=2, default=(0.5, 0.5), precision=3,
        update=_marker_update,
        description="캔버스 위 위치 (0~1, 정면 기준). 다시 찍거나 숫자로 조절")
    placed: bpy.props.BoolProperty(default=False)
    co: bpy.props.FloatVectorProperty(size=3, default=(0.0, 0.0, 0.0))


def _tag_over_cb(self, context):
    s = context.scene.fskr
    for st in s.eyes:
        if not any(g == self for g in st.tags):
            continue
        hit = False
        for L in st.layers:
            if L.tag == self.uid and L.over != self.over:
                L["over"] = self.over
                hit = True
        if hit and st.built:
            eye_build(s, st)
    _redraw_ui(context)


class FSKR_FaceTag(bpy.types.PropertyGroup):
    """태그(그룹): 이름과 기준 마커, 새 파츠의 기본값."""
    uid: bpy.props.StringProperty(default="")
    name: bpy.props.StringProperty(name="이름", default="태그")
    marker: bpy.props.StringProperty(default="")
    marker_pick: bpy.props.EnumProperty(
        name="기준 마커", items=_marker_items, get=_tag_marker_get,
        set=_tag_marker_set,
        description="이 태그 파츠의 위치 X/Y가 이 마커로부터의 거리가 됩니다")
    sym: bpy.props.BoolProperty(
        name="대칭", default=False,
        description="새 파츠의 '대칭 복사'를 켠 채로 추가")
    look: bpy.props.BoolProperty(
        name="시선", default=False,
        description="새 파츠의 '시선 따라 이동'을 켠 채로 추가")
    over: bpy.props.BoolProperty(
        name="머리카락 위로", default=False, update=_tag_over_cb,
        description="이 태그 파츠가 앞머리 등에 가려져도 위로 보이게 "
                    "(지금 있는 파츠에도 바로 적용)")
    mouth: bpy.props.BoolProperty(
        name="입 (시퀀스·립싱크)", default=False,
        description="이 태그 파츠는 ⑥의 입 시퀀스·립싱크로 칸이 바뀝니다")
    size: bpy.props.FloatProperty(
        name="기본 크기", default=0.2, min=0.01, soft_max=1.0, precision=3,
        description="새 파츠 크기 (1 = 캔버스 전체)")
    dy: bpy.props.FloatProperty(
        name="기본 위치 Y", default=0.0, soft_min=-0.5, soft_max=0.5,
        precision=3, description="새 파츠를 마커보다 위(+)/아래(-)에 놓기")
    clip_tag: bpy.props.StringProperty(default="")
    clip_pick: bpy.props.EnumProperty(
        name="자동 클리핑", items=_tag_clip_items, get=_tag_clip_get,
        set=_tag_clip_set,
        description="새 파츠를 이 태그의 가장 아래 파츠 모양으로 클리핑하고 "
                    "그 바로 위에 놓습니다 (예: 눈동자 → 흰자 태그)")
    mk_sel: bpy.props.BoolProperty(
        name="이 마커 사용", default=False, options={'SKIP_SAVE'},
        description="마커 추가 창에서: 이 태그의 기준을 새 마커로")
    apply_sel: bpy.props.BoolProperty(
        name="적용", default=True,
        description="표정 프리셋을 적용할 때 이 그룹 포함")
    key_interp: bpy.props.EnumProperty(
        name="보간", default='BEZIER',
        items=(('CONSTANT', "Constant", "다음 키까지 값 그대로 (뚝 바뀜)",
                'IPO_CONSTANT', 0),
               ('LINEAR', "Linear", "일정한 속도로 변함", 'IPO_LINEAR', 1),
               ('BEZIER', "Spline", "부드럽게 가속·감속 (Bezier)",
                'IPO_BEZIER', 2)),
        description="이 태그 파츠에 키를 넣을 때 쓸 보간 방법 (위치·크기·회전·"
                    "불투명도·크롭). 태그마다 따로 저장. 칸(그림) 키는 항상 "
                    "Constant")
    expand: bpy.props.BoolProperty(default=False)


def _hsv_update(self, context):
    """색조/채도/명도는 노드 값만 바로 바꿈 (재구성 없이 가벼움)."""
    st = _owner(self)
    if st is None:
        return
    nm = _hsv_node_name(st, self)
    hit = False
    for m in bpy.data.materials:
        if not m.name.startswith(_MAT_PREFIX) or m.node_tree is None:
            continue
        for nd in m.node_tree.nodes:
            if nd.name != nm and not nd.name.startswith(nm + ".in"):
                continue
            nd.inputs["Hue"].default_value = 0.5 + self.hue
            nd.inputs["Saturation"].default_value = self.sat
            nd.inputs["Value"].default_value = self.val
            hit = True
    if not hit:
        _rebuild_cb(self, context)


def _ov_node_name(lst, L):
    return "EYO_%s_%s" % (lst.uid, L.lid)


def _ov_update(self, context):
    """색 덮기 색·세기는 노드 값만 바꿈."""
    st = _owner(self)
    if st is None:
        return
    nm = _ov_node_name(st, self)
    hit = False
    for m in bpy.data.materials:
        if not m.name.startswith(_MAT_PREFIX) or m.node_tree is None:
            continue
        for nd in m.node_tree.nodes:
            if nd.name != nm and not nd.name.startswith(nm + ".in"):
                continue
            nd.inputs[0].default_value = self.ov_fac
            nd.inputs[7].default_value = _lin4(self.ov_color)
            hit = True
    if not hit and self.ov_on:
        _rebuild_cb(self, context)


def _s2l(c):
    c = max(0.0, float(c))
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _lin4(rgb):
    return (_s2l(rgb[0]), _s2l(rgb[1]), _s2l(rgb[2]), 1.0)


def hsv_match(src, dst):
    """원래 색 → 바꿀 색이 되는 (색조 이동, 채도 배율, 명도 배율, 경고).
    셰이더의 Hue/Saturation 노드는 선형 색에서 계산하므로 선형으로 맞춤."""
    import colorsys
    hs, ss, vs = colorsys.rgb_to_hsv(*_lin4(src)[:3])
    hd, sd, vd = colorsys.rgb_to_hsv(*_lin4(dst)[:3])
    warn = ""
    if ss < 1e-4:
        warn = _tr("원래 색이 무채색이라 색조를 바꿀 수 없습니다 (색 덮기 "
                   "'색상만'을 쓰세요)")
        dh, sm = 0.0, 1.0
    else:
        dh = (hd - hs + 0.5) % 1.0 - 0.5
        sm = sd / ss
    vm = vd / vs if vs > 1e-6 else 1.0
    return dh, sm, vm, warn


def _atlas_items(self, context):
    items = [("NONE", _tr("없음"), "", 0)]
    try:
        for i, a in enumerate(bpy.context.scene.fskr.atlases):
            items.append((a.uid, a.name, "", i + 1))
    except Exception:
        pass
    return _stable_items("eya_%s" % self.lid, items)


def _atlas_get(self):
    for t in _atlas_items(self, None):
        if t[0] == (self.atlas or "NONE"):
            return t[3]
    return 0


def _atlas_set(self, n):
    for t in _atlas_items(self, None):
        if t[3] == n:
            self.atlas = "" if t[0] == "NONE" else t[0]
            break
    _mouth_link(self, bpy.context)


def _mouth_link(self, context):
    """입 레이어에 시트를 연결하면 그 시트의 출력을 캔버스로 돌린다."""
    st = _owner(self)
    if st is None:
        return
    s = context.scene.fskr
    it = _layer_atlas(s, self)
    if it is not None and (it.target != st.target or it.method != 'CANVAS'):
        it.target = st.target
        it.method = 'CANVAS'
        try:
            AT._build(s, it)   # 예전 데칼의 UV Warp 등 정리 + 캔버스 재구성
        except Exception as e:
            print("FSKR mouth link:", e)
        return
    _rebuild_cb(self, context)


def _layer_tag_items(self, context):
    st = _owner(self)
    items = [("NONE", _tr("태그 없음"), "", 0)]
    if st is not None:
        for i, g in enumerate(st.tags):
            items.append((g.uid, g.name, "", i + 1))
    return _stable_items("elt_%s" % self.lid, items)


def _layer_tag_get(self):
    for it in _layer_tag_items(self, None):
        if it[0] == (self.tag or "NONE"):
            return it[3]
    return 0


def _layer_tag_set(self, v):
    for it in _layer_tag_items(self, None):
        if it[3] == v:
            self.tag = "" if it[0] == "NONE" else it[0]
            break


def _filter_items(self, context):
    items = [("ALL", _tr("전체"), "", 0)]
    for i, g in enumerate(self.tags):
        items.append((g.uid, g.name, "", i + 1))
    return _stable_items("eflt_%s" % self.uid, items)


def _filter_get(self):
    for it in _filter_items(self, None):
        if it[0] == (self.tag_filter or "ALL"):
            return it[3]
    return 0


def _filter_set(self, v):
    for it in _filter_items(self, None):
        if it[3] == v:
            self.tag_filter = "" if it[0] == "ALL" else it[0]
            break


# ----- 크기·회전 기준점 (마커 기준 / 파츠 중심) -----

def _cell_now(s, st, L):
    """지금 보이는 칸 index."""
    rig = s.rig
    ait = _layer_atlas(s, L)
    if ait is not None:
        cols = max(1, int(ait.cols))
        r = AT._get_val(rig, AT._prop_row(AT._row_source(s, ait)))
        c = AT._get_val(rig, AT._prop_col(ait))
        return r * cols + c
    cst, cL = _cell_source(s, st, L)
    return _get(rig, _prop_cell(cst, cL)) if rig is not None else 0


_BBOX_CACHE = {}


def cell_bbox(s, st, L, idx=None):
    """칸 안 그림(불투명 픽셀)의 영역 (u0, u1, v0, v1), 칸 공간 0~1."""
    img = _layer_image(s, L)
    if img is None:
        return None
    cols, rows = _layer_grid(s, L)
    if idx is None:
        idx = _cell_now(s, st, L)
    idx = max(0, min(cols * rows - 1, int(idx)))
    key = (img.name, img.size[0], img.size[1], cols, rows, idx)
    if key in _BBOX_CACHE:
        return _BBOX_CACHE[key]
    import numpy as np
    w, h = img.size
    if w <= 0 or h <= 0:
        return None
    r, c = idx // cols, idx % cols
    a = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    a = a.reshape(h, w, 4)[:, :, 3]
    cw, ch = w / cols, h / rows
    x0, x1 = int(round(c * cw)), int(round((c + 1) * cw))
    y0, y1 = int(round(h - (r + 1) * ch)), int(round(h - r * ch))
    sub = a[y0:y1, x0:x1]
    del a
    ys, xs = np.nonzero(sub > 0.05)
    if not len(xs):
        res = None
    else:
        W9, H9 = max(1, x1 - x0), max(1, y1 - y0)
        res = (float(xs.min()) / W9, float(xs.max() + 1) / W9,
               float(ys.min()) / H9, float(ys.max() + 1) / H9)
    _BBOX_CACHE[key] = res
    return res


def cell_center(s, st, L, idx=None):
    """칸 안에서 그림(불투명 픽셀)이 차지하는 영역의 중심 (칸 공간 0~1)."""
    import numpy as np
    img = _layer_image(s, L)
    if img is None:
        return None
    try:
        w, h = img.size
    except Exception:
        return None
    if w <= 0 or h <= 0:
        return None
    cols, rows = _layer_grid(s, L)
    if idx is None:
        idx = _cell_now(s, st, L)
    idx = max(0, min(cols * rows - 1, int(idx)))
    r, c = idx // cols, idx % cols
    a = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    a = a.reshape(h, w, 4)[:, :, 3]
    cw, ch = w / cols, h / rows
    x0, x1 = int(round(c * cw)), int(round((c + 1) * cw))
    y0, y1 = int(round(h - (r + 1) * ch)), int(round(h - r * ch))
    sub = a[y0:y1, x0:x1]
    del a
    ys, xs = np.nonzero(sub > 0.05)
    if not len(xs):
        return None
    u = ((xs.min() + xs.max() + 1) * 0.5) / max(1, x1 - x0)
    v = ((ys.min() + ys.max() + 1) * 0.5) / max(1, y1 - y0)
    return float(u), float(v)


def _pivot_eff(L, mode=None, uv=None):
    """필요한 기준점 (반전 전 파츠 공간)."""
    mode = mode or L.pivot
    if mode != 'PART':
        return 0.5, 0.5
    u, v = uv if uv is not None else tuple(L.pivot_uv)
    if L.flip_x:
        u = 1.0 - u
    return u, v


def _pivot_shift(s, st, L, old_c, new_c):
    """기준점이 바뀌어도 그림이 제자리에 있도록 위치 보정.
    o' = o + (I - R·S)(c_old - c_new)"""
    import math as _m
    rig = s.rig
    if rig is None:
        return
    ast, aL = _anim_source(s, st, L)
    _ensure_anim_props(rig, ast, aL)
    sx = float(rig.get(_p_sx(ast, aL), 1.0))
    sy = sx * float(L.aspect or 1.0) if L.scale_lock \
        else float(rig.get(_p_sy(ast, aL), 1.0))
    th = _m.radians(float(rig.get(_p_rot(ast, aL), 0.0)))
    dx, dy = old_c[0] - new_c[0], old_c[1] - new_c[1]
    ax, ay = sx * dx, sy * dy
    rx = _m.cos(th) * ax - _m.sin(th) * ay
    ry = _m.sin(th) * ax + _m.cos(th) * ay
    ddx, ddy = dx - rx, dy - ry
    if abs(ddx) < 1e-7 and abs(ddy) < 1e-7:
        return
    for prop, d in ((_p_px(ast, aL), ddx), (_p_py(ast, aL), ddy)):
        rig[prop] = float(rig.get(prop, 0.0)) + d
        for fc in AT._fcurves_for(rig, '["%s"]' % prop):
            for kp in fc.keyframe_points:
                kp.co.y += d
                kp.handle_left.y += d
                kp.handle_right.y += d
            fc.update()


def _pivot_apply(s, st, L, mode, uv=None):
    """기준점 바꾸기 (+ 위치 보정). uv None이면 지금 칸에서 계산."""
    old_c = _pivot_eff(L, L.get("pivot_cur", "MARKER") or "MARKER")
    if mode == 'PART':
        if uv is None:
            uv = cell_center(s, st, L) or (0.5, 0.5)
        L.pivot_uv = uv
    new_c = _pivot_eff(L, mode)
    _pivot_shift(s, st, L, old_c, new_c)
    L["pivot_cur"] = mode


def _pivot_cb(self, context):
    st = _owner(self)
    if st is None:
        return
    s = context.scene.fskr
    if self.get("pivot_cur", "MARKER") == self.pivot and \
            self.pivot != 'PART':
        return
    try:
        _pivot_apply(s, st, self, self.pivot)
    except Exception as e:
        print("FSKR pivot:", e)
    _rebuild_cb(self, context)


def _over_alpha_cb(self, context):
    st = _owner(self)
    if st is None:
        return
    s = context.scene.fskr
    targets = [st] + [e for e in s.eyes if e is not st and
                      e.follow == st.uid and _mirror_all(s, e)]
    for e in targets:
        mat = bpy.data.materials.get(_MAT_PREFIX + e.uid + _OVER_SUFFIX)
        n = mat.node_tree.nodes.get("FSKR_over_a_" + self.lid) \
            if mat is not None else None
        if n is not None:
            n.outputs[0].default_value = self.over_alpha
    _redraw_ui(context)


def _eff_depth(st, L):
    """패럴랙스 깊이 (부모들의 깊이를 더함)."""
    d = float(getattr(L, "depth", 0.0))
    for A in layer_ancestors(st, L):
        d += float(getattr(A, "depth", 0.0))
    return d


def _parallax_cb(self, context):
    for mat_name in (_MAT_PREFIX + self.uid,
                     _MAT_PREFIX + self.uid + _OVER_SUFFIX):
        mat = bpy.data.materials.get(mat_name)
        n = mat.node_tree.nodes.get("FSKR_parallax") if mat else None
        if n is not None:
            n.outputs[0].default_value = self.parallax
    _redraw_ui(context)


# ----- 입 파츠: 칸별 배치 (지금 보이는 입 칸) -----
# 화면에는 '파츠 공통 값 + 칸 보정'을 실제 값으로 보여 주고, 고치면 칸 보정만
# 바꾼다. 공통 값은 키·애니메이션이 그대로 되고, 칸 보정은 입 칸이 바뀔 때
# 셰이더의 조회표가 자동으로 고른다.

_CX_ADD = {"px": "lpx", "py": "lpy", "rot": "lrot",
           "ct": "lct", "cb": "lcb", "cl": "lcl", "cr": "lcr"}


PX_PREFIX = "FSKR_PX_"


def _px_tab(s, lst, L):
    """일반 파츠 칸별 배치 표 정보 (칸이 2개 이상일 때만, 아니면 None).

    (값 스택, 값 레이어 = 표를 가진 레이어, 칸 프로퍼티, 칸 수, 열 수)
    """
    if _layer_atlas(s, L) is not None:
        return None
    cst, cL = _cell_source(s, lst, L)
    n = _ncells(cL)
    if n <= 1:
        return None
    ast, aL = _anim_source(s, lst, L)
    return ast, aL, _prop_cell(cst, cL), n, max(1, int(cL.cols))


def _px_name(ast, aL, kind, L):
    return "%s%s_%s_%s_%s" % (PX_PREFIX, ast.uid, aL.lid, kind, L.lid)


def _px_entry(tab, r, c):
    for e in tab.cells:
        if e.r == r and e.c == c:
            return e
    return None


def _px_ensure(tab, r, c):
    e = _px_entry(tab, r, c)
    if e is None:
        e = tab.cells.add()
        e.r, e.c = r, c
    return e


def _px_lut(fc, tab, n, cols, role):
    f, d, conv = AT._LX_ROLES[role]
    for md in list(fc.modifiers):
        fc.modifiers.remove(md)
    pts = fc.keyframe_points
    if len(pts) != n:
        pts.clear()
        pts.add(n)
    for i in range(n):
        e = _px_entry(tab, *divmod(i, cols))
        p = pts[i]
        p.co = (float(i), conv(float(getattr(e, f)) if e is not None else d))
        p.interpolation = 'CONSTANT'
    fc.extrapolation = 'CONSTANT'
    fc.update()


def _px_bind(rig, fc, spec, role):
    ast, aL, cp, n, cols = spec
    d = fc.driver
    d.type = 'SCRIPTED'
    for v in list(d.variables):
        d.variables.remove(v)
    for vn, dp in (("c", cp), ("pv", _prop_cell_pv(cp))):
        var = d.variables.new()
        var.name = vn
        var.type = 'SINGLE_PROP'
        var.targets[0].id_type = 'OBJECT'
        var.targets[0].id = rig
        var.targets[0].data_path = '["%s"]' % dp
    _pv_cell_ensure(rig, cp, n)
    d.expression = "min(max(floor((c if pv<0 else pv)+0.5),0),%d)" % (n - 1)
    _px_lut(fc, aL, n, cols, role)


_PX_KIND = {"M": ('XPX', 'XPY'), "R": ('XR', 'XR', 'XR'),
            "S": ('XSX', 'XSY', 'XSY'), "OP": ('XOP',), "CT": ('XCT',),
            "CB": ('XCB',), "CL": ('XCL',), "CR": ('XCR',)}


def _px_refresh(s, ast, aL):
    """일반 파츠 칸별 배치 표만 다시 씀 (재구성 없이). 고친 드라이버 수."""
    hit = 0
    specs = {}
    for lst in s.eyes:
        for L in lst.layers:
            sp = _px_tab(s, lst, L)
            if sp is not None and sp[0].uid == ast.uid and \
                    sp[1].lid == aL.lid:
                specs[L.lid] = sp
    if not specs:
        return 0
    pre = 'nodes["%s%s_%s_' % (PX_PREFIX, ast.uid, aL.lid)
    for m in bpy.data.materials:
        nt = m.node_tree
        nad = nt.animation_data if nt else None
        if nad is None:
            continue
        touched = False
        for fc in nad.drivers:
            dp = fc.data_path
            if not dp.startswith(pre):
                continue
            rest = dp[len(pre):].split('"]', 1)[0]
            kind, _, lid = rest.partition("_")
            # 대칭 복사본 노드는 같은 이름 + '.001' 이 붙음
            sp = specs.get(lid.split(".", 1)[0])
            roles = _PX_KIND.get(kind)
            if sp is None or roles is None:
                continue
            role = roles[min(fc.array_index, len(roles) - 1)]
            _px_lut(fc, aL, sp[3], sp[4], role)
            try:
                fc.driver.expression = fc.driver.expression
            except Exception:
                pass
            touched = True
            hit += 1
        if touched:
            try:
                nt.update_tag()
                m.update_tag()
            except Exception:
                pass
    return hit


class _CX:
    """칸별 배치 편집 대상: 입이면 입 시트 표, 일반 파츠면 레이어 표."""
    __slots__ = ("s", "st", "tab", "P", "cur", "mouth", "ast", "aL")

    def entry(self, r, c):
        return (AT._cell_entry(self.tab, r, c) if self.mouth
                else _px_entry(self.tab, r, c))

    def ensure(self, r, c):
        return (AT._cell_ensure(self.tab, r, c) if self.mouth
                else _px_ensure(self.tab, r, c))

    def others(self):
        return AT._msel_others(self.tab, self.cur)

    def refresh(self):
        if self.mouth:
            _cx_refresh(self.tab)
            return
        n = 0
        try:
            n = _px_refresh(self.s, self.ast, self.aL)
        except Exception as e:
            print("FSKR part cell refresh:", e)
        if not n:   # 보정 노드가 없는 예전 머티리얼 → 한 번 다시 만들기
            for st in self.s.eyes:
                if any(_px_tab(self.s, st, L) is not None
                       and _anim_source(self.s, st, L)[1] == self.aL
                       for L in st.layers):
                    try:
                        eye_build(self.s, st)
                    except Exception as e:
                        print("FSKR part cell rebuild:", e)
        try:
            self.s.rig.update_tag()
        except Exception:
            pass


def cell_table(s, st, L):
    """L의 칸별 배치 대상 (_CX) 또는 None (칸이 하나뿐인 파츠)."""
    if s.rig is None or st is None:
        return None
    ast, aL = _anim_source(s, st, L)
    x = _CX()
    x.s, x.st, x.ast, x.aL = s, st, ast, aL
    x.P = dict(zip(ANIM_KEYS, _anim_props(ast, aL)))
    ait = _layer_atlas(s, L)
    if ait is not None:
        x.tab, x.mouth = ait, True
        x.cur = tuple(AT._cur_cell(ait))
        return x
    sp = _px_tab(s, st, L)
    if sp is None:
        return None
    x.tab, x.mouth = aL, False
    cst, cL = _cell_source(s, st, L)
    x.cur = divmod(part_cell_now(s.rig, cst, cL), sp[4])
    return x


def _cx(L):
    try:
        s = bpy.context.scene.fskr
    except Exception:
        return None
    return cell_table(s, _owner(L), L)


def _cx_base(rig, P, k, d):
    try:
        return float(rig.get(P[k], d))
    except Exception:
        return d


def _cx_syb(rig, L, P):
    if L.scale_lock:
        return _cx_base(rig, P, "sx", 1.0) * float(L.aspect or 1.0)
    return _cx_base(rig, P, "sy", 1.0)


def cx_locked(L, e):
    if e is not None and int(e.llock) >= 0:
        return bool(e.llock)
    return bool(L.scale_lock)


def _cx_refresh(ait):
    try:
        n = AT._lut_refresh(ait)
    except Exception:
        n = 0
    if not n:   # 예전 머티리얼(보정 노드 없음) → 한 번 다시 만들기
        try:
            s = bpy.context.scene.fskr
            for st in s.eyes:
                if any(_layer_atlas(s, L) is ait for L in st.layers):
                    eye_build(s, st)
        except Exception as e:
            print("FSKR cell place rebuild:", e)


def _cx_cells(ait):
    cur = tuple(AT._cur_cell(ait))
    return cur, AT._msel_others(ait, cur)


def _mk_cx(key):
    d = 1.0 if key == "op" else 0.0

    def get(self):
        x = _cx(self)
        if x is None:
            return d
        base = _cx_base(x.s.rig, x.P, key, d)
        e = x.entry(*x.cur)
        if key == "op":
            return base * (float(e.lop) if e is not None else 1.0)
        return base + (float(getattr(e, _CX_ADD[key])) if e is not None
                       else 0.0)

    def set_(self, v):
        x = _cx(self)
        if x is None:
            return
        base = _cx_base(x.s.rig, x.P, key, d)
        old = get(self)
        others = x.others()
        e = x.ensure(*x.cur)
        if key == "op":
            e.lop = (v / base) if abs(base) > 1e-6 else 1.0
            for rc in others:
                x.ensure(*rc).lop = e.lop
        else:
            f = _CX_ADD[key]
            setattr(e, f, float(v) - base)
            for rc in others:      # 위치·회전은 움직인 만큼, 크롭은 같은 값
                e2 = x.ensure(*rc)
                if key in ("px", "py", "rot"):
                    setattr(e2, f, float(getattr(e2, f)) + (v - old))
                else:
                    setattr(e2, f, getattr(e, f))
        x.refresh()
    return get, set_


def _mk_cx_size(which):
    """which: 'x' 가로, 'y' 세로, 'both' 고정 크기."""
    def get(self):
        x = _cx(self)
        if x is None:
            return 1.0
        e = x.entry(*x.cur)
        kx = float(e.lkx) if e is not None else 1.0
        ky = float(e.lky) if e is not None else 1.0
        if which == 'y':
            return _cx_syb(x.s.rig, self, x.P) * ky
        return _cx_base(x.s.rig, x.P, "sx", 1.0) * kx

    def set_(self, v):
        x = _cx(self)
        if x is None:
            return
        sx = max(_cx_base(x.s.rig, x.P, "sx", 1.0), 1e-6)
        sy = max(_cx_syb(x.s.rig, self, x.P), 1e-6)
        old = max(get(self), 1e-9)
        others = x.others()
        e = x.ensure(*x.cur)
        v = max(float(v), 1e-4)
        k = v / old
        # 🔗 = 지금 가로세로 비율을 지킨 채 같이 커지고 작아짐
        both = which == 'both' or cx_locked(self, e)
        if both:
            e.lkx = float(e.lkx) * k
            e.lky = float(e.lky) * k
        elif which == 'x':
            e.lkx = v / sx
        else:
            e.lky = v / sy
        for rc in others:          # 크기는 같은 비율로
            e2 = x.ensure(*rc)
            if both or which == 'x':
                e2.lkx = float(e2.lkx) * k
            if both or which == 'y':
                e2.lky = float(e2.lky) * k
        x.refresh()
    return get, set_


def _cx_lock_get(self):
    x = _cx(self)
    if x is None:
        return bool(self.scale_lock)
    return cx_locked(self, x.entry(*x.cur))


def _cx_lock_set(self, v):
    x = _cx(self)
    if x is None:
        return
    for rc in [x.cur] + x.others():
        x.ensure(*rc).llock = 1 if v else 0  # 켜도 지금 비율 그대로
    x.refresh()


def _cx_prop(key, name, **kw):
    g, s_ = _mk_cx(key)
    return bpy.props.FloatProperty(name=name, get=g, set=s_, **kw)


def _cx_size_prop(which, name):
    g, s_ = _mk_cx_size(which)
    return bpy.props.FloatProperty(name=name, get=g, set=s_, min=0.001,
                                   soft_min=0.01, soft_max=5.0, step=1,
                                   precision=3)


def _lk_ctx(L):
    try:
        s = bpy.context.scene.fskr
    except Exception:
        return None
    st = _owner(L)
    if st is None or s.rig is None:
        return None
    ast, aL = _anim_source(s, st, L)
    return s, st, s.rig, _p_sx(ast, aL), _p_sy(ast, aL)


def _lock_cb(self, context):
    """종횡비 고정을 켜고 꺼도 지금 모양이 그대로 유지되게."""
    c = _lk_ctx(self)
    if c is not None:
        s, st, rig, psx, psy = c
        sx = float(rig.get(psx, 1.0))
        if self.scale_lock:      # 켬: 지금 세로/가로 비율 기억
            sy = float(rig.get(psy, sx))
            self["aspect"] = (sy / sx) if abs(sx) > 1e-9 else 1.0
        else:                    # 끔: 기억한 비율로 세로 값을 채움
            rig[psy] = sx * float(self.aspect)
    _rebuild_cb(self, context)


def _sylk_get(self):
    c = _lk_ctx(self)
    if c is None:
        return 1.0
    s, st, rig, psx, psy = c
    if self.scale_lock:
        return float(rig.get(psx, 1.0)) * float(self.aspect)
    return float(rig.get(psy, 1.0))


def _sylk_set(self, v):
    c = _lk_ctx(self)
    if c is None:
        return
    s, st, rig, psx, psy = c
    if self.scale_lock:
        a = float(self.aspect) or 1.0
        rig[psx] = float(v) / a
    else:
        rig[psy] = float(v)
    try:
        rig.update_tag()
    except Exception:
        pass


class FSKR_EyeLayer(bpy.types.PropertyGroup):
    lid: bpy.props.StringProperty(default="")
    name: bpy.props.StringProperty(name="이름", default="파츠",
                                   update=lambda a, b: _layer_name_cb(a, b))
    image: bpy.props.StringProperty(
        name="이미지", update=_rebuild_cb,
        description="이 파츠의 스프라이트 시트 (칸 = 파츠의 상태)")
    cols: bpy.props.IntProperty(name="열 (가로 칸 수)", default=1, min=1,
                                max=64, update=_rebuild_cb)
    rows: bpy.props.IntProperty(name="행 (세로 칸 수)", default=1, min=1,
                                max=64, update=_rebuild_cb)
    clip: bpy.props.StringProperty(default="", update=_rebuild_cb)
    clip_pick: bpy.props.EnumProperty(
        name="마스크", items=_clip_items,
        get=_mk_pick("clip", _clip_items)[0],
        set=_mk_pick("clip", _clip_items)[1],
        description="이 레이어가 보일 영역. 고른 레이어(예: 흰자)의 지금 칸 "
                    "모양 안에서만 보입니다")
    parent: bpy.props.StringProperty(default="")
    # 부모를 지정한 순간의 부모 월드 배치 (2D 아핀 a,b,c,d,tx,ty)
    bind: bpy.props.FloatVectorProperty(size=6,
                                        default=(1.0, 0.0, 0.0, 1.0, 0.0, 0.0))
    bind_ok: bpy.props.BoolProperty(default=False)
    inh_hsv: bpy.props.BoolProperty(
        name="부모 HSV", default=True, update=_rebuild_cb,
        description="부모(조상)의 색조·채도·명도 조정을 이 파츠에도 적용합니다. "
                    "하이라이트처럼 원래 색을 지켜야 하는 파츠는 끄세요")
    inh_ov: bpy.props.BoolProperty(
        name="부모 색 덮기", default=False, update=_rebuild_cb,
        description="부모(조상)의 색 덮기(컬러 오버레이)를 이 파츠에도 적용합니다. "
                    "켜면 이 파츠도 부모와 같은 색으로 덮입니다")
    parent_pick: bpy.props.EnumProperty(
        name="부모", items=_parent_items, get=_parent_get, set=_parent_set,
        description="부모 파츠를 고르면 부모의 위치·회전·크기·불투명도·색(HSV·"
                    "색 덮기)·시선을 그대로 따라갑니다 (자식은 부모 바로 위에 "
                    "그려짐). 지정할 때 그림은 제자리 유지")
    show_children: bpy.props.BoolProperty(name="자식 펼치기", default=True)
    show_common: bpy.props.BoolProperty(
        name="입 전체 배치", default=False,
        description="모든 입 칸에 공통으로 적용되는 배치 값 펼치기")
    # 입 파츠 칸별 배치 (지금 보이는 입 칸의 실제 값)
    cell_px: _cx_prop("px", "위치 X", soft_min=-2.0, soft_max=2.0,
                      step=1, precision=3)
    cell_py: _cx_prop("py", "위치 Y", soft_min=-2.0, soft_max=2.0,
                      step=1, precision=3)
    cell_rot: _cx_prop("rot", "회전", soft_min=-360.0, soft_max=360.0,
                       precision=3)
    cell_op: _cx_prop("op", "불투명도", min=0.0, max=1.0, precision=3)
    cell_ct: _cx_prop("ct", "위에서", min=0.0, max=1.0, precision=3)
    cell_cb: _cx_prop("cb", "아래서", min=0.0, max=1.0, precision=3)
    cell_cl: _cx_prop("cl", "왼쪽에서", min=0.0, max=1.0, precision=3)
    cell_cr: _cx_prop("cr", "오른쪽에서", min=0.0, max=1.0, precision=3)
    cell_sx: _cx_size_prop('x', "가로")
    cell_sy: _cx_size_prop('y', "세로")
    cell_size: _cx_size_prop('both', "크기")
    cell_lock: bpy.props.BoolProperty(
        name="종횡비 고정 (이 칸)", get=_cx_lock_get, set=_cx_lock_set,
        description="켜면 지금 가로세로 비율을 그대로 지킨 채 가로나 세로를 "
                    "바꿀 때 둘이 같이 커지고 작아집니다 (이 입 칸만)")
    msel: bpy.props.BoolProperty(
        name="함께 조절", default=False,
        description="여러 파츠를 골라 속성을 한꺼번에 조절합니다")
    # 일반 파츠 칸별 배치 (칸이 2개 이상일 때, 입과 같은 방식)
    cells: bpy.props.CollectionProperty(type=AT.FSKR_AtlasCellXf)
    msel_open: bpy.props.BoolProperty(name="일괄 조절", default=False)
    pkey: bpy.props.StringProperty(default="")   # 리그 프로퍼티 이름 앞부분
    edit_on: bpy.props.BoolProperty(
        name="편집 모드", default=False, update=_part_edit_cb,
        description="켜면 키프레임을 무시하고 고른 칸을 계속 보여 줍니다 "
                    "(칸을 골라도 키가 들어가지 않음). 칸별 배치를 조절할 때 "
                    "켜고, 끝나면 끄세요")
    show_vp: bpy.props.BoolProperty(
        name="뷰포트 컨트롤러", default=True,
        update=lambda s, c: _show_vp_cb(s, c),
        description="뷰포트에 이 파츠의 시트 격자를 띄웁니다. 노란 테두리를 "
                    "끌면 칸이 바뀝니다 (칸이 2개 이상인 파츠만)")
    cell_link: bpy.props.StringProperty(default="", update=_rebuild_cb)
    link_pick: bpy.props.EnumProperty(
        name="칸 따라가기", items=_link_items,
        get=_mk_pick("cell_link", _link_items)[0],
        set=_mk_pick("cell_link", _link_items)[1],
        description="다른 레이어와 같은 칸 번호를 씁니다 (예: 속눈썹이 흰자의 "
                    "깜빡임 단계를 따라감). 두 시트의 칸 배치가 같아야 합니다")
    look: bpy.props.BoolProperty(
        name="시선 따라 이동", default=False, update=_rebuild_cb,
        description="시선 패드를 움직이면 이 레이어가 따라 움직입니다 "
                    "(눈동자, 하이라이트)")
    look_mul: bpy.props.FloatProperty(
        name="이동 배율", default=1.0, soft_min=-2.0, soft_max=2.0,
        update=_rebuild_cb,
        description="시선 이동량 배율 (하이라이트를 덜/더 움직일 때)")
    show: bpy.props.BoolProperty(
        name="표시", get=lambda s_: _vis_get(s_), set=lambda s_, v: _vis_set(s_, v),
        description="파츠 보이기/숨기기. 키를 넣을 수 있고(Constant) 표정 "
                    "프리셋에도 저장됩니다. 부모를 숨기면 자식도 숨겨집니다")
    blend: bpy.props.EnumProperty(
        name="합성 모드", items=lambda s, c: _blend_items_tr(), default=0,
        update=_rebuild_cb,
        description="아래 레이어들과 섞는 방식 (포토샵 레이어 혼합 모드)")
    flip_x: bpy.props.BoolProperty(
        name="좌우 반전", default=False, update=_rebuild_cb,
        description="이 레이어 그림을 데칼 안에서 좌우로 뒤집습니다")
    sym: bpy.props.BoolProperty(
        name="대칭 복사", default=False, update=_rebuild_cb,
        description="데칼 가운데를 기준으로 반대쪽에 거울처럼 하나 더 "
                    "그립니다 (땀방울, 빗금 등)")
    hue: bpy.props.FloatProperty(
        name="색조", default=0.0, min=-0.5, max=0.5, precision=3,
        update=lambda s, c: _hsv_update(s, c),
        description="색조 이동 (-0.5~0.5 = -180°~180°)")
    sat: bpy.props.FloatProperty(
        name="채도", default=1.0, min=0.0, soft_max=2.0, precision=3,
        update=lambda s, c: _hsv_update(s, c))
    val: bpy.props.FloatProperty(
        name="명도", default=1.0, min=0.0, soft_max=2.0, precision=3,
        update=lambda s, c: _hsv_update(s, c))
    show_fx: bpy.props.BoolProperty(default=True)
    # 색 덮기 (컬러 오버레이)
    ov_on: bpy.props.BoolProperty(
        name="색 덮기", default=False, update=_rebuild_cb,
        description="파츠 그림 위에 한 색을 덮습니다 (모양·투명도는 그대로)")
    ov_color: bpy.props.FloatVectorProperty(
        name="색", subtype='COLOR_GAMMA', size=3, min=0.0, max=1.0,
        default=(0.22, 0.227, 0.29), update=lambda s, c: _ov_update(s, c))
    ov_mode: bpy.props.EnumProperty(
        name="방식", default='MIX', update=_rebuild_cb,
        items=(('MIX', "덮기", "그 색으로 칠함 (명암 없어짐)"),
               ('COLOR', "색상만", "명암은 두고 색상·채도만 바꿈"),
               ('MULTIPLY', "곱하기", "어둡게 물들임")))
    ov_fac: bpy.props.FloatProperty(
        name="세기", default=1.0, min=0.0, max=1.0, subtype='FACTOR',
        update=lambda s, c: _ov_update(s, c))
    # 색 맞추기 (원래 색 → 바꿀 색 으로 색조/채도/명도 자동 계산)
    cm_src: bpy.props.FloatVectorProperty(
        name="원래 색", subtype='COLOR_GAMMA', size=3, min=0.0, max=1.0,
        default=(0.471, 0.263, 0.263))
    cm_dst: bpy.props.FloatVectorProperty(
        name="바꿀 색", subtype='COLOR_GAMMA', size=3, min=0.0, max=1.0,
        default=(0.22, 0.227, 0.29))
    show_cm: bpy.props.BoolProperty(default=False)
    tag: bpy.props.StringProperty(default="", update=_rebuild_cb)
    tag_pick: bpy.props.EnumProperty(
        name="태그", items=lambda s, c: _layer_tag_items(s, c),
        get=lambda s: _layer_tag_get(s), set=lambda s, v: _layer_tag_set(s, v),
        description="파츠 그룹. 그 태그의 기준 마커 위치에 놓입니다")
    sheet: bpy.props.StringProperty(default="")
    kind: bpy.props.EnumProperty(
        name="종류", default='PART', update=lambda s, c: _mouth_link(s, c),
        items=(('PART', "파츠", "시트의 칸 하나를 골라 배치", 0),
               ('MOUTH', "입 (스프라이트 시트)",
                "입 스프라이트 시트를 그대로 그림 (시퀀스·립싱크·뷰포트 "
                "컨트롤러가 그대로 동작)", 1),
               ('FOLDER', "폴더",
                "파츠를 묶는 폴더 (그림 없음). 같은 태그·같은 자리의 폴더끼리는 "
                "하나만 켜집니다", 2)))
    atlas: bpy.props.StringProperty(default="")
    atlas_pick: bpy.props.EnumProperty(
        name="입 시트", items=_atlas_items, get=_atlas_get, set=_atlas_set,
        description="이 레이어로 그릴 입 스프라이트 시트")
    over: bpy.props.BoolProperty(
        name="머리카락 위로", default=False, update=_rebuild_cb,
        description="앞머리 등 다른 메시에 가려져도 이 파츠가 위로 보입니다 "
                    "(눈썹 등). 보는 쪽으로 살짝 앞당긴 복사본을 그립니다")
    depth: bpy.props.FloatProperty(
        name="깊이 (패럴랙스)", default=0.0, soft_min=-0.05, soft_max=0.1,
        step=0.1, precision=3, update=_rebuild_cb,
        description="얼굴 표면보다 얼마나 안쪽(+)/바깥쪽(-)에 있는 것처럼 "
                    "보일지. 고개를 돌리면 깊은 레이어가 표면보다 덜 따라와 "
                    "입체감이 생깁니다 (예: 홍채 0.01, 동공 0.02, 하이라이트 "
                    "-0.005). 자식은 부모 깊이에 더해집니다")
    over_alpha: bpy.props.FloatProperty(
        name="머리카락 위 불투명도", default=1.0, min=0.0, max=1.0,
        subtype='FACTOR', update=_over_alpha_cb,
        description="머리카락 위로 보이는 부분의 진하기 (1 = 완전히 위, "
                    "0.5 = 머리카락이 비쳐 보임). 가려지지 않은 부분은 그대로")
    pivot: bpy.props.EnumProperty(
        name="크기·회전 기준",
        items=(('MARKER', "마커 기준",
                "칸 가운데(= 마커 + 위치)를 기준으로 크기·회전", 'PIVOT_CURSOR', 0),
               ('PART', "파츠 중심",
                "칸 안에 그려진 그림의 가운데를 기준으로 크기·회전",
                'PIVOT_BOUNDBOX', 1)),
        default='MARKER', update=_pivot_cb)
    pivot_uv: bpy.props.FloatVectorProperty(size=2, default=(0.5, 0.5))
    scale_lock: bpy.props.BoolProperty(
        name="종횡비 고정", default=True, update=lambda s, c: _lock_cb(s, c),
        description="켜면 지금 가로세로 비율을 그대로 지킨 채 가로·세로가 같이 "
                    "커지고 작아집니다. 꺼도 모양은 그대로")
    # 종횡비 고정 중의 세로/가로 비율 (켤 때의 모양을 기억)
    aspect: bpy.props.FloatProperty(default=1.0)
    size_y_lk: bpy.props.FloatProperty(
        name="세로", min=0.001, soft_min=0.01, soft_max=5.0, step=1,
        precision=3, get=lambda s: _sylk_get(s),
        set=lambda s, v: _sylk_set(s, v),
        description="종횡비 고정 중: 세로를 바꾸면 가로도 같은 비율로")
    pick: bpy.props.EnumProperty(name="칸", items=_cell_items,
                                 get=_cell_get, set=_cell_set)


class FSKR_FaceSheet(bpy.types.PropertyGroup):
    """파츠 스프라이트 시트 (격자로 잘라 파츠 번호를 매김)."""
    uid: bpy.props.StringProperty(default="")
    name: bpy.props.StringProperty(name="이름", default="시트")
    image: bpy.props.StringProperty(name="이미지")
    cols: bpy.props.IntProperty(name="열 (가로 칸 수)", default=8, min=1,
                                max=64)
    rows: bpy.props.IntProperty(name="행 (세로 칸 수)", default=8, min=1,
                                max=64)
    names: bpy.props.StringProperty(default="{}")   # {칸: 이름}
    expand: bpy.props.BoolProperty(default=True)


def _preset_name_cb(self, context):
    from .preset_vp import name_cb
    name_cb(self, context)


class FSKR_FacePreset(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="이름", default="표정",
                                   update=_preset_name_cb)
    data: bpy.props.StringProperty(default="{}")


def _over_props_cb(self, context):
    """거리·불투명도만 바뀌면 다시 짓지 않고 값만."""
    ob = bpy.data.objects.get(_over_name(self))
    if ob is not None:
        ng = bpy.data.node_groups.get(_OVER_GN + "_" + self.uid)
        if ng is not None:
            _over_group_set(ng, dist=self.over_dist)
            ob.update_tag()
        ob.show_wire = self.over_wire
        ob.show_all_edges = self.over_wire
    _redraw_ui(context)


def _wrap_on(cv):
    """캔버스를 얼굴에서 띄우는 모디파이어가 꺼져 있으면 켠다."""
    for m in cv.modifiers:
        if m.name in ("FSKR_Canvas_Wrap", "FSKR_Canvas_Follow") or \
                m.type == 'SUBSURF':
            m.show_viewport = True
            m.show_render = True
    try:
        wrap_modes(cv)      # 가벼운 모드면 뷰포트/렌더 띄우기를 나눔
    except Exception:
        pass


def _lift_cb(self, context):
    cv = bpy.data.objects.get(self.target)
    sw = cv.modifiers.get("FSKR_Canvas_Wrap") if cv is not None else None
    if sw is not None:
        sc = max(1e-6, sum(cv.matrix_world.to_scale()) / 3.0)
        sw.offset = self.lift / sc
        vp = cv.modifiers.get(_WRAP_VP)
        if vp is not None:
            vp.offset = sw.offset
        _wrap_on(cv)


def lift_init(st):
    """예전 캔버스: 띄우기 값을 월드 거리로 맞추고 너무 작으면 키움."""
    if "lift" in st.keys():
        return
    cv = bpy.data.objects.get(st.target)
    sw = cv.modifiers.get("FSKR_Canvas_Wrap") if cv is not None else None
    if sw is None:
        return
    sc = max(1e-6, sum(cv.matrix_world.to_scale()) / 3.0)
    want = max(sw.offset * sc, max(cv.dimensions) * 0.012)
    st.lift = want


_PRESET_MUTE = {"on": False}


def _preset_pick_cb(self, context):
    """목록에서 프리셋을 고르면 바로 그 표정으로 (키는 넣지 않음)."""
    if _PRESET_MUTE["on"]:
        return
    if not (0 <= self.preset_index < len(self.presets)):
        return
    try:
        from .face_ui import preset_apply
        groups = None    # '그룹만 적용'은 없앰 (1.0.168): 항상 전체 적용
        ak = bool(self.autokey) and not self.preset_edit
        preset_apply(context.scene.fskr, self,
                     self.presets[self.preset_index], groups, ak)
        from .preset_vp import note
        note(context.scene.fskr, self, self.preset_index, ak)
    except Exception as e:
        print("FSKR preset pick:", e)
    _redraw_ui(context)


class FSKR_PartSet(bpy.types.PropertyGroup):
    """파츠 폴더: 파츠 구성 프리셋 — 어떤 파츠가 보이는지 + 각 파츠의 상태
    (칸·위치·크기·회전·불투명도·크롭·반전). 폴더마다 따로 저장된다."""
    name: bpy.props.StringProperty(name="폴더 이름", default="폴더")
    members: bpy.props.StringProperty(default="[]")   # 보이는 파츠 lid 목록
    states: bpy.props.StringProperty(default="{}")    # {lid: 파츠 상태}


def part_set_members(ps):
    try:
        return set(json.loads(ps.members or "[]"))
    except Exception:
        return set()


def part_set_include(st, lid):
    """폴더를 보고 있으면 새로 생긴 파츠를 그 폴더에도 넣는다."""
    pa = getattr(st, "part_set_active", -1)
    if 0 <= pa < len(st.part_sets):
        m = part_set_members(st.part_sets[pa])
        if lid not in m:
            m.add(lid)
            st.part_sets[pa].members = json.dumps(sorted(m))


def part_set_capture(st):
    """지금 실제로 보이는 파츠들의 lid (부모가 숨은 파츠는 제외)."""
    return sorted(L.lid for L in st.layers if layer_visible(st, L))


def part_set_store(s, st, idx=None):
    """폴더(기본: 지금 폴더)에 지금 파츠 상태를 저장 (보이는 파츠 + 각 상태)."""
    if idx is None:
        idx = st.part_set_active
    if not (0 <= idx < len(st.part_sets)) or s.rig is None:
        return
    from .face_ui import layer_states_capture
    ps = st.part_sets[idx]
    ps.members = json.dumps(part_set_capture(st))
    ps.states = json.dumps(layer_states_capture(s, st), ensure_ascii=False)


def part_set_apply(s, st, idx, key=False):
    """폴더 전환: 지금 폴더의 작업 내용을 먼저 그 폴더에 저장하고, idx 폴더의
    파츠 구성·상태를 불러온다. idx < 0 = 목록 전체 보기 (상태는 그대로)."""
    if st.part_set_active != idx:
        part_set_store(s, st)
    if not (0 <= idx < len(st.part_sets)):
        st.part_set_active = -1
        return
    ps = st.part_sets[idx]
    mem = part_set_members(ps)
    rig = s.rig
    try:
        states = json.loads(ps.states or "{}")
    except Exception:
        states = {}
    if states:
        from .face_ui import layer_states_apply
        for lid, d in states.items():
            d["vis"] = 1.0 if lid in mem else 0.0
        layer_states_apply(s, st, states,
                           key=bool(key) and not preset_editing(s))
    for L in st.layers:
        _vis_raw(rig, L, L.lid in mem)
    st.part_set_active = idx
    if key and rig is not None and not preset_editing(s):
        for L in st.layers:
            try:
                key_layer(s, st, L,
                          only={_p_vis(*_anim_source(s, st, L))})
            except Exception:
                pass
    try:
        rig.update_tag()
        ob = bpy.data.objects.get(st.target)
        if ob is not None:
            ob.update_tag()
    except Exception:
        pass


class FSKR_EyeStack(bpy.types.PropertyGroup):
    uid: bpy.props.StringProperty(default="")
    pkey: bpy.props.StringProperty(default="")   # 표정 프로퍼티 이름
    preset_edit: bpy.props.BoolProperty(default=False)  # 프리셋 편집 중
    name: bpy.props.StringProperty(name="이름", default="눈",
                                   update=lambda s_, c_: _canvas_name_cb(s_, c_))
    target: bpy.props.StringProperty(name="대상 오브젝트")
    uv_map: bpy.props.StringProperty(name="UV 맵", update=_rebuild_cb)
    layers: bpy.props.CollectionProperty(type=FSKR_EyeLayer)
    layer_index: bpy.props.IntProperty(default=0)
    range_x: bpy.props.FloatProperty(
        name="오른쪽 범위", default=0.2, min=0.0, soft_max=1.0, precision=3,
        update=_rebuild_cb,
        description="패드를 오른쪽 끝까지 밀었을 때 눈동자가 움직이는 거리 "
                    "(캔버스 폭 대비. 0.03 = 3%)")
    range_y: bpy.props.FloatProperty(
        name="위 범위", default=0.15, min=0.0, soft_max=1.0, precision=3,
        update=_rebuild_cb,
        description="패드를 위 끝까지 밀었을 때 눈동자가 움직이는 거리 "
                    "(캔버스 높이 대비)")
    range_xl: bpy.props.FloatProperty(
        name="왼쪽 범위", default=0.035, min=0.0, soft_max=1.0, precision=3,
        update=_rebuild_cb,
        description="패드를 왼쪽 끝까지 밀었을 때 눈동자가 움직이는 거리 "
                    "(캔버스 폭 대비. 0.03 = 3%)")
    range_yd: bpy.props.FloatProperty(
        name="아래 범위", default=0.025, min=0.0, soft_max=1.0, precision=3,
        update=_rebuild_cb,
        description="패드를 아래 끝까지 밀었을 때 눈동자가 움직이는 거리 "
                    "(캔버스 높이 대비)")
    link_x: bpy.props.BoolProperty(
        name="좌우 같게", default=True, update=_rebuild_cb,
        description="켜면 왼쪽 범위 = 오른쪽 범위")
    link_y: bpy.props.BoolProperty(
        name="위아래 같게", default=True, update=_rebuild_cb,
        description="켜면 아래 범위 = 위 범위 (보통 아래를 조금 더 크게)")
    follow: bpy.props.StringProperty(default="")
    follow_pick: bpy.props.EnumProperty(
        name="다른 눈 따라가기", items=_stack_items,
        get=_stack_pick_get, set=_stack_pick_set,
        description="고른 눈의 시선 패드와 칸 값을 그대로 씁니다 (같은 이름의 "
                    "파츠끼리). 오른쪽 눈을 왼쪽 눈에 연결할 때")
    mirror: bpy.props.BoolProperty(
        name="따라갈 때 좌우 반전", default=False, update=_rebuild_cb,
        description="따라가는 눈의 시선 좌우를 뒤집습니다 (데칼 UV가 좌우 "
                    "반전되어 있을 때)")
    mirror_all: bpy.props.BoolProperty(
        name="따라가는 눈의 파츠를 전부 좌우 반전해서 사용", default=False,
        update=_rebuild_cb,
        description="켜면 이 눈은 자기 파츠 목록 대신 따라가는 눈의 파츠 "
                    "전체를 좌우로 뒤집어 씁니다. 왼눈만 세팅하면 됩니다")
    over_dist: bpy.props.FloatProperty(
        name="앞으로 당기는 거리", default=0.1, min=0.0, soft_max=1.0,
        precision=3, unit='LENGTH', update=_over_props_cb,
        description="'머리카락 위로' 파츠를 보는 쪽으로 얼마나 앞당길지. "
                    "앞머리보다 앞에 올 만큼만 (너무 크면 옆모습에서 "
                    "반대쪽 파츠가 머리를 뚫고 보일 수 있음)")
    parallax: bpy.props.FloatProperty(
        name="패럴랙스 강도", default=1.0, min=0.0, soft_max=3.0,
        update=_parallax_cb,
        description="모든 레이어의 깊이(패럴랙스)에 곱하는 값. 0이면 끔")
    lift: bpy.props.FloatProperty(
        name="얼굴에서 띄우기", default=0.005, min=0.0, soft_max=0.05,
        precision=4, unit='LENGTH', update=_lift_cb,
        description="캔버스를 얼굴 표면에서 띄우는 거리. 비스듬히 볼 때 피부가 "
                    "줄무늬처럼 비쳐 보이면(Z-fighting) 조금 올리세요")
    over_info: bpy.props.StringProperty(default="", options={'SKIP_SAVE'})
    over_follow: bpy.props.EnumProperty(
        name="화면 돌릴 때",
        items=(('FRAME', "부드럽게", "매 프레임 따라감. 가장 부드럽지만 화면을 "
                "돌릴 때마다 씬 전체가 다시 계산되어 무거움", 0),
               ('HZ', "보통", "초당 약 12번 따라감 (조금 끊겨 보이지만 가벼움)",
                1),
               ('STOP', "가볍게", "돌리는 동안은 그대로, 멈추면 맞춤 (가장 가벼움)",
                2)),
        default='HZ',
        description="'머리카락 위로' 파츠가 뷰포트 시점을 얼마나 자주 따라갈지 "
                    "(렌더와는 무관)")
    over_live: bpy.props.BoolProperty(
        name="시점 따라가기", default=True,
        description="'머리카락 위로' 파츠가 뷰포트 시점을 따라갑니다. 화면을 "
                    "돌리는 동안에는 가볍게 두었다가 멈추면 바로 맞춥니다 "
                    "(렌더와는 무관)")
    over_wire: bpy.props.BoolProperty(
        name="앞쪽 복사본 위치 보기", default=False, update=_over_props_cb,
        description="'머리카락 위로' 복사본 메시를 와이어로 표시합니다 "
                    "(머리카락 앞에 있는지 확인용)")
    over_alpha: bpy.props.FloatProperty(
        name="(예전) 머리카락 위 불투명도", default=1.0, min=0.0, max=1.0,
        subtype='FACTOR',
        description="머리카락 위로 보이는 부분의 진하기 "
                    "(1 = 완전히 위, 0.5 = 머리카락이 비쳐 보임)")
    billboard: bpy.props.BoolProperty(
        name="항상 카메라를 봄", default=False,
        update=lambda s_, c_: fx_billboard_apply(s_, c_),
        description="감정표현 Plane: 켜면 면이 항상 활성 카메라 정면을 봅니다 "
                    "(위치는 머리를 따라감). 끄면 머리 정면에 고정")
    vp_autolayout: bpy.props.BoolProperty(
        name="자동 정렬", default=True,
        description="컨트롤러가 생기거나 크기가 바뀌면 기본 배치로 다시 "
                    "쌓습니다. 직접 옮긴 자리를 지키려면 끄세요")
    key_interp: bpy.props.EnumProperty(
        name="보간", default='BEZIER',
        items=(('CONSTANT', "Constant", "다음 키까지 값 그대로 (뚝 바뀜)",
                'IPO_CONSTANT', 0),
               ('LINEAR', "Linear", "일정한 속도로 변함", 'IPO_LINEAR', 1),
               ('BEZIER', "Spline", "부드럽게 가속·감속 (Bezier)",
                'IPO_BEZIER', 2)),
        description="파츠 키를 넣을 때 쓸 보간 방법 (위치·크기·회전·불투명도·"
                    "크롭). 칸(그림) 키는 항상 Constant")
    autokey: bpy.props.BoolProperty(
        name="바꾸면 자동 키", default=False,
        description="파츠의 칸·위치·크기·회전·불투명도·크롭이나 시선, 표정을 "
                    "바꾸면 현재 프레임에 키를 바로 넣습니다")
    look_x: bpy.props.FloatProperty(name="좌우", min=-1.0, max=1.0,
                                    get=_mk_gaze(0)[0], set=_mk_gaze(0)[1])
    look_y: bpy.props.FloatProperty(name="상하", min=-1.0, max=1.0,
                                    get=_mk_gaze(1)[0], set=_mk_gaze(1)[1])
    built: bpy.props.BoolProperty(default=False)
    prev_mats: bpy.props.StringProperty(default="")
    expand: bpy.props.BoolProperty(default=True)
    show_settings: bpy.props.BoolProperty(default=False)
    # 위치 마커 / 태그 (사용자 정의). 파츠 위치 = 태그의 마커 + 위치 X/Y
    markers: bpy.props.CollectionProperty(type=FSKR_FaceMarker)
    tags: bpy.props.CollectionProperty(type=FSKR_FaceTag)
    show_markers: bpy.props.BoolProperty(
        name="마커 표시", default=True,
        description="뷰포트에 위치 마커를 표시합니다")
    sheets: bpy.props.CollectionProperty(type=FSKR_FaceSheet)
    sheet_index: bpy.props.IntProperty(default=0)
    presets: bpy.props.CollectionProperty(type=FSKR_FacePreset)
    part_sets: bpy.props.CollectionProperty(type=FSKR_PartSet)
    part_set_active: bpy.props.IntProperty(default=-1)
    preset_index: bpy.props.IntProperty(default=0, update=_preset_pick_cb)
    preset_mix: bpy.props.BoolProperty(
        name="그룹만 적용", default=False,
        description="켜면 아래에서 고른 그룹(태그)만 바꿉니다 ('화난 눈 + "
                    "웃는 입'처럼 섞기). 끄면 표정 전체를 바꿉니다")
    tag_filter: bpy.props.StringProperty(default="")
    tag_filter_pick: bpy.props.EnumProperty(
        name="그룹", items=lambda s, c: _filter_items(s, c),
        get=lambda s: _filter_get(s), set=lambda s, v: _filter_set(s, v),
        description="목록에 이 그룹 파츠만 표시")


FSKR_Settings.__annotations__["eyes"] = bpy.props.CollectionProperty(
    type=FSKR_EyeStack)
FSKR_Settings.__annotations__["face_axis"] = bpy.props.EnumProperty(
    name="얼굴 방향", items=(
        ('-Y', "-Y", "얼굴이 -Y를 봄 (정면 = 숫자패드 1). Blender 기본", 0),
        ('Y', "Y", "얼굴이 +Y를 봄 (정면 = Ctrl+숫자패드 1)", 1),
        ('X', "X", "얼굴이 +X를 봄 (정면 = 숫자패드 3)", 2),
        ('-X', "-X", "얼굴이 -X를 봄 (정면 = Ctrl+숫자패드 3)", 3)),
    default='-Y',
    description="캐릭터 얼굴이 바라보는 축. 캔버스 정면 투영 UV와 마커 찍기 "
                "화면 방향의 기준이 됩니다")


# ------------------------------------------------------------------
# 머티리얼 합성
# ------------------------------------------------------------------

def _src_stack(s, st):
    """시선/칸을 읽어 올 스택 (따라가기 대상이 있으면 그쪽)."""
    if st.follow and st.follow != st.uid:
        src = _find(s, st.follow)
        if src is not None and not src.follow:
            return src
    return st


def _cell_source(s, st, L):
    """칸 값을 읽을 (스택, 레이어): 다른 눈 따라가기 → 같은 이름 파츠,
    칸 따라가기 → 그 레이어."""
    seen = set()
    cur_st, cur = st, L
    while cur.cell_link and cur.lid not in seen:
        seen.add(cur.lid)
        nxt = _layer(cur_st, cur.cell_link)
        if nxt is None:
            break
        cur = nxt
    src = _src_stack(s, st)
    if src is not st:
        m = next((x for x in src.layers if x.name == cur.name), None)
        if m is not None:
            return src, m
    return cur_st, cur


def _mats_of(ob):
    return [sl.material for sl in ob.material_slots]


def _assign(ob, st, mat):
    if not st.prev_mats:
        st.prev_mats = json.dumps([m.name if m else "" for m in _mats_of(ob)])
    if not ob.material_slots:
        ob.data.materials.append(mat)
    for sl in ob.material_slots:
        sl.material = mat


def _restore(ob, st):
    try:
        names = json.loads(st.prev_mats or "[]")
    except Exception:
        names = []
    for i, sl in enumerate(ob.material_slots):
        nm = names[i] if i < len(names) else ""
        sl.material = bpy.data.materials.get(nm) if nm else None
    st.prev_mats = ""


def _drv_vars(sock, idx, expr, pairs):
    """소켓 default_value[idx]에 드라이버. pairs: [(이름, ID, data_path)]."""
    fc = sock.driver_add("default_value", idx) if idx is not None \
        else sock.driver_add("default_value")
    d = fc.driver
    d.type = 'SCRIPTED'
    for v in list(d.variables):
        d.variables.remove(v)
    for vn, idv, dp in pairs:
        var = d.variables.new()
        var.name = vn
        var.type = 'SINGLE_PROP'
        t = var.targets[0]
        t.id_type = 'OBJECT'
        t.id = idv
        t.data_path = dp
    d.expression = expr
    return fc


_BLEND_TR = {}


def _blend_items_tr():
    """합성 모드 목록 (언어별로 번역해 캐시: 동적 목록 문자열 유지용)."""
    from .core import _lang_get
    lg = _lang_get()
    v = _BLEND_TR.get(lg)
    if v is None:
        v = tuple((i[0], _tr(i[1]), _tr(i[2])) + tuple(i[3:])
                  for i in _BLEND_ITEMS)
        _BLEND_TR[lg] = v
    return v


_BLEND_ITEMS = (
    ('MIX', "일반", "", 0),
    ('MULTIPLY', "곱하기", "", 1),
    ('SCREEN', "스크린", "", 2),
    ('OVERLAY', "오버레이", "", 3),
    ('SOFT_LIGHT', "소프트 라이트", "", 4),
    ('LINEAR_LIGHT', "선형 라이트", "", 5),
    ('ADD', "더하기 (선형 닷지)", "", 6),
    ('SUBTRACT', "빼기", "", 7),
    ('DARKEN', "어둡게", "", 8),
    ('LIGHTEN', "밝게", "", 9),
    ('DODGE', "닷지", "", 10),
    ('BURN', "번", "", 11),
    ('DIFFERENCE', "차이", "", 12),
    ('HUE', "색조", "", 13),
    ('SATURATION', "채도", "", 14),
    ('COLOR', "색상", "", 15),
    ('VALUE', "명도", "", 16),
)


def _layer_atlas(s, L):
    """입 레이어면 연결된 입 스프라이트 시트 (없으면 None)."""
    if getattr(L, "kind", 'PART') != 'MOUTH' or not L.atlas:
        return None
    return AT._find(s, L.atlas)


def _layer_image(s, L):
    ait = _layer_atlas(s, L)
    nm = ait.image if ait is not None else L.image
    return bpy.data.images.get(nm) if nm else None


def _layer_grid(s, L):
    ait = _layer_atlas(s, L)
    src = ait if ait is not None else L
    return max(1, int(src.cols)), max(1, int(src.rows))


def eye_rebuild_for_atlas(s, uid):
    """입 시트가 바뀌면 그 시트를 입 레이어로 쓰는 캔버스를 재구성."""
    for st in s.eyes:
        lst = _src_stack(s, st) if _mirror_all(s, st) else st
        if any(getattr(L, "kind", 'PART') == 'MOUTH' and L.atlas == uid
               for L in lst.layers):
            try:
                eye_build(s, st)
            except Exception as e:
                print("FSKR canvas rebuild:", e)


def marker_uv(st, tag_uid):
    """태그의 기준 마커 UV (태그·마커 없으면 캔버스 가운데)."""
    g = find_tag(st, tag_uid)
    m = find_marker(st, g.marker) if g is not None else None
    return tuple(m.uv) if m is not None else (0.5, 0.5)


def _anim_source(s, st, L):
    """불투명도/위치를 읽을 (스택, 레이어): 다른 눈을 같은 이름으로 따라가면
    그쪽 파츠 값."""
    src = _src_stack(s, st)
    if src is not st:
        m = next((x for x in src.layers if x.name == L.name), None)
        if m is not None:
            return src, m
    return st, L


def _p_op(st, L):
    k = _pk(L)
    return (k + "_Opacity") if k else "fskr_ey_%s_%s_op" % (st.uid, L.lid)


def _p_px(st, L):
    k = _pk(L)
    return (k + "_Pos_X") if k else "fskr_ey_%s_%s_px" % (st.uid, L.lid)


def _p_py(st, L):
    k = _pk(L)
    return (k + "_Pos_Y") if k else "fskr_ey_%s_%s_py" % (st.uid, L.lid)


def _ensure_float(rig, prop, default, lo, hi, soft=None):
    if prop not in rig.keys():
        rig[prop] = float(default)
    try:
        ui = rig.id_properties_ui(prop)
        if soft:
            ui.update(min=lo, max=hi, soft_min=soft[0], soft_max=soft[1],
                      precision=3, step=1)
        else:
            ui.update(min=lo, max=hi, soft_min=lo, soft_max=hi, precision=3,
                      step=1)
    except Exception:
        pass


def _p_rot(st, L):
    k = _pk(L)
    return (k + "_Rot") if k else "fskr_ey_%s_%s_rot" % (st.uid, L.lid)


def _p_sx(st, L):
    k = _pk(L)
    return (k + "_Size_X") if k else "fskr_ey_%s_%s_sx" % (st.uid, L.lid)


def _p_sy(st, L):
    k = _pk(L)
    return (k + "_Size_Y") if k else "fskr_ey_%s_%s_sy" % (st.uid, L.lid)


def _p_crop(st, L, side):
    """크롭 (side: t/b/l/r) — 그림 영역 대비 잘라낼 비율 0~1."""
    k = _pk(L)
    if k:
        return k + "_Crop_" + {"t": "Top", "b": "Bottom", "l": "Left",
                               "r": "Right"}[side]
    return "fskr_ey_%s_%s_c%s" % (st.uid, L.lid, side)


def _p_vis(st, L):
    """보이기 (👁): 1 = 보임, 0 = 숨김. 키·프리셋에 들어감 (Constant)."""
    k = _pk(L)
    return (k + "_Visible") if k else "fskr_ey_%s_%s_vis" % (st.uid, L.lid)


def _anim_props(st, L):
    return (_p_op(st, L), _p_px(st, L), _p_py(st, L), _p_sx(st, L),
            _p_sy(st, L), _p_rot(st, L),
            _p_crop(st, L, "t"), _p_crop(st, L, "b"),
            _p_crop(st, L, "l"), _p_crop(st, L, "r"), _p_vis(st, L))


ANIM_KEYS = ("op", "px", "py", "sx", "sy", "rot", "ct", "cb", "cl", "cr",
             "vis")
ANIM_DEFAULTS = (1.0, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0)
CONST_KEYS = ("vis",)   # 항상 Constant 보간 (켜짐/꺼짐)


def _ensure_anim_props(rig, st, L):
    # 입력은 사실상 제한 없음(hard), 끌기 범위(soft)만 넉넉하게
    _ensure_float(rig, _p_rot(st, L), 0.0, -1.0e5, 1.0e5, (-360.0, 360.0))
    _ensure_float(rig, _p_sx(st, L), 1.0, 0.001, 1.0e4, (0.01, 5.0))
    _ensure_float(rig, _p_sy(st, L), 1.0, 0.001, 1.0e4, (0.01, 5.0))
    _ensure_float(rig, _p_op(st, L), 1.0, 0.0, 1.0)
    _ensure_float(rig, _p_px(st, L), 0.0, -1.0e4, 1.0e4, (-2.0, 2.0))
    _ensure_float(rig, _p_py(st, L), 0.0, -1.0e4, 1.0e4, (-2.0, 2.0))
    for side in "tblr":
        _ensure_float(rig, _p_crop(st, L, side), 0.0, 0.0, 1.0)
    pv = _p_vis(st, L)
    if pv not in rig.keys():
        # 예전 파일: 레이어에 저장된 👁 값을 한 번 옮겨 옴
        raw = L.get("show", True) if hasattr(L, "get") else True
        rig[pv] = 1.0 if raw else 0.0
    _ensure_float(rig, pv, 1.0, 0.0, 1.0)


def _mirror_all(s, st):
    """오른눈이 왼눈 파츠 전체를 좌우 반전해서 쓰는지."""
    return bool(st.follow and st.mirror_all and _src_stack(s, st) is not st)


def _hsv_node_name(lst, L):
    return "EYH_%s_%s" % (lst.uid, L.lid)


# ------------------------------------------------------------------
# 머리카락 위로 보이기 (앞쪽 오버레이)
#   캔버스와 같은 메시·모디파이어를 쓰는 복제 오브젝트를 만들고, 정점을
#   '보는 쪽(카메라/뷰포트 시점)'을 향해 시선 방향으로 앞당긴다.
#   시선 광선 위에서만 움직이므로 화면상 위치는 그대로, 깊이만 앞쪽.
# ------------------------------------------------------------------

_OVER_SUFFIX = "_over"
_OVER_OB = "FaceCanvasOver_"
_OVER_GN = "FSKR_OverPush"
_VIEW_EMPTY = "FSKR_ViewPoint"


def _over_name(st):
    return _OVER_OB + st.uid


def _over_used(s, st):
    lst = _src_stack(s, st) if _mirror_all(s, st) else st
    return any(L.over and L.kind != 'MOUTH' for L in lst.layers)


def _view_empty():
    """뷰포트 시점 위치를 따라다니는 빈 오브젝트 (씬에 넣어야 갱신이 확실)."""
    e = bpy.data.objects.get(_VIEW_EMPTY)
    if e is None:
        e = bpy.data.objects.new(_VIEW_EMPTY, None)
        e.empty_display_size = 0.0001
        e.empty_display_type = 'PLAIN_AXES'
    try:
        sc = bpy.context.scene
        if sc is not None and e.name not in sc.collection.objects and \
                not any(e.name in c.objects for c in sc.collection.children_recursive):
            sc.collection.objects.link(e)
    except Exception:
        pass
    e.hide_select = True
    e.hide_render = True
    return e


def _over_group(st):
    """캔버스의 '최종 모양'(쉐이프키·아마추어·Shrinkwrap 등 전부 적용된)을
    그대로 가져와 보는 쪽으로 앞당기고, 앞쪽 머티리얼을 입힌다.
    오브젝트는 원점·회전 없음이라 거리·방향이 곧 월드 기준.
    값은 모디파이어 입력이 아니라 노드에 직접 넣는다 (버전 차이 회피)."""
    name = _OVER_GN + "_" + st.uid
    ng = bpy.data.node_groups.get(name)
    if ng is not None and ng.get("fskr_v") == 5:
        return ng
    if ng is None:
        ng = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    ng.nodes.clear()
    ng.interface.clear()
    ng.interface.new_socket("Geometry", in_out='INPUT',
                            socket_type='NodeSocketGeometry')
    ng.interface.new_socket("Geometry", in_out='OUTPUT',
                            socket_type='NodeSocketGeometry')
    N, Lk = ng.nodes, ng.links
    go = N.new('NodeGroupOutput')
    go.location = (700, 0)
    gi = N.new('NodeGroupInput')
    gi.location = (-900, 300)

    def objinfo(nm, x, y):
        n = N.new('GeometryNodeObjectInfo')
        n.name = nm
        n.label = nm
        n.location = (x, y)
        n.transform_space = 'RELATIVE'
        return n
    src = objinfo("src", -650, 150)
    oc = objinfo("cam", -650, -150)
    ov = objinfo("view", -650, -400)
    isv = N.new('GeometryNodeIsViewport')
    isv.location = (-650, 300)
    sw = N.new('GeometryNodeSwitch')
    sw.input_type = 'VECTOR'
    sw.location = (-400, -200)
    Lk.new(isv.outputs[0], sw.inputs[0])
    Lk.new(oc.outputs["Location"], sw.inputs[1])
    Lk.new(ov.outputs["Location"], sw.inputs[2])
    pos = N.new('GeometryNodeInputPosition')
    pos.location = (-400, -400)
    sub = N.new('ShaderNodeVectorMath')
    sub.operation = 'SUBTRACT'
    sub.location = (-200, -250)
    Lk.new(sw.outputs[0], sub.inputs[0])
    Lk.new(pos.outputs[0], sub.inputs[1])
    nrm = N.new('ShaderNodeVectorMath')
    nrm.operation = 'NORMALIZE'
    nrm.location = (-20, -250)
    Lk.new(sub.outputs[0], nrm.inputs[0])
    dist = N.new('ShaderNodeValue')
    dist.name = "dist"
    dist.label = "Distance"
    dist.location = (-20, -450)
    scl = N.new('ShaderNodeVectorMath')
    scl.operation = 'SCALE'
    scl.location = (150, -250)
    Lk.new(nrm.outputs[0], scl.inputs[0])
    Lk.new(dist.outputs[0], scl.inputs["Scale"])
    sp = N.new('GeometryNodeSetPosition')
    sp.location = (320, 0)
    Lk.new(src.outputs["Geometry"], sp.inputs["Geometry"])
    Lk.new(scl.outputs[0], sp.inputs["Offset"])
    sm = N.new('GeometryNodeSetMaterial')
    sm.name = "mat"
    sm.location = (500, 0)
    Lk.new(sp.outputs[0], sm.inputs["Geometry"])
    Lk.new(sm.outputs[0], go.inputs[0])
    ng["fskr_v"] = 5
    return ng


def _over_group_set(ng, src=None, cam=None, view=None, dist=None,
                    mat=None):
    N = ng.nodes
    for nm, val in (("src", src), ("cam", cam), ("view", view)):
        if val is not None and nm in N:
            N[nm].inputs["Object"].default_value = val
    if dist is not None and "dist" in N:
        N["dist"].outputs[0].default_value = dist
    if mat is not None and "mat" in N:
        N["mat"].inputs["Material"].default_value = mat


def _copy_mod(src, dst):
    for pr in src.bl_rna.properties:
        if pr.is_readonly or pr.identifier in ("name", "type", "rna_type"):
            continue
        try:
            setattr(dst, pr.identifier, getattr(src, pr.identifier))
        except Exception:
            pass


def over_remove(st):
    ob = bpy.data.objects.get(_over_name(st))
    if ob is not None:
        bpy.data.objects.remove(ob)
    mat = bpy.data.materials.get(_MAT_PREFIX + st.uid + _OVER_SUFFIX)
    if mat is not None and mat.users == 0:
        bpy.data.materials.remove(mat)
    ng = bpy.data.node_groups.get(_OVER_GN + "_" + st.uid)
    if ng is not None and ng.users == 0:
        bpy.data.node_groups.remove(ng)


def over_sync(s, st):
    """'머리카락 위로' 파츠가 있으면 오버레이를 만들고/갱신, 없으면 제거."""
    cv = bpy.data.objects.get(st.target)
    if cv is None or cv.type != 'MESH' or not _over_used(s, st):
        over_remove(st)
        return
    mat = _eye_mat(s, st, True)
    if not isinstance(mat, bpy.types.Material):
        return
    nm = _over_name(st)
    ob = bpy.data.objects.get(nm)
    if ob is None and "over_dist" not in st.keys():
        # 처음 만들 때: 캔버스 크기에 맞춘 기본 거리 (단위 설정과 무관)
        try:
            dims = cv.dimensions
            st["over_dist"] = max(dims.x, dims.y, dims.z) * 0.12
        except Exception:
            pass
    if ob is not None and ob.data is cv.data:
        # 예전 방식(메시 공유 + 모디파이어 복사)이면 새로 만든다
        bpy.data.objects.remove(ob)
        ob = None
    if ob is None:
        me = bpy.data.meshes.new(nm)
        ob = bpy.data.objects.new(nm, me)
        for col in cv.users_collection:
            col.objects.link(ob)
        if not ob.users_collection:
            bpy.context.scene.collection.objects.link(ob)
    # 원점·회전·배율 없음 → 노드 안 좌표 = 월드 좌표
    ob.parent = None
    ob.matrix_world = __import__("mathutils").Matrix.Identity(4)
    ob.hide_select = True
    ob.show_wire = False
    try:
        ob.visible_shadow = False
    except Exception:
        pass
    ob.modifiers.clear()
    gm = ob.modifiers.new("FSKR 머리카락 위로", 'NODES')
    ng = _over_group(st)
    cam = bpy.context.scene.camera
    _over_group_set(ng, src=cv,
                    cam=cam if cam is not None else _view_empty(),
                    view=_view_empty(), dist=st.over_dist, mat=mat)
    gm.node_group = ng
    if ob.data.materials:
        ob.data.materials.clear()
    ob.data.materials.append(mat)
    view_track(force=True)


_VIEW_STATE = {"m": None}


def _main_view3d():
    best, area_px = None, -1
    try:
        wins = bpy.context.window_manager.windows
    except Exception:
        return None
    for w in wins:
        for a in w.screen.areas:
            if a.type != 'VIEW_3D':
                continue
            px = a.width * a.height
            if px > area_px:
                sp = a.spaces.active
                if sp is not None and sp.region_3d is not None:
                    best, area_px = sp.region_3d, px
    return best


def _view_point(r3=None):
    """지금 뷰포트 시점 위치 (정사영이면 아주 먼 뒤쪽)."""
    if r3 is None:
        r3 = _main_view3d()
    if r3 is None:
        return None
    vi = r3.view_matrix.inverted()
    if r3.is_perspective:
        return vi.translation.copy()
    # 정사영 뷰: 아주 멀리 뒤에서 보는 것처럼 (광선이 거의 평행)
    return vi.translation + vi.to_3x3() @ __import__(
        "mathutils").Vector((0.0, 0.0, 1.0e4))


def view_track(force=False):
    """뷰포트 시점 위치를 빈 오브젝트로 (오버레이가 그쪽으로 당겨짐)."""
    if not force and not any(o.name.startswith(_OVER_OB)
                             for o in bpy.data.objects):
        return
    loc = _view_point()
    if loc is None:
        return
    _set_view_loc(loc, force)


def _set_view_loc(loc, force=False):
    """시점 위치를 바로 쓰지 않고 '멈췄을 때' 한 번만 쓴다.

    화면을 돌리는 매 프레임마다 위치를 쓰면 그때마다 씬 전체가 다시
    계산되고(다른 애드온의 핸들러·N패널도 매번 다시 돌아감) 뷰포트가
    버벅인다. 시점이 잠깐(0.15초) 멈추면 그때 반영한다."""
    import time
    key = tuple(round(v, 4) for v in loc)
    if not force and key == _VIEW_STATE["m"]:
        _VIEW_STATE["pend"] = None
        return
    if force:
        _VIEW_STATE["m"] = key
        _VIEW_STATE["pend"] = None
        _view_empty().location = loc
        return
    p = _VIEW_STATE.get("pend")
    now = time.perf_counter()
    if p is None or p[0] != key:
        _VIEW_STATE["pend"] = (key, tuple(loc), now)   # 아직 움직이는 중
        return
    if now - p[2] >= 0.15:                             # 멈춘 지 0.15초
        _VIEW_STATE["m"] = key
        _VIEW_STATE["pend"] = None
        _view_empty().location = p[1]


def _live_on():
    try:
        return any(e.over_live for e in bpy.context.scene.fskr.eyes)
    except Exception:
        return False


def _view_draw():
    """화면을 그릴 때 바로 시점 갱신 (타이머보다 지연이 적음)."""
    try:
        if _VIEW_EMPTY not in bpy.data.objects or not _live_on():
            return
        ctx = bpy.context
        area, r3 = ctx.area, ctx.region_data
        if area is None or r3 is None:
            return
        # 가장 큰 3D 뷰만 기준 (여러 뷰가 서로 싸우지 않게)
        big = max((a for a in ctx.window.screen.areas
                   if a.type == 'VIEW_3D'),
                  key=lambda a: a.width * a.height, default=None)
        if big is None or big.as_pointer() != area.as_pointer():
            return
        loc = _view_point(r3)
        if loc is not None:
            _set_view_loc(loc)
    except Exception:
        pass


_VIEW_DRAW = {"h": None}


def _view_tick():
    try:
        view_track()
    except Exception:
        pass
    # 시점이 멈추길 기다리는 중이면 자주, 아니면 드물게 확인
    return 0.05 if _VIEW_STATE.get("pend") else 0.25


def light_apply(context, s):
    """가벼운 모드 켜기/끄기를 모든 캔버스에 적용 (다시 바인드)."""
    n = 0
    for st in s.eyes:
        cv = bpy.data.objects.get(st.target)
        if cv is None or cv.type != 'MESH':
            continue
        sd = cv.modifiers.get(_FOLLOW_MOD)
        if sd is None:
            continue
        on_cage = sd.target is not None and bool(sd.target.get("fskr_src"))
        if on_cage == bool(s.canvas_light):
            try:
                wrap_modes(cv)
            except Exception:
                pass
            continue
        face = canvas_face(cv)
        if face is None:
            continue
        err = canvas_follow_face(context, cv, face)
        if err:
            print("FSKR light mode:", err)
        n += 1
    if not s.canvas_light:   # 안 쓰는 케이지 정리
        used = {m.target.name for ob in bpy.data.objects
                for m in getattr(ob, "modifiers", ())
                if getattr(m, "target", None) is not None}
        for ob in list(bpy.data.objects):
            if ob.name.startswith(_CAGE_PREFIX) and ob.name not in used:
                bpy.data.objects.remove(ob)
    return n


def _light_cb(self, context):
    try:
        light_apply(context, self)
    except Exception as e:
        print("FSKR light mode:", e)
    _redraw_ui(context)


FSKR_Settings.__annotations__["canvas_light"] = bpy.props.BoolProperty(
    name="뷰포트 가볍게", default=False, update=_light_cb,
    description="캔버스가 얼굴의 서브디비전 없이 같은 변형(아마추어·셰이프 "
                "키)만 따라가게 합니다. 리그를 움직이거나 재생할 때 훨씬 "
                "가볍고(얼굴 GPU 서브디비전도 다시 켜짐), 렌더에서는 지금처럼 "
                "실제 얼굴 표면에 딱 맞습니다. 뷰포트에서는 파츠가 얼굴에서 "
                "아주 살짝 더 떠 보일 수 있습니다")


def _over_upgrade():
    """예전 방식(메시 공유) 복사본을 새 방식으로. 편 캔버스는 되돌림."""
    try:
        s = bpy.context.scene.fskr
        # 1.0.183: '뷰포트 가볍게'(1.0.182)는 되돌림 — 켜져 있던 캔버스는
        # 원래대로 실제 얼굴에 다시 붙인다
        try:
            if s.get("canvas_light", False) or any(
                    o.name.startswith(_CAGE_PREFIX) for o in bpy.data.objects):
                s["canvas_light"] = False
                light_apply(bpy.context, s)
        except Exception as e:
            print("FSKR light revert:", e)
        for st in s.eyes:
            cv = bpy.data.objects.get(st.target)
            if cv is not None and cv.type == 'MESH':
                try:
                    canvas_unflatten(bpy.context, cv)
                except Exception as e:
                    print("FSKR unflatten:", e)
                try:
                    lift_init(st)
                except Exception as e:
                    print("FSKR lift:", e)
                # 1.0.131: 시트 이미지 가장자리 흰 선 제거 (한 번만)
                try:
                    from .face_ui import fix_edge_bleed
                    for sh in st.sheets:
                        im9 = bpy.data.images.get(sh.image)
                        if im9 is not None and not im9.get("fskr_bleed_fixed"):
                            fix_edge_bleed(im9)
                except Exception as e:
                    print("FSKR edge fix:", e)
                if s.rig is not None:     # 1.0.130: 값 제한 넓힘
                    for L9 in st.layers:
                        try:
                            _ensure_anim_props(s.rig, *_anim_source(s, st, L9))
                        except Exception:
                            pass
                # 1.0.119 크롭: 예전 머티리얼이면 다시 만들어 크롭 노드 추가
                rig9 = s.rig
                if rig9 is not None and st.built and any(
                        _p_crop(*_anim_source(s, st, L), "t")
                        not in rig9.keys() for L in st.layers):
                    try:
                        eye_build(s, st)
                    except Exception as e:
                        print("FSKR crop upgrade:", e)
                _wrap_on(cv)
                try:
                    canvas_uv_remember(s, st)
                except Exception as e:
                    print("FSKR uv remember:", e)
    except Exception:
        pass
    try:
        s = bpy.context.scene.fskr
        for st in s.eyes:
            ob = bpy.data.objects.get(_over_name(st))
            cv = bpy.data.objects.get(st.target)
            if ob is not None and cv is not None and (
                    ob.data is cv.data or not any(
                        m.type == 'NODES' and m.node_group is not None
                        and m.node_group.get("fskr_v") == 5
                        for m in ob.modifiers)):
                over_sync(s, st)
    except Exception as e:
        print("FSKR over upgrade:", e)
    return None


@bpy.app.handlers.persistent
def _over_cam_sync(scene, *_a):
    """렌더 직전: 앞쪽 복사본이 '지금 씬 카메라' 쪽으로 당겨지게."""
    try:
        cam = scene.camera
        if cam is None:
            return
        for st in scene.fskr.eyes:
            ng = bpy.data.node_groups.get(_OVER_GN + "_" + st.uid)
            n = ng.nodes.get("cam") if ng is not None else None
            if n is not None and n.inputs["Object"].default_value is not cam:
                n.inputs["Object"].default_value = cam
    except Exception:
        pass


@bpy.app.handlers.persistent
def _over_on_load(*_a):
    try:
        bpy.app.timers.register(_over_upgrade, first_interval=0.3)
    except Exception:
        pass


def over_register():
    try:
        app_handler_add(bpy.app.handlers.load_post, _names_on_load)
        bpy.app.timers.register(_names_tick, first_interval=0.6)
    except Exception:
        pass
    try:
        app_handler_add(bpy.app.handlers.load_post, _over_on_load)
        for hl in (bpy.app.handlers.render_pre,
                   bpy.app.handlers.frame_change_pre):
            app_handler_add(hl, _over_cam_sync)
        bpy.app.timers.register(_over_upgrade, first_interval=0.5)
    except Exception:
        pass
    try:
        if not bpy.app.timers.is_registered(_view_tick):
            bpy.app.timers.register(_view_tick, first_interval=0.5,
                                    persistent=True)
    except Exception:
        pass
    try:
        _VIEW_DRAW["h"] = draw_add(bpy.types.SpaceView3D, _view_draw, (),
                                   'WINDOW', 'PRE_VIEW', "eye_view")
    except Exception:
        pass


def over_unregister():
    draw_remove("eye_view")
    _VIEW_DRAW["h"] = None
    try:
        if _over_on_load in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.remove(_over_on_load)
        for hl in (bpy.app.handlers.render_pre,
                   bpy.app.handlers.frame_change_pre):
            if _over_cam_sync in hl:
                hl.remove(_over_cam_sync)
    except Exception:
        pass
    try:
        if bpy.app.timers.is_registered(_view_tick):
            bpy.app.timers.unregister(_view_tick)
    except Exception:
        pass


# ----- 리그 프로퍼티 이름 (도프시트에 보이는 이름) -----
# 'Iris_Pos_X', 'Mouth_Size_Y', 'Mouth_Cell_Row' 처럼 파츠 이름 + 속성.
# 파츠 이름을 바꾸면 프로퍼티·키·드라이버를 같이 옮긴다.

def _san(name, d="Part"):
    t = re.sub(r"[\s.\-/]+", "_", (name or "").strip())
    t = re.sub(r"[\"'\[\]\\]", "", t).strip("_")
    return t[:40] or d


def _desired_keys(s):
    used = set()
    stk, lay, atl = {}, {}, {}
    for i, st in enumerate(s.eyes):
        k = "Expression" if i == 0 else _san(st.name, "Canvas") + \
            "_Expression"
        while k in used:
            k += "_" + st.uid
        used.add(k)
        stk[st.uid] = k
    for st in s.eyes:
        for L in st.layers:
            k = _san(L.name)
            if k in used:
                k = _san(st.name, "Canvas") + "_" + k
            while k in used:
                k += "_" + L.lid
            used.add(k)
            lay[(st.uid, L.lid)] = k
    for it in s.atlases:
        ml = mouth_layers(s, it)
        if ml:
            k = lay[(ml[0][0].uid, ml[0][1].lid)]
        else:
            k = _san(it.name, "Sheet")
            while k in used:
                k += "_" + it.uid
            used.add(k)
        atl[it.uid] = k
    return stk, lay, atl


def _all_prop_names(s):
    from .preset_vp import prop_name
    out = []
    for st in s.eyes:
        out.append(prop_name(st))
        for L in st.layers:
            cp = _prop_cell(st, L)
            out += [cp, _prop_cell_pv(cp)] + list(_anim_props(st, L))
    for it in s.atlases:
        out += [AT._prop_row(it), AT._prop_col(it), AT._prop_talk(it),
                AT._prop_q(it)] + [AT._prop_pv(it, k) for k in "rctq"]
    return out


def _all_fcurves():
    for act in bpy.data.actions:
        fcs = getattr(act, "fcurves", None)
        if fcs is not None:
            yield from fcs
            continue
        try:
            for ly in act.layers:
                for strip in ly.strips:
                    for cb in strip.channelbags:
                        yield from cb.fcurves
        except Exception:
            pass


def _all_drivers():
    for coll in (bpy.data.objects, bpy.data.materials, bpy.data.node_groups,
                 bpy.data.meshes, bpy.data.armatures, bpy.data.shape_keys,
                 bpy.data.scenes, bpy.data.worlds):
        for idb in coll:
            ad = getattr(idb, "animation_data", None)
            nt = getattr(idb, "node_tree", None)
            for a in (ad, getattr(nt, "animation_data", None)
                      if nt is not None else None):
                if a is not None:
                    yield from a.drivers


def _rename_props(rig, mapping):
    """리그 커스텀 프로퍼티 이름 바꾸기 + 키(F-커브)·드라이버 경로도 함께."""
    if not mapping:
        return
    tmp = {}
    for i, (o, n) in enumerate(mapping.items()):   # 두 단계 (a→b, b→c 대비)
        t = "__fskr_tmp_%d" % i
        tmp[o] = t
    for phase in (tmp, {tmp[o]: n for o, n in mapping.items()}):
        paths = {'["%s"]' % o: '["%s"]' % n for o, n in phase.items()}
        for o, n in phase.items():
            if o not in rig.keys():
                continue
            ui = None
            try:
                ui = rig.id_properties_ui(o).as_dict()
            except Exception:
                pass
            rig[n] = rig[o]
            del rig[o]
            if ui:
                try:
                    rig.id_properties_ui(n).update(**{
                        k: v for k, v in ui.items()
                        if k in ("min", "max", "soft_min", "soft_max",
                                 "step", "precision", "subtype",
                                 "description", "default")})
                except Exception:
                    pass
        for fc in _all_fcurves():
            np_ = paths.get(fc.data_path)
            if np_ is not None:
                try:
                    fc.data_path = np_
                except Exception:
                    pass
        for fc in _all_drivers():
            for var in fc.driver.variables:
                for t in var.targets:
                    np_ = paths.get(t.data_path)
                    if np_ is not None:
                        t.data_path = np_
    try:
        rig.update_tag()
    except Exception:
        pass


def sync_prop_names(s):
    """파츠 이름 기준으로 리그 프로퍼티 이름을 맞춘다 (바뀐 개수)."""
    if s.rig is None:
        return 0
    stk, lay, atl = _desired_keys(s)
    if all(st.pkey == stk[st.uid] for st in s.eyes) and \
            all(L.pkey == lay[(st.uid, L.lid)] for st in s.eyes
                for L in st.layers) and \
            all(it.pkey == atl[it.uid] for it in s.atlases):
        return 0
    old = _all_prop_names(s)
    for st in s.eyes:
        st.pkey = stk[st.uid]
        for L in st.layers:
            L.pkey = lay[(st.uid, L.lid)]
    for it in s.atlases:
        it.pkey = atl[it.uid]
    new = _all_prop_names(s)
    mp = {o: n for o, n in zip(old, new) if o != n}
    _rename_props(s.rig, mp)
    return len(mp)


def _canvas_name_cb(st, context):
    """캔버스 이름 변경 → 리그 프로퍼티 이름 + 뷰포트 컨트롤러 제목 갱신."""
    import json
    try:
        s = context.scene.fskr
        if not any(e == st for e in s.eyes):
            return
        sync_prop_names(s)
    except Exception as e:
        print("FSKR canvas rename:", e)
        return
    for nm in ("FPLBL_eye_" + st.uid, "FPLBL_pre_" + st.uid):
        lb = bpy.data.objects.get(nm)
        if lb is None or lb.type != 'FONT':
            continue
        try:
            parts = json.loads(lb.get("fskr_lbl", "[]"))
        except Exception:
            parts = []
        if parts:
            parts[0] = [st.name + " · ", False]
            lb["fskr_lbl"] = json.dumps(parts, ensure_ascii=False)
        try:
            from .atlas_vp import _lbl_body
            lb.data.body = _lbl_body(parts) if parts else st.name
        except Exception:
            pass
    try:
        from . import preset_vp as PV, layer_vp as LV
        if s.rig is not None:
            PV.fit_labels(s.rig, st, force=True)
        LV._GFIT.pop(st.uid, None)
        LV.fit_gaze_labels(context.scene)
    except Exception as e:
        print("FSKR canvas relabel:", e)


def _layer_name_cb(self, context):
    try:
        sync_prop_names(context.scene.fskr)
    except Exception as e:
        print("FSKR prop rename:", e)
    _rebuild_cb(self, context)


@bpy.app.handlers.persistent
def _names_on_load(*_a):
    try:
        bpy.app.timers.register(_names_tick, first_interval=0.4)
    except Exception:
        pass


def _names_tick():
    try:
        n = sync_prop_names(bpy.context.scene.fskr)
        if n:
            print("FSKR: renamed %d rig properties" % n)
    except Exception as e:
        print("FSKR prop names:", e)
    try:
        parent_cell_migrate(bpy.context.scene.fskr)
    except Exception as e:
        print("FSKR parent cell migrate:", e)
    return None


def parent_cell_migrate(s):
    """1.0.219: 자식이 부모의 위치·회전·크기·불투명도·색을 모두 따라감.
    예전 자식(묶음 정보 없음)이 있으면 보이는 그대로 옮기고 재구성."""
    n = 0
    for st in s.eyes:
        if not any(layer_parent(st, L) is not None and not L.bind_ok
                   for L in st.layers):
            continue
        if st.built:
            eye_build(s, st)
        else:
            bind_migrate(s, st)
        n += 1
    return n


def eye_build(s, st):
    """눈 머티리얼을 현재 레이어 설정대로 다시 만든다. 오류 문자열 반환."""
    try:
        sync_prop_names(s)
    except Exception as e:
        print("FSKR prop names:", e)
    for st9 in {st.uid: st, _src_stack(s, st).uid: _src_stack(s, st)}.values():
        try:
            bind_migrate(s, st9)
        except Exception as e:
            print("FSKR bind migrate:", e)
    err = _eye_mat(s, st, False)
    if not err:
        try:
            over_sync(s, st)
        except Exception as e:
            print("FSKR over:", e)
    return err


def _eye_mat(s, st, over=False):
    """over=True: '머리카락 위로' 파츠만 그리는 앞쪽 오버레이 머티리얼."""
    rig = s.rig
    if rig is None:
        return _tr("리그를 먼저 지정하세요")
    ob = bpy.data.objects.get(st.target)
    if ob is None or ob.type != 'MESH':
        return _tr("대상이 메시가 아닙니다")
    name = _MAT_PREFIX + st.uid + (_OVER_SUFFIX if over else "")
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    if nt.animation_data is not None:
        for fc in list(nt.animation_data.drivers):
            nt.animation_data.drivers.remove(fc)
    nt.nodes.clear()
    for attr, val in (("surface_render_method", 'BLENDED'),
                      ("blend_method", 'BLEND'),
                      ("use_backface_culling", False)):
        try:
            setattr(mat, attr, val)
        except Exception:
            pass
    N = nt.nodes
    Lk = nt.links

    def node(tp, x, y, **kw):
        n = N.new(tp)
        n.location = (x, y)
        for k, v in kw.items():
            setattr(n, k, v)
        return n

    def link(a, b):
        Lk.new(a, b)

    def math(op, a, b, x, y, clamp=False):
        n = node('ShaderNodeMath', x, y, operation=op, use_clamp=clamp)
        for i, v in enumerate((a, b)):
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                link(v, n.inputs[i])
        return n.outputs[0]

    def vscale(v, sc, x, y):
        n = node('ShaderNodeVectorMath', x, y, operation='SCALE')
        link(v, n.inputs[0])
        if isinstance(sc, (int, float)):
            n.inputs["Scale"].default_value = sc
        else:
            link(sc, n.inputs["Scale"])
        return n.outputs[0]

    def vadd(a, b, x, y):
        n = node('ShaderNodeVectorMath', x, y, operation='ADD')
        link(a, n.inputs[0])
        link(b, n.inputs[1])
        return n.outputs[0]

    def mixc(fac, a, b, x, y, blend='MIX'):
        n = node('ShaderNodeMix', x, y, data_type='RGBA', blend_type=blend)
        n.clamp_result = False
        if isinstance(fac, (int, float)):
            n.inputs[0].default_value = fac
        else:
            link(fac, n.inputs[0])
        link(a, n.inputs[6])
        link(b, n.inputs[7])
        return n.outputs[2]

    out = node('ShaderNodeOutputMaterial', 2600, 0)
    mix = node('ShaderNodeMixShader', 2400, 0)
    tr = node('ShaderNodeBsdfTransparent', 2200, 120)
    em = node('ShaderNodeEmission', 2200, -60)
    link(tr.outputs[0], mix.inputs[1])
    link(em.outputs[0], mix.inputs[2])
    link(mix.outputs[0], out.inputs["Surface"])
    uvn = node('ShaderNodeUVMap', -2000, 0)
    if st.uv_map:
        uvn.uv_map = st.uv_map
    base_uv = uvn.outputs[0]

    gsrc = _src_stack(s, st)
    mall = _mirror_all(s, st)
    lst = gsrc if mall else st          # 레이어 목록을 가져올 스택
    if mall:
        # 왼눈 그림 전체를 좌우 반전: u -> 1 - u
        fm = node('ShaderNodeMapping', -1850, 0, vector_type='POINT')
        fm.inputs["Location"].default_value = (1.0, 0.0, 0.0)
        fm.inputs["Scale"].default_value = (-1.0, 1.0, 1.0)
        link(base_uv, fm.inputs["Vector"])
        base_uv = fm.outputs[0]
    # 패럴랙스: 레이어 깊이만큼, 보는 방향에 따라 UV를 밀어 입체감
    #   off = -깊이 · (V·T, V·B) / max(V·N, 0.2)   (T,B = UV의 u,v 방향)
    plx = None
    if any(_eff_depth(lst, L) for L in lst.layers):
        geo = node('ShaderNodeNewGeometry', -2300, 400)
        tg = node('ShaderNodeTangent', -2300, 200, direction_type='UV_MAP')
        if st.uv_map:
            tg.uv_map = st.uv_map

        def vm(op, a, b, x, y9):
            n9 = node('ShaderNodeVectorMath', x, y9, operation=op)
            link(a, n9.inputs[0])
            link(b, n9.inputs[1])
            return n9
        bt = vm('CROSS_PRODUCT', geo.outputs["Normal"], tg.outputs[0],
                -2100, 250).outputs[0]
        vx = vm('DOT_PRODUCT', geo.outputs["Incoming"], tg.outputs[0],
                -2100, 450).outputs["Value"]
        vy = vm('DOT_PRODUCT', geo.outputs["Incoming"], bt,
                -2100, 350).outputs["Value"]
        vz = vm('DOT_PRODUCT', geo.outputs["Incoming"],
                geo.outputs["Normal"], -2100, 150).outputs["Value"]
        vz = math('MAXIMUM', vz, 0.2, -1950, 150)
        cx = math('DIVIDE', vx, vz, -1950, 450)
        if mall:
            cx = math('MULTIPLY', cx, -1.0, -1900, 450)
        cy = math('DIVIDE', vy, vz, -1950, 350)
        cmb = node('ShaderNodeCombineXYZ', -1800, 400)
        link(cx, cmb.inputs[0])
        link(cy, cmb.inputs[1])
        stn = node('ShaderNodeValue', -1800, 250)
        stn.name = "FSKR_parallax"
        stn.label = "parallax strength"
        stn.outputs[0].default_value = st.parallax
        plx = vscale(cmb.outputs[0], stn.outputs[0], -1650, 400)
    gpad = _pad_name(gsrc)
    sgn = 1.0
    if gsrc is not st and st.mirror:
        sgn = -sgn
    if mall:
        sgn = -sgn  # 반전된 공간에서 같은 방향을 보도록
    gx_dp = 'pose.bones["%s"].location[0]' % gpad
    gy_dp = 'pose.bones["%s"].location[1]' % gpad

    # 숨긴 파츠도 셰이더에 넣고 '보이기' 값(키 가능)으로 끈다
    layers = [L for L in lst.layers if _layer_image(s, L) is not None]
    draw_lids = None
    if over:
        # 앞쪽에 그릴 파츠 + 그 파츠의 클리핑 마스크로 쓰이는 파츠(마스크만)
        draw_lids = {L.lid for L in layers if L.over and L.kind != 'MOUTH'}
        need = set(draw_lids)
        # 부모(크롭 상속용)도 마스크로만 포함
        for L9 in layers:
            if L9.lid in draw_lids:
                need |= {A.lid for A in layer_ancestors(lst, L9)}
        stack9 = list(need)
        while stack9:
            L9 = _layer(lst, stack9.pop())
            for ck in (clip_chain(lst, L9) if L9 is not None else ()):
                if ck not in need:
                    need.add(ck)
                    stack9.append(ck)
        layers = [L for L in layers if L.lid in need and L.kind != 'MOUTH']
    raw = {}   # lid -> (color, alpha, y)
    cmask = {}     # lid -> [복사본별 크롭 창 마스크]
    pending = []   # 크롭 상속 뒤에 합칠 레이어들
    xinfo = {}     # lid -> (칸별 보정 여부, 노드 이름 함수, 바인드 함수)
    y = 0
    for L in layers:
        cols, rows = _layer_grid(s, L)
        n = cols * rows
        ait = _layer_atlas(s, L)       # 입 레이어면 입 스프라이트 시트
        ptab = _px_tab(s, lst, L) if ait is None else None  # 일반 파츠 칸별
        y -= 520
        ast, aL = _anim_source(s, lst, L)

        def xname(kind, _L=L, _ait=ait, _pt=ptab):
            if _ait is not None:
                return "%s%s_%s_%s" % (AT.LX_PREFIX, _ait.uid, kind, _L.lid)
            return _px_name(_pt[0], _pt[1], kind, _L)

        def xbind(fc, role, _ait=ait, _pt=ptab):
            if _ait is not None:
                AT.atlas_bind(s, _ait, fc, role)
            else:
                _px_bind(rig, fc, _pt, role)
        cellx = ait is not None or ptab is not None
        _ensure_anim_props(rig, ast, aL)
        pairs = [("px", rig, '["%s"]' % _p_px(ast, aL)),
                 ("py", rig, '["%s"]' % _p_py(ast, aL))]
        # 파츠 배치 (데칼 공간, 파츠 중심 기준):
        #   q = c + S^-1 · R(-θ) · (p - 이동 - 시선 - c),  c = (0.5, 0.5)
        # 크기 1 = 칸 하나가 데칼 전체, 0.3 = 데칼의 30% 크기
        tpairs = {"rot": ("r", rig, '["%s"]' % _p_rot(ast, aL)),
                  "sx": ("sx", rig, '["%s"]' % _p_sx(ast, aL)),
                  "sy": ("sy", rig, '["%s"]' % _p_sy(ast, aL))}
        mu, mv = marker_uv(lst, L.tag)
        # 기준점 c (파츠 중심 모드): q = c + S^-1·R(-θ)·(p - m - o - (c-0.5))
        pcu, pcv = _pivot_eff(L)
        mu, mv = mu + (pcu - 0.5), mv + (pcv - 0.5)

        chain = layer_ancestors(lst, L)

        def move_exprs(X, xast, xaL, xmu, xmv, gsign):
            """X 자체 이동 (위치 + X의 시선). 부모 몫은 따로 (위 체인)."""
            ex, ey = "-px-(%.6g)" % xmu, "-py-(%.6g)" % xmv
            px_ = [("px", rig, '["%s"]' % _p_px(xast, xaL))]
            py_ = [("py", rig, '["%s"]' % _p_py(xast, xaL))]
            gmx = gmy = (X.look_mul if X.look else 0.0)
            if (gmx or gmy) and gpad in rig.pose.bones:
                rr, rl = st.range_x, (st.range_x if st.link_x
                                      else st.range_xl)
                ru, rd = st.range_y, (st.range_y if st.link_y
                                      else st.range_yd)
                k = gmx * sgn * gsign / PAD
                # 오른쪽(+)/왼쪽(-) 범위를 따로: max(g,0)*R + min(g,0)*L
                ex += "-(max(gx,0)*(%.6g)+min(gx,0)*(%.6g))" % (rr * k,
                                                                rl * k)
                ey += "-(max(gy,0)*(%.6g)+min(gy,0)*(%.6g))" % (
                    ru * gmy / PAD, rd * gmy / PAD)
                px_.append(("gx", rig, gx_dp))
                py_.append(("gy", rig, gy_dp))
            return ex, ey, px_, py_

        def place_inv(X, v_in, ci, yy, own):
            """데칼 UV → X의 파츠 공간 q (X 자체 배치의 역변환).
            own=False 면 조상 복제본 (노드 이름 끝에 .in<자식 lid>)."""
            xast, xaL = (ast, aL) if own else _anim_source(s, lst, X)
            _ensure_anim_props(rig, xast, xaL)
            sfx = "" if own else ".in" + L.lid
            xmu, xmv = marker_uv(lst, X.tag)
            xcu, xcv = _pivot_eff(X)
            xmu, xmv = xmu + (xcu - 0.5), xmv + (xcv - 0.5)
            if own:
                xn, xb, xcell = xname, xbind, cellx
            else:
                pt9 = _px_tab(s, lst, X)
                xcell = pt9 is not None

                def xn(kind, _X=X, _pt=pt9):
                    return _px_name(_pt[0], _pt[1], kind, _X) + sfx

                def xb(fc, role, _pt=pt9):
                    _px_bind(rig, fc, _pt, role)
            lbl = L.name if own else "%s < %s" % (L.name, X.name)
            sh = node('ShaderNodeMapping', -1750, yy, vector_type='POINT')
            sh.name = "EYMV_%s_%s_%d%s" % (lst.uid, X.lid, ci, sfx)
            sh.label = "%s: move" % lbl
            link(v_in, sh.inputs["Vector"])
            # 대칭 복사본은 반전된 공간이라 시선 좌우를 뒤집어 같은 방향을 봄
            ex, ey, pairs_x, pairs_y = move_exprs(X, xast, xaL, xmu, xmv,
                                                  -1.0 if ci else 1.0)
            _drv_vars(sh.inputs["Location"], 0, ex, pairs_x)
            _drv_vars(sh.inputs["Location"], 1, ey, pairs_y)
            out = sh.outputs[0]
            if xcell:   # 칸별 위치 보정 (조회표)
                xm = node('ShaderNodeMapping', -1675, yy - 60,
                          vector_type='POINT')
                xm.name = xn("M")
                xm.label = "%s: cell move" % lbl
                link(out, xm.inputs["Vector"])
                xb(xm.inputs["Location"].driver_add("default_value", 0),
                   'XPX')
                xb(xm.inputs["Location"].driver_add("default_value", 1),
                   'XPY')
                out = xm.outputs[0]
            ro = node('ShaderNodeMapping', -1600, yy, vector_type='POINT')
            ro.label = "%s: rotate" % lbl
            link(out, ro.inputs["Vector"])
            _drv_vars(ro.inputs["Rotation"], 2, "-r*0.0174533",
                      [("r", rig, '["%s"]' % _p_rot(xast, xaL))])
            out = ro.outputs[0]
            if xcell:   # 칸별 회전·크기 보정
                xr = node('ShaderNodeMapping', -1525, yy - 60,
                          vector_type='POINT')
                xr.name = xn("R")
                xr.label = "%s: cell rotate" % lbl
                link(out, xr.inputs["Vector"])
                xb(xr.inputs["Rotation"].driver_add("default_value", 2),
                   'XR')
                xs = node('ShaderNodeMapping', -1490, yy - 120,
                          vector_type='POINT')
                xs.name = xn("S")
                xs.label = "%s: cell size" % lbl
                link(xr.outputs[0], xs.inputs["Vector"])
                xb(xs.inputs["Scale"].driver_add("default_value", 0), 'XSX')
                xb(xs.inputs["Scale"].driver_add("default_value", 1), 'XSY')
                out = xs.outputs[0]
            sc = node('ShaderNodeMapping', -1450, yy, vector_type='POINT')
            sc.name = "EYSZ_%s_%s_%d%s" % (lst.uid, X.lid, ci, sfx)
            sc.label = "%s: size" % lbl
            link(out, sc.inputs["Vector"])
            sc.inputs["Location"].default_value = (xcu, xcv, 0.0)
            spx = ("sx", rig, '["%s"]' % _p_sx(xast, xaL))
            _drv_vars(sc.inputs["Scale"], 0, "1/max(sx,0.001)", [spx])
            if X.scale_lock:   # 고정: 세로 = 가로 × 켤 때의 비율
                _drv_vars(sc.inputs["Scale"], 1,
                          "1/max(sx*%.8g,0.001)" % float(X.aspect or 1.0),
                          [spx])
            else:
                _drv_vars(sc.inputs["Scale"], 1, "1/max(sy,0.001)",
                          [("sy", rig, '["%s"]' % _p_sy(xast, xaL))])
            return sc.outputs[0]

        def bind_node(X, v_in, ci, yy):
            """X 파츠 공간 → 데칼 (X의 부모를 지정한 순간의 부모 배치)."""
            al, s1, s2, be = aff_svd(layer_bind(X))
            b1 = node('ShaderNodeMapping', -1700, yy + 60,
                      vector_type='POINT')
            b1.label = "%s: parent bind" % X.name
            b1.inputs["Rotation"].default_value = (0.0, 0.0, be)
            link(v_in, b1.inputs["Vector"])
            b2 = node('ShaderNodeMapping', -1680, yy + 60,
                      vector_type='POINT')
            b2.name = "EYBD_%s_%s_%d.in%s" % (lst.uid, X.lid, ci, L.lid)
            b2.label = "%s: parent bind" % X.name
            b2.inputs["Scale"].default_value = (s1, s2, 1.0)
            b2.inputs["Rotation"].default_value = (0.0, 0.0, al)
            bx = layer_bind(X)
            b2.inputs["Location"].default_value = (bx[4], bx[5], 0.0)
            link(b1.outputs[0], b2.inputs["Vector"])
            return b2.outputs[0]

        luv = base_uv
        dep = _eff_depth(lst, L)
        if plx is not None and dep:
            luv = vadd(base_uv, vscale(plx, -dep, -1950, y + 100),
                       -1900, y + 100)
        srcs = [luv]
        if L.sym:  # 대칭: 데칼 가운데 기준으로 반대쪽에 하나 더 (그림도 반전)
            sm = node('ShaderNodeMapping', -1900, y - 260,
                      vector_type='POINT')
            sm.inputs["Location"].default_value = (1.0, 0.0, 0.0)
            sm.inputs["Scale"].default_value = (-1.0, 1.0, 1.0)
            link(luv, sm.inputs["Vector"])
            srcs.append(sm.outputs[0])
        coords = []
        for ci, src_uv in enumerate(srcs):
            yy = y - ci * 260
            v9 = src_uv
            # 조상(맨 위부터) → 부모 순으로: 부모의 지금 배치를 되돌린 뒤
            # 묶을 때의 배치로 다시 놓음 = 부모의 변화량만 자식에 적용
            seq = list(reversed(chain)) + [L]
            for i9 in range(len(seq) - 1):
                v9 = place_inv(seq[i9], v9, ci, yy, False)
                v9 = bind_node(seq[i9 + 1], v9, ci, yy)
            out9 = place_inv(L, v9, ci, yy, True)
            if ait is not None:   # 입: 시퀀스 단계 위치 보정 (파츠 공간 %)
                xf9 = node('ShaderNodeMapping', -1400, yy - 60,
                           vector_type='POINT')
                xf9.name = xname("F")
                xf9.label = "%s: step offset" % L.name
                link(out9, xf9.inputs["Vector"])
                xbind(xf9.inputs["Location"].driver_add(
                    "default_value", 0), 'XFX')
                xbind(xf9.inputs["Location"].driver_add(
                    "default_value", 1), 'XFY')
                out9 = xf9.outputs[0]
            coords.append(out9)
        # 칸 선택 (리그 프로퍼티). 입 레이어는 입 시트의 조회표를 그대로 씀
        if ait is None:
            cst, cL = _cell_source(s, lst, L)
            cp = _prop_cell(cst, cL)
            _ensure_prop(rig, cp, _ncells(cL))
        k = "min(max(floor((c if pv<0 else pv)+0.5),0),%d)" % (n - 1)
        if ait is None:
            _pv_cell_ensure(rig, cp, n)
        mouth_ofs = None
        if ait is not None:
            # 입 시트 마스크용 현재 칸 오프셋 (CU/CV)
            mouth_ofs = node('ShaderNodeCombineXYZ', -1150, y + 160)
            mouth_ofs.name = AT._MASK_PREFIX + ait.uid + "_ofs"
            AT.atlas_bind(s, ait, mouth_ofs.inputs[0].driver_add(
                "default_value"), 'CU')
            AT.atlas_bind(s, ait, mouth_ofs.inputs[1].driver_add(
                "default_value"), 'CV')
        # 크롭: 그림 영역(bbox) 기준으로 위/아래/왼쪽/오른쪽을 잘라냄
        #   화면 기준 방향이 되도록 좌우 반전 전 공간(q)에서 판정
        bb = None
        if ait is None:
            try:
                bb = cell_bbox(s, lst, L)
            except Exception:
                bb = None
        u0, u1, v0, v1 = bb if bb else (0.0, 1.0, 0.0, 1.0)
        if L.flip_x:
            u0, u1 = 1.0 - u1, 1.0 - u0
        cw_, ch_ = u1 - u0, v1 - v0
        crop_n = {}
        # 0이면 그 방향은 무한히 열어 둠 (자식에게 물려줄 때 안 잘리게)
        for side, expr in (("t", "%.6g-c*%.6g+(c<=0)*1e3" % (v1, ch_)),
                           ("b", "%.6g+c*%.6g-(c<=0)*1e3" % (v0, ch_)),
                           ("l", "%.6g+c*%.6g-(c<=0)*1e3" % (u0, cw_)),
                           ("r", "%.6g-c*%.6g+(c<=0)*1e3" % (u1, cw_))):
            yv = y + 200 - 40 * len(crop_n)
            if cellx:
                # 크롭 = 파츠 공통 값 + 칸별 보정 (조회표), 노드로 계산
                cv = node('ShaderNodeValue', -1500, yv)
                cv.label = "%s: crop %s" % (L.name, side)
                _drv_vars(cv.outputs[0], None, "c",
                          [("c", rig, '["%s"]' % _p_crop(ast, aL, side))])
                xc = node('ShaderNodeValue', -1500, yv - 20)
                xc.name = xname("C" + side.upper())
                xc.label = "%s: cell crop %s" % (L.name, side)
                xbind(xc.outputs[0].driver_add("default_value"),
                      'XC' + side.upper())
                ce = math('ADD', cv.outputs[0], xc.outputs[0], -1450, yv)
                off = math('MULTIPLY',
                           math('LESS_THAN', ce, 1e-7, -1400, yv - 20),
                           1e3, -1350, yv - 20)
                lo, span = {"t": (v1, -ch_), "b": (v0, ch_),
                            "l": (u0, cw_), "r": (u1, -cw_)}[side]
                edge = math('ADD', math('MULTIPLY', ce, span, -1400, yv),
                            lo, -1350, yv)
                crop_n[side] = math('ADD' if side in ("t", "r")
                                    else 'SUBTRACT', edge, off, -1300, yv)
                continue
            vn = node('ShaderNodeValue', -1300, yv)
            vn.label = "%s: crop %s" % (L.name, side)
            _drv_vars(vn.outputs[0], None, expr,
                      [("c", rig, '["%s"]' % _p_crop(ast, aL, side))])
            crop_n[side] = vn.outputs[0]
        samples = []
        cmask[L.lid] = []
        for ci, crd in enumerate(coords):
            yy = y - ci * 260
            sq = node('ShaderNodeSeparateXYZ', -1300, yy - 200)
            link(crd, sq.inputs[0])
            cm9 = math('MULTIPLY',
                       math('MULTIPLY',
                            math('GREATER_THAN', sq.outputs[0], crop_n["l"],
                                 -1200, yy - 180),
                            math('LESS_THAN', sq.outputs[0], crop_n["r"],
                                 -1200, yy - 210), -1100, yy - 190),
                       math('MULTIPLY',
                            math('GREATER_THAN', sq.outputs[1], crop_n["b"],
                                 -1200, yy - 240),
                            math('LESS_THAN', sq.outputs[1], crop_n["t"],
                                 -1200, yy - 270), -1100, yy - 250),
                       -1000, yy - 220)
            if L.flip_x:  # 좌우 반전 (파츠 그림만)
                fx = node('ShaderNodeMapping', -1300, yy,
                          vector_type='POINT')
                fx.inputs["Location"].default_value = (1.0, 0.0, 0.0)
                fx.inputs["Scale"].default_value = (-1.0, 1.0, 1.0)
                link(crd, fx.inputs["Vector"])
                crd = fx.outputs[0]
            sep = node('ShaderNodeSeparateXYZ', -1150, yy - 120)
            link(crd, sep.inputs[0])
            ins = math('MULTIPLY',
                       math('MULTIPLY',
                            math('GREATER_THAN', sep.outputs[0], 0.0,
                                 -1000, yy - 80),
                            math('LESS_THAN', sep.outputs[0], 1.0,
                                 -1000, yy - 120), -850, yy - 100),
                       math('MULTIPLY',
                            math('GREATER_THAN', sep.outputs[1], 0.0,
                                 -1000, yy - 160),
                            math('LESS_THAN', sep.outputs[1], 1.0,
                                 -1000, yy - 200), -850, yy - 180),
                       -700, yy - 140)
            if ait is None:
                cm = node('ShaderNodeMapping', -1150, yy,
                          vector_type='POINT')
                cm.label = "%s: cell" % L.name
                link(crd, cm.inputs["Vector"])
                cm.inputs["Scale"].default_value = (1.0 / cols, 1.0 / rows,
                                                    1.0)
                _drv_vars(cm.inputs["Location"], 0,
                          "(%s-floor(%s/%d)*%d)/%d" % (k, k, cols, cols,
                                                       cols),
                          [("c", rig, '["%s"]' % cp),
                           ("pv", rig, '["%s"]' % _prop_cell_pv(cp))])
                _drv_vars(cm.inputs["Location"], 1,
                          "1-(floor(%s/%d)+1)/%d" % (k, cols, rows),
                          [("c", rig, '["%s"]' % cp),
                           ("pv", rig, '["%s"]' % _prop_cell_pv(cp))])
            else:
                # 파츠 공간(0~1) → 입 시트의 "첫 칸" UV → 입 시트 Mapping
                # (시퀀스·말하기·칸별 크기/위치/반전이 그대로 적용됨)
                cw9, ch9 = 1.0 / cols, 1.0 / rows
                pre = node('ShaderNodeMapping', -1250, yy + 60,
                           vector_type='POINT')
                pre.inputs["Scale"].default_value = (cw9, ch9, 1.0)
                pre.inputs["Location"].default_value = (0.0, 1.0 - ch9, 0.0)
                link(crd, pre.inputs["Vector"])
                cm = node('ShaderNodeMapping', -1150, yy,
                          vector_type='POINT')
                cm.name = AT._MAP_PREFIX + ait.uid + "_canvas%d" % ci
                cm.label = "%s: mouth" % L.name
                link(pre.outputs[0], cm.inputs["Vector"])
                for idx, role in ((0, 'LU'), (1, 'LV')):
                    AT.atlas_bind(s, ait, cm.inputs["Location"].driver_add(
                        "default_value", idx), role)
                for idx, role in ((0, 'SU'), (1, 'SV')):
                    AT.atlas_bind(s, ait, cm.inputs["Scale"].driver_add(
                        "default_value", idx), role)
                # 입 시트 마스크: 현재 칸 밖(옆 칸) 샘플은 투명
                sub = node('ShaderNodeVectorMath', -1000, yy + 120,
                           operation='SUBTRACT')
                link(cm.outputs[0], sub.inputs[0])
                link(mouth_ofs.outputs[0], sub.inputs[1])
                sp2 = node('ShaderNodeSeparateXYZ', -900, yy + 120)
                link(sub.outputs[0], sp2.inputs[0])
                ex9, ey9 = AT._crop_margin(ait, cw9, ch9)
                for ti, (ax9, op9, val9) in enumerate(
                        AT._mask_tests(cw9, ch9, ex9, ey9)):
                    tn = node('ShaderNodeMath', -800, yy + 160 - 30 * ti,
                              operation=op9)
                    if ci == 0:
                        tn.name = AT._MASK_PREFIX + ait.uid + "_t%d" % ti
                    link(sp2.outputs[ax9], tn.inputs[0])
                    tn.inputs[1].default_value = val9
                    ins = math('MULTIPLY', ins, tn.outputs[0], -700,
                               yy + 160 - 30 * ti)
            tex = node('ShaderNodeTexImage', -950, yy)
            tex.image = _layer_image(s, L)
            tex.extension = 'CLIP'
            tex.interpolation = 'Linear'
            tex.label = L.name
            link(cm.outputs[0], tex.inputs["Vector"])
            a = math('MULTIPLY', tex.outputs["Alpha"], ins, -600, yy)
            a = math('MULTIPLY', a, cm9, -560, yy)
            cmask[L.lid].append(cm9)
            samples.append((tex.outputs["Color"], a))
        pending.append((L, samples, y, ast, aL))
        xinfo[L.lid] = (cellx, xname, xbind)

    # 3-b) 크롭은 자식에게도: 조상들의 크롭 창(같은 복사본 번호)을 곱함
    for L, samples, y, ast, aL in pending:
        anc = [A for A in layer_ancestors(lst, L) if A.lid in cmask]
        if anc:
            ns = []
            for ci, (c9, a9) in enumerate(samples):
                for A in anc:
                    ms = cmask[A.lid]
                    if ms:
                        a9 = math('MULTIPLY', a9, ms[ci if ci < len(ms)
                                                    else 0], -540,
                                  y - ci * 260 - 40)
                ns.append((c9, a9))
            samples = ns
        col, a = samples[0]
        if len(samples) > 1:  # 원본 위에 대칭 복사본 (겹치면 원본 우선)
            # 알파 기준 합성 (투명 픽셀의 색이 가장자리에 섞이지 않게):
            #   A = a + a2(1-a),  C = (c·a + c2·a2·(1-a)) / A
            c2, a2 = samples[1]
            w2 = math('MULTIPLY', a2, math('SUBTRACT', 1.0, a, -560,
                                           y - 300), -500, y - 300)
            A2 = math('ADD', a, w2, -420, y - 260, clamp=True)
            pc = vadd(vscale(col, a, -500, y), vscale(c2, w2, -500, y - 80),
                      -440, y)
            rec = math('DIVIDE', 1.0, math('MAXIMUM', A2, _EPS, -420,
                                           y - 340), -380, y - 340)
            col = vscale(pc, rec, -360, y)
            a = A2
        # 4) 색조/채도/명도 (Ctrl+U) + 색 덮기. 부모(조상) 것도 차례로 적용
        #    (자기 → 부모 → 조부모 …, 포토샵 그룹의 조정처럼)
        #    부모 것을 받을지는 자식 설정: HSV(기본 켬) / 색 덮기(기본 끔)
        for X in [L] + layer_ancestors(lst, L):
            own = X is L
            sfx = "" if own else ".in" + L.lid
            lbl = L.name if own else "%s < %s" % (L.name, X.name)
            if own or L.inh_hsv:
                hsv = node('ShaderNodeHueSaturation', -300, y)
                hsv.name = _hsv_node_name(lst, X) + sfx
                hsv.label = "%s: H/S/V" % lbl
                hsv.inputs["Hue"].default_value = 0.5 + X.hue
                hsv.inputs["Saturation"].default_value = X.sat
                hsv.inputs["Value"].default_value = X.val
                link(col, hsv.inputs["Color"])
                col = hsv.outputs[0]
            if getattr(X, "ov_on", False) and (own or L.inh_ov):
                ov = node('ShaderNodeMix', -220, y)
                ov.data_type = 'RGBA'
                ov.blend_type = {'MIX': 'MIX', 'COLOR': 'COLOR',
                                 'MULTIPLY': 'MULTIPLY'}.get(X.ov_mode, 'MIX')
                ov.clamp_result = True
                ov.name = _ov_node_name(lst, X) + sfx
                ov.label = "%s: overlay" % lbl
                ov.inputs[0].default_value = X.ov_fac
                link(col, ov.inputs[6])
                ov.inputs[7].default_value = _lin4(X.ov_color)
                col = ov.outputs[2]
        # 5) 불투명도 (키 가능)
        opn = node('ShaderNodeValue', -300, y - 200)
        opn.label = "%s: opacity" % L.name
        _ensure_anim_props(rig, ast, aL)
        vpairs = [("op", rig, '["%s"]' % _p_op(ast, aL)),
                  ("v", rig, '["%s"]' % _p_vis(ast, aL))]
        vexpr = "op*(v>=0.5)"
        # 부모(조상)의 불투명도·보이기도 곱함 (부모가 숨으면 자식도)
        for ai9, A9 in enumerate(layer_ancestors(lst, L)):
            bst9, bL9 = _anim_source(s, lst, A9)
            _ensure_anim_props(rig, bst9, bL9)
            vpairs.append(("a%d" % ai9, rig, '["%s"]' % _p_vis(bst9, bL9)))
            vpairs.append(("o%d" % ai9, rig, '["%s"]' % _p_op(bst9, bL9)))
            vexpr += "*(a%d>=0.5)*o%d" % (ai9, ai9)
        _drv_vars(opn.outputs[0], None, vexpr, vpairs)
        a = math('MULTIPLY', a, opn.outputs[0], -120, y - 160)
        for A9 in layer_ancestors(lst, L):   # 부모의 칸별 불투명도
            pa9 = _px_tab(s, lst, A9)
            if pa9 is None:
                continue
            ao = node('ShaderNodeValue', -300, y - 300)
            ao.name = "%s.in%s" % (_px_name(pa9[0], pa9[1], "OP", A9), L.lid)
            ao.label = "%s < %s: cell opacity" % (L.name, A9.name)
            _px_bind(rig, ao.outputs[0].driver_add("default_value"), pa9,
                     'XOP')
            a = math('MULTIPLY', a, ao.outputs[0], -80, y - 300)
        cellx, xname, xbind = xinfo.get(L.lid, (False, None, None))
        if cellx:   # 칸별 불투명도 보정
            xo = node('ShaderNodeValue', -300, y - 260)
            xo.name = xname("OP")
            xo.label = "%s: cell opacity" % L.name
            xbind(xo.outputs[0].driver_add("default_value"), 'XOP')
            a = math('MULTIPLY', a, xo.outputs[0], -60, y - 220)
        raw[L.lid] = (col, a, y)

    # 6) 클리핑 마스크: 대상 레이어의 최종 알파를 곱함 (순환 방지)
    final = {}

    def alpha_of(lid, stack):
        if lid in final:
            return final[lid]
        c, a, yy = raw[lid]
        L = _layer(lst, lid)
        # 자기 마스크 + 부모에게서 물려받은 마스크 모두 곱함
        for k9, mk in enumerate(clip_chain(lst, L) if L is not None else ()):
            if mk in raw and mk not in stack:
                a = math('MULTIPLY', a, alpha_of(mk, stack | {lid}),
                         40 + 60 * k9, yy)
        final[lid] = a
        return a
    for L in layers:
        alpha_of(L.lid, frozenset())

    # 7) 합성 (뒤 → 앞). 합성 모드는 아래 그림(Cb) 위에서만 적용:
    #    c' = mix(c, B(Cb, c), Ab),  P = c'·a + P·(1-a),  A = a + A·(1-a)
    P = None
    A = None
    x = 250
    for L in reversed(layers):
        if draw_lids is not None and L.lid not in draw_lids:
            continue
        c, _a, yy = raw[L.lid]
        a = final[L.lid]
        if over:
            # 파츠별 '머리카락 위 불투명도'
            ovn = node('ShaderNodeValue', x - 120, yy - 300)
            ovn.name = "FSKR_over_a_" + L.lid
            ovn.label = "%s: over alpha" % L.name
            ovn.outputs[0].default_value = L.over_alpha
            a = math('MULTIPLY', a, ovn.outputs[0], x, yy - 300)
        if P is not None and L.blend != 'MIX':
            rec = math('DIVIDE', 1.0, math('MAXIMUM', A, _EPS, x, yy + 200),
                       x + 120, yy + 200)
            cb = vscale(P, rec, x + 240, yy + 200)
            bl = mixc(1.0, cb, c, x + 360, yy + 120, blend=L.blend)
            c = mixc(A, c, bl, x + 480, yy + 60)
        ca = vscale(c, a, x + 600, yy)
        if P is None:
            P, A = ca, a
        else:
            inv = math('SUBTRACT', 1.0, a, x + 600, yy - 160)
            P = vadd(ca, vscale(P, inv, x + 720, yy - 80), x + 840, yy)
            A = math('ADD', a, math('MULTIPLY', A, inv, x + 720, yy - 220),
                     x + 840, yy - 220, clamp=True)
        x += 160
    if P is not None:
        rec = math('DIVIDE', 1.0, math('MAXIMUM', A, _EPS, 1900, -300),
                   2000, -300)
        link(vscale(P, rec, 2050, -60), em.inputs["Color"])
        link(A, mix.inputs[0])
    else:
        mix.inputs[0].default_value = 0.0
    # Solid 뷰의 '텍스처' 표시는 활성 이미지 노드를 그대로 보여 주므로
    # 시트 전체가 보이지 않게 활성 노드를 출력으로 둔다
    try:
        nt.nodes.active = out
    except Exception:
        pass
    if over:
        return mat
    _assign(ob, st, mat)
    st.built = True
    try:
        rig.update_tag()
        ob.update_tag()
    except Exception:
        pass
    # 이 눈을 따라가는 눈(전체 반전)도 같이 갱신
    for e in s.eyes:
        if e is not st and e.follow == st.uid and e.built \
                and _mirror_all(s, e):
            try:
                eye_build(s, e)
            except Exception:
                pass
    return ""



# ------------------------------------------------------------------
# 시선 패드 (뷰포트)
# ------------------------------------------------------------------

def _pad_remove(context, rig, st):
    if rig is None:
        return
    base = _pad_name(st)
    bones = [b.name for b in rig.data.bones
             if b.name == base or b.name.startswith(base + "_")]
    for ob in list(bpy.data.objects):
        if ob.name == "FPLBL_eye_" + st.uid:
            bpy.data.objects.remove(ob)
    ad = rig.animation_data
    if ad is not None:
        for fc in list(ad.drivers):
            if any(('"%s"' % b) in fc.data_path for b in bones):
                try:
                    ad.drivers.remove(fc)
                except Exception:
                    pass
    if not bones:
        return
    prev_mode = context.mode
    _to_object_mode(context, rig)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = rig.data.edit_bones
    for b in bones:
        if b in eb:
            eb.remove(eb[b])
    bpy.ops.object.mode_set(mode='OBJECT')
    if prev_mode == 'POSE':
        bpy.ops.object.mode_set(mode='POSE')


def _pad_build(context, s, st):
    """시선 패드 생성 (이미 있으면 그대로). 따라가는 눈은 만들지 않음."""
    rig = s.rig
    base = _pad_name(st)
    if base in rig.data.bones:
        return
    prev = context.view_layer.objects.active
    prev_mode = context.mode
    _to_object_mode(context, rig)
    _ensure_root(context, s, rig)
    pos = _next_position(rig, 0.18)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = rig.data.edit_bones
    f = eb.new(base + "_frame")
    f.head = pos
    f.tail = pos + Vector((0, 0, 0.02))
    f.use_deform = False
    f.parent = eb["FP_root"]
    h = eb.new(base)
    h.head = pos
    h.tail = pos + Vector((0, 0, 0.02))
    h.use_deform = False
    h.parent = f
    bpy.ops.object.mode_set(mode='OBJECT')
    from .core import _widget_coll, _wire_square
    coll = _widget_coll(context)
    w_frame = _wire_square(coll, "WGT_FP_frame")
    w_handle = _wire_square(coll, "WGT_FP_handle", cross=True)
    fb, hb = rig.pose.bones[base + "_frame"], rig.pose.bones[base]
    fb.custom_shape = w_frame
    fb.use_custom_shape_bone_size = False
    fb.custom_shape_scale_xyz = (2 * PAD + 0.03, 2 * PAD + 0.03, 1.0)
    fb["fskr_spr_top"] = PAD + 0.04
    hb.custom_shape = w_handle
    hb.use_custom_shape_bone_size = False
    hb.custom_shape_scale_xyz = (0.028, 0.028, 1.0)
    hb.lock_location[2] = True
    hb.lock_rotation = (True, True, True)
    hb.lock_scale = (True, True, True)
    c = hb.constraints.new('LIMIT_LOCATION')
    c.owner_space = 'LOCAL'
    c.use_transform_limit = True
    for attr in ("use_min_x", "use_max_x", "use_min_y", "use_max_y",
                 "use_min_z", "use_max_z"):
        setattr(c, attr, True)
    c.min_x, c.max_x = -PAD, PAD
    c.min_y, c.max_y = -PAD, PAD
    c.min_z = c.max_z = 0.0
    from .layer_vp import set_vcol
    set_vcol(hb, (0.55, 0.85, 1.0))
    set_vcol(fb, (0.30, 0.42, 0.55))
    from .core import arrange_for
    arr = arrange_for(s, base)
    rig.data.bones[base + "_frame"].hide_select = not arr
    rig.data.bones[base].hide_select = arr
    try:
        from .core import _fskr_apply_locks
        _fskr_apply_locks(rig, arr)
    except Exception:
        pass
    # ON/OFF 토글
    if "FP_toggle" in rig.data.bones:
        TH = TGL / 2
        for path, exprs in (
                ('pose.bones["%s"].custom_shape_scale_xyz' % (base + "_frame"),
                 ["%r*(t<%s)" % (2 * PAD + 0.03, TH)] * 2 + ["1.0"]),
                ('pose.bones["%s"].scale' % base, ["t<%s" % TH] * 3)):
            for fc in rig.driver_add(path):
                d = fc.driver
                d.type = 'SCRIPTED'
                d.expression = exprs[fc.array_index]
                v = d.variables.new()
                v.name = "t"
                v.type = 'SINGLE_PROP'
                v.targets[0].id = rig
                v.targets[0].data_path = 'pose.bones["FP_toggle"].location[0]'
    # 라벨
    context.view_layer.update()
    cu = bpy.data.curves.new("FPLBL_eye_" + st.uid, 'FONT')
    cu.body = "%s · %s" % (st.name, _tr("시선"))
    cu.size = 0.022
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    if any(ord(ch) > 127 for ch in cu.body):
        try:
            from .atlas_vp import _cjk_font
            fnt = _cjk_font()
            if fnt is not None:
                cu.font = fnt
        except Exception:
            pass
    lb = bpy.data.objects.new("FPLBL_eye_" + st.uid, cu)
    lb["fskr_lbl"] = json.dumps([[st.name + " · ", False], ["시선", True]],
                                ensure_ascii=False)
    context.scene.collection.objects.link(lb)
    lb.parent = rig
    lb.parent_type = 'BONE'
    lb.parent_bone = base + "_frame"
    context.view_layer.update()
    wpos = rig.matrix_world @ (fb.matrix @ Vector((0.0, PAD + 0.03, 0.0)))
    lb.matrix_world = (Matrix.Translation(wpos)
                       @ Matrix.Rotation(radians(90), 4, 'X'))
    lb.hide_select = True
    lb.hide_viewport = not s.labels_visible
    _text_toggle_driver(context.scene, rig, lb)
    if prev_mode == 'POSE':
        context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode='POSE')
    elif prev is not None:
        context.view_layer.objects.active = prev


# ------------------------------------------------------------------
# 오퍼레이터
# ------------------------------------------------------------------

def _new_lid(st):
    used = {L.lid for L in st.layers}
    i = 1
    while "L%d" % i in used:
        i += 1
    return "L%d" % i


class FSKR_OT_eye_add(bpy.types.Operator):
    bl_idname = "fskr.eye_add"
    bl_label = "눈 추가"
    bl_description = "선택한 눈 데칼 메시에 파츠 레이어 합성 머티리얼을 만듭니다"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        ob = context.active_object
        return (context.scene.fskr.rig is not None and ob is not None
                and ob.type == 'MESH')

    def execute(self, context):
        s = context.scene.fskr
        ob = context.active_object
        used = {e.uid for e in s.eyes}
        i = 1
        while "E%d" % i in used:
            i += 1
        st = s.eyes.add()
        st.uid = "E%d" % i
        st.name = ob.name
        st.target = ob.name
        _pad_build(context, s, st)
        err = eye_build(s, st)
        if err:
            self.report({'WARNING'}, err)
        context.view_layer.objects.active = ob
        _redraw_ui(context)
        return {'FINISHED'}


FACE_AXIS_ITEMS = (
    ('-Y', "-Y", "얼굴이 -Y를 봄 (정면 = 숫자패드 1). Blender 기본", 0),
    ('Y', "Y", "얼굴이 +Y를 봄 (정면 = Ctrl+숫자패드 1)", 1),
    ('X', "X", "얼굴이 +X를 봄 (정면 = 숫자패드 3)", 2),
    ('-X', "-X", "얼굴이 -X를 봄 (정면 = Ctrl+숫자패드 3)", 3),
)
_VIEW_OF_AXIS = {'-Y': 'FRONT', 'Y': 'BACK', 'X': 'RIGHT', '-X': 'LEFT'}


def face_lateral(s):
    """정면에서 봤을 때 화면 오른쪽(+u) 방향의 월드 좌표 값을 주는 함수."""
    ax = getattr(s, "face_axis", '-Y')
    if ax == 'Y':
        return lambda p: -p.x
    if ax == 'X':
        return lambda p: p.y
    if ax == '-X':
        return lambda p: -p.y
    return lambda p: p.x


def face_lateral_index(s):
    """좌우 대칭이 일어나는 월드 축 번호 (0 = X, 1 = Y)."""
    return 1 if getattr(s, "face_axis", '-Y') in ('X', '-X') else 0


def face_view(context, ob=None):
    """숫자패드 1처럼 얼굴 정면 뷰로 (축 설정 반영) + 캔버스를 가운데로."""
    s = context.scene.fskr
    vtype = _VIEW_OF_AXIS.get(getattr(s, "face_axis", '-Y'), 'FRONT')
    area = context.area if (context.area is not None
                            and context.area.type == 'VIEW_3D') else None
    if area is None:
        for a in context.window.screen.areas:
            if a.type == 'VIEW_3D':
                area = a
                break
    if area is None:
        return False
    region = next((r for r in area.regions if r.type == 'WINDOW'), None)
    if region is None:
        return False
    try:
        with context.temp_override(area=area, region=region):
            bpy.ops.view3d.view_axis(type=vtype)
    except Exception as e:
        print("FSKR face view:", e)
        return False
    if ob is not None:
        try:
            rv3d = area.spaces.active.region_3d
            bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
            c = sum(bb, Vector()) / 8.0
            size = max((max(p[i] for p in bb) - min(p[i] for p in bb))
                       for i in range(3))
            rv3d.view_location = c
            rv3d.view_distance = max(size * 1.8, 0.05)
        except Exception:
            pass
    return True


def _flip_name(n):
    """좌우 이름 뒤집기 (.L/.R, _L/_R, .l/.r, Left/Right)."""
    import re
    pairs = (("Left", "Right"), ("left", "right"), ("LEFT", "RIGHT"))
    for a9, b9 in pairs:
        if a9 in n:
            return n.replace(a9, b9)
        if b9 in n:
            return n.replace(b9, a9)
    m = re.match(r"^(.*[._\- ])([LlRr])(\.\d+)?$", n)
    if m:
        sd = {"L": "R", "R": "L", "l": "r", "r": "l"}[m.group(2)]
        return m.group(1) + sd + (m.group(3) or "")
    m = re.match(r"^([LlRr])([._\- ].*)$", n)
    if m:
        sd = {"L": "R", "R": "L", "l": "r", "r": "l"}[m.group(1)]
        return sd + m.group(2)
    return n


def _apply_mirror(ob, md):
    """Mirror 모디파이어(X축)를 메시 데이터에 적용 (셰이프 키 있어도 동작)."""
    import bmesh
    me = ob.data
    axes = [i for i, on in enumerate(md.use_axis) if on] or [0]
    bm = bmesh.new()
    bm.from_mesh(me)
    shape_layers = list(bm.verts.layers.shape.values())
    dl = bm.verts.layers.deform.active
    vg_names = [g.name for g in ob.vertex_groups]
    idx_of = {n: i for i, n in enumerate(vg_names)}
    flip_idx = {}
    if md.use_mirror_vertex_groups:
        for i, n in enumerate(vg_names):
            fn = _flip_name(n)
            if fn != n and fn not in idx_of:
                ob.vertex_groups.new(name=fn)
                idx_of[fn] = len(vg_names)
                vg_names.append(fn)
            flip_idx[i] = idx_of.get(fn, i)
    thr = md.merge_threshold if md.use_mirror_merge else 0.0
    for ax in axes:
        geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
        before = set(bm.verts)
        before_f = set(bm.faces)
        bmesh.ops.mirror(bm, geom=geom, axis='XYZ'[ax], merge_dist=thr)
        # 거울 복사된 면은 감김 방향이 반대 → 법선이 안쪽을 보지 않게 뒤집기
        newf = [f for f in bm.faces if f not in before_f]
        if newf:
            bmesh.ops.reverse_faces(bm, faces=newf)
        for v in bm.verts:
            if v in before:
                continue
            for sl in shape_layers:
                co = v[sl].copy()
                co[ax] = -co[ax]
                v[sl] = co
            if dl is not None and flip_idx:
                dv = v[dl]
                items = list(dv.items())
                dv.clear()
                for gi, w in items:
                    dv[flip_idx.get(gi, gi)] = w
    bm.to_mesh(me)
    bm.free()
    me.update()


# ------------------------------------------------------------------
# 캔버스가 얼굴 변형을 그대로 따라가게 (Surface Deform)
#   얼굴 메시의 최종 모양(아마추어·셰이프 키 등)을 그대로 옮겨 받으므로
#   캔버스에 따로 웨이트를 칠하거나 리그에 바인드할 필요가 없다.
# ------------------------------------------------------------------

_FOLLOW_MOD = "FSKR_Canvas_Follow"
_DEFORM_TYPES = {'ARMATURE', 'LATTICE', 'MESH_DEFORM', 'CORRECTIVE_SMOOTH',
                 'SMOOTH', 'LAPLACIANSMOOTH', 'HOOK', 'CAST', 'SIMPLE_DEFORM',
                 'WARP', 'WAVE', 'DISPLACE', 'CURVE', 'SURFACE_DEFORM',
                 'LAPLACIANDEFORM', 'DATA_TRANSFER'}


def canvas_face(cv):
    """캔버스가 붙어 있는 얼굴 메시 (Shrinkwrap/Surface Deform 대상).
    가벼운 모드의 대리 메시(케이지)면 원래 얼굴을 돌려준다."""
    for m in cv.modifiers:
        tg = getattr(m, "target", None)
        if m.type in ('SURFACE_DEFORM', 'SHRINKWRAP') and tg is not None \
                and tg.type == 'MESH':
            src = tg.get("fskr_src") if hasattr(tg, "get") else None
            if src:
                tg = bpy.data.objects.get(src) or tg
            return tg
    return None


# ----- 뷰포트 가볍게: 얼굴의 서브디비전 없이 따라가기 -----
#   캔버스가 얼굴의 '최종 모양'(서브디비전 포함)을 따라가면, Blender가 얼굴
#   서브디비전을 매번 CPU로 계산해야 해서(GPU 서브디비전도 꺼짐) 리그를
#   움직이거나 재생할 때 느려진다. 뷰포트에서는 얼굴과 같은 메시·변형(아마추어
#   ·셰이프 키·미러)만 가진 숨은 '케이지'를 따라가고, 렌더에서만 실제 얼굴
#   표면에 딱 맞춘다.

_CAGE_PREFIX = "FSKR_FaceCage_"
_WRAP = "FSKR_Canvas_Wrap"
_WRAP_VP = "FSKR_Canvas_WrapVP"
_NO_CAGE = {'SUBSURF', 'MULTIRES'}


def light_on():
    try:
        return bool(bpy.context.scene.fskr.canvas_light)
    except Exception:
        return True


def _copy_mod(src, dst):
    for p in src.bl_rna.properties:
        idn = p.identifier
        if p.is_readonly or idn in ("name", "type", "rna_type"):
            continue
        try:
            setattr(dst, idn, getattr(src, idn))
        except Exception:
            pass


def face_cage(context, face):
    """얼굴과 같은 메시·변형(서브디비전 제외)을 가진 숨은 대리 오브젝트."""
    name = (_CAGE_PREFIX + face.name)[:63]
    ob = bpy.data.objects.get(name)
    if ob is None:
        ob = bpy.data.objects.new(name, face.data)
        context.scene.collection.objects.link(ob)
    if ob.data is not face.data:
        ob.data = face.data
    ob["fskr_src"] = face.name
    # 위치: 얼굴 오브젝트를 그대로 따라감 (메시 모양에는 의존하지 않음)
    ob.parent = None
    ob.matrix_world = face.matrix_world.copy()
    c = ob.constraints.get("FSKR_follow") or ob.constraints.new(
        'COPY_TRANSFORMS')
    c.name = "FSKR_follow"
    c.target = face
    # 변형 모디파이어 복사 (서브디비전·멀티레스 제외)
    for m in list(ob.modifiers):
        ob.modifiers.remove(m)
    for m in face.modifiers:
        if m.type in _NO_CAGE:
            continue
        try:
            n = ob.modifiers.new(m.name, m.type)
        except Exception:
            continue
        _copy_mod(m, n)
    try:
        ob.show_only_shape_key = face.show_only_shape_key
    except Exception:
        pass
    ob.hide_render = True
    ob.hide_select = True
    ob.hide_viewport = True
    ob.display_type = 'BOUNDS'
    return ob


def wrap_modes(cv):
    """띄우기(Shrinkwrap): 가벼운 모드면 뷰포트는 케이지에, 렌더는 실제
    얼굴에. 아니면 실제 얼굴 하나로 둘 다."""
    sw = cv.modifiers.get(_WRAP)
    if sw is None:
        return
    vp = cv.modifiers.get(_WRAP_VP)
    sd = cv.modifiers.get(_FOLLOW_MOD)
    cage = sd.target if (sd is not None and sd.target is not None and
                         sd.target.get("fskr_src")) else None
    if cage is None:
        if vp is not None:
            cv.modifiers.remove(vp)
        sw.show_viewport = True
        sw.show_render = True
        return
    if vp is None:
        vp = cv.modifiers.new(_WRAP_VP, 'SHRINKWRAP')
    _copy_mod(sw, vp)
    vp.target = cage
    vp.show_viewport = True
    vp.show_render = False
    sw.show_viewport = False
    sw.show_render = True
    try:   # 원래 띄우기 바로 뒤로
        i = next(k for k, m in enumerate(cv.modifiers) if m.name == sw.name)
        j = next(k for k, m in enumerate(cv.modifiers) if m.name == vp.name)
        if j != i + 1:
            cv.modifiers.move(j, i + 1 if j > i else i)
    except Exception:
        pass


def _face_armatures(face):
    return [m.object for m in face.modifiers
            if m.type == 'ARMATURE' and m.object is not None]


def canvas_follow_face(context, cv, face):
    """캔버스의 변형 모디파이어를 정리하고 얼굴에 Surface Deform으로 붙인다.
    얼굴이 기본 자세(레스트·기본 셰이프)일 때 바인드. 오류 문자열 반환."""
    # 1) 따로 붙은 변형(아마추어 등) 제거 — 얼굴 변형을 그대로 받을 것이므로
    for m in list(cv.modifiers):
        if m.type in _DEFORM_TYPES:
            cv.modifiers.remove(m)
    # 2) 캔버스 자체 셰이프 키는 끔 (얼굴 셰이프 키 변형이 그대로 옮겨 옴)
    sk = cv.data.shape_keys
    if sk is not None:
        ad = sk.animation_data
        if ad is not None:
            for fc in ad.drivers:
                fc.mute = True
        for kb in sk.key_blocks[1:]:
            kb.value = 0.0
    # 3) Surface Deform (맨 앞). 가벼운 모드면 얼굴 대신 케이지를 따라감
    sd = cv.modifiers.new(_FOLLOW_MOD, 'SURFACE_DEFORM')
    tgt = face
    if light_on():
        try:
            tgt = face_cage(context, face)
        except Exception as e:
            print("FSKR face cage:", e)
            tgt = face
    sd.target = tgt
    try:
        sd.falloff = 4.0
    except Exception:
        pass
    i = next(k for k, m in enumerate(cv.modifiers) if m.name == sd.name)
    if i:
        try:
            cv.modifiers.move(i, 0)
        except Exception:
            with context.temp_override(object=cv, active_object=cv):
                bpy.ops.object.modifier_move_to_index(modifier=sd.name,
                                                      index=0)
    # 4) 얼굴을 기본 자세로 두고 바인드
    arms = _face_armatures(face)
    prev_pose = [(a, a.data.pose_position) for a in arms]
    prev_only = face.show_only_shape_key
    prev_idx = face.active_shape_key_index
    err = ""
    try:
        for a in arms:
            a.data.pose_position = 'REST'
        if face.data.shape_keys is not None:
            face.show_only_shape_key = True
            face.active_shape_key_index = 0
            if tgt is not face:
                tgt.show_only_shape_key = True
                tgt.active_shape_key_index = 0
        context.view_layer.update()
        with context.temp_override(object=cv, active_object=cv,
                                   selected_objects=[cv]):
            bpy.ops.object.surfacedeform_bind(modifier=sd.name)
        context.view_layer.update()
        if not sd.is_bound:
            err = _tr("바인드에 실패했습니다 (얼굴 메시 모양을 확인하세요)")
    except Exception as e:
        err = str(e)
    finally:
        for a, pp in prev_pose:
            a.data.pose_position = pp
        face.show_only_shape_key = prev_only
        face.active_shape_key_index = prev_idx
        if tgt is not face:
            tgt.show_only_shape_key = prev_only
            tgt.active_shape_key_index = prev_idx
        context.view_layer.update()
    try:
        wrap_modes(cv)
    except Exception as e:
        print("FSKR wrap modes:", e)
    return err


# ----- (예전 1.0.113) '평평하게' 되돌리기 -----
#   1.0.113에서 편 캔버스는 원래 위치를 메시 속성 fskr_rest 에 보관했다.
#   기능을 없앴으므로, 남아 있으면 원래 모양으로 되돌리고 다시 붙인다.

_REST_ATTR = "fskr_rest"


def canvas_unflatten(context, cv):
    me = cv.data
    at = me.attributes.get(_REST_ATTR)
    if at is None or len(at.data) != len(me.vertices):
        return False
    for i, v in enumerate(me.vertices):
        v.co = at.data[i].vector
    me.attributes.remove(me.attributes[_REST_ATTR])
    me.update()
    sw = cv.modifiers.get("FSKR_Canvas_Wrap")
    if sw is not None:
        sw.wrap_mode = 'ABOVE_SURFACE'
    face = canvas_face(cv)
    if face is not None:
        canvas_follow_face(context, cv, face)
    return True


# ----- 캔버스 메시를 직접 고친 뒤 정리 (UV 이어 붙이기 + 다시 붙이기) -----
#   정면 투영 UV: u = a·(정면 기준 가로 좌표) + b,  v = c·(월드 Z) + d
#   만들 때의 a,b,c,d 를 보관해 두면, Extrude 등으로 늘린 면에도 같은
#   투영을 이어서 줄 수 있다 (기존 면 UV·마커·파츠 위치는 그대로).

def _canvas_uv_samples(s, cv, uvname):
    me = cv.data
    uvl = me.uv_layers.get(uvname) if uvname else me.uv_layers.active
    if uvl is None:
        return None, []
    mw = cv.matrix_world
    hx = face_lateral(s)
    out = []
    for lp in me.loops:
        p = mw @ me.vertices[lp.vertex_index].co
        uv = uvl.data[lp.index].uv
        out.append((lp.index, hx(p), p.z, uv[0], uv[1]))
    return uvl, out


def _fit_line(pairs, tol=0.002):
    """y = a·x + b, 튀는 값(새로 뽑은 면의 엉터리 UV)은 빼고 다시 맞춤."""
    import numpy as np
    if len(pairs) < 3:
        return None
    arr = np.array(pairs, dtype=float)
    keep = np.ones(len(arr), dtype=bool)
    a = b = 0.0
    for _ in range(4):
        x, y = arr[keep, 0], arr[keep, 1]
        if len(x) < 3 or np.ptp(x) < 1e-9:
            return None
        a, b = np.polyfit(x, y, 1)
        res = np.abs(arr[:, 0] * a + b - arr[:, 1])
        thr = max(tol, float(np.median(res[keep])) * 4)
        keep = res < thr
    return float(a), float(b), float(np.mean(keep))


def canvas_uv_params(s, st, cv):
    """보관된 투영값, 없으면 지금 메시에서 추정 (a, b, c, d)."""
    # 지금 메시에서 '대부분의 면'이 따르는 투영을 찾는다 (리그를 옮겼어도
    # 맞음). 늘린 면의 엉터리 UV는 튀는 값으로 빠진다. 안 되면 보관값
    _uvl, smp = _canvas_uv_samples(s, cv, st.uv_map)
    fu = _fit_line([(h, u) for _i, h, _z, u, _v in smp]) if smp else None
    fv = _fit_line([(z, v) for _i, _h, z, _u, v in smp]) if smp else None
    if fu and fv and fu[2] > 0.5 and fv[2] > 0.5:
        return (fu[0], fu[1], fv[0], fv[1])
    pr = st.get("uv_proj")
    if pr is not None and len(pr) == 4:
        return tuple(float(x) for x in pr)
    return None


def canvas_uv_remember(s, st):
    """지금 UV가 깨끗할 때(모든 면이 한 투영) 투영값을 저장."""
    if st.get("uv_proj") is not None:
        return
    cv = bpy.data.objects.get(st.target)
    if cv is None or cv.type != 'MESH':
        return
    _uvl, smp = _canvas_uv_samples(s, cv, st.uv_map)
    if not smp:
        return
    fu = _fit_line([(h, u) for _i, h, _z, u, _v in smp])
    fv = _fit_line([(z, v) for _i, _h, z, _u, v in smp])
    if fu and fv and fu[2] > 0.999 and fv[2] > 0.999:
        st["uv_proj"] = [fu[0], fu[1], fv[0], fv[1]]


class FSKR_OT_canvas_refit(bpy.types.Operator):
    bl_idname = "fskr.canvas_refit"
    bl_label = "메시 수정 후 정리"
    bl_description = ("캔버스 메시를 직접 고친 뒤(Extrude·정점 이동 등) 누르세요. "
                      "늘린 면에 같은 정면 UV를 이어 주고, 얼굴에 다시 붙입니다. "
                      "기존 파츠·마커 위치는 그대로")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        s = context.scene.fskr
        st = _find(s, self.uid)
        cv = bpy.data.objects.get(st.target) if st else None
        if cv is None or cv.type != 'MESH':
            return {'CANCELLED'}
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        pr = canvas_uv_params(s, st, cv)
        if pr is None:
            self.report({'ERROR'}, _tr("UV 투영을 알아내지 못했습니다"))
            return {'CANCELLED'}
        a, b, c, d = pr
        st["uv_proj"] = [a, b, c, d]
        uvl, smp = _canvas_uv_samples(s, cv, st.uv_map)
        n_fix = 0
        for li, h, z, u, v in smp:
            nu, nv = a * h + b, c * z + d
            if abs(nu - u) > 1e-5 or abs(nv - v) > 1e-5:
                n_fix += 1
            uvl.data[li].uv = (nu, nv)
        cv.data.update()
        # 정점 수가 바뀌었을 수 있으니 예전 '평평하게' 보관값은 버림
        if _REST_ATTR in cv.data.attributes:
            cv.data.attributes.remove(cv.data.attributes[_REST_ATTR])
        face = canvas_face(cv)
        err = canvas_follow_face(context, cv, face) if face else ""
        _wrap_on(cv)
        eye_build(s, st)
        if err:
            self.report({'WARNING'}, err)
        else:
            self.report({'INFO'}, _tr("UV %d곳을 이어 붙이고 얼굴에 다시 "
                                      "붙였습니다") % n_fix)
        return {'FINISHED'}


class FSKR_OT_canvas_reselect(bpy.types.Operator):
    bl_idname = "fskr.canvas_reselect"
    bl_label = "선택 영역 적용"
    bl_description = ("얼굴 메시 편집 모드에서 새로 고른 면으로 캔버스 메시만 "
                      "바꿉니다. 파츠·마커·프리셋·설정과 그림 위치는 그대로 "
                      "(같은 정면 UV를 이어서 씀)")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        ob = context.active_object
        return (context.mode == 'EDIT_MESH' and ob is not None
                and ob.type == 'MESH')

    def execute(self, context):
        import bmesh
        s = context.scene.fskr
        st = _find(s, self.uid)
        cv = bpy.data.objects.get(st.target) if st else None
        face = context.active_object
        if cv is None or cv.type != 'MESH':
            self.report({'ERROR'}, _tr("캔버스를 찾지 못했습니다"))
            return {'CANCELLED'}
        if face is cv:
            self.report({'ERROR'}, _tr("캔버스가 아니라 얼굴 메시(원본)를 "
                                       "편집 모드로 열고 면을 고르세요"))
            return {'CANCELLED'}
        bm = bmesh.from_edit_mesh(face.data)
        if not any(f.select for f in bm.faces):
            self.report({'ERROR'}, _tr("선택된 면이 없습니다"))
            return {'CANCELLED'}
        # 지금 캔버스의 정면 투영값 (그림 위치를 그대로 두기 위해)
        pr = canvas_uv_params(s, st, cv)
        if pr is None:
            self.report({'ERROR'}, _tr("지금 캔버스의 UV 투영을 알아내지 "
                                       "못했습니다"))
            return {'CANCELLED'}
        a, b, c, d = pr
        before = set(bpy.data.objects)
        bpy.ops.mesh.duplicate()
        bpy.ops.mesh.separate(type='SELECTED')
        bpy.ops.object.mode_set(mode='OBJECT')
        new = [o for o in bpy.data.objects if o not in before]
        if not new:
            self.report({'ERROR'}, _tr("선택 영역을 복사하지 못했습니다"))
            return {'CANCELLED'}
        tmp = new[0]
        for md in list(tmp.modifiers):
            if md.type == 'MIRROR':
                _apply_mirror(tmp, md)
        if tmp.data.shape_keys is not None:
            tmp.shape_key_clear()
        me = tmp.data
        me.materials.clear()
        # 얼굴 오브젝트 공간 → 캔버스 오브젝트 공간
        xf = cv.matrix_world.inverted() @ tmp.matrix_world
        me.transform(xf)
        uvl = me.uv_layers.get(st.uv_map or "FSKR_Canvas") or \
            me.uv_layers.new(name=st.uv_map or "FSKR_Canvas")
        mw = cv.matrix_world
        hx = face_lateral(s)
        for lp in me.loops:
            p = mw @ me.vertices[lp.vertex_index].co
            uvl.data[lp.index].uv = (a * hx(p) + b, c * p.z + d)
        me.uv_layers.active = uvl
        try:
            uvl.active_render = True
        except Exception:
            pass
        old = cv.data
        me.name = old.name
        cv.data = me
        bpy.data.objects.remove(tmp)
        if old.users == 0:
            bpy.data.meshes.remove(old)
        st["uv_proj"] = [a, b, c, d]
        context.view_layer.objects.active = cv
        for o in context.selected_objects:
            o.select_set(False)
        cv.select_set(True)
        _reselect_end(context, st, cv, select_canvas=False)
        err = canvas_follow_face(context, cv, canvas_face(cv) or face)
        _wrap_on(cv)
        eye_build(s, st)
        if err:
            self.report({'WARNING'}, err)
        else:
            self.report({'INFO'}, _tr("캔버스 영역을 바꿨습니다 (면 %d개)")
                        % len(me.polygons))
        return {'FINISHED'}


def _local_view(context, on):
    """가장 큰 3D 뷰를 로컬 뷰(/ 키, 고른 것만 보기)로 켜거나 끈다."""
    try:
        win = context.window
        areas = [a for a in win.screen.areas if a.type == 'VIEW_3D']
    except Exception:
        return
    if not areas:
        return
    area = max(areas, key=lambda a: a.width * a.height)
    sp = area.spaces.active
    if (sp.local_view is not None) == bool(on):
        return
    reg = next((r for r in area.regions if r.type == 'WINDOW'), None)
    try:
        with context.temp_override(window=win, area=area, region=reg):
            bpy.ops.view3d.localview(frame_selected=bool(on))
    except Exception as e:
        print("FSKR local view:", e)


def _reselect_end(context, st, cv, select_canvas=True):
    """영역 수정 모드 끝: 숨긴 캔버스·복사본 다시 보이기."""
    if st is not None and st.get("reselect_local"):
        _local_view(context, False)
        del st["reselect_local"]
    for ob in (cv, bpy.data.objects.get(_over_name(st))):
        if ob is not None:
            try:
                ob.hide_set(False)
            except Exception:
                pass
    if "reselect" in st.keys():
        del st["reselect"]
    if select_canvas and cv is not None:
        try:
            if context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            for o in context.selected_objects:
                o.select_set(False)
            cv.select_set(True)
            context.view_layer.objects.active = cv
        except Exception:
            pass


class FSKR_OT_canvas_reselect_start(bpy.types.Operator):
    bl_idname = "fskr.canvas_reselect_start"
    bl_label = "선택 영역 수정"
    bl_description = ("캔버스를 잠시 숨기고 얼굴 메시를 편집 모드로 엽니다. "
                      "지금 캔버스 영역이 미리 선택되어 있으니 면을 더하거나 "
                      "빼고 '적용'을 누르세요")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        from mathutils.bvhtree import BVHTree
        import bmesh
        s = context.scene.fskr
        st = _find(s, self.uid)
        cv = bpy.data.objects.get(st.target) if st else None
        face = canvas_face(cv) if cv is not None else None
        if cv is None or face is None:
            self.report({'ERROR'}, _tr("캔버스가 붙은 얼굴 메시를 찾지 "
                                       "못했습니다"))
            return {'CANCELLED'}
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        # 지금 캔버스와 겹치는 얼굴 면을 미리 선택 (쉬는 자세 기준)
        cme = cv.data
        cmw = cv.matrix_world
        verts = [cmw @ v.co for v in cme.vertices]
        polys = [tuple(p.vertices) for p in cme.polygons]
        bvh = BVHTree.FromPolygons(verts, polys) if polys else None
        fmw = face.matrix_world
        tol = max(1e-4, max(face.dimensions) * 0.004)
        st["reselect"] = 1
        for ob in (cv, bpy.data.objects.get(_over_name(st))):
            if ob is not None:
                try:
                    ob.hide_set(True)
                except Exception:
                    pass
        for o in context.selected_objects:
            o.select_set(False)
        try:
            face.hide_set(False)
        except Exception:
            pass
        face.select_set(True)
        context.view_layer.objects.active = face
        bpy.ops.object.mode_set(mode='EDIT')
        try:
            bpy.ops.mesh.select_mode(type='FACE')
        except Exception:
            pass
        bm = bmesh.from_edit_mesh(face.data)
        n = 0
        for f in bm.faces:
            hit = False
            if bvh is not None:
                c = fmw @ f.calc_center_median()
                r = bvh.find_nearest(c)
                hit = r[0] is not None and r[3] <= tol
            f.select_set(hit)
            n += hit
        bm.select_flush_mode()
        bmesh.update_edit_mesh(face.data)
        # 얼굴 메시만 보이게 (로컬 뷰, '/' 키와 같음)
        try:
            areas = [a for a in context.window.screen.areas
                     if a.type == 'VIEW_3D']
            big = max(areas, key=lambda a: a.width * a.height) \
                if areas else None
            if big is not None and big.spaces.active.local_view is None:
                _local_view(context, True)
                st["reselect_local"] = 1
        except Exception:
            pass
        try:
            face_view(context, face)
        except Exception:
            pass
        self.report({'INFO'}, _tr("지금 캔버스 영역(면 %d개)을 선택해 "
                                  "두었습니다. 면을 더하거나 빼고 '적용'을 "
                                  "누르세요") % n)
        return {'FINISHED'}


class FSKR_OT_canvas_reselect_cancel(bpy.types.Operator):
    bl_idname = "fskr.canvas_reselect_cancel"
    bl_label = "취소"
    bl_description = "영역 수정을 그만두고 캔버스를 다시 보이게 합니다"
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        s = context.scene.fskr
        st = _find(s, self.uid)
        cv = bpy.data.objects.get(st.target) if st else None
        _reselect_end(context, st, cv)
        return {'FINISHED'}


class FSKR_OT_canvas_follow(bpy.types.Operator):
    bl_idname = "fskr.canvas_follow"
    bl_label = "얼굴 움직임에 다시 붙이기"
    bl_description = ("캔버스가 얼굴 메시의 최종 모양(아마추어·셰이프 키)을 "
                      "그대로 따라가게 다시 붙입니다. 리그에 캔버스를 따로 "
                      "바인드해서 일그러질 때 누르세요 (캔버스의 아마추어 "
                      "모디파이어는 지워짐)")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        s = context.scene.fskr
        st = _find(s, self.uid)
        cv = bpy.data.objects.get(st.target) if st else None
        face = canvas_face(cv) if cv else None
        if cv is None or face is None:
            self.report({'ERROR'}, _tr("캔버스가 붙은 얼굴 메시를 찾지 "
                                       "못했습니다"))
            return {'CANCELLED'}
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        if canvas_unflatten(context, cv):
            self.report({'INFO'}, _tr("편 캔버스를 원래 모양으로 되돌렸습니다"))
            return {'FINISHED'}
        err = canvas_follow_face(context, cv, face)
        _wrap_on(cv)
        if err:
            self.report({'ERROR'}, err)
            return {'CANCELLED'}
        self.report({'INFO'}, _tr("얼굴(%s) 움직임을 따라가게 붙였습니다")
                    % face.name)
        return {'FINISHED'}


class FSKR_OT_face_canvas(bpy.types.Operator):
    bl_idname = "fskr.face_canvas"
    bl_label = "얼굴 캔버스 만들기"
    bl_description = ("편집 모드에서 고른 얼굴 면을 복사해 살짝 띄운 '얼굴 "
                      "캔버스'를 만듭니다. 정면 투영 UV, 얼굴과 같은 변형"
                      "(아마추어·셰이프 키)을 따라가며, 눈·입 파츠를 이 "
                      "메시 하나에 조립합니다")
    bl_options = {'REGISTER', 'UNDO'}

    offset: bpy.props.FloatProperty(
        name="띄우기", default=1.2, min=0.0, soft_max=5.0, precision=2,
        subtype='PERCENTAGE',
        description="얼굴 표면에서 띄우는 거리 (선택 영역 높이 대비 %). "
                    "깜빡이면(Z-fighting) 조금 올리세요")
    margin: bpy.props.FloatProperty(
        name="UV 여백", default=2.0, min=0.0, max=30.0, precision=1,
        subtype='PERCENTAGE',
        description="캔버스 가장자리 여백 (파츠가 테두리에 잘리지 않게)")

    @classmethod
    def poll(cls, context):
        return context.scene.fskr.rig is not None

    def _problem(self, context):
        """선택 영역 확인. 문제가 있으면 안내 문구 목록, 없으면 None."""
        ob = context.active_object
        if ob is None or ob.type != 'MESH':
            return [_tr("얼굴 메시를 먼저 선택하세요."),
                    _tr("1. 얼굴 메시 선택 → Tab(편집 모드)"),
                    _tr("2. 눈썹 위~턱까지 얼굴 앞면을 면 선택"),
                    _tr("3. 얼굴 캔버스 만들기")]
        if context.mode != 'EDIT_MESH':
            return [_tr("얼굴 영역이 지정되지 않았습니다."),
                    _tr("Tab으로 편집 모드에 들어가 캔버스로 쓸 얼굴 "
                        "앞면(눈썹 위~턱)을 면 선택한 뒤 다시 누르세요.")]
        try:
            ob.update_from_editmode()
        except Exception:
            pass
        if not any(p.select for p in ob.data.polygons):
            return [_tr("선택된 면이 없습니다."),
                    _tr("캔버스로 쓸 얼굴 앞면(눈썹 위~턱)을 면 선택한 뒤 "
                        "다시 누르세요. (점·선만 선택하면 면이 잡히지 "
                        "않습니다)")]
        return None

    def invoke(self, context, event):
        lines = self._problem(context)
        if lines:
            def draw(menu, _ctx):
                for i, ln in enumerate(lines):
                    menu.layout.label(text=ln,
                                      icon='ERROR' if i == 0 else 'BLANK1')
            context.window_manager.popup_menu(
                draw, title=_tr("얼굴 캔버스 만들기"), icon='ERROR')
            self.report({'WARNING'}, lines[0])
            return {'CANCELLED'}
        return self.execute(context)

    def execute(self, context):
        import bmesh
        lines = self._problem(context)
        if lines:
            self.report({'ERROR'}, " ".join(lines[:2]))
            return {'CANCELLED'}
        s = context.scene.fskr
        face = context.active_object
        bm = bmesh.from_edit_mesh(face.data)
        if not any(f.select for f in bm.faces):
            self.report({'ERROR'}, _tr("선택된 면이 없습니다."))
            return {'CANCELLED'}
        before = set(bpy.data.objects)
        bpy.ops.mesh.duplicate()
        bpy.ops.mesh.separate(type='SELECTED')
        bpy.ops.object.mode_set(mode='OBJECT')
        new = [o for o in bpy.data.objects if o not in before]
        if not new:
            self.report({'ERROR'}, _tr("캔버스를 만들지 못했습니다"))
            return {'CANCELLED'}
        cv = new[0]
        cv.name = "FaceCanvas_" + face.name
        cv.data.name = cv.name
        me = cv.data
        # 머티리얼/외곽선 등 캔버스에 필요 없는 것 정리
        me.materials.clear()
        for md in list(cv.modifiers):
            if md.type in ('SOLIDIFY', 'UV_WARP') or \
                    md.name.startswith(AT._MOD_PREFIX):
                cv.modifiers.remove(md)
        # 반쪽 얼굴 + Mirror 모디파이어: 실제 지오메트리로 펼쳐서 얼굴 전체를
        # 한 장의 캔버스로 (셰이프 키·좌우 버텍스 그룹도 반전)
        for md in list(cv.modifiers):
            if md.type == 'MIRROR':
                _apply_mirror(cv, md)
                cv.modifiers.remove(md)
        # 정면 투영 UV (얼굴 정면에서 본 가로 = u, 월드 Z = v, 정사각형)
        mw = cv.matrix_world
        hx = face_lateral(s)   # 정면에서 본 '오른쪽' 방향의 월드 축 함수
        pts = [Vector((hx(mw @ v.co), 0.0, (mw @ v.co).z))
               for v in me.vertices]
        x0 = min(p.x for p in pts)
        x1 = max(p.x for p in pts)
        z0 = min(p.z for p in pts)
        z1 = max(p.z for p in pts)
        w, h = (x1 - x0) or 1.0, (z1 - z0) or 1.0
        side = max(w, h) * (1.0 + 2.0 * self.margin / 100.0)
        cx, cz = (x0 + x1) / 2.0, (z0 + z1) / 2.0
        uvl = me.uv_layers.get("FSKR_Canvas") or me.uv_layers.new(
            name="FSKR_Canvas")
        for loop in me.loops:
            p = pts[loop.vertex_index]
            uvl.data[loop.index].uv = ((p.x - cx) / side + 0.5,
                                       (p.z - cz) / side + 0.5)
        me.uv_layers.active = uvl
        try:
            uvl.active_render = True
        except Exception:
            pass
        # 최종 얼굴 표면(아마추어·셰이프 키·서브디비전 적용 후)에 딱 붙인 뒤
        # 살짝 띄우기. 일부만 떼어낸 메시는 서브디비전으로 얼굴보다 안쪽으로
        # 말려 들어가므로 Shrinkwrap으로 표면을 다시 맞춘다
        sw = cv.modifiers.new("FSKR_Canvas_Wrap", 'SHRINKWRAP')
        sw.target = face
        sw.wrap_method = 'NEAREST_SURFACEPOINT'
        sw.wrap_mode = 'ABOVE_SURFACE'
        # h는 월드 크기이므로 캔버스(오브젝트) 배율로 나눠 로컬 값으로
        sc9 = max(1e-6, sum(cv.matrix_world.to_scale()) / 3.0)
        sw.offset = h * self.offset / 100.0 / sc9
        # 얼굴 변형(아마추어·셰이프 키)을 그대로 따라가게: Surface Deform.
        # 리깅을 나중에 해도 캔버스에 따로 웨이트·바인드가 필요 없다
        err9 = canvas_follow_face(context, cv, face)
        if err9:
            self.report({'WARNING'}, err9)
        for attr in ("visible_shadow",):
            try:
                setattr(cv, attr, False)
            except Exception:
                pass
        # 캔버스 = 파츠 레이어 스택
        used = {e.uid for e in s.eyes}
        i = 1
        while "E%d" % i in used:
            i += 1
        base9 = _tr("얼굴 캔버스")
        names9 = {e.name for e in s.eyes}
        nm9, k9 = base9, 2
        while nm9 in names9:
            nm9 = "%s %d" % (base9, k9)
            k9 += 1
        st = s.eyes.add()
        st.uid = "E%d" % i
        st["name"] = nm9          # 콜백 없이 (라벨은 아래에서 새로 만듦)
        st.target = cv.name
        st["uv_map"] = "FSKR_Canvas"
        st["lift"] = h * self.offset / 100.0
        st["uv_proj"] = [1.0 / side, 0.5 - cx / side, 1.0 / side,
                         0.5 - cz / side]
        st["range_x"] = 0.035   # 캔버스 = 얼굴 전체라 눈동자 이동은 작게
        st["range_y"] = 0.025
        try:  # 기초 태그 (눈·눈썹·입·감정표현) + 눈·입 마커
            from .face_ui import ensure_base_tags
            ensure_base_tags(st)
        except Exception as e:
            print("FSKR base tags:", e)
        _pad_build(context, s, st)
        eye_build(s, st)
        try:
            s.canvas_uid = st.uid
        except Exception:
            pass
        for o in context.selected_objects:
            o.select_set(False)
        cv.select_set(True)
        context.view_layer.objects.active = cv
        self.report({'INFO'}, _tr("얼굴 캔버스를 만들었습니다: ") + cv.name)
        return {'FINISHED'}


# ----- 감정표현 Plane: 얼굴 밖으로 나가는 연출용 평면 캔버스 -----
_FX_TRACK = "FSKR_Billboard"
_HEAD_NAMES = ("head.x", "head", "def-head", "mixamorig:head", "head_ref.x",
               "c_head.x", "j_bip_c_head", "bip001 head")


def fx_billboard_apply(st, context):
    ob = bpy.data.objects.get(st.target)
    if ob is None:
        return
    con = ob.constraints.get(_FX_TRACK)
    if con is None:
        con = ob.constraints.new('TRACK_TO')
        con.name = _FX_TRACK
        con.track_axis = 'TRACK_NEGATIVE_Y'
        con.up_axis = 'UP_Z'
    cam = context.scene.camera if context is not None else None
    if cam is not None:
        con.target = cam
    con.enabled = bool(st.billboard) and con.target is not None
    con.mute = not con.enabled


def _face_armature(face):
    for m in getattr(face, "modifiers", ()):
        if m.type == 'ARMATURE' and m.object is not None:
            return m.object
    p = face.parent
    while p is not None:
        if p.type == 'ARMATURE':
            return p
        p = p.parent
    return None


def _guess_head(arm):
    if arm is None or arm.type != 'ARMATURE':
        return ""
    low = {b.name.lower(): b.name for b in arm.data.bones}
    for n in _HEAD_NAMES:
        if n in low:
            return low[n]
    for ln, n in low.items():
        if "head" in ln and not ln.startswith(("c_", "fp_", "mch")):
            return n
    return ""


_FRONT = {'-Y': ((1, 0, 0), (0, -1, 0)), 'Y': ((-1, 0, 0), (0, 1, 0)),
          'X': ((0, 1, 0), (1, 0, 0)), '-X': ((0, -1, 0), (-1, 0, 0))}


class FSKR_OT_fx_canvas(bpy.types.Operator):
    bl_idname = "fskr.fx_canvas"
    bl_label = "감정표현 Plane 만들기"
    bl_description = ("얼굴 앞에 머리보다 넓은 평면 캔버스를 만들어 머리 본에 "
                      "붙입니다. 분노 마크처럼 얼굴 밖으로 나가는 감정표현용. "
                      "파츠·태그·프리셋은 다른 캔버스와 같이 씁니다")
    bl_options = {'REGISTER', 'UNDO'}

    arm: bpy.props.StringProperty(name="아마추어")
    bone: bpy.props.StringProperty(name="머리 본")
    scale: bpy.props.FloatProperty(
        name="크기 (얼굴 대비)", default=2.0, min=1.0, soft_max=4.0,
        description="얼굴 캔버스 크기의 몇 배로 만들지")
    ahead: bpy.props.FloatProperty(
        name="앞으로", default=0.15, min=0.0, soft_max=1.0,
        subtype='FACTOR',
        description="얼굴 앞쪽으로 띄우는 거리 (Plane 크기 대비). 앞머리보다 "
                    "앞에 오게")

    @classmethod
    def poll(cls, context):
        s = context.scene.fskr
        return s.rig is not None and any(
            bpy.data.objects.get(e.target) is not None and not e.get("fx")
            for e in s.eyes)

    def _src(self, s):
        st = _canvas_cur(s)
        if st is None or st.get("fx"):
            st = next((e for e in s.eyes if not e.get("fx")), None)
        return st

    def invoke(self, context, event):
        s = context.scene.fskr
        st = self._src(s)
        cv = bpy.data.objects.get(st.target) if st else None
        face = canvas_face(cv) if cv is not None else None
        arm = _face_armature(face) if face is not None else None
        arm = arm or s.rig
        self.arm = arm.name if arm is not None else ""
        self.bone = _guess_head(arm)
        return context.window_manager.invoke_props_dialog(self, width=360)

    def draw(self, context):
        col = self.layout.column()
        col.prop_search(self, "arm", bpy.data, "objects")
        arm = bpy.data.objects.get(self.arm)
        if arm is not None and arm.type == 'ARMATURE':
            col.prop_search(self, "bone", arm.data, "bones")
        col.prop(self, "scale")
        col.prop(self, "ahead")

    def execute(self, context):
        from mathutils import Matrix
        s = context.scene.fskr
        src = self._src(s)
        cv = bpy.data.objects.get(src.target) if src else None
        if cv is None or cv.type != 'MESH':
            self.report({'ERROR'}, _tr("먼저 ①에서 얼굴 캔버스를 만드세요"))
            return {'CANCELLED'}
        arm = bpy.data.objects.get(self.arm)
        if arm is None or arm.type != 'ARMATURE' or \
                self.bone not in arm.data.bones:
            self.report({'ERROR'}, _tr("머리 본을 고르세요"))
            return {'CANCELLED'}
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        lat, front = (Vector(v) for v in _FRONT.get(
            getattr(s, "face_axis", '-Y'), _FRONT['-Y']))
        up = Vector((0.0, 0.0, 1.0))
        dg = context.evaluated_depsgraph_get()
        ce = cv.evaluated_get(dg)
        me9 = ce.to_mesh()
        pts = [ce.matrix_world @ v.co for v in me9.vertices]
        ce.to_mesh_clear()
        if not pts:
            return {'CANCELLED'}
        hs = [p.dot(lat) for p in pts]
        zs = [p.z for p in pts]
        ds = [p.dot(front) for p in pts]
        w, h = max(hs) - min(hs), max(zs) - min(zs)
        side = max(w, h) * self.scale
        cx, cz = (max(hs) + min(hs)) / 2.0, (max(zs) + min(zs)) / 2.0
        center = lat * cx + front * (max(ds) + side * self.ahead) + up * cz
        a = side / 2.0
        me = bpy.data.meshes.new("FaceFX")
        me.from_pydata([(-a, 0, -a), (a, 0, -a), (a, 0, a), (-a, 0, a)], [],
                       [(0, 1, 2, 3)])
        uvl = me.uv_layers.new(name="FSKR_Canvas")
        for li, uv in zip(range(4), ((0, 0), (1, 0), (1, 1), (0, 1))):
            uvl.data[li].uv = uv
        me.update()
        ob = bpy.data.objects.new("FaceFX_" + src.target.replace(
            "FaceCanvas_", ""), me)
        coll = cv.users_collection[0] if cv.users_collection else \
            context.scene.collection
        coll.objects.link(ob)
        rot = Matrix((lat, -front, up)).transposed().to_4x4()
        mw = Matrix.Translation(center) @ rot
        ob.matrix_world = mw
        ob.parent = arm
        ob.parent_type = 'BONE'
        ob.parent_bone = self.bone
        context.view_layer.update()
        ob.matrix_world = mw
        try:
            ob.visible_shadow = False
        except Exception:
            pass
        # 캔버스 = 파츠 레이어 스택
        used = {e.uid for e in s.eyes}
        i = 1
        while "E%d" % i in used:
            i += 1
        names9 = {e.name for e in s.eyes}
        base9 = _tr("감정표현")
        nm9, k9 = base9, 2
        while nm9 in names9:
            nm9 = "%s %d" % (base9, k9)
            k9 += 1
        st = s.eyes.add()
        st.uid = "E%d" % i
        st["name"] = nm9
        st.target = ob.name
        st["uv_map"] = "FSKR_Canvas"
        st["fx"] = 1
        # 정면 투영값 (마커 찍기용): u = (가로 - 왼쪽) / 크기
        st["uv_proj"] = [1.0 / side, 0.5 - cx / side, 1.0 / side,
                         0.5 - cz / side]
        try:
            from .face_ui import new_tag, _new_uid
            mk = st.markers.add()
            mk.uid = _new_uid(st.markers, "M")
            mk.name = base9
            mk["uv"] = (0.5, 0.5)
            mk["placed"] = True
            g = new_tag(st, base9, mk.uid)
            g.size = 0.15
            g.expand = False
        except Exception as e:
            print("FSKR fx tags:", e)
        _pad_build(context, s, st)
        eye_build(s, st)
        fx_billboard_apply(st, context)
        try:
            s.canvas_uid = st.uid
        except Exception:
            pass
        for o in context.selected_objects:
            o.select_set(False)
        ob.select_set(True)
        context.view_layer.objects.active = ob
        self.report({'INFO'}, _tr("감정표현 Plane을 만들었습니다: ") + ob.name)
        return {'FINISHED'}


# ----- 머리 납작하게 (카메라 기준): 2D 그림처럼 보이게 시선 방향 두께를 줄임 -----
FLAT_GROUP = "FSKR_HeadFlatten"
FLAT_MOD = "FSKR_HeadFlatten"
FLAT_CENTER = "FSKR_HeadCenter"
FLAT_PROPS = (("Head_Flatten", 0.5, "카메라 시선 방향으로 머리를 누르는 정도"),
              ("Head_Flatten_Side", 0.0,
               "옆모습일수록 더 누르기 (0 = 각도와 상관없이 같게)"))


def _flat_group(cam, center):
    ng = bpy.data.node_groups.get(FLAT_GROUP)
    if ng is None:
        ng = bpy.data.node_groups.new(FLAT_GROUP, 'GeometryNodeTree')
        it = ng.interface
        it.new_socket("Geometry", in_out='INPUT',
                      socket_type='NodeSocketGeometry')
        mk = it.new_socket("Mask", in_out='INPUT',
                           socket_type='NodeSocketFloat')
        mk.default_value, mk.min_value, mk.max_value = 1.0, 0.0, 1.0
        it.new_socket("Geometry", in_out='OUTPUT',
                      socket_type='NodeSocketGeometry')
        try:
            ng.is_modifier = True
        except Exception:
            pass
        N, L = ng.nodes, ng.links

        def nd(t, x, y, name=None, **kw):
            n = N.new(t)
            n.location = (x, y)
            if name:
                n.name = n.label = name
            for k, v in kw.items():
                setattr(n, k, v)
            return n

        def vm(op, a, b=None, x=0, y=0):
            n = nd('ShaderNodeVectorMath', x, y, operation=op)
            L.new(a, n.inputs[0])
            if b is not None:
                L.new(b, n.inputs[1])
            return n

        def fm(op, a, b=None, x=0, y=0, bv=None):
            n = nd('ShaderNodeMath', x, y, operation=op)
            if isinstance(a, (int, float)):
                n.inputs[0].default_value = a
            else:
                L.new(a, n.inputs[0])
            if b is not None:
                L.new(b, n.inputs[1])
            elif bv is not None:
                n.inputs[1].default_value = bv
            return n.outputs[0]

        gi = nd('NodeGroupInput', -1600, 0)
        go = nd('NodeGroupOutput', 1400, 0)
        val = {}
        for i, (k, v) in enumerate((("Strength", 0.5), ("Side", 0.0),
                                    ("Radius", 0.15), ("Falloff", 0.15))):
            n = nd('ShaderNodeValue', -1600, -300 - i * 90, k)
            n.outputs[0].default_value = v
            val[k] = n.outputs[0]
        so = nd('GeometryNodeSelfObject', -1600, 300)
        oi = nd('GeometryNodeObjectInfo', -1400, 300, "Self",
                transform_space='ORIGINAL')
        L.new(so.outputs[0], oi.inputs['Object'])
        oc = nd('GeometryNodeObjectInfo', -1400, 600, "Camera",
                transform_space='ORIGINAL')
        oh = nd('GeometryNodeObjectInfo', -1400, 900, "Center",
                transform_space='ORIGINAL')
        pos = nd('GeometryNodeInputPosition', -1400, 0)
        tp = nd('FunctionNodeTransformPoint', -1200, 0)
        L.new(pos.outputs[0], tp.inputs['Vector'])
        L.new(oi.outputs['Transform'], tp.inputs['Transform'])
        pw = tp.outputs[0]
        c = oh.outputs['Location']
        # 카메라 앞 방향 (로컬 -Z), 얼굴 앞 방향 (기준점 로컬 -Y)
        rf = nd('FunctionNodeRotateVector', -1200, 600)
        rf.inputs['Vector'].default_value = (0.0, 0.0, -1.0)
        L.new(oc.outputs['Rotation'], rf.inputs['Rotation'])
        f = vm('NORMALIZE', rf.outputs[0], x=-1000, y=600).outputs[0]
        rh = nd('FunctionNodeRotateVector', -1200, 900)
        rh.inputs['Vector'].default_value = (0.0, -1.0, 0.0)
        L.new(oh.outputs['Rotation'], rh.inputs['Rotation'])
        fwd = vm('NORMALIZE', rh.outputs[0], x=-1000, y=900).outputs[0]
        # 옆모습 정도: 1 - |얼굴 앞 · 카메라로 가는 방향|
        tocam = vm('NORMALIZE', vm('SUBTRACT', oc.outputs['Location'], c,
                                   -1000, 750).outputs[0],
                   x=-850, y=750).outputs[0]
        dd = vm('DOT_PRODUCT', fwd, tocam, -700, 800).outputs['Value']
        side = fm('SUBTRACT', 1.0, fm('ABSOLUTE', dd, x=-550, y=800),
                  -400, 800)
        # 세기 = Strength × (1 - Side + Side × 옆모습)
        sk = fm('ADD', fm('SUBTRACT', 1.0, val["Side"], -550, -380),
                fm('MULTIPLY', val["Side"], side, -400, 600), -250, 400)
        # 머리 중심에서 멀어지면(목·몸) 약하게
        dist = vm('DISTANCE', pw, c, -1000, -150).outputs['Value']
        r2 = fm('ADD', val["Radius"], val["Falloff"], -1000, -400)
        mr = nd('ShaderNodeMapRange', -800, -150,
                interpolation_type='SMOOTHSTEP', clamp=True)
        L.new(dist, mr.inputs['Value'])
        L.new(val["Radius"], mr.inputs['From Min'])
        L.new(r2, mr.inputs['From Max'])
        mr.inputs['To Min'].default_value = 1.0
        mr.inputs['To Max'].default_value = 0.0
        k = fm('MULTIPLY', fm('MULTIPLY', val["Strength"], sk, -100, 300),
               fm('MULTIPLY', mr.outputs[0], gi.outputs['Mask'], -600, -250),
               50, 100)
        d = vm('SUBTRACT', pw, c, -1000, 150).outputs[0]
        fd = vm('DOT_PRODUCT', d, f, -800, 150).outputs['Value']
        amt = fm('MULTIPLY', fd, k, 200, 150)
        sc = nd('ShaderNodeVectorMath', 350, 150, operation='SCALE')
        L.new(f, sc.inputs[0])
        L.new(amt, sc.inputs['Scale'])
        nw = vm('SUBTRACT', pw, sc.outputs[0], 500, 50).outputs[0]
        inv = nd('FunctionNodeInvertMatrix', 500, 250)
        L.new(oi.outputs['Transform'], inv.inputs[0])
        tb = nd('FunctionNodeTransformPoint', 700, 50)
        L.new(nw, tb.inputs['Vector'])
        L.new(inv.outputs[0], tb.inputs['Transform'])
        sp = nd('GeometryNodeSetPosition', 1000, 0)
        L.new(gi.outputs[0], sp.inputs['Geometry'])
        L.new(tb.outputs[0], sp.inputs['Position'])
        L.new(sp.outputs[0], go.inputs[0])
    if cam is not None:
        ng.nodes["Camera"].inputs['Object'].default_value = cam
    if center is not None:
        ng.nodes["Center"].inputs['Object'].default_value = center
    return ng


def flat_value(name):
    ng = bpy.data.node_groups.get(FLAT_GROUP)
    n = ng.nodes.get(name) if ng is not None else None
    return n.outputs[0] if n is not None else None


def flat_objects():
    return [o for o in bpy.data.objects
            if o.type == 'MESH' and o.modifiers.get(FLAT_MOD) is not None]


def _flat_add_mod(ob, ng):
    md = ob.modifiers.get(FLAT_MOD)
    if md is None:
        md = ob.modifiers.new(FLAT_MOD, 'NODES')
    md.node_group = ng
    # 아마추어(포즈) 바로 다음: 움직인 뒤의 모양을 누름
    mods = list(ob.modifiers)
    last = max((i for i, m in enumerate(mods) if m.type == 'ARMATURE'),
               default=-1)
    want = last + 1 if last < mods.index(md) else last
    cur = mods.index(md)
    if cur != want:
        try:
            with bpy.context.temp_override(object=ob):
                bpy.ops.object.modifier_move_to_index(
                    modifier=md.name, index=min(want, len(mods) - 1))
        except Exception as e:
            print("FSKR flatten move:", e)
    return md


class FSKR_OT_head_flatten(bpy.types.Operator):
    bl_idname = "fskr.head_flatten"
    bl_label = "머리 납작하게 (카메라 기준)"
    bl_description = ("선택한 메시(얼굴·머리카락·모자 등)를 카메라 시선 방향으로 "
                      "눌러 2D 그림처럼 보이게 합니다. 캔버스 파츠도 같이 "
                      "눌립니다. 렌더 카메라 기준 연출")
    bl_options = {'REGISTER', 'UNDO'}

    arm: bpy.props.StringProperty(name="아마추어")
    bone: bpy.props.StringProperty(name="머리 본")

    @classmethod
    def poll(cls, context):
        return context.scene.fskr.rig is not None

    def _targets(self, context, s):
        canv = {e.target for e in s.eyes} | {
            "FaceCanvasOver_" + e.uid for e in s.eyes}
        obs = [o for o in context.selected_objects
               if o.type == 'MESH' and o.name not in canv]
        if not obs:
            for e in s.eyes:
                cv = bpy.data.objects.get(e.target)
                f = canvas_face(cv) if cv is not None else None
                if f is not None and f not in obs:
                    obs.append(f)
        return obs

    def invoke(self, context, event):
        s = context.scene.fskr
        obs = self._targets(context, s)
        arm = None
        for o in obs:
            arm = _face_armature(o)
            if arm is not None:
                break
        arm = arm or s.rig
        cen = bpy.data.objects.get(FLAT_CENTER)
        if cen is not None and cen.parent is not None:
            arm, self.bone = cen.parent, cen.parent_bone
        else:
            self.bone = _guess_head(arm)
        self.arm = arm.name if arm is not None else ""
        return context.window_manager.invoke_props_dialog(self, width=380)

    def draw(self, context):
        col = self.layout.column()
        obs = self._targets(context, context.scene.fskr)
        col.label(text=_tr("적용할 메시: ") + (", ".join(o.name for o in obs)
                                             or "-"), icon='MESH_DATA')
        g = col.column(align=True)
        g.scale_y = 0.8
        g.active = False
        g.label(text=_tr("얼굴·머리카락·모자 등 같이 눌릴 메시를 선택하고 "
                         "누르세요"))
        g.label(text=_tr("캔버스는 얼굴을 따라가므로 고르지 않아도 됩니다"))
        col.prop_search(self, "arm", bpy.data, "objects")
        arm = bpy.data.objects.get(self.arm)
        if arm is not None and arm.type == 'ARMATURE':
            col.prop_search(self, "bone", arm.data, "bones")

    def execute(self, context):
        s = context.scene.fskr
        rig = s.rig
        obs = self._targets(context, s)
        arm = bpy.data.objects.get(self.arm)
        if not obs:
            self.report({'ERROR'}, _tr("누를 메시를 선택하세요"))
            return {'CANCELLED'}
        if arm is None or arm.type != 'ARMATURE' or \
                self.bone not in arm.data.bones:
            self.report({'ERROR'}, _tr("머리 본을 고르세요"))
            return {'CANCELLED'}
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        b = arm.data.bones[self.bone]
        # 머리 중심 기준점 (머리 본 가운데, 얼굴 정면 방향 = 로컬 -Y)
        cen = bpy.data.objects.get(FLAT_CENTER)
        if cen is None:
            cen = bpy.data.objects.new(FLAT_CENTER, None)
            cen.empty_display_type = 'SPHERE'
            (obs[0].users_collection[0] if obs[0].users_collection
             else context.scene.collection).objects.link(cen)
        lat, front = (Vector(v) for v in _FRONT.get(
            getattr(s, "face_axis", '-Y'), _FRONT['-Y']))
        up = Vector((0.0, 0.0, 1.0))
        pb = arm.pose.bones[self.bone]
        mid = arm.matrix_world @ ((pb.head + pb.tail) / 2.0)
        rot = Matrix((lat, -front, up)).transposed().to_4x4()
        mw = Matrix.Translation(mid) @ rot
        cen.parent = arm
        cen.parent_type = 'BONE'
        cen.parent_bone = self.bone
        context.view_layer.update()
        cen.matrix_world = mw
        blen = (arm.matrix_world.to_3x3() @ (b.tail_local - b.head_local)
                ).length
        cen.empty_display_size = blen * 0.5
        new = bpy.data.node_groups.get(FLAT_GROUP) is None
        ng = _flat_group(context.scene.camera, cen)
        if new:
            ng.nodes["Radius"].outputs[0].default_value = blen * 0.55
            ng.nodes["Falloff"].outputs[0].default_value = blen * 0.45
        # 리그 프로퍼티 → 세기 (키 넣기 가능)
        for (pn, dv, desc), node in zip(FLAT_PROPS, ("Strength", "Side")):
            _ensure_float(rig, pn, dv, 0.0, 1.0)
            try:
                rig.id_properties_ui(pn).update(description=desc)
            except Exception:
                pass
            sock = ng.nodes[node].outputs[0]
            try:
                sock.driver_remove("default_value")
            except Exception:
                pass
            _drv_vars(sock, None, "v", [("v", rig, '["%s"]' % pn)])
        for o in obs:
            _flat_add_mod(o, ng)
        # 새 드라이버는 의존 관계가 잡힌 뒤 한 번 더 건드려야 살아남
        context.view_layer.update()
        if ng.animation_data is not None:
            for fc in ng.animation_data.drivers:
                fc.driver.expression = fc.driver.expression
        rig.update_tag()
        context.view_layer.update()
        if context.scene.camera is None:
            self.report({'WARNING'}, _tr("씬에 활성 카메라가 없습니다. 카메라를 "
                                         "정한 뒤 '카메라 다시 연결'을 누르세요"))
        else:
            self.report({'INFO'}, _tr("머리 납작하게: %d개 메시") % len(obs))
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_head_flatten_cam(bpy.types.Operator):
    bl_idname = "fskr.head_flatten_cam"
    bl_label = "카메라 다시 연결"
    bl_description = "지금 씬의 활성 카메라를 기준으로 누르게 합니다"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        if context.scene.camera is None:
            self.report({'WARNING'}, _tr("씬에 활성 카메라가 없습니다"))
            return {'CANCELLED'}
        _flat_group(context.scene.camera, None)
        return {'FINISHED'}


class FSKR_OT_head_flatten_remove(bpy.types.Operator):
    bl_idname = "fskr.head_flatten_remove"
    bl_label = "머리 납작하게 지우기"
    bl_description = "모든 메시에서 납작하게 모디파이어를 지웁니다"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    name: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, context):
        obs = flat_objects()
        if self.name:
            obs = [o for o in obs if o.name == self.name]
        for o in obs:
            o.modifiers.remove(o.modifiers[FLAT_MOD])
        if not flat_objects():
            cen = bpy.data.objects.get(FLAT_CENTER)
            if cen is not None:
                bpy.data.objects.remove(cen)
            ng = bpy.data.node_groups.get(FLAT_GROUP)
            if ng is not None:
                bpy.data.node_groups.remove(ng)
        _redraw_ui(context)
        return {'FINISHED'}


def _canvas_cur(s):
    uid = getattr(s, "canvas_uid", "")
    st = _find(s, uid) if uid else None
    return st or (s.eyes[0] if len(s.eyes) else None)


class FSKR_OT_eye_remove(bpy.types.Operator):
    bl_idname = "fskr.eye_remove"
    bl_label = "눈 삭제"
    bl_description = ("눈 머티리얼·시선 패드를 지우고 원래 머티리얼로 "
                      "되돌립니다 (키는 유지)")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        s = context.scene.fskr
        st = _find(s, self.uid)
        if st is None:
            return {'CANCELLED'}
        ob = bpy.data.objects.get(st.target)
        if ob is not None:
            _restore(ob, st)
        mat = bpy.data.materials.get(_MAT_PREFIX + st.uid)
        if mat is not None and mat.users == 0:
            bpy.data.materials.remove(mat)
        over_remove(st)
        prev = context.view_layer.objects.active
        _pad_remove(context, s.rig, st)
        for e in s.eyes:
            if e.follow == st.uid:
                e.follow = ""
        idx = next(i for i, e in enumerate(s.eyes) if e.uid == self.uid)
        s.eyes.remove(idx)
        for e in s.eyes:
            if e.built:
                eye_build(s, e)
        if prev is not None:
            try:
                context.view_layer.objects.active = prev
            except Exception:
                pass
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_eye_build(bpy.types.Operator):
    bl_idname = "fskr.eye_build"
    bl_label = "적용 (머티리얼 재구성)"
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        s = context.scene.fskr
        st = _find(s, self.uid)
        if st is None:
            return {'CANCELLED'}
        if not st.follow:
            _pad_build(context, s, st)
        err = eye_build(s, st)
        if err:
            self.report({'ERROR'}, err)
            return {'CANCELLED'}
        return {'FINISHED'}


class FSKR_OT_eye_layer_add(bpy.types.Operator):
    bl_idname = "fskr.eye_layer_add"
    bl_label = "파츠 추가"
    bl_description = "새 파츠 레이어를 맨 앞에 추가합니다"
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        s = context.scene.fskr
        st = _find(s, self.uid)
        if st is None:
            return {'CANCELLED'}
        prev = (st.layers[st.layer_index]
                if 0 <= st.layer_index < len(st.layers) else None)
        L = st.layers.add()
        L.lid = _new_lid(st)
        L["name"] = "%s %d" % (_tr("파츠"), len(st.layers))
        if prev is not None:  # 같은 시트를 쓰는 경우가 많아 그대로 이어받음
            L["image"] = prev.image
            L["cols"] = prev.cols
            L["rows"] = prev.rows
        part_set_include(st, L.lid)
        st.layers.move(len(st.layers) - 1, 0)   # 맨 앞(맨 위)
        st.layer_index = 0
        eye_build(s, st)
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_eye_folder_add(bpy.types.Operator):
    bl_idname = "fskr.eye_folder_add"
    bl_label = "새 폴더"
    bl_description = ("선택한 파츠 자리에 폴더를 만들고 그 파츠를 넣습니다. "
                      "같은 태그·같은 자리의 폴더끼리는 하나만 켜져서, 예를 들어 "
                      "'일반 눈'과 '폭소 눈' 폴더를 눈 하나로 전환할 수 있습니다")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, context):
        s = context.scene.fskr
        st = _find(s, self.uid)
        if st is None:
            return {'CANCELLED'}
        sel = st.layers[st.layer_index] if \
            0 <= st.layer_index < len(st.layers) else None
        sel_lid = sel.lid if sel is not None else ""
        par = sel.parent if sel is not None else ""
        tag = sel.tag if sel is not None else ""
        used = {L.name for L in st.layers}
        k = 1
        while "%s %d" % (_tr("폴더"), k) in used:
            k += 1
        F = st.layers.add()
        F.lid = _new_lid(st)
        F["name"] = "%s %d" % (_tr("폴더"), k)
        F["kind"] = 2               # FOLDER
        F["tag"] = tag
        F["parent"] = par
        flid = F.lid
        if sel_lid:   # 선택한 파츠 자리로 (그리는 순서 유지)
            si = next(i for i, L in enumerate(st.layers) if L.lid == sel_lid)
            st.layers.move(len(st.layers) - 1, si)
        rig = s.rig
        F = _layer(st, flid)
        if rig is not None:
            _ensure_anim_props(rig, st, F)
            for p9, v9 in zip(_anim_props(st, F), ANIM_DEFAULTS):
                rig[p9] = v9         # 폴더는 이동 0 · 크기 1 · 보임
        # 같은 자리의 다른 폴더가 이미 켜져 있으면 새 폴더는 꺼 둠
        Fo = _layer(st, flid)
        if any(G.show for G in folder_group(st, Fo)):
            _vis_raw(rig, Fo, False)
        if sel_lid:      # 선택한 파츠를 새 폴더 안으로
            c = _layer(st, sel_lid)
            if c is not None and getattr(c, "kind", 'PART') != 'FOLDER':
                set_parent(s, st, c, flid, build=False)
        tree_normalize(st)
        st.layer_index = next(i for i, L in enumerate(st.layers)
                              if L.lid == flid)
        eye_build(s, st)
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_eye_folder_on(bpy.types.Operator):
    bl_idname = "fskr.eye_folder_on"
    bl_label = "이 폴더로 전환"
    bl_description = ("이 폴더를 켜고 같은 태그·같은 자리의 다른 폴더는 끕니다 "
                      "('바꾸면 자동 키'가 켜져 있으면 키도 넣음)")
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    uid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    lid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, context):
        s = context.scene.fskr
        st = _find(s, self.uid)
        F = _layer(st, self.lid) if st else None
        if F is None:
            return {'CANCELLED'}
        F.show = True
        if st.autokey and s.rig is not None and not preset_editing(s):
            for L9 in [F] + folder_group(st, F):
                try:
                    key_layer(s, st, L9, only={_p_vis(*_anim_source(
                        s, st, L9))})
                except Exception:
                    pass
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_part_set(bpy.types.Operator):
    bl_idname = "fskr.part_set"
    bl_label = "파츠 폴더"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    action: bpy.props.EnumProperty(
        items=(('APPLY', "전환", ""), ('ADD', "새 폴더", ""),
               ('UPDATE', "덮어쓰기", ""), ('REMOVE', "삭제", ""),
               ('ALL', "전체 보기", ""), ('SHOWALL', "모두 보이기", "")),
        options={'HIDDEN', 'SKIP_SAVE'})
    index: bpy.props.IntProperty(default=-1, options={'HIDDEN', 'SKIP_SAVE'})

    @classmethod
    def description(cls, context, props):
        a = getattr(props, "action", 'APPLY')
        return {
            'APPLY': _tr("이 폴더의 파츠만 보이게 전환합니다 ('바꾸면 자동 "
                         "키'가 켜져 있으면 키도 넣음)"),
            'ADD': _tr("지금 보이는 파츠들로 새 폴더를 만듭니다"),
            'UPDATE': _tr("지금 폴더를 지금 보이는 파츠들로 덮어씁니다"),
            'REMOVE': _tr("지금 폴더를 지웁니다 (파츠는 그대로)"),
            'ALL': _tr("목록에 모든 파츠를 보여 줍니다 (보이기는 그대로)"),
            'SHOWALL': _tr("모든 파츠를 보이게 합니다"),
        }.get(a, "")

    def execute(self, context):
        s = context.scene.fskr
        from .face_ui import _canvas
        st = _canvas(s)
        if st is None:
            return {'CANCELLED'}
        a = self.action
        if a == 'APPLY':
            part_set_apply(s, st, self.index,
                           key=bool(st.autokey) and not preset_editing(s))
        elif a == 'ADD':
            part_set_store(s, st)          # 지금 폴더 작업 내용 저장
            used = {p.name for p in st.part_sets}
            k = 1
            while "%s %d" % (_tr("폴더"), k) in used:
                k += 1
            ps = st.part_sets.add()
            ps.name = "%s %d" % (_tr("폴더"), k)
            st.part_set_active = len(st.part_sets) - 1
            part_set_store(s, st)
        elif a == 'UPDATE':
            i = st.part_set_active
            if not (0 <= i < len(st.part_sets)):
                return {'CANCELLED'}
            part_set_store(s, st, i)
        elif a == 'REMOVE':
            i = st.part_set_active
            if not (0 <= i < len(st.part_sets)):
                return {'CANCELLED'}
            st.part_sets.remove(i)
            st.part_set_active = -1
        elif a == 'ALL':
            part_set_store(s, st)
            st.part_set_active = -1
        elif a == 'SHOWALL':
            for L in st.layers:
                _vis_raw(s.rig, L, True)
            st.part_set_active = -1
            try:
                s.rig.update_tag()
            except Exception:
                pass
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_MT_part_sets(bpy.types.Menu):
    bl_idname = "FSKR_MT_part_sets"
    bl_label = "파츠 폴더"

    def draw(self, context):
        lay = self.layout
        from .face_ui import _canvas
        st = _canvas(context.scene.fskr)
        if st is None:
            return
        act = st.part_set_active
        op = lay.operator("fskr.part_set", text=_tr("전체 보기 (폴더 없이)"),
                          icon='CHECKMARK' if act < 0 else 'BLANK1')
        op.action = 'ALL'
        if len(st.part_sets):
            lay.separator()
        for i, ps in enumerate(st.part_sets):
            op = lay.operator("fskr.part_set", text=ps.name or "-",
                              icon='CHECKMARK' if i == act
                              else 'FILE_FOLDER')
            op.action, op.index = 'APPLY', i
        lay.separator()
        lay.operator("fskr.part_set", text=_tr("새 폴더 (지금 보이는 파츠로)"),
                     icon='ADD').action = 'ADD'
        if 0 <= act < len(st.part_sets):
            lay.operator("fskr.part_set",
                         text=_tr("지금 보이는 파츠로 덮어쓰기"),
                         icon='FILE_REFRESH').action = 'UPDATE'
            lay.operator("fskr.part_set", text=_tr("이 폴더 삭제"),
                         icon='TRASH').action = 'REMOVE'
        lay.separator()
        lay.operator("fskr.part_set", text=_tr("모든 파츠 보이기"),
                     icon='HIDE_OFF').action = 'SHOWALL'


class FSKR_OT_eye_layer_remove(bpy.types.Operator):
    bl_idname = "fskr.eye_layer_remove"
    bl_label = "파츠 삭제"
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        s = context.scene.fskr
        st = _find(s, self.uid)
        if st is None or not len(st.layers):
            return {'CANCELLED'}
        i = max(0, min(len(st.layers) - 1, st.layer_index))
        lid = st.layers[i].lid
        gp = st.layers[i].parent
        for clid in [c.lid for c in st.layers if c.parent == lid]:
            c = _layer(st, clid)       # 순서가 바뀌면 참조가 달라지므로 다시
            if c is not None:
                set_parent(s, st, c, gp, build=False)
        i = next(k for k, x in enumerate(st.layers) if x.lid == lid)
        rig = s.rig
        if rig is not None:
            p = _prop_cell(st, st.layers[i])
            if p in rig.keys():
                del rig[p]
        st.layers.remove(i)
        for L in st.layers:
            if L.clip == lid:
                L["clip"] = ""
            if L.cell_link == lid:
                L["cell_link"] = ""
        st.layer_index = max(0, min(len(st.layers) - 1, i))
        eye_build(s, st)
        _redraw_ui(context)
        return {'FINISHED'}


def _dup_name(st, name):
    """블렌더처럼 '이름.001', '이름.002' … (이미 .###이면 그 앞을 기준)."""
    import re
    base = re.sub(r"\.\d{3,}$", "", name) or name
    used = {x.name for x in st.layers}
    n = 1
    while "%s.%03d" % (base, n) in used:
        n += 1
    return "%s.%03d" % (base, n)


def _copy_rig_prop(rig, src, dst):
    """리그 커스텀 프로퍼티 값·범위·키프레임 복사."""
    if src not in rig.keys():
        return
    v = rig[src]
    rig[dst] = v.to_list() if hasattr(v, "to_list") else v
    try:
        rig.id_properties_ui(dst).update(
            **rig.id_properties_ui(src).as_dict())
    except Exception:
        pass
    path_s, path_d = '["%s"]' % src, '["%s"]' % dst
    for fc in AT._fcurves_for(rig, path_s):
        kps = fc.keyframe_points
        if not len(kps):
            continue
        arr = hasattr(rig[dst], "__len__")
        try:
            rig.keyframe_insert(data_path=path_d,
                                index=fc.array_index if arr else -1,
                                frame=kps[0].co.x,
                                group=fc.group.name if fc.group else "")
        except Exception:
            continue
        nf = next((f for f in AT._fcurves_for(rig, path_d)
                   if f.array_index == fc.array_index), None)
        if nf is None:
            continue
        nk = nf.keyframe_points
        if len(nk) < len(kps):
            nk.add(len(kps) - len(nk))
        for a, b in zip(kps, nk):
            b.co = a.co
            b.interpolation = a.interpolation
            b.handle_left_type = a.handle_left_type
            b.handle_right_type = a.handle_right_type
            b.handle_left = a.handle_left
            b.handle_right = a.handle_right
            b.easing = a.easing
        nf.extrapolation = fc.extrapolation
        nf.update()


class FSKR_OT_eye_layer_duplicate(bpy.types.Operator):
    bl_idname = "fskr.eye_layer_duplicate"
    bl_label = "파츠 복제"
    bl_description = ("선택한 파츠를 그림·값·키프레임까지 똑같이 복제해 "
                      "바로 위에 놓습니다 (이름 뒤에 .001)")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        s = context.scene.fskr
        st = _find(s, self.uid)
        if st is None or not len(st.layers):
            return {'CANCELLED'}
        i = max(0, min(len(st.layers) - 1, st.layer_index))
        src = st.layers[i]
        name = _dup_name(st, src.name)
        N = st.layers.add()
        src = st.layers[i]          # add() 뒤 참조 다시 잡기
        keys = list(src.keys())
        lid = _new_lid(st)
        for k in keys:
            # pkey(리그 프로퍼티 이름)는 복사하지 않음: 같으면 원본의 값·키가
            # 복제본 이름으로 옮겨져 원본이 0-0으로 돌아가 버림
            if k in ("lid", "name", "pkey", "edit_on"):
                continue
            v = src[k]
            try:
                N[k] = v.to_list() if hasattr(v, "to_list") else \
                    (v.to_dict() if hasattr(v, "to_dict") else v)
            except Exception:
                pass
        N.lid = lid
        N["name"] = name
        rig = s.rig
        if rig is not None:
            props = [(_prop_cell(st, src), _prop_cell(st, N))]
            props += list(zip(_anim_props(st, src), _anim_props(st, N)))
            for a, b in props:
                _copy_rig_prop(rig, a, b)
        part_set_include(st, lid)      # 보고 있는 폴더에도 넣음
        st.layers.move(len(st.layers) - 1, i)
        st.layer_index = i
        tree_normalize(st)
        eye_build(s, st)
        _redraw_ui(context)
        self.report({'INFO'}, _tr("복제: ") + name)
        return {'FINISHED'}


def _uv_to_world(ob_eval, uvname, uv):
    """평가된 캔버스에서 UV 점 → 월드 좌표 (없으면 None)."""
    from mathutils import Vector
    from mathutils.geometry import barycentric_transform, \
        intersect_point_tri_2d
    me = ob_eval.data
    uvl = me.uv_layers.get(uvname) if uvname else me.uv_layers.active
    if uvl is None:
        return None
    me.calc_loop_triangles()
    p = Vector((uv[0], uv[1], 0.0))
    for tri in me.loop_triangles:
        a, b, c = (uvl.data[i].uv for i in tri.loops)
        A3, B3, C3 = (Vector((q[0], q[1], 0.0)) for q in (a, b, c))
        if intersect_point_tri_2d(p.to_2d(), A3.to_2d(), B3.to_2d(),
                                  C3.to_2d()):
            v = [me.vertices[i].co for i in tri.vertices]
            w = barycentric_transform(p, A3, B3, C3, v[0], v[1], v[2])
            return ob_eval.matrix_world @ w
    return None


def over_measure(context, s, st):
    """'머리카락 위로' 파츠 자리에서 보는 쪽으로 광선을 쏴 가리는 메시까지
    거리를 잰다. [(파츠 이름, 거리 또는 None, 가린 오브젝트 이름)]"""
    dg = context.evaluated_depsgraph_get()
    cv = bpy.data.objects.get(st.target)
    if cv is None:
        return [], None
    ce = cv.evaluated_get(dg)
    r3 = _main_view3d()
    if r3 is not None:
        vi = r3.view_matrix.inverted()
        view = vi.translation if r3.is_perspective else None
        vdir = vi.to_3x3() @ __import__("mathutils").Vector((0, 0, 1))
    elif context.scene.camera is not None:
        cam = context.scene.camera
        view, vdir = cam.matrix_world.translation, None
    else:
        return [], None
    skip = {cv.name, _over_name(st), _VIEW_EMPTY}
    try:
        lim = max(cv.dimensions) * 1.5
    except Exception:
        lim = 10.0
    # 캔버스가 붙어 있는 얼굴 메시(Shrinkwrap 대상)는 가림막이 아님
    for m in cv.modifiers:
        tg = getattr(m, "target", None)
        if m.type == 'SHRINKWRAP' and tg is not None:
            skip.add(tg.name)
    lst = _src_stack(s, st) if _mirror_all(s, st) else st
    rig = s.rig
    out = []
    for L in lst.layers:
        if not (L.over and layer_visible(lst, L)) or L.kind == 'MOUTH':
            continue
        ast, aL = _anim_source(s, lst, L)
        mu, mv = marker_uv(lst, L.tag)
        px = float(rig.get(_p_px(ast, aL), 0.0)) if rig else 0.0
        py = float(rig.get(_p_py(ast, aL), 0.0)) if rig else 0.0
        sx = float(rig.get(_p_sx(ast, aL), 0.2)) if rig else 0.2
        pts = []
        for du in (-0.35, 0.0, 0.35):
            u, v = mu + px + du * sx, mv + py
            pts.append((u, v))
            if L.sym:
                pts.append((1.0 - u, v))
        best, who = None, ""
        for uv in pts:
            P = _uv_to_world(ce, st.uv_map, uv)
            if P is None:
                continue
            d = (view - P).normalized() if view is not None else vdir
            o = P + d * 1e-4
            travelled = 0.0
            # 보는 쪽 사이의 가림막을 전부 지나야 하므로 '가장 먼' 것까지
            for _ in range(32):
                hit, loc, nrm, idx, hob, mtx = context.scene.ray_cast(
                    dg, o, d, distance=lim)
                if not hit:
                    break
                travelled += (loc - o).length
                o = loc + d * 1e-4
                if travelled > lim:
                    break
                if hob is not None and (hob.original.name in skip or
                                        hob.name in skip):
                    continue
                if best is None or travelled > best:
                    best, who = travelled, hob.original.name
        out.append((L.name, best, who))
    return out, ("VIEW" if r3 is not None else "CAMERA")


class FSKR_OT_over_measure(bpy.types.Operator):
    bl_idname = "fskr.over_measure"
    bl_label = "가림 거리 재서 맞추기"
    bl_description = ("'머리카락 위로' 파츠 자리에서 지금 보는 쪽으로 광선을 "
                      "쏴서 앞머리까지의 거리를 재고, 앞으로 당기는 거리를 "
                      "그보다 조금 크게 맞춥니다")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        s = context.scene.fskr
        st = _find(s, self.uid)
        if st is None:
            return {'CANCELLED'}
        # 예전 방식 복사본이면 여기서 새 방식으로 다시 만든다
        try:
            over_sync(s, st)
        except Exception as e:
            print("FSKR over:", e)
        view_track(force=True)
        context.view_layer.update()
        res, src = over_measure(context, s, st)
        if not res:
            self.report({'WARNING'}, _tr("'머리카락 위로' 파츠가 없거나 "
                                         "시점을 찾지 못했습니다"))
            return {'CANCELLED'}
        hits = [(n, d, w) for n, d, w in res if d is not None]
        if not hits:
            self.report({'WARNING'}, _tr("지금 시점에서는 파츠를 가리는 "
                                         "메시가 없습니다 (가려지는 각도에서 "
                                         "다시 눌러 보세요)"))
            return {'CANCELLED'}
        mx = max(d for _n, d, _w in hits)
        st.over_dist = mx * 1.2
        names = sorted({w for _n, _d, w in hits})
        msg = _tr("가리는 메시: %s, 최대 %.4g → 거리 %.4g") % (
            ", ".join(names), mx, st.over_dist)
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class FSKR_OT_eye_pivot_recenter(bpy.types.Operator):
    bl_idname = "fskr.eye_pivot_recenter"
    bl_label = "중심 다시 잡기"
    bl_description = ("지금 보이는 칸의 그림으로 파츠 중심을 다시 계산합니다 "
                      "(그림 위치는 그대로)")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})
    lid: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        s = context.scene.fskr
        st = _find(s, self.uid)
        L = _layer(st, self.lid) if st else None
        if L is None:
            return {'CANCELLED'}
        c = cell_center(s, st, L)
        if c is None:
            self.report({'WARNING'}, _tr("이 칸에 그림이 없습니다"))
            return {'CANCELLED'}
        _pivot_apply(s, st, L, 'PART', c)
        L["pivot"] = 1
        eye_build(s, st)
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_eye_layer_move(bpy.types.Operator):
    bl_idname = "fskr.eye_layer_move"
    bl_label = "순서 바꾸기"
    bl_description = "위에 있을수록 앞에 그려집니다"
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})
    direction: bpy.props.IntProperty(default=-1, options={'HIDDEN'})

    def execute(self, context):
        s = context.scene.fskr
        st = _find(s, self.uid)
        if st is None or not len(st.layers):
            return {'CANCELLED'}
        i = st.layer_index
        if not (0 <= i < len(st.layers)):
            return {'CANCELLED'}
        if not tree_move(st, st.layers[i], self.direction):
            return {'CANCELLED'}
        eye_build(s, st)
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_eye_cell_step(bpy.types.Operator):
    bl_idname = "fskr.eye_cell_step"
    bl_label = "이전/다음 칸"
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})
    lid: bpy.props.StringProperty(options={'HIDDEN'})
    delta: bpy.props.IntProperty(default=1, options={'HIDDEN'})

    def execute(self, context):
        s = context.scene.fskr
        st = _find(s, self.uid)
        L = _layer(st, self.lid) if st else None
        rig = s.rig
        if L is None or rig is None:
            return {'CANCELLED'}
        n = _ncells(L)
        cur = part_cell_now(rig, st, L)
        if L.edit_on and not preset_editing():
            part_edit_show(st, L, (cur + self.delta) % n)
        else:
            _set_cell(st, L, (cur + self.delta) % n)
        _redraw_ui(context)
        return {'FINISHED'}


def layer_tag(st, L):
    """파츠의 태그 (없으면 None)."""
    if not getattr(L, "tag", ""):
        return None
    return next((g for g in st.tags if g.uid == L.tag), None)


def interp_owner(st, L):
    """보간 값을 가진 데이터: 태그가 있으면 태그, 없으면 캔버스."""
    g = layer_tag(st, L)
    return g if g is not None else st


def interp_for(st, L):
    return getattr(interp_owner(st, L), "key_interp", 'BEZIER')


def key_layer(s, st, L, only=None, interp=None):
    """파츠 하나의 칸·배치·불투명도·크롭을 현재 프레임에 키 (개수 반환).

    only: 키를 넣을 리그 프로퍼티 이름 집합 (None = 전부).
    """
    rig = s.rig
    n = 0
    ast, aL = _anim_source(s, st, L)
    _ensure_anim_props(rig, ast, aL)
    if interp is None:
        interp = interp_for(st, L)
    f = bpy.context.scene.frame_current
    for p in _anim_props(ast, aL):
        if only is not None and p not in only:
            continue
        try:
            rig.keyframe_insert(data_path='["%s"]' % p, group="Face Parts")
            n += 1
        except Exception:
            continue
        # 고른 보간 방법을 방금 넣은 키와, 이 키로 들어오는 구간(바로 앞
        # 키)에 적용 — Blender의 보간은 '키 다음 구간'에 걸리기 때문
        ip9 = 'CONSTANT' if p.endswith(("_Visible", "_vis")) else interp
        for fc in AT._fcurves_for(rig, '["%s"]' % p):
            prev = None
            for kp in fc.keyframe_points:
                if kp.co[0] < f - 0.5 and (prev is None
                                            or kp.co[0] > prev.co[0]):
                    prev = kp
                if abs(kp.co[0] - f) < 0.5:
                    kp.interpolation = ip9
            if prev is not None and ip9 == interp:
                prev.interpolation = interp
            fc.update()
    ait = _layer_atlas(s, L)
    if ait is not None:   # 입: 칸 + 시퀀스 선택 + 말하기 (Constant)
        for p in AT._mouth_key_props(s, ait):
            if only is None or p in only:
                AT._key(rig, p)
                n += 1
    else:
        cst, cL = _cell_source(s, st, L)
        p = _prop_cell(cst, cL)
        if p in rig.keys() and (only is None or p in only):
            AT._key(rig, p)
            n += 1
    return n


def set_layer_interp(s, st, L, interp, selected_only=False):
    """이 파츠의 위치·크기·회전·불투명도·크롭 키를 같은 보간으로.

    selected_only: 도프시트/그래프 에디터에서 선택한 키프레임만.
    """
    rig = s.rig
    n = 0
    ast, aL = _anim_source(s, st, L)
    for p in _anim_props(ast, aL):
        if p.endswith(("_Visible", "_vis")):
            continue                 # 보이기는 항상 Constant
        for fc in AT._fcurves_for(rig, '["%s"]' % p):
            for kp in fc.keyframe_points:
                if selected_only and not kp.select_control_point:
                    continue
                kp.interpolation = interp
                n += 1
            fc.update()
    return n


class FSKR_OT_layer_interp_apply(bpy.types.Operator):
    bl_idname = "fskr.layer_interp_apply"
    bl_label = "보간 적용"
    bl_description = ("이미 넣은 키에 지금 고른 보간 방법을 적용합니다 "
                      "(선택한 키프레임만 / 이 파츠의 모든 키)")
    bl_options = {'REGISTER', 'UNDO'}

    scope: bpy.props.EnumProperty(
        name="범위",
        items=(('SELECTED', "선택한 키프레임만",
                "도프시트·그래프 에디터에서 선택해 둔 키프레임만 (이 파츠)",
                'RESTRICT_SELECT_OFF', 0),
               ('ALL', "이 파츠의 모든 키",
                "이 파츠의 위치·크기·회전·불투명도·크롭 키 전부",
                'KEYFRAME_HLT', 1)),
        options={'SKIP_SAVE'})
    uid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    lid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, context):
        s = context.scene.fskr
        st = L = None
        if self.uid and self.lid:
            st = _find(s, self.uid)
            L = _layer(st, self.lid) if st else None
        if L is None:
            try:
                from .face_ui import _canvas
                st = _canvas(s)
            except Exception:
                st = None
            if st is None or not (0 <= st.layer_index < len(st.layers)):
                return {'CANCELLED'}
            L = st.layers[st.layer_index]
        if s.rig is None:
            return {'CANCELLED'}
        ip = interp_for(st, L)
        n = set_layer_interp(s, st, L, ip,
                             selected_only=(self.scope == 'SELECTED'))
        if n == 0 and self.scope == 'SELECTED':
            self.report({'WARNING'}, _tr("선택한 키프레임이 없습니다 (도프시트·"
                                         "그래프 에디터에서 키를 선택하세요)"))
            return {'CANCELLED'}
        self.report({'INFO'}, "%s: %s %d" % (L.name, ip, n))
        _redraw_ui(context)
        return {'FINISHED'}


def mouth_layers(s, it):
    """입 스프라이트 시트 it에 연결된 입 레이어들 [(스택, 레이어)]."""
    out = []
    for st in s.eyes:
        for L in st.layers:
            ait = _layer_atlas(s, L)
            if ait is not None and ait.uid == it.uid:
                out.append((st, L))
    return out


class FSKR_MT_interp_apply(bpy.types.Menu):
    bl_idname = "FSKR_MT_interp_apply"
    bl_label = "보간 적용"

    def draw(self, context):
        lay = self.layout
        L = getattr(context, "fskr_layer", None)
        st = _owner(L) if L is not None else None
        for sc, lab, ic in (('SELECTED', "선택한 키프레임만",
                             'RESTRICT_SELECT_OFF'),
                            ('ALL', "이 파츠의 모든 키", 'KEYFRAME_HLT')):
            op = lay.operator("fskr.layer_interp_apply", text=_tr(lab),
                              icon=ic)
            op.scope = sc
            if st is not None:
                op.uid, op.lid = st.uid, L.lid


def interp_menu(layout, st, L):
    """보간 줄의 ↻ 메뉴 (어느 파츠인지 함께 넘김)."""
    sub = layout.row(align=True)
    sub.context_pointer_set("fskr_layer", L)
    sub.menu("FSKR_MT_interp_apply", text="", icon='FILE_REFRESH')


def layer_key_props(s, st, L):
    """key_layer가 다루는 리그 프로퍼티 이름 목록 (자동 키 감시용)."""
    rig = s.rig
    out = list(_anim_props(*_anim_source(s, st, L)))
    ait = _layer_atlas(s, L)
    if ait is not None:
        out += AT._mouth_key_props(s, ait)
    else:
        cst, cL = _cell_source(s, st, L)
        out.append(_prop_cell(cst, cL))
    return [p for p in out if p in rig.keys()]


class FSKR_OT_eye_key(bpy.types.Operator):
    bl_idname = "fskr.eye_key"
    bl_label = "키 삽입"
    bl_description = "현재 프레임에 키를 넣습니다"
    bl_options = {'REGISTER', 'UNDO'}

    # SKIP_SAVE: 직전에 쓴 what(예: ANIM)이 다음 버튼에 남지 않게
    uid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    lid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})  # 비우면 시선
    what: bpy.props.StringProperty(default="CELL",
                                   options={'HIDDEN', 'SKIP_SAVE'})

    @classmethod
    def description(cls, context, props):
        w = getattr(props, "what", "CELL")
        if w == 'INTERP':
            return _tr("이 파츠에 이미 넣은 키 전부(위치·크기·회전·불투명도·"
                       "크롭)를 지금 고른 보간 방법으로 바꿉니다")
        if w == 'ALL':
            return _tr("이 파츠의 지금 값 전부(칸·위치·크기·회전·불투명도·"
                       "크롭)를 현재 프레임에 키로 넣습니다")
        return _tr("현재 프레임에 키를 넣습니다")

    def execute(self, context):
        s = context.scene.fskr
        st = _find(s, self.uid)
        rig = s.rig
        if st is None or rig is None:
            return {'CANCELLED'}
        if self.lid and self.what == 'INTERP':
            L = _layer(st, self.lid)
            if L is None:
                return {'CANCELLED'}
            ip = interp_for(st, L)
            n = set_layer_interp(s, st, L, ip)
            self.report({'INFO'}, "%s: %d" % (ip, n))
            _redraw_ui(context)
            return {'FINISHED'}
        if self.lid and self.what == 'ALL':
            L = _layer(st, self.lid)
            if L is None:
                return {'CANCELLED'}
            n = key_layer(s, st, L)
            self.report({'INFO'}, _tr("키 삽입: ") + "%s (%d)" % (L.name, n))
            _redraw_ui(context)
            return {'FINISHED'}
        if self.lid and self.what == 'ANIM':
            L = _layer(st, self.lid)
            if L is None:
                return {'CANCELLED'}
            _ensure_anim_props(rig, st, L)
            for p in _anim_props(st, L):
                try:
                    rig.keyframe_insert(data_path='["%s"]' % p,
                                        group="Eye Parts")
                except Exception:
                    pass
        elif self.lid:
            L = _layer(st, self.lid)
            if L is None:
                return {'CANCELLED'}
            p = _prop_cell(st, L)
            _ensure_prop(rig, p, _ncells(L))
            AT._key(rig, p)
        else:
            pb = _gaze_bone(st)
            if pb is None:
                return {'CANCELLED'}
            pb.keyframe_insert("location", index=0, group="Eye Gaze")
            pb.keyframe_insert("location", index=1, group="Eye Gaze")
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_eye_place_reset(bpy.types.Operator):
    bl_idname = "fskr.eye_place_reset"
    bl_label = "배치 초기화"
    bl_description = "위치 0, 크기 1, 회전 0, 불투명도 1로 되돌립니다"
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})
    lid: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        s = context.scene.fskr
        st = _find(s, self.uid)
        L = _layer(st, self.lid) if st else None
        rig = s.rig
        if L is None or rig is None:
            return {'CANCELLED'}
        _ensure_anim_props(rig, st, L)
        for p, v in zip(_anim_props(st, L), ANIM_DEFAULTS):
            rig[p] = v
        rig.update_tag()
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_eye_fit_uv(bpy.types.Operator):
    bl_idname = "fskr.eye_fit_uv"
    bl_label = "데칼 UV를 0~1로 펴기"
    bl_description = ("눈 데칼의 UV를 0~1 정사각형 안에 꽉 차게 맞춥니다 "
                      "(가로세로 비율 유지, 가운데 정렬). 파츠 위치/크기의 "
                      "기준이 데칼 전체가 됩니다")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        s = context.scene.fskr
        st = _find(s, self.uid)
        ob = bpy.data.objects.get(st.target) if st else None
        if ob is None or ob.type != 'MESH':
            return {'CANCELLED'}
        me = ob.data
        uvl = (me.uv_layers.get(st.uv_map) if st.uv_map
               else me.uv_layers.active)
        if uvl is None:
            uvl = me.uv_layers.new(name="UVMap")
        prev_mode = ob.mode
        if prev_mode == 'EDIT':
            bpy.ops.object.mode_set(mode='OBJECT')
        # 버텍스 위치 기준으로 다시 펴기 (데칼 평면의 가장 넓은 두 축)
        import numpy as np
        co = np.array([v.co[:] for v in me.vertices]) if len(me.vertices) \
            else np.zeros((1, 3))
        ext = co.max(0) - co.min(0)
        ax = list(np.argsort(-ext)[:2])
        ax.sort()
        # X축이 포함되면 X를 가로로, 나머지를 세로로
        h_ax = 0 if 0 in ax else ax[0]
        v_ax = [a for a in ax if a != h_ax][0]
        lo = co.min(0)
        w, h = ext[h_ax] or 1.0, ext[v_ax] or 1.0
        side = max(w, h)
        ox = (side - w) / 2
        oy = (side - h) / 2
        for loop in me.loops:
            p = me.vertices[loop.vertex_index].co
            uvl.data[loop.index].uv = ((p[h_ax] - lo[h_ax] + ox) / side,
                                       (p[v_ax] - lo[v_ax] + oy) / side)
        me.update()
        if prev_mode == 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')
        self.report({'INFO'}, _tr("데칼 UV를 0~1로 폈습니다"))
        return {'FINISHED'}


class FSKR_OT_eye_hsv_reset(bpy.types.Operator):
    bl_idname = "fskr.eye_hsv_reset"
    bl_label = "색조/채도/명도 초기화"
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})
    lid: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        st = _find(context.scene.fskr, self.uid)
        L = _layer(st, self.lid) if st else None
        if L is None:
            return {'CANCELLED'}
        L.hue, L.sat, L.val = 0.0, 1.0, 1.0
        return {'FINISHED'}


class FSKR_OT_eye_color_match(bpy.types.Operator):
    bl_idname = "fskr.eye_color_match"
    bl_label = "색조/채도/명도 계산"
    bl_description = ("'원래 색'이 '바꿀 색'이 되도록 색조·채도·명도 값을 "
                      "계산해 넣습니다. 비슷한 색의 명암도 같이 따라 바뀜")
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})
    lid: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        st = _find(context.scene.fskr, self.uid)
        L = _layer(st, self.lid) if st else None
        if L is None:
            return {'CANCELLED'}
        dh, sm, vm, warn = hsv_match(L.cm_src, L.cm_dst)
        L.hue, L.sat, L.val = dh, sm, vm
        L.show_fx = True
        if warn:
            self.report({'WARNING'}, warn)
        else:
            self.report({'INFO'}, _tr("색조 %+.0f°, 채도 ×%.2f, 명도 ×%.2f")
                        % (dh * 360.0, sm, vm))
        return {'FINISHED'}


class FSKR_OT_eye_color_pick(bpy.types.Operator):
    bl_idname = "fskr.eye_color_pick"
    bl_label = "그림에서 찾기"
    bl_description = ("지금 칸 그림에서 가장 많이 쓰인 색을 '원래 색'으로 "
                      "넣습니다 (스포이트는 화면 색이라 조명·색 관리 때문에 "
                      "틀릴 수 있음)")
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})
    lid: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        import numpy as np
        s = context.scene.fskr
        st = _find(s, self.uid)
        L = _layer(st, self.lid) if st else None
        img = _layer_image(s, L) if L is not None else None
        if img is None:
            return {'CANCELLED'}
        w, h = img.size
        cols, rows = _layer_grid(s, L)
        idx = max(0, min(cols * rows - 1, int(_cell_now(s, st, L))))
        r, c = idx // cols, idx % cols
        a = np.empty(w * h * 4, dtype=np.float32)
        img.pixels.foreach_get(a)
        a = a.reshape(h, w, 4)
        cw, ch = w / cols, h / rows
        x0, x1 = int(round(c * cw)), int(round((c + 1) * cw))
        y0, y1 = int(round(h - (r + 1) * ch)), int(round(h - r * ch))
        sub = a[y0:y1, x0:x1].reshape(-1, 4)
        del a
        sub = sub[sub[:, 3] > 0.9][:, :3]
        if not len(sub):
            self.report({'WARNING'}, _tr("이 칸에 그림이 없습니다"))
            return {'CANCELLED'}
        q = np.clip(np.round(sub * 255.0), 0, 255).astype(np.int32)
        key = q[:, 0] * 65536 + q[:, 1] * 256 + q[:, 2]
        vals, cnt = np.unique(key, return_counts=True)
        k = int(vals[np.argmax(cnt)])
        rgb = ((k >> 16) & 255, (k >> 8) & 255, k & 255)
        L.cm_src = tuple(v / 255.0 for v in rgb)
        self.report({'INFO'}, _tr("원래 색: #%02X%02X%02X") % rgb)
        return {'FINISHED'}


class FSKR_OT_eye_gaze_reset(bpy.types.Operator):
    bl_idname = "fskr.eye_gaze_reset"
    bl_label = "시선 초기화"
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        st = _find(context.scene.fskr, self.uid)
        if st is None:
            return {'CANCELLED'}
        st.look_x = 0.0
        st.look_y = 0.0
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_cell_place_reset(bpy.types.Operator):
    bl_idname = "fskr.cell_place_reset"
    bl_label = "이 칸 배치 되돌리기"
    bl_description = ("지금 칸의 칸별 배치(위치·크기·회전·불투명도·크롭)를 "
                      "지워 전체 배치 값으로 되돌립니다 (일괄 조절로 체크한 "
                      "칸도 같이)")
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    uid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    lid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, context):
        s = context.scene.fskr
        st = _find(s, self.uid)
        L = _layer(st, self.lid) if st else None
        x = cell_table(s, st, L) if L else None
        if x is None:
            return {'CANCELLED'}
        for rc in [x.cur] + x.others():
            e = x.entry(*rc)
            if e is None:
                continue
            for f, (fld, d, _c) in AT._LX_ROLES.items():
                setattr(e, fld, d)
            e.llock = -1
        x.refresh()
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_gaze_pad(bpy.types.Operator):
    bl_idname = "fskr.gaze_pad"
    bl_label = "시선 컨트롤러"
    bl_description = "뷰포트에 시선 패드(눈동자 컨트롤러)를 만들거나 다시 만들거나 지웁니다"
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})
    action: bpy.props.EnumProperty(items=(('BUILD', "만들기", ""),
                                          ('REBUILD', "다시 만들기", ""),
                                          ('REMOVE', "지우기", "")),
                                   options={'HIDDEN'})

    def execute(self, context):
        s = context.scene.fskr
        st = _find(s, self.uid)
        if st is None or s.rig is None:
            self.report({'ERROR'}, _tr("리그를 먼저 지정하세요"))
            return {'CANCELLED'}
        prev = context.view_layer.objects.active
        if self.action in ('REBUILD', 'REMOVE'):
            _pad_remove(context, s.rig, st)
        if self.action in ('BUILD', 'REBUILD'):
            _pad_build(context, s, st)
        eye_build(s, st)
        if prev is not None:
            try:
                context.view_layer.objects.active = prev
            except Exception:
                pass
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_gaze_test(bpy.types.Operator):
    bl_idname = "fskr.gaze_test"
    bl_label = "시선 미리보기"
    bl_description = "패드를 끝까지 밀어 범위를 확인합니다 (키는 넣지 않음)"
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})
    x: bpy.props.FloatProperty(options={'HIDDEN'})
    y: bpy.props.FloatProperty(options={'HIDDEN'})

    def execute(self, context):
        st = _find(context.scene.fskr, self.uid)
        pb = _gaze_bone(st) if st else None
        if pb is None:
            return {'CANCELLED'}
        pb.location[0] = self.x * PAD
        pb.location[1] = self.y * PAD
        _redraw_ui(context)
        return {'FINISHED'}


# ------------------------------------------------------------------
# UI
# ------------------------------------------------------------------

class FSKR_UL_eye_layers(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index):
        r = layout.row(align=True)
        r.prop(item, "show", text="", emboss=False,
               icon='HIDE_OFF' if item.show else 'HIDE_ON')
        r.prop(item, "name", text="", emboss=False)
        if item.clip:
            m = _layer(data, item.clip)
            sub = r.row()
            sub.active = False
            sub.label(text=(m.name if m else "?"), icon='MOD_MASK')
        if item.look:
            r.label(text="", icon='ORIENTATION_VIEW')
        if not item.image:
            r.label(text="", icon='ERROR')


class FSKR_PT_eyes(bpy.types.Panel):
    bl_label = "얼굴 캔버스 (눈·입 파츠)"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Face Rig"

    @classmethod
    def poll(cls, context):
        return getattr(context.scene.fskr, "ui_mode", 'DRIVER') == 'SPRITE'

    def draw(self, context):
        s = context.scene.fskr
        layout = self.layout
        rig = s.rig
        if rig is None:
            layout.label(text=_tr("리그를 먼저 지정하세요"), icon='INFO')
            return
        cb = layout.column(align=True)
        cb.scale_y = 1.2
        cb.operator("fskr.face_canvas", icon='MOD_SHRINKWRAP')
        aob = context.active_object
        if context.mode != 'EDIT_MESH':
            cb.label(text=_tr("얼굴 메시 편집 모드에서 눈~입 면을 고르고 "
                              "누르세요"), icon='INFO')
        elif aob is not None and aob.type == 'MESH' and \
                aob.data.total_face_sel == 0:
            r = cb.row()
            r.alert = True
            r.label(text=_tr("선택된 면이 없습니다. 얼굴 앞면을 면 선택하세요"),
                    icon='ERROR')
        layout.operator("fskr.eye_add", text=_tr("기존 메시를 캔버스로"),
                        icon='ADD')
        if not len(s.eyes):
            return
        for st in s.eyes:
            self._draw_stack(context, layout, s, rig, st)

    def _draw_stack(self, context, layout, s, rig, st):
        box = layout.box()
        hr = box.row(align=True)
        hr.prop(st, "expand", text="", emboss=False,
                icon='TRIA_DOWN' if st.expand else 'TRIA_RIGHT')
        hr.prop(st, "name", text="")
        hr.prop(st, "show_settings", text="", icon='PREFERENCES',
                toggle=True)
        hr.operator("fskr.eye_remove", text="", icon='X').uid = st.uid
        if not st.expand:
            return
        if st.show_settings:
            sb = box.box().column()
            sb.label(text=_tr("대상 오브젝트") + ": " + st.target,
                     icon='MESH_DATA')
            ob = bpy.data.objects.get(st.target)
            if ob is not None and ob.type == 'MESH':
                sb.prop_search(st, "uv_map", ob.data, "uv_layers")
            sb.prop(st, "follow_pick")
            if st.follow:
                sb.prop(st, "mirror_all")
                sb.prop(st, "mirror")
            r9 = sb.row(align=True)
            r9.operator("fskr.eye_build", icon='FILE_REFRESH').uid = st.uid
            r9.operator("fskr.eye_fit_uv", icon='UV').uid = st.uid
        # 시선
        gb = box.box().column(align=True)
        src = _src_stack(s, st)
        if src is not st:
            gb.label(text=_tr("다른 눈 따라가기") + ": " + src.name,
                     icon='LINKED')
        else:
            r = gb.row(align=True)
            r.label(text=_tr("시선"), icon='ORIENTATION_VIEW')
            r.operator("fskr.eye_gaze_reset", text="",
                       icon='LOOP_BACK').uid = st.uid
            op = r.operator("fskr.eye_key", text="", icon='KEY_HLT')
            op.uid, op.lid = st.uid, ""
            if _gaze_bone(st) is not None:
                r = gb.row(align=True)
                r.prop(st, "look_x", slider=True)
                r.prop(st, "look_y", slider=True)
            else:
                gb.operator("fskr.eye_build", icon='FILE_REFRESH').uid = \
                    st.uid
        r = gb.row(align=True)
        r.prop(st, "range_x")
        r.prop(st, "range_y")
        if _mirror_all(s, st):
            box.label(text=_tr("파츠: ") + src.name + _tr(" 파츠 전체를 "
                                                         "좌우 반전해서 사용"),
                      icon='MOD_MIRROR')
            return
        # 레이어 목록
        lb = box.column()
        lb.label(text=_tr("위가 앞 (위에 있을수록 앞에 그려짐)"),
                 icon='SORTALPHA')
        row = lb.row()
        row.template_list("FSKR_UL_eye_layers", "eyl_" + st.uid, st,
                          "layers", st, "layer_index", rows=4)
        cc = row.column(align=True)
        cc.operator("fskr.eye_layer_add", text="", icon='ADD').uid = st.uid
        cc.operator("fskr.eye_layer_remove", text="",
                    icon='REMOVE').uid = st.uid
        cc.separator()
        op = cc.operator("fskr.eye_layer_move", text="", icon='TRIA_UP')
        op.uid, op.direction = st.uid, -1
        op = cc.operator("fskr.eye_layer_move", text="", icon='TRIA_DOWN')
        op.uid, op.direction = st.uid, 1
        if not len(st.layers):
            lb.label(text=_tr("파츠가 없습니다. + 로 흰자부터 추가하세요"),
                     icon='INFO')
            return
        i = max(0, min(len(st.layers) - 1, st.layer_index))
        L = st.layers[i]
        db = box.box().column()
        db.prop(L, "name")
        db.prop(L, "kind", expand=True)
        mouth = L.kind == 'MOUTH'
        if mouth:
            db.prop(L, "atlas_pick", icon='IMAGE_DATA')
            db.label(text=_tr("칸은 입 시트(시퀀스·립싱크·뷰포트 "
                              "컨트롤러)로 바뀝니다"), icon='INFO')
        else:
            ir = db.row(align=True)
            ir.prop_search(L, "image", bpy.data, "images")
            op = ir.operator("fskr.image_open", text="", icon='FILEBROWSER')
            op.kind, op.uid, op.lid = 'EYE', st.uid, L.lid
            r = db.row(align=True)
            r.prop(L, "cols")
            r.prop(L, "rows")
        db.prop(L, "clip_pick", text=_tr("클리핑 마스크"), icon='MOD_MASK')
        db.prop(L, "blend")
        # 배치: 위치 / 크기 / 회전 / 불투명도 (리그 프로퍼티, 키 가능)
        ast, aL = _anim_source(s, st, L)
        _p = _anim_props(ast, aL)
        if all(p in rig.keys() for p in _p):
            tb = db.box().column(align=True)
            r = tb.row(align=True)
            r.label(text=_tr("배치"), icon='OBJECT_ORIGIN')
            op = r.operator("fskr.eye_place_reset", text="",
                            icon='LOOP_BACK')
            op.uid, op.lid = ast.uid, aL.lid
            op = r.operator("fskr.eye_key", text="", icon='KEY_HLT')
            op.uid, op.lid, op.what = ast.uid, aL.lid, 'ANIM'
            r = tb.row(align=True)
            r.prop(rig, '["%s"]' % _p[1], text=_tr("위치 X"))
            r.prop(rig, '["%s"]' % _p[2], text=_tr("위치 Y"))
            r = tb.row(align=True)
            r.prop(rig, '["%s"]' % _p[3], text=_tr("가로"))
            r.prop(L, "size_y_lk", text=_tr("세로"))
            r.prop(L, "scale_lock", text="",
                   icon='LINKED' if L.scale_lock else 'UNLINKED')
            r = tb.row(align=True)
            r.prop(rig, '["%s"]' % _p[5], text=_tr("회전"))
            r.prop(rig, '["%s"]' % _p[0], text=_tr("불투명도"), slider=True)
        else:
            db.operator("fskr.eye_build", icon='FILE_REFRESH').uid = st.uid
        r = db.row(align=True)
        r.prop(L, "flip_x", toggle=True, icon='MOD_MIRROR')
        r.prop(L, "sym", toggle=True, icon='MOD_MIRROR')
        # 색조/채도/명도
        hb = db.column(align=True)
        hr = hb.row(align=True)
        hr.prop(L, "show_fx", emboss=False, text=_tr("색조/채도/명도"),
                icon='TRIA_DOWN' if L.show_fx else 'TRIA_RIGHT')
        op = hr.operator("fskr.eye_hsv_reset", text="", icon='LOOP_BACK')
        op.uid, op.lid = st.uid, L.lid
        if L.show_fx:
            hb.prop(L, "hue", slider=True)
            hb.prop(L, "sat", slider=True)
            hb.prop(L, "val", slider=True)
        r = db.row(align=True)
        r.prop(L, "look", toggle=True, icon='ORIENTATION_VIEW')
        sub = r.row(align=True)
        sub.active = L.look
        sub.prop(L, "look_mul")
        if mouth:
            return
        db.prop(L, "link_pick", icon='LINKED')
        # 칸 선택
        if not L.image:
            db.label(text=_tr("이미지를 고르세요"), icon='ERROR')
            return
        cst, cL = _cell_source(s, st, L)
        if cL is not L or cst is not st:
            db.label(text=_tr("칸 따라가기") + ": " + cst.name + " / "
                     + cL.name, icon='LINKED')
            return
        if _ncells(L) > 1:
            if not _thumbs_ready(st, L):
                _thumbs_request(st, L)
            r = db.row(align=True)
            op = r.operator("fskr.eye_cell_step", text="", icon='TRIA_LEFT')
            op.uid, op.lid, op.delta = st.uid, L.lid, -1
            r.prop(L, "pick", text="")
            op = r.operator("fskr.eye_cell_step", text="", icon='TRIA_RIGHT')
            op.uid, op.lid, op.delta = st.uid, L.lid, 1
            op = r.operator("fskr.eye_key", text="", icon='KEY_HLT')
            op.uid, op.lid = st.uid, L.lid
            db.template_icon_view(L, "pick", show_labels=True, scale=4.0,
                                  scale_popup=4.0)
        db.prop(st, "autokey", icon='REC')


def px_transformed(e):
    """칸에 이미 따로 바꿔 둔 배치 (설명 목록)."""
    if e is None:
        return []
    lx = []
    if abs(e.lpx) > 1e-4 or abs(e.lpy) > 1e-4:
        lx.append(_tr("위치"))
    if abs(e.lkx - 1.0) > 1e-4 or abs(e.lky - 1.0) > 1e-4:
        lx.append(_tr("크기"))
    if abs(e.lrot) > 1e-4:
        lx.append(_tr("회전"))
    if abs(e.lop - 1.0) > 1e-4:
        lx.append(_tr("불투명도"))
    if any(abs(getattr(e, f)) > 1e-4 for f in ("lct", "lcb", "lcl", "lcr")):
        lx.append(_tr("크롭"))
    return [_tr("칸별 배치") + ": " + "/".join(lx)] if lx else []


class FSKR_OT_part_cell_msel(bpy.types.Operator):
    bl_idname = "fskr.part_cell_msel"
    bl_label = "일괄 조절할 칸"
    bl_description = ("이 칸을 일괄 조절할 칸으로 체크합니다. 지금 칸의 배치를 "
                      "바꾸면 체크한 칸들도 같이 바뀝니다 (크기는 같은 비율, "
                      "위치·회전은 움직인 만큼)")
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    uid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    lid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    r: bpy.props.IntProperty(default=-1, options={'HIDDEN', 'SKIP_SAVE'})
    c: bpy.props.IntProperty(default=-1, options={'HIDDEN', 'SKIP_SAVE'})
    clear: bpy.props.BoolProperty(default=False,
                                  options={'HIDDEN', 'SKIP_SAVE'})

    def _x(self, context):
        s = context.scene.fskr
        st = _find(s, self.uid)
        L = _layer(st, self.lid) if st else None
        return cell_table(s, st, L) if L else None

    def invoke(self, context, event):
        x = self._x(context)
        if x is None:
            return {'CANCELLED'}
        if not self.clear and (self.r, self.c) not in AT.cells_msel(x.tab) \
                and (self.r, self.c) != tuple(x.cur):
            tr = px_transformed(x.entry(self.r, self.c))
            if tr:
                msg = "%d-%d: %s\n%s" % (
                    self.r, self.c, ", ".join(tr),
                    _tr("그래도 일괄 조절할까요? 크기는 같은 비율로, 위치는 "
                        "움직인 만큼 바뀝니다."))
                try:
                    return context.window_manager.invoke_confirm(
                        self, event,
                        title=_tr("이미 변형된 값이 있는 칸입니다"),
                        message=msg, confirm_text=_tr("일괄 조절하기"),
                        icon='WARNING')
                except TypeError:
                    return context.window_manager.invoke_confirm(self, event)
        return self.execute(context)

    def execute(self, context):
        x = self._x(context)
        if x is None:
            return {'CANCELLED'}
        sel = AT.cells_msel(x.tab)
        if self.clear:
            sel = set()
        else:
            rc = (self.r, self.c)
            if rc in sel:
                sel.discard(rc)
            else:
                sel.add(rc)
        AT.cells_msel_set(x.tab, sel)
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_part_cell_show(bpy.types.Operator):
    bl_idname = "fskr.part_cell_show"
    bl_label = "이 칸 보기"
    bl_description = ("이 칸을 지금 칸으로 만들어 뷰포트에 바로 보여 줍니다 "
                      "(자동 키가 켜져 있으면 키도 들어감). 배치는 이 칸 "
                      "기준으로 조절됩니다")
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    uid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    lid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    r: bpy.props.IntProperty(default=0, options={'HIDDEN', 'SKIP_SAVE'})
    c: bpy.props.IntProperty(default=0, options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, context):
        s = context.scene.fskr
        st = _find(s, self.uid)
        L = _layer(st, self.lid) if st else None
        if L is None:
            return {'CANCELLED'}
        cst, cL = _cell_source(s, st, L)
        v = self.r * max(1, int(cL.cols)) + self.c
        if cL.edit_on and not preset_editing():
            part_edit_show(cst, cL, v)
        else:
            _set_cell(cst, cL, v)
        _redraw_ui(context)
        return {'FINISHED'}


eye_classes = (
    FSKR_OT_cell_place_reset, FSKR_OT_layer_interp_apply,
    FSKR_OT_part_cell_msel, FSKR_OT_part_cell_show, FSKR_MT_interp_apply,
    FSKR_OT_eye_folder_add, FSKR_OT_eye_folder_on, FSKR_OT_part_set,
    FSKR_MT_part_sets,
    FSKR_OT_face_canvas, FSKR_OT_fx_canvas, FSKR_OT_head_flatten,
    FSKR_OT_head_flatten_cam, FSKR_OT_head_flatten_remove, FSKR_OT_eye_add, FSKR_OT_eye_remove, FSKR_OT_eye_build,
    FSKR_OT_eye_layer_add, FSKR_OT_eye_layer_remove,
    FSKR_OT_eye_layer_duplicate, FSKR_OT_eye_pivot_recenter,
    FSKR_OT_over_measure, FSKR_OT_canvas_follow, FSKR_OT_gaze_pad,
    FSKR_OT_gaze_test, FSKR_OT_canvas_refit, FSKR_OT_canvas_reselect,
    FSKR_OT_canvas_reselect_start, FSKR_OT_canvas_reselect_cancel,
    FSKR_OT_eye_layer_move, FSKR_OT_eye_cell_step, FSKR_OT_eye_key,
    FSKR_OT_eye_gaze_reset, FSKR_OT_eye_hsv_reset, FSKR_UL_eye_layers,
    FSKR_OT_eye_place_reset, FSKR_OT_eye_fit_uv,
    FSKR_OT_eye_color_match, FSKR_OT_eye_color_pick,
)
eye_pg_classes = (FSKR_EyeLayer, FSKR_FaceSheet, FSKR_FacePreset,
                  FSKR_FaceMarker, FSKR_FaceTag, FSKR_PartSet,
                  FSKR_EyeStack)
