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
from .core import (
    NONE,
    _MOCAP,
    _SLOT_ARROW,
    _addon_prefs,
    _driven_map,
    _is_handle_name,
    _kb_val,
    _lipsync_audio_info,
    _slot_order,
    _sorted_ctls,
    _tr,
)


class FSKR_PT_setup(bpy.types.Panel):
    bl_label = "설정"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Face Rig"

    @classmethod
    def poll(cls, context):
        return getattr(context.scene.fskr, "ui_mode", 'DRIVER') == 'DRIVER'

    def draw(self, context):
        s = context.scene.fskr
        col = self.layout.column()
        col.prop(s, "mesh")
        col.prop(s, "rig")
        col.prop(s, "auto_switch")
        col.operator("fskr.place_panel", icon='CURSOR')
        pbr = (s.rig.pose.bones.get("FP_root")
               if s.rig and s.rig.type == 'ARMATURE' else None)
        if pbr is not None:
            boxr = col.box()
            boxr.label(text=_tr("패널 위치 (그랩 바)"),
                       icon='EMPTY_ARROWS')
            cr = boxr.column(align=True)
            cr.prop(pbr, "location", index=0, text="X")
            cr.prop(pbr, "location", index=1, text="Y")
            cr.prop(pbr, "location", index=2, text="Z")
            boxr.prop(s, "panel_follow", toggle=True, icon='CON_CHILDOF')
            if s.panel_follow:
                boxr.prop(s, "panel_follow_rig")
                if (s.panel_follow_rig
                        and s.panel_follow_rig.type == 'ARMATURE'):
                    boxr.prop_search(s, "panel_follow_bone",
                                     s.panel_follow_rig.data, "bones")
                boxr.operator("fskr.panel_rebind", icon='PINNED')
        row = col.row(align=True)
        row.prop(s, "token_l", text=_tr("좌"))
        row.prop(s, "token_r", text=_tr("우"))
        col.separator()
        row = col.row(align=True)
        row.operator("fskr.add_slider", icon='IPO_LINEAR')
        row.operator("fskr.add_pad", icon='MESH_PLANE')
        col.operator("fskr.add_bonepad", icon='ORIENTATION_GIMBAL')
        row = col.row(align=True)
        row.operator("fskr.add_text", icon='FONT_DATA')
        row.operator("fskr.text_color", icon='COLOR')
        col.operator("fskr.text_autocolor", icon='EYEDROPPER')


