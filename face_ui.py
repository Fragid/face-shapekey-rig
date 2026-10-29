"""스프라이트 방식 — 얼굴 캔버스 작업 순서 화면과 조작.

① 얼굴 캔버스   얼굴 메시에서 캔버스 메시 만들기
② 위치 마커     정면에서 눈·입·코 위치를 클릭으로 찍기
③ 스프라이트 시트  격자 시트를 행·열로 잘라 파츠 번호 매기기
④ 캔버스 레이어  + 로 파츠와 태그(그룹) 고르기 → 세부 조정
⑤ 표정 프리셋   배치를 표정으로 저장, 그룹 단위 적용
⑥ 입 (시퀀스·립싱크)  기존 스프라이트 시트 패널
"""
import bpy
import json
from mathutils import Vector, geometry
from bpy_extras import view3d_utils

from .core import (
    _EN,
    _JA,
    _ZH,
    _redraw_ui,
    _stable_items,
    _tr,
)
from . import atlas as AT
from . import eye as EY


_EN.update({"보간": "Interpolation",
            "선택한 키프레임만": "Selected keyframes only",
            "이 파츠의 모든 키": "All keys of this part",
            "보간 적용": "Apply interpolation",
            "부모에게서 물려받음: ": "Inherited from parent: ",
            "배치 (이 칸 %d-%d만)": "Placement (cell %d-%d only)",
            "입 칸마다 따로 저장됩니다. 다른 칸으로 바꾸면 그 칸의 값이 보입니다":
                "Saved per mouth cell. Switching cells shows that cell's values",
            "이 칸 값 지우기": "Clear this cell",
            "이 칸(%d-%d)만 크기·위치": "This cell (%d-%d) only: size/position",
            "입 모양마다 크기가 다르면 여기서 맞추세요. 다른 칸에는 영향 없음":
                "Fix per-mouth sizes here. Other cells are not affected",
            "입 전체 배치 (모든 입 칸 공통)": "Whole mouth placement (all cells)",
            "여기 값은 모든 입 모양에 똑같이 적용됩니다":
                "These values apply to every mouth shape",
            "한 칸만 바꾸려면 위의 '이 칸만 크기·위치'를 쓰세요":
                "To change one cell only, use 'This cell only' above",
            "준비": "Setup", "파츠": "Parts", "입": "Mouth", "시선": "Gaze",
            "탭": "Tab", "스프라이트 방식 작업 단계": "Sprite workflow step",
            "④ 캔버스 레이어 (파츠 배치)": "④ Canvas layers (parts)",
            "⑤ 표정 프리셋": "⑤ Expression presets",
            "⑥ 입 시퀀스 · 립싱크": "⑥ Mouth sequences · lip sync",
            "시선 (눈동자 이동)": "Gaze (pupil movement)",
            "① 얼굴 캔버스 · ② 위치 마커 · ③ 스프라이트 시트":
                "① Face canvas · ② Markers · ③ Sprite sheets"})
_JA.update({"준비": "準備", "파츠": "パーツ", "입": "口", "시선": "視線"})
_ZH.update({"준비": "准备", "파츠": "部件", "입": "嘴", "시선": "视线"})
_EN.update({
    "① 얼굴 캔버스": "① Face canvas",
    "② 위치 마커": "② Position markers",
    "③ 스프라이트 시트": "③ Sprite sheets",
    "④ 캔버스 레이어 (파츠 배치)": "④ Canvas layers (part placement)",
    "⑤ 표정 프리셋": "⑤ Expression presets",
    "⑥ 입 (시퀀스·립싱크)": "⑥ Mouth (sequences & lip sync)",
    "완료": "Done", "할 일": "To do",
    "리그": "Rig",
    "먼저 ①에서 얼굴 캔버스를 만드세요": "Create a face canvas in ① first",
    "먼저 ③에서 스프라이트 시트를 추가하세요": "Add a sprite sheet in ③ first",
    "마커 찍기": "Place marker", "다시 찍기": "Re-place",
    "찍지 않음": "Not placed",
    "정면 뷰에서 얼굴의 %s 위치를 클릭하세요 · 우클릭/ESC 취소": "Click the %s position on the face in front view · RMB/ESC to cancel",
    "캔버스 위를 클릭하세요": "Click on the canvas",
    "마커를 찍었습니다: ": "Marker placed: ",
    "시트 추가": "Add sheet", "파츠 %d개": "%d parts",
    "칸을 잘라 파츠 번호를 매기는 중…": "Slicing cells into numbered parts…",
    "파츠 추가": "Add part", "파츠": "Part", "시트": "Sheet", "태그": "Tag",
    "프리셋 저장": "Save preset", "프리셋 적용": "Apply preset",
    "적용할 그룹": "Groups to apply", "키 넣기": "Insert keys",
    "프리셋 덮어쓰기": "Overwrite preset", "프리셋 삭제": "Delete preset",
    "새 표정": "New expression",
    "마커 추가": "Add marker", "마커 삭제": "Remove marker", "찍기": "Place",
    "태그 추가": "Add tag", "태그 삭제": "Remove tag", "태그 (그룹)": "Tags (groups)",
    "+ 새 태그": "+ New tag", "새 태그 이름": "New tag name",
    "기준 마커": "Anchor marker", "얼굴 가운데": "Face center", "가운데": "Center",
    "쓰는 태그: ": "Used by tags: ", "기준: ": "Anchor: ",
    "태그 없음": "No tag", "기본 크기": "Default size", "기본 위치 Y": "Default Y",
    "자동 클리핑": "Auto clip", "새 파츠 기본값": "Defaults for new parts",
    "태그 없는 파츠는 항상 적용됩니다": "Parts without a tag are always applied",
    "입 시퀀스": "Mouth sequence",
    "이 마커를 쓸 태그 (선택 안 해도 됨)": "Tags that use this marker (optional)",
    "이름을 비우면 고른 태그 이름을 씁니다. 괄호 = 지금 쓰는 마커": "Empty name = picked tag's name. Parentheses = current marker",
    "눈": "Eye", "눈썹": "Brow", "감정표현": "Emotion",
    "이름을 직접 정하는 마커": "Marker with a custom name",
    "괄호 = 그 태그가 지금 쓰는 마커": "Parentheses = marker the tag uses now",
    "추가하고 바로 찍기": "Place right after adding",
    "얼굴 방향": "Face axis", "얼굴 정면 보기": "Face front view",
    "기초 태그 넣기": "Add base tags", "기초 태그 %d개 추가": "Added %d base tags",
})


# ------------------------------------------------------------------
# 공통
# ------------------------------------------------------------------

def _canvas(s):
    """지금 작업 중인 캔버스 스택."""
    if not len(s.eyes):
        return None
    st = EY._find(s, getattr(s, "canvas_uid", "")) if \
        getattr(s, "canvas_uid", "") else None
    return st or s.eyes[0]


def _canvas_items(self, context):
    items = []
    for i, st in enumerate(self.eyes):
        items.append((st.uid, "%s (%s)" % (st.name, st.target), "", i))
    if not items:
        items = [("NONE", "-", "", 0)]
    return _stable_items("fcv", items)


def _canvas_get(self):
    for i, st in enumerate(self.eyes):
        if st.uid == self.canvas_uid:
            return i
    return 0


def _canvas_set(self, v):
    if 0 <= v < len(self.eyes):
        self.canvas_uid = self.eyes[v].uid


EY.FSKR_Settings.__annotations__["canvas_uid"] = bpy.props.StringProperty(
    default="")
EY.FSKR_Settings.__annotations__["show_flatten"] = bpy.props.BoolProperty(
    name="머리 납작하게 (카메라 기준)", default=False)
EY.FSKR_Settings.__annotations__["show_canvas_add"] = bpy.props.BoolProperty(
    name="캔버스 추가 (모자 얼굴 · 감정표현 Plane)", default=False)
SPRITE_TABS = (
    ('SETUP', "준비", "① 얼굴 캔버스 · ② 위치 마커 · ③ 스프라이트 시트",
     'MESH_UVSPHERE', 0),
    ('PARTS', "파츠", "④ 캔버스 레이어 (파츠 배치)", 'IMAGE_DATA', 1),
    ('EXPR', "표정", "⑤ 표정 프리셋", 'SHAPEKEY_DATA', 2),
    ('MOUTH', "입", "⑥ 입 시퀀스 · 립싱크", 'SPEAKER', 3),
    ('GAZE', "시선", "시선 (눈동자 이동)", 'ORIENTATION_VIEW', 4),
    ('CTRL', "컨트롤러", "뷰포트 컨트롤러", 'ARMATURE_DATA', 5),
)
EY.FSKR_Settings.__annotations__["sprite_tab"] = bpy.props.EnumProperty(
    name="탭", items=SPRITE_TABS, default='SETUP',
    description="스프라이트 방식 작업 단계")
EY.FSKR_Settings.__annotations__["canvas_pick"] = bpy.props.EnumProperty(
    name="캔버스", items=_canvas_items, get=_canvas_get, set=_canvas_set)


def _step(layout, num, title, done, icon='NONE'):
    """단계 머리줄: ① 제목 ............ ✓ 완료 / ● 할 일."""
    box = layout.box()
    r = box.row()
    r.label(text="%s  %s" % (num, title), icon=icon)
    sub = r.row()
    sub.alignment = 'RIGHT'
    if done:
        sub.label(text=_tr("완료"), icon='CHECKMARK')
    else:
        sub.alert = True
        sub.label(text=_tr("할 일"), icon='RADIOBUT_ON')
    return box.column()


def _guide(col, lines):
    g = col.column(align=True)
    g.scale_y = 0.85
    for i, ln in enumerate(lines):
        g.label(text=ln, icon='DOT' if i else 'INFO')


def _sheet_duck(st, sh):
    d = EY._Duck("SH_%s_%s" % (st.uid, sh.uid), sh)
    return d


def _sheet_ready(st, sh):
    d = _sheet_duck(st, sh)
    return (d.uid in AT._PREV_ICONS
            and AT._PREV_SIG.get(d.uid) == AT._thumb_sig(d))


_SH_PENDING = set()


def _sheet_tick():
    try:
        s = bpy.context.scene.fskr
        for key in list(_SH_PENDING):
            suid, shuid = key
            st = EY._find(s, suid)
            sh = next((x for x in st.sheets if x.uid == shuid), None) \
                if st else None
            if sh is not None and sh.image:
                try:
                    AT._thumbs_build(_sheet_duck(st, sh))
                except Exception as e:
                    print("FSKR sheet thumbs:", e)
        _redraw_ui(bpy.context)
    except Exception:
        pass
    _SH_PENDING.clear()
    return None


def _sheet_request(st, sh):
    _SH_PENDING.add((st.uid, sh.uid))
    try:
        if not bpy.app.timers.is_registered(_sheet_tick):
            bpy.app.timers.register(_sheet_tick, first_interval=0.05)
    except Exception:
        pass


def sheet_parts(st, sh):
    """[(번호, 칸 index, r, c, icon)] — 그림이 있는 칸만, 행 우선 번호."""
    d = _sheet_duck(st, sh)
    filled = AT._PREV_FILLED.get(d.uid)
    icons = AT._PREV_ICONS.get(d.uid, {})
    cols, rows = max(1, int(sh.cols)), max(1, int(sh.rows))
    out = []
    n = 0
    for r in range(rows):
        for c in range(cols):
            if filled is not None and not filled.get((r, c), True):
                continue
            n += 1
            out.append((n, r * cols + c, r, c, icons.get((r, c), 0)))
    return out


def _part_name(sh, idx, num):
    try:
        nm = json.loads(sh.names or "{}").get(str(idx))
    except Exception:
        nm = None
    return nm or "%d" % num


# ------------------------------------------------------------------
# ② 위치 마커 (뷰포트 클릭)
# ------------------------------------------------------------------

def _hit_canvas_uv(context, ob, coord, region, rv3d):
    """화면 좌표 → 캔버스(평가된 메시) 위의 (UV, 로컬 좌표)."""
    org = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
    vec = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
    return ray_canvas_uv(context, ob, org, vec)


def ray_canvas_uv(context, ob, org, vec):
    """월드 광선 → 캔버스 위 가장 가까운 교차점의 (UV, 로컬 좌표)."""
    dg = context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    try:
        uvl = me.uv_layers.get("FSKR_Canvas") or me.uv_layers.active
        if uvl is None:
            return None
        inv = ob.matrix_world.inverted()
        o = inv @ org
        dvec = (inv.to_3x3() @ vec).normalized()
        try:
            me.calc_loop_triangles()
        except Exception:
            pass
        best = None
        for tri in me.loop_triangles:
            a, b, c = (me.vertices[i].co for i in tri.vertices)
            hit = geometry.intersect_ray_tri(a, b, c, dvec, o, True)
            if hit is None:
                continue
            dist = (hit - o).length
            if best is None or dist < best[0]:
                best = (dist, hit, tri, a, b, c)
        if best is None:
            return None
        _d, hit, tri, a, b, c = best
        ua, ub, uc = (Vector((*uvl.data[li].uv, 0.0)) for li in tri.loops)
        uv = geometry.barycentric_transform(hit, a, b, c, ua, ub, uc)
        return (uv.x, uv.y), tuple(hit)
    finally:
        ev.to_mesh_clear()


class FSKR_OT_marker_place(bpy.types.Operator):
    bl_idname = "fskr.marker_place"
    bl_label = "마커 찍기"
    bl_description = ("뷰포트에서 얼굴 캔버스 위를 클릭해 이 마커의 위치를 "
                      "정합니다 (정면 뷰 권장)")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        return _canvas(context.scene.fskr) is not None

    def _view(self, context, event):
        for area in context.window.screen.areas:
            if area.type != 'VIEW_3D':
                continue
            for rg in area.regions:
                if rg.type == 'WINDOW' and \
                        rg.x <= event.mouse_x < rg.x + rg.width and \
                        rg.y <= event.mouse_y < rg.y + rg.height:
                    return area, rg, area.spaces.active.region_3d
        return None, None, None

    def invoke(self, context, event):
        st = _canvas(context.scene.fskr)
        m = EY.find_marker(st, self.uid) if st else None
        if st is None or bpy.data.objects.get(st.target) is None:
            self.report({'ERROR'}, _tr("먼저 ①에서 얼굴 캔버스를 만드세요"))
            return {'CANCELLED'}
        if m is None:
            return {'CANCELLED'}
        _front_view(context, bpy.data.objects.get(st.target))
        context.workspace.status_text_set(
            _tr("정면 뷰에서 얼굴의 %s 위치를 클릭하세요 · 우클릭/ESC 취소")
            % m.name)
        context.window.cursor_modal_set('CROSSHAIR')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def _end(self, context):
        try:
            context.workspace.status_text_set(None)
            context.window.cursor_modal_restore()
        except Exception:
            pass

    def modal(self, context, event):
        if event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            self._end(context)
            return {'CANCELLED'}
        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE',
                          'TRACKPADPAN', 'TRACKPADZOOM'}:
            return {'PASS_THROUGH'}   # 화면 돌리기/줌은 허용
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            area, rg, rv3d = self._view(context, event)
            if area is None:
                return {'RUNNING_MODAL'}
            st = _canvas(context.scene.fskr)
            m = EY.find_marker(st, self.uid)
            ob = bpy.data.objects.get(st.target)
            coord = (event.mouse_x - rg.x, event.mouse_y - rg.y)
            res = _hit_canvas_uv(context, ob, coord, rg, rv3d)
            if res is None:
                self.report({'WARNING'}, _tr("캔버스 위를 클릭하세요"))
                return {'RUNNING_MODAL'}
            set_marker(st, m, *res)
            self._end(context)
            self.report({'INFO'}, _tr("마커를 찍었습니다: ") + m.name)
            _redraw_ui(context)
            return {'FINISHED'}
        return {'RUNNING_MODAL'}


def _front_view(context, ob):
    """숫자패드 1처럼 얼굴 정면 뷰 (얼굴 방향 설정 반영) + 캔버스를 가운데로."""
    EY.face_view(context, ob)


def set_marker(st, m, uv, co=None):
    """마커 저장 (캔버스 재구성은 uv 업데이트로 자동)."""
    if co is not None:
        m.co = co
    m.placed = True
    m.uv = (float(uv[0]), float(uv[1]))


def _new_uid(coll, prefix):
    used = {x.uid for x in coll}
    i = 1
    while "%s%d" % (prefix, i) in used:
        i += 1
    return "%s%d" % (prefix, i)


_BASE_NAMES = ("눈", "눈썹", "입", "감정표현")


def _marker_choice_items(self, context):
    st = _canvas(bpy.context.scene.fskr)
    have = {m.name for m in st.markers} if st else set()
    items = []
    for i, nm in enumerate(_BASE_NAMES):
        tn = _tr(nm)
        items.append((nm, tn, _tr("'%s' 마커를 만들고 '%s' 태그와 연결")
                      % (tn, tn), 'CHECKMARK' if (nm in have or tn in have)
                      else 'NONE', i))
    items.append(("CUSTOM", "+", _tr("이름을 직접 정하는 마커"), 'NONE',
                  len(_BASE_NAMES)))
    return _stable_items("fmc_%d" % len(have), items)


class FSKR_OT_face_front_view(bpy.types.Operator):
    bl_idname = "fskr.face_front_view"
    bl_label = "얼굴 정면 보기"
    bl_description = ("숫자패드 1처럼 얼굴 정면 뷰로 바꾸고 캔버스를 화면 "
                      "가운데로 (얼굴 방향 설정 반영)")

    def execute(self, context):
        st = _canvas(context.scene.fskr)
        EY.face_view(context, bpy.data.objects.get(st.target) if st else None)
        return {'FINISHED'}


class FSKR_OT_marker_add(bpy.types.Operator):
    bl_idname = "fskr.marker_add"
    bl_label = "마커 추가"
    bl_description = ("파츠를 놓을 기준점을 추가합니다. 눈·눈썹·입·감정표현을 "
                      "고르거나 + 로 이름을 직접 정합니다")
    bl_options = {'REGISTER', 'UNDO'}

    choice: bpy.props.EnumProperty(name="마커", items=_marker_choice_items)
    name: bpy.props.StringProperty(name="이름", default="")
    place_now: bpy.props.BoolProperty(
        name="추가하고 바로 찍기", default=True,
        description="OK를 누르면 정면 뷰로 바뀌고 바로 얼굴을 클릭해 위치를 "
                    "찍습니다")
    _ui: bool = False

    @classmethod
    def poll(cls, context):
        return _canvas(context.scene.fskr) is not None

    def invoke(self, context, event):
        self.name = ""
        st = _canvas(context.scene.fskr)
        for g in st.tags:
            g.mk_sel = False
        # 아직 없는 기초 마커를 먼저 골라 둠
        have = {m.name for m in st.markers}
        nxt = next((n for n in _BASE_NAMES
                    if n not in have and _tr(n) not in have), "CUSTOM")
        try:
            self.choice = nxt
        except TypeError:
            pass
        self._ui = True
        return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, context):
        st = _canvas(context.scene.fskr)
        col = self.layout.column()
        r = col.row(align=True)
        r.scale_y = 1.6
        r.prop(self, "choice", expand=True)
        if self.choice != "CUSTOM":
            tn9 = _tr(self.choice)
            ex = next((m for m in st.markers
                       if m.name in (self.choice, tn9)), None)
            sub = col.row()
            sub.active = False
            if ex is not None:
                sub.label(text=_tr("이미 있는 '%s' 마커에 '%s' 태그를 연결합니다")
                          % (ex.name, tn9), icon='LINKED')
            else:
                sub.label(text=_tr("'%s' 마커를 만들고 '%s' 태그와 연결합니다 "
                                   "(태그가 없으면 같이 만듦)")
                          % (tn9, tn9), icon='INFO')
            col.prop(self, "place_now")
            return
        col.separator()
        col.prop(self, "name")
        if len(st.tags):
            col.label(text=_tr("이 마커를 쓸 태그 (선택 안 해도 됨)"),
                      icon='OUTLINER_COLLECTION')
            g = col.grid_flow(columns=2, even_columns=True, align=True)
            for tg in st.tags:
                m = EY.find_marker(st, tg.marker)
                g.prop(tg, "mk_sel", toggle=True,
                       text=tg.name + ("  (%s)" % m.name if m else ""))
            sub = col.row()
            sub.active = False
            sub.label(text=_tr("괄호 = 그 태그가 지금 쓰는 마커"))
        col.separator()
        col.prop(self, "place_now")

    def execute(self, context):
        s = context.scene.fskr
        st = _canvas(s)
        if self.choice and self.choice != "CUSTOM":
            nm = self.choice
            tn = _tr(nm)     # 이름은 지금 UI 언어로 (예전 한국어 이름도 인정)
            m = next((x for x in st.markers if x.name in (nm, tn)), None)
            if m is None:
                m = st.markers.add()
                m.uid = _new_uid(st.markers, "M")
                m.name = tn
            g = next((x for x in st.tags if x.name in (nm, tn)), None)
            if g is None:  # 기초 태그가 없으면 기본값으로 만듦
                spec = next(b for b in BASE_TAGS if b[0] == nm)
                g = new_tag(st, tn, m.uid)
                g.sym, g.look, g.mouth, g.size, g.dy = spec[2:]
                g.expand = False
            g.marker = m.uid
            EY.eye_build(s, st)
            _redraw_ui(context)
            self._start_place(context, m)
            return {'FINISHED'}
        picked = [g for g in st.tags if g.mk_sel]
        m = st.markers.add()
        m.uid = _new_uid(st.markers, "M")
        m.name = (self.name or (picked[0].name if picked else "")
                  or "%s %d" % (_tr("마커"), len(st.markers)))
        for g in picked:
            g.marker = m.uid
            g.mk_sel = False
        if picked:
            EY.eye_build(s, st)
        _redraw_ui(context)
        self._start_place(context, m)
        return {'FINISHED'}

    def _start_place(self, context, m):
        """추가 직후 바로 찍기 (창에서 OK를 눌렀을 때만)."""
        if not (self.place_now and self._ui):
            return
        try:
            bpy.ops.fskr.marker_place('INVOKE_DEFAULT', uid=m.uid)
        except Exception as e:
            print("FSKR place now:", e)


class FSKR_OT_marker_remove(bpy.types.Operator):
    bl_idname = "fskr.marker_remove"
    bl_label = "마커 삭제"
    bl_description = ("마커를 지웁니다. 이 마커를 쓰던 태그는 얼굴 가운데 "
                      "기준이 됩니다")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        s = context.scene.fskr
        st = _canvas(s)
        i = next((k for k, m in enumerate(st.markers) if m.uid == self.uid),
                 -1)
        if i < 0:
            return {'CANCELLED'}
        st.markers.remove(i)
        for g in st.tags:
            if g.marker == self.uid:
                g.marker = ""
        EY.eye_build(s, st)
        _redraw_ui(context)
        return {'FINISHED'}


# 마커 표시 (뷰포트)
_MK = {"h": None}


def _marker_sym(st, m):
    """이 마커를 쓰는 태그 중 대칭 태그가 있으면 반대쪽도 표시."""
    return any(g.marker == m.uid and g.sym for g in st.tags) or any(
        L.sym and EY.find_tag(st, L.tag) is not None
        and EY.find_tag(st, L.tag).marker == m.uid for L in st.layers)


