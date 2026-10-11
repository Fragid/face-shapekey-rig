"""스프라이트 시트용 뷰포트 컨트롤러.

드라이버 방식의 패널(FP_root)에 스프라이트 시트 전용 컨트롤러를 붙인다.

* 칸 격자 패드: 시트 그림이 깔린 격자 위에서 핸들을 끌면 칸(행, 열)이 바뀜
* 말하기 슬라이더 (자유 배치): 기본 / 닫힘 / 반 / 열림 4단계

값의 원본은 지금처럼 리그의 커스텀 프로퍼티(fskr_at_X_r/_c/_t)다. 핸들은
입력 장치일 뿐이라, 립싱크 굽기·편집기·패널 피커는 그대로 동작한다.
핸들을 움직이면 핸들러가 프로퍼티에 값을 쓰고, 프레임이 바뀌거나 패널에서
값이 바뀌면 핸들을 그 칸으로 옮긴다. 핸들에 직접 찍힌 키(I 키, 자동 키)는
칸 키로 변환한 뒤 핸들 키는 지운다.
"""
import bpy
from .core import app_handler_add, draw_add, draw_remove
import json
from math import floor, radians
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
    _set_color,
    _text_toggle_driver,
    _to_object_mode,
    _tr,
)
from .atlas import (
    _autokey_on,
    _find,
    _get_val,
    _key,
    _prop_col,
    _prop_row,
    _prop_q,
    _prop_talk,
    _row_source,
)


_EN.update({
    "뷰포트 컨트롤러 만들기": "Create viewport controller",
    "뷰포트 컨트롤러 갱신": "Update viewport controller",
    "뷰포트 컨트롤러 삭제": "Remove viewport controller",
    "이 시트의 칸을 뷰포트에서 고르는 격자 패드(+ 말하기 슬라이더)를 드라이버 방식 패널에 만듭니다": "Adds a grid pad (+ talk slider) to the controller panel for picking this sheet's cells in the viewport",
    "이 시트의 뷰포트 컨트롤러를 지웁니다 (칸 키는 유지)": "Removes this sheet's viewport controller (cell keys are kept)",
    "칸 수/이미지가 바뀌었습니다. 컨트롤러를 갱신하세요": "Cells/image changed. Update the controller",
    "뷰포트 컨트롤러: ": "Viewport controller: ",
    "기본": "Base", "말하기": "Talk",
    "핸들 키 %d개를 칸 키로 변환": "Converted %d handle keys to cell keys",
})
_JA.update({
    "뷰포트 컨트롤러 만들기": "ビューポートコントローラー作成",
    "뷰포트 컨트롤러 갱신": "ビューポートコントローラー更新",
    "뷰포트 컨트롤러 삭제": "ビューポートコントローラー削除",
})
_ZH.update({
    "뷰포트 컨트롤러 만들기": "创建视口控制器",
    "뷰포트 컨트롤러 갱신": "更新视口控制器",
    "뷰포트 컨트롤러 삭제": "删除视口控制器",
})


_PAD_MAX = 0.24     # 격자 패드의 긴 변 길이 (패널 단위)
_TALK_N = 4         # 말하기 단계 수: 0 기본, 1 닫힘, 2 반, 3 열림
_GRID_COLOR = (0.30, 0.42, 0.55)   # 격자/레일: 차분하게
_SEL_COLOR = (1.00, 0.86, 0.10)    # 지금 고른 칸: 눈에 띄게
_TALK_COLOR = (0.55, 0.40, 0.28)
_SEL_WIRE = 2.5                    # 선택 칸 테두리 두께 (픽셀)


# ------------------------------------------------------------------
# 이름 / 메타데이터
# ------------------------------------------------------------------

def _names(it):
    b = "FP_spr_" + it.uid
    return {"h": b, "f": b + "_frame", "hs": b + "_sel",
            "img": "FPSPR_" + it.uid, "lbl": "FPLBL_spr_" + it.uid,
            "wg": "WGT_FP_spr_" + it.uid, "wt": "WGT_FP_sprt_" + it.uid}


def _own(name, base):
    """base 본/오브젝트 자신이거나 그 하위 이름인지 (A1 / A10 혼동 방지)."""
    return name == base or name.startswith(base + "_")


def _has_talk(it):
    return it.layout == 'FREE'


_LIST_STEP = 0.026  # 시퀀스 목록 줄 간격


def _seq_names(it):
    """시퀀스 목록 줄 이름. 0번 = 자동(표정 따라), i번 = i번째 시퀀스."""
    out = [_tr("자동 (표정 따라)")]
    for i, e in enumerate(it.flaps):
        out.append(e.name or ("%s %d" % (_tr("시퀀스"), i + 1)))
    return out


def _auto_src(it):
    """목록 0번 라벨의 번역 원본 (언어 전환 때 다시 씀)."""
    return [("자동 (표정 따라)", True)]


def _sliders(it):
    """격자 아래 입 컨트롤: 시퀀스 목록(어느 시퀀스로 말할지) + 말하기
    슬라이더 하나(기본/닫힘/반/열림). 목록 = 프로퍼티 q, 슬라이더 = t."""
    if not _has_talk(it) or not len(it.flaps):
        return []  # 시퀀스가 하나도 없으면 말하기 컨트롤 없음
    b = "FP_spr_" + it.uid
    names = _seq_names(it)
    return [{"kind": "list", "h": b + "_seq", "f": b + "_seq_frame",
             "s": b + "_seq_sel", "n": len(names), "names": names,
             "name": ""},
            {"kind": "talk", "h": b + "_talk", "f": b + "_talk_frame",
             "s": b + "_talk_sel", "n": _TALK_N, "name": _tr("말하기")}]


def _sig(it):
    return json.dumps([int(it.rows), int(it.cols), it.image, it.layout,
                       [(d["kind"], d["n"], d.get("names"))
                        for d in _sliders(it)]])


def vp_exists(rig, it):
    return rig is not None and _names(it)["h"] in rig.data.bones


def _meta(rig, it):
    fb = rig.pose.bones.get(_names(it)["f"]) if rig else None
    if fb is None:
        return None
    try:
        return json.loads(fb.get("fskr_spr", "") or "{}") or None
    except Exception:
        return None


def vp_stale(rig, it):
    m = _meta(rig, it)
    return m is not None and (m.get("sig") != _sig(it)
                              or int(m.get("fv", 0) or 0) < 4)


def _geom(it):
    """칸 크기 (cw, ch): 이미지의 칸 비율을 유지하고 긴 변 = _PAD_MAX."""
    cols, rows = max(1, int(it.cols)), max(1, int(it.rows))
    aspect = 1.0
    img = bpy.data.images.get(it.image) if it.image else None
    try:
        if img is not None and img.size[0] == 0:
            img.pixels[0]  # 아직 안 읽힌 이미지는 한 번 읽어서 크기 확보
    except Exception:
        pass
    try:
        if img is not None and img.size[0] > 0 and img.size[1] > 0:
            aspect = (img.size[0] / cols) / (img.size[1] / rows)
    except Exception:
        pass
    # cw / ch = aspect, max(cols*cw, rows*ch) = _PAD_MAX
    ch = _PAD_MAX / max(cols * aspect, rows)
    cw = ch * aspect
    return cols, rows, cw, ch


