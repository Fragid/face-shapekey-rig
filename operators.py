import bpy
import blf
import gpu
import json
import re
import time
import threading
from gpu_extras.batch import batch_for_shader
from math import radians, cos, sin
from mathutils import Vector, Matrix
from bpy_extras import view3d_utils
from bpy_extras.io_utils import ExportHelper, ImportHelper
from http.server import (BaseHTTPRequestHandler,
                         ThreadingHTTPServer)
from .atlas import (
    atlas_seq_names,
    atlas_apply,
    atlas_key_all,
    atlas_lip_bake,
    atlas_lip_enabled,
    atlas_reset,
    atlas_save_default,
    atlas_snapshot,
)
from .core import (
    _bone_world,
    _char_snapshot,
    _childof_set_inverse,
    _panel_follow_bind,
    _pb_pull,
    _pb_solo_apply,
    _pb_strips,
    _pb_target,
    _lipsync_resample,
    _ctl_mesh_get,
    _panel_space,
    _pg_restore,
    _resolve_mesh_name,
    AXIS_ITEMS,
    CTYPE_ITEMS,
    FSKR_ChainItem,
    FSKR_WizRoleItem,
    NONE,
    PAD,
    SLD,
    _ARKIT,
    _LIPSRV,
    _LipsyncHTTPHandler,
    _MOCAP,
    _SLOT_ORDER,
    _action_fcurves,
    _apply_ctl,
    _armature_items,
    _armature_items_keep,
    _batch_sel,
    _cd_tick,
    _chain_add_update,
    _collection_items,
    _copy_label_update,
    _create_ctl_bones,
    _draw_cb,
    _draw_group_row,
    _draw_pad_grid,
    _edge_arrows,
    _ensure_root,
    _frame_corners,
    _group_pick_items,
    _group_pick_update,
    _invalidate_ui_cache,
    _is_handle_name,
    _lipsrv_tick,
    _lipsync_analyze,
    _lipsync_build_segs,
    _lipsync_hist_json,
    _lipsync_html,
    _lipsync_padinfo,
    _lipsync_sync_off,
    _lipsync_topmost_tick,
    _mesh_items,
    _mesh_items_keep,
    _mirror_plan,
    _mocap_handshake,
    _mocap_stop_sock,
    _mocap_tick,
    _name_tokens,
    _next_ctl_name,
    _next_position,
    _open_editor_window,
    _pick_items,
    _pick_update,
    _preset_blend_start,
    _rdp_indices,
    _read_audio_mono,
    _read_meta,
    _redraw_ui,
    _remove_bone_drivers_for,
    _remove_drivers_for_bone,
    _shader,
    _shape_key_items,
    _shape_key_items_keep,
    _simplify_fcurve,
    _sorted_ctls,
    _start_playback,
    _stop_playback,
    _sync_key_names,
    _text_items,
    _text_set_color,
    _text_toggle_driver,
    _to_object_mode,
    _tr,
)


def _fit_scene_range(scene, a, b, op=None):
    """립싱크 구간이 씬 프레임 범위를 넘으면 끝 프레임을 늘린다.

    씬 끝 프레임보다 대사가 길면 재생이 끝 프레임에서 처음으로
    돌아가 버려 편집기와 블렌더 프레임이 어긋난다.
    """
    try:
        changed = False
        if b > scene.frame_end:
            scene.frame_end = b
            changed = True
        if a < scene.frame_start:
            scene.frame_start = a
            changed = True
        if scene.use_preview_range and b > scene.frame_preview_end:
            scene.frame_preview_end = b
            changed = True
        if changed and op is not None:
            op.report({'INFO'}, _tr("대사 길이에 맞춰 씬 끝 프레임을 %d로 "
                                    "늘렸습니다") % scene.frame_end)
    except Exception:
        pass


class FSKR_OT_add_slider(bpy.types.Operator):
    bl_idname = "fskr.add_slider"
    bl_label = "슬라이더 추가"
    bl_description = "선택한 셰이프 키를 조절하는 1D 슬라이더를 추가합니다"
    bl_options = {'REGISTER', 'UNDO'}

    mesh: bpy.props.EnumProperty(
        name="메시", items=_mesh_items,
        description="셰이프 키를 가져올 메시 (기본 = 설정의 얼굴 메시)")
    key: bpy.props.EnumProperty(name="셰이프 키", items=_shape_key_items)
    axis: bpy.props.EnumProperty(
        name="방향", default='H',
        items=(('H', "가로", "왼쪽→오른쪽"), ('V', "세로", "아래→위")))
    invert: bpy.props.BoolProperty(
        name="방향 반전", default=False,
        description="이동 방향을 반대로 (가로: 오른쪽→왼쪽, 세로: 위→아래). "
                    "원점은 항상 값 0")
    value_min: bpy.props.FloatProperty(
        name="최솟값", default=0.0, soft_min=-1.0, soft_max=1.0,
        description="음수로 하면 양방향 슬라이더가 됩니다 (중앙=0). "
                    "셰이프 키 자체의 Range Min도 음수여야 합니다")
    value_max: bpy.props.FloatProperty(
        name="최댓값", default=1.0, soft_min=-1.0, soft_max=1.0)
    snap: bpy.props.FloatProperty(
        name="앵커 스냅 임계값", default=0.0, min=0.0, soft_max=0.5,
        precision=3,
        description="핸들이 앵커(시작/중간/끝) 반경 안이면 위치와 값이 고정 "
                    "(0 = 스냅 끄기)")
    group: bpy.props.StringProperty(
        name="그룹", default="",
        description="같은 그룹끼리 목록에서 묶어 표시 (비우면 그룹 없음)")
    group_pick: bpy.props.EnumProperty(
        name="기존 그룹", items=_group_pick_items,
        update=_group_pick_update,
        description="기존 그룹/컬렉션에서 골라 채웁니다")
    use_color: bpy.props.BoolProperty(name="색상 사용", default=False)
    color: bpy.props.FloatVectorProperty(
        name="색상", subtype='COLOR', size=3, min=0.0, max=1.0,
        default=(1.0, 0.85, 0.4))
    chain: bpy.props.CollectionProperty(type=FSKR_ChainItem)
    chain_add: bpy.props.BoolProperty(
        name="연쇄 추가", default=False, update=_chain_add_update,
        description="이 슬라이더 값을 따라 함께 움직일 셰이프 키를 추가합니다")

    @classmethod
    def poll(cls, context):
        s = context.scene.fskr
        return s.mesh and s.rig

    def invoke(self, context, event):
        self.chain.clear()
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        col = self.layout.column()
        col.prop(self, "mesh")
        col.prop(self, "key")
        col.prop(self, "axis")
        col.prop(self, "invert")
        row = col.row(align=True)
        row.prop(self, "value_min")
        row.prop(self, "value_max")
        col.prop(self, "snap")
        _draw_group_row(col, self)
        row = col.row(align=True)
        row.prop(self, "use_color")
        if self.use_color:
            row.prop(self, "color", text="")
        # 연쇄 드라이버
        box = col.box()
        hr = box.row(align=True)
        hr.label(text=_tr("연쇄 드라이버"), icon='LINKED')
        hr.prop(self, "chain_add", text="", icon='ADD', toggle=True)
        if not len(self.chain):
            box.label(text=_tr("이 슬라이더를 따라 움직일 키를 + 로 추가"))
        for it in self.chain:
            r = box.row(align=True)
            r.prop(it, "mesh", text="")
            r.prop(it, "key", text="")
            sub = r.row(align=True)
            sub.ui_units_x = 1.8
            sub.prop(it, "factor", text="")
            r.prop(it, "rm", text="", icon='X', toggle=True)

    def execute(self, context):
        s = context.scene.fskr
        if self.key == NONE:
            self.report({'ERROR'}, _tr("셰이프 키를 선택하세요"))
            return {'CANCELLED'}
        if self.value_max <= self.value_min:
            self.report({'ERROR'}, _tr("최댓값이 최솟값보다 커야 합니다"))
            return {'CANCELLED'}
        rig = s.rig
        label = self.key
        ctype = 'SLD_V' if self.axis == 'V' else 'SLD_H'

        _to_object_mode(context, rig)
        _ensure_root(context, s, rig)
        if ctype == 'SLD_V':
            pos = _next_position(rig, SLD + 0.06)
        else:
            pos = _next_position(rig, 0.12)
            pos.x -= SLD / 2
        name = _next_ctl_name(rig)
        _create_ctl_bones(rig, name, pos)
        cfg = {"ctype": ctype, "label": label, "key": self.key,
               "mesh": "" if self.mesh == "__DEF__" else self.mesh,
               "invert": self.invert,
               "vmin": self.value_min, "vmax": self.value_max,
               "snap": self.snap, "group": self.group,
               "use_color": self.use_color, "color": tuple(self.color)}
        cfg["chain"] = [{"mesh": ("" if it.mesh == "__DEF__" else it.mesh),
                         "key": it.key, "f": float(it.factor)}
                        for it in self.chain
                        if not it.rm and it.key != NONE]
        if not _apply_ctl(context, s, rig, name, cfg):
            self.report({'ERROR'}, _tr("셰이프 키를 찾을 수 없습니다"))
            return {'CANCELLED'}
        bpy.ops.object.mode_set(mode='POSE')
        self.report({'INFO'}, _tr("슬라이더 추가: ") + label)
        return {'FINISHED'}


class FSKR_OT_add_pad(bpy.types.Operator):
    bl_idname = "fskr.add_pad"
    bl_label = "2D 패드 추가"
    bl_description = ("상/하/좌/우 방향별로 셰이프 키를 연결한 XY 패드를 추가합니다. "
                      "같은 키를 상+하(또는 좌+우)에 넣으면 -1~1 풀레인지로 동작합니다")
    bl_options = {'REGISTER', 'UNDO'}

    mesh: bpy.props.EnumProperty(
        name="메시", items=_mesh_items,
        description="셰이프 키를 가져올 메시 (기본 = 설정의 얼굴 메시)")
    up: bpy.props.EnumProperty(name="위 (Y+)", items=_shape_key_items)
    down: bpy.props.EnumProperty(name="아래 (Y-)", items=_shape_key_items)
    left: bpy.props.EnumProperty(name="왼쪽 (X-)", items=_shape_key_items)
    right: bpy.props.EnumProperty(name="오른쪽 (X+)", items=_shape_key_items)
    ul: bpy.props.EnumProperty(name="좌상 (대각)", items=_shape_key_items)
    ur: bpy.props.EnumProperty(name="우상 (대각)", items=_shape_key_items)
    dl: bpy.props.EnumProperty(name="좌하 (대각)", items=_shape_key_items)
    dr: bpy.props.EnumProperty(name="우하 (대각)", items=_shape_key_items)
    snap: bpy.props.FloatProperty(
        name="앵커 스냅 임계값", default=0.0, min=0.0, soft_max=0.5,
        precision=3,
        description="핸들이 앵커(모서리/변 중앙/중앙) 반경 안이면 위치와 값이 "
                    "앵커에 고정됩니다. 이동 범위 대비 비율 (0=끄기)")
    pmul: bpy.props.FloatProperty(
        name="배율", default=1.0, soft_min=-2.0, soft_max=2.0,
        precision=2,
        description="패드의 모든 값에 곱해질 배율 (예: 0.5 = 절반 강도, "
                    "음수 = 반대 방향)")
    pm_up: bpy.props.FloatProperty(
        name="배율", default=1.0, soft_min=-2.0, soft_max=2.0, precision=2,
        description="이 방향 키에만 곱해질 배율 (전체 배율과 곱해짐)")
    pm_down: bpy.props.FloatProperty(
        name="배율", default=1.0, soft_min=-2.0, soft_max=2.0, precision=2,
        description="이 방향 키에만 곱해질 배율 (전체 배율과 곱해짐)")
    pm_left: bpy.props.FloatProperty(
        name="배율", default=1.0, soft_min=-2.0, soft_max=2.0, precision=2,
        description="이 방향 키에만 곱해질 배율 (전체 배율과 곱해짐)")
    pm_right: bpy.props.FloatProperty(
        name="배율", default=1.0, soft_min=-2.0, soft_max=2.0, precision=2,
        description="이 방향 키에만 곱해질 배율 (전체 배율과 곱해짐)")
    pm_ul: bpy.props.FloatProperty(
        name="배율", default=1.0, soft_min=-2.0, soft_max=2.0, precision=2,
        description="이 방향 키에만 곱해질 배율 (전체 배율과 곱해짐)")
    pm_ur: bpy.props.FloatProperty(
        name="배율", default=1.0, soft_min=-2.0, soft_max=2.0, precision=2,
        description="이 방향 키에만 곱해질 배율 (전체 배율과 곱해짐)")
    pm_dl: bpy.props.FloatProperty(
        name="배율", default=1.0, soft_min=-2.0, soft_max=2.0, precision=2,
        description="이 방향 키에만 곱해질 배율 (전체 배율과 곱해짐)")
    pm_dr: bpy.props.FloatProperty(
        name="배율", default=1.0, soft_min=-2.0, soft_max=2.0, precision=2,
        description="이 방향 키에만 곱해질 배율 (전체 배율과 곱해짐)")
    group: bpy.props.StringProperty(
        name="그룹", default="",
        description="같은 그룹끼리 목록에서 묶어 표시 (비우면 그룹 없음)")
    group_pick: bpy.props.EnumProperty(
        name="기존 그룹", items=_group_pick_items,
        update=_group_pick_update,
        description="기존 그룹/컬렉션에서 골라 채웁니다")
    use_color: bpy.props.BoolProperty(name="색상 사용", default=False)
    color: bpy.props.FloatVectorProperty(
        name="색상", subtype='COLOR', size=3, min=0.0, max=1.0,
        default=(1.0, 0.85, 0.4))

    DIRS = ("up", "down", "left", "right", "ul", "ur", "dl", "dr")

    @classmethod
    def poll(cls, context):
        s = context.scene.fskr
        return s.mesh and s.rig

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=560)

    def draw(self, context):
        col = self.layout.column()
        col.prop(self, "mesh")
        col.separator()
        _draw_pad_grid(col, self)
        col.separator()
        col.prop(self, "snap")
        col.prop(self, "pmul")
        _draw_group_row(col, self)
        row = col.row(align=True)
        row.prop(self, "use_color")
        if self.use_color:
            row.prop(self, "color", text="")

    def execute(self, context):
        s = context.scene.fskr
        if all(getattr(self, d) == NONE for d in self.DIRS):
            self.report({'ERROR'}, _tr("방향을 하나 이상 연결하세요"))
            return {'CANCELLED'}
        rig = s.rig
        label = next((getattr(self, d) for d in self.DIRS
                      if getattr(self, d) != NONE), "Pad")

        _to_object_mode(context, rig)
        _ensure_root(context, s, rig)
        pos = _next_position(rig, 0.18)
        name = _next_ctl_name(rig)
        _create_ctl_bones(rig, name, pos)
        cfg = {"ctype": 'PAD', "label": label, "up": self.up,
               "mesh": "" if self.mesh == "__DEF__" else self.mesh,
               "down": self.down, "left": self.left, "right": self.right,
               "ul": self.ul, "ur": self.ur, "dl": self.dl, "dr": self.dr,
               "snap": self.snap, "pmul": self.pmul, "group": self.group,
               "use_color": self.use_color, "color": tuple(self.color)}
        for sl9 in self.DIRS:
            cfg["pm_" + sl9] = getattr(self, "pm_" + sl9)
        if not _apply_ctl(context, s, rig, name, cfg):
            self.report({'ERROR'}, _tr("선택한 셰이프 키를 찾을 수 없습니다"))
            return {'CANCELLED'}
        bpy.ops.object.mode_set(mode='POSE')
        self.report({'INFO'}, _tr("패드 추가: ") + label)
        return {'FINISHED'}


class FSKR_OT_add_bonepad(bpy.types.Operator):
    bl_idname = "fskr.add_bonepad"
    bl_label = "본 패드 추가"
    bl_description = ("핸들의 XY 이동으로 리그의 본(눈알 타겟 등)을 움직이는 "
                      "2D 패드를 추가합니다. 본을 2개 넣으면 동시에 움직입니다 "
                      "(양눈). 눈마다 따로 만들려면 본 1개씩 + 미러를 쓰세요")
    bl_options = {'REGISTER', 'UNDO'}

    trig: bpy.props.EnumProperty(
        name="대상 리그", items=_armature_items,
        description="움직일 본이 들어있는 아마추어 (설정의 리그와 달라도 됨)")
    tb1: bpy.props.StringProperty(
        name="대상 본 1",
        description="핸들을 따라 움직일 본 (예: c_eye_target.l)")
    tb2: bpy.props.StringProperty(
        name="대상 본 2 (선택)",
        description="함께 움직일 두 번째 본 (양눈 동시 제어용, 비우면 1개만)")
    bmode: bpy.props.EnumProperty(
        name="구동 방식", default='LOC',
        items=(('LOC', "위치 (이동)", ""),
               ('ROT', "회전 (머리 기준)", "")),
        description="본을 이동시킬지, 제자리에서 회전시킬지")
    bax: bpy.props.EnumProperty(
        name="가로 → 본 축", default='X', items=AXIS_ITEMS,
        description="핸들 좌우 이동을 대상 본의 어느 로컬 축으로 보낼지. "
                    "본을 G로 움직여 눈이 좌우로 도는 축을 고르세요")
    bay: bpy.props.EnumProperty(
        name="세로 → 본 축", default='Z', items=AXIS_ITEMS,
        description="핸들 상하 이동을 대상 본의 어느 로컬 축으로 보낼지")
    gx: bpy.props.FloatProperty(
        name="가로 이동량", default=0.1, soft_min=-1.0, soft_max=1.0,
        precision=3,
        description="핸들을 오른쪽 끝까지 밀었을 때 본이 이동하는 거리. "
                    "음수 = 반대 방향")
    gy: bpy.props.FloatProperty(
        name="세로 이동량", default=0.1, soft_min=-1.0, soft_max=1.0,
        precision=3,
        description="핸들을 위 끝까지 밀었을 때 본이 이동하는 거리. "
                    "음수 = 반대 방향")
    label: bpy.props.StringProperty(
        name="라벨", default="",
        description="목록에 표시할 이름 (비우면 대상 본 이름)")
    snap: bpy.props.FloatProperty(
        name="앵커 스냅 임계값", default=0.0, min=0.0, soft_max=0.5,
        precision=3,
        description="핸들이 앵커(모서리/변 중앙/중앙) 반경 안이면 위치와 값이 "
                    "앵커에 고정됩니다. 이동 범위 대비 비율 (0=끄기)")
    group: bpy.props.StringProperty(
        name="그룹", default="",
        description="같은 그룹끼리 목록에서 묶어 표시 (비우면 그룹 없음)")
    group_pick: bpy.props.EnumProperty(
        name="기존 그룹", items=_group_pick_items,
        update=_group_pick_update,
        description="기존 그룹/컬렉션에서 골라 채웁니다")
    use_color: bpy.props.BoolProperty(name="색상 사용", default=False)
    color: bpy.props.FloatVectorProperty(
        name="색상", subtype='COLOR', size=3, min=0.0, max=1.0,
        default=(1.0, 0.85, 0.4))

    @classmethod
    def poll(cls, context):
        s = context.scene.fskr
        return s.mesh and s.rig

    def invoke(self, context, event):
        s = context.scene.fskr
        if s.rig:
            try:
                self.trig = s.rig.name
            except TypeError:
                pass
        return context.window_manager.invoke_props_dialog(self, width=380)

    def draw(self, context):
        col = self.layout.column()
        col.prop(self, "trig")
        tob = bpy.data.objects.get(self.trig)
        if tob and tob.type == 'ARMATURE':
            col.prop_search(self, "tb1", tob.data, "bones")
            col.prop_search(self, "tb2", tob.data, "bones")
        else:
            col.prop(self, "tb1")
            col.prop(self, "tb2")
        col.prop(self, "bmode")
        rot9 = (self.bmode == 'ROT')
        row = col.row(align=True)
        row.prop(self, "bax")
        row.prop(self, "gx",
                 text=_tr("가로 회전량 (도)") if rot9 else "")
        row = col.row(align=True)
        row.prop(self, "bay")
        row.prop(self, "gy",
                 text=_tr("세로 회전량 (도)") if rot9 else "")
        col.separator()
        col.prop(self, "label")
        col.prop(self, "snap")
        _draw_group_row(col, self)
        row = col.row(align=True)
        row.prop(self, "use_color")
        if self.use_color:
            row.prop(self, "color", text="")

    def execute(self, context):
        s = context.scene.fskr
        rig = s.rig
        tob = bpy.data.objects.get(self.trig)
        if tob is None or tob.type != 'ARMATURE':
            self.report({'ERROR'}, _tr("대상 리그를 선택하세요"))
            return {'CANCELLED'}
        if not self.tb1 or self.tb1 not in tob.pose.bones:
            self.report({'ERROR'}, _tr("대상 본 1을 선택하세요"))
            return {'CANCELLED'}
        if self.tb1.startswith("FP_"):
            self.report({'ERROR'}, _tr("패널 본은 대상으로 쓸 수 없습니다"))
            return {'CANCELLED'}
        label = self.label.strip() or self.tb1

        _to_object_mode(context, rig)
        _ensure_root(context, s, rig)
        pos = _next_position(rig, 0.18)
        name = _next_ctl_name(rig)
        _create_ctl_bones(rig, name, pos)
        cfg = {"ctype": 'BONE', "label": label,
               "trig": self.trig,
               "tb1": self.tb1, "tb2": self.tb2,
               "bmode": self.bmode,
               "bax": self.bax, "bay": self.bay,
               "gx": self.gx, "gy": self.gy,
               "snap": self.snap, "group": self.group,
               "use_color": self.use_color, "color": tuple(self.color)}
        if not _apply_ctl(context, s, rig, name, cfg):
            self.report({'ERROR'}, _tr("대상 본을 찾을 수 없습니다"))
            return {'CANCELLED'}
        bpy.ops.object.mode_set(mode='POSE')
        self.report({'INFO'}, _tr("본 패드 추가: ") + label)
        return {'FINISHED'}


