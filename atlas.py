"""스프라이트 시트(텍스처 아틀라스) 표정.

한 장의 이미지에 그려 둔 입/눈 모양을 격자 칸 단위로 바꿔 끼우는 방식.
행 = 표정, 열 = 입 벌림(립싱크)으로 두 축을 분리해서, 표정 키와 대사
키를 서로 건드리지 않고 작업할 수 있다.

값은 리그 오브젝트의 커스텀 프로퍼티(정수)에 저장되므로 다른 컨트롤러와
같은 액션에 키가 찍힌다. 대상 메시는 UV Warp 모디파이어 또는 머티리얼의
Mapping 노드를 드라이버로 밀어서 칸을 바꾼다.
"""
import bpy
from .core import app_handler_add, draw_add, draw_remove
import bpy.utils.previews
import json
import re

from .core import (
    FSKR_Settings,
    _EN,
    _JA,
    _ZH,
    _action_fcurves,
    _redraw_ui,
    _stable_items,
    _tr,
)


# ------------------------------------------------------------------
# 번역
# ------------------------------------------------------------------

_EN.update({
    "일괄 조절": "Batch adjust",
    "체크 모두 해제": "Clear checks",
    "이미 변형된 값이 있는 칸입니다": "This cell already has adjusted values",
    "그래도 일괄 조절할까요? 크기는 같은 비율로, 위치는 움직인 만큼 바뀝니다.":
        "Edit it together anyway? Size changes by the same ratio, position "
        "by the same amount.",
    "일괄 조절하기": "Batch adjust",
    "지금 칸(빨간 버튼)의 크기·위치·반전을 바꾸면 체크한 칸도 같이 바뀝니다":
        "Changing the current cell (red) also changes the checked cells",
    "크기는 같은 비율로, 위치는 움직인 만큼":
        "Size by the same ratio, position by the same amount",
    "다른 칸 그림": "Other cell's image", "반전": "Flip",
    "이 칸 보기": "Show this cell",
    "칸 번호 버튼 = 그 칸을 뷰포트에 보기 · 체크 = 일괄 조절":
        "Cell number button = show it in the viewport · check = batch adjust",
})
_EN.update({
    "스프라이트 시트 (텍스처 표정)": "Sprite Sheet (texture expressions)",
    "스프라이트 시트 추가": "Add sprite sheet",
    "선택한 오브젝트(입/눈 데칼 등)에 격자 이미지 칸 전환을 추가합니다": "Adds grid-cell switching to the selected object (mouth/eye decal etc.)",
    "스프라이트 시트 삭제": "Remove sprite sheet",
    "드라이버·모디파이어·노드와 리그 값을 모두 제거합니다 (키프레임은 유지)": "Removes drivers, modifier, nodes and rig values (keyframes are kept)",
    "적용 (드라이버 재구성)": "Apply (rebuild drivers)",
    "현재 설정대로 모디파이어/노드와 드라이버를 다시 만듭니다": "Rebuilds the modifier/nodes and drivers from the current settings",
    "썸네일 갱신": "Refresh thumbnails",
    "이미지를 칸 단위로 잘라 선택 그리드 썸네일을 만듭니다": "Slices the image into cells for the picker thumbnails",
    "UV를 첫 칸에 맞추기": "Fit UVs to first cell",
    "대상의 UV(버텍스 그룹이 있으면 그 부분만)를 좌상단 첫 칸 크기로 맞춥니다": "Fits the target's UVs (vertex group only, if set) into the top-left cell",
    "칸 키프레임": "Key cell",
    "현재 칸 번호에 Constant 키를 삽입합니다": "Inserts a Constant key for the current cell index",
    "이전/다음 칸": "Previous/next cell",
    "Constant 보간 정리": "Fix to Constant",
    "스프라이트 시트 키를 모두 Constant 보간으로 바꿉니다 (칸 사이가 섞이는 문제 방지)": "Sets every sprite-sheet key to Constant interpolation (prevents in-between cells)",
    "스프라이트 립싱크 다시 굽기": "Rebake sprite lip sync",
    "현재 립싱크 구간으로 입 칸 키만 다시 굽습니다": "Rebakes only the mouth-cell keys from the current lip-sync segments",
    "이름": "Name", "대상 오브젝트": "Target object", "이미지": "Image",
    "방식": "Method", "UV 맵": "UV map", "버텍스 그룹": "Vertex group",
    "열 (가로 칸 수)": "Columns", "행 (세로 칸 수)": "Rows",
    "행 이름": "Row names", "열 이름": "Column names",
    "행 따라가기": "Follow row of",
    "행": "Row", "열": "Column", "표정": "Expression", "입": "Mouth",
    "선택하면 키 삽입": "Key on pick",
    "립싱크에 사용": "Use for lip sync", "립싱크 방식": "Lip-sync mode",
    "모음 (A/I/U/E/O)": "Vowels (A/I/U/E/O)", "벌림 3단계": "Open 3-step",
    "닫힘": "Closed", "반 열림": "Half open", "열림": "Open",
    "반 열림 기준": "Half threshold", "열림 기준": "Open threshold",
    "최소 유지 (프레임)": "Min hold (frames)",
    "설정": "Settings",
    "설정이 바뀌었습니다. '적용'을 눌러 주세요": "Settings changed. Press Apply",
    "대상이 메시가 아닙니다": "Target is not a mesh",
    "리그를 먼저 지정하세요": "Set the rig first",
    "스프라이트 시트가 없습니다. 입/눈 데칼을 선택하고 + 를 누르세요": "No sprite sheets. Select a mouth/eye decal and press +",
    "(자체 행)": "(own row)",
    "행을 따라감: ": "Row follows: ",
    "이미지 없음 (썸네일 불가)": "No image (no thumbnails)",
    "스프라이트 시트 적용: ": "Sprite sheet applied: ",
    "UV 맞춤 완료 (루프 %d개)": "UVs fitted (%d loops)",
    "맞출 UV가 없습니다": "No UVs to fit",
    "Constant 정리: 키 %d개": "Constant fix: %d keys",
    "스프라이트 립싱크: %d개 굽기": "Sprite lip sync: baked %d",
    "머티리얼에서 이미지 텍스처를 찾지 못했습니다": "No image texture found in the materials",
    "작업 방식": "Workflow",
    "드라이버 방식": "Driver mode",
    "스프라이트 방식": "Sprite mode",
    "셰이프 키 슬라이더/패드 컨트롤러 (기존 Face Rig)": "Shape key slider/pad controllers (classic Face Rig)",
    "격자 이미지 칸 전환 (텍스처 표정·립싱크)": "Grid image cell switching (texture expressions & lip sync)",
    "오디오 립싱크": "Audio lip sync",
    "시트의 '립싱크에 사용'을 켜 주세요": "Turn on 'Use for lip sync' on a sheet",
    "배치 방식": "Layout",
    "그림 크기": "Drawing size", "종횡비 고정": "Lock aspect",
    "가장자리 잘라내기": "Edge crop",
    "상하 반전": "Flip V", "좌우 반전": "Flip H",
    "기본 입": "Default mouth", "메인": "Main", "말하는 중": "Talking",
    "이 입의 크기/위치": "Size/position of this mouth", "크기": "Size",
    "위쪽 칸별 크기/위치와 같은 값": "Same values as the per-cell size/position above",
    "이 시퀀스를 메인으로 사용": "Use this sequence as main",
    "메인으로 사용": "Use as main",
    "뷰포트 리그에 표시": "Show on viewport rig",
    "뷰포트 리그에 표시 (메인은 항상)": "Show on viewport rig (always for main)",
    "자동": "Auto", "켬": "On",
    "어떤 표정에서 말하든 이 입을 씀": "Used when talking in any expression",
    "이 표정일 때만 사용": "Only for this expression",
    "나머지 표정 전부": "All other expressions",
    "표정: 나머지 표정 전부": "Expression: all other expressions",
    "표정": "Expression", "단일 입": "Single mouth",
    "말할 때도 이 입 그대로 (뻐끔 안 함)": "Keeps this mouth while talking (no flapping)",
    "말할 때 쓸 입:": "Mouths while talking:",
    "값을 바꾸면 그 단계가 미리보기됩니다": "Editing a value previews that step",
    "미리보기 중 (프레임을 옮기면 꺼짐)": "Previewing (turns off on frame change)", "기준: 그 외 모든 칸": "Base: all other cells",
    "단계 크기/위치": "Step size/position", "시퀀스 미리보기": "Sequence preview",
    "반전 칸 만들기": "Make flipped cell", "원본 칸: ": "Source cell: ",
    "만들 칸 (행, 열)": "Target cell (row, col)",
    "칸 번호가 범위를 벗어났습니다": "Cell is out of range",
    "원본과 다른 칸을 고르세요": "Pick a cell other than the source",
    "반전 칸 만들기: %d-%d → %d-%d": "Flipped cell: %d-%d → %d-%d",
    "이 칸 = %d-%d 그림": "This cell = drawing of %d-%d",
    "칸 비우기": "Clear cell",
    "이미지 불러오기": "Open image", "이미지 불러오기: ": "Image loaded: ",
    "이미지 파일을 고르세요": "Pick an image file",
    "대상 머티리얼에서 바꿀 시트 이미지를 찾지 못했습니다. 이미지 텍스처 노드에 직접 연결해 주세요": "Could not find the sheet image in the target material. Connect it to an Image Texture node manually", "칸 비우기로 해제": "use Clear cell to remove",
    "다른 칸 그림 연결 모두 비우기": "Clear all cell links",
    "다른 칸 그림 연결 모두 비우기 (%d칸)": "Clear all cell links (%d cells)",
    "칸 %d개를 비웠습니다": "Cleared %d cells",
    " (상하 반전)": " (flipped V)", " (좌우 반전)": " (flipped H)",
    "  · ↺ 로 해제": "  · ↺ to clear",
    "말할 때 입": "Mouth while talking", "모음 (A/I/U/E/O)": "Vowels (A/I/U/E/O)",
    "시퀀스": "Sequence", "지금 칸으로 지정": "Set to current cell",
    "피커에서 칸을 고른 뒤 ⤓ 로 지정": "Pick a cell, then press ⤓",
    "미리보기": "Preview", "끄기": "Off", "말하기 미리보기": "Talk preview",
    "키 삽입: '%s' 오브젝트 (프레임 %d)": "Keyed on object '%s' (frame %d)",
    "칸마다 따로": "Per cell", "이 칸 전용 값": "This cell's own value",
    "공통값 (움직이면 이 칸만 저장)": "Shared value (editing saves to this cell only)",
    "이 칸 개별 설정 지우기": "Clear this cell's override",
    "이 값을 모든 칸에": "Apply to all cells",
    "가로": "Width", "세로": "Height", "위치 X": "Offset X", "위치 Y": "Offset Y",
    "투명 배경 설정을 눌러야 칸 밖이 잘립니다": "Run 'Set up transparency' to clip outside the cell",
    "투명 배경 설정": "Set up transparency",
    "투명 배경 설정 완료 (머티리얼 %d개)": "Transparency set up (%d materials)",
    "격자 (행=표정, 열=입)": "Grid (row=expression, column=mouth)",
    "자유 배치": "Free layout",
    "표정 칸": "Expression cell",
    "현재 칸 기준으로 시퀀스 추가": "Add sequence for current cell",
    "시퀀스 삭제": "Remove sequence",
    "위아래 시퀀스 자동 생성": "Auto sequences (top/bottom)",
    "없음 (-1)": "None (-1)",
    "표정 칸마다 닫힘/반/열림 칸 시퀀스를 번갈아 씁니다": "Cycles closed/half/open cells per expression cell",
    "그 외 모든 칸": "All other cells",
    "기준": "Base", "기준 칸": "Base cell", "반": "Half",
    "시퀀스 %d개 생성": "Created %d sequences",
    "표정 칸을 고른 뒤 + 로 시퀀스 추가, 또는 마법봉으로 위아래 자동 생성": "Pick a cell and press +, or use the wand for top/bottom auto sequences",
})

_JA.update({
    "스프라이트 시트 (텍스처 표정)": "スプライトシート (テクスチャ表情)",
    "스프라이트 시트 추가": "スプライトシート追加",
    "스프라이트 시트 삭제": "スプライトシート削除",
    "적용 (드라이버 재구성)": "適用 (ドライバー再構築)",
    "썸네일 갱신": "サムネイル更新",
    "UV를 첫 칸에 맞추기": "UVを最初のマスに合わせる",
    "칸 키프레임": "マスにキー",
    "Constant 보간 정리": "Constant補間に整理",
    "스프라이트 립싱크 다시 굽기": "スプライト口パク再ベイク",
    "행": "行", "열": "列", "표정": "表情", "입": "口",
    "선택하면 키 삽입": "選択でキー挿入",
    "립싱크에 사용": "口パクに使用",
    "닫힘": "閉じ", "반 열림": "半開き", "열림": "開き",
    "설정": "設定",
    "드라이버 방식": "ドライバー方式",
    "스프라이트 방식": "スプライト方式",
    "오디오 립싱크": "音声口パク",
    "배치 방식": "配置方式",
    "투명 배경 설정": "透明背景設定",
    "표정 칸": "表情マス",
    "시퀀스": "シーケンス",
    "위아래 시퀀스 자동 생성": "上下シーケンス自動生成",
    "설정이 바뀌었습니다. '적용'을 눌러 주세요": "設定が変わりました。「適用」を押してください",
})

_ZH.update({
    "스프라이트 시트 (텍스처 표정)": "精灵图 (贴图表情)",
    "스프라이트 시트 추가": "添加精灵图",
    "스프라이트 시트 삭제": "删除精灵图",
    "적용 (드라이버 재구성)": "应用 (重建驱动)",
    "썸네일 갱신": "刷新缩略图",
    "행": "行", "열": "列", "표정": "表情", "입": "嘴",
    "설정": "设置",
    "드라이버 방식": "驱动方式",
    "스프라이트 방식": "精灵图方式",
})


# ------------------------------------------------------------------
# 데이터
# ------------------------------------------------------------------

_MOD_PREFIX = "FSKR_Atlas_"
_MAP_PREFIX = "FSKR_AT_"
_UVN_PREFIX = "FSKR_ATUV_"
_DEF_PROP = "fskr_at_def"


def _rig():
    try:
        return bpy.context.scene.fskr.rig
    except Exception:
        return None


def _apk(it):
    return getattr(it, "pkey", "") or ""


def _prop_row(it):
    k = _apk(it)
    return (k + "_Cell_Row") if k else "fskr_at_%s_r" % it.uid


def _prop_col(it):
    k = _apk(it)
    return (k + "_Cell_Col") if k else "fskr_at_%s_c" % it.uid


def _prop_talk(it):
    k = _apk(it)
    return (k + "_Talk") if k else "fskr_at_%s_t" % it.uid


def _prop_q(it):
    """시퀀스 강제 선택 (0 = 표정 따라 자동, i = i번째 시퀀스)."""
    k = _apk(it)
    return (k + "_Sequence") if k else "fskr_at_%s_q" % it.uid


def _prop_pv(it, k):
    """미리보기 전용 값 (키를 넣지 않음, -1 = 꺼짐). k: 'r' / 'c' / 't'."""
    a = _apk(it)
    if a:
        return a + "_Edit_" + {"r": "Row", "c": "Col", "t": "Talk",
                               "q": "Sequence"}.get(k, k)
    return "fskr_at_%s_p%s" % (it.uid, k)


def _pv_ensure(rig, it):
    for k, n in (("r", int(it.rows)), ("c", int(it.cols)), ("t", _K),
                 ("q", len(it.flaps) + 1)):
        p = _prop_pv(it, k)
        if p not in rig.keys():
            rig[p] = -1
        try:
            rig.id_properties_ui(p).update(min=-1, max=max(0, n - 1))
        except Exception:
            pass


def _pv_active(rig, it):
    if rig is None:
        return False
    return any(_get_val(rig, _prop_pv(it, k)) >= 0 for k in "rctq"
               if _prop_pv(it, k) in rig.keys())


_PV_STATE = {"frame": None}


def _pv_set(rig, it, r=None, c=None, tcode=None, q=None):
    _pv_ensure(rig, it)
    try:
        on = not (r is None and c is None and tcode is None)
        _PV_STATE["frame"] = (bpy.context.scene.frame_current if on
                              else None)
    except Exception:
        pass
    rig[_prop_pv(it, "r")] = -1 if r is None else int(r)
    rig[_prop_pv(it, "c")] = -1 if c is None else int(c)
    rig[_prop_pv(it, "t")] = -1 if tcode is None else int(tcode)
    rig[_prop_pv(it, "q")] = -1 if q is None else int(q)
    try:
        rig.update_tag()
    except Exception:
        pass


def _find(s, uid):
    return next((a for a in s.atlases if a.uid == uid), None)


def _row_source(s, it):
    """행 값을 읽을 아틀라스 (다른 시트의 행을 따라가면 그쪽)."""
    if it.row_link and it.row_link != it.uid:
        src = _find(s, it.row_link)
        if src is not None and not (src.row_link and src.row_link != src.uid):
            return src
    return it


def _get_val(rig, prop):
    if rig is None:
        return 0
    try:
        return int(round(float(rig.get(prop, 0))))
    except Exception:
        return 0


def _names(txt, n, fallback):
    parts = [p.strip() for p in (txt or "").split(",")]
    out = []
    for i in range(n):
        nm = parts[i] if i < len(parts) and parts[i] else ""
        out.append(nm or ("%s %d" % (fallback, i)))
    return out


def _sig(it):
    """드라이버 구성에 영향을 주는 설정 요약 (적용 필요 여부 판단용)."""
    return json.dumps([it.target, it.method, it.image, it.uv_map,
                       it.vgroup, int(it.cols), int(it.rows), it.row_link,
                       it.layout, "lut7",
                       len(it.flaps) if it.layout == 'FREE' else 0])


def _ensure_prop(rig, prop, n):
    if prop not in rig.keys():
        rig[prop] = 0
    try:
        ui = rig.id_properties_ui(prop)
        ui.update(min=0, max=max(0, n - 1), soft_min=0,
                  soft_max=max(0, n - 1), step=1)
    except Exception:
        pass


def _fcurves_for(rig, path):
    ad = rig.animation_data if rig else None
    return [fc for fc in _action_fcurves(ad) if fc.data_path == path]


def _make_constant(rig, path):
    n = 0
    for fc in _fcurves_for(rig, path):
        for kp in fc.keyframe_points:
            if kp.interpolation != 'CONSTANT':
                kp.interpolation = 'CONSTANT'
                n += 1
        fc.update()
    return n


def _key(rig, prop, frame=None):
    """커스텀 프로퍼티에 Constant 키 삽입."""
    if rig is None:
        return
    if frame is None:
        frame = bpy.context.scene.frame_current
    path = '["%s"]' % prop
    try:
        rig.keyframe_insert(data_path=path, frame=frame, group="Sprite Sheet")
    except Exception:
        return
    _make_constant(rig, path)


def mouth_autokey(s, it):
    """입 '바꾸면 자동 키': 시트 설정 또는 입 파츠가 있는 캔버스의 설정."""
    if it.autokey:
        return True
    try:
        from . import eye as EY
        return any(st.autokey for st, L in EY.mouth_layers(s, it))
    except Exception:
        return False


def _autokey_on(it):
    try:
        from .eye import preset_editing
        if preset_editing():
            return False
    except Exception:
        pass
    try:
        sc = bpy.context.scene
        return bool(mouth_autokey(sc.fskr, it)
                    or sc.tool_settings.use_keyframe_insert_auto)
    except Exception:
        return bool(it.autokey)


def _poke(context=None):
    """RNA 경로로 씬을 건드려 드라이버 재계산을 확실히 일으킨다."""
    ctx = context or bpy.context
    try:
        s = ctx.scene.fskr
        s.ui_mode = s.ui_mode
    except Exception:
        pass
    try:
        ctx.view_layer.update()
    except Exception:
        pass
    _redraw_ui(ctx)


def _key_state(it, what):
    """이 축에 키가 있는지: 현재 프레임에 키 = 다이아몬드, 애니메이션만 = 점."""
    rig = _rig()
    if rig is None:
        return None
    if what == 'ROW':
        props = [_prop_row(it)]
    elif what == 'COL':
        props = [_prop_col(it)]
    else:
        props = [_prop_row(it), _prop_col(it)]
    try:
        f = bpy.context.scene.frame_current
    except Exception:
        return None
    any_anim = False
    for p in props:
        for fc in _fcurves_for(rig, '["%s"]' % p):
            any_anim = True
            if any(abs(k.co[0] - f) < 0.5 for k in fc.keyframe_points):
                return 'DECORATE_KEYFRAME'
    return 'DECORATE_ANIMATE' if any_anim else None


def _set_val(it, prop, v, n, key=None):
    rig = _rig()
    if rig is None:
        return
    v = max(0, min(int(n) - 1, int(v)))
    rig[prop] = v
    if key is None:
        key = _autokey_on(it)
    if key:
        _key(rig, prop)
    try:
        rig.update_tag()
        ob = bpy.data.objects.get(it.target)
        if ob is not None:
            ob.update_tag()
    except Exception:
        pass


# ----- 썸네일 -----

_PREV = {}      # uid -> previews collection
_PREV_SIG = {}  # uid -> 생성 시 서명
_PREV_ICONS = {}  # uid -> {(r, c): icon_id}
_PREV_PENDING = set()
_PREV_FILLED = {}  # uid -> {(r, c): 그림이 있는지}


def _thumb_sig(it):
    img = bpy.data.images.get(it.image) if it.image else None
    if img is None:
        return None
    alias = tuple((e.r, e.c, e.src_r, e.src_c, e.flip_x, e.flip_y)
                  for e in it.cells if e.src_r >= 0 or e.flip_x or e.flip_y)
    return (img.name, tuple(img.size), int(it.cols), int(it.rows),
            img.filepath, alias)


def _thumbs_free(uid):
    pc = _PREV.pop(uid, None)
    if pc is not None:
        try:
            bpy.utils.previews.remove(pc)
        except Exception:
            pass
    _PREV_SIG.pop(uid, None)
    _PREV_ICONS.pop(uid, None)