# ------------------------------------------------------------------
# 위젯 메시
# ------------------------------------------------------------------

def _widget_coll(context):
    from .core import _widget_coll as wc
    return wc(context)


def _mesh_obj(coll, name, verts, edges):
    """이름이 같은 위젯이 있으면 메시만 교체 (크기 변경 대응)."""
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, edges, [])
    ob = bpy.data.objects.get(name)
    if ob is None:
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
    else:
        old = ob.data
        ob.data = me
        if old is not None and old.users == 0:
            bpy.data.meshes.remove(old)
    return ob


def _grid_widget(coll, name, cols, rows, cw, ch):
    """원점 = 왼쪽 위 칸 중심. 오른쪽(+X)으로 열, 아래(-Y)로 행."""
    x0, x1 = -cw / 2, cols * cw - cw / 2
    y0, y1 = ch / 2, ch / 2 - rows * ch
    v, e = [], []

    def line(a, b):
        v.extend([a, b])
        e.append((len(v) - 2, len(v) - 1))
    for i in range(cols + 1):
        x = x0 + i * cw
        line((x, y0, 0.0), (x, y1, 0.0))
    for j in range(rows + 1):
        y = y0 - j * ch
        line((x0, y, 0.0), (x1, y, 0.0))
    return _mesh_obj(coll, name, v, e)


def _sel_widget(coll):
    """선택 칸 표시: 두 겹 사각형 (단위 크기, 칸 크기로 스케일)."""
    name = "WGT_FP_spr_sel3"
    ob = bpy.data.objects.get(name)
    if ob is not None:
        return ob
    v, e = [], []
    for s in (0.46,):
        b = len(v)
        v += [(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)]
        e += [(b, b + 1), (b + 1, b + 2), (b + 2, b + 3), (b + 3, b)]
    return _mesh_obj(coll, name, v, e)


def _none_widget(coll):
    """아무것도 그리지 않는 위젯 (위치만 제공하는 숨은 본용)."""
    name = "WGT_FP_spr_none"
    ob = bpy.data.objects.get(name)
    if ob is not None:
        return ob
    return _mesh_obj(coll, name, [], [])


def _hide_bone(rig, name):
    """본 숨기기: Blender 5는 포즈 본 쪽 숨김도 따로 켜야 한다."""
    b = rig.data.bones.get(name)
    if b is not None:
        b.hide = True
        b.hide_select = True
    pb = rig.pose.bones.get(name)
    if pb is not None and hasattr(pb, "hide"):
        try:
            pb.hide = True
        except Exception:
            pass


def _talk_widget(coll, name, step, n=_TALK_N):
    """세로 레일 + 단계 눈금. 원점 = 맨 아래 단계(끔/기본)."""
    top = step * (n - 1)
    w = 0.012
    v, e = [], []

    def line(a, b):
        v.extend([a, b])
        e.append((len(v) - 2, len(v) - 1))
    line((-w, -0.01, 0), (-w, top + 0.01, 0))
    line((w, -0.01, 0), (w, top + 0.01, 0))
    line((-w, -0.01, 0), (w, -0.01, 0))
    line((-w, top + 0.01, 0), (w, top + 0.01, 0))
    for i in range(n):
        y = i * step
        line((-w - 0.008, y, 0), (-w, y, 0))
        line((w, y, 0), (w + 0.008, y, 0))
    return _mesh_obj(coll, name, v, e)


def _list_widget(coll, name, w, ls, n):
    """세로 목록 틀. 원점 = 맨 윗줄 가운데, 아래(-Y)로 줄."""
    x0, x1, y0 = -w / 2, w / 2, ls / 2
    v, e = [], []

    def line(a, b):
        v.extend([a, b])
        e.append((len(v) - 2, len(v) - 1))
    for j in range(n + 1):
        line((x0, y0 - j * ls, 0.0), (x1, y0 - j * ls, 0.0))
    y1 = y0 - n * ls
    line((x0, y0, 0.0), (x0, y1, 0.0))
    line((x1, y0, 0.0), (x1, y1, 0.0))
    return _mesh_obj(coll, name, v, e)


# ------------------------------------------------------------------
# 드라이버 도우미
# ------------------------------------------------------------------

def _drv(owner, path, exprs, vars_, n=None):
    try:
        owner.driver_remove(path)
    except Exception:
        pass
    res = owner.driver_add(path)
    fcs = res if isinstance(res, list) else [res]
    for fc in fcs:
        d = fc.driver
        d.type = 'SCRIPTED'
        if isinstance(exprs, (list, tuple)):
            d.expression = exprs[fc.array_index]
        else:
            d.expression = exprs
        for vn, (idv, dp) in vars_.items():
            var = d.variables.new()
            var.name = vn
            var.type = 'SINGLE_PROP'
            t = var.targets[0]
            t.id = idv
            t.data_path = dp


def _bone_setup(rig, pb, shape, scale, tr=(0.0, 0.0, 0.0)):
    pb.custom_shape = shape
    pb.use_custom_shape_bone_size = False
    pb.custom_shape_scale_xyz = scale
    pb.custom_shape_translation = tr
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
    pb.scale = (1.0, 1.0, 1.0)
    pb.lock_location[2] = True
    pb.lock_rotation_w = True
    pb.lock_rotation = (True, True, True)
    pb.lock_scale = (True, True, True)


def _limit(pb, xr, yr):
    for c in list(pb.constraints):
        pb.constraints.remove(c)
    c = pb.constraints.new('LIMIT_LOCATION')
    c.owner_space = 'LOCAL'
    c.use_transform_limit = True
    for attr in ("use_min_x", "use_max_x", "use_min_y",
                 "use_max_y", "use_min_z", "use_max_z"):
        setattr(c, attr, True)
    c.min_x, c.max_x = xr
    c.min_y, c.max_y = yr
    c.min_z = c.max_z = 0.0


_FONT_PATHS = (
    "C:/Windows/Fonts/malgun.ttf",
    "C:/Windows/Fonts/gulim.ttc",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/Library/Fonts/AppleGothic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
)


def _cjk_font():
    """한글/일본어/중국어 라벨용 시스템 폰트 (Blender 기본 폰트엔 한글 없음)."""
    import os
    for f in bpy.data.fonts:
        if f.filepath and os.path.basename(f.filepath).lower() in {
                os.path.basename(p).lower() for p in _FONT_PATHS}:
            return f
    for p in _FONT_PATHS:
        if os.path.exists(p):
            try:
                return bpy.data.fonts.load(p, check_existing=True)
            except Exception:
                continue
    return None