class FSKR_OT_edit_ctl(bpy.types.Operator):
    bl_idname = "fskr.edit_ctl"
    bl_label = "컨트롤러 수정"
    bl_description = "타입/방향/셰이프 키/라벨을 변경합니다"
    bl_options = {'REGISTER', 'UNDO'}

    bone: bpy.props.StringProperty(options={'HIDDEN'})
    ctype: bpy.props.EnumProperty(name="타입", items=CTYPE_ITEMS)
    mesh: bpy.props.EnumProperty(
        name="메시", items=_mesh_items,
        description="셰이프 키를 가져올 메시 (기본 = 설정의 얼굴 메시)")
    key: bpy.props.EnumProperty(name="셰이프 키", items=_shape_key_items)
    up: bpy.props.EnumProperty(name="위 (Y+)", items=_shape_key_items)
    down: bpy.props.EnumProperty(name="아래 (Y-)", items=_shape_key_items)
    left: bpy.props.EnumProperty(name="왼쪽 (X-)", items=_shape_key_items)
    right: bpy.props.EnumProperty(name="오른쪽 (X+)", items=_shape_key_items)
    ul: bpy.props.EnumProperty(name="좌상 (대각)", items=_shape_key_items)
    ur: bpy.props.EnumProperty(name="우상 (대각)", items=_shape_key_items)
    dl: bpy.props.EnumProperty(name="좌하 (대각)", items=_shape_key_items)
    dr: bpy.props.EnumProperty(name="우하 (대각)", items=_shape_key_items)
    label: bpy.props.StringProperty(name="라벨")
    copy_label: bpy.props.BoolProperty(
        name="셰이프 키 이름 복사", default=False,
        description="라벨을 셰이프 키(또는 대상 본) 이름으로 채웁니다",
        update=_copy_label_update)
    group: bpy.props.StringProperty(
        name="그룹", default="",
        description="같은 그룹끼리 목록에서 묶어 표시 (비우면 그룹 없음)")
    group_pick: bpy.props.EnumProperty(
        name="기존 그룹", items=_group_pick_items,
        update=_group_pick_update,
        description="기존 그룹/컬렉션에서 골라 채웁니다")
    invert: bpy.props.BoolProperty(
        name="방향 반전", default=False,
        description="이동 방향을 반대로 (원점은 항상 값 0)")
    value_min: bpy.props.FloatProperty(
        name="최솟값", default=0.0, soft_min=-1.0, soft_max=1.0,
        description="음수로 하면 양방향 슬라이더가 됩니다 (중앙=0)")
    value_max: bpy.props.FloatProperty(
        name="최댓값", default=1.0, soft_min=-1.0, soft_max=1.0)
    snap: bpy.props.FloatProperty(
        name="앵커 스냅 임계값", default=0.0, min=0.0, soft_max=0.5,
        precision=3,
        description="핸들이 앵커 반경 안이면 위치와 값이 고정 (0 = 끄기)")
    pmul: bpy.props.FloatProperty(
        name="배율", default=1.0, soft_min=-2.0, soft_max=2.0,
        precision=2,
        description="패드의 모든 값에 곱해질 배율 (예: 0.5 = 절반 강도, "
                    "음수 = 반대 방향)")
    pm_up: bpy.props.FloatProperty(
        name="배율", default=1.0, soft_min=-2.0, soft_max=2.0, precision=2,
        description="이 방향 키에만 곱해질 배율 (전체 배율과 곱해짐)")
    pm_down: bpy.props.FloatProperty(
        name="배율", default=1.0, soft_min=-2.0, soft_max=2.0, precision=2,
        description="이 방향 키에만 곱해질 배율 (전체 배율과 곱해짐)")
    pm_left: bpy.props.FloatProperty(
        name="배율", default=1.0, soft_min=-2.0, soft_max=2.0, precision=2,
        description="이 방향 키에만 곱해질 배율 (전체 배율과 곱해짐)")
    pm_right: bpy.props.FloatProperty(
        name="배율", default=1.0, soft_min=-2.0, soft_max=2.0, precision=2,
        description="이 방향 키에만 곱해질 배율 (전체 배율과 곱해짐)")
    pm_ul: bpy.props.FloatProperty(
        name="배율", default=1.0, soft_min=-2.0, soft_max=2.0, precision=2,
        description="이 방향 키에만 곱해질 배율 (전체 배율과 곱해짐)")
    pm_ur: bpy.props.FloatProperty(
        name="배율", default=1.0, soft_min=-2.0, soft_max=2.0, precision=2,
        description="이 방향 키에만 곱해질 배율 (전체 배율과 곱해짐)")
    pm_dl: bpy.props.FloatProperty(
        name="배율", default=1.0, soft_min=-2.0, soft_max=2.0, precision=2,
        description="이 방향 키에만 곱해질 배율 (전체 배율과 곱해짐)")
    pm_dr: bpy.props.FloatProperty(
        name="배율", default=1.0, soft_min=-2.0, soft_max=2.0, precision=2,
        description="이 방향 키에만 곱해질 배율 (전체 배율과 곱해짐)")
    use_color: bpy.props.BoolProperty(name="색상 사용", default=False)
    color: bpy.props.FloatVectorProperty(
        name="색상", subtype='COLOR', size=3, min=0.0, max=1.0,
        default=(1.0, 0.85, 0.4))
    trig: bpy.props.EnumProperty(
        name="대상 리그", items=_armature_items,
        description="움직일 본이 들어있는 아마추어")
    tb1: bpy.props.StringProperty(
        name="대상 본 1", description="핸들을 따라 움직일 본")
    tb2: bpy.props.StringProperty(
        name="대상 본 2 (선택)", description="함께 움직일 두 번째 본")
    bmode: bpy.props.EnumProperty(
        name="구동 방식", default='LOC',
        items=(('LOC', "위치 (이동)", ""),
               ('ROT', "회전 (머리 기준)", "")),
        description="본을 이동시킬지, 제자리에서 회전시킬지")
    bax: bpy.props.EnumProperty(
        name="가로 → 본 축", default='X', items=AXIS_ITEMS)
    bay: bpy.props.EnumProperty(
        name="세로 → 본 축", default='Z', items=AXIS_ITEMS)
    gx: bpy.props.FloatProperty(
        name="가로 이동량", default=0.1, soft_min=-1.0, soft_max=1.0,
        precision=3, description="음수 = 반대 방향")
    gy: bpy.props.FloatProperty(
        name="세로 이동량", default=0.1, soft_min=-1.0, soft_max=1.0,
        precision=3, description="음수 = 반대 방향")
    chain: bpy.props.CollectionProperty(type=FSKR_ChainItem)
    chain_add: bpy.props.BoolProperty(
        name="연쇄 추가", default=False, update=_chain_add_update,
        description="이 슬라이더 값을 따라 함께 움직일 셰이프 키를 추가합니다")

    def invoke(self, context, event):
        s = context.scene.fskr
        rig = s.rig
        if not rig or self.bone not in rig.pose.bones:
            return {'CANCELLED'}
        pb = rig.pose.bones[self.bone]
        # 체크된 항목의 연필을 누르면(2개 이상 체크) 일괄 수정으로 전환
        sel9, cats9 = _batch_sel(rig)
        if getattr(pb, "fskr_sel", False) and len(sel9) >= 2:
            if len(cats9) > 1:
                self.report({'ERROR'},
                            _tr("타입이 섞여 있습니다. 같은 타입끼리만 "
                            "일괄 수정할 수 있습니다"))
                return {'CANCELLED'}
            try:
                bpy.ops.fskr.batch_edit('INVOKE_DEFAULT')
            except RuntimeError:
                pass
            return {'CANCELLED'}
        mo_p = _ctl_mesh_get(pb)
        mv = mo_p.name if mo_p is not None else str(pb.get("fskr_mesh", ""))
        try:
            self.mesh = mv if mv else "__DEF__"
        except TypeError:  # 메시가 삭제/개명된 경우
            self.mesh = "__DEF__"
        tn5 = str(pb.get("fskr_trig", "")) or (s.rig.name if s.rig else "")
        if tn5:
            try:
                self.trig = tn5
            except TypeError:
                pass
        self.tb1 = str(pb.get("fskr_tb1", ""))
        self.tb2 = str(pb.get("fskr_tb2", ""))
        try:
            self.bmode = str(pb.get("fskr_bmode", "LOC")) or "LOC"
        except TypeError:
            self.bmode = 'LOC'
        self.bax = str(pb.get("fskr_bax", "X")) or "X"
        self.bay = str(pb.get("fskr_bay", "Z")) or "Z"
        self.gx = float(pb.get("fskr_gx", 0.1))
        self.gy = float(pb.get("fskr_gy", 0.1))
        self.ctype = str(pb.get("fskr_type", 'SLD_H'))
        self.label = str(pb.get("fskr_label", ""))
        self.group = str(pb.get("fskr_group", ""))
        self.invert = bool(pb.get("fskr_invert", 0))
        self.value_min = float(pb.get("fskr_vmin", 0.0))
        self.value_max = float(pb.get("fskr_vmax", 1.0))
        self.snap = float(pb.get("fskr_snap", 0.0))
        self.pmul = float(pb.get("fskr_pmul", 1.0))
        for sl9 in ("up", "down", "left", "right", "ul", "ur", "dl", "dr"):
            setattr(self, "pm_" + sl9,
                    float(pb.get("fskr_pm_" + sl9, 1.0)))
        self.use_color = bool(pb.get("fskr_usecolor", 0))
        col = pb.get("fskr_color", None)
        if col is not None and len(col) >= 3:
            self.color = (col[0], col[1], col[2])
        # 목록 스와치에서 색을 바꿨을 수 있으니 실제 본 색상을 우선
        if (self.use_color and hasattr(pb, "color")
                and pb.color.palette == 'CUSTOM'):
            self.color = tuple(pb.color.custom.normal)
        for prop in ("key", "up", "down", "left", "right",
                     "ul", "ur", "dl", "dr"):
            val = str(pb.get("fskr_" + prop, NONE))
            try:
                setattr(self, prop, val)
            except TypeError:  # 셰이프 키가 삭제/개명된 경우
                setattr(self, prop, NONE)
        # 연쇄 드라이버 목록 불러오기
        self.chain.clear()
        try:
            ch0 = json.loads(str(pb.get("fskr_chain", "[]")))
        except Exception:
            ch0 = []
        for ent in ch0:
            it = self.chain.add()
            mv0 = str(ent.get("mesh", ""))
            try:
                it.mesh = mv0 if mv0 else "__DEF__"
            except TypeError:
                it.mesh = "__DEF__"
            try:
                it.key = str(ent.get("key", NONE))
            except TypeError:
                pass
            it.factor = float(ent.get("f", 1.0))
        return context.window_manager.invoke_props_dialog(self, width=560)

    def draw(self, context):
        col = self.layout.column()
        col.prop(self, "ctype")
        if self.ctype != 'BONE':
            col.prop(self, "mesh")
        row = col.row(align=True)
        row.prop(self, "label")
        row.prop(self, "copy_label", text="", icon='COPYDOWN', toggle=True)
        _draw_group_row(col, self)
        row = col.row(align=True)
        row.prop(self, "use_color")
        if self.use_color:
            row.prop(self, "color", text="")
        col.separator()
        if self.ctype == 'PAD':
            _draw_pad_grid(col, self)
            col.prop(self, "snap", text=_tr("앵커 스냅 임계값"))
            col.prop(self, "pmul")
        elif self.ctype == 'BONE':
            col.prop(self, "trig")
            tob = bpy.data.objects.get(self.trig)
            if tob and tob.type == 'ARMATURE':
                col.prop_search(self, "tb1", tob.data, "bones")
                col.prop_search(self, "tb2", tob.data, "bones")
            else:
                col.prop(self, "tb1")
                col.prop(self, "tb2")
            col.prop(self, "bmode")
            rot9 = (self.bmode == 'ROT')
            row = col.row(align=True)
            row.prop(self, "bax")
            row.prop(self, "gx",
                     text=_tr("가로 회전량 (도)") if rot9 else "")
            row = col.row(align=True)
            row.prop(self, "bay")
            row.prop(self, "gy",
                     text=_tr("세로 회전량 (도)") if rot9 else "")
            col.prop(self, "snap")
        else:
            col.prop(self, "key")
            col.prop(self, "invert")
            row = col.row(align=True)
            row.prop(self, "value_min")
            row.prop(self, "value_max")
            col.prop(self, "snap")
            # 연쇄 드라이버 목록
            box = col.box()
            hr = box.row(align=True)
            hr.label(text=_tr("연쇄 드라이버"), icon='LINKED')
            hr.prop(self, "chain_add", text="", icon='ADD', toggle=True)
            if not len(self.chain):
                box.label(text=_tr("이 슬라이더를 따라 움직일 키를 + 로 추가"))
            for it in self.chain:
                r = box.row(align=True)
                r.prop(it, "mesh", text="")
                r.prop(it, "key", text="")
                sub = r.row(align=True)
                sub.ui_units_x = 1.8
                sub.prop(it, "factor", text="")
                r.prop(it, "rm", text="", icon='X', toggle=True)

    def execute(self, context):
        s = context.scene.fskr
        rig = s.rig
        if not rig or self.bone not in rig.pose.bones:
            return {'CANCELLED'}
        if (self.ctype in ('SLD_H', 'SLD_V')
                and self.value_max <= self.value_min):
            self.report({'ERROR'}, _tr("최댓값이 최솟값보다 커야 합니다"))
            return {'CANCELLED'}
        if self.ctype == 'BONE' and not self.tb1:
            self.report({'ERROR'}, _tr("대상 본 1을 선택하세요"))
            return {'CANCELLED'}
        _to_object_mode(context, rig)
        cfg = {"ctype": self.ctype, "label": self.label.strip() or self.bone,
               "mesh": "" if self.mesh == "__DEF__" else self.mesh,
               "key": self.key, "up": self.up, "down": self.down,
               "left": self.left, "right": self.right,
               "ul": self.ul, "ur": self.ur, "dl": self.dl, "dr": self.dr,
               "invert": self.invert,
               "vmin": self.value_min, "vmax": self.value_max,
               "snap": self.snap, "pmul": self.pmul, "group": self.group,
               "trig": self.trig,
               "tb1": self.tb1, "tb2": self.tb2,
               "bmode": self.bmode,
               "bax": self.bax, "bay": self.bay,
               "gx": self.gx, "gy": self.gy,
               "use_color": self.use_color, "color": tuple(self.color)}
        cfg["chain"] = [{"mesh": ("" if it.mesh == "__DEF__" else it.mesh),
                         "key": it.key, "f": float(it.factor)}
                        for it in self.chain
                        if not it.rm and it.key != NONE]
        for sl9 in ("up", "down", "left", "right", "ul", "ur", "dl", "dr"):
            cfg["pm_" + sl9] = getattr(self, "pm_" + sl9)
        if not _apply_ctl(context, s, rig, self.bone, cfg):
            self.report({'ERROR'}, _tr("연결할 셰이프 키(또는 대상 본)가 없습니다"))
            return {'CANCELLED'}
        bpy.ops.object.mode_set(mode='POSE')
        return {'FINISHED'}


class FSKR_OT_batch_edit(bpy.types.Operator):
    bl_idname = "fskr.batch_edit"
    bl_label = "일괄 수정 (체크된 항목)"
    bl_description = ("체크된 컨트롤러들을 한 번에 수정합니다 (체크된 항목의 "
                      "연필 버튼으로 열림). 같은 타입끼리만 가능하며, 값이 "
                      "서로 다른 항목은 '(다수 선택됨)'으로 표시됩니다")
    bl_options = {'REGISTER', 'UNDO'}

    label: bpy.props.StringProperty(name="라벨")
    group: bpy.props.StringProperty(
        name="그룹", description="비우고 적용하면 그룹에서 빠집니다")
    group_pick: bpy.props.EnumProperty(
        name="기존 그룹", items=_group_pick_items,
        update=_group_pick_update,
        description="기존 그룹/컬렉션에서 골라 채웁니다")
    usecol3: bpy.props.EnumProperty(
        name="색상", default='KEEP',
        items=(('KEEP', "(변경 안 함)", ""),
               ('ON', "사용", ""), ('OFF', "해제", "")))
    color: bpy.props.FloatVectorProperty(
        name="색상", subtype='COLOR', size=3, min=0.0, max=1.0,
        default=(1.0, 0.85, 0.4))
    mesh: bpy.props.EnumProperty(name="메시", items=_mesh_items_keep)
    key: bpy.props.EnumProperty(name="셰이프 키", items=_shape_key_items_keep)
    invert3: bpy.props.EnumProperty(
        name="방향 반전", default='KEEP',
        items=(('KEEP', "(변경 안 함)", ""),
               ('ON', "켬", ""), ('OFF', "끔", "")))
    apply_range: bpy.props.BoolProperty(name="범위 적용", default=False)
    value_min: bpy.props.FloatProperty(
        name="최솟값", default=0.0, soft_min=-1.0, soft_max=1.0)
    value_max: bpy.props.FloatProperty(
        name="최댓값", default=1.0, soft_min=-1.0, soft_max=1.0)
    apply_snap: bpy.props.BoolProperty(name="스냅 적용", default=False)
    snap: bpy.props.FloatProperty(
        name="앵커 스냅 임계값", default=0.0, min=0.0, soft_max=0.5,
        precision=3)
    trig: bpy.props.EnumProperty(name="대상 리그", items=_armature_items_keep)
    apply_axes: bpy.props.BoolProperty(name="축 적용", default=False)
    bmode: bpy.props.EnumProperty(
        name="구동 방식", default='LOC',
        items=(('LOC', "위치 (이동)", ""),
               ('ROT', "회전 (머리 기준)", "")),
        description="본을 이동시킬지, 제자리에서 회전시킬지")
    bax: bpy.props.EnumProperty(
        name="가로 → 본 축", default='X', items=AXIS_ITEMS)
    bay: bpy.props.EnumProperty(
        name="세로 → 본 축", default='Z', items=AXIS_ITEMS)
    apply_gain: bpy.props.BoolProperty(name="이동량 적용", default=False)
    gx: bpy.props.FloatProperty(
        name="가로 이동량", default=0.1, soft_min=-1.0, soft_max=1.0,
        precision=3)
    gy: bpy.props.FloatProperty(
        name="세로 이동량", default=0.1, soft_min=-1.0, soft_max=1.0,
        precision=3)

    @classmethod
    def poll(cls, context):
        s = context.scene.fskr
        return s.mesh and s.rig

    def invoke(self, context, event):
        s = context.scene.fskr
        rig = s.rig
        sel, cats = _batch_sel(rig)
        if not sel:
            self.report({'ERROR'}, _tr("체크된 컨트롤러가 없습니다"))
            return {'CANCELLED'}
        if len(cats) > 1:
            self.report({'ERROR'},
                        _tr("타입이 섞여 있습니다. 같은 타입끼리만 "
                        "일괄 수정할 수 있습니다"))
            return {'CANCELLED'}
        self._cat = cats.pop()
        metas = [_read_meta(rig.pose.bones[n]) for n in sel]

        def com(k, d=""):
            vals = {str(m.get(k, d)) for m in metas}
            return str(metas[0].get(k, d)) if len(vals) == 1 else None

        lb = com("label")
        self.label = lb if lb is not None else _tr("(다수 선택됨)")
        gp = com("group")
        self.group = gp if gp is not None else _tr("(다수 선택됨)")
        self._init_label = self.label
        self._init_group = self.group
        self.color = tuple(metas[0].get("color", (1.0, 0.85, 0.4)))
        self.value_min = float(metas[0].get("vmin", 0.0))
        self.value_max = float(metas[0].get("vmax", 1.0))
        self.snap = float(metas[0].get("snap", 0.0))
        self.bax = str(metas[0].get("bax", "X")) or "X"
        self.bay = str(metas[0].get("bay", "Z")) or "Z"
        self.gx = float(metas[0].get("gx", 0.1))
        self.gy = float(metas[0].get("gy", 0.1))
        return context.window_manager.invoke_props_dialog(self, width=380)

    def draw(self, context):
        col = self.layout.column()
        sel, _cats = _batch_sel(context.scene.fskr.rig)
        col.label(text=_tr("선택됨: %d개") % len(sel), icon='CHECKBOX_HLT')
        col.prop(self, "label")
        _draw_group_row(col, self)
        row = col.row(align=True)
        row.prop(self, "usecol3")
        if self.usecol3 == 'ON':
            row.prop(self, "color", text="")
        cat = getattr(self, "_cat", 'SLD')
        if cat != 'BONE':
            col.prop(self, "mesh")
        if cat == 'SLD':
            col.prop(self, "key")
            col.prop(self, "invert3")
            row = col.row(align=True)
            row.prop(self, "apply_range")
            sub = row.row(align=True)
            sub.enabled = self.apply_range
            sub.prop(self, "value_min", text="")
            sub.prop(self, "value_max", text="")
        if cat == 'BONE':
            col.prop(self, "trig")
            row = col.row(align=True)
            row.prop(self, "apply_axes")
            sub = row.row(align=True)
            sub.enabled = self.apply_axes
            sub.prop(self, "bax", text="")
            sub.prop(self, "bay", text="")
            row = col.row(align=True)
            row.prop(self, "apply_gain")
            sub = row.row(align=True)
            sub.enabled = self.apply_gain
            sub.prop(self, "gx", text="")
            sub.prop(self, "gy", text="")
        row = col.row(align=True)
        row.prop(self, "apply_snap")
        sub = row.row(align=True)
        sub.enabled = self.apply_snap
        sub.prop(self, "snap", text="")

    def execute(self, context):
        s = context.scene.fskr
        rig = s.rig
        sel, cats = _batch_sel(rig)
        if not sel or len(cats) > 1:
            return {'CANCELLED'}
        cat = getattr(self, "_cat", cats.pop() if cats else 'SLD')
        if (cat == 'SLD' and self.apply_range
                and self.value_max <= self.value_min):
            self.report({'ERROR'}, _tr("최댓값이 최솟값보다 커야 합니다"))
            return {'CANCELLED'}
        multi = _tr("(다수 선택됨)")
        _to_object_mode(context, rig)
        n = 0
        for name in sel:
            pb = rig.pose.bones[name]
            cfg = _read_meta(pb)
            if (self.label != getattr(self, "_init_label", multi)
                    and self.label.strip() and self.label != multi):
                cfg["label"] = self.label.strip()
            if (self.group != getattr(self, "_init_group", multi)
                    and self.group != multi):
                cfg["group"] = self.group
            if self.usecol3 == 'ON':
                cfg["use_color"] = True
                cfg["color"] = tuple(self.color)
            elif self.usecol3 == 'OFF':
                cfg["use_color"] = False
            if cat != 'BONE' and self.mesh != "__KEEP__":
                cfg["mesh"] = "" if self.mesh == "__DEF__" else self.mesh
            if cat == 'SLD':
                if self.key not in ("__KEEP__", NONE):
                    cfg["key"] = self.key
                if self.invert3 != 'KEEP':
                    cfg["invert"] = (self.invert3 == 'ON')
                if self.apply_range:
                    cfg["vmin"] = self.value_min
                    cfg["vmax"] = self.value_max
            if cat == 'BONE':
                if self.trig != "__KEEP__":
                    cfg["trig"] = self.trig
                if self.apply_axes:
                    cfg["bax"] = self.bax
                    cfg["bay"] = self.bay
                if self.apply_gain:
                    cfg["gx"] = self.gx
                    cfg["gy"] = self.gy
            if self.apply_snap:
                cfg["snap"] = self.snap
            if _apply_ctl(context, s, rig, name, cfg):
                n += 1
        bpy.ops.object.mode_set(mode='POSE')
        _redraw_ui(context)
        self.report({'INFO'}, _tr("일괄 수정: %d개 적용") % n)
        return {'FINISHED'}