def _thumbs_build(it):
    """이미지를 칸 단위로 잘라 미리보기 아이콘 생성 (축소 복사본 사용)."""
    import numpy as np
    uid = it.uid
    _thumbs_free(uid)
    img = bpy.data.images.get(it.image) if it.image else None
    if img is None:
        return False
    cols, rows = max(1, int(it.cols)), max(1, int(it.rows))
    try:
        w, h = img.size
    except Exception:
        return False
    if w <= 0 or h <= 0:
        return False
    cell = 192   # 썸네일 해상도 (크게 보여도 흐리지 않게)
    tw = max(1, min(w // cols, cell))
    th = max(1, min(h // rows, cell))
    W, H = tw * cols, th * rows
    if w * h <= 4096 * 4096:
        # 원본 픽셀을 직접 읽어 샘플링 (저장 안 된 이미지도 정확)
        full = np.empty(w * h * 4, dtype=np.float32)
        img.pixels.foreach_get(full)
        full = full.reshape(h, w, 4)
        xs = np.minimum(((np.arange(W) + 0.5) * (w / W)).astype(int), w - 1)
        ys = np.minimum(((np.arange(H) + 0.5) * (h / H)).astype(int), h - 1)
        arr = full[np.ix_(ys, xs)].copy()
        del full
    else:
        tmp = img.copy()
        try:
            tmp.scale(W, H)
            W, H = tmp.size
            arr = np.empty(W * H * 4, dtype=np.float32)
            tmp.pixels.foreach_get(arr)
        finally:
            bpy.data.images.remove(tmp)
        arr = arr.reshape(H, W, 4)
    filled = {}
    # 투명 배경 → 밝은 회색 위에 합성 (어두운 선도 잘 보이게)
    a = arr[..., 3:4]
    rgb = arr[..., :3] * a + 0.82 * (1.0 - a)
    pc = bpy.utils.previews.new()
    icons = {}
    for r in range(rows):
        y1 = H - r * th
        y0 = y1 - th
        for c in range(cols):
            x0 = c * tw
            sub = rgb[y0:y1, x0:x0 + tw]
            filled[(r, c)] = bool(arr[y0:y1, x0:x0 + tw, 3].max() > 0.05)
            rgba = np.concatenate(
                [sub, np.ones(sub.shape[:2] + (1,), np.float32)], axis=2)
            flat = rgba.ravel()
            pv = pc.new("%d_%d" % (r, c))
            pv.image_size = (tw, th)
            pv.image_pixels_float.foreach_set(flat)
            pv.icon_size = (tw, th)
            pv.icon_pixels_float.foreach_set(flat)
            icons[(r, c)] = pv.icon_id
    # 반전 칸(또는 뒤집은 칸) 썸네일: 원본 칸 픽셀을 뒤집어 생성
    for e in it.cells:
        if not (e.src_r >= 0 or e.flip_x or e.flip_y):
            continue
        sr, sc2 = _cell_src(it, e.r, e.c)
        y1 = H - sr * th
        sub = rgb[y1 - th:y1, sc2 * tw:sc2 * tw + tw]
        if e.flip_y:
            sub = sub[::-1]
        if e.flip_x:
            sub = sub[:, ::-1]
        rgba = np.concatenate(
            [sub, np.ones(sub.shape[:2] + (1,), np.float32)], axis=2)
        flat = np.ascontiguousarray(rgba).ravel()
        pv = pc.new("a%d_%d" % (e.r, e.c))
        pv.image_size = (tw, th)
        pv.image_pixels_float.foreach_set(flat)
        pv.icon_size = (tw, th)
        pv.icon_pixels_float.foreach_set(flat)
        icons[(e.r, e.c)] = pv.icon_id
        filled[(e.r, e.c)] = filled.get((sr, sc2), True)
    _PREV[uid] = pc
    _PREV_ICONS[uid] = icons
    _PREV_FILLED[uid] = filled
    _PREV_SIG[uid] = _thumb_sig(it)
    return True


def _thumbs_tick():
    try:
        s = bpy.context.scene.fskr
        for uid in list(_PREV_PENDING):
            it = _find(s, uid)
            if it is not None:
                try:
                    _thumbs_build(it)
                except Exception:
                    pass
        _redraw_ui(bpy.context)
    except Exception:
        pass
    _PREV_PENDING.clear()
    return None


def _thumbs_request(it):
    """draw 중에는 픽셀을 못 읽으므로 타이머로 미룬다."""
    if it.uid in _PREV_PENDING:
        return
    _PREV_PENDING.add(it.uid)
    try:
        bpy.app.timers.register(_thumbs_tick, first_interval=0.05)
    except Exception:
        pass


def _icon(it, r, c):
    return _PREV_ICONS.get(it.uid, {}).get((r, c), 0)


def _thumbs_ready(it):
    return (it.uid in _PREV_ICONS
            and _PREV_SIG.get(it.uid) == _thumb_sig(it))


def _thumbs_free_all():
    for uid in list(_PREV):
        _thumbs_free(uid)


# ----- 피커 (EnumProperty get/set) -----

def _row_items(self, context):
    n = max(1, int(self.rows))
    rest = int(self.lip_closed) if self.lip_on else 0
    rest = max(0, min(int(self.cols) - 1, rest))
    nms = _names(self.row_names, n, _tr("표정"))
    items = [(str(r), nms[r], "", _icon(self, r, rest), r)
             for r in range(n)]
    return _stable_items("atr_" + self.uid, items)


def _col_items(self, context):
    n = max(1, int(self.cols))
    src = _row_source((context or bpy.context).scene.fskr, self)
    r = max(0, min(int(self.rows) - 1, _get_val(_rig(), _prop_row(src))))
    nms = _names(self.col_names, n, _tr("입"))
    items = [(str(c), nms[c], "", _icon(self, r, c), c)
             for c in range(n)]
    return _stable_items("atc_%s_%d" % (self.uid, r), items)


def _pick_row_get(self):
    return max(0, min(int(self.rows) - 1, _get_val(_rig(), _prop_row(self))))


def _pick_row_set(self, v):
    _set_val(self, _prop_row(self), v, self.rows)


def _pick_col_get(self):
    return max(0, min(int(self.cols) - 1, _get_val(_rig(), _prop_col(self))))


def _pick_col_set(self, v):
    _set_val(self, _prop_col(self), v, self.cols)


# ----- 칸별 뻐끔 (자유 배치) -----

_FLAP = {}  # uid -> (cols, rows, {(r, c): (닫힘, 반, 열림)}, 기타 칸 항목)


def _cell_ok(v, it):
    r, c = int(v[0]), int(v[1])
    if 0 <= r < int(it.rows) and 0 <= c < int(it.cols):
        return (r, c)
    return None


_STEPS = ("closed", "half", "open")


def _step_xf(e, step):
    """시퀀스 단계의 크기/위치 보정 (가로%, 세로%, X%, Y%). 기본이면 None."""
    kx = float(getattr(e, step + "_sx"))
    ky = float(getattr(e, step + "_sy"))
    px = float(getattr(e, step + "_px"))
    py = float(getattr(e, step + "_py"))
    if (abs(kx - 100.0) < 1e-6 and abs(ky - 100.0) < 1e-6
            and abs(px) < 1e-6 and abs(py) < 1e-6):
        return None
    return (kx, ky, px, py)


def _flap_resolve(e, it):
    """단계별 (칸, 보정). 비어 있는 단계는 다른 단계의 칸을 빌리되,
    크기/위치 보정은 그 단계 자신의 값을 쓴다 (예: 반 = 열림 칸의 세로 50%)."""
    if e.single:  # 단일 입: 말할 때도 기준 칸 그대로
        if e.any_src:
            return ((None, None),) * 3
        s0 = _cell_ok(e.src, it)
        return ((s0, None),) * 3
    cl, hf, op = _cell_ok(e.closed, it), _cell_ok(e.half, it), \
        _cell_ok(e.open, it)
    hf = hf or op or cl
    op = op or hf or cl
    cells = (cl, hf, op)
    return tuple((cells[i], _step_xf(e, s)) if cells[i] is not None
                 else (None, None) for i, s in enumerate(_STEPS))


def _flap_cache(it):
    table = {}
    anyv = None
    for e in it.flaps:
        res = _flap_resolve(e, it)
        if e.any_src:
            anyv = res
        else:
            src = _cell_ok(e.src, it)
            if src is not None:
                table[src] = res
    _FLAP[it.uid] = (max(1, int(it.cols)), max(1, int(it.rows)),
                     table, anyv)


def _flap_cache_all():
    try:
        for sc in bpy.data.scenes:
            s = getattr(sc, "fskr", None)
            if s is None:
                continue
            for it in s.atlases:
                _flap_cache(it)
    except Exception:
        pass


def _flap_update(self, context):
    """짝 변경 → 조회표를 다시 쓰기 위해 적용된 자유 배치 시트 재구성."""
    _flap_cache_all()
    if _SIZE_BUSY[0]:
        return
    try:
        ctx = context or bpy.context
        s = ctx.scene.fskr
        if s.rig is None:
            return
        _SIZE_BUSY[0] = True
        for it in s.atlases:
            if (it.layout == 'FREE'
                    and bpy.data.objects.get(it.target) is not None):
                if not it.built or _is_stale(it):
                    _build(s, it)
                else:
                    _lut_refresh(it)
    except Exception:
        pass
    finally:
        _SIZE_BUSY[0] = False


def _flap_step(m, r, c, t):
    """기준 칸 + 말하기 단계 → (보일 칸 r, c, 단계 보정 또는 None)."""
    cols, rows, table, anyv = m
    r = max(0, min(rows - 1, int(r + 0.5)))
    c = max(0, min(cols - 1, int(c + 0.5)))
    ti = int(t + 0.5)
    if 1 <= ti <= 3:
        e = table.get((r, c), anyv)
        if e is not None and e[ti - 1][0] is not None:
            (r, c), xf = e[ti - 1]
            return r, c, xf
    return r, c, None


def _flap_cell(m, r, c, t):
    """기준 칸 + 말하기 단계 → 실제로 보일 칸 (r, c)."""
    r, c, _xf = _flap_step(m, r, c, t)
    return r, c


def cell_locked(it, e):
    """그 칸의 종횡비 고정 (칸에 따로 정한 값이 없으면 시트 공통 설정)."""
    if e is None or int(getattr(e, "lock", -1)) < 0:
        return bool(it.size_lock)
    return bool(e.lock)


def _cell_entry(it, r, c):
    for e in it.cells:
        if e.r == r and e.c == c:
            return e
    return None


def _cell_params(it, r, c, xf=None):
    """칸 (r, c)의 크기/위치 → (sx, sy, dx, dy). 개별 설정 없으면 공통값.

    xf: 시퀀스 단계 보정 (가로%, 세로%, X%, Y%) — 칸 값에 곱하고 더함.
    """
    cols, rows = max(1, int(it.cols)), max(1, int(it.rows))
    e = _cell_entry(it, r, c)
    if e is not None:
        if cell_locked(it, e):
            wx = wy = float(e.size)
        else:
            wx, wy = float(e.size_x), float(e.size_y)
        nx, ny = float(e.nx), float(e.ny)
    else:
        wx, wy = _size_xy(it)
        nx, ny = float(it.nudge_x), float(it.nudge_y)
    if xf is not None:
        wx *= xf[0] / 100.0
        wy *= xf[1] / 100.0
        nx += xf[2]
        ny += xf[3]
    sx, sy = 100.0 / max(1.0, wx), 100.0 / max(1.0, wy)
    if e is not None and e.flip_x:
        sx = -sx  # 배율 음수 = 칸 중심 기준 좌우 반전
    if e is not None and e.flip_y:
        sy = -sy
    return (sx, sy, nx / 100.0 / cols, ny / 100.0 / rows)


def _cell_src(it, r, c):
    """실제로 그림을 가져올 칸 (반전 칸이면 원본 칸)."""
    e = _cell_entry(it, r, c)
    if e is not None and e.src_r >= 0 and e.src_c >= 0:
        if e.src_r < int(it.rows) and e.src_c < int(it.cols):
            return e.src_r, e.src_c
    return r, c


_LX_ROLES = {   # ④ 입 파츠 칸별 배치 보정: 역할 → (필드, 기본값, 변환)
    'XPX': ("lpx", 0.0, lambda v: -v),
    'XPY': ("lpy", 0.0, lambda v: -v),
    'XR': ("lrot", 0.0, lambda v: -v * 0.0174533),
    'XSX': ("lkx", 1.0, lambda v: 1.0 / max(abs(v), 1e-3)),
    'XSY': ("lky", 1.0, lambda v: 1.0 / max(abs(v), 1e-3)),
    'XOP': ("lop", 1.0, lambda v: v),
    'XCT': ("lct", 0.0, lambda v: v),
    'XCB': ("lcb", 0.0, lambda v: v),
    'XCL': ("lcl", 0.0, lambda v: v),
    'XCR': ("lcr", 0.0, lambda v: v),
}
LX_PREFIX = "FSKR_LX_"


def _role_val(it, role, r, c, xf=None):
    """조회표 값. O=UV Warp 오프셋, S=배율, L=Mapping 위치, C=칸 오프셋."""
    if role in ('XFX', 'XFY'):
        # 시퀀스 단계 위치 보정 (%): 파츠 공간에서 옮김 → 칸 창에 안 잘림
        if not xf:
            return 0.0
        return -float(xf[2 if role == 'XFX' else 3]) / 100.0
    if role in _LX_ROLES:
        f, d, conv = _LX_ROLES[role]
        e = _cell_entry(it, r, c)
        v = float(getattr(e, f)) if e is not None else d
        if xf and role in ('XSX', 'XSY'):
            # 시퀀스 단계 크기 보정 (%): 칸 창 안 확대가 아니라 파츠째로 확대
            v *= float(xf[0 if role == 'XSX' else 1]) / 100.0
        return conv(v)
    if it.method == 'CANVAS':
        xf = None      # 얼굴 캔버스: 단계 보정은 위(파츠 공간)에서 처리
    cols, rows = max(1, int(it.cols)), max(1, int(it.rows))
    cw, ch = 1.0 / cols, 1.0 / rows
    cx, cy = 0.5 * cw, 1.0 - 0.5 * ch
    sr, sc = _cell_src(it, r, c)
    ou, ov = sc * cw, -sr * ch
    if role == 'CU':
        return ou
    if role == 'CV':
        return ov
    sx, sy, dx, dy = _cell_params(it, r, c, xf)
    if role == 'OU':      # UV Warp: uv' = (uv + ofs - center) * s + center
        return ou / sx - dx
    if role == 'OV':
        return ov / sy - dy
    if role == 'SU':
        return sx
    if role == 'SV':
        return sy
    if role == 'LU':      # Mapping: out = in * s + loc
        return ou + cx - (cx + dx) * sx
    if role == 'LV':
        return ov + cy - (cy + dy) * sy
    return 0.0


_K = 8  # 말하기 코드 수: 0 기준칸, 1 닫힘, 2~6 모음 A/I/U/E/O (짝 모드는 1~3)
_VOWEL_CODE = {'_A': 2, '_I': 3, '_U': 4, '_E': 5, '_O': 6, '_N': 2}
_VOWEL_FIELDS = ("lipv_n", "lipv_a", "lipv_i", "lipv_u", "lipv_e", "lipv_o")


def _talk_cell(it, m, r, c, tt):
    """기준 칸 + 말하기 코드 → (보일 칸 r, c, 단계 보정)."""
    if it.layout != 'FREE' or tt <= 0:
        return r, c, None
    return _flap_step(m, r, c, tt if tt <= 3 else 0)


def _seq_step(it, qi, tt):
    """지정된 시퀀스(qi번째)의 단계 tt → (칸 r, c, 보정)."""
    try:
        res = _flap_resolve(it.flaps[qi], it)
    except Exception:
        return 0, 0, None
    k = tt - 1 if 1 <= tt <= 3 else 0
    cell, xf = res[k]
    if cell is None:
        cell, xf = next(((c9, x9) for c9, x9 in res if c9 is not None),
                        ((0, 0), None))
    return cell[0], cell[1], xf


def _lut_role(fc, it, role):
    """드라이버 F-커브를 조회표로: x = 기준칸*8 + 말하기 코드, y = 값.

    보이는 칸은 (자유 배치면) 뻐끔 짝으로 바꾼 칸이고, 그 칸의 개별
    크기/위치가 값에 들어간다. Python 없이 Simple Expression으로 동작.
    """
    _flap_cache(it)
    m = _FLAP[it.uid]
    cols, rows = m[0], m[1]
    free = it.layout == 'FREE'
    for md in list(fc.modifiers):
        fc.modifiers.remove(md)
    pts = fc.keyframe_points
    base_n = rows * cols * _K
    n = base_n + (len(it.flaps) * _K if free else 0)
    if len(pts) != n:
        pts.clear()
        pts.add(n)
    for i in range(n):
        if i >= base_n:  # 지정 시퀀스 영역
            qi, tt = divmod(i - base_n, _K)
            r, c, xf = _seq_step(it, qi, tt)
        else:
            cell, tt = divmod(i, _K)
            r, c, xf = _talk_cell(it, m, cell // cols, cell % cols,
                                  tt if free else 0)
        p = pts[i]
        p.co = (float(i), _role_val(it, role, r, c, xf))
        p.interpolation = 'CONSTANT'
    fc.extrapolation = 'CONSTANT'
    fc.update()


def _role_fcurves(it):
    """이 시트의 조회표 드라이버 F-커브와 역할 목록."""
    out = []
    ob = bpy.data.objects.get(it.target)
    if ob is None:
        return out
    mn = _MOD_PREFIX + it.uid
    ad = ob.animation_data
    if ad is not None:
        for fc in ad.drivers:
            if fc.data_path == 'modifiers["%s"].offset' % mn:
                out.append((fc, ('OU', 'OV')[fc.array_index & 1], ob))
            elif fc.data_path == 'modifiers["%s"].scale' % mn:
                out.append((fc, ('SU', 'SV')[fc.array_index & 1], ob))
    mp_pre = 'nodes["%s%s_' % (_MAP_PREFIX, it.uid)
    ofs_dp = 'nodes["%s%s_ofs"]' % (_MASK_PREFIX, it.uid)
    lx_pre = 'nodes["%s%s_' % (LX_PREFIX, it.uid)
    # 칸별 배치 보정 노드 (캔버스·머리카락 위 복사본 머티리얼 모두)
    for m in bpy.data.materials:
        nad = m.node_tree.animation_data if m.node_tree else None
        if nad is None:
            continue
        for fc in nad.drivers:
            dp = fc.data_path
            if not dp.startswith(lx_pre):
                continue
            kind = dp[len(lx_pre):].split("_", 1)[0]
            if kind == "M":
                out.append((fc, ('XPX', 'XPY')[fc.array_index & 1], m))
            elif kind == "R":
                out.append((fc, 'XR', m))
            elif kind == "S":
                out.append((fc, ('XSX', 'XSY')[fc.array_index & 1], m))
            elif kind in ("OP", "CT", "CB", "CL", "CR"):
                out.append((fc, "X" + kind, m))
            elif kind == "F":
                out.append((fc, ('XFX', 'XFY')[fc.array_index & 1], m))
    for m in _mats(ob):
        nad = m.node_tree.animation_data
        if nad is None:
            continue
        for fc in nad.drivers:
            dp = fc.data_path
            if dp.startswith(mp_pre):
                if dp.endswith("inputs[1].default_value"):
                    out.append((fc, ('LU', 'LV')[fc.array_index & 1], m))
                elif dp.endswith("inputs[3].default_value"):
                    out.append((fc, ('SU', 'SV')[fc.array_index & 1], m))
            elif dp.startswith(ofs_dp):
                out.append((fc, 'CU' if ".inputs[0]." in dp else 'CV', m))
    return out


def _lut_refresh(it):
    """크기/위치/짝이 바뀌면 조회표 값만 다시 쓴다 (재구성 없이 가벼움)."""
    touched = set()
    for fc, role, owner in _role_fcurves(it):
        _lut_role(fc, it, role)
        touched.add(owner)
        try:  # RNA로 드라이버를 건드려 즉시 재계산 (표만 바뀐 경우 대비)
            fc.driver.expression = fc.driver.expression
        except Exception:
            pass
    for owner in touched:
        try:
            if isinstance(owner, bpy.types.Material):
                owner.node_tree.update_tag()
            owner.update_tag()
        except Exception:
            pass
    _poke()
    return len(touched)


def _atl_eval(uid, axis, r, c, t):
    """드라이버 함수: 기준 칸 (r, c) + 말하기 단계 t → UV 오프셋.

    t: 0 = 기준 칸 그대로, 1 = 닫힘, 2 = 반, 3 = 열림 짝으로 교체.
    """
    m = _FLAP.get(uid)
    if m is None:
        _flap_cache_all()
        m = _FLAP.get(uid)
        if m is None:
            return 0.0
    r, c = _flap_cell(m, r, c, t)
    cols, rows = m[0], m[1]
    return (c / cols) if axis == 0 else (-r / rows)


def _atl_ns_install():
    try:
        bpy.app.driver_namespace["fskr_atl"] = _atl_eval
    except Exception:
        pass


@bpy.app.handlers.persistent
def _pv_clear_on_frame(scene, *_args):
    """프레임이 실제로 바뀌면 미리보기를 끈다 (재생/렌더에 남지 않게).

    같은 프레임으로 다시 설정되는 경우(립싱크 편집기 동기화 등)는 유지.
    """
    try:
        f0 = _PV_STATE.get("frame")
        if f0 is None or int(scene.frame_current) == int(f0):
            return
        _PV_STATE["frame"] = None
        s = scene.fskr
        rig = s.rig
        if rig is None:
            return
        hit = False
        for it in s.atlases:
            if getattr(it, "edit_on", False):
                continue          # 편집 모드는 프레임을 옮겨도 유지
            for k in "rctq":
                p = _prop_pv(it, k)
                if p in rig.keys() and _get_val(rig, p) >= 0:
                    rig[p] = -1
                    hit = True
        if hit:
            rig.update_tag()
            for it in s.atlases:
                ob = bpy.data.objects.get(it.target)
                if ob is not None:
                    ob.update_tag()
    except Exception:
        pass


def _drivers_revive():
    """오류로 멈춘(무효 표시된) 스프라이트 드라이버를 다시 켠다."""
    def fix(ad):
        if ad is None:
            return
        for fc in ad.drivers:
            dp = fc.data_path
            if (_MOD_PREFIX in dp or _MAP_PREFIX in dp
                    or _MASK_PREFIX in dp):
                try:
                    fc.driver.is_valid = True
                    fc.driver.expression = fc.driver.expression
                except Exception:
                    pass
    try:
        for ob in bpy.data.objects:
            fix(ob.animation_data)
        for m in bpy.data.materials:
            if m.node_tree is not None:
                fix(m.node_tree.animation_data)
    except Exception:
        pass


@bpy.app.handlers.persistent
def pct_migrate(force=False):
    """④ 입 파츠의 칸별 % 크기·위치(칸 창 안에서 확대 → 창 밖은 잘림)를
    칸별 배치(창째로 확대 → 잘리지 않음)로 옮긴다. 보이는 크기·위치는 같다."""
    try:
        s = bpy.context.scene.fskr
    except Exception:
        return 0
    used = set()
    for st in s.eyes:
        for L in st.layers:
            if getattr(L, "kind", 'PART') == 'MOUTH' and L.atlas:
                used.add(L.atlas)
    n = 0
    for it in s.atlases:
        if it.uid not in used or (it.get("pct_mig") and not force):
            continue
        gx, gy = _size_xy(it)
        for e in it.cells:
            if cell_locked(it, e):
                wx = wy = float(e.size)
            else:
                wx, wy = float(e.size_x), float(e.size_y)
            fx, fy = wx / max(gx, 1e-6), wy / max(gy, 1e-6)
            if abs(fx - 1.0) < 1e-4 and abs(fy - 1.0) < 1e-4:
                continue
            e.lkx = float(e.lkx) * fx
            e.lky = float(e.lky) * fy
            # 창이 커진 만큼 창 안 위치 보정은 줄여야 화면 위치가 같음
            e.nx = it.nudge_x + (e.nx - it.nudge_x) / max(fx, 1e-6)
            e.ny = it.nudge_y + (e.ny - it.nudge_y) / max(fy, 1e-6)
            e.size = gx
            e.size_x, e.size_y = gx, gy
            e.lock = -1
            n += 1
        it["pct_mig"] = 1
        if n:
            k = 0
            try:
                k = _lut_refresh(it)
            except Exception:
                pass
            if not k:   # 칸별 배치 노드가 아직 없는 머티리얼 → 다시 만들기
                try:
                    from .eye import eye_build, _layer_atlas
                    for st in s.eyes:
                        if any(_layer_atlas(s, L) is it for L in st.layers):
                            eye_build(s, st)
                except Exception as e:
                    print("FSKR pct rebuild:", e)
    return n


def _atl_on_load(*_args):
    _atl_ns_install()
    _flap_cache_all()
    _drivers_revive()
    try:
        bpy.app.timers.register(_mig_tick, first_interval=0.6)
    except Exception:
        pass


def step_node_migrate():
    """1.0.197: 시퀀스 단계 크기/위치를 파츠 공간 노드(XF)로 → 없으면 재구성."""
    try:
        s = bpy.context.scene.fskr
        from .eye import eye_build, _layer_atlas
    except Exception:
        return 0
    n = 0
    for st in s.eyes:
        its = [_layer_atlas(s, L) for L in st.layers]
        its = [it for it in its if it is not None]
        if not its:
            continue
        need = False
        for it in its:
            if not any(r in ('XFX', 'XFY') for _f, r, _o in _role_fcurves(it)):
                need = True
                break
        if need:
            try:
                eye_build(s, st)
                n += 1
            except Exception as e:
                print("FSKR step rebuild:", e)
    return n


def _mig_tick():
    try:
        n = pct_migrate()
        if n:
            print("FSKR: %d mouth cells moved to per-cell placement" % n)
    except Exception as e:
        print("FSKR pct migrate:", e)
    try:
        step_node_migrate()
    except Exception as e:
        print("FSKR step migrate:", e)
    return None


def _revive_tick():
    _drivers_revive()
    _mig_tick()
    return None


def atlas_register():
    _atl_ns_install()
    _flap_cache_all()
    app_handler_add(bpy.app.handlers.frame_change_pre, _pv_clear_on_frame)
    try:
        bpy.app.timers.register(_revive_tick, first_interval=0.3)
    except Exception:
        pass
    app_handler_add(bpy.app.handlers.load_post, _atl_on_load)


def atlas_unregister():
    if _pv_clear_on_frame in bpy.app.handlers.frame_change_pre:
        bpy.app.handlers.frame_change_pre.remove(_pv_clear_on_frame)
    if _atl_on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_atl_on_load)
    bpy.app.driver_namespace.pop("fskr_atl", None)
    _thumbs_free_all()


def _cell_label(it, r, c):
    return "%d-%d" % (r, c)


def _cell_items(self, context):
    rows, cols = max(1, int(self.rows)), max(1, int(self.cols))
    fl = _PREV_FILLED.get(self.uid)
    items = []
    for r in range(rows):
        for c in range(cols):
            if fl and not fl.get((r, c), True):
                continue  # 빈 칸은 목록에서 생략
            items.append((str(r * cols + c), _cell_label(self, r, c), "",
                          _icon(self, r, c), r * cols + c))
    if not items:
        items = [("0", "0-0", "", 0, 0)]
    return _stable_items("atx_" + self.uid, items)


def _pick_cell_get(self):
    rig = _rig()
    cols = max(1, int(self.cols))
    if getattr(self, "edit_on", False):   # 편집 모드: 고정해 둔 칸
        r, c = _cur_cell(self)
        return r * cols + c
    return (_pick_row_get(self) * cols
            + max(0, min(cols - 1, _get_val(rig, _prop_col(self)))))


def _pe_on():
    try:
        from .eye import preset_editing
        return preset_editing()
    except Exception:
        return False


def edit_show(it, r, c):
    """편집 모드: 키프레임과 상관없이 (r, c) 칸을 고정해서 보여 줌 (키 없음)."""
    rig = _rig()
    if rig is None:
        return
    _pv_set(rig, it, r=r, c=c, tcode=0, q=0)
    _PV_STATE["frame"] = None     # 프레임을 옮겨도 유지
    ob = bpy.data.objects.get(it.target)
    if ob is not None:
        ob.update_tag()


def _edit_on_update(self, context):
    rig = _rig()
    if rig is None:
        return
    if self.edit_on:
        r = _get_val(rig, _prop_row(_row_source(context.scene.fskr, self)))
        c = _get_val(rig, _prop_col(self))
        edit_show(self, max(0, min(int(self.rows) - 1, r)),
                  max(0, min(int(self.cols) - 1, c)))
    else:
        _pv_set(rig, self)
    _redraw_ui(context)


def _pick_cell_set(self, v):
    cols = max(1, int(self.cols))
    rig = _rig()
    if rig is None:
        return
    if getattr(self, "edit_on", False) and not _pe_on():
        edit_show(self, v // cols, v % cols)
        return
    key = _autokey_on(self)
    _set_val(self, _prop_row(self), v // cols, self.rows, key=key)
    _set_val(self, _prop_col(self), v % cols, self.cols, key=key)


_NONE_NUM = 99999


def _owner_atlas(self):
    """시퀀스 항목/시트 → 소속 시트."""
    if hasattr(self, "flaps"):
        return self
    try:
        m = re.search(r"atlases\[(\d+)\]", self.path_from_id())
        return self.id_data.fskr.atlases[int(m.group(1))]
    except Exception:
        return None


def _mk_cellpick(field, allow_none):
    """(행, 열) 필드를 썸네일로 고르는 EnumProperty (get/set/items)."""
    def items(self, context):
        it = _owner_atlas(self)
        if it is None:
            return [("NONE", "-", "", 0, _NONE_NUM)]
        base = list(_cell_items(it, context))
        if allow_none:
            base = [("NONE", _tr("없음 (-1)"), "", 0, _NONE_NUM)] + base
        return _stable_items("cp%d_%s" % (int(allow_none), it.uid), base)

    def get(self):
        it = _owner_atlas(self)
        if it is None:
            return _NONE_NUM
        cols = max(1, int(it.cols))
        v = getattr(self, field)
        ids = [int(i[4]) for i in items(self, None)]
        if min(v) >= 0:
            n = int(v[0]) * cols + int(v[1])
            if n in ids:
                return n
        if allow_none or not ids:
            return _NONE_NUM if allow_none else 0
        return ids[0]

    def set_(self, n):
        it = _owner_atlas(self)
        if it is None:
            return
        cols = max(1, int(it.cols))
        if n == _NONE_NUM:
            setattr(self, field, (-1, -1))
        else:
            setattr(self, field, (n // cols, n % cols))
    return items, get, set_


def _cellpick_prop(field, allow_none, name):
    i, g, s = _mk_cellpick(field, allow_none)
    return bpy.props.EnumProperty(name=name, items=i, get=g, set=s,
                                  description="썸네일에서 칸을 고릅니다")


_SINGLE_FIELD = {"size": "tex_size", "size_x": "tex_size_x",
                 "size_y": "tex_size_y", "nx": "nudge_x", "ny": "nudge_y"}


def _mk_single(field):
    """단일 입: 표정 칸(src) 자신의 크기/위치를 읽고 쓰는 프록시."""
    def get(self):
        it = _owner_atlas(self)
        src = _cell_ok(self.src, it) if it is not None else None
        if src is None:
            return 100.0 if field.startswith("size") else 0.0
        e = _cell_entry(it, *src)
        if e is not None:
            return float(getattr(e, field))
        return float(getattr(it, _SINGLE_FIELD[field]))

    def set_(self, v):
        it = _owner_atlas(self)
        src = _cell_ok(self.src, it) if it is not None else None
        if src is None:
            return
        e = _cell_entry(it, *src)
        if e is None:
            e = it.cells.add()
            e.r, e.c = src
            for f9, g9 in _SINGLE_FIELD.items():
                setattr(e, f9, getattr(it, g9))
        setattr(e, field, v)
        if field == "size":
            e.size_x = e.size_y = v
        try:
            rig = _rig()
            if rig is not None:
                _pv_set(rig, it, src[0], src[1], 3)  # 말하는 중 미리보기
        except Exception:
            pass
        _size_update(it, None)
    return get, set_


def _single_prop(field, name, pct_size):
    g, s = _mk_single(field)
    if pct_size:
        return bpy.props.FloatProperty(
            name=name, min=10.0, max=400.0, subtype='PERCENTAGE',
            precision=0, get=g, set=s)
    return bpy.props.FloatProperty(
        name=name, soft_min=-50.0, soft_max=50.0, subtype='PERCENTAGE',
        precision=0, get=g, set=s)


def _mk_stepsize(step):
    """종횡비 고정 시: 한 값으로 가로·세로를 같이."""
    def get(self):
        return float(getattr(self, step + "_sx"))

    def set_(self, v):
        self[step + "_sx"] = float(v)
        self[step + "_sy"] = float(v)
        _step_update(self, bpy.context, step)
    return get, set_


def _stepsize_prop(step):
    g, s = _mk_stepsize(step)
    return bpy.props.FloatProperty(
        name="크기", min=5.0, max=400.0, subtype='PERCENTAGE', precision=0,
        get=g, set=s)


def _xf_lock_update(self, context):
    """고정을 켜면 각 단계의 세로를 가로에 맞춘다."""
    if self.xf_lock:
        for st in _STEPS:
            self[st + "_sy"] = float(getattr(self, st + "_sx"))
        _flap_update(self, context)


class FSKR_AtlasFlap(bpy.types.PropertyGroup):
    """자유 배치: 기준 칸 → 말할 때 번갈아 쓸 닫힘/반/열림 칸."""
    name: bpy.props.StringProperty(
        name="이름", default="", update=lambda s, c: _vp_auto(s))
    any_src: bpy.props.BoolProperty(
        name="이 시퀀스를 메인으로 사용", default=False,
        update=lambda s, c: _main_update(s, c),
        description="어떤 표정에서 말하든 이 시퀀스의 입을 씁니다 "
                    "(전용 시퀀스가 있는 표정만 예외). 메인은 하나만 가능")
    src: bpy.props.IntVectorProperty(
        name="기준 칸", size=2, default=(0, 0), min=0, update=_flap_update,
        description="이 칸이 표정으로 선택되어 있을 때 (행, 열)")
    closed: bpy.props.IntVectorProperty(
        name="닫힘", size=2, default=(-1, -1), min=-1, update=_flap_update,
        description="작게 벌린 칸 (행, 열). -1 = 기준 칸 그대로")
    half: bpy.props.IntVectorProperty(
        name="반 열림", size=2, default=(-1, -1), min=-1,
        update=_flap_update,
        description="중간 칸 (행, 열). -1 = 열림 칸 사용")
    open: bpy.props.IntVectorProperty(
        name="열림", size=2, default=(-1, -1), min=-1, update=_flap_update,
        description="크게 벌린 칸 (행, 열). -1 = 반 열림 칸 사용")
    show_vp: bpy.props.BoolProperty(
        name="뷰포트 리그에 표시", default=False,
        update=lambda s, c: _vp_auto(s),
        description="뷰포트 컨트롤러의 격자 아래에 이 시퀀스 전용 슬라이더를 "
                    "추가합니다 (닫힘/반/열림, 단일 입이면 끔/켬). 메인 "
                    "시퀀스는 항상 표시됩니다")
    single: bpy.props.BoolProperty(
        name="단일 입", default=False,
        update=lambda s, c: (_flap_update(s, c), _vp_auto(s)),
        description="말할 때도 이 입을 그대로 둡니다 (뻐끔거리지 않음). "
                    "'나머지 표정 전부'의 입으로 바뀌지 않게 할 때 사용")
    cur_single_size: _single_prop("size", "크기", True)
    cur_single_sx: _single_prop("size_x", "가로", True)
    cur_single_sy: _single_prop("size_y", "세로", True)
    cur_single_px: _single_prop("nx", "X", False)
    cur_single_py: _single_prop("ny", "Y", False)
    xf_lock: bpy.props.BoolProperty(
        name="종횡비 고정", default=False, update=_xf_lock_update,
        description="켜면 크기 하나로 가로·세로를 같이, 끄면 따로 조절")
    cur_sz_closed: _stepsize_prop("closed")
    cur_sz_half: _stepsize_prop("half")
    cur_sz_open: _stepsize_prop("open")
    xf_step: bpy.props.EnumProperty(
        name="단계", default='half',
        items=(('closed', "닫힘", ""), ('half', "반", ""),
               ('open', "열림", "")))
    show_xf: bpy.props.BoolProperty(
        name="단계 크기/위치", default=False,
        description="닫힘/반/열림 단계마다 칸의 크기와 위치를 따로 보정")
    closed_sx: bpy.props.FloatProperty(
        name="가로", default=100.0, min=5.0, max=400.0, subtype='PERCENTAGE',
        precision=0, update=lambda s_, c_: _step_update(s_, c_, 'closed'))
    closed_sy: bpy.props.FloatProperty(
        name="세로", default=100.0, min=5.0, max=400.0, subtype='PERCENTAGE',
        precision=0, update=lambda s_, c_: _step_update(s_, c_, 'closed'))
    closed_px: bpy.props.FloatProperty(
        name="X", default=0.0, soft_min=-50.0, soft_max=50.0,
        subtype='PERCENTAGE', precision=0, update=lambda s_, c_: _step_update(s_, c_, 'closed'))
    closed_py: bpy.props.FloatProperty(
        name="Y", default=0.0, soft_min=-50.0, soft_max=50.0,
        subtype='PERCENTAGE', precision=0, update=lambda s_, c_: _step_update(s_, c_, 'closed'))
    half_sx: bpy.props.FloatProperty(
        name="가로", default=100.0, min=5.0, max=400.0, subtype='PERCENTAGE',
        precision=0, update=lambda s_, c_: _step_update(s_, c_, 'half'))
    half_sy: bpy.props.FloatProperty(
        name="세로", default=100.0, min=5.0, max=400.0, subtype='PERCENTAGE',
        precision=0, update=lambda s_, c_: _step_update(s_, c_, 'half'))
    half_px: bpy.props.FloatProperty(
        name="X", default=0.0, soft_min=-50.0, soft_max=50.0,
        subtype='PERCENTAGE', precision=0, update=lambda s_, c_: _step_update(s_, c_, 'half'))
    half_py: bpy.props.FloatProperty(
        name="Y", default=0.0, soft_min=-50.0, soft_max=50.0,
        subtype='PERCENTAGE', precision=0, update=lambda s_, c_: _step_update(s_, c_, 'half'))
    open_sx: bpy.props.FloatProperty(
        name="가로", default=100.0, min=5.0, max=400.0, subtype='PERCENTAGE',
        precision=0, update=lambda s_, c_: _step_update(s_, c_, 'open'))
    open_sy: bpy.props.FloatProperty(
        name="세로", default=100.0, min=5.0, max=400.0, subtype='PERCENTAGE',
        precision=0, update=lambda s_, c_: _step_update(s_, c_, 'open'))
    open_px: bpy.props.FloatProperty(
        name="X", default=0.0, soft_min=-50.0, soft_max=50.0,
        subtype='PERCENTAGE', precision=0, update=lambda s_, c_: _step_update(s_, c_, 'open'))
    open_py: bpy.props.FloatProperty(
        name="Y", default=0.0, soft_min=-50.0, soft_max=50.0,
        subtype='PERCENTAGE', precision=0, update=lambda s_, c_: _step_update(s_, c_, 'open'))
    pick_src: _cellpick_prop("src", False, "기준 칸")
    pick_closed: _cellpick_prop("closed", True, "닫힘")
    pick_half: _cellpick_prop("half", True, "반 열림")
    pick_open: _cellpick_prop("open", True, "열림")


_SIZE_BUSY = [False]


def _main_update(self, context):
    """메인 시퀀스는 하나만: 켜면 다른 시퀀스의 메인을 끈다."""
    if self.any_src:
        it = _owner_atlas(self)
        if it is not None:
            for f in it.flaps:
                if f != self and f.any_src:
                    f["any_src"] = False  # 업데이트 재귀 없이 끄기
    _flap_update(self, context)
    _vp_auto(self)


def _vp_auto(flap):
    """뷰포트 컨트롤러가 있으면 시퀀스 변경을 바로 반영 (갱신 버튼 없이)."""
    try:
        from .atlas_vp import vp_schedule
        it = _owner_atlas(flap)
        if it is not None:
            vp_schedule(it.uid)
    except Exception as e:
        print("FSKR vp auto:", e)


_STEP_CODE = {"closed": 1, "half": 2, "open": 3}


def _step_update(self, context, step):
    """단계 크기/위치를 만지면 그 단계를 자동으로 미리보기."""
    try:
        it = _owner_atlas(self)
        rig = _rig()
        if it is not None and rig is not None:
            src = None if self.any_src else _cell_ok(self.src, it)
            code = {"closed": 1, "half": 2, "open": 3}[step]
            qi = next((i + 1 for i, f in enumerate(it.flaps)
                       if f == self), None)
            _pv_set(rig, it, src[0] if src else None,
                    src[1] if src else None, code, qi)
    except Exception:
        pass
    _flap_update(self, context)


def _switching():
    try:
        from .core import _SWITCH
        return bool(_SWITCH.get("busy"))
    except Exception:
        return False


def _size_update(self, context):
    """크기/위치 변경 → 조회표 갱신. 예전 구조면 자동으로 재구성."""
    if _SIZE_BUSY[0] or not self.uid or _switching():
        return
    try:
        s = (context or bpy.context).scene.fskr
        if s.rig is None or bpy.data.objects.get(self.target) is None:
            return
        _SIZE_BUSY[0] = True
        if not self.built or _is_stale(self):
            _build(s, self)  # 적용 안 된 시트 → 자동 적용
        else:
            _lut_refresh(self)
    except Exception as e:
        print("FSKR size:", e)
    finally:
        _SIZE_BUSY[0] = False


def _lock_update(self, context):
    """고정을 끄면 현재 크기에서 가로/세로를 시작, 켜면 가로 값으로 통일."""
    if _SIZE_BUSY[0]:
        return
    _SIZE_BUSY[0] = True
    try:
        # 칸마다 따로 정한 고정(lock >= 0)은 건드리지 않음
        if self.size_lock:
            self.tex_size = self.tex_size_x
            for e in self.cells:
                if e.lock < 0:
                    e.size = e.size_x
        else:
            self.tex_size_x = self.tex_size
            self.tex_size_y = self.tex_size
            for e in self.cells:
                if e.lock < 0:
                    e.size_x = e.size_y = e.size
    finally:
        _SIZE_BUSY[0] = False
    _size_update(self, context)


def _size_xy(it):
    if it.size_lock:
        return float(it.tex_size), float(it.tex_size)
    return float(it.tex_size_x), float(it.tex_size_y)


_PROXY_GLOBAL = {"size": "tex_size", "size_x": "tex_size_x",
                 "size_y": "tex_size_y", "nx": "nudge_x", "ny": "nudge_y"}


def _cur_cell(it):
    """슬라이더가 편집할 칸 = 지금 선택된 표정(기준) 칸."""
    try:
        s = bpy.context.scene.fskr
        src = _row_source(s, it)
    except Exception:
        src = it
    rig = _rig()
    r = _get_val(rig, _prop_row(src))
    c = _get_val(rig, _prop_col(it))
    if rig is not None and _prop_pv(it, "r") in rig.keys():
        pr, pc = _get_val(rig, _prop_pv(it, "r")), _get_val(rig, _prop_pv(it, "c"))
        if pr >= 0:
            r = pr
        if pc >= 0:
            c = pc
    r = max(0, min(int(it.rows) - 1, r))
    c = max(0, min(int(it.cols) - 1, c))
    return r, c


# ----- 여러 칸 함께 조절 -----

def cells_msel(it):
    """함께 조절하려고 체크한 칸 {(r, c)}."""
    try:
        return {tuple(x) for x in json.loads(it.get("msel", "[]") or "[]")}
    except Exception:
        return set()


def cells_msel_set(it, cells):
    it["msel"] = json.dumps(sorted([list(x) for x in cells]))


def _msel_others(it, cur):
    return [rc for rc in sorted(cells_msel(it)) if rc != tuple(cur)]


def cell_transformed(it, r, c):
    """그 칸에 이미 따로 바꿔 둔 값 (설명 목록). 공통값 그대로면 빈 목록."""
    e = _cell_entry(it, r, c)
    if e is None:
        return []
    out = []
    gx, gy = _size_xy(it)
    if cell_locked(it, e):
        if abs(e.size - gx) > 0.05:
            out.append(_tr("크기") + " %.0f%%" % e.size)
    else:
        if abs(e.size_x - gx) > 0.05:
            out.append(_tr("가로") + " %.0f%%" % e.size_x)
        if abs(e.size_y - gy) > 0.05:
            out.append(_tr("세로") + " %.0f%%" % e.size_y)
    if abs(e.nx - it.nudge_x) > 0.05 or abs(e.ny - it.nudge_y) > 0.05:
        out.append(_tr("위치") + " (%.0f, %.0f)" % (e.nx, e.ny))
    if e.flip_x or e.flip_y:
        out.append(_tr("반전"))
    if e.src_r >= 0 and e.src_c >= 0:
        out.append(_tr("다른 칸 그림"))
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
    if lx:
        out.append(_tr("칸별 배치") + ": " + "/".join(lx))
    return out


def _mk_proxy(field):
    gname = _PROXY_GLOBAL[field]

    def get(self):
        e = _cell_entry(self, *_cur_cell(self))
        if e is not None:
            return float(getattr(e, field))
        return float(getattr(self, gname))

    def set_(self, v):
        if True:  # 항상 지금 칸에만 저장 (토글 혼동 방지로 1.0.51부터 고정)
            r, c = _cur_cell(self)
            old = get(self)
            e = _cell_entry(self, r, c)
            if e is None:
                e = self.cells.add()
                e.r, e.c = r, c
                for f9, g9 in _PROXY_GLOBAL.items():
                    setattr(e, f9, getattr(self, g9))
            setattr(e, field, v)
            if field == "size":
                e.size_x = e.size_y = v
            # 함께 조절하는 칸: 크기는 같은 비율, 위치는 움직인 만큼
            for rc in _msel_others(self, (r, c)):
                e2 = _cell_ensure(self, *rc)
                if field.startswith("size"):
                    k = (v / old) if abs(old) > 1e-6 else 1.0
                    nv = max(1.0, float(getattr(e2, field)) * k)
                    setattr(e2, field, nv)
                    if field == "size":
                        e2.size_x = e2.size_y = nv
                else:
                    setattr(e2, field, float(getattr(e2, field)) + (v - old))
            _size_update(self, None)
    return get, set_


def _cell_ensure(it, r, c):
    e = _cell_entry(it, r, c)
    if e is None:
        e = it.cells.add()
        e.r, e.c = r, c
        for f9, g9 in _PROXY_GLOBAL.items():
            setattr(e, f9, getattr(it, g9))
    return e


def _cur_lock_get(self):
    return cell_locked(self, _cell_entry(self, *_cur_cell(self)))


def _cur_lock_set(self, v):
    v = bool(v)
    cur = _cur_cell(self)
    for rc in [tuple(cur)] + _msel_others(self, cur):
        e = _cell_ensure(self, *rc)
        if cell_locked(self, e) != v:
            if v:
                e.size = e.size_x          # 켜면 가로 값으로 통일
            else:
                e.size_x = e.size_y = e.size
        e.lock = 1 if v else 0
    _size_update(self, None)


def _mk_flip(field):
    def get(self):
        e = _cell_entry(self, *_cur_cell(self))
        return bool(getattr(e, field)) if e is not None else False

    def set_(self, v):
        cur = _cur_cell(self)
        e = _cell_ensure(self, *cur)
        setattr(e, field, bool(v))
        for rc in _msel_others(self, cur):
            setattr(_cell_ensure(self, *rc), field, bool(v))
        _size_update(self, None)
        _thumbs_request(self)
    return get, set_


class FSKR_AtlasCellXf(bpy.types.PropertyGroup):
    """칸별 그림 크기/위치 (없는 칸은 시트 공통값 사용)."""
    r: bpy.props.IntProperty(default=0)
    c: bpy.props.IntProperty(default=0)
    size: bpy.props.FloatProperty(default=100.0)
    size_x: bpy.props.FloatProperty(default=100.0)
    size_y: bpy.props.FloatProperty(default=100.0)
    nx: bpy.props.FloatProperty(default=0.0)
    ny: bpy.props.FloatProperty(default=0.0)
    # 반전 칸: 이 칸 자리에 다른 칸(src)의 그림을 뒤집어 보여 줌
    src_r: bpy.props.IntProperty(default=-1)
    src_c: bpy.props.IntProperty(default=-1)
    flip_x: bpy.props.BoolProperty(default=False)
    flip_y: bpy.props.BoolProperty(default=False)
    # 칸별 종횡비 고정: -1 = 시트 공통 설정 따름, 0 = 끔, 1 = 켬
    lock: bpy.props.IntProperty(default=-1, min=-1, max=1)
    # ④ 입 파츠 배치의 칸별 보정 (파츠 공통 배치에 더하거나 곱함)
    lpx: bpy.props.FloatProperty(default=0.0)
    lpy: bpy.props.FloatProperty(default=0.0)
    lrot: bpy.props.FloatProperty(default=0.0)
    lkx: bpy.props.FloatProperty(default=1.0)
    lky: bpy.props.FloatProperty(default=1.0)
    lop: bpy.props.FloatProperty(default=1.0)
    lct: bpy.props.FloatProperty(default=0.0)
    lcb: bpy.props.FloatProperty(default=0.0)
    lcl: bpy.props.FloatProperty(default=0.0)
    lcr: bpy.props.FloatProperty(default=0.0)
    llock: bpy.props.IntProperty(default=-1, min=-1, max=1)


def _per_cell_update(self, context):
    _size_update(self, context)


LAYOUT_ITEMS = (('GRID', "격자 (행=표정, 열=입)",
                 "립싱크가 열만 바꿉니다. 표정마다 닫힘/반/열림을 가로로 배치"),
                ('FREE', "자유 배치",
                 "칸 하나를 표정으로 고르고, 말할 때 입은 모음 또는 "
                 "시퀀스로 지정합니다"))


LIP_MODE_ITEMS = (('OPEN', "벌림 3단계", "음량으로 닫힘/반 열림/열림 전환"),
                  ('VOWEL', "모음 (A/I/U/E/O)", "모음별로 다른 칸"))
METHOD_ITEMS = (('UVWARP', "UV Warp 모디파이어",
                 "데칼 오브젝트용. 머티리얼을 건드리지 않음"),
                ('MAPPING', "머티리얼 Mapping 노드",
                 "이미지 텍스처 앞에 Mapping 노드를 넣어 이동"),
                ('CANVAS', "얼굴 캔버스 레이어",
                 "얼굴 캔버스의 '입' 레이어로 그립니다. 모디파이어/노드를 "
                 "따로 만들지 않고 캔버스 머티리얼이 이 시트를 읽습니다"))


def _link_ids(self):
    s = bpy.context.scene.fskr
    return [""] + [a.uid for a in s.atlases if a.uid != self.uid]


def _link_items(self, context):
    s = (context or bpy.context).scene.fskr
    items = [("__SELF__", _tr("(자체 행)"), "", 0, 0)]
    for i, a in enumerate([a for a in s.atlases if a.uid != self.uid]):
        items.append((a.uid, a.name, "", 0, i + 1))
    return _stable_items("atl_" + self.uid, items)


def _link_get(self):
    ids = _link_ids(self)
    return ids.index(self.row_link) if self.row_link in ids else 0


def _link_set(self, v):
    ids = _link_ids(self)
    self.row_link = ids[v] if 0 <= v < len(ids) else ""


def _atlas_name_cb(self, context):
    """시트 이름을 바꾸면 뷰포트 컨트롤러 제목도 바로."""
    try:
        from .eye import sync_prop_names
        sync_prop_names(context.scene.fskr)
    except Exception as e:
        print("FSKR prop rename:", e)
    ob = bpy.data.objects.get("FPLBL_spr_" + self.uid)
    if ob is not None and ob.type == 'FONT' and ob.data.body != self.name:
        ob.data.body = self.name
        try:
            from .atlas_vp import _lbl_font
            _lbl_font(ob.data)
        except Exception:
            pass


class FSKR_AtlasItem(bpy.types.PropertyGroup):
    uid: bpy.props.StringProperty(default="")
    pkey: bpy.props.StringProperty(default="")   # 리그 프로퍼티 이름 앞부분
    name: bpy.props.StringProperty(name="이름", default="입",
                                   update=_atlas_name_cb)
    target: bpy.props.StringProperty(
        name="대상 오브젝트",
        description="칸이 바뀔 오브젝트 (입 데칼, 범고래 얼굴 등)")
    image: bpy.props.StringProperty(
        name="이미지", description="격자로 그린 스프라이트 시트 이미지")
    method: bpy.props.EnumProperty(name="방식", items=METHOD_ITEMS,
                                   default='UVWARP')
    uv_map: bpy.props.StringProperty(
        name="UV 맵", description="비우면 활성 UV 맵")
    vgroup: bpy.props.StringProperty(
        name="버텍스 그룹",
        description="UV Warp를 이 그룹에만 적용 (얼굴 메시 일부일 때)")
    cols: bpy.props.IntProperty(name="열 (가로 칸 수)", default=4,
                                min=1, max=64)
    rows: bpy.props.IntProperty(name="행 (세로 칸 수)", default=4,
                                min=1, max=64)
    row_names: bpy.props.StringProperty(
        name="행 이름", description="쉼표로 구분 (예: 기본, 화남, 반짝, 당황)")
    col_names: bpy.props.StringProperty(
        name="열 이름", description="쉼표로 구분 (예: 닫힘, 반, 열림)")
    row_link: bpy.props.StringProperty(default="")
    row_link_pick: bpy.props.EnumProperty(
        name="행 따라가기", items=_link_items, get=_link_get, set=_link_set,
        description="다른 스프라이트 시트의 행(표정)을 그대로 따라갑니다. "
                    "얼굴 표정과 범고래 표정을 한 번에 바꿀 때 사용")
    layout: bpy.props.EnumProperty(name="배치 방식", items=LAYOUT_ITEMS,
                                   default='GRID')
    flaps: bpy.props.CollectionProperty(type=FSKR_AtlasFlap)
    free_lip: bpy.props.EnumProperty(
        name="말할 때 입", default='VOWEL',
        items=(('VOWEL', "모음 (A/I/U/E/O)",
                "드라이버 방식처럼 모음마다 지정한 입 칸으로 바뀝니다", 0),
               ('FLAP', "시퀀스",
                "표정 칸마다 닫힘/반/열림 칸 시퀀스를 번갈아 씁니다", 1)),
        update=lambda s, c: _size_update(s, c))
    lipv_n: bpy.props.IntVectorProperty(
        name="닫힘", size=2, default=(-1, -1), min=-1,
        update=lambda s, c: _size_update(s, c),
        description="말하는 중 소리가 작을 때 (행, 열). -1 = 표정 칸 그대로")
    lipv_a: bpy.props.IntVectorProperty(
        name="A", size=2, default=(-1, -1), min=-1,
        update=lambda s, c: _size_update(s, c), description="아 (행, 열)")
    lipv_i: bpy.props.IntVectorProperty(
        name="I", size=2, default=(-1, -1), min=-1,
        update=lambda s, c: _size_update(s, c), description="이 (행, 열)")
    lipv_u: bpy.props.IntVectorProperty(
        name="U", size=2, default=(-1, -1), min=-1,
        update=lambda s, c: _size_update(s, c), description="우 (행, 열)")
    lipv_e: bpy.props.IntVectorProperty(
        name="E", size=2, default=(-1, -1), min=-1,
        update=lambda s, c: _size_update(s, c), description="에 (행, 열)")
    lipv_o: bpy.props.IntVectorProperty(
        name="O", size=2, default=(-1, -1), min=-1,
        update=lambda s, c: _size_update(s, c), description="오 (행, 열)")
    pick_lipv_n: _cellpick_prop("lipv_n", True, "닫힘")
    pick_lipv_a: _cellpick_prop("lipv_a", True, "A")
    pick_lipv_i: _cellpick_prop("lipv_i", True, "I")
    pick_lipv_u: _cellpick_prop("lipv_u", True, "U")
    pick_lipv_e: _cellpick_prop("lipv_e", True, "E")
    pick_lipv_o: _cellpick_prop("lipv_o", True, "O")
    show_flaps: bpy.props.BoolProperty(default=True)
    msel_open: bpy.props.BoolProperty(
        name="일괄 조절", default=False,
        description="칸 썸네일 격자를 펼쳐 일괄 조절할 칸을 고릅니다")
    pick_cell: bpy.props.EnumProperty(
        name="칸", items=_cell_items, get=_pick_cell_get, set=_pick_cell_set)
    built: bpy.props.StringProperty(default="")  # 마지막 적용 JSON
    tex_size: bpy.props.FloatProperty(
        name="그림 크기", default=100.0, min=10.0, max=400.0,
        subtype='PERCENTAGE', precision=0, update=_size_update,
        description="데칼 위에서 그림이 보이는 크기. 줄여도 옆 칸이 "
                    "침범하지 않습니다 (칸 밖은 투명 처리). 투명 배경 "
                    "설정이 되어 있어야 잘림이 적용됩니다")
    size_lock: bpy.props.BoolProperty(
        name="종횡비 고정", default=True, update=_lock_update,
        description="켜면 크기 하나로 가로·세로를 같이, 끄면 따로 조절")
    tex_size_x: bpy.props.FloatProperty(
        name="가로", default=100.0, min=10.0, max=400.0,
        subtype='PERCENTAGE', precision=0, update=_size_update,
        description="그림 가로 크기 (종횡비 고정을 끈 경우)")
    tex_size_y: bpy.props.FloatProperty(
        name="세로", default=100.0, min=10.0, max=400.0,
        subtype='PERCENTAGE', precision=0, update=_size_update,
        description="그림 세로 크기 (종횡비 고정을 끈 경우)")
    edge_crop: bpy.props.FloatProperty(
        name="가장자리 잘라내기", default=0.0, min=0.0, max=45.0,
        subtype='PERCENTAGE', precision=0, update=lambda s, c: _crop_update(s, c),
        description="각 칸의 테두리를 이만큼 투명하게 잘라냅니다. 칸 모서리의 "
                    "번호 글씨나 가이드선이 보일 때 사용 (그림이 칸 가운데 "
                    "있어야 함)")
    per_cell: bpy.props.BoolProperty(
        name="칸마다 따로", default=True, update=_per_cell_update,
        description="켜면 크기/위치를 칸마다 따로 기억합니다 (손대지 않은 "
                    "칸은 공통값). 끄면 모든 칸이 공통값을 씁니다")
    cells: bpy.props.CollectionProperty(type=FSKR_AtlasCellXf)
    cur_size: bpy.props.FloatProperty(
        name="그림 크기", min=10.0, max=400.0, subtype='PERCENTAGE',
        precision=0, get=_mk_proxy("size")[0], set=_mk_proxy("size")[1],
        description="지금 칸의 그림 크기 (칸마다 따로가 꺼져 있으면 공통)")
    cur_size_x: bpy.props.FloatProperty(
        name="가로", min=10.0, max=400.0, subtype='PERCENTAGE',
        precision=0, get=_mk_proxy("size_x")[0], set=_mk_proxy("size_x")[1])
    cur_size_y: bpy.props.FloatProperty(
        name="세로", min=10.0, max=400.0, subtype='PERCENTAGE',
        precision=0, get=_mk_proxy("size_y")[0], set=_mk_proxy("size_y")[1])
    cur_size_lock: bpy.props.BoolProperty(
        name="종횡비 고정 (이 칸)", get=_cur_lock_get, set=_cur_lock_set,
        description="지금 칸만 종횡비를 고정하거나 풉니다 (칸마다 따로). "
                    "일괄 조절로 체크한 칸에도 같이 적용")
    cur_flip_x: bpy.props.BoolProperty(
        name="좌우 반전", get=_mk_flip("flip_x")[0], set=_mk_flip("flip_x")[1],
        description="지금 칸의 그림을 좌우로 뒤집습니다")
    cur_flip_y: bpy.props.BoolProperty(
        name="상하 반전", get=_mk_flip("flip_y")[0], set=_mk_flip("flip_y")[1],
        description="지금 칸의 그림을 위아래로 뒤집습니다")
    cur_nx: bpy.props.FloatProperty(
        name="위치 X", soft_min=-50.0, soft_max=50.0, subtype='PERCENTAGE',
        precision=0, get=_mk_proxy("nx")[0], set=_mk_proxy("nx")[1])
    cur_ny: bpy.props.FloatProperty(
        name="위치 Y", soft_min=-50.0, soft_max=50.0, subtype='PERCENTAGE',
        precision=0, get=_mk_proxy("ny")[0], set=_mk_proxy("ny")[1])
    nudge_x: bpy.props.FloatProperty(
        name="위치 X", default=0.0, soft_min=-50.0, soft_max=50.0,
        subtype='PERCENTAGE', precision=0, update=_size_update,
        description="그림을 데칼 위에서 좌우로 이동 (칸 너비 대비 %)")
    nudge_y: bpy.props.FloatProperty(
        name="위치 Y", default=0.0, soft_min=-50.0, soft_max=50.0,
        subtype='PERCENTAGE', precision=0, update=_size_update,
        description="그림을 데칼 위에서 위아래로 이동 (칸 높이 대비 %)")
    expand: bpy.props.BoolProperty(default=True)
    show_settings: bpy.props.BoolProperty(default=False)
    show_lip: bpy.props.BoolProperty(default=False)
    edit_on: bpy.props.BoolProperty(
        name="편집 모드", default=False, update=_edit_on_update,
        description="켜면 키프레임을 무시하고 고른 칸을 계속 보여 줍니다 "
                    "(칸을 골라도 키가 들어가지 않음). 칸별 배치를 조절할 때 "
                    "켜고, 끝나면 끄세요")
    autokey: bpy.props.BoolProperty(
        name="바꾸면 자동 키", default=False,
        description="입 칸을 고르거나 입 배치(위치·크기·회전·불투명도·크롭), "
                    "시퀀스 선택·말하기 값을 바꾸면 현재 프레임에 키를 바로 "
                    "넣습니다 (꺼져 있어도 Blender 자동 키가 켜져 있으면 칸은 삽입)")
    key_interp: bpy.props.EnumProperty(
        name="보간", default='BEZIER',
        items=(('CONSTANT', "Constant", "다음 키까지 값 그대로 (뚝 바뀜)",
                'IPO_CONSTANT', 0),
               ('LINEAR', "Linear", "일정한 속도로 변함", 'IPO_LINEAR', 1),
               ('BEZIER', "Spline", "부드럽게 가속·감속 (Bezier)",
                'IPO_BEZIER', 2)),
        description="입 키를 넣을 때 쓸 보간 방법 (입 전체의 위치·크기·회전·"
                    "불투명도·크롭). 칸·시퀀스·말하기 키는 항상 Constant")
    pick_row: bpy.props.EnumProperty(
        name="행", items=_row_items, get=_pick_row_get, set=_pick_row_set)
    pick_col: bpy.props.EnumProperty(
        name="열", items=_col_items, get=_pick_col_get, set=_pick_col_set)
    # 립싱크
    lip_on: bpy.props.BoolProperty(
        name="립싱크에 사용", default=False,
        description="오디오 립싱크를 굽을 때 이 시트의 열(입)에도 키를 넣습니다")
    lip_mode: bpy.props.EnumProperty(name="립싱크 방식",
                                     items=LIP_MODE_ITEMS, default='OPEN')
    lip_closed: bpy.props.IntProperty(name="닫힘", default=0, min=0)
    lip_half: bpy.props.IntProperty(name="반 열림", default=1, min=0)
    lip_open: bpy.props.IntProperty(name="열림", default=2, min=0)
    lip_th_half: bpy.props.FloatProperty(
        name="반 열림 기준", default=0.12, min=0.0, soft_max=1.0,
        precision=2, description="이 개방도 이상이면 반 열림")
    lip_th_open: bpy.props.FloatProperty(
        name="열림 기준", default=0.45, min=0.0, soft_max=1.5,
        precision=2, description="이 개방도 이상이면 열림")
    lip_a: bpy.props.IntProperty(name="A", default=1, min=0)
    lip_i: bpy.props.IntProperty(name="I", default=2, min=0)
    lip_u: bpy.props.IntProperty(name="U", default=3, min=0)
    lip_e: bpy.props.IntProperty(name="E", default=4, min=0)
    lip_o: bpy.props.IntProperty(name="O", default=5, min=0)
    lip_hold: bpy.props.IntProperty(
        name="최소 유지 (프레임)", default=2, min=1, max=12,
        description="입 모양이 이보다 짧게 바뀌면 앞 모양에 합칩니다. "
                    "2 = 애니메이션식 on twos")


def _mode_update(self, context):
    _redraw_ui(context)


# 탭 맨 위 두 갈래 (드라이버 방식 / 스프라이트 방식)
FSKR_Settings.__annotations__["ui_mode"] = bpy.props.EnumProperty(
    name="작업 방식",
    items=(('DRIVER', "드라이버 방식",
            "셰이프 키 슬라이더/패드 컨트롤러 (기존 Face Rig)", 'DRIVER', 0),
           ('SPRITE', "스프라이트 방식",
            "격자 이미지 칸 전환 (텍스처 표정·립싱크)", 'IMAGE_DATA', 1)),
    default='DRIVER', update=_mode_update)

# 립싱크 구간이 '입 벌림 단계'(스프라이트)로 만들어졌는지
FSKR_Settings.__annotations__["lipsync_sprite"] = bpy.props.BoolProperty(
    default=False)
# 편집기에서 지정한 시퀀스 구간 JSON: [[시작, 끝, 시퀀스 이름], ...]
FSKR_Settings.__annotations__["lipsync_seqr"] = bpy.props.StringProperty(
    default="[]")

# FSKR_Settings에 컬렉션 추가 (FSKR_AtlasItem이 먼저 등록되어야 함)
FSKR_Settings.__annotations__["atlases"] = bpy.props.CollectionProperty(
    type=FSKR_AtlasItem)


# ------------------------------------------------------------------
# 드라이버 구성
# ------------------------------------------------------------------

def _drv(fc, rig, prop, expr):
    _drv_vars(fc, rig, [("v", prop)], expr)


def _drv_vars(fc, rig, pairs, expr):
    for m in list(fc.modifiers):
        try:
            fc.modifiers.remove(m)
        except Exception:
            pass
    d = fc.driver
    d.type = 'SCRIPTED'
    for v in list(d.variables):
        d.variables.remove(v)
    for vn, prop in pairs:
        var = d.variables.new()
        var.name = vn
        var.type = 'SINGLE_PROP'
        t = var.targets[0]
        t.id_type = 'OBJECT'
        t.id = rig
        t.data_path = '["%s"]' % prop
    d.expression = expr


def _exprs(n_c, n_r):
    ex_u = "min(max(floor(v+0.5),0),%d)/%d" % (n_c - 1, n_c)
    ex_v = "-min(max(floor(v+0.5),0),%d)/%d" % (n_r - 1, n_r)
    return ex_u, ex_v


def _mats(ob):
    out = []
    for sl in getattr(ob, "material_slots", []):
        m = sl.material
        if m is not None and m.use_nodes and m.node_tree and m not in out:
            out.append(m)
    return out


def _cleanup(it, target=None, method=None):
    """이 시트가 만든 모디파이어/노드/드라이버 제거."""
    try:
        bi = json.loads(it.built or "{}")
    except Exception:
        bi = {}
    tnames = {n for n in (target, bi.get("target"), it.target) if n}
    for tn in tnames:
        ob = bpy.data.objects.get(tn)
        if ob is None:
            continue
        mn = _MOD_PREFIX + it.uid
        md = ob.modifiers.get(mn) if hasattr(ob, "modifiers") else None
        if md is not None:
            for pp in ("offset", "scale"):
                try:
                    ob.driver_remove('modifiers["%s"].%s' % (mn, pp))
                except Exception:
                    pass
            ob.modifiers.remove(md)
        for m in _mats(ob):
            nt = m.node_tree
            pre = _MAP_PREFIX + it.uid + "_"
            for nd in [n for n in nt.nodes if n.name.startswith(pre)]:
                for sk in ("Location", "Scale"):
                    try:
                        nd.inputs[sk].driver_remove("default_value")
                    except Exception:
                        pass
                src = (nd.inputs["Vector"].links[0].from_socket
                       if nd.inputs["Vector"].is_linked else None)
                dsts = [lk.to_socket for lk in nd.outputs["Vector"].links]
                nt.nodes.remove(nd)
                if src is not None and not src.node.name.startswith(
                        _UVN_PREFIX + it.uid + "_"):
                    for ds in dsts:
                        nt.links.new(src, ds)
            upre = _UVN_PREFIX + it.uid + "_"
            for nd in [n for n in nt.nodes if n.name.startswith(upre)]:
                nt.nodes.remove(nd)
            _mask_remove(it, nt)


def _detect_image(ob):
    for m in _mats(ob):
        for nd in m.node_tree.nodes:
            if nd.type == 'TEX_IMAGE' and nd.image is not None:
                return nd.image.name
    return ""


_ALPHA_PREFIX = "FSKR_ATA_"


def _out_node(nt):
    out = None
    try:
        out = nt.get_output_node('ALL')
    except Exception:
        out = None
    if out is None:
        out = next((nd for nd in nt.nodes
                    if nd.type == 'OUTPUT_MATERIAL'), None)
    return out


def _alpha_mix(nt):
    """출력에 실제로 연결된 투명 Mix 노드 (없으면 None)."""
    out = _out_node(nt)
    if out is None or not out.inputs["Surface"].is_linked:
        return None
    nd = out.inputs["Surface"].links[0].from_node
    return nd if nd.name.startswith(_ALPHA_PREFIX + "mix") else None


def _setup_alpha(it):
    """데칼 머티리얼: 이미지 알파로 투명 처리 + 블렌드 설정 + 그림자 끄기.

    Surface에 연결된 셰이더 앞에 Mix Shader(Transparent / 기존 셰이더,
    Fac = 이미지 Alpha)를 끼운다. 이미 처리된 머티리얼은 연결만 확인.
    반환: 처리한 머티리얼 수 (-1 = 대상 없음).
    """
    ob = bpy.data.objects.get(it.target)
    if ob is None or ob.type != 'MESH':
        return -1
    n = 0
    for m in _mats(ob):
        nt = m.node_tree
        texs = [nd for nd in nt.nodes if nd.type == 'TEX_IMAGE'
                and nd.image is not None
                and (not it.image or nd.image.name == it.image)]
        if not texs:
            continue
        tex = texs[0]
        out = _out_node(nt)
        if out is None or not out.inputs["Surface"].is_linked:
            continue
        surf = out.inputs["Surface"]
        src = surf.links[0].from_socket
        if src.node.name.startswith(_ALPHA_PREFIX + "mix"):
            mix = src.node
        else:
            # 출력에서 떨어져 남은 예전 투명 노드 정리 (연결을 바꾼 경우)
            for nd in [n for n in nt.nodes
                       if n.name.startswith(_ALPHA_PREFIX)
                       or n.name.startswith(_MASK_PREFIX)]:
                nt.nodes.remove(nd)
            mix = nt.nodes.new('ShaderNodeMixShader')
            mix.name = _ALPHA_PREFIX + "mix"
            mix.label = "Sprite Alpha"
            tr = nt.nodes.new('ShaderNodeBsdfTransparent')
            tr.name = _ALPHA_PREFIX + "transparent"
            mix.location = (out.location.x - 200, out.location.y)
            tr.location = (mix.location.x - 220, mix.location.y + 140)
            nt.links.new(tr.outputs[0], mix.inputs[1])
            nt.links.new(src, mix.inputs[2])
            nt.links.new(mix.outputs[0], surf)
        # Fac = 이미지 알파 (다시 눌러도 연결 보장)
        fl = (mix.inputs[0].links[0].from_node
              if mix.inputs[0].is_linked else None)
        if not (fl == tex or (fl is not None
                              and fl.name.startswith(_MASK_PREFIX))):
            nt.links.new(tex.outputs["Alpha"], mix.inputs[0])
        try:
            tex.image.alpha_mode = 'STRAIGHT'
        except Exception:
            pass
        # 렌더 방식 (4.2+ EEVEE) / 구버전 블렌드 모드
        if hasattr(m, "surface_render_method"):
            try:
                m.surface_render_method = 'BLENDED'
            except Exception:
                pass
        if hasattr(m, "blend_method"):
            try:
                m.blend_method = 'BLEND'
            except Exception:
                pass
        if hasattr(m, "shadow_method"):
            try:
                m.shadow_method = 'NONE'
            except Exception:
                pass
        n += 1
    for attr in ("visible_shadow",):
        if hasattr(ob, attr):
            try:
                setattr(ob, attr, False)
            except Exception:
                pass
    return n


_MASK_PREFIX = "FSKR_ATM_"


def _mask_remove(it, nt):
    pre = _MASK_PREFIX + it.uid + "_"
    nds = [n for n in nt.nodes if n.name.startswith(pre)]
    if not nds:
        return
    for nd in nds:
        if nd.type == 'COMBXYZ':
            for sk in nd.inputs:
                try:
                    sk.driver_remove("default_value")
                except Exception:
                    pass
        nt.nodes.remove(nd)
    mix = _alpha_mix(nt)
    tex = _alpha_tex(it, nt)
    if mix is not None and tex is not None and not mix.inputs[0].is_linked:
        nt.links.new(tex.outputs["Alpha"], mix.inputs[0])


def _alpha_tex(it, nt):
    return next((nd for nd in nt.nodes if nd.type == 'TEX_IMAGE'
                 and nd.image is not None
                 and (not it.image or nd.image.name == it.image)), None)


def _crop_margin(it, cw, ch):
    """마스크 안쪽 여백: 번짐 방지 0.4% + 가장자리 잘라내기."""
    k = 0.004 + max(0.0, float(it.edge_crop)) / 100.0
    return cw * k, ch * k


def _mask_tests(cw, ch, ex, ey):
    return ((0, 'GREATER_THAN', ex), (0, 'LESS_THAN', cw - ex),
            (1, 'GREATER_THAN', 1.0 - ch + ey), (1, 'LESS_THAN', 1.0 - ey))


def _crop_update(self, context):
    """가장자리 잘라내기: 마스크 비교값만 바꾼다 (재구성 불필요)."""
    ob = bpy.data.objects.get(self.target)
    if ob is None:
        return
    cw, ch = 1.0 / max(1, int(self.cols)), 1.0 / max(1, int(self.rows))
    ex, ey = _crop_margin(self, cw, ch)
    tests = _mask_tests(cw, ch, ex, ey)
    pre = _MASK_PREFIX + self.uid + "_t"
    for m in _mats(ob):
        nt = m.node_tree
        for i, (_ax, _op, val) in enumerate(tests):
            nd = nt.nodes.get(pre + str(i))
            if nd is not None:
                nd.inputs[1].default_value = val
        nt.update_tag()
    _redraw_ui(context or bpy.context)


def _mask_build(it, ob, cols, rows, put):
    """칸 밖으로 나간 샘플링을 투명 처리 (Fake Margin + 번짐 방지).

    W = (샘플링 UV) - (현재 칸 오프셋) 이 첫 칸 사각형 안일 때만 보임.
    투명 배경 설정(Mix Shader)이 된 머티리얼에만 적용된다.
    """
    cw, ch = 1.0 / cols, 1.0 / rows
    ex, ey = _crop_margin(it, cw, ch)
    pre = _MASK_PREFIX + it.uid + "_"
    for m in _mats(ob):
        nt = m.node_tree
        _mask_remove(it, nt)
        mix = _alpha_mix(nt)
        tex = _alpha_tex(it, nt)
        if mix is None or tex is None:
            continue
        x0, y0 = tex.location.x - 900, tex.location.y - 420

        def node(tp, nm, dx, dy):
            nd = nt.nodes.new(tp)
            nd.name = pre + nm
            nd.label = "Sprite Mask"
            nd.location = (x0 + dx, y0 + dy)
            nd.hide = True
            return nd
        if it.method == 'UVWARP':
            uvn = node('ShaderNodeUVMap', "uv", 0, 0)
            if it.uv_map:
                uvn.uv_map = it.uv_map
            vsrc = uvn.outputs["UV"]
        else:
            mp = nt.nodes.get(_MAP_PREFIX + it.uid + "_" + tex.name)
            if mp is None:
                continue
            vsrc = mp.outputs["Vector"]
        ofs = node('ShaderNodeCombineXYZ', "ofs", 0, -60)
        put(ofs.inputs[0].driver_add("default_value"),
            ofs.inputs[1].driver_add("default_value"))
        sub = node('ShaderNodeVectorMath', "sub", 180, 0)
        sub.operation = 'SUBTRACT'
        nt.links.new(vsrc, sub.inputs[0])
        nt.links.new(ofs.outputs[0], sub.inputs[1])
        sep = node('ShaderNodeSeparateXYZ', "sep", 360, 0)
        nt.links.new(sub.outputs[0], sep.inputs[0])
        tests = _mask_tests(cw, ch, ex, ey)
        outs = []
        for i, (ax, op, val) in enumerate(tests):
            mt = node('ShaderNodeMath', "t%d" % i, 540, -40 * i)
            mt.operation = op
            nt.links.new(sep.outputs[ax], mt.inputs[0])
            mt.inputs[1].default_value = val
            outs.append(mt.outputs[0])
        cur = tex.outputs["Alpha"]
        for i, o in enumerate(outs):
            mu = node('ShaderNodeMath', "m%d" % i, 720, -40 * i)
            mu.operation = 'MULTIPLY'
            nt.links.new(cur, mu.inputs[0])
            nt.links.new(o, mu.inputs[1])
            cur = mu.outputs[0]
        nt.links.new(cur, mix.inputs[0])


def fix_target(s, it, context=None):
    """대상 오브젝트가 없거나 메시가 아니면 맞춰 준다: 입 파츠에 연결된 시트면
    그 얼굴 캔버스, 아니면 지금 선택한 메시. 바꿨으면 True."""
    ob = bpy.data.objects.get(it.target) if it.target else None
    if ob is not None and ob.type == 'MESH':
        return False
    try:
        from . import eye as EY
        ml = EY.mouth_layers(s, it)
    except Exception:
        ml = []
    cand = None
    if ml:
        cand = bpy.data.objects.get(ml[0][0].target)
        if cand is not None:
            it.method = 'CANVAS'
    if cand is None:
        ctx = context or bpy.context
        a = getattr(ctx, "active_object", None)
        if a is not None and a.type == 'MESH':
            cand = a
        else:   # 선택한 메시 중 하나 (포즈 모드라 활성은 리그일 때)
            cand = next((o for o in getattr(ctx, "selected_objects", ())
                         or () if o.type == 'MESH'), None)
    if cand is None:
        # 그래도 없으면 얼굴 캔버스 (입 시트는 보통 캔버스에 그림)
        for st in s.eyes:
            o = bpy.data.objects.get(st.target)
            if o is not None and o.type == 'MESH':
                cand = o
                it.method = 'CANVAS'
                break
    if cand is None or cand.type != 'MESH':
        return False
    it.target = cand.name
    return True


def _build(s, it):
    """모디파이어/노드 + 드라이버를 현재 설정대로 (재)구성. 오류 문자열 반환."""
    rig = s.rig
    if rig is None:
        return _tr("리그를 먼저 지정하세요")
    fix_target(s, it)
    ob = bpy.data.objects.get(it.target)
    if ob is None or ob.type != 'MESH':
        return _tr("대상이 메시가 아닙니다")
    _cleanup(it)
    cols, rows = max(1, int(it.cols)), max(1, int(it.rows))
    pairs, fx_i = atlas_drv_spec(s, it)
    if it.method == 'CANVAS':
        # 얼굴 캔버스가 이 시트를 레이어로 읽는다 (캔버스 머티리얼 재구성)
        it.built = json.dumps({"target": it.target, "sig": _sig(it)})
        try:
            from .eye import eye_rebuild_for_atlas
            eye_rebuild_for_atlas(s, it.uid)
        except Exception as e:
            print("FSKR canvas mouth:", e)
        return ""
    cw, ch = 1.0 / cols, 1.0 / rows

    def bind(fc, role):
        _drv_vars(fc, rig, pairs, fx_i)
        _lut_role(fc, it, role)

    def put(fc_u, fc_v):  # 마스크용: 칸 오프셋만
        bind(fc_u, 'CU')
        bind(fc_v, 'CV')
    return _build_rest(s, it, ob, rig, cols, rows, cw, ch, bind, put)


def atlas_drv_spec(s, it):
    """칸 전환 드라이버의 변수 목록과 식 (모든 출력 방식 공통)."""
    rig = s.rig
    cols, rows = max(1, int(it.cols)), max(1, int(it.rows))
    _ensure_prop(rig, _prop_row(it), rows)
    _ensure_prop(rig, _prop_col(it), cols)
    src = _row_source(s, it)
    rprop, cprop = _prop_row(src), _prop_col(it)
    free = it.layout == 'FREE'
    _flap_cache(it)
    pairs = [("r", rprop), ("c", cprop)]
    if free:
        # 미리보기 값(pr/pc/pt/pq, 키 없음)이 0 이상이면 그 값을 우선 사용
        _ensure_prop(rig, _prop_talk(it), _K)
        _ensure_prop(rig, _prop_q(it), len(it.flaps) + 1)
        _pv_ensure(rig, it)
        pairs += [("t", _prop_talk(it)), ("q", _prop_q(it)),
                  ("pr", _prop_pv(it, "r")), ("pc", _prop_pv(it, "c")),
                  ("pt", _prop_pv(it, "t")), ("pq", _prop_pv(it, "q"))]
        X = ("(min(max((r if pr<0 else pr),0),%d)*%d"
             "+min(max((c if pc<0 else pc),0),%d))" % (rows - 1, cols,
                                                         cols - 1))
        T = "(t if pt<0 else pt)"
        Q = "(q if pq<0 else pq)"
        # 말하는 중이고 시퀀스가 지정되어 있으면 지정 시퀀스 영역을 조회
        fx_i = ("(%s*%d+%s if min(%s,%s)<0.5 else %d+%s*%d+%s)+0.25"
                % (X, _K, T, Q, T, rows * cols * _K - _K, Q, _K, T))
    else:
        fx_i = ("(min(max(floor(r+0.5),0),%d)*%d+min(max(floor(c+0.5),0),%d))"
                "*%d+0.25" % (rows - 1, cols, cols - 1, _K))
    return pairs, fx_i


def atlas_bind(s, it, fc, role):
    """임의의 드라이버 F-커브를 이 시트의 칸 조회표(role)로 묶는다."""
    pairs, fx_i = atlas_drv_spec(s, it)
    _drv_vars(fc, s.rig, pairs, fx_i)
    _lut_role(fc, it, role)


def _build_rest(s, it, ob, rig, cols, rows, cw, ch, bind, put):
    if it.method == 'UVWARP':
        mn = _MOD_PREFIX + it.uid
        md = ob.modifiers.new(mn, 'UV_WARP')
        if it.uv_map and it.uv_map in ob.data.uv_layers:
            md.uv_layer = it.uv_map
        if it.vgroup and it.vgroup in ob.vertex_groups:
            md.vertex_group = it.vgroup
        md.center = (0.5 * cw, 1.0 - 0.5 * ch)  # 첫 칸 중심
        fo = ob.driver_add('modifiers["%s"].offset' % mn)
        bind(fo[0], 'OU')
        bind(fo[1], 'OV')
        fs = ob.driver_add('modifiers["%s"].scale' % mn)
        bind(fs[0], 'SU')
        bind(fs[1], 'SV')
    else:
        n_done = 0
        for m in _mats(ob):
            nt = m.node_tree
            texs = [n for n in nt.nodes if n.type == 'TEX_IMAGE'
                    and n.image is not None
                    and (not it.image or n.image.name == it.image)]
            for tex in texs:
                vin = tex.inputs["Vector"]
                srcs = vin.links[0].from_socket if vin.is_linked else None
                if srcs is None:
                    uvn = nt.nodes.new('ShaderNodeUVMap')
                    uvn.name = _UVN_PREFIX + it.uid + "_" + tex.name
                    uvn.label = "Sprite UV"
                    if it.uv_map:
                        uvn.uv_map = it.uv_map
                    uvn.location = (tex.location.x - 420, tex.location.y)
                    srcs = uvn.outputs["UV"]
                mp = nt.nodes.new('ShaderNodeMapping')
                mp.name = _MAP_PREFIX + it.uid + "_" + tex.name
                mp.label = "Sprite: " + it.name
                mp.vector_type = 'POINT'
                mp.location = (tex.location.x - 220, tex.location.y)
                nt.links.new(srcs, mp.inputs["Vector"])
                nt.links.new(mp.outputs["Vector"], vin)
                loc, scl = mp.inputs["Location"], mp.inputs["Scale"]
                bind(loc.driver_add("default_value", 0), 'LU')
                bind(loc.driver_add("default_value", 1), 'LV')
                bind(scl.driver_add("default_value", 0), 'SU')
                bind(scl.driver_add("default_value", 1), 'SV')
                n_done += 1
        if not n_done:
            it.built = json.dumps({"target": it.target, "sig": ""})
            return _tr("머티리얼에서 이미지 텍스처를 찾지 못했습니다")
    try:
        _mask_build(it, ob, cols, rows, put)
    except Exception as e:  # 마스크 실패는 칸 전환 자체를 막지 않음
        print("FSKR mask:", e)
    it.built = json.dumps({"target": it.target, "sig": _sig(it)})
    # 같은 행을 따라가는 시트도 재구성 (행 수가 바뀌었을 수 있음)
    try:
        rig.update_tag()
        ob.update_tag()
    except Exception:
        pass
    return ""


def _has_mask(it):
    ob = bpy.data.objects.get(it.target)
    if ob is None:
        return False
    pre = _MASK_PREFIX + it.uid + "_"
    return any(any(n.name.startswith(pre) for n in m.node_tree.nodes)
               for m in _mats(ob))


def _is_stale(it):
    try:
        return json.loads(it.built or "{}").get("sig") != _sig(it)
    except Exception:
        return True


def _fit_uv(it):
    ob = bpy.data.objects.get(it.target)
    if ob is None or ob.type != 'MESH':
        return -1
    me = ob.data
    uvl = (me.uv_layers.get(it.uv_map) if it.uv_map else me.uv_layers.active)
    if uvl is None:
        return 0
    use = None
    vg = ob.vertex_groups.get(it.vgroup) if it.vgroup else None
    if vg is not None:
        use = set()
        gi = vg.index
        for v in me.vertices:
            for g in v.groups:
                if g.group == gi and g.weight > 0.0:
                    use.add(v.index)
                    break
    idx = [lp.index for lp in me.loops
           if use is None or lp.vertex_index in use]
    if not idx:
        return 0
    us = [uvl.data[i].uv[0] for i in idx]
    vs = [uvl.data[i].uv[1] for i in idx]
    u0, u1, v0, v1 = min(us), max(us), min(vs), max(vs)
    du = (u1 - u0) or 1.0
    dv = (v1 - v0) or 1.0
    cw, ch = 1.0 / max(1, it.cols), 1.0 / max(1, it.rows)
    for i in idx:
        u, v = uvl.data[i].uv
        uvl.data[i].uv = ((u - u0) / du * cw, 1.0 - ch + (v - v0) / dv * ch)
    me.update()
    return len(idx)


# ------------------------------------------------------------------
# 다른 기능 연동 (프리셋 / 기본값 / 전체 키 / 립싱크)
# ------------------------------------------------------------------

def atlas_snapshot(s):
    """{uid: [row, col]} (프리셋 저장용)."""
    rig = s.rig
    out = {}
    for it in s.atlases:
        out[it.uid] = [_get_val(rig, _prop_row(it)),
                       _get_val(rig, _prop_col(it))]
    return out


def atlas_apply(s, data, key=False):
    """프리셋 값 적용 (스프라이트는 블렌딩 없이 즉시 전환)."""
    rig = s.rig
    if rig is None or not isinstance(data, dict):
        return 0
    n = 0
    for it in s.atlases:
        v = data.get(it.uid)
        if not v or len(v) < 2:
            continue
        for prop, val, lim in ((_prop_row(it), v[0], it.rows),
                               (_prop_col(it), v[1], it.cols)):
            if prop in rig.keys():
                rig[prop] = max(0, min(int(lim) - 1, int(val)))
                if key:
                    _key(rig, prop)
        n += 1
    try:
        rig.update_tag()
        for it in s.atlases:
            ob = bpy.data.objects.get(it.target)
            if ob is not None:
                ob.update_tag()
    except Exception:
        pass
    _poke()
    return n


def atlas_key_all(s):
    rig = s.rig
    n = 0
    for it in s.atlases:
        for prop in (_prop_row(it), _prop_col(it)):
            if rig is not None and prop in rig.keys():
                _key(rig, prop)
                n += 1
    return n


def atlas_save_default(s):
    rig = s.rig
    if rig is None:
        return
    rig[_DEF_PROP] = json.dumps(atlas_snapshot(s))


def atlas_reset(s, key=False):
    rig = s.rig
    if rig is None:
        return
    try:
        d = json.loads(rig.get(_DEF_PROP, "{}"))
    except Exception:
        d = {}
    data = {it.uid: d.get(it.uid, [0, 0]) for it in s.atlases}
    atlas_apply(s, data, key=key)


def atlas_lip_enabled(s):
    return any(it.lip_on for it in s.atlases)


# 스프라이트 립싱크 구간 코드 (구간 데이터의 모음 칸을 빌려 씀)
_LEVEL_V = {1: '_U', 2: '_E', 3: '_A'}      # 닫힘 / 반 / 열림
_V_LEVEL = {v: k for k, v in _LEVEL_V.items()}


def atlas_sprite_lip(s):
    """자동 립싱크를 입 벌림 단계로 분석할지 (스프라이트 방식 + 립싱크 사용)."""
    return (getattr(s, "ui_mode", 'DRIVER') == 'SPRITE'
            and atlas_lip_enabled(s))


def atlas_level_segs(s, opens, start):
    """개방도 → 닫힘/반/열림 구간. 기준값·최소 유지는 립싱크 켜진 첫 시트."""
    it = next((a for a in s.atlases if a.lip_on), None)
    th_h = float(it.lip_th_half) if it else 0.12
    th_o = float(it.lip_th_open) if it else 0.45
    hold = int(it.lip_hold) if it else 2
    sil = min(th_h, 0.02) if th_h > 0.02 else 0.02
    lv = []
    for o in opens:
        o = float(o)
        if o < sil:
            lv.append(0)
        elif o >= th_o:
            lv.append(3)
        elif o >= th_h:
            lv.append(2)
        else:
            lv.append(1)
    runs = _hold_runs(lv, hold)
    s.lipsync_segs.clear()
    f = 0
    for v, ln in runs:
        if v > 0:
            g = s.lipsync_segs.add()
            g.fs = start + f
            g.fe = start + f + ln - 1
            g.vowel = _LEVEL_V[v]
        f += ln
    s.lipsync_sprite = True


def _hold_runs(vals, hold):
    runs = []
    for v in vals:
        if runs and runs[-1][0] == v:
            runs[-1][1] += 1
        else:
            runs.append([v, 1])
    hold = max(1, int(hold))
    out = []
    for v, ln in runs:
        if out and (ln < hold or out[-1][0] == v):
            out[-1][1] += ln
        else:
            out.append([v, ln])
    return out


def _lip_levels(s, it, start, n, opens):
    """자유 배치: 프레임별 말하기 코드.

    모음 모드: 0 구간 밖, 1 닫힘(작은 소리), 2~6 A/I/U/E/O
    짝 모드:   0 구간 밖, 1 닫힘, 2 반, 3 열림
    """
    vals = [0] * n
    if getattr(s, "lipsync_sprite", False):  # 편집기 구간 단계 그대로
        for sg in s.lipsync_segs:
            lv = _V_LEVEL.get(sg.vowel, 2)
            for f in range(max(0, int(sg.fs) - start),
                           min(n - 1, int(sg.fe) - start) + 1):
                vals[f] = lv
        return _hold_runs(vals, it.lip_hold), 0
    for sg in s.lipsync_segs:
        for f in range(max(0, int(sg.fs) - start),
                       min(n - 1, int(sg.fe) - start) + 1):
            o = float(opens[f]) if f < len(opens) else 0.0
            if o >= it.lip_th_open:
                vals[f] = 3
            elif o >= it.lip_th_half:
                vals[f] = 2
            else:
                vals[f] = 1
    return _hold_runs(vals, it.lip_hold), 0


def _lip_values(s, it, start, n, opens):
    if it.layout == 'FREE':
        return _lip_levels(s, it, start, n, opens)
    cols = max(1, int(it.cols))

    def cl(v):
        return max(0, min(cols - 1, int(v)))

    closed = cl(it.lip_closed)
    vals = [closed] * n
    if getattr(s, "lipsync_sprite", False):  # 편집기 구간 단계 그대로
        colv = {1: cl(it.lip_closed), 2: cl(it.lip_half), 3: cl(it.lip_open)}
        for sg in s.lipsync_segs:
            c9 = colv[_V_LEVEL.get(sg.vowel, 2)]
            for f in range(max(0, int(sg.fs) - start),
                           min(n - 1, int(sg.fe) - start) + 1):
                vals[f] = c9
    elif True:  # 벌림 3단계 (모음 방식은 1.0.66에서 제거)
        for i in range(min(n, len(opens))):
            o = float(opens[i])
            if o >= it.lip_th_open:
                vals[i] = cl(it.lip_open)
            elif o >= it.lip_th_half:
                vals[i] = cl(it.lip_half)
        # 구간 밖(무음으로 판정된 곳)은 닫힘
        inside = [False] * n
        for sg in s.lipsync_segs:
            for f in range(max(0, int(sg.fs) - start),
                           min(n - 1, int(sg.fe) - start) + 1):
                inside[f] = True
        if any(inside):
            vals = [v if inside[i] else closed for i, v in enumerate(vals)]
    else:
        vm = {'_A': it.lip_a, '_I': it.lip_i, '_U': it.lip_u,
              '_E': it.lip_e, '_O': it.lip_o, '_N': it.lip_a}
        for sg in s.lipsync_segs:
            c = cl(vm.get(sg.vowel, it.lip_a))
            for f in range(max(0, int(sg.fs) - start),
                           min(n - 1, int(sg.fe) - start) + 1):
                vals[f] = c
    # 최소 유지: 짧은 입모양은 앞 모양에 합침
    runs = []
    for v in vals:
        if runs and runs[-1][0] == v:
            runs[-1][1] += 1
        else:
            runs.append([v, 1])
    hold = max(1, int(it.lip_hold))
    out = []
    for v, ln in runs:
        if out and (ln < hold or out[-1][0] == v):
            out[-1][1] += ln
        else:
            out.append([v, ln])
    return out, closed


def _write_runs(rig, prop, runs, end_val, start, n, prev):
    """(값, 길이) 목록을 Constant 키로 기록 (범위 안의 이전 키는 지움)."""
    path = '["%s"]' % prop
    try:
        rig.keyframe_insert(data_path=path, frame=start, group="Sprite Sheet")
    except Exception:
        return False
    fcs = _fcurves_for(rig, path)
    if not fcs:
        return False
    rngs = [(start, start + n)]
    if prev and len(prev) == 2:
        rngs.append((int(prev[0]), int(prev[0]) + int(prev[1])))
    for fc in fcs:
        pts = fc.keyframe_points
        for i in range(len(pts) - 1, -1, -1):
            f = pts[i].co[0]
            if any(a - 0.5 <= f <= b + 0.5 for a, b in rngs):
                pts.remove(pts[i], fast=True)
        fc.update()
    fc = fcs[0]
    keys = []
    f = start
    for v, ln in runs:
        keys.append((f, v))
        f += ln
    keys.append((start + n, end_val))
    pts = fc.keyframe_points
    base = len(pts)
    pts.add(len(keys))
    for j, (fr, v) in enumerate(keys):
        p = pts[base + j]
        p.co = (float(fr), float(v))
        p.interpolation = 'CONSTANT'
    fc.update()
    return True


def _seq_runs(s, it, start, n):
    """편집기 시퀀스 구간 → 프레임별 시퀀스 번호 (0 = 표정 따라 자동)."""
    vals = [0] * n
    try:
        rr = json.loads(getattr(s, "lipsync_seqr", "[]") or "[]")
    except Exception:
        rr = []
    names = [f.name for f in it.flaps]
    for e in rr:
        try:
            a, b, nm = int(e[0]), int(e[1]), str(e[2])
        except Exception:
            continue
        if nm not in names:
            continue
        q = names.index(nm) + 1
        for f in range(max(0, a - start), min(n - 1, b - start) + 1):
            vals[f] = q
    return _hold_runs(vals, 1)


def atlas_seq_names(s):
    """편집기 시퀀스 목록: 립싱크 켜진 자유 배치 시트의 시퀀스 이름."""
    it = next((a for a in s.atlases if a.lip_on and a.layout == 'FREE'),
              None)
    return [f.name for f in it.flaps] if it is not None else []


def atlas_lip_bake(s, rig, start, n, opens, prev=None):
    """립싱크 구간/개방도로 입 칸 키를 굽는다. 굽은 시트 수 반환."""
    if rig is None or n <= 0:
        return 0
    done = 0
    for it in s.atlases:
        if not it.lip_on:
            continue
        if it.layout == 'FREE':
            prop = _prop_talk(it)
            _ensure_prop(rig, prop, _K)
        else:
            prop = _prop_col(it)
            _ensure_prop(rig, prop, max(1, int(it.cols)))
        runs, closed = _lip_values(s, it, start, n, opens)
        if not _write_runs(rig, prop, runs, closed, start, n, prev):
            continue
        if it.layout == 'FREE':  # 편집기에서 지정한 시퀀스 구간
            qp = _prop_q(it)
            _ensure_prop(rig, qp, len(it.flaps) + 1)
            _write_runs(rig, qp, _seq_runs(s, it, start, n), 0,
                        start, n, prev)
        done += 1
    try:
        rig.update_tag()
    except Exception:
        pass
    return done


# ------------------------------------------------------------------
# 오퍼레이터
# ------------------------------------------------------------------

class FSKR_OT_atlas_add(bpy.types.Operator):
    bl_idname = "fskr.atlas_add"
    bl_label = "스프라이트 시트 추가"
    bl_description = ("선택한 오브젝트(입/눈 데칼 등)에 격자 이미지 칸 "
                      "전환을 추가합니다")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.fskr.rig is not None

    def execute(self, context):
        s = context.scene.fskr
        used = {a.uid for a in s.atlases}
        i = 1
        while "A%d" % i in used:
            i += 1
        it = s.atlases.add()
        it.uid = "A%d" % i
        ob = context.active_object
        if ob is not None and ob.type == 'MESH':
            it.target = ob.name
            it.name = ob.name
            it.image = _detect_image(ob)
        else:
            it.name = _tr("입")
        it.show_settings = True
        if it.target:
            err = _build(s, it)
            if err:
                self.report({'WARNING'}, err)
            elif it.method == 'UVWARP' and it.image:
                try:
                    if _setup_alpha(it) > 0:
                        _build(s, it)
                except Exception:
                    pass
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_atlas_remove(bpy.types.Operator):
    bl_idname = "fskr.atlas_remove"
    bl_label = "스프라이트 시트 삭제"
    bl_description = ("드라이버·모디파이어·노드와 리그 값을 모두 제거합니다 "
                      "(키프레임은 유지)")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        s = context.scene.fskr
        it = _find(s, self.uid)
        if it is None:
            return {'CANCELLED'}
        _cleanup(it)
        rig = s.rig
        try:
            from .atlas_vp import vp_remove
            vp_remove(context, rig, it)
        except Exception as e:
            print("FSKR vp remove:", e)
        if rig is not None:
            for p in (_prop_row(it), _prop_col(it), _prop_talk(it),
                      _prop_pv(it, "r"), _prop_pv(it, "c"),
                      _prop_pv(it, "t")):
                if p in rig.keys():
                    del rig[p]
        for a in s.atlases:
            if a.row_link == it.uid:
                a.row_link = ""
        _thumbs_free(it.uid)
        idx = next(i for i, a in enumerate(s.atlases) if a.uid == self.uid)
        s.atlases.remove(idx)
        for a in s.atlases:  # 행을 따라가던 시트는 자체 행으로 재구성
            if a.target and _is_stale(a):
                _build(s, a)
        try:  # 이 시트를 입 레이어로 쓰던 얼굴 캔버스 재구성
            from .eye import eye_rebuild_for_atlas
            eye_rebuild_for_atlas(s, self.uid)
        except Exception:
            pass
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_atlas_build(bpy.types.Operator):
    bl_idname = "fskr.atlas_build"
    bl_label = "적용 (드라이버 재구성)"
    bl_description = "현재 설정대로 모디파이어/노드와 드라이버를 다시 만듭니다"
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        s = context.scene.fskr
        it = _find(s, self.uid)
        if it is None:
            return {'CANCELLED'}
        err = _build(s, it)
        if err:
            self.report({'ERROR'}, err)
            return {'CANCELLED'}
        # 이 시트의 행을 따라가는 시트도 갱신
        for a in s.atlases:
            if a.row_link == it.uid and a.target:
                _build(s, a)
        if it.image:
            try:
                _thumbs_build(it)
            except Exception:
                pass
        context.view_layer.update()
        self.report({'INFO'}, _tr("스프라이트 시트 적용: ") + it.name)
        return {'FINISHED'}


class FSKR_OT_atlas_alpha(bpy.types.Operator):
    bl_idname = "fskr.atlas_alpha"
    bl_label = "투명 배경 설정"
    bl_description = ("데칼 머티리얼을 이미지 알파로 투명하게 만듭니다 "
                      "(Transparent + Mix Shader 삽입, Blended 렌더, "
                      "그림자 끄기). 얼굴 본체 머티리얼에는 쓰지 마세요")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        it = _find(context.scene.fskr, self.uid)
        if it is None or it.method == 'CANVAS':
            return {'CANCELLED'}
        n = _setup_alpha(it)
        if n < 0:
            self.report({'ERROR'}, _tr("대상이 메시가 아닙니다"))
            return {'CANCELLED'}
        if n == 0:
            self.report({'WARNING'},
                        _tr("머티리얼에서 이미지 텍스처를 찾지 못했습니다"))
            return {'CANCELLED'}
        if it.built and not _is_stale(it):
            _build(context.scene.fskr, it)
        self.report({'INFO'}, _tr("투명 배경 설정 완료 (머티리얼 %d개)") % n)
        return {'FINISHED'}


class FSKR_OT_atlas_thumbs(bpy.types.Operator):
    bl_idname = "fskr.atlas_thumbs"
    bl_label = "썸네일 갱신"
    bl_description = "이미지를 칸 단위로 잘라 선택 그리드 썸네일을 만듭니다"

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        it = _find(context.scene.fskr, self.uid)
        if it is None or not _thumbs_build(it):
            self.report({'WARNING'}, _tr("이미지 없음 (썸네일 불가)"))
            return {'CANCELLED'}
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_atlas_fit_uv(bpy.types.Operator):
    bl_idname = "fskr.atlas_fit_uv"
    bl_label = "UV를 첫 칸에 맞추기"
    bl_description = ("대상의 UV(버텍스 그룹이 있으면 그 부분만)를 좌상단 "
                      "첫 칸 크기로 맞춥니다")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        it = _find(context.scene.fskr, self.uid)
        if it is None or it.method == 'CANVAS':
            return {'CANCELLED'}
        ob = bpy.data.objects.get(it.target)
        prev_mode = None
        if ob is not None and ob.mode == 'EDIT':
            prev_mode = 'EDIT'
            bpy.ops.object.mode_set(mode='OBJECT')
        n = _fit_uv(it)
        if prev_mode:
            bpy.ops.object.mode_set(mode=prev_mode)
        if n < 0:
            self.report({'ERROR'}, _tr("대상이 메시가 아닙니다"))
            return {'CANCELLED'}
        if n == 0:
            self.report({'WARNING'}, _tr("맞출 UV가 없습니다"))
            return {'CANCELLED'}
        self.report({'INFO'}, _tr("UV 맞춤 완료 (루프 %d개)") % n)
        return {'FINISHED'}


class FSKR_OT_atlas_key(bpy.types.Operator):
    bl_idname = "fskr.atlas_key"
    bl_label = "칸 키프레임"
    bl_description = ("현재 칸 번호에 Constant 키를 삽입합니다. 키는 데칼이 아니라 "
                      "리그 오브젝트에 들어가므로, 타임라인에서 보려면 리그를 "
                      "선택하거나 'Only Show Selected'를 끄세요")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})
    what: bpy.props.StringProperty(default="BOTH", options={'HIDDEN'})

    def execute(self, context):
        s = context.scene.fskr
        it = _find(s, self.uid)
        if it is None or s.rig is None:
            return {'CANCELLED'}
        props = []
        if self.what == 'CELL':
            self.what = 'BOTH'
        if self.what in ('ROW', 'BOTH') and not (
                it.row_link and _row_source(s, it) is not it):
            props.append(_prop_row(it))
        if self.what in ('COL', 'BOTH'):
            props.append(_prop_col(it))
        for p in props:
            _ensure_prop(s.rig, p, it.rows if p.endswith("_r") else it.cols)
            _key(s.rig, p)
        self.report({'INFO'}, _tr("키 삽입: '%s' 오브젝트 (프레임 %d)")
                    % (s.rig.name, context.scene.frame_current))
        _redraw_ui(context)
        return {'FINISHED'}


def _scene_fskr():
    return bpy.context.scene.fskr


def _mouth_interp_owner(s, it):
    """입 보간 값을 가진 데이터: 입 레이어의 태그 (없으면 시트)."""
    from . import eye as EY
    ml = EY.mouth_layers(s, it)
    g = EY.layer_tag(*ml[0]) if ml else None
    return g if g is not None else it


def _mouth_key_props(s, it):
    """입 시트 키 대상 (칸/시퀀스/말하기 — 리그에 있는 것만)."""
    rig = s.rig
    out = []
    if it.layout == 'FREE':
        out.append(_prop_col(it))
        if not (it.row_link and _row_source(s, it) is not it):
            out.insert(0, _prop_row(it))
        out += [_prop_q(it), _prop_talk(it)]
    else:
        if not (it.row_link and _row_source(s, it) is not it):
            out.append(_prop_row(it))
        out.append(_prop_col(it))
    return [p for p in out if rig is not None and p in rig.keys()]


def mouth_watch_props(s, it):
    """자동 키 감시 대상: 칸/시퀀스/말하기 + 연결된 입 레이어 배치."""
    from . import eye as EY
    out = list(_mouth_key_props(s, it))
    for st, L in EY.mouth_layers(s, it):
        try:
            out += [p for p in EY._anim_props(*EY._anim_source(s, st, L))
                    if p in s.rig.keys()]
        except Exception:
            pass
    return list(dict.fromkeys(out))


def key_mouth(s, it, only=None):
    """입 시트 키 삽입 (개수 반환). only: 프로퍼티 이름 집합 (None = 전부)."""
    from . import eye as EY
    rig = s.rig
    if rig is None:
        return 0
    n = 0
    for p in _mouth_key_props(s, it):
        if only is not None and p not in only:
            continue
        _key(rig, p)
        n += 1
    seen = set()
    for st, L in EY.mouth_layers(s, it):
        ast, aL = EY._anim_source(s, st, L)
        k = (ast.uid, aL.lid)
        if k in seen:
            continue
        seen.add(k)
        lp = set(EY._anim_props(ast, aL))
        sub = lp if only is None else (lp & set(only))
        if not sub:
            continue
        # 칸 키는 위에서 이미 넣었으므로 배치 프로퍼티만
        # 보간: 입 레이어의 태그 값 (태그가 없으면 이 시트 값)
        ip = it.key_interp if EY.layer_tag(st, L) is None else None
        n += EY.key_layer(s, st, L, only=sub, interp=ip)
    return n


class FSKR_OT_atlas_key_all(bpy.types.Operator):
    bl_idname = "fskr.atlas_key_all"
    bl_label = "입 키 넣기"
    bl_description = ("현재 프레임에 입 키를 넣습니다: 칸(그림)·시퀀스·말하기 "
                      "(Constant) + 입 전체 배치 (고른 보간). 키는 리그 오브젝트에 "
                      "들어갑니다")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, context):
        s = context.scene.fskr
        it = _find(s, self.uid)
        if it is None or s.rig is None:
            return {'CANCELLED'}
        n = key_mouth(s, it)
        self.report({'INFO'}, _tr("키 삽입: '%s' 오브젝트 (프레임 %d)")
                    % (s.rig.name, context.scene.frame_current)
                    + " · %d" % n)
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_atlas_interp_apply(bpy.types.Operator):
    bl_idname = "fskr.atlas_interp_apply"
    bl_label = "보간 적용"
    bl_description = ("이미 넣은 입 배치 키에 지금 고른 보간 방법을 적용합니다 "
                      "(선택한 키프레임만 / 이 입의 모든 키)")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    scope: bpy.props.EnumProperty(
        name="범위",
        items=(('SELECTED', "선택한 키프레임만",
                "도프시트·그래프 에디터에서 선택해 둔 키프레임만 (이 입)",
                'RESTRICT_SELECT_OFF', 0),
               ('ALL', "이 입의 모든 키",
                "이 입의 위치·크기·회전·불투명도·크롭 키 전부",
                'KEYFRAME_HLT', 1)),
        options={'SKIP_SAVE'})

    def execute(self, context):
        from . import eye as EY
        s = context.scene.fskr
        if s.rig is None:
            return {'CANCELLED'}
        it = _find(s, self.uid) if self.uid else None
        items = [it] if it is not None else list(s.atlases)
        n = 0
        seen = set()
        for st, L in [x for a in items for x in EY.mouth_layers(s, a)]:
            ast, aL = EY._anim_source(s, st, L)
            if (ast.uid, aL.lid) in seen:
                continue
            seen.add((ast.uid, aL.lid))
            ai = EY._layer_atlas(s, L)
            ip = ai.key_interp if EY.layer_tag(st, L) is None \
                else EY.interp_for(st, L)
            n += EY.set_layer_interp(s, st, L, ip,
                                     selected_only=(self.scope == 'SELECTED'))
        if n == 0 and self.scope == 'SELECTED':
            self.report({'WARNING'}, _tr("선택한 키프레임이 없습니다 (도프시트·"
                                         "그래프 에디터에서 키를 선택하세요)"))
            return {'CANCELLED'}
        self.report({'INFO'}, "%s: %s %d" % (
            ", ".join(a.name for a in items),
            _mouth_interp_owner(s, items[0]).key_interp if items else "",
            n))
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_atlas_step(bpy.types.Operator):
    bl_idname = "fskr.atlas_step"
    bl_label = "이전/다음 칸"
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})
    what: bpy.props.StringProperty(default="COL", options={'HIDDEN'})
    delta: bpy.props.IntProperty(default=1, options={'HIDDEN'})

    def execute(self, context):
        s = context.scene.fskr
        it = _find(s, self.uid)
        if it is None or s.rig is None:
            return {'CANCELLED'}
        # 드롭다운과 같은 경로(RNA 프로퍼티 설정)로 바꿔야 Blender가
        # 씬 갱신을 걸어 드라이버가 다시 계산된다.
        if self.what == 'CELL':
            ids = [int(i[0]) for i in _cell_items(it, context)]
            cur = _pick_cell_get(it)
            pos = ids.index(cur) if cur in ids else 0
            it.pick_cell = str(ids[(pos + self.delta) % len(ids)])
        elif self.what == 'ROW':
            n = max(1, int(it.rows))
            it.pick_row = str((_pick_row_get(it) + self.delta) % n)
        else:
            n = max(1, int(it.cols))
            it.pick_col = str((_pick_col_get(it) + self.delta) % n)
        _poke(context)
        return {'FINISHED'}


class FSKR_OT_atlas_cell_show(bpy.types.Operator):
    bl_idname = "fskr.atlas_cell_show"
    bl_label = "이 칸 보기"
    bl_description = ("이 칸을 지금 칸으로 만들어 뷰포트에 바로 보여 줍니다 "
                      "(자동 키가 켜져 있으면 키도 들어감). 크기·위치는 이 칸 "
                      "기준으로 조절됩니다")
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})
    r: bpy.props.IntProperty(default=0, options={'HIDDEN'})
    c: bpy.props.IntProperty(default=0, options={'HIDDEN'})

    def execute(self, context):
        it = _find(context.scene.fskr, self.uid)
        if it is None:
            return {'CANCELLED'}
        cols = max(1, int(it.cols))
        if it.edit_on and not _pe_on():
            edit_show(it, self.r, self.c)
        else:
            _pick_cell_set(it, self.r * cols + self.c)
        try:
            rig = _rig()
            if rig is not None:
                rig.update_tag()
            ob = bpy.data.objects.get(it.target)
            if ob is not None:
                ob.update_tag()
        except Exception:
            pass
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_atlas_cell_msel(bpy.types.Operator):
    bl_idname = "fskr.atlas_cell_msel"
    bl_label = "일괄 조절할 칸"
    bl_description = ("이 칸을 일괄 조절할 칸으로 체크합니다. 지금 칸의 크기·위치를 "
                      "바꾸면 체크한 칸들도 같이 바뀝니다 (크기는 같은 비율, "
                      "위치는 움직인 만큼)")
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    # SKIP_SAVE: 'X'(모두 해제)로 쓴 clear=True가 다음 클릭에 남지 않게
    uid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    r: bpy.props.IntProperty(default=-1, options={'HIDDEN', 'SKIP_SAVE'})
    c: bpy.props.IntProperty(default=-1, options={'HIDDEN', 'SKIP_SAVE'})
    clear: bpy.props.BoolProperty(default=False,
                                  options={'HIDDEN', 'SKIP_SAVE'})

    def invoke(self, context, event):
        it = _find(context.scene.fskr, self.uid)
        if it is None:
            return {'CANCELLED'}
        if not self.clear and (self.r, self.c) not in cells_msel(it) and \
                (self.r, self.c) != tuple(_cur_cell(it)):
            tr = cell_transformed(it, self.r, self.c)
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
        it = _find(context.scene.fskr, self.uid)
        if it is None:
            return {'CANCELLED'}
        sel = cells_msel(it)
        if self.clear:
            sel = set()
        else:
            rc = (self.r, self.c)
            if rc in sel:
                sel.discard(rc)
            else:
                sel.add(rc)   # 직접 체크한 칸만 (지금 칸을 몰래 넣지 않음)
        cells_msel_set(it, sel)
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_atlas_cell_reset(bpy.types.Operator):
    bl_idname = "fskr.atlas_cell_reset"
    bl_label = "칸 비우기"
    bl_description = ("지금 칸에 저장된 크기·위치·반전과 다른 칸 그림 연결을 "
                      "모두 지우고, 이미지에 그려진 원래 칸으로 되돌립니다 "
                      "(이미지 파일은 건드리지 않음)")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        it = _find(context.scene.fskr, self.uid)
        if it is None:
            return {'CANCELLED'}
        r, c = _cur_cell(it)
        for i, e in enumerate(it.cells):
            if e.r == r and e.c == c:
                it.cells.remove(i)
                break
        _size_update(it, context)
        _thumbs_request(it)
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_atlas_cell_clear_alias(bpy.types.Operator):
    bl_idname = "fskr.atlas_cell_clear_alias"
    bl_label = "다른 칸 그림 연결 모두 비우기"
    bl_description = ("예전 '반전 칸 만들기'로 다른 칸 그림을 가져다 쓰던 칸을 "
                      "모두 원래 칸으로 되돌립니다 (그 칸의 크기·위치도 지움)")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        it = _find(context.scene.fskr, self.uid)
        if it is None:
            return {'CANCELLED'}
        n = 0
        for i in reversed(range(len(it.cells))):
            e = it.cells[i]
            if e.src_r >= 0 and e.src_c >= 0:
                it.cells.remove(i)
                n += 1
        _size_update(it, context)
        _thumbs_request(it)
        _redraw_ui(context)
        self.report({'INFO'}, _tr("칸 %d개를 비웠습니다") % n)
        return {'FINISHED'}