_BLF = {}


def _text_w(cu, text):
    """글자 폭 (커브 로컬 단위). Blender 폰트 크기 = em 기준."""
    import os
    fp = ""
    try:
        if cu.font is not None and cu.font.filepath and \
                cu.font.filepath != "<builtin>":
            fp = bpy.path.abspath(cu.font.filepath)
    except Exception:
        fp = ""
    w = 0.0
    if fp and os.path.exists(fp):
        try:
            import blf
            fid = _BLF.get(fp)
            if fid is None:
                fid = _BLF[fp] = blf.load(fp)
            if fid is not None and fid >= 0:
                blf.size(fid, 100)
                w = blf.dimensions(fid, text)[0] / 100.0
        except Exception:
            w = 0.0
    if w <= 0.0:   # 폰트를 못 읽으면 대략: 한중일 1em, 그 밖 0.55em
        w = sum(1.0 if ord(ch) > 0x2E7F else (0.3 if ch == " " else 0.58)
                for ch in text)
    return w * float(cu.size)


def fit_label(ob, full, avail_w):
    """라벨을 찌그러지지 않게(가로·세로 같은 비율) 하고, 칸 폭
    avail_w(월드 길이)보다 길면 뒤를 '...'로 줄인다. 바꿨으면 True."""
    if ob is None or ob.type != 'FONT':
        return False
    changed = False
    mw = ob.matrix_world
    ax = Vector(mw.col[0][:3]).length
    ay = Vector(mw.col[1][:3]).length
    # 글자 크기는 틀을 늘이거나 줄여도 처음 그대로 (리그 크기 기준)
    k = 1.0
    try:
        if ob.parent is not None:
            k = Vector(ob.parent.matrix_world.col[0][:3]).length or 1.0
    except Exception:
        k = 1.0
    if ax > 1e-9 and abs(ax - k) > k * 1e-3:
        ob.scale.x = ob.scale.x * (k / ax)
        changed = True
    if ay > 1e-9 and abs(ay - k) > k * 1e-3:
        ob.scale.y = ob.scale.y * (k / ay)
        changed = True
    full = full or "-"
    body = full
    if avail_w > 0 and _text_w(ob.data, full) * k > avail_w:
        body = "..."
        for n in range(len(full) - 1, 0, -1):
            t = full[:n].rstrip() + "..."
            if _text_w(ob.data, t) * k <= avail_w:
                body = t
                break
    if ob.data.body != body:
        ob.data.body = body
        _lbl_font(ob.data)
        changed = True
    return changed


def _lbl_body(parts):
    return "".join(_tr(t) if tr else t for t, tr in parts)


def _lbl_font(cu):
    if any(ord(ch) > 127 for ch in cu.body):
        fnt = _cjk_font()
        if fnt is not None and cu.font != fnt:
            cu.font = fnt


def relabel_all():
    """언어가 바뀌면 컨트롤러 라벨 글자를 바로 바꾼다."""
    for ob in bpy.data.objects:
        if ob.type != 'FONT' or "fskr_lbl" not in ob.keys():
            continue
        try:
            parts = json.loads(ob["fskr_lbl"])
            body = _lbl_body(parts)
            if ob.data.body != body:
                ob.data.body = body
                _lbl_font(ob.data)
        except Exception:
            pass


def _label(context, rig, name, body, size, bone, pos_w, src=None):
    """라벨 생성. src = [(글자, 번역 여부)] 이면 언어 전환 때 다시 씀."""
    s = context.scene.fskr
    ob = bpy.data.objects.get(name)
    if ob is not None:
        bpy.data.objects.remove(ob)
    if src is not None:
        body = _lbl_body(src)
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body = body
    cu.size = size
    if any(ord(ch) > 127 for ch in body):
        fnt = _cjk_font()
        if fnt is not None:
            cu.font = fnt
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    mat = bpy.data.materials.new("FPLBL_mat")
    mat.use_nodes = False
    mat.diffuse_color = (0.9, 0.9, 0.9, 1.0)
    cu.materials.append(mat)
    ob = bpy.data.objects.new(name, cu)
    ob.color = (0.9, 0.9, 0.9, 1.0)
    context.scene.collection.objects.link(ob)
    ob.parent = rig
    ob.parent_type = 'BONE'
    ob.parent_bone = bone
    context.view_layer.update()
    ob.matrix_world = (rig.matrix_world @ Matrix.Translation(pos_w)
                       @ Matrix.Rotation(radians(90), 4, 'X'))
    ob.hide_viewport = not s.labels_visible
    ob.hide_select = True
    if src is not None:
        ob["fskr_lbl"] = json.dumps(src, ensure_ascii=False)
    _text_toggle_driver(context.scene, rig, ob)
    return ob


# ------------------------------------------------------------------
# 생성 / 삭제
# ------------------------------------------------------------------

def _remove_objects(it, rig):
    nm = _names(it)
    for ob in list(bpy.data.objects):
        n = ob.name
        if n == nm["img"] or _own(n, nm["lbl"]):
            bpy.data.objects.remove(ob)
    for ob in list(bpy.data.objects):
        if _own(ob.name, nm["wg"]) or _own(ob.name, nm["wt"]):
            me = ob.data
            bpy.data.objects.remove(ob)
            if me is not None and me.users == 0:
                bpy.data.meshes.remove(me)


def vp_remove(context, rig, it):
    """컨트롤러 본/위젯/그림/라벨 제거 (프로퍼티 값과 키는 유지)."""
    if rig is None:
        return
    base = _names(it)["h"]
    _remove_objects(it, rig)
    bones = [b.name for b in rig.data.bones if _own(b.name, base)]
    # 핸들에 남은 키/드라이버 정리
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
    _LAST.pop(it.uid, None)


_SL_GAP = 0.06     # 슬라이더 사이 간격
_SL_DROP = 0.025   # 격자 아랫변 → 슬라이더 윗끝


def _name_w(name, size=0.012):
    """라벨 글자 폭 대략값 (한글은 넓게)."""
    w = 0.0
    for ch in name or "":
        w += size * (0.95 if ord(ch) > 0x2E80 else 0.55)
    return w


def _list_w(names):
    return max(0.12, max([_name_w(n, 0.0125) for n in names] or [0]) + 0.03)


def _layout(it, cols, rows, cw, ch, step):
    """틀 본 원점(왼쪽 위 칸 중심) 기준 목록/슬라이더 위치와 전체 깊이.

    목록은 원점 = 맨 윗줄 가운데(아래로 줄), 슬라이더는 원점 = 맨 아래
    단계(위로 단계). 둘 다 윗변을 격자 아래 같은 높이에 맞춘다.
    """
    sls = _sliders(it)
    top_y = 0.0                              # 시트 격자 없이 목록·슬라이더만
    pos = []
    foot = 0.0
    x = 0.0
    for d in sls:
        if d["kind"] == "list":
            lw = _list_w(d["names"])
            d["w"] = lw
            y0 = top_y - _LIST_STEP / 2
            pos.append((x + lw / 2, y0))
            x += lw + 0.04
            foot = max(foot, -(y0 - _LIST_STEP * (d["n"] - 1)
                               - _LIST_STEP / 2 - 0.005))
        else:
            y0 = top_y - 0.012 - step * (d["n"] - 1)
            pos.append((x + 0.02, y0))
            x += 0.02 + 0.07
            foot = max(foot, -(y0 - 0.02))
    _LAYOUT_W[it.uid] = x
    return sls, pos, foot