class FSKR_OT_mirror_ctl(bpy.types.Operator):
    bl_idname = "fskr.mirror_ctl"
    bl_label = "반대쪽 자동 생성"
    bl_description = ("좌/우 포함식을 바꿔 반대쪽 셰이프 키를 찾아, 같은 설정과 "
                      "색상으로 반대쪽 컨트롤러를 만듭니다 (위치는 패널 중심 기준 "
                      "미러). 체크된 항목이 2개 이상이면 체크된 것들을 한꺼번에 "
                      "미러합니다")
    bl_options = {'REGISTER', 'UNDO'}

    bone: bpy.props.StringProperty()

    def execute(self, context):
        s = context.scene.fskr
        rig, mesh = s.rig, s.mesh
        if not (rig and mesh) or self.bone not in rig.pose.bones:
            return {'CANCELLED'}
        tl, tr = s.token_l, s.token_r
        if not tl or not tr:
            self.report({'ERROR'}, _tr("설정에서 좌/우 포함식을 입력하세요"))
            return {'CANCELLED'}
        pb0 = rig.pose.bones[self.bone]
        sel, _cats = _batch_sel(rig)
        targets = (sel if (getattr(pb0, "fskr_sel", False)
                           and len(sel) >= 2) else [self.bone])
        # 전부 사전 검증: 하나라도 문제가 있으면 아무것도 만들지 않음
        plans = []
        errs = []
        for b in targets:
            plan, err = _mirror_plan(s, rig, b)
            if err:
                errs.append(err)
            else:
                plans.append(plan)
        if errs:
            self.report({'ERROR'}, _tr("미러 취소 — ") + " | ".join(errs))
            return {'CANCELLED'}
        _to_object_mode(context, rig)
        made = []
        for plan in plans:
            name = _next_ctl_name(rig)
            _create_ctl_bones(rig, name, plan["pos"])
            nf = rig.pose.bones[name + "_frame"]
            nf.location = plan["loc"]
            nf.rotation_quaternion = plan["rot"]
            nf.scale = plan["scl"]
            context.view_layer.update()
            if not _apply_ctl(context, s, rig, name, plan["cfg"]):
                self.report({'ERROR'}, _tr("셰이프 키 연결에 실패했습니다"))
                return {'CANCELLED'}
            made.append(plan["cfg"]["label"])
        bpy.ops.object.mode_set(mode='POSE')
        self.report({'INFO'}, _tr("반대쪽 컨트롤러 생성: ") + ", ".join(made))
        return {'FINISHED'}


class FSKR_OT_add_text(bpy.types.Operator):
    bl_idname = "fskr.add_text"
    bl_label = "텍스트 추가"
    bl_description = ("자유 배치 가능한 라벨 텍스트를 만듭니다. 오브젝트 모드에서 "
                      "G/S로 배치·크기 조절, Tab으로 내용 수정, 폰트는 폰트 속성에서")
    bl_options = {'REGISTER', 'UNDO'}

    body: bpy.props.StringProperty(name="내용", default="Label")
    size: bpy.props.FloatProperty(name="크기", default=0.04,
                                  min=0.001, soft_max=0.2)
    color: bpy.props.FloatVectorProperty(
        name="색상", subtype='COLOR', size=3, min=0.0, max=1.0,
        default=(0.9, 0.9, 0.9))

    @classmethod
    def poll(cls, context):
        return context.scene.fskr.rig is not None

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        s = context.scene.fskr
        rig = s.rig
        _to_object_mode(context, rig)
        _ensure_root(context, s, rig)
        pos = _next_position(rig, 0.06)
        cu = bpy.data.curves.new("FPLBL_txt", 'FONT')
        cu.body = self.body
        cu.size = self.size
        cu.align_x = 'CENTER'
        cu.align_y = 'CENTER'
        # 텍스트 색상 (머티리얼 + 오브젝트 컬러)
        mat = bpy.data.materials.new("FPLBL_mat")
        mat.use_nodes = False
        mat.diffuse_color = (*self.color, 1.0)
        cu.materials.append(mat)
        ob = bpy.data.objects.new("FPLBL_txt", cu)
        ob.color = (*self.color, 1.0)
        context.scene.collection.objects.link(ob)
        ob.parent = rig
        ob.parent_type = 'BONE'
        ob.parent_bone = "FP_root"  # 패널과 함께 움직이도록
        context.view_layer.update()
        ob.matrix_world = (rig.matrix_world @ Matrix.Translation(pos)
                           @ Matrix.Rotation(radians(90), 4, 'X'))
        ob.hide_viewport = not s.labels_visible
        _text_toggle_driver(context.scene, rig, ob)
        for o in context.selected_objects:
            o.select_set(False)
        ob.select_set(True)
        context.view_layer.objects.active = ob
        self.report({'INFO'},
                    _tr("텍스트 생성: G/S로 배치, Tab으로 내용 수정"))
        return {'FINISHED'}


class FSKR_OT_text_color(bpy.types.Operator):
    bl_idname = "fskr.text_color"
    bl_label = "텍스트 색상"
    bl_description = ("텍스트(라벨)의 색상을 변경합니다. 포즈 모드에서도 대상 "
                      "텍스트를 골라 적용할 수 있고, 컨트롤러 색을 따올 수 있습니다")
    bl_options = {'REGISTER', 'UNDO'}

    target_text: bpy.props.EnumProperty(name="대상 텍스트", items=_text_items)
    pick_from: bpy.props.EnumProperty(
        name="스포이드", items=_pick_items, update=_pick_update,
        description="컨트롤러를 고르면 그 색을 그대로 따옵니다")
    color: bpy.props.FloatVectorProperty(
        name="색상", subtype='COLOR', size=3, min=0.0, max=1.0,
        default=(0.9, 0.9, 0.9))

    @classmethod
    def poll(cls, context):
        return (context.scene.fskr.rig is not None
                or any(o.type == 'FONT' for o in context.selected_objects))

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        col = self.layout.column()
        col.prop(self, "target_text")
        col.prop(self, "pick_from", icon='EYEDROPPER')
        col.prop(self, "color")

    def execute(self, context):
        if self.target_text != "SEL":
            ob = bpy.data.objects.get(self.target_text)
            targets = [ob] if (ob and ob.type == 'FONT') else []
        else:
            targets = [o for o in context.selected_objects
                       if o.type == 'FONT']
        if not targets:
            self.report({'ERROR'},
                        _tr("대상 텍스트가 없습니다 (팝업에서 텍스트를 선택하세요)"))
            return {'CANCELLED'}
        n = 0
        for ob in targets:
            _text_set_color(ob, tuple(self.color))
            n += 1
        self.report({'INFO'}, _tr("텍스트 %d개 색상 변경") % n)
        return {'FINISHED'}


class FSKR_OT_text_autocolor(bpy.types.Operator):
    bl_idname = "fskr.text_autocolor"
    bl_label = "텍스트 색상 자동"
    bl_description = ("각 텍스트에서 가장 가까운 컨트롤러를 찾아 그 색을 "
                      "자동으로 적용합니다 (색상을 사용하는 컨트롤러 기준)")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.fskr.rig is not None

    def execute(self, context):
        s = context.scene.fskr
        rig = s.rig
        ctls = []
        for b in rig.data.bones:
            if _is_handle_name(b.name):
                pb = rig.pose.bones[b.name]
                if bool(pb.get("fskr_usecolor", 0)):
                    fb = rig.pose.bones.get(b.name + "_frame")
                    cs = _frame_corners(fb if fb else pb)
                    x0 = min(c.x for c in cs)
                    x1 = max(c.x for c in cs)
                    z0 = min(c.z for c in cs)
                    z1 = max(c.z for c in cs)
                    center = Vector(((x0 + x1) / 2, cs[0].y,
                                     (z0 + z1) / 2))
                    ctls.append((rig.matrix_world @ center, pb))
        if not ctls:
            self.report({'ERROR'}, _tr("색상을 사용하는 컨트롤러가 없습니다"))
            return {'CANCELLED'}
        n = 0
        for ob in bpy.data.objects:
            if not (ob.name.startswith("FPLBL") and ob.type == 'FONT'):
                continue
            tp = ob.matrix_world.translation
            best = min(ctls, key=lambda c: (c[0] - tp).length)
            col2 = tuple(best[1].fskr_col)
            _text_set_color(ob, col2)
            n += 1
        self.report({'INFO'},
                    _tr("텍스트 %d개에 가장 가까운 컨트롤러 색 적용") % n)
        return {'FINISHED'}