class FSKR_PT_list(bpy.types.Panel):
    bl_label = "컨트롤러 목록"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Face Rig"

    @classmethod
    def poll(cls, context):
        return getattr(context.scene.fskr, "ui_mode", 'DRIVER') == 'DRIVER'

    def draw(self, context):
        s = context.scene.fskr
        layout = self.layout
        rig = s.rig
        ctls = ([b.name for b in rig.data.bones if _is_handle_name(b.name)]
                if rig else [])

        row = layout.row(align=True)
        row.operator("fskr.arrange_toggle", text=_tr("배치 모드"),
                     icon='ORIENTATION_GLOBAL' if s.arrange
                     else 'RESTRICT_SELECT_OFF',
                     depress=bool(s.arrange)).scope = ""
        row.prop(s, "labels_visible", toggle=True, icon='FONT_DATA')
        if hasattr(s, "show_no_overlay"):
            row.prop(s, "show_no_overlay", toggle=True, icon='OVERLAY')
        row = layout.row(align=True)
        row.operator("fskr.add_collection", icon='COLLECTION_NEW')
        row.operator("fskr.assign_collection", icon='OUTLINER_COLLECTION')

        if not ctls:
            layout.label(text=_tr("추가된 컨트롤러가 없습니다"), icon='INFO')
            row = layout.row(align=True)
            row.operator("fskr.export_layout", icon='EXPORT')
            row.operator("fskr.import_layout", icon='IMPORT')
            return
        # 뷰포트에서 선택(조작 중)된 컨트롤러 파악
        ab = context.active_pose_bone
        act = None
        if ab is not None:
            n = ab.name
            if n.endswith("_frame") and n.startswith("FP_ctl"):
                act = n[:-len("_frame")]
            elif _is_handle_name(n):
                act = n

        # 핸들 → 실제 드라이버가 걸린 셰이프 키 (캐시 사용)
        driven = _driven_map(rig) if rig else {}

        cur_grp = None
        col = None
        for name in _sorted_ctls(rig):
            pb = rig.pose.bones[name]
            grp = str(pb.get("fskr_group", ""))
            if grp != cur_grp:
                cur_grp = grp
                if grp:
                    citem = next((c for c in s.collections
                                  if c.name == grp), None)
                    box = layout.box()
                    hr = box.row(align=True)
                    if citem is not None:
                        hr.prop(citem, "expand", text="", emboss=False,
                                icon='TRIA_DOWN' if citem.expand
                                else 'TRIA_RIGHT')
                    hr.label(text=grp, icon='OUTLINER_COLLECTION')
                    hr.operator("fskr.del_collection", text="",
                                icon='X').coll_name = grp
                    if citem is None or citem.expand:
                        col = box.column(align=True)
                    else:
                        col = None  # 접힘: 소속 컨트롤러 숨김
                else:
                    col = layout.column(align=True)
            if col is None:
                continue
            ctype = str(pb.get("fskr_type", 'SLD_H'))
            if ctype == 'PAD':
                icon = 'MESH_PLANE'
            elif ctype == 'BONE':
                icon = 'ORIENTATION_GIMBAL'
            else:
                icon = 'IPO_LINEAR'
            row = col.row(align=True)
            if ctype == 'PAD':
                row.prop(pb, "fskr_expand", text="", emboss=False,
                         icon='TRIA_DOWN' if pb.fskr_expand else 'TRIA_RIGHT')
            row.prop(pb, "fskr_sel", text="")
            # 순번 (직접 수정하면 그 위치로 끼어듦)
            sub = row.row(align=True)
            sub.ui_units_x = 1.4
            sub.prop(pb, "fskr_idx", text="")
            # 색상 스와치 (뷰포트 컨트롤러 색과 실시간 연동, 클릭해서 변경)
            has_col9 = bool(pb.get("fskr_usecolor", 0))
            if not has_col9:
                try:  # 플래그가 없어도 실제로 색이 칠해져 있으면 표시
                    has_col9 = (pb.color.palette == 'CUSTOM')
                except Exception:
                    has_col9 = False
            if has_col9:
                sub = row.row(align=True)
                sub.ui_units_x = 1.1
                sub.prop(pb, "fskr_col", text="")
            key_nm = str(pb.get("fskr_key", NONE))
            mo6 = bpy.data.objects.get(str(pb.get("fskr_mesh", "")))
            if mo6 and mo6.type == 'MESH' and mo6.data.shape_keys:
                keys = mo6.data.shape_keys.key_blocks
            else:
                keys = (s.mesh.data.shape_keys.key_blocks
                        if s.mesh and s.mesh.data.shape_keys else None)
            # 켜져 있음(값이 0이 아님) 판정 — 실제 드라이버 기준
            dkbs = driven.get(name, [])
            dmap = {kb9.name: kb9 for kb9 in dkbs}
            active = False
            if ctype == 'BONE':
                active = (abs(pb.location[0]) > 1e-4
                          or abs(pb.location[1]) > 1e-4)
            elif dkbs:
                for kb9 in dkbs:
                    v9 = _kb_val(kb9)
                    if v9 is not None and abs(v9) > 0.001:
                        active = True
                        break
            elif keys and key_nm in keys:
                active = abs(keys[key_nm].value) > 0.001
            # 이름 버튼 (켜져 있으면 빨간색)
            nsub = row.row(align=True)
            nsub.alert = active
            op = nsub.operator("fskr.select_ctl", icon=icon,
                               text=str(pb.get("fskr_label", name)),
                               depress=(name == act))
            op.bone = name
            # 셰이프 키 현재 값 표시
            sub = row.row(align=True)
            sub.ui_units_x = 2.6
            if ctype == 'BONE':
                t1 = str(pb.get("fskr_tb1", ""))
                t2 = str(pb.get("fskr_tb2", ""))
                sub.label(text=(t1 + (" +" if t2 else "")) if t1 else "")
            elif ctype != 'PAD':
                # 메타데이터 → 실제 드라이버 순으로 값 표시
                kb9 = (keys[key_nm] if (keys and key_nm in keys)
                       else (dkbs[0] if dkbs else None))
                if kb9 is not None and _kb_val(kb9) is not None:
                    sub.prop(kb9, "value", text="")
                else:
                    sub.label(text="")
            else:
                sub.label(text="")
            row.operator("fskr.mirror_ctl", text="", icon='MOD_MIRROR').bone = name
            row.operator("fskr.edit_ctl", text="", icon='GREASEPENCIL').bone = name
            row.operator("fskr.remove_ctl", text="", icon='X').bone = name
            # 패드 펼침: 슬롯별 셰이프 키와 현재 드라이버 값 (순번으로 정렬 가능)
            if ctype == 'PAD' and pb.fskr_expand and (keys or dkbs):
                shown = set()
                for slot in _slot_order(pb):
                    k = str(pb.get("fskr_" + slot, NONE))
                    if k == NONE or k in shown:
                        continue
                    kb9 = ((keys.get(k) if keys else None)
                           or dmap.get(k))
                    if kb9 is None or _kb_val(kb9) is None:
                        continue
                    shown.add(k)
                    r2 = col.row(align=True)
                    r2.label(text="", icon='BLANK1')
                    si = r2.row(align=True)
                    si.ui_units_x = 1.4
                    si.prop(pb, "fskr_si_" + slot, text="")
                    r2.separator(factor=1.2)
                    r2.label(text="%s %s" % (_SLOT_ARROW[slot], k))
                    vs = r2.row(align=True)
                    vs.ui_units_x = 2.6
                    vs.alert = abs(kb9.value) > 0.001
                    vs.prop(kb9, "value", text="")
        # 빈 컬렉션도 표시
        used_grps = {str(rig.pose.bones[n2].get("fskr_group", ""))
                     for n2 in _sorted_ctls(rig)}
        for citem in s.collections:
            if citem.name and citem.name not in used_grps:
                box = layout.box()
                hr = box.row(align=True)
                hr.label(text=citem.name, icon='OUTLINER_COLLECTION')
                hr.label(text=_tr("(비어 있음)"))
                hr.operator("fskr.del_collection", text="",
                            icon='X').coll_name = citem.name
        layout.separator()
        col = layout.column(align=True)
        col.operator("fskr.sort_visual", icon='SORTSIZE')
        col.operator("fskr.key_all", icon='KEY_HLT')
        col.operator("fskr.save_default", icon='FILE_TICK')
        col.operator("fskr.reset_all", icon='LOOP_BACK')
        col.operator("fskr.reload_panel", icon='FILE_REFRESH')
        col.operator("fskr.repair_layout", icon='ORIENTATION_GLOBAL')
        col.operator("fskr.sync_names", icon='SORTALPHA')
        col.operator("fskr.sync_colors", icon='COLOR')
        col.operator("fskr.bake_keys", icon='RENDER_ANIMATION')
        row = col.row(align=True)
        row.operator("fskr.export_layout", icon='EXPORT')
        row.operator("fskr.import_layout", icon='IMPORT')
        row2 = col.row(align=True)
        row2.operator("fskr.char_export", icon='PACKAGE')
        row2.operator("fskr.char_import", icon='APPEND_BLEND')
        col.operator("fskr.remove_all", icon='TRASH')


