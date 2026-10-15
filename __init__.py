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
    _fskr_char_autoswitch,
    _fskr_char_save_pre,
    FSKR_ChainItem,
    FSKR_CollectionItem,
    FSKR_LipSegItem,
    FSKR_MocapMapItem,
    FSKR_Prefs,
    FSKR_PresetItem,
    FSKR_Settings,
    FSKR_UL_lipsegs,
    FSKR_WizRoleItem,
    _LANG_STATE,
    _SLOT_ORDER,
    _col_update,
    _draw_arrows,
    _draw_countdown,
    _draw_help_text,
    _draw_mocap_preview,
    _fskr_ns_install,
    _fskr_refresh_drivers,
    _idx_get,
    _idx_set,
    _lipsrv_stop,
    _mk_slot_get,
    _mk_slot_set,
    _mocap_stop_sock,
    _persist_handlers_img,
    _retranslate,
    _tr,
)
from .operators import (
    FSKR_OT_panel_rebind,
    FSKR_OT_playback_add,
    FSKR_OT_playback_del,
    FSKR_OT_char_export,
    FSKR_OT_char_import,
    FSKR_OT_add_slider,
    FSKR_OT_add_pad,
    FSKR_OT_add_bonepad,
    FSKR_OT_edit_ctl,
    FSKR_OT_batch_edit,
    FSKR_OT_mirror_ctl,
    FSKR_OT_add_text,
    FSKR_OT_text_color,
    FSKR_OT_text_autocolor,
    FSKR_OT_export_layout,
    FSKR_OT_import_layout,
    FSKR_OT_preset_save,
    FSKR_OT_preset_apply,
    FSKR_OT_preset_rename,
    FSKR_OT_preset_del,
    FSKR_OT_bake_keys,
    FSKR_OT_add_collection,
    FSKR_OT_del_collection,
    FSKR_OT_assign_collection,
    FSKR_OT_reload_panel,
    FSKR_OT_repair_layout,
    FSKR_OT_sync_names,
    FSKR_OT_place_panel,
    FSKR_OT_attach_panel,
    FSKR_OT_sync_colors,
    FSKR_OT_snap_move,
    FSKR_OT_pose_clear_guard,
    FSKR_OT_edge_move,
    FSKR_OT_arrange_exit,
    FSKR_OT_arrange_toggle,
    FSKR_OT_move_ctl,
    FSKR_OT_sort_visual,
    FSKR_OT_select_ctl,
    FSKR_OT_remove_ctl,
    FSKR_OT_remove_all,
    FSKR_OT_save_default,
    FSKR_OT_reset_all,
    FSKR_OT_key_all,
    FSKR_OT_mocap_start,
    FSKR_OT_mocap_stop,
    FSKR_OT_mocap_rec_start,
    FSKR_OT_mocap_calibrate,
    FSKR_OT_mocap_cal_clear,
    FSKR_OT_mocap_automap,
    FSKR_OT_mocap_wizard,
    FSKR_OT_mocap_preset_key,
    FSKR_OT_lipsync_seek,
    FSKR_OT_lipsync_edit,
    FSKR_OT_lipsync_sound_del,
    FSKR_OT_lipsync_apply,
    FSKR_OT_lipsync,
    FSKR_OT_simplify_curves,
    FSKR_OT_mocap_map_add,
    FSKR_OT_mocap_map_del,
)
from .atlas import (
    FSKR_AtlasCellXf,
    FSKR_AtlasFlap,
    FSKR_AtlasItem,
    atlas_register,
    atlas_unregister,
    FSKR_PT_atlas,
    FSKR_PT_mode,
    atlas_classes,
    _thumbs_free_all,
)
from .atlas_vp import vp_classes, vp_register, vp_unregister
from .eye import eye_classes, eye_pg_classes, over_register, over_unregister
from .face_ui import face_classes, face_register, face_unregister
from .preset_vp import pvp_classes, pvp_register, pvp_unregister
from .layer_vp import lvp_classes, lvp_register, lvp_unregister
from .ime import ime_classes, ime_register, ime_unregister
from .panels import (
    FSKR_PT_setup,
    FSKR_PT_list,
    FSKR_PT_presets,
    FSKR_PT_mocap,
    FSKR_PT_help,
)