def _draw_markers():
    ctx = bpy.context
    try:
        s = ctx.scene.fskr
        st = _canvas(s)
        if st is None or not st.show_markers or s.ui_mode != 'SPRITE':
            return
        ob = bpy.data.objects.get(st.target)
        if ob is None or not ob.visible_get():
            return
    except Exception:
        return
    import blf
    import gpu
    from gpu_extras.batch import batch_for_shader
    region, rv3d = ctx.region, ctx.space_data.region_3d
    pts = []
    for m in st.markers:
        if not m.placed:
            continue
        co = tuple(m.co)
        pts.append((m.name, ob.matrix_world @ Vector(co)))
        if _marker_sym(st, m):
            mc = list(co)
            li = EY.face_lateral_index(s)
            mc[li] = -mc[li]
            pts.append((m.name + _tr(" (대칭)"), ob.matrix_world @ Vector(mc)))
    if not pts:
        return
    sh = gpu.shader.from_builtin('UNIFORM_COLOR')
    segs = []
    labels = []
    for lab, w in pts:
        p = view3d_utils.location_3d_to_region_2d(region, rv3d, w)
        if p is None:
            continue
        r = 9
        segs += [(p.x - r, p.y), (p.x + r, p.y), (p.x, p.y - r),
                 (p.x, p.y + r)]
        labels.append((lab, p))
    if segs:
        gpu.state.line_width_set(2.0)
        bt = batch_for_shader(sh, 'LINES', {"pos": segs})
        sh.bind()
        sh.uniform_float("color", (1.0, 0.25, 0.45, 1.0))
        bt.draw(sh)
        gpu.state.line_width_set(1.0)
    fid = 0
    blf.size(fid, 13)
    for lab, p in labels:
        blf.color(fid, 1.0, 0.35, 0.55, 1.0)
        blf.position(fid, p.x + 12, p.y + 6, 0)
        blf.draw(fid, lab)


# ------------------------------------------------------------------
# 태그 (사용자 정의)
# ------------------------------------------------------------------

class FSKR_OT_tag_add(bpy.types.Operator):
    bl_idname = "fskr.tag_add"
    bl_label = "태그 추가"
    bl_description = ("파츠 그룹(태그)을 만듭니다. 기준 마커와 새 파츠의 "
                      "기본값(대칭·시선·입·크기)을 정합니다")
    bl_options = {'REGISTER', 'UNDO'}

    name: bpy.props.StringProperty(name="이름", default="")

    @classmethod
    def poll(cls, context):
        return _canvas(context.scene.fskr) is not None

    def invoke(self, context, event):
        self.name = ""
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        st = _canvas(context.scene.fskr)
        new_tag(st, self.name)
        _redraw_ui(context)
        return {'FINISHED'}


def new_tag(st, name, marker=""):
    g = st.tags.add()
    g.uid = _new_uid(st.tags, "T")
    g.name = name or "%s %d" % (_tr("태그"), len(st.tags))
    g.marker = marker
    g.expand = True
    return g


# 기초 태그: (이름, 마커 이름, 대칭, 시선, 입, 크기, 위치 Y)
BASE_TAGS = (
    ("눈", "눈", True, False, False, 0.2, 0.0),
    ("눈썹", "눈", True, False, False, 0.2, 0.09),
    ("입", "입", False, False, True, 0.16, 0.0),
    ("감정표현", "", False, False, False, 0.15, 0.0),
)


def ensure_base_tags(st):
    """기초 태그(눈·눈썹·입·감정표현)와 그 기준 마커(눈·입)를 없을 때만 추가."""
    added = 0
    for name, mk, sym, look, mouth, size, dy in BASE_TAGS:
        # 이름은 지금 UI 언어로 (예전 한국어 이름도 같은 태그로 봄)
        tn, tm = _tr(name), (_tr(mk) if mk else "")
        if any(g.name in (name, tn) for g in st.tags):
            continue
        muid = ""
        if mk:
            m = next((x for x in st.markers if x.name in (mk, tm)), None)
            if m is None:
                m = st.markers.add()
                m.uid = _new_uid(st.markers, "M")
                m.name = tm
            muid = m.uid
        g = new_tag(st, tn, muid)
        g.sym, g.look, g.mouth, g.size, g.dy = sym, look, mouth, size, dy
        g.expand = False
        added += 1
    return added


class FSKR_OT_tag_base(bpy.types.Operator):
    bl_idname = "fskr.tag_base"
    bl_label = "기초 태그 넣기"
    bl_description = ("눈·눈썹·입·감정표현 태그와 눈·입 마커를 없는 것만 "
                      "추가합니다")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return _canvas(context.scene.fskr) is not None

    def execute(self, context):
        n = ensure_base_tags(_canvas(context.scene.fskr))
        self.report({'INFO'}, _tr("기초 태그 %d개 추가") % n)
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_tag_remove(bpy.types.Operator):
    bl_idname = "fskr.tag_remove"
    bl_label = "태그 삭제"
    bl_description = ("태그를 지웁니다. 이 태그였던 파츠는 '태그 없음'(얼굴 "
                      "가운데 기준)이 됩니다")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        s = context.scene.fskr
        st = _canvas(s)
        i = next((k for k, g in enumerate(st.tags) if g.uid == self.uid), -1)
        if i < 0:
            return {'CANCELLED'}
        st.tags.remove(i)
        for g in st.tags:
            if g.clip_tag == self.uid:
                g.clip_tag = ""
        for L in st.layers:
            if L.tag == self.uid:
                L["tag"] = ""
        if st.tag_filter == self.uid:
            st.tag_filter = ""
        EY.eye_build(s, st)
        _redraw_ui(context)
        return {'FINISHED'}


# ------------------------------------------------------------------
# ③ 스프라이트 시트
# ------------------------------------------------------------------

# ------------------------------------------------------------------
# 가장자리 흰 선 제거 (투명 픽셀의 숨은 색 채우기)
#   PNG의 완전 투명 픽셀에도 색(보통 흰색)이 들어 있어, 텍스처를 부드럽게
#   읽을 때 그 색이 가장자리에 섞여 얇은 흰 선이 생긴다. 투명 픽셀의 색을
#   가까운 그림 색으로 채우면(알파는 그대로) 사라진다.
# ------------------------------------------------------------------

def fix_edge_bleed(img):
    """투명 픽셀의 색을 가까운 그림 색으로 (피라미드 채우기, 수 초 이내)."""
    import numpy as np
    w, h = img.size
    if w <= 0 or h <= 0:
        return 0
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)
    filled = px[..., 3] > 0.004
    if filled.all() or not filled.any():
        return 0
    m = filled.astype(np.float32)
    levels = [(px[..., :3] * m[..., None], m)]
    while max(levels[-1][1].shape) > 1:
        c, wt = levels[-1]
        H, W = wt.shape
        H2, W2 = H + (H & 1), W + (W & 1)
        if (H2, W2) != (H, W):
            c = np.pad(c, ((0, H2 - H), (0, W2 - W), (0, 0)))
            wt = np.pad(wt, ((0, H2 - H), (0, W2 - W)))
        c = c.reshape(H2 // 2, 2, W2 // 2, 2, 3).sum((1, 3))
        wt = wt.reshape(H2 // 2, 2, W2 // 2, 2).sum((1, 3))
        levels.append((c, wt))
    # 가장 거친 단계부터 내려오며 빈 곳을 위 단계 색으로
    c, wt = levels[-1]
    col = c / np.maximum(wt, 1e-8)[..., None]
    for c, wt in reversed(levels[:-1]):
        H, W = wt.shape
        up = np.repeat(np.repeat(col, 2, 0), 2, 1)[:H, :W]
        own = c / np.maximum(wt, 1e-8)[..., None]
        col = np.where((wt > 0)[..., None], own, up)
    hole = ~filled
    px[..., :3] = np.where(hole[..., None], col, px[..., :3])
    img.pixels.foreach_set(px.ravel())
    img.update()
    try:
        img.pack()
    except Exception:
        pass
    img["fskr_bleed_fixed"] = 1
    return int(hole.sum())


class FSKR_OT_sheet_fix_edges(bpy.types.Operator):
    bl_idname = "fskr.sheet_fix_edges"
    bl_label = "가장자리 흰 선 제거"
    bl_description = ("파츠 가장자리에 얇은 흰 선이 보일 때. 투명한 곳에 숨어 "
                      "있는 흰색을 그림 색으로 채웁니다 (그림·투명도는 그대로). "
                      "고친 이미지는 .blend 안에 저장됩니다")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        s = context.scene.fskr
        st = _canvas(s)
        sh = next((x for x in st.sheets if x.uid == self.uid), None) \
            if st else None
        img = bpy.data.images.get(sh.image) if sh and sh.image else None
        if img is None:
            return {'CANCELLED'}
        n = fix_edge_bleed(img)
        self.report({'INFO'}, _tr("투명 픽셀 %d개의 색을 채웠습니다") % n)
        return {'FINISHED'}


class FSKR_OT_sheet_add(bpy.types.Operator):
    bl_idname = "fskr.sheet_add"
    bl_label = "시트 추가"
    bl_description = ("격자로 그린 스프라이트 시트 이미지를 불러와 행·열로 "
                      "자르고 파츠 번호를 매깁니다")
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    filter_image: bpy.props.BoolProperty(default=True, options={'HIDDEN'})
    filter_folder: bpy.props.BoolProperty(default=True, options={'HIDDEN'})
    relative_path: bpy.props.BoolProperty(name="상대 경로", default=True)
    cols: bpy.props.IntProperty(name="열 (가로 칸 수)", default=8, min=1,
                                max=64)
    rows: bpy.props.IntProperty(name="행 (세로 칸 수)", default=8, min=1,
                                max=64)

    @classmethod
    def poll(cls, context):
        return _canvas(context.scene.fskr) is not None

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def draw(self, context):
        col = self.layout.column()
        col.prop(self, "cols")
        col.prop(self, "rows")
        col.prop(self, "relative_path")

    def execute(self, context):
        import os
        st = _canvas(context.scene.fskr)
        path = bpy.path.abspath(self.filepath) if self.filepath else ""
        path = os.path.normpath(path) if path else ""
        if not path or not os.path.isfile(path):
            self.report({'ERROR'}, _tr("이미지 파일을 고르세요"))
            return {'CANCELLED'}
        img = bpy.data.images.load(path, check_existing=True)
        if img.packed_file is None and not img.get("fskr_bleed_fixed"):
            try:
                fix_edge_bleed(img)
            except Exception as e:
                print("FSKR edge fix:", e)
        if self.relative_path and bpy.data.filepath:
            try:
                img.filepath = bpy.path.relpath(path)
            except Exception:
                pass
        try:
            img.alpha_mode = 'STRAIGHT'
        except Exception:
            pass
        used = {x.uid for x in st.sheets}
        i = 1
        while "S%d" % i in used:
            i += 1
        sh = st.sheets.add()
        sh.uid = "S%d" % i
        sh.name = os.path.splitext(os.path.basename(path))[0]
        sh.image = img.name
        sh.cols, sh.rows = self.cols, self.rows
        st.sheet_index = len(st.sheets) - 1
        try:
            AT._thumbs_build(_sheet_duck(st, sh))
        except Exception:
            _sheet_request(st, sh)
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_sheet_remove(bpy.types.Operator):
    bl_idname = "fskr.sheet_remove"
    bl_label = "시트 삭제"
    bl_description = "시트를 목록에서 뺍니다 (이미 배치한 파츠는 그대로)"
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        st = _canvas(context.scene.fskr)
        i = next((k for k, x in enumerate(st.sheets) if x.uid == self.uid),
                 -1)
        if i < 0:
            return {'CANCELLED'}
        st.sheets.remove(i)
        st.sheet_index = max(0, min(len(st.sheets) - 1, st.sheet_index))
        return {'FINISHED'}


def _sheet_users(s, st, sh, old_image):
    """이 시트를 쓰는 파츠 레이어와 입 스프라이트 시트."""
    lays = [L for L in st.layers if L.sheet == sh.uid]
    ats = [a for a in s.atlases if a.image == old_image
           and a.method == 'CANVAS' and a.target == st.target]
    return lays, ats


def _sheet_refresh(context, s, st, sh, lays, ats):
    """썸네일 다시 자르고, 이 시트를 쓰는 곳을 다시 만든다."""
    AT._thumbs_free(_sheet_duck(st, sh).uid)
    for L in lays:
        AT._thumbs_free(EY._thumb_uid(st, L))
    for a in ats:
        AT._thumbs_free(a.uid)
    try:
        AT._thumbs_build(_sheet_duck(st, sh))
    except Exception:
        _sheet_request(st, sh)
    if lays:
        EY.eye_build(s, st)
    for a in ats:
        try:
            AT._build(s, a)
        except Exception:
            pass
    _redraw_ui(context)


class FSKR_OT_sheet_reload(bpy.types.Operator):
    bl_idname = "fskr.sheet_reload"
    bl_label = "이미지 다시 불러오기"
    bl_description = ("디스크의 시트 이미지 파일을 다시 읽습니다 "
                      "(다른 프로그램에서 고친 뒤 사용)")
    bl_options = {'REGISTER'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        s = context.scene.fskr
        st = _canvas(s)
        sh = next((x for x in st.sheets if x.uid == self.uid), None) \
            if st else None
        img = bpy.data.images.get(sh.image) if sh and sh.image else None
        if img is None:
            self.report({'ERROR'}, _tr("시트 이미지를 찾을 수 없습니다"))
            return {'CANCELLED'}
        try:
            if img.packed_file is not None:   # 고친 사본 말고 디스크 파일
                img.unpack(method='REMOVE')
            img.reload()
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        try:
            fix_edge_bleed(img)
        except Exception as e:
            print("FSKR edge fix:", e)
        lays, ats = _sheet_users(s, st, sh, sh.image)
        _sheet_refresh(context, s, st, sh, lays, ats)
        self.report({'INFO'}, _tr("다시 불러왔습니다: ") + img.name)
        return {'FINISHED'}


class FSKR_OT_sheet_replace(bpy.types.Operator):
    bl_idname = "fskr.sheet_replace"
    bl_label = "다른 파일로 바꾸기"
    bl_description = ("이 시트의 이미지를 다른 파일로 바꿉니다. 이 시트에서 "
                      "올린 파츠와 입 시퀀스도 새 이미지를 씁니다")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})
    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    filter_image: bpy.props.BoolProperty(default=True, options={'HIDDEN'})
    filter_folder: bpy.props.BoolProperty(default=True, options={'HIDDEN'})
    relative_path: bpy.props.BoolProperty(name="상대 경로", default=True)
    cols: bpy.props.IntProperty(name="열 (가로 칸 수)", default=4, min=1,
                                max=64)
    rows: bpy.props.IntProperty(name="행 (세로 칸 수)", default=4, min=1,
                                max=64)

    def invoke(self, context, event):
        st = _canvas(context.scene.fskr)
        sh = next((x for x in st.sheets if x.uid == self.uid), None) \
            if st else None
        if sh is None:
            return {'CANCELLED'}
        self.cols, self.rows = sh.cols, sh.rows
        img = bpy.data.images.get(sh.image) if sh.image else None
        if img is not None and img.filepath:
            self.filepath = bpy.path.abspath(img.filepath)
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def draw(self, context):
        col = self.layout.column()
        col.prop(self, "cols")
        col.prop(self, "rows")
        col.prop(self, "relative_path")
        col.label(text=_tr("칸 배치가 같아야 파츠 번호가 유지됩니다"),
                  icon='INFO')

    def execute(self, context):
        import os
        s = context.scene.fskr
        st = _canvas(s)
        sh = next((x for x in st.sheets if x.uid == self.uid), None) \
            if st else None
        if sh is None:
            return {'CANCELLED'}
        path = bpy.path.abspath(self.filepath) if self.filepath else ""
        path = os.path.normpath(path) if path else ""
        if not path or not os.path.isfile(path):
            self.report({'ERROR'}, _tr("이미지 파일을 고르세요"))
            return {'CANCELLED'}
        old = sh.image
        lays, ats = _sheet_users(s, st, sh, old)
        img = bpy.data.images.load(path, check_existing=True)
        if img.name == old:
            try:
                if img.packed_file is not None:
                    img.unpack(method='REMOVE')
                img.reload()
            except Exception:
                pass
        try:
            fix_edge_bleed(img)
        except Exception as e:
            print("FSKR edge fix:", e)
        if self.relative_path and bpy.data.filepath:
            try:
                img.filepath = bpy.path.relpath(path)
            except Exception:
                pass
        try:
            img.alpha_mode = 'STRAIGHT'
        except Exception:
            pass
        sh.image = img.name
        sh.cols, sh.rows = self.cols, self.rows
        for L in lays:
            L["image"] = img.name
            L["cols"] = sh.cols
            L["rows"] = sh.rows
        for a in ats:
            a["image"] = img.name
            a["cols"] = sh.cols
            a["rows"] = sh.rows
        _sheet_refresh(context, s, st, sh, lays, ats)
        self.report({'INFO'}, _tr("이미지를 바꿨습니다: ") + img.name)
        return {'FINISHED'}


class FSKR_OT_sheet_slice(bpy.types.Operator):
    bl_idname = "fskr.sheet_slice"
    bl_label = "다시 자르기"
    bl_description = "행·열을 바꾼 뒤 칸을 다시 잘라 파츠 번호를 매깁니다"
    bl_options = {'REGISTER'}

    uid: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        st = _canvas(context.scene.fskr)
        sh = next((x for x in st.sheets if x.uid == self.uid), None)
        if sh is None:
            return {'CANCELLED'}
        AT._thumbs_build(_sheet_duck(st, sh))
        _redraw_ui(context)
        return {'FINISHED'}


# ------------------------------------------------------------------
# ④ 파츠 추가 (+): 파츠와 태그 고르기
# ------------------------------------------------------------------

def _add_sheet_items(self, context):
    st = _canvas(bpy.context.scene.fskr)
    items = []
    if st is not None:
        for i, sh in enumerate(st.sheets):
            items.append((sh.uid, sh.name, "", i))
    if not items:
        items = [("NONE", "-", "", 0)]
    return _stable_items("fas", items)


def _add_part_items(self, context):
    st = _canvas(bpy.context.scene.fskr)
    sh = next((x for x in st.sheets if x.uid == self.sheet), None) \
        if st else None
    items = []
    if sh is not None:
        if not _sheet_ready(st, sh):
            _sheet_request(st, sh)
        for num, idx, r, c, icon in sheet_parts(st, sh):
            items.append((str(idx), "%s  (%d-%d)" % (
                _part_name(sh, idx, num), r, c), "", icon, idx))
    if not items:
        items = [("0", "-", "", 0, 0)]
    return _stable_items("fap_%s" % self.sheet, items)


def _add_tag_items(self, context):
    st = _canvas(bpy.context.scene.fskr)
    items = []
    if st is not None:
        for i, g in enumerate(st.tags):
            items.append((g.uid, g.name, "", i))
    items.append(("__NEW__", _tr("+ 새 태그"), _tr("이름을 정해 새로 만듭니다"),
                  len(items)))
    return _stable_items("fat", items)


def _add_marker_items(self, context):
    st = _canvas(bpy.context.scene.fskr)
    items = [("NONE", _tr("얼굴 가운데"), "", 0)]
    if st is not None:
        for i, m in enumerate(st.markers):
            items.append((m.uid, m.name, "", i + 1))
    return _stable_items("fam", items)


class FSKR_OT_part_add(bpy.types.Operator):
    bl_idname = "fskr.part_add"
    bl_label = "파츠 추가"
    bl_description = ("시트에서 파츠를 고르고 태그를 정해 캔버스에 올립니다. "
                      "태그의 기준 마커 위치에 놓입니다")
    bl_options = {'REGISTER', 'UNDO'}

    sheet: bpy.props.EnumProperty(name="시트", items=_add_sheet_items)
    part: bpy.props.EnumProperty(name="파츠", items=_add_part_items)
    tag: bpy.props.EnumProperty(name="태그", items=_add_tag_items)
    new_name: bpy.props.StringProperty(name="새 태그 이름", default="")
    part_name: bpy.props.StringProperty(
        name="파츠 이름", default="",
        description="비워 두면 '태그 이름 + 번호'로 자동으로 붙습니다")
    ime_name: bpy.props.BoolProperty(
        name="입력 창으로 이름 쓰기", default=False, options={'SKIP_SAVE'},
        description="만든 뒤 한중일 입력 창을 띄워 이름을 씁니다 (Blender에서 "
                    "한글 입력이 안 될 때)")
    use_dlg: bpy.props.BoolProperty(default=False,
                                    options={'HIDDEN', 'SKIP_SAVE'})
    new_marker: bpy.props.EnumProperty(name="기준 마커",
                                       items=_add_marker_items)

    @classmethod
    def poll(cls, context):
        st = _canvas(context.scene.fskr)
        return st is not None and len(st.sheets) > 0

    def invoke(self, context, event):
        st = _canvas(context.scene.fskr)
        if 0 <= st.sheet_index < len(st.sheets):
            try:
                self.sheet = st.sheets[st.sheet_index].uid
            except TypeError:
                pass
        # 지금 고른 파츠의 태그를 기본으로
        if 0 <= st.layer_index < len(st.layers) and \
                EY.find_tag(st, st.layers[st.layer_index].tag) is not None:
            try:
                self.tag = st.layers[st.layer_index].tag
            except TypeError:
                pass
        self.new_name = ""
        self.part_name = ""
        context.window_manager.fskr_dlg_part = ""
        context.window_manager.fskr_dlg_tag = ""
        self.use_dlg = True
        return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, context):
        st = _canvas(context.scene.fskr)
        col = self.layout.column()
        col.prop(self, "sheet")
        col.template_icon_view(self, "part", show_labels=True, scale=8.0,
                               scale_popup=4.0)
        col.prop(self, "part", text=_tr("파츠"))
        col.separator()
        col.prop(self, "tag")
        wm = context.window_manager
        r9 = col.row(align=True)
        r9.prop(wm, "fskr_dlg_part", text=_tr("파츠 이름"),
                placeholder=_tr("비우면 자동 (태그 이름 + 번호)"))
        op = r9.operator("fskr.ime_dlg", text="", icon='FONTPREVIEW')
        op.attr, op.label = "fskr_dlg_part", _tr("파츠 이름")
        if self.tag == "__NEW__":
            b = col.box().column()
            r8 = b.row(align=True)
            r8.prop(wm, "fskr_dlg_tag", text=_tr("새 태그 이름"))
            op = r8.operator("fskr.ime_dlg", text="", icon='FONTPREVIEW')
            op.attr, op.label = "fskr_dlg_tag", _tr("새 태그 이름")
            b.prop(self, "new_marker")
            if not len(st.markers):
                b.label(text=_tr("②에서 마커를 먼저 만들면 기준점으로 고를 수 "
                                 "있습니다"), icon='INFO')
        else:
            g = EY.find_tag(st, self.tag)
            if g is not None:
                m = EY.find_marker(st, g.marker)
                bits = [_tr("기준: ") + (m.name if m else _tr("얼굴 가운데"))]
                if g.sym:
                    bits.append(_tr("대칭"))
                if g.look:
                    bits.append(_tr("시선"))
                if g.mouth:
                    bits.append(_tr("입 시퀀스"))
                col.label(text=" · ".join(bits), icon='INFO')

    def execute(self, context):
        s = context.scene.fskr
        st = _canvas(s)
        rig = s.rig
        sh = next((x for x in st.sheets if x.uid == self.sheet), None)
        if sh is None or rig is None:
            return {'CANCELLED'}
        if self.use_dlg:   # 창에서 쓴 이름 (한중일 입력 창으로 쓴 것 포함)
            wm = context.window_manager
            self.part_name = wm.fskr_dlg_part
            self.new_name = wm.fskr_dlg_tag
        if self.tag == "__NEW__" or not self.tag:
            g = new_tag(st, self.new_name,
                        "" if self.new_marker == "NONE" else self.new_marker)
        else:
            g = EY.find_tag(st, self.tag)
            if g is None:
                g = new_tag(st, self.new_name)
        idx = int(self.part or 0)
        num = next((n for n, i9, *_ in sheet_parts(st, sh) if i9 == idx),
                   idx + 1)
        sel = st.layer_index if len(st.layers) else -1
        L = st.layers.add()
        L.lid = EY._new_lid(st)
        L["name"] = self.part_name.strip() or \
            "%s %s" % (g.name, _part_name(sh, idx, num))
        EY.part_set_include(st, L.lid)  # 폴더 보기 중이면 그 폴더에 추가
        L["tag"] = g.uid
        L["sheet"] = sh.uid
        L["image"] = sh.image
        L["cols"] = sh.cols
        L["rows"] = sh.rows
        L["sym"] = g.sym
        L["look"] = g.look
        L["over"] = g.over
        # 새 파츠 위치: 선택한 파츠 바로 위. 선택이 없으면 같은 태그의
        # 맨 앞. 자동 클리핑 태그가 있으면 그
        # 태그의 가장 아래 파츠 바로 위 (예: 눈동자 → 흰자 바로 위)
        last = len(st.layers) - 1
        clip_lid = ""
        # 이 태그 + 이 태그로 클리핑되는 태그(예: 흰자 ← 눈동자)는 한 묶음
        dep = {x.uid for x in st.tags if x.clip_tag == g.uid} | {g.uid}
        tgt = next((k for k, x in enumerate(st.layers)
                    if k != last and x.tag in dep), None)
        if g.clip_tag:
            base = [k for k, x in enumerate(st.layers)
                    if k != last and x.tag == g.clip_tag]
            if base:
                clip_lid = st.layers[base[-1]].lid
                if tgt is None:
                    tgt = base[-1]
        if tgt is None:
            tgt = 0
        # 선택한 파츠가 있으면 그 바로 위에 (선택 파츠는 한 칸 아래로)
        if 0 <= sel < last:
            tgt = sel
        st.layers.move(last, tgt)
        st.layer_index = tgt
        L = st.layers[tgt]
        # 선택한 파츠가 누군가의 자식이면 새 파츠도 같은 부모 아래로
        sel_par = st.layers[tgt + 1].parent \
            if (0 <= sel < last and tgt == sel and tgt + 1 < len(st.layers)) \
            else ""
        if clip_lid:
            L["clip"] = clip_lid
        if g.mouth:
            it = _mouth_atlas_for(context, s, st, sh, idx)
            L["kind"] = 1
            L["atlas"] = it.uid
        else:
            EY._ensure_prop(rig, EY._prop_cell(st, L), EY._ncells(L))
            rig[EY._prop_cell(st, L)] = idx
        EY._ensure_anim_props(rig, st, L)
        rig[EY._p_sx(st, L)] = g.size
        rig[EY._p_sy(st, L)] = g.size
        rig[EY._p_py(st, L)] = g.dy
        if sel_par and EY._layer(st, sel_par) is not None:
            nlid = L.lid
            EY.set_parent(s, st, L, sel_par, build=False)
            st.layer_index = next(k for k, x in enumerate(st.layers)
                                  if x.lid == nlid)
        EY.eye_build(s, st)
        if self.ime_name and 0 <= st.layer_index < len(st.layers):
            from .ime import open_for
            err = open_for(st.layers[st.layer_index], "name",
                           _tr("파츠 이름"))
            if err:
                self.report({'WARNING'}, err)
        _redraw_ui(context)
        return {'FINISHED'}