_LAYOUT_W = {}


def _old_gap(rig, nm, old_foot):
    """격자 아래 빈 공간 중 줄일 양 (없으면 0)."""
    try:
        from .core import _frame_corners
        fb = rig.pose.bones[nm["f"]]
        low = fb.matrix.translation.z - old_foot
        below = []
        for pb in rig.pose.bones:
            n = pb.name
            if not (n == "FP_root" or n == "FP_toggle_frame"
                    or (n.startswith("FP_ctl") and n.endswith("_frame"))):
                continue
            zs = [c.z for c in _frame_corners(pb)]
            if max(zs) < low:
                below.append(max(zs))
        if not below:
            return 0.0
        gap = low - max(below)
        return gap - 0.05 if gap > 0.08 else 0.0
    except Exception:
        return 0.0


def vp_build(context, s, it):
    """컨트롤러 생성/갱신. 오류 문자열 반환 (성공이면 "")."""
    rig = s.rig
    if rig is None or rig.type != 'ARMATURE':
        return _tr("리그를 먼저 지정하세요")
    nm = _names(it)
    cols, rows, cw, ch = _geom(it)
    W, H = cols * cw, rows * ch
    step = 0.03
    sls, spos, foot = _layout(it, cols, rows, cw, ch, step)
    if not sls:
        # 시퀀스가 없으면 뷰포트로 다룰 게 없음 (시트 격자는 쓰지 않음)
        if vp_exists(rig, it):
            vp_remove(context, rig, it)
        return ""

    _to_object_mode(context, rig)
    _ensure_root(context, s, rig)

    # 기존 컨트롤러가 있으면 그 자리(레스트 + 배치 이동)를 유지
    keep = None
    if nm["f"] in rig.data.bones:
        fb0 = rig.pose.bones[nm["f"]]
        old = _meta(rig, it) or {}
        old_foot = float(old.get("foot", H - ch / 2))
        keep = (rig.data.bones[nm["f"]].head_local.copy(),
                fb0.location.copy(), fb0.scale.copy(), old_foot,
                bool(old.get("fv")),
                0.0 if old.get("fv") else _old_gap(rig, nm, old_foot))
    from .layer_vp import _cur_col
    cols_keep = (_GRID_COLOR, _SEL_COLOR)
    if nm["f"] in rig.pose.bones:
        hb0 = rig.pose.bones.get(nm["h"])
        cols_keep = (_cur_col(rig.pose.bones[nm["f"]], _GRID_COLOR),
                     _cur_col(hb0, _SEL_COLOR) if hb0 else _SEL_COLOR)
    vp_remove(context, rig, it)
    _to_object_mode(context, rig)

    if keep is not None:
        origin = keep[0].copy()
        # 아래쪽 길이가 바뀐 만큼 위아래로 옮겨 바닥을 제자리에 유지
        # (슬라이더가 생기면 위로, 없어지면 아래로 내려와 빈 공간이 안 남음)
        origin.z += foot - keep[3]
        if not keep[4]:
            # 1.0.79 이전에 만든 컨트롤러: 슬라이더가 빠지며 남은 빈 공간을
            # 한 번만 정리 (아래 패널 요소 바로 위까지 내림)
            origin.z -= keep[5]
    else:
        # 패널 맨 위에 배치: 라벨부터 맨 아래 슬라이더 이름까지 확보
        top = _next_position(rig, 0.06 + foot)
        rootb = rig.data.bones["FP_root"]
        origin = Vector((rootb.head_local.x - W / 2 + cw / 2, top.y,
                         top.z - 0.035))

    bpy.ops.object.mode_set(mode='EDIT')
    eb = rig.data.edit_bones

    def new(n, head, parent):
        b = eb.new(n)
        b.head = head
        b.tail = head + Vector((0, 0, 0.02))
        b.roll = 0.0
        b.use_deform = False
        b.parent = eb[parent]
        return b
    new(nm["f"], origin, "FP_root")
    new(nm["hs"], origin, nm["f"])     # 선택 칸 표시 (핸들을 칸 단위로 따라감)
    new(nm["h"], origin, nm["f"])
    for d, (sx, sy) in zip(sls, spos):
        o = origin + Vector((sx, 0.0, sy))
        new(d["f"], o, nm["f"])
        new(d["s"], o, d["f"])
        new(d["h"], o, d["f"])
    bpy.ops.object.mode_set(mode='OBJECT')

    coll = _widget_coll(context)
    # 틀 = 목록·슬라이더를 감싸는 네모 (시트 격자 그림은 보여 주지 않음)
    xw = _LAYOUT_W.get(it.uid, 0.2)
    v9 = [(-0.012, 0.012, 0.0), (xw, 0.012, 0.0), (xw, -foot, 0.0),
          (-0.012, -foot, 0.0)]
    w_grid = _mesh_obj(coll, nm["wg"], v9,
                       [(0, 1), (1, 2), (2, 3), (3, 0)])
    w_sel = _sel_widget(coll)
    w_none = _none_widget(coll)

    pbs = rig.pose.bones
    fb, hb, hs = pbs[nm["f"]], pbs[nm["h"]], pbs[nm["hs"]]
    _bone_setup(rig, fb, w_grid, (1.0, 1.0, 1.0))
    # 핸들 모양은 칸 단위로 끊어 움직이는 표시 본(_sel) 위치에 그려진다
    # → 끄는 동안 핸들이 칸에서 칸으로 딱딱 넘어감 (Custom Shape Transform)
    _bone_setup(rig, hs, w_none, (1.0, 1.0, 1.0))
    _bone_setup(rig, hb, w_sel, (cw, ch, 1.0))
    if hasattr(hb, "custom_shape_wire_width"):
        hb.custom_shape_wire_width = _SEL_WIRE
    hb.custom_shape_transform = hs
    hb.location = (0.0, 0.0, 0.0)
    _limit(hb, (0.0, (cols - 1) * cw), (-(rows - 1) * ch, 0.0))
    from .layer_vp import set_vcol
    sub_f = [d["f"] for d in sls]
    sub_h = [nm["hs"]] + [d["h"] for d in sls] + [d["s"] for d in sls]
    set_vcol(fb, cols_keep[0], sub_f)
    set_vcol(hb, cols_keep[1], sub_h)
    if keep is not None:
        fb.location = keep[1]   # 시트 격자는 크기 고정 (scale 유지 안 함)
    fb["fskr_fixed"] = 1
    meta = {"cols": cols, "rows": rows, "cw": cw, "ch": ch,
            "step": step, "sig": _sig(it), "uid": it.uid, "foot": foot,
            "fv": 4,
            "xr": max([x + 0.06 for d, (x, _y) in zip(sls, spos)
                       if d["kind"] == "talk"] or [0.0]),
            "ls": _LIST_STEP,
            "sl": [{"h": d["h"], "kind": d["kind"], "n": d["n"]}
                   for d in sls]}
    fb["fskr_spr"] = json.dumps(meta)
    fb["fskr_spr_top"] = 0.05

    tgl = "FP_toggle" in rig.data.bones
    tv = {"t": (rig, 'pose.bones["FP_toggle"].location[0]')}
    TH = TGL / 2
    # 선택 칸 표시: 핸들 위치를 칸 단위로 끊어서 따라감 (끄는 중에도)
    hx = 'pose.bones["%s"].location' % nm["h"]
    _drv(rig, 'pose.bones["%s"].location' % nm["hs"],
         ["min(max(floor(x/%r+0.5),0),%d)*%r" % (cw, cols - 1, cw),
          "-min(max(floor(-y/%r+0.5),0),%d)*%r" % (ch, rows - 1, ch),
          "0.0"],
         {"x": (rig, hx + "[0]"), "y": (rig, hx + "[1]")})
    if tgl:
        _drv(rig, 'pose.bones["%s"].custom_shape_scale_xyz' % nm["f"],
             ["1.0*(t<%s)" % TH] * 3, tv)
        for n9 in (nm["h"], nm["hs"]):
            _drv(rig, 'pose.bones["%s"].scale' % n9, "t<%s" % TH, tv)

    # 격자 아래: 시퀀스 목록 + 말하기 슬라이더
    for d in sls:
        tf, th, ts = pbs[d["f"]], pbs[d["h"]], pbs[d["s"]]
        n = d["n"]
        _bone_setup(rig, ts, w_none, (1.0, 1.0, 1.0))
        th.custom_shape_transform = ts
        th.location = (0.0, 0.0, 0.0)
        tp = 'pose.bones["%s"].location[1]' % d["h"]
        if d["kind"] == "list":
            ls = _LIST_STEP
            w_list = _list_widget(coll, "%s_l%d_%d" % (nm["wt"], n,
                                                       int(d["w"] * 1000)),
                                  d["w"], ls, n)
            _bone_setup(rig, tf, w_list, (1.0, 1.0, 1.0))
            _bone_setup(rig, th, w_sel, (d["w"] / 0.92 * 0.96, ls, 1.0))
            _limit(th, (0.0, 0.0), (-ls * (n - 1), 0.0))
            _drv(rig, 'pose.bones["%s"].location' % d["s"],
                 ["0.0",
                  "-min(max(floor(-y/%r+0.5),0),%d)*%r" % (ls, n - 1, ls),
                  "0.0"],
                 {"y": (rig, tp)})
        else:
            w_talk = _talk_widget(coll, "%s_%d" % (nm["wt"], n), step, n)
            _bone_setup(rig, tf, w_talk, (1.0, 1.0, 1.0))
            _bone_setup(rig, th, w_sel, (0.05, 0.022, 1.0))
            _limit(th, (0.0, 0.0), (0.0, step * (n - 1)))
            _drv(rig, 'pose.bones["%s"].location' % d["s"],
                 ["0.0",
                  "min(max(floor(y/%r+0.5),0),%d)*%r" % (step, n - 1, step),
                  "0.0"],
                 {"y": (rig, tp)})
        if hasattr(th, "custom_shape_wire_width"):
            th.custom_shape_wire_width = _SEL_WIRE
        _set_color(tf, True, cols_keep[0])
        _set_color(th, True, cols_keep[1])
        _set_color(ts, True, cols_keep[1])
        if tgl:
            _drv(rig, 'pose.bones["%s"].custom_shape_scale_xyz' % d["f"],
                 ["1.0*(t<%s)" % TH] * 3, tv)
            for n9 in (d["h"], d["s"]):
                _drv(rig, 'pose.bones["%s"].scale' % n9, "t<%s" % TH, tv)

    # 배치 모드 상태에 맞는 선택 가능 여부
    from .core import arrange_for
    arr = arrange_for(s, nm["f"])
    for n in [nm["f"]] + [d["f"] for d in sls]:
        rig.data.bones[n].hide_select = not arr
    for n in [nm["h"]] + [d["h"] for d in sls]:
        rig.data.bones[n].hide_select = arr
    for n in [nm["hs"]] + [d["s"] for d in sls]:
        _hide_bone(rig, n)  # 위치만 제공하는 숨은 본
    _hide_bone(rig, nm["h"])  # 칸 고르기 손잡이는 쓰지 않음 (시퀀스만)
    try:
        from .core import _fskr_apply_locks
        _fskr_apply_locks(rig, arr)
    except Exception:
        pass
    context.view_layer.update()

    # 월드 좌표 계산 (틀 본 포즈 기준)
    fmw = rig.matrix_world @ fb.matrix
    rmw = rig.matrix_world.inverted()

    def at(local):  # 틀 본 로컬 (x=오른쪽, y=위) → 아마추어 공간
        return rmw @ (fmw @ Vector(local))

    # 라벨
    _label(context, rig, nm["lbl"], it.name, 0.022, nm["f"],
           at((xw / 2, 0.032, 0.0)))
    for d, (sx, sy) in zip(sls, spos):
        if d["kind"] == "list":
            for k, body in enumerate(d["names"]):
                ob = _label(context, rig, "%s_q%d" % (nm["lbl"], k), body,
                            0.0125, nm["f"],
                            at((sx - d["w"] / 2 + 0.01,
                                sy - k * _LIST_STEP, 0.0)),
                            src=(_auto_src(it) if k == 0 else None))
                ob.data.align_x = 'LEFT'
        else:
            tl_names = ("기본", "닫힘", "반", "열림")
            for k, body in enumerate(tl_names[:d["n"]]):
                ob = _label(context, rig, "%s_t%d" % (nm["lbl"], k), "",
                            0.012, nm["f"],
                            at((sx + 0.022, sy + k * step, 0.0)),
                            src=[(body, True)])
                ob.data.align_x = 'LEFT'

    # 현재 값으로 핸들 위치 맞춤
    _LAST.pop(it.uid, None)
    _sync_one(context.scene, s, rig, it, from_frame=True)

    context.view_layer.objects.active = rig
    try:
        bpy.ops.object.mode_set(mode='POSE')
    except Exception:
        pass
    _redraw_ui(context)
    return ""