classes = (FSKR_CollectionItem, FSKR_PresetItem, FSKR_ChainItem,
           FSKR_LipSegItem,
           FSKR_MocapMapItem, FSKR_WizRoleItem,
           FSKR_AtlasCellXf, FSKR_AtlasFlap, FSKR_AtlasItem,
           ) + eye_pg_classes + (
           FSKR_Settings, FSKR_UL_lipsegs,
           FSKR_OT_add_slider, FSKR_OT_add_pad, FSKR_OT_add_bonepad,
           FSKR_OT_add_text,
           FSKR_OT_text_color, FSKR_OT_text_autocolor,
           FSKR_OT_preset_save, FSKR_OT_preset_apply,
           FSKR_OT_preset_rename, FSKR_OT_preset_del,
           FSKR_OT_bake_keys,
           FSKR_OT_export_layout, FSKR_OT_import_layout,
           FSKR_OT_edit_ctl, FSKR_OT_batch_edit,
           FSKR_OT_mirror_ctl, FSKR_OT_move_ctl,
           FSKR_OT_sort_visual,
           FSKR_OT_snap_move, FSKR_OT_pose_clear_guard, FSKR_OT_edge_move, FSKR_OT_arrange_exit,
           FSKR_OT_arrange_toggle,
           FSKR_OT_add_collection, FSKR_OT_del_collection,
           FSKR_OT_assign_collection,
           FSKR_OT_place_panel, FSKR_OT_attach_panel,
           FSKR_OT_reload_panel, FSKR_OT_repair_layout, FSKR_OT_sync_names, FSKR_OT_sync_colors,
           FSKR_OT_select_ctl, FSKR_OT_remove_ctl, FSKR_OT_remove_all,
           FSKR_OT_char_export, FSKR_OT_char_import,
           FSKR_OT_playback_add, FSKR_OT_playback_del,
           FSKR_OT_panel_rebind,
           FSKR_OT_save_default, FSKR_OT_reset_all, FSKR_OT_key_all,
           FSKR_OT_mocap_start, FSKR_OT_mocap_stop, FSKR_OT_mocap_automap,
           FSKR_OT_mocap_wizard, FSKR_OT_mocap_preset_key,
           FSKR_OT_mocap_calibrate, FSKR_OT_mocap_cal_clear,
           FSKR_OT_mocap_rec_start,
           FSKR_OT_simplify_curves, FSKR_OT_lipsync,
           FSKR_OT_lipsync_edit, FSKR_OT_lipsync_sound_del,
           FSKR_OT_lipsync_apply, FSKR_OT_lipsync_seek,
           FSKR_OT_mocap_map_add, FSKR_OT_mocap_map_del,
           ) + atlas_classes + vp_classes + eye_classes + face_classes + pvp_classes + lvp_classes + ime_classes + (
           FSKR_Prefs,
           FSKR_PT_mode,
           FSKR_PT_setup, FSKR_PT_list, FSKR_PT_atlas, FSKR_PT_presets,
           FSKR_PT_mocap, FSKR_PT_help)


addon_keymaps = []


_persist_handlers = []


@bpy.app.handlers.persistent
def _fskr_on_load(_dummy):
    """파일을 열 때마다 드라이버 네임스페이스가 초기화되므로 재설치."""
    _fskr_ns_install()
    # 이전 파일의 '지금 캐릭터' 기억을 이 파일 것으로 (다른 파일 리그와
    # 이름이 같아 엉뚱한 스냅샷을 쓰거나 되살리지 않게)
    try:
        from .core import _SWITCH
        r9 = getattr(bpy.context.scene.fskr, "rig", None)
        _SWITCH["rig"] = r9.name if r9 is not None else ""
        _SWITCH["busy"] = False
    except Exception:
        pass
    try:
        bpy.app.timers.register(_fskr_refresh_drivers,
                                first_interval=0.2)
    except Exception:
        pass