def _mouth_atlas_for(context, s, st, sh, idx):
    """입 태그: 이 시트를 쓰는 입 스프라이트 시트(시퀀스·립싱크)를 준비."""
    it = next((a for a in s.atlases if a.image == sh.image
               and a.method == 'CANVAS' and a.target == st.target), None)
    if it is None:
        used = {a.uid for a in s.atlases}
        i = 1
        while "A%d" % i in used:
            i += 1
        it = s.atlases.add()
        it.uid = "A%d" % i
        it.name = _tr("입")
        it["image"] = sh.image
        it["cols"] = sh.cols
        it["rows"] = sh.rows
        it["layout"] = 1          # FREE (자유 배치)
        it["free_lip"] = 1        # 시퀀스
        it.target = st.target
        it.method = 'CANVAS'
    cols = max(1, int(it.cols))
    rig = s.rig
    AT._ensure_prop(rig, AT._prop_row(it), max(1, int(it.rows)))
    AT._ensure_prop(rig, AT._prop_col(it), cols)
    rig[AT._prop_row(it)] = idx // cols
    rig[AT._prop_col(it)] = idx % cols
    AT._build(s, it)
    return it


# ------------------------------------------------------------------
# ⑤ 표정 프리셋
# ------------------------------------------------------------------

def _layer_state(s, st, L, rig):
    d = {"tag": L.tag}
    ait = EY._layer_atlas(s, L)
    if ait is not None:
        if getattr(ait, "edit_on", False):   # 편집 모드로 띄운 칸
            d["mr"], d["mc"] = (int(v) for v in AT._cur_cell(ait))
        else:
            d["mr"] = int(AT._get_val(rig,
                                      AT._prop_row(AT._row_source(s, ait))))
            d["mc"] = int(AT._get_val(rig, AT._prop_col(ait)))
    else:
        p = EY._prop_cell(st, L)
        d["cell"] = int(EY.part_cell_now(rig, st, L)) if p in rig.keys() \
            else 0
    for k, p, dv in zip(EY.ANIM_KEYS, EY._anim_props(st, L),
                        EY.ANIM_DEFAULTS):
        d[k] = float(rig.get(p, dv))
    return d


def layer_states_capture(s, st):
    """파츠 폴더용: 모든 파츠의 지금 상태 {lid: 상태} (칸·배치·보이기·반전)."""
    rig = s.rig
    out = {}
    if rig is None:
        return out
    for L in st.layers:
        d = _layer_state(s, st, L, rig)     # 반전(flip)은 리그 값으로 포함
        d["sym"] = bool(L.sym)
        out[L.lid] = d
    return out


def layer_states_apply(s, st, states, key=False):
    """layer_states_capture로 저장한 상태를 되돌린다 (없는 파츠는 그대로)."""
    rig = s.rig
    if rig is None:
        return
    rebuild = False
    for L in st.layers:
        d = states.get(L.lid)
        if not d:
            continue
        EY._ensure_anim_props(rig, st, L)
        if "flip" not in d and "flip_x" in d:   # 1.0.225까지 저장한 폴더
            d = dict(d)
            d["flip"] = 1.0 if d["flip_x"] else 0.0
        for k, p in zip(EY.ANIM_KEYS, EY._anim_props(st, L)):
            if k in d:
                rig[p] = d[k]
                if key:
                    _key_const(rig, p)
        ait = EY._layer_atlas(s, L)
        if ait is not None and "mr" in d:
            pr_ = AT._prop_row(AT._row_source(s, ait))
            pc_ = AT._prop_col(ait)
            rig[pr_], rig[pc_] = d["mr"], d["mc"]
            if key:
                AT._key(rig, pr_)
                AT._key(rig, pc_)
        elif "cell" in d:
            p = EY._prop_cell(st, L)
            EY._ensure_prop(rig, p, EY._ncells(L))
            rig[p] = d["cell"]
            if key:
                AT._key(rig, p)
        for a in ("sym",):
            if a in d and bool(getattr(L, a)) != bool(d[a]):
                L[a] = bool(d[a])
                rebuild = True
    if rebuild:
        EY.eye_build(s, st)
    try:
        rig.update_tag()
        ob = bpy.data.objects.get(st.target)
        if ob is not None:
            ob.update_tag()
    except Exception:
        pass


def _key_const(rig, prop):
    try:
        rig.keyframe_insert(data_path='["%s"]' % prop, group="Expression")
        AT._make_constant(rig, '["%s"]' % prop)
    except Exception:
        pass


def preset_apply(s, st, pr, groups, key):
    rig = s.rig
    if getattr(st, "preset_edit", False):
        key = False      # 프리셋 편집 중엔 키 없음
    try:
        data = json.loads(pr.data or "{}")
    except Exception:
        data = {}
    lay = data.get("layers", {})
    if "folder" in data:      # 그 표정의 파츠 폴더 (목록 보기)
        fi = next((i for i, p in enumerate(st.part_sets)
                   if p.name == data["folder"]), -1)
        EY.part_set_store(s, st)   # 지금 폴더에서 작업한 내용은 먼저 저장
        st.part_set_active = fi
    for L in st.layers:
        if groups is not None and L.tag not in groups:
            continue
        EY._ensure_anim_props(rig, st, L)
        props = EY._anim_props(st, L)
        d = lay.get(L.lid)
        if d is None:   # 이 표정에 없는 파츠는 숨김
            rig[props[0]] = 0.0
            if key:
                _key_const(rig, props[0])
            continue
        if "vis" not in d:      # 보이기가 없던 때 저장한 프리셋 = 보임
            d = dict(d)
            d["vis"] = 1.0
        for k, p, dv in zip(EY.ANIM_KEYS, props, EY.ANIM_DEFAULTS):
            if k not in d and k in ("ct", "cb", "cl", "cr"):
                # 크롭이 없던 때 저장한 프리셋 = 크롭 없음(0)
                d = dict(d)
                d[k] = dv
            if k in d:
                rig[p] = d[k]
                if key:
                    _key_const(rig, p)
        ait = EY._layer_atlas(s, L)
        if ait is not None and "mr" in d:
            pr_ = AT._prop_row(AT._row_source(s, ait))
            pc_ = AT._prop_col(ait)
            rig[pr_], rig[pc_] = d["mr"], d["mc"]
            if key:
                AT._key(rig, pr_)
                AT._key(rig, pc_)
        elif "cell" in d:
            p = EY._prop_cell(st, L)
            EY._ensure_prop(rig, p, EY._ncells(L))
            rig[p] = d["cell"]
            if key:
                AT._key(rig, p)
    try:
        rig.update_tag()
        ob = bpy.data.objects.get(st.target)
        if ob is not None:
            ob.update_tag()
    except Exception:
        pass


def _fskr_paths(s):
    return {'["%s"]' % n for n in EY._all_prop_names(s)}


def preset_edit_begin(context, s, st):
    """프리셋 편집 시작: 이 애드온 채널의 키를 잠시 멈춤(뮤트) → 프리셋 값을
    그대로 고칠 수 있음. 키·자동 키는 넣지 않음."""
    rig = s.rig
    ad = rig.animation_data if rig else None
    paths = _fskr_paths(s)
    muted = []
    for fc in AT._action_fcurves(ad):
        if fc.data_path in paths and not fc.mute:
            fc.mute = True
            muted.append([fc.data_path, int(fc.array_index)])
    st["pe_muted"] = json.dumps(muted)
    ts = context.scene.tool_settings
    st["pe_ak"] = int(bool(ts.use_keyframe_insert_auto))
    ts.use_keyframe_insert_auto = False      # Blender 자동 키도 잠시 끔
    # 칸 편집 모드는 끔 (프리셋은 실제 칸 값을 저장하므로)
    for L in st.layers:
        if L.edit_on:
            L.edit_on = False
    for it in s.atlases:
        if getattr(it, "edit_on", False):
            it.edit_on = False
    st.preset_edit = True
    if 0 <= st.preset_index < len(st.presets):
        preset_apply(s, st, st.presets[st.preset_index], None, False)
        try:
            from .preset_vp import note
            note(s, st, st.preset_index, False)   # 표정 번호·손잡이도 맞춤
        except Exception:
            pass


def preset_edit_end(context, s, st):
    """프리셋 편집 끝: 멈췄던 키를 되살리고 현재 프레임 값으로 되돌림."""
    rig = s.rig
    ad = rig.animation_data if rig else None
    try:
        muted = {(a, int(b)) for a, b in json.loads(st.get("pe_muted", "[]"))}
    except Exception:
        muted = set()
    for fc in AT._action_fcurves(ad):
        if (fc.data_path, int(fc.array_index)) in muted:
            fc.mute = False
    st["pe_muted"] = "[]"
    try:
        context.scene.tool_settings.use_keyframe_insert_auto = bool(
            st.get("pe_ak", 0))
    except Exception:
        pass
    st.preset_edit = False
    try:
        context.scene.frame_set(context.scene.frame_current)
    except Exception:
        pass


class FSKR_OT_preset_edit(bpy.types.Operator):
    bl_idname = "fskr.preset_edit"
    bl_label = "프리셋 편집"
    bl_description = ("키프레임을 잠시 멈추고 고른 프리셋(표정)의 파츠를 그대로 "
                      "고칩니다. 끝나면 '저장하고 끝내기' 또는 '취소'")
    bl_options = {'REGISTER', 'UNDO'}

    action: bpy.props.EnumProperty(
        items=(('START', "편집 시작", ""), ('SAVE', "저장하고 끝내기", ""),
               ('CANCEL', "취소", "")), options={'HIDDEN', 'SKIP_SAVE'})

    @classmethod
    def description(cls, context, props):
        a = getattr(props, "action", 'START')
        if a == 'SAVE':
            return _tr("지금 파츠 상태를 이 프리셋에 덮어쓰고, 멈췄던 키프레임을 "
                       "되살립니다")
        if a == 'CANCEL':
            return _tr("저장하지 않고 끝냅니다 (멈췄던 키프레임을 되살림)")
        return _tr("키프레임을 잠시 멈추고 이 프리셋의 파츠를 고칩니다. 그동안 "
                   "키는 들어가지 않습니다")

    def execute(self, context):
        s = context.scene.fskr
        st = _canvas(s)
        if st is None or s.rig is None:
            return {'CANCELLED'}
        if self.action == 'START':
            if not (0 <= st.preset_index < len(st.presets)):
                self.report({'WARNING'}, _tr("편집할 프리셋을 고르세요"))
                return {'CANCELLED'}
            if not st.preset_edit:
                preset_edit_begin(context, s, st)
        else:
            if self.action == 'SAVE' and \
                    0 <= st.preset_index < len(st.presets):
                bpy.ops.fskr.face_preset_save('EXEC_DEFAULT', overwrite=True)
                self.report({'INFO'}, _tr("프리셋 저장: ")
                            + st.presets[st.preset_index].name)
            preset_edit_end(context, s, st)
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_ime_dlg(bpy.types.Operator):
    bl_idname = "fskr.ime_dlg"
    bl_label = "한중일 입력 창"
    bl_description = ("한중일 입력 창(작은 브라우저)을 띄워 이 칸에 글자를 "
                      "씁니다. 넣으면 이 창의 칸에 바로 들어갑니다")
    bl_options = {'INTERNAL'}

    attr: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    label: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, context):
        from .ime import open_for
        err = open_for(context.window_manager, self.attr,
                       self.label or None)
        if err:
            self.report({'WARNING'}, err)
            return {'CANCELLED'}
        return {'FINISHED'}


class FSKR_OT_preset_save_face(bpy.types.Operator):
    bl_idname = "fskr.face_preset_save"
    bl_label = "프리셋 저장"
    bl_description = ("지금 보이는 파츠 배치(칸·위치·크기·회전·불투명도, 입 "
                      "칸)를 표정으로 저장합니다")
    bl_options = {'REGISTER', 'UNDO'}

    name: bpy.props.StringProperty(name="이름", default="")
    use_dlg: bpy.props.BoolProperty(default=False,
                                    options={'HIDDEN', 'SKIP_SAVE'})
    overwrite: bpy.props.BoolProperty(default=False, options={'HIDDEN'})
    ime_name: bpy.props.BoolProperty(
        name="입력 창으로 이름 쓰기", default=False, options={'SKIP_SAVE'},
        description="만든 뒤 한중일 입력 창을 띄워 이름을 씁니다 (Blender에서 "
                    "한글 입력이 안 될 때)")

    def draw(self, context):
        wm = context.window_manager
        r = self.layout.row(align=True)
        r.prop(wm, "fskr_dlg_name", text=_tr("이름"))
        op = r.operator("fskr.ime_dlg", text="", icon='FONTPREVIEW')
        op.attr, op.label = "fskr_dlg_name", _tr("프리셋 이름")

    @classmethod
    def poll(cls, context):
        st = _canvas(context.scene.fskr)
        return st is not None and len(st.layers) > 0

    def invoke(self, context, event):
        st = _canvas(context.scene.fskr)
        if self.overwrite and 0 <= st.preset_index < len(st.presets):
            return self.execute(context)
        if not self.name:
            self.name = "%s %d" % (_tr("새 표정"), len(st.presets) + 1)
        # 이름은 창 밖(한중일 입력 창)에서도 바꿀 수 있게 wm 값으로 받음
        context.window_manager.fskr_dlg_name = self.name
        self.use_dlg = True
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        s = context.scene.fskr
        st = _canvas(s)
        rig = s.rig
        lay = {}
        for L in st.layers:
            # 숨긴 파츠도 '보이기' 값(vis)과 함께 저장 → 적용하면 그대로 숨김
            d = _layer_state(s, st, L, rig)
            if d.get("op", 1.0) <= 0.0:
                continue  # 숨겨 둔 파츠는 이 표정에 없음
            lay[L.lid] = d
        pa9 = st.part_set_active
        fold9 = st.part_sets[pa9].name if 0 <= pa9 < len(st.part_sets) \
            else ""
        data = json.dumps({"layers": lay, "folder": fold9},
                          ensure_ascii=False)
        if self.overwrite and 0 <= st.preset_index < len(st.presets):
            st.presets[st.preset_index].data = data
        else:
            if self.use_dlg:
                self.name = context.window_manager.fskr_dlg_name
            pr = st.presets.add()
            pr.name = self.name or _tr("새 표정")
            pr.data = data
            EY._PRESET_MUTE["on"] = True
            try:
                st.preset_index = len(st.presets) - 1
            finally:
                EY._PRESET_MUTE["on"] = False
            if self.ime_name:
                from .ime import open_for
                err = open_for(pr, "name", _tr("프리셋 이름"))
                if err:
                    self.report({'WARNING'}, err)
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_preset_apply_face(bpy.types.Operator):
    bl_idname = "fskr.face_preset_apply"
    bl_label = "프리셋 적용 + 키"
    bl_description = ("이 표정을 적용하고 현재 프레임에 키를 넣습니다 "
                      "(이 프레임부터 표정이 바뀜)")
    bl_options = {'REGISTER', 'UNDO'}

    index: bpy.props.IntProperty(default=-1, options={'HIDDEN'})
    all_groups: bpy.props.BoolProperty(
        default=False, options={'HIDDEN', 'SKIP_SAVE'},
        description="그룹 선택 무시하고 전부 적용")
    key: bpy.props.BoolProperty(
        name="키 넣기", default=True,
        description="현재 프레임에 Constant 키를 넣어 이 프레임부터 표정이 "
                    "바뀌게 합니다")

    @classmethod
    def poll(cls, context):
        st = _canvas(context.scene.fskr)
        return st is not None and len(st.presets) > 0

    def execute(self, context):
        s = context.scene.fskr
        st = _canvas(s)
        i = self.index if self.index >= 0 else st.preset_index
        if not (0 <= i < len(st.presets)):
            return {'CANCELLED'}
        if self.index >= 0 and st.preset_index != i:
            EY._PRESET_MUTE["on"] = True     # 목록 선택만 맞추고
            try:
                st.preset_index = i
            finally:
                EY._PRESET_MUTE["on"] = False
        groups = None    # 항상 전체 적용
        preset_apply(s, st, st.presets[i], groups, self.key)
        try:
            from .preset_vp import note
            note(s, st, i, self.key)
        except Exception as e:
            print("FSKR preset note:", e)
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_preset_remove_face(bpy.types.Operator):
    bl_idname = "fskr.face_preset_remove"
    bl_label = "프리셋 삭제"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        st = _canvas(context.scene.fskr)
        if st is None or not (0 <= st.preset_index < len(st.presets)):
            return {'CANCELLED'}
        st.presets.remove(st.preset_index)
        EY._PRESET_MUTE["on"] = True
        try:
            st.preset_index = max(0, st.preset_index - 1)
        finally:
            EY._PRESET_MUTE["on"] = False
        return {'FINISHED'}


# ------------------------------------------------------------------
# UI 목록
# ------------------------------------------------------------------

class FSKR_UL_face_layers(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index):
        r = layout.row(align=True)
        depth = EY.layer_depth(data, item)
        for _ in range(depth):
            r.label(text="", icon='BLANK1')
        # 펼침 화살표 자리는 모든 줄에 확보 (같은 레벨끼리 줄이 맞도록)
        if EY.layer_children(data, item):
            r.prop(item, "show_children", text="", emboss=False,
                   icon='TRIA_DOWN' if item.show_children else 'TRIA_RIGHT')
        else:
            r.label(text="", icon='BLANK1')
        # 부모가 꺼져 있으면 자식도 안 보임 → 흐리게 + 닫힌 눈 표시
        par_off = item.show and not EY.layer_visible(data, item)
        eb9 = r.row(align=True)
        eb9.active = not par_off
        eb9.prop(item, "show", text="", emboss=False,
                 icon='HIDE_ON' if (par_off or not item.show) else 'HIDE_OFF')
        nm9 = r.row(align=True)
        nm9.active = not par_off
        folder = getattr(item, "kind", 'PART') == 'FOLDER'
        if folder:
            nm9.prop(item, "name", text="", emboss=False,
                     icon='FILE_FOLDER' if item.show else 'FOLDER_REDIRECT')
        else:
            nm9.prop(item, "name", text="", emboss=False)
        g = EY.find_tag(data, item.tag)
        sub = r.row(align=True)
        sub.active = False
        sub.label(text=g.name if g else "-")
        if folder:
            b = r.row(align=True)
            b.ui_units_x = 5.5
            n9 = len(EY.layer_descendants(data, item))
            if EY.folder_group(data, item):
                op = b.operator("fskr.eye_folder_on",
                                text=_tr("켜짐") if item.show else _tr("전환"),
                                depress=item.show)
                op.uid, op.lid = data.uid, item.lid
            else:
                b.label(text=_tr("%d개") % n9)
            r.label(text="", icon='BLANK1')
            r.label(text="", icon='BLANK1')
            return
        b = r.row(align=True)
        b.ui_units_x = 5.5
        b.prop(item, "blend", text="")
        r.label(text="", icon='MOD_MIRROR' if item.sym else 'BLANK1')
        r.label(text="", icon='MOD_MASK' if item.clip else 'BLANK1')

    def filter_items(self, context, data, propname):
        items = getattr(data, propname)
        f = data.tag_filter
        flags = []
        pa = getattr(data, "part_set_active", -1)
        mem = EY.part_set_members(data.part_sets[pa]) \
            if 0 <= pa < len(data.part_sets) else None
        for it in items:
            ok = not f or it.tag == f
            if ok and mem is not None and it.lid not in mem:
                ok = False          # 폴더 보기: 그 폴더의 파츠만
            # 접힌 부모의 자손은 숨김
            if ok and any(not a.show_children
                          for a in EY.layer_ancestors(data, it)):
                ok = False
            flags.append(self.bitflag_filter_item if ok else 0)
        if not any(it.parent for it in items):
            return flags, []
        # 블렌더 아웃라이너처럼: 부모 다음 줄에 자식들 (자식끼리는 앞→뒤)
        idx = {it.lid: k for k, it in enumerate(items)}
        seq, seen = [], set()

        def walk(n):
            if n.lid in seen:
                return
            seen.add(n.lid)
            seq.append(idx[n.lid])
            for c in sorted(EY.layer_children(data, n),
                            key=lambda x: idx[x.lid]):
                walk(c)
        for it in items:
            if EY.layer_parent(data, it) is None:
                walk(it)
        for it in items:
            if it.lid not in seen:
                seen.add(it.lid)
                seq.append(idx[it.lid])
        neworder = [0] * len(items)
        for pos, k in enumerate(seq):
            neworder[k] = pos
        return flags, neworder