# ------------------------------------------------------------------
# 값 동기화 (핸들 <-> 리그 프로퍼티)
# ------------------------------------------------------------------

_LAST = {}          # uid -> {"cell": (r, c), "lv": {핸들: 단계}}
_BUSY = [False]


def _clamp(v, n):
    return max(0, min(int(n) - 1, int(v)))


def _loc_cell(m, x, y):
    c = _clamp(floor(x / m["cw"] + 0.5), m["cols"])
    r = _clamp(floor(-y / m["ch"] + 0.5), m["rows"])
    return r, c


def _loc_level(m, d, y):
    """핸들 위치 → 단계/줄 번호 (목록은 아래로, 슬라이더는 위로)."""
    if d.get("kind") == "list":
        return _clamp(floor(-y / m.get("ls", _LIST_STEP) + 0.5), d["n"])
    return _clamp(floor(y / m["step"] + 0.5), d["n"])


def _level_loc(m, d, lv):
    if d.get("kind") == "list":
        return -lv * m.get("ls", _LIST_STEP)
    return lv * m["step"]


def _remove_fcurves(ad, fcs):
    if not fcs or ad is None or ad.action is None:
        return
    act = ad.action
    for fc in fcs:
        done = False
        try:
            act.fcurves.remove(fc)
            done = True
        except Exception:
            pass
        if done:
            continue
        try:
            for layer in act.layers:
                for strip in layer.strips:
                    for cb in strip.channelbags:
                        try:
                            cb.fcurves.remove(fc)
                            done = True
                            break
                        except Exception:
                            continue
                    if done:
                        break
                if done:
                    break
        except Exception:
            pass