class FSKR_OT_export_layout(bpy.types.Operator, ExportHelper):
    bl_idname = "fskr.export_layout"
    bl_label = "레이아웃 내보내기"
    bl_description = "패널 레이아웃(컨트롤러/텍스트/컬렉션)을 JSON으로 저장합니다"
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(default="*.json", options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        s = context.scene.fskr
        return s.rig is not None and "FP_root" in s.rig.data.bones

    def execute(self, context):
        s = context.scene.fskr
        rig = s.rig
        rootp = rig.pose.bones["FP_root"]
        rinv = rootp.matrix.inverted()
        data = {"fskr_layout": 2,
                "collections": [c.name for c in s.collections],
                "presets": [{"name": p.name, "data": p.data}
                            for p in s.presets],
                "controllers": [], "texts": []}
        for b in rig.data.bones:
            if not _is_handle_name(b.name):
                continue
            pb = rig.pose.bones[b.name]
            fb = rig.pose.bones[b.name + "_frame"]
            rel = rinv @ fb.matrix  # 루트 기준 상대 배치 (위치/회전/크기 통짜)
            ent = {"meta": _read_meta(pb),
                   "matrix": [list(r) for r in rel],
                   "order": int(pb.get("fskr_order", 0))}
            d = pb.get("fskr_def", None)
            if d is not None and len(d) >= 2:
                ent["default"] = [float(d[0]), float(d[1])]
            data["controllers"].append(ent)
        base = rig.matrix_world @ rig.pose.bones["FP_root"].matrix
        binv = base.inverted()
        for ob in bpy.data.objects:
            if ob.name.startswith("FPLBL") and ob.type == 'FONT':
                rel = binv @ ob.matrix_world
                data["texts"].append({
                    "body": ob.data.body,
                    "size": float(ob.data.size),
                    "color": [float(c) for c in tuple(ob.color)[:3]],
                    "matrix": [list(r) for r in rel]})
        # iFacialMocap 매핑도 포함 (컨트롤러는 라벨로 저장해 이식 가능하게)
        mmap = []
        for it in s.mocap_map:
            pbm = rig.pose.bones.get(it.ctl)
            mmap.append({
                "arkit": it.arkit, "tgt": it.tgt,
                "ctl_label": (str(pbm.get("fskr_label", it.ctl))
                              if pbm else ""),
                "comp": it.comp, "mesh": it.mesh, "key": it.key,
                "f": float(it.factor)})
        data["mocap"] = {
            "map": mmap,
            "head_rig": (s.mocap_head_rig.name
                         if s.mocap_head_rig else ""),
            "head_bone": s.mocap_head_bone,
            "head_gain": float(s.mocap_head_gain),
            "head_axes": [s.mocap_head_ax_p, s.mocap_head_ax_y,
                          s.mocap_head_ax_r],
            "head_invs": [bool(s.mocap_head_inv_p),
                          bool(s.mocap_head_inv_y),
                          bool(s.mocap_head_inv_r)],
            "smooth": float(s.mocap_smooth),
            "blend": float(s.mocap_blend),
        }
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.report({'INFO'}, _tr("레이아웃 저장: 컨트롤러 %d개, 텍스트 %d개")
                    % (len(data["controllers"]), len(data["texts"])))
        return {'FINISHED'}


class FSKR_OT_import_layout(bpy.types.Operator, ImportHelper):
    bl_idname = "fskr.import_layout"
    bl_label = "레이아웃 가져오기"
    bl_description = ("JSON 레이아웃을 불러와 패널을 구성합니다. "
                      "같은 이름의 셰이프 키에 자동 연결되며, 없는 키의 "
                      "컨트롤러는 건너뜁니다")
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(default="*.json", options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        s = context.scene.fskr
        return s.mesh is not None and s.rig is not None

    def execute(self, context):
        s = context.scene.fskr
        rig = s.rig
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            self.report({'ERROR'}, _tr("파일을 읽을 수 없습니다: %s") % e)
            return {'CANCELLED'}
        if "fskr_layout" not in data:
            self.report({'ERROR'}, _tr("레이아웃 파일이 아닙니다"))
            return {'CANCELLED'}

        _to_object_mode(context, rig)
        _ensure_root(context, s, rig)
        for nm in data.get("collections", []):
            if nm not in [c.name for c in s.collections]:
                item = s.collections.add()
                item.name = nm
        for pr in data.get("presets", []):
            item = next((p for p in s.presets
                         if p.name == pr.get("name")), None)
            if item is None:
                item = s.presets.add()
                item.name = pr.get("name", "Preset")
            item.data = pr.get("data", "{}")

        rootb = rig.data.bones["FP_root"]
        rootp = rig.pose.bones["FP_root"]
        n = 0
        skipped = 0
        for ent in sorted(data.get("controllers", []),
                          key=lambda e: e.get("order", 0)):
            if "matrix" in ent:  # v2: 루트 기준 상대 행렬
                relm = Matrix(ent["matrix"])
                pos = Vector(rootb.head_local) + relm.translation
            else:  # v1 호환
                relm = None
                pos = Vector(rootb.head_local) + Vector(ent["offset"])
            name = _next_ctl_name(rig)
            _create_ctl_bones(rig, name, pos)
            fb = rig.pose.bones[name + "_frame"]
            if relm is not None:
                context.view_layer.update()
                fb.matrix = rootp.matrix @ relm
            else:
                fb.location = ent.get("loc", (0.0, 0.0, 0.0))
                fb.rotation_quaternion = ent.get("rot",
                                                 (1.0, 0.0, 0.0, 0.0))
                fb.scale = ent.get("scl", (1.0, 1.0, 1.0))
            context.view_layer.update()
            cfg = dict(ent["meta"])
            cfg["color"] = tuple(cfg.get("color", (1.0, 0.85, 0.4)))
            if not _apply_ctl(context, s, rig, name, cfg):
                # 대응하는 셰이프 키가 없는 컨트롤러는 제거
                bpy.ops.object.mode_set(mode='EDIT')
                eb = rig.data.edit_bones
                for n2 in (name, name + "_frame"):
                    if n2 in eb:
                        eb.remove(eb[n2])
                bpy.ops.object.mode_set(mode='OBJECT')
                skipped += 1
                continue
            pb = rig.pose.bones[name]
            pb["fskr_order"] = int(ent.get("order", 0))
            if "default" in ent:
                pb["fskr_def"] = [float(v) for v in ent["default"]]
            n += 1

        # 텍스트 복원
        base = rig.matrix_world @ rig.pose.bones["FP_root"].matrix
        tn2 = 0
        for t in data.get("texts", []):
            cu = bpy.data.curves.new("FPLBL_txt", 'FONT')
            cu.body = t.get("body", "Label")
            cu.size = float(t.get("size", 0.04))
            cu.align_x = 'CENTER'
            cu.align_y = 'CENTER'
            col3 = tuple(t.get("color", (0.9, 0.9, 0.9)))[:3]
            mat = bpy.data.materials.new("FPLBL_mat")
            mat.use_nodes = False
            mat.diffuse_color = (*col3, 1.0)
            cu.materials.append(mat)
            ob = bpy.data.objects.new("FPLBL_txt", cu)
            ob.color = (*col3, 1.0)
            context.scene.collection.objects.link(ob)
            ob.parent = rig
            ob.parent_type = 'BONE'
            ob.parent_bone = "FP_root"
            context.view_layer.update()
            ob.matrix_world = base @ Matrix(t["matrix"])
            ob.hide_viewport = not s.labels_visible
            _text_toggle_driver(context.scene, rig, ob)
            tn2 += 1

        # iFacialMocap 매핑 복원 (라벨 → 새 컨트롤러 본으로 연결)
        mc = data.get("mocap")
        if mc:
            lbl_map = {}
            for b in rig.data.bones:
                if _is_handle_name(b.name):
                    lbl_map[str(rig.pose.bones[b.name]
                                .get("fskr_label", ""))] = b.name
            s.mocap_map.clear()
            for ent in mc.get("map", []):
                it = s.mocap_map.add()
                for attr, dv in (("arkit", "eyeBlinkLeft"), ("tgt", 'CTL'),
                                 ("comp", 'VAL')):
                    try:
                        setattr(it, attr, str(ent.get(attr, dv)))
                    except TypeError:
                        pass
                cn9 = lbl_map.get(str(ent.get("ctl_label", "")))
                if cn9:
                    try:
                        it.ctl = cn9
                    except TypeError:
                        pass
                try:
                    it.mesh = str(ent.get("mesh", "__DEF__")) or "__DEF__"
                except TypeError:
                    pass
                try:
                    it.key = str(ent.get("key", NONE))
                except TypeError:
                    pass
                it.factor = float(ent.get("f", 1.0))
            s.mocap_head_bone = str(mc.get("head_bone",
                                           s.mocap_head_bone))
            hr9 = str(mc.get("head_rig", ""))
            ob9 = bpy.data.objects.get(hr9) if hr9 else None
            if ob9 and ob9.type == 'ARMATURE':
                s.mocap_head_rig = ob9
            s.mocap_head_gain = float(mc.get("head_gain",
                                             s.mocap_head_gain))
            axs = mc.get("head_axes")
            if isinstance(axs, list) and len(axs) >= 3:
                for attr9, v9 in zip(("mocap_head_ax_p", "mocap_head_ax_y",
                                      "mocap_head_ax_r"), axs):
                    try:
                        setattr(s, attr9, str(v9))
                    except TypeError:
                        pass
            invs = mc.get("head_invs")
            if isinstance(invs, list) and len(invs) >= 3:
                s.mocap_head_inv_p = bool(invs[0])
                s.mocap_head_inv_y = bool(invs[1])
                s.mocap_head_inv_r = bool(invs[2])
            s.mocap_smooth = float(mc.get("smooth", s.mocap_smooth))
            s.mocap_blend = float(mc.get("blend", s.mocap_blend))

        bpy.ops.object.mode_set(mode='POSE')
        msg = _tr("가져오기 완료: 컨트롤러 %d개, 텍스트 %d개") % (n, tn2)
        if skipped:
            msg += _tr(" (셰이프 키 없음 %d개 건너뜀)") % skipped
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class FSKR_OT_preset_save(bpy.types.Operator):
    bl_idname = "fskr.preset_save"
    bl_label = "프리셋 저장"
    bl_description = "현재 컨트롤러 값들을 표정 프리셋으로 저장합니다"
    bl_options = {'REGISTER'}  # UNDO 제외: 무거운 씬에서 스냅샷 지연 방지

    pname: bpy.props.StringProperty(name="프리셋 이름", default="표정")

    @classmethod
    def poll(cls, context):
        return context.scene.fskr.rig is not None

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        s = context.scene.fskr
        name = self.pname.strip()
        if not name:
            self.report({'ERROR'}, _tr("프리셋 이름을 입력하세요"))
            return {'CANCELLED'}
        vals = {}
        for pb in s.rig.pose.bones:
            if _is_handle_name(pb.name):
                lbl = str(pb.get("fskr_label", pb.name))
                vals[lbl] = [float(pb.location[0]), float(pb.location[1])]
        if len(s.atlases):
            vals["__atlas__"] = atlas_snapshot(s)
        item = next((p for p in s.presets if p.name == name), None)
        if item is None:
            item = s.presets.add()
            item.name = name
        item.data = json.dumps(vals, ensure_ascii=False)
        _redraw_ui(context)
        self.report({'INFO'}, _tr("프리셋 '%s' 저장 (컨트롤러 %d개)")
                    % (name, len(vals) - (1 if "__atlas__" in vals else 0)))
        return {'FINISHED'}


class FSKR_OT_preset_apply(bpy.types.Operator):
    bl_idname = "fskr.preset_apply"
    bl_label = "프리셋 적용"
    bl_description = "저장된 표정 프리셋을 컨트롤러에 적용합니다"
    bl_options = {'REGISTER', 'UNDO'}

    pname: bpy.props.StringProperty()

    def execute(self, context):
        s = context.scene.fskr
        item = next((p for p in s.presets if p.name == self.pname), None)
        if item is None or not s.rig:
            return {'CANCELLED'}
        try:
            vals = json.loads(item.data)
        except Exception:
            self.report({'ERROR'}, _tr("프리셋 데이터가 손상되었습니다"))
            return {'CANCELLED'}
        n = 0
        targets = {}
        for pb in s.rig.pose.bones:
            if _is_handle_name(pb.name):
                lbl = str(pb.get("fskr_label", pb.name))
                if lbl in vals:
                    v = vals[lbl]
                    targets[pb.name] = (float(v[0]), float(v[1]))
                    n += 1
        _preset_blend_start(s.rig, targets, float(s.mocap_blend))
        try:
            atlas_apply(s, vals.get("__atlas__", {}),
                        key=context.scene.tool_settings.use_keyframe_insert_auto)
        except Exception:
            pass
        context.view_layer.update()
        self.report({'INFO'}, _tr("'%s' 적용 (컨트롤러 %d개)") % (self.pname, n))
        return {'FINISHED'}


class FSKR_OT_preset_rename(bpy.types.Operator):
    bl_idname = "fskr.preset_rename"
    bl_label = "프리셋 이름 변경"
    bl_description = "표정 프리셋의 이름을 바꿉니다"
    bl_options = {'REGISTER'}  # UNDO 제외: 무거운 씬에서 스냅샷 지연 방지

    pname: bpy.props.StringProperty(options={'HIDDEN'})
    new_name: bpy.props.StringProperty(name="새 이름")

    def invoke(self, context, event):
        self.new_name = self.pname
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        s = context.scene.fskr
        nm = self.new_name.strip()
        if not nm:
            self.report({'ERROR'}, _tr("이름을 입력하세요"))
            return {'CANCELLED'}
        if any(p.name == nm for p in s.presets if p.name != self.pname):
            self.report({'ERROR'}, _tr("같은 이름의 프리셋이 있습니다"))
            return {'CANCELLED'}
        p = next((p for p in s.presets if p.name == self.pname), None)
        if p is None:
            return {'CANCELLED'}
        p.name = nm
        _redraw_ui(context)
        self.report({'INFO'}, _tr("이름 변경: ") + nm)
        return {'FINISHED'}


class FSKR_OT_preset_del(bpy.types.Operator):
    bl_idname = "fskr.preset_del"
    bl_label = "프리셋 삭제"
    bl_options = {'REGISTER'}  # UNDO 제외: 무거운 씬에서 스냅샷 지연 방지

    pname: bpy.props.StringProperty()

    def execute(self, context):
        s = context.scene.fskr
        for i, p in enumerate(s.presets):
            if p.name == self.pname:
                s.presets.remove(i)
                break
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_bake_keys(bpy.types.Operator):
    bl_idname = "fskr.bake_keys"
    bl_label = "셰이프 키 베이크 (익스포트용)"
    bl_description = ("프레임 구간의 드라이버 값을 셰이프 키 키프레임으로 굽고 "
                      "드라이버를 제거합니다. FBX/VRM 익스포트 전에 사용하세요. "
                      "패널 복구는 '뷰포트 패널 리로드'")
    bl_options = {'REGISTER', 'UNDO'}

    frame_start: bpy.props.IntProperty(name="시작 프레임", default=1)
    frame_end: bpy.props.IntProperty(name="끝 프레임", default=250)

    @classmethod
    def poll(cls, context):
        s = context.scene.fskr
        return s.mesh is not None and s.mesh.data.shape_keys is not None

    def invoke(self, context, event):
        self.frame_start = context.scene.frame_start
        self.frame_end = context.scene.frame_end
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        s = context.scene.fskr
        rig = s.rig
        # 이 리그의 FP_ctl 핸들이 모는 셰이프 키 드라이버 수집 (모든 메시)
        kchans = []
        for kd in bpy.data.shape_keys:
            ad = kd.animation_data
            if not (ad and ad.drivers):
                continue
            for fc in ad.drivers:
                dp = fc.data_path
                if not dp.startswith('key_blocks["'):
                    continue
                if any(any(t.id == rig
                           and str(t.bone_target).startswith("FP_ctl")
                           for t in var.targets)
                       for var in fc.driver.variables):
                    nm = dp[len('key_blocks["'):dp.rfind('"]')]
                    if (kd, nm) not in kchans:
                        kchans.append((kd, nm))
        # 본 패드가 움직이는 본 위치 채널도 베이크 대상 (모든 아마추어)
        bchans = []
        for ob5 in bpy.data.objects:
            if ob5.type != 'ARMATURE' or not ob5.animation_data:
                continue
            for fc in ob5.animation_data.drivers:
                dp = fc.data_path
                if not (dp.startswith('pose.bones["')
                        and dp.endswith('].location')):
                    continue
                if "FP_ctl" in dp:
                    continue
                if any(any(t.id == rig
                           and str(t.bone_target).startswith("FP_ctl")
                           for t in var.targets)
                       for var in fc.driver.variables):
                    bn = dp[len('pose.bones["'):dp.rfind('"]')]
                    bchans.append((ob5, bn, fc.array_index))
        if not kchans and not bchans:
            self.report({'ERROR'}, _tr("베이크할 드라이버가 없습니다"))
            return {'CANCELLED'}
        scene = context.scene
        cur = scene.frame_current
        for f in range(self.frame_start, self.frame_end + 1):
            scene.frame_set(f)
            for kd, nm in kchans:
                kb = kd.key_blocks.get(nm)
                if kb:
                    kb.keyframe_insert("value", frame=f)
            for ob5, bn, bi in bchans:
                pb4 = ob5.pose.bones.get(bn)
                if pb4:
                    pb4.keyframe_insert("location", index=bi, frame=f)
        scene.frame_set(cur)
        for kd, nm in kchans:
            kb = kd.key_blocks.get(nm)
            if kb:
                try:
                    kb.driver_remove("value")
                except Exception:
                    pass
        for ob5, bn, bi in bchans:
            try:
                ob5.driver_remove('pose.bones["%s"].location' % bn, bi)
            except Exception:
                pass
        _invalidate_ui_cache()
        self.report({'INFO'},
                    _tr("셰이프 키 %d개 + 본 채널 %d개 x %d프레임 베이크 완료. "
                    "드라이버 제거됨 — 패널 복구는 '뷰포트 패널 리로드'")
                    % (len(kchans), len(bchans),
                       self.frame_end - self.frame_start + 1))
        return {'FINISHED'}


class FSKR_OT_add_collection(bpy.types.Operator):
    bl_idname = "fskr.add_collection"
    bl_label = "컬렉션 추가"
    bl_description = "새 컬렉션을 만듭니다. 체크한 컨트롤러가 있으면 바로 담습니다"
    bl_options = {'REGISTER', 'UNDO'}

    coll_name: bpy.props.StringProperty(name="컬렉션 이름", default="")

    @classmethod
    def poll(cls, context):
        return context.scene.fskr.rig is not None

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        s = context.scene.fskr
        name = self.coll_name.strip()
        if not name:
            self.report({'ERROR'}, _tr("컬렉션 이름을 입력하세요"))
            return {'CANCELLED'}
        if name not in [c.name for c in s.collections]:
            item = s.collections.add()
            item.name = name
        # 체크된 컨트롤러가 있으면 바로 담기
        n = 0
        for pb in s.rig.pose.bones:
            if _is_handle_name(pb.name) and getattr(pb, "fskr_sel", False):
                pb["fskr_group"] = name
                pb.fskr_sel = False
                n += 1
        msg = _tr("컬렉션 '%s' 생성") % name
        if n:
            msg += _tr(" (컨트롤러 %d개 추가)") % n
        _redraw_ui(context)
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class FSKR_OT_del_collection(bpy.types.Operator):
    bl_idname = "fskr.del_collection"
    bl_label = "컬렉션 삭제"
    bl_description = "컬렉션을 없애고 소속 컨트롤러를 컬렉션 밖으로 뺍니다 (컨트롤러는 유지)"
    bl_options = {'REGISTER', 'UNDO'}

    coll_name: bpy.props.StringProperty()

    def execute(self, context):
        s = context.scene.fskr
        if s.rig:
            for pb in s.rig.pose.bones:
                if (_is_handle_name(pb.name)
                        and str(pb.get("fskr_group", "")) == self.coll_name):
                    pb["fskr_group"] = ""
        for i, c in enumerate(s.collections):
            if c.name == self.coll_name:
                s.collections.remove(i)
                break
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_assign_collection(bpy.types.Operator):
    bl_idname = "fskr.assign_collection"
    bl_label = "선택 → 컬렉션"
    bl_description = "체크한 컨트롤러들을 선택한 컬렉션에 넣거나 뺍니다"
    bl_options = {'REGISTER', 'UNDO'}

    target: bpy.props.EnumProperty(name="대상 컬렉션", items=_collection_items)

    @classmethod
    def poll(cls, context):
        return context.scene.fskr.rig is not None

    def invoke(self, context, event):
        rig = context.scene.fskr.rig
        if not any(_is_handle_name(pb.name) and getattr(pb, "fskr_sel", False)
                   for pb in rig.pose.bones):
            self.report({'ERROR'}, _tr("먼저 컨트롤러 옆 체크박스를 선택하세요"))
            return {'CANCELLED'}
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        s = context.scene.fskr
        target = "" if self.target == "__REMOVE__" else self.target
        n = 0
        for pb in s.rig.pose.bones:
            if _is_handle_name(pb.name) and getattr(pb, "fskr_sel", False):
                pb["fskr_group"] = target
                pb.fskr_sel = False
                n += 1
        _redraw_ui(context)
        if target:
            self.report({'INFO'}, _tr("컨트롤러 %d개 → '%s'") % (n, target))
        else:
            self.report({'INFO'}, _tr("컨트롤러 %d개를 컬렉션에서 제거") % n)
        return {'FINISHED'}


class FSKR_OT_repair_layout(bpy.types.Operator):
    bl_idname = "fskr.repair_layout"
    bl_label = "패널 정렬 복구"
    bl_description = ("틀/핸들에 남은 포즈 회전을 초기화해 배치 모드 "
                      "화살표와 스냅을 정상화합니다 (위치·크기·값은 유지)")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        s = context.scene.fskr
        return s.rig is not None

    def execute(self, context):
        s = context.scene.fskr
        rig = s.rig
        n = 0
        for pb in rig.pose.bones:
            if not pb.name.startswith("FP_"):
                continue
            try:
                had9 = (tuple(pb.rotation_quaternion) !=
                        (1.0, 0.0, 0.0, 0.0)
                        or tuple(pb.rotation_euler) != (0.0, 0.0, 0.0))
                pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
                pb.rotation_euler = (0.0, 0.0, 0.0)
                if had9:
                    n += 1
            except Exception:
                pass
        try:
            context.view_layer.update()
        except Exception:
            pass
        self.report({'INFO'}, _tr("패널 정렬 복구 완료 (%d개)") % n)
        return {'FINISHED'}


class FSKR_OT_reload_panel(bpy.types.Operator):
    bl_idname = "fskr.reload_panel"
    bl_label = "뷰포트 패널 리로드"
    bl_description = ("저장된 설정으로 모든 컨트롤러를 다시 구성합니다. "
                      "위젯/드라이버/토글 연결을 최신 버전 방식으로 재적용합니다")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        s = context.scene.fskr
        return s.mesh is not None and s.rig is not None

    def execute(self, context):
        s = context.scene.fskr
        rig = s.rig
        _sync_key_names(rig)  # 셰이프 키 이름 변경분 먼저 반영
        _to_object_mode(context, rig)
        _ensure_root(context, s, rig)
        names = [b.name for b in rig.data.bones if _is_handle_name(b.name)]
        # 리로드 전 컨트롤러 값(핸들 위치) 보존
        vals9 = {}
        for name in names:
            try:
                vals9[name] = tuple(rig.pose.bones[name].location)
            except Exception:
                pass
        n = 0
        for name in names:
            pb = rig.pose.bones[name]
            cfg = _read_meta(pb)
            if _apply_ctl(context, s, rig, name, cfg):
                n += 1
        # 값 복원 (리로드가 세팅을 초기화하지 않도록)
        for name, lv9 in vals9.items():
            try:
                rig.pose.bones[name].location = lv9
            except Exception:
                pass
        # 텍스트 라벨도 토글에 연결
        for ob in bpy.data.objects:
            if ob.name.startswith("FPLBL"):
                _text_toggle_driver(context.scene, rig, ob)
        bpy.ops.object.mode_set(mode='POSE')
        self.report({'INFO'}, _tr("패널 리로드 완료 (컨트롤러 %d개)") % n)
        return {'FINISHED'}


class FSKR_OT_sync_names(bpy.types.Operator):
    bl_idname = "fskr.sync_names"
    bl_label = "셰이프 키 이름 동기화"
    bl_description = ("셰이프 키 이름을 바꾼 뒤 실행하세요. 드라이버가 실제로 "
                      "연결된 키 이름을 읽어 목록/메타데이터를 갱신합니다")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.fskr.rig is not None

    def execute(self, context):
        n = _sync_key_names(context.scene.fskr.rig)
        _redraw_ui(context)
        self.report({'INFO'}, _tr("이름 갱신 %d건") % n)
        return {'FINISHED'}


class FSKR_OT_attach_panel(bpy.types.Operator):
    bl_idname = "fskr.attach_panel"
    bl_label = "머리에 부착"
    bl_description = "패널을 본에 붙이기 (해제하려면 본을 비우고 실행)"
    bl_options = {'REGISTER', 'UNDO'}

    trig: bpy.props.EnumProperty(name="대상 리그", items=_armature_items)
    bone: bpy.props.StringProperty(name="패널이 따라갈 본")

    @classmethod
    def poll(cls, context):
        s = context.scene.fskr
        return s.rig is not None and "FP_root" in s.rig.pose.bones

    def invoke(self, context, event):
        s = context.scene.fskr
        pb = s.rig.pose.bones["FP_root"]
        for c9 in pb.constraints:
            if c9.name == "FSKR_follow" and c9.type == 'CHILD_OF':
                self.bone = str(getattr(c9, "subtarget", ""))
                if getattr(c9, "target", None) is not None:
                    try:
                        self.trig = c9.target.name
                    except TypeError:
                        pass
        if not self.bone:
            hr9 = getattr(s, "mocap_head_rig", None)
            if hr9 is not None:
                try:
                    self.trig = hr9.name
                except TypeError:
                    pass
            self.bone = str(getattr(s, "mocap_head_bone", "") or "")
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        col = self.layout.column()
        col.prop(self, "trig")
        tob = bpy.data.objects.get(self.trig)
        if tob and tob.type == 'ARMATURE':
            col.prop_search(self, "bone", tob.data, "bones")
        else:
            col.prop(self, "bone")

    def execute(self, context):
        s = context.scene.fskr
        rig = s.rig
        pb = rig.pose.bones["FP_root"]
        for c9 in list(pb.constraints):
            if c9.name == "FSKR_follow":
                pb.constraints.remove(c9)
        bn = self.bone.strip()
        if not bn:
            self.report({'INFO'}, _tr("패널 부착 해제"))
            return {'FINISHED'}
        tob = bpy.data.objects.get(self.trig)
        if tob is None or tob.type != 'ARMATURE':
            tob = rig
        if bn not in tob.pose.bones or bn.startswith("FP_"):
            self.report({'ERROR'}, _tr("대상 본을 찾을 수 없습니다"))
            return {'CANCELLED'}
        try:
            bpy.context.view_layer.update()
            before9 = _bone_world(rig, pb).copy()
        except Exception:
            before9 = None
        c9 = pb.constraints.new('CHILD_OF')
        c9.name = "FSKR_follow"
        c9.target = tob
        c9.subtarget = bn
        # 위치만 따라감 (회전을 따라가면 배치 모드 계산이 어긋남)
        c9.use_rotation_x = False
        c9.use_rotation_y = False
        c9.use_rotation_z = False
        c9.use_scale_x = False
        c9.use_scale_y = False
        c9.use_scale_z = False
        # 현재 위치 유지 (실측 인버스 설정)
        if before9 is not None:
            _childof_set_inverse(c9, rig, pb, before9)
        self.report({'INFO'}, _tr("패널 부착: ") + bn)
        return {'FINISHED'}


class FSKR_OT_place_panel(bpy.types.Operator):
    bl_idname = "fskr.place_panel"
    bl_label = "패널 위치 지정"
    bl_description = ("뷰포트에 크로스헤어가 나타납니다. 클릭한 위치에 패널이 "
                      "생성되고, 이미 있으면 패널 전체가 그곳으로 이동합니다. "
                      "우클릭/ESC = 취소")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.fskr.rig is not None

    def invoke(self, context, event):
        if context.area is None or context.area.type != 'VIEW_3D':
            self.report({'ERROR'}, _tr("3D 뷰포트에서 실행하세요"))
            return {'CANCELLED'}
        self._mouse = (event.mouse_region_x, event.mouse_region_y)
        self._handler = bpy.types.SpaceView3D.draw_handler_add(
            self._draw, (context,), 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def _draw(self, context):
        x, y = self._mouse
        shader = _shader()
        L, g = 18.0, 4.0
        pts = [(x - L, y), (x - g, y), (x + g, y), (x + L, y),
               (x, y - L), (x, y - g), (x, y + g), (x, y + L)]
        gpu.state.blend_set('ALPHA')
        gpu.state.line_width_set(2.0)
        batch = batch_for_shader(_shader(), 'LINES', {"pos": pts})
        shader.bind()
        shader.uniform_float("color", (1.0, 0.9, 0.1, 1.0))
        batch.draw(shader)
        gpu.state.line_width_set(1.0)
        gpu.state.blend_set('NONE')

    def _finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self._handler, 'WINDOW')
        context.area.tag_redraw()

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            self._mouse = (event.mouse_region_x, event.mouse_region_y)
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self._finish(context)
            s = context.scene.fskr
            rig = s.rig
            depth = rig.matrix_world @ Vector(
                (0.0, 0.0, rig.dimensions.z * 0.85))
            loc = view3d_utils.region_2d_to_location_3d(
                context.region, context.region_data, self._mouse, depth)
            s.panel_pos = loc
            s.panel_pos_set = True
            if "FP_root" in rig.pose.bones:
                rootp = rig.pose.bones["FP_root"]
                m = rootp.matrix.copy()
                m.translation = rig.matrix_world.inverted() @ loc
                rootp.matrix = m
                context.view_layer.update()
                self.report({'INFO'}, _tr("패널을 옮겼습니다"))
            else:
                self.report({'INFO'},
                            _tr("패널 위치 저장: 컨트롤러가 여기에 생성됩니다"))
            return {'FINISHED'}
        if event.type in ('RIGHTMOUSE', 'ESC'):
            self._finish(context)
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}


class FSKR_OT_sync_colors(bpy.types.Operator):
    bl_idname = "fskr.sync_colors"
    bl_label = "뷰포트 색상 다시 불러오기"
    bl_description = ("현재 뷰포트 컨트롤러의 실제 본 색상을 읽어 목록 스와치와 "
                      "메타데이터에 동기화합니다 (애드온 재설치 후 색이 어긋날 때)")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.fskr.rig is not None

    def execute(self, context):
        n = 0
        for pb in context.scene.fskr.rig.pose.bones:
            if not _is_handle_name(pb.name):
                continue
            if hasattr(pb, "color") and pb.color.palette == 'CUSTOM':
                pb["fskr_usecolor"] = 1
                pb.fskr_col = tuple(pb.color.custom.normal)
                n += 1
        self.report({'INFO'}, _tr("컨트롤러 %d개의 색상 동기화 완료") % n)
        return {'FINISHED'}


class FSKR_OT_snap_move(bpy.types.Operator):
    bl_idname = "fskr.snap_move"
    bl_label = "스냅 이동"
    bl_description = ("배치 모드에서 G로 틀을 이동합니다. "
                      "Shift를 누르는 동안 다른 틀 모서리에 스냅됩니다")
    bl_options = {'REGISTER', 'UNDO', 'GRAB_CURSOR', 'BLOCKING'}

    SNAP_DIST = 0.015  # 스냅 임계 거리 (m)

    @classmethod
    def poll(cls, context):
        s = context.scene.fskr
        return (s.rig is not None and context.area is not None
                and context.area.type == 'VIEW_3D')

    def _plane_point(self, context, event):
        area = context.area
        region = next((r for r in area.regions if r.type == 'WINDOW'), None)
        rv3d = area.spaces.active.region_3d
        if not (region and rv3d):
            return None
        coord = (event.mouse_x - region.x, event.mouse_y - region.y)
        rig = context.scene.fskr.rig
        depth = rig.matrix_world @ self.init_matrix.translation
        p = view3d_utils.region_2d_to_location_3d(region, rv3d, coord, depth)
        return None if p is None else (self.inv @ p)

    def _end(self, context):
        if getattr(self, "_dh", None) is not None:
            bpy.types.SpaceView3D.draw_handler_remove(self._dh, 'WINDOW')
            self._dh = None
        context.area.header_text_set(None)
        context.area.tag_redraw()

    def invoke(self, context, event):
        s = context.scene.fskr
        rig = s.rig
        if not s.arrange or context.mode != 'POSE':
            return {'PASS_THROUGH'}  # 조건이 아니면 일반 G로
        from .core import _vp_frame_name, _vp_frames
        ab = context.active_pose_bone
        fn9 = _vp_frame_name(rig, ab.name) if ab is not None else None
        if not fn9 or fn9 not in rig.pose.bones:
            return {'PASS_THROUGH'}
        self.fname = fn9
        pb = rig.pose.bones[self.fname]
        self.init_matrix = pb.matrix.copy()
        self.inv = rig.matrix_world.inverted()
        self.mw = rig.matrix_world.copy()
        self.R, self.Rinv = _panel_space(rig)
        self.R3 = self.R.to_3x3()
        mw3 = self.mw.to_3x3()
        self.snap_axes = (
            (mw3 @ (self.R3 @ Vector((1, 0, 0)))).normalized(),
            (mw3 @ (self.R3 @ Vector((0, 0, 1)))).normalized())

        self.my_corners = [self.Rinv @ c for c in _frame_corners(pb)]
        self.targets = []
        root9 = rig.pose.bones.get("FP_root")
        for b in _vp_frames(rig) + ([root9] if root9 else []):
            if b.name == self.fname:
                continue
            self.targets.extend(self.Rinv @ c for c in _frame_corners(b))

        self.start_mouse = self._plane_point(context, event)
        if self.start_mouse is None:
            return {'PASS_THROUGH'}
        self.start_mouse = self.Rinv @ self.start_mouse
        self.snap_pts = []
        self.hl_lines = []
        self._axis = None
        self._dh = bpy.types.SpaceView3D.draw_handler_add(
            _draw_cb, (self,), 'WINDOW', 'POST_VIEW')
        context.window_manager.modal_handler_add(self)
        context.area.header_text_set(
            _tr("이동: Ctrl=모서리 스냅, X/Y/Z=축 고정, 클릭=확정, 우클릭/ESC=취소"))
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        rig = context.scene.fskr.rig
        pb = rig.pose.bones[self.fname]

        if event.type in ('X', 'Y', 'Z') and event.value == 'PRESS':
            ax3 = event.type
            self._axis = None if self._axis == ax3 else ax3
            context.area.header_text_set(
                _tr("이동%s: Ctrl=스냅, X/Y/Z=축 고정, 클릭=확정, ESC=취소")
                % ((_tr(" [%s축]") % self._axis) if self._axis else ""))
            return {'RUNNING_MODAL'}

        if event.type == 'MOUSEMOVE':
            cur = self._plane_point(context, event)
            if cur is not None:
                cur = self.Rinv @ cur
                delta = cur - self.start_mouse
                if self._axis == 'X':
                    delta = Vector((delta.x, 0.0, 0.0))
                elif self._axis == 'Y':
                    delta = Vector((0.0, delta.y, 0.0))
                elif self._axis == 'Z':
                    delta = Vector((0.0, 0.0, delta.z))
                else:
                    delta.y = 0.0  # 기본: 패널 평면(XZ) 유지
                self.snap_pts = []
                if event.ctrl:
                    th = self.SNAP_DIST
                    # 1) 꼭짓점 스냅 (양축 동시)
                    best = None
                    bc = None
                    bd = th
                    for mc in self.my_corners:
                        mx, mz = mc.x + delta.x, mc.z + delta.z
                        for tc in self.targets:
                            dist = ((mx - tc.x) ** 2
                                    + (mz - tc.z) ** 2) ** 0.5
                            if dist < bd:
                                bd = dist
                                best = (tc.x - mc.x, tc.z - mc.z)
                                bc = tc
                    if best is not None:
                        delta.x, delta.z = best
                        self.snap_pts = [self.mw @ (self.R @ bc)]
                    else:
                        # 2) 축 정렬 스냅 (엣지 라인 맞춤)
                        bx = bz = None
                        bcx = bcz = None
                        bdx = bdz = th
                        for mc in self.my_corners:
                            for tc in self.targets:
                                dx = abs(mc.x + delta.x - tc.x)
                                if dx < bdx:
                                    bdx, bx, bcx = dx, tc.x - mc.x, tc
                                dz = abs(mc.z + delta.z - tc.z)
                                if dz < bdz:
                                    bdz, bz, bcz = dz, tc.z - mc.z, tc
                        if bx is not None:
                            delta.x = bx
                            self.snap_pts.append(
                                self.mw @ (self.R @ bcx))
                        if bz is not None:
                            delta.z = bz
                            self.snap_pts.append(
                                self.mw @ (self.R @ bcz))
                m = self.init_matrix.copy()
                m.translation = (self.init_matrix.translation
                                 + (self.R3 @ delta))
                pb.matrix = m
                context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self._end(context)
            return {'FINISHED'}
        if event.type in ('RIGHTMOUSE', 'ESC'):
            pb.matrix = self.init_matrix
            self._end(context)
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}