class FSKR_UL_face_presets(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index):
        r = layout.row(align=True)
        r.prop(item, "name", text="", emboss=False, icon='SHAPEKEY_DATA')
        _paste(r, item)
        op = r.operator("fskr.face_preset_apply", text="", icon='KEY_HLT')
        op.index = index
        op.key = True


# ------------------------------------------------------------------
# 패널
# ------------------------------------------------------------------

def _clip_text(context):
    t = (context.window_manager.clipboard or "").strip()
    return t.splitlines()[0].strip()[:63] if t else ""


def _paste(layout, owner, attr="name"):
    from .layer_vp import paste_btn
    paste_btn(layout, owner, attr)


def sprite_tab_on(context, tab):
    """스프라이트 방식이고 지금 탭이 tab 인지."""
    s = context.scene.fskr
    return (getattr(s, "ui_mode", 'DRIVER') == 'SPRITE'
            and getattr(s, "sprite_tab", 'SETUP') == tab)


class _SpritePanel:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Face Rig"
    _tab = 'SETUP'

    @classmethod
    def poll(cls, context):
        return sprite_tab_on(context, cls._tab)


def _draw_flatten(lay, context, s):
    """머리 납작하게 (카메라 기준) 상자."""
    fb = lay.box().column(align=True)
    hr = fb.row(align=True)
    hr.prop(s, "show_flatten", emboss=False,
            icon='TRIA_DOWN' if s.show_flatten else 'TRIA_RIGHT')
    obs = EY.flat_objects()
    if obs:
        hr.label(text="%d" % len(obs), icon='MOD_SIMPLEDEFORM')
    if not s.show_flatten:
        return
    rig = s.rig
    if not obs:
        _guide(fb, [_tr("머리를 카메라 시선 방향으로 눌러 2D 그림처럼 "
                        "보이게 합니다 (캔버스 파츠도 같이)"),
                    _tr("얼굴·머리카락·모자 등 같이 눌릴 메시를 선택"),
                    _tr("아래 버튼 → 머리 본 확인")])
        r = fb.row()
        r.scale_y = 1.3
        r.operator("fskr.head_flatten", icon='MOD_SIMPLEDEFORM')
        return
    for pn, lab in (("Head_Flatten", _tr("세기")),
                    ("Head_Flatten_Side", _tr("옆모습일수록 더"))):
        if rig is not None and pn in rig.keys():
            fb.prop(rig, '["%s"]' % pn, text=lab, slider=True)
    rr = fb.row(align=True)
    for nm, lab in (("Radius", _tr("범위")), ("Falloff", _tr("부드럽게"))):
        sk = EY.flat_value(nm)
        if sk is not None:
            rr.prop(sk, "default_value", text=lab)
    ng = bpy.data.node_groups.get(EY.FLAT_GROUP)
    cam = ng.nodes["Camera"].inputs['Object'].default_value \
        if ng is not None else None
    cr = fb.row(align=True)
    cr.alert = cam is None
    cr.label(text=_tr("카메라: ") + (cam.name if cam else "-"),
             icon='CAMERA_DATA')
    cr.operator("fskr.head_flatten_cam", text="", icon='FILE_REFRESH')
    lb = fb.box().column(align=True)
    for o in obs:
        r = lb.row(align=True)
        r.label(text=o.name, icon='MESH_DATA')
        r.operator("fskr.head_flatten_remove", text="",
                   icon='X').name = o.name
    ar = fb.row(align=True)
    ar.operator("fskr.head_flatten", text=_tr("선택한 메시 추가"),
                icon='ADD')
    ar.operator("fskr.head_flatten_remove", text=_tr("전부 지우기"),
                icon='TRASH')
    g = fb.column(align=True)
    g.scale_y = 0.8
    g.active = False
    g.label(text=_tr("세기는 리그 프로퍼티라 키를 넣을 수 있습니다 (I)"),
            icon='INFO')
    g.label(text=_tr("100% 가까이면 앞뒤가 겹쳐 깜빡일 수 있습니다"))
    g.label(text=_tr("렌더 카메라 기준: 다른 각도로 보면 납작해 보임"))


class FSKR_PT_f1_canvas(_SpritePanel, bpy.types.Panel):
    bl_label = "① 얼굴 캔버스"
    bl_order = 1

    def draw(self, context):
        s = context.scene.fskr
        lay = self.layout
        st = _canvas(s)
        col = _step(lay, "", _tr("리그"), s.rig is not None, 'ARMATURE_DATA')
        col.prop(s, "rig", text="")
        if s.rig is None:
            _guide(col, [_tr("애니메이션 키가 들어갈 아마추어(리그)를 "
                             "고르세요")])
            return
        col = _step(lay, "", _tr("얼굴 캔버스"), st is not None,
                    'MOD_SHRINKWRAP')
        if st is None:
            _guide(col, [_tr("얼굴 메시와 분리된, 눈·입이 그려질 메시를 "
                             "만듭니다"),
                         _tr("얼굴 메시 선택 → Tab (편집 모드)"),
                         _tr("눈썹 위~턱까지 얼굴 앞면을 면 선택"),
                         _tr("아래 버튼 누르기")])
            ar = col.row(align=True)
            ar.label(text=_tr("얼굴 방향"))
            ar.prop(s, "face_axis", expand=True)
            r = col.row()
            r.scale_y = 1.4
            r.operator("fskr.face_canvas", icon='MOD_SHRINKWRAP')
            aob = context.active_object
            if context.mode == 'EDIT_MESH' and aob is not None and \
                    aob.type == 'MESH' and aob.data.total_face_sel == 0:
                w = col.row()
                w.alert = True
                w.label(text=_tr("선택된 면이 없습니다. 얼굴 앞면을 면 "
                                 "선택하세요"), icon='ERROR')
        if st is not None:
            if len(s.eyes) > 1:
                col.prop(s, "canvas_pick", text="")
            nr = col.row(align=True)
            nr.prop(st, "name", text=_tr("이름"))
            r = col.row(align=True)
            r.label(text=st.target, icon='MESH_DATA')
            r.prop(st, "show_settings", text="", icon='PREFERENCES',
                   toggle=True)
            r.operator("fskr.eye_remove", text="", icon='X').uid = st.uid
            ob9 = bpy.data.objects.get(st.target)
            if ob9 is not None and st.get("fx"):
                fb = col.column(align=True)
                fb.prop(st, "billboard", toggle=True, icon='CAMERA_DATA')
                if st.billboard and context.scene.camera is None:
                    w9 = fb.row()
                    w9.alert = True
                    w9.label(text=_tr("씬에 활성 카메라가 없습니다"),
                             icon='ERROR')
                g9 = fb.column(align=True)
                g9.scale_y = 0.8
                g9.active = False
                g9.label(text=_tr("감정표현 Plane · 머리 본: %s")
                         % (ob9.parent_bone or "-"), icon='INFO')
                g9.label(text=_tr("크기·위치는 오브젝트를 직접 옮기거나 "
                                  "S로 조절해도 됩니다"))
            elif ob9 is not None:
                fm = ob9.modifiers.get(EY._FOLLOW_MOD)
                sw9 = ob9.modifiers.get("FSKR_Canvas_Wrap")
                vp9 = ob9.modifiers.get(EY._WRAP_VP)
                bad = fm is None or not fm.is_bound or any(
                    m.type == 'ARMATURE' for m in ob9.modifiers) or (
                    sw9 is not None and not (
                        (sw9.show_viewport or (vp9 is not None and
                                               vp9.show_viewport))
                        and sw9.show_render))
                col.prop(st, "lift")
                rs = col.column(align=True)
                if st.get("reselect"):
                    bx = rs.box().column(align=True)
                    bx.alert = True
                    bx.label(text=_tr("선택 영역 수정 중"), icon='EDITMODE_HLT')
                    gg = bx.column(align=True)
                    gg.alert = False
                    gg.scale_y = 0.85
                    gg.label(text=_tr("지금 캔버스 영역이 선택되어 있습니다"))
                    gg.label(text=_tr("면을 더하거나(Shift+클릭) 빼고 적용"))
                    rr9 = bx.row(align=True)
                    rr9.alert = False
                    rr9.scale_y = 1.3
                    rr9.operator("fskr.canvas_reselect", icon='CHECKMARK',
                                 text=_tr("적용")).uid = st.uid
                    rr9.operator("fskr.canvas_reselect_cancel",
                                 icon='X').uid = st.uid
                else:
                    r9 = rs.row()
                    r9.enabled = context.active_object is ob9 and \
                        context.mode == 'OBJECT'
                    r9.operator("fskr.canvas_reselect_start",
                                icon='SELECT_SET').uid = st.uid
                    if not r9.enabled:
                        g9 = rs.row()
                        g9.active = False
                        g9.label(text=_tr("캔버스(%s)를 선택하면 켜집니다")
                                 % ob9.name, icon='INFO')
                rr = col.row()
                rr.alert = bad
                rr.operator("fskr.canvas_follow",
                            icon='ERROR' if bad else 'LINKED').uid = st.uid
                if bad:
                    _guide(col, [_tr("캔버스가 얼굴과 따로 움직일 수 있습니다. "
                                     "위 버튼으로 다시 붙이세요"),
                                 _tr("리그 바인드(ARP 등)할 때 캔버스는 "
                                     "빼고 얼굴 메시만 바인드하세요")])
            if st.show_settings:
                sb = col.box().column()
                ob = bpy.data.objects.get(st.target)
                if ob is not None and ob.type == 'MESH':
                    sb.prop_search(st, "uv_map", ob.data, "uv_layers")
                r = sb.row(align=True)
                r.operator("fskr.eye_build", icon='FILE_REFRESH').uid = \
                    st.uid
                r.operator("fskr.eye_fit_uv", icon='UV').uid = st.uid
            if hasattr(s, "show_no_overlay"):
                col.prop(s, "show_no_overlay", toggle=True, icon='OVERLAY')
            pr = col.row(align=True)
            pr.operator("fskr.canvas_export", icon='EXPORT',
                        text=_tr("내보내기"))
            pr.operator("fskr.canvas_import", icon='IMPORT',
                        text=_tr("불러오기 (덮어쓰기)"))
        if st is not None:   # 한 캐릭터에 캔버스 여러 개 (모자 얼굴 등)
            ab = lay.box().column(align=True)
            hr = ab.row(align=True)
            hr.prop(s, "show_canvas_add", emboss=False,
                    icon='TRIA_DOWN' if s.show_canvas_add else 'TRIA_RIGHT')
            if s.show_canvas_add:
                _guide(ab, [_tr("모자 얼굴처럼 표정·시선을 따로 움직일 "
                                "얼굴이 하나 더 있을 때"),
                            _tr("그 메시 선택 → Tab (편집 모드)"),
                            _tr("캔버스로 쓸 앞면을 면 선택"),
                            _tr("아래 버튼 누르기 → 새 캔버스로 전환됨")])
                ar = ab.row(align=True)
                ar.label(text=_tr("얼굴 방향"))
                ar.prop(s, "face_axis", expand=True)
                r = ab.row()
                r.scale_y = 1.3
                r.operator("fskr.face_canvas", icon='ADD',
                           text=_tr("새 캔버스 만들기"))
                ab.separator()
                fr = ab.row()
                fr.scale_y = 1.3
                fr.operator("fskr.fx_canvas", icon='MESH_PLANE',
                            text=_tr("감정표현 Plane 만들기"))
                _guide(ab, [_tr("분노 마크처럼 얼굴 밖으로 나가는 연출용 "
                                "평면 (머리 본을 따라감)")])
                aob = context.active_object
                if context.mode == 'EDIT_MESH' and aob is not None and \
                        aob.type == 'MESH' and aob.data.total_face_sel == 0:
                    w = ab.row()
                    w.alert = True
                    w.label(text=_tr("선택된 면이 없습니다"), icon='ERROR')
        if st is not None:
            _draw_flatten(lay, context, s)
        sub = lay.column()
        sub.active = False
        sub.operator("fskr.eye_add", text=_tr("(고급) 선택한 메시를 그대로 "
                                              "캔버스로"), icon='ADD')


class FSKR_PT_f2_markers(_SpritePanel, bpy.types.Panel):
    bl_label = "② 위치 마커"
    bl_order = 2

    def draw(self, context):
        s = context.scene.fskr
        lay = self.layout
        st = _canvas(s)
        if st is None:
            lay.label(text=_tr("먼저 ①에서 얼굴 캔버스를 만드세요"),
                      icon='INFO')
            return
        done = len(st.markers) > 0 and all(m.placed for m in st.markers)
        col = _step(lay, "", _tr("기준점 만들기 · 찍기"), done, 'PIVOT_CURSOR')
        _guide(col, [_tr("+ 로 마커를 만들고 이름을 붙이세요 (예: 눈, 입, 볼)"),
                     _tr("'찍기'를 누르면 화면이 얼굴 정면(숫자패드 1과 같음)으로 "
                         "바뀝니다. 얼굴을 클릭하세요"),
                     _tr("대칭 태그가 쓰는 마커는 한쪽만 찍으면 반대쪽이 "
                         "따라갑니다"),
                     _tr("마커를 옮기면 그 마커에 붙은 파츠가 전부 따라갑니다")])
        ar = col.row(align=True)
        ar.label(text=_tr("얼굴 방향"))
        ar.prop(s, "face_axis", expand=True)
        ar.operator("fskr.face_front_view", text="", icon='VIEW_PERSPECTIVE')
        r = col.row()
        r.scale_y = 1.2
        r.operator("fskr.marker_add", icon='ADD')
        for m in st.markers:
            b = col.box().column(align=True)
            r = b.row(align=True)
            r.label(text="", icon='CHECKMARK' if m.placed else 'RADIOBUT_OFF')
            r.prop(m, "name", text="")
            _paste(r, m)
            op = r.operator("fskr.marker_place",
                            text=_tr("다시 찍기") if m.placed else _tr("찍기"),
                            icon='RESTRICT_SELECT_OFF')
            op.uid = m.uid
            r.operator("fskr.marker_remove", text="", icon='X').uid = m.uid
            if m.placed:
                b.prop(m, "uv", text="")
            users = [g.name for g in st.tags if g.marker == m.uid]
            if users:
                sub = b.row()
                sub.active = False
                sub.label(text=_tr("쓰는 태그: ") + ", ".join(users))
        col.prop(st, "show_markers", toggle=True, icon='HIDE_OFF')


class FSKR_PT_f3_sheets(_SpritePanel, bpy.types.Panel):
    bl_label = "③ 스프라이트 시트"
    bl_order = 3

    def draw(self, context):
        s = context.scene.fskr
        lay = self.layout
        st = _canvas(s)
        if st is None:
            lay.label(text=_tr("먼저 ①에서 얼굴 캔버스를 만드세요"),
                      icon='INFO')
            return
        col = _step(lay, "", _tr("시트 불러오기 · 자르기"), len(st.sheets) > 0,
                    'IMAGE_DATA')
        _guide(col, [_tr("격자로 그린 시트 이미지를 고르고 행·열 수를 "
                         "넣으세요 (파일 창 오른쪽)"),
                     _tr("그림이 있는 칸만 번호가 매겨져 파츠가 됩니다")])
        r = col.row()
        r.scale_y = 1.3
        r.operator("fskr.sheet_add", icon='FILEBROWSER')
        for sh in st.sheets:
            b = col.box()
            hr = b.row(align=True)
            hr.prop(sh, "expand", text="", emboss=False,
                    icon='TRIA_DOWN' if sh.expand else 'TRIA_RIGHT')
            hr.prop(sh, "name", text="")
            _paste(hr, sh)
            ready = _sheet_ready(st, sh)
            n = len(sheet_parts(st, sh)) if ready else 0
            hr.label(text=_tr("파츠 %d개") % n if ready else "…")
            hr.operator("fskr.sheet_remove", text="", icon='X').uid = sh.uid
            if sh.expand or not ready:
                r = b.row(align=True)
                r.operator("fskr.sheet_reload", text=_tr("다시 불러오기"),
                           icon='FILE_REFRESH').uid = sh.uid
                r.operator("fskr.sheet_replace", text=_tr("다른 파일로"),
                           icon='FILEBROWSER').uid = sh.uid
                imgx = bpy.data.images.get(sh.image)
                r = b.row(align=True)
                r.operator("fskr.sheet_fix_edges", icon='BRUSH_DATA',
                           text=_tr("가장자리 흰 선 제거") + (
                               _tr(" (적용됨)") if imgx is not None and
                               imgx.get("fskr_bleed_fixed") else "")
                           ).uid = sh.uid
            if not ready:
                _sheet_request(st, sh)
                b.label(text=_tr("칸을 잘라 파츠 번호를 매기는 중…"),
                        icon='TIME')
                continue
            if not sh.expand:
                continue
            r = b.row(align=True)
            r.prop(sh, "cols")
            r.prop(sh, "rows")
            r.operator("fskr.sheet_slice", text="", icon='FILE_REFRESH') \
                .uid = sh.uid
            g = b.grid_flow(columns=6, even_columns=True, align=True)
            for num, idx, rr, cc, icon in sheet_parts(st, sh):
                cell = g.column(align=True)
                cell.template_icon(icon_value=icon, scale=2.4)
                cell.label(text="%d" % num)


class FSKR_PT_f7_gaze(_SpritePanel, bpy.types.Panel):
    bl_idname = "FSKR_PT_gaze_tab"
    bl_label = "시선 (눈동자 이동)"
    bl_order = 7
    _tab = 'GAZE'

    def draw_header(self, context):
        self.layout.label(text="", icon='ORIENTATION_VIEW')

    def draw(self, context):
        s = context.scene.fskr
        lay = self.layout
        st = _canvas(s)
        if st is None:
            lay.label(text=_tr("먼저 ①에서 얼굴 캔버스를 만드세요"),
                      icon='INFO')
            return
        has_pad = EY._gaze_bone(st) is not None
        # 1) 컨트롤러
        col = _step(lay, "1", _tr("뷰포트 컨트롤러 (시선 패드)"), has_pad,
                    'ORIENTATION_VIEW')
        if not has_pad:
            _guide(col, [_tr("뷰포트에 네모 패드와 가운데 십자 손잡이를 "
                             "만듭니다"),
                         _tr("손잡이를 끌면 '시선'을 켠 파츠가 따라 움직입니다")])
            r = col.row()
            r.scale_y = 1.3
            op = r.operator("fskr.gaze_pad", text=_tr("시선 컨트롤러 만들기"),
                            icon='ADD')
            op.uid, op.action = st.uid, 'BUILD'
        else:
            r = col.row(align=True)
            op = r.operator("fskr.gaze_pad", text=_tr("다시 만들기"),
                            icon='FILE_REFRESH')
            op.uid, op.action = st.uid, 'REBUILD'
            op = r.operator("fskr.gaze_pad", text=_tr("지우기"), icon='X')
            op.uid, op.action = st.uid, 'REMOVE'
            if hasattr(s, "arrange"):
                from .operators import arrange_button
                arrange_button(col, s, EY._BONE_PREFIX)   # 시선 패드만
            r = col.row(align=True)
            r.prop(st, "look_x", slider=True)
            r.prop(st, "look_y", slider=True)
            r.operator("fskr.eye_gaze_reset", text="",
                       icon='LOOP_BACK').uid = st.uid
            op = r.operator("fskr.eye_key", text="", icon='KEY_HLT')
            op.uid, op.lid = st.uid, ""
            col.prop(st, "autokey", icon='REC')
        # 2) 범위
        col = _step(lay, "2", _tr("움직이는 범위 (끝까지 밀었을 때)"), True,
                    'FULLSCREEN_ENTER')
        _guide(col, [_tr("값 = 캔버스 크기 대비 거리 (0.03 = 3%)"),
                     _tr("아래 화살표로 끝까지 밀어 보며 맞추세요")])
        g = col.grid_flow(columns=2, even_columns=True, align=True)
        g.prop(st, "range_x", text=_tr("오른쪽"))
        sub = g.row(align=True)
        sub.enabled = not st.link_x
        sub.prop(st, "range_xl", text=_tr("왼쪽"))
        g.prop(st, "range_y", text=_tr("위"))
        sub = g.row(align=True)
        sub.enabled = not st.link_y
        sub.prop(st, "range_yd", text=_tr("아래"))
        r = col.row(align=True)
        r.prop(st, "link_x", toggle=True, icon='LINKED')
        r.prop(st, "link_y", toggle=True, icon='LINKED')
        if has_pad:
            # 3×3 같은 폭 격자 (아이콘 버튼과 글자 버튼이 섞이면 폭이 달라짐)
            tb = col.grid_flow(row_major=True, columns=3, even_columns=True,
                               even_rows=True, align=True)
            arrows = {(-1, 1): "↖", (0, 1): "↑", (1, 1): "↗",
                      (-1, 0): "←", (0, 0): None, (1, 0): "→",
                      (-1, -1): "↙", (0, -1): "↓", (1, -1): "↘"}
            for y9 in (1, 0, -1):
                for x9 in (-1, 0, 1):
                    t9 = arrows[(x9, y9)]
                    op = tb.operator("fskr.gaze_test",
                                     text=t9 if t9 else _tr("가운데"))
                    op.uid, op.x, op.y = st.uid, float(x9), float(y9)
        # 3) 따라가는 파츠
        col = _step(lay, "3", _tr("시선을 따라가는 파츠"),
                    any(L.look for L in st.layers), 'RENDERLAYERS')
        _guide(col, [_tr("부모만 켜면 자식(홍채·하이라이트)은 같이 "
                         "움직입니다"),
                     _tr("자식에서 켜면 부모 위에 '추가로' 더 움직임 "
                         "(배율로 양 조절)")])
        lb = col.column(align=True)
        for L in display_order(st):
            if L.kind == 'MOUTH':
                continue
            anc = EY.layer_ancestors(st, L)
            r = lb.row(align=True)
            for _ in anc:
                r.label(text="", icon='BLANK1')
            r.prop(L, "look", text="", toggle=True, icon='ORIENTATION_VIEW')
            nm = r.row(align=True)
            nm.label(text=L.name)
            if any(a.look for a in anc):
                info = nm.row()
                info.active = False
                info.label(text=_tr("부모 따라감"))
            sub = r.row(align=True)
            sub.active = L.look
            sub.prop(L, "look_mul", text="")