def _absorb(scene, s, rig, it, m):
    """핸들 본에 찍힌 키를 칸/말하기 키로 옮기고 핸들 키는 지운다."""
    ad = rig.animation_data
    if ad is None or ad.action is None:
        return 0
    nm = _names(it)
    sls = m.get("sl", [])
    heads = [nm["h"]] + [d["h"] for d in sls]
    pre = {h: 'pose.bones["%s"].' % h for h in heads}
    mine = [fc for fc in _action_fcurves(ad)
            if any(fc.data_path.startswith(p) for p in pre.values())]
    if not mine:
        return 0
    src = _row_source(s, it)
    pr, pc = _prop_row(src), _prop_col(it)
    ptk, pq = _prop_talk(it), _prop_q(it)
    cur = scene.frame_current
    n = 0

    def locs(h):
        return {fc.array_index: fc for fc in mine
                if fc.data_path == pre[h] + "location"}

    def frames(d9):
        out = set()
        for fc in d9.values():
            for kp in fc.keyframe_points:
                out.add(int(round(kp.co[0])))
        return sorted(out)

    def ev(d9, i, f):
        fc = d9.get(i)
        return fc.evaluate(f) if fc is not None else 0.0

    keep_h = None
    lh = locs(nm["h"])
    for f in frames(lh):
        r, c = _loc_cell(m, ev(lh, 0, f), ev(lh, 1, f))
        rig[pr] = r
        rig[pc] = c
        _key(rig, pr, f)
        _key(rig, pc, f)
        n += 1
    if lh:
        keep_h = _loc_cell(m, ev(lh, 0, cur), ev(lh, 1, cur))
    keep_qt = {}
    for d in sls:
        prop = pq if d.get("kind") == "list" else ptk
        if prop not in rig.keys():
            continue
        ld = locs(d["h"])
        for f in frames(ld):
            rig[prop] = _loc_level(m, d, ev(ld, 1, f))
            _key(rig, prop, f)
            n += 1
        if ld:
            keep_qt[prop] = _loc_level(m, d, ev(ld, 1, cur))
    _remove_fcurves(ad, mine)
    # 현재 프레임 값 복원 (키 삽입 중 바뀐 값)
    if keep_h is not None:
        rig[pr], rig[pc] = keep_h
    for prop, v in keep_qt.items():
        rig[prop] = v
    return n


def _tag(rig, it):
    try:
        rig.update_tag()
        ob = bpy.data.objects.get(it.target)
        if ob is not None:
            ob.update_tag()
    except Exception:
        pass


def _sync_one(scene, s, rig, it, from_frame=False):
    nm = _names(it)
    hb = rig.pose.bones.get(nm["h"])
    if hb is None:
        return
    m = _meta(rig, it)
    if not m:
        return
    if _absorb(scene, s, rig, it, m):
        from_frame = True  # 키에서 온 값이 기준
    rows = min(int(m["rows"]), max(1, int(it.rows)))
    cols = min(int(m["cols"]), max(1, int(it.cols)))
    src = _row_source(s, it)
    pr, pc = _prop_row(src), _prop_col(it)
    ptk, pq = _prop_talk(it), _prop_q(it)
    last = _LAST.setdefault(it.uid, {})
    key = None

    # --- 격자 (행, 열) ---
    prop_cell = (_clamp(_get_val(rig, pr), rows),
                 _clamp(_get_val(rig, pc), cols))
    loc_cell = _loc_cell(m, hb.location[0], hb.location[1])
    loc_cell = (_clamp(loc_cell[0], rows), _clamp(loc_cell[1], cols))
    if loc_cell != prop_cell:
        moved = (not from_frame and "cell" in last
                 and loc_cell != last["cell"])
        if moved:  # 사용자가 핸들을 옮김 → 값 기록
            key = _autokey_on(it)
            rig[pr] = loc_cell[0]
            rig[pc] = loc_cell[1]
            if key:
                _key(rig, pr)
                _key(rig, pc)
            _tag(rig, it)
            prop_cell = loc_cell
        else:      # 값이 바뀜(프레임 이동/패널) → 핸들을 그 칸으로
            hb.location[0] = prop_cell[1] * m["cw"]
            hb.location[1] = -prop_cell[0] * m["ch"]
    last["cell"] = prop_cell

    # --- 시퀀스 목록(q) / 말하기 슬라이더(t): 서로 독립 ---
    lv_last = last.setdefault("lv", {})
    for d in m.get("sl", []):
        b = rig.pose.bones.get(d["h"])
        if b is None or "kind" not in d:
            continue
        prop = pq if d["kind"] == "list" else ptk
        if prop not in rig.keys():
            continue
        cur = _clamp(_get_val(rig, prop), d["n"])
        lv = _loc_level(m, d, b.location[1])
        if lv != cur:
            if not from_frame and d["h"] in lv_last and lv != lv_last[d["h"]]:
                key = _autokey_on(it) if key is None else key
                rig[prop] = lv
                if key:
                    _key(rig, prop)
                _tag(rig, it)
                cur = lv
            else:
                b.location[1] = _level_loc(m, d, cur)
        lv_last[d["h"]] = cur


_AUTO = {"pending": set(), "tried": {}}