def register():
    from .core import app_handler_add, draw_add
    _fskr_ns_install()  # 클래스 등록 실패와 무관하게 항상 먼저
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.fskr = bpy.props.PointerProperty(type=FSKR_Settings)
    bpy.types.PoseBone.fskr_col = bpy.props.FloatVectorProperty(
        name=_tr("색상"), subtype='COLOR', size=3, min=0.0, max=1.0,
        default=(1.0, 0.85, 0.4), update=_col_update)
    bpy.types.PoseBone.fskr_sel = bpy.props.BoolProperty(
        name=_tr("선택"), default=False,
        description=_tr("컬렉션에 넣거나 뺄 컨트롤러 체크"))
    bpy.types.PoseBone.fskr_expand = bpy.props.BoolProperty(
        name=_tr("펼치기"), default=False,
        description=_tr("패드에 연결된 셰이프 키와 값 표시"))
    bpy.types.PoseBone.fskr_idx = bpy.props.IntProperty(
        name=_tr("순번"), min=0, get=_idx_get, set=_idx_set,
        description=_tr("목록 순번. 숫자를 고치면 그 위치로 끼어듭니다"))
    for _sl in _SLOT_ORDER:
        setattr(bpy.types.PoseBone, "fskr_si_" + _sl,
                bpy.props.IntProperty(
                    name=_tr("순번"), min=0,
                    get=_mk_slot_get(_sl), set=_mk_slot_set(_sl),
                    description=_tr("패드 슬롯 표시 순번. 숫자를 고치면 "
                                "그 위치로 끼어듭니다")))
    # 배치 모드에서 Ctrl+클릭 = 엣지 이동
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='Pose', space_type='EMPTY')
        # 배치 모드: 클릭이 변 화살표 위면 변 크기 조절, 아니면 일반 클릭
        kmi = km.keymap_items.new("fskr.edge_move", 'LEFTMOUSE', 'PRESS')
        addon_keymaps.append((km, kmi))
        # 배치 모드에서 G = 이동 (Ctrl=스냅, 조건 밖에서는 일반 G로 통과)
        kmi = km.keymap_items.new("fskr.snap_move", 'G', 'PRESS')
        addon_keymaps.append((km, kmi))
        # Alt+G/R/S: 몸 본과 함께 선택된 페이스 컨트롤러는 보호
        for ck, cw in (('G', 'LOC'), ('R', 'ROT'), ('S', 'SCALE')):
            kmi = km.keymap_items.new("fskr.pose_clear_guard", ck, 'PRESS',
                                      alt=True)
            kmi.properties.what = cw
            addon_keymaps.append((km, kmi))
        # 배치 모드에서 ESC / 우클릭 = 배치 모드 끄기 (조작 중이면 조작 취소가
        # 먼저 받음, 배치 모드가 아니면 원래 동작으로 통과)
        for ek in ('ESC', 'RIGHTMOUSE'):
            kmi = km.keymap_items.new("fskr.arrange_exit", ek, 'PRESS')
            addon_keymaps.append((km, kmi))
        # 캡처 중 숫자키 = 표정 프리셋 (0 = 기본 표정)
        digits = ('ZERO', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE',
                  'SIX', 'SEVEN', 'EIGHT', 'NINE')
        for di, dk in enumerate(digits):
            kmi = km.keymap_items.new("fskr.mocap_preset_key", dk, 'PRESS')
            kmi.properties.idx = di
            addon_keymaps.append((km, kmi))
        # 모드와 무관하게(오브젝트 모드 등) 캡처 중 프리셋 사용
        km2 = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
        for di, dk in enumerate(digits):
            kmi = km2.keymap_items.new("fskr.mocap_preset_key", dk,
                                       'PRESS')
            kmi.properties.idx = di
            addon_keymaps.append((km2, kmi))
        # 캔버스를 고른 오브젝트 모드에서 Ctrl+T = 파츠 자유 변형
        # (캔버스가 아니면 poll이 막혀 원래 Ctrl+T로 넘어감)
        km3 = kc.keymaps.new(name='Object Mode', space_type='EMPTY')
        kmi = km3.keymap_items.new("fskr.part_transform_key", 'T', 'PRESS',
                                   ctrl=True)
        addon_keymaps.append((km3, kmi))
    atlas_register()
    vp_register()
    over_register()
    face_register()
    pvp_register()
    lvp_register()
    ime_register()
    # 배치 모드 화살표 상시 표시
    _persist_handlers.append(draw_add(bpy.types.SpaceView3D, _draw_arrows, (),
                                      'WINDOW', 'POST_VIEW', "init_draw_arrows"))
    # 배치 모드 단축키 안내 (좌측 하단)
    _persist_handlers.append(draw_add(bpy.types.SpaceView3D, _draw_help_text, (),
                                      'WINDOW', 'POST_PIXEL', "init_draw_help_text"))
    # 언어 설정 적용 (환경설정에 저장된 언어로 라벨 재구성)
    _LANG_STATE["classes"] = classes
    try:
        bpy.app.timers.register(_retranslate, first_interval=0.1)
    except Exception:
        pass
    # iFacialMocap 수신 미리보기 (좌측 상단)
    _persist_handlers.append(draw_add(bpy.types.SpaceView3D, _draw_mocap_preview, (),
                                      'WINDOW', 'POST_PIXEL', "init_draw_mocap_preview"))
    # 녹화 카운트다운 표시 (뷰포트 중앙)
    _persist_handlers.append(draw_add(bpy.types.SpaceView3D, _draw_countdown, (),
                                      'WINDOW', 'POST_PIXEL', "init_draw_countdown"))



    try:
        bpy.app.timers.register(_fskr_refresh_drivers,
                                first_interval=0.2)
    except Exception:
        pass
    try:
        app_handler_add(bpy.app.handlers.load_post, _fskr_on_load)
    except Exception:
        pass
    try:
        app_handler_add(bpy.app.handlers.save_pre, _fskr_char_save_pre)
    except Exception:
        pass
    try:
        app_handler_add(bpy.app.handlers.depsgraph_update_post,
                        _fskr_char_autoswitch)
    except Exception:
        pass