class FSKR_PT_presets(bpy.types.Panel):
    bl_label = "표정 프리셋"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Face Rig"

    @classmethod
    def poll(cls, context):
        # 스프라이트 방식은 ⑤ 표정 프리셋을 씀
        return getattr(context.scene.fskr, "ui_mode", 'DRIVER') != 'SPRITE'

    def draw(self, context):
        s = context.scene.fskr
        layout = self.layout
        layout.operator("fskr.preset_save", icon='ADD')
        if not s.presets:
            layout.label(text=_tr("저장된 프리셋이 없습니다"), icon='INFO')
            return
        col = layout.column(align=True)
        for pi, p in enumerate(s.presets):
            row = col.row(align=True)
            # 1~9번은 캡처 중 숫자키로도 적용 가능
            txt = ("%d. %s" % (pi + 1, p.name)) if pi < 9 else p.name
            row.operator("fskr.preset_apply", text=txt,
                         icon='POSE_HLT').pname = p.name
            row.operator("fskr.preset_rename", text="",
                         icon='GREASEPENCIL').pname = p.name
            row.operator("fskr.preset_del", text="", icon='X').pname = p.name


class FSKR_PT_mocap(bpy.types.Panel):
    bl_label = "iFacialMocap"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Face Rig"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return getattr(context.scene.fskr, "ui_mode", 'DRIVER') == 'DRIVER'

    def draw(self, context):
        s = context.scene.fskr
        col = self.layout.column()
        col.prop(s, "mocap_ip")
        running = _MOCAP.get("sock") is not None
        row = col.row(align=True)
        if running:
            row.operator("fskr.mocap_stop", icon='PAUSE')
        else:
            row.operator("fskr.mocap_start", icon='PLAY')
        if running:
            row3 = col.row(align=True)
            row3.operator("fskr.mocap_rec_start", icon='REC')
            sub3 = row3.row(align=True)
            sub3.ui_units_x = 2.6
            sub3.prop(s, "mocap_countdown", text="")
        row2 = col.row(align=True)
        row2.operator("fskr.mocap_calibrate", icon='CHECKMARK')
        row2.operator("fskr.mocap_cal_clear", text="", icon='X')
        row2.prop(s, "mocap_preview", text="", toggle=True, icon='HIDE_OFF')
        if _MOCAP.get("neutral"):
            col.label(text=_tr("캘리브레이션 적용 중"), icon='CHECKMARK')
        if s.mocap_preview:
            col.prop(s, "mocap_preview_scale", slider=True)
        col.prop(s, "mocap_smooth", slider=True)
        col.prop(s, "mocap_blend")
        rowl = col.row(align=True)
        rowl.operator("fskr.lipsync", icon='SPEAKER')
        rowl.operator("fskr.lipsync_edit", text="", icon='GREASEPENCIL')
        rowl2 = col.row(align=True)
        rowl2.prop(context.scene, "use_audio_scrub",
                   text=_tr("스크럽 소리"), toggle=True)
        rowl2.operator("fskr.lipsync_sound_del", text="", icon='X')
        boxa = col.box()
        inf9 = _lipsync_audio_info(s)
        if inf9 is None:
            boxa.label(text=_tr("오디오: 파일 없음"), icon='LIBRARY_DATA_BROKEN')
        else:
            boxa.label(text=_tr("파일: ") + inf9["name"], icon='SOUND')
            boxa.label(text=_tr("형식: ") + inf9["codec"])
            boxa.label(text=_tr("크기: %s · 길이: %s")
                       % (inf9["size"], inf9["dur"]))
        boxp = col.box()
        rowp = boxp.row(align=True)
        rowp.label(text=_tr("재생 오디오 (스페이스바)"), icon='PLAY_SOUND')
        rowp.operator("fskr.playback_add", text="", icon='ADD')
        rowp.operator("fskr.playback_del", text="", icon='X')
        boxp.prop(s, "playback_target", text="")
        if s.playback_target != NONE:
            rowv = boxp.row(align=True)
            rowv.prop(s, "playback_vol", slider=True)
            rowv.prop(s, "playback_mute", text="",
                      icon='MUTE_IPO_OFF' if s.playback_mute
                      else 'MUTE_IPO_ON', toggle=True)
            if s.playback_target.startswith("SEQ:"):
                boxp.prop(s, "playback_start")
        col.operator("fskr.simplify_curves", icon='MOD_SMOOTH')
        col.operator("fskr.mocap_wizard", icon='PRESET')
        boxh = col.box()
        boxh.label(text=_tr("머리/목 회전"), icon='BONE_DATA')
        boxh.prop(s, "mocap_head_rig")
        if s.mocap_head_rig and s.mocap_head_rig.type == 'ARMATURE':
            boxh.prop_search(s, "mocap_head_bone",
                             s.mocap_head_rig.data, "bones")
        boxh.prop(s, "mocap_head_gain")
        for pax, pinv in (("mocap_head_ax_p", "mocap_head_inv_p"),
                          ("mocap_head_ax_y", "mocap_head_inv_y"),
                          ("mocap_head_ax_r", "mocap_head_inv_r")):
            r9 = boxh.row(align=True)
            r9.prop(s, pax)
            r9.prop(s, pinv, text="", icon='ARROW_LEFTRIGHT', toggle=True)
        if running:
            if _MOCAP.get("ok"):
                col.label(text=_tr("수신 중"), icon='CHECKMARK')
            else:
                col.label(text=_tr("대기 중 (앱/와이파이/IP 확인)"), icon='TIME')
            col.label(text=_tr("숫자키 1~9 = 표정 프리셋, 0 = 기본 표정"),
                      icon='EVENT_NDOF_BUTTON_1')
        if _MOCAP.get("err"):
            col.label(text=str(_MOCAP["err"]), icon='ERROR')
        box = col.box()
        hr = box.row(align=True)
        hr.label(text=_tr("매핑 (ARKit → 컨트롤러)"), icon='ANIM')
        # ARKit 블렌드셰이프가 각각 어떤 표정인지 그림으로 보여주는 사이트
        op0 = hr.operator("wm.url_open", text="", icon='HELP')
        op0.url = "https://arkit-face-blendshapes.com/"
        hr.operator("fskr.mocap_automap", text="", icon='SHADERFX')
        hr.operator("fskr.mocap_map_add", text="", icon='ADD')
        for i, it in enumerate(s.mocap_map):
            r = box.row(align=True)
            r.prop(it, "arkit", text="")
            sub0 = r.row(align=True)
            sub0.ui_units_x = 2.2
            sub0.prop(it, "tgt", text="")
            if it.tgt == 'KEY':
                r.prop(it, "mesh", text="")
                r.prop(it, "key", text="")
            else:
                r.prop(it, "ctl", text="")
                sub = r.row(align=True)
                sub.ui_units_x = 2.0
                sub.prop(it, "comp", text="")
            sub2 = r.row(align=True)
            sub2.ui_units_x = 1.4
            sub2.prop(it, "factor", text="")
            r.operator("fskr.mocap_map_del", text="", icon='X').index = i
        if not len(s.mocap_map):
            box.label(text=_tr("자동 매핑(마법봉) 또는 +로 추가하세요"))