class FSKR_OT_atlas_cell_all(bpy.types.Operator):
    bl_idname = "fskr.atlas_cell_all"
    bl_label = "이 값을 모든 칸에"
    bl_description = ("지금 칸의 크기/위치를 공통값으로 만들고 다른 칸의 "
                      "개별 설정을 모두 지웁니다")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        it = _find(context.scene.fskr, self.uid)
        if it is None:
            return {'CANCELLED'}
        vals = {f: getattr(it, "cur_" + f) for f in
                ("size", "size_x", "size_y", "nx", "ny")}
        _SIZE_BUSY[0] = True
        try:
            it.cells.clear()
            for f, g in _PROXY_GLOBAL.items():
                setattr(it, g, vals[f])
        finally:
            _SIZE_BUSY[0] = False
        _size_update(it, context)
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_atlas_vowel_set(bpy.types.Operator):
    bl_idname = "fskr.atlas_vowel_set"
    bl_label = "지금 칸으로 지정"
    bl_description = "표정 칸 피커에서 지금 고른 칸을 이 모음의 입으로 지정합니다"
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})
    field: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        it = _find(context.scene.fskr, self.uid)
        if it is None or self.field not in _VOWEL_FIELDS:
            return {'CANCELLED'}
        setattr(it, self.field, _cur_cell(it))
        return {'FINISHED'}