def display_order(st):
    """④ 목록과 같은 순서 (아웃라이너처럼 부모 다음 줄에 자식)."""
    idx = {L.lid: k for k, L in enumerate(st.layers)}
    out, seen = [], set()

    def walk(n):
        if n.lid in seen:
            return
        seen.add(n.lid)
        out.append(n)
        for c in sorted(EY.layer_children(st, n), key=lambda x: idx[x.lid]):
            walk(c)
    for L in st.layers:
        if EY.layer_parent(st, L) is None:
            walk(L)
    for L in st.layers:
        if L.lid not in seen:
            seen.add(L.lid)
            out.append(L)
    return out


class FSKR_PT_f4_layers(_SpritePanel, bpy.types.Panel):
    _tab = 'PARTS'
    bl_label = "④ 캔버스 레이어 (파츠 배치)"
    bl_order = 4

    def draw(self, context):
        s = context.scene.fskr
        lay = self.layout
        st = _canvas(s)
        rig = s.rig
        if st is None:
            lay.label(text=_tr("먼저 ①에서 얼굴 캔버스를 만드세요"),
                      icon='INFO')
            return
        if not len(st.sheets):
            lay.label(text=_tr("먼저 ③에서 스프라이트 시트를 추가하세요"),
                      icon='INFO')
        col = _step(lay, "", _tr("파츠 올리기"), len(st.layers) > 0,
                    'RENDERLAYERS')
        _guide(col, [_tr("+ 로 파츠와 태그를 고르면 그 태그의 기준 마커 "
                         "위치에 놓입니다"),
                     _tr("목록 위에 있을수록 앞에 그려집니다 (▲▼로 순서)")])
        # 태그 (그룹) 관리
        tb = col.box().column(align=True)
        hr = tb.row(align=True)
        hr.label(text=_tr("태그 (그룹)"), icon='OUTLINER_COLLECTION')
        hr.operator("fskr.tag_base", text="", icon='PRESET')
        hr.operator("fskr.tag_add", text="", icon='ADD')
        if not len(st.tags):
            tb.label(text=_tr("+ 로 태그를 만들거나, 파츠를 추가할 때 '새 "
                              "태그'로 바로 만드세요"), icon='INFO')
        for g in st.tags:
            r = tb.row(align=True)
            r.prop(g, "expand", text="", emboss=False,
                   icon='TRIA_DOWN' if g.expand else 'TRIA_RIGHT')
            r.prop(g, "name", text="")
            _paste(r, g)
            m = EY.find_marker(st, g.marker)
            sub = r.row(align=True)
            sub.active = False
            sub.label(text=m.name if m else _tr("가운데"),
                      icon='PIVOT_CURSOR')
            r.operator("fskr.tag_remove", text="", icon='X').uid = g.uid
            if g.expand:
                gb = tb.box().column(align=True)
                gb.prop(g, "marker_pick")
                gb.label(text=_tr("새 파츠 기본값"))
                rr = gb.row(align=True)
                rr.prop(g, "sym", toggle=True, icon='MOD_MIRROR')
                rr.prop(g, "look", toggle=True, icon='ORIENTATION_VIEW')
                rr.prop(g, "mouth", toggle=True, icon='SPEAKER')
                gb.prop(g, "over", toggle=True, icon='XRAY')
                rr = gb.row(align=True)
                rr.prop(g, "size")
                rr.prop(g, "dy")
                gb.prop(g, "clip_pick")
                ri = gb.row(align=True)
                ri.label(text=_tr("키 보간"), icon='IPO_BEZIER')
                ri.prop(g, "key_interp", expand=True)
        if len(st.tags):
            col.prop(st, "tag_filter_pick", text="")
        # 파츠 폴더 (보이는 파츠 구성 묶음)
        if 0 <= st.part_set_active < len(st.part_sets):
            ps9 = st.part_sets[st.part_set_active]
            fr9 = col.row(align=True)
            fr9.label(text="", icon='FILE_FOLDER')
            fr9.prop(ps9, "name", text="")
            from .layer_vp import paste_btn as _pb9
            _pb9(fr9, ps9)
            op = fr9.operator("fskr.part_set", text="", icon='FILE_REFRESH')
            op.action = 'UPDATE'
            fr9.operator("fskr.part_set", text="", icon='X').action = 'ALL'
        row = col.row()
        row.template_list("FSKR_UL_face_layers", "fl_" + st.uid, st,
                          "layers", st, "layer_index", rows=6)
        cc = row.column(align=True)
        cc.operator("fskr.part_add", text="", icon='ADD')
        cc.operator("fskr.eye_layer_remove", text="",
                    icon='REMOVE').uid = st.uid
        cc.operator("fskr.eye_layer_duplicate", text="",
                    icon='DUPLICATE').uid = st.uid
        cc.menu("FSKR_MT_part_sets", text="", icon='FILE_FOLDER')
        cc.separator()
        op = cc.operator("fskr.eye_layer_move", text="", icon='TRIA_UP')
        op.uid, op.direction = st.uid, -1
        op = cc.operator("fskr.eye_layer_move", text="", icon='TRIA_DOWN')
        op.uid, op.direction = st.uid, 1
        if not len(st.layers):
            return
        i = max(0, min(len(st.layers) - 1, st.layer_index))
        L = st.layers[i]
        self._draw_detail(context, lay, s, st, L, rig)

    def _draw_folder(self, col, s, st, L, rig):
        """폴더: 켜기(전환) · 안의 파츠 · 키."""
        b = col.box().column(align=True)
        grp = EY.folder_group(st, L)
        hr = b.row(align=True)
        hr.scale_y = 1.3
        if grp:
            op = hr.operator("fskr.eye_folder_on",
                             text=_tr("이 폴더로 전환") if not L.show
                             else _tr("켜져 있음"),
                             icon='FILE_FOLDER', depress=L.show)
            op.uid, op.lid = st.uid, L.lid
        hr.prop(L, "show", text=_tr("보이기"), toggle=True,
                icon='HIDE_OFF' if L.show else 'HIDE_ON')
        g9 = b.column(align=True)
        g9.scale_y = 0.8
        if grp:
            g9.label(text=_tr("함께 전환되는 폴더: ") + ", ".join(
                G.name for G in grp), icon='INFO')
        else:
            g9.label(text=_tr("같은 태그로 같은 자리에 폴더를 하나 더 만들면 "
                              "둘 중 하나만 켜집니다"), icon='INFO')
        g9.label(text=_tr("켜짐/꺼짐은 키·표정 프리셋에 들어갑니다"))
        kids = EY.layer_children(st, L)
        cb = col.box().column(align=True)
        cb.label(text=_tr("폴더 안 파츠") + " (%d)" % len(kids),
                 icon='OUTLINER')
        if not kids:
            n9 = cb.column(align=True)
            n9.scale_y = 0.8
            n9.label(text=_tr("파츠를 고른 뒤 '부모'를 이 폴더로 바꾸면 "
                              "들어옵니다"))
        for c in kids:
            cr = cb.row(align=True)
            cr.label(text=c.name, icon='FILE_FOLDER'
                     if getattr(c, "kind", 'PART') == 'FOLDER'
                     else 'IMAGE_DATA')
        kb = col.row(align=True)
        kb.scale_y = 1.2
        op = kb.operator("fskr.eye_key", text=_tr("이 폴더 키 넣기"),
                         icon='KEY_HLT')
        op.uid, op.lid, op.what = st.uid, L.lid, 'ALL'
        kb.prop(st, "autokey", icon='REC', text=_tr("바꾸면 자동 키"))

    def _draw_detail(self, context, lay, s, st, L, rig):
        col = _step(lay, "", _tr("선택한 파츠: ") + L.name, True,
                    'RENDERLAYERS')
        r = col.row(align=True)
        r.prop(L, "name", text="")
        from .layer_vp import eligible, paste_btn
        paste_btn(r, L)
        r.prop(L, "tag_pick", text="")
        col.prop(L, "parent_pick", text=_tr("부모"), icon='CON_CHILDOF')
        if EY.layer_parent(st, L) is not None:
            r = col.row(align=True)
            r.label(text=_tr("부모 색 따라가기"), icon='COLOR')
            r.prop(L, "inh_hsv", toggle=True)
            r.prop(L, "inh_ov", toggle=True)
        if getattr(L, "kind", 'PART') == 'FOLDER':
            self._draw_folder(col, s, st, L, rig)
            return
        draw_part_props(col, context, s, st, L, rig)
        # 겹치기
        b = col.box().column()
        b.label(text=_tr("겹치기"), icon='SELECT_INTERSECT')
        b.prop(L, "clip_pick", text=_tr("클리핑 마스크"), icon='MOD_MASK')
        inh9 = [c for c in EY.clip_chain(st, L) if c != L.clip]
        if inh9:
            ib9 = b.row()
            ib9.active = False
            ib9.label(text=_tr("부모에게서 물려받음: ") + ", ".join(
                (EY._layer(st, c).name if EY._layer(st, c) else c)
                for c in inh9), icon='CON_CHILDOF')
        b.prop(L, "over", toggle=True, icon='XRAY')
        if L.over:
            ob9 = bpy.data.objects.get(EY._over_name(st))
            ib = b.column(align=True)
            ib.prop(L, "over_alpha", slider=True)
            ib.separator()
            ib.label(text=_tr("모든 '머리카락 위로' 파츠 공통"), icon='INFO')
            rr = ib.row(align=True)
            rr.prop(st, "over_dist")
            rr.operator("fskr.over_measure", text="", icon='DRIVER_DISTANCE')\
                .uid = st.uid
            if L.kind == 'MOUTH':
                ib.label(text=_tr("입 파츠는 지원하지 않습니다"), icon='ERROR')
            elif ob9 is None:
                ib.label(text=_tr("오버레이가 아직 없습니다"), icon='ERROR')
        # 색
        b = col.box().column(align=True)
        r = b.row(align=True)
        r.prop(L, "show_fx", emboss=False, text=_tr("색조/채도/명도"),
               icon='TRIA_DOWN' if L.show_fx else 'TRIA_RIGHT')
        op = r.operator("fskr.eye_hsv_reset", text="", icon='LOOP_BACK')
        op.uid, op.lid = st.uid, L.lid
        if L.show_fx:
            b.prop(L, "hue", slider=True)
            b.prop(L, "sat", slider=True)
            b.prop(L, "val", slider=True)
            # 색 맞추기: 원래 색 → 바꿀 색
            cb = b.box().column(align=True)
            cr = cb.row(align=True)
            cr.prop(L, "show_cm", emboss=False, text=_tr("색 맞추기"),
                    icon='TRIA_DOWN' if L.show_cm else 'TRIA_RIGHT')
            if L.show_cm:
                r1 = cb.row(align=True)
                r1.prop(L, "cm_src")
                op = r1.operator("fskr.eye_color_pick", text="",
                                 icon='EYEDROPPER')
                op.uid, op.lid = st.uid, L.lid
                cb.prop(L, "cm_dst")
                op = cb.operator("fskr.eye_color_match", icon='COLOR')
                op.uid, op.lid = st.uid, L.lid
                g9 = cb.column(align=True)
                g9.scale_y = 0.8
                g9.active = False
                g9.label(text=_tr("색 칸을 누르면 Hex(784343 등)로 입력할 수 "
                                  "있습니다"), icon='INFO')
            # 색 덮기 (컬러 오버레이)
            ob = b.box().column(align=True)
            orow = ob.row(align=True)
            orow.prop(L, "ov_on", text=_tr("색 덮기"), icon='BRUSH_DATA')
            if L.ov_on:
                orow.prop(L, "ov_color", text="")
                ob.prop(L, "ov_mode", expand=True)
                ob.prop(L, "ov_fac", slider=True)
        # 움직임
        b = col.box().column(align=True)
        b.label(text=_tr("움직임"), icon='ANIM')
        anc = EY.layer_ancestors(st, L)
        if anc:
            b.label(text=_tr("부모(%s)의 위치·시선을 따라갑니다") % anc[0].name,
                    icon='CON_CHILDOF')
        r = b.row(align=True)
        r.prop(L, "look", toggle=True, icon='ORIENTATION_VIEW',
               text=_tr("시선 추가 이동") if any(a.look for a in anc)
               else _tr("시선 따라 이동"))
        sub = r.row(align=True)
        sub.active = L.look
        sub.prop(L, "look_mul")
        if L.kind != 'MOUTH':
            b.prop(L, "link_pick", icon='LINKED')
        r = b.row(align=True)
        r.prop(L, "depth", text=_tr("깊이 (패럴랙스)"))
        if anc:
            sub = r.row(align=True)
            sub.active = False
            sub.label(text="= %.3f" % EY._eff_depth(st, L))
        # 캔버스 전체 패럴랙스 강도 (모든 파츠 공통)
        r = b.row(align=True)
        r.prop(st, "parallax", slider=True)
        nd9 = sum(1 for L9 in st.layers if L9.depth)
        sub = r.row(align=True)
        sub.active = False
        sub.label(text=_tr("깊이 있는 파츠 %d개") % nd9)


class FSKR_PT_f5_presets(_SpritePanel, bpy.types.Panel):
    _tab = 'EXPR'
    bl_label = "⑤ 표정 프리셋"
    bl_order = 5

    def draw(self, context):
        s = context.scene.fskr
        lay = self.layout
        st = _canvas(s)
        if st is None or not len(st.layers):
            lay.label(text=_tr("④에서 파츠를 배치한 뒤 표정으로 저장합니다"),
                      icon='INFO')
            return
        col = _step(lay, "", _tr("표정 저장 · 적용"), len(st.presets) > 0,
                    'SHAPEKEY_DATA')
        _guide(col, [_tr("배치를 마치면 '프리셋 저장'으로 표정을 만드세요"),
                     _tr("목록에서 누르면 바로 그 표정으로 바뀝니다 (키 없음)"),
                     _tr("🔑 = 그 표정으로 바꾸고 현재 프레임에 키 넣기")])
        row = col.row()
        row.template_list("FSKR_UL_face_presets", "fp_" + st.uid, st,
                          "presets", st, "preset_index", rows=4)
        cc = row.column(align=True)
        cc.operator("fskr.face_preset_save", text="", icon='ADD')
        cc.operator("fskr.face_preset_remove", text="", icon='REMOVE')
        # 프리셋 편집 (키프레임과 충돌 없이 프리셋 내용 고치기)
        if st.preset_edit:
            eb = col.box().column(align=True)
            hr = eb.row()
            hr.alert = True
            nm9 = st.presets[st.preset_index].name if \
                0 <= st.preset_index < len(st.presets) else "-"
            hr.label(text=_tr("프리셋 편집 중: ") + nm9, icon='EDITMODE_HLT')
            g9 = eb.column(align=True)
            g9.scale_y = 0.8
            g9.label(text=_tr("키프레임은 잠시 멈춰 있고, 키는 들어가지 "
                              "않습니다"), icon='INFO')
            g9.label(text=_tr("④·⑥에서 파츠를 고친 뒤 '저장하고 끝내기'"))
            r = eb.row(align=True)
            r.scale_y = 1.3
            r.operator("fskr.preset_edit", text=_tr("저장하고 끝내기"),
                       icon='CHECKMARK').action = 'SAVE'
            r.operator("fskr.preset_edit", text=_tr("취소"),
                       icon='X').action = 'CANCEL'
        else:
            r = col.row(align=True)
            r.scale_y = 1.2
            r.operator("fskr.face_preset_save", icon='FILE_TICK')
            r.operator("fskr.preset_edit", text=_tr("프리셋 편집"),
                       icon='GREASEPENCIL').action = 'START'
        # 뷰포트 컨트롤러 (표정 목록) — 만들기 · 다시 만들기 · 지우기 · 배치 모드
        if s.rig is not None:
            from .preset_vp import pre_exists
            vb = col.box().column(align=True)
            vb.label(text=_tr("뷰포트 컨트롤러 (표정 목록)"),
                     icon='ARMATURE_DATA')
            if not pre_exists(s.rig, st):
                r = vb.row()
                r.scale_y = 1.3
                r.enabled = len(st.presets) > 0
                r.operator("fskr.preset_vp", text=_tr("표정 컨트롤러 만들기"),
                           icon='ADD').action = 'BUILD'
                if not len(st.presets):
                    vb.label(text=_tr("프리셋을 하나 이상 저장하면 만들 수 "
                                      "있습니다"), icon='INFO')
            else:
                r = vb.row(align=True)
                r.operator("fskr.preset_vp", text=_tr("다시 만들기"),
                           icon='FILE_REFRESH').action = 'BUILD'
                r.operator("fskr.preset_vp", text=_tr("지우기"),
                           icon='X').action = 'REMOVE'
                if hasattr(s, "arrange"):
                    from .operators import arrange_button
                    arrange_button(vb, s, "FP_pre_")   # 표정 목록만


class FSKR_PT_f8_vp(_SpritePanel, bpy.types.Panel):
    _tab = 'CTRL'
    bl_idname = "FSKR_PT_sprite_vp"
    bl_label = "뷰포트 컨트롤러"
    bl_order = 8

    def draw_header(self, context):
        self.layout.label(text="", icon='ARMATURE_DATA')

    def draw(self, context):
        s = context.scene.fskr
        st = _canvas(s)
        if st is None or s.rig is None:
            self.layout.label(text=_tr("①에서 캔버스와 리그를 먼저 정하세요"),
                              icon='INFO')
            return
        from .layer_vp import draw_panel
        draw_panel(self.layout, s, st)


face_classes = (
    FSKR_OT_face_front_view, FSKR_OT_marker_place, FSKR_OT_marker_add, FSKR_OT_marker_remove,
    FSKR_OT_tag_add, FSKR_OT_tag_remove, FSKR_OT_tag_base, FSKR_OT_sheet_add, FSKR_OT_sheet_remove,
    FSKR_OT_sheet_slice, FSKR_OT_sheet_reload, FSKR_OT_sheet_replace,
    FSKR_OT_sheet_fix_edges,
    FSKR_OT_part_add, FSKR_OT_preset_save_face, FSKR_OT_ime_dlg, FSKR_OT_preset_edit,
    FSKR_OT_preset_apply_face, FSKR_OT_preset_remove_face,
    FSKR_UL_face_layers, FSKR_UL_face_presets,
    FSKR_PT_f1_canvas, FSKR_PT_f2_markers, FSKR_PT_f3_sheets,
    FSKR_PT_f4_layers, FSKR_PT_f5_presets, FSKR_PT_f7_gaze,
    FSKR_PT_f8_vp,
)


# ------------------------------------------------------------------
# '바꾸면 자동 키': 고른 파츠의 값이 바뀌면 그 값만 현재 프레임에 키
# ------------------------------------------------------------------

_AK = {"key": None, "snap": None}


_AKM = {}


def _draw_cell_msel(layout, st, L, x):
    """일괄 조절: 시트의 칸을 체크 (입·일반 파츠 공통, 접을 수 있음)."""
    tab = x.tab
    sel = AT.cells_msel(tab)
    if x.mouth:
        ait = tab
        icons = AT._PREV_ICONS.get(ait.uid) if AT._thumbs_ready(ait) \
            else None
        fl = AT._PREV_FILLED.get(ait.uid) or {}
        cols, rows = max(1, int(ait.cols)), max(1, int(ait.rows))
        cL = None
    else:
        cst, cL = EY._cell_source(bpy.context.scene.fskr, st, L)
        if not EY._thumbs_ready(cst, cL):
            EY._thumbs_request(cst, cL)
        u = EY._thumb_uid(cst, cL)
        icons = AT._PREV_ICONS.get(u)
        fl = AT._PREV_FILLED.get(u) or {}
        cols, rows = max(1, int(cL.cols)), max(1, int(cL.rows))

    def msel_op(lay, **kw):
        if x.mouth:
            op = lay.operator("fskr.atlas_cell_msel", **kw)
            op.uid = tab.uid
        else:
            op = lay.operator("fskr.part_cell_msel", **kw)
            op.uid, op.lid = st.uid, L.lid
        return op

    def show_op(lay, **kw):
        if x.mouth:
            op = lay.operator("fskr.atlas_cell_show", **kw)
            op.uid = tab.uid
        else:
            op = lay.operator("fskr.part_cell_show", **kw)
            op.uid, op.lid = st.uid, L.lid
        return op

    # 편집 모드를 가진 쪽: 입 = 입 시트, 일반 파츠 = 칸을 가진 레이어
    eown = tab if x.mouth else cL
    b = layout.box().column(align=True)
    if eown is not None and (not x.mouth or tab.layout == 'FREE'):
        er = b.row(align=True)
        er.alert = bool(eown.edit_on)
        er.prop(eown, "edit_on", toggle=True,
                icon='EDITMODE_HLT' if eown.edit_on else 'OBJECT_DATAMODE',
                text=(_tr("편집 모드 켜짐 (%d-%d 고정)") % tuple(x.cur))
                if eown.edit_on else _tr("편집 모드 (키프레임 무시)"))
        if eown.edit_on:
            n9 = b.row()
            n9.scale_y = 0.8
            n9.label(text=_tr("고른 칸이 키프레임과 상관없이 계속 보입니다. "
                              "끝나면 꼭 끄세요"), icon='INFO')
    hr = b.row(align=True)
    hr.prop(tab, "msel_open", text="", emboss=False,
            icon='TRIA_DOWN' if tab.msel_open else 'TRIA_RIGHT')
    hr.prop(tab, "msel_open", emboss=False, toggle=True,
            text=_tr("일괄 조절") + ("  (%d)" % len(sel) if sel else ""))
    if sel:
        msel_op(hr, text="", icon='X').clear = True
    if not tab.msel_open:
        if sel:
            b.label(text=", ".join("%d-%d" % rc for rc in sorted(sel)),
                    icon='CHECKBOX_HLT')
        return
    cur = tuple(x.cur)
    g = b.grid_flow(row_major=True, columns=4, even_columns=True,
                    even_rows=True, align=True)
    for r in range(rows):
        for c in range(cols):
            if fl and not fl.get((r, c), True):
                continue          # 빈 칸은 생략
            ic = icons.get((r, c)) if icons else None
            cc = g.column(align=True)
            is_cur = (r, c) == cur
            if ic:
                cc.box().template_icon(icon_value=ic, scale=2.6)
            bt = cc.row(align=True)
            bt.alert = is_cur
            op = msel_op(bt, text="",
                         icon='CHECKBOX_HLT' if (r, c) in sel
                         else 'CHECKBOX_DEHLT', depress=(r, c) in sel)
            op.r, op.c = r, c
            sb = bt.row(align=True)
            sb.scale_x = 3.0
            op = show_op(sb, text="%d-%d" % (r, c), icon='HIDE_OFF',
                         depress=is_cur)
            op.r, op.c = r, c
    hn = b.row()
    hn.scale_y = 0.8
    hn.label(text=_tr("칸 번호 버튼 = 그 칸을 뷰포트에 보기 · 체크 = 일괄 조절"),
             icon='INFO')
    if sel:
        n = b.column(align=True)
        n.scale_y = 0.8
        n.label(text=_tr("지금 칸(빨간 버튼)의 배치를 바꾸면 체크한 칸도 "
                         "같이 바뀝니다"), icon='INFO')
        n.label(text=_tr("크기는 같은 비율로, 위치·회전은 움직인 만큼"))