class FSKR_PT_help(bpy.types.Panel):
    bl_label = "조작법"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Face Rig"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return getattr(context.scene.fskr, "ui_mode", 'DRIVER') == 'DRIVER'

    def draw(self, context):
        col = self.layout.column(align=True)
        for line in (
            _tr("포즈 모드에서 컨트롤러 선택 후 G로 이동"),
            _tr("텍스트 추가 = 자유 라벨 (오브젝트 모드에서 편집)"),
            _tr("목록에서 이름 클릭 = 뷰포트에서 선택"),
            _tr("연필 아이콘 = 타입/키/라벨 수정"),
            _tr("미러 아이콘 = 반대쪽 컨트롤러 자동 생성"),
            _tr("화살표 = 목록 순서 이동, 그룹은 수정 팝업에서"),
            _tr("배치 모드 ON = 틀을 G/R/S로 자유 배치"),
            _tr("배치 모드: G 이동 중 Ctrl = 모서리 스냅"),
            _tr("배치 모드: 노란 화살표 드래그 = 그 변만 크기 조절"),
            _tr("변 드래그 중 Ctrl = 스냅, Alt = 대칭 조절"),
            _tr("패드: 같은 키를 상+하에 넣으면 -1~1 범위"),
            _tr("본 패드 = 핸들 XY로 본(눈알 타겟) 이동"),
            _tr("슬라이더 최솟값<0 = 양방향 (중앙이 0)"),
            _tr("키프레임: I > Location (또는 자동 키)"),
            _tr("패널 전체 이동: FP_root 본을 G로 이동"),
            _tr("우상단 빨간 토글 오른쪽으로 = 패널 숨김"),
        ):
            col.label(text=line)