class FSKR_OT_atlas_talk_preview(bpy.types.Operator):
    bl_idname = "fskr.atlas_talk_preview"
    bl_label = "말하기 미리보기"
    bl_description = ("이 입 모양을 지금 바로 보여 줍니다 (키는 넣지 않음). "
                      "'끄기'로 표정 칸으로 돌아갑니다")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})
    code: bpy.props.IntProperty(default=0, options={'HIDDEN'})

    def execute(self, context):
        s = context.scene.fskr
        it = _find(s, self.uid)
        if it is None or s.rig is None:
            return {'CANCELLED'}
        if not it.built or _is_stale(it):
            _build(s, it)
        code = max(0, min(_K - 1, int(self.code)))
        _pv_set(s.rig, it, tcode=(code if code > 0 else None))
        _poke(context)
        return {'FINISHED'}


class FSKR_OT_atlas_flip_copy(bpy.types.Operator):
    bl_idname = "fskr.atlas_flip_copy"
    bl_label = "반전 칸 만들기"
    bl_description = ("지금 칸의 그림을 뒤집어서 다른 칸 번호로 씁니다. "
                      "이미지에 반전 그림을 따로 그릴 필요가 없습니다")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})
    target: bpy.props.IntVectorProperty(
        name="만들 칸 (행, 열)", size=2, min=0,
        description="반전 그림을 둘 칸. 보통 이미지에서 비어 있는 칸")
    flip_y: bpy.props.BoolProperty(name="상하 반전", default=True)
    flip_x: bpy.props.BoolProperty(name="좌우 반전", default=False)

    def invoke(self, context, event):
        it = _find(context.scene.fskr, self.uid)
        if it is None:
            return {'CANCELLED'}
        r, c = _cur_cell(it)
        fl = _PREV_FILLED.get(it.uid, {})
        rows, cols = int(it.rows), int(it.cols)
        cand = [(r + 1, c)] + [(rr, cc) for rr in range(rows)
                               for cc in range(cols)]
        tgt = next(((rr, cc) for rr, cc in cand
                    if 0 <= rr < rows and 0 <= cc < cols
                    and (rr, cc) != (r, c) and not fl.get((rr, cc), False)
                    and _cell_entry(it, rr, cc) is None), (r, c))
        self.target = tgt
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        it = _find(context.scene.fskr, self.uid)
        col = self.layout.column()
        if it is not None:
            r, c = _cur_cell(it)
            col.label(text=_tr("원본 칸: ") + "%d-%d" % (r, c))
        col.prop(self, "target")
        row = col.row(align=True)
        row.prop(self, "flip_y", toggle=True)
        row.prop(self, "flip_x", toggle=True)

    def execute(self, context):
        s = context.scene.fskr
        it = _find(s, self.uid)
        if it is None:
            return {'CANCELLED'}
        r, c = _cur_cell(it)
        tr, tc = int(self.target[0]), int(self.target[1])
        if not (0 <= tr < int(it.rows) and 0 <= tc < int(it.cols)):
            self.report({'ERROR'}, _tr("칸 번호가 범위를 벗어났습니다"))
            return {'CANCELLED'}
        if (tr, tc) == (r, c):
            self.report({'ERROR'}, _tr("원본과 다른 칸을 고르세요"))
            return {'CANCELLED'}
        src = _cell_entry(it, r, c)
        e = _cell_ensure(it, tr, tc)
        for f9, g9 in _PROXY_GLOBAL.items():  # 원본 칸의 크기/위치를 이어받음
            setattr(e, f9, getattr(src, f9) if src is not None
                    else getattr(it, g9))
        sr, sc2 = _cell_src(it, r, c)  # 원본이 반전 칸이어도 실제 그림 칸
        e.src_r, e.src_c = sr, sc2
        base_fx = bool(src.flip_x) if src is not None else False
        base_fy = bool(src.flip_y) if src is not None else False
        e.flip_x = base_fx != bool(self.flip_x)
        e.flip_y = base_fy != bool(self.flip_y)
        _size_update(it, context)
        try:
            _thumbs_build(it)
        except Exception:
            pass
        _redraw_ui(context)
        self.report({'INFO'}, _tr("반전 칸 만들기: %d-%d → %d-%d")
                    % (r, c, tr, tc))
        return {'FINISHED'}