def _place_fields(b, rig, L, P, cell):
    """배치 값 줄 (위치 / 가로·세로·🔗 / 회전·불투명도 / 크롭).

    cell: True = 이 칸 값(칸별), False = 전체 공통 값(리그 프로퍼티, 키 가능).
    """
    r = b.row(align=True)
    if cell:
        r.prop(L, "cell_px", text=_tr("위치 X"))
        r.prop(L, "cell_py", text=_tr("위치 Y"))
        r = b.row(align=True)
        lk = L.cell_lock
        r.prop(L, "cell_sx", text=_tr("가로"))
        r.prop(L, "cell_sy", text=_tr("세로"))
        r.prop(L, "cell_lock", text="",
               icon='LINKED' if lk else 'UNLINKED')
        r = b.row(align=True)
        r.prop(L, "cell_rot", text=_tr("회전"))
        r.prop(L, "cell_op", text=_tr("불투명도"), slider=True)
        cb9 = b.column(align=True)
        cb9.label(text=_tr("크롭 (그림 영역 기준으로 잘라내기)"),
                  icon='SELECT_SUBTRACT')
        r = cb9.row(align=True)
        r.prop(L, "cell_ct", text=_tr("위에서"), slider=True)
        r.prop(L, "cell_cb", text=_tr("아래서"), slider=True)
        r = cb9.row(align=True)
        r.prop(L, "cell_cl", text=_tr("왼쪽에서"), slider=True)
        r.prop(L, "cell_cr", text=_tr("오른쪽에서"), slider=True)
        return True
    if not all(p in rig.keys() for p in P[:6]):
        return False
    r.prop(rig, '["%s"]' % P[1], text=_tr("위치 X"))
    r.prop(rig, '["%s"]' % P[2], text=_tr("위치 Y"))
    r = b.row(align=True)
    # 🔗 고정이어도 가로·세로를 모두 보여 줌 (비율 유지하며 같이 바뀜)
    r.prop(rig, '["%s"]' % P[3], text=_tr("가로"))
    if L.scale_lock:
        r.prop(L, "size_y_lk", text=_tr("세로"))
    else:
        r.prop(rig, '["%s"]' % P[4], text=_tr("세로"))
    r.prop(L, "scale_lock", text="",
           icon='LINKED' if L.scale_lock else 'UNLINKED')
    r = b.row(align=True)
    r.prop(rig, '["%s"]' % P[5], text=_tr("회전"))
    r.prop(rig, '["%s"]' % P[0], text=_tr("불투명도"), slider=True)
    cb9 = b.column(align=True)
    cb9.enabled = all(p in rig.keys() for p in P[6:])
    cb9.label(text=_tr("크롭 (그림 영역 기준으로 잘라내기)"),
              icon='SELECT_SUBTRACT')
    if cb9.enabled:
        r = cb9.row(align=True)
        r.prop(rig, '["%s"]' % P[6], text=_tr("위에서"), slider=True)
        r.prop(rig, '["%s"]' % P[7], text=_tr("아래서"), slider=True)
        r = cb9.row(align=True)
        r.prop(rig, '["%s"]' % P[8], text=_tr("왼쪽에서"), slider=True)
        r.prop(rig, '["%s"]' % P[9], text=_tr("오른쪽에서"), slider=True)
    return True


def draw_part_props(col, context, s, st, L, rig, mouth_panel=False):
    """파츠 속성 (그림 · 일괄 조절 · 배치 · 키). ④와 ⑥ 입 패널이 같이 씀.

    입·일반 파츠 모두 같은 모양: 칸이 2개 이상이면 '배치'는 지금 칸의
    값(칸마다 따로 저장)이고, 모든 칸 공통 값(키 가능)은 아래 '전체 배치'.
    """
    from .layer_vp import eligible
    mouth = L.kind == 'MOUTH'
    ait = EY._layer_atlas(s, L) if mouth else None
    x = EY.cell_table(s, st, L)
    if getattr(st, "preset_edit", False):
        pb = col.box().column(align=True)
        hr = pb.row()
        hr.alert = True
        nm9 = st.presets[st.preset_index].name if \
            0 <= st.preset_index < len(st.presets) else "-"
        hr.label(text=_tr("프리셋 편집 중: ") + nm9 + "  ("
                 + _tr("키프레임 멈춤") + ")", icon='EDITMODE_HLT')
        r = pb.row(align=True)
        r.operator("fskr.preset_edit", text=_tr("저장하고 끝내기"),
                   icon='CHECKMARK').action = 'SAVE'
        r.operator("fskr.preset_edit", text=_tr("취소"),
                   icon='X').action = 'CANCEL'

    # 그림
    b = col.box().column()
    hr = b.row()
    hr.label(text=_tr("그림"), icon='IMAGE_DATA')
    if mouth:   # 뷰포트 컨트롤러는 입(시퀀스)만
        sub9 = hr.row()
        sub9.alignment = 'RIGHT'
        sub9.active = eligible(s, L)
        sub9.prop(L, "show_vp", text=_tr("뷰포트 컨트롤러"),
                  icon='ARMATURE_DATA')
    if mouth:
        if ait is not None:
            if not AT._thumbs_ready(ait):
                AT._thumbs_request(ait)
            r = b.row(align=True)
            op = r.operator("fskr.atlas_step", text="", icon='TRIA_LEFT')
            op.uid, op.what, op.delta = ait.uid, 'CELL', -1
            r.prop(ait, "pick_cell", text="")
            op = r.operator("fskr.atlas_step", text="", icon='TRIA_RIGHT')
            op.uid, op.what, op.delta = ait.uid, 'CELL', 1
            op = r.operator("fskr.atlas_key", text="", icon='KEY_HLT')
            op.uid, op.what = ait.uid, 'BOTH'
            b.template_icon_view(ait, "pick_cell", show_labels=True,
                                 scale=7.0, scale_popup=6.0)
        if not mouth_panel:
            n9 = b.row()
            n9.scale_y = 0.8
            n9.label(text=_tr("말할 때 입은 ⑥ 시퀀스·립싱크로 바뀝니다"),
                     icon='INFO')
    else:
        cst, cL = EY._cell_source(s, st, L)
        if cL is not L or cst is not st:
            b.label(text=_tr("칸 따라가기") + ": " + cL.name,
                    icon='LINKED')
        else:
            if not EY._thumbs_ready(st, L):
                EY._thumbs_request(st, L)
            r = b.row(align=True)
            op = r.operator("fskr.eye_cell_step", text="",
                            icon='TRIA_LEFT')
            op.uid, op.lid, op.delta = st.uid, L.lid, -1
            r.prop(L, "pick", text="")
            op = r.operator("fskr.eye_cell_step", text="",
                            icon='TRIA_RIGHT')
            op.uid, op.lid, op.delta = st.uid, L.lid, 1
            op = r.operator("fskr.eye_key", text="", icon='KEY_HLT')
            op.uid, op.lid = st.uid, L.lid
            b.template_icon_view(L, "pick", show_labels=True, scale=7.0,
                                 scale_popup=6.0)
    if x is not None:
        _draw_cell_msel(b, st, L, x)
    # 배치
    ast, aL = EY._anim_source(s, st, L)
    P = EY._anim_props(ast, aL)
    b = col.box().column(align=True)
    r = b.row(align=True)
    if x is not None and EY.preset_editing(s):
        r.label(text=_tr("배치 (마커 기준)") + "  ·  " + _tr("이 표정"),
                icon='OBJECT_ORIGIN')
    elif x is not None:
        r.label(text=_tr("배치 (마커 기준)") + "  ·  "
                + (_tr("이 칸 %d-%d") % tuple(x.cur)), icon='OBJECT_ORIGIN')
        op = r.operator("fskr.cell_place_reset", text="", icon='LOOP_BACK')
        op.uid, op.lid = st.uid, L.lid
    else:
        r.label(text=_tr("배치 (마커 기준)"), icon='OBJECT_ORIGIN')
        op = r.operator("fskr.eye_place_reset", text="", icon='LOOP_BACK')
        op.uid, op.lid = ast.uid, aL.lid
        op = r.operator("fskr.eye_key", text="", icon='KEY_HLT')
        op.uid, op.lid, op.what = ast.uid, aL.lid, 'ANIM'
    if x is not None and EY.preset_editing(s):
        h9 = b.row()
        h9.active = False
        h9.label(text=_tr("프리셋 편집 중: 여기서 바꾼 값은 이 표정에만 "
                          "저장됩니다 (칸 보정은 그대로)"), icon='INFO')
    tr9 = b.row()
    tr9.scale_y = 1.2
    op = tr9.operator("fskr.part_transform", icon='FULLSCREEN_ENTER',
                      text=_tr("뷰포트에서 자유 변형 (Ctrl+T)"))
    op.uid, op.lid = st.uid, L.lid
    if not _place_fields(b, rig, L, P, x is not None):
        op = b.operator("fskr.eye_build", text=_tr("배치 켜기 "
                        "(머티리얼 다시 만들기)"), icon='FILE_REFRESH')
        op.uid = st.uid
    r = b.row(align=True)
    r.label(text=_tr("크기·회전 기준"))
    r.prop(L, "pivot", expand=True)
    if L.pivot == 'PART':
        op = r.operator("fskr.eye_pivot_recenter", text="",
                        icon='FILE_REFRESH')
        op.uid, op.lid = st.uid, L.lid
    r = b.row(align=True)
    r.prop(L, "flip_x", toggle=True, icon='MOD_MIRROR')
    r.prop(L, "sym", toggle=True, icon='MOD_MIRROR')
    if L.sym:   # 대칭 복사: 보일 쪽 (윙크 등)
        r = b.row(align=True)
        r.prop(L, "sym_side", expand=True)
        sd9 = EY.sym_side_label(s, st, L)
        if sd9:
            h9 = b.row()
            h9.active = False
            h9.label(text=_tr("원본 = 화면 왼쪽, 복사본 = 화면 오른쪽")
                     if sd9 == "L" else
                     _tr("원본 = 화면 오른쪽, 복사본 = 화면 왼쪽"),
                     icon='INFO')
    # 키: 이 파츠의 지금 값 전부 (칸·배치·불투명도·크롭)
    b.separator(factor=0.5)
    kb = b.row(align=True)
    kb.scale_y = 1.3
    op = kb.operator("fskr.eye_key", text=_tr("이 파츠 키 넣기"),
                     icon='KEY_HLT')
    op.uid, op.lid, op.what = st.uid, L.lid, 'ALL'
    kb.prop(st, "autokey", icon='REC', text=_tr("바꾸면 자동 키"))
    ir = b.row(align=True)
    tg9 = EY.layer_tag(st, L)
    ir.label(text=(_tr("보간") + " · " + tg9.name) if tg9 is not None
             else _tr("보간"), icon='IPO_BEZIER')
    ir.prop(EY.interp_owner(st, L), "key_interp", expand=True)
    EY.interp_menu(ir, st, L)
    if tg9 is not None:
        hn9 = b.row()
        hn9.scale_y = 0.8
        hn9.label(text=_tr("보간은 태그마다 따로 저장됩니다 (같은 태그 "
                           "파츠끼리 공유)"), icon='INFO')
    # 전체 배치 (모든 칸 공통 · 키·애니메이션은 이 값에 들어감)
    if x is not None:
        cb = col.box().column(align=True)
        r = cb.row(align=True)
        r.prop(L, "show_common", text="", emboss=False,
               icon='TRIA_DOWN' if L.show_common else 'TRIA_RIGHT')
        r.prop(L, "show_common", emboss=False, toggle=True,
               text=_tr("전체 배치 (모든 칸 공통)"))
        op = r.operator("fskr.eye_place_reset", text="", icon='LOOP_BACK')
        op.uid, op.lid = ast.uid, aL.lid
        op = r.operator("fskr.eye_key", text="", icon='KEY_HLT')
        op.uid, op.lid, op.what = ast.uid, aL.lid, 'ANIM'
        if L.show_common:
            w9 = cb.column(align=True)
            w9.scale_y = 0.8
            w9.label(text=_tr("여기 값은 모든 칸에 똑같이 적용되고, 키·"
                              "애니메이션은 이 값에 들어갑니다"), icon='INFO')
            w9.label(text=_tr("위 '배치'는 이 값 + 칸별 보정입니다"))
            _place_fields(cb, rig, L, P, False)


def _ak_mouth(ctx, s, rig):
    """⑥ 입 시트의 '바꾸면 자동 키' 감시."""
    if rig is None or getattr(s, "ui_mode", 'DRIVER') != 'SPRITE' or \
            EY.preset_editing(s):
        _AKM.clear()
        return
    f = ctx.scene.frame_current
    for it in s.atlases:
        if not AT.mouth_autokey(s, it):
            _AKM.pop(it.uid, None)
            continue
        try:
            props = AT.mouth_watch_props(s, it)
            snap = {p: float(rig[p]) for p in props}
        except Exception:
            continue
        old = _AKM.get(it.uid)
        if old is None or old[0] != f:
            _AKM[it.uid] = (f, snap)
            continue
        changed = {p for p, v in snap.items()
                   if abs(v - old[1].get(p, v)) > 1e-7}
        if changed:
            try:
                AT.key_mouth(s, it, only=changed)
            except Exception as e:
                print("FSKR mouth autokey:", e)
            _redraw_ui(ctx)
        _AKM[it.uid] = (f, snap)


def _ak_tick():
    try:
        ctx = bpy.context
        s = ctx.scene.fskr
        st = _canvas(s)
        rig = s.rig
    except Exception:
        return 0.5
    try:
        _ak_mouth(ctx, s, rig)
    except Exception:
        pass
    if st is None or rig is None or not st.autokey or \
            EY.preset_editing(s) or \
            getattr(s, "ui_mode", 'DRIVER') != 'SPRITE' or \
            not (0 <= st.layer_index < len(st.layers)):
        _AK["key"] = _AK["snap"] = None
        return 0.4
    L = st.layers[st.layer_index]
    try:
        props = EY.layer_key_props(s, st, L)
        snap = {p: float(rig[p]) for p in props}
    except Exception:
        return 0.4
    key = (st.uid, L.lid, ctx.scene.frame_current)
    if _AK["key"] != key or _AK["snap"] is None:
        _AK["key"], _AK["snap"] = key, snap      # 파츠/프레임이 바뀜: 기준만
        return 0.2
    changed = {p for p, v in snap.items()
               if abs(v - _AK["snap"].get(p, v)) > 1e-7}
    if changed:
        try:
            EY.key_layer(s, st, L, only=changed)
        except Exception as e:
            print("FSKR autokey:", e)
        _AK["snap"] = snap
        _redraw_ui(ctx)
    return 0.2


@bpy.app.handlers.persistent
def _ak_reset(*_a):
    _AK["key"] = _AK["snap"] = None
    _AKM.clear()


def face_register():
    from .core import app_handler_add, draw_add
    WM = bpy.types.WindowManager
    WM.fskr_dlg_name = bpy.props.StringProperty(name="이름", default="")
    WM.fskr_dlg_part = bpy.props.StringProperty(name="파츠 이름", default="")
    WM.fskr_dlg_tag = bpy.props.StringProperty(name="새 태그 이름",
                                               default="")
    _MK["h"] = draw_add(bpy.types.SpaceView3D, _draw_markers, (),
                        'WINDOW', 'POST_PIXEL', "face_markers")
    for lst in (bpy.app.handlers.undo_post, bpy.app.handlers.redo_post,
                bpy.app.handlers.load_post):
        app_handler_add(lst, _ak_reset)
    for lst in (bpy.app.handlers.undo_pre, bpy.app.handlers.redo_pre,
                bpy.app.handlers.load_pre):
        app_handler_add(lst, _xf_abort)
    try:
        if not bpy.app.timers.is_registered(_ak_tick):
            bpy.app.timers.register(_ak_tick, first_interval=1.0,
                                    persistent=True)
    except Exception:
        pass


def face_unregister():
    from .core import draw_remove
    for a in ("fskr_dlg_name", "fskr_dlg_part", "fskr_dlg_tag"):
        try:
            delattr(bpy.types.WindowManager, a)
        except Exception:
            pass
    draw_remove("face_markers")
    _MK["h"] = None
    for lst in (bpy.app.handlers.undo_post, bpy.app.handlers.redo_post,
                bpy.app.handlers.load_post):
        if _ak_reset in lst:
            lst.remove(_ak_reset)
    for lst in (bpy.app.handlers.undo_pre, bpy.app.handlers.redo_pre,
                bpy.app.handlers.load_pre):
        try:
            if _xf_abort in lst:
                lst.remove(_xf_abort)
        except Exception:
            pass
    _xf_abort()
    try:
        if bpy.app.timers.is_registered(_ak_tick):
            bpy.app.timers.unregister(_ak_tick)
    except Exception:
        pass


# ------------------------------------------------------------------
# 캔버스 내보내기 / 불러오기 (설정 + 시트 이미지 원본 해상도, 키프레임 제외)
# ------------------------------------------------------------------

PORT_FORMAT = "fskr_canvas"
PORT_VERSION = 1
# 캔버스 메시·상태에 묶인 값 (불러올 때 대상 캔버스 것을 유지)
_PORT_ST_SKIP = {"uid", "target", "uv_map", "uv_proj", "lift", "prev_mats",
                 "built", "vp_layout_sig", "vp_layout_v", "vp_on", "pe_ak",
                 "pe_muted", "preset_edit", "follow", "mirror_all", "pkey",
                 "reselect", "fx"}
_PORT_L_SKIP = {"pkey", "edit_on"}
_PORT_A_SKIP = {"uid", "target", "built", "pkey", "edit_on", "seq_edit"}


def _port_plain(v):
    if hasattr(v, "to_dict"):
        return v.to_dict()
    if hasattr(v, "to_list"):
        return v.to_list()
    if isinstance(v, (list, tuple)):
        return [_port_plain(x) for x in v]
    return v


def _port_dump(pg, skip):
    d = {}
    for k in pg.keys():
        if k in skip:
            continue
        try:
            d[k] = _port_plain(pg[k])
        except Exception:
            pass
    return d


def _port_atlases(s, st):
    """이 캔버스의 입 파츠가 쓰는 입 시트들."""
    out = []
    for L in st.layers:
        it = EY._layer_atlas(s, L)
        if it is not None and it not in out:
            out.append(it)
    return out


def _port_rig_values(s, st, atlases):
    from .preset_vp import prop_name
    rig = s.rig
    out = {"preset": None, "layers": {}, "atlases": {}}
    if rig is None:
        return out
    p = prop_name(st)
    if p in rig.keys():
        out["preset"] = _port_plain(rig[p])
    for L in st.layers:
        d = {}
        cp = EY._prop_cell(st, L)
        if cp in rig.keys():
            d["cell"] = _port_plain(rig[cp])
        an = {}
        for k, pn in zip(EY.ANIM_KEYS, EY._anim_props(st, L)):
            if pn in rig.keys():
                an[k] = _port_plain(rig[pn])
        d["anim"] = an
        out["layers"][L.lid] = d
    for it in atlases:
        d = {}
        for k, fn in (("row", AT._prop_row), ("col", AT._prop_col),
                      ("talk", AT._prop_talk), ("seq", AT._prop_q)):
            pn = fn(it)
            if pn in rig.keys():
                d[k] = _port_plain(rig[pn])
        out["atlases"][it.uid] = d
    return out


def _port_image_bytes(img, tmpdir):
    """원본 그대로의 이미지 파일 바이트와 확장자 (해상도 유지)."""
    import os
    path = ""
    try:
        path = bpy.path.abspath(img.filepath_raw or img.filepath,
                                library=img.library)
    except Exception:
        pass
    ext = os.path.splitext(path)[1].lower() or ".png"
    if not img.is_dirty:
        if img.packed_file is not None:
            return bytes(img.packed_file.data), ext
        if path and os.path.isfile(path):
            with open(path, "rb") as f:
                return f.read(), ext
    # 고친 뒤 저장 안 했거나 원본 파일이 없음 → 지금 픽셀 그대로 PNG로
    tmp = os.path.join(tmpdir, "img.png")
    old_fmt = img.file_format
    try:
        img.file_format = 'PNG'
        img.save(filepath=tmp)
    finally:
        try:
            img.file_format = old_fmt
        except Exception:
            pass
    with open(tmp, "rb") as f:
        return f.read(), ".png"


def canvas_export(s, st, filepath):
    import json, os, tempfile, zipfile
    atlases = _port_atlases(s, st)
    cdata = _port_dump(st, _PORT_ST_SKIP)
    cdata["layers"] = [{k: v for k, v in L.items() if k not in _PORT_L_SKIP}
                       for L in cdata.get("layers", [])]
    adata = []
    for it in atlases:
        d = _port_dump(it, _PORT_A_SKIP)
        d["_uid"] = it.uid
        adata.append(d)
    names = []
    for sh in st.sheets:
        names.append(sh.image)
    for L in st.layers:
        names.append(L.image)
    for it in atlases:
        names.append(it.image)
    names = [n for i, n in enumerate(names) if n and n not in names[:i]]
    man = {"format": PORT_FORMAT, "version": PORT_VERSION,
           "canvas": cdata, "atlases": adata, "images": {},
           "rig": _port_rig_values(s, st, atlases)}
    missing = []
    with tempfile.TemporaryDirectory() as td, \
            zipfile.ZipFile(filepath, "w", zipfile.ZIP_DEFLATED) as z:
        for i, nm in enumerate(names):
            img = bpy.data.images.get(nm)
            if img is None:
                missing.append(nm)
                continue
            try:
                data, ext = _port_image_bytes(img, td)
            except Exception as e:
                print("FSKR export image:", nm, e)
                missing.append(nm)
                continue
            fn = "images/%02d%s" % (i, ext)
            z.writestr(fn, data)
            man["images"][nm] = {
                "file": fn, "size": list(img.size),
                "colorspace": img.colorspace_settings.name,
                "alpha_mode": img.alpha_mode}
        z.writestr("canvas.json", json.dumps(man, ensure_ascii=False,
                                             indent=1))
    return len(man["images"]), missing


def _port_clear_canvas(context, s, st):
    """덮어쓰기 전: 이 캔버스의 컨트롤러·입 시트·파츠 리그 값을 정리."""
    rig = s.rig
    try:
        from . import layer_vp as LV
        LV.remove_all(context, s, st)
    except Exception as e:
        print("FSKR import vp remove:", e)
    others = set()
    for e in s.eyes:
        if e != st:
            for it in _port_atlases(s, e):
                others.add(it.uid)
    for it in _port_atlases(s, st):
        if it.uid in others:
            continue
        try:
            bpy.ops.fskr.atlas_remove('EXEC_DEFAULT', uid=it.uid)
        except Exception as e:
            print("FSKR import atlas remove:", e)
    if rig is not None:
        for L in st.layers:
            cp = EY._prop_cell(st, L)
            for pn in (cp, EY._prop_cell_pv(cp)) + tuple(
                    EY._anim_props(st, L)):
                if pn in rig.keys():
                    del rig[pn]
    for sh in st.sheets:
        try:
            AT._thumbs_free(sh.uid)
        except Exception:
            pass