class FSKR_OT_arrange_toggle(bpy.types.Operator):
    bl_idname = "fskr.arrange_toggle"
    bl_label = "컨트롤러 위치 옮기기 (배치 모드)"
    bl_description = ("이 탭의 컨트롤러만 배치 모드로: 틀을 선택해 옮길 수 있습니다. "
                      "다시 누르거나 ESC/우클릭으로 끕니다")
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    scope: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, context):
        s = context.scene.fskr
        if s.rig is None:
            return {'CANCELLED'}
        self.scope = ""          # 범위 나누기는 없앰: 항상 전부
        if s.arrange and (s.arrange_scope or "") == self.scope:
            s.arrange = False
        else:
            s.arrange_scope = self.scope
            if s.arrange:
                from .core import _arrange_update
                _arrange_update(s, context)   # 범위만 바뀜 → 다시 적용
            else:
                s.arrange = True
        try:
            for a in context.screen.areas:
                if a.type == 'VIEW_3D':
                    a.tag_redraw()
        except Exception:
            pass
        return {'FINISHED'}


def arrange_button(layout, s, scope, text=None):
    """탭별 배치 모드 버튼 (그 탭의 컨트롤러만)."""
    # 어느 탭의 버튼이든 모든 컨트롤러를 함께 배치 (scope는 쓰지 않음)
    on = bool(s.arrange)
    layout.operator("fskr.arrange_toggle",
                    text=text or _tr("컨트롤러 위치 옮기기 (배치 모드)"),
                    icon='OBJECT_ORIGIN', depress=on).scope = ""


class FSKR_OT_arrange_exit(bpy.types.Operator):
    bl_idname = "fskr.arrange_exit"
    bl_label = "배치 모드 끄기"
    bl_description = "배치 모드를 끕니다 (ESC 또는 우클릭)"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        s = context.scene.fskr
        return (s.rig is not None and bool(getattr(s, "arrange", False))
                and context.mode == 'POSE'
                and context.area is not None
                and context.area.type == 'VIEW_3D')

    def execute(self, context):
        context.scene.fskr.arrange = False
        try:
            context.area.tag_redraw()
        except Exception:
            pass
        self.report({'INFO'}, _tr("배치 모드 끔"))
        return {'FINISHED'}


class FSKR_OT_edge_move(bpy.types.Operator):
    bl_idname = "fskr.edge_move"
    bl_label = "변 크기 조절"
    bl_description = ("배치 모드에서 선택된 틀의 변 화살표를 드래그해 그 변만 "
                      "이동합니다. Ctrl을 누르는 동안 다른 틀 모서리에 스냅됩니다")
    bl_options = {'REGISTER', 'UNDO', 'GRAB_CURSOR', 'BLOCKING'}

    PICK_DIST = 0.015  # 화살표를 잡을 수 있는 마우스 거리
    SNAP_DIST = 0.015  # 스냅 임계 거리

    @classmethod
    def poll(cls, context):
        s = context.scene.fskr
        return (s.rig is not None and s.arrange
                and context.area is not None
                and context.area.type == 'VIEW_3D'
                and context.mode == 'POSE')

    def _plane_point(self, context, event, depth_arm):
        area = context.area
        region = next((r for r in area.regions if r.type == 'WINDOW'), None)
        rv3d = area.spaces.active.region_3d
        if not (region and rv3d):
            return None
        coord = (event.mouse_x - region.x, event.mouse_y - region.y)
        rig = context.scene.fskr.rig
        depth = rig.matrix_world @ depth_arm
        p = view3d_utils.region_2d_to_location_3d(region, rv3d, coord, depth)
        return None if p is None else (self.inv @ p)

    def _end(self, context):
        if getattr(self, "_dh", None) is not None:
            bpy.types.SpaceView3D.draw_handler_remove(self._dh, 'WINDOW')
            self._dh = None
        context.area.header_text_set(None)
        context.area.tag_redraw()

    def _update_highlight(self, pb):
        """현재 이동 중인 변(대칭 모드면 양쪽)을 하이라이트 라인으로."""
        cs = [self.Rinv @ c for c in _frame_corners(pb)]
        vals = [c.x for c in cs] if self.axis == 'X' else [c.z for c in cs]
        lo, hi = min(vals), max(vals)
        if getattr(self, "_sym", False):
            sel = [lo, hi]
        else:
            sel = [hi if self.m0 > self.fixed else lo]
        lines = []
        for val in sel:
            if self.axis == 'X':
                pts = [c for c in cs if abs(c.x - val) < 1e-4]
            else:
                pts = [c for c in cs if abs(c.z - val) < 1e-4]
            if len(pts) >= 2:
                lines += [self.mw @ (self.R @ pts[0]),
                          self.mw @ (self.R @ pts[1])]
        self.hl_lines = lines

    def invoke(self, context, event):
        s = context.scene.fskr
        rig = s.rig
        # 배치 모드에서는 모든 컨트롤러 틀에 화살표가 있음: 누른 화살표의 틀
        # (선택된 틀이 우선)
        from .core import _vp_frame_name, _vp_resizable, _vp_frames
        ab = context.active_pose_bone
        cands = []
        fa = _vp_frame_name(rig, ab.name) if ab is not None else None
        if fa and fa in rig.pose.bones:
            cands.append(rig.pose.bones[fa])
        cands += [b for b in _vp_frames(rig) if b.name != fa]
        self.inv = rig.matrix_world.inverted()
        fname = None
        for b9 in cands:
            p9 = self._plane_point(context, event, b9.matrix.translation)
            if p9 is None:
                continue
            ar9, sz9 = _edge_arrows(b9)
            bd9 = max(sz9 * 1.5, 0.008)
            if any((p9 - ap).length < bd9 for ap, _d, _q in ar9.values()):
                fname = b9.name
                break
        if not fname:
            return {'PASS_THROUGH'}
        fb = rig.pose.bones[fname]
        if fa != fname:   # 누른 틀을 선택 (다른 틀 선택 해제)
            try:
                for pb9 in rig.pose.bones:
                    if getattr(pb9, "select", False):
                        pb9.select = False
                fb.select = True
                rig.data.bones.active = rig.data.bones[fname]
            except Exception:
                pass
        if not _vp_resizable(rig, fname):
            # 크기 고정 틀: 화살표를 잡으면 빨간색으로만 알려 주고 그대로
            self.inv = rig.matrix_world.inverted()
            p = self._plane_point(context, event, fb.matrix.translation)
            if p is None:
                return {'PASS_THROUGH'}
            arrows, size = _edge_arrows(fb)
            bd = max(size * 1.5, 0.008)
            if not any((p - ap).length < bd for ap, _d, _q in arrows.values()):
                return {'PASS_THROUGH'}
            from .core import _ARROW_BLOCK
            _ARROW_BLOCK["name"] = fname
            self.blocked = True
            context.area.header_text_set(_tr("이 컨트롤러는 크기를 바꿀 수 없습니다 "
                                             "(위치만 옮길 수 있음)"))
            context.area.tag_redraw()
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        self.blocked = False
        self.inv = rig.matrix_world.inverted()
        self.mw = rig.matrix_world.copy()
        self.R, self.Rinv = _panel_space(rig)
        self.R3 = self.R.to_3x3()
        mw3 = self.mw.to_3x3()
        self.snap_axes = (
            (mw3 @ (self.R3 @ Vector((1, 0, 0)))).normalized(),
            (mw3 @ (self.R3 @ Vector((0, 0, 1)))).normalized())
        p = self._plane_point(context, event, fb.matrix.translation)
        if p is None:
            return {'PASS_THROUGH'}

        # 화살표 히트 판정 (패널 공간에서 축 정렬로 계산)
        cs = [self.Rinv @ c for c in _frame_corners(fb)]
        x0 = min(c.x for c in cs)
        x1 = max(c.x for c in cs)
        z0 = min(c.z for c in cs)
        z1 = max(c.z for c in cs)
        edge_map = {'X1': ('X', x1, x0), 'X0': ('X', x0, x1),
                    'Z1': ('Z', z1, z0), 'Z0': ('Z', z0, z1)}
        arrows, size = _edge_arrows(fb)
        best = None
        bd = max(size * 1.5, 0.008)
        for k, (ap, _d, _pp) in arrows.items():
            d = (p - ap).length
            if d < bd:
                bd = d
                best = k
        if best is None:
            return {'PASS_THROUGH'}  # 화살표가 아니면 일반 클릭으로

        self.axis, self.m0, self.fixed = edge_map[best]
        self.fname = fname
        self.init_matrix = fb.matrix.copy()
        # 스냅 대상: 다른 틀 + 루트 바의 모서리
        from .core import _vp_frames
        root = rig.pose.bones.get("FP_root")
        frames = _vp_frames(rig)
        self.targets = []
        for b in frames + ([root] if root else []):
            if b.name == self.fname:
                continue
            self.targets.extend(self.Rinv @ c
                                for c in _frame_corners(b))

        self.snap_pts = []
        self.hl_lines = []
        self._sym = False
        self._update_highlight(fb)  # 잡은 변을 즉시 하이라이트
        self._dh = bpy.types.SpaceView3D.draw_handler_add(
            _draw_cb, (self,), 'WINDOW', 'POST_VIEW')
        context.window_manager.modal_handler_add(self)
        context.area.header_text_set(
            _tr("변 이동: 드래그=크기 조절, Ctrl=스냅, Alt=대칭 조절, "
            "놓으면 확정, ESC 취소"))
        context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if getattr(self, "blocked", False):
            if (event.type == 'LEFTMOUSE' and event.value == 'RELEASE') or \
                    event.type in ('RIGHTMOUSE', 'ESC'):
                from .core import _ARROW_BLOCK
                _ARROW_BLOCK["name"] = None
                context.area.header_text_set(None)
                context.area.tag_redraw()
                return {'CANCELLED'}
            return {'RUNNING_MODAL'}
        rig = context.scene.fskr.rig
        pb = rig.pose.bones[self.fname]

        if event.type == 'MOUSEMOVE':
            p = self._plane_point(context, event, self.init_matrix.translation)
            if p is not None:
                p = self.Rinv @ p
                m1 = p.x if self.axis == 'X' else p.z
                self.snap_pts = []
                near = min(self.targets,
                           key=lambda c: abs(m1 - (c.x if self.axis == 'X'
                                                   else c.z)),
                           default=None)
                if near is not None and event.ctrl:
                    coord = near.x if self.axis == 'X' else near.z
                    if abs(m1 - coord) < self.SNAP_DIST:
                        m1 = coord
                        self.snap_pts = [self.mw @ (self.R @ near)]
                # Alt = 중앙 기준 대칭 조절 (반대쪽 변도 함께)
                self._sym = event.alt
                anchor = ((self.m0 + self.fixed) / 2 if self._sym
                          else self.fixed)
                denom = self.m0 - anchor
                if abs(denom) > 1e-6:
                    f = (m1 - anchor) / denom
                    if f > 0.05:  # 뒤집힘/붕괴 방지
                        ci = 0 if self.axis == 'X' else 1  # 본 로컬 X / Y
                        wi = 0 if self.axis == 'X' else 2  # 패널 X / Z
                        mp = self.Rinv @ self.init_matrix
                        m = mp.copy()
                        m.col[ci] = mp.col[ci] * f
                        h = mp.translation[wi]
                        a_new = h + f * (anchor - h)
                        tr = m.translation.copy()
                        tr[wi] += anchor - a_new
                        m.translation = tr
                        pb.matrix = self.R @ m
                        self._update_highlight(pb)
                        context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            self._end(context)
            return {'FINISHED'}
        if event.type in ('RIGHTMOUSE', 'ESC'):
            pb.matrix = self.init_matrix
            self._end(context)
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}


class FSKR_OT_move_ctl(bpy.types.Operator):
    bl_idname = "fskr.move_ctl"
    bl_label = "순서 이동"
    bl_description = ("목록에서 컨트롤러 순서를 위/아래로 이동합니다 "
                      "(같은 그룹 안에서, Shift = 맨 위/맨 아래로)")
    bl_options = {'REGISTER', 'UNDO'}

    bone: bpy.props.StringProperty()
    dir: bpy.props.IntProperty(default=1)

    def invoke(self, context, event):
        if event.shift:  # Shift = 끝으로 점프
            self.dir = 9999 if self.dir > 0 else -9999
        return self.execute(context)

    def execute(self, context):
        s = context.scene.fskr
        rig = s.rig
        if not rig or self.bone not in rig.pose.bones:
            return {'CANCELLED'}
        pb = rig.pose.bones[self.bone]
        grp = str(pb.get("fskr_group", ""))
        sibs = [n for n in _sorted_ctls(rig)
                if str(rig.pose.bones[n].get("fskr_group", "")) == grp]
        i = sibs.index(self.bone)
        j = max(0, min(len(sibs) - 1, i + self.dir))
        if j != i:
            nm = sibs.pop(i)
            sibs.insert(j, nm)
        for k2, n2 in enumerate(sibs):
            rig.pose.bones[n2]["fskr_order"] = k2
        return {'FINISHED'}