def unregister():
    from .core import draw_remove
    try:
        if _fskr_on_load in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.remove(_fskr_on_load)
    except Exception:
        pass
    try:
        if _fskr_char_save_pre in bpy.app.handlers.save_pre:
            bpy.app.handlers.save_pre.remove(_fskr_char_save_pre)
    except Exception:
        pass
    try:
        h9 = bpy.app.handlers.depsgraph_update_post
        if _fskr_char_autoswitch in h9:
            h9.remove(_fskr_char_autoswitch)
    except Exception:
        pass
    _mocap_stop_sock()
    _lipsrv_stop()
    ime_unregister()
    lvp_unregister()
    pvp_unregister()
    face_unregister()
    over_unregister()
    vp_unregister()
    atlas_unregister()
    try:
        tx9 = bpy.data.textures.get("FSKR_wave_tex")
        if tx9 is not None:
            bpy.data.textures.remove(tx9)
        im9 = bpy.data.images.get("FSKR_wave")
        if im9 is not None:
            bpy.data.images.remove(im9)
    except Exception:
        pass
    bpy.app.driver_namespace.pop("fskr_pad", None)
    bpy.app.driver_namespace.pop("fskr_pofs", None)
    bpy.app.driver_namespace.pop("fskr_ssnap", None)
    bpy.app.driver_namespace.pop("fskr_z", None)
    for k9 in ("init_draw_arrows", "init_draw_help_text",
               "init_draw_mocap_preview", "init_draw_countdown"):
        draw_remove(k9)
    _persist_handlers.clear()
    for h in _persist_handlers_img:
        try:
            bpy.types.SpaceImageEditor.draw_handler_remove(h, 'WINDOW')
        except Exception:
            pass
    _persist_handlers_img.clear()
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
    for _sl in _SLOT_ORDER:
        delattr(bpy.types.PoseBone, "fskr_si_" + _sl)
    del bpy.types.PoseBone.fskr_idx
    del bpy.types.PoseBone.fskr_expand
    del bpy.types.PoseBone.fskr_sel
    del bpy.types.PoseBone.fskr_col
    del bpy.types.Scene.fskr
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