class FSKR_OT_atlas_seq_preview(bpy.types.Operator):
    bl_idname = "fskr.atlas_seq_preview"
    bl_label = "시퀀스 미리보기"
    bl_description = ("이 시퀀스의 단계를 지금 바로 보여 줍니다 (키는 넣지 않음). "
                      "기준 칸으로 표정이 바뀌며, '끄기'로 말하기를 끕니다")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})
    index: bpy.props.IntProperty(options={'HIDDEN'})
    code: bpy.props.IntProperty(default=0, options={'HIDDEN'})

    def execute(self, context):
        s = context.scene.fskr
        it = _find(s, self.uid)
        rig = s.rig
        if it is None or rig is None or not (0 <= self.index < len(it.flaps)):
            return {'CANCELLED'}
        if not it.built or _is_stale(it):
            _build(s, it)
        e = it.flaps[self.index]
        code = max(0, min(3, int(self.code)))
        if code == 0:
            _pv_set(rig, it)  # 미리보기 끄기
        else:
            src = None if e.any_src else _cell_ok(e.src, it)
            _pv_set(rig, it, src[0] if src else None,
                    src[1] if src else None, code, self.index + 1)
        _poke(context)
        return {'FINISHED'}


class FSKR_OT_atlas_merge(bpy.types.Operator):
    bl_idname = "fskr.atlas_merge"
    bl_label = "시퀀스를 입 파츠의 시트로 옮기기"
    bl_description = ("이 시트의 시퀀스를 ④ 입 파츠가 그리는 시트로 옮기고, 이 "
                      "시트는 지웁니다 (같은 입 그림을 쓰는 시트끼리)")
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    uid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    dst: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, context):
        s = context.scene.fskr
        src = _find(s, self.uid)
        dst = _find(s, self.dst)
        if src is None or dst is None or src == dst:
            return {'CANCELLED'}
        n = 0
        for f in src.flaps:
            g = dst.flaps.add()
            for k in f.keys():       # 저장된 값 그대로 복사 (칸·단계 보정 등)
                try:
                    v = f[k]
                    g[k] = v.to_list() if hasattr(v, "to_list") else (
                        v.to_dict() if hasattr(v, "to_dict") else v)
                except Exception:
                    pass
            n += 1
        name9 = dst.name
        suid = src.uid
        try:
            bpy.ops.fskr.atlas_remove('EXEC_DEFAULT', uid=suid)
        except Exception as e:
            print("FSKR merge remove:", e)
        dst = next((a for a in s.atlases if a.name == name9), None)
        if dst is not None:
            dst.show_flaps = True
            try:
                _build(s, dst)
            except Exception as e:
                print("FSKR merge build:", e)
            from . import eye as EY
            for st, L in EY.mouth_layers(s, dst):
                EY.eye_build(s, st)
                break
        self.report({'INFO'}, _tr("시퀀스 %d개를 옮겼습니다") % n)
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_atlas_link_mouth(bpy.types.Operator):
    bl_idname = "fskr.atlas_link_mouth"
    bl_label = "입 파츠에 연결"
    bl_description = ("④의 입 파츠가 이 시트를 그리도록 연결합니다 (시퀀스·"
                      "미리보기·립싱크가 화면에 보이려면 필요)")
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    uid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, context):
        s = context.scene.fskr
        it = _find(s, self.uid)
        if it is None:
            return {'CANCELLED'}
        hit = None
        for st in s.eyes:
            for L in st.layers:
                if getattr(L, "kind", 'PART') == 'MOUTH':
                    hit = (st, L)
                    break
            if hit:
                break
        if hit is None:
            self.report({'WARNING'}, _tr("④에 입 파츠가 없습니다"))
            return {'CANCELLED'}
        st, L = hit
        L.atlas = it.uid
        it.target = st.target
        it.method = 'CANVAS'
        from . import eye as EY
        try:
            AT_build = _build(s, it)
        except Exception as e:
            AT_build = str(e)
        EY.eye_build(s, st)
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_atlas_constant(bpy.types.Operator):
    bl_idname = "fskr.atlas_constant"
    bl_label = "Constant 보간 정리"
    bl_description = ("스프라이트 시트 키를 모두 Constant 보간으로 바꿉니다 "
                      "(칸 사이가 섞이는 문제 방지)")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        s = context.scene.fskr
        n = 0
        for it in s.atlases:
            for p in (_prop_row(it), _prop_col(it), _prop_talk(it)):
                n += _make_constant(s.rig, '["%s"]' % p)
        self.report({'INFO'}, _tr("Constant 정리: 키 %d개") % n)
        return {'FINISHED'}