def _auto_tick():
    """예약된 시트의 뷰포트 컨트롤러를 다시 만든다 (모드/활성 오브젝트 복원)."""
    pend = list(_AUTO["pending"])
    _AUTO["pending"].clear()
    if not pend:
        return None
    ctx = bpy.context
    win = ctx.window_manager.windows[0] if ctx.window_manager.windows \
        else None
    area = None
    if win is not None:
        area = next((a for a in win.screen.areas if a.type == 'VIEW_3D'),
                    None)
    kw = {}
    if win is not None:
        kw["window"] = win
        if area is not None:
            kw["area"] = area
            kw["region"] = next((r for r in area.regions
                                 if r.type == 'WINDOW'), None)
    try:
        with ctx.temp_override(**kw):
            c2 = bpy.context
            s = c2.scene.fskr
            rig = s.rig
            if rig is None:
                return None
            prev = c2.view_layer.objects.active
            prev_mode = c2.mode
            for uid in pend:
                it = _find(s, uid)
                if it is None or not vp_exists(rig, it):
                    continue
                _AUTO["tried"][uid] = _sig(it)
                vp_build(c2, s, it)
                from .layer_vp import auto_layout
                auto_layout(c2)
            # 원래 선택 상태로 복귀
            if prev is not None and prev is not rig:
                try:
                    bpy.ops.object.mode_set(mode='OBJECT')
                except Exception:
                    pass
                c2.view_layer.objects.active = prev
            elif prev is rig and prev_mode == 'OBJECT':
                try:
                    bpy.ops.object.mode_set(mode='OBJECT')
                except Exception:
                    pass
    except Exception as e:
        print("FSKR vp auto rebuild:", e)
    return None


def vp_schedule(uid):
    """설정 변경 직후 컨트롤러 자동 갱신 예약 (UI 콜백 밖에서 실행)."""
    _AUTO["pending"].add(uid)
    try:
        if not bpy.app.timers.is_registered(_auto_tick):
            bpy.app.timers.register(_auto_tick, first_interval=0.05)
    except Exception:
        pass


def _sync_all(scene, from_frame):
    if _BUSY[0]:
        return
    try:
        if bpy.app.is_job_running('RENDER'):
            return
    except Exception:
        pass
    try:
        s = scene.fskr
        rig = s.rig
    except Exception:
        return
    if rig is None or rig.type != 'ARMATURE' or not len(s.atlases):
        return
    _BUSY[0] = True
    try:
        for it in s.atlases:
            if ("FP_spr_" + it.uid) in rig.data.bones:
                # 이름/칸 수 등이 바뀌어 낡았으면 자동 갱신 (같은 설정엔 한 번만)
                try:
                    if not from_frame and vp_stale(rig, it):
                        sg = _sig(it)
                        if _AUTO["tried"].get(it.uid) != sg:
                            _AUTO["tried"][it.uid] = sg
                            vp_schedule(it.uid)
                except Exception:
                    pass
                try:
                    _sync_one(scene, s, rig, it, from_frame)
                except Exception as e:
                    print("FSKR sprite vp:", e)
    finally:
        _BUSY[0] = False


@bpy.app.handlers.persistent
def _on_depsgraph(scene, depsgraph=None):
    _sync_all(scene, False)


@bpy.app.handlers.persistent
def _on_frame(scene, depsgraph=None):
    _sync_all(scene, True)


@bpy.app.handlers.persistent
def _on_load(*_args):
    _LAST.clear()


# ------------------------------------------------------------------
# 오퍼레이터 / UI
# ------------------------------------------------------------------

class FSKR_OT_atlas_vp_build(bpy.types.Operator):
    bl_idname = "fskr.atlas_vp_build"
    bl_label = "뷰포트 컨트롤러 만들기"
    bl_description = ("이 시트의 칸을 뷰포트에서 고르는 격자 패드(+ 말하기 "
                      "슬라이더)를 드라이버 방식 패널에 만듭니다")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        return context.scene.fskr.rig is not None

    def execute(self, context):
        s = context.scene.fskr
        it = _find(s, self.uid)
        if it is None:
            return {'CANCELLED'}
        err = vp_build(context, s, it)
        if err:
            self.report({'ERROR'}, err)
            return {'CANCELLED'}
        try:
            from .layer_vp import auto_layout
            auto_layout(context)      # 자동 정렬이 켜져 있으면 다른 컨트롤러와 맞춤
        except Exception:
            pass
        _redraw_ui(context)
        self.report({'INFO'}, _tr("뷰포트 컨트롤러: ") + it.name)
        return {'FINISHED'}


class FSKR_OT_atlas_vp_remove(bpy.types.Operator):
    bl_idname = "fskr.atlas_vp_remove"
    bl_label = "뷰포트 컨트롤러 삭제"
    bl_description = "이 시트의 뷰포트 컨트롤러를 지웁니다 (칸 키는 유지)"
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        return context.scene.fskr.rig is not None

    def execute(self, context):
        s = context.scene.fskr
        it = _find(s, self.uid)
        if it is None:
            return {'CANCELLED'}
        vp_remove(context, s.rig, it)
        _redraw_ui(context)
        return {'FINISHED'}


def vp_draw(layout, rig, it):
    """시트 상자 안의 컨트롤러 버튼 줄."""
    row = layout.row(align=True)
    if vp_exists(rig, it):
        stale = vp_stale(rig, it)
        row.alert = stale
        row.operator("fskr.atlas_vp_build", text=_tr("뷰포트 컨트롤러 갱신"),
                     icon='ERROR' if stale else 'FILE_REFRESH').uid = it.uid
        row.alert = False
        row.operator("fskr.atlas_vp_remove", text="",
                     icon='TRASH').uid = it.uid
        try:
            s = bpy.context.scene.fskr
            if hasattr(s, "arrange"):
                # 입 컨트롤러만 배치 모드 (위치만 옮김, 크기는 고정)
                from .operators import arrange_button
                arrange_button(layout, s, "FP_spr_")
        except Exception:
            pass
        if stale:
            layout.label(text=_tr("칸 수/이미지가 바뀌었습니다. "
                                  "컨트롤러를 갱신하세요"), icon='INFO')
    else:
        row.operator("fskr.atlas_vp_build", text=_tr("뷰포트 컨트롤러 만들기"),
                     icon='ARMATURE_DATA').uid = it.uid


vp_classes = (FSKR_OT_atlas_vp_build, FSKR_OT_atlas_vp_remove)


def vp_register():
    nov_register()
    from .core import _LANG_HOOKS
    app_handler_add(_LANG_HOOKS, relabel_all)
    h = bpy.app.handlers
    app_handler_add(h.depsgraph_update_post, _on_depsgraph)
    app_handler_add(h.frame_change_post, _on_frame)
    app_handler_add(h.load_post, _on_load)


def vp_unregister():
    nov_unregister()
    h = bpy.app.handlers
    for lst, fn in ((h.depsgraph_update_post, _on_depsgraph),
                    (h.frame_change_post, _on_frame),
                    (h.load_post, _on_load)):
        if fn in lst:
            lst.remove(fn)