class FSKR_OT_sort_visual(bpy.types.Operator):
    bl_idname = "fskr.sort_visual"
    bl_label = "배치 순서로 정렬"
    bl_description = ("뷰포트 배치 위치(위→아래, 왼쪽→오른쪽) 순서대로 "
                      "목록 순서를 자동 정렬합니다 (그룹별)")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.fskr.rig is not None

    def execute(self, context):
        s = context.scene.fskr
        rig = s.rig
        groups = {}
        for b in rig.data.bones:
            if _is_handle_name(b.name):
                grp = str(rig.pose.bones[b.name].get("fskr_group", ""))
                groups.setdefault(grp, []).append(b.name)

        def keyf(n):
            fb = rig.pose.bones.get(n + "_frame")
            cs = _frame_corners(fb if fb else rig.pose.bones[n])
            # 위젯 사각형의 시각적 중심 기준 (본 위치 편향 제거)
            cx = (min(c.x for c in cs) + max(c.x for c in cs)) / 2
            cz = (min(c.z for c in cs) + max(c.z for c in cs)) / 2
            return (-cz, cx)

        n2 = 0
        for grp, names in groups.items():
            for i, nm in enumerate(sorted(names, key=keyf)):
                rig.pose.bones[nm]["fskr_order"] = i
                n2 += 1
        _redraw_ui(context)
        self.report({'INFO'}, _tr("컨트롤러 %d개 정렬 완료") % n2)
        return {'FINISHED'}


class FSKR_OT_select_ctl(bpy.types.Operator):
    bl_idname = "fskr.select_ctl"
    bl_label = "컨트롤러 선택"
    bl_description = "뷰포트에서 이 컨트롤러를 선택합니다 (배치 모드면 틀을 선택)"
    bl_options = {'REGISTER', 'UNDO'}

    bone: bpy.props.StringProperty()

    def execute(self, context):
        s = context.scene.fskr
        rig = s.rig
        if not rig or self.bone not in rig.data.bones:
            return {'CANCELLED'}
        context.view_layer.objects.active = rig
        try:
            bpy.ops.object.mode_set(mode='POSE')
        except RuntimeError:
            return {'CANCELLED'}
        # 버전 호환 선택 (Blender 5.x는 Bone.select가 제거됨)
        try:
            bpy.ops.pose.select_all(action='DESELECT')
        except RuntimeError:
            pass
        from .core import arrange_for
        target = self.bone + "_frame" if arrange_for(s, self.bone) \
            else self.bone
        db = rig.data.bones[target]
        pbn = rig.pose.bones[target]
        for t in (db, pbn):
            if hasattr(t, "select"):
                try:
                    t.select = True
                    break
                except AttributeError:
                    continue
        try:
            rig.data.bones.active = db
        except Exception:
            pass
        return {'FINISHED'}


class FSKR_OT_remove_ctl(bpy.types.Operator):
    bl_idname = "fskr.remove_ctl"
    bl_label = "컨트롤러 삭제"
    bl_description = ("이 컨트롤러와 연결된 드라이버를 제거합니다 (셰이프 키는 "
                      "유지). 체크된 항목이 2개 이상이면 체크된 것들을 한꺼번에 "
                      "삭제합니다")
    bl_options = {'REGISTER', 'UNDO'}

    bone: bpy.props.StringProperty()

    def _targets(self, rig):
        pb = rig.pose.bones.get(self.bone)
        sel, _cats = _batch_sel(rig)
        if pb is not None and getattr(pb, "fskr_sel", False) and len(sel) >= 2:
            return sel
        return [self.bone]

    def invoke(self, context, event):
        rig = context.scene.fskr.rig
        if rig and self.bone in rig.pose.bones:
            if len(self._targets(rig)) >= 2:
                # 일괄 삭제는 실수 방지를 위해 확인창
                return context.window_manager.invoke_confirm(self, event)
        return self.execute(context)

    def execute(self, context):
        s = context.scene.fskr
        rig = s.rig
        if not rig or self.bone not in rig.data.bones:
            return {'CANCELLED'}
        targets = self._targets(rig)
        for b in targets:
            _remove_drivers_for_bone(s.mesh, b, rig)
            _remove_bone_drivers_for(rig, b)
            for p in ('pose.bones["%s"].scale' % b,
                      'pose.bones["%s"].scale' % (b + "_snap"),
                      'pose.bones["%s"].scale' % (b + "_thr"),
                      'pose.bones["%s"].custom_shape_scale_xyz'
                      % (b + "_frame")):
                try:
                    rig.driver_remove(p)
                except Exception:
                    pass
            lbl = bpy.data.objects.get("FPLBL_" + b)
            if lbl:
                bpy.data.objects.remove(lbl)
        _to_object_mode(context, rig)
        bpy.ops.object.mode_set(mode='EDIT')
        eb = rig.data.edit_bones
        for b in targets:
            for suffix in ("", "_frame", "_snap", "_thr"):
                n = b + suffix
                try:
                    rig.data.driver_remove('bones["%s"].hide' % n)
                except Exception:
                    pass
                if n in eb:
                    eb.remove(eb[n])
        bpy.ops.object.mode_set(mode='OBJECT')
        _invalidate_ui_cache()
        if len(targets) > 1:
            self.report({'INFO'}, _tr("컨트롤러 %d개 삭제") % len(targets))
        return {'FINISHED'}


class FSKR_OT_remove_all(bpy.types.Operator):
    bl_idname = "fskr.remove_all"
    bl_label = "패널 전체 제거"
    bl_description = "모든 컨트롤러/라벨/위젯과 셰이프 키 드라이버를 제거합니다"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.fskr.rig is not None

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        s = context.scene.fskr
        rig = s.rig
        # 이 리그의 패널이 걸어둔 셰이프 키 드라이버만 제거 (모든 메시)
        for kd in bpy.data.shape_keys:
            ad0 = kd.animation_data
            if not ad0:
                continue
            for fc in list(ad0.drivers):
                if any(any(t.id == rig
                           and str(t.bone_target).startswith("FP_")
                           for t in var.targets)
                       for var in fc.driver.variables):
                    ad0.drivers.remove(fc)
        _to_object_mode(context, rig)
        bpy.ops.object.mode_set(mode='EDIT')
        eb = rig.data.edit_bones
        for b in [b for b in eb if b.name.startswith("FP_")]:
            eb.remove(b)
        bpy.ops.object.mode_set(mode='OBJECT')
        # 이 리그에 부모된 라벨만 제거 (다른 캐릭터 라벨 보호)
        for ob in [o for o in bpy.data.objects
                   if (o.name.startswith("FPLBL")
                       or o.name.startswith("FPSPR_")) and o.parent is rig]:
            bpy.data.objects.remove(ob)
        # 위젯은 다른 패널이 남아 있으면 공유 중이므로 유지
        other9 = any(o.type == 'ARMATURE' and o is not rig
                     and "FP_root" in o.data.bones
                     for o in bpy.data.objects)
        if not other9:
            for ob in [o for o in bpy.data.objects
                       if o.name.startswith("WGT_FP")]:
                bpy.data.objects.remove(ob)
            coll = bpy.data.collections.get("FP_Widgets")
            if coll:
                bpy.data.collections.remove(coll)
        # 리그에 남은 스냅 표시용/본 패드 드라이버 정리 (모든 아마추어)
        for ob2 in bpy.data.objects:
            if ob2.type != 'ARMATURE':
                continue
            ad = ob2.animation_data
            if not ad:
                continue
            for fc in list(ad.drivers):
                if ob2 is rig and "FP_ctl" in fc.data_path:
                    ad.drivers.remove(fc)
                elif any(any(t.id == rig
                             and str(t.bone_target).startswith("FP_ctl")
                             for t in var.targets)
                         for var in fc.driver.variables):
                    ad.drivers.remove(fc)
        # 아마추어 데이터에 남은 숨김 드라이버 정리
        ad2 = rig.data.animation_data
        if ad2:
            for fc in list(ad2.drivers):
                if 'bones["FP_' in fc.data_path:
                    ad2.drivers.remove(fc)
        _invalidate_ui_cache()
        self.report({'INFO'}, _tr("표정 패널 제거 완료"))
        return {'FINISHED'}


class FSKR_OT_char_export(bpy.types.Operator):
    bl_idname = "fskr.char_export"
    bl_label = "캐릭터 이동 준비"
    bl_description = ("씬 설정(컬렉션/프리셋/모캡/립싱크/라벨)을 리그에 "
                      "저장합니다. 다른 파일에서 리그와 메시를 Append 한 뒤 "
                      "'캐릭터 가져오기'로 복구하세요. 파일 저장 시 자동 "
                      "갱신됩니다")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.fskr.rig is not None

    def execute(self, context):
        snap = _char_snapshot(context.scene)
        if snap is None:
            self.report({'ERROR'}, _tr("리그가 설정되지 않았습니다"))
            return {'CANCELLED'}
        self.report({'INFO'},
                    _tr("캐릭터 설정을 리그에 저장했습니다 (라벨 %d개 포함)")
                    % len(snap.get("labels", [])))
        return {'FINISHED'}


class FSKR_OT_char_import(bpy.types.Operator):
    bl_idname = "fskr.char_import"
    bl_label = "캐릭터 가져오기"
    bl_description = ("Append 한 리그에서 캐릭터 설정을 복구합니다. "
                      "컨트롤러는 새로 만들지 않고 기존 본의 설정을 "
                      "그대로 사용합니다")
    bl_options = {'REGISTER', 'UNDO'}

    trig: bpy.props.EnumProperty(name="가져온 리그", items=_armature_items)
    scene_only: bpy.props.BoolProperty(
        name="씬 설정만 복구", default=False,
        description="패널 리로드와 라벨 재생성 없이 컬렉션/프리셋/모캡/"
                    "립싱크 설정만 복구합니다")

    def invoke(self, context, event):
        ao = context.active_object
        if ao and ao.type == 'ARMATURE' and ao.get("fskr_char"):
            try:
                self.trig = ao.name
            except TypeError:
                pass
        else:  # 스냅샷 있는 아마추어를 기본값으로
            for ob in bpy.data.objects:
                if ob.type == 'ARMATURE' and ob.get("fskr_char"):
                    try:
                        self.trig = ob.name
                    except TypeError:
                        pass
                    break
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        rig = bpy.data.objects.get(self.trig)
        raw = str(rig.get("fskr_char", "")) if rig is not None else ""
        if not raw:
            self.report({'ERROR'},
                        _tr("이 리그에는 캐릭터 스냅샷이 없습니다. 원본 "
                            "파일에서 '캐릭터 이동 준비'를 먼저 실행하세요"))
            return {'CANCELLED'}
        try:
            snap = json.loads(raw)
        except Exception:
            self.report({'ERROR'},
                        _tr("이 리그에는 캐릭터 스냅샷이 없습니다. 원본 "
                            "파일에서 '캐릭터 이동 준비'를 먼저 실행하세요"))
            return {'CANCELLED'}
        s = context.scene.fskr
        st = snap.get("settings", {})
        # 포인터: 리그는 선택한 것, 메시/목 리그는 이름 재해석
        # (리그 변경 콜백이 스냅샷을 덮어쓰지 않게 잠시 막음)
        from .core import _SWITCH
        _SWITCH["busy"] = True
        try:
            s.rig = rig
        finally:
            _SWITCH["busy"] = False
        _SWITCH["rig"] = rig.name
        mn = st.get("mesh")
        if isinstance(mn, str) and mn.startswith("@id:"):
            mo = _resolve_mesh_name(mn[4:], rig)
            if mo is not None:
                s.mesh = mo
        _pg_restore(s, st, skip=("rig", "mesh", "mocap_head_rig",
                                 "arrange"))
        hn = st.get("mocap_head_rig")
        if isinstance(hn, str) and hn.startswith("@id:"):
            ho = bpy.data.objects.get(hn[4:])
            if ho is None:  # 접미사 밀림 대응
                base9 = hn[4:].rsplit(".", 1)[0]
                for ob9 in bpy.data.objects:
                    if (ob9.type == 'ARMATURE'
                            and ob9.name.rsplit(".", 1)[0] == base9):
                        ho = ob9
                        break
            if ho is not None and ho.type == 'ARMATURE':
                s.mocap_head_rig = ho
        made = 0
        if not self.scene_only:
            # 라벨 재생성 (이 리그의 기존 라벨은 정리 후)
            for ob in [o for o in bpy.data.objects
                       if o.name.startswith("FPLBL") and o.parent is rig]:
                bpy.data.objects.remove(ob)
            for li in snap.get("labels", []):
                cu = bpy.data.curves.new("FPLBL_txt", 'FONT')
                cu.body = str(li.get("body", ""))
                cu.size = float(li.get("size", 0.02))
                cu.align_x = 'CENTER'
                cu.align_y = 'CENTER'
                col4 = (list(li.get("color", [1, 1, 1, 1])) + [1.0])[:4]
                mat = bpy.data.materials.new("FPLBL_mat")
                mat.use_nodes = False
                mat.diffuse_color = col4
                cu.materials.append(mat)
                ob = bpy.data.objects.new("FPLBL_txt", cu)
                ob.color = col4
                context.scene.collection.objects.link(ob)
                ob.parent = rig
                ob.parent_type = 'BONE'
                ob.parent_bone = str(li.get("bone", "FP_root"))
                context.view_layer.update()
                vals = li.get("matrix")
                if vals and len(vals) == 16:
                    m9 = Matrix([vals[0:4], vals[4:8],
                                 vals[8:12], vals[12:16]])
                    ob.matrix_world = rig.matrix_world @ m9
                ob.hide_viewport = not s.labels_visible
                _text_toggle_driver(context.scene, rig, ob)
                made += 1
            # 기존 본 재사용 리로드 (머지) — 새 컨트롤러 생성 없음
            try:
                bpy.ops.fskr.reload_panel()
            except Exception:
                pass
        _invalidate_ui_cache()
        self.report({'INFO'},
                    _tr("캐릭터 가져오기 완료 (라벨 %d개 재생성)") % made)
        return {'FINISHED'}


class FSKR_OT_save_default(bpy.types.Operator):
    bl_idname = "fskr.save_default"
    bl_label = "현재 값을 기본값으로 저장"
    bl_description = ("지금의 컨트롤러 위치들을 기본 표정으로 저장합니다. "
                      "'기본값으로 되돌리기'가 이 상태로 복원합니다")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.fskr.rig is not None

    def execute(self, context):
        n = 0
        for pb in context.scene.fskr.rig.pose.bones:
            if _is_handle_name(pb.name):
                pb["fskr_def"] = [pb.location[0], pb.location[1]]
                n += 1
        atlas_save_default(context.scene.fskr)
        self.report({'INFO'}, _tr("컨트롤러 %d개의 기본값 저장 완료") % n)
        return {'FINISHED'}


class FSKR_OT_reset_all(bpy.types.Operator):
    bl_idname = "fskr.reset_all"
    bl_label = "기본값으로 되돌리기"
    bl_description = ("모든 컨트롤러를 저장된 기본값으로 되돌립니다. "
                      "저장된 기본값이 없으면 0으로 (키프레임은 지우지 않음)")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.fskr.rig is not None

    def execute(self, context):
        for pb in context.scene.fskr.rig.pose.bones:
            if _is_handle_name(pb.name):
                d = pb.get("fskr_def", None)
                if d is not None and len(d) >= 2:
                    pb.location = (d[0], d[1], 0.0)
                else:
                    pb.location = (0.0, 0.0, 0.0)
        atlas_reset(context.scene.fskr)
        context.view_layer.update()
        return {'FINISHED'}


class FSKR_OT_key_all(bpy.types.Operator):
    bl_idname = "fskr.key_all"
    bl_label = "표정 전체 키프레임"
    bl_description = "현재 프레임에 모든 컨트롤러의 키프레임을 삽입합니다"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.fskr.rig is not None

    def execute(self, context):
        n = 0
        for pb in context.scene.fskr.rig.pose.bones:
            if _is_handle_name(pb.name):
                pb.keyframe_insert("location",
                                   group=str(pb.get("fskr_label", pb.name)))
                n += 1
        n += atlas_key_all(context.scene.fskr)
        self.report({'INFO'}, _tr("컨트롤러 %d개에 키프레임 삽입") % n)
        return {'FINISHED'}