def canvas_import(context, s, st, filepath):
    import json, os, tempfile, zipfile
    with zipfile.ZipFile(filepath) as z:
        man = json.loads(z.read("canvas.json").decode("utf-8"))
        if man.get("format") != PORT_FORMAT:
            raise ValueError(_tr("Face Rig 캔버스 파일이 아닙니다"))
        # 1) 이미지: 원본 파일 그대로 읽고 블렌드 파일에 포함(pack)
        imap = {}
        with tempfile.TemporaryDirectory() as td:
            for nm, info in man.get("images", {}).items():
                fn = info["file"]
                raw = z.read(fn)
                # 같은 그림이 이미 블렌드에 들어 있으면 그대로 씀 (중복 방지)
                same = None
                for im in bpy.data.images:
                    if (im.name == nm or im.name.startswith(nm + ".")) and \
                            im.packed_file is not None and \
                            im.packed_file.size == len(raw) and \
                            not im.is_dirty:
                        try:
                            if bytes(im.packed_file.data) == raw:
                                same = im
                                break
                        except Exception:
                            pass
                if same is not None:
                    imap[nm] = same.name
                    continue
                dst = os.path.join(td, os.path.basename(fn))
                with open(dst, "wb") as f:
                    f.write(raw)
                img = bpy.data.images.load(dst, check_existing=False)
                img.name = nm
                try:
                    img.colorspace_settings.name = info.get(
                        "colorspace", img.colorspace_settings.name)
                except Exception:
                    pass
                try:
                    img.alpha_mode = info.get("alpha_mode", img.alpha_mode)
                except Exception:
                    pass
                img.pack()
                img.filepath_raw = "//" + nm if os.path.splitext(nm)[1] \
                    else "//" + nm + os.path.splitext(fn)[1]
                imap[nm] = img.name
    _port_clear_canvas(context, s, st)
    # 2) 캔버스 설정 덮어쓰기 (대상 캔버스 메시에 묶인 값은 유지)
    keep = {k: _port_plain(st[k]) for k in list(st.keys())
            if k in _PORT_ST_SKIP}
    for k in list(st.keys()):
        del st[k]
    cdata = man.get("canvas", {})
    for k, v in cdata.items():
        if k in _PORT_ST_SKIP:
            continue
        try:
            st[k] = v
        except Exception as e:
            print("FSKR import canvas key:", k, e)
    for k, v in keep.items():
        if k in ("follow", "mirror_all", "preset_edit", "pkey"):
            continue
        st[k] = v
    nm0 = cdata.get("name", st.name)
    names9 = {e.name for e in s.eyes if e != st}
    nm9, k9 = nm0, 2
    while nm9 in names9:
        nm9 = "%s %d" % (nm0, k9)
        k9 += 1
    st["name"] = nm9
    # 3) 입 시트 (uid가 겹치면 새로)
    used = {a.uid for a in s.atlases}
    amap = {}
    new_atl = []
    for d in man.get("atlases", []):
        old = d.get("_uid", "")
        uid = old
        if not uid or uid in used:
            i = 1
            while "A%d" % i in used:
                i += 1
            uid = "A%d" % i
        used.add(uid)
        amap[old] = uid
        it = s.atlases.add()
        for k, v in d.items():
            if k in _PORT_A_SKIP or k == "_uid":
                continue
            try:
                it[k] = v
            except Exception as e:
                print("FSKR import atlas key:", k, e)
        it["uid"] = uid
        it["target"] = st.target
        if it.get("image"):
            it["image"] = imap.get(it["image"], it["image"])
        new_atl.append(it)
    for it in new_atl:
        rl = it.get("row_link", "")
        if rl:
            it["row_link"] = amap.get(rl, "")
    for L in st.layers:
        if L.get("atlas"):
            L["atlas"] = amap.get(L["atlas"], "")
        if L.get("image"):
            L["image"] = imap.get(L["image"], L["image"])
    for sh in st.sheets:
        if sh.get("image"):
            sh["image"] = imap.get(sh["image"], sh["image"])
    # 4) 재구성
    EY.sync_prop_names(s)
    for it in new_atl:
        try:
            AT._build(s, it)
        except Exception as e:
            print("FSKR import atlas build:", e)
    err = EY.eye_build(s, st)
    # 5) 리그 값
    rig = s.rig
    rv = man.get("rig", {})
    if rig is not None:
        from .preset_vp import prop_name
        if rv.get("preset") is not None:
            rig[prop_name(st)] = rv["preset"]
        for L in st.layers:
            d = rv.get("layers", {}).get(L.lid)
            if not d:
                continue
            if d.get("cell") is not None:
                rig[EY._prop_cell(st, L)] = d["cell"]
            for k, pn in zip(EY.ANIM_KEYS, EY._anim_props(st, L)):
                if k in d.get("anim", {}):
                    rig[pn] = d["anim"][k]
        for old, d in rv.get("atlases", {}).items():
            it = AT._find(s, amap.get(old, ""))
            if it is None:
                continue
            for k, fn in (("row", AT._prop_row), ("col", AT._prop_col),
                          ("talk", AT._prop_talk), ("seq", AT._prop_q)):
                if k in d:
                    rig[fn(it)] = d[k]
        rig.update_tag()
    for it in new_atl:
        try:
            AT._lut_refresh(it)
        except Exception:
            pass
    try:
        EY._pad_build(context, s, st)
    except Exception as e:
        print("FSKR import pad:", e)
    if st.get("fx"):
        try:
            EY.fx_billboard_apply(st, context)
        except Exception:
            pass
    return err, len(imap)