# ------------------------------------------------------------------
# 오버레이를 꺼도 컨트롤러 표시 (애드온이 직접 그림)
# ------------------------------------------------------------------
# Blender는 Show Overlays를 끄면 본과 이미지 엠프티를 그리지 않는다.
# 켜 두면 그 상태에서만 FP_ 본 위젯과 시트 그림을 GPU로 다시 그린다.
# (라벨 텍스트는 일반 오브젝트라 원래 보임)

from .core import FSKR_Settings  # noqa: E402


def _nov_update(self, context):
    try:
        for win in context.window_manager.windows:
            for area in win.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
    except Exception:
        pass


FSKR_Settings.__annotations__["show_no_overlay"] = bpy.props.BoolProperty(
    name="오버레이 꺼도 표시", default=False, update=_nov_update,
    description="뷰포트의 Show Overlays를 꺼도 컨트롤러(표정 목록/시선 패드 "
                "등)를 보이게 합니다. 화면 표시용이며 렌더에는 "
                "나오지 않습니다")

_EN.update({
    "오버레이 꺼도 표시": "Show without overlays",
})
_JA.update({"오버레이 꺼도 표시": "オーバーレイOFFでも表示"})
_ZH.update({"오버레이 꺼도 표시": "关闭叠加层也显示"})

_NOV = {"handle": None, "edges": {}}


def _mesh_lines(me):
    """위젯 메시 → 로컬 좌표 선분 목록 (메시가 바뀌면 다시 계산)."""
    key = me.as_pointer()
    sig = (len(me.vertices), len(me.edges))
    hit = _NOV["edges"].get(key)
    if hit is not None and hit[0] == sig:
        return hit[1]
    vs = [v.co.copy() for v in me.vertices]
    out = []
    for e in me.edges:
        out.append(vs[e.vertices[0]])
        out.append(vs[e.vertices[1]])
    _NOV["edges"][key] = (sig, out)
    return out


def _bone_visible(ob, pb):
    b = pb.bone
    if b.hide or getattr(pb, "hide", False):
        return False
    cols = getattr(b, "collections", None)
    if cols is not None and len(cols):
        return any(getattr(c, "is_visible_effectively",
                           getattr(c, "is_visible", True)) for c in cols)
    return True


def _bone_color(pb, selected):
    try:
        c = pb.color
        if c.palette == 'CUSTOM':
            cc = c.custom
            return tuple(cc.select if selected else cc.normal)
    except Exception:
        pass
    return (0.95, 0.6, 0.2) if selected else (0.08, 0.08, 0.08)


def _shape_matrix(ob, pb):
    from mathutils import Euler
    src = pb.custom_shape_transform or pb
    m = ob.matrix_world @ src.matrix
    if pb.use_custom_shape_bone_size:
        m = m @ Matrix.Scale(pb.bone.length, 4)
    m = m @ Matrix.Translation(pb.custom_shape_translation)
    m = m @ Euler(pb.custom_shape_rotation_euler).to_matrix().to_4x4()
    m = m @ Matrix.Diagonal((*pb.custom_shape_scale_xyz, 1.0))
    return m


def _nov_draw():
    ctx = bpy.context
    try:
        sd = ctx.space_data
        if sd is None or sd.type != 'VIEW_3D' or sd.overlay.show_overlays:
            return
        scene = ctx.scene
        if not scene.fskr.show_no_overlay:
            return
    except Exception:
        return
    import gpu
    from gpu_extras.batch import batch_for_shader
    try:
        region = ctx.region
        vp = (region.width, region.height)
    except Exception:
        vp = (1000, 1000)
    try:
        gpu.state.blend_set('ALPHA')
        gpu.state.depth_test_set('NONE')
        # 시트 그림 (이미지 엠프티)
        img_sh = None
        for ob in scene.objects:
            if not (ob.name.startswith("FPSPR_") and ob.type == 'EMPTY'
                    and ob.empty_display_type == 'IMAGE'
                    and ob.data is not None):
                continue
            if ob.hide_viewport or not ob.visible_get():
                continue
            img = ob.data
            try:
                iw, ih = img.size[:]
                if iw <= 0 or ih <= 0:
                    continue
                tex = gpu.texture.from_image(img)
            except Exception:
                continue
            S = ob.empty_display_size
            if iw >= ih:
                w, h = S, S * ih / iw
            else:
                w, h = S * iw / ih, S
            ox, oy = ob.empty_image_offset
            x0, y0 = ox * w, oy * h
            x1, y1 = x0 + w, y0 + h
            mw = ob.matrix_world
            pos = [mw @ Vector(p) for p in ((x0, y0, 0), (x1, y0, 0),
                                            (x1, y1, 0), (x0, y1, 0))]
            if img_sh is None:
                img_sh = gpu.shader.from_builtin('IMAGE_COLOR')
            bt = batch_for_shader(
                img_sh, 'TRIS',
                {"pos": pos, "texCoord": ((0, 0), (1, 0), (1, 1), (0, 1))},
                indices=((0, 1, 2), (0, 2, 3)))
            img_sh.bind()
            img_sh.uniform_sampler("image", tex)
            img_sh.uniform_float("color", (1.0, 1.0, 1.0, ob.color[3]))
            bt.draw(img_sh)
        # 컨트롤러 본 위젯
        ln_sh = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        for ob in scene.objects:
            if ob.type != 'ARMATURE' or "FP_root" not in ob.data.bones:
                continue
            if not ob.visible_get():
                continue
            for pb in ob.pose.bones:
                if not pb.name.startswith("FP_"):
                    continue
                sh = pb.custom_shape
                if sh is None or sh.type != 'MESH':
                    continue
                if not _bone_visible(ob, pb):
                    continue
                loc = _mesh_lines(sh.data)
                if not loc:
                    continue
                m = _shape_matrix(ob, pb)
                pts = [m @ v for v in loc]
                sel = bool(getattr(pb, "select", False)
                           or getattr(pb.bone, "select", False))
                col = _bone_color(pb, sel)
                bt = batch_for_shader(ln_sh, 'LINES', {"pos": pts})
                ln_sh.bind()
                ln_sh.uniform_float("viewportSize", vp)
                ln_sh.uniform_float(
                    "lineWidth", max(1.0, float(getattr(
                        pb, "custom_shape_wire_width", 1.0))) * 1.2)
                ln_sh.uniform_float("color", (*col[:3], 1.0))
                bt.draw(ln_sh)
    except Exception as e:  # 그리기 오류가 뷰포트를 막지 않게
        print("FSKR no-overlay draw:", e)
    finally:
        try:
            gpu.state.blend_set('NONE')
        except Exception:
            pass


def nov_register():
    _NOV["handle"] = draw_add(bpy.types.SpaceView3D, _nov_draw, (),
                              'WINDOW', 'POST_VIEW', "atlas_vp_nov")


def nov_unregister():
    draw_remove("atlas_vp_nov")
    _NOV["handle"] = None
    _NOV["edges"].clear()