class FSKR_OT_atlas_lip_bake(bpy.types.Operator):
    bl_idname = "fskr.atlas_lip_bake"
    bl_label = "스프라이트 립싱크 다시 굽기"
    bl_description = "현재 립싱크 구간으로 입 칸 키만 다시 굽습니다"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        s = context.scene.fskr
        return (s.rig is not None and atlas_lip_enabled(s)
                and bool(s.lipsync_open))

    def execute(self, context):
        s = context.scene.fskr
        try:
            opens = json.loads(s.lipsync_open or "[]")
        except Exception:
            opens = []
        n = atlas_lip_bake(s, s.rig, int(s.lipsync_start), len(opens), opens)
        context.scene.frame_set(context.scene.frame_current)
        self.report({'INFO'}, _tr("스프라이트 립싱크: %d개 굽기") % n)
        return {'FINISHED'}


# ------------------------------------------------------------------
# 패널
# ------------------------------------------------------------------

class FSKR_PT_mode(bpy.types.Panel):
    """탭 맨 위: 작업 방식 선택 (드라이버 / 스프라이트)."""
    bl_label = "작업 방식"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Face Rig"
    bl_options = {'HIDE_HEADER'}
    bl_order = 0

    def draw(self, context):
        s = context.scene.fskr
        col = self.layout.column()
        row = col.row(align=True)
        row.scale_y = 1.6
        row.prop(s, "ui_mode", expand=True)
        try:
            from .layer_vp import draw_copy_warning
            draw_copy_warning(col)
        except Exception:
            pass
        if getattr(s, "ui_mode", 'DRIVER') == 'SPRITE' and \
                hasattr(s, "sprite_tab"):
            g = col.grid_flow(row_major=True, columns=3, even_columns=True,
                              align=True)
            g.scale_y = 1.25
            for key in ('SETUP', 'PARTS', 'EXPR', 'MOUTH', 'GAZE', 'CTRL'):
                g.prop_enum(s, "sprite_tab", key)
        try:
            from .core import _addon_prefs
            ap = _addon_prefs(context)
            if ap:
                col.prop(ap, "lang")
        except Exception:
            pass
        try:
            from .layer_vp import draw_perf
            draw_perf(col)
        except Exception:
            pass