class FSKR_OT_canvas_export(bpy.types.Operator):
    bl_idname = "fskr.canvas_export"
    bl_label = "캔버스 내보내기"
    bl_description = ("지금 고른 캔버스의 파츠·태그·마커·시트·표정 프리셋·입 "
                      "시퀀스·립싱크 설정과 속성값, 시트 이미지(원본 해상도)를 "
                      ".zip 하나로 저장합니다 (키프레임 제외)")
    bl_options = {'REGISTER'}

    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    filter_glob: bpy.props.StringProperty(default="*.zip",
                                          options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        return _canvas(context.scene.fskr) is not None

    def invoke(self, context, event):
        import os
        st = _canvas(context.scene.fskr)
        base = bpy.path.clean_name(st.name) or "canvas"
        d = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else ""
        self.filepath = os.path.join(d, base + ".fskr.zip")
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        s = context.scene.fskr
        st = _canvas(s)
        fp = self.filepath
        if not fp.lower().endswith(".zip"):
            fp += ".zip"
        try:
            n, missing = canvas_export(s, st, fp)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.report({'ERROR'}, _tr("내보내기 실패: ") + str(e))
            return {'CANCELLED'}
        if missing:
            self.report({'WARNING'}, _tr("이미지를 찾지 못해 빠졌습니다: ")
                        + ", ".join(missing))
        else:
            self.report({'INFO'}, _tr("내보냈습니다 (시트 %d장): ") % n + fp)
        return {'FINISHED'}


class FSKR_OT_canvas_import(bpy.types.Operator):
    bl_idname = "fskr.canvas_import"
    bl_label = "캔버스 불러오기 (덮어쓰기)"
    bl_description = ("내보낸 .zip을 지금 고른 캔버스에 덮어씁니다. 이 캔버스의 "
                      "기존 파츠·프리셋·입 시트·컨트롤러는 지워집니다 "
                      "(Ctrl+Z로 되돌릴 수 있음)")
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    filter_glob: bpy.props.StringProperty(default="*.zip",
                                          options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        s = context.scene.fskr
        return s.rig is not None and _canvas(s) is not None

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        s = context.scene.fskr
        st = _canvas(s)
        if context.mode != 'OBJECT':
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except Exception:
                pass
        try:
            err, n = canvas_import(context, s, st, self.filepath)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.report({'ERROR'}, _tr("불러오기 실패: ") + str(e))
            return {'CANCELLED'}
        if err:
            self.report({'WARNING'}, err)
        else:
            self.report({'INFO'}, _tr("불러왔습니다 (시트 %d장). 뷰포트 "
                                      "컨트롤러는 컨트롤러 탭에서 다시 "
                                      "만드세요") % n)
        _redraw_ui(context)
        return {'FINISHED'}


face_classes = face_classes + (FSKR_OT_canvas_export, FSKR_OT_canvas_import)


# ------------------------------------------------------------------
# 뷰포트 자유 변형 (포토샵 Ctrl+T): 이동 · 크기 · 회전
# ------------------------------------------------------------------

_XF = {"h": None, "op": None, "abort": False}


class _UVMap:
    """캔버스 UV → 월드 좌표 (평가된 메시 삼각형에서 찾기)."""

    def __init__(self, context, ob, uv_name):
        from mathutils.kdtree import KDTree
        dg = context.evaluated_depsgraph_get()
        oe = ob.evaluated_get(dg)
        me = oe.to_mesh()
        try:
            me.calc_loop_triangles()
        except Exception:
            pass
        uvl = me.uv_layers.get(uv_name) if uv_name else None
        uvl = uvl or me.uv_layers.active
        mw = oe.matrix_world
        self.tris = []
        if uvl is not None:
            for t in me.loop_triangles:
                uv = [Vector(uvl.data[li].uv) for li in t.loops]
                co = [mw @ me.vertices[vi].co for vi in t.vertices]
                self.tris.append((uv, co))
        oe.to_mesh_clear()
        self.kd = KDTree(max(1, len(self.tris)))
        for i, (uv, _co) in enumerate(self.tris):
            c = (uv[0] + uv[1] + uv[2]) / 3.0
            self.kd.insert((c.x, c.y, 0.0), i)
        self.kd.balance()

    def world(self, u, v):
        if not self.tris:
            return None
        best = None
        for _co, i, _d in self.kd.find_n((u, v, 0.0), 12):
            (a, b, c), co = self.tris[i]
            d = (b.x - a.x) * (c.y - a.y) - (c.x - a.x) * (b.y - a.y)
            if abs(d) < 1e-12:
                continue
            w1 = ((u - a.x) * (c.y - a.y) - (c.x - a.x) * (v - a.y)) / d
            w2 = ((b.x - a.x) * (v - a.y) - (u - a.x) * (b.y - a.y)) / d
            w0 = 1.0 - w1 - w2
            out = min(w0, w1, w2)
            if best is None or out > best[0]:
                best = (out, w0, w1, w2, co)
            if out >= -1e-6:
                break
        if best is None:
            return None
        _o, w0, w1, w2, co = best
        return co[0] * w0 + co[1] * w1 + co[2] * w2


def _xf_region(context):
    area = context.area
    if area is None or area.type != 'VIEW_3D':
        return None, None
    reg = next((r for r in area.regions if r.type == 'WINDOW'), None)
    return area, reg


def _xf_draw():
    op = _XF.get("op")
    if op is None:
        return
    try:
        op.draw_px(bpy.context)
    except Exception as e:
        print("FSKR transform draw:", e)


def m_deg(r):
    import math as _m
    return _m.degrees(r)


class _PartTransformBase:
    """자유 변형 공통 동작 (버튼용·Ctrl+T용 오퍼레이터가 같이 씀)."""

    def _s(self):
        return bpy.context.scene.fskr

    def _st(self):
        return EY._find(self._s(), self.uid)

    def _L(self):
        st = self._st()
        return EY._layer(st, self.lid) if st is not None else None

    # ----- 값 읽기/쓰기 -----
    def _ctx(self, context):
        s = context.scene.fskr
        if not self.uid:
            st = _canvas(s)
            L = st.layers[st.layer_index] if st is not None and \
                0 <= st.layer_index < len(st.layers) else None
            return s, st, L
        st = EY._find(s, self.uid)
        L = EY._layer(st, self.lid) if st else None
        return s, st, L

    def _get(self):
        s, st, L, rig = self._s(), self._st(), self._L(), self._s().rig
        P = self.P
        if self.cell:
            return [L.cell_px, L.cell_py, L.cell_sx, L.cell_sy, L.cell_rot]
        sx = float(rig.get(P[3], 1.0))
        sy = float(L.size_y_lk) if L.scale_lock else float(rig.get(P[4], 1.0))
        return [float(rig.get(P[1], 0.0)), float(rig.get(P[2], 0.0)), sx, sy,
                float(rig.get(P[5], 0.0))]

    def _locked(self):
        L = self._L()
        if self.cell:
            return bool(L.cell_lock)
        return bool(L.scale_lock)

    def _set(self, v):
        L, rig, P = self._L(), self._s().rig, self.P
        px, py, sx, sy, rot = v
        sx = max(1e-4, sx)
        sy = max(1e-4, sy)
        x = EY.cell_table(self._s(), self._st(), L) if self.cell else None
        if x is not None and not x.others() and \
                not EY.preset_editing(self._s()):
            # 빠른 길: 지금 칸 값만 직접 쓰고 조회표는 한 번만 갱신
            P9 = x.P
            bx = EY._cx_base(rig, P9, "px", 0.0)
            by = EY._cx_base(rig, P9, "py", 0.0)
            br = EY._cx_base(rig, P9, "rot", 0.0)
            bsx = max(EY._cx_base(rig, P9, "sx", 1.0), 1e-6)
            bsy = max(EY._cx_syb(rig, L, P9), 1e-6)
            e = x.ensure(*x.cur)
            e.lpx, e.lpy, e.lrot = px - bx, py - by, rot - br
            e.lkx, e.lky = sx / bsx, sy / bsy
            x.refresh()
        elif self.cell:
            cur = self._get()
            if abs(cur[0] - px) > 1e-9:
                L.cell_px = px
            if abs(cur[1] - py) > 1e-9:
                L.cell_py = py
            if abs(cur[4] - rot) > 1e-9:
                L.cell_rot = rot
            if self._locked():
                if abs(cur[2] - sx) > 1e-9:
                    L.cell_sx = sx
            else:
                if abs(cur[2] - sx) > 1e-9:
                    L.cell_sx = sx
                if abs(cur[3] - sy) > 1e-9:
                    L.cell_sy = sy
        else:
            rig[P[1]], rig[P[2]], rig[P[5]] = px, py, rot
            rig[P[3]] = sx
            if not L.scale_lock:
                rig[P[4]] = sy
            rig.update_tag()
        self.cur = list(v)

    # ----- 기하 -----
    def _box_q(self):
        bb = None
        try:
            bb = EY.cell_bbox(self._s(), self._st(), self._L())
        except Exception:
            bb = None
        u0, u1, v0, v1 = bb if bb else (0.0, 1.0, 0.0, 1.0)
        if self._L().flip_x:
            u0, u1 = 1.0 - u1, 1.0 - u0
        return u0, u1, v0, v1

    def _q2uv(self, q, v=None):
        """파츠 공간 q → 캔버스 UV (부모에게서 물려받는 배치 포함)."""
        lo = self._q2l(q, v)
        x, y = EY.aff_apply(getattr(self, "inh", EY._AFF_I), lo.x, lo.y)
        return Vector((x, y))

    def _w2l(self, uv):
        """캔버스 UV → 부모 상속을 뺀 이 파츠 자체 공간의 UV."""
        x, y = EY.aff_apply(getattr(self, "inh_inv", EY._AFF_I), uv.x, uv.y)
        return Vector((x, y))

    def _q2l(self, q, v=None):
        import math as m
        v = v or self.cur
        px, py, sx, sy, rot = v
        c = self.c
        d = ((q[0] - c[0]) * sx, (q[1] - c[1]) * sy)
        a = m.radians(rot)
        ca, sa = m.cos(a), m.sin(a)
        return Vector((self.rest[0] + px + ca * d[0] - sa * d[1],
                       self.rest[1] + py + sa * d[0] + ca * d[1]))

    def _jac(self, context):
        """피벗 근처 UV → 화면 (아핀 근사): (원점, du 열, dv 열)."""
        from bpy_extras import view3d_utils as V
        area, reg = _xf_region(context)
        rv3d = area.spaces.active.region_3d
        t = self._q2uv(self.c)
        h = 0.01
        pts = []
        for du, dv in ((0, 0), (h, 0), (0, h)):
            w = self.uvmap.world(t.x + du, t.y + dv)
            if w is None:
                return None
            p = V.location_3d_to_region_2d(reg, rv3d, w)
            if p is None:
                return None
            pts.append(p)
        ju = (pts[1] - pts[0]) / h
        jv = (pts[2] - pts[0]) / h
        # 기울지 않게: 가로 = 화면 가로, 세로 = 화면 세로로 맞춤
        ju = Vector((ju.length if ju.x >= 0 else -ju.length, 0.0))
        jv = Vector((0.0, jv.length if jv.y >= 0 else -jv.length))
        return t, pts[0], ju, jv

    def _scr(self, uv, J):
        t, o, ju, jv = J
        d = uv - t
        return o + ju * d.x + jv * d.y

    def _uv(self, sp, J):
        t, o, ju, jv = J
        det = ju.x * jv.y - jv.x * ju.y
        if abs(det) < 1e-9:
            return t.copy()
        d = sp - o
        a = (d.x * jv.y - jv.x * d.y) / det
        b = (ju.x * d.y - d.x * ju.y) / det
        return Vector((t.x + a, t.y + b))

    def _handles(self, J):
        u0, u1, v0, v1 = self._box_q()
        um, vm = (u0 + u1) / 2.0, (v0 + v1) / 2.0
        q = {"c00": (u0, v0), "c10": (u1, v0), "c11": (u1, v1),
             "c01": (u0, v1), "e0m": (u0, vm), "e1m": (u1, vm),
             "em0": (um, v0), "em1": (um, v1)}
        sc = {k: self._scr(self._q2uv(v), J) for k, v in q.items()}
        top = sc["em1"]
        cen = self._scr(self._q2uv((um, vm)), J)
        dirv = top - cen
        if dirv.length < 1e-6:
            dirv = Vector((0.0, 1.0))
        sc["rot"] = top + dirv.normalized() * 28.0
        return q, sc

    # ----- 그리기 -----
    def draw_px(self, context):
        import gpu
        import blf
        from gpu_extras.batch import batch_for_shader
        if context.area is None or context.area != self.area:
            return
        if self._L() is None:
            return
        J = self._jac(context)
        if J is None:
            return
        self.J = J
        q, sc = self._handles(J)
        sh = gpu.shader.from_builtin('UNIFORM_COLOR')
        gpu.state.blend_set('ALPHA')
        box = [sc["c00"], sc["c10"], sc["c11"], sc["c01"]]
        lines = []
        for i in range(4):
            lines += [box[i], box[(i + 1) % 4]]
        lines += [sc["em1"], sc["rot"]]
        gpu.state.line_width_set(1.5)
        b = batch_for_shader(sh, 'LINES', {"pos": [tuple(p) for p in lines]})
        sh.bind()
        sh.uniform_float("color", (0.3, 0.65, 1.0, 1.0))
        b.draw(sh)
        # 손잡이
        tris = []
        for k in ("c00", "c10", "c11", "c01", "e0m", "e1m", "em0", "em1"):
            p, r = sc[k], 5.0
            a, b2, c2, d2 = ((p.x - r, p.y - r), (p.x + r, p.y - r),
                             (p.x + r, p.y + r), (p.x - r, p.y + r))
            tris += [a, b2, c2, a, c2, d2]
        bt = batch_for_shader(sh, 'TRIS', {"pos": tris})
        sh.uniform_float("color", (0.3, 0.65, 1.0, 1.0))
        bt.draw(sh)
        import math as m
        circ = []
        p = sc["rot"]
        for i in range(16):
            a1, a2 = i / 16 * 2 * m.pi, (i + 1) / 16 * 2 * m.pi
            circ += [(p.x + 6 * m.cos(a1), p.y + 6 * m.sin(a1)),
                     (p.x + 6 * m.cos(a2), p.y + 6 * m.sin(a2))]
        bc = batch_for_shader(sh, 'LINES', {"pos": circ})
        sh.uniform_float("color", (1.0, 0.6, 0.2, 1.0))
        bc.draw(sh)
        # 기준점 +
        pv = self._scr(self._q2uv(self.c), J) if self.mode != "pivot" \
            else self.pv_drag
        bp = batch_for_shader(sh, 'LINES', {"pos": [
            (pv.x - 7, pv.y), (pv.x + 7, pv.y), (pv.x, pv.y - 7),
            (pv.x, pv.y + 7)]})
        sh.uniform_float("color", (1.0, 0.85, 0.2, 1.0)
                         if self.mode == "pivot" else (1.0, 1.0, 1.0, 0.9))
        bp.draw(sh)
        cp = []
        for i in range(16):
            a1, a2 = i / 16 * 2 * m.pi, (i + 1) / 16 * 2 * m.pi
            cp += [(pv.x + 5 * m.cos(a1), pv.y + 5 * m.sin(a1)),
                   (pv.x + 5 * m.cos(a2), pv.y + 5 * m.sin(a2))]
        bcp = batch_for_shader(sh, 'LINES', {"pos": cp})
        bcp.draw(sh)
        # 확정 / 취소 버튼 (상자 아래)
        # 확정/취소: 상자 바로 아래 (화면 밖으로 나가지 않게)
        lo = min(box, key=lambda v: v.y)
        cx = sum(v.x for v in box) / 4.0
        bot = self._bottom_inset()
        try:
            ui9 = float(context.preferences.system.ui_scale)
        except Exception:
            ui9 = 1.0
        by = max(bot + 112 * ui9, lo.y - 26)   # 아래 도움말과 겹치지 않게
        cx = min(max(cx, 120), self.reg.width - 120)
        self.btns = {"ok": (cx - 110, by - 32, cx - 4, by),
                     "no": (cx + 4, by - 32, cx + 110, by)}
        for k, (x0, y0, x1, y1) in self.btns.items():
            hot = self.hover == k
            bb = batch_for_shader(sh, 'TRIS', {"pos": [
                (x0, y0), (x1, y0), (x1, y1), (x0, y0), (x1, y1), (x0, y1)]})
            sh.uniform_float("color", (0.35, 0.35, 0.38, 0.95) if hot
                             else (0.2, 0.2, 0.22, 0.9))
            bb.draw(sh)
        gpu.state.line_width_set(1.0)
        gpu.state.blend_set('NONE')
        fid = 0
        blf.size(fid, 13)
        blf.color(fid, 1, 1, 1, 1)
        for k, lab in (("ok", _tr("✓ 확정")), ("no", _tr("✕ 취소"))):
            x0, y0, x1, y1 = self.btns[k]
            w, h = blf.dimensions(fid, lab)
            blf.position(fid, (x0 + x1 - w) / 2, (y0 + y1 - h) / 2 + 2, 0)
            blf.draw(fid, lab)
        # 도움말: 뷰포트 아래 가운데 (아래쪽 헤더에 가리지 않게)
        tips = (_tr("안쪽 드래그 = 이동 (Shift 45°)   ·   방향키 (Shift ×10)   ·   모서리/변 = 크기 "
                    "(Shift 비율, Alt 기준점)   ·   바깥/○ = 회전 (Shift 15°)"),
                _tr("기준점 ⊕ 드래그 = 기준점 옮기기   ·   Ctrl+Z 한 단계 되돌리기"
                    "   ·   Enter 확정   ·   Esc 취소   ·   원근 뷰가 되면 확정"))
        try:
            ui = float(context.preferences.system.ui_scale)
        except Exception:
            ui = 1.0
        fs = 15 * ui
        blf.size(fid, fs)
        lh = fs * 1.55
        pad = 10 * ui
        ws = [blf.dimensions(fid, t9)[0] for t9 in tips]
        bw = max(ws) + pad * 2
        bh = lh * len(tips) + pad * 1.2
        bx0 = (self.reg.width - bw) / 2
        by0 = self._bottom_inset() + 8 * ui
        gpu.state.blend_set('ALPHA')
        bg = batch_for_shader(sh, 'TRIS', {"pos": [
            (bx0, by0), (bx0 + bw, by0), (bx0 + bw, by0 + bh),
            (bx0, by0), (bx0 + bw, by0 + bh), (bx0, by0 + bh)]})
        sh.bind()
        sh.uniform_float("color", (0.06, 0.06, 0.08, 0.72))
        bg.draw(sh)
        gpu.state.blend_set('NONE')
        for i, t9 in enumerate(reversed(tips)):
            w = ws[len(tips) - 1 - i]
            x9 = (self.reg.width - w) / 2
            y9 = by0 + pad * 0.8 + i * lh
            blf.color(fid, 1, 1, 1, 1)
            blf.position(fid, x9, y9, 0)
            blf.draw(fid, t9)

    def _bottom_inset(self):
        """뷰포트 아래쪽에 겹쳐 있는 헤더·툴 헤더 높이 (그 위에 그림)."""
        off = 0
        try:
            for r in self.area.regions:
                if r.type in ('HEADER', 'TOOL_HEADER', 'ASSET_SHELF',
                              'ASSET_SHELF_HEADER') and \
                        r.alignment == 'BOTTOM' and r.height > 1:
                    off = max(off, (r.y + r.height) - self.reg.y)
        except Exception:
            pass
        return max(0, off)

    # ----- 맞추기 -----
    def _pick(self, mp):
        if self.J is None:
            return None
        for k, (x0, y0, x1, y1) in (self.btns or {}).items():
            if x0 <= mp.x <= x1 and y0 <= mp.y <= y1:
                return "btn_" + k
        q, sc = self._handles(self.J)
        pv = self._scr(self._q2uv(self.c), self.J)
        if (pv - mp).length < 10:
            return "pivot"
        if (sc["rot"] - mp).length < 12:
            return "rot"
        best, bd = None, 11.0
        for k in ("c00", "c10", "c11", "c01", "e0m", "e1m", "em0", "em1"):
            d = (sc[k] - mp).length
            if d < bd:
                best, bd = k, d
        if best:
            return best
        box = [sc["c00"], sc["c10"], sc["c11"], sc["c01"]]
        inside = True
        sgn = None
        for i in range(4):
            a, b = box[i], box[(i + 1) % 4]
            cr = (b.x - a.x) * (mp.y - a.y) - (b.y - a.y) * (mp.x - a.x)
            if sgn is None:
                sgn = cr >= 0
            elif (cr >= 0) != sgn:
                inside = False
                break
        return "move" if inside else "rot"

    def _snap_pivot(self, mp):
        """기준점 드래그: 상자 9점(모서리·변 가운데·가운데) 근처면 붙임."""
        J = self.J0
        u0, u1, v0, v1 = self._box_q()
        best, bd = None, 10.0
        for qu in (u0, (u0 + u1) / 2, u1):
            for qv in (v0, (v0 + v1) / 2, v1):
                sp = self._scr(self._q2uv((qu, qv)), J)
                d = (sp - mp).length
                if d < bd:
                    best, bd = sp, d
        return best if best is not None else mp

    def _uv2q(self, uv, v=None):
        """캔버스 UV → 파츠 공간 q (지금 값 기준)."""
        import math as m
        v = v or self.cur
        uv = self._w2l(uv)
        px, py, sx, sy, rot = v
        d = (uv.x - self.rest[0] - px, uv.y - self.rest[1] - py)
        a = -m.radians(rot)
        ca, sa = m.cos(a), m.sin(a)
        lx, ly = ca * d[0] - sa * d[1], sa * d[0] + ca * d[1]
        return Vector((self.c.x + lx / max(sx, 1e-6),
                       self.c.y + ly / max(sy, 1e-6)))

    def _move_pivot(self, context, new_c):
        """기준점을 new_c(파츠 공간, 반전 전)로. 그림은 제자리에 있게 보정."""
        import math as m
        s, st, L = self._s(), self._st(), self._L()
        old_c = Vector(EY._pivot_eff(L))
        new_c = Vector(new_c)
        if (new_c - old_c).length < 1e-6:
            return
        # 기본(모든 칸 공통) 값 보정: 리그 위치 (+ 키프레임)
        EY._pivot_shift(s, st, L, tuple(old_c), tuple(new_c))
        # 칸별 크기·회전이 다른 칸은 그 차이만큼 칸 위치를 더 보정
        x = EY.cell_table(s, st, L)
        if x is not None:
            rig = s.rig
            P9 = x.P
            sx = EY._cx_base(rig, P9, "sx", 1.0)
            sy = EY._cx_syb(rig, L, P9)
            th = m.radians(EY._cx_base(rig, P9, "rot", 0.0))
            dx, dy = old_c.x - new_c.x, old_c.y - new_c.y

            def corr(kx, ky, dr):
                t = th + m.radians(dr)
                ax, ay = sx * kx * dx, sy * ky * dy
                return (dx - (m.cos(t) * ax - m.sin(t) * ay),
                        dy - (m.sin(t) * ax + m.cos(t) * ay))
            b0 = corr(1.0, 1.0, 0.0)
            for e in x.tab.cells:
                ce = corr(float(e.lkx), float(e.lky), float(e.lrot))
                e.lpx = float(e.lpx) + ce[0] - b0[0]
                e.lpy = float(e.lpy) + ce[1] - b0[1]
        u = 1.0 - new_c.x if L.flip_x else new_c.x
        L["pivot_uv"] = (u, new_c.y)
        L["pivot"] = 1
        L["pivot_cur"] = "PART"
        EY.eye_build(s, st)
        if x is not None:
            x.refresh()
        # 고정 이동분(마커 + 기준점)과 지금 값 다시 읽기
        self.rest = (self.rest[0] + new_c.x - old_c.x,
                     self.rest[1] + new_c.y - old_c.y)
        self.c = new_c
        self.cur = self._get()
        self.hist, self.redo = [], []
        self.pivot_moved = True

    def _drag(self, mp, ev):
        import math as m
        J = self.J0
        if self.mode == "pivot":
            self.pv_drag = self._snap_pivot(mp)
            return
        uv = self._w2l(self._uv(mp, J))
        uv0 = self._w2l(self.uv_start)
        v = list(self.v_start)
        k = self.mode
        if k == "move":
            if ev.shift and self.mp_start is not None:
                # Shift = 가로·세로·45° 방향으로만 (포토샵처럼)
                dm = mp - self.mp_start
                if dm.length > 1e-6:
                    ang = m.atan2(dm.y, dm.x)
                    sa = round(ang / (m.pi / 4)) * (m.pi / 4)
                    dirv = Vector((m.cos(sa), m.sin(sa)))
                    uv = self._w2l(self._uv(
                        self.mp_start + dirv * dm.dot(dirv), J))
            d = uv - uv0
            v[0] += d.x
            v[1] += d.y
        elif k == "rot":
            t = self._q2l(self.c, self.v_start)
            a0 = m.atan2(uv0.y - t.y, uv0.x - t.x)
            a1 = m.atan2(uv.y - t.y, uv.x - t.x)
            ang = m.degrees(a1 - a0)
            nr = self.v_start[4] + ang
            if ev.shift:
                nr = round(nr / 15.0) * 15.0
            v[4] = nr
        else:
            # 크기: 반대쪽 모서리(Alt면 기준점)를 고정
            u0, u1, v0, v1 = self._box_q()
            qk = {"c00": (u0, v0), "c10": (u1, v0), "c11": (u1, v1),
                  "c01": (u0, v1), "e0m": (u0, None), "e1m": (u1, None),
                  "em0": (None, v0), "em1": (None, v1)}[k]
            opp = {u0: u1, u1: u0}
            oppv = {v0: v1, v1: v0}
            if ev.alt:
                anc = tuple(self.c)
            else:
                anc = (opp.get(qk[0], (u0 + u1) / 2) if qk[0] is not None
                       else (u0 + u1) / 2,
                       oppv.get(qk[1], (v0 + v1) / 2) if qk[1] is not None
                       else (v0 + v1) / 2)
            a = m.radians(self.v_start[4])
            ca, sa = m.cos(a), m.sin(a)
            pa = self._q2l(anc, self.v_start)
            d = uv - pa
            lx = ca * d.x + sa * d.y      # 파츠 축으로 되돌림
            ly = -sa * d.x + ca * d.y
            hq = ((qk[0] - anc[0]) if qk[0] is not None else None,
                  (qk[1] - anc[1]) if qk[1] is not None else None)
            sx0, sy0 = self.v_start[2], self.v_start[3]
            nsx, nsy = sx0, sy0
            if hq[0] is not None and abs(hq[0]) > 1e-6:
                nsx = lx / hq[0]
            if hq[1] is not None and abs(hq[1]) > 1e-6:
                nsy = ly / hq[1]
            corner = k.startswith("c")
            keep = self._locked() != bool(ev.shift) if corner else \
                self._locked()
            if keep:
                if corner:
                    kx, ky = nsx / sx0, nsy / sy0
                    kk = kx if abs(kx - 1) > abs(ky - 1) else ky
                else:
                    kk = (nsx / sx0) if hq[0] is not None else (nsy / sy0)
                nsx, nsy = sx0 * kk, sy0 * kk
            nsx = max(1e-3, nsx)
            nsy = max(1e-3, nsy)
            v[2], v[3] = nsx, nsy
            # 고정점이 제자리에 있도록 위치 보정
            pa2 = self._q2l(anc, v)
            v[0] += pa.x - pa2.x
            v[1] += pa.y - pa2.y
        self._set(v)

    # ----- 실행 -----
    def invoke(self, context, event):
        try:
            return self._invoke(context, event)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._cleanup()
            self.report({'ERROR'}, _tr("자유 변형 시작 실패: ") + repr(e))
            return {'CANCELLED'}

    def _invoke(self, context, event):
        s, st, L = self._ctx(context)
        if L is None or s.rig is None:
            return {'CANCELLED'}
        area, reg = _xf_region(context)
        if reg is None:
            self.report({'WARNING'}, _tr("3D 뷰포트에서 실행하세요"))
            return {'CANCELLED'}
        if EY._mirror_all(s, st):
            self.report({'WARNING'}, _tr("다른 캔버스를 따라가는 캔버스는 "
                                         "지원하지 않습니다"))
            return {'CANCELLED'}
        ob = bpy.data.objects.get(st.target)
        if ob is None:
            return {'CANCELLED'}
        self.uid, self.lid = st.uid, L.lid
        self.area, self.reg = area, reg
        ast, aL = EY._anim_source(s, st, L)
        self.P = EY._anim_props(ast, aL)
        self.cell = EY.cell_table(s, st, L) is not None
        self.c = Vector(EY._pivot_eff(L))
        # 고정 이동분 (마커·부모·시선): -(move 노드 위치) - 리그 위치
        mat = ob.active_material
        nt = mat.node_tree if mat is not None else None
        mv = None
        if nt is not None:
            mv = nt.nodes.get("EYMV_%s_%s_0" % (st.uid, L.lid)) or next(
                (n for n in nt.nodes if n.label == "%s: move" % L.name),
                None)
        rig = s.rig
        context.view_layer.update()
        pxr = float(rig.get(self.P[1], 0.0))
        pyr = float(rig.get(self.P[2], 0.0))
        cur = self._get()
        if mv is not None:
            loc = mv.inputs["Location"].default_value
            lpx, lpy = (cur[0] - pxr, cur[1] - pyr) if self.cell else (0, 0)
            # 화면 위치 = -loc + 칸 보정 = rest + (pxr + lpx)
            rx, ry = -loc[0] - pxr, -loc[1] - pyr
            self.rest = (rx, ry)
            # 부모(조상)에게서 물려받는 배치: move 노드 앞의 Mapping 체인
            #   (데칼 UV → 이 파츠 자체 공간)의 역
            F = EY._AFF_I
            n9 = mv
            for _i in range(512):
                lk = n9.inputs["Vector"].links if "Vector" in n9.inputs \
                    else ()
                if not lk:
                    break
                n9 = lk[0].from_node
                if n9.type != 'MAPPING' or n9.vector_type != 'POINT':
                    break
                l9 = n9.inputs["Location"].default_value
                r9 = n9.inputs["Rotation"].default_value
                k9 = n9.inputs["Scale"].default_value
                F = EY.aff_mul(F, EY.aff_rs(m_deg(r9[2]), k9[0], k9[1],
                                            l9[0], l9[1]))
            self.inh_inv = F
            self.inh = EY.aff_inv(F)
        else:
            mu, mv9 = EY.marker_uv(st, L.tag)
            self.rest = (mu + self.c.x - 0.5, mv9 + self.c.y - 0.5)
            self.inh = EY.layer_inh_aff(s, st, L)
            self.inh_inv = EY.aff_inv(self.inh)
        self.cur = cur
        self.orig = list(cur)
        self.hist = []
        self.redo = []
        self.orig_c = Vector(self.c)
        self.orig_pv = (L.get("pivot", 0), tuple(L.pivot_uv),
                        L.get("pivot_cur", ""))
        self.pivot_moved = False
        self.pv_drag = None
        self.mp_start = None
        self.uvmap = _UVMap(context, ob, st.uv_map)
        # 얼굴 정면 · 직교(Ortho) 뷰로: 원근 때문에 기울어 보이지 않게
        # (view_axis 연산자는 부드러운 전환 애니메이션이 끝날 때 원근으로
        #  되돌릴 수 있어서, 회전값을 직접 넣어 즉시 바꿈)
        try:
            import math as m
            from mathutils import Euler
            zr = {'-Y': 0.0, 'Y': m.pi, 'X': m.pi / 2,
                  '-X': -m.pi / 2}.get(getattr(s, "face_axis", '-Y'), 0.0)
            rv3d = area.spaces.active.region_3d
            rv3d.view_rotation = Euler((m.pi / 2, 0.0, zr)).to_quaternion()
            rv3d.view_perspective = 'ORTHO'
        except Exception as e:
            print("FSKR transform view:", e)
        self.J = self.J0 = None
        self.btns = None
        self.hover = None
        self.mode = None
        _XF["op"] = self
        _XF["abort"] = False
        if _XF["h"] is None:
            _XF["h"] = bpy.types.SpaceView3D.draw_handler_add(
                _xf_draw, (), 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self)
        area.tag_redraw()
        return {'RUNNING_MODAL'}

    def _push(self):
        """변형 안 되돌리기 기록 (드래그·방향키 시작 때)."""
        self.hist.append(list(self.cur))
        if len(self.hist) > 200:
            del self.hist[0]
        self.redo = []

    def _mp(self, ev):
        return Vector((ev.mouse_x - self.reg.x, ev.mouse_y - self.reg.y))

    def _end(self, context, ok):
        if not ok and self._L() is not None:
            if self.pivot_moved:
                try:
                    self._move_pivot(context, self.orig_c)
                    L9 = self._L()
                    L9["pivot"], L9["pivot_uv"] = self.orig_pv[0], \
                        self.orig_pv[1]
                    if self.orig_pv[2]:
                        L9["pivot_cur"] = self.orig_pv[2]
                except Exception as e:
                    print("FSKR pivot restore:", e)
            self._set(self.orig)
        self._cleanup()
        _redraw_ui(context)
        return {'FINISHED'} if ok else {'CANCELLED'}

    def modal(self, context, ev):
        if _XF.get("abort") or self._L() is None:
            # Undo·파일 열기 등으로 중단됨: 데이터는 건드리지 않고 끝냄
            self._cleanup()
            self.report({'INFO'}, _tr("자유 변형이 중단되었습니다 (Undo·파일 "
                                      "열기·파츠 삭제)"))
            return {'CANCELLED'}
        try:
            self.area.tag_redraw()
            persp = self.area.spaces.active.region_3d.view_perspective
        except Exception:
            return self._end(context, True)
        if persp != 'ORTHO' and not self.mode:
            # 뷰를 돌려 원근(Pers)이 되면 자유 변형 끝 (바꾼 값은 적용)
            self.report({'INFO'}, _tr("원근 뷰가 되어 자유 변형을 확정하고 "
                                      "끝냈습니다"))
            return self._end(context, True)
        if ev.type == 'Z' and (ev.ctrl or ev.oskey) and ev.value == 'PRESS':
            # 변형 중 Ctrl+Z = 변형 안에서 한 단계 되돌리기 (Shift = 다시)
            # 실제 Blender Undo로는 넘기지 않음
            if not self.mode:
                if ev.shift:
                    if self.redo:
                        self.hist.append(list(self.cur))
                        self._set(self.redo.pop())
                elif self.hist:
                    self.redo.append(list(self.cur))
                    self._set(self.hist.pop())
            return {'RUNNING_MODAL'}
        if ev.type in ('LEFT_ARROW', 'RIGHT_ARROW', 'UP_ARROW', 'DOWN_ARROW') \
                and ev.value in ('PRESS', 'REPEAT') and not self.mode:
            # 방향키 = 화면 1픽셀 이동 (Shift = 10픽셀)
            if self.J is not None:
                step = 10.0 if ev.shift else 1.0
                dx, dy = {'LEFT_ARROW': (-step, 0), 'RIGHT_ARROW': (step, 0),
                          'UP_ARROW': (0, step),
                          'DOWN_ARROW': (0, -step)}[ev.type]
                if ev.value == 'PRESS':   # 꾹 누르는 동안은 한 단계로
                    self._push()
                J = self.J
                o = J[1]
                d = self._w2l(self._uv(o + Vector((dx, dy)), J)) - \
                    self._w2l(self._uv(o, J))
                v = list(self.cur)
                v[0] += d.x
                v[1] += d.y
                self._set(v)
            return {'RUNNING_MODAL'}
        mp = self._mp(ev)
        inside = 0 <= mp.x <= self.reg.width and 0 <= mp.y <= self.reg.height
        if ev.type in ('ESC', 'RIGHTMOUSE') and ev.value == 'PRESS':
            return self._end(context, False)
        if ev.type in ('RET', 'NUMPAD_ENTER') and ev.value == 'PRESS':
            return self._end(context, True)
        if ev.type == 'MOUSEMOVE':
            if self.mode:
                self._drag(mp, ev)
                return {'RUNNING_MODAL'}
            k = self._pick(mp) if inside else None
            self.hover = k[4:] if k and k.startswith("btn_") else None
            return {'PASS_THROUGH'}
        if ev.type == 'LEFTMOUSE':
            if ev.value == 'PRESS' and inside:
                k = self._pick(mp)
                if k == "btn_ok":
                    return self._end(context, True)
                if k == "btn_no":
                    return self._end(context, False)
                if k is None:
                    return {'PASS_THROUGH'}
                self.mode = k
                if k != "pivot":
                    self._push()
                self.J0 = self.J
                self.pv_drag = mp
                self.mp_start = mp.copy()
                self.uv_start = self._uv(mp, self.J0)
                self.v_start = list(self.cur)
                return {'RUNNING_MODAL'}
            if ev.value == 'RELEASE' and self.mode:
                if self.mode == "pivot":
                    nq = self._uv2q(self._uv(self.pv_drag, self.J0))
                    self.mode = None
                    try:
                        self._move_pivot(context, nq)
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        self.report({'WARNING'}, repr(e))
                self.mode = None
                return {'RUNNING_MODAL'}
            if not inside:
                return {'PASS_THROUGH'}
            return {'RUNNING_MODAL'}
        if ev.type in _XF_NAV or ev.type.startswith(("NDOF", "TRACKPAD",
                                                      "TIMER")):
            return {'PASS_THROUGH'}   # 뷰 돌리기·확대만 통과
        return {'RUNNING_MODAL'}      # 나머지 단축키는 변형 중 막음

    def _cleanup(self):
        _XF["op"] = None
        if _XF["h"] is not None:
            try:
                bpy.types.SpaceView3D.draw_handler_remove(_XF["h"], 'WINDOW')
            except Exception:
                pass
            _XF["h"] = None
        try:
            self.area.header_text_set(None)
            self.area.tag_redraw()
        except Exception:
            pass


_XF_NAV = {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'WHEELINMOUSE',
           'WHEELOUTMOUSE', 'INBETWEEN_MOUSEMOVE', 'WINDOW_DEACTIVATE',
           'NUMPAD_0', 'NUMPAD_1', 'NUMPAD_2', 'NUMPAD_3', 'NUMPAD_4',
           'NUMPAD_5', 'NUMPAD_6', 'NUMPAD_7', 'NUMPAD_8', 'NUMPAD_9',
           'NUMPAD_PERIOD', 'NUMPAD_PLUS', 'NUMPAD_MINUS', 'LEFT_SHIFT',
           'RIGHT_SHIFT', 'LEFT_ALT', 'RIGHT_ALT', 'LEFT_CTRL', 'RIGHT_CTRL'}


@bpy.app.handlers.persistent
def _xf_abort(*_a):
    """Undo·Redo·파일 열기 전: 진행 중인 자유 변형을 안전하게 끊음."""
    if _XF.get("op") is not None:
        _XF["abort"] = True
    _XF["op"] = None
    if _XF["h"] is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_XF["h"], 'WINDOW')
        except Exception:
            pass
        _XF["h"] = None


class FSKR_OT_part_transform(_PartTransformBase, bpy.types.Operator):
    bl_idname = "fskr.part_transform"
    bl_label = "뷰포트에서 자유 변형"
    bl_description = ("포토샵 Ctrl+T처럼 뷰포트에서 파츠를 옮기고(안쪽 드래그), "
                      "크기를 바꾸고(모서리·변), 돌립니다(위 동그라미·바깥). "
                      "Enter 확정 · Esc 취소. Shift = 비율 유지/15° 단위, "
                      "Alt = 기준점 기준 크기")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    lid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    @classmethod
    def poll(cls, context):
        s = context.scene.fskr
        return s.rig is not None and len(s.eyes) > 0


class FSKR_OT_part_transform_key(_PartTransformBase, bpy.types.Operator):
    """Ctrl+T: 캔버스를 골랐을 때만 자유 변형 (아니면 원래 Ctrl+T로)."""
    bl_idname = "fskr.part_transform_key"
    bl_label = "자유 변형 (Ctrl+T)"
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    lid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    @classmethod
    def poll(cls, context):
        s = context.scene.fskr
        ob = context.active_object
        return (s.rig is not None and ob is not None
                and context.mode == 'OBJECT'
                and any(ob.name == e.target for e in s.eyes))


face_classes = face_classes + (FSKR_OT_part_transform,
                               FSKR_OT_part_transform_key)