class FSKR_OT_mocap_start(bpy.types.Operator):
    bl_idname = "fskr.mocap_start"
    bl_label = "연결 시작"
    bl_description = ("iFacialMocap 수신을 시작합니다. 아이폰과 PC가 같은 "
                      "와이파이에 있어야 하며, 앱이 켜져 있어야 합니다")
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.scene.fskr.rig is not None

    def execute(self, context):
        import socket as sk
        s = context.scene.fskr
        ip = s.mocap_ip.strip()
        if not ip:
            self.report({'ERROR'}, _tr("아이폰 IP를 입력하세요 (앱 화면에 표시됨)"))
            return {'CANCELLED'}
        _mocap_stop_sock()
        try:
            sock = sk.socket(sk.AF_INET, sk.SOCK_DGRAM)
            sock.setsockopt(sk.SOL_SOCKET, sk.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", 49983))
            sock.setblocking(False)
        except OSError as e:
            self.report({'ERROR'}, _tr("포트 49983 열기 실패: %s") % e)
            return {'CANCELLED'}
        _MOCAP.update({"sock": sock, "ip": ip, "vals": {},
                       "err": "", "hs": 0, "ok": False, "cvals": {}})
        # 저장된 캘리브레이션 불러오기
        try:
            d0 = json.loads(s.mocap_neutral) if s.mocap_neutral else {}
            _MOCAP["neutral"] = d0.get("v") or {}
            _MOCAP["neutral_head"] = d0.get("h")
            _MOCAP["neutral_eyes"] = d0.get("e")
        except Exception:
            _MOCAP["neutral"] = {}
            _MOCAP["neutral_head"] = None
            _MOCAP["neutral_eyes"] = None
        _mocap_handshake()
        try:
            bpy.app.timers.register(_mocap_tick, first_interval=0.05)
        except Exception:
            pass
        self.report({'INFO'}, _tr("iFacialMocap 수신 시작 (포트 49983)"))
        return {'FINISHED'}


class FSKR_OT_mocap_stop(bpy.types.Operator):
    bl_idname = "fskr.mocap_stop"
    bl_label = "중지"
    bl_description = "iFacialMocap 수신을 중지합니다"
    bl_options = {'REGISTER'}

    def execute(self, context):
        _mocap_stop_sock()
        self.report({'INFO'}, _tr("iFacialMocap 수신 중지"))
        return {'FINISHED'}


class FSKR_OT_mocap_rec_start(bpy.types.Operator):
    bl_idname = "fskr.mocap_rec_start"
    bl_label = "녹화 시작"
    bl_description = ("시작 프레임으로 이동해 카운트다운 후 재생과 녹화를 "
                      "시작합니다. 다시 누르면 취소/정지되고, End Frame에 "
                      "도달하면 자동으로 멈춥니다")
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return _MOCAP.get("sock") is not None

    def execute(self, context):
        s = context.scene.fskr
        if _MOCAP.get("cd_end"):
            _MOCAP["cd_end"] = None
            self.report({'INFO'}, _tr("카운트다운 취소"))
            return {'FINISHED'}
        try:
            playing = bool(context.screen
                           and context.screen.is_animation_playing)
        except Exception:
            playing = False
        if playing:
            _stop_playback()
            s.mocap_record = False
            self.report({'INFO'}, _tr("녹화 정지"))
            return {'FINISHED'}
        try:
            bk9 = json.loads(s.lipsync_baked or "[]")
            if len(bk9) == 2:
                b0, b1 = int(bk9[0]), int(bk9[0]) + int(bk9[1]) - 1
                if (b0 <= context.scene.frame_end
                        and b1 >= context.scene.frame_start):
                    self.report({'WARNING'},
                                _tr("립싱크 키 구간과 겹칩니다. 녹화가 립싱크 "
                                "키를 덮어쓸 수 있습니다"))
        except Exception:
            pass
        context.scene.frame_current = context.scene.frame_start
        s.mocap_record = True
        cd = float(s.mocap_countdown)
        if cd > 0.0:
            _MOCAP["cd_end"] = time.monotonic() + cd
            try:
                bpy.app.timers.register(_cd_tick, first_interval=0.05)
            except Exception:
                pass
            self.report({'INFO'}, _tr("%d초 후 녹화 시작") % round(cd))
        else:
            _start_playback()
            self.report({'INFO'}, _tr("녹화 시작"))
        return {'FINISHED'}


class FSKR_OT_mocap_calibrate(bpy.types.Operator):
    bl_idname = "fskr.mocap_calibrate"
    bl_label = "Calibrate (중립 캡처)"
    bl_description = ("무표정으로 카메라를 정면으로 본 상태에서 누르세요. "
                      "지금 값을 기준(0)으로 저장해서 이후 수신값을 "
                      "보정합니다. 씬에 저장되어 다음에도 유지됩니다")
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return _MOCAP.get("sock") is not None

    def execute(self, context):
        s = context.scene.fskr
        vals = dict(_MOCAP.get("vals") or {})
        if not vals:
            self.report({'ERROR'}, _tr("수신된 데이터가 없습니다"))
            return {'CANCELLED'}
        _MOCAP["neutral"] = vals
        hd = _MOCAP.get("head")
        _MOCAP["neutral_head"] = list(hd) if hd else None
        pts9 = [e for e in (_MOCAP.get("eyeL"), _MOCAP.get("eyeR")) if e]
        _MOCAP["neutral_eyes"] = (
            [sum(p[0] for p in pts9) / len(pts9),
             sum(p[1] for p in pts9) / len(pts9)] if pts9 else None)
        s.mocap_neutral = json.dumps(
            {"v": vals, "h": _MOCAP["neutral_head"],
             "e": _MOCAP["neutral_eyes"]})
        self.report({'INFO'}, _tr("캘리브레이션 완료: 지금 표정이 기준이 됩니다"))
        return {'FINISHED'}


class FSKR_OT_mocap_cal_clear(bpy.types.Operator):
    bl_idname = "fskr.mocap_cal_clear"
    bl_label = "보정 해제"
    bl_description = "캘리브레이션 보정을 지우고 원본 수신값을 사용합니다"
    bl_options = {'REGISTER'}

    def execute(self, context):
        _MOCAP["neutral"] = {}
        _MOCAP["neutral_head"] = None
        _MOCAP["neutral_eyes"] = None
        context.scene.fskr.mocap_neutral = ""
        self.report({'INFO'}, _tr("캘리브레이션 해제"))
        return {'FINISHED'}


class FSKR_OT_mocap_automap(bpy.types.Operator):
    bl_idname = "fskr.mocap_automap"
    bl_label = "자동 매핑"
    bl_description = ("셰이프 키 이름과 ARKit 이름을 비교해 매핑을 자동으로 "
                      "채웁니다 (기존 매핑은 교체). 눈동자 패드 등은 수동으로 "
                      "추가하세요")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.fskr.rig is not None

    def execute(self, context):
        s = context.scene.fskr
        rig = s.rig
        s.mocap_map.clear()
        n = 0
        for cn in _sorted_ctls(rig):
            pb = rig.pose.bones[cn]
            if str(pb.get("fskr_type", "")) not in ('SLD_H', 'SLD_V'):
                continue
            keynm = str(pb.get("fskr_key", NONE))
            if keynm == NONE:
                continue
            kt = _name_tokens(keynm)
            best, bs = None, 0.0
            for an in _ARKIT:
                at = _name_tokens(an)
                sc = len(at & kt) / len(at)
                if sc > bs:
                    bs, best = sc, an
            if best and bs >= 0.99:
                it = s.mocap_map.add()
                it.arkit = best
                try:
                    it.ctl = cn
                except TypeError:
                    pass
                n += 1
        _redraw_ui(context)
        self.report({'INFO'}, _tr("자동 매핑 %d개 (나머지는 +로 수동 추가)") % n)
        return {'FINISHED'}


class FSKR_OT_mocap_wizard(bpy.types.Operator):
    bl_idname = "fskr.mocap_wizard"
    bl_label = "간단 자동 설정"
    bl_description = ("컨트롤러마다 역할(눈 감기/눈썹/입 모음/눈동자)을 "
                      "고르면 ARKit 매핑을 자동으로 만들어 줍니다. "
                      "이름으로 미리 추측해서 채워둡니다")
    bl_options = {'REGISTER', 'UNDO'}

    roles: bpy.props.CollectionProperty(type=FSKR_WizRoleItem)

    @classmethod
    def poll(cls, context):
        return context.scene.fskr.rig is not None

    def invoke(self, context, event):
        rig = context.scene.fskr.rig
        self.roles.clear()
        taken = set()
        for cn in _sorted_ctls(rig):
            pb = rig.pose.bones[cn]
            ctype = str(pb.get("fskr_type", 'SLD_H'))
            if ctype not in ('SLD_H', 'SLD_V', 'BONE', 'PAD'):
                continue
            it = self.roles.add()
            it.bone = cn
            it.label = str(pb.get("fskr_label", cn))
            it.ctype = ('BONE' if ctype == 'BONE'
                        else ('PAD' if ctype == 'PAD' else 'SLD'))
            toks = _name_tokens(it.label + " "
                                + str(pb.get("fskr_key", ""))
                                + " " + str(pb.get("fskr_tb1", "")))
            role = "__NONE__"
            if it.ctype == 'PAD':
                # 슬롯에 모음 키가 있으면 입 패드로 추측 + 내용 표시
                vws = []
                for sl in _SLOT_ORDER:
                    k = str(pb.get("fskr_" + sl, NONE))
                    if k == NONE:
                        continue
                    for vw in ("a", "e", "i", "o", "u"):
                        if vw in _name_tokens(k) and vw.upper() not in vws:
                            vws.append(vw.upper())
                if vws:
                    role = 'M_PAD'
                    it.label += _tr(" (%s 패드)") % "/".join(vws)
                else:
                    it.label += _tr(" (패드)")
            elif it.ctype == 'BONE':
                if "left" in toks:
                    role = 'PAD_L'
                elif "right" in toks:
                    role = 'PAD_R'
            elif {"eye", "blink", "left"} <= toks:
                role = 'EYE_L'
            elif {"eye", "blink", "right"} <= toks:
                role = 'EYE_R'
            elif {"brow", "left"} <= toks:
                role = 'BROW_L'
            elif {"brow", "right"} <= toks:
                role = 'BROW_R'
            else:
                for vw, rl in (("a", 'M_A'), ("i", 'M_I'), ("u", 'M_U'),
                               ("e", 'M_E'), ("o", 'M_O')):
                    if vw in toks:
                        role = rl
                        break
            if role != "__NONE__" and role in taken:
                role = "__NONE__"  # 같은 역할 중복 방지
            if role != "__NONE__":
                taken.add(role)
            try:
                it.role = role
            except TypeError:
                pass
        return context.window_manager.invoke_props_dialog(self, width=360)

    def draw(self, context):
        col = self.layout.column(align=True)
        col.label(text=_tr("컨트롤러마다 역할을 고르세요"), icon='PRESET')
        for it in self.roles:
            r = col.row(align=True)
            if it.ctype == 'BONE':
                ic = 'ORIENTATION_GIMBAL'
            elif it.ctype == 'PAD':
                ic = 'MESH_PLANE'
            else:
                ic = 'IPO_LINEAR'
            r.label(text=it.label, icon=ic)
            sub = r.row(align=True)
            sub.ui_units_x = 7.5
            sub.prop(it, "role", text="")

    def execute(self, context):
        s = context.scene.fskr
        s.mocap_map.clear()
        rmap = {}
        for it in self.roles:
            if it.role != "__NONE__":
                rmap[it.role] = it.bone

        def add(ak, role, comp='VAL', f=1.0):
            ctl = rmap.get(role)
            if not ctl:
                return 0
            it = s.mocap_map.add()
            it.arkit = ak
            try:
                it.ctl = ctl
            except TypeError:
                s.mocap_map.remove(len(s.mocap_map) - 1)
                return 0
            it.comp = comp
            it.factor = f
            return 1

        n = 0
        n += add("eyeBlinkLeft", 'EYE_L')
        n += add("eyeBlinkRight", 'EYE_R')
        # 눈썹: 올리면 +, 내리면(찌푸림) − (양방향 슬라이더 기준)
        n += add("browOuterUpLeft", 'BROW_L')
        n += add("browDownLeft", 'BROW_L', 'VALN')
        n += add("browOuterUpRight", 'BROW_R')
        n += add("browDownRight", 'BROW_R', 'VALN')
        for ak, rl in (('_A', 'M_A'), ('_I', 'M_I'), ('_U', 'M_U'),
                       ('_E', 'M_E'), ('_O', 'M_O')):
            n += add(ak, rl)
        # 눈동자: 패드 X+ = 오른쪽 보기 기준 (방향이 반대면 배율을 음수로)
        n += add("eyeLookInLeft", 'PAD_L', 'XP')
        n += add("eyeLookOutLeft", 'PAD_L', 'XN')
        n += add("eyeLookUpLeft", 'PAD_L', 'YP')
        n += add("eyeLookDownLeft", 'PAD_L', 'YN')
        n += add("eyeLookOutRight", 'PAD_R', 'XP')
        n += add("eyeLookInRight", 'PAD_R', 'XN')
        n += add("eyeLookUpRight", 'PAD_R', 'YP')
        n += add("eyeLookDownRight", 'PAD_R', 'YN')
        # 입 패드: 슬롯에 연결된 모음 키의 방향으로 자동 매핑
        pad_b = rmap.get('M_PAD')
        rig = s.rig
        if pad_b and rig and pad_b in rig.pose.bones:
            pb2 = rig.pose.bones[pad_b]
            # 대각 슬롯도 두 축 모두 1.0: 값 1이면 핸들이 코너까지 가서
            # 쌍선형 가중치가 정확히 1이 됨
            slot_comp = {"up": (("YP", 1.0),), "down": (("YN", 1.0),),
                         "left": (("XN", 1.0),), "right": (("XP", 1.0),),
                         "ul": (("XN", 1.0), ("YP", 1.0)),
                         "ur": (("XP", 1.0), ("YP", 1.0)),
                         "dl": (("XN", 1.0), ("YN", 1.0)),
                         "dr": (("XP", 1.0), ("YN", 1.0))}
            vw_ch = {"a": '_A', "i": '_I', "u": '_U',
                     "e": '_E', "o": '_O'}
            seen9 = set()
            for slot, comps in slot_comp.items():
                k = str(pb2.get("fskr_" + slot, NONE))
                if k == NONE:
                    continue
                toks9 = _name_tokens(k)
                ch = next((vw_ch[vw] for vw in vw_ch if vw in toks9),
                          None)
                if ch is None:
                    continue
                for comp, f in comps:
                    if (ch, comp) in seen9:
                        continue
                    seen9.add((ch, comp))
                    it2 = s.mocap_map.add()
                    it2.arkit = ch
                    try:
                        it2.ctl = pad_b
                    except TypeError:
                        s.mocap_map.remove(len(s.mocap_map) - 1)
                        continue
                    it2.comp = comp
                    it2.factor = f
                    n += 1
        _redraw_ui(context)
        self.report({'INFO'}, _tr("매핑 %d개 생성 완료") % n)
        return {'FINISHED'}


class FSKR_OT_mocap_preset_key(bpy.types.Operator):
    bl_idname = "fskr.mocap_preset_key"
    bl_label = "캡처 중 프리셋 적용"
    bl_description = ("iFacialMocap 캡처 중 숫자키로 표정 프리셋을 적용합니다 "
                      "(1~9 = 프리셋 순번, 0 = 기본 표정). 캡처 중이 아니면 "
                      "숫자키는 원래 기능대로 동작합니다")
    bl_options = {'REGISTER', 'UNDO'}

    idx: bpy.props.IntProperty(default=1)

    def invoke(self, context, event):
        s = getattr(context.scene, "fskr", None)
        if _MOCAP.get("sock") is None or s is None or s.rig is None:
            return {'PASS_THROUGH'}  # 캡처 중이 아닐 땐 기본 동작 유지
        return self.execute(context)

    def execute(self, context):
        s = context.scene.fskr
        rig = s.rig
        if not rig:
            return {'CANCELLED'}
        rec = bool(s.mocap_record)
        playing = False
        if rec:
            try:
                playing = bool(context.screen
                               and context.screen.is_animation_playing)
            except Exception:
                playing = False
        if self.idx == 0:
            targets = {}
            for pb in rig.pose.bones:
                if _is_handle_name(pb.name):
                    d = pb.get("fskr_def", None)
                    if d is not None and len(d) >= 2:
                        targets[pb.name] = (float(d[0]), float(d[1]))
                    else:
                        targets[pb.name] = (0.0, 0.0)
            _MOCAP["preset_cur"] = None
            _preset_blend_start(rig, targets, float(s.mocap_blend))
            atlas_reset(s, key=(rec and playing))
            self.report({'INFO'}, _tr("기본 표정으로"))
            return {'FINISHED'}
        if _MOCAP.get("preset_cur") == self.idx:
            # 같은 프리셋을 다시 누르면 기본 표정으로 복귀 (토글)
            targets = {}
            for pb in rig.pose.bones:
                if _is_handle_name(pb.name):
                    d = pb.get("fskr_def", None)
                    if d is not None and len(d) >= 2:
                        targets[pb.name] = (float(d[0]), float(d[1]))
                    else:
                        targets[pb.name] = (0.0, 0.0)
            _MOCAP["preset_cur"] = None
            _preset_blend_start(rig, targets, float(s.mocap_blend))
            atlas_reset(s, key=(rec and playing))
            self.report({'INFO'}, _tr("기본 표정으로"))
            return {'FINISHED'}
        i = self.idx - 1
        if i >= len(s.presets):
            self.report({'WARNING'}, _tr("프리셋 %d번이 없습니다") % self.idx)
            return {'CANCELLED'}
        p = s.presets[i]
        try:
            vals = json.loads(p.data)
        except Exception:
            return {'CANCELLED'}
        targets = {}
        for pb in rig.pose.bones:
            if _is_handle_name(pb.name):
                lbl = str(pb.get("fskr_label", pb.name))
                if lbl in vals:
                    v = vals[lbl]
                    targets[pb.name] = (float(v[0]), float(v[1]))
        _MOCAP["preset_cur"] = self.idx
        _preset_blend_start(rig, targets, float(s.mocap_blend))
        atlas_apply(s, vals.get("__atlas__", {}), key=(rec and playing))
        self.report({'INFO'}, _tr("프리셋 적용: ") + p.name)
        return {'FINISHED'}


class FSKR_OT_lipsync_seek(bpy.types.Operator):
    bl_idname = "fskr.lipsync_seek"
    bl_label = "구간으로 이동"
    bl_description = "이 구간의 시작 프레임으로 이동합니다"
    bl_options = {'INTERNAL'}

    idx: bpy.props.IntProperty()

    def execute(self, context):
        s = context.scene.fskr
        if 0 <= self.idx < len(s.lipsync_segs):
            s.lipsync_idx = self.idx
            context.scene.frame_current = s.lipsync_segs[self.idx].fs
        return {'FINISHED'}


class FSKR_OT_lipsync_edit(bpy.types.Operator):
    bl_idname = "fskr.lipsync_edit"
    bl_label = "립싱크 편집기 열기"
    bl_description = ("브라우저에 전용 립싱크 편집기를 엽니다. 파형과 모음 "
                      "구간을 보며 구간을 클릭해 A/I/U/E/O를 바꾸고, 적용을 "
                      "누르면 Blender에 다시 굽습니다")
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        s = context.scene.fskr
        return s.rig is not None and len(s.lipsync_segs) > 0

    def execute(self, context):
        s = context.scene.fskr
        try:
            opens = json.loads(s.lipsync_open or "[]")
        except Exception:
            opens = []
        if not opens:
            self.report({'ERROR'}, _tr("립싱크 데이터가 없습니다"))
            return {'CANCELLED'}
        scene = context.scene
        if _lipsync_resample(s, scene):
            try:
                bpy.ops.fskr.lipsync_apply(refresh=False)
            except Exception:
                pass
            try:
                opens = json.loads(s.lipsync_open or "[]")
            except Exception:
                opens = []
            self.report({'INFO'},
                        _tr("프레임 레이트 변경 감지: 립싱크를 새 프레임 "
                            "레이트에 맞춰 재배치했습니다"))
        fps = scene.render.fps / scene.render.fps_base
        _lipsync_sync_off()  # 이전 세션의 재생 동기 상태 정리
        pad_pb9, vmap9 = _lipsync_padinfo(s, s.rig)
        pmm9 = {}
        if pad_pb9 is not None:
            gm9 = float(pad_pb9.get("fskr_pmul", 1.0))
            for sl9c, js9c in (("up", "U"), ("down", "D"),
                               ("left", "L"), ("right", "R"),
                               ("ul", "UL"), ("ur", "UR"),
                               ("dl", "DL"), ("dr", "DR")):
                pmm9[js9c] = round(gm9 * float(
                    pad_pb9.get("fskr_pm_" + sl9c, 1.0)), 6)
        try:
            favs9 = json.loads(s.lipsync_favs or "[]")
        except Exception:
            favs9 = []
        try:
            clus9 = json.loads(s.lipsync_clus or "[]")
        except Exception:
            clus9 = []
        init = {"opens": opens, "start": int(s.lipsync_start), "fps": fps,
                "clus": clus9, "cgap": int(s.lipsync_mk_gap),
                "favs": favs9, "blend": int(s.lipsync_blend),
                "pmul": pmm9,
                "haspad": (pad_pb9 is not None
                           and not getattr(s, "lipsync_sprite", False)),
                "sprite": bool(getattr(s, "lipsync_sprite", False)),
                "seqn": atlas_seq_names(s),
                "seqr": json.loads(getattr(s, "lipsync_seqr", "[]") or "[]"),
                "lvn": {"_U": _tr("닫힘"), "_E": _tr("반"),
                        "_A": _tr("열림")},
                "snap": (float(pad_pb9.get("fskr_snap", 0.0))
                         if pad_pb9 is not None else 0.0),
                "vmap": {k9: [round(v9[0], 4), round(v9[1], 4)]
                         for k9, v9 in vmap9.items()},
                "segs": [{"fs": int(it.fs), "fe": int(it.fe),
                          "v": it.vowel, "px": float(it.px),
                          "py": float(it.py)} for it in s.lipsync_segs]}
        with _LIPSRV["lock"]:
            _LIPSRV["init"] = json.dumps(init)
            _LIPSRV["html"] = _lipsync_html()
        if _LIPSRV.get("srv") is None:
            try:
                srv = ThreadingHTTPServer(("127.0.0.1", 0),
                                          _LipsyncHTTPHandler)
            except Exception as e:
                self.report({'ERROR'}, str(e))
                return {'CANCELLED'}
            _LIPSRV["srv"] = srv
            _LIPSRV["port"] = srv.server_address[1]
            th = threading.Thread(target=srv.serve_forever, daemon=True)
            th.start()
            _LIPSRV["thread"] = th
            try:
                bpy.app.timers.register(_lipsrv_tick, first_interval=0.1)
            except Exception:
                pass
        # 오디오 파일 로드 (브라우저 재생용)
        import os as _os
        ap = str(getattr(s, "lipsync_audio", ""))
        if not ap or not _os.path.exists(bpy.path.abspath(ap)):
            # 구버전 씬: 시퀀서의 립싱크 사운드 스트립에서 경로 회수
            try:
                se9 = scene.sequence_editor
                coll9 = (getattr(se9, "sequences", None)
                         or getattr(se9, "strips", None)) if se9 else None
                for st9 in (coll9 or []):
                    if (st9.name.startswith("FSKR_lipsync")
                            and getattr(st9, "sound", None)):
                        ap = bpy.path.abspath(st9.sound.filepath)
                        s.lipsync_audio = ap
                        break
            except Exception:
                pass
        else:
            ap = bpy.path.abspath(ap)
        audio = b""
        mime = "application/octet-stream"
        if ap and _os.path.exists(ap):
            try:
                with open(ap, "rb") as f9:
                    audio = f9.read()
                ext9 = ap.lower().rsplit(".", 1)[-1]
                mime = {"wav": "audio/wav", "mp3": "audio/mpeg",
                        "ogg": "audio/ogg", "flac": "audio/flac",
                        "m4a": "audio/mp4",
                        "aac": "audio/aac"}.get(ext9,
                                                "application/octet-stream")
            except Exception:
                audio = b""
        init["has_audio"] = bool(audio)
        init["hist"], init["hidx"] = _lipsync_hist_json()
        with _LIPSRV["lock"]:
            _LIPSRV["audio"] = audio
            _LIPSRV["amime"] = mime
            _LIPSRV["init"] = json.dumps(init)
        _open_editor_window("http://127.0.0.1:%d/" % _LIPSRV["port"])
        _LIPSRV["top_tries"] = 0
        try:
            bpy.app.timers.register(_lipsync_topmost_tick,
                                    first_interval=0.15)
        except Exception:
            pass
        self.report({'INFO'}, _tr("브라우저에서 립싱크 편집기를 열었습니다"))
        return {'FINISHED'}


class FSKR_OT_panel_rebind(bpy.types.Operator):
    bl_idname = "fskr.panel_rebind"
    bl_label = "현재 위치로 고정"
    bl_description = ("지금 보이는 패널 위치를 기준으로 다시 묶습니다. "
                      "캐릭터나 패널을 옮긴 뒤 위치가 어긋났을 때 "
                      "누르세요")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        s = context.scene.fskr
        return (s.rig is not None
                and "FP_root" in s.rig.pose.bones)

    def execute(self, context):
        s = context.scene.fskr
        if not _panel_follow_bind(s, context.scene):
            self.report({'ERROR'},
                        _tr("대상 리그와 본을 먼저 지정하세요"))
            return {'CANCELLED'}
        self.report({'INFO'}, _tr("패널 위치를 고정했습니다"))
        return {'FINISHED'}


class FSKR_OT_playback_add(bpy.types.Operator, ImportHelper):
    bl_idname = "fskr.playback_add"
    bl_label = "재생 오디오 추가"
    bl_description = ("스페이스바로 재생할 때 들리는 오디오를 시퀀서에 "
                      "추가합니다. 립싱크 분석용 오디오와는 별개라 "
                      "여기서 볼륨/음소거/시작 프레임만 따로 조절할 수 "
                      "있습니다")
    bl_options = {'REGISTER', 'UNDO'}

    filter_glob: bpy.props.StringProperty(
        default="*.wav;*.mp3;*.ogg;*.flac;*.m4a;*.aac",
        options={'HIDDEN'})
    frame_start: bpy.props.IntProperty(name="시작 프레임", default=1)
    mute_lipsync: bpy.props.BoolProperty(
        name="립싱크 사운드 음소거", default=True,
        description="립싱크용 사운드가 함께 울려 이중으로 들리는 것을 "
                    "막습니다")

    def execute(self, context):
        scene = context.scene
        s = scene.fskr
        try:
            se9 = scene.sequence_editor_create()
            coll9 = (getattr(se9, "sequences", None)
                     or getattr(se9, "strips", None))
            ch9 = 1
            for st9 in (coll9 or []):
                try:
                    ch9 = max(ch9, int(st9.channel))
                except Exception:
                    pass
            nm9 = "FSKR_play"
            new9 = coll9.new_sound(nm9, self.filepath, ch9 + 1,
                                   int(self.frame_start))
        except Exception as e9:
            self.report({'ERROR'}, str(e9))
            return {'CANCELLED'}
        if self.mute_lipsync:
            for st9 in _pb_strips(scene):
                if st9.name.startswith("FSKR_lipsync"):
                    try:
                        st9.mute = True
                    except Exception:
                        pass
        try:
            scene.use_audio = True
        except Exception:
            pass
        try:
            s.playback_target = "SEQ:" + new9.name
            _pb_pull(s, scene)
            _pb_solo_apply(s, scene)
        except Exception:
            pass
        _invalidate_ui_cache()
        self.report({'INFO'}, _tr("재생 오디오 추가: %s") % new9.name)
        return {'FINISHED'}


class FSKR_OT_playback_del(bpy.types.Operator):
    bl_idname = "fskr.playback_del"
    bl_label = "재생 오디오 제거"
    bl_description = ("선택한 재생 오디오를 제거합니다 (시퀀서 스트립만 "
                      "해당). 립싱크 데이터는 그대로 남습니다")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        kind9, t9 = _pb_target(context.scene.fskr, context.scene)
        return kind9 == "SEQ"

    def execute(self, context):
        scene = context.scene
        s = scene.fskr
        kind9, t9 = _pb_target(s, scene)
        if kind9 != "SEQ" or t9 is None:
            return {'CANCELLED'}
        nm9 = t9.name
        try:
            se9 = scene.sequence_editor
            coll9 = (getattr(se9, "sequences", None)
                     or getattr(se9, "strips", None))
            coll9.remove(t9)
        except Exception as e9:
            self.report({'ERROR'}, str(e9))
            return {'CANCELLED'}
        try:
            s.playback_target = NONE
        except Exception:
            pass
        _invalidate_ui_cache()
        self.report({'INFO'}, _tr("재생 오디오 제거: %s") % nm9)
        return {'FINISHED'}


class FSKR_OT_lipsync_sound_del(bpy.types.Operator):
    bl_idname = "fskr.lipsync_sound_del"
    bl_label = "립싱크 사운드 제거"
    bl_description = ("시퀀서에 넣은 립싱크 사운드 스트립을 제거합니다. "
                      "타임라인 스크럽 시 소리가 나지 않게 됩니다")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        n9 = 0
        try:
            se9 = context.scene.sequence_editor
            coll9 = ((getattr(se9, "sequences", None)
                      or getattr(se9, "strips", None)) if se9 else None)
            for st9 in [st for st in (coll9 or [])
                        if st.name.startswith("FSKR_lipsync")]:
                coll9.remove(st9)
                n9 += 1
        except Exception:
            pass
        self.report({'INFO'}, _tr("사운드 스트립 %d개 제거") % n9)
        return {'FINISHED'}


class FSKR_OT_lipsync_apply(bpy.types.Operator):
    bl_idname = "fskr.lipsync_apply"
    bl_label = "구간 적용 (다시 굽기)"
    bl_description = ("편집한 모음 구간대로 립싱크 키프레임을 다시 굽습니다")
    bl_options = {'REGISTER', 'UNDO'}

    refresh: bpy.props.BoolProperty(default=True, options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        s = context.scene.fskr
        return s.rig is not None and len(s.lipsync_segs) > 0

    def execute(self, context):
        s = context.scene.fskr
        rig = s.rig
        if _lipsync_resample(s, context.scene):
            self.report({'INFO'},
                        _tr("프레임 레이트 변경 감지: 립싱크를 새 프레임 "
                            "레이트에 맞춰 재배치했습니다"))
        try:
            opens = json.loads(s.lipsync_open or "[]")
        except Exception:
            opens = []
        if not opens or not rig:
            return {'CANCELLED'}
        start = int(s.lipsync_start)
        n = len(opens)
        _fit_scene_range(context.scene, start, start + n - 1, self)
        # 라우팅 사전 계산 (모음 채널 행만)
        routes = []
        for it in s.mocap_map:
            if not it.arkit.startswith('_'):
                continue
            vw9 = it.arkit
            fac = float(it.factor)
            if it.tgt == 'KEY':
                nm = str(it.mesh)
                mo = (bpy.data.objects.get(nm)
                      if nm and nm != "__DEF__" else s.mesh)
                kb = (mo.data.shape_keys.key_blocks.get(it.key)
                      if (mo and mo.type == 'MESH'
                          and mo.data.shape_keys) else None)
                if kb is not None and it.key != NONE:
                    routes.append((vw9, 'KEY', kb, 0, fac))
                continue
            pb = rig.pose.bones.get(it.ctl)
            if pb is None:
                continue
            ctype = str(pb.get("fskr_type", 'SLD_H'))
            c = it.comp
            if c in ('VAL', 'VALN'):
                if ctype not in ('SLD_H', 'SLD_V'):
                    continue
                axis = 1 if ctype == 'SLD_V' else 0
                inv = bool(pb.get("fskr_invert", 0))
                bidir = float(pb.get("fskr_vmin", 0.0)) < 0.0
                full = SLD / 2 if bidir else SLD
                sign = -1.0 if inv else 1.0
                if c == 'VALN':
                    sign = -sign
                routes.append((vw9, 'CTL', pb, axis, sign * full * fac))
            elif c in ('XP', 'XN', 'YP', 'YN'):
                axis = 0 if c in ('XP', 'XN') else 1
                sign = 1.0 if c in ('XP', 'YP') else -1.0
                routes.append((vw9, 'CTL', pb, axis, sign * PAD * fac))
        # 채널별 값 배열 계산
        ctl_arrays = {}
        key_arrays = {}
        for vw9, kind, tgt, axis, scale in routes:
            store = ctl_arrays if kind == 'CTL' else key_arrays
            k9 = (tgt, axis) if kind == 'CTL' else tgt
            if k9 not in store:
                store[k9] = [0.0] * n
        # 구간별 단순 엔벨로프 (상승→유지→하강): 키가 구간당 몇 개만 생김
        pad_pb9, _vm9 = _lipsync_padinfo(s, rig)
        if pad_pb9 is not None:
            for ax9 in (0, 1):
                ctl_arrays.setdefault((pad_pb9, ax9), [0.0] * n)
        bl9 = max(0, min(12, int(getattr(s, "lipsync_blend", 2))))
        blz9 = max(float(bl9), 0.5)

        # 구간별 채널 값 (구간 중심 = 이 값 그대로)
        seg_items = []
        for it in s.lipsync_segs:
            i0 = max(0, int(it.fs) - start)
            i1 = min(n - 1, int(it.fe) - start)
            if i1 < i0:
                continue
            amp9 = max(float(opens[k9]) for k9 in range(i0, i1 + 1))
            use_pos = pad_pb9 is not None and float(it.px) < 900.0
            if amp9 <= 0.0 and not use_pos:
                continue
            d9 = {}
            for vw9, kind, tgt, axis, scale in routes:
                if vw9 != it.vowel:
                    continue
                if use_pos and kind == 'CTL' and tgt == pad_pb9:
                    continue  # 패드는 좌표로 직접
                k9c = (('C', tgt, axis) if kind == 'CTL'
                       else ('K', tgt))
                d9[k9c] = d9.get(k9c, 0.0) + amp9 * scale
            if use_pos:
                d9[('C', pad_pb9, 0)] = float(it.px) * PAD
                d9[('C', pad_pb9, 1)] = float(it.py) * PAD
            seg_items.append((i0, i1, d9))
        seg_items.sort(key=lambda e9: e9[0])

        def poly_pts(chan9):
            """채널의 (프레임, 값) 폴리라인: 중심 유지·경계 크로스페이드·
            빈틈 0 램프."""
            pts9 = []
            for j9, (i0, i1, d9) in enumerate(seg_items):
                v9 = float(d9.get(chan9, 0.0))
                ln9 = i1 - i0 + 1
                h9 = min(bl9 * 0.5, (ln9 - 1) / 2.0)
                if j9 == 0:
                    pts9.append((i0 - blz9, 0.0))
                else:
                    _p0, p1, _pd = seg_items[j9 - 1]
                    g9 = i0 - p1 - 1
                    if g9 >= blz9:
                        z1, z2 = p1 + blz9, i0 - blz9
                        if z1 >= z2:
                            pts9.append(((z1 + z2) / 2.0, 0.0))
                        else:
                            pts9.append((z1, 0.0))
                            pts9.append((z2, 0.0))
                pts9.append((i0 + h9, v9))
                pts9.append((i1 - h9, v9))
                if j9 == len(seg_items) - 1:
                    pts9.append((i1 + blz9, 0.0))
            return pts9

        def poly_eval(pts9, f9):
            if not pts9:
                return 0.0
            if f9 <= pts9[0][0]:
                return pts9[0][1]
            for j9 in range(1, len(pts9)):
                if f9 <= pts9[j9][0]:
                    a9, b9 = pts9[j9 - 1], pts9[j9]
                    if b9[0] <= a9[0]:
                        return b9[1]
                    return (a9[1] + (b9[1] - a9[1])
                            * (f9 - a9[0]) / (b9[0] - a9[0]))
            return pts9[-1][1]

        for (pb9c, ax9c), arr9 in list(ctl_arrays.items()):
            pts9 = poly_pts(('C', pb9c, ax9c))
            for i9 in range(n):
                arr9[i9] = poly_eval(pts9, float(i9))
        for kb9c, arr9 in list(key_arrays.items()):
            pts9 = poly_pts(('K', kb9c))
            for i9 in range(n):
                arr9[i9] = poly_eval(pts9, float(i9))

        try:
            prev9 = json.loads(s.lipsync_baked or "[]")
        except Exception:
            prev9 = []

        def batch_write(ad_id, dp, idx, vals):
            """키프레임 일괄 기록: 같은 채널의 모든 커브 청소 후 기록."""
            ad9 = ad_id.animation_data if ad_id else None
            fcs9 = [c9 for c9 in _action_fcurves(ad9)
                    if c9.data_path == dp and c9.array_index == idx]
            if not fcs9:
                return
            rngs = [(start, start + n - 1)]
            if len(prev9) == 2:
                rngs.append((int(prev9[0]),
                             int(prev9[0]) + int(prev9[1]) - 1))
            for fc9c in fcs9:
                pts9c = fc9c.keyframe_points
                for i9 in range(len(pts9c) - 1, -1, -1):
                    fco = pts9c[i9].co[0]
                    if any(a9 <= fco <= b9 for a9, b9 in rngs):
                        pts9c.remove(pts9c[i9], fast=True)
                fc9c.update()
            if all(abs(v9) < 1e-6 for v9 in vals):
                return
            fc = fcs9[0]
            try:  # 활성 슬롯의 커브 우선 (평가되는 커브에 기록)
                act9 = ad9.action
                slot9 = getattr(ad9, "action_slot", None)
                if slot9 is not None:
                    for ly9 in act9.layers:
                        for st9s in ly9.strips:
                            cb9 = st9s.channelbag(slot9)
                            if cb9 is None:
                                continue
                            for c9 in cb9.fcurves:
                                if (c9.data_path == dp
                                        and c9.array_index == idx):
                                    fc = c9
            except Exception:
                pass
            pts = fc.keyframe_points
            # 타이밍이 있는 순간에만 키 (RDP 간소화)
            keep9 = _rdp_indices([(float(start + i9), vals[i9])
                                  for i9 in range(n)], 0.002)
            base = len(pts)
            pts.add(len(keep9))
            for j9, i9 in enumerate(keep9):
                p9 = pts[base + j9]
                p9.co = (float(start + i9), vals[i9])
                p9.interpolation = 'LINEAR'
            fc.update()

        for (pb, axis), vals in ctl_arrays.items():
            try:
                pb.keyframe_insert("location", index=axis, frame=start,
                                   group=str(pb.get("fskr_label",
                                                    pb.name)))
            except Exception:
                pass
            batch_write(rig, 'pose.bones["%s"].location' % pb.name,
                        axis, vals)
        for kb, vals in key_arrays.items():
            try:
                kb.keyframe_insert("value", frame=start)
            except Exception:
                pass
            batch_write(kb.id_data, kb.path_from_id() + ".value", 0, vals)
        try:
            atlas_lip_bake(s, rig, start, n, opens, prev9)
        except Exception:
            pass
        s.lipsync_baked = json.dumps([start, n])
        try:
            rig.update_tag()
        except Exception:
            pass
        if self.refresh:
            try:
                context.scene.frame_set(context.scene.frame_current)
            except Exception:
                pass
            try:
                for win in context.window_manager.windows:
                    for area in win.screen.areas:
                        area.tag_redraw()
            except Exception:
                pass
        self.report({'INFO'}, _tr("립싱크 다시 굽기 완료 (%d프레임)") % n)
        return {'FINISHED'}


class FSKR_OT_lipsync(bpy.types.Operator, ImportHelper):
    bl_idname = "fskr.lipsync"
    bl_label = "오디오 립싱크 생성"
    bl_description = ("대사 녹음(WAV/MP3/OGG/FLAC)을 분석해 A/I/U/E/O 립싱크 "
                      "키프레임을 자동 생성합니다. '간단 자동 설정'의 입 "
                      "매핑을 그대로 사용하므로 먼저 매핑을 만들어 두세요")
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".wav"
    filter_glob: bpy.props.StringProperty(
        default="*.wav;*.mp3;*.ogg;*.flac;*.m4a;*.aac",
        options={'HIDDEN'})
    frame_start: bpy.props.IntProperty(name="시작 프레임", default=1)
    gain: bpy.props.FloatProperty(
        name="입 벌림 배율", default=1.0, min=0.1, soft_max=2.0,
        precision=2, description="전체 입 벌림 강도")
    silence: bpy.props.FloatProperty(
        name="무음 임계값", default=0.06, min=0.0, soft_max=0.3,
        precision=2,
        description="최대 음량 대비 이 비율 아래면 입을 다뭅니다")
    smooth: bpy.props.FloatProperty(
        name="스무딩", default=0.35, min=0.0, max=0.95, precision=2,
        description="입 움직임 완화. 높을수록 부드럽지만 둔해집니다")
    use_sound: bpy.props.BoolProperty(
        name="사운드 스트립 추가", default=True,
        description="시퀀서에 오디오를 넣어 재생 시 소리가 같이 나오게 합니다")

    @classmethod
    def poll(cls, context):
        s = context.scene.fskr
        return s.rig is not None

    def invoke(self, context, event):
        self.frame_start = context.scene.frame_current
        return ImportHelper.invoke(self, context, event)

    def execute(self, context):
        s = context.scene.fskr
        rig = s.rig
        if (not any(it.arkit.startswith('_') for it in s.mocap_map)
                and not atlas_lip_enabled(s)):
            self.report({'ERROR'},
                        _tr("입 모음 매핑이 없습니다. iFacialMocap 패널의 "
                        "'간단 자동 설정'으로 먼저 만들어 주세요"))
            return {'CANCELLED'}
        try:
            import numpy  # noqa: F401
        except ImportError:
            self.report({'ERROR'}, _tr("numpy를 사용할 수 없습니다"))
            return {'CANCELLED'}
        try:
            data, sr = _read_audio_mono(self.filepath)
        except Exception as e:
            self.report({'ERROR'}, _tr("오디오를 읽을 수 없습니다: %s") % e)
            return {'CANCELLED'}
        if len(data) < sr // 10:
            self.report({'ERROR'}, _tr("오디오가 너무 짧습니다"))
            return {'CANCELLED'}
        scene = context.scene
        fps = scene.render.fps / scene.render.fps_base
        frames = _lipsync_analyze(data, sr, fps, float(self.gain),
                                  float(self.silence), float(self.smooth))

        if self.use_sound:
            try:
                se = scene.sequence_editor_create()
                coll9 = getattr(se, "sequences", None) or getattr(
                    se, "strips", None)
                # 이전 립싱크 사운드 제거 (중복 재생 방지)
                for st9 in [st for st in coll9
                            if st.name.startswith("FSKR_lipsync")]:
                    try:
                        coll9.remove(st9)
                    except Exception:
                        pass
                coll9.new_sound("FSKR_lipsync", self.filepath, 5,
                                int(self.frame_start))
                # 오디오 재생 설정 자동화 (AV 동기 + 오디오 켜기)
                try:
                    scene.sync_mode = 'AUDIO_SYNC'
                except Exception:
                    pass
                try:
                    scene.use_audio = True
                except Exception:
                    pass
                try:
                    scene.use_audio_scrub = True  # 스크럽 시 소리
                except Exception:
                    pass
            except Exception:
                pass
        s.lipsync_audio = self.filepath
        _fit_scene_range(scene, int(self.frame_start),
                         int(self.frame_start) + len(frames) - 1, self)
        _invalidate_ui_cache()
        # 구간 추출 + 간소화 굽기 + 편집 팝업
        _lipsync_build_segs(s, frames, int(self.frame_start))
        try:
            bpy.ops.fskr.lipsync_apply()
        except Exception:
            pass
        self.report({'INFO'},
                    _tr("립싱크 생성: %d프레임 (%.1f초). 필요하면 '녹화 커브 "
                    "단순화'로 정리하세요") % (len(frames), len(data) / sr))
        try:
            bpy.ops.fskr.lipsync_edit()  # 편집 창 자동 열기
        except Exception:
            pass
        return {'FINISHED'}


class FSKR_OT_simplify_curves(bpy.types.Operator):
    bl_idname = "fskr.simplify_curves"
    bl_label = "녹화 커브 단순화"
    bl_description = ("mocap 녹화로 촘촘히 박힌 키프레임을 모양을 유지하는 "
                      "한도 안에서 줄입니다 (핸들 위치·목 회전·셰이프 키 값). "
                      "그래프 에디터에서 손질하기 쉬워집니다")
    bl_options = {'REGISTER', 'UNDO'}

    error: bpy.props.FloatProperty(
        name="허용 오차", default=0.01, min=0.0001, soft_max=0.1,
        precision=3,
        description="값 단위 오차 한도. 클수록 키가 많이 줄어듭니다")

    @classmethod
    def poll(cls, context):
        return context.scene.fskr.rig is not None

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        s = context.scene.fskr
        rig = s.rig
        fcs = []
        seen = set()

        def add_fc(fc):
            k = (fc.id_data.name if fc.id_data else "",
                 fc.data_path, fc.array_index)
            if k not in seen:
                seen.add(k)
                fcs.append(fc)

        if rig:
            for fc in _action_fcurves(rig.animation_data):
                dp = fc.data_path
                if (dp.startswith('pose.bones["FP_ctl')
                        and dp.endswith('.location')):
                    add_fc(fc)
        hob = s.mocap_head_rig
        if hob and s.mocap_head_bone:
            pref = 'pose.bones["%s"].' % s.mocap_head_bone
            for fc in _action_fcurves(hob.animation_data):
                if fc.data_path.startswith(pref) and \
                        "rotation" in fc.data_path:
                    add_fc(fc)
        for kd in bpy.data.shape_keys:
            for fc in _action_fcurves(kd.animation_data):
                if fc.data_path.endswith(".value"):
                    add_fc(fc)
        before = 0
        removed = 0
        for fc in fcs:
            before += len(fc.keyframe_points)
            removed += _simplify_fcurve(fc, float(self.error))
        if not fcs:
            self.report({'WARNING'}, _tr("단순화할 커브가 없습니다"))
            return {'CANCELLED'}
        # 즉시 반영: 애니메이션 재평가 + 전체 영역 리드로우
        try:
            context.scene.frame_set(context.scene.frame_current)
        except Exception:
            pass
        try:
            for win in context.window_manager.windows:
                for area in win.screen.areas:
                    area.tag_redraw()
        except Exception:
            pass
        self.report({'INFO'},
                    _tr("커브 %d개: 키 %d개 → %d개 (%d개 제거)")
                    % (len(fcs), before, before - removed, removed))
        return {'FINISHED'}


class FSKR_OT_mocap_map_add(bpy.types.Operator):
    bl_idname = "fskr.mocap_map_add"
    bl_label = "매핑 추가"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        context.scene.fskr.mocap_map.add()
        return {'FINISHED'}


class FSKR_OT_mocap_map_del(bpy.types.Operator):
    bl_idname = "fskr.mocap_map_del"
    bl_label = "매핑 삭제"
    bl_options = {'REGISTER', 'UNDO'}

    index: bpy.props.IntProperty()

    def execute(self, context):
        s = context.scene.fskr
        if 0 <= self.index < len(s.mocap_map):
            s.mocap_map.remove(self.index)
        return {'FINISHED'}