class FSKR_PT_atlas(bpy.types.Panel):
    # idname을 새로 줘서 예전 버전에서 저장된 패널 위치(맨 위)를 버리고
    # bl_order 순서(⑤ 다음)로 다시 놓이게 한다
    bl_idname = "FSKR_PT_mouth_seq"
    bl_label = "⑥ 입 (시퀀스·립싱크)"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Face Rig"
    bl_order = 6

    @classmethod
    def poll(cls, context):
        from .face_ui import sprite_tab_on
        return sprite_tab_on(context, 'MOUTH')

    def draw_header(self, context):
        self.layout.label(text="", icon='IMAGE_DATA')

    def draw(self, context):
        s = context.scene.fskr
        layout = self.layout
        rig = s.rig
        if rig is None:
            layout.label(text=_tr("①에서 리그를 먼저 지정하세요"), icon='INFO')
            return
        has_mouth = any(a.method == 'CANVAS' for a in s.atlases)
        g = layout.column(align=True)
        g.scale_y = 0.85
        if not has_mouth:
            g.label(text=_tr("입 파츠 추가 방법"), icon='INFO')
            for ln in (_tr("1. ②에서 '입' 마커를 입 위치에 찍기"),
                       _tr("2. ③에서 입 모양 시트 불러오기 (칸마다 입 모양 "
                           "하나)"),
                       _tr("3. ④에서 + → 그 시트의 입 모양 → 태그 '입' → OK"),
                       _tr("   ('입' 태그의 '입 (시퀀스·립싱크)'가 켜져 있어야 "
                           "함)"),
                       _tr("4. 여기에 입 시트가 생기면 시퀀스(닫힘·반·열림) "
                           "→ 립싱크 순서로 설정")):
                g.label(text=ln)
        else:
            g.label(text=_tr("시퀀스(닫힘·반·열림) → 립싱크 순서로 "
                             "설정하세요"), icon='INFO')
        if not len(s.atlases):
            sub = layout.row(align=True)
            sub.active = False
            sub.operator("fskr.atlas_add", text=_tr("(고급) 별도 입 데칼에 "
                                                    "시트 추가"), icon='ADD')
            return
        for it in s.atlases:
            self._draw_item(context, layout, s, rig, it)
        # 오디오 립싱크 (드라이버 방식의 iFacialMocap 패널과 같은 분석기)
        lb = layout.box()
        lb.label(text=_tr("오디오 립싱크"), icon='SPEAKER')
        if not atlas_lip_enabled(s):
            lb.label(text=_tr("시트의 '립싱크에 사용'을 켜 주세요"),
                     icon='INFO')
        r = lb.row(align=True)
        r.enabled = atlas_lip_enabled(s)
        r.operator("fskr.lipsync", icon='SPEAKER')
        r.operator("fskr.lipsync_edit", text="", icon='GREASEPENCIL')
        r.operator("fskr.lipsync_sound_del", text="", icon='X')
        r = lb.row(align=True)
        r.enabled = atlas_lip_enabled(s)
        r.operator("fskr.atlas_lip_bake", icon='FILE_REFRESH')
        r = layout.row(align=True)
        r.active = False
        r.operator("fskr.atlas_constant", icon='IPO_CONSTANT')
        r.operator("fskr.atlas_add", text=_tr("(고급) 별도 데칼"), icon='ADD')

    def _draw_item(self, context, layout, s, rig, it):
        box = layout.box()
        hr = box.row(align=True)
        hr.prop(it, "expand", text="", emboss=False,
                icon='TRIA_DOWN' if it.expand else 'TRIA_RIGHT')
        hr.prop(it, "name", text="")
        hr.prop(it, "show_settings", text="", icon='PREFERENCES',
                toggle=True)
        hr.operator("fskr.atlas_remove", text="", icon='X').uid = it.uid
        if not it.expand:
            return
        # 입 파츠가 이 시트를 그리지 않으면 시퀀스·미리보기가 화면에 안 보임
        from . import eye as EY
        if not EY.mouth_layers(s, it):
            wb = box.box().column(align=True)
            wr = wb.row()
            wr.alert = True
            wr.label(text=_tr("이 시트를 그리는 입 파츠가 없습니다 — 미리보기·"
                              "시퀀스가 화면에 안 보입니다"), icon='ERROR')
            drawn9 = [a for a in s.atlases
                      if a != it and EY.mouth_layers(s, a)]
            if drawn9 and len(it.flaps):
                op = wb.operator("fskr.atlas_merge",
                                 text=_tr("시퀀스를 '%s' 시트로 옮기기 (추천)")
                                 % drawn9[0].name, icon='FORWARD')
                op.uid, op.dst = it.uid, drawn9[0].uid
                g9 = wb.column(align=True)
                g9.scale_y = 0.8
                g9.label(text=_tr("입 파츠는 '%s' 시트를 그리고 있습니다. "
                                  "옮기면 이 시트는 지워집니다")
                         % drawn9[0].name)
            if any(getattr(L, "kind", 'PART') == 'MOUTH'
                   for st9 in s.eyes for L in st9.layers):
                wb.operator("fskr.atlas_link_mouth",
                            text=_tr("④ 입 파츠에 이 시트 연결"),
                            icon='LINKED').uid = it.uid
            else:
                wb.label(text=_tr("④에서 + → 이 시트의 입 모양 → '입' 태그로 "
                                  "입 파츠를 만드세요"), icon='INFO')
        stale = _is_stale(it)
        if it.show_settings or stale:
            self._draw_settings(context, box, s, it, stale)
        if rig is None:
            return
        # 썸네일 준비
        if it.image and not _thumbs_ready(it):
            _thumbs_request(it)
        has_icons = _thumbs_ready(it)
        src = _row_source(s, it)
        col = box.column()
        # 얼굴 캔버스 입: ④ 파츠 속성과 똑같은 모양 (그림·일괄 조절·배치·키)
        from . import eye as EY
        ml = EY.mouth_layers(s, it) if it.method == 'CANVAS' else []
        if ml:
            from .face_ui import draw_part_props
            e9 = _cell_entry(it, *_cur_cell(it))
            if e9 is not None and (e9.src_r >= 0 or e9.flip_x
                                   or e9.flip_y):
                ar = col.row(align=True)
                ar.alert = True
                rc9 = (e9.src_r, e9.src_c) if e9.src_r >= 0 and \
                    e9.src_c >= 0 else tuple(_cur_cell(it))
                ar.label(text=(_tr("이 칸 = %d-%d 그림") % rc9)
                    + (_tr(" (상하 반전)") if e9.flip_y else "")
                    + (_tr(" (좌우 반전)") if e9.flip_x else ""),
                    icon='ERROR')
                ar.operator("fskr.atlas_cell_reset", text=_tr("해제"),
                            icon='TRASH').uid = it.uid
            draw_part_props(col, context, s, ml[0][0], ml[0][1], rig,
                            mouth_panel=True)
            if not _has_mask(it) and it.cells:
                col.label(text=_tr("투명 배경 설정을 눌러야 칸 밖이 "
                                   "잘립니다"), icon='ERROR')
            if it.layout == 'FREE':
                self._draw_free(col, box, it, has_icons, unified=True)
                return
            if src is it:
                self._draw_axis(col, it, "ROW", "pick_row", _tr("표정"),
                                has_icons)
            self._draw_axis(col, it, "COL", "pick_col", _tr("입"),
                            has_icons)
            self._draw_lip(box, it)
            return
        sz = col.box().column(align=True)
        hr = sz.row(align=True)
        r9, c9 = _cur_cell(it)
        own = _cell_entry(it, r9, c9) is not None
        hr.label(text=("%d-%d  " % (r9, c9))
                 + (_tr("이 칸 전용 값") if own
                    else _tr("공통값 (움직이면 이 칸만 저장)")),
                 icon='PINNED' if own else 'GRID')
        sub = hr.row(align=True)
        sub.enabled = own
        sub.operator("fskr.atlas_cell_reset", text=_tr("칸 비우기"),
                     icon='TRASH').uid = it.uid
        hr.operator("fskr.atlas_cell_all", text="",
                    icon='DUPLICATE').uid = it.uid
        e9 = _cell_entry(it, r9, c9)
        if e9 is not None and e9.src_r >= 0 and e9.src_c >= 0:
            ar = sz.row()
            ar.alert = True
            ar.label(text=(_tr("이 칸 = %d-%d 그림") % (e9.src_r, e9.src_c))
                     + (_tr(" (상하 반전)") if e9.flip_y else "")
                     + (_tr(" (좌우 반전)") if e9.flip_x else "")
                     + "  · " + _tr("칸 비우기로 해제"), icon='ERROR')
        n_alias = sum(1 for e in it.cells if e.src_r >= 0 and e.src_c >= 0)
        if n_alias:
            sz.operator("fskr.atlas_cell_clear_alias",
                        text=_tr("다른 칸 그림 연결 모두 비우기 (%d칸)")
                        % n_alias, icon='UNLINKED').uid = it.uid
        if it.method == 'CANVAS':
            n9 = sz.column(align=True)
            n9.scale_y = 0.8
            n9.label(text=_tr("얼굴 캔버스 입은 ④ 입 파츠의 '배치 (이 칸만)'에서 "
                              "칸별로 맞추는 것을 권합니다"), icon='INFO')
            n9.label(text=_tr("여기 %는 칸 창 안에서 확대라 100%를 넘기면 "
                              "가장자리가 잘릴 수 있습니다"))
        r = sz.row(align=True)
        lk9 = cell_locked(it, e9)
        if lk9:
            r.prop(it, "cur_size", slider=True)
        else:
            r.prop(it, "cur_size_x", slider=True)
            r.prop(it, "cur_size_y", slider=True)
        r.prop(it, "cur_size_lock", text="",
               icon='LOCKED' if lk9 else 'UNLOCKED')
        r = sz.row(align=True)
        r.prop(it, "cur_nx")
        r.prop(it, "cur_ny")
        r = sz.row(align=True)
        r.prop(it, "cur_flip_y", toggle=True, icon='MOD_MIRROR')
        r.prop(it, "cur_flip_x", toggle=True, icon='MOD_MIRROR')
        self._draw_msel(sz, it, (r9, c9))
        sz.prop(it, "edge_crop", slider=True)
        if (not _has_mask(it) and (it.cells or max(
                abs(v - 100.0) for v in _size_xy(it)) > 0.01)):
            sz.label(text=_tr("투명 배경 설정을 눌러야 칸 밖이 잘립니다"),
                     icon='ERROR')
        if it.layout == 'FREE':
            self._draw_free(col, box, it, has_icons)
            return
        # 행 (표정)
        if src is it:
            self._draw_axis(col, it, "ROW", "pick_row", _tr("표정"),
                            has_icons)
        else:
            col.label(text=_tr("행을 따라감: ") + src.name,
                      icon='LINKED')
        # 열 (입)
        self._draw_axis(col, it, "COL", "pick_col", _tr("입"), has_icons)
        self._draw_keys(col, it)
        self._draw_lip(box, it)

    def _draw_lip(self, box, it):
        # 립싱크
        lb = box.box()
        lr = lb.row(align=True)
        lr.prop(it, "show_lip", text="", emboss=False,
                icon='TRIA_DOWN' if it.show_lip else 'TRIA_RIGHT')
        lr.prop(it, "lip_on", icon='SPEAKER')
        if it.show_lip:
            lc = lb.column(align=True)
            lc.active = it.lip_on
            lc.prop(it, "lip_closed")
            r = lc.row(align=True)
            r.prop(it, "lip_half")
            r.prop(it, "lip_open")
            r = lc.row(align=True)
            r.prop(it, "lip_th_half", text=_tr("반 열림 기준"))
            r.prop(it, "lip_th_open", text=_tr("열림 기준"))
            lc.prop(it, "lip_hold")

    def _draw_keys(self, layout, it):
        """키 넣기 · 자동 키 · 보간 (④ 파츠의 키 줄과 같은 구성)."""
        kb = layout.box().column(align=True)
        kr = kb.row(align=True)
        kr.scale_y = 1.2
        kr.operator("fskr.atlas_key_all", text=_tr("이 입 키 넣기"),
                    icon='KEY_HLT').uid = it.uid
        kb.prop(it, "autokey", icon='REC')
        ir = kb.row(align=True)
        from . import eye as EY
        ml9 = EY.mouth_layers(_scene_fskr(), it)
        tg9 = EY.layer_tag(*ml9[0]) if ml9 else None
        ir.label(text=(_tr("보간") + " · " + tg9.name) if tg9 is not None
                 else _tr("보간"))
        ir.prop(tg9 if tg9 is not None else it, "key_interp", expand=True)
        op = ir.operator_menu_enum("fskr.atlas_interp_apply", "scope",
                                   text="", icon='FILE_REFRESH')
        try:
            op.uid = it.uid
        except Exception:
            pass

    def _draw_msel(self, layout, it, cur):
        """여러 칸 함께 조절: 칸 썸네일에서 체크 (접을 수 있음)."""
        sel = cells_msel(it)
        b = layout.box().column(align=True)
        hr = b.row(align=True)
        hr.prop(it, "msel_open", text="", emboss=False,
                icon='TRIA_DOWN' if it.msel_open else 'TRIA_RIGHT')
        hr.prop(it, "msel_open", emboss=False, toggle=True,
                text=_tr("일괄 조절") + (
                    "  (%d)" % len(sel) if sel else ""))
        if sel:
            op = hr.operator("fskr.atlas_cell_msel", text="", icon='X')
            op.uid, op.clear = it.uid, True
        if not it.msel_open:
            if sel:
                b.label(text=", ".join("%d-%d" % rc for rc in sorted(sel)),
                        icon='CHECKBOX_HLT')
            return
        icons = _PREV_ICONS.get(it.uid) if _thumbs_ready(it) else None
        fl = _PREV_FILLED.get(it.uid) or {}
        cols, rows = max(1, int(it.cols)), max(1, int(it.rows))
        g = b.grid_flow(row_major=True, columns=4, even_columns=True,
                        even_rows=True, align=True)
        for r in range(rows):
            for c in range(cols):
                if fl and not fl.get((r, c), True):
                    continue          # 빈 칸은 생략
                ic = icons.get((r, c)) if icons else None
                cc = g.column(align=True)
                is_cur = (r, c) == tuple(cur)
                # Blender는 버튼 안 아이콘을 키울 수 없어서, 큰 썸네일은
                # 그림으로 보여 주고 바로 아래 넓은 버튼으로 적용한다
                if ic:
                    cc.box().template_icon(icon_value=ic, scale=2.6)
                bt = cc.row(align=True)
                bt.alert = is_cur
                op = bt.operator("fskr.atlas_cell_msel", text="",
                                 icon='CHECKBOX_HLT' if (r, c) in sel
                                 else 'CHECKBOX_DEHLT',
                                 depress=(r, c) in sel)
                op.uid, op.r, op.c = it.uid, r, c
                sb = bt.row(align=True)
                sb.scale_x = 3.0
                op = sb.operator("fskr.atlas_cell_show",
                                 text="%d-%d" % (r, c), icon='HIDE_OFF',
                                 depress=is_cur)
                op.uid, op.r, op.c = it.uid, r, c
        hn = b.row()
        hn.scale_y = 0.8
        hn.label(text=_tr("칸 번호 버튼 = 그 칸을 뷰포트에 보기 · 체크 = 일괄 조절"),
                 icon='INFO')
        if sel:
            n = b.column(align=True)
            n.scale_y = 0.8
            n.label(text=_tr("지금 칸(빨간 버튼)의 크기·위치·반전을 바꾸면 "
                             "체크한 칸도 같이 바뀝니다"), icon='INFO')
            n.label(text=_tr("크기는 같은 비율로, 위치는 움직인 만큼"))

    def _draw_free(self, col, box, it, has_icons, unified=False):
        """자유 배치: 칸 하나 선택 + 칸별 뻐끔 짝 + 립싱크."""
        if not unified:   # 통합 모양이면 그림·키는 위 파츠 속성에 있음
            self._draw_axis(col, it, "CELL", "pick_cell", _tr("표정 칸"),
                            has_icons)
            self._draw_keys(col, it)
        mb = box.box()
        if _pv_active(_rig(), it):
            pr9 = mb.row(align=True)
            pr9.alert = True
            pr9.label(text=_tr("미리보기 중 (프레임을 옮기면 꺼짐)"),
                      icon='HIDE_OFF')
            op = pr9.operator("fskr.atlas_talk_preview", text=_tr("끄기"))
            op.uid, op.code = it.uid, 0
        fb = mb.box()
        hr = fb.row(align=True)
        hr.prop(it, "show_flaps", text="", emboss=False,
                icon='TRIA_DOWN' if it.show_flaps else 'TRIA_RIGHT')
        hr.label(text=_tr("시퀀스") + " (%d)" % len(it.flaps),
                 icon='LINKED')
        hr.operator("fskr.atlas_flap_auto", text="",
                    icon='SHADERFX').uid = it.uid
        op = hr.operator("fskr.atlas_flap_add", text="", icon='ADD')
        op.uid, op.any_src = it.uid, False
        # 뷰포트 컨트롤러 (시퀀스 목록 + 말하기 슬라이더)
        from .atlas_vp import vp_draw
        vr = fb.column(align=True)
        if len(it.flaps):
            vp_draw(vr, _rig(), it)
        else:
            vv = vr.row(align=True)
            vv.enabled = False
            vv.operator("fskr.atlas_vp_build",
                        text=_tr("뷰포트 컨트롤러 만들기"),
                        icon='ARMATURE_DATA').uid = it.uid
            vr.label(text=_tr("시퀀스를 하나 이상 만들면 쓸 수 있습니다"),
                     icon='INFO')
        if it.show_flaps:
            if not len(it.flaps):
                fb.label(text=_tr("표정 칸을 고른 뒤 + 로 시퀀스 추가, 또는 "
                                  "마법봉으로 위아래 자동 생성"))
            cols = max(1, int(it.cols))
            cur = _pick_cell_get(it)
            cur_rc = (cur // cols, cur % cols)
            for i, e in enumerate(it.flaps):
                eb = fb.box()
                r = eb.row(align=True)
                is_cur = (not e.any_src and tuple(e.src) == cur_rc)
                r.alert = is_cur
                r.prop(e, "name", text="",
                       icon='SOLO_ON' if e.any_src else 'SEQUENCE')
                from .layer_vp import paste_btn
                paste_btn(r, e)
                op = r.operator("fskr.atlas_flap_remove", text="",
                                icon='X')
                op.uid, op.index = it.uid, i
                # 메인 여부 | 단일 여부 (반반 체크박스)
                sp = eb.split(factor=0.5, align=True)
                sp.prop(e, "any_src", text=_tr("메인으로 사용"))
                sp.prop(e, "single", text=_tr("단일 입"))
                if e.any_src:
                    eb.label(text=_tr("어떤 표정에서 말하든 이 입을 씀"),
                             icon='INFO')
                else:
                    rr = eb.row(align=True)
                    rr.label(text=_tr("이 표정일 때만 사용"), icon='PINNED')
                    self._cell_field(rr, it, e, "src")
                if e.single:
                    eb.label(text=_tr("말할 때도 이 입 그대로 (뻐끔 안 함)"),
                             icon='INFO')
                    if not e.any_src:
                        sxr = eb.row(align=True)
                        sxr.prop(e, "show_xf", emboss=False,
                                 text=_tr("이 입의 크기/위치"),
                                 icon='TRIA_DOWN' if e.show_xf
                                 else 'TRIA_RIGHT')
                        if e.show_xf:
                            gx = eb.row(align=True)
                            if it.size_lock:
                                gx.prop(e, "cur_single_size")
                            else:
                                gx.prop(e, "cur_single_sx")
                                gx.prop(e, "cur_single_sy")
                            gx.prop(it, "size_lock", text="",
                                    icon='LOCKED' if it.size_lock
                                    else 'UNLOCKED')
                            gx.prop(e, "cur_single_px")
                            gx.prop(e, "cur_single_py")
                            eb.label(text=_tr("위쪽 칸별 크기/위치와 같은 값"),
                                     icon='LINKED')
                    pr = eb.row(align=True)
                    pr.label(text="", icon='HIDE_OFF')
                    for code, lab in ((0, _tr("끄기")),
                                      (3, _tr("말하는 중"))):
                        op = pr.operator("fskr.atlas_seq_preview",
                                         text=lab)
                        op.uid, op.index, op.code = it.uid, i, code
                    continue
                eb.label(text=_tr("말할 때 쓸 입:"))
                g = eb.row(align=True)
                for pn, lab in (("closed", _tr("닫힘")),
                                ("half", _tr("반")),
                                ("open", _tr("열림"))):
                    cc = g.column(align=True)
                    cc.label(text=lab)
                    self._cell_field(cc, it, e, pn)
                # 단계별 크기/위치
                xr = eb.row(align=True)
                xr.prop(e, "show_xf", emboss=False,
                        icon='TRIA_DOWN' if e.show_xf else 'TRIA_RIGHT')
                if e.show_xf:
                    tr9 = eb.row(align=True)
                    tr9.prop(e, "xf_step", expand=True)
                    gx = eb.row(align=True)  # 한 줄: 여러 칸 동시 드래그 방지
                    st9 = e.xf_step
                    if e.xf_lock:
                        gx.prop(e, "cur_sz_" + st9)
                    else:
                        gx.prop(e, st9 + "_sx")
                        gx.prop(e, st9 + "_sy")
                    gx.prop(e, "xf_lock", text="",
                            icon='LOCKED' if e.xf_lock else 'UNLOCKED')
                    gx.prop(e, st9 + "_px")
                    gx.prop(e, st9 + "_py")
                    eb.label(text=_tr("값을 바꾸면 그 단계가 미리보기됩니다"),
                             icon='INFO')
                # 미리보기
                pr = eb.row(align=True)
                pr.label(text="", icon='HIDE_OFF')
                for code, lab in ((0, _tr("끄기")), (1, _tr("닫힘")),
                                  (2, _tr("반")), (3, _tr("열림"))):
                    op = pr.operator("fskr.atlas_seq_preview", text=lab)
                    op.uid, op.index, op.code = it.uid, i, code

        lb = box.box()
        lr = lb.row(align=True)
        lr.prop(it, "show_lip", text="", emboss=False,
                icon='TRIA_DOWN' if it.show_lip else 'TRIA_RIGHT')
        lr.prop(it, "lip_on", icon='SPEAKER')
        if it.show_lip:
            lc = lb.column(align=True)
            lc.active = it.lip_on
            r = lc.row(align=True)
            r.prop(it, "lip_th_half", text=_tr("반 열림 기준"))
            r.prop(it, "lip_th_open", text=_tr("열림 기준"))
            lc.prop(it, "lip_hold")

    def _cell_field(self, layout, it, e, pname):
        """썸네일로 고르기 + 번호(행, 열)로 입력 둘 다."""
        c = layout.column(align=True)
        if _thumbs_ready(it):
            c.template_icon_view(e, "pick_" + pname, show_labels=True,
                                 scale=2.2, scale_popup=4.0)
        else:
            c.prop(e, "pick_" + pname, text="")
        c.prop(e, pname, text="")

    def _draw_axis(self, col, it, what, pname, label, has_icons):
        r = col.row(align=True)
        r.label(text=label)
        st = _key_state(it, what)
        if st:
            r.label(text="", icon=st)
        op = r.operator("fskr.atlas_step", text="", icon='TRIA_LEFT')
        op.uid, op.what, op.delta = it.uid, what, -1
        r.prop(it, pname, text="")
        op = r.operator("fskr.atlas_step", text="", icon='TRIA_RIGHT')
        op.uid, op.what, op.delta = it.uid, what, 1
        op = r.operator("fskr.atlas_key", text="", icon='KEY_HLT')
        op.uid, op.what = it.uid, what
        if has_icons:
            col.template_icon_view(it, pname, show_labels=True,
                                   scale=4.0, scale_popup=4.0)

    def _draw_settings(self, context, box, s, it, stale):
        sb = box.box()
        c = sb.column()
        c.prop(it, "edge_crop", slider=True)
        c.prop_search(it, "target", bpy.data, "objects", icon='MESH_DATA')
        ob = bpy.data.objects.get(it.target)
        c.prop(it, "method")
        ir = c.row(align=True)
        ir.prop_search(it, "image", bpy.data, "images")
        op = ir.operator("fskr.image_open", text="", icon='FILEBROWSER')
        op.kind, op.uid = 'ATLAS', it.uid
        if ob is not None and ob.type == 'MESH' and it.method != 'CANVAS':
            c.prop_search(it, "uv_map", ob.data, "uv_layers")
            if it.method == 'UVWARP':
                c.prop_search(it, "vgroup", ob, "vertex_groups")
        r = c.row(align=True)
        r.prop(it, "cols")
        r.prop(it, "rows")
        c.prop(it, "layout")
        if it.layout == 'GRID':
            c.prop(it, "row_names")
            c.prop(it, "col_names")
        if len(s.atlases) > 1:
            c.prop(it, "row_link_pick")
        if stale:
            c.label(text=_tr("설정이 바뀌었습니다. '적용'을 눌러 주세요"),
                    icon='ERROR')
        r = c.row(align=True)
        r.scale_y = 1.2
        r.alert = stale
        r.operator("fskr.atlas_build", icon='FILE_REFRESH').uid = it.uid
        if it.method == 'CANVAS':
            c.label(text=_tr("얼굴 캔버스의 입 레이어로 그려집니다 (배치는 "
                             "얼굴 캔버스 패널에서)"), icon='INFO')
            r = c.row(align=True)
            r.operator("fskr.atlas_thumbs", icon='IMAGE_REFERENCE').uid = \
                it.uid
            return
        r = c.row(align=True)
        r.operator("fskr.atlas_fit_uv", icon='UV').uid = it.uid
        r.operator("fskr.atlas_alpha", icon='TEXTURE').uid = it.uid
        r.operator("fskr.atlas_thumbs", text="",
                   icon='IMAGE_REFERENCE').uid = it.uid


def _sprite_material(ob, img):
    """머티리얼이 없는 대상: 이미지 → Emission 데칼 머티리얼을 만들어 붙임."""
    m = bpy.data.materials.new("Sprite " + ob.name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    out.location = (400, 0)
    em = nt.nodes.new('ShaderNodeEmission')
    em.location = (150, 0)
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.location = (-200, 0)
    tex.image = img
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    ob.data.materials.append(m)
    return m


class FSKR_OT_image_open(bpy.types.Operator):
    bl_idname = "fskr.image_open"
    bl_label = "이미지 불러오기"
    bl_description = ("파일에서 스프라이트 시트 이미지를 불러와 바로 "
                      "적용합니다 (대상 머티리얼의 기존 시트 이미지도 교체)")
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    filter_image: bpy.props.BoolProperty(default=True, options={'HIDDEN'})
    filter_folder: bpy.props.BoolProperty(default=True, options={'HIDDEN'})
    relative_path: bpy.props.BoolProperty(
        name="상대 경로", default=True,
        description="블렌드 파일 기준 상대 경로로 저장 (폴더째 옮겨도 유지)")
    kind: bpy.props.StringProperty(default='ATLAS', options={'HIDDEN'})
    uid: bpy.props.StringProperty(options={'HIDDEN'})
    lid: bpy.props.StringProperty(options={'HIDDEN'})

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        import os
        # 상대 경로 옵션이 켜져 있으면 Blender가 "//..." 로 넘겨주므로 절대
        # 경로로 바꿔서 확인한다
        path = bpy.path.abspath(self.filepath) if self.filepath else ""
        path = os.path.normpath(path) if path else ""
        if not path or not os.path.isfile(path):
            self.report({'ERROR'}, _tr("이미지 파일을 고르세요"))
            return {'CANCELLED'}
        try:
            img = bpy.data.images.load(path, check_existing=True)
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        if self.relative_path and bpy.data.filepath:
            try:
                img.filepath = bpy.path.relpath(path)
            except Exception:
                pass  # 다른 드라이브 등 상대 경로가 안 되면 절대 경로 유지
        try:
            img.alpha_mode = 'STRAIGHT'
        except Exception:
            pass
        s = context.scene.fskr
        if self.kind == 'EYE':
            from .eye import _find as _efind, _layer as _elayer
            st = _efind(s, self.uid)
            L = _elayer(st, self.lid) if st else None
            if L is None:
                return {'CANCELLED'}
            L.image = img.name          # 머티리얼은 자동 재구성
            self.report({'INFO'}, _tr("이미지 불러오기: ") + img.name)
            return {'FINISHED'}
        it = _find(s, self.uid)
        if it is None:
            return {'CANCELLED'}
        old = it.image
        ob = bpy.data.objects.get(it.target)
        swapped = 0
        if ob is not None and ob.type == 'MESH':
            # 지금 시트 이미지를 쓰는 텍스처 노드만 교체 (피부 등은 그대로)
            for m in _mats(ob):
                for nd in m.node_tree.nodes:
                    if (nd.type == 'TEX_IMAGE' and nd.image is not None
                            and old and nd.image.name == old):
                        nd.image = img
                        swapped += 1
            if not swapped and not any(sl.material
                                       for sl in ob.material_slots):
                _sprite_material(ob, img)
                swapped = 1
        it.image = img.name
        if not swapped and ob is not None:
            self.report({'WARNING'},
                        _tr("대상 머티리얼에서 바꿀 시트 이미지를 찾지 "
                            "못했습니다. 이미지 텍스처 노드에 직접 "
                            "연결해 주세요"))
        if it.target:
            err = _build(s, it)
            if not err and it.method == 'UVWARP':
                try:
                    if _setup_alpha(it) > 0:
                        _build(s, it)
                except Exception:
                    pass
            if err:
                self.report({'WARNING'}, err)
        _thumbs_request(it)
        try:
            from .atlas_vp import vp_exists, vp_schedule
            if vp_exists(s.rig, it):
                vp_schedule(it.uid)
        except Exception:
            pass
        _redraw_ui(context)
        if swapped:
            self.report({'INFO'}, _tr("이미지 불러오기: ") + img.name)
        return {'FINISHED'}


class FSKR_OT_atlas_flap_add(bpy.types.Operator):
    bl_idname = "fskr.atlas_flap_add"
    bl_label = "현재 칸 기준으로 시퀀스 추가"
    bl_description = ("지금 선택된 칸을 기준 칸으로 하는 시퀀스를 추가합니다 "
                      "(열림 = 기준 칸). 닫힘 칸을 지정해 주세요")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})
    any_src: bpy.props.BoolProperty(default=False, options={'HIDDEN'})

    def execute(self, context):
        s = context.scene.fskr
        it = _find(s, self.uid)
        if it is None:
            return {'CANCELLED'}
        cols = max(1, int(it.cols))
        cur = _pick_cell_get(it)
        make_main = self.any_src or not any(f.any_src for f in it.flaps)
        e = it.flaps.add()
        e["any_src"] = bool(make_main)
        self.any_src = bool(make_main)
        e.src = (cur // cols, cur % cols)
        e.name = (_tr("메인") if self.any_src
                  else "%d-%d" % (cur // cols, cur % cols))
        if not self.any_src:
            e.open = (cur // cols, cur % cols)
        _flap_update(None, context)
        return {'FINISHED'}


class FSKR_OT_atlas_flap_remove(bpy.types.Operator):
    bl_idname = "fskr.atlas_flap_remove"
    bl_label = "시퀀스 삭제"
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})
    index: bpy.props.IntProperty(options={'HIDDEN'})

    def execute(self, context):
        s = context.scene.fskr
        it = _find(s, self.uid)
        if it is None or not (0 <= self.index < len(it.flaps)):
            return {'CANCELLED'}
        it.flaps.remove(self.index)
        _flap_update(None, context)
        return {'FINISHED'}


class FSKR_OT_atlas_flap_auto(bpy.types.Operator):
    bl_idname = "fskr.atlas_flap_auto"
    bl_label = "위아래 시퀀스 자동 생성"
    bl_description = ("0-1, 2-3, 4-5행... 두 행씩 묶어서, 위 칸 = 열림, "
                      "아래 칸 = 닫힘 시퀀스를 만듭니다. 두 칸 모두 그림이 있는 "
                      "곳만 (투명 배경 이미지 기준)")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        s = context.scene.fskr
        it = _find(s, self.uid)
        if it is None:
            return {'CANCELLED'}
        if not _thumbs_ready(it):
            try:
                _thumbs_build(it)
            except Exception:
                pass
        fl = _PREV_FILLED.get(it.uid, {})
        rows, cols = int(it.rows), int(it.cols)
        have = {tuple(e.src) for e in it.flaps if not e.any_src}
        n = 0
        for r in range(0, rows - 1, 2):
            for c in range(cols):
                top, bot = (r, c), (r + 1, c)
                if fl and not (fl.get(top) and fl.get(bot)):
                    continue
                for src in (top, bot):
                    if src in have:
                        continue
                    e = it.flaps.add()
                    e.name = "%d-%d" % src
                    e.src = src
                    e.open = top
                    e.closed = bot
                    have.add(src)
                    n += 1
        _flap_update(None, context)
        self.report({'INFO'}, _tr("시퀀스 %d개 생성") % n)
        return {'FINISHED'}


atlas_classes = (
    FSKR_OT_atlas_cell_msel, FSKR_OT_atlas_cell_show,
    FSKR_OT_atlas_add, FSKR_OT_atlas_remove, FSKR_OT_atlas_build,
    FSKR_OT_atlas_thumbs, FSKR_OT_atlas_fit_uv, FSKR_OT_atlas_key,
    FSKR_OT_atlas_step, FSKR_OT_atlas_constant, FSKR_OT_atlas_lip_bake,
    FSKR_OT_atlas_flap_add, FSKR_OT_atlas_flap_remove,
    FSKR_OT_atlas_key_all, FSKR_OT_atlas_interp_apply,
    FSKR_OT_atlas_link_mouth, FSKR_OT_atlas_merge,
    FSKR_OT_atlas_flap_auto, FSKR_OT_atlas_alpha,
    FSKR_OT_atlas_cell_reset, FSKR_OT_atlas_cell_all,
    FSKR_OT_atlas_cell_clear_alias,
    FSKR_OT_atlas_talk_preview, FSKR_OT_atlas_seq_preview,
    FSKR_OT_image_open,
)
