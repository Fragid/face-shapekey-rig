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


PAD = 0.05   # 2D 패드 이동 범위 (±)


SLD = 0.08   # 1D 슬라이더 이동 범위 (0~)


TGL = 0.05   # 패널 ON/OFF 토글 슬라이더 이동 범위


NONE = "NONE"


_LANG_STATE = {"classes": (), "orig": {}}


_EN = {
    "패널 정렬 복구": "Repair panel alignment",
    "틀/핸들에 남은 포즈 회전을 초기화해 배치 모드 화살표와 스냅을 정상화합니다 (위치·크기·값은 유지)": "Clears leftover pose rotations on frames/handles so Arrange Mode arrows and snapping work again (positions, sizes and values are kept)",
    "패널 정렬 복구 완료 (%d개)": "Panel alignment repaired (%d bones)",
    "머리에 부착": "Attach to head",
    "패널이 따라갈 본": "Bone the panel follows",
    "패널을 본에 붙이기 (해제하려면 본을 비우고 실행)": "Attach the panel to a bone (run with empty bone to detach)",
    "패널 부착: ": "Panel attached: ",
    "패널 부착 해제": "Panel detached",
    "구동 방식": "Drive by",
    "위치 (이동)": "Location (move)",
    "회전 (머리 기준)": "Rotation (around head)",
    "본을 이동시킬지, 제자리에서 회전시킬지": "Move the bone, or rotate it in place",
    "가로 회전량 (도)": "Horizontal rotation (deg)",
    "세로 회전량 (도)": "Vertical rotation (deg)",
    " (%s 패드)": " (%s pad)",
    " (셰이프 키 없음 %d개 건너뜀)": " (%d skipped, shape keys missing)",
    " (컨트롤러 %d개 추가)": " (%d controllers added)",
    " (패드)": " (pad)",
    " [%s축]": " [%s]",
    "%d초 후 녹화 시작": "Recording starts in %d s",
    "%s: 대상 본 '%s'의 좌/우 짝을 리그 '%s'에서 찾지 못했습니다": "%s: no left/right pair for target bone '%s' in rig '%s'",
    "%s: 반대쪽 셰이프 키 '%s' 없음 (메시 '%s')": "%s: opposite shape key '%s' not found (mesh '%s')",
    "%s: 연쇄 셰이프 키 '%s' 없음 (메시 '%s')": "%s: chained shape key '%s' not found (mesh '%s')",
    "%s: 키 이름에서 '%s'/'%s'를 찾지 못했습니다": "%s: '%s'/'%s' not found in the connected key names",
    "'%s' 적용 (컨트롤러 %d개)": "Applied '%s' (%d controllers)",
    "'에' 채널 (조합)": "'Eh' channel (combo)",
    "(그룹 없음)": "(no group)",
    "(기존 그룹에서 선택)": "(pick existing group)",
    "(다수 선택됨)": "(Multiple Values)",
    "(변경 안 함)": "(No Change)",
    "(비어 있음)": "(empty)",
    "(사용 안 함)": "(unused)",
    "(선택된 텍스트)": "(Selected texts)",
    "(설정의 얼굴 메시)": "(Face Mesh from Setup)",
    "(아마추어 없음)": "(no armature)",
    "(없음)": "(None)",
    "(직접 지정)": "(Pick manually)",
    "(컨트롤러 없음)": "(no controllers)",
    "(컬렉션에서 제거)": "(Remove from collection)",
    "1프레임 뒤로": "1 frame back",
    "1프레임 앞으로": "1 frame forward",
    "2D 패드": "2D Pad",
    "2D 패드 추가": "Add 2D Pad",
    "3D 뷰포트 > N패널 > Face Rig 탭": "3D Viewport > N-panel > Face Rig tab",
    "3D 뷰포트에서 실행하세요": "Run this from a 3D viewport",
    "Calibrate (중립 캡처)": "Calibrate (neutral)",
    "FLAC (무손실)": "FLAC (lossless)",
    "G: 이동  (Ctrl = 모서리/중앙 스냅)": "G: move  (Ctrl = corner/center snap)",
    "JSON 레이아웃을 불러와 패널을 구성합니다. 같은 이름의 셰이프 키에 자동 연결되며, 없는 키의 컨트롤러는 건너뜁니다": "Build the panel from a JSON layout. Connects to shape keys with matching names; controllers with missing keys are skipped",
    "N패널 설정에서 지정한 메시의 셰이프 키 사용": "Use shape keys of the mesh set in the N-panel Setup",
    "R / S: 회전 / 크기": "R / S: rotate / scale",
    "WAV PCM %d비트": "WAV PCM %d-bit",
    "WAV를 읽을 수 없습니다: %s": "Cannot read WAV: %s",
    "[배치 모드]": "[Arrange Mode]",
    "iFacialMocap 수신 시작 (포트 49983)": "iFacialMocap receiving started (port 49983)",
    "iFacialMocap 수신 중지": "iFacialMocap receiving stopped",
    "iFacialMocap 수신을 시작합니다. 아이폰과 PC가 같은 와이파이에 있어야 하며, 앱이 켜져 있어야 합니다": "Starts receiving from iFacialMocap. iPhone and PC must be on the same Wi-Fi with the app running",
    "iFacialMocap 수신을 중지합니다": "Stops receiving from iFacialMocap",
    "iFacialMocap 앱 화면에 표시되는 아이폰의 IP 주소 (같은 와이파이여야 함)": "iPhone IP address shown in the iFacialMocap app (must be on the same Wi-Fi)",
    "iFacialMocap 캡처 중 숫자키로 표정 프리셋을 적용합니다 (1~9 = 프리셋 순번, 0 = 기본 표정). 캡처 중이 아니면 숫자키는 원래 기능대로 동작합니다": "Applies expression presets with number keys during iFacialMocap capture (1-9 = preset order, 0 = default expression). When not capturing, number keys work as usual",
    "jawOpen 등에서 자동 계산되는 '아' 채널": "'Ah' channel computed from jawOpen etc.",
    "mocap 녹화로 촘촘히 박힌 키프레임을 모양을 유지하는 한도 안에서 줄입니다 (핸들 위치·목 회전·셰이프 키 값). 그래프 에디터에서 손질하기 쉬워집니다": "Reduces the dense keyframes from mocap recording while preserving the curve shape (handle locations, neck rotation, shape key values). Makes curves easier to edit in the Graph Editor",
    "mouthFunnel에서 계산되는 '오' 채널": "'Oh' channel computed from mouthFunnel",
    "mouthPucker에서 계산되는 '우' 채널": "'Oo' channel computed from mouthPucker",
    "numpy를 사용할 수 없습니다": "numpy is not available",
    "← 왼쪽": "← Left",
    "↑ 위": "↑ Up",
    "→ 오른쪽": "→ Right",
    "↓ 아래": "↓ Down",
    "↖ 좌상": "↖ Up-Left",
    "↗ 우상": "↗ Up-Right",
    "↘ 우하": "↘ Down-Right",
    "↙ 좌하": "↙ Down-Left",
    "가로": "Horizontal",
    "가로 → 본 축": "H → Bone Axis",
    "가로 이동량": "H Distance",
    "가져오기 완료: 컨트롤러 %d개, 텍스트 %d개": "Import complete: %d controller(s), %d text(s)",
    "각 텍스트에서 가장 가까운 컨트롤러를 찾아 그 색을 자동으로 적용합니다 (색상을 사용하는 컨트롤러 기준)": "Apply to each text the color of its nearest controller (among controllers that use color)",
    "간단 자동 설정": "Quick Setup",
    "값": "Value",
    "값 −": "Value −",
    "값 단위 오차 한도. 클수록 키가 많이 줄어듭니다": "Error limit in value units. Higher removes more keys",
    "값 떨림 완화. 높을수록 부드럽지만 반응이 느려집니다": "Reduces jitter. Higher = smoother but slower response",
    "같은 그룹끼리 목록에서 묶어 표시 (비우면 그룹 없음)": "Group controllers together in the list (empty = no group)",
    "같은 이름의 프리셋이 있습니다": "A preset with that name already exists",
    "갸웃 →": "Tilt →",
    "갸웃 방향 반전": "Invert tilt direction",
    "구간 앞뒤로 이만큼의 프레임에 걸쳐 부드럽게 전환": "Smoothly transition over this many frames before and after each segment",
    "구간 적용 (다시 굽기)": "Apply Segments (Re-bake)",
    "구간으로 이동": "Jump to Segment",
    "그래프 에디터를 새 창으로 열어 모음 구간을 편집합니다. 사이드바의 Face Rig 탭에 구간 목록이 있습니다": "Opens the Graph Editor in a new window to edit vowel segments. The segment list is in the Face Rig tab of the sidebar",
    "그룹": "Group",
    "기본 표정으로": "Back to default expression",
    "기본값으로 되돌리기": "Reset to Default",
    "기존 그룹": "Existing Group",
    "기존 그룹/컬렉션에서 골라 채웁니다": "Pick from existing groups/collections",
    "끄덕임 →": "Nod →",
    "끄덕임 방향 반전": "Invert nod direction",
    "끔": "Off",
    "끝 프레임": "End Frame",
    "내용": "Content",
    "노란 화살표 드래그: 변 크기 조절  (Ctrl = 스냅, Alt = 대칭)": "Drag yellow arrow: resize edge  (Ctrl = snap, Alt = symmetric)",
    "녹화": "Record",
    "녹화 시작": "Start Recording",
    "녹화 시작 버튼을 누른 뒤 재생까지의 대기 시간 (0 = 즉시 시작)": "Delay between pressing Start Recording and playback (0 = immediate)",
    "녹화 정지": "Recording stopped",
    "녹화 커브 단순화": "Simplify Recorded Curves",
    "눈": "Eyes",
    "눈 리그": "Eye Rig",
    "눈 회전 반영 정도": "How much eye rotation is applied",
    "눈동자": "Pupils",
    "눈썹": "Brows",
    "눈알 본이 들어있는 아마추어": "Armature that contains the eyeball bones",
    "눈알 본이 바라보는 방향의 로컬 축": "Local axis the eyeball bone looks along",
    "단순화할 커브가 없습니다": "No curves to simplify",
    "닫기": "Close",
    "대기 중 (앱/와이파이/IP 확인)": "Waiting (check app / Wi-Fi / IP)",
    "대사 녹음(WAV)을 분석해 A/I/U/E/O 립싱크 키프레임을 자동 생성합니다. '간단 자동 설정'의 입 매핑을 그대로 사용하므로 먼저 매핑을 만들어 두세요": "Analyzes a dialogue recording (WAV) and auto-generates A/I/U/E/O lipsync keyframes. Uses the mouth mapping from Quick Setup, so create the mapping first",
    "대사 녹음(WAV/MP3/OGG/FLAC)을 분석해 A/I/U/E/O 립싱크 키프레임을 자동 생성합니다. '간단 자동 설정'의 입 매핑을 그대로 사용하므로 먼저 매핑을 만들어 두세요": "Analyzes a dialogue recording (WAV/MP3/OGG/FLAC) and auto-generates A/I/U/E/O lipsync keyframes. Uses the mouth mapping from Quick Setup, so create the mapping first",
    "대상": "Target",
    "대상 리그": "Target Rig",
    "대상 리그를 선택하세요": "Select a target rig",
    "대상 본 1": "Target Bone 1",
    "대상 본 1을 선택하세요": "Select target bone 1",
    "대상 본 2 (선택)": "Target Bone 2 (optional)",
    "대상 본 이름에서 좌/우 짝(.l/.r 등)을 찾지 못했습니다": "No left/right pair (.l/.r etc.) found in target bone names",
    "대상 본을 찾을 수 없습니다": "Target bone not found",
    "대상 컬렉션": "Target Collection",
    "대상 텍스트": "Target Text",
    "대상 텍스트가 없습니다 (팝업에서 텍스트를 선택하세요)": "No target text (choose one in the popup)",
    "돌림 →": "Turn →",
    "돌림 방향 반전": "Invert turn direction",
    "드래그 = 범위 선택 · 클릭 = 이동/선택 해제 · 선택 드래그 = 범위 이동 · + = 구간 추가 · ✂ = 잘라내기 · 패드 = 입모양 · ★ = 즐겨찾기 (우클릭 편집) · Ctrl+Z = 실행취소 · Ctrl+C/V = 복사/붙여넣기 · Del = 삭제 · Space = 재생 · 휠 = 줌 · 휠 클릭 = 패닝": "Drag = select range · Click = seek/deselect · Drag selection = move range · + = add segment · ✂ = cut · Pad = mouth shape · ★ = favorites (right-click to edit) · Ctrl+Z = undo · Ctrl+C/V = copy/paste · Del = delete · Space = play · Wheel = zoom · Middle-drag = pan",
    "라벨": "Label",
    "라벨을 셰이프 키(또는 대상 본) 이름으로 채웁니다": "Fills the label with the shape key (or target bone) name",
    "레이아웃 가져오기": "Import Layout",
    "레이아웃 내보내기": "Export Layout",
    "레이아웃 저장: 컨트롤러 %d개, 텍스트 %d개": "Layout saved: %d controller(s), %d text(s)",
    "레이아웃 파일이 아닙니다": "Not a layout file",
    "루프": "Loop",
    "리그": "Rig",
    "립싱크 구간": "Lipsync Segments",
    "립싱크 구간 편집": "Edit Lipsync Segments",
    "립싱크 다시 굽기 완료 (%d프레임)": "Lipsync re-baked (%d frames)",
    "립싱크 데이터가 없습니다": "No lipsync data",
    "립싱크 사운드 제거": "Remove Lipsync Sound",
    "립싱크 생성: %d프레임 (%.1f초). 필요하면 '녹화 커브 단순화'로 정리하세요": "Lipsync generated: %d frames (%.1f s). Use 'Simplify Recorded Curves' to clean up if needed",
    "립싱크 자동 재계산": "Auto-recalculate lipsync",
    "립싱크 키 구간과 겹칩니다. 녹화가 립싱크 키를 덮어쓸 수 있습니다": "Overlaps the baked lipsync range. Recording may overwrite lipsync keys",
    "립싱크 편집 창 열기": "Open Lipsync Editor Window",
    "립싱크 편집기": "Lipsync Editor",
    "립싱크 편집기 열기": "Open Lipsync Editor",
    "립싱크 편집기 재생": "Lipsync Editor Play",
    "립싱크 편집기 클릭": "Lipsync Editor Click",
    "매핑 %d개 생성 완료": "Created %d mapping(s)",
    "매핑 (ARKit → 컨트롤러)": "Mapping (ARKit → Controller)",
    "매핑 삭제": "Delete Mapping",
    "매핑 추가": "Add Mapping",
    "머리 본": "Head Bone",
    "머리 회전 반영 정도. 방향이 반대면 음수로": "How much head rotation is applied. Use negative if reversed",
    "머리 회전을 따라 돌 본 (예: c_head.x, neck)": "Bone that follows head rotation (e.g. c_head.x, neck)",
    "머리 회전을 적용할 본이 있는 아마추어": "Armature containing the bone that receives head rotation",
    "머리/목 회전": "Head/Neck Rotation",
    "먼저 컨트롤러 옆 체크박스를 선택하세요": "Check some controllers in the list first",
    "메시": "Mesh",
    "모노": "Mono",
    "모든 라벨 텍스트 표시/숨김": "Show/hide all label texts",
    "모든 컨트롤러/라벨/위젯과 셰이프 키 드라이버를 제거합니다": "Remove all controllers/labels/widgets and shape key drivers",
    "모든 컨트롤러를 저장된 기본값으로 되돌립니다. 저장된 기본값이 없으면 0으로 (키프레임은 지우지 않음)": "Reset all controllers to their saved defaults, or to 0 if none saved (keyframes are kept)",
    "모음": "Vowel",
    "목 리그": "Neck Rig",
    "목 본": "Neck Bone",
    "목록 순번. 숫자를 고치면 그 위치로 끼어듭니다": "List position. Edit the number to insert at that spot",
    "목록에 표시할 이름 (비우면 대상 본 이름)": "Name shown in the list (empty = target bone name)",
    "목록에서 이름 클릭 = 뷰포트에서 선택": "Click a name in the list = select in viewport",
    "목록에서 컨트롤러 순서를 위/아래로 이동합니다 (같은 그룹 안에서, Shift = 맨 위/맨 아래로)": "Move the controller up/down in the list (within its group, Shift = jump to top/bottom)",
    "무음 임계값": "Silence Threshold",
    "무음화": "Silence",
    "무음화 (길이 유지)": "Silence (keep length)",
    "무표정으로 카메라를 정면으로 본 상태에서 누르세요. 지금 값을 기준(0)으로 저장해서 이후 수신값을 보정합니다. 씬에 저장되어 다음에도 유지됩니다": "Press while facing the camera with a neutral expression. Stores the current values as the zero baseline and corrects all incoming data. Saved with the scene",
    "미러 아이콘 = 반대쪽 컨트롤러 자동 생성": "Mirror icon = auto-create opposite controller",
    "미러 취소 — ": "Mirror cancelled — ",
    "미리보기 도식의 표시 배율": "Display scale of the preview schematic",
    "미리보기 크기": "Preview Size",
    "미지정 (입 다묾)": "Unassigned (mouth closed)",
    "반대쪽 셰이프 키가 없습니다: ": "Opposite shape key not found: ",
    "반대쪽 자동 생성": "Mirror Controller",
    "반대쪽 컨트롤러 생성: ": "Mirrored controller created: ",
    "반전": "Invert",
    "방향": "Direction",
    "방향 반전": "Invert Direction",
    "방향을 하나 이상 연결하세요": "Connect at least one direction",
    "배율": "Factor",
    "배치 모드": "Arrange Mode",
    "배치 모드 ON = 틀을 G/R/S로 자유 배치": "Arrange Mode ON = place frames with G/R/S",
    "배치 모드: G 이동 중 Ctrl = 모서리 스냅": "Arrange: hold Ctrl while G-moving = corner snap",
    "배치 모드: 노란 화살표 드래그 = 그 변만 크기 조절": "Arrange: drag yellow arrow = resize that edge",
    "배치 모드에서 G로 틀을 이동합니다. Shift를 누르는 동안 다른 틀 모서리에 스냅됩니다": "Move the frame with G in Arrange Mode. Hold Ctrl to snap to other frame corners",
    "배치 모드에서 선택된 틀의 변 화살표를 드래그해 그 변만 이동합니다. Ctrl을 누르는 동안 다른 틀 모서리에 스냅됩니다": "Drag an edge arrow of the selected frame in Arrange Mode to move only that edge. Hold Ctrl to snap to other corners",
    "배치 순서로 정렬": "Sort by Layout",
    "범위 적용": "Apply Range",
    "베이크할 드라이버가 없습니다": "No drivers to bake",
    "변 드래그 중 Ctrl = 스냅, Alt = 대칭 조절": "Edge drag: Ctrl = snap, Alt = symmetric",
    "변 이동: 드래그=크기 조절, Ctrl=스냅, Alt=대칭 조절, 놓으면 확정, ESC 취소": "Edge move: drag=resize, Ctrl=snap, Alt=symmetric, release=confirm, ESC=cancel",
    "변 크기 조절": "Resize Edge",
    "보정 해제": "Clear Calibration",
    "본 패드": "Bone Pad",
    "본 패드 = 핸들 XY로 본(눈알 타겟) 이동": "Bone pad = move bones (eye target) via handle XY",
    "본 패드 추가": "Add Bone Pad",
    "본 패드 추가: ": "Bone pad added: ",
    "본을 만들 리그": "Rig for the Bone",
    "본을 만들 리그를 선택하세요": "Select a rig for the bone",
    "볼륨": "Volume",
    "뷰포트 배치 위치(위→아래, 왼쪽→오른쪽) 순서대로 목록 순서를 자동 정렬합니다 (그룹별)": "Auto-sort the list by viewport placement (top to bottom, left to right, per group)",
    "뷰포트 색상 다시 불러오기": "Resync Viewport Colors",
    "뷰포트 패널 리로드": "Reload Viewport Panel",
    "뷰포트 패널 컨트롤러를 움직임 (키프레임은 핸들에 기록)": "Moves a viewport panel controller (keyframes go on the handle)",
    "뷰포트에 크로스헤어가 나타납니다. 클릭한 위치에 패널이 생성되고, 이미 있으면 패널 전체가 그곳으로 이동합니다. 우클릭/ESC = 취소": "A crosshair appears in the viewport. The panel is created at the clicked position, or moved there if it already exists. Right-click/ESC = cancel",
    "뷰포트에서 이 컨트롤러를 선택합니다 (배치 모드면 틀을 선택)": "Select this controller in the viewport (frame in Arrange Mode)",
    "브라우저에 전용 립싱크 편집기를 엽니다. 파형과 모음 구간을 보며 구간을 클릭해 A/I/U/E/O를 바꾸고, 적용을 누르면 Blender에 다시 굽습니다": "Opens the dedicated lipsync editor in your browser. View the waveform and vowel segments, click segments to change A/I/U/E/O, and press Apply to re-bake into Blender",
    "브라우저에서 립싱크 편집기를 열었습니다": "Lipsync editor opened in your browser",
    "블렌딩": "Blend",
    "비우고 적용하면 그룹에서 빠집니다": "Apply with an empty value to remove from the group",
    "비우면 컨스트레인트 생략": "Leave empty to skip the constraint",
    "사용": "Enable",
    "사운드 스트립 %d개 제거": "Removed %d sound strip(s)",
    "사운드 스트립 추가": "Add Sound Strip",
    "삭제": "Delete",
    "상/하/좌/우 방향별 연결": "Connect keys per direction",
    "상/하/좌/우 방향별로 셰이프 키를 연결한 XY 패드를 추가합니다. 같은 키를 상+하(또는 좌+우)에 넣으면 -1~1 풀레인지로 동작합니다": "Add an XY pad with shape keys per direction. Same key on up+down (or left+right) gives -1 to 1 full range",
    "상하 반전": "Invert V",
    "새 이름": "New Name",
    "새 컬렉션을 만듭니다. 체크한 컨트롤러가 있으면 바로 담습니다": "Create a new collection. Checked controllers are added to it",
    "색상": "Color",
    "색상 사용": "Use Color",
    "색상을 사용하는 컨트롤러가 없습니다": "No controllers using color",
    "선택": "Check",
    "선택 → 컬렉션": "Checked → Collection",
    "선택 범위 립싱크 재계산 (선택 없으면 전체)": "Recalculate lipsync for selected range (whole if none)",
    "선택 범위 볼륨 조절 (선택 없으면 전체) · 립싱크 재계산": "Adjust volume of selected range (whole audio if none) · lipsync recalculated",
    "선택 범위 잘라내기 (오디오 포함) · 선택 없으면 타임바에서 분할": "Cut selected range (including audio) · without a selection, split at the playhead",
    "선택됨: %d개": "Selected: %d",
    "선택한 셰이프 키를 조절하는 1D 슬라이더를 추가합니다": "Add a 1D slider controlling the selected shape key",
    "선택한 셰이프 키를 찾을 수 없습니다": "Selected shape keys not found",
    "설정": "Settings",
    "설정에서 좌/우 포함식을 입력하세요": "Set the left/right tokens in Settings first",
    "성분": "Component",
    "세로": "Vertical",
    "세로 → 본 축": "V → Bone Axis",
    "세로 이동량": "V Distance",
    "셰이프 키": "Shape Key",
    "셰이프 키 %d개 + 본 채널 %d개 x %d프레임 베이크 완료. 드라이버 제거됨 — 패널 복구는 '뷰포트 패널 리로드'": "Baked %d shape keys + %d bone channels x %d frames. Drivers removed — use 'Reload Viewport Panel' to restore",
    "셰이프 키 %d개 x %d프레임 베이크 완료. 드라이버 제거됨 — 패널 복구는 '뷰포트 패널 리로드'": "Baked %d shape keys x %d frames. Drivers removed - restore the panel with 'Reload Viewport Panel'",
    "셰이프 키 값을 직접 움직임 (패널 컨트롤러 불필요)": "Drives the shape key value directly (no panel controller needed)",
    "셰이프 키 대상일 때: 키가 있는 메시": "For shape key targets: the mesh that has the key",
    "셰이프 키 베이크 (익스포트용)": "Bake Shape Keys (for export)",
    "셰이프 키 연결에 실패했습니다": "Failed to connect shape keys",
    "셰이프 키 이름 동기화": "Sync Shape Key Names",
    "셰이프 키 이름 복사": "Copy Shape Key Name",
    "셰이프 키 이름과 ARKit 이름을 비교해 매핑을 자동으로 채웁니다 (기존 매핑은 교체). 눈동자 패드 등은 수동으로 추가하세요": "Fills the mapping by comparing shape key names with ARKit names (replaces existing mapping). Add eye pads etc. manually",
    "셰이프 키 이름에서 오른쪽을 뜻하는 부분 (예: (Right), .R, _right)": "Substring meaning right in shape key names (e.g. (Right), .R, _right)",
    "셰이프 키 이름에서 왼쪽을 뜻하는 부분 (예: (Left), .L, _left)": "Substring meaning left in shape key names (e.g. (Left), .L, _left)",
    "셰이프 키 이름을 바꾼 뒤 실행하세요. 드라이버가 실제로 연결된 키 이름을 읽어 목록/메타데이터를 갱신합니다": "Run after renaming shape keys. Reads the key names the drivers are actually connected to and updates the list/metadata",
    "셰이프 키를 가져올 메시 (기본 = 설정의 얼굴 메시)": "Mesh to take shape keys from (default = the Face Mesh in Setup)",
    "셰이프 키를 골라 1D 슬라이더/2D 패드 컨트롤러를 뷰포트에 조립하는 빌더": "Builder for in-viewport 1D slider / 2D pad controllers driving shape keys",
    "셰이프 키를 선택하세요": "Select a shape key",
    "셰이프 키를 찾을 수 없습니다": "Shape key not found",
    "수신 미리보기": "Live Preview",
    "수신 중": "Receiving",
    "수신 중인 표정 값을 뷰포트 좌상단에 도식으로 표시": "Shows incoming expression values as a schematic in the viewport corner",
    "수신 중인 표정 값을 뷰포트에 도식으로 표시": "Shows incoming expression values as a schematic in the viewport",
    "수신된 데이터가 없습니다": "No data received yet",
    "순번": "Index",
    "순서 이동": "Move in List",
    "숫자키 1~9 = 표정 프리셋, 0 = 기본 표정": "Number keys 1-9 = presets, 0 = default expression",
    "스냅 이동": "Snap Move",
    "스냅 적용": "Apply Snap",
    "스무딩": "Smoothing",
    "스크럽 소리": "Scrub Audio",
    "스포이드": "Eyedropper",
    "슬라이더 (가로)": "Slider (Horizontal)",
    "슬라이더 (세로)": "Slider (Vertical)",
    "슬라이더 값 (반전/양방향 자동 반영)": "Slider value (invert/bidirectional handled automatically)",
    "슬라이더 값에 곱해질 배율 (음수 = 반대로 움직임)": "Factor multiplied with the slider value (negative = moves opposite)",
    "슬라이더 최솟값<0 = 양방향 (중앙이 0)": "Slider min<0 = bidirectional (center is 0)",
    "슬라이더 추가": "Add Slider",
    "슬라이더 추가: ": "Slider added: ",
    "슬라이더는 '값', 패드는 방향 성분을 고르세요": "Use 'Value' for sliders, or a direction component for pads",
    "슬롯에 연결된 A/I/U/E/O 키의 방향을 읽어 자동 매핑": "Reads which direction each A/I/U/E/O key sits on and maps automatically",
    "시작 프레임": "Start Frame",
    "시작 프레임으로 이동해 카운트다운 후 재생과 녹화를 시작합니다. 다시 누르면 취소/정지되고, End Frame에 도달하면 자동으로 멈춥니다": "Jumps to the start frame, counts down, then starts playback and recording. Press again to cancel/stop; stops automatically at the End Frame",
    "시퀀서에 넣은 립싱크 사운드 스트립을 제거합니다. 타임라인 스크럽 시 소리가 나지 않게 됩니다": "Removes the lipsync sound strip from the sequencer so scrubbing the timeline no longer plays audio",
    "시퀀서에 오디오를 넣어 재생 시 소리가 같이 나오게 합니다": "Adds the audio to the sequencer so it plays along",
    "아래 (Y-)": "Down (Y-)",
    "아래 색상 필드로 직접 선택": "Choose with the color field below",
    "아래→위": "Bottom to top",
    "아래에서 위로 0~1": "0 to 1, bottom to top",
    "아이폰 IP": "iPhone IP",
    "아이폰 IP를 입력하세요 (앱 화면에 표시됨)": "Enter the iPhone IP (shown in the app)",
    "애니메이션 재생 중일 때 매핑된 핸들에 키프레임을 기록합니다 (스페이스바로 재생하며 연기하세요)": "Inserts keyframes on mapped handles while the animation is playing (press Space to play, then perform)",
    "앵커 스냅 임계값": "Anchor Snap Threshold",
    "양방향 슬라이더의 음수 방향으로": "Negative direction of a bidirectional slider",
    "어니언 스킨": "Onion Skin",
    "얼굴 메시": "Face Mesh",
    "역할": "Role",
    "역할별로 컨트롤러만 고르면 ARKit 매핑을 자동으로 만들어 줍니다. 입 모양은 A/I/U/E/O 조합 채널로 연결되고, 컨트롤러 이름으로 미리 추측해서 채워둡니다": "Pick a controller per role and the ARKit mapping is generated automatically. Mouth shapes use combined A/I/U/E/O channels, and fields are pre-filled by guessing from controller names",
    "연결 시작": "Start Connection",
    "연결 안 함": "Not connected",
    "연결된 키 이름에서 '%s' / '%s' 를 찾지 못했습니다": "Could not find '%s' / '%s' in connected key names",
    "연결할 셰이프 키(또는 대상 본)가 없습니다": "No shape key (or target bone) to connect",
    "연결할 셰이프 키가 없습니다": "No shape keys to connect",
    "연쇄 드라이버": "Chain Drivers",
    "연쇄 셰이프 키가 있는 메시 (기본 = 설정의 얼굴 메시)": "Mesh that has the chained shape key (default = the Face Mesh in Setup)",
    "연쇄 추가": "Add Chain",
    "연필 아이콘 = 타입/키/라벨 수정": "Pencil icon = edit type/keys/label",
    "영역 선택 모드 (끄면 드래그 = 스크럽)": "Range select mode (off: drag = scrub)",
    "오디오 립싱크 생성": "Generate Audio Lipsync",
    "오디오: 파일 없음": "Audio: no file",
    "오디오가 너무 짧습니다": "Audio is too short",
    "오디오를 읽을 수 없습니다: %s": "Cannot read the audio: %s",
    "오른눈 감기": "Right Eye Blink",
    "오른눈 눈동자 패드": "Right Eye Pad",
    "오른눈 본": "Right Eye Bone",
    "오른눈썹 (위/아래)": "Right Brow (Up/Down)",
    "오른쪽 (X+)": "Right (X+)",
    "오브젝트 모드에서 선택한 텍스트에 적용": "Apply to texts selected in Object Mode",
    "오토 키": "Auto Key",
    "왼눈 감기": "Left Eye Blink",
    "왼눈 눈동자 패드": "Left Eye Pad",
    "왼눈 본": "Left Eye Bone",
    "왼눈썹 (위/아래)": "Left Brow (Up/Down)",
    "왼쪽 (X-)": "Left (X-)",
    "왼쪽→오른쪽": "Left to right",
    "왼쪽에서 오른쪽으로 0~1": "0 to 1, left to right",
    "우": "R",
    "우상 (대각)": "Up-Right (diag)",
    "우상단 빨간 토글 오른쪽으로 = 패널 숨김": "Red toggle (top-right) to the right = hide panel",
    "우측 포함식": "Right Token",
    "우하 (대각)": "Down-Right (diag)",
    "움직일 본이 들어있는 아마추어": "Armature that contains the target bone",
    "움직일 본이 들어있는 아마추어 (설정의 리그와 달라도 됨)": "Armature that contains the bone to move (can differ from the Rig in Setup)",
    "원본": "Original",
    "위 (Y+)": "Up (Y+)",
    "위아래 끄덕임(피치)을 보낼 본 로컬 축": "Bone local axis that receives up/down nodding (pitch)",
    "위치 갱신": "Update position",
    "음수 = 반대 방향": "Negative = opposite direction",
    "음수로 하면 양방향 슬라이더가 됩니다 (중앙=0)": "Negative makes a bidirectional slider (center=0)",
    "음수로 하면 양방향 슬라이더가 됩니다 (중앙=0). 셰이프 키 자체의 Range Min도 음수여야 합니다": "Negative makes a bidirectional slider (center=0). The shape key Range Min must also be negative",
    "이 ARKit 값이 움직일 컨트롤러": "Controller driven by this ARKit value",
    "이 구간의 시작 프레임으로 이동합니다": "Jumps to the start frame of this segment",
    "이 방향 키에만 곱해질 배율 (전체 배율과 곱해짐)": "Multiplier for this direction only (multiplied with the overall factor)",
    "이 슬라이더 값에 배율을 곱해 함께 움직일 셰이프 키": "Shape key that follows this slider (value × factor)",
    "이 슬라이더 값을 따라 함께 움직일 셰이프 키를 추가합니다": "Adds a shape key that follows this slider's value",
    "이 슬라이더를 따라 움직일 키를 + 로 추가": "Press + to add keys that follow this slider",
    "이 컨트롤러와 연결된 드라이버를 제거합니다 (셰이프 키는 유지)": "Remove this controller and its drivers (shape keys are kept)",
    "이 컨트롤러와 연결된 드라이버를 제거합니다 (셰이프 키는 유지). 체크된 항목이 2개 이상이면 체크된 것들을 한꺼번에 삭제합니다": "Removes this controller and its drivers (shape keys are kept). If 2+ items are checked, deletes all checked controllers at once",
    "이동": "Move",
    "이동 방향을 반대로 (가로: 오른쪽→왼쪽, 세로: 위→아래). 원점은 항상 값 0": "Reverse travel direction (H: right to left, V: top to bottom). Origin is always value 0",
    "이동 방향을 반대로 (원점은 항상 값 0)": "Reverse travel direction (origin is always value 0)",
    "이동%s: Ctrl=스냅, X/Y/Z=축 고정, 클릭=확정, ESC=취소": "Move%s: Ctrl=snap, X/Y/Z=axis lock, Click=confirm, ESC=cancel",
    "이동: Ctrl=모서리 스냅, X/Y/Z=축 고정, 클릭=확정, 우클릭/ESC=취소": "Move: Ctrl=snap, X/Y/Z=axis lock, Click=confirm, RMB/ESC=cancel",
    "이동량 적용": "Apply Distance",
    "이름 갱신 %d건": "%d name(s) updated",
    "이름 변경: ": "Renamed: ",
    "이름을 입력하세요": "Enter a name",
    "일괄 수정 (체크된 항목)": "Batch Edit (Checked)",
    "일괄 수정: %d개 적용": "Batch edit applied to %d controller(s)",
    "일시정지": "Pause",
    "입 (모음)": "Mouth (vowels)",
    "입 A (아)": "Mouth A (ah)",
    "입 E (에)": "Mouth E (eh)",
    "입 I (이)": "Mouth I (ee)",
    "입 O (오)": "Mouth O (oh)",
    "입 U (우)": "Mouth U (oo)",
    "입 모음 매핑이 없습니다. iFacialMocap 패널의 '간단 자동 설정'으로 먼저 만들어 주세요": "No mouth vowel mapping. Create it first with Quick Setup in the iFacialMocap panel",
    "입 벌림 배율": "Mouth Open Gain",
    "입 움직임 완화. 높을수록 부드럽지만 둔해집니다": "Smooths mouth motion. Higher = softer but less responsive",
    "입 패드 (모음 자동 배치)": "Mouth Pad (auto vowels)",
    "입꼬리 당김에서 계산되는 '이' 채널": "'Ee' channel computed from mouth stretch/smile",
    "입모양 A (조합)": "Mouth A (combo)",
    "입모양 E (조합)": "Mouth E (combo)",
    "입모양 I (조합)": "Mouth I (combo)",
    "입모양 O (조합)": "Mouth O (combo)",
    "입모양 U (조합)": "Mouth U (combo)",
    "자동 매핑": "Auto Map",
    "자동 매핑 %d개 (나머지는 +로 수동 추가)": "Auto-mapped %d (add the rest manually with +)",
    "자동 매핑(마법봉) 또는 +로 추가하세요": "Use Auto Map (wand) or + to add mappings",
    "자동 배치된 모음 구간을 확인하고 바꿉니다. 프레임 숫자 클릭 = 그 지점으로 이동, 모음을 고치고 OK를 누르면 키프레임을 다시 굽습니다": "Review and change the auto-assigned vowel segments. Click a frame number to jump there; change vowels and press OK to re-bake",
    "자유 배치 가능한 라벨 텍스트를 만듭니다. 오브젝트 모드에서 G/S로 배치·크기 조절, Tab으로 내용 수정, 폰트는 폰트 속성에서": "Create a freely placeable label text. In Object Mode use G/S to place/scale, Tab to edit content, font in Font properties",
    "잘라내기": "Cut",
    "잘라내기 (길이 단축)": "Cut (shorten length)",
    "재계산": "Recalculate",
    "재계산 결과가 무음이라 중단했습니다. 진단: len=%d sr=%s fps=%.2f peak=%.4f frames=%d": "Recalculation produced silence; aborted. Diag: len=%d sr=%s fps=%.2f peak=%.4f frames=%d",
    "재생": "Play",
    "저장된 설정으로 모든 컨트롤러를 다시 구성합니다. 위젯/드라이버/토글 연결을 최신 버전 방식으로 재적용합니다": "Rebuild all controllers from stored settings. Re-applies widgets/drivers/toggle wiring with the current version",
    "저장된 표정 프리셋을 컨트롤러에 적용합니다": "Apply a saved expression preset to the controllers",
    "저장된 프리셋이 없습니다": "No saved presets",
    "적용 (다시 굽기)": "Apply (Re-bake)",
    "적용 중...": "Applying...",
    "전용 립싱크 편집 창을 엽니다. 파형과 모음 구간을 보며 구간을 클릭해 A/I/U/E/O를 바꿀 수 있습니다": "Opens the dedicated lipsync editor window. View the waveform and vowel segments, click a segment and change A/I/U/E/O",
    "전체 입 벌림 강도": "Overall mouth opening strength",
    "정지": "Stop",
    "조작법": "How to Use",
    "좌": "L",
    "좌/우 포함식을 바꿔 반대쪽 셰이프 키를 찾아, 같은 설정과 색상으로 반대쪽 컨트롤러를 만듭니다 (위치는 패널 중심 기준 미러)": "Swap the left/right tokens to find opposite shape keys and create a mirrored controller with the same settings and color",
    "좌/우 포함식을 바꿔 반대쪽 셰이프 키를 찾아, 같은 설정과 색상으로 반대쪽 컨트롤러를 만듭니다 (위치는 패널 중심 기준 미러). 체크된 항목이 2개 이상이면 체크된 것들을 한꺼번에 미러합니다": "Finds the opposite shape key by swapping the L/R tokens and creates a mirrored controller with the same settings and color. If 2+ items are checked, mirrors all checked controllers at once",
    "좌상 (대각)": "Up-Left (diag)",
    "좌우 갸웃(롤)을 보낼 본 로컬 축": "Bone local axis that receives head tilting (roll)",
    "좌우 돌림(요)을 보낼 본 로컬 축": "Bone local axis that receives left/right turning (yaw)",
    "좌우 반전": "Invert H",
    "좌측 포함식": "Left Token",
    "좌하 (대각)": "Down-Left (diag)",
    "중앙 (원점)": "Center (origin)",
    "중지": "Stop",
    "즐겨찾기 수정": "Edit favorites",
    "즐겨찾기 이름:": "Favorite name:",
    "지금의 컨트롤러 위치들을 기본 표정으로 저장합니다. '기본값으로 되돌리기'가 이 상태로 복원합니다": "Store current controller positions as the default pose. 'Reset to Default' restores this state",
    "직접 움직일 셰이프 키": "Shape key to drive directly",
    "체크된 컨트롤러가 없습니다": "No controllers are checked",
    "체크된 컨트롤러들을 한 번에 수정합니다 (체크된 항목의 연필 버튼으로 열림). 같은 타입끼리만 가능하며, 값이 서로 다른 항목은 '(다수 선택됨)'으로 표시됩니다": "Edits all checked controllers at once (opened via the pencil button of a checked item). Only controllers of the same type can be edited together; fields with differing values show '(Multiple Values)'",
    "체크된 컨트롤러들을 한 번에 수정합니다. 같은 타입끼리만 가능하며, 값이 서로 다른 항목은 '(다수 선택됨)'으로 표시됩니다": "Edits all checked controllers at once. Only controllers of the same type can be edited together; fields with differing values show '(Multiple Values)'",
    "체크하고 OK를 누르면 이 연쇄가 삭제됩니다": "Check and press OK to remove this chain",
    "체크한 컨트롤러들을 선택한 컬렉션에 넣거나 뺍니다": "Move checked controllers into or out of a collection",
    "체크한 컨트롤러를 컬렉션 밖으로": "Move checked controllers out of their collection",
    "최대 음량 대비 이 비율 아래면 입을 다뭅니다": "Below this ratio of the peak volume the mouth closes",
    "최댓값": "Max Value",
    "최댓값이 최솟값보다 커야 합니다": "Max value must be greater than min value",
    "최솟값": "Min Value",
    "추가된 컨트롤러가 없습니다": "No controllers yet",
    "축 적용": "Apply Axes",
    "카운트다운 (초)": "Countdown (sec)",
    "카운트다운 취소": "Countdown cancelled",
    "캘리브레이션 보정을 지우고 원본 수신값을 사용합니다": "Removes the calibration and uses raw incoming values",
    "캘리브레이션 완료: 지금 표정이 기준이 됩니다": "Calibrated: the current expression is now the baseline",
    "캘리브레이션 적용 중": "Calibration active",
    "캘리브레이션 해제": "Calibration cleared",
    "캡처 중 프리셋 적용": "Apply Preset During Capture",
    "커브 %d개: 키 %d개 → %d개 (%d개 제거)": "%d curves: %d keys → %d (%d removed)",
    "컨트롤러": "Controller",
    "컨트롤러 %d개 → '%s'": "%d controller(s) → '%s'",
    "컨트롤러 %d개 삭제": "Deleted %d controller(s)",
    "컨트롤러 %d개 정렬 완료": "Sorted %d controller(s)",
    "컨트롤러 %d개를 컬렉션에서 제거": "Removed %d controller(s) from collection",
    "컨트롤러 %d개에 키프레임 삽입": "Inserted keyframes on %d controller(s)",
    "컨트롤러 %d개의 기본값 저장 완료": "Saved defaults for %d controller(s)",
    "컨트롤러 %d개의 색상 동기화 완료": "Synced colors of %d controller(s)",
    "컨트롤러 목록": "Controller List",
    "컨트롤러 삭제": "Delete Controller",
    "컨트롤러 선택": "Select Controller",
    "컨트롤러 수정": "Edit Controller",
    "컨트롤러를 고르면 그 색을 그대로 따옵니다": "Pick a controller to copy its color",
    "컨트롤러마다 역할(눈 감기/눈썹/입 모음/눈동자)을 고르면 ARKit 매핑을 자동으로 만들어 줍니다. 이름으로 미리 추측해서 채워둡니다": "Pick a role (eye blink / brow / mouth vowel / pupil) for each controller and the ARKit mapping is generated automatically. Roles are pre-guessed from names",
    "컨트롤러마다 역할을 고르세요": "Pick a role for each controller",
    "컨트롤러의 틀을 선택해서 G/R/S로 자유롭게 배치합니다. 끄면 다시 핸들 조작 모드로 돌아갑니다": "Select controller frames and arrange freely with G/R/S. Turn off to return to handle interaction",
    "컬렉션 '%s' 생성": "Collection '%s' created",
    "컬렉션 삭제": "Delete Collection",
    "컬렉션 이름": "Collection Name",
    "컬렉션 이름을 입력하세요": "Enter a collection name",
    "컬렉션 추가": "Add Collection",
    "컬렉션에 넣거나 뺄 컨트롤러 체크": "Check controllers to add to / remove from a collection",
    "컬렉션을 없애고 소속 컨트롤러를 컬렉션 밖으로 뺍니다 (컨트롤러는 유지)": "Remove the collection; its controllers are kept, just ungrouped",
    "켬": "On",
    "크기": "Size",
    "크기: %s · 길이: %s": "Size: %s · Length: %s",
    "클릭 = 위치 · 드래그 = 구간 선택 · Space = 재생 · 휠 = 줌 · Shift+휠 = 이동": "Click = position · Drag = select range · Space = play · Wheel = zoom · Shift+Wheel = pan",
    "키프레임: I > Location (또는 자동 키)": "Keyframe: I > Location (or auto-key)",
    "타입": "Type",
    "타입/방향/셰이프 키/라벨을 변경합니다": "Change type/direction/shape keys/label",
    "타입이 섞여 있습니다. 같은 타입끼리만 일괄 수정할 수 있습니다": "Mixed controller types. Only controllers of the same type can be batch-edited",
    "텍스트 %d개 색상 변경": "Changed color of %d text(s)",
    "텍스트 %d개에 가장 가까운 컨트롤러 색 적용": "Applied nearest controller color to %d text(s)",
    "텍스트 색상": "Text Color",
    "텍스트 색상 자동": "Auto Text Colors",
    "텍스트 생성: G/S로 배치, Tab으로 내용 수정": "Text created: place with G/S, edit content with Tab",
    "텍스트 추가": "Add Text",
    "텍스트 추가 = 자유 라벨 (오브젝트 모드에서 편집)": "Add Text = free label (edit in Object Mode)",
    "텍스트(라벨)의 색상을 변경합니다. 포즈 모드에서도 대상 텍스트를 골라 적용할 수 있고, 컨트롤러 색을 따올 수 있습니다": "Change label text color. Works in Pose Mode by choosing a target text, and can pick a color from a controller",
    "투명도": "Opacity",
    "파일: ": "File: ",
    "파일을 읽을 수 없습니다: %s": "Cannot read file: %s",
    "파형 함께 이동": "Move waveform together",
    "패널": "Panel",
    "패널 높이 기준이 될 본 (예: c_head.x)": "Bone used as panel height reference (e.g. c_head.x)",
    "패널 레이아웃(컨트롤러/텍스트/컬렉션)을 JSON으로 저장합니다": "Save panel layout (controllers/texts/collections) as JSON",
    "패널 리로드 완료 (컨트롤러 %d개)": "Panel reloaded (%d controllers)",
    "패널 본은 대상으로 쓸 수 없습니다": "Panel bones cannot be targets",
    "패널 위치 저장: 컨트롤러가 여기에 생성됩니다": "Panel position saved: controllers will be created here",
    "패널 위치 지정": "Set Panel Position",
    "패널 전체 이동: FP_root 본을 G로 이동": "Move whole panel: G on the FP_root bone",
    "패널 전체 제거": "Remove Entire Panel",
    "패널 위치 (그랩 바)": "Panel position (grab bar)",
    "캐릭터 따라다니기": "Follow character",
    "패널(그랩 바)과 뷰포트 컨트롤러가 아래 본을 따라다니며 지금의 상대 위치를 계속 유지합니다. 캐릭터가 움직여도 옆에 붙어 있습니다 (켜면 리그의 c_pos·root 본을 자동으로 고름)": "The panel (grab bar) and viewport controllers follow the bone below and keep their current relative position, so they stay beside the character as it moves (turning this on picks the rig's c_pos / root bone automatically)",
    "따라갈 본이 있는 아마추어 (캐릭터 리그)": "The armature holding the bone to follow (the character rig)",
    "패널이 따라갈 본 (보통 머리 본)": "The bone the panel follows (usually the head bone)",
    "현재 위치로 고정": "Pin at current position",
    "지금 보이는 패널 위치를 기준으로 다시 묶습니다. 캐릭터나 패널을 옮긴 뒤 위치가 어긋났을 때 누르세요": "Re-binds using the panel's current position. Use it if things drift after moving the character or the panel",
    "대상 리그와 본을 먼저 지정하세요": "Set the target rig and bone first",
    "패널 위치를 고정했습니다": "Panel position pinned",
    "여기서 고른 오디오만 재생됩니다 (나머지 사운드는 자동 음소거). 립싱크 분석용 오디오와 따로 조절됩니다": "Only the audio chosen here plays; every other sound is muted automatically. Controlled separately from the lipsync analysis audio",
    "재생 오디오 (스페이스바)": "Playback audio (Spacebar)",
    "재생 오디오": "Playback audio",
    "재생 오디오 추가": "Add playback audio",
    "재생 오디오 제거": "Remove playback audio",
    "재생 오디오 추가: %s": "Playback audio added: %s",
    "재생 오디오 제거: %s": "Playback audio removed: %s",
    "(선택 안 함)": "(none)",
    " (립싱크)": " (lipsync)",
    "시퀀서 사운드 스트립": "Sequencer sound strip",
    "스피커 오브젝트": "Speaker object",
    "블렌더에서 재생할 때 들리는 오디오를 고릅니다. 립싱크 분석용 오디오와 따로 조절됩니다": "Pick the audio you hear when playing back in Blender. Controlled separately from the lipsync analysis audio",
    "재생 오디오의 볼륨": "Volume of the playback audio",
    "재생 오디오만 잠시 끕니다 (립싱크 편집기 소리는 유지)": "Mutes only the playback audio (the lipsync editor keeps its sound)",
    "사운드 스트립이 시작할 프레임": "Frame the sound strip starts on",
    "스페이스바로 재생할 때 들리는 오디오를 시퀀서에 추가합니다. 립싱크 분석용 오디오와는 별개라 여기서 볼륨/음소거/시작 프레임만 따로 조절할 수 있습니다": "Adds the audio you hear on playback to the sequencer. It is separate from the lipsync analysis audio, so volume, mute and start frame are adjusted here on their own",
    "립싱크 사운드 음소거": "Mute lipsync sound",
    "립싱크용 사운드가 함께 울려 이중으로 들리는 것을 막습니다": "Prevents the lipsync sound from playing at the same time and doubling up",
    "선택한 재생 오디오를 제거합니다 (시퀀서 스트립만 해당). 립싱크 데이터는 그대로 남습니다": "Removes the selected playback audio (sequencer strips only). Lipsync data is left untouched",
    "영역으로 생성": "From selection",
    "드래그로 선택한 범위를 클러스터로 만듭니다": "Turn the dragged selection into a cluster",
    "쪼개기": "Split",
    "재생 헤드(빨간 세로선) 위치에서 클러스터를 둘로 나눕니다": "Split the cluster in two at the playhead (red line)",
    "선택 삭제": "Delete selected",
    "선택한 클러스터 하나만 삭제": "Delete only the selected cluster",
    "먼저 파형에서 범위를 드래그해 선택하세요": "First drag a range on the waveform",
    "재생 헤드가 클러스터 안에 있어야 합니다": "The playhead must be inside a cluster",
    "먼저 클러스터를 클릭해 선택하세요": "First click a cluster to select it",
    "클러스터를 클릭하면 이름을 지정할 수 있습니다": "Click a cluster to name its markers",
    "시작 이름": "Start name",
    "끝 이름": "End name",
    "마커 이름. 한쪽만 적으면 반대쪽도 같은 이름이 됩니다. 비우면 기본 이름(LS_01A/B)": "Marker name. Fill in one side and the other gets the same name. Leave empty for the default (LS_01A/B)",
    "간격": "Gap",
    "클러스터 (프레임 단위)": "Clusters (frames)",
    "클러스터 제거": "Clear clusters",
    "클러스터 간격": "Cluster gap",
    "클러스터 생성": "Detect clusters",
    "말소리 덩어리를 자동으로 찾아 표시합니다. 양 끝을 드래그해 조절하고, 위쪽 띠를 클릭해 선택 후 Del로 삭제할 수 있습니다. '적용'을 누르면 블렌더 타임라인에 마커로 만들어집니다": "Automatically finds speech clusters. Drag either end to adjust, click the top strip to select and Del to delete. Press Apply to turn them into timeline markers in Blender",
    "클러스터 간격 (프레임): 이만큼 이하로 떨어진 소리는 한 덩어리로 봅니다": "Cluster gap (frames): sounds closer together than this are treated as one cluster",
    "클러스터 모두 지우기": "Clear all clusters",
    "프레임 레이트가 %.4g → %.4g로 바뀌어 립싱크를 재배치했습니다": "Frame rate changed %.4g → %.4g; lipsync was re-timed to match",
    "프레임 레이트 변경 감지: 립싱크를 새 프레임 레이트에 맞춰 재배치했습니다": "Frame rate change detected: lipsync re-timed to the new frame rate",
    "선택한 리그 자동 전환": "Auto-switch to selected rig",
    "뷰포트에서 패널이 있는 다른 리그를 선택하면 이 패널 설정(컨트롤러 목록/프리셋/모캡/립싱크)을 그 캐릭터의 것으로 자동 전환합니다": "When you select another rig that has a panel, this panel's settings (controllers/presets/mocap/lipsync) automatically switch to that character",
    "캐릭터 이동 준비": "Prepare Character Transfer",
    "캐릭터 가져오기": "Import Character",
    "가져온 리그": "Appended Rig",
    "씬 설정만 복구": "Restore scene settings only",
    "씬 설정(컬렉션/프리셋/모캡/립싱크/라벨)을 리그에 저장합니다. 다른 파일에서 리그와 메시를 Append 한 뒤 '캐릭터 가져오기'로 복구하세요. 파일 저장 시 자동 갱신됩니다": "Stores scene settings (collections/presets/mocap/lipsync/labels) on the rig. Append the rig and meshes in another file, then run 'Import Character'. Auto-updated on file save",
    "Append 한 리그에서 캐릭터 설정을 복구합니다. 컨트롤러는 새로 만들지 않고 기존 본의 설정을 그대로 사용합니다": "Restores character settings from an appended rig. Existing controller bones are reused; nothing is duplicated",
    "패널 리로드와 라벨 재생성 없이 컬렉션/프리셋/모캡/립싱크 설정만 복구합니다": "Only restores collections/presets/mocap/lipsync, without panel reload or label rebuild",
    "캐릭터 설정을 리그에 저장했습니다 (라벨 %d개 포함)": "Character settings stored on the rig (incl. %d labels)",
    "이 리그에는 캐릭터 스냅샷이 없습니다. 원본 파일에서 '캐릭터 이동 준비'를 먼저 실행하세요": "No character snapshot on this rig. Run 'Prepare Character Transfer' in the source file first",
    "캐릭터 가져오기 완료 (라벨 %d개 재생성)": "Character import complete (%d labels rebuilt)",
    "패널을 옮겼습니다": "Panel moved",
    "패드 슬롯 표시 순번": "Pad slot display order",
    "패드 슬롯 표시 순번. 숫자를 고치면 그 위치로 끼어듭니다": "Pad slot display order. Edit the number to move it to that position",
    "패드 아래로": "Pad down",
    "패드 오른쪽으로": "Pad right",
    "패드 왼쪽으로": "Pad left",
    "패드 위로": "Pad up",
    "패드 추가: ": "Pad added: ",
    "패드: 같은 키를 상+하에 넣으면 -1~1 범위": "Pad: same key on up+down = -1 to 1 range",
    "패드에 연결된 셰이프 키와 값 표시": "Show shape keys and values connected to this pad",
    "패드의 모든 값에 곱해질 배율 (예: 0.5 = 절반 강도, 음수 = 반대 방향)": "Multiplier for all pad values (e.g. 0.5 = half strength, negative = opposite)",
    "편집기가 종료되었습니다. 탭을 닫아 주세요.": "Editor closed. You can close this tab.",
    "편집한 모음 구간대로 립싱크 키프레임을 다시 굽습니다": "Re-bakes the lipsync keyframes from the edited vowel segments",
    "펼치기": "Expand",
    "포즈 모드에서 컨트롤러 선택 후 G로 이동": "Pose Mode: select a controller, move with G",
    "포트 49983 열기 실패: %s": "Failed to open port 49983: %s",
    "표정": "Expression",
    "표정 전체 키프레임": "Keyframe All Expression",
    "표정 패널 제거 완료": "Face panel removed",
    "표정 프리셋": "Expression Presets",
    "표정 프리셋의 이름을 바꿉니다": "Renames the expression preset",
    "프레임 구간의 드라이버 값을 셰이프 키 키프레임으로 굽고 드라이버를 제거합니다. FBX/VRM 익스포트 전에 사용하세요. 패널 복구는 '뷰포트 패널 리로드'": "Bake driver values to shape key keyframes over a frame range and remove the drivers. Use before FBX/VRM export. Restore the panel with 'Reload Viewport Panel'",
    "프레임 범위": "Frame range",
    "프레임 클릭 = 이동": "Click frame = jump",
    "프레임 클릭 = 이동 · OK = 다시 굽기": "Click frame = jump · OK = re-bake",
    "프리셋 %d번이 없습니다": "Preset #%d does not exist",
    "프리셋 '%s' 저장 (컨트롤러 %d개)": "Preset '%s' saved (%d controllers)",
    "프리셋 데이터가 손상되었습니다": "Preset data is corrupted",
    "프리셋 블렌딩 (초)": "Preset Blend (sec)",
    "프리셋 삭제": "Delete Preset",
    "프리셋 이름": "Preset Name",
    "프리셋 이름 변경": "Rename Preset",
    "프리셋 이름을 입력하세요": "Enter a preset name",
    "프리셋 저장": "Save Preset",
    "프리셋 적용": "Apply Preset",
    "프리셋 적용: ": "Preset applied: ",
    "프리셋 전환에 걸리는 시간. 0이면 즉시 전환": "Time taken to transition between presets. 0 = instant",
    "함께 움직일 두 번째 본": "Second bone to move together",
    "함께 움직일 두 번째 본 (양눈 동시 제어용, 비우면 1개만)": "Second bone moved together (for both eyes; leave empty for one)",
    "항상 위": "Always on top",
    "해제": "Disable",
    "핸들 XY로 본(눈알 타겟 등)의 위치를 움직임": "Move bone locations (eye targets etc.) with handle XY",
    "핸들 상하 이동을 대상 본의 어느 로컬 축으로 보낼지": "Which local axis of the target bone receives vertical handle motion",
    "핸들 좌우 이동을 대상 본의 어느 로컬 축으로 보낼지. 본을 G로 움직여 눈이 좌우로 도는 축을 고르세요": "Which local axis of the target bone receives horizontal handle motion. Move the bone with G to find the axis that turns the eye left/right",
    "핸들을 따라 움직일 본": "Bone that follows the handle",
    "핸들을 따라 움직일 본 (예: c_eye_target.l)": "Bone that follows the handle (e.g. c_eye_target.l)",
    "핸들을 오른쪽 끝까지 밀었을 때 본이 이동하는 거리. 음수 = 반대 방향": "Distance the bone moves when the handle is pushed fully right. Negative = opposite",
    "핸들을 위 끝까지 밀었을 때 본이 이동하는 거리. 음수 = 반대 방향": "Distance the bone moves when the handle is pushed fully up. Negative = opposite",
    "핸들의 XY 이동으로 리그의 본(눈알 타겟 등)을 움직이는 2D 패드를 추가합니다. 본을 2개 넣으면 동시에 움직입니다 (양눈). 눈마다 따로 만들려면 본 1개씩 + 미러를 쓰세요": "Adds a 2D pad that moves rig bones (eye targets etc.) with handle XY. Two bones move together (both eyes). For per-eye pads, use one bone each + Mirror",
    "핸들이 앵커 반경 안이면 위치와 값이 고정 (0 = 끄기)": "Handle and value lock to anchors within this radius (0 = off)",
    "핸들이 앵커(모서리/변 중앙/중앙) 반경 안이면 위치와 값이 앵커에 고정됩니다. 이동 범위 대비 비율 (0=끄기)": "Handle and value lock to anchors (corners/edge mids/center) within this radius, as a ratio of travel (0 = off)",
    "핸들이 앵커(시작/중간/끝) 반경 안이면 위치와 값이 고정 (0 = 스냅 끄기)": "Handle and value snap to anchors (start/mid/end) within this radius (0 = off)",
    "허용 오차": "Tolerance",
    "현재 값을 기본값으로 저장": "Save Current as Default",
    "현재 뷰포트 컨트롤러의 실제 본 색상을 읽어 목록 스와치와 메타데이터에 동기화합니다 (애드온 재설치 후 색이 어긋날 때)": "Read actual bone colors from the viewport into the list swatches and metadata (fixes colors after reinstalling)",
    "현재 컨트롤러 값들을 표정 프리셋으로 저장합니다": "Save current controller values as an expression preset",
    "현재 프레임에 모든 컨트롤러의 키프레임을 삽입합니다": "Insert keyframes for all controllers at the current frame",
    "형식: ": "Format: ",
    "화살표 = 목록 순서 이동, 그룹은 수정 팝업에서": "Arrows = reorder list, group via edit popup",
    "확인": "OK",
    "확정: 클릭 · 취소: 우클릭/ESC": "Confirm: click - Cancel: RMB/ESC",
    "조작 중: 확정 = 클릭 · 취소 = 우클릭/ESC":
        "While moving: confirm = click - cancel = RMB/ESC",
    "표정 컨트롤러만": "expression controller only",
    "입 컨트롤러만": "mouth controller only",
    "시선 컨트롤러만": "gaze controller only",
    "모든 컨트롤러 위치 옮기기 (배치 모드)": "Move all controllers (arrange mode)",
    "배치 모드 끄기: ESC 또는 우클릭 (조작 중이 아닐 때)":
        "Exit arrange mode: ESC or RMB (when not moving)",
    "회전 배율": "Rotation Gain",
    "히스토리": "History",
}


_JA = {
    "패널 정렬 복구": "パネル整列を修復",
    "틀/핸들에 남은 포즈 회전을 초기화해 배치 모드 화살표와 스냅을 정상화합니다 (위치·크기·값은 유지)": "枠/ハンドルに残った回転をリセットし、配置モードの矢印とスナップを正常化します (位置・サイズ・値は維持)",
    "패널 정렬 복구 완료 (%d개)": "パネル整列を修復しました (%d個)",
    "머리에 부착": "頭に追従",
    "패널이 따라갈 본": "パネルが追従するボーン",
    "패널을 본에 붙이기 (해제하려면 본을 비우고 실행)": "パネルをボーンに追従させる (解除はボーンを空にして実行)",
    "패널 부착: ": "パネル追従: ",
    "패널 부착 해제": "パネル追従を解除",
    "구동 방식": "駆動方式",
    "위치 (이동)": "位置 (移動)",
    "회전 (머리 기준)": "回転 (頭基準)",
    "본을 이동시킬지, 제자리에서 회전시킬지": "ボーンを移動させるか、その場で回転させるか",
    "가로 회전량 (도)": "横の回転量 (度)",
    "세로 회전량 (도)": "縦の回転量 (度)",
    " (%s 패드)": " (%sパッド)",
    " (셰이프 키 없음 %d개 건너뜀)": " (シェイプキーなし %d件スキップ)",
    " (컨트롤러 %d개 추가)": " (コントローラー%d個追加)",
    " (패드)": " (パッド)",
    " [%s축]": " [%s軸]",
    "%d초 후 녹화 시작": "%d秒後に録画開始",
    "%s: 대상 본 '%s'의 좌/우 짝을 리그 '%s'에서 찾지 못했습니다": "%s: ターゲットボーン'%s'の左右ペアがリグ'%s'に見つかりません",
    "%s: 반대쪽 셰이프 키 '%s' 없음 (메시 '%s')": "%s: 反対側のシェイプキー'%s'がありません (メッシュ'%s')",
    "%s: 연쇄 셰이프 키 '%s' 없음 (메시 '%s')": "%s: 連動シェイプキー'%s'がありません (メッシュ'%s')",
    "%s: 키 이름에서 '%s'/'%s'를 찾지 못했습니다": "%s: キー名に'%s'/'%s'が見つかりません",
    "'%s' 적용 (컨트롤러 %d개)": "'%s'を適用 (コントローラー%d個)",
    "'에' 채널 (조합)": "「え」チャンネル (合成)",
    "(그룹 없음)": "(グループなし)",
    "(기존 그룹에서 선택)": "(既存グループから選択)",
    "(다수 선택됨)": "(複数値)",
    "(변경 안 함)": "(変更しない)",
    "(비어 있음)": "(空)",
    "(사용 안 함)": "(使用しない)",
    "(선택된 텍스트)": "(選択中のテキスト)",
    "(설정의 얼굴 메시)": "(設定の顔メッシュ)",
    "(아마추어 없음)": "(アーマチュアなし)",
    "(없음)": "(なし)",
    "(직접 지정)": "(手動指定)",
    "(컨트롤러 없음)": "(コントローラーなし)",
    "(컬렉션에서 제거)": "(コレクションから外す)",
    "1프레임 뒤로": "1フレーム戻る",
    "1프레임 앞으로": "1フレーム進む",
    "2D 패드": "2Dパッド",
    "2D 패드 추가": "2Dパッドを追加",
    "3D 뷰포트 > N패널 > Face Rig 탭": "3Dビューポート > Nパネル > Face Rigタブ",
    "3D 뷰포트에서 실행하세요": "3Dビューポートで実行してください",
    "Calibrate (중립 캡처)": "Calibrate (ニュートラル記録)",
    "FLAC (무손실)": "FLAC (ロスレス)",
    "G: 이동  (Ctrl = 모서리/중앙 스냅)": "G: 移動  (Ctrl = 角/中央スナップ)",
    "JSON 레이아웃을 불러와 패널을 구성합니다. 같은 이름의 셰이프 키에 자동 연결되며, 없는 키의 컨트롤러는 건너뜁니다": "JSONレイアウトを読み込みパネルを構築します。同名のシェイプキーに自動接続し、無いキーのコントローラーはスキップします",
    "N패널 설정에서 지정한 메시의 셰이프 키 사용": "Nパネル設定で指定したメッシュのシェイプキーを使用",
    "R / S: 회전 / 크기": "R / S: 回転 / スケール",
    "WAV PCM %d비트": "WAV PCM %dビット",
    "WAV를 읽을 수 없습니다: %s": "WAVを読み込めません: %s",
    "[배치 모드]": "[配置モード]",
    "iFacialMocap 수신 시작 (포트 49983)": "iFacialMocap受信開始 (ポート49983)",
    "iFacialMocap 수신 중지": "iFacialMocap受信を停止しました",
    "iFacialMocap 수신을 시작합니다. 아이폰과 PC가 같은 와이파이에 있어야 하며, 앱이 켜져 있어야 합니다": "iFacialMocapの受信を開始します。iPhoneとPCが同じWi-Fiにあり、アプリが起動している必要があります",
    "iFacialMocap 수신을 중지합니다": "iFacialMocapの受信を停止します",
    "iFacialMocap 앱 화면에 표시되는 아이폰의 IP 주소 (같은 와이파이여야 함)": "iFacialMocapアプリに表示されるiPhoneのIPアドレス (同じWi-Fiであること)",
    "iFacialMocap 캡처 중 숫자키로 표정 프리셋을 적용합니다 (1~9 = 프리셋 순번, 0 = 기본 표정). 캡처 중이 아니면 숫자키는 원래 기능대로 동작합니다": "iFacialMocapキャプチャ中に数字キーで表情プリセットを適用します (1~9 = プリセット番号、0 = デフォルト表情)。キャプチャ中でなければ数字キーは通常どおり動作します",
    "jawOpen 등에서 자동 계산되는 '아' 채널": "jawOpenなどから自動計算される「あ」チャンネル",
    "mocap 녹화로 촘촘히 박힌 키프레임을 모양을 유지하는 한도 안에서 줄입니다 (핸들 위치·목 회전·셰이프 키 값). 그래프 에디터에서 손질하기 쉬워집니다": "モーキャプ録画で密になったキーフレームを、形状を保つ範囲で間引きます (ハンドル位置・首回転・シェイプキー値)。グラフエディターで編集しやすくなります",
    "mouthFunnel에서 계산되는 '오' 채널": "mouthFunnelから計算される「お」チャンネル",
    "mouthPucker에서 계산되는 '우' 채널": "mouthPuckerから計算される「う」チャンネル",
    "numpy를 사용할 수 없습니다": "numpyが使用できません",
    "← 왼쪽": "← 左",
    "↑ 위": "↑ 上",
    "→ 오른쪽": "→ 右",
    "↓ 아래": "↓ 下",
    "↖ 좌상": "↖ 左上",
    "↗ 우상": "↗ 右上",
    "↘ 우하": "↘ 右下",
    "↙ 좌하": "↙ 左下",
    "가로": "横",
    "가로 → 본 축": "横 → ボーン軸",
    "가로 이동량": "横の移動量",
    "가져오기 완료: 컨트롤러 %d개, 텍스트 %d개": "読み込み完了: コントローラー%d個、テキスト%d個",
    "각 텍스트에서 가장 가까운 컨트롤러를 찾아 그 색을 자동으로 적용합니다 (색상을 사용하는 컨트롤러 기준)": "各テキストに最も近いコントローラーの色を自動適用します (色を使用するコントローラーが対象)",
    "간단 자동 설정": "かんたん自動設定",
    "값": "値",
    "값 −": "値 −",
    "값 단위 오차 한도. 클수록 키가 많이 줄어듭니다": "値単位の誤差上限。大きいほどキーが減ります",
    "값 떨림 완화. 높을수록 부드럽지만 반응이 느려집니다": "値のブレを軽減。高いほど滑らかですが反応が遅くなります",
    "같은 그룹끼리 목록에서 묶어 표시 (비우면 그룹 없음)": "同じグループをリストでまとめて表示 (空欄でグループなし)",
    "같은 이름의 프리셋이 있습니다": "同名のプリセットがあります",
    "갸웃 →": "傾げ →",
    "갸웃 방향 반전": "傾げ方向を反転",
    "구간 앞뒤로 이만큼의 프레임에 걸쳐 부드럽게 전환": "区間の前後この幅のフレームで滑らかに遷移",
    "구간 적용 (다시 굽기)": "区間を適用 (再ベイク)",
    "구간으로 이동": "区間へ移動",
    "그래프 에디터를 새 창으로 열어 모음 구간을 편집합니다. 사이드바의 Face Rig 탭에 구간 목록이 있습니다": "グラフエディターを新しいウィンドウで開き母音区間を編集します。サイドバーのFace Rigタブに区間リストがあります",
    "그룹": "グループ",
    "기본 표정으로": "デフォルト表情へ",
    "기본값으로 되돌리기": "デフォルトに戻す",
    "기존 그룹": "既存グループ",
    "기존 그룹/컬렉션에서 골라 채웁니다": "既存のグループ/コレクションから選んで入力します",
    "끄덕임 →": "うなずき →",
    "끄덕임 방향 반전": "うなずき方向を反転",
    "끔": "オフ",
    "끝 프레임": "終了フレーム",
    "내용": "内容",
    "노란 화살표 드래그: 변 크기 조절  (Ctrl = 스냅, Alt = 대칭)": "黄色い矢印ドラッグ: 辺のサイズ調整  (Ctrl = スナップ、Alt = 対称)",
    "녹화": "録画",
    "녹화 시작": "録画開始",
    "녹화 시작 버튼을 누른 뒤 재생까지의 대기 시간 (0 = 즉시 시작)": "録画開始ボタンから再生までの待ち時間 (0 = 即時開始)",
    "녹화 정지": "録画停止",
    "녹화 커브 단순화": "録画カーブの単純化",
    "눈": "目",
    "눈 리그": "目のリグ",
    "눈 회전 반영 정도": "眼球回転の反映度",
    "눈동자": "瞳",
    "눈썹": "眉",
    "눈알 본이 들어있는 아마추어": "眼球ボーンがあるアーマチュア",
    "눈알 본이 바라보는 방향의 로컬 축": "眼球ボーンが向いている方向のローカル軸",
    "단순화할 커브가 없습니다": "単純化するカーブがありません",
    "닫기": "閉じる",
    "대기 중 (앱/와이파이/IP 확인)": "待機中 (アプリ/Wi-Fi/IPを確認)",
    "대사 녹음(WAV)을 분석해 A/I/U/E/O 립싱크 키프레임을 자동 생성합니다. '간단 자동 설정'의 입 매핑을 그대로 사용하므로 먼저 매핑을 만들어 두세요": "セリフ録音(WAV)を解析しA/I/U/E/Oリップシンクのキーフレームを自動生成します。かんたん自動設定の口マッピングを使うため、先にマッピングを作成してください",
    "대사 녹음(WAV/MP3/OGG/FLAC)을 분석해 A/I/U/E/O 립싱크 키프레임을 자동 생성합니다. '간단 자동 설정'의 입 매핑을 그대로 사용하므로 먼저 매핑을 만들어 두세요": "セリフ録音(WAV/MP3/OGG/FLAC)を解析しA/I/U/E/Oリップシンクのキーフレームを自動生成します。かんたん自動設定の口マッピングを使うため、先にマッピングを作成してください",
    "대상": "対象",
    "대상 리그": "ターゲットリグ",
    "대상 리그를 선택하세요": "ターゲットリグを選択してください",
    "대상 본 1": "ターゲットボーン1",
    "대상 본 1을 선택하세요": "ターゲットボーン1を選択してください",
    "대상 본 2 (선택)": "ターゲットボーン2 (任意)",
    "대상 본 이름에서 좌/우 짝(.l/.r 등)을 찾지 못했습니다": "ターゲットボーン名に左右ペア(.l/.rなど)が見つかりません",
    "대상 본을 찾을 수 없습니다": "ターゲットボーンが見つかりません",
    "대상 컬렉션": "対象コレクション",
    "대상 텍스트": "対象テキスト",
    "대상 텍스트가 없습니다 (팝업에서 텍스트를 선택하세요)": "対象テキストがありません (ポップアップで選択してください)",
    "돌림 →": "振り向き →",
    "돌림 방향 반전": "振り向き方向を反転",
    "드래그 = 범위 선택 · 클릭 = 이동/선택 해제 · 선택 드래그 = 범위 이동 · + = 구간 추가 · ✂ = 잘라내기 · 패드 = 입모양 · ★ = 즐겨찾기 (우클릭 편집) · Ctrl+Z = 실행취소 · Ctrl+C/V = 복사/붙여넣기 · Del = 삭제 · Space = 재생 · 휠 = 줌 · 휠 클릭 = 패닝": "ドラッグ = 範囲選択 · クリック = 移動/選択解除 · 選択をドラッグ = 範囲移動 · + = 区間追加 · ✂ = 切り取り · パッド = 口の形 · ★ = お気に入り (右クリックで編集) · Ctrl+Z = 元に戻す · Ctrl+C/V = コピー/貼り付け · Del = 削除 · Space = 再生 · ホイール = ズーム · ホイールクリック = パン",
    "라벨": "ラベル",
    "라벨을 셰이프 키(또는 대상 본) 이름으로 채웁니다": "ラベルをシェイプキー(またはターゲットボーン)名で埋めます",
    "레이아웃 가져오기": "レイアウト読み込み",
    "레이아웃 내보내기": "レイアウト書き出し",
    "레이아웃 저장: 컨트롤러 %d개, 텍스트 %d개": "レイアウト保存: コントローラー%d個、テキスト%d個",
    "레이아웃 파일이 아닙니다": "レイアウトファイルではありません",
    "루프": "ループ",
    "리그": "リグ",
    "립싱크 구간": "リップシンク区間",
    "립싱크 구간 편집": "リップシンク区間編集",
    "립싱크 다시 굽기 완료 (%d프레임)": "リップシンク再ベイク完了 (%dフレーム)",
    "립싱크 데이터가 없습니다": "リップシンクデータがありません",
    "립싱크 사운드 제거": "リップシンク音声を削除",
    "립싱크 생성: %d프레임 (%.1f초). 필요하면 '녹화 커브 단순화'로 정리하세요": "リップシンク生成: %dフレーム (%.1f秒)。必要なら「録画カーブの単純化」で整理してください",
    "립싱크 자동 재계산": "リップシンク自動再計算",
    "립싱크 키 구간과 겹칩니다. 녹화가 립싱크 키를 덮어쓸 수 있습니다": "リップシンクのベイク範囲と重なっています。録画がリップシンクキーを上書きする可能性があります",
    "립싱크 편집 창 열기": "リップシンク編集ウィンドウを開く",
    "립싱크 편집기": "リップシンクエディター",
    "립싱크 편집기 열기": "リップシンクエディターを開く",
    "립싱크 편집기 재생": "リップシンクエディター再生",
    "립싱크 편집기 클릭": "リップシンクエディタークリック",
    "매핑 %d개 생성 완료": "マッピング%d件を作成しました",
    "매핑 (ARKit → 컨트롤러)": "マッピング (ARKit → コントローラー)",
    "매핑 삭제": "マッピング削除",
    "매핑 추가": "マッピング追加",
    "머리 본": "頭ボーン",
    "머리 회전 반영 정도. 방향이 반대면 음수로": "頭回転の反映度。逆方向ならマイナスに",
    "머리 회전을 따라 돌 본 (예: c_head.x, neck)": "頭の回転に追従するボーン (例: c_head.x、neck)",
    "머리 회전을 적용할 본이 있는 아마추어": "頭回転を適用するボーンがあるアーマチュア",
    "머리/목 회전": "頭/首の回転",
    "먼저 컨트롤러 옆 체크박스를 선택하세요": "先にコントローラー横のチェックを入れてください",
    "메시": "メッシュ",
    "모노": "モノラル",
    "모든 라벨 텍스트 표시/숨김": "すべてのラベルテキストを表示/非表示",
    "모든 컨트롤러/라벨/위젯과 셰이프 키 드라이버를 제거합니다": "すべてのコントローラー/ラベル/ウィジェットとシェイプキードライバーを削除します",
    "모든 컨트롤러를 저장된 기본값으로 되돌립니다. 저장된 기본값이 없으면 0으로 (키프레임은 지우지 않음)": "すべてのコントローラーを保存済みデフォルトに戻します。保存が無ければ0に (キーフレームは削除しません)",
    "모음": "母音",
    "목 리그": "首のリグ",
    "목 본": "首ボーン",
    "목록 순번. 숫자를 고치면 그 위치로 끼어듭니다": "リスト番号。数字を変えるとその位置に割り込みます",
    "목록에 표시할 이름 (비우면 대상 본 이름)": "リストに表示する名前 (空欄でターゲットボーン名)",
    "목록에서 이름 클릭 = 뷰포트에서 선택": "リストで名前クリック = ビューポートで選択",
    "목록에서 컨트롤러 순서를 위/아래로 이동합니다 (같은 그룹 안에서, Shift = 맨 위/맨 아래로)": "リストでコントローラーを上下に移動します (同グループ内、Shift = 最上/最下へ)",
    "무음 임계값": "無音しきい値",
    "무음화": "無音化",
    "무음화 (길이 유지)": "無音化 (長さ維持)",
    "무표정으로 카메라를 정면으로 본 상태에서 누르세요. 지금 값을 기준(0)으로 저장해서 이후 수신값을 보정합니다. 씬에 저장되어 다음에도 유지됩니다": "無表情でカメラを正面に見た状態で押してください。現在値を基準(0)として保存し、以後の受信値を補正します。シーンに保存され次回も維持されます",
    "미러 아이콘 = 반대쪽 컨트롤러 자동 생성": "ミラーアイコン = 反対側コントローラーを自動生成",
    "미러 취소 — ": "ミラー中止 — ",
    "미리보기 도식의 표시 배율": "プレビュー図の表示倍率",
    "미리보기 크기": "プレビューサイズ",
    "미지정 (입 다묾)": "未指定 (口を閉じる)",
    "반대쪽 셰이프 키가 없습니다: ": "反対側のシェイプキーがありません: ",
    "반대쪽 자동 생성": "反対側を自動生成",
    "반대쪽 컨트롤러 생성: ": "反対側コントローラーを生成: ",
    "반전": "反転",
    "방향": "方向",
    "방향 반전": "方向反転",
    "방향을 하나 이상 연결하세요": "方向を1つ以上接続してください",
    "배율": "倍率",
    "배치 모드": "配置モード",
    "배치 모드 ON = 틀을 G/R/S로 자유 배치": "配置モードON = 枠をG/R/Sで自由配置",
    "배치 모드: G 이동 중 Ctrl = 모서리 스냅": "配置モード: G移動中Ctrl = 角スナップ",
    "배치 모드: 노란 화살표 드래그 = 그 변만 크기 조절": "配置モード: 黄色矢印ドラッグ = その辺だけサイズ調整",
    "배치 모드에서 G로 틀을 이동합니다. Shift를 누르는 동안 다른 틀 모서리에 스냅됩니다": "配置モードでGで枠を移動します。Shift押下中は他の枠の角にスナップします",
    "배치 모드에서 선택된 틀의 변 화살표를 드래그해 그 변만 이동합니다. Ctrl을 누르는 동안 다른 틀 모서리에 스냅됩니다": "配置モードで選択枠の辺矢印をドラッグしてその辺だけ移動します。Ctrl押下中は他の枠の角にスナップします",
    "배치 순서로 정렬": "配置順に並べ替え",
    "범위 적용": "範囲を適用",
    "베이크할 드라이버가 없습니다": "ベイクするドライバーがありません",
    "변 드래그 중 Ctrl = 스냅, Alt = 대칭 조절": "辺ドラッグ中Ctrl = スナップ、Alt = 対称調整",
    "변 이동: 드래그=크기 조절, Ctrl=스냅, Alt=대칭 조절, 놓으면 확정, ESC 취소": "辺移動: ドラッグ=サイズ調整、Ctrl=スナップ、Alt=対称、離して確定、ESCキャンセル",
    "변 크기 조절": "辺のサイズ調整",
    "보정 해제": "補正解除",
    "본 패드": "ボーンパッド",
    "본 패드 = 핸들 XY로 본(눈알 타겟) 이동": "ボーンパッド = ハンドルXYでボーン(眼球ターゲット)移動",
    "본 패드 추가": "ボーンパッドを追加",
    "본 패드 추가: ": "ボーンパッド追加: ",
    "본을 만들 리그": "ボーンを作るリグ",
    "본을 만들 리그를 선택하세요": "ボーンを作るリグを選択してください",
    "볼륨": "音量",
    "뷰포트 배치 위치(위→아래, 왼쪽→오른쪽) 순서대로 목록 순서를 자동 정렬합니다 (그룹별)": "ビューポートの配置(上→下、左→右)順にリストを自動整列します (グループ別)",
    "뷰포트 색상 다시 불러오기": "ビューポート色を再読み込み",
    "뷰포트 패널 리로드": "ビューポートパネルをリロード",
    "뷰포트 패널 컨트롤러를 움직임 (키프레임은 핸들에 기록)": "ビューポートパネルのコントローラーを動かす (キーフレームはハンドルに記録)",
    "뷰포트에 크로스헤어가 나타납니다. 클릭한 위치에 패널이 생성되고, 이미 있으면 패널 전체가 그곳으로 이동합니다. 우클릭/ESC = 취소": "ビューポートに十字カーソルが表示されます。クリック位置にパネルを作成し、既にあればパネル全体をそこへ移動します。右クリック/ESC = キャンセル",
    "뷰포트에서 이 컨트롤러를 선택합니다 (배치 모드면 틀을 선택)": "ビューポートでこのコントローラーを選択します (配置モードでは枠を選択)",
    "브라우저에 전용 립싱크 편집기를 엽니다. 파형과 모음 구간을 보며 구간을 클릭해 A/I/U/E/O를 바꾸고, 적용을 누르면 Blender에 다시 굽습니다": "ブラウザに専用リップシンクエディターを開きます。波形と母音区間を見ながら区間をクリックしてA/I/U/E/Oを変更し、適用でBlenderに再ベイクします",
    "브라우저에서 립싱크 편집기를 열었습니다": "ブラウザでリップシンクエディターを開きました",
    "블렌딩": "ブレンド",
    "비우고 적용하면 그룹에서 빠집니다": "空欄で適用するとグループから外れます",
    "비우면 컨스트레인트 생략": "空欄ならコンストレイントを省略",
    "사용": "有効",
    "사운드 스트립 %d개 제거": "サウンドストリップを%d個削除",
    "사운드 스트립 추가": "サウンドストリップを追加",
    "삭제": "削除",
    "상/하/좌/우 방향별 연결": "上/下/左/右の方向別に接続",
    "상/하/좌/우 방향별로 셰이프 키를 연결한 XY 패드를 추가합니다. 같은 키를 상+하(또는 좌+우)에 넣으면 -1~1 풀레인지로 동작합니다": "上/下/左/右の方向別にシェイプキーを接続したXYパッドを追加します。同じキーを上+下(または左+右)に入れると-1~1のフルレンジで動作します",
    "상하 반전": "上下反転",
    "새 이름": "新しい名前",
    "새 컬렉션을 만듭니다. 체크한 컨트롤러가 있으면 바로 담습니다": "新しいコレクションを作成します。チェック済みコントローラーがあればすぐ入れます",
    "색상": "カラー",
    "색상 사용": "カラーを使用",
    "색상을 사용하는 컨트롤러가 없습니다": "カラーを使用するコントローラーがありません",
    "선택": "選択",
    "선택 → 컬렉션": "選択 → コレクション",
    "선택 범위 립싱크 재계산 (선택 없으면 전체)": "選択範囲のリップシンク再計算 (選択なしなら全体)",
    "선택 범위 볼륨 조절 (선택 없으면 전체) · 립싱크 재계산": "選択範囲の音量調整 (選択なしなら全体) · リップシンク再計算",
    "선택 범위 잘라내기 (오디오 포함) · 선택 없으면 타임바에서 분할": "選択範囲を切り取り (オーディオ含む) · 選択なしならタイムバーで分割",
    "선택됨: %d개": "選択中: %d個",
    "선택한 셰이프 키를 조절하는 1D 슬라이더를 추가합니다": "選択したシェイプキーを操作する1Dスライダーを追加します",
    "선택한 셰이프 키를 찾을 수 없습니다": "選択したシェイプキーが見つかりません",
    "설정": "設定",
    "설정에서 좌/우 포함식을 입력하세요": "設定で左右トークンを入力してください",
    "성분": "成分",
    "세로": "縦",
    "세로 → 본 축": "縦 → ボーン軸",
    "세로 이동량": "縦の移動量",
    "셰이프 키": "シェイプキー",
    "셰이프 키 %d개 + 본 채널 %d개 x %d프레임 베이크 완료. 드라이버 제거됨 — 패널 복구는 '뷰포트 패널 리로드'": "シェイプキー%d個 + ボーンチャンネル%d個 x %dフレームのベイク完了。ドライバーは削除 — 復旧は「ビューポートパネルをリロード」",
    "셰이프 키 %d개 x %d프레임 베이크 완료. 드라이버 제거됨 — 패널 복구는 '뷰포트 패널 리로드'": "シェイプキー%d個 x %dフレームのベイク完了。ドライバーは削除 — 復旧は「ビューポートパネルをリロード」",
    "셰이프 키 값을 직접 움직임 (패널 컨트롤러 불필요)": "シェイプキー値を直接動かす (パネルコントローラー不要)",
    "셰이프 키 대상일 때: 키가 있는 메시": "シェイプキー対象の場合: キーがあるメッシュ",
    "셰이프 키 베이크 (익스포트용)": "シェイプキーをベイク (エクスポート用)",
    "셰이프 키 연결에 실패했습니다": "シェイプキーの接続に失敗しました",
    "셰이프 키 이름 동기화": "シェイプキー名を同期",
    "셰이프 키 이름 복사": "シェイプキー名をコピー",
    "셰이프 키 이름과 ARKit 이름을 비교해 매핑을 자동으로 채웁니다 (기존 매핑은 교체). 눈동자 패드 등은 수동으로 추가하세요": "シェイプキー名とARKit名を比較しマッピングを自動作成します (既存は置換)。瞳パッドなどは手動で追加してください",
    "셰이프 키 이름에서 오른쪽을 뜻하는 부분 (예: (Right), .R, _right)": "シェイプキー名で右を示す部分 (例: (Right)、.R、_right)",
    "셰이프 키 이름에서 왼쪽을 뜻하는 부분 (예: (Left), .L, _left)": "シェイプキー名で左を示す部分 (例: (Left)、.L、_left)",
    "셰이프 키 이름을 바꾼 뒤 실행하세요. 드라이버가 실제로 연결된 키 이름을 읽어 목록/메타데이터를 갱신합니다": "シェイプキー名を変更した後に実行してください。ドライバーが実際に接続しているキー名を読み、リスト/メタデータを更新します",
    "셰이프 키를 가져올 메시 (기본 = 설정의 얼굴 메시)": "シェイプキーを取得するメッシュ (既定 = 設定の顔メッシュ)",
    "셰이프 키를 골라 1D 슬라이더/2D 패드 컨트롤러를 뷰포트에 조립하는 빌더": "シェイプキーを選んで1Dスライダー/2Dパッドをビューポートに組み立てるビルダー",
    "셰이프 키를 선택하세요": "シェイプキーを選択してください",
    "셰이프 키를 찾을 수 없습니다": "シェイプキーが見つかりません",
    "수신 미리보기": "受信プレビュー",
    "수신 중": "受信中",
    "수신 중인 표정 값을 뷰포트 좌상단에 도식으로 표시": "受信中の表情値をビューポート左上に図で表示",
    "수신 중인 표정 값을 뷰포트에 도식으로 표시": "受信中の表情値をビューポートに図で表示",
    "수신된 데이터가 없습니다": "受信データがありません",
    "순번": "番号",
    "순서 이동": "順序を移動",
    "숫자키 1~9 = 표정 프리셋, 0 = 기본 표정": "数字キー1~9 = 表情プリセット、0 = デフォルト表情",
    "스냅 이동": "スナップ移動",
    "스냅 적용": "スナップを適用",
    "스무딩": "スムージング",
    "스크럽 소리": "スクラブ音",
    "스포이드": "スポイト",
    "슬라이더 (가로)": "スライダー (横)",
    "슬라이더 (세로)": "スライダー (縦)",
    "슬라이더 값 (반전/양방향 자동 반영)": "スライダー値 (反転/双方向を自動反映)",
    "슬라이더 값에 곱해질 배율 (음수 = 반대로 움직임)": "スライダー値に掛ける倍率 (マイナス = 逆に動く)",
    "슬라이더 최솟값<0 = 양방향 (중앙이 0)": "スライダー最小値<0 = 双方向 (中央が0)",
    "슬라이더 추가": "スライダーを追加",
    "슬라이더 추가: ": "スライダー追加: ",
    "슬라이더는 '값', 패드는 방향 성분을 고르세요": "スライダーは「値」、パッドは方向成分を選んでください",
    "슬롯에 연결된 A/I/U/E/O 키의 방향을 읽어 자동 매핑": "スロットのA/I/U/E/Oキーの方向を読み取り自動マッピング",
    "시작 프레임": "開始フレーム",
    "시작 프레임으로 이동해 카운트다운 후 재생과 녹화를 시작합니다. 다시 누르면 취소/정지되고, End Frame에 도달하면 자동으로 멈춥니다": "開始フレームへ移動しカウントダウン後に再生と録画を開始します。もう一度押すとキャンセル/停止し、End Frameで自動停止します",
    "시퀀서에 넣은 립싱크 사운드 스트립을 제거합니다. 타임라인 스크럽 시 소리가 나지 않게 됩니다": "シーケンサーのリップシンク音声ストリップを削除します。タイムラインのスクラブで音が鳴らなくなります",
    "시퀀서에 오디오를 넣어 재생 시 소리가 같이 나오게 합니다": "シーケンサーに音声を入れて再生時に音が出るようにします",
    "아래 (Y-)": "下 (Y-)",
    "아래 색상 필드로 직접 선택": "下のカラーフィールドで直接選択",
    "아래→위": "下→上",
    "아래에서 위로 0~1": "下から上へ0~1",
    "아이폰 IP": "iPhone IP",
    "아이폰 IP를 입력하세요 (앱 화면에 표시됨)": "iPhoneのIPを入力してください (アプリに表示)",
    "애니메이션 재생 중일 때 매핑된 핸들에 키프레임을 기록합니다 (스페이스바로 재생하며 연기하세요)": "アニメーション再生中にマッピング済みハンドルへキーフレームを記録します (スペースで再生しながら演技)",
    "앵커 스냅 임계값": "アンカースナップしきい値",
    "양방향 슬라이더의 음수 방향으로": "双方向スライダーのマイナス方向へ",
    "어니언 스킨": "オニオンスキン",
    "얼굴 메시": "顔メッシュ",
    "역할": "役割",
    "역할별로 컨트롤러만 고르면 ARKit 매핑을 자동으로 만들어 줍니다. 입 모양은 A/I/U/E/O 조합 채널로 연결되고, 컨트롤러 이름으로 미리 추측해서 채워둡니다": "役割ごとにコントローラーを選ぶだけでARKitマッピングを自動作成します。口はA/I/U/E/O合成チャンネルに接続され、名前から推測して事前入力します",
    "연결 시작": "接続開始",
    "연결 안 함": "接続しない",
    "연결된 키 이름에서 '%s' / '%s' 를 찾지 못했습니다": "接続キー名に'%s' / '%s'が見つかりません",
    "연결할 셰이프 키(또는 대상 본)가 없습니다": "接続するシェイプキー(またはターゲットボーン)がありません",
    "연결할 셰이프 키가 없습니다": "接続するシェイプキーがありません",
    "연쇄 드라이버": "連動ドライバー",
    "연쇄 셰이프 키가 있는 메시 (기본 = 설정의 얼굴 메시)": "連動シェイプキーがあるメッシュ (既定 = 設定の顔メッシュ)",
    "연쇄 추가": "連動を追加",
    "연필 아이콘 = 타입/키/라벨 수정": "鉛筆アイコン = タイプ/キー/ラベル編集",
    "영역 선택 모드 (끄면 드래그 = 스크럽)": "範囲選択モード (オフ: ドラッグ = スクラブ)",
    "오디오 립싱크 생성": "音声リップシンク生成",
    "오디오: 파일 없음": "オーディオ: ファイルなし",
    "오디오가 너무 짧습니다": "音声が短すぎます",
    "오디오를 읽을 수 없습니다: %s": "音声を読み込めません: %s",
    "오른눈 감기": "右目まばたき",
    "오른눈 눈동자 패드": "右目の瞳パッド",
    "오른눈 본": "右目ボーン",
    "오른눈썹 (위/아래)": "右眉 (上/下)",
    "오른쪽 (X+)": "右 (X+)",
    "오브젝트 모드에서 선택한 텍스트에 적용": "オブジェクトモードで選択したテキストに適用",
    "오토 키": "自動キー",
    "왼눈 감기": "左目まばたき",
    "왼눈 눈동자 패드": "左目の瞳パッド",
    "왼눈 본": "左目ボーン",
    "왼눈썹 (위/아래)": "左眉 (上/下)",
    "왼쪽 (X-)": "左 (X-)",
    "왼쪽→오른쪽": "左→右",
    "왼쪽에서 오른쪽으로 0~1": "左から右へ0~1",
    "우": "右",
    "우상 (대각)": "右上 (対角)",
    "우상단 빨간 토글 오른쪽으로 = 패널 숨김": "右上の赤トグルを右へ = パネル非表示",
    "우측 포함식": "右トークン",
    "우하 (대각)": "右下 (対角)",
    "움직일 본이 들어있는 아마추어": "動かすボーンがあるアーマチュア",
    "움직일 본이 들어있는 아마추어 (설정의 리그와 달라도 됨)": "動かすボーンがあるアーマチュア (設定のリグと別でも可)",
    "원본": "オリジナル",
    "위 (Y+)": "上 (Y+)",
    "위아래 끄덕임(피치)을 보낼 본 로컬 축": "上下うなずき(ピッチ)を送るボーンローカル軸",
    "위치 갱신": "位置を更新",
    "음수 = 반대 방향": "マイナス = 逆方向",
    "음수로 하면 양방향 슬라이더가 됩니다 (중앙=0)": "マイナスにすると双方向スライダーになります (中央=0)",
    "음수로 하면 양방향 슬라이더가 됩니다 (중앙=0). 셰이프 키 자체의 Range Min도 음수여야 합니다": "マイナスにすると双方向スライダーになります (中央=0)。シェイプキー自体のRange Minもマイナスが必要です",
    "이 ARKit 값이 움직일 컨트롤러": "このARKit値が動かすコントローラー",
    "이 구간의 시작 프레임으로 이동합니다": "この区間の開始フレームへ移動します",
    "이 방향 키에만 곱해질 배율 (전체 배율과 곱해짐)": "この方向のキーにだけ掛ける倍率 (全体倍率と乗算)",
    "이 슬라이더 값에 배율을 곱해 함께 움직일 셰이프 키": "このスライダー値×倍率で連動するシェイプキー",
    "이 슬라이더 값을 따라 함께 움직일 셰이프 키를 추가합니다": "このスライダーに連動するシェイプキーを追加します",
    "이 슬라이더를 따라 움직일 키를 + 로 추가": "このスライダーに連動するキーを+で追加",
    "이 컨트롤러와 연결된 드라이버를 제거합니다 (셰이프 키는 유지)": "このコントローラーと関連ドライバーを削除します (シェイプキーは維持)",
    "이 컨트롤러와 연결된 드라이버를 제거합니다 (셰이프 키는 유지). 체크된 항목이 2개 이상이면 체크된 것들을 한꺼번에 삭제합니다": "このコントローラーと関連ドライバーを削除します (シェイプキーは維持)。チェックが2個以上ならまとめて削除します",
    "이동": "移動",
    "이동 방향을 반대로 (가로: 오른쪽→왼쪽, 세로: 위→아래). 원점은 항상 값 0": "移動方向を逆に (横: 右→左、縦: 上→下)。原点は常に値0",
    "이동 방향을 반대로 (원점은 항상 값 0)": "移動方向を逆に (原点は常に値0)",
    "이동%s: Ctrl=스냅, X/Y/Z=축 고정, 클릭=확정, ESC=취소": "移動%s: Ctrl=スナップ、X/Y/Z=軸固定、クリック=確定、ESC=キャンセル",
    "이동: Ctrl=모서리 스냅, X/Y/Z=축 고정, 클릭=확정, 우클릭/ESC=취소": "移動: Ctrl=角スナップ、X/Y/Z=軸固定、クリック=確定、右クリック/ESC=キャンセル",
    "이동량 적용": "移動量を適用",
    "이름 갱신 %d건": "名前を%d件更新",
    "이름 변경: ": "名前変更: ",
    "이름을 입력하세요": "名前を入力してください",
    "일괄 수정 (체크된 항목)": "一括編集 (チェック項目)",
    "일괄 수정: %d개 적용": "一括編集: %d個に適用",
    "일시정지": "一時停止",
    "입 (모음)": "口 (母音)",
    "입 A (아)": "口 A (あ)",
    "입 E (에)": "口 E (え)",
    "입 I (이)": "口 I (い)",
    "입 O (오)": "口 O (お)",
    "입 U (우)": "口 U (う)",
    "입 모음 매핑이 없습니다. iFacialMocap 패널의 '간단 자동 설정'으로 먼저 만들어 주세요": "口の母音マッピングがありません。iFacialMocapパネルのかんたん自動設定で先に作成してください",
    "입 벌림 배율": "口の開き倍率",
    "입 움직임 완화. 높을수록 부드럽지만 둔해집니다": "口の動きを滑らかに。高いほど柔らかいが鈍くなります",
    "입 패드 (모음 자동 배치)": "口パッド (母音を自動配置)",
    "입꼬리 당김에서 계산되는 '이' 채널": "口角の引きから計算される「い」チャンネル",
    "입모양 A (조합)": "口形 A (合成)",
    "입모양 E (조합)": "口形 E (合成)",
    "입모양 I (조합)": "口形 I (合成)",
    "입모양 O (조합)": "口形 O (合成)",
    "입모양 U (조합)": "口形 U (合成)",
    "자동 매핑": "自動マッピング",
    "자동 매핑 %d개 (나머지는 +로 수동 추가)": "自動マッピング%d件 (残りは+で手動追加)",
    "자동 매핑(마법봉) 또는 +로 추가하세요": "自動マッピング(魔法の杖)か+で追加してください",
    "자동 배치된 모음 구간을 확인하고 바꿉니다. 프레임 숫자 클릭 = 그 지점으로 이동, 모음을 고치고 OK를 누르면 키프레임을 다시 굽습니다": "自動配置された母音区間を確認・変更します。フレーム番号クリックで移動、母音を変えてOKで再ベイクします",
    "자유 배치 가능한 라벨 텍스트를 만듭니다. 오브젝트 모드에서 G/S로 배치·크기 조절, Tab으로 내용 수정, 폰트는 폰트 속성에서": "自由配置できるラベルテキストを作成します。オブジェクトモードでG/S配置・サイズ調整、Tabで内容編集、フォントはフォント設定で",
    "잘라내기": "切り取り",
    "잘라내기 (길이 단축)": "切り取り (長さ短縮)",
    "재계산": "再計算",
    "재계산 결과가 무음이라 중단했습니다. 진단: len=%d sr=%s fps=%.2f peak=%.4f frames=%d": "再計算の結果が無音のため中断しました。診断: len=%d sr=%s fps=%.2f peak=%.4f frames=%d",
    "재생": "再生",
    "저장된 설정으로 모든 컨트롤러를 다시 구성합니다. 위젯/드라이버/토글 연결을 최신 버전 방식으로 재적용합니다": "保存済み設定で全コントローラーを再構築します。ウィジェット/ドライバー/トグル接続を最新方式で再適用します",
    "저장된 표정 프리셋을 컨트롤러에 적용합니다": "保存済みの表情プリセットをコントローラーに適用します",
    "저장된 프리셋이 없습니다": "保存されたプリセットがありません",
    "적용 (다시 굽기)": "適用 (再ベイク)",
    "적용 중...": "適用中...",
    "전용 립싱크 편집 창을 엽니다. 파형과 모음 구간을 보며 구간을 클릭해 A/I/U/E/O를 바꿀 수 있습니다": "専用のリップシンク編集ウィンドウを開きます。波形と母音区間を見ながら区間をクリックしてA/I/U/E/Oを変更できます",
    "전체 입 벌림 강도": "全体の口の開き強度",
    "정지": "停止",
    "조작법": "操作方法",
    "좌": "左",
    "좌/우 포함식을 바꿔 반대쪽 셰이프 키를 찾아, 같은 설정과 색상으로 반대쪽 컨트롤러를 만듭니다 (위치는 패널 중심 기준 미러)": "左右トークンを入れ替えて反対側のシェイプキーを探し、同じ設定と色で反対側のコントローラーを作成します (位置はパネル中心基準でミラー)",
    "좌/우 포함식을 바꿔 반대쪽 셰이프 키를 찾아, 같은 설정과 색상으로 반대쪽 컨트롤러를 만듭니다 (위치는 패널 중심 기준 미러). 체크된 항목이 2개 이상이면 체크된 것들을 한꺼번에 미러합니다": "左右トークンを入れ替えて反対側のシェイプキーを探し、同じ設定と色で反対側のコントローラーを作成します (位置はパネル中心基準でミラー)。チェックが2個以上ならまとめてミラーします",
    "좌상 (대각)": "左上 (対角)",
    "좌우 갸웃(롤)을 보낼 본 로컬 축": "左右の傾げ(ロール)を送るボーンローカル軸",
    "좌우 돌림(요)을 보낼 본 로컬 축": "左右の振り向き(ヨー)を送るボーンローカル軸",
    "좌우 반전": "左右反転",
    "좌측 포함식": "左トークン",
    "좌하 (대각)": "左下 (対角)",
    "중앙 (원점)": "中央 (原点)",
    "중지": "停止",
    "즐겨찾기 수정": "お気に入りを編集",
    "즐겨찾기 이름:": "お気に入り名:",
    "지금의 컨트롤러 위치들을 기본 표정으로 저장합니다. '기본값으로 되돌리기'가 이 상태로 복원합니다": "現在のコントローラー位置をデフォルト表情として保存します。「デフォルトに戻す」がこの状態に復元します",
    "직접 움직일 셰이프 키": "直接動かすシェイプキー",
    "체크된 컨트롤러가 없습니다": "チェック済みコントローラーがありません",
    "체크된 컨트롤러들을 한 번에 수정합니다 (체크된 항목의 연필 버튼으로 열림). 같은 타입끼리만 가능하며, 값이 서로 다른 항목은 '(다수 선택됨)'으로 표시됩니다": "チェック済みコントローラーを一括編集します (チェック項目の鉛筆ボタンで開く)。同タイプ同士のみ可能で、値が異なる項目は「(複数値)」と表示されます",
    "체크된 컨트롤러들을 한 번에 수정합니다. 같은 타입끼리만 가능하며, 값이 서로 다른 항목은 '(다수 선택됨)'으로 표시됩니다": "チェック済みコントローラーを一括編集します。同タイプ同士のみ可能で、値が異なる項目は「(複数値)」と表示されます",
    "체크하고 OK를 누르면 이 연쇄가 삭제됩니다": "チェックしてOKでこの連動を削除します",
    "체크한 컨트롤러들을 선택한 컬렉션에 넣거나 뺍니다": "チェック済みコントローラーを選択コレクションに入れる/外す",
    "체크한 컨트롤러를 컬렉션 밖으로": "チェック済みコントローラーをコレクション外へ",
    "최대 음량 대비 이 비율 아래면 입을 다뭅니다": "最大音量に対しこの比率未満なら口を閉じます",
    "최댓값": "最大値",
    "최댓값이 최솟값보다 커야 합니다": "最大値は最小値より大きい必要があります",
    "최솟값": "最小値",
    "추가된 컨트롤러가 없습니다": "追加されたコントローラーがありません",
    "축 적용": "軸を適用",
    "카운트다운 (초)": "カウントダウン (秒)",
    "카운트다운 취소": "カウントダウンをキャンセル",
    "캘리브레이션 보정을 지우고 원본 수신값을 사용합니다": "キャリブレーション補正を消して生の受信値を使います",
    "캘리브레이션 완료: 지금 표정이 기준이 됩니다": "キャリブレーション完了: 現在の表情が基準になります",
    "캘리브레이션 적용 중": "キャリブレーション適用中",
    "캘리브레이션 해제": "キャリブレーション解除",
    "캡처 중 프리셋 적용": "キャプチャ中プリセット適用",
    "커브 %d개: 키 %d개 → %d개 (%d개 제거)": "カーブ%d本: キー%d個 → %d個 (%d個削除)",
    "컨트롤러": "コントローラー",
    "컨트롤러 %d개 → '%s'": "コントローラー%d個 → '%s'",
    "컨트롤러 %d개 삭제": "コントローラー%d個を削除",
    "컨트롤러 %d개 정렬 완료": "コントローラー%d個を整列しました",
    "컨트롤러 %d개를 컬렉션에서 제거": "コントローラー%d個をコレクションから外しました",
    "컨트롤러 %d개에 키프레임 삽입": "コントローラー%d個にキーフレーム挿入",
    "컨트롤러 %d개의 기본값 저장 완료": "コントローラー%d個のデフォルトを保存しました",
    "컨트롤러 %d개의 색상 동기화 완료": "コントローラー%d個の色を同期しました",
    "컨트롤러 목록": "コントローラーリスト",
    "컨트롤러 삭제": "コントローラー削除",
    "컨트롤러 선택": "コントローラー選択",
    "컨트롤러 수정": "コントローラー編集",
    "컨트롤러를 고르면 그 색을 그대로 따옵니다": "コントローラーを選ぶとその色をそのまま取得します",
    "컨트롤러마다 역할(눈 감기/눈썹/입 모음/눈동자)을 고르면 ARKit 매핑을 자동으로 만들어 줍니다. 이름으로 미리 추측해서 채워둡니다": "コントローラーごとに役割(まばたき/眉/口母音/瞳)を選ぶとARKitマッピングを自動作成します。名前から推測して事前入力します",
    "컨트롤러마다 역할을 고르세요": "コントローラーごとに役割を選んでください",
    "컨트롤러의 틀을 선택해서 G/R/S로 자유롭게 배치합니다. 끄면 다시 핸들 조작 모드로 돌아갑니다": "コントローラーの枠を選択しG/R/Sで自由配置します。オフでハンドル操作モードに戻ります",
    "컬렉션 '%s' 생성": "コレクション'%s'を作成",
    "컬렉션 삭제": "コレクション削除",
    "컬렉션 이름": "コレクション名",
    "컬렉션 이름을 입력하세요": "コレクション名を入力してください",
    "컬렉션 추가": "コレクション追加",
    "컬렉션에 넣거나 뺄 컨트롤러 체크": "コレクションに入れる/外すコントローラーをチェック",
    "컬렉션을 없애고 소속 컨트롤러를 컬렉션 밖으로 뺍니다 (컨트롤러는 유지)": "コレクションを削除し所属コントローラーを外に出します (コントローラーは維持)",
    "켬": "オン",
    "크기": "サイズ",
    "크기: %s · 길이: %s": "サイズ: %s · 長さ: %s",
    "클릭 = 위치 · 드래그 = 구간 선택 · Space = 재생 · 휠 = 줌 · Shift+휠 = 이동": "クリック = 位置 · ドラッグ = 範囲選択 · Space = 再生 · ホイール = ズーム · Shift+ホイール = 移動",
    "키프레임: I > Location (또는 자동 키)": "キーフレーム: I > Location (または自動キー)",
    "타입": "タイプ",
    "타입/방향/셰이프 키/라벨을 변경합니다": "タイプ/方向/シェイプキー/ラベルを変更します",
    "타입이 섞여 있습니다. 같은 타입끼리만 일괄 수정할 수 있습니다": "タイプが混在しています。同タイプ同士のみ一括編集できます",
    "텍스트 %d개 색상 변경": "テキスト%d個の色を変更",
    "텍스트 %d개에 가장 가까운 컨트롤러 색 적용": "テキスト%d個に最寄りのコントローラー色を適用",
    "텍스트 색상": "テキストカラー",
    "텍스트 색상 자동": "テキストカラー自動",
    "텍스트 생성: G/S로 배치, Tab으로 내용 수정": "テキスト作成: G/Sで配置、Tabで内容編集",
    "텍스트 추가": "テキスト追加",
    "텍스트 추가 = 자유 라벨 (오브젝트 모드에서 편집)": "テキスト追加 = 自由ラベル (オブジェクトモードで編集)",
    "텍스트(라벨)의 색상을 변경합니다. 포즈 모드에서도 대상 텍스트를 골라 적용할 수 있고, 컨트롤러 색을 따올 수 있습니다": "テキスト(ラベル)の色を変更します。ポーズモードでも対象テキストを選んで適用でき、コントローラーの色を取得できます",
    "투명도": "不透明度",
    "파일: ": "ファイル: ",
    "파일을 읽을 수 없습니다: %s": "ファイルを読み込めません: %s",
    "파형 함께 이동": "波形も一緒に移動",
    "패널": "パネル",
    "패널 높이 기준이 될 본 (예: c_head.x)": "パネル高さの基準ボーン (例: c_head.x)",
    "패널 레이아웃(컨트롤러/텍스트/컬렉션)을 JSON으로 저장합니다": "パネルレイアウト(コントローラー/テキスト/コレクション)をJSONで保存します",
    "패널 리로드 완료 (컨트롤러 %d개)": "パネルリロード完了 (コントローラー%d個)",
    "패널 본은 대상으로 쓸 수 없습니다": "パネルのボーンは対象にできません",
    "패널 위치 저장: 컨트롤러가 여기에 생성됩니다": "パネル位置を保存: コントローラーはここに作成されます",
    "패널 위치 지정": "パネル位置を指定",
    "패널 전체 이동: FP_root 본을 G로 이동": "パネル全体移動: FP_rootボーンをGで移動",
    "패널 전체 제거": "パネル全体を削除",
    "패널 위치 (그랩 바)": "パネル位置（グラブバー）",
    "캐릭터 따라다니기": "キャラクターに追従",
    "패널(그랩 바)과 뷰포트 컨트롤러가 아래 본을 따라다니며 지금의 상대 위치를 계속 유지합니다. 캐릭터가 움직여도 옆에 붙어 있습니다 (켜면 리그의 c_pos·root 본을 자동으로 고름)": "パネル（グラブバー）とビューポートコントローラーが下のボーンに追従し、現在の相対位置を保ちます。キャラクターが動いても横に付いてきます（オンにするとリグの c_pos・root ボーンを自動で選択）",
    "따라갈 본이 있는 아마추어 (캐릭터 리그)": "追従するボーンがあるアーマチュア（キャラクターリグ）",
    "패널이 따라갈 본 (보통 머리 본)": "パネルが追従するボーン（通常は頭のボーン）",
    "현재 위치로 고정": "現在の位置で固定",
    "지금 보이는 패널 위치를 기준으로 다시 묶습니다. 캐릭터나 패널을 옮긴 뒤 위치가 어긋났을 때 누르세요": "今のパネル位置を基準に結び直します。キャラクターやパネルを動かして位置がずれたときに押してください",
    "대상 리그와 본을 먼저 지정하세요": "先に対象のリグとボーンを指定してください",
    "패널 위치를 고정했습니다": "パネル位置を固定しました",
    "여기서 고른 오디오만 재생됩니다 (나머지 사운드는 자동 음소거). 립싱크 분석용 오디오와 따로 조절됩니다": "ここで選んだオーディオだけが再生されます（他のサウンドは自動でミュート）。リップシンク解析用オーディオとは別に調整されます",
    "재생 오디오 (스페이스바)": "再生オーディオ（スペースキー）",
    "재생 오디오": "再生オーディオ",
    "재생 오디오 추가": "再生オーディオを追加",
    "재생 오디오 제거": "再生オーディオを削除",
    "재생 오디오 추가: %s": "再生オーディオを追加しました: %s",
    "재생 오디오 제거: %s": "再生オーディオを削除しました: %s",
    "(선택 안 함)": "（未選択）",
    " (립싱크)": "（リップシンク）",
    "시퀀서 사운드 스트립": "シーケンサーのサウンドストリップ",
    "스피커 오브젝트": "スピーカーオブジェクト",
    "블렌더에서 재생할 때 들리는 오디오를 고릅니다. 립싱크 분석용 오디오와 따로 조절됩니다": "Blenderで再生したときに聞こえるオーディオを選びます。リップシンク解析用オーディオとは別に調整されます",
    "재생 오디오의 볼륨": "再生オーディオの音量",
    "재생 오디오만 잠시 끕니다 (립싱크 편집기 소리는 유지)": "再生オーディオだけを一時的に消します（リップシンクエディターの音はそのまま）",
    "사운드 스트립이 시작할 프레임": "サウンドストリップの開始フレーム",
    "스페이스바로 재생할 때 들리는 오디오를 시퀀서에 추가합니다. 립싱크 분석용 오디오와는 별개라 여기서 볼륨/음소거/시작 프레임만 따로 조절할 수 있습니다": "再生時に聞こえるオーディオをシーケンサーに追加します。リップシンク解析用とは別なので、音量・ミュート・開始フレームをここで個別に調整できます",
    "립싱크 사운드 음소거": "リップシンク音をミュート",
    "립싱크용 사운드가 함께 울려 이중으로 들리는 것을 막습니다": "リップシンク用の音が同時に鳴って二重になるのを防ぎます",
    "선택한 재생 오디오를 제거합니다 (시퀀서 스트립만 해당). 립싱크 데이터는 그대로 남습니다": "選択した再生オーディオを削除します（シーケンサーストリップのみ）。リップシンクデータはそのまま残ります",
    "영역으로 생성": "選択範囲から作成",
    "드래그로 선택한 범위를 클러스터로 만듭니다": "ドラッグで選択した範囲をクラスターにします",
    "쪼개기": "分割",
    "재생 헤드(빨간 세로선) 위치에서 클러스터를 둘로 나눕니다": "再生ヘッド（赤い縦線）の位置でクラスターを二つに分けます",
    "선택 삭제": "選択を削除",
    "선택한 클러스터 하나만 삭제": "選択したクラスターだけを削除します",
    "먼저 파형에서 범위를 드래그해 선택하세요": "先に波形上で範囲をドラッグして選択してください",
    "재생 헤드가 클러스터 안에 있어야 합니다": "再生ヘッドがクラスターの中にある必要があります",
    "먼저 클러스터를 클릭해 선택하세요": "先にクラスターをクリックして選択してください",
    "클러스터를 클릭하면 이름을 지정할 수 있습니다": "クラスターをクリックすると名前を指定できます",
    "시작 이름": "開始名",
    "끝 이름": "終了名",
    "마커 이름. 한쪽만 적으면 반대쪽도 같은 이름이 됩니다. 비우면 기본 이름(LS_01A/B)": "マーカー名。片方だけ入力すると反対側も同じ名前になります。空欄なら既定名（LS_01A/B）",
    "간격": "間隔",
    "클러스터 (프레임 단위)": "クラスター（フレーム）",
    "클러스터 제거": "クラスター削除",
    "클러스터 간격": "クラスター間隔",
    "클러스터 생성": "クラスター検出",
    "말소리 덩어리를 자동으로 찾아 표시합니다. 양 끝을 드래그해 조절하고, 위쪽 띠를 클릭해 선택 후 Del로 삭제할 수 있습니다. '적용'을 누르면 블렌더 타임라인에 마커로 만들어집니다": "音声のかたまりを自動で検出して表示します。両端をドラッグで調整、上部の帯をクリックして選択しDelで削除できます。「適用」でBlenderのタイムラインマーカーになります",
    "클러스터 간격 (프레임): 이만큼 이하로 떨어진 소리는 한 덩어리로 봅니다": "クラスター間隔（フレーム）: これ以下の間隔の音は一つのかたまりとみなします",
    "클러스터 모두 지우기": "クラスターをすべて消去",
    "프레임 레이트가 %.4g → %.4g로 바뀌어 립싱크를 재배치했습니다": "フレームレートが %.4g → %.4g に変わったため、リップシンクを再配置しました",
    "프레임 레이트 변경 감지: 립싱크를 새 프레임 레이트에 맞춰 재배치했습니다": "フレームレート変更を検出：リップシンクを新しいフレームレートに合わせて再配置しました",
    "선택한 리그 자동 전환": "選択したリグへ自動切替",
    "뷰포트에서 패널이 있는 다른 리그를 선택하면 이 패널 설정(컨트롤러 목록/프리셋/모캡/립싱크)을 그 캐릭터의 것으로 자동 전환합니다": "パネルを持つ別のリグを選択すると、パネル設定（コントローラー／プリセット／モーキャプ／リップシンク）がそのキャラクターへ自動的に切り替わります",
    "캐릭터 이동 준비": "キャラクター移行の準備",
    "캐릭터 가져오기": "キャラクターを読み込む",
    "가져온 리그": "アペンドしたリグ",
    "씬 설정만 복구": "シーン設定のみ復元",
    "씬 설정(컬렉션/프리셋/모캡/립싱크/라벨)을 리그에 저장합니다. 다른 파일에서 리그와 메시를 Append 한 뒤 '캐릭터 가져오기'로 복구하세요. 파일 저장 시 자동 갱신됩니다": "シーン設定（コレクション／プリセット／モーキャプ／リップシンク／ラベル）をリグに保存します。別ファイルでリグとメッシュをアペンド後「キャラクターを読み込む」で復元。ファイル保存時に自動更新",
    "Append 한 리그에서 캐릭터 설정을 복구합니다. 컨트롤러는 새로 만들지 않고 기존 본의 설정을 그대로 사용합니다": "アペンドしたリグからキャラクター設定を復元します。既存のコントローラーボーンを再利用し、複製しません",
    "패널 리로드와 라벨 재생성 없이 컬렉션/프리셋/모캡/립싱크 설정만 복구합니다": "パネル再読込やラベル再生成を行わず、コレクション／プリセット／モーキャプ／リップシンクのみ復元",
    "캐릭터 설정을 리그에 저장했습니다 (라벨 %d개 포함)": "キャラクター設定をリグに保存しました（ラベル%d個を含む）",
    "이 리그에는 캐릭터 스냅샷이 없습니다. 원본 파일에서 '캐릭터 이동 준비'를 먼저 실행하세요": "このリグにはスナップショットがありません。元ファイルで「キャラクター移行の準備」を先に実行してください",
    "캐릭터 가져오기 완료 (라벨 %d개 재생성)": "キャラクター読み込み完了（ラベル%d個を再生成）",
    "패널을 옮겼습니다": "パネルを移動しました",
    "패드 슬롯 표시 순번": "パッドスロット表示番号",
    "패드 슬롯 표시 순번. 숫자를 고치면 그 위치로 끼어듭니다": "パッドスロット表示番号。数字を変えるとその位置に割り込みます",
    "패드 아래로": "パッド下へ",
    "패드 오른쪽으로": "パッド右へ",
    "패드 왼쪽으로": "パッド左へ",
    "패드 위로": "パッド上へ",
    "패드 추가: ": "パッド追加: ",
    "패드: 같은 키를 상+하에 넣으면 -1~1 범위": "パッド: 同じキーを上+下に入れると-1~1範囲",
    "패드에 연결된 셰이프 키와 값 표시": "パッドに接続されたシェイプキーと値を表示",
    "패드의 모든 값에 곱해질 배율 (예: 0.5 = 절반 강도, 음수 = 반대 방향)": "パッドの全値に掛ける倍率 (例: 0.5 = 半分、マイナス = 逆方向)",
    "편집기가 종료되었습니다. 탭을 닫아 주세요.": "エディターを終了しました。タブを閉じてください。",
    "편집한 모음 구간대로 립싱크 키프레임을 다시 굽습니다": "編集した母音区間どおりにリップシンクのキーフレームを再ベイクします",
    "펼치기": "展開",
    "포즈 모드에서 컨트롤러 선택 후 G로 이동": "ポーズモードでコントローラーを選択しGで移動",
    "포트 49983 열기 실패: %s": "ポート49983を開けません: %s",
    "표정": "表情",
    "표정 전체 키프레임": "表情全体にキーフレーム",
    "표정 패널 제거 완료": "表情パネルを削除しました",
    "표정 프리셋": "表情プリセット",
    "표정 프리셋의 이름을 바꿉니다": "表情プリセットの名前を変更します",
    "프레임 구간의 드라이버 값을 셰이프 키 키프레임으로 굽고 드라이버를 제거합니다. FBX/VRM 익스포트 전에 사용하세요. 패널 복구는 '뷰포트 패널 리로드'": "フレーム区間のドライバー値をシェイプキーのキーフレームにベイクしドライバーを削除します。FBX/VRMエクスポート前に使用してください。復旧は「ビューポートパネルをリロード」",
    "프레임 범위": "フレーム範囲",
    "프레임 클릭 = 이동": "フレームクリック = 移動",
    "프레임 클릭 = 이동 · OK = 다시 굽기": "フレームクリック = 移動 · OK = 再ベイク",
    "프리셋 %d번이 없습니다": "プリセット%d番がありません",
    "프리셋 '%s' 저장 (컨트롤러 %d개)": "プリセット'%s'を保存 (コントローラー%d個)",
    "프리셋 데이터가 손상되었습니다": "プリセットデータが破損しています",
    "프리셋 블렌딩 (초)": "プリセットブレンド (秒)",
    "프리셋 삭제": "プリセット削除",
    "프리셋 이름": "プリセット名",
    "프리셋 이름 변경": "プリセット名を変更",
    "프리셋 이름을 입력하세요": "プリセット名を入力してください",
    "프리셋 저장": "プリセット保存",
    "프리셋 적용": "プリセット適用",
    "프리셋 적용: ": "プリセット適用: ",
    "프리셋 전환에 걸리는 시간. 0이면 즉시 전환": "プリセット切替にかかる時間。0で即時切替",
    "한국어": "한국어",
    "함께 움직일 두 번째 본": "一緒に動く2つ目のボーン",
    "함께 움직일 두 번째 본 (양눈 동시 제어용, 비우면 1개만)": "一緒に動く2つ目のボーン (両目同時制御用、空欄で1つのみ)",
    "항상 위": "常に手前に表示",
    "해제": "解除",
    "핸들 XY로 본(눈알 타겟 등)의 위치를 움직임": "ハンドルXYでボーン(眼球ターゲットなど)の位置を動かす",
    "핸들 상하 이동을 대상 본의 어느 로컬 축으로 보낼지": "ハンドル上下移動を送るターゲットボーンのローカル軸",
    "핸들 좌우 이동을 대상 본의 어느 로컬 축으로 보낼지. 본을 G로 움직여 눈이 좌우로 도는 축을 고르세요": "ハンドル左右移動を送るターゲットボーンのローカル軸。ボーンをGで動かし、目が左右に動く軸を選んでください",
    "핸들을 따라 움직일 본": "ハンドルに追従するボーン",
    "핸들을 따라 움직일 본 (예: c_eye_target.l)": "ハンドルに追従するボーン (例: c_eye_target.l)",
    "핸들을 오른쪽 끝까지 밀었을 때 본이 이동하는 거리. 음수 = 반대 방향": "ハンドルを右端まで動かした時のボーン移動距離。マイナス = 逆方向",
    "핸들을 위 끝까지 밀었을 때 본이 이동하는 거리. 음수 = 반대 방향": "ハンドルを上端まで動かした時のボーン移動距離。マイナス = 逆方向",
    "핸들의 XY 이동으로 리그의 본(눈알 타겟 등)을 움직이는 2D 패드를 추가합니다. 본을 2개 넣으면 동시에 움직입니다 (양눈). 눈마다 따로 만들려면 본 1개씩 + 미러를 쓰세요": "ハンドルのXY移動でリグのボーン(眼球ターゲットなど)を動かす2Dパッドを追加します。ボーンを2つ入れると同時に動きます (両目)。片目ずつ作るならボーン1つ+ミラーを使ってください",
    "핸들이 앵커 반경 안이면 위치와 값이 고정 (0 = 끄기)": "ハンドルがアンカー半径内なら位置と値を固定 (0 = オフ)",
    "핸들이 앵커(모서리/변 중앙/중앙) 반경 안이면 위치와 값이 앵커에 고정됩니다. 이동 범위 대비 비율 (0=끄기)": "ハンドルがアンカー(角/辺中央/中央)の半径内なら位置と値がアンカーに固定されます。移動範囲比 (0=オフ)",
    "핸들이 앵커(시작/중간/끝) 반경 안이면 위치와 값이 고정 (0 = 스냅 끄기)": "ハンドルがアンカー(始/中/終)の半径内なら位置と値を固定 (0 = スナップオフ)",
    "허용 오차": "許容誤差",
    "현재 값을 기본값으로 저장": "現在値をデフォルトとして保存",
    "현재 뷰포트 컨트롤러의 실제 본 색상을 읽어 목록 스와치와 메타데이터에 동기화합니다 (애드온 재설치 후 색이 어긋날 때)": "現在のビューポートコントローラーの実際のボーン色を読み、リストのスウォッチとメタデータに同期します (アドオン再インストール後に色がずれた時)",
    "현재 컨트롤러 값들을 표정 프리셋으로 저장합니다": "現在のコントローラー値を表情プリセットとして保存します",
    "현재 프레임에 모든 컨트롤러의 키프레임을 삽입합니다": "現在フレームに全コントローラーのキーフレームを挿入します",
    "형식: ": "形式: ",
    "화살표 = 목록 순서 이동, 그룹은 수정 팝업에서": "矢印 = リスト順移動、グループは編集ポップアップで",
    "확인": "OK",
    "확정: 클릭 · 취소: 우클릭/ESC": "確定: クリック · キャンセル: 右クリック/ESC",
    "조작 중: 확정 = 클릭 · 취소 = 우클릭/ESC":
        "操作中: 確定 = クリック · キャンセル = 右クリック/ESC",
    "배치 모드 끄기: ESC 또는 우클릭 (조작 중이 아닐 때)":
        "配置モード終了: ESC または右クリック (操作中でないとき)",
    "회전 배율": "回転倍率",
    "히스토리": "履歴",
}


_ZH = {
    "패널 정렬 복구": "修复面板对齐",
    "틀/핸들에 남은 포즈 회전을 초기화해 배치 모드 화살표와 스냅을 정상화합니다 (위치·크기·값은 유지)": "清除框/手柄上残留的旋转，使排布模式的箭头与吸附恢复正常 (位置、大小和数值保持不变)",
    "패널 정렬 복구 완료 (%d개)": "面板对齐已修复 (%d个)",
    "머리에 부착": "跟随头部",
    "패널이 따라갈 본": "面板跟随的骨骼",
    "패널을 본에 붙이기 (해제하려면 본을 비우고 실행)": "将面板附加到骨骼 (清空骨骼后执行即解除)",
    "패널 부착: ": "面板已附加: ",
    "패널 부착 해제": "已解除面板附加",
    "구동 방식": "驱动方式",
    "위치 (이동)": "位置 (移动)",
    "회전 (머리 기준)": "旋转 (以头部为准)",
    "본을 이동시킬지, 제자리에서 회전시킬지": "移动骨骼，或在原地旋转",
    "가로 회전량 (도)": "水平旋转量 (度)",
    "세로 회전량 (도)": "垂直旋转量 (度)",
    " (%s 패드)": " (%s面板)",
    " (셰이프 키 없음 %d개 건너뜀)": " (缺少形态键，跳过%d个)",
    " (컨트롤러 %d개 추가)": " (添加了%d个控制器)",
    " (패드)": " (面板)",
    " [%s축]": " [%s轴]",
    "%d초 후 녹화 시작": "%d秒后开始录制",
    "%s: 대상 본 '%s'의 좌/우 짝을 리그 '%s'에서 찾지 못했습니다": "%s: 在绑定'%s'中找不到目标骨骼'%s'的左右配对",
    "%s: 반대쪽 셰이프 키 '%s' 없음 (메시 '%s')": "%s: 找不到对侧形态键'%s' (网格'%s')",
    "%s: 연쇄 셰이프 키 '%s' 없음 (메시 '%s')": "%s: 找不到联动形态键'%s' (网格'%s')",
    "%s: 키 이름에서 '%s'/'%s'를 찾지 못했습니다": "%s: 键名中找不到'%s'/'%s'",
    "'%s' 적용 (컨트롤러 %d개)": "已应用'%s' (%d个控制器)",
    "'에' 채널 (조합)": "「诶」通道 (组合)",
    "(그룹 없음)": "(无分组)",
    "(기존 그룹에서 선택)": "(从现有分组选择)",
    "(다수 선택됨)": "(多个值)",
    "(변경 안 함)": "(不更改)",
    "(비어 있음)": "(空)",
    "(사용 안 함)": "(不使用)",
    "(선택된 텍스트)": "(选中的文本)",
    "(설정의 얼굴 메시)": "(设置中的面部网格)",
    "(아마추어 없음)": "(无骨架)",
    "(없음)": "(无)",
    "(직접 지정)": "(手动指定)",
    "(컨트롤러 없음)": "(无控制器)",
    "(컬렉션에서 제거)": "(从集合移除)",
    "1프레임 뒤로": "后退1帧",
    "1프레임 앞으로": "前进1帧",
    "2D 패드": "2D面板",
    "2D 패드 추가": "添加2D面板",
    "3D 뷰포트 > N패널 > Face Rig 탭": "3D视口 > N面板 > Face Rig选项卡",
    "3D 뷰포트에서 실행하세요": "请在3D视口中执行",
    "Calibrate (중립 캡처)": "Calibrate (中立校准)",
    "FLAC (무손실)": "FLAC (无损)",
    "G: 이동  (Ctrl = 모서리/중앙 스냅)": "G: 移动  (Ctrl = 角/中心吸附)",
    "JSON 레이아웃을 불러와 패널을 구성합니다. 같은 이름의 셰이프 키에 자동 연결되며, 없는 키의 컨트롤러는 건너뜁니다": "读取JSON布局并构建面板。自动连接同名形态键，缺少的键对应的控制器将被跳过",
    "N패널 설정에서 지정한 메시의 셰이프 키 사용": "使用N面板设置中指定网格的形态键",
    "R / S: 회전 / 크기": "R / S: 旋转 / 缩放",
    "WAV PCM %d비트": "WAV PCM %d位",
    "WAV를 읽을 수 없습니다: %s": "无法读取WAV: %s",
    "[배치 모드]": "[排布模式]",
    "iFacialMocap 수신 시작 (포트 49983)": "iFacialMocap开始接收 (端口49983)",
    "iFacialMocap 수신 중지": "iFacialMocap已停止接收",
    "iFacialMocap 수신을 시작합니다. 아이폰과 PC가 같은 와이파이에 있어야 하며, 앱이 켜져 있어야 합니다": "开始接收iFacialMocap。iPhone和电脑需在同一Wi-Fi，且应用已打开",
    "iFacialMocap 수신을 중지합니다": "停止接收iFacialMocap",
    "iFacialMocap 앱 화면에 표시되는 아이폰의 IP 주소 (같은 와이파이여야 함)": "iFacialMocap应用中显示的iPhone IP地址 (需在同一Wi-Fi)",
    "iFacialMocap 캡처 중 숫자키로 표정 프리셋을 적용합니다 (1~9 = 프리셋 순번, 0 = 기본 표정). 캡처 중이 아니면 숫자키는 원래 기능대로 동작합니다": "捕捉中用数字键应用表情预设 (1~9 = 预设序号，0 = 默认表情)。未在捕捉时数字键按原功能工作",
    "jawOpen 등에서 자동 계산되는 '아' 채널": "由jawOpen等自动计算的「啊」通道",
    "mocap 녹화로 촘촘히 박힌 키프레임을 모양을 유지하는 한도 안에서 줄입니다 (핸들 위치·목 회전·셰이프 키 값). 그래프 에디터에서 손질하기 쉬워집니다": "在保持曲线形状的范围内精简动捕录制产生的密集关键帧 (手柄位置·颈部旋转·形态键值)。方便在曲线编辑器中修整",
    "mouthFunnel에서 계산되는 '오' 채널": "由mouthFunnel计算的「哦」通道",
    "mouthPucker에서 계산되는 '우' 채널": "由mouthPucker计算的「呜」通道",
    "numpy를 사용할 수 없습니다": "无法使用numpy",
    "← 왼쪽": "← 左",
    "↑ 위": "↑ 上",
    "→ 오른쪽": "→ 右",
    "↓ 아래": "↓ 下",
    "↖ 좌상": "↖ 左上",
    "↗ 우상": "↗ 右上",
    "↘ 우하": "↘ 右下",
    "↙ 좌하": "↙ 左下",
    "가로": "横向",
    "가로 → 본 축": "横向 → 骨骼轴",
    "가로 이동량": "横向移动量",
    "가져오기 완료: 컨트롤러 %d개, 텍스트 %d개": "导入完成: %d个控制器、%d个文本",
    "각 텍스트에서 가장 가까운 컨트롤러를 찾아 그 색을 자동으로 적용합니다 (색상을 사용하는 컨트롤러 기준)": "为每个文本查找最近的控制器并自动应用其颜色 (以使用颜色的控制器为准)",
    "간단 자동 설정": "快速自动设置",
    "값": "值",
    "값 −": "值 −",
    "값 단위 오차 한도. 클수록 키가 많이 줄어듭니다": "以值为单位的误差上限。越大删除的关键帧越多",
    "값 떨림 완화. 높을수록 부드럽지만 반응이 느려집니다": "减轻数值抖动。越高越平滑但响应越慢",
    "같은 그룹끼리 목록에서 묶어 표시 (비우면 그룹 없음)": "同组在列表中归类显示 (留空则无分组)",
    "같은 이름의 프리셋이 있습니다": "已存在同名预设",
    "갸웃 →": "歪头 →",
    "갸웃 방향 반전": "反转歪头方向",
    "구간 앞뒤로 이만큼의 프레임에 걸쳐 부드럽게 전환": "在每个区间前后此帧数内平滑过渡",
    "구간 적용 (다시 굽기)": "应用区段 (重新烘焙)",
    "구간으로 이동": "跳到区段",
    "그래프 에디터를 새 창으로 열어 모음 구간을 편집합니다. 사이드바의 Face Rig 탭에 구간 목록이 있습니다": "在新窗口中打开曲线编辑器以编辑元音区段。区段列表在侧栏的Face Rig选项卡中",
    "그룹": "分组",
    "기본 표정으로": "回到默认表情",
    "기본값으로 되돌리기": "恢复默认值",
    "기존 그룹": "现有分组",
    "기존 그룹/컬렉션에서 골라 채웁니다": "从现有分组/集合中选择填入",
    "끄덕임 →": "点头 →",
    "끄덕임 방향 반전": "反转点头方向",
    "끔": "关",
    "끝 프레임": "结束帧",
    "내용": "内容",
    "노란 화살표 드래그: 변 크기 조절  (Ctrl = 스냅, Alt = 대칭)": "拖动黄色箭头: 调整边大小  (Ctrl = 吸附、Alt = 对称)",
    "녹화": "录制",
    "녹화 시작": "开始录制",
    "녹화 시작 버튼을 누른 뒤 재생까지의 대기 시간 (0 = 즉시 시작)": "按下开始录制后到播放的等待时间 (0 = 立即开始)",
    "녹화 정지": "已停止录制",
    "녹화 커브 단순화": "简化录制曲线",
    "눈": "眼睛",
    "눈 리그": "眼睛绑定",
    "눈 회전 반영 정도": "眼球旋转的应用程度",
    "눈동자": "瞳孔",
    "눈썹": "眉毛",
    "눈알 본이 들어있는 아마추어": "包含眼球骨骼的骨架",
    "눈알 본이 바라보는 방향의 로컬 축": "眼球骨骼朝向的本地轴",
    "단순화할 커브가 없습니다": "没有可简化的曲线",
    "닫기": "关闭",
    "대기 중 (앱/와이파이/IP 확인)": "等待中 (检查应用/Wi-Fi/IP)",
    "대사 녹음(WAV)을 분석해 A/I/U/E/O 립싱크 키프레임을 자동 생성합니다. '간단 자동 설정'의 입 매핑을 그대로 사용하므로 먼저 매핑을 만들어 두세요": "分析台词录音(WAV)并自动生成A/I/U/E/O口型关键帧。使用快速自动设置的嘴部映射，请先创建映射",
    "대사 녹음(WAV/MP3/OGG/FLAC)을 분석해 A/I/U/E/O 립싱크 키프레임을 자동 생성합니다. '간단 자동 설정'의 입 매핑을 그대로 사용하므로 먼저 매핑을 만들어 두세요": "分析台词录音(WAV/MP3/OGG/FLAC)并自动生成A/I/U/E/O口型关键帧。使用快速自动设置的嘴部映射，请先创建映射",
    "대상": "目标",
    "대상 리그": "目标绑定",
    "대상 리그를 선택하세요": "请选择目标绑定",
    "대상 본 1": "目标骨骼1",
    "대상 본 1을 선택하세요": "请选择目标骨骼1",
    "대상 본 2 (선택)": "目标骨骼2 (可选)",
    "대상 본 이름에서 좌/우 짝(.l/.r 등)을 찾지 못했습니다": "目标骨骼名中找不到左右配对(.l/.r等)",
    "대상 본을 찾을 수 없습니다": "找不到目标骨骼",
    "대상 컬렉션": "目标集合",
    "대상 텍스트": "目标文本",
    "대상 텍스트가 없습니다 (팝업에서 텍스트를 선택하세요)": "没有目标文本 (请在弹窗中选择)",
    "돌림 →": "转头 →",
    "돌림 방향 반전": "反转转头方向",
    "드래그 = 범위 선택 · 클릭 = 이동/선택 해제 · 선택 드래그 = 범위 이동 · + = 구간 추가 · ✂ = 잘라내기 · 패드 = 입모양 · ★ = 즐겨찾기 (우클릭 편집) · Ctrl+Z = 실행취소 · Ctrl+C/V = 복사/붙여넣기 · Del = 삭제 · Space = 재생 · 휠 = 줌 · 휠 클릭 = 패닝": "拖动 = 选择范围 · 单击 = 移动/取消选择 · 拖动选区 = 移动范围 · + = 添加区间 · ✂ = 剪切 · 面板 = 口型 · ★ = 收藏 (右键编辑) · Ctrl+Z = 撤销 · Ctrl+C/V = 复制/粘贴 · Del = 删除 · Space = 播放 · 滚轮 = 缩放 · 中键拖动 = 平移",
    "라벨": "标签",
    "라벨을 셰이프 키(또는 대상 본) 이름으로 채웁니다": "用形态键(或目标骨骼)名称填充标签",
    "레이아웃 가져오기": "导入布局",
    "레이아웃 내보내기": "导出布局",
    "레이아웃 저장: 컨트롤러 %d개, 텍스트 %d개": "布局已保存: %d个控制器、%d个文本",
    "레이아웃 파일이 아닙니다": "不是布局文件",
    "루프": "循环",
    "리그": "绑定",
    "립싱크 구간": "口型区段",
    "립싱크 구간 편집": "编辑口型区段",
    "립싱크 다시 굽기 완료 (%d프레임)": "口型已重新烘焙 (%d帧)",
    "립싱크 데이터가 없습니다": "没有口型数据",
    "립싱크 사운드 제거": "移除口型声音",
    "립싱크 생성: %d프레임 (%.1f초). 필요하면 '녹화 커브 단순화'로 정리하세요": "已生成口型: %d帧 (%.1f秒)。如有需要请用「简化录制曲线」整理",
    "립싱크 자동 재계산": "自动重新计算口型同步",
    "립싱크 키 구간과 겹칩니다. 녹화가 립싱크 키를 덮어쓸 수 있습니다": "与已烘焙的口型同步范围重叠。录制可能会覆盖口型同步关键帧",
    "립싱크 편집 창 열기": "打开口型编辑窗口",
    "립싱크 편집기": "口型编辑器",
    "립싱크 편집기 열기": "打开口型编辑器",
    "립싱크 편집기 재생": "口型编辑器播放",
    "립싱크 편집기 클릭": "口型编辑器点击",
    "매핑 %d개 생성 완료": "已创建%d条映射",
    "매핑 (ARKit → 컨트롤러)": "映射 (ARKit → 控制器)",
    "매핑 삭제": "删除映射",
    "매핑 추가": "添加映射",
    "머리 본": "头部骨骼",
    "머리 회전 반영 정도. 방향이 반대면 음수로": "头部旋转的应用程度。方向相反时用负数",
    "머리 회전을 따라 돌 본 (예: c_head.x, neck)": "跟随头部旋转的骨骼 (如 c_head.x、neck)",
    "머리 회전을 적용할 본이 있는 아마추어": "包含应用头部旋转骨骼的骨架",
    "머리/목 회전": "头/颈旋转",
    "먼저 컨트롤러 옆 체크박스를 선택하세요": "请先勾选控制器旁的复选框",
    "메시": "网格",
    "모노": "单声道",
    "모든 라벨 텍스트 표시/숨김": "显示/隐藏所有标签文本",
    "모든 컨트롤러/라벨/위젯과 셰이프 키 드라이버를 제거합니다": "删除所有控制器/标签/控件及形态键驱动器",
    "모든 컨트롤러를 저장된 기본값으로 되돌립니다. 저장된 기본값이 없으면 0으로 (키프레임은 지우지 않음)": "将所有控制器恢复到已保存的默认值。没有保存则归零 (不删除关键帧)",
    "모음": "元音",
    "목 리그": "颈部绑定",
    "목 본": "颈部骨骼",
    "목록 순번. 숫자를 고치면 그 위치로 끼어듭니다": "列表序号。修改数字即插入到该位置",
    "목록에 표시할 이름 (비우면 대상 본 이름)": "列表中显示的名称 (留空则用目标骨骼名)",
    "목록에서 이름 클릭 = 뷰포트에서 선택": "点击列表中的名称 = 在视口中选中",
    "목록에서 컨트롤러 순서를 위/아래로 이동합니다 (같은 그룹 안에서, Shift = 맨 위/맨 아래로)": "在列表中上下移动控制器顺序 (同组内，Shift = 移到最上/最下)",
    "무음 임계값": "静音阈值",
    "무음화": "静音",
    "무음화 (길이 유지)": "静音 (保持长度)",
    "무표정으로 카메라를 정면으로 본 상태에서 누르세요. 지금 값을 기준(0)으로 저장해서 이후 수신값을 보정합니다. 씬에 저장되어 다음에도 유지됩니다": "请在无表情正视摄像头时按下。将当前值保存为基准(0)并校正之后的接收值。随场景保存，下次仍然有效",
    "미러 아이콘 = 반대쪽 컨트롤러 자동 생성": "镜像图标 = 自动生成对侧控制器",
    "미러 취소 — ": "镜像已取消 — ",
    "미리보기 도식의 표시 배율": "预览示意图的显示比例",
    "미리보기 크기": "预览大小",
    "미지정 (입 다묾)": "未指定 (闭嘴)",
    "반대쪽 셰이프 키가 없습니다: ": "找不到对侧形态键: ",
    "반대쪽 자동 생성": "自动生成对侧",
    "반대쪽 컨트롤러 생성: ": "已生成对侧控制器: ",
    "반전": "反转",
    "방향": "方向",
    "방향 반전": "方向反转",
    "방향을 하나 이상 연결하세요": "请至少连接一个方向",
    "배율": "倍率",
    "배치 모드": "排布模式",
    "배치 모드 ON = 틀을 G/R/S로 자유 배치": "排布模式ON = 用G/R/S自由排布外框",
    "배치 모드: G 이동 중 Ctrl = 모서리 스냅": "排布模式: G移动时Ctrl = 角吸附",
    "배치 모드: 노란 화살표 드래그 = 그 변만 크기 조절": "排布模式: 拖动黄色箭头 = 只调整该边",
    "배치 모드에서 G로 틀을 이동합니다. Shift를 누르는 동안 다른 틀 모서리에 스냅됩니다": "排布模式中用G移动外框。按住Shift时吸附到其他外框的角",
    "배치 모드에서 선택된 틀의 변 화살표를 드래그해 그 변만 이동합니다. Ctrl을 누르는 동안 다른 틀 모서리에 스냅됩니다": "排布模式中拖动选中外框的边箭头以只移动该边。按住Ctrl时吸附到其他外框的角",
    "배치 순서로 정렬": "按排布顺序排序",
    "범위 적용": "应用范围",
    "베이크할 드라이버가 없습니다": "没有可烘焙的驱动器",
    "변 드래그 중 Ctrl = 스냅, Alt = 대칭 조절": "拖动边时Ctrl = 吸附、Alt = 对称调整",
    "변 이동: 드래그=크기 조절, Ctrl=스냅, Alt=대칭 조절, 놓으면 확정, ESC 취소": "移动边: 拖动=调整大小、Ctrl=吸附、Alt=对称、松开确定、ESC取消",
    "변 크기 조절": "调整边大小",
    "보정 해제": "清除校准",
    "본 패드": "骨骼面板",
    "본 패드 = 핸들 XY로 본(눈알 타겟) 이동": "骨骼面板 = 用手柄XY移动骨骼(眼球目标)",
    "본 패드 추가": "添加骨骼面板",
    "본 패드 추가: ": "已添加骨骼面板: ",
    "본을 만들 리그": "创建骨骼的绑定",
    "본을 만들 리그를 선택하세요": "请选择创建骨骼的绑定",
    "볼륨": "音量",
    "뷰포트 배치 위치(위→아래, 왼쪽→오른쪽) 순서대로 목록 순서를 자동 정렬합니다 (그룹별)": "按视口排布位置(上→下、左→右)自动排序列表 (按分组)",
    "뷰포트 색상 다시 불러오기": "重新读取视口颜色",
    "뷰포트 패널 리로드": "重载视口面板",
    "뷰포트 패널 컨트롤러를 움직임 (키프레임은 핸들에 기록)": "驱动视口面板控制器 (关键帧记录在手柄上)",
    "뷰포트에 크로스헤어가 나타납니다. 클릭한 위치에 패널이 생성되고, 이미 있으면 패널 전체가 그곳으로 이동합니다. 우클릭/ESC = 취소": "视口中出现十字光标。面板将在点击位置创建，若已存在则整体移动到该处。右键/ESC = 取消",
    "뷰포트에서 이 컨트롤러를 선택합니다 (배치 모드면 틀을 선택)": "在视口中选中此控制器 (排布模式下选中外框)",
    "브라우저에 전용 립싱크 편집기를 엽니다. 파형과 모음 구간을 보며 구간을 클릭해 A/I/U/E/O를 바꾸고, 적용을 누르면 Blender에 다시 굽습니다": "在浏览器中打开专用口型编辑器。查看波形和元音区段，点击区段修改A/I/U/E/O，按应用重新烘焙到Blender",
    "브라우저에서 립싱크 편집기를 열었습니다": "已在浏览器中打开口型编辑器",
    "블렌딩": "混合",
    "비우고 적용하면 그룹에서 빠집니다": "留空应用即从分组移除",
    "비우면 컨스트레인트 생략": "留空则跳过约束",
    "사용": "启用",
    "사운드 스트립 %d개 제거": "已移除%d个声音片段",
    "사운드 스트립 추가": "添加声音片段",
    "삭제": "删除",
    "상/하/좌/우 방향별 연결": "按上/下/左/右方向连接",
    "상/하/좌/우 방향별로 셰이프 키를 연결한 XY 패드를 추가합니다. 같은 키를 상+하(또는 좌+우)에 넣으면 -1~1 풀레인지로 동작합니다": "添加按上/下/左/右方向连接形态键的XY面板。同一键放入上+下(或左+右)时按-1~1全范围工作",
    "상하 반전": "上下反转",
    "새 이름": "新名称",
    "새 컬렉션을 만듭니다. 체크한 컨트롤러가 있으면 바로 담습니다": "创建新集合。已勾选的控制器会直接放入",
    "색상": "颜色",
    "색상 사용": "使用颜色",
    "색상을 사용하는 컨트롤러가 없습니다": "没有使用颜色的控制器",
    "선택": "选择",
    "선택 → 컬렉션": "勾选 → 集合",
    "선택 범위 립싱크 재계산 (선택 없으면 전체)": "重新计算所选范围的口型同步 (无选择时为全部)",
    "선택 범위 볼륨 조절 (선택 없으면 전체) · 립싱크 재계산": "调整所选范围音量 (无选择时为全部) · 重新计算口型同步",
    "선택 범위 잘라내기 (오디오 포함) · 선택 없으면 타임바에서 분할": "剪切所选范围 (包含音频) · 无选择时在时间条处拆分",
    "선택됨: %d개": "已选: %d个",
    "선택한 셰이프 키를 조절하는 1D 슬라이더를 추가합니다": "添加控制所选形态键的1D滑块",
    "선택한 셰이프 키를 찾을 수 없습니다": "找不到所选形态键",
    "설정": "设置",
    "설정에서 좌/우 포함식을 입력하세요": "请在设置中输入左右标记",
    "성분": "分量",
    "세로": "纵向",
    "세로 → 본 축": "纵向 → 骨骼轴",
    "세로 이동량": "纵向移动量",
    "셰이프 키": "形态键",
    "셰이프 키 %d개 + 본 채널 %d개 x %d프레임 베이크 완료. 드라이버 제거됨 — 패널 복구는 '뷰포트 패널 리로드'": "已烘焙%d个形态键 + %d个骨骼通道 x %d帧。驱动器已删除 — 用「重载视口面板」恢复",
    "셰이프 키 %d개 x %d프레임 베이크 완료. 드라이버 제거됨 — 패널 복구는 '뷰포트 패널 리로드'": "已烘焙%d个形态键 x %d帧。驱动器已删除 — 用「重载视口面板」恢复",
    "셰이프 키 값을 직접 움직임 (패널 컨트롤러 불필요)": "直接驱动形态键值 (无需面板控制器)",
    "셰이프 키 대상일 때: 키가 있는 메시": "目标为形态键时: 键所在的网格",
    "셰이프 키 베이크 (익스포트용)": "烘焙形态键 (用于导出)",
    "셰이프 키 연결에 실패했습니다": "形态键连接失败",
    "셰이프 키 이름 동기화": "同步形态键名称",
    "셰이프 키 이름 복사": "复制形态键名称",
    "셰이프 키 이름과 ARKit 이름을 비교해 매핑을 자동으로 채웁니다 (기존 매핑은 교체). 눈동자 패드 등은 수동으로 추가하세요": "比较形态键名和ARKit名自动填充映射 (替换现有映射)。瞳孔面板等请手动添加",
    "셰이프 키 이름에서 오른쪽을 뜻하는 부분 (예: (Right), .R, _right)": "形态键名中表示右侧的部分 (如 (Right)、.R、_right)",
    "셰이프 키 이름에서 왼쪽을 뜻하는 부분 (예: (Left), .L, _left)": "形态键名中表示左侧的部分 (如 (Left)、.L、_left)",
    "셰이프 키 이름을 바꾼 뒤 실행하세요. 드라이버가 실제로 연결된 키 이름을 읽어 목록/메타데이터를 갱신합니다": "重命名形态键后执行。读取驱动器实际连接的键名并更新列表/元数据",
    "셰이프 키를 가져올 메시 (기본 = 설정의 얼굴 메시)": "获取形态键的网格 (默认 = 设置中的面部网格)",
    "셰이프 키를 골라 1D 슬라이더/2D 패드 컨트롤러를 뷰포트에 조립하는 빌더": "选择形态键并在视口中组装1D滑块/2D面板控制器的构建器",
    "셰이프 키를 선택하세요": "请选择形态键",
    "셰이프 키를 찾을 수 없습니다": "找不到形态键",
    "수신 미리보기": "接收预览",
    "수신 중": "接收中",
    "수신 중인 표정 값을 뷰포트 좌상단에 도식으로 표시": "在视口左上角以示意图显示接收中的表情值",
    "수신 중인 표정 값을 뷰포트에 도식으로 표시": "在视口中以示意图显示接收中的表情值",
    "수신된 데이터가 없습니다": "尚未收到数据",
    "순번": "序号",
    "순서 이동": "移动顺序",
    "숫자키 1~9 = 표정 프리셋, 0 = 기본 표정": "数字键1~9 = 表情预设，0 = 默认表情",
    "스냅 이동": "吸附移动",
    "스냅 적용": "应用吸附",
    "스무딩": "平滑",
    "스크럽 소리": "滑动预览声音",
    "스포이드": "吸管",
    "슬라이더 (가로)": "滑块 (横向)",
    "슬라이더 (세로)": "滑块 (纵向)",
    "슬라이더 값 (반전/양방향 자동 반영)": "滑块值 (自动处理反转/双向)",
    "슬라이더 값에 곱해질 배율 (음수 = 반대로 움직임)": "乘到滑块值上的倍率 (负数 = 反向运动)",
    "슬라이더 최솟값<0 = 양방향 (중앙이 0)": "滑块最小值<0 = 双向 (中央为0)",
    "슬라이더 추가": "添加滑块",
    "슬라이더 추가: ": "已添加滑块: ",
    "슬라이더는 '값', 패드는 방향 성분을 고르세요": "滑块选「值」，面板选方向分量",
    "슬롯에 연결된 A/I/U/E/O 키의 방향을 읽어 자동 매핑": "读取槽位中A/I/U/E/O键的方向自动映射",
    "시작 프레임": "起始帧",
    "시작 프레임으로 이동해 카운트다운 후 재생과 녹화를 시작합니다. 다시 누르면 취소/정지되고, End Frame에 도달하면 자동으로 멈춥니다": "跳到起始帧，倒计时后开始播放和录制。再按一次取消/停止，到达End Frame自动停止",
    "시퀀서에 넣은 립싱크 사운드 스트립을 제거합니다. 타임라인 스크럽 시 소리가 나지 않게 됩니다": "从序列编辑器移除口型声音片段，拖动时间线时不再播放声音",
    "시퀀서에 오디오를 넣어 재생 시 소리가 같이 나오게 합니다": "将音频加入序列编辑器，播放时同步出声",
    "아래 (Y-)": "下 (Y-)",
    "아래 색상 필드로 직접 선택": "用下方颜色字段直接选择",
    "아래→위": "下→上",
    "아래에서 위로 0~1": "从下到上0~1",
    "아이폰 IP": "iPhone IP",
    "아이폰 IP를 입력하세요 (앱 화면에 표시됨)": "请输入iPhone的IP (应用中显示)",
    "애니메이션 재생 중일 때 매핑된 핸들에 키프레임을 기록합니다 (스페이스바로 재생하며 연기하세요)": "动画播放时向已映射的手柄记录关键帧 (按空格播放并表演)",
    "앵커 스냅 임계값": "锚点吸附阈值",
    "양방향 슬라이더의 음수 방향으로": "送到双向滑块的负方向",
    "어니언 스킨": "洋葱皮",
    "얼굴 메시": "面部网格",
    "역할": "角色",
    "역할별로 컨트롤러만 고르면 ARKit 매핑을 자동으로 만들어 줍니다. 입 모양은 A/I/U/E/O 조합 채널로 연결되고, 컨트롤러 이름으로 미리 추측해서 채워둡니다": "只需按角色选择控制器即可自动创建ARKit映射。口型连接到A/I/U/E/O组合通道，并根据名称预先猜测填充",
    "연결 시작": "开始连接",
    "연결 안 함": "不连接",
    "연결된 키 이름에서 '%s' / '%s' 를 찾지 못했습니다": "连接的键名中找不到'%s' / '%s'",
    "연결할 셰이프 키(또는 대상 본)가 없습니다": "没有可连接的形态键(或目标骨骼)",
    "연결할 셰이프 키가 없습니다": "没有可连接的形态键",
    "연쇄 드라이버": "联动驱动器",
    "연쇄 셰이프 키가 있는 메시 (기본 = 설정의 얼굴 메시)": "联动形态键所在的网格 (默认 = 设置中的面部网格)",
    "연쇄 추가": "添加联动",
    "연필 아이콘 = 타입/키/라벨 수정": "铅笔图标 = 编辑类型/键/标签",
    "영역 선택 모드 (끄면 드래그 = 스크럽)": "范围选择模式 (关闭时拖动 = 预览)",
    "오디오 립싱크 생성": "生成音频口型同步",
    "오디오: 파일 없음": "音频: 无文件",
    "오디오가 너무 짧습니다": "音频太短",
    "오디오를 읽을 수 없습니다: %s": "无法读取音频: %s",
    "오른눈 감기": "右眼眨眼",
    "오른눈 눈동자 패드": "右眼瞳孔面板",
    "오른눈 본": "右眼骨骼",
    "오른눈썹 (위/아래)": "右眉 (上/下)",
    "오른쪽 (X+)": "右 (X+)",
    "오브젝트 모드에서 선택한 텍스트에 적용": "应用到物体模式中选中的文本",
    "오토 키": "自动关键帧",
    "왼눈 감기": "左眼眨眼",
    "왼눈 눈동자 패드": "左眼瞳孔面板",
    "왼눈 본": "左眼骨骼",
    "왼눈썹 (위/아래)": "左眉 (上/下)",
    "왼쪽 (X-)": "左 (X-)",
    "왼쪽→오른쪽": "左→右",
    "왼쪽에서 오른쪽으로 0~1": "从左到右0~1",
    "우": "右",
    "우상 (대각)": "右上 (对角)",
    "우상단 빨간 토글 오른쪽으로 = 패널 숨김": "右上角红色开关拨到右侧 = 隐藏面板",
    "우측 포함식": "右侧标记",
    "우하 (대각)": "右下 (对角)",
    "움직일 본이 들어있는 아마추어": "包含要驱动骨骼的骨架",
    "움직일 본이 들어있는 아마추어 (설정의 리그와 달라도 됨)": "包含要驱动骨骼的骨架 (可与设置中的绑定不同)",
    "원본": "原始",
    "위 (Y+)": "上 (Y+)",
    "위아래 끄덕임(피치)을 보낼 본 로컬 축": "接收上下点头(俯仰)的骨骼本地轴",
    "위치 갱신": "更新位置",
    "음수 = 반대 방향": "负数 = 反方向",
    "음수로 하면 양방향 슬라이더가 됩니다 (중앙=0)": "设为负数则成为双向滑块 (中央=0)",
    "음수로 하면 양방향 슬라이더가 됩니다 (중앙=0). 셰이프 키 자체의 Range Min도 음수여야 합니다": "设为负数则成为双向滑块 (中央=0)。形态键自身的Range Min也需为负",
    "이 ARKit 값이 움직일 컨트롤러": "此ARKit值驱动的控制器",
    "이 구간의 시작 프레임으로 이동합니다": "跳到此区段的起始帧",
    "이 방향 키에만 곱해질 배율 (전체 배율과 곱해짐)": "仅乘到该方向键上的倍率 (与整体倍率相乘)",
    "이 슬라이더 값에 배율을 곱해 함께 움직일 셰이프 키": "按此滑块值×倍率联动的形态键",
    "이 슬라이더 값을 따라 함께 움직일 셰이프 키를 추가합니다": "添加跟随此滑块值联动的形态键",
    "이 슬라이더를 따라 움직일 키를 + 로 추가": "用+添加跟随此滑块的键",
    "이 컨트롤러와 연결된 드라이버를 제거합니다 (셰이프 키는 유지)": "删除此控制器及关联驱动器 (保留形态键)",
    "이 컨트롤러와 연결된 드라이버를 제거합니다 (셰이프 키는 유지). 체크된 항목이 2개 이상이면 체크된 것들을 한꺼번에 삭제합니다": "删除此控制器及关联驱动器 (保留形态键)。勾选2个以上时将一并删除所有勾选项",
    "이동": "移动",
    "이동 방향을 반대로 (가로: 오른쪽→왼쪽, 세로: 위→아래). 원점은 항상 값 0": "反转移动方向 (横向: 右→左、纵向: 上→下)。原点始终为0",
    "이동 방향을 반대로 (원점은 항상 값 0)": "反转移动方向 (原点始终为0)",
    "이동%s: Ctrl=스냅, X/Y/Z=축 고정, 클릭=확정, ESC=취소": "移动%s: Ctrl=吸附、X/Y/Z=锁轴、点击=确定、ESC=取消",
    "이동: Ctrl=모서리 스냅, X/Y/Z=축 고정, 클릭=확정, 우클릭/ESC=취소": "移动: Ctrl=角吸附、X/Y/Z=锁轴、点击=确定、右键/ESC=取消",
    "이동량 적용": "应用移动量",
    "이름 갱신 %d건": "已更新%d个名称",
    "이름 변경: ": "已重命名: ",
    "이름을 입력하세요": "请输入名称",
    "일괄 수정 (체크된 항목)": "批量编辑 (勾选项)",
    "일괄 수정: %d개 적용": "批量编辑: 已应用%d个",
    "일시정지": "暂停",
    "입 (모음)": "嘴 (元音)",
    "입 A (아)": "嘴 A (啊)",
    "입 E (에)": "嘴 E (诶)",
    "입 I (이)": "嘴 I (衣)",
    "입 O (오)": "嘴 O (哦)",
    "입 U (우)": "嘴 U (呜)",
    "입 모음 매핑이 없습니다. iFacialMocap 패널의 '간단 자동 설정'으로 먼저 만들어 주세요": "没有嘴部元音映射。请先用iFacialMocap面板的快速自动设置创建",
    "입 벌림 배율": "张嘴倍率",
    "입 움직임 완화. 높을수록 부드럽지만 둔해집니다": "平滑嘴部动作。越高越柔和但越迟钝",
    "입 패드 (모음 자동 배치)": "嘴部面板 (自动排布元音)",
    "입꼬리 당김에서 계산되는 '이' 채널": "由嘴角拉伸计算的「衣」通道",
    "입모양 A (조합)": "口型 A (组合)",
    "입모양 E (조합)": "口型 E (组合)",
    "입모양 I (조합)": "口型 I (组合)",
    "입모양 O (조합)": "口型 O (组合)",
    "입모양 U (조합)": "口型 U (组合)",
    "자동 매핑": "自动映射",
    "자동 매핑 %d개 (나머지는 +로 수동 추가)": "自动映射%d条 (其余用+手动添加)",
    "자동 매핑(마법봉) 또는 +로 추가하세요": "请用自动映射(魔棒)或+添加",
    "자동 배치된 모음 구간을 확인하고 바꿉니다. 프레임 숫자 클릭 = 그 지점으로 이동, 모음을 고치고 OK를 누르면 키프레임을 다시 굽습니다": "查看并修改自动分配的元音区段。点击帧号跳转，修改元音后按OK重新烘焙",
    "자유 배치 가능한 라벨 텍스트를 만듭니다. 오브젝트 모드에서 G/S로 배치·크기 조절, Tab으로 내용 수정, 폰트는 폰트 속성에서": "创建可自由摆放的标签文本。物体模式中用G/S摆放·缩放、Tab编辑内容、字体在字体属性中设置",
    "잘라내기": "剪切",
    "잘라내기 (길이 단축)": "剪切 (缩短长度)",
    "재계산": "重新计算",
    "재계산 결과가 무음이라 중단했습니다. 진단: len=%d sr=%s fps=%.2f peak=%.4f frames=%d": "重新计算结果为静音，已中止。诊断: len=%d sr=%s fps=%.2f peak=%.4f frames=%d",
    "재생": "播放",
    "저장된 설정으로 모든 컨트롤러를 다시 구성합니다. 위젯/드라이버/토글 연결을 최신 버전 방식으로 재적용합니다": "按已保存设置重建所有控制器。以最新方式重新应用控件/驱动器/开关连接",
    "저장된 표정 프리셋을 컨트롤러에 적용합니다": "将已保存的表情预设应用到控制器",
    "저장된 프리셋이 없습니다": "没有已保存的预设",
    "적용 (다시 굽기)": "应用 (重新烘焙)",
    "적용 중...": "应用中...",
    "전용 립싱크 편집 창을 엽니다. 파형과 모음 구간을 보며 구간을 클릭해 A/I/U/E/O를 바꿀 수 있습니다": "打开专用口型编辑窗口。查看波形和元音区段，点击区段修改A/I/U/E/O",
    "전체 입 벌림 강도": "整体张嘴强度",
    "정지": "停止",
    "조작법": "操作说明",
    "좌": "左",
    "좌/우 포함식을 바꿔 반대쪽 셰이프 키를 찾아, 같은 설정과 색상으로 반대쪽 컨트롤러를 만듭니다 (위치는 패널 중심 기준 미러)": "交换左右标记找到对侧形态键，用相同设置和颜色创建对侧控制器 (位置以面板中心镜像)",
    "좌/우 포함식을 바꿔 반대쪽 셰이프 키를 찾아, 같은 설정과 색상으로 반대쪽 컨트롤러를 만듭니다 (위치는 패널 중심 기준 미러). 체크된 항목이 2개 이상이면 체크된 것들을 한꺼번에 미러합니다": "交换左右标记找到对侧形态键，用相同设置和颜色创建对侧控制器 (位置以面板中心镜像)。勾选2个以上时一并镜像所有勾选项",
    "좌상 (대각)": "左上 (对角)",
    "좌우 갸웃(롤)을 보낼 본 로컬 축": "接收左右歪头(翻滚)的骨骼本地轴",
    "좌우 돌림(요)을 보낼 본 로컬 축": "接收左右转头(偏航)的骨骼本地轴",
    "좌우 반전": "左右反转",
    "좌측 포함식": "左侧标记",
    "좌하 (대각)": "左下 (对角)",
    "중앙 (원점)": "中央 (原点)",
    "중지": "停止",
    "즐겨찾기 수정": "编辑收藏",
    "즐겨찾기 이름:": "收藏名称:",
    "지금의 컨트롤러 위치들을 기본 표정으로 저장합니다. '기본값으로 되돌리기'가 이 상태로 복원합니다": "将当前控制器位置保存为默认表情。「恢复默认值」会还原到此状态",
    "직접 움직일 셰이프 키": "直接驱动的形态键",
    "체크된 컨트롤러가 없습니다": "没有勾选的控制器",
    "체크된 컨트롤러들을 한 번에 수정합니다 (체크된 항목의 연필 버튼으로 열림). 같은 타입끼리만 가능하며, 값이 서로 다른 항목은 '(다수 선택됨)'으로 표시됩니다": "一次编辑所有勾选的控制器 (从勾选项的铅笔按钮打开)。仅限相同类型，值不同的项目显示为「(多个值)」",
    "체크된 컨트롤러들을 한 번에 수정합니다. 같은 타입끼리만 가능하며, 값이 서로 다른 항목은 '(다수 선택됨)'으로 표시됩니다": "一次编辑所有勾选的控制器。仅限相同类型，值不同的项目显示为「(多个值)」",
    "체크하고 OK를 누르면 이 연쇄가 삭제됩니다": "勾选后按OK即删除此联动",
    "체크한 컨트롤러들을 선택한 컬렉션에 넣거나 뺍니다": "将勾选的控制器放入所选集合或从中移除",
    "체크한 컨트롤러를 컬렉션 밖으로": "将勾选的控制器移出集合",
    "최대 음량 대비 이 비율 아래면 입을 다뭅니다": "低于峰值音量的此比例时闭嘴",
    "최댓값": "最大值",
    "최댓값이 최솟값보다 커야 합니다": "最大值必须大于最小值",
    "최솟값": "最小值",
    "추가된 컨트롤러가 없습니다": "尚未添加控制器",
    "축 적용": "应用轴",
    "카운트다운 (초)": "倒计时 (秒)",
    "카운트다운 취소": "已取消倒计时",
    "캘리브레이션 보정을 지우고 원본 수신값을 사용합니다": "清除校准并使用原始接收值",
    "캘리브레이션 완료: 지금 표정이 기준이 됩니다": "校准完成: 当前表情成为基准",
    "캘리브레이션 적용 중": "校准生效中",
    "캘리브레이션 해제": "已清除校准",
    "캡처 중 프리셋 적용": "捕捉中应用预设",
    "커브 %d개: 키 %d개 → %d개 (%d개 제거)": "%d条曲线: %d个键 → %d个 (删除%d个)",
    "컨트롤러": "控制器",
    "컨트롤러 %d개 → '%s'": "%d个控制器 → '%s'",
    "컨트롤러 %d개 삭제": "已删除%d个控制器",
    "컨트롤러 %d개 정렬 완료": "已排序%d个控制器",
    "컨트롤러 %d개를 컬렉션에서 제거": "已将%d个控制器移出集合",
    "컨트롤러 %d개에 키프레임 삽입": "已为%d个控制器插入关键帧",
    "컨트롤러 %d개의 기본값 저장 완료": "已保存%d个控制器的默认值",
    "컨트롤러 %d개의 색상 동기화 완료": "已同步%d个控制器的颜色",
    "컨트롤러 목록": "控制器列表",
    "컨트롤러 삭제": "删除控制器",
    "컨트롤러 선택": "选择控制器",
    "컨트롤러 수정": "编辑控制器",
    "컨트롤러를 고르면 그 색을 그대로 따옵니다": "选择控制器即可获取其颜色",
    "컨트롤러마다 역할(눈 감기/눈썹/입 모음/눈동자)을 고르면 ARKit 매핑을 자동으로 만들어 줍니다. 이름으로 미리 추측해서 채워둡니다": "为每个控制器选择角色(眨眼/眉毛/口型元音/瞳孔)即可自动创建ARKit映射。根据名称预先猜测填充",
    "컨트롤러마다 역할을 고르세요": "请为每个控制器选择角色",
    "컨트롤러의 틀을 선택해서 G/R/S로 자유롭게 배치합니다. 끄면 다시 핸들 조작 모드로 돌아갑니다": "选择控制器外框并用G/R/S自由排布。关闭后回到手柄操作模式",
    "컬렉션 '%s' 생성": "已创建集合'%s'",
    "컬렉션 삭제": "删除集合",
    "컬렉션 이름": "集合名称",
    "컬렉션 이름을 입력하세요": "请输入集合名称",
    "컬렉션 추가": "添加集合",
    "컬렉션에 넣거나 뺄 컨트롤러 체크": "勾选要放入/移出集合的控制器",
    "컬렉션을 없애고 소속 컨트롤러를 컬렉션 밖으로 뺍니다 (컨트롤러는 유지)": "删除集合并将其中的控制器移出 (保留控制器)",
    "켬": "开",
    "크기": "大小",
    "크기: %s · 길이: %s": "大小: %s · 时长: %s",
    "클릭 = 위치 · 드래그 = 구간 선택 · Space = 재생 · 휠 = 줌 · Shift+휠 = 이동": "点击 = 位置 · 拖动 = 选择范围 · Space = 播放 · 滚轮 = 缩放 · Shift+滚轮 = 平移",
    "키프레임: I > Location (또는 자동 키)": "关键帧: I > Location (或自动插帧)",
    "타입": "类型",
    "타입/방향/셰이프 키/라벨을 변경합니다": "更改类型/方向/形态键/标签",
    "타입이 섞여 있습니다. 같은 타입끼리만 일괄 수정할 수 있습니다": "类型混杂。只能批量编辑相同类型",
    "텍스트 %d개 색상 변경": "已更改%d个文本的颜色",
    "텍스트 %d개에 가장 가까운 컨트롤러 색 적용": "已为%d个文本应用最近控制器的颜色",
    "텍스트 색상": "文本颜色",
    "텍스트 색상 자동": "文本颜色自动",
    "텍스트 생성: G/S로 배치, Tab으로 내용 수정": "文本已创建: 用G/S摆放、Tab编辑内容",
    "텍스트 추가": "添加文本",
    "텍스트 추가 = 자유 라벨 (오브젝트 모드에서 편집)": "添加文本 = 自由标签 (在物体模式编辑)",
    "텍스트(라벨)의 색상을 변경합니다. 포즈 모드에서도 대상 텍스트를 골라 적용할 수 있고, 컨트롤러 색을 따올 수 있습니다": "更改文本(标签)颜色。姿态模式下也可选择目标文本应用，并可获取控制器颜色",
    "투명도": "不透明度",
    "파일: ": "文件: ",
    "파일을 읽을 수 없습니다: %s": "无法读取文件: %s",
    "파형 함께 이동": "波形一起移动",
    "패널": "面板",
    "패널 높이 기준이 될 본 (예: c_head.x)": "作为面板高度基准的骨骼 (如 c_head.x)",
    "패널 레이아웃(컨트롤러/텍스트/컬렉션)을 JSON으로 저장합니다": "将面板布局(控制器/文本/集合)保存为JSON",
    "패널 리로드 완료 (컨트롤러 %d개)": "面板重载完成 (%d个控制器)",
    "패널 본은 대상으로 쓸 수 없습니다": "面板骨骼不能作为目标",
    "패널 위치 저장: 컨트롤러가 여기에 생성됩니다": "面板位置已保存: 控制器将在此创建",
    "패널 위치 지정": "指定面板位置",
    "패널 전체 이동: FP_root 본을 G로 이동": "整体移动面板: 用G移动FP_root骨骼",
    "패널 전체 제거": "删除整个面板",
    "패널 위치 (그랩 바)": "面板位置（抓取条）",
    "캐릭터 따라다니기": "跟随角色",
    "패널(그랩 바)과 뷰포트 컨트롤러가 아래 본을 따라다니며 지금의 상대 위치를 계속 유지합니다. 캐릭터가 움직여도 옆에 붙어 있습니다 (켜면 리그의 c_pos·root 본을 자동으로 고름)": "面板（抓取条）和视口控制器跟随下方的骨骼并保持当前相对位置，角色移动时始终贴在旁边（开启时自动选择绑定的 c_pos / root 骨骼）",
    "따라갈 본이 있는 아마추어 (캐릭터 리그)": "包含目标骨骼的骨架（角色绑定）",
    "패널이 따라갈 본 (보통 머리 본)": "面板要跟随的骨骼（通常是头部骨骼）",
    "현재 위치로 고정": "固定在当前位置",
    "지금 보이는 패널 위치를 기준으로 다시 묶습니다. 캐릭터나 패널을 옮긴 뒤 위치가 어긋났을 때 누르세요": "以当前面板位置重新绑定。移动角色或面板后位置偏移时请点击",
    "대상 리그와 본을 먼저 지정하세요": "请先指定目标骨架和骨骼",
    "패널 위치를 고정했습니다": "面板位置已固定",
    "여기서 고른 오디오만 재생됩니다 (나머지 사운드는 자동 음소거). 립싱크 분석용 오디오와 따로 조절됩니다": "仅播放此处选择的音频（其余声音会自动静音）。与口型同步分析音频分开控制",
    "재생 오디오 (스페이스바)": "播放音频（空格键）",
    "재생 오디오": "播放音频",
    "재생 오디오 추가": "添加播放音频",
    "재생 오디오 제거": "移除播放音频",
    "재생 오디오 추가: %s": "已添加播放音频：%s",
    "재생 오디오 제거: %s": "已移除播放音频：%s",
    "(선택 안 함)": "（未选择）",
    " (립싱크)": "（口型同步）",
    "시퀀서 사운드 스트립": "序列器音频条",
    "스피커 오브젝트": "扬声器物体",
    "블렌더에서 재생할 때 들리는 오디오를 고릅니다. 립싱크 분석용 오디오와 따로 조절됩니다": "选择在 Blender 播放时听到的音频。与口型同步分析用音频分开控制",
    "재생 오디오의 볼륨": "播放音频的音量",
    "재생 오디오만 잠시 끕니다 (립싱크 편집기 소리는 유지)": "仅静音播放音频（口型编辑器的声音保持不变）",
    "사운드 스트립이 시작할 프레임": "音频条开始的帧",
    "스페이스바로 재생할 때 들리는 오디오를 시퀀서에 추가합니다. 립싱크 분석용 오디오와는 별개라 여기서 볼륨/음소거/시작 프레임만 따로 조절할 수 있습니다": "将播放时听到的音频添加到序列器。它与口型同步分析音频相互独立，可在此单独调整音量、静音和起始帧",
    "립싱크 사운드 음소거": "静音口型同步音频",
    "립싱크용 사운드가 함께 울려 이중으로 들리는 것을 막습니다": "防止口型同步音频同时播放而产生重音",
    "선택한 재생 오디오를 제거합니다 (시퀀서 스트립만 해당). 립싱크 데이터는 그대로 남습니다": "移除所选的播放音频（仅限序列器音频条）。口型同步数据保持不变",
    "영역으로 생성": "从选区创建",
    "드래그로 선택한 범위를 클러스터로 만듭니다": "将拖动选中的范围创建为语音簇",
    "쪼개기": "拆分",
    "재생 헤드(빨간 세로선) 위치에서 클러스터를 둘로 나눕니다": "在播放头（红色竖线）位置将语音簇一分为二",
    "선택 삭제": "删除所选",
    "선택한 클러스터 하나만 삭제": "仅删除选中的语音簇",
    "먼저 파형에서 범위를 드래그해 선택하세요": "请先在波形上拖动选择范围",
    "재생 헤드가 클러스터 안에 있어야 합니다": "播放头必须位于语音簇内",
    "먼저 클러스터를 클릭해 선택하세요": "请先点击选择一个语音簇",
    "클러스터를 클릭하면 이름을 지정할 수 있습니다": "点击语音簇即可为其标记命名",
    "시작 이름": "起始名称",
    "끝 이름": "结束名称",
    "마커 이름. 한쪽만 적으면 반대쪽도 같은 이름이 됩니다. 비우면 기본 이름(LS_01A/B)": "标记名称。只填一侧时另一侧使用相同名称。留空则使用默认名称（LS_01A/B）",
    "간격": "间隔",
    "클러스터 (프레임 단위)": "语音簇（帧）",
    "클러스터 제거": "清除语音簇",
    "클러스터 간격": "语音簇间隔",
    "클러스터 생성": "检测语音簇",
    "말소리 덩어리를 자동으로 찾아 표시합니다. 양 끝을 드래그해 조절하고, 위쪽 띠를 클릭해 선택 후 Del로 삭제할 수 있습니다. '적용'을 누르면 블렌더 타임라인에 마커로 만들어집니다": "自动检测并显示语音簇。拖动两端可调整，点击顶部条带选中后按 Del 删除。点击“应用”即可在 Blender 时间轴生成标记",
    "클러스터 간격 (프레임): 이만큼 이하로 떨어진 소리는 한 덩어리로 봅니다": "语音簇间隔（帧）：间隔小于此值的声音视为同一簇",
    "클러스터 모두 지우기": "清除所有语音簇",
    "프레임 레이트가 %.4g → %.4g로 바뀌어 립싱크를 재배치했습니다": "帧率从 %.4g 变为 %.4g，已重新对齐口型同步",
    "프레임 레이트 변경 감지: 립싱크를 새 프레임 레이트에 맞춰 재배치했습니다": "检测到帧率更改：口型同步已按新帧率重新对齐",
    "선택한 리그 자동 전환": "自动切换到所选骨架",
    "뷰포트에서 패널이 있는 다른 리그를 선택하면 이 패널 설정(컨트롤러 목록/프리셋/모캡/립싱크)을 그 캐릭터의 것으로 자동 전환합니다": "在视口中选择另一个带面板的骨架时，面板设置（控制器/预设/动捕/口型同步）会自动切换到该角色",
    "캐릭터 이동 준비": "准备角色迁移",
    "캐릭터 가져오기": "导入角色",
    "가져온 리그": "追加的骨架",
    "씬 설정만 복구": "仅恢复场景设置",
    "씬 설정(컬렉션/프리셋/모캡/립싱크/라벨)을 리그에 저장합니다. 다른 파일에서 리그와 메시를 Append 한 뒤 '캐릭터 가져오기'로 복구하세요. 파일 저장 시 자동 갱신됩니다": "将场景设置（集合/预设/动捕/口型同步/标签）保存到骨架上。在其他文件中追加骨架和网格后运行“导入角色”恢复。保存文件时自动更新",
    "Append 한 리그에서 캐릭터 설정을 복구합니다. 컨트롤러는 새로 만들지 않고 기존 본의 설정을 그대로 사용합니다": "从追加的骨架恢复角色设置。重用现有控制器骨骼，不会重复创建",
    "패널 리로드와 라벨 재생성 없이 컬렉션/프리셋/모캡/립싱크 설정만 복구합니다": "仅恢复集合/预设/动捕/口型同步设置，不重载面板、不重建标签",
    "캐릭터 설정을 리그에 저장했습니다 (라벨 %d개 포함)": "角色设置已保存到骨架（含 %d 个标签）",
    "이 리그에는 캐릭터 스냅샷이 없습니다. 원본 파일에서 '캐릭터 이동 준비'를 먼저 실행하세요": "此骨架没有角色快照。请先在源文件中运行“准备角色迁移”",
    "캐릭터 가져오기 완료 (라벨 %d개 재생성)": "角色导入完成（重建 %d 个标签）",
    "패널을 옮겼습니다": "已移动面板",
    "패드 슬롯 표시 순번": "面板槽位显示序号",
    "패드 슬롯 표시 순번. 숫자를 고치면 그 위치로 끼어듭니다": "面板槽位显示序号。修改数字即插入到该位置",
    "패드 아래로": "面板向下",
    "패드 오른쪽으로": "面板向右",
    "패드 왼쪽으로": "面板向左",
    "패드 위로": "面板向上",
    "패드 추가: ": "已添加面板: ",
    "패드: 같은 키를 상+하에 넣으면 -1~1 범위": "面板: 同一键放入上+下则为-1~1范围",
    "패드에 연결된 셰이프 키와 값 표시": "显示面板连接的形态键和值",
    "패드의 모든 값에 곱해질 배율 (예: 0.5 = 절반 강도, 음수 = 반대 방향)": "乘到面板所有值上的倍率 (如 0.5 = 一半强度、负数 = 反方向)",
    "편집기가 종료되었습니다. 탭을 닫아 주세요.": "编辑器已关闭。请关闭此标签页。",
    "편집한 모음 구간대로 립싱크 키프레임을 다시 굽습니다": "按编辑后的元音区段重新烘焙口型关键帧",
    "펼치기": "展开",
    "포즈 모드에서 컨트롤러 선택 후 G로 이동": "姿态模式中选中控制器后用G移动",
    "포트 49983 열기 실패: %s": "无法打开端口49983: %s",
    "표정": "表情",
    "표정 전체 키프레임": "为整个表情插入关键帧",
    "표정 패널 제거 완료": "表情面板已删除",
    "표정 프리셋": "表情预设",
    "표정 프리셋의 이름을 바꿉니다": "重命名表情预设",
    "프레임 구간의 드라이버 값을 셰이프 키 키프레임으로 굽고 드라이버를 제거합니다. FBX/VRM 익스포트 전에 사용하세요. 패널 복구는 '뷰포트 패널 리로드'": "将帧区间的驱动器值烘焙为形态键关键帧并删除驱动器。请在导出FBX/VRM前使用。用「重载视口面板」恢复",
    "프레임 범위": "帧范围",
    "프레임 클릭 = 이동": "点击帧 = 跳转",
    "프레임 클릭 = 이동 · OK = 다시 굽기": "点击帧 = 跳转 · OK = 重新烘焙",
    "프리셋 %d번이 없습니다": "预设%d号不存在",
    "프리셋 '%s' 저장 (컨트롤러 %d개)": "已保存预设'%s' (%d个控制器)",
    "프리셋 데이터가 손상되었습니다": "预设数据已损坏",
    "프리셋 블렌딩 (초)": "预设混合 (秒)",
    "프리셋 삭제": "删除预设",
    "프리셋 이름": "预设名称",
    "프리셋 이름 변경": "重命名预设",
    "프리셋 이름을 입력하세요": "请输入预设名称",
    "프리셋 저장": "保存预设",
    "프리셋 적용": "应用预设",
    "프리셋 적용: ": "已应用预设: ",
    "프리셋 전환에 걸리는 시간. 0이면 즉시 전환": "预设切换所需时间。0为立即切换",
    "한국어": "한국어",
    "함께 움직일 두 번째 본": "一起移动的第二根骨骼",
    "함께 움직일 두 번째 본 (양눈 동시 제어용, 비우면 1개만)": "一起移动的第二根骨骼 (用于双眼同时控制，留空则只用1根)",
    "항상 위": "总在最前",
    "해제": "停用",
    "핸들 XY로 본(눈알 타겟 등)의 위치를 움직임": "用手柄XY移动骨骼(眼球目标等)的位置",
    "핸들 상하 이동을 대상 본의 어느 로컬 축으로 보낼지": "手柄上下移动送到目标骨骼的哪个本地轴",
    "핸들 좌우 이동을 대상 본의 어느 로컬 축으로 보낼지. 본을 G로 움직여 눈이 좌우로 도는 축을 고르세요": "手柄左右移动送到目标骨骼的哪个本地轴。用G移动骨骼，选择让眼睛左右转动的轴",
    "핸들을 따라 움직일 본": "跟随手柄移动的骨骼",
    "핸들을 따라 움직일 본 (예: c_eye_target.l)": "跟随手柄移动的骨骼 (如 c_eye_target.l)",
    "핸들을 오른쪽 끝까지 밀었을 때 본이 이동하는 거리. 음수 = 반대 방향": "手柄推到最右端时骨骼移动的距离。负数 = 反方向",
    "핸들을 위 끝까지 밀었을 때 본이 이동하는 거리. 음수 = 반대 방향": "手柄推到最上端时骨骼移动的距离。负数 = 反方向",
    "핸들의 XY 이동으로 리그의 본(눈알 타겟 등)을 움직이는 2D 패드를 추가합니다. 본을 2개 넣으면 동시에 움직입니다 (양눈). 눈마다 따로 만들려면 본 1개씩 + 미러를 쓰세요": "添加用手柄XY移动绑定骨骼(眼球目标等)的2D面板。放入2根骨骼则同时移动 (双眼)。每只眼单独制作时用1根骨骼+镜像",
    "핸들이 앵커 반경 안이면 위치와 값이 고정 (0 = 끄기)": "手柄在锚点半径内时位置和值被固定 (0 = 关闭)",
    "핸들이 앵커(모서리/변 중앙/중앙) 반경 안이면 위치와 값이 앵커에 고정됩니다. 이동 범위 대비 비율 (0=끄기)": "手柄在锚点(角/边中央/中央)半径内时位置和值固定到锚点。相对移动范围的比例 (0=关闭)",
    "핸들이 앵커(시작/중간/끝) 반경 안이면 위치와 값이 고정 (0 = 스냅 끄기)": "手柄在锚点(起/中/末)半径内时位置和值被固定 (0 = 关闭吸附)",
    "허용 오차": "容差",
    "현재 값을 기본값으로 저장": "将当前值保存为默认",
    "현재 뷰포트 컨트롤러의 실제 본 색상을 읽어 목록 스와치와 메타데이터에 동기화합니다 (애드온 재설치 후 색이 어긋날 때)": "读取当前视口控制器的实际骨骼颜色并同步到列表色板和元数据 (重装插件后颜色错位时)",
    "현재 컨트롤러 값들을 표정 프리셋으로 저장합니다": "将当前控制器值保存为表情预设",
    "현재 프레임에 모든 컨트롤러의 키프레임을 삽입합니다": "在当前帧为所有控制器插入关键帧",
    "형식: ": "格式: ",
    "화살표 = 목록 순서 이동, 그룹은 수정 팝업에서": "箭头 = 移动列表顺序，分组在编辑弹窗中",
    "확인": "确定",
    "확정: 클릭 · 취소: 우클릭/ESC": "确定: 点击 · 取消: 右键/ESC",
    "조작 중: 확정 = 클릭 · 취소 = 우클릭/ESC":
        "操作中: 确定 = 点击 · 取消 = 右键/ESC",
    "배치 모드 끄기: ESC 또는 우클릭 (조작 중이 아닐 때)":
        "退出布局模式: ESC 或右键 (未在操作时)",
    "회전 배율": "旋转倍率",
    "히스토리": "历史",
}


_L10N = {'JA': _JA, 'ZH': _ZH}


def _lang_get():
    try:
        pkg = __package__ or "face_shapekey_rig"
        ad = bpy.context.preferences.addons.get(pkg)
        if ad and ad.preferences:
            return str(ad.preferences.lang)
    except Exception:
        pass
    return 'KO'


def _tr(s):
    """현재 언어에 맞는 문자열 (소스는 한국어, 사전 치환 + 영어 폴백)."""
    lg = _lang_get()
    if lg == 'KO':
        return s
    if lg == 'EN':
        return _EN.get(s, s)
    d = _L10N.get(lg)
    if d is not None:
        v = d.get(s)
        if v is not None:
            return v
    return _EN.get(s, s)


def _retranslate():
    """언어 전환: 클래스 라벨/설명/프로퍼티 문구를 바꾸고 재등록."""
    classes2 = _LANG_STATE.get("classes") or ()
    orig_all = _LANG_STATE["orig"]
    for cls in classes2:
        if cls.__name__ == "FSKR_Prefs":
            continue
        orig = orig_all.setdefault(cls.__name__, {})
        for attr in ("bl_label", "bl_description"):
            v = getattr(cls, attr, None)
            if isinstance(v, str):
                orig.setdefault(attr, v)
                setattr(cls, attr, _tr(orig[attr]))
        for pn, pd in getattr(cls, "__annotations__", {}).items():
            kw = getattr(pd, "keywords", None)
            if not isinstance(kw, dict):
                continue
            st = orig.setdefault("p_" + pn, {})
            for k in ("name", "description", "default"):
                v = kw.get(k)
                if isinstance(v, str):
                    st.setdefault(k, v)
                    kw[k] = _tr(st[k])
            it = kw.get("items")
            if (isinstance(it, (tuple, list)) and it
                    and isinstance(it[0], (tuple, list))):
                st.setdefault("items", tuple(tuple(i) for i in it))
                kw["items"] = tuple(
                    tuple([i[0], _tr(i[1]), _tr(i[2])] + list(i[3:]))
                    for i in st["items"])
    for cls in reversed(classes2):
        if cls.__name__ == "FSKR_Prefs":
            continue
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
    for cls in classes2:
        if cls.__name__ == "FSKR_Prefs":
            continue
        try:
            bpy.utils.register_class(cls)
        except Exception:
            pass
    try:
        bpy.types.Scene.fskr = bpy.props.PointerProperty(type=FSKR_Settings)
    except Exception:
        pass
    for fn in list(globals().get("_LANG_HOOKS", ())):
        try:
            fn()
        except Exception as e:
            print("FSKR lang hook:", e)
    try:
        for win in bpy.context.window_manager.windows:
            for area in win.screen.areas:
                area.tag_redraw()
    except Exception:
        pass
    return None


_LANG_HOOKS = []   # 언어가 바뀐 뒤 부를 함수 (뷰포트 라벨 등)


def _lang_update(self, context):
    try:
        bpy.app.timers.register(_retranslate, first_interval=0.01)
    except Exception:
        _retranslate()


def _addon_prefs(context):
    pkg = __package__ or "face_shapekey_rig"
    ad = context.preferences.addons.get(pkg)
    return ad.preferences if ad else None


class FSKR_Prefs(bpy.types.AddonPreferences):
    bl_idname = __package__ or "face_shapekey_rig"

    lang: bpy.props.EnumProperty(
        name="Language / \uc5b8\uc5b4",
        items=(('KO', "\ud55c\uad6d\uc5b4", ""), ('EN', "English", ""),
               ('JA', "\u65e5\u672c\u8a9e", ""),
               ('ZH', "\u4e2d\u6587", "")),
        default='KO', update=_lang_update)

    def draw(self, context):
        self.layout.prop(self, "lang")


def _pad_eval(x, y, p, r, slot, eu, ed, el, er, cul, cur, cdl, cdr):
    """8방향 2D 패드 가중치 계산 (드라이버 네임스페이스 함수).

    slot: U/D/L/R(변), UR/UL/DR/DL(대각), X/Y(같은 키 좌우/상하 풀레인지)
    eu..er / cul..cdr: 각 슬롯에 키가 연결되어 있는지 (재분배 판단용)
    r: 앵커 스냅 반경 (핸들 이동 단위). 반경 안이면 위치가 앵커에 고정됨.
    """
    if r > 0.0:
        best = None
        bd = r
        for ax2 in (-p, 0.0, p):
            for ay2 in (-p, 0.0, p):
                d = ((x - ax2) ** 2 + (y - ay2) ** 2) ** 0.5
                if d < bd:
                    bd = d
                    best = (ax2, ay2)
        if best is not None:
            x, y = best

    u = x / p
    v = y / p
    if slot == 'X':
        return u
    if slot == 'Y':
        return v

    ar = max(0.0, u)
    al = max(0.0, -u)
    bu = max(0.0, v)
    bn = max(0.0, -v)
    au = abs(u)
    av = abs(v)
    # 기본 가중치 (쌍선형: 앵커 지점에서 정확히 1, 중앙 0)
    w = {'R': ar * (1 - av), 'L': al * (1 - av),
         'U': bu * (1 - au), 'D': bn * (1 - au),
         'UR': ar * bu, 'UL': al * bu, 'DR': ar * bn, 'DL': al * bn}
    ex = {'U': eu, 'D': ed, 'L': el, 'R': er,
          'UL': cul, 'UR': cur, 'DL': cdl, 'DR': cdr}
    out = dict(w)
    # 빈 대각 슬롯의 가중치 → 인접한 변으로
    for c, (h, e2) in (('UR', ('R', 'U')), ('UL', ('L', 'U')),
                       ('DR', ('R', 'D')), ('DL', ('L', 'D'))):
        if not ex[c] and w[c] > 0.0:
            if ex[h]:
                out[h] += w[c]
            if ex[e2]:
                out[e2] += w[c]
            out[c] = 0.0
    # 빈 변 슬롯의 가중치 → 인접한 대각 두 곳으로 (위치 비율대로)
    if not ex['R'] and w['R'] > 0.0:
        s = (v + 1) / 2
        if ex['UR']:
            out['UR'] += w['R'] * s
        if ex['DR']:
            out['DR'] += w['R'] * (1 - s)
        out['R'] = 0.0
    if not ex['L'] and w['L'] > 0.0:
        s = (v + 1) / 2
        if ex['UL']:
            out['UL'] += w['L'] * s
        if ex['DL']:
            out['DL'] += w['L'] * (1 - s)
        out['L'] = 0.0
    if not ex['U'] and w['U'] > 0.0:
        s = (u + 1) / 2
        if ex['UR']:
            out['UR'] += w['U'] * s
        if ex['UL']:
            out['UL'] += w['U'] * (1 - s)
        out['U'] = 0.0
    if not ex['D'] and w['D'] > 0.0:
        s = (u + 1) / 2
        if ex['DR']:
            out['DR'] += w['D'] * s
        if ex['DL']:
            out['DL'] += w['D'] * (1 - s)
        out['D'] = 0.0
    return out.get(slot, 0.0)


def _pad_ofs(x, y, p, r, i):
    """스냅 중일 때 핸들 X 표시를 앵커에 고정하기 위한 표시 오프셋."""
    if r <= 0.0:
        return 0.0
    best = None
    bd = r
    for ax2 in (-p, 0.0, p):
        for ay2 in (-p, 0.0, p):
            d = ((x - ax2) ** 2 + (y - ay2) ** 2) ** 0.5
            if d < bd:
                bd = d
                best = (ax2, ay2)
    if best is None:
        return 0.0
    return (best[0] - x) if i == 0 else (best[1] - y)


def _zero_snap(v):
    """부동소수점 오차로 생기는 -0.00 표시 방지 (±0.0001 이내는 정확히 0)."""
    return 0.0 if -1e-4 < v < 1e-4 else v


def _sld_snap(v, r, a, b, c):
    """1D 슬라이더 앵커 스냅: 세 앵커 중 반경 안의 가장 가까운 곳으로."""
    if r <= 0.0:
        return v
    best = v
    bd = r
    for t in (a, b, c):
        d = abs(v - t)
        if d < bd:
            bd = d
            best = t
    return best


_enum_cache = []


_ITEM_CACHES = {}


def _stable_items(key, items):
    """Enum 콜백용: 내용이 같으면 기존 리스트 객체를 재사용 (참조 유지).

    여러 프로퍼티가 같은 콜백을 공유하면 다시 그릴 때마다 목록이 새로
    만들어져 문자열이 해제되고 드롭다운이 잘리는 문제가 생긴다.
    """
    old = _ITEM_CACHES.get(key)
    if old == items:
        return old
    _ITEM_CACHES[key] = items
    return items


def _mesh_poll(self, obj):
    return obj.type == 'MESH' and obj.data.shape_keys is not None


def _rig_poll(self, obj):
    return obj.type == 'ARMATURE'


def _is_handle_name(n):
    """실제 조작용 핸들 본인지 (프레임/스냅표시/임계값표시/중간 본 제외)."""
    return (n.startswith("FP_ctl") and not n.endswith("_frame")
            and not n.endswith("_snap") and not n.endswith("_thr")
            and not n.endswith("_out"))


def arrange_for(s, name):
    """이 본(컨트롤러)이 지금 배치 모드인지. 탭에서 켠 배치 모드는 그 탭의
    컨트롤러만 (arrange_scope = 본 이름 앞부분, 빈 값 = 전부)."""
    # 1.0.178: 탭별 범위는 없앰 — 배치 모드면 모든 컨트롤러
    return bool(s is not None and getattr(s, "arrange", False))


def _fskr_apply_locks(rig, arrange):
    """패널 본 트랜스폼 잠금: 전체 선택 후 Alt+G/R/S로 배치가 깨지는
    것을 방지. 핸들은 이동(값)만 허용, 틀은 배치 모드에서만 해제.
    애드온 자체 기능은 파이썬으로 값을 쓰므로 잠금의 영향을 받지 않음.
    """
    try:
        s9 = bpy.context.scene.fskr
    except Exception:
        s9 = None

    def arr_of(n):
        if s9 is None:
            return bool(arrange)
        return arrange_for(s9, n)
    try:
        for pb in rig.pose.bones:
            n9 = pb.name
            if not n9.startswith("FP_"):
                continue
            arrange = arr_of(n9)
            if _is_handle_name(n9):
                pb.lock_rotation_w = True
                pb.lock_rotation = (True, True, True)
                pb.lock_scale = (True, True, True)
                continue
            if n9 == "FP_root":
                # 그랩 바: 이동은 항상 허용, 회전/크기는 배치 모드에서
                pb.lock_location = (False, False, False)
                lk9r = not arrange
                pb.lock_rotation_w = lk9r
                pb.lock_rotation = (lk9r, lk9r, lk9r)
                pb.lock_scale = (lk9r, lk9r, lk9r)
                continue
            struct9 = n9.endswith(("_frame", "_snap",
                                   "_thr", "_out"))
            if not struct9:
                # 기능 본(토글 등): 위치가 곧 기능이므로 이동 항상 허용
                pb.lock_location = (False, False, False)
                pb.lock_rotation_w = True
                pb.lock_rotation = (True, True, True)
                pb.lock_scale = (True, True, True)
                continue
            # 구조물(틀/루트/표시 헬퍼): 배치 모드에서만 이동 가능
            lk9 = not arrange
            if n9.startswith(_VP_PREFIX) and pb.parent is not None and \
                    pb.parent.name != "FP_root":
                lk9 = True   # 스프라이트 컨트롤러 안쪽 틀: 부모와 같이만
            pb.lock_location = (lk9, lk9, lk9)
            pb.lock_rotation_w = lk9
            pb.lock_rotation = (lk9, lk9, lk9)
            lks = lk9 or (n9.startswith(_VP_PREFIX)
                          and not _vp_resizable(rig, n9))
            pb.lock_scale = (lks, lks, lks)
    except Exception:
        pass


def _arrange_update(self, context):
    """배치 모드: ON이면 프레임(틀)을 선택/이동 가능, 핸들은 잠금. OFF면 반대."""
    rig = self.rig
    if not rig:
        return
    for b in rig.data.bones:
        arr9 = arrange_for(self, b.name)
        if b.name.startswith(_VP_PREFIX):  # 스프라이트 컨트롤러
            if b.name.endswith("_sel") or b.hide:
                b.hide_select = True  # 선택 칸 표시 전용 / 숨은 본
            else:
                b.hide_select = (not arr9
                                 if b.name.endswith("_frame")
                                 else arr9)
            continue
        if not b.name.startswith("FP_ctl"):
            continue
        if (b.name.endswith("_snap") or b.name.endswith("_thr")
                or b.name.endswith("_out")):
            continue  # 표시/내부 전용, 항상 선택 불가
        if b.name.endswith("_frame"):
            b.hide_select = not arr9
        else:
            b.hide_select = arr9
    _fskr_apply_locks(rig, bool(self.arrange))


def _labels_update(self, context):
    for ob in bpy.data.objects:
        if ob.name.startswith("FPLBL"):
            ob.hide_viewport = not self.labels_visible


class FSKR_CollectionItem(bpy.types.PropertyGroup):
    expand: bpy.props.BoolProperty(default=True)  # 목록에서 펼침/접힘


class FSKR_PresetItem(bpy.types.PropertyGroup):
    data: bpy.props.StringProperty(default="{}")  # {라벨: [x, y]} JSON


_enum_cache_mesh = []


def _mesh_items(self, context):
    """셰이프 키가 있는 메시 목록 (기본 = 설정의 얼굴 메시)."""
    global _enum_cache_mesh
    items = [("__DEF__", _tr("(설정의 얼굴 메시)"),
              _tr("N패널 설정에서 지정한 메시의 셰이프 키 사용"))]
    for ob in bpy.data.objects:
        if ob.type == 'MESH' and ob.data.shape_keys:
            items.append((ob.name, ob.name, ""))
    return _stable_items("mesh", items)


def _op_mesh(self, context):
    """오퍼레이터에서 선택된 메시 (기본이면 설정의 얼굴 메시)."""
    s = context.scene.fskr
    nm = str(getattr(self, "mesh", "__DEF__"))
    if nm and nm != "__DEF__":
        ob = bpy.data.objects.get(nm)
        if ob and ob.type == 'MESH' and ob.data.shape_keys:
            return ob
    return s.mesh


def _shape_key_items(self, context):
    global _enum_cache
    items = [(NONE, _tr("(없음)"), _tr("연결 안 함"))]
    mesh = _op_mesh(self, context)
    if mesh and mesh.data.shape_keys:
        keys = mesh.data.shape_keys
        for kb in keys.key_blocks:
            if kb != keys.reference_key:
                items.append((kb.name, kb.name, ""))
    return _stable_items("keys:%s" % (mesh.name if mesh else ""), items)


AXIS_ITEMS = (('X', "X", ""), ('Y', "Y", ""), ('Z', "Z", ""))


_ARKIT = (
    "browDownLeft", "browDownRight", "browInnerUp",
    "browOuterUpLeft", "browOuterUpRight",
    "cheekPuff", "cheekSquintLeft", "cheekSquintRight",
    "eyeBlinkLeft", "eyeBlinkRight",
    "eyeLookDownLeft", "eyeLookDownRight",
    "eyeLookInLeft", "eyeLookInRight",
    "eyeLookOutLeft", "eyeLookOutRight",
    "eyeLookUpLeft", "eyeLookUpRight",
    "eyeSquintLeft", "eyeSquintRight",
    "eyeWideLeft", "eyeWideRight",
    "jawForward", "jawLeft", "jawOpen", "jawRight",
    "mouthClose", "mouthDimpleLeft", "mouthDimpleRight",
    "mouthFrownLeft", "mouthFrownRight", "mouthFunnel",
    "mouthLeft", "mouthLowerDownLeft", "mouthLowerDownRight",
    "mouthPressLeft", "mouthPressRight", "mouthPucker", "mouthRight",
    "mouthRollLower", "mouthRollUpper",
    "mouthShrugLower", "mouthShrugUpper",
    "mouthSmileLeft", "mouthSmileRight",
    "mouthStretchLeft", "mouthStretchRight",
    "mouthUpperUpLeft", "mouthUpperUpRight",
    "noseSneerLeft", "noseSneerRight", "tongueOut")


ARKIT_ITEMS = tuple((n, n, "") for n in _ARKIT) + (
    ('_A', "입모양 A (조합)", "jawOpen 등에서 자동 계산되는 '아' 채널"),
    ('_I', "입모양 I (조합)", "입꼬리 당김에서 계산되는 '이' 채널"),
    ('_U', "입모양 U (조합)", "mouthPucker에서 계산되는 '우' 채널"),
    ('_E', "입모양 E (조합)", "'에' 채널 (조합)"),
    ('_O', "입모양 O (조합)", "mouthFunnel에서 계산되는 '오' 채널"))


def _ak_norm(n):
    return re.sub(r"[^a-z]", "", n.lower())


_AK_ALIAS = {}


for _n in _ARKIT:
    _AK_ALIAS[_ak_norm(_n)] = _n
    for _suf, _rep in (("Left", "_L"), ("Right", "_R")):
        if _n.endswith(_suf):
            _AK_ALIAS[_ak_norm(_n[:-len(_suf)] + _rep)] = _n


MCOMP_ITEMS = (('VAL', "값", "슬라이더 값 (반전/양방향 자동 반영)"),
               ('VALN', "값 −", "양방향 슬라이더의 음수 방향으로"),
               ('XP', "X+", "패드 오른쪽으로"), ('XN', "X−", "패드 왼쪽으로"),
               ('YP', "Y+", "패드 위로"), ('YN', "Y−", "패드 아래로"))


_enum_cache_mc = []


def _mocap_ctl_items(self, context):
    """매핑 대상 컨트롤러 목록."""
    global _enum_cache_mc
    s = context.scene.fskr
    items = []
    if s.rig:
        for n in _sorted_ctls(s.rig):
            pb = s.rig.pose.bones[n]
            items.append((n, str(pb.get("fskr_label", n)), ""))
    if not items:
        items = [(NONE, _tr("(컨트롤러 없음)"), "")]
    return _stable_items("mctl", items)


VOWEL5_ITEMS = (('_A', "A", ""), ('_I', "I", ""), ('_U', "U", ""),
                ('_E', "E", ""), ('_O', "O", ""),
                ('_N', "-", "미지정 (입 다묾)"))


class FSKR_LipSegItem(bpy.types.PropertyGroup):
    """립싱크 모음 구간 (편집용)."""
    fs: bpy.props.IntProperty()  # 시작 프레임
    fe: bpy.props.IntProperty()  # 끝 프레임
    vowel: bpy.props.EnumProperty(name="모음", items=VOWEL5_ITEMS)
    px: bpy.props.FloatProperty(default=999.0)  # 패드 X (-1~1, 999=미지정)
    py: bpy.props.FloatProperty(default=999.0)  # 패드 Y


class FSKR_MocapMapItem(bpy.types.PropertyGroup):
    arkit: bpy.props.EnumProperty(name="ARKit", items=ARKIT_ITEMS)
    tgt: bpy.props.EnumProperty(
        name="대상", default='CTL',
        items=(('CTL', "패널", "뷰포트 패널 컨트롤러를 움직임 "
                              "(키프레임은 핸들에 기록)"),
               ('KEY', "셰이프 키", "셰이프 키 값을 직접 움직임 "
                                   "(패널 컨트롤러 불필요)")))
    ctl: bpy.props.EnumProperty(
        name="컨트롤러", items=_mocap_ctl_items,
        description="이 ARKit 값이 움직일 컨트롤러")
    comp: bpy.props.EnumProperty(
        name="성분", items=MCOMP_ITEMS, default='VAL',
        description="슬라이더는 '값', 패드는 방향 성분을 고르세요")
    mesh: bpy.props.EnumProperty(
        name="메시", items=_mesh_items,
        description="셰이프 키 대상일 때: 키가 있는 메시")
    key: bpy.props.EnumProperty(
        name="셰이프 키", items=_shape_key_items,
        description="직접 움직일 셰이프 키")
    factor: bpy.props.FloatProperty(
        name="배율", default=1.0, soft_min=-2.0, soft_max=2.0,
        precision=2)


def _pb_strips(scene):
    """시퀀서의 사운드 스트립 목록 (버전별 API 흡수)."""
    se9 = getattr(scene, "sequence_editor", None)
    coll9 = ((getattr(se9, "sequences", None)
              or getattr(se9, "strips", None)) if se9 else None)
    return [st9 for st9 in (coll9 or [])
            if getattr(st9, "type", "") == 'SOUND']


def _pb_items(self, context):
    """재생 오디오 후보: 시퀀서 사운드 스트립 + 스피커 오브젝트."""
    items = [(NONE, _tr("(선택 안 함)"), "")]
    try:
        for st9 in _pb_strips(context.scene):
            tag9 = (_tr(" (립싱크)")
                    if st9.name.startswith("FSKR_lipsync") else "")
            items.append(("SEQ:" + st9.name, st9.name + tag9,
                          _tr("시퀀서 사운드 스트립")))
    except Exception:
        pass
    try:
        for ob9 in bpy.data.objects:
            if ob9.type == 'SPEAKER':
                items.append(("SPK:" + ob9.name, ob9.name,
                              _tr("스피커 오브젝트")))
    except Exception:
        pass
    return _stable_items("pbaud", items)


def _pb_target(s, scene):
    """선택된 재생 오디오 대상 반환. (종류, 객체) 또는 (None, None)."""
    key9 = str(getattr(s, "playback_target", NONE) or NONE)
    if key9 == NONE or ":" not in key9:
        return None, None
    kind9, nm9 = key9.split(":", 1)
    if kind9 == "SEQ":
        for st9 in _pb_strips(scene):
            if st9.name == nm9:
                return "SEQ", st9
    elif kind9 == "SPK":
        ob9 = bpy.data.objects.get(nm9)
        if ob9 is not None and ob9.type == 'SPEAKER':
            return "SPK", ob9
    return None, None


def _pb_pull(s, scene):
    """대상의 현재 값을 패널 필드로 읽어옴 (대상 변경 시)."""
    kind9, t9 = _pb_target(s, scene)
    if t9 is None:
        return
    s["_pb_sync"] = 1  # 되쓰기 방지
    try:
        if kind9 == "SEQ":
            s.playback_vol = float(getattr(t9, "volume", 1.0))
            s.playback_mute = bool(getattr(t9, "mute", False))
            s.playback_start = int(getattr(t9, "frame_start", 1))
        else:
            sp9 = t9.data
            s.playback_vol = float(getattr(sp9, "volume", 1.0))
            s.playback_mute = bool(getattr(sp9, "muted", False))
    except Exception:
        pass
    finally:
        s["_pb_sync"] = 0


def _pb_push(s, scene):
    """패널 필드를 대상에 적용."""
    if int(s.get("_pb_sync", 0)):
        return
    kind9, t9 = _pb_target(s, scene)
    if t9 is None:
        return
    try:
        if kind9 == "SEQ":
            t9.volume = float(s.playback_vol)
            t9.mute = bool(s.playback_mute)
            if int(t9.frame_start) != int(s.playback_start):
                t9.frame_start = int(s.playback_start)
        else:
            sp9 = t9.data
            sp9.volume = float(s.playback_vol)
            sp9.muted = bool(s.playback_mute)
    except Exception:
        pass


def _pb_speakers():
    return [ob9 for ob9 in bpy.data.objects if ob9.type == 'SPEAKER']


def _pb_solo_restore(s, scene):
    """이 기능이 껐던 소리만 다시 켬 (직접 꺼둔 것은 그대로)."""
    try:
        prev9 = json.loads(str(s.get("_pb_solo", "[]")))
    except Exception:
        prev9 = []
    for key9 in prev9:
        try:
            k9, nm9 = str(key9).split(":", 1)
        except Exception:
            continue
        try:
            if k9 == "SEQ":
                for st9 in _pb_strips(scene):
                    if st9.name == nm9:
                        st9.mute = False
            else:
                ob9 = bpy.data.objects.get(nm9)
                if ob9 is not None and ob9.type == 'SPEAKER':
                    ob9.data.muted = False
        except Exception:
            pass
    s["_pb_solo"] = "[]"


def _pb_solo_apply(s, scene):
    """목록에서 고른 오디오만 재생되도록 나머지를 음소거.

    (선택 안 함)이면 이 기능이 껐던 것을 모두 되살린다.
    """
    _pb_solo_restore(s, scene)
    kind9, tgt9 = _pb_target(s, scene)
    if tgt9 is None:
        return
    try:  # 고른 것은 확실히 들리게
        if kind9 == "SEQ":
            tgt9.mute = bool(s.playback_mute)
        else:
            tgt9.data.muted = bool(s.playback_mute)
    except Exception:
        pass
    muted9 = []
    for st9 in _pb_strips(scene):
        if kind9 == "SEQ" and st9 == tgt9:
            continue
        if not st9.mute:
            st9.mute = True
            muted9.append("SEQ:" + st9.name)
    for ob9 in _pb_speakers():
        if kind9 == "SPK" and ob9 == tgt9:
            continue
        try:
            if not ob9.data.muted:
                ob9.data.muted = True
                muted9.append("SPK:" + ob9.name)
        except Exception:
            pass
    s["_pb_solo"] = json.dumps(muted9)


def _pb_target_update(self, context):
    _pb_pull(self, context.scene)
    _pb_solo_apply(self, context.scene)


def _pb_update(self, context):
    _pb_push(self, context.scene)


def _bone_world(ob9, pb9):
    """포즈 본의 현재 월드 행렬."""
    return ob9.matrix_world @ pb9.matrix


def _childof_set_inverse(c9, ob9, pb9, before9):
    """Child Of '인버스 설정' — 실제로 어긋난 만큼을 재서 되돌린다.

    채널을 일부만 켜면(위치만 따라가기 등) 대상의 전체 역행렬로는
    상쇄가 되지 않아 패널이 튄다. 그래서 제약을 건 뒤 실제 위치를
    측정해 before9(붙이기 직전 위치)로 정확히 되돌리는 역행렬을 쓴다.
    """
    from mathutils import Matrix
    try:
        c9.inverse_matrix = Matrix.Identity(4)
        bpy.context.view_layer.update()
        after9 = _bone_world(ob9, pb9)
        # after = M @ before  →  M = after @ before⁻¹, 되돌리려면 M⁻¹
        m9 = after9 @ before9.inverted()
        c9.inverse_matrix = m9.inverted()
        bpy.context.view_layer.update()
        return True
    except Exception:
        try:
            c9.inverse_matrix = Matrix.Identity(4)
        except Exception:
            pass
        return False


def _panel_follow_bind(s, scene=None):
    """FP_root(그랩 바)가 대상 본을 따라다니도록 Child Of 재설정.

    위치만 따라가게 해서(회전/크기 제외) 패널이 기울지 않는다.
    현재 보이는 위치를 그대로 유지하도록 역행렬을 다시 잡는다.
    """
    rig = getattr(s, "rig", None)
    if rig is None:
        return False
    pb9 = rig.pose.bones.get("FP_root")
    if pb9 is None:
        return False
    try:  # 지금 보이는 위치를 기억해 두었다가 그대로 되돌림
        bpy.context.view_layer.update()
        before9 = _bone_world(rig, pb9).copy()
    except Exception:
        before9 = None
    for c9 in list(pb9.constraints):
        if c9.name == "FSKR_follow":
            try:
                pb9.constraints.remove(c9)
            except Exception:
                pass
    if not bool(getattr(s, "panel_follow", False)):
        return True
    tob9 = getattr(s, "panel_follow_rig", None)
    bn9 = str(getattr(s, "panel_follow_bone", "") or "")
    if tob9 is None or tob9.type != 'ARMATURE' or bn9 not in tob9.pose.bones:
        return False
    try:
        c9 = pb9.constraints.new('CHILD_OF')
        c9.name = "FSKR_follow"
        c9.target = tob9
        c9.subtarget = bn9
        c9.use_rotation_x = False
        c9.use_rotation_y = False
        c9.use_rotation_z = False
        c9.use_scale_x = False
        c9.use_scale_y = False
        c9.use_scale_z = False
        if before9 is not None:
            _childof_set_inverse(c9, rig, pb9, before9)
    except Exception:
        return False
    return True


_ROOT_BONES = ("c_pos", "c_traj", "root", "Root", "ROOT", "master",
               "Master", "c_root", "torso")


def _guess_root_bone(rig):
    """캐릭터 전체를 옮기는 본 추정 (ARP c_pos, Rigify root 등)."""
    if rig is None or rig.type != 'ARMATURE':
        return ""
    for n in _ROOT_BONES:
        if n in rig.pose.bones:
            return n
    return ""


def _panel_follow_update(self, context):
    if self.panel_follow and _SWITCH.get("pf_fill") is not True:
        # 켜는 순간 비어 있으면 지금 리그와 그 리그의 루트 본으로 채움
        _SWITCH["pf_fill"] = True
        try:
            if self.panel_follow_rig is None and self.rig is not None:
                self.panel_follow_rig = self.rig
            if not self.panel_follow_bone:
                self.panel_follow_bone = _guess_root_bone(
                    self.panel_follow_rig)
        finally:
            _SWITCH["pf_fill"] = False
    _panel_follow_bind(self, context.scene)


def draw_panel_follow(layout, s):
    """패널(그랩 바) 위치 + 캐릭터 따라다니기 설정 (두 방식 공통)."""
    pbr = (s.rig.pose.bones.get("FP_root")
           if s.rig and s.rig.type == 'ARMATURE' else None)
    if pbr is None:
        return
    boxr = layout.box()
    boxr.label(text=_tr("패널 위치 (그랩 바)"), icon='EMPTY_ARROWS')
    cr = boxr.column(align=True)
    cr.prop(pbr, "location", index=0, text="X")
    cr.prop(pbr, "location", index=1, text="Y")
    cr.prop(pbr, "location", index=2, text="Z")
    boxr.prop(s, "panel_follow", toggle=True, icon='CON_CHILDOF')
    if s.panel_follow:
        boxr.prop(s, "panel_follow_rig")
        if s.panel_follow_rig and s.panel_follow_rig.type == 'ARMATURE':
            boxr.prop_search(s, "panel_follow_bone",
                             s.panel_follow_rig.data, "bones")
        boxr.operator("fskr.panel_rebind", icon='PINNED')


_SWITCH = {"busy": False, "last": "", "rig": ""}


def _rig_update(self, context):
    """리그를 직접 고르면 그 캐릭터의 설정으로 전환.

    이전 캐릭터의 설정은 그 리그에 스냅샷으로 보존한다.
    """
    if _SWITCH.get("busy"):
        return
    rig = self.rig
    if rig is None:
        return
    prev = None
    try:
        prev = bpy.data.objects.get(str(_SWITCH.get("rig", "")))
    except Exception:
        prev = None
    try:
        act = context.view_layer.objects.active
        _SWITCH["last"] = act.name if act is not None else ""
    except Exception:
        pass
    if prev is None or prev is rig:
        # 다른 캐릭터에서 넘어오는 게 아니면(같은 리그를 다시 고름, 처음
        # 고름) 리그에 남은 예전 스냅샷으로 되살리지 않는다. 지금 패널
        # 상태(예: 다 지운 상태)가 그 리그의 상태가 됨.
        # (다른 파일의 캐릭터 설정을 가져오는 건 '캐릭터 가져오기'로)
        _SWITCH["rig"] = rig.name
        try:
            _char_snapshot(context.scene, rig)
        except Exception:
            pass
        _invalidate_ui_cache()
        return
    try:
        _char_snapshot(context.scene, prev)
    except Exception:
        pass
    _char_switch_to(context.scene, rig)


class FSKR_Settings(bpy.types.PropertyGroup):
    mesh: bpy.props.PointerProperty(
        name="얼굴 메시", type=bpy.types.Object, poll=_mesh_poll)
    rig: bpy.props.PointerProperty(
        name="리그", type=bpy.types.Object, poll=_rig_poll,
        update=_rig_update)
    bone: bpy.props.StringProperty(
        name="머리 본", description="패널 높이 기준이 될 본 (예: c_head.x)")
    arrange_scope: bpy.props.StringProperty(default="")
    arrange: bpy.props.BoolProperty(
        name="배치 모드", default=False, update=_arrange_update,
        description="컨트롤러의 틀을 선택해서 G/R/S로 자유롭게 배치합니다. "
                    "끄면 다시 핸들 조작 모드로 돌아갑니다")
    auto_switch: bpy.props.BoolProperty(
        name="선택한 리그 자동 전환", default=True,
        description="뷰포트에서 패널이 있는 다른 리그를 선택하면 이 패널 "
                    "설정(컨트롤러 목록/프리셋/모캡/립싱크)을 그 캐릭터의 "
                    "것으로 자동 전환합니다")
    labels_visible: bpy.props.BoolProperty(
        name="라벨", default=True, update=_labels_update,
        description="모든 라벨 텍스트 표시/숨김")
    token_l: bpy.props.StringProperty(
        name="좌측 포함식", default="(Left)",
        description="셰이프 키 이름에서 왼쪽을 뜻하는 부분 (예: (Left), .L, _left)")
    token_r: bpy.props.StringProperty(
        name="우측 포함식", default="(Right)",
        description="셰이프 키 이름에서 오른쪽을 뜻하는 부분 (예: (Right), .R, _right)")
    collections: bpy.props.CollectionProperty(type=FSKR_CollectionItem)
    presets: bpy.props.CollectionProperty(type=FSKR_PresetItem)
    # 패널 따라다니기 (그랩 바가 캐릭터 옆 위치를 유지)
    panel_follow: bpy.props.BoolProperty(
        name="캐릭터 따라다니기", default=False,
        update=_panel_follow_update,
        description="패널(그랩 바)과 뷰포트 컨트롤러가 아래 본을 따라다니며 "
                    "지금의 상대 위치를 계속 유지합니다. 캐릭터가 움직여도 "
                    "옆에 붙어 있습니다 (켜면 리그의 c_pos·root 본을 자동으로 "
                    "고름)")
    panel_follow_rig: bpy.props.PointerProperty(
        name="대상 리그", type=bpy.types.Object, poll=_rig_poll,
        update=_panel_follow_update,
        description="따라갈 본이 있는 아마추어 (캐릭터 리그)")
    panel_follow_bone: bpy.props.StringProperty(
        name="대상 본", update=_panel_follow_update,
        description="패널이 따라갈 본 (보통 머리 본)")
    # 패널 생성 위치 (크로스헤어로 지정, 월드 좌표)
    panel_pos: bpy.props.FloatVectorProperty(size=3,
                                             default=(0.0, 0.0, 0.0))
    panel_pos_set: bpy.props.BoolProperty(default=False)
    # iFacialMocap
    mocap_ip: bpy.props.StringProperty(
        name="아이폰 IP", default="",
        description="iFacialMocap 앱 화면에 표시되는 아이폰의 IP 주소 "
                    "(같은 와이파이여야 함)")
    mocap_record: bpy.props.BoolProperty(
        name="녹화", default=False,
        description="애니메이션 재생 중일 때 매핑된 핸들에 키프레임을 "
                    "기록합니다 (스페이스바로 재생하며 연기하세요)")
    mocap_smooth: bpy.props.FloatProperty(
        name="스무딩", default=0.5, min=0.0, max=0.95,
        description="값 떨림 완화. 높을수록 부드럽지만 반응이 느려집니다")
    mocap_blend: bpy.props.FloatProperty(
        name="프리셋 블렌딩 (초)", default=0.25, min=0.0, soft_max=2.0,
        precision=2,
        description="프리셋 전환에 걸리는 시간. 0이면 즉시 전환")
    mocap_preview: bpy.props.BoolProperty(
        name="수신 미리보기", default=True,
        description="수신 중인 표정 값을 뷰포트에 도식으로 표시")
    mocap_preview_scale: bpy.props.FloatProperty(
        name="미리보기 크기", default=1.6, min=0.8, soft_max=3.0,
        precision=1, description="미리보기 도식의 표시 배율")
    mocap_countdown: bpy.props.FloatProperty(
        name="카운트다운 (초)", default=3.0, min=0.0, soft_max=10.0,
        precision=1,
        description="녹화 시작 버튼을 누른 뒤 재생까지의 대기 시간 "
                    "(0 = 즉시 시작)")
    # 립싱크 구간 편집 데이터
    lipsync_segs: bpy.props.CollectionProperty(type=FSKR_LipSegItem)
    lipsync_idx: bpy.props.IntProperty(default=0)
    lipsync_open: bpy.props.StringProperty(default="")  # 프레임별 개방도 JSON
    lipsync_start: bpy.props.IntProperty(default=1)
    lipsync_audio: bpy.props.StringProperty(default="")  # 원본 오디오 경로
    lipsync_baked: bpy.props.StringProperty(default="")  # 마지막 굽기 범위
    lipsync_fps: bpy.props.FloatProperty(default=0.0)  # 분석 시점 fps
    # 재생 오디오 (스페이스바로 들리는 소리) — 립싱크 분석용과 별개
    playback_target: bpy.props.EnumProperty(
        name="재생 오디오", items=_pb_items, update=_pb_target_update,
        description="여기서 고른 오디오만 재생됩니다 (나머지 사운드는 "
                    "자동 음소거). 립싱크 분석용 오디오와 따로 "
                    "조절됩니다")
    playback_vol: bpy.props.FloatProperty(
        name="볼륨", default=1.0, min=0.0, soft_max=2.0, precision=2,
        update=_pb_update, description="재생 오디오의 볼륨")
    playback_mute: bpy.props.BoolProperty(
        name="음소거", default=False, update=_pb_update,
        description="재생 오디오만 잠시 끕니다 (립싱크 편집기 소리는 유지)")
    playback_start: bpy.props.IntProperty(
        name="시작 프레임", default=1, update=_pb_update,
        description="사운드 스트립이 시작할 프레임")
    lipsync_clus: bpy.props.StringProperty(default="[]")  # 클러스터 JSON
    lipsync_mk_gap: bpy.props.IntProperty(default=8, min=1)
    lipsync_favs: bpy.props.StringProperty(default="[]")  # 입모양 즐겨찾기
    lipsync_blend: bpy.props.IntProperty(
        name="블렌딩", default=2, min=0, max=12,
        description="구간 앞뒤로 이만큼의 프레임에 걸쳐 부드럽게 전환")
    mocap_neutral: bpy.props.StringProperty(default="")  # 캘리브레이션 JSON
    mocap_map: bpy.props.CollectionProperty(type=FSKR_MocapMapItem)
    mocap_head_rig: bpy.props.PointerProperty(
        name="목 리그", type=bpy.types.Object, poll=_rig_poll,
        description="머리 회전을 적용할 본이 있는 아마추어")
    mocap_head_bone: bpy.props.StringProperty(
        name="목 본",
        description="머리 회전을 따라 돌 본 (예: c_head.x, neck)")
    mocap_head_gain: bpy.props.FloatProperty(
        name="회전 배율", default=1.0, soft_min=-2.0, soft_max=2.0,
        precision=2,
        description="머리 회전 반영 정도. 방향이 반대면 음수로")
    # 머리 회전 축 리매핑 (리그마다 본 로컬 축이 다름)
    mocap_head_ax_p: bpy.props.EnumProperty(
        name="끄덕임 →", default='X', items=AXIS_ITEMS,
        description="위아래 끄덕임(피치)을 보낼 본 로컬 축")
    mocap_head_ax_y: bpy.props.EnumProperty(
        name="돌림 →", default='Y', items=AXIS_ITEMS,
        description="좌우 돌림(요)을 보낼 본 로컬 축")
    mocap_head_ax_r: bpy.props.EnumProperty(
        name="갸웃 →", default='Z', items=AXIS_ITEMS,
        description="좌우 갸웃(롤)을 보낼 본 로컬 축")
    mocap_head_inv_p: bpy.props.BoolProperty(
        name="반전", default=False, description="끄덕임 방향 반전")
    mocap_head_inv_y: bpy.props.BoolProperty(
        name="반전", default=False, description="돌림 방향 반전")
    mocap_head_inv_r: bpy.props.BoolProperty(
        name="반전", default=False, description="갸웃 방향 반전")


class FSKR_ChainItem(bpy.types.PropertyGroup):
    """연쇄 드라이버 항목: 슬라이더 값 × 배율로 함께 움직이는 셰이프 키."""
    mesh: bpy.props.EnumProperty(
        name="메시", items=_mesh_items,
        description="연쇄 셰이프 키가 있는 메시 (기본 = 설정의 얼굴 메시)")
    key: bpy.props.EnumProperty(
        name="셰이프 키", items=_shape_key_items,
        description="이 슬라이더 값에 배율을 곱해 함께 움직일 셰이프 키")
    factor: bpy.props.FloatProperty(
        name="배율", default=1.0, soft_min=-2.0, soft_max=2.0,
        precision=2,
        description="슬라이더 값에 곱해질 배율 (음수 = 반대로 움직임)")
    rm: bpy.props.BoolProperty(
        name="삭제", default=False,
        description="체크하고 OK를 누르면 이 연쇄가 삭제됩니다")


def _chain_add_update(self, context):
    if not self.chain_add:
        return
    self.chain_add = False
    self.chain.add()


_enum_cache_coll = []


def _collection_items(self, context):
    """저장된 컬렉션 + 본에 이미 지정된 그룹명의 합집합."""
    global _enum_cache_coll
    s = context.scene.fskr
    names = [c.name for c in s.collections]
    if s.rig:
        for b in s.rig.data.bones:
            if _is_handle_name(b.name):
                g = str(s.rig.pose.bones[b.name].get("fskr_group", ""))
                if g and g not in names:
                    names.append(g)
    items = [("__REMOVE__", _tr("(컬렉션에서 제거)"), _tr("체크한 컨트롤러를 컬렉션 밖으로"))]
    items += [(n, n, "") for n in names]
    return _stable_items("coll", items)


_enum_cache_gp = []


def _group_pick_items(self, context):
    """기존 그룹/컬렉션 목록 (그룹 입력칸 옆 드롭다운용)."""
    global _enum_cache_gp
    s = context.scene.fskr
    names = [c.name for c in s.collections]
    if s.rig:
        for b in s.rig.data.bones:
            if _is_handle_name(b.name):
                g = str(s.rig.pose.bones[b.name].get("fskr_group", ""))
                if g and g not in names:
                    names.append(g)
    return _stable_items("grp",
                         [("__PICK__", _tr("(기존 그룹에서 선택)"), ""),
                          ("__NONE__", _tr("(그룹 없음)"), "")]
                         + [(n, n, "") for n in names])


def _group_pick_update(self, context):
    """드롭다운에서 고르면 그룹 입력칸을 채움."""
    if self.group_pick == "__PICK__":
        return
    self.group = "" if self.group_pick == "__NONE__" else self.group_pick
    self.group_pick = "__PICK__"


def _draw_group_row(col, op):
    row = col.row(align=True)
    row.prop(op, "group")
    sub = row.row(align=True)
    sub.ui_units_x = 2.2
    sub.prop(op, "group_pick", text="")


def _draw_pad_grid(layout, op):
    """패드 모양 그대로의 3x3 그리드에 방향별 드롭박스 배치."""
    grid = layout.grid_flow(row_major=True, columns=3, even_columns=True)
    cells = (("ul", _tr("↖ 좌상")), ("up", _tr("↑ 위")), ("ur", _tr("↗ 우상")),
             ("left", _tr("← 왼쪽")), (None, _tr("중앙 (원점)")), ("right", _tr("→ 오른쪽")),
             ("dl", _tr("↙ 좌하")), ("down", _tr("↓ 아래")), ("dr", _tr("↘ 우하")))
    for pname, lab in cells:
        cell = grid.box().column(align=True)
        if pname:
            cell.label(text=lab)
            cell.prop(op, pname, text="")
            # 방향별 배율 (지원하는 팝업에서만)
            if hasattr(op, "pm_" + pname):
                cell.prop(op, "pm_" + pname, text="x")
        else:
            cell.label(text="")
            r = cell.row()
            r.alignment = 'CENTER'
            r.label(text=lab)


CTYPE_ITEMS = (('SLD_H', "슬라이더 (가로)", "왼쪽에서 오른쪽으로 0~1"),
               ('SLD_V', "슬라이더 (세로)", "아래에서 위로 0~1"),
               ('PAD', "2D 패드", "상/하/좌/우 방향별 연결"),
               ('BONE', "본 패드", "핸들 XY로 본(눈알 타겟 등)의 위치를 움직임"))


_enum_cache_arm = []


def _armature_items(self, context):
    """씬의 모든 아마추어 (본 패드 대상 리그 선택용)."""
    global _enum_cache_arm
    items = [(ob.name, ob.name, "")
             for ob in bpy.data.objects if ob.type == 'ARMATURE']
    if not items:
        items = [(NONE, _tr("(아마추어 없음)"), "")]
    return _stable_items("arm", items)


def _widget_coll(context):
    coll = bpy.data.collections.get("FP_Widgets")
    if not coll:
        coll = bpy.data.collections.new("FP_Widgets")
        context.scene.collection.children.link(coll)

    def exclude(lc):
        for c in lc.children:
            if c.collection is coll:
                c.exclude = True
                return True
            if exclude(c):
                return True
        return False
    exclude(context.view_layer.layer_collection)
    return coll


def _wire_square(coll, name, cross=False):
    ob = bpy.data.objects.get(name)
    if ob:
        return ob
    edges = [(0, 1), (1, 2), (2, 3), (3, 0)]
    if cross:
        edges += [(0, 2), (1, 3)]
    me = bpy.data.meshes.new(name)
    me.from_pydata([(-.5, -.5, 0), (.5, -.5, 0), (.5, .5, 0), (-.5, .5, 0)],
                   edges, [])
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def _set_color(pb, use, col):
    """본 커스텀 색상 설정 (Blender 4.0+ 전용, 이전 버전에선 무시)."""
    if not hasattr(pb, "color"):
        return
    if use:
        pb.color.palette = 'CUSTOM'
        c = pb.color.custom
        c.normal = col
        c.select = tuple(min(v + 0.25, 1.0) for v in col)
        c.active = tuple(min(v + 0.45, 1.0) for v in col)
    else:
        pb.color.palette = 'DEFAULT'


_col_sync_guard = [False]


def _col_update(self, context):
    """N패널 스와치에서 색을 바꾸면 핸들/틀/스냅 표시 본에 실시간 반영.

    체크박스가 켜진 상태면 체크된 다른 컨트롤러들에도 같은 색을 일괄 적용.
    """
    rig = self.id_data
    use = bool(self.get("fskr_usecolor", 0))
    col = tuple(self.fskr_col)
    self["fskr_color"] = list(col)
    _set_color(self, use, col)
    for suf in ("_frame", "_snap", "_thr"):
        b = rig.pose.bones.get(self.name + suf)
        if b:
            _set_color(b, use, col)
    # 체크된 컨트롤러 일괄 적용 (재귀 방지 가드)
    if getattr(self, "fskr_sel", False) and not _col_sync_guard[0]:
        _col_sync_guard[0] = True
        try:
            for pb2 in rig.pose.bones:
                if (pb2.name != self.name and _is_handle_name(pb2.name)
                        and getattr(pb2, "fskr_sel", False)):
                    pb2["fskr_usecolor"] = 1
                    pb2.fskr_col = col
        finally:
            _col_sync_guard[0] = False


_SLOT_ORDER = ("up", "down", "left", "right", "ul", "ur", "dl", "dr")


_SLOT_ARROW = {"up": "↑", "down": "↓", "left": "←", "right": "→",
               "ul": "↖", "ur": "↗", "dl": "↙", "dr": "↘"}


def _slot_order(pb):
    """패드의 슬롯 표시 순서 (저장값 + 누락분은 기본 순서로 보충)."""
    raw = str(pb.get("fskr_sloto", ""))
    parts = [p for p in raw.split(",") if p in _SLOT_ORDER]
    for s in _SLOT_ORDER:
        if s not in parts:
            parts.append(s)
    return parts


def _slot_visible(pb, order):
    """키가 연결된 슬롯만, 같은 키 중복 없이 표시 순서대로."""
    vis = []
    seen = set()
    for s in order:
        k = str(pb.get("fskr_" + s, NONE))
        if k != NONE and k not in seen:
            seen.add(k)
            vis.append(s)
    return vis


def _mk_slot_get(slot):
    def g(self):
        try:
            return _slot_visible(self, _slot_order(self)).index(slot) + 1
        except ValueError:
            return 0
    return g


def _mk_slot_set(slot):
    def st(self, value):
        order = _slot_order(self)
        vis = _slot_visible(self, order)
        if slot not in vis:
            return
        i = vis.index(slot)
        j = max(0, min(len(vis) - 1, value - 1))
        if j != i:
            vis.pop(i)
            vis.insert(j, slot)
        rest = [s for s in order if s not in vis]
        self["fskr_sloto"] = ",".join(vis + rest)
    return st


def _idx_get(self):
    """목록 내 1-기준 순번 (그룹 내)."""
    rig = self.id_data
    try:
        grp = str(self.get("fskr_group", ""))
        sibs = [n for n in _sorted_ctls(rig)
                if str(rig.pose.bones[n].get("fskr_group", "")) == grp]
        return sibs.index(self.name) + 1
    except Exception:
        return 0


def _idx_set(self, value):
    """순번 입력 시 해당 위치에 끼어들고 나머지는 한 칸씩 밀림."""
    rig = self.id_data
    grp = str(self.get("fskr_group", ""))
    sibs = [n for n in _sorted_ctls(rig)
            if str(rig.pose.bones[n].get("fskr_group", "")) == grp]
    if self.name not in sibs:
        return
    i = sibs.index(self.name)
    j = max(0, min(len(sibs) - 1, value - 1))
    if j != i:
        sibs.pop(i)
        sibs.insert(j, self.name)
    for k, n in enumerate(sibs):
        rig.pose.bones[n]["fskr_order"] = k


def _sorted_ctls(rig):
    """그룹 → 순서 → 이름 순으로 정렬된 핸들 본 이름 목록."""
    def keyf(n):
        pb = rig.pose.bones[n]
        return (str(pb.get("fskr_group", "")),
                int(pb.get("fskr_order", 9999)), n)
    return sorted([b.name for b in rig.data.bones if _is_handle_name(b.name)],
                  key=keyf)


def _frame_corners(pb):
    """프레임 본 위젯 사각형의 네 모서리 + 중앙점 (armature space)."""
    w, h, _ = pb.custom_shape_scale_xyz
    tx, ty, _ = pb.custom_shape_translation
    m = pb.matrix
    pts = []
    sh = pb.custom_shape
    if (not pb.name.startswith("FP_ctl") and sh is not None
            and sh.type == 'MESH' and len(sh.data.vertices)):
        # 스프라이트 컨트롤러: 위젯 메시의 실제 경계 (격자/목록/패드)
        xs = [v.co.x for v in sh.data.vertices]
        ys = [v.co.y for v in sh.data.vertices]
        ax0, ax1 = min(xs) * w + tx, max(xs) * w + tx
        ay0, ay1 = min(ys) * h + ty, max(ys) * h + ty
        for x in (ax0, ax1):
            for y in (ay0, ay1):
                pts.append(m @ Vector((x, y, 0.0)))
        pts.append(m @ Vector(((ax0 + ax1) / 2, (ay0 + ay1) / 2, 0.0)))
        return pts
    for dx in (-w / 2, w / 2):
        for dy in (-h / 2, h / 2):
            pts.append(m @ Vector((tx + dx, ty + dy, 0.0)))
    pts.append(m @ Vector((tx, ty, 0.0)))  # 중앙 (중앙 스냅용)
    return pts


_VP_PREFIX = ("FP_spr_", "FP_eye_", "FP_pre_", "FP_lay_")


def _vp_frame_name(rig, n):
    """선택한 본 → 배치 모드로 옮길 틀 이름 (드라이버 방식/스프라이트 공통).

    스프라이트 컨트롤러는 FP_root 바로 아래의 틀까지 거슬러 올라간다.
    """
    if n.startswith("FP_ctl"):
        if n.endswith("_frame"):
            return n
        if _is_handle_name(n):
            return n + "_frame"
        return None
    if not n.startswith(_VP_PREFIX):
        return None
    pb = rig.pose.bones.get(n)
    while pb is not None and pb.parent is not None and \
            pb.parent.name != "FP_root":
        pb = pb.parent
    if pb is None or not pb.name.endswith("_frame"):
        return None
    return pb.name


def _vp_handle_of(rig, fname):
    """틀 이름 → 그 컨트롤러의 손잡이 본 (없으면 None)."""
    return rig.pose.bones.get(fname[:-len("_frame")])


_ARROW_BLOCK = {"name": None}   # 크기 고정 틀의 화살표를 잡는 중 (빨간색)


def _vp_resizable(rig, fname):
    """크기 조절 가능 여부: 시트 격자(입/파츠)는 고정."""
    if fname.startswith("FP_ctl"):
        return True
    pb = rig.pose.bones.get(fname)
    if pb is None:
        return False
    return not (fname.startswith(("FP_spr_", "FP_lay_"))
                or pb.get("fskr_fixed"))


def _vp_frames(rig):
    """스냅 대상이 되는 모든 최상위 틀 (드라이버 방식 + 스프라이트)."""
    out = []
    for b in rig.pose.bones:
        n = b.name
        if not n.endswith("_frame"):
            continue
        if n.startswith("FP_ctl"):
            out.append(b)
        elif n.startswith(_VP_PREFIX) and b.parent is not None and \
                b.parent.name == "FP_root":
            out.append(b)
    return out


def _add_driver(kb, rig, bone, expr, chain=False):
    try:
        kb.driver_remove("value")
    except Exception:
        pass
    fc = kb.driver_add("value")
    drv = fc.driver
    drv.type = 'SCRIPTED'
    drv.expression = "fskr_z(%s)" % expr
    if chain:
        # 연쇄 표시용 마커 변수 (이름 동기화에서 제외하기 위함)
        var = drv.variables.new()
        var.name = "chx"
        var.type = 'SINGLE_PROP'
        t = var.targets[0]
        t.id = rig
        t.data_path = "name"
    for vn, tt in (("x", 'LOC_X'), ("y", 'LOC_Y')):
        var = drv.variables.new()
        var.name = vn
        var.type = 'TRANSFORMS'
        t = var.targets[0]
        t.id = rig
        t.bone_target = bone
        t.transform_type = tt
        t.transform_space = 'LOCAL_SPACE'


def _resolve_mesh_name(nm, rig=None):
    """이름 문자열로 메시 찾기. 정확 일치 → 접미사 밀림 대응 순.

    Append로 Face가 Face.001이 된 경우, 같은 베이스 이름에
    이 리그를 타겟으로 하는 Armature 모디파이어를 가진 메시를 찾는다.
    """
    if not nm:
        return None
    ob = bpy.data.objects.get(nm)
    if ob is not None and ob.type == 'MESH':
        return ob
    import re as _re
    base = _re.sub(r"\.\d+$", "", nm)
    loose = []
    for o in bpy.data.objects:
        if o.type != 'MESH' or _re.sub(r"\.\d+$", "", o.name) != base:
            continue
        if rig is not None and any(
                m.type == 'ARMATURE' and m.object == rig
                for m in o.modifiers):
            return o
        loose.append(o)
    return loose[0] if loose else None


def _ctl_mesh_get(pb):
    """컨트롤러별 메시: ID 포인터 우선, 이름 문자열 폴백.

    비어 있으면 None(=설정의 얼굴 메시 사용). 포인터는 개명/Append를
    자동으로 따라가므로 이름 충돌에 안전하다.
    """
    ob = None
    try:
        ob = pb.get("fskr_mesh_ptr", None)
    except Exception:
        ob = None
    if ob is not None:
        try:
            if isinstance(ob, bpy.types.Object) and ob.type == 'MESH':
                return ob
        except Exception:
            pass
    nm = str(pb.get("fskr_mesh", ""))
    if not nm:
        return None
    return _resolve_mesh_name(nm, pb.id_data)


def _mesh_meta_name(pb):
    """메타데이터/내보내기용 메시 이름 (포인터가 있으면 현재 이름)."""
    ob = _ctl_mesh_get(pb)
    if ob is not None:
        return ob.name
    return str(pb.get("fskr_mesh", ""))


def _pg_virtual(pid):
    """저장하지 않는 계산용 프로퍼티 (스프라이트 피커/칸별 슬라이더)."""
    return (pid.startswith(("pick_", "cur_"))
            or pid in ("row_link_pick", "pick", "clip_pick", "link_pick",
                       "follow_pick", "look_x", "look_y", "atlas_pick",
                       "canvas_pick", "tag_filter_pick",
                       "tag_pick", "marker_pick", "mk_sel", "over_info", "parent_pick"))


def _pg_snap(pg):
    """PropertyGroup → dict. ID 포인터는 "@id:이름", 컬렉션은 재귀."""
    out = {}
    for pr in pg.bl_rna.properties:
        pid = pr.identifier
        if pid == "rna_type" or _pg_virtual(pid):
            continue
        try:
            if pr.type == 'POINTER':
                val = getattr(pg, pid)
                if val is None:
                    out[pid] = None
                elif isinstance(val, bpy.types.ID):
                    out[pid] = "@id:" + val.name
                else:
                    out[pid] = _pg_snap(val)
            elif pr.type == 'COLLECTION':
                out[pid] = [_pg_snap(it) for it in getattr(pg, pid)]
            else:
                val = getattr(pg, pid)
                if hasattr(val, "__len__") and not isinstance(val, str):
                    val = list(val)
                out[pid] = val
        except Exception:
            pass
    return out


def _pg_restore(pg, data, skip=()):
    """dict → PropertyGroup. ID 포인터("@id:")는 호출자가 별도 처리."""
    for pr in pg.bl_rna.properties:
        pid = pr.identifier
        if (pid == "rna_type" or pid in skip or pid not in data
                or _pg_virtual(pid)):
            continue
        try:
            val = data[pid]
            if pr.type == 'POINTER':
                if isinstance(val, dict):
                    _pg_restore(getattr(pg, pid), val)
            elif pr.type == 'COLLECTION':
                col = getattr(pg, pid)
                col.clear()
                for it in val:
                    _pg_restore(col.add(), it)
            elif not pr.is_readonly:
                setattr(pg, pid,
                        tuple(val) if isinstance(val, list) else val)
        except Exception:
            pass


def _char_snapshot(scene, rig=None):
    """씬 설정 + 라벨을 리그의 커스텀 프로퍼티에 JSON으로 저장.

    Append는 오브젝트 커스텀 프로퍼티를 함께 가져오므로, 다른 파일에서
    '캐릭터 가져오기'가 이 스냅샷으로 씬 설정을 복구할 수 있다.
    rig를 넘기면 그 리그에 저장한다(캐릭터 전환 직전 보존용).
    """
    s = scene.fskr
    if rig is None:
        rig = s.rig
    if rig is None:
        return None
    labels = []
    try:
        inv = rig.matrix_world.inverted()
    except Exception:
        from mathutils import Matrix
        inv = Matrix.Identity(4)
    for ob in bpy.data.objects:
        if not (ob.name.startswith("FPLBL") and ob.type == 'FONT'
                and ob.parent is rig):
            continue
        m = inv @ ob.matrix_world
        labels.append({
            "body": ob.data.body,
            "size": float(ob.data.size),
            "color": [float(c) for c in ob.color],
            "bone": ob.parent_bone or "FP_root",
            "matrix": [v for row in m for v in row],
        })
    snap = {"ver": 1, "settings": _pg_snap(s), "labels": labels}
    try:
        rig["fskr_char"] = json.dumps(snap, ensure_ascii=False)
    except Exception:
        return None
    return snap


@bpy.app.handlers.persistent
def _fskr_char_save_pre(*args):
    """파일 저장 직전 스냅샷 자동 갱신 (내보내기를 잊어도 안전)."""
    try:
        for sc in bpy.data.scenes:
            if getattr(sc.fskr, "rig", None) is not None:
                _char_snapshot(sc)
    except Exception:
        pass


def _char_switch_to(scene, rig):
    """패널 설정을 이 리그의 캐릭터로 전환.

    떠나는 캐릭터의 상태는 스냅샷으로 보존하고, 대상 리그의 스냅샷이
    있으면 씬 설정(컬렉션/프리셋/모캡/립싱크)을 복구한다.
    """
    s = scene.fskr
    if _SWITCH["busy"]:
        return
    _SWITCH["busy"] = True
    try:
        _char_switch_do(scene, s, rig)
    finally:
        _SWITCH["busy"] = False


def _char_switch_do(scene, s, rig):
    try:
        if s.rig is not None and s.rig is not rig:
            _char_snapshot(scene)  # 떠나는 캐릭터 보존
    except Exception:
        pass
    raw = ""
    try:
        raw = str(rig.get("fskr_char", ""))
    except Exception:
        pass
    s.rig = rig
    if raw:
        try:
            snap = json.loads(raw)
            st = snap.get("settings", {})
            mn = st.get("mesh")
            if isinstance(mn, str) and mn.startswith("@id:"):
                mo = _resolve_mesh_name(mn[4:], rig)
                if mo is not None:
                    s.mesh = mo
            _pg_restore(s, st, skip=("rig", "mesh", "mocap_head_rig",
                                     "arrange", "auto_switch"))
            hn = st.get("mocap_head_rig")
            if isinstance(hn, str) and hn.startswith("@id:"):
                ho = bpy.data.objects.get(hn[4:])
                if ho is not None and ho.type == 'ARMATURE':
                    s.mocap_head_rig = ho
        except Exception:
            pass
    else:
        # 스냅샷 없음: 이 리그가 모는 셰이프 키 메시로 추정
        for ob9 in bpy.data.objects:
            if (ob9.type == 'MESH' and ob9.data.shape_keys
                    and any(m.type == 'ARMATURE' and m.object == rig
                            for m in ob9.modifiers)):
                s.mesh = ob9
                break
        _char_snapshot(scene)
    try:
        _SWITCH["rig"] = rig.name
    except Exception:
        pass
    _invalidate_ui_cache()


@bpy.app.handlers.persistent
def _fskr_char_autoswitch(scene, depsgraph=None):
    """활성 오브젝트가 패널 있는 다른 리그로 '바뀐 순간'에만 따라 전환.

    단순히 s.rig와 다르다고 전환하면, 드롭다운으로 직접 고른 리그를
    되돌려 버린다(립싱크 작업 중 이전 캐릭터 설정이 되살아나는 원인).
    또 립싱크 편집기가 열려 있는 동안에는 전환하지 않는다.
    """
    try:
        s = scene.fskr
        act = bpy.context.view_layer.objects.active
        nm9 = act.name if act is not None else ""
        prev9 = _SWITCH.get("last", "")
        _SWITCH["last"] = nm9
        if nm9 != prev9 and act is not None and act.type == 'MESH':
            # 캔버스(또는 그 머리카락 위 복사본)를 고르면 N패널도 그 캔버스로
            for e in s.eyes:
                if act.name in (e.target, "FaceCanvasOver_" + e.uid):
                    if getattr(s, "canvas_uid", "") != e.uid:
                        s.canvas_uid = e.uid
                        for w in bpy.context.window_manager.windows:
                            for a in w.screen.areas:
                                if a.type in ('VIEW_3D', 'PROPERTIES'):
                                    a.tag_redraw()
                    break
        if not s.auto_switch or _SWITCH["busy"]:
            return
        if nm9 == prev9:
            return  # 선택이 그대로 → 사용자의 수동 선택을 존중
        if _LIPSRV.get("srv") is not None:
            return  # 립싱크 편집 중에는 캐릭터 전환 금지
        if act is None or act is s.rig or act.type != 'ARMATURE':
            return
        if "FP_root" not in act.data.bones:
            return
        _char_switch_to(scene, act)
    except Exception:
        pass


def _driver_belongs_to(fc, rig):
    """이 드라이버의 변수 타겟이 해당 리그를 가리키는가.

    한 파일에 캐릭터(패널)가 여러 개 있을 때 다른 리그의
    드라이버를 건드리지 않기 위한 공통 필터.
    """
    try:
        for var in fc.driver.variables:
            for t in var.targets:
                if t.id == rig:
                    return True
    except Exception:
        pass
    return False


def _remove_drivers_for_bone(mesh, bone, rig=None):
    """모든 셰이프 키 데이터에서 이 본을 참조하는 드라이버 제거.

    컨트롤러마다 다른 메시를 쓸 수 있으므로 씬 전체를 검사.
    rig가 주어지면 그 리그를 가리키는 드라이버만 제거한다
    (여러 캐릭터 공존 대비).
    """
    for kd in bpy.data.shape_keys:
        ad = kd.animation_data
        if not ad:
            continue
        for fc in list(ad.drivers):
            for var in fc.driver.variables:
                if any(t.bone_target == bone
                       and (rig is None or t.id == rig)
                       for t in var.targets):
                    ad.drivers.remove(fc)
                    break


def _remove_bone_drivers_for(rig, handle):
    """이 핸들이 움직이는 대상 본 위치 드라이버 제거 (씬의 모든 아마추어에서)."""
    for ob in bpy.data.objects:
        if ob.type != 'ARMATURE':
            continue
        ad = ob.animation_data
        if not ad:
            continue
        for fc in list(ad.drivers):
            if not fc.data_path.endswith(".location"):
                continue
            if "FP_ctl" in fc.data_path:
                continue  # 패널 자체 본의 표시 드라이버는 제외
            for var in fc.driver.variables:
                if any(t.bone_target == handle and t.id == rig
                       for t in var.targets):
                    ad.drivers.remove(fc)
                    break


def _clear_bone_drivers(rig, handle, trig, target):
    """이 핸들이 대상 본에 만든 위치/회전 드라이버를 모두 제거.

    축이나 구동 방식(위치/회전)을 바꿨을 때 옛 축의 드라이버가 남아
    본이 엉뚱하게 도는 것을 막는다. 다른 컨트롤러가 만든 드라이버는
    건드리지 않는다.
    """
    ad9 = getattr(trig, "animation_data", None)
    if ad9 is None:
        return
    paths9 = ('pose.bones["%s"].location' % target,
              'pose.bones["%s"].rotation_euler' % target)
    for dp9 in paths9:
        for ix9 in (0, 1, 2):
            fc9 = None
            for c9 in ad9.drivers:
                if c9.data_path == dp9 and c9.array_index == ix9:
                    fc9 = c9
                    break
            if fc9 is None:
                continue
            mine9 = False
            try:
                for v9 in fc9.driver.variables:
                    for t9 in v9.targets:
                        if (t9.id == rig
                                and t9.bone_target == handle):
                            mine9 = True
            except Exception:
                pass
            if not mine9:
                continue
            try:
                trig.driver_remove(dp9, ix9)
            except Exception:
                pass
            # 남은 값 초기화 (회전↔위치 전환 잔상 방지)
            try:
                pb9 = trig.pose.bones.get(target)
                if pb9 is not None:
                    if dp9.endswith("location"):
                        pb9.location[ix9] = 0.0
                    else:
                        pb9.rotation_euler[ix9] = 0.0
            except Exception:
                pass


def _add_bone_axis_driver(rig, handle, trig, target, idx, expr,
                          mode='LOC'):
    """대상 본의 위치 또는 회전에 핸들 XY 기반 드라이버 연결."""
    if mode == 'ROT':
        try:
            pb9 = trig.pose.bones.get(target)
            if pb9 is not None and pb9.rotation_mode in (
                    'QUATERNION', 'AXIS_ANGLE'):
                pb9.rotation_mode = 'XYZ'
        except Exception:
            pass
        path = 'pose.bones["%s"].rotation_euler' % target
    else:
        path = 'pose.bones["%s"].location' % target
    try:
        trig.driver_remove(path, idx)
    except Exception:
        pass
    fc = trig.driver_add(path, idx)
    drv = fc.driver
    drv.type = 'SCRIPTED'
    drv.expression = "fskr_z(%s)" % expr
    for vn, tt in (("x", 'LOC_X'), ("y", 'LOC_Y')):
        var = drv.variables.new()
        var.name = vn
        var.type = 'TRANSFORMS'
        t = var.targets[0]
        t.id = rig
        t.bone_target = handle
        t.transform_type = tt
        t.transform_space = 'LOCAL_SPACE'


_SLOT_FIELDS = {'U': ("up",), 'D': ("down",), 'L': ("left",),
                'R': ("right",), 'UR': ("ur",), 'UL': ("ul",),
                'DR': ("dr",), 'DL': ("dl",),
                'X': ("left", "right"), 'Y': ("up", "down")}


def _sync_key_names(rig):
    """드라이버가 실제로 물고 있는 셰이프 키 이름으로 메타데이터 갱신.

    셰이프 키 이름을 바꾸면 Blender가 드라이버 경로는 따라가지만
    컨트롤러 메타데이터(fskr_*)에는 옛 이름이 남으므로 여기서 동기화.
    """
    import re as _re
    n = 0
    for kd in bpy.data.shape_keys:
        ad = kd.animation_data
        if not (ad and ad.drivers):
            continue
        for fc in ad.drivers:
            dp = fc.data_path
            if not dp.startswith('key_blocks["'):
                continue
            if any(v.name == "chx" for v in fc.driver.variables):
                continue  # 연쇄 드라이버는 메타데이터 갱신 대상 아님
            nm = dp[len('key_blocks["'):dp.rfind('"]')]
            handle = None
            for var in fc.driver.variables:
                for t in var.targets:
                    if (t.id == rig
                            and str(t.bone_target).startswith("FP_ctl")):
                        handle = t.bone_target
                        break
                if handle:
                    break
            if not handle or handle not in rig.pose.bones:
                continue
            pb = rig.pose.bones[handle]
            ctype = str(pb.get("fskr_type", 'SLD_H'))
            expr = fc.driver.expression or ""
            if ctype == 'PAD':
                slots = set(_re.findall(r"'(UR|UL|DR|DL|U|D|L|R|X|Y)'",
                                        expr))
                fields = []
                for sl in slots:
                    fields += list(_SLOT_FIELDS.get(sl, ()))
            elif ctype in ('SLD_H', 'SLD_V'):
                fields = ["key"]
            else:
                continue
            for f2 in fields:
                old = str(pb.get("fskr_" + f2, NONE))
                if old != nm:
                    pb["fskr_" + f2] = nm
                    if str(pb.get("fskr_label", "")) == old:
                        pb["fskr_label"] = nm
                    n += 1
            # 키가 실제로 있는 메시로 메시 메타데이터도 갱신
            owner = None
            for ob9 in bpy.data.objects:
                if ob9.type == 'MESH' and ob9.data.shape_keys is kd:
                    owner = ob9
                    break
            if owner is not None:
                try:
                    s9 = bpy.context.scene.fskr
                    def_m = s9.mesh.name if s9.mesh else ""
                except Exception:
                    def_m = ""
                cur_m = str(pb.get("fskr_mesh", "")) or def_m
                if owner.name != cur_m:
                    pb["fskr_mesh"] = ("" if owner.name == def_m
                                       else owner.name)
                    try:
                        if owner.name == def_m:
                            if "fskr_mesh_ptr" in pb:
                                del pb["fskr_mesh_ptr"]
                        else:
                            pb["fskr_mesh_ptr"] = owner
                    except Exception:
                        pass
                    n += 1
    _invalidate_ui_cache()
    return n


_UI_CACHE = {"t": 0.0, "driven": {}, "rig": ""}


def _invalidate_ui_cache():
    _UI_CACHE["t"] = 0.0


def _kb_val(kb):
    """키블록 값 (undo 등으로 참조가 죽었으면 None)."""
    try:
        return kb.value
    except Exception:
        return None


def _driven_map(rig):
    """핸들 → 실제 드라이버가 걸린 셰이프 키 목록 (캐시, TTL 2초)."""
    now = time.monotonic()
    if (_UI_CACHE.get("rig") == rig.name
            and now - _UI_CACHE.get("t", 0.0) < 2.0):
        return _UI_CACHE["driven"]
    driven = {}
    for kd0 in bpy.data.shape_keys:
        ad0 = kd0.animation_data
        if not (ad0 and ad0.drivers):
            continue
        for fc0 in ad0.drivers:
            dp0 = fc0.data_path
            if not dp0.startswith('key_blocks["'):
                continue
            kb0 = kd0.key_blocks.get(
                dp0[len('key_blocks["'):dp0.rfind('"]')])
            if kb0 is None:
                continue
            for var0 in fc0.driver.variables:
                h0 = next((t.bone_target for t in var0.targets
                           if str(t.bone_target).startswith("FP_ctl")),
                          None)
                if h0:
                    driven.setdefault(h0, []).append(kb0)
                    break
    _UI_CACHE.update({"driven": driven, "rig": rig.name, "t": now})
    return driven


def _redraw_ui(context):
    """N패널 등 뷰포트 UI 강제 갱신 (팝업 오퍼레이터 후 리드로우 누락 방지)."""
    try:
        for win in context.window_manager.windows:
            for area in win.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
    except Exception:
        pass


def _to_object_mode(context, rig):
    context.view_layer.objects.active = rig
    try:
        bpy.ops.object.mode_set(mode='OBJECT')
    except RuntimeError:
        pass


def _text_toggle_driver(scene, rig, ob):
    """텍스트 라벨을 ON/OFF 토글과 전역 라벨 토글에 연결."""
    if "FP_toggle" not in rig.data.bones:
        return
    try:
        ob.driver_remove("hide_viewport")
    except Exception:
        pass
    fc = ob.driver_add("hide_viewport")
    d = fc.driver
    d.type = 'SCRIPTED'
    d.expression = "(t>%s) or (lv<0.5)" % (TGL / 2)
    var = d.variables.new()
    var.name = "t"
    var.type = 'SINGLE_PROP'
    tg = var.targets[0]
    tg.id = rig
    tg.data_path = 'pose.bones["FP_toggle"].location[0]'
    var = d.variables.new()
    var.name = "lv"
    var.type = 'SINGLE_PROP'
    tg = var.targets[0]
    tg.id_type = 'SCENE'
    tg.id = scene
    tg.data_path = "fskr.labels_visible"


def _ensure_root(context, s, rig):
    need_root = "FP_root" not in rig.data.bones
    need_tgl = "FP_toggle" not in rig.data.bones
    if not (need_root or need_tgl):
        return
    if need_root:
        if s.panel_pos_set:
            # 크로스헤어로 지정한 위치 (월드 → 아마추어 공간)
            base = rig.matrix_world.inverted() @ Vector(s.panel_pos)
        else:
            if s.bone and s.bone in rig.data.bones:
                head_z = rig.data.bones[s.bone].head_local.z
            else:
                head_z = rig.dimensions.z * 0.85
            base = Vector((rig.dimensions.x * 0.5 + 0.25, 0.0,
                           head_z + 0.1))

    bpy.ops.object.mode_set(mode='EDIT')
    eb = rig.data.edit_bones
    if need_root:
        b = eb.new("FP_root")
        b.head = base
        b.tail = base + Vector((0, 0, 0.02))
        b.use_deform = False
    if need_tgl:
        rb = eb["FP_root"]
        pos = rb.head + Vector((0.22, 0.0, 0.0))  # 루트 바 오른쪽 끝

        def new(n, parent):
            bb = eb.new(n)
            bb.head = pos
            bb.tail = pos + Vector((0, 0, 0.02))
            bb.use_deform = False
            bb.parent = parent
            return bb

        tf = new("FP_toggle_frame", rb)
        new("FP_toggle", tf)
    bpy.ops.object.mode_set(mode='OBJECT')

    coll = _widget_coll(context)
    w_frame = _wire_square(coll, "WGT_FP_frame")
    w_handle = _wire_square(coll, "WGT_FP_handle", cross=True)
    if need_root:
        pb = rig.pose.bones["FP_root"]
        pb.custom_shape = w_frame
        pb.use_custom_shape_bone_size = False
        pb.custom_shape_scale_xyz = (0.36, 0.025, 1)
    if need_tgl:
        fb = rig.pose.bones["FP_toggle_frame"]
        fb.custom_shape = w_frame
        fb.use_custom_shape_bone_size = False
        fb.custom_shape_scale_xyz = (TGL + 0.025, 0.035, 1)
        fb.custom_shape_translation = (TGL / 2, 0, 0)
        rig.data.bones["FP_toggle_frame"].hide_select = True

        pb = rig.pose.bones["FP_toggle"]
        pb.custom_shape = w_handle
        pb.use_custom_shape_bone_size = False
        pb.custom_shape_scale_xyz = (0.014, 0.032, 1)
        pb.lock_location[2] = True
        pb.lock_rotation = (True, True, True)
        pb.lock_scale = (True, True, True)
        c = pb.constraints.new('LIMIT_LOCATION')
        c.owner_space = 'LOCAL'
        c.use_transform_limit = True
        for attr in ("use_min_x", "use_max_x", "use_min_y",
                     "use_max_y", "use_min_z", "use_max_z"):
            setattr(c, attr, True)
        c.min_x, c.max_x = 0.0, TGL
        c.min_y = c.max_y = c.min_z = c.max_z = 0.0
        _set_color(pb, True, (1.0, 0.35, 0.25))
        _set_color(fb, True, (1.0, 0.35, 0.25))


def _next_position(rig, spacing):
    """새 컨트롤러 배치 좌표: 화면에 보이는 패널 최상단 바로 위 (포즈 반영).

    레스트 위치가 아니라 실제 표시 위치 기준이라, 배치 모드로 옮겨도
    생성 지점이 위로 무한히 밀려나지 않음.
    """
    rootp = rig.pose.bones["FP_root"]
    rootb = rig.data.bones["FP_root"]
    tops = [rootp.matrix.translation.z]
    for pb in rig.pose.bones:
        if pb.name.startswith("FP_ctl") and pb.name.endswith("_frame"):
            tops.append(pb.matrix.translation.z)
        elif (pb.name.startswith(_VP_PREFIX)
              and "fskr_spr_top" in pb):
            # 스프라이트 격자 패드: 틀 원점 위로 라벨까지 차지
            tops.append(pb.matrix.translation.z
                        + float(pb.get("fskr_spr_top", 0.0)))
    high = max(tops)
    # 새 본은 FP_root의 자식이라 시각 위치 = 레스트 + 루트 포즈 오프셋
    off = rootp.matrix.translation - rootb.head_local
    rest = Vector((rootp.matrix.translation.x - off.x,
                   rootb.head_local.y,
                   high + spacing - off.z))
    return rest


def _next_ctl_name(rig):
    i = 0
    while ("FP_ctl_%03d" % i) in rig.data.bones:
        i += 1
    return "FP_ctl_%03d" % i


def _create_ctl_bones(rig, name, pos):
    bpy.ops.object.mode_set(mode='EDIT')
    eb = rig.data.edit_bones

    def new(n, parent=None):
        b = eb.new(n)
        b.head = pos
        b.tail = pos + Vector((0, 0, 0.02))
        b.use_deform = False
        if parent:
            b.parent = eb[parent]
        return b.name

    f = new(name + "_frame", "FP_root")
    new(name, f)
    bpy.ops.object.mode_set(mode='OBJECT')


def _apply_ctl(context, s, rig, name, cfg):
    """cfg로 컨트롤러(기존/신규)의 위젯·제한·드라이버·라벨·메타데이터를 설정."""
    mesh_nm = str(cfg.get("mesh", ""))
    mo = _resolve_mesh_name(mesh_nm, rig) if mesh_nm else None
    if mo is not None and (mo.type != 'MESH' or mo.data.shape_keys is None):
        mo = None  # 없어진/셰이프 키 없는 메시 → 설정 메시로 폴백
    mesh = mo or s.mesh
    keys = (mesh.data.shape_keys.key_blocks
            if mesh and mesh.data.shape_keys else None)
    ctype = cfg["ctype"]          # 'SLD_H' / 'SLD_V' / 'PAD'
    label = cfg["label"]

    # ----- 드라이버 식과 이동 제한 -----
    terms = {}  # shape key name -> [expr]
    inv = bool(cfg.get("invert"))
    bidir = False   # 최솟값<0 슬라이더: 양방향(중앙=0)
    snap_v = 0.0    # 스냅 임계값 (값 기준)
    drv_src = name  # 값 드라이버가 읽을 본 (패드 스냅 사용시 _out)

    def term(k, e):
        if k and k != NONE and keys and k in keys:
            terms.setdefault(k, []).append(e)

    def ensure_range(k, lo, hi):
        """셰이프 키 자체의 Range가 좁으면 드라이버 값이 잘리므로 자동 확장."""
        kb = keys.get(k) if (keys and k and k != NONE) else None
        if kb:
            if lo < kb.slider_min:
                kb.slider_min = lo
            if hi > kb.slider_max:
                kb.slider_max = hi

    bone_drv = None  # 본 패드: (대상 리그, 대상 본, 축 인덱스, 드라이버 식)
    chain_list = []  # 연쇄 드라이버 (슬라이더 전용)
    chain_expr = None
    if ctype == 'BONE':
        snap_v = float(cfg.get("snap", 0.0))
        rr = snap_v * PAD
        trig_nm = str(cfg.get("trig", ""))
        trig = bpy.data.objects.get(trig_nm) if trig_nm else rig
        if trig is None or trig.type != 'ARMATURE':
            trig = rig
        cfg["trig"] = trig.name  # 메타데이터에 실제 대상 리그 저장
        tbs = [t for t in (str(cfg.get("tb1", "")), str(cfg.get("tb2", "")))
               if t and t in trig.pose.bones and not t.startswith("FP_")]
        if not tbs:
            return False
        ax_h = {"X": 0, "Y": 1, "Z": 2}.get(str(cfg.get("bax", "X")), 0)
        ax_v = {"X": 0, "Y": 1, "Z": 2}.get(str(cfg.get("bay", "Z")), 2)
        bmode = str(cfg.get("bmode", "LOC"))
        gx = float(cfg.get("gx", 0.1))
        gy = float(cfg.get("gy", 0.1))
        if bmode == 'ROT':  # 각도(도) → 라디안
            from math import radians as _rad9
            gx = _rad9(gx)
            gy = _rad9(gy)
        flags = "1,1,1,1,0,0,0,0"
        ex_h = "fskr_pad(x,y,%s,%s,'X',%s)*%s" % (PAD, rr, flags, gx)
        ex_v = "fskr_pad(x,y,%s,%s,'Y',%s)*%s" % (PAD, rr, flags, gy)
        bone_drv = [(trig, t, ax_h, ex_h, bmode) for t in tbs]
        if ax_v != ax_h:
            bone_drv += [(trig, t, ax_v, ex_v, bmode) for t in tbs]
        xlim = (-PAD, PAD)
        ylim = (-PAD, PAD)
    elif ctype == 'PAD':
        up, down = cfg["up"], cfg["down"]
        left, right = cfg["left"], cfg["right"]
        ul, ur = cfg.get("ul", NONE), cfg.get("ur", NONE)
        dl, dr = cfg.get("dl", NONE), cfg.get("dr", NONE)
        snap_v = float(cfg.get("snap", 0.0))
        pmul = float(cfg.get("pmul", 1.0))
        rr = snap_v * PAD  # 앵커 스냅 반경 (핸들 이동 단위)

        def ok(k):
            return 1 if (k != NONE and keys and k in keys) else 0

        pair_y = (up != NONE and up == down)
        pair_x = (left != NONE and left == right)
        eu = 1 if pair_y else ok(up)
        ed = 1 if pair_y else ok(down)
        el = 1 if pair_x else ok(left)
        er = 1 if pair_x else ok(right)
        cul, cur = ok(ul), ok(ur)
        cdl, cdr = ok(dl), ok(dr)
        base_args = "x,y,%s,%s" % (PAD, rr)
        flags = "%d,%d,%d,%d,%d,%d,%d,%d" % (eu, ed, el, er,
                                             cul, cur, cdl, cdr)

        def slot_mul(sname):
            return pmul * float(cfg.get("pm_" + sname, 1.0))

        def padterm(k, slot, sname):
            m9 = slot_mul(sname)
            e = "fskr_pad(%s,'%s',%s)" % (base_args, slot, flags)
            if abs(m9 - 1.0) > 1e-9:
                e = "(%s)*%s" % (e, m9)
            term(k, e)
            ensure_range(k, min(0.0, m9), max(1.0, m9))

        if up != NONE and up == down:
            padterm(up, 'Y', "up")
            m9 = abs(slot_mul("up"))
            ensure_range(up, min(-1.0, -m9), max(1.0, m9))
        else:
            padterm(up, 'U', "up")
            padterm(down, 'D', "down")
        if left != NONE and left == right:
            padterm(left, 'X', "left")
            m9 = abs(slot_mul("left"))
            ensure_range(left, min(-1.0, -m9), max(1.0, m9))
        else:
            padterm(right, 'R', "right")
            padterm(left, 'L', "left")
        # 모서리(대각) 키: 인접 변과 자동 블렌딩 (없으면 변 키가 그대로 커버)
        padterm(ur, 'UR', "ur")
        padterm(ul, 'UL', "ul")
        padterm(dr, 'DR', "dr")
        padterm(dl, 'DL', "dl")

        has_l = any(k != NONE for k in (left, ul, dl))
        has_r = any(k != NONE for k in (right, ur, dr))
        has_u = any(k != NONE for k in (up, ul, ur))
        has_d = any(k != NONE for k in (down, dl, dr))
        xlim = (-PAD if has_l else 0.0, PAD if has_r else 0.0)
        ylim = (-PAD if has_d else 0.0, PAD if has_u else 0.0)
    else:  # SLD_H / SLD_V
        vmin = float(cfg.get("vmin", 0.0))
        vmax = float(cfg.get("vmax", 1.0))
        if vmax <= vmin:
            vmin, vmax = 0.0, 1.0
        snap_v = float(cfg.get("snap", 0.0))
        rr = snap_v * (SLD / 2)  # 앵커 스냅 반경 (핸들 이동 단위)
        ax = "y" if ctype == 'SLD_V' else "x"
        v = ("-" + ax) if inv else ax
        if vmin < 0.0:
            # 양방향: 원점=0, 한쪽 끝=최솟값, 반대쪽 끝=최댓값
            bidir = True
            half = SLD / 2
            if rr > 0.0:
                v = "fskr_ssnap(%s,%s,%s,0.0,%s)" % (v, rr, -half, half)
            expr = ("max(0,%s)/%s*%s+min(0,%s)/%s*%s"
                    % (v, half, vmax, v, half, -vmin))
            lim = (-half, half)
        else:
            # 단방향: 원점=최솟값, 끝=최댓값
            if rr > 0.0:
                v = "fskr_ssnap(%s,%s,0.0,%s,%s)" % (v, rr, SLD / 2, SLD)
            expr = "%s+(%s)/%s*%s" % (vmin, v, SLD, vmax - vmin)
            lim = (-SLD, 0.0) if inv else (0.0, SLD)
        term(cfg["key"], expr)
        ensure_range(cfg["key"], min(vmin, 0.0), max(vmax, 1.0))
        # 연쇄 드라이버: 이 슬라이더 값 × 배율로 따라가는 추가 셰이프 키
        ch = cfg.get("chain", [])
        if isinstance(ch, str):
            try:
                ch = json.loads(ch)
            except Exception:
                ch = []
        for ent in ch:
            k9 = str(ent.get("key", NONE))
            if not k9 or k9 == NONE:
                continue
            chain_list.append({"mesh": str(ent.get("mesh", "")),
                               "key": k9,
                               "f": float(ent.get("f", 1.0))})
        chain_expr = expr
        if ctype == 'SLD_V':
            xlim, ylim = (0.0, 0.0), lim
        else:
            xlim, ylim = lim, (0.0, 0.0)

    if not terms and ctype != 'BONE':
        return False

    # ----- 위젯 / 잠금 / 제한 -----
    coll = _widget_coll(context)
    w_frame = _wire_square(coll, "WGT_FP_frame")
    w_handle = _wire_square(coll, "WGT_FP_handle", cross=True)
    pbs = rig.pose.bones
    pb, fb = pbs[name], pbs[name + "_frame"]

    for old in list(pb.constraints):
        pb.constraints.remove(old)
    pb.location = (0.0, 0.0, 0.0)
    pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
    pb.scale = (1.0, 1.0, 1.0)
    rig.data.bones[name].hide = False
    rig.data.bones[name + "_frame"].hide = False

    # 틀 위젯 기준 크기 (드라이버가 이 상수를 기반으로 하므로 현재 값에서 읽지 않음)
    if ctype in ('PAD', 'BONE'):
        fsc = (2 * PAD + 0.03, 2 * PAD + 0.03, 1.0)
        ftr = (0.0, 0.0, 0.0)
    elif ctype == 'SLD_V':
        fsc = (0.04, SLD + 0.025, 1.0)
        ftr = (0.0, 0.0 if bidir else (-SLD / 2 if inv else SLD / 2), 0.0)
    else:
        fsc = (SLD + 0.025, 0.04, 1.0)
        ftr = (0.0 if bidir else (-SLD / 2 if inv else SLD / 2), 0.0, 0.0)
    fb.custom_shape = w_frame
    fb.use_custom_shape_bone_size = False
    fb.custom_shape_scale_xyz = fsc
    fb.custom_shape_translation = ftr

    pb.custom_shape = w_handle
    pb.use_custom_shape_bone_size = False
    if ctype in ('PAD', 'BONE'):
        pb.custom_shape_scale_xyz = (0.028, 0.028, 1)
    elif ctype == 'SLD_V':
        pb.custom_shape_scale_xyz = (0.036, 0.014, 1)
    else:
        pb.custom_shape_scale_xyz = (0.014, 0.036, 1)
    pb.lock_location[2] = True
    pb.lock_rotation = (True, True, True)
    pb.lock_scale = (True, True, True)

    # 배치 모드 상태에 맞는 선택 가능 여부
    arr9 = arrange_for(s, name)
    rig.data.bones[name + "_frame"].hide_select = not arr9
    rig.data.bones[name].hide_select = arr9

    c = pb.constraints.new('LIMIT_LOCATION')
    c.owner_space = 'LOCAL'
    c.use_transform_limit = True
    for attr in ("use_min_x", "use_max_x", "use_min_y",
                 "use_max_y", "use_min_z", "use_max_z"):
        setattr(c, attr, True)
    c.min_x, c.max_x = xlim
    c.min_y, c.max_y = ylim
    c.min_z = c.max_z = 0.0

    # ----- 스냅 표시용 헬퍼 본 (양방향 슬라이더 전용) -----
    thr = 0.0  # (구) 중앙 X/임계 틀 헬퍼 본 방식 폐지 — 오버레이 표시로 대체
    sn, tn = name + "_snap", name + "_thr"
    hpath = 'pose.bones["%s"].scale' % name
    spath = 'pose.bones["%s"].scale' % sn
    htpath = 'pose.bones["%s"].custom_shape_translation' % name
    for p in (hpath, spath, htpath):
        try:
            rig.driver_remove(p)
        except Exception:
            pass
    bpy.ops.object.mode_set(mode='EDIT')
    eb = rig.data.edit_bones
    if thr > 0.0:
        for n in (sn, tn):
            if n not in eb:
                b = eb.new(n)
                b.head = eb[name + "_frame"].head.copy()
                b.tail = b.head + Vector((0, 0, 0.02))
                b.use_deform = False
                b.parent = eb[name + "_frame"]
    else:
        for n in (sn, tn):
            if n in eb:
                eb.remove(eb[n])
    bpy.ops.object.mode_set(mode='OBJECT')
    pbs = rig.pose.bones
    pb, fb = pbs[name], pbs[name + "_frame"]  # 에딧 모드를 거쳤으므로 참조 갱신

    if thr > 0.0:
        axis_i = 1 if ctype == 'SLD_V' else 0
        raw = 'pose.bones["%s"].location[%d]' % (name, axis_i)
        sb, tb = pbs[sn], pbs[tn]
        for b2 in (sb, tb):
            b2.location = (0.0, 0.0, 0.0)
            b2.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
            b2.scale = (1.0, 1.0, 1.0)
        # 중앙 X 표시 (임계값 안일 때만 나타남)
        sb.custom_shape = w_handle
        sb.use_custom_shape_bone_size = False
        sb.custom_shape_scale_xyz = ((0.036, 0.014, 1) if ctype == 'SLD_V'
                                     else (0.014, 0.036, 1))
        # 임계값 구간 표시 (항상 표시)
        tb.custom_shape = w_frame
        tb.use_custom_shape_bone_size = False
        tb.custom_shape_scale_xyz = ((0.052, 2 * thr, 1) if ctype == 'SLD_V'
                                     else (2 * thr, 0.052, 1))
        rig.data.bones[sn].hide_select = True
        rig.data.bones[tn].hide_select = True

    # ----- 표시 드라이버 (스냅 표시 + ON/OFF 토글) -----
    tgl = "FP_toggle" in rig.data.bones
    tpath = 'pose.bones["FP_toggle"].location[0]'
    TH = TGL / 2

    def drv(path, exprs, vars_):
        try:
            rig.driver_remove(path)
        except Exception:
            pass
        for fc2 in rig.driver_add(path):
            d2 = fc2.driver
            d2.type = 'SCRIPTED'
            if isinstance(exprs, (list, tuple)):
                d2.expression = exprs[fc2.array_index]
            else:
                d2.expression = exprs
            for vn, dp in vars_:
                var2 = d2.variables.new()
                var2.name = vn
                var2.type = 'SINGLE_PROP'
                t2 = var2.targets[0]
                t2.id = rig
                t2.data_path = dp

    # 이전 버전(hide 드라이버) 잔재 제거
    for n2 in (name, name + "_frame", sn, tn):
        try:
            rig.data.driver_remove('bones["%s"].hide' % n2)
        except Exception:
            pass

    if thr > 0.0:
        if tgl:
            drv(spath, "(abs(v)<%s)*(t<%s)" % (thr, TH),
                [("v", raw), ("t", tpath)])
            drv(hpath, "(1-0.65*(abs(v)<%s))*(t<%s)" % (thr, TH),
                [("v", raw), ("t", tpath)])
            drv('pose.bones["%s"].scale' % tn, "t<%s" % TH,
                [("t", tpath)])
        else:
            drv(spath, "abs(v)<%s" % thr, [("v", raw)])
            drv(hpath, "1-0.65*(abs(v)<%s)" % thr, [("v", raw)])
    elif tgl:
        drv(hpath, "t<%s" % TH, [("t", tpath)])

    # 앵커 스냅: 스냅 중엔 핸들 X 표시가 앵커에 고정 (버텍스 스냅처럼)
    if ctype in ('PAD', 'BONE') and snap_v > 0.0:
        rawx = 'pose.bones["%s"].location[0]' % name
        rawy = 'pose.bones["%s"].location[1]' % name
        rr2 = snap_v * PAD
        drv(htpath,
            ["fskr_pofs(a,b,%s,%s,0)" % (PAD, rr2),
             "fskr_pofs(a,b,%s,%s,1)" % (PAD, rr2),
             "0.0"],
            [("a", rawx), ("b", rawy)])
    elif ctype in ('SLD_H', 'SLD_V') and snap_v > 0.0:
        axis_i = 1 if ctype == 'SLD_V' else 0
        raw1 = 'pose.bones["%s"].location[%d]' % (name, axis_i)
        rr3 = snap_v * (SLD / 2)
        if bidir:
            a3 = (-SLD / 2, 0.0, SLD / 2)
        elif inv:
            a3 = (0.0, -SLD / 2, -SLD)
        else:
            a3 = (0.0, SLD / 2, SLD)
        exprs3 = ["0.0", "0.0", "0.0"]
        exprs3[axis_i] = ("fskr_ssnap(v,%s,%s,%s,%s)-v"
                          % (rr3, a3[0], a3[1], a3[2]))
        drv(htpath, exprs3, [("v", raw1)])

    if tgl:
        # 틀은 위젯 표시 크기에 연결 (배치 모드의 본 스케일과 충돌 없음)
        drv('pose.bones["%s"].custom_shape_scale_xyz' % (name + "_frame"),
            ["%s*(t<%s)" % (b3, TH) for b3 in fsc],
            [("t", tpath)])

    # ----- 반전/범위 변경 보정: 스트립 중심은 제자리 유지 -----
    if ctype in ('SLD_H', 'SLD_V') and "fskr_type" in pb:
        prev_t = str(pb.get("fskr_type", ""))
        if prev_t == ctype:
            prev_inv = bool(pb.get("fskr_invert", 0))
            prev_bidir = float(pb.get("fskr_vmin", 0.0)) < 0.0

            def _center_off(bd, iv):
                # 스트립 중심의 원점 대비 오프셋 (본 로컬 축 기준)
                if bd:
                    return 0.0
                return -SLD / 2 if iv else SLD / 2

            d_off = (_center_off(prev_bidir, prev_inv)
                     - _center_off(bidir, inv))
            if abs(d_off) > 1e-9:
                i2 = 1 if ctype == 'SLD_V' else 0
                fb.location[i2] += d_off * fb.scale[i2]

    # ----- 색상 -----
    use_color = bool(cfg.get("use_color", False))
    color = tuple(cfg.get("color", (1.0, 0.85, 0.4)))[:3]
    pb["fskr_usecolor"] = 1 if use_color else 0
    pb["fskr_color"] = list(color)
    try:
        pb.fskr_col = color  # 값이 같으면 콜백이 안 오므로 아래에서 직접 적용
    except Exception:
        pass
    # 콜백에 의존하지 않고 핸들/틀/헬퍼 본에 즉시 반영
    _set_color(pb, use_color, color)
    for _suf9 in ("_frame", "_snap", "_thr"):
        _b9 = rig.pose.bones.get(pb.name + _suf9)
        if _b9:
            _set_color(_b9, use_color, color)

    pb["fskr_label"] = label
    pb["fskr_type"] = ctype
    pb["fskr_key"] = cfg.get("key", NONE)
    # 그룹이 컬렉션 목록에 없으면 자동 등록 (접기/펼치기용)
    grp2 = str(cfg.get("group", ""))
    if grp2 and grp2 not in [c2.name for c2 in s.collections]:
        item2 = s.collections.add()
        item2.name = grp2
    pb["fskr_invert"] = 1 if cfg.get("invert") else 0
    pb["fskr_vmin"] = float(cfg.get("vmin", 0.0))
    pb["fskr_vmax"] = float(cfg.get("vmax", 1.0))
    pb["fskr_snap"] = float(cfg.get("snap", 0.0))
    pb["fskr_pmul"] = float(cfg.get("pmul", 1.0))
    for _sl9 in ("up", "down", "left", "right", "ul", "ur", "dl", "dr"):
        pb["fskr_pm_" + _sl9] = float(cfg.get("pm_" + _sl9, 1.0))
    pb["fskr_usecolor"] = 1 if use_color else 0
    pb["fskr_color"] = list(color)
    pb["fskr_group"] = str(cfg.get("group", ""))
    if "fskr_order" not in pb:
        orders = [int(p.get("fskr_order", -1)) for p in pbs
                  if _is_handle_name(p.name)]
        pb["fskr_order"] = (max(orders) + 1) if orders else 0
    for d in ("up", "down", "left", "right", "ul", "ur", "dl", "dr"):
        pb["fskr_" + d] = cfg.get(d, NONE)
    # 컨트롤러별 메시 (비우면 설정의 얼굴 메시)
    pb["fskr_mesh"] = (mo.name if (mesh_nm and mo is not None)
                       else mesh_nm)
    try:  # ID 포인터: 개명/Append에도 참조 유지
        if mesh_nm and mo is not None:
            pb["fskr_mesh_ptr"] = mo
        elif "fskr_mesh_ptr" in pb:
            del pb["fskr_mesh_ptr"]
    except Exception:
        pass
    pb["fskr_chain"] = json.dumps(chain_list, ensure_ascii=False)
    # 본 패드 메타데이터
    pb["fskr_bmode"] = str(cfg.get("bmode", "LOC"))
    pb["fskr_trig"] = str(cfg.get("trig", ""))
    pb["fskr_tb1"] = str(cfg.get("tb1", ""))
    pb["fskr_tb2"] = str(cfg.get("tb2", ""))
    pb["fskr_bax"] = str(cfg.get("bax", "X"))
    pb["fskr_bay"] = str(cfg.get("bay", "Z"))
    pb["fskr_gx"] = float(cfg.get("gx", 0.1))
    pb["fskr_gy"] = float(cfg.get("gy", 0.1))

    # ----- 라벨: 컨트롤러 부착형은 폐지 (텍스트는 별도 오브젝트로 관리) -----
    old_lbl = bpy.data.objects.get("FPLBL_" + name)
    if old_lbl:
        bpy.data.objects.remove(old_lbl)

    # ----- 드라이버 -----
    _remove_drivers_for_bone(mesh, name, rig)
    _remove_bone_drivers_for(rig, name)
    for k, es in terms.items():
        _add_driver(keys[k], rig, name, "+".join(es))
    if chain_expr is not None:
        vmin9 = float(cfg.get("vmin", 0.0))
        vmax9 = float(cfg.get("vmax", 1.0))
        for ent in chain_list:
            mo9 = (_resolve_mesh_name(ent["mesh"], rig)
                   if ent["mesh"] else None) or mesh
            kb9 = (mo9.data.shape_keys.key_blocks.get(ent["key"])
                   if (mo9 and mo9.type == 'MESH'
                       and mo9.data.shape_keys) else None)
            if kb9 is None:
                continue
            f9 = ent["f"]
            lo9 = min(0.0, vmin9 * f9, vmax9 * f9)
            hi9 = max(0.0, vmin9 * f9, vmax9 * f9)
            if lo9 < kb9.slider_min:
                kb9.slider_min = lo9
            if hi9 > kb9.slider_max:
                kb9.slider_max = hi9
            _add_driver(kb9, rig, name,
                        "(%s)*%s" % (chain_expr, f9), chain=True)
    if bone_drv:
        done9 = set()
        used9 = {}
        for trig3, tb3, idx3, ex3, bm3 in bone_drv:
            k9 = (trig3.name, tb3)
            if k9 not in done9:
                done9.add(k9)
                _clear_bone_drivers(rig, name, trig3, tb3)
            used9.setdefault((trig3, tb3, bm3), set()).add(idx3)
        # 안 쓰는 축의 잔여 포즈 값 초기화 (옛 설정 흔적 제거)
        for (trig4, tb4, bm4), axes4 in used9.items():
            pb4 = trig4.pose.bones.get(tb4)
            if pb4 is None:
                continue
            for i4 in (0, 1, 2):
                try:
                    if bm4 == 'ROT':
                        pb4.location[i4] = 0.0
                        if i4 not in axes4:
                            pb4.rotation_euler[i4] = 0.0
                    else:
                        pb4.rotation_euler[i4] = 0.0
                        if i4 not in axes4:
                            pb4.location[i4] = 0.0
                except Exception:
                    pass
            try:
                if pb4.rotation_mode in ('QUATERNION', 'AXIS_ANGLE'):
                    pb4.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
            except Exception:
                pass
        for trig3, tb3, idx3, ex3, bm3 in bone_drv:
            _add_bone_axis_driver(rig, name, trig3, tb3, idx3, ex3,
                                  bm3)

    # 중간 처리에 덮이지 않도록 색상 최종 재적용
    try:
        pb["fskr_usecolor"] = 1 if use_color else 0
        pb["fskr_color"] = list(color)
        _set_color(pb, use_color, color)
        for _suf8 in ("_frame", "_snap", "_thr"):
            _b8 = rig.pose.bones.get(pb.name + _suf8)
            if _b8:
                _set_color(_b8, use_color, color)
    except Exception:
        pass

    context.view_layer.update()
    _invalidate_ui_cache()
    return True


def _copy_label_update(self, context):
    """라벨 옆 복사 버튼: 셰이프 키(또는 대상 본) 이름을 라벨로."""
    if not self.copy_label:
        return
    self.copy_label = False
    if str(getattr(self, "ctype", "")) == 'BONE':
        if getattr(self, "tb1", ""):
            self.label = self.tb1
        return
    k = str(getattr(self, "key", NONE))
    if k and k != NONE:
        self.label = k
        return
    for d in ("up", "down", "left", "right", "ul", "ur", "dl", "dr"):
        k = str(getattr(self, d, NONE))
        if k != NONE:
            self.label = k
            return


_enum_cache_k1 = []


_enum_cache_k2 = []


_enum_cache_k3 = []


def _shape_key_items_keep(self, context):
    global _enum_cache_k1
    return _stable_items("keysk",
                         [("__KEEP__", _tr("(변경 안 함)"), "")]
                         + list(_shape_key_items(self, context)))


def _mesh_items_keep(self, context):
    global _enum_cache_k2
    return _stable_items("meshk",
                         [("__KEEP__", _tr("(변경 안 함)"), "")]
                         + list(_mesh_items(self, context)))


def _armature_items_keep(self, context):
    global _enum_cache_k3
    return _stable_items("armk",
                         [("__KEEP__", _tr("(변경 안 함)"), "")]
                         + list(_armature_items(self, context)))


def _batch_sel(rig):
    """체크된 핸들 이름 목록과 타입 카테고리 집합."""
    sel = [b.name for b in rig.data.bones
           if _is_handle_name(b.name)
           and getattr(rig.pose.bones[b.name], "fskr_sel", False)]
    cats = set()
    for n in sel:
        t = str(rig.pose.bones[n].get("fskr_type", 'SLD_H'))
        cats.add('SLD' if t in ('SLD_H', 'SLD_V') else t)
    return sel, cats


def _mirror_plan(s, rig, bone):
    """미러 생성 계획을 만들고 검증. (plan, None) 또는 (None, 오류 문자열)."""
    mesh = s.mesh
    tl, tr = s.token_l, s.token_r
    pb = rig.pose.bones[bone]
    lbl0 = str(pb.get("fskr_label", bone))
    # 컨트롤러별 메시 (비어 있으면 설정 메시)
    mo7 = _ctl_mesh_get(pb)
    if not (mo7 and mo7.type == 'MESH' and mo7.data.shape_keys):
        mo7 = mesh

    # 미러 대상 메시: 메시 이름의 좌/우 짝이 있으면 그 메시에서 키를 찾고,
    # 없으면 같은 메시에서 찾음 (예: Eye Right → Eye Left)
    def _swap_obj_names(nm):
        for a, b in ((tl, tr), ("Left", "Right"),
                     ("left", "right"), ("LEFT", "RIGHT")):
            if not a or not b:
                continue
            for p, q in ((a, b), (b, a)):
                if p in nm and nm.replace(p, q) != nm:
                    yield nm.replace(p, q)
        for a, b in ((".l", ".r"), (".L", ".R"),
                     ("_l", "_r"), ("_L", "_R")):
            for p, q in ((a, b), (b, a)):
                if nm.endswith(p):
                    yield nm[:-len(p)] + q

    tgt_mo = None
    if mo7:
        for cand8 in _swap_obj_names(mo7.name):
            ob8 = bpy.data.objects.get(cand8)
            if ob8 and ob8.type == 'MESH' and ob8.data.shape_keys:
                tgt_mo = ob8
                break
    if tgt_mo is None:
        tgt_mo = mo7
    keys = (tgt_mo.data.shape_keys.key_blocks
            if tgt_mo and tgt_mo.data.shape_keys else {})
    mnm_t = ("" if (s.mesh and tgt_mo is s.mesh)
             else (tgt_mo.name if tgt_mo else ""))

    def swap(nm):
        if not nm or nm == NONE:
            return nm, False
        if tl in nm:
            return nm.replace(tl, tr), True
        if tr in nm:
            return nm.replace(tr, tl), True
        return nm, False

    cfg = {"ctype": str(pb.get("fskr_type", 'SLD_H')),
           "mesh": mnm_t,
           "invert": bool(pb.get("fskr_invert", 0)),
           "vmin": float(pb.get("fskr_vmin", 0.0)),
           "vmax": float(pb.get("fskr_vmax", 1.0)),
           "snap": float(pb.get("fskr_snap", 0.0)),
           "pmul": float(pb.get("fskr_pmul", 1.0)),
           "group": str(pb.get("fskr_group", "")),
           "use_color": bool(pb.get("fskr_usecolor", 0)),
           "color": tuple(pb.get("fskr_color", (1.0, 0.85, 0.4)))[:3]}
    # 실제 본에 칠해진 색을 우선 (스와치로 바꾼 색도 그대로 미러)
    try:
        if pb.color.palette == 'CUSTOM':
            cfg["use_color"] = True
            cfg["color"] = tuple(pb.color.custom.normal)[:3]
    except Exception:
        pass

    def find_key(nm):
        """정확히 없으면 공백/대소문자 차이를 무시하고 찾기."""
        if nm in keys:
            return nm
        t = nm.replace(" ", "").lower()
        for kb in keys:
            if kb.name.replace(" ", "").lower() == t:
                return kb.name
        return None

    swapped_any = False
    for prop in ("key", "up", "down", "left", "right",
                 "ul", "ur", "dl", "dr"):
        nm = str(pb.get("fskr_" + prop, NONE))
        new_nm, sw = swap(nm)
        if sw:
            swapped_any = True
            found = find_key(new_nm)
            if found is None:
                return None, (_tr("%s: 반대쪽 셰이프 키 '%s' 없음 (메시 '%s')")
                              % (lbl0, new_nm,
                                 tgt_mo.name if tgt_mo else "?"))
            new_nm = found
        cfg[prop] = new_nm
    # 방향별 배율도 복사
    for sl9 in ("up", "down", "left", "right", "ul", "ur", "dl", "dr"):
        cfg["pm_" + sl9] = float(pb.get("fskr_pm_" + sl9, 1.0))
    # 패드는 좌우 슬롯도 기하학적으로 미러 (배율 포함)
    if cfg["ctype"] == 'PAD':
        cfg["left"], cfg["right"] = cfg["right"], cfg["left"]
        cfg["ul"], cfg["ur"] = cfg["ur"], cfg["ul"]
        cfg["dl"], cfg["dr"] = cfg["dr"], cfg["dl"]
        cfg["pm_left"], cfg["pm_right"] = cfg["pm_right"], cfg["pm_left"]
        cfg["pm_ul"], cfg["pm_ur"] = cfg["pm_ur"], cfg["pm_ul"]
        cfg["pm_dl"], cfg["pm_dr"] = cfg["pm_dr"], cfg["pm_dl"]
    # 본 패드: 대상 본 이름의 좌/우 짝을 찾아 치환
    if cfg["ctype"] == 'BONE':
        trig = bpy.data.objects.get(str(pb.get("fskr_trig", "")))
        if trig is None or trig.type != 'ARMATURE':
            trig = rig

        def swap_bone(nm):
            if not nm:
                return nm, False
            for a, b in ((".l", ".r"), (".L", ".R"),
                         ("_l", "_r"), ("_L", "_R")):
                for p, q in ((a, b), (b, a)):
                    if nm.endswith(p):
                        cand = nm[:-len(p)] + q
                        if cand in trig.pose.bones:
                            return cand, True
            for a, b in (("Left", "Right"), ("left", "right"),
                         ("LEFT", "RIGHT"), (tl, tr)):
                if not a or not b:
                    continue
                for p, q in ((a, b), (b, a)):
                    if p in nm:
                        cand = nm.replace(p, q)
                        if cand != nm and cand in trig.pose.bones:
                            return cand, True
            return nm, False

        t1, s1 = swap_bone(str(pb.get("fskr_tb1", "")))
        t2, s2 = swap_bone(str(pb.get("fskr_tb2", "")))
        if not (s1 or s2):
            return None, (_tr("%s: 대상 본 '%s'의 좌/우 짝을 리그 '%s'에서 "
                          "찾지 못했습니다")
                          % (lbl0, str(pb.get("fskr_tb1", "")), trig.name))
        cfg["trig"] = trig.name
        cfg["tb1"], cfg["tb2"] = t1, t2
        bm9 = str(pb.get("fskr_bmode", "LOC")) or "LOC"
        cfg["bmode"] = bm9  # 구동 방식(위치/회전) 유지
        bax9 = str(pb.get("fskr_bax", "X"))
        bay9 = str(pb.get("fskr_bay", "Z"))
        cfg["bax"] = bax9
        cfg["bay"] = bay9

        cfg["gx"] = float(pb.get("fskr_gx", 0.1))
        cfg["gy"] = float(pb.get("fskr_gy", 0.1))
        swapped_any = True
    if not swapped_any:
        return None, (_tr("%s: 키 이름에서 '%s'/'%s'를 찾지 못했습니다")
                      % (lbl0, tl, tr))
    if cfg["ctype"] == 'BONE':
        # 본 패드: 미러된 대상 본 이름을 라벨로
        cfg["label"] = str(cfg.get("tb1", "")) or bone
    else:
        lbl, _sw = swap(str(pb.get("fskr_label", "")))
        cfg["label"] = lbl or bone

    # 연쇄 드라이버도 미러 (키/메시의 좌우 짝 검색)
    try:
        ch0 = json.loads(str(pb.get("fskr_chain", "[]")))
    except Exception:
        ch0 = []
    ch_out = []
    for ent in ch0:
        k9 = str(ent.get("key", NONE))
        if not k9 or k9 == NONE:
            continue
        em = str(ent.get("mesh", ""))
        src_m = bpy.data.objects.get(em) if em else None
        if not (src_m and src_m.type == 'MESH' and src_m.data.shape_keys):
            src_m = mo7
        tgt_m = None
        if src_m:
            for cand9 in _swap_obj_names(src_m.name):
                ob9 = bpy.data.objects.get(cand9)
                if ob9 and ob9.type == 'MESH' and ob9.data.shape_keys:
                    tgt_m = ob9
                    break
        if tgt_m is None:
            tgt_m = src_m
        kbl = (tgt_m.data.shape_keys.key_blocks
               if tgt_m and tgt_m.data.shape_keys else {})
        nk, sw9 = swap(k9)
        if sw9:
            found9 = nk if nk in kbl else None
            if found9 is None:
                t9 = nk.replace(" ", "").lower()
                for kb in kbl:
                    if kb.name.replace(" ", "").lower() == t9:
                        found9 = kb.name
                        break
            if found9 is None:
                return None, (_tr("%s: 연쇄 셰이프 키 '%s' 없음 (메시 '%s')")
                              % (lbl0, nk, tgt_m.name if tgt_m else "?"))
            nk = found9
        ch_out.append({"mesh": ("" if (s.mesh and tgt_m is s.mesh)
                                else (tgt_m.name if tgt_m else "")),
                       "key": nk, "f": float(ent.get("f", 1.0))})
    cfg["chain"] = ch_out

    # 위치: FP_root의 X를 축으로 미러
    src_f = bone + "_frame"
    root_x = rig.data.bones["FP_root"].head_local.x
    src_head = rig.data.bones[src_f].head_local
    x = 2 * root_x - src_head.x
    if cfg["ctype"] == 'SLD_H' and cfg["vmin"] >= 0.0:
        # 가로 슬라이더는 한쪽으로 뻗으므로 띠 전체가 미러되도록 보정
        x += SLD if cfg["invert"] else -SLD
    pos = Vector((x, src_head.y, src_head.z))

    # 배치 모드에서 옮긴 포즈 오프셋도 미러해서 복사
    src_pose = rig.pose.bones[src_f]
    return {"cfg": cfg, "pos": pos,
            "loc": (-src_pose.location[0], src_pose.location[1],
                    src_pose.location[2]),
            "rot": tuple(src_pose.rotation_quaternion),
            "scl": tuple(src_pose.scale)}, None


_enum_cache_txt = []


_enum_cache_pick = []


def _text_items(self, context):
    global _enum_cache_txt
    items = [("SEL", _tr("(선택된 텍스트)"), _tr("오브젝트 모드에서 선택한 텍스트에 적용"))]
    for o in bpy.data.objects:
        if o.name.startswith("FPLBL") and o.type == 'FONT':
            body = (o.data.body or o.name).strip()
            items.append((o.name, body[:24], ""))
    return _stable_items("txt", items)


def _pick_items(self, context):
    global _enum_cache_pick
    items = [(NONE, _tr("(직접 지정)"), _tr("아래 색상 필드로 직접 선택"))]
    s = context.scene.fskr
    if s.rig:
        for b in s.rig.data.bones:
            if _is_handle_name(b.name):
                pb = s.rig.pose.bones[b.name]
                if bool(pb.get("fskr_usecolor", 0)):
                    items.append((b.name,
                                  str(pb.get("fskr_label", b.name)), ""))
    return _stable_items("pick", items)


def _pick_update(self, context):
    """스포이드: 선택한 컨트롤러의 색을 색상 필드에 채움."""
    s = context.scene.fskr
    if self.pick_from != NONE and s.rig:
        pb = s.rig.pose.bones.get(self.pick_from)
        if pb is not None:
            self.color = tuple(pb.fskr_col)


def _text_set_color(ob, col):
    """텍스트 색 적용. Shift+D 복제로 공유된 데이터/머티리얼은 분리 후 적용."""
    data = ob.data
    if data.users > 1:
        data = data.copy()
        ob.data = data
    if data.materials and data.materials[0]:
        mat = data.materials[0]
        if mat.users > 1:
            mat = mat.copy()
            data.materials[0] = mat
    else:
        mat = bpy.data.materials.new("FPLBL_mat")
        data.materials.append(mat)
    mat.use_nodes = False
    mat.diffuse_color = (*col, 1.0)
    ob.color = (*col, 1.0)


def _read_meta(pb):
    """컨트롤러의 저장된 설정을 cfg 딕셔너리로."""
    return {
        "ctype": str(pb.get("fskr_type", 'SLD_H')),
        "label": str(pb.get("fskr_label", pb.name)),
        "key": str(pb.get("fskr_key", NONE)),
        "up": str(pb.get("fskr_up", NONE)),
        "down": str(pb.get("fskr_down", NONE)),
        "left": str(pb.get("fskr_left", NONE)),
        "right": str(pb.get("fskr_right", NONE)),
        "ul": str(pb.get("fskr_ul", NONE)),
        "ur": str(pb.get("fskr_ur", NONE)),
        "dl": str(pb.get("fskr_dl", NONE)),
        "dr": str(pb.get("fskr_dr", NONE)),
        "invert": bool(pb.get("fskr_invert", 0)),
        "vmin": float(pb.get("fskr_vmin", 0.0)),
        "vmax": float(pb.get("fskr_vmax", 1.0)),
        "snap": float(pb.get("fskr_snap", 0.0)),
        "pmul": float(pb.get("fskr_pmul", 1.0)),
        "pm_up": float(pb.get("fskr_pm_up", 1.0)),
        "pm_down": float(pb.get("fskr_pm_down", 1.0)),
        "pm_left": float(pb.get("fskr_pm_left", 1.0)),
        "pm_right": float(pb.get("fskr_pm_right", 1.0)),
        "pm_ul": float(pb.get("fskr_pm_ul", 1.0)),
        "pm_ur": float(pb.get("fskr_pm_ur", 1.0)),
        "pm_dl": float(pb.get("fskr_pm_dl", 1.0)),
        "pm_dr": float(pb.get("fskr_pm_dr", 1.0)),
        "group": str(pb.get("fskr_group", "")),
        "use_color": bool(pb.get("fskr_usecolor", 0)),
        "color": [float(c) for c in
                  tuple(pb.get("fskr_color", (1.0, 0.85, 0.4)))[:3]],
        "mesh": _mesh_meta_name(pb),
        "chain": str(pb.get("fskr_chain", "[]")),
        "bmode": str(pb.get("fskr_bmode", "LOC")),
        "trig": str(pb.get("fskr_trig", "")),
        "tb1": str(pb.get("fskr_tb1", "")),
        "tb2": str(pb.get("fskr_tb2", "")),
        "bax": str(pb.get("fskr_bax", "X")),
        "bay": str(pb.get("fskr_bay", "Z")),
        "gx": float(pb.get("fskr_gx", 0.1)),
        "gy": float(pb.get("fskr_gy", 0.1)),
    }


def _shader():
    try:
        return gpu.shader.from_builtin('UNIFORM_COLOR')
    except Exception:
        return gpu.shader.from_builtin('3D_UNIFORM_COLOR')


def _draw_cb(op):
    """모달 중 오버레이: 선택된 변 하이라이트 + 스냅된 모서리 네모 표시."""
    shader = _shader()
    gpu.state.line_width_set(3.0)
    lines = getattr(op, "hl_lines", None)
    if lines:
        batch = batch_for_shader(shader, 'LINES', {"pos": lines})
        shader.bind()
        shader.uniform_float("color", (1.0, 0.9, 0.1, 1.0))
        batch.draw(shader)
    pts = getattr(op, "snap_pts", None)
    if pts:
        segs = []
        r = 0.008
        ax9 = getattr(op, "snap_axes", None)
        if ax9 is not None:  # 패널 회전을 따라가는 축
            ex9, ez9 = ax9[0] * r, ax9[1] * r
        else:
            ex9, ez9 = Vector((r, 0, 0)), Vector((0, 0, r))
        for p in pts:
            c = [p - ex9 - ez9, p + ex9 - ez9,
                 p + ex9 + ez9, p - ex9 + ez9]
            segs += [c[0], c[1], c[1], c[2], c[2], c[3], c[3], c[0]]
        batch = batch_for_shader(shader, 'LINES', {"pos": segs})
        shader.bind()
        shader.uniform_float("color", (0.2, 1.0, 0.4, 1.0))
        batch.draw(shader)
    gpu.state.line_width_set(1.0)


def _panel_space(rig):
    """패널 공간: FP_root의 포즈 회전/이동을 반영한 좌표계.

    루트가 회전해 있어도 이 공간 안에서는 패널이 축 정렬 상태가
    되어 배치 모드 계산(화살표/스냅/크기 조절)이 그대로 성립한다.
    레스트 상태에서는 항등 행렬.
    """
    from mathutils import Matrix
    pb = rig.pose.bones.get("FP_root")
    if pb is None:
        return Matrix.Identity(4), Matrix.Identity(4)
    try:
        R = pb.matrix @ pb.bone.matrix_local.inverted()
        return R, R.inverted()
    except Exception:
        return Matrix.Identity(4), Matrix.Identity(4)


def _edge_arrows(pb):
    """틀 네 변의 중앙점/방향/수직 (armature space, 패널 회전 대응)."""
    rig = pb.id_data
    R, Rinv = _panel_space(rig)
    R3 = R.to_3x3()
    cs = [Rinv @ c for c in _frame_corners(pb)]
    x0 = min(c.x for c in cs)
    x1 = max(c.x for c in cs)
    z0 = min(c.z for c in cs)
    z1 = max(c.z for c in cs)
    y = cs[0].y
    xc, zc = (x0 + x1) / 2, (z0 + z1) / 2
    # 틀 크기에 비례한 화살표 크기 (너무 크거나 작지 않게 제한)
    size = max(0.004, min(0.012, 0.2 * min(x1 - x0, z1 - z0)))

    def mk9(px, py, pz, dx, dy, dz, qx, qy, qz):
        return (R @ Vector((px, py, pz)),
                (R3 @ Vector((dx, dy, dz))).normalized(),
                (R3 @ Vector((qx, qy, qz))).normalized())

    arrows = {
        'X1': mk9(x1, y, zc, 1, 0, 0, 0, 0, 1),
        'X0': mk9(x0, y, zc, -1, 0, 0, 0, 0, 1),
        'Z1': mk9(xc, y, z1, 0, 0, 1, 1, 0, 0),
        'Z0': mk9(xc, y, z0, 0, 0, -1, 1, 0, 0),
    }
    return arrows, size


def _draw_all_arrows(s):
    """배치 모드: 모든 컨트롤러 틀의 네 변에 삼각형 (선택하지 않아도 보임).
    잡으면 크기 조절, 크기 고정 틀은 잡는 동안 빨간색."""
    rig = s.rig
    mw = rig.matrix_world
    shader = _shader()
    gpu.state.blend_set('ALPHA')
    norm, red = [], []
    for pb in _vp_frames(rig):
        try:
            if rig.data.bones[pb.name].hide or \
                    pb.custom_shape_scale_xyz[0] < 1e-6:
                continue      # 숨긴 컨트롤러 (토글로 접음 등)
        except Exception:
            pass
        arrows, size = _edge_arrows(pb)
        tris = []
        for ap, d, perp in arrows.values():
            base = ap - d * (size * 0.5)  # 변 중앙에 걸치도록
            tip = ap + d * (size * 0.5)
            tris += [mw @ (base + perp * (size * 0.45)),
                     mw @ (base - perp * (size * 0.45)),
                     mw @ tip]
        (red if _ARROW_BLOCK.get("name") == pb.name else norm).extend(tris)
    for tris, col in ((norm, (1.0, 0.85, 0.1, 0.9)),
                      (red, (1.0, 0.18, 0.15, 0.95))):
        if tris:
            batch = batch_for_shader(shader, 'TRIS', {"pos": tris})
            shader.bind()
            shader.uniform_float("color", col)
            batch.draw(shader)
    gpu.state.blend_set('NONE')


def _draw_arrows():
    """선택된 컨트롤러의 오버레이: 배치 모드 화살표 + 패드 스냅 앵커 표시."""
    if not _is_owner():
        return
    ctx = bpy.context
    s = getattr(ctx.scene, "fskr", None)
    if not (s and s.rig) or ctx.mode != 'POSE':
        return
    if s.arrange:
        try:
            _draw_all_arrows(s)
        except Exception:
            pass
    ab = ctx.active_pose_bone
    if ab is None:
        return
    fname = _vp_frame_name(s.rig, ab.name)
    if not fname:
        return
    pb = s.rig.pose.bones.get(fname)
    hb = s.rig.pose.bones.get(fname[:-len("_frame")])
    if pb is None or hb is None:
        return
    mw = s.rig.matrix_world
    shader = _shader()
    gpu.state.blend_set('ALPHA')

    # 배치 모드: 변 크기 조절 화살표. 크기 고정 틀(입 등)도 배치 모드임을
    # 알 수 있게 그리되, 잡으면 빨간색이 되고 크기는 바뀌지 않음

    # 스냅 앵커 표시: 패드(9개) / 슬라이더(시작·중간·끝) 공통
    snap = float(hb.get("fskr_snap", 0.0))
    htype = str(hb.get("fskr_type", ""))
    if snap > 0.0 and htype in ('PAD', 'BONE', 'SLD_H', 'SLD_V'):
        m = pb.matrix  # 틀 기준 좌표계 (스케일 포함)
        o = m.translation
        exv = m.col[0].xyz
        eyv = m.col[1].xyz
        segs = []
        green = []

        def quad(cx, cy, hx, hy, buf):
            pts = [o + exv * (cx - hx) + eyv * (cy - hy),
                   o + exv * (cx + hx) + eyv * (cy - hy),
                   o + exv * (cx + hx) + eyv * (cy + hy),
                   o + exv * (cx - hx) + eyv * (cy + hy)]
            pts = [mw @ p4 for p4 in pts]
            buf += [pts[0], pts[1], pts[1], pts[2],
                    pts[2], pts[3], pts[3], pts[0]]

        if htype in ('PAD', 'BONE'):
            rr = snap * PAD
            # 셰이프 키를 직접 넣은 앵커만 연두색 (본 패드는 전부 유효)
            slot_map = {(-PAD, PAD): "ul", (0.0, PAD): "up",
                        (PAD, PAD): "ur", (-PAD, 0.0): "left",
                        (PAD, 0.0): "right", (-PAD, -PAD): "dl",
                        (0.0, -PAD): "down", (PAD, -PAD): "dr"}
            cands = []
            for ax2 in (-PAD, 0.0, PAD):
                for ay2 in (-PAD, 0.0, PAD):
                    cands.append((ax2, ay2))
                    sl = slot_map.get((ax2, ay2))
                    ok2 = (htype == 'BONE'
                           or (sl is not None
                               and str(hb.get("fskr_" + sl, NONE)) != NONE))
                    quad(ax2, ay2, rr, rr, green if ok2 else segs)
        else:
            rr = snap * (SLD / 2)
            inv2 = bool(hb.get("fskr_invert", 0))
            bidir2 = float(hb.get("fskr_vmin", 0.0)) < 0.0
            if bidir2:
                pts3 = (-SLD / 2, 0.0, SLD / 2)
                full = (pts3[0], pts3[2])
            elif inv2:
                pts3 = (0.0, -SLD / 2, -SLD)
                full = (pts3[2],)
            else:
                pts3 = (0.0, SLD / 2, SLD)
                full = (pts3[2],)
            vert = htype == 'SLD_V'
            cands = []
            for t3 in pts3:
                cx, cy = (0.0, t3) if vert else (t3, 0.0)
                cands.append((cx, cy))
                quad(cx, cy, rr, rr, green if t3 in full else segs)

        gpu.state.line_width_set(2.0)
        if segs:
            batch = batch_for_shader(shader, 'LINES', {"pos": segs})
            shader.bind()
            shader.uniform_float("color", (1.0, 0.25, 0.2, 0.9))
            batch.draw(shader)
        if green:
            batch = batch_for_shader(shader, 'LINES', {"pos": green})
            shader.bind()
            shader.uniform_float("color", (0.4, 1.0, 0.3, 0.9))
            batch.draw(shader)

        # 스냅 중이면 스냅된 앵커에 노란 사각형 (핸들 X 외곽)
        lx, ly = hb.location[0], hb.location[1]
        best = None
        bd = rr
        for cx, cy in cands:
            d = ((lx - cx) ** 2 + (ly - cy) ** 2) ** 0.5
            if d < bd:
                bd = d
                best = (cx, cy)
        if best is not None:
            ys = []
            quad(best[0], best[1], 0.022, 0.022, ys)
            gpu.state.line_width_set(3.0)
            batch = batch_for_shader(shader, 'LINES', {"pos": ys})
            shader.bind()
            shader.uniform_float("color", (1.0, 0.9, 0.1, 1.0))
            batch.draw(shader)
        gpu.state.line_width_set(1.0)

    gpu.state.blend_set('NONE')


def _draw_help_text():
    """배치 모드일 때 뷰포트 좌측 하단에 단축키 안내 표시."""
    if not _is_owner():
        return
    ctx = bpy.context
    s = getattr(ctx.scene, "fskr", None)
    if not (s and s.arrange and s.rig) or ctx.mode != 'POSE':
        return
    who9 = ""
    lines = (
        _tr("[배치 모드]") + ("  " + who9 if who9 else ""),
        _tr("G: 이동  (Ctrl = 모서리/중앙 스냅)"),
        _tr("노란 화살표 드래그: 변 크기 조절  (Ctrl = 스냅, Alt = 대칭)"),
        _tr("R / S: 회전 / 크기"),
        _tr("조작 중: 확정 = 클릭 · 취소 = 우클릭/ESC"),
        _tr("배치 모드 끄기: ESC 또는 우클릭 (조작 중이 아닐 때)"),
    )
    try:
        scale = ctx.preferences.system.ui_scale
    except Exception:
        scale = 1.0
    font_id = 0
    try:
        blf.size(font_id, int(13 * scale))
    except TypeError:  # Blender 3.x
        blf.size(font_id, int(13 * scale), 72)
    x = int(20 * scale)
    y = int(20 * scale)
    # 헤더/툴 헤더가 아래에 붙어 있으면(겹침 영역) 그 위로 올림
    try:
        for rg in ctx.area.regions:
            if rg.type in ('HEADER', 'TOOL_HEADER') and \
                    getattr(rg, "alignment", '') == 'BOTTOM' and rg.height > 1:
                y += rg.height
    except Exception:
        pass
    lh = int(19 * scale)
    blf.color(font_id, 1.0, 0.85, 0.3, 1.0)
    try:
        blf.enable(font_id, blf.SHADOW)
        blf.shadow(font_id, 3, 0.0, 0.0, 0.0, 0.8)
        blf.shadow_offset(font_id, 1, -1)
    except Exception:
        pass
    for i, ln in enumerate(reversed(lines)):
        blf.position(font_id, x, y + i * lh, 0)
        blf.draw(font_id, ln)
    try:
        blf.disable(font_id, blf.SHADOW)
    except Exception:
        pass


_MOCAP = {"sock": None, "ip": "", "vals": {}, "err": "", "hs": 0,
          "ok": False, "head": None, "blend": None,
          "neutral": {}, "neutral_head": None, "cvals": {},
          "eyeL": None, "eyeR": None, "neutral_eyes": None,
          "cd_end": None}


def _mocap_corr(vals):
    """캘리브레이션 보정: 무표정 값을 0으로 재배율."""
    neu = _MOCAP.get("neutral") or {}
    if not neu:
        return vals
    out = {}
    for k, v in vals.items():
        n = float(neu.get(k, 0.0))
        out[k] = max(0.0, min(1.5, (v - n) / max(0.2, 1.0 - n)))
    return out


def _mocap_stop_sock():
    sock = _MOCAP.get("sock")
    if sock is not None:
        try:
            sock.close()
        except Exception:
            pass
    _MOCAP["sock"] = None
    _MOCAP["ok"] = False


def _mocap_handshake():
    sock = _MOCAP.get("sock")
    ip = _MOCAP.get("ip", "")
    if sock is None or not ip:
        return
    try:
        sock.sendto(
            b"iFacialMocap_sahuasouryya9218sauhuiayeta91555dy3719",
            (ip, 49983))
    except Exception as e:
        _MOCAP["err"] = str(e)


def _mocap_parse(txt):
    """iFacialMocap UDP 패킷 파싱 (v1/v2 이름 모두)."""
    vals = _MOCAP["vals"]
    for tok in txt.split("|"):
        if not tok:
            continue
        if "#" in tok:
            # 머리 회전: "=head#피치,요,롤,x,y,z" (도 단위)
            nm2, _sep2, sv2 = tok.partition("#")
            nm3 = nm2.lstrip("=")
            if nm3 == "head":
                try:
                    parts = [float(x) for x in sv2.split(",")]
                    if len(parts) >= 3:
                        _MOCAP["head"] = parts[:3]
                        _MOCAP["ok"] = True
                except ValueError:
                    pass
            elif nm3 in ("rightEye", "leftEye"):
                # 눈알 회전 (피치, 요) — 시선 본에 사용
                try:
                    parts = [float(x) for x in sv2.split(",")]
                    if len(parts) >= 2:
                        key3 = "eyeR" if nm3 == "rightEye" else "eyeL"
                        _MOCAP[key3] = parts[:3]
                except ValueError:
                    pass
            continue
        if tok.startswith("="):
            continue
        nm, sep, sv = tok.rpartition("-")
        if not sep or not nm:
            continue
        canon = _AK_ALIAS.get(_ak_norm(nm))
        if canon is None:
            continue
        try:
            vals[_ak_norm(canon)] = float(sv) / 100.0
            _MOCAP["ok"] = True
        except ValueError:
            pass


def _mocap_virtual(vals):
    """ARKit 조합으로 입모양 A/I/U/E/O 가상 채널 계산."""
    def g(n):
        return vals.get(_ak_norm(n), 0.0)

    jaw = g("jawOpen")
    fun = g("mouthFunnel")
    puk = g("mouthPucker")
    smi = (g("mouthSmileLeft") + g("mouthSmileRight")) / 2.0
    st = (g("mouthStretchLeft") + g("mouthStretchRight")) / 2.0

    def cl(x):
        return max(0.0, min(1.0, x))

    a = cl(jaw - 0.5 * fun - 0.5 * puk)
    i = cl(max(smi, st) * (1.0 - jaw))
    u = cl(puk * (1.0 - 0.5 * jaw))
    e = cl(0.8 * jaw * max(smi, st))
    o = cl(fun * (0.4 + 0.6 * jaw))
    tot = a + i + u + e + o
    if tot > 1.0:  # 모음끼리 겹치면 비율로 정규화
        a, i, u, e, o = (x / tot for x in (a, i, u, e, o))
    return {'_A': a, '_I': i, '_U': u, '_E': e, '_O': o}


def _mocap_apply(s, rig):
    vals = _mocap_corr(_MOCAP["vals"])
    _MOCAP["cvals"] = vals  # 미리보기용 (보정 반영)
    if not vals:
        return
    ext = _mocap_virtual(vals)
    acc = {}       # 패널 대상: 핸들 → [x, y]
    key_acc = {}   # 셰이프 키 대상: 키블록 → 값
    for it in s.mocap_map:
        if it.arkit.startswith('_'):
            v = ext.get(it.arkit)
        else:
            v = vals.get(_ak_norm(it.arkit))
        if v is None:
            continue
        v = max(-1.5, min(1.5, v * it.factor))
        if it.tgt == 'KEY':
            # 셰이프 키 직접 구동 (패널 컨트롤러 불필요)
            nm = str(it.mesh)
            mo = (bpy.data.objects.get(nm)
                  if nm and nm != "__DEF__" else s.mesh)
            kb = (mo.data.shape_keys.key_blocks.get(it.key)
                  if (mo and mo.type == 'MESH'
                      and mo.data.shape_keys) else None)
            if kb is not None and it.key != NONE:
                key_acc[kb] = key_acc.get(kb, 0.0) + v
            continue
        pb = rig.pose.bones.get(it.ctl)
        if pb is None:
            continue
        ctype = str(pb.get("fskr_type", 'SLD_H'))
        e = acc.setdefault(it.ctl, [0.0, 0.0])
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
            e[axis] += sign * v * full
        elif c == 'XP':
            e[0] += v * PAD
        elif c == 'XN':
            e[0] -= v * PAD
        elif c == 'YP':
            e[1] += v * PAD
        elif c == 'YN':
            e[1] -= v * PAD
    # 머리/목 회전 대상
    hb = None
    hob = s.mocap_head_rig
    if hob and hob.type == 'ARMATURE' and s.mocap_head_bone:
        hb = hob.pose.bones.get(s.mocap_head_bone)
    hd = _MOCAP.get("head")
    nh = _MOCAP.get("neutral_head")
    if hd is not None and nh:
        hd = [hd[i4] - nh[i4] for i4 in range(3)]  # 머리도 중립 보정
    if not acc and not key_acc and (hb is None or hd is None):
        return
    sm = float(s.mocap_smooth)
    rec = bool(s.mocap_record)
    playing = False
    if rec:
        try:
            scr = bpy.context.screen
            playing = bool(scr and scr.is_animation_playing)
        except Exception:
            playing = False
    for h, (x, y) in acc.items():
        pb = rig.pose.bones[h]
        pb.location[0] = pb.location[0] * sm + x * (1.0 - sm)
        pb.location[1] = pb.location[1] * sm + y * (1.0 - sm)
        if rec and playing:
            pb.keyframe_insert("location",
                               group=str(pb.get("fskr_label", h)))
    for kb, val in key_acc.items():
        kb.value = kb.value * sm + val * (1.0 - sm)
        if rec and playing:
            kb.keyframe_insert("value")
    # 머리/목 회전 적용 (피치→X, 요→Y, 롤→Z, 본 로컬 기준)
    if hb is not None and hd is not None:
        g = float(s.mocap_head_gain)
        if hb.rotation_mode == 'QUATERNION' or hb.rotation_mode == 'AXIS_ANGLE':
            hb.rotation_mode = 'XYZ'
        # 축 리매핑: 끄덕임/돌림/갸웃 → 사용자가 고른 본 로컬 축 (+반전)
        idxm = {"X": 0, "Y": 1, "Z": 2}
        tgtr = [0.0, 0.0, 0.0]
        for v9, ax9, inv9 in (
                (hd[0], s.mocap_head_ax_p, s.mocap_head_inv_p),
                (hd[1], s.mocap_head_ax_y, s.mocap_head_inv_y),
                (hd[2], s.mocap_head_ax_r, s.mocap_head_inv_r)):
            tgtr[idxm.get(str(ax9), 0)] += (radians(v9 * g)
                                            * (-1.0 if inv9 else 1.0))
        for i3 in range(3):
            hb.rotation_euler[i3] = (hb.rotation_euler[i3] * sm
                                     + tgtr[i3] * (1.0 - sm))
        if rec and playing:
            hb.keyframe_insert("rotation_euler")


def _draw_mocap_preview():
    """뷰포트 좌상단에 수신 중인 표정을 도식으로 표시 (보정 반영)."""
    if not _is_owner():
        return
    ctx = bpy.context
    s = getattr(ctx.scene, "fskr", None)
    if s is None or not getattr(s, "mocap_preview", False):
        return
    if _MOCAP.get("sock") is None:
        return
    region = ctx.region
    if region is None or ctx.area is None or ctx.area.type != 'VIEW_3D':
        return
    cv = _MOCAP.get("cvals") or {}

    def g(n):
        return cv.get(_ak_norm(n), 0.0)

    shader = _shader()
    gpu.state.blend_set('ALPHA')
    sc = float(getattr(s, "mocap_preview_scale", 1.6))
    W0, H0 = 190.0, 150.0
    W, H = W0 * sc, H0 * sc
    # N패널 바로 왼쪽, 우측 하단에 표시
    ui_w = 0
    try:
        for r2 in ctx.area.regions:
            if r2.type == 'UI':
                ui_w = r2.width
                break
    except Exception:
        pass
    bx = max(10.0, region.width - ui_w - W - 20.0)
    by = 20.0

    def P(x, y):
        return (bx + x * sc, by + y * sc)

    quad = [P(0, 0), P(W0, 0), P(W0, H0), P(0, H0)]
    batch = batch_for_shader(shader, 'TRIS',
                             {"pos": [quad[0], quad[1], quad[2],
                                      quad[0], quad[2], quad[3]]})
    shader.bind()
    shader.uniform_float("color", (0.0, 0.0, 0.0, 0.35))
    batch.draw(shader)

    lines = []

    def ellipse(cx2, cy2, rx, ry, seg=20):
        prev = None
        for i2 in range(seg + 1):
            a2 = 6.28318 * i2 / seg
            p2 = P(cx2 + rx * cos(a2), cy2 + ry * sin(a2))
            if prev is not None:
                lines.extend([prev, p2])
            prev = p2

    cx = W0 / 2.0
    cy = H0 - 55.0
    ext = _mocap_virtual(cv)
    for sd, ex in ((-1, "Left"), (1, "Right")):
        ec = (cx + sd * 34.0, cy)
        blink = max(0.0, min(1.0, g("eyeBlink" + ex)))
        ellipse(ec[0], ec[1], 16.0, 9.0)
        lidy = ec[1] + 9.0 - 16.2 * blink
        lines.extend([P(ec[0] - 14.0, lidy), P(ec[0] + 14.0, lidy)])
        lookx = (g("eyeLookIn" + ex) - g("eyeLookOut" + ex)) * (-sd)
        looky = g("eyeLookUp" + ex) - g("eyeLookDown" + ex)
        ellipse(ec[0] + lookx * 8.0, ec[1] + looky * 5.0, 2.5, 2.5, 8)
        brow = (g("browOuterUp" + ex) + g("browInnerUp") * 0.5
                - g("browDown" + ex))
        byy = ec[1] + 14.0 + brow * 6.0
        lines.extend([P(ec[0] - 13.0, byy), P(ec[0] + 13.0, byy)])
    a9, i9, u9, e9, o9 = (ext['_A'], ext['_I'], ext['_U'],
                          ext['_E'], ext['_O'])
    jaw = g("jawOpen")
    mw = 24.0 * (1.0 + 0.5 * (i9 + e9) - 0.45 * (u9 + o9))
    mh = 3.0 + 24.0 * max(a9, jaw * 0.8, o9 * 0.6)
    ellipse(cx, cy - 40.0, max(6.0, mw), mh * 0.5)
    if lines:
        gpu.state.line_width_set(max(1.0, 1.2 * sc))
        batch = batch_for_shader(shader, 'LINES', {"pos": lines})
        shader.bind()
        shader.uniform_float("color", (0.9, 0.9, 0.9, 0.9))
        batch.draw(shader)
    # 모음 바 (A/I/U/E/O)
    bars = []
    labels = (('A', a9), ('I', i9), ('U', u9), ('E', e9), ('O', o9))
    bx0 = 14.0
    for k9, (_nm9, v9) in enumerate(labels):
        x0 = bx0 + k9 * 34.0
        h9 = 16.0 * max(0.0, min(1.0, v9))
        if h9 > 0.5:
            bars.extend([P(x0, 10.0), P(x0 + 8.0, 10.0),
                         P(x0 + 8.0, 10.0 + h9),
                         P(x0, 10.0), P(x0 + 8.0, 10.0 + h9),
                         P(x0, 10.0 + h9)])
    if bars:
        batch = batch_for_shader(shader, 'TRIS', {"pos": bars})
        shader.bind()
        shader.uniform_float("color", (0.4, 0.8, 1.0, 0.9))
        batch.draw(shader)
    gpu.state.line_width_set(1.0)
    gpu.state.blend_set('NONE')
    try:
        fs = max(9, int(10 * sc))
        try:
            blf.size(0, fs)
        except TypeError:
            blf.size(0, fs, 72)
        blf.color(0, 0.9, 0.9, 0.9, 1.0)
        for k9, (nm9, _v9) in enumerate(labels):
            px9, py9 = P(bx0 + k9 * 34.0 + 12.0, 10.0)
            blf.position(0, px9, py9, 0)
            blf.draw(0, nm9)
        hd = _MOCAP.get("head")
        nh = _MOCAP.get("neutral_head")
        if hd:
            h2 = list(hd)
            if nh:
                h2 = [h2[i2] - nh[i2] for i2 in range(3)]
            px9, py9 = P(10.0, H0 - 16.0)
            blf.position(0, px9, py9, 0)
            blf.draw(0, "head %d / %d / %d" % (h2[0], h2[1], h2[2]))
        if _MOCAP.get("neutral"):
            px9, py9 = P(W0 - 36.0, H0 - 16.0)
            blf.position(0, px9, py9, 0)
            blf.draw(0, "CAL")
    except Exception:
        pass


def _preset_blend_start(rig, targets, dur):
    """프리셋 블렌딩 시작. targets: {핸들이름: (x, y)}."""
    import time as _t
    st = {}
    for h, (tx, ty) in targets.items():
        pb = rig.pose.bones.get(h)
        if pb is None:
            continue
        st[h] = (pb.location[0], pb.location[1], tx, ty)
    if not st:
        return
    if dur <= 0.0:
        for h, (_sx, _sy, tx, ty) in st.items():
            pb = rig.pose.bones[h]
            pb.location[0], pb.location[1] = tx, ty
        return
    _MOCAP["blend"] = {"rig": rig.name, "items": st,
                       "t0": _t.time(), "dur": dur}
    if _MOCAP.get("sock") is None:
        # 캡처 중이 아니면 블렌딩 전용 타이머로 진행
        try:
            bpy.app.timers.register(_blend_tick, first_interval=0.02)
        except Exception:
            pass


def _blend_step(rec_playing=False):
    """진행 중인 블렌딩 한 스텝 (완료되면 True)."""
    import time as _t
    b = _MOCAP.get("blend")
    if not b:
        return True
    rig = bpy.data.objects.get(b["rig"])
    if rig is None:
        _MOCAP["blend"] = None
        return True
    p = (_t.time() - b["t0"]) / b["dur"]
    done = p >= 1.0
    p = max(0.0, min(1.0, p))
    p = p * p * (3.0 - 2.0 * p)  # smoothstep
    for h, (sx, sy, tx, ty) in b["items"].items():
        pb = rig.pose.bones.get(h)
        if pb is None:
            continue
        pb.location[0] = sx + (tx - sx) * p
        pb.location[1] = sy + (ty - sy) * p
        if rec_playing:
            pb.keyframe_insert("location",
                               group=str(pb.get("fskr_label", pb.name)))
    if done:
        _MOCAP["blend"] = None
    return done


def _blend_tick():
    done = _blend_step()
    try:
        for win in bpy.context.window_manager.windows:
            for area in win.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
    except Exception:
        pass
    return None if done else 0.02


def _start_playback():
    """타이머 컨텍스트에서 안전하게 애니메이션 재생 시작."""
    try:
        wm = bpy.context.window_manager
        for win in wm.windows:
            scr = win.screen
            if not getattr(scr, "is_animation_playing", False):
                with bpy.context.temp_override(window=win, screen=scr):
                    bpy.ops.screen.animation_play()
                return True
    except Exception:
        pass
    try:
        bpy.ops.screen.animation_play()
        return True
    except Exception:
        return False


def _cd_tick():
    """녹화 카운트다운 타이머."""
    end = _MOCAP.get("cd_end")
    if not end:
        return None
    try:
        for win in bpy.context.window_manager.windows:
            for area in win.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
    except Exception:
        pass
    if time.monotonic() >= end:
        _MOCAP["cd_end"] = None
        try:
            sc9 = bpy.context.scene
            sc9.frame_current = sc9.frame_start
        except Exception:
            pass
        _start_playback()
        return None
    return 0.05


def _draw_countdown():
    """카운트다운 중 뷰포트 중앙에 남은 초 표시."""
    if not _is_owner():
        return
    end = _MOCAP.get("cd_end")
    if not end:
        return
    ctx = bpy.context
    if ctx.area is None or ctx.area.type != 'VIEW_3D' or ctx.region is None:
        return
    rem = end - time.monotonic()
    if rem <= 0:
        return
    txt = "%d" % (int(rem) + 1)
    region = ctx.region
    try:
        fs = 120
        try:
            blf.size(0, fs)
        except TypeError:
            blf.size(0, fs, 72)
        w9, h9 = blf.dimensions(0, txt)
        blf.position(0, region.width / 2 - w9 / 2,
                     region.height / 2 - h9 / 2, 0)
        blf.color(0, 1.0, 0.35, 0.25, 0.95)
        blf.draw(0, txt)
    except Exception:
        pass


def _stop_playback():
    """타이머 컨텍스트에서 안전하게 애니메이션 재생 정지."""
    try:
        wm = bpy.context.window_manager
        for win in wm.windows:
            scr = win.screen
            if getattr(scr, "is_animation_playing", False):
                with bpy.context.temp_override(window=win, screen=scr):
                    bpy.ops.screen.animation_cancel(restore_frame=False)
                return True
    except Exception:
        pass
    try:
        bpy.ops.screen.animation_cancel(restore_frame=False)
        return True
    except Exception:
        return False


def _mocap_tick():
    st = _MOCAP
    sock = st.get("sock")
    if sock is None:
        return None  # 타이머 종료
    try:
        while True:
            try:
                data, _a = sock.recvfrom(65535)
            except (BlockingIOError, InterruptedError):
                break
            except OSError:
                break
            _mocap_parse(data.decode("utf-8", "ignore"))
    except Exception:
        pass
    st["hs"] = st.get("hs", 0) + 1
    if st["hs"] >= 60:  # 약 2초마다 핸드셰이크 재전송
        st["hs"] = 0
        _mocap_handshake()
    try:
        s = getattr(bpy.context.scene, "fskr", None)
        if s and s.rig:
            rp = False
            if s.mocap_record:
                try:
                    scr = bpy.context.screen
                    rp = bool(scr and scr.is_animation_playing)
                except Exception:
                    rp = False
            # 녹화 중 End Frame 도달/루프 감지 → 재생 정지 (덮어쓰기 방지)
            if rp:
                sc9 = bpy.context.scene
                cur = sc9.frame_current
                lastf = _MOCAP.get("lastf", cur)
                if cur >= sc9.frame_end or cur < lastf:
                    _stop_playback()
                    try:
                        sc9.frame_current = sc9.frame_end
                    except Exception:
                        pass
                    try:
                        s.mocap_record = False  # 녹화 자동 종료
                    except Exception:
                        pass
                    _MOCAP["lastf"] = 0
                    rp = False
                else:
                    _MOCAP["lastf"] = cur
            else:
                _MOCAP["lastf"] = 0
            _blend_step(rp)  # 프리셋 블렌딩 (매핑된 핸들은 아래에서 덮음)
            _mocap_apply(s, s.rig)
            if getattr(s, "mocap_preview", False):
                for win in bpy.context.window_manager.windows:
                    for area in win.screen.areas:
                        if area.type == 'VIEW_3D':
                            area.tag_redraw()
    except Exception:
        pass
    return 0.033


_AK_SYN = {"close": "blink", "eyebrow": "brow", "brows": "brow",
           "wink": "blink"}


def _name_tokens(nm):
    nm = re.sub(r"([a-z])([A-Z])", r"\1 \2", nm)
    out = set()
    for t in re.split(r"[^A-Za-z]+", nm.lower()):
        if not t:
            continue
        t = _AK_SYN.get(t, t)
        if t == "l":
            t = "left"
        if t == "r":
            t = "right"
        out.add(t)
    return out


_WROLES_SLD = (("__NONE__", "(사용 안 함)", ""),
               ('EYE_L', "왼눈 감기", ""), ('EYE_R', "오른눈 감기", ""),
               ('BROW_L', "왼눈썹 (위/아래)", ""),
               ('BROW_R', "오른눈썹 (위/아래)", ""),
               ('M_A', "입 A (아)", ""), ('M_I', "입 I (이)", ""),
               ('M_U', "입 U (우)", ""), ('M_E', "입 E (에)", ""),
               ('M_O', "입 O (오)", ""))


_WROLES_BONE = (("__NONE__", "(사용 안 함)", ""),
                ('PAD_L', "왼눈 눈동자 패드", ""),
                ('PAD_R', "오른눈 눈동자 패드", ""))


_WROLES_PAD = (("__NONE__", "(사용 안 함)", ""),
               ('M_PAD', "입 패드 (모음 자동 배치)",
                "슬롯에 연결된 A/I/U/E/O 키의 방향을 읽어 자동 매핑"))


def _wrole_items(self, context):
    if self.ctype == 'BONE':
        return _WROLES_BONE
    if self.ctype == 'PAD':
        return _WROLES_PAD
    return _WROLES_SLD


class FSKR_WizRoleItem(bpy.types.PropertyGroup):
    bone: bpy.props.StringProperty()
    label: bpy.props.StringProperty()
    ctype: bpy.props.StringProperty()
    role: bpy.props.EnumProperty(name="역할", items=_wrole_items)


def _action_fcurves(ad):
    """애니메이션 데이터의 F-커브 목록 (Blender 5.x 슬롯 액션 호환)."""
    act = ad.action if ad else None
    if act is None:
        return []
    fcs = getattr(act, "fcurves", None)
    if fcs is not None:
        return list(fcs)
    out = []
    try:
        slot = getattr(ad, "action_slot", None)
        for layer in act.layers:
            for strip in layer.strips:
                cb = None
                if slot is not None:
                    try:
                        cb = strip.channelbag(slot)
                    except Exception:
                        cb = None
                if cb is not None:
                    out.extend(cb.fcurves)
                else:
                    for cb2 in strip.channelbags:
                        out.extend(cb2.fcurves)
    except Exception:
        pass
    return out


def _read_wav_mono(path):
    """WAV를 모노 float 배열로 (16/24/32비트 PCM, float 지원)."""
    import wave
    import numpy as np
    wf = wave.open(path, 'rb')
    try:
        sr = wf.getframerate()
        ch = wf.getnchannels()
        sw = wf.getsampwidth()
        raw = wf.readframes(wf.getnframes())
    finally:
        wf.close()
    if sw == 2:
        data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sw == 4:
        # 32비트: int PCM 또는 float — 휴리스틱으로 판별
        di = (np.frombuffer(raw, dtype=np.int32).astype(np.float32)
              / 2147483648.0)
        df = np.frombuffer(raw, dtype=np.float32)
        ok_f = bool(np.all(np.isfinite(df))) and float(
            np.abs(df).max(initial=0.0)) <= 4.0
        data = df.copy() if ok_f else di
    elif sw == 1:
        data = ((np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
                 - 128.0) / 128.0)
    elif sw == 3:
        a = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        b = (a[:, 0].astype(np.int32) | (a[:, 1].astype(np.int32) << 8)
             | (a[:, 2].astype(np.int32) << 16))
        b = np.where(b >= (1 << 23), b - (1 << 24), b)
        data = b.astype(np.float32) / float(1 << 23)
    else:
        raise ValueError("bit depth")
    if ch > 1:
        data = data.reshape(-1, ch).mean(axis=1)
    return data, sr


def _read_audio_mono(path):
    """오디오 파일을 모노 float 배열로 (WAV는 직접, 그 외는 aud로 디코딩)."""
    if path.lower().endswith(".wav"):
        try:
            return _read_wav_mono(path)
        except Exception:
            pass  # 비표준 WAV → aud로 재시도
    import aud
    import numpy as np
    snd = aud.Sound(path)
    try:
        snd = snd.rechannel(1)
    except Exception:
        pass
    snd = snd.cache()
    arr = np.asarray(snd.data(), dtype=np.float32)
    if arr.ndim > 1:
        arr = arr.mean(axis=1)
    sr = 48000
    try:
        sp = snd.specs
        sr = int(sp[0] if float(sp[0]) > 1000 else sp[1])
    except Exception:
        pass
    return arr, sr


_VOWEL_PROTO = {'_A': (850.0, 1300.0), '_I': (300.0, 2500.0),
                '_U': (350.0, 800.0), '_E': (500.0, 2000.0),
                '_O': (500.0, 900.0)}


def _lipsync_analyze(data, sr, fps, gain, sil, smooth):
    """프레임별 A/I/U/E/O 가중치 계산 (포먼트 기반)."""
    import numpy as np
    from math import log, exp
    win = max(256, int(sr * 0.040))
    hann = np.hanning(win)
    n_out = int(len(data) / sr * fps) + 1
    freqs = np.fft.rfftfreq(win, 1.0 / sr)
    keys = list(_VOWEL_PROTO)
    rms_all = []
    feats = []
    kern = np.ones(5) / 5.0
    for i in range(n_out):
        c = int(i / fps * sr)
        a = max(0, c - win // 2)
        seg = data[a:a + win]
        if len(seg) < win:
            seg = np.pad(seg, (0, win - len(seg)))
        seg = seg - seg.mean()
        rms_all.append(float(np.sqrt((seg ** 2).mean())))
        sp = np.abs(np.fft.rfft(seg * hann))
        sp = np.convolve(sp, kern, mode='same')

        def peak(lo, hi):
            m = (freqs >= lo) & (freqs <= hi)
            if not m.any() or float(sp[m].max()) <= 0.0:
                return None
            return float(freqs[m][int(np.argmax(sp[m]))])

        f1 = peak(150.0, 1000.0)
        f2 = peak(max((f1 or 0.0) + 150.0, 700.0), 3200.0)
        feats.append((f1, f2))
    mx = max(rms_all) or 1.0
    alpha = 1.0 - min(0.95, max(0.0, smooth))
    ema = {k: 0.0 for k in keys}
    frames = []
    for i in range(n_out):
        rms = rms_all[i] / mx
        f1, f2 = feats[i]
        w = {k: 0.0 for k in keys}
        if rms >= sil and f1 and f2:
            d = {}
            for k, (p1, p2) in _VOWEL_PROTO.items():
                d[k] = (log(f1 / p1)) ** 2 + 0.7 * (log(f2 / p2)) ** 2
            sc = {k: exp(-d[k] / 0.18) for k in keys}
            tot = sum(sc.values()) or 1.0
            openv = min(1.0, (rms - sil) / max(1e-6, 0.4)) * gain
            for k in keys:
                w[k] = sc[k] / tot * openv
                if w[k] < 0.05:
                    w[k] = 0.0
        for k in keys:
            ema[k] = ema[k] * (1.0 - alpha) + w[k] * alpha
        frames.append({k: (ema[k] if ema[k] > 0.005 else 0.0)
                       for k in keys})
    return frames


def _lipsync_trim(s, a, b):
    """프레임 범위 [a,b]를 개방도·세그먼트·오디오에서 잘라낸다."""
    import os as _os
    scene = bpy.context.scene
    start = int(s.lipsync_start)
    try:
        opens = json.loads(s.lipsync_open or "[]")
    except Exception:
        opens = []
    n = len(opens)
    fps = scene.render.fps / scene.render.fps_base
    a = max(a, start)
    b = min(b, start + n - 1)
    if b < a or n == 0:
        return
    _lipsync_hist_pre(s)
    ln = b - a + 1
    opens = opens[:a - start] + opens[b - start + 1:]
    s.lipsync_open = json.dumps(opens)
    # 세그먼트: 범위 제거 + 뒤 당기기
    olds = [(int(it.fs), int(it.fe), str(it.vowel),
             float(it.px), float(it.py)) for it in s.lipsync_segs]
    s.lipsync_segs.clear()
    for fs9, fe9, vw9, px9t, py9t in olds:
        parts = []
        if fe9 < a:
            parts.append((fs9, fe9))
        elif fs9 > b:
            parts.append((fs9 - ln, fe9 - ln))
        else:
            if fs9 < a:
                parts.append((fs9, a - 1))
            if fe9 > b:
                parts.append((a, fe9 - ln))
        for p0, p1 in parts:
            if p1 < p0:
                continue
            it = s.lipsync_segs.add()
            it.fs = p0
            it.fe = p1
            try:
                it.vowel = vw9
            except TypeError:
                pass
            it.px = px9t
            it.py = py9t
    # 오디오 자르기 → 임시 WAV
    ap = str(getattr(s, "lipsync_audio", ""))
    ap = bpy.path.abspath(ap) if ap else ""
    if ap and _os.path.exists(ap):
        try:
            data9, sr9 = _read_audio_mono(ap)
            import numpy as np
            s0 = max(0, int((a - start) / fps * sr9))
            s1 = min(len(data9), int((b + 1 - start) / fps * sr9))
            data9 = np.concatenate([data9[:s0], data9[s1:]])
            import tempfile
            import wave
            import time as _t9
            np9 = _os.path.join(
                tempfile.gettempdir(),
                "fskr_lipsync_trim_%d.wav" % int(_t9.time()))
            pcm9 = np.clip(data9, -1.0, 1.0)
            pcm9 = (pcm9 * 32767.0).astype("<i2").tobytes()
            with wave.open(np9, "wb") as w9:
                w9.setnchannels(1)
                w9.setsampwidth(2)
                w9.setframerate(int(sr9))
                w9.writeframes(pcm9)
            s.lipsync_audio = np9
            with open(np9, "rb") as f9:
                audio9 = f9.read()
            with _LIPSRV["lock"]:
                _LIPSRV["audio"] = audio9
                _LIPSRV["amime"] = "audio/wav"
            try:
                se9 = scene.sequence_editor
                coll9 = ((getattr(se9, "sequences", None)
                          or getattr(se9, "strips", None))
                         if se9 else None)
                if coll9 is not None:
                    ch9 = 5
                    for st9 in [t9 for t9 in coll9
                                if t9.name.startswith("FSKR_lipsync")]:
                        ch9 = int(getattr(st9, "channel", 5))
                        coll9.remove(st9)
                    coll9.new_sound("FSKR_lipsync", np9, ch9, start)
            except Exception:
                pass
        except Exception:
            pass
    try:
        bpy.ops.fskr.lipsync_apply(refresh=False)
    except Exception:
        pass
    # init 갱신 (창 새로고침 대비)
    _lipsync_hist_push(s, "cut")
    try:
        init9 = json.loads(_LIPSRV.get("init") or "{}")
        init9["opens"] = opens
        init9["segs"] = [{"fs": int(it.fs), "fe": int(it.fe),
                          "v": it.vowel, "px": float(it.px),
                          "py": float(it.py)}
                         for it in s.lipsync_segs]
        init9["has_audio"] = bool(_LIPSRV.get("audio"))
        init9["hist"], init9["hidx"] = _lipsync_hist_json()
        with _LIPSRV["lock"]:
            _LIPSRV["init"] = json.dumps(init9)
    except Exception:
        pass


def _lipsync_move(s, a, b, d):
    """프레임 범위 [a,b]를 d만큼 이동 (개방도·오디오·세그먼트 함께)."""
    import os as _os
    scene = bpy.context.scene
    start = int(s.lipsync_start)
    try:
        opens = json.loads(s.lipsync_open or "[]")
    except Exception:
        opens = []
    n = len(opens)
    fps = scene.render.fps / scene.render.fps_base
    a = max(a, start)
    b = min(b, start + n - 1)
    if b < a or n == 0 or d == 0:
        return
    ln = b - a + 1
    ta = max(start, min(a + d, start + n - ln))
    if ta == a:
        return
    _lipsync_hist_pre(s)

    def remap9(f):
        if a <= f <= b:
            return ta + (f - a)
        g = f - (ln if f > b else 0)
        return g + (ln if g >= ta else 0)

    # 개방도 재배치
    chunk9 = opens[a - start:b - start + 1]
    rest9 = opens[:a - start] + opens[b - start + 1:]
    p9 = ta - start
    opens = rest9[:p9] + chunk9 + rest9[p9:]
    s.lipsync_open = json.dumps(opens)
    # 세그먼트 재배치 (프레임 단위 재매핑 후 연속 구간 재조립)
    olds = [(int(it.fs), int(it.fe), str(it.vowel),
             float(it.px), float(it.py)) for it in s.lipsync_segs]
    s.lipsync_segs.clear()
    news = []
    for fs9, fe9, vw9, px9t, py9t in olds:
        fr9 = sorted(remap9(f9) for f9 in range(fs9, fe9 + 1))
        r0 = pr = fr9[0]
        for f9 in fr9[1:]:
            if f9 != pr + 1:
                news.append((r0, pr, vw9, px9t, py9t))
                r0 = f9
            pr = f9
        news.append((r0, pr, vw9, px9t, py9t))
    for fs9, fe9, vw9, px9t, py9t in sorted(news):
        it = s.lipsync_segs.add()
        it.fs = fs9
        it.fe = fe9
        try:
            it.vowel = vw9
        except TypeError:
            pass
        it.px = px9t
        it.py = py9t
    # 오디오 재배치 → 임시 WAV
    ap = str(getattr(s, "lipsync_audio", ""))
    ap = bpy.path.abspath(ap) if ap else ""
    if ap and _os.path.exists(ap):
        try:
            data9, sr9 = _read_audio_mono(ap)
            import numpy as np
            sa9 = max(0, int((a - start) / fps * sr9))
            sb9 = min(len(data9), int((b + 1 - start) / fps * sr9))
            ck9 = data9[sa9:sb9]
            rs9 = np.concatenate([data9[:sa9], data9[sb9:]])
            ti9 = max(0, min(len(rs9),
                             int((ta - start) / fps * sr9)))
            data9 = np.concatenate([rs9[:ti9], ck9, rs9[ti9:]])
            import tempfile
            import wave
            import time as _t9
            np9 = _os.path.join(
                tempfile.gettempdir(),
                "fskr_lipsync_move_%d.wav" % int(_t9.time()))
            pcm9 = np.clip(data9, -1.0, 1.0)
            pcm9 = (pcm9 * 32767.0).astype("<i2").tobytes()
            with wave.open(np9, "wb") as w9:
                w9.setnchannels(1)
                w9.setsampwidth(2)
                w9.setframerate(int(sr9))
                w9.writeframes(pcm9)
            s.lipsync_audio = np9
            with open(np9, "rb") as f9:
                audio9 = f9.read()
            with _LIPSRV["lock"]:
                _LIPSRV["audio"] = audio9
                _LIPSRV["amime"] = "audio/wav"
            try:
                se9 = scene.sequence_editor
                coll9 = ((getattr(se9, "sequences", None)
                          or getattr(se9, "strips", None))
                         if se9 else None)
                if coll9 is not None:
                    ch9 = 5
                    for st9 in [t9 for t9 in coll9
                                if t9.name.startswith("FSKR_lipsync")]:
                        ch9 = int(getattr(st9, "channel", 5))
                        coll9.remove(st9)
                    coll9.new_sound("FSKR_lipsync", np9, ch9, start)
            except Exception:
                pass
        except Exception:
            pass
    try:
        bpy.ops.fskr.lipsync_apply(refresh=False)
    except Exception:
        pass
    _lipsync_hist_push(s, "move")
    try:
        init9 = json.loads(_LIPSRV.get("init") or "{}")
        init9["opens"] = opens
        init9["segs"] = [{"fs": int(it.fs), "fe": int(it.fe),
                          "v": it.vowel, "px": float(it.px),
                          "py": float(it.py)}
                         for it in s.lipsync_segs]
        init9["has_audio"] = bool(_LIPSRV.get("audio"))
        init9["hist"], init9["hidx"] = _lipsync_hist_json()
        with _LIPSRV["lock"]:
            _LIPSRV["init"] = json.dumps(init9)
    except Exception:
        pass


def _lipsync_state_snap(s, op9):
    """현재 립싱크 상태의 스냅샷 (히스토리 항목)."""
    import time as _t9
    return {"open": s.lipsync_open,
            "audio": str(getattr(s, "lipsync_audio", "")),
            "segs": [(int(it.fs), int(it.fe), str(it.vowel),
                      float(it.px), float(it.py))
                     for it in s.lipsync_segs],
            "op": op9, "t": _t9.strftime("%H:%M:%S")}


def _lipsync_hist_pre(s):
    """첫 오디오 편집 전, 원본 상태를 히스토리에 저장."""
    try:
        ah9 = _LIPSRV.setdefault("ahist", [])
        if not ah9:
            ah9.append(_lipsync_state_snap(s, "orig"))
            _LIPSRV["ahidx"] = 0
    except Exception:
        pass


def _lipsync_hist_push(s, op9):
    """편집 결과 상태를 히스토리에 추가 (앞으로 가기 가지는 잘림)."""
    try:
        ah9 = _LIPSRV.setdefault("ahist", [])
        idx9 = _LIPSRV.get("ahidx", len(ah9) - 1)
        del ah9[idx9 + 1:]
        ah9.append(_lipsync_state_snap(s, op9))
        if len(ah9) > 20:
            ah9.pop(0)
        _LIPSRV["ahidx"] = len(ah9) - 1
    except Exception:
        pass


def _lipsync_hist_json():
    ah9 = _LIPSRV.get("ahist") or []
    return ([{"op": e9.get("op", "?"), "t": e9.get("t", "")}
             for e9 in ah9],
            _LIPSRV.get("ahidx", len(ah9) - 1))


def _lipsync_silence(s, a, b):
    """범위 [a,b]의 파형을 무음으로 만들되 길이는 유지."""
    import os as _os
    scene = bpy.context.scene
    start = int(s.lipsync_start)
    try:
        opens = json.loads(s.lipsync_open or "[]")
    except Exception:
        opens = []
    n = len(opens)
    fps = scene.render.fps / scene.render.fps_base
    a = max(a, start)
    b = min(b, start + n - 1)
    if b < a or n == 0:
        return
    _lipsync_hist_pre(s)
    for i9 in range(a - start, b - start + 1):
        opens[i9] = 0.0
    s.lipsync_open = json.dumps(opens)
    # 범위 내 구간 제거 (경계는 분할)
    olds = [(int(it.fs), int(it.fe), str(it.vowel),
             float(it.px), float(it.py)) for it in s.lipsync_segs]
    s.lipsync_segs.clear()
    for fs9, fe9, vw9, px9t, py9t in olds:
        parts = []
        if fe9 < a or fs9 > b:
            parts.append((fs9, fe9))
        else:
            if fs9 < a:
                parts.append((fs9, a - 1))
            if fe9 > b:
                parts.append((b + 1, fe9))
        for p0, p1 in parts:
            if p1 < p0:
                continue
            it = s.lipsync_segs.add()
            it.fs = p0
            it.fe = p1
            try:
                it.vowel = vw9
            except TypeError:
                pass
            it.px = px9t
            it.py = py9t
    # 오디오 무음화
    ap = str(getattr(s, "lipsync_audio", ""))
    ap = bpy.path.abspath(ap) if ap else ""
    if ap and _os.path.exists(ap):
        try:
            data9, sr9 = _read_audio_mono(ap)
            import numpy as np
            sa9 = max(0, int((a - start) / fps * sr9))
            sb9 = min(len(data9), int((b + 1 - start) / fps * sr9))
            data9 = np.array(data9, copy=True)
            data9[sa9:sb9] = 0.0
            import tempfile
            import wave
            import time as _t9
            np9 = _os.path.join(
                tempfile.gettempdir(),
                "fskr_lipsync_sil_%d.wav" % int(_t9.time()))
            pcm9 = np.clip(data9, -1.0, 1.0)
            pcm9 = (pcm9 * 32767.0).astype("<i2").tobytes()
            with wave.open(np9, "wb") as w9:
                w9.setnchannels(1)
                w9.setsampwidth(2)
                w9.setframerate(int(sr9))
                w9.writeframes(pcm9)
            s.lipsync_audio = np9
            with open(np9, "rb") as f9:
                audio9 = f9.read()
            with _LIPSRV["lock"]:
                _LIPSRV["audio"] = audio9
                _LIPSRV["amime"] = "audio/wav"
            try:
                se9 = scene.sequence_editor
                coll9 = ((getattr(se9, "sequences", None)
                          or getattr(se9, "strips", None))
                         if se9 else None)
                if coll9 is not None:
                    ch9 = 5
                    for st9 in [t9 for t9 in coll9
                                if t9.name.startswith("FSKR_lipsync")]:
                        ch9 = int(getattr(st9, "channel", 5))
                        coll9.remove(st9)
                    coll9.new_sound("FSKR_lipsync", np9, ch9, start)
            except Exception:
                pass
        except Exception:
            pass
    try:
        bpy.ops.fskr.lipsync_apply(refresh=False)
    except Exception:
        pass
    _lipsync_hist_push(s, "sil")
    try:
        init9 = json.loads(_LIPSRV.get("init") or "{}")
        init9["opens"] = opens
        init9["segs"] = [{"fs": int(it.fs), "fe": int(it.fe),
                          "v": it.vowel, "px": float(it.px),
                          "py": float(it.py)}
                         for it in s.lipsync_segs]
        init9["has_audio"] = bool(_LIPSRV.get("audio"))
        init9["hist"], init9["hidx"] = _lipsync_hist_json()
        with _LIPSRV["lock"]:
            _LIPSRV["init"] = json.dumps(init9)
    except Exception:
        pass


def _lipsync_volume(s, a, b, g, rc=True):
    """범위 [a,b]의 볼륨을 g배로 조절. rc면 립싱크도 재계산."""
    import os as _os
    scene = bpy.context.scene
    start = int(s.lipsync_start)
    try:
        opens = json.loads(s.lipsync_open or "[]")
    except Exception:
        opens = []
    n = len(opens)
    fps = scene.render.fps / scene.render.fps_base
    a = max(a, start)
    b = min(b, start + n - 1)
    if b < a or n == 0 or g <= 0.0:
        return
    _lipsync_hist_pre(s)
    ap = str(getattr(s, "lipsync_audio", ""))
    ap = bpy.path.abspath(ap) if ap else ""
    if not (ap and _os.path.exists(ap)):
        _LIPSRV["err"] = "volume: audio not found: " + ap
        return
    try:
        data9, sr9 = _read_audio_mono(ap)
        import numpy as np
        sa9 = max(0, int((a - start) / fps * sr9))
        sb9 = min(len(data9), int((b + 1 - start) / fps * sr9))
        data9 = np.array(data9, copy=True)
        data9[sa9:sb9] = np.clip(data9[sa9:sb9] * g, -1.0, 1.0)
        import tempfile
        import wave
        import time as _t9
        np9 = _os.path.join(
            tempfile.gettempdir(),
            "fskr_lipsync_vol_%d.wav" % int(_t9.time()))
        pcm9 = np.clip(data9, -1.0, 1.0)
        pcm9 = (pcm9 * 32767.0).astype("<i2").tobytes()
        with wave.open(np9, "wb") as w9:
            w9.setnchannels(1)
            w9.setsampwidth(2)
            w9.setframerate(int(sr9))
            w9.writeframes(pcm9)
        s.lipsync_audio = np9
        with open(np9, "rb") as f9:
            audio9 = f9.read()
        with _LIPSRV["lock"]:
            _LIPSRV["audio"] = audio9
            _LIPSRV["amime"] = "audio/wav"
        try:
            se9 = scene.sequence_editor
            coll9 = ((getattr(se9, "sequences", None)
                      or getattr(se9, "strips", None))
                     if se9 else None)
            if coll9 is not None:
                ch9 = 5
                for st9 in [t9 for t9 in coll9
                            if t9.name.startswith("FSKR_lipsync")]:
                    ch9 = int(getattr(st9, "channel", 5))
                    coll9.remove(st9)
                coll9.new_sound("FSKR_lipsync", np9, ch9, start)
        except Exception:
            pass
        # 범위 재분석 → 개방도/세그먼트 갱신
        frames9 = _lipsync_analyze(data9, sr9, fps, 1.0, 0.06, 0.35)
        n2 = min(n, len(frames9))
        i0 = a - start
        i1 = min(b - start, n2 - 1)
        new_open9 = [round(min(1.5, sum(frames9[i9].values())), 3)
                     for i9 in range(i0, i1 + 1)]
        if sum(new_open9) < 0.05 and (i1 - i0) > 10:
            # 재분석이 사실상 무음 → 기존 데이터 보호를 위해 중단
            import numpy as _np9
            _LIPSRV["err"] = (
                _tr("재계산 결과가 무음이라 중단했습니다. 진단: "
                "len=%d sr=%s fps=%.2f peak=%.4f frames=%d") % (
                    len(data9), str(sr9), fps,
                    float(_np9.abs(data9).max(initial=0.0)),
                    len(frames9)))
            return
        for j9, i9 in enumerate(range(i0, i1 + 1)):
            opens[i9] = new_open9[j9]
        s.lipsync_open = json.dumps(opens)
        if rc:
            # 기존 범위 내 구간 제거 (경계 분할)
            olds = [(int(it.fs), int(it.fe), str(it.vowel),
                     float(it.px), float(it.py)) for it in s.lipsync_segs]
            keep9 = []
            for fs9, fe9, vw9, px9t, py9t in olds:
                if fe9 < a or fs9 > b:
                    keep9.append((fs9, fe9, vw9, px9t, py9t))
                else:
                    if fs9 < a:
                        keep9.append((fs9, a - 1, vw9, px9t, py9t))
                    if fe9 > b:
                        keep9.append((b + 1, fe9, vw9, px9t, py9t))
            # 범위를 새로 자동 분석해 구간 생성
            _pb9, vmap9 = _lipsync_padinfo(s, s.rig)
            news9 = []
            if vmap9:
                poss9 = []
                for i9 in range(i0, i1 + 1):
                    vw9 = frames9[i9]
                    tot9 = sum(vw9.values())
                    if tot9 > 0.02:
                        x9 = sum(w9 * vmap9.get(k9, (0.0, 0.0))[0]
                                 for k9, w9 in vw9.items()) / tot9
                        y9 = sum(w9 * vmap9.get(k9, (0.0, 0.0))[1]
                                 for k9, w9 in vw9.items()) / tot9
                        sc9 = min(1.0, tot9)
                        poss9.append((x9 * sc9, y9 * sc9))
                    else:
                        poss9.append(None)

                def flushv(a2, b2):
                    if b2 < a2:
                        return
                    ws = xs = ys = 0.0
                    for i9 in range(a2, b2 + 1):
                        if poss9[i9] is None:
                            continue
                        w9 = max(0.05, abs(poss9[i9][0])
                                 + abs(poss9[i9][1]))
                        xs += poss9[i9][0] * w9
                        ys += poss9[i9][1] * w9
                        ws += w9
                    if ws <= 0.0:
                        return
                    px9 = max(-1.0, min(1.0, xs / ws))
                    py9 = max(-1.0, min(1.0, ys / ws))
                    bv9, bd9 = '_A', 1e9
                    for k9, q9 in vmap9.items():
                        d9 = (q9[0] - px9) ** 2 + (q9[1] - py9) ** 2
                        if d9 < bd9:
                            bd9 = d9
                            bv9 = k9
                    news9.append((start + i0 + a2, start + i0 + b2,
                                  bv9, round(px9, 4), round(py9, 4)))
                m9 = len(poss9)
                i9 = 0
                min_len = 3
                th2 = 0.30 ** 2
                while i9 < m9:
                    if poss9[i9] is None:
                        i9 += 1
                        continue
                    a2 = i9
                    mx = my = mw = 0.0
                    while i9 < m9 and poss9[i9] is not None:
                        p9 = poss9[i9]
                        if mw > 0.0 and (i9 - a2) >= min_len:
                            cx, cy = mx / mw, my / mw
                            if ((p9[0] - cx) ** 2
                                    + (p9[1] - cy) ** 2) > th2:
                                flushv(a2, i9 - 1)
                                a2 = i9
                                mx = my = mw = 0.0
                        w9 = max(0.05, abs(p9[0]) + abs(p9[1]))
                        mx += p9[0] * w9
                        my += p9[1] * w9
                        mw += w9
                        i9 += 1
                    flushv(a2, i9 - 1)
            s.lipsync_segs.clear()
            for fs9, fe9, vw9, px9t, py9t in sorted(keep9 + news9):
                it = s.lipsync_segs.add()
                it.fs = fs9
                it.fe = fe9
                try:
                    it.vowel = vw9
                except TypeError:
                    pass
                it.px = px9t
                it.py = py9t
    except Exception as e9v:
        _LIPSRV["err"] = "volume: " + repr(e9v)
    if rc:
        try:
            bpy.ops.fskr.lipsync_apply(refresh=False)
        except Exception:
            pass
    _lipsync_hist_push(s, "rec" if (rc and abs(g - 1.0) < 1e-9)
                       else "vol")
    try:
        init9 = json.loads(_LIPSRV.get("init") or "{}")
        init9["opens"] = opens
        init9["segs"] = [{"fs": int(it.fs), "fe": int(it.fe),
                          "v": it.vowel, "px": float(it.px),
                          "py": float(it.py)}
                         for it in s.lipsync_segs]
        init9["has_audio"] = bool(_LIPSRV.get("audio"))
        init9["hist"], init9["hidx"] = _lipsync_hist_json()
        with _LIPSRV["lock"]:
            _LIPSRV["init"] = json.dumps(init9)
    except Exception:
        pass


def _lipsync_restore(s, snap):
    """오디오 편집(잘라내기/이동) 이전 상태로 복원."""
    import os as _os
    scene = bpy.context.scene
    s.lipsync_open = str(snap.get("open", "[]"))
    s.lipsync_segs.clear()
    for fs9, fe9, vw9, px9t, py9t in snap.get("segs", []):
        it = s.lipsync_segs.add()
        it.fs = int(fs9)
        it.fe = int(fe9)
        try:
            it.vowel = str(vw9)
        except TypeError:
            pass
        it.px = float(px9t)
        it.py = float(py9t)
    ap = str(snap.get("audio", ""))
    apf = bpy.path.abspath(ap) if ap else ""
    if apf and _os.path.exists(apf):
        s.lipsync_audio = ap
        try:
            with open(apf, "rb") as f9:
                audio9 = f9.read()
            ext9 = apf.lower().rsplit(".", 1)[-1]
            mime9 = {"wav": "audio/wav", "mp3": "audio/mpeg",
                     "ogg": "audio/ogg", "flac": "audio/flac",
                     "m4a": "audio/mp4", "aac": "audio/aac"
                     }.get(ext9, "application/octet-stream")
            with _LIPSRV["lock"]:
                _LIPSRV["audio"] = audio9
                _LIPSRV["amime"] = mime9
            se9 = scene.sequence_editor
            coll9 = ((getattr(se9, "sequences", None)
                      or getattr(se9, "strips", None))
                     if se9 else None)
            if coll9 is not None:
                ch9 = 5
                for st9 in [t9 for t9 in coll9
                            if t9.name.startswith("FSKR_lipsync")]:
                    ch9 = int(getattr(st9, "channel", 5))
                    coll9.remove(st9)
                coll9.new_sound("FSKR_lipsync", apf, ch9,
                                int(s.lipsync_start))
        except Exception:
            pass
    try:
        bpy.ops.fskr.lipsync_apply(refresh=False)
    except Exception:
        pass
    try:
        opens9 = json.loads(s.lipsync_open or "[]")
    except Exception:
        opens9 = []
    try:
        init9 = json.loads(_LIPSRV.get("init") or "{}")
        init9["opens"] = opens9
        init9["segs"] = [{"fs": int(it.fs), "fe": int(it.fe),
                          "v": it.vowel, "px": float(it.px),
                          "py": float(it.py)}
                         for it in s.lipsync_segs]
        init9["has_audio"] = bool(_LIPSRV.get("audio"))
        init9["hist"], init9["hidx"] = _lipsync_hist_json()
        with _LIPSRV["lock"]:
            _LIPSRV["init"] = json.dumps(init9)
    except Exception:
        pass


def _lipsync_pad_sig(s):
    """패드 위치 F-커브의 키프레임 서명 (외부 편집 감지용)."""
    pad9, _v9 = _lipsync_padinfo(s, s.rig)
    if pad9 is None or not s.rig or not s.rig.animation_data:
        return None
    dp9 = 'pose.bones["%s"].location' % pad9.name
    sig9 = []
    for fc9 in _action_fcurves(s.rig.animation_data):
        if fc9.data_path == dp9 and fc9.array_index in (0, 1):
            for p9 in fc9.keyframe_points:
                sig9.append((fc9.array_index, round(p9.co[0], 3),
                             round(p9.co[1], 5)))
    sig9.sort()
    return hash(tuple(sig9))


def _lipsync_segs_from_curves(s):
    """패드 F-커브의 평탄 구간(같은 값 키 쌍)을 찾아 세그먼트 복원."""
    if getattr(s, "lipsync_sprite", False):
        return False  # 스프라이트 구간은 패드 커브에서 복원하지 않음
    pad9, vmap9 = _lipsync_padinfo(s, s.rig)
    if pad9 is None or not s.rig or not s.rig.animation_data:
        return False
    dp9 = 'pose.bones["%s"].location' % pad9.name
    fcx = fcy = None
    for fc9 in _action_fcurves(s.rig.animation_data):
        if fc9.data_path == dp9:
            if fc9.array_index == 0:
                fcx = fc9
            elif fc9.array_index == 1:
                fcy = fc9
    if fcx is None and fcy is None:
        return False
    try:
        opens = json.loads(s.lipsync_open or "[]")
    except Exception:
        opens = []
    n = len(opens)
    if n == 0:
        return False
    start = int(s.lipsync_start)
    kfs = set()
    for fc9 in (fcx, fcy):
        if fc9 is None:
            continue
        for p9 in fc9.keyframe_points:
            f9 = float(p9.co[0])
            if start - 1 <= f9 <= start + n:
                kfs.add(round(f9, 3))
    kfs = sorted(kfs)
    if not kfs:
        return False

    def ev9(f9):
        x9 = (fcx.evaluate(f9) / PAD) if fcx else 0.0
        y9 = (fcy.evaluate(f9) / PAD) if fcy else 0.0
        return (x9, y9)

    # 키프레임 지점들을 평탄 구간으로 묶기
    plateaus = []  # [f0, f1, sx, sy, cnt]
    cur = None
    tol2 = 0.05 ** 2
    for f9 in kfs:
        p9 = ev9(f9)
        if abs(p9[0]) + abs(p9[1]) <= 0.04:
            if cur is not None:
                plateaus.append(cur)
                cur = None
            continue
        if cur is None:
            cur = [f9, f9, p9[0], p9[1], 1]
        else:
            ax9 = cur[2] / cur[4]
            ay9 = cur[3] / cur[4]
            if ((p9[0] - ax9) ** 2 + (p9[1] - ay9) ** 2) <= tol2:
                cur[1] = f9
                cur[2] += p9[0]
                cur[3] += p9[1]
                cur[4] += 1
            else:
                plateaus.append(cur)
                cur = [f9, f9, p9[0], p9[1], 1]
    if cur is not None:
        plateaus.append(cur)
    s.lipsync_segs.clear()
    if not plateaus:
        return True
    bl9 = max(0, min(12, int(getattr(s, "lipsync_blend", 2))))
    h9 = bl9 / 2.0
    prev_end = None
    for j9, pl9 in enumerate(plateaus):
        a9f = pl9[0] - h9
        b9f = pl9[1] + h9
        if j9 > 0:
            a9f = max(a9f, (plateaus[j9 - 1][1] + pl9[0]) / 2.0 + 0.5)
        if j9 < len(plateaus) - 1:
            b9f = min(b9f, (pl9[1] + plateaus[j9 + 1][0]) / 2.0 - 0.5)
        a9 = int(round(max(start, a9f)))
        b9 = int(round(min(start + n - 1, b9f)))
        if prev_end is not None and a9 <= prev_end:
            a9 = prev_end + 1
        if b9 < a9:
            b9 = a9
        if prev_end is not None and a9 <= prev_end:
            continue
        px9 = max(-1.0, min(1.0, pl9[2] / pl9[4]))
        py9 = max(-1.0, min(1.0, pl9[3] / pl9[4]))
        it = s.lipsync_segs.add()
        it.fs = a9
        it.fe = b9
        it.px = round(px9, 4)
        it.py = round(py9, 4)
        bv9, bd9 = '_A', 1e9
        for k9, q9 in vmap9.items():
            d9 = (q9[0] - px9) ** 2 + (q9[1] - py9) ** 2
            if d9 < bd9:
                bd9 = d9
                bv9 = k9
        try:
            it.vowel = bv9
        except TypeError:
            pass
        prev_end = b9
    return True


_AUD_INFO = {"key": None, "val": None}


def _lipsync_audio_info(s):
    """현재 립싱크 오디오의 상세 정보 (파일명·형식·크기·파형)."""
    import os as _os
    ap = str(getattr(s, "lipsync_audio", ""))
    apf = bpy.path.abspath(ap) if ap else ""
    if not apf or not _os.path.exists(apf):
        return None
    try:
        mt9 = _os.path.getmtime(apf)
    except Exception:
        mt9 = 0
    key9 = (apf, mt9, str(getattr(s, "lipsync_open", ""))[:40])
    if _AUD_INFO["key"] == key9:
        return _AUD_INFO["val"]
    inf9 = {"name": _os.path.basename(apf)}
    try:
        sz9 = _os.path.getsize(apf)
        inf9["size"] = ("%.1f MB" % (sz9 / 1048576.0)
                        if sz9 >= 1048576
                        else "%.0f KB" % (sz9 / 1024.0))
    except Exception:
        inf9["size"] = "?"
    ext9 = apf.lower().rsplit(".", 1)[-1]
    dur9 = None
    if ext9 == "wav":
        try:
            import wave
            wf9 = wave.open(apf, 'rb')
            try:
                sw9 = wf9.getsampwidth() * 8
                ch9 = wf9.getnchannels()
                sr9 = wf9.getframerate()
                nf9 = wf9.getnframes()
            finally:
                wf9.close()
            dur9 = nf9 / float(sr9 or 1)
            inf9["codec"] = (_tr("WAV PCM %d비트") % sw9
                             + " · %dHz · " % sr9
                             + (_tr("모노") if ch9 == 1
                                else "%dch" % ch9))
        except Exception:
            inf9["codec"] = "WAV"
    else:
        inf9["codec"] = {"mp3": "MP3 (MPEG Layer III)",
                         "ogg": "OGG Vorbis",
                         "flac": _tr("FLAC (무손실)"),
                         "m4a": "AAC (M4A)",
                         "aac": "AAC"}.get(ext9, ext9.upper())
    try:
        opens9 = json.loads(s.lipsync_open or "[]")
    except Exception:
        opens9 = []
    if dur9 is None and opens9:
        try:
            sc9 = bpy.context.scene
            fps9 = sc9.render.fps / sc9.render.fps_base
            dur9 = len(opens9) / fps9
        except Exception:
            pass
    inf9["dur"] = ("%.1fs" % dur9) if dur9 else "?"
    inf9["wave"] = ""
    _AUD_INFO["key"] = key9
    _AUD_INFO["val"] = inf9
    return inf9


def _lipsync_slot_of(x9, y9):
    """패드 위치(-1~1)를 슬롯 이름으로 (웹 padSlots와 동일 규칙)."""
    sx = 0 if abs(x9) < 0.35 else (1 if x9 > 0 else -1)
    sy = 0 if abs(y9) < 0.35 else (1 if y9 > 0 else -1)
    if sy > 0:
        return 'ur' if sx > 0 else ('ul' if sx < 0 else 'up')
    if sy < 0:
        return 'dr' if sx > 0 else ('dl' if sx < 0 else 'down')
    return 'right' if sx > 0 else 'left'


def _lipsync_padinfo(s, rig):
    """매핑의 모음 행에서 입 2D 패드 본과 모음별 위치(-1~1)를 추출."""
    pad_pb = None
    vmap = {}
    if not rig:
        return None, vmap
    for it in s.mocap_map:
        if not it.arkit.startswith('_') or it.tgt == 'KEY':
            continue
        if it.comp not in ('XP', 'XN', 'YP', 'YN'):
            continue
        pb = rig.pose.bones.get(it.ctl)
        if pb is None or str(pb.get("fskr_type", "")) != 'PAD':
            continue
        if pad_pb is None:
            pad_pb = pb
        if pb != pad_pb:
            continue
        x9, y9 = vmap.get(it.arkit, (0.0, 0.0))
        f9 = float(it.factor)
        if it.comp == 'XP':
            x9 += f9
        elif it.comp == 'XN':
            x9 -= f9
        elif it.comp == 'YP':
            y9 += f9
        else:
            y9 -= f9
        vmap[it.arkit] = (x9, y9)
    return pad_pb, vmap


def _lipsync_build_segs(s, frames, start):
    """프레임별 가중치에서 구간 추출·저장.

    입 2D 패드가 있으면 모음 가중치를 패드 좌표로 합성해 중간
    입모양([ae] 등)을 그대로 담고, 입모양이 크게 변하는 지점에서
    구간을 분할해 이중모음 글라이드도 표현한다.
    """
    s.lipsync_segs.clear()
    # 스프라이트 방식: 모음 대신 입 벌림 단계(닫힘/반/열림)로 구간 생성
    try:
        from . import atlas as _at9
        spr9 = _at9.atlas_sprite_lip(s)
    except Exception:
        _at9, spr9 = None, False
    if spr9:
        opens = [round(min(1.5, sum(vw.values())), 3) for vw in frames]
        _at9.atlas_level_segs(s, opens, start)
        s.lipsync_open = json.dumps(opens)
        s.lipsync_start = start
        s.lipsync_idx = 0
        try:
            sc9f = bpy.context.scene
            s.lipsync_fps = sc9f.render.fps / sc9f.render.fps_base
        except Exception:
            pass
        return
    try:
        s.lipsync_sprite = False
    except Exception:
        pass
    opens = []
    _pb9, vmap9 = _lipsync_padinfo(s, s.rig)
    use_pad = bool(vmap9)
    poss = []  # 프레임별 합성 패드 위치 (개방도 반영)
    for vw in frames:
        tot = sum(vw.values())
        opens.append(round(min(1.5, tot), 3))
        if use_pad and tot > 0.02:
            x9 = sum(w9 * vmap9.get(k9, (0.0, 0.0))[0]
                     for k9, w9 in vw.items()) / tot
            y9 = sum(w9 * vmap9.get(k9, (0.0, 0.0))[1]
                     for k9, w9 in vw.items()) / tot
            sc9 = min(1.0, tot)
            poss.append((x9 * sc9, y9 * sc9))
        else:
            poss.append(None)

    if not use_pad:
        # 패드 없는 리그: 기존 지배 모음 방식
        cur_v = None
        seg_a = 0
        for i, vw in enumerate(frames):
            tot = sum(vw.values())
            dom = max(vw, key=vw.get) if tot > 0.02 else None
            if dom != cur_v:
                if cur_v is not None:
                    it = s.lipsync_segs.add()
                    it.fs = start + seg_a
                    it.fe = start + i - 1
                    it.vowel = cur_v
                cur_v = dom
                seg_a = i
        if cur_v is not None:
            it = s.lipsync_segs.add()
            it.fs = start + seg_a
            it.fe = start + len(frames) - 1
            it.vowel = cur_v
    else:
        def flush9(a9, b9):
            """[a9,b9] 구간 저장 (개방도 가중 평균 위치)."""
            if b9 < a9:
                return
            it = s.lipsync_segs.add()
            it.fs = start + a9
            it.fe = start + b9
            wsum = xs = ys = 0.0
            dom9 = {}
            for i9 in range(a9, b9 + 1):
                w9 = opens[i9]
                for k9, v9 in frames[i9].items():
                    dom9[k9] = dom9.get(k9, 0.0) + v9
                if poss[i9] is not None and w9 > 0.0:
                    xs += poss[i9][0] * w9
                    ys += poss[i9][1] * w9
                    wsum += w9
            it.vowel = (max(dom9, key=dom9.get)
                        if dom9 and max(dom9.values()) > 0.0 else '_N')
            if wsum > 0.0:
                it.px = round(max(-1.0, min(1.0, xs / wsum)), 4)
                it.py = round(max(-1.0, min(1.0, ys / wsum)), 4)

        n9 = len(frames)
        i = 0
        min_len = 3       # 구간 최소 길이 (프레임)
        th2 = 0.30 ** 2   # 분할 임계 (입모양 이동 거리)
        while i < n9:
            if opens[i] <= 0.02:
                i += 1
                continue
            a9 = i
            mx = my = mw = 0.0
            while i < n9 and opens[i] > 0.02:
                p9 = poss[i]
                if p9 is not None:
                    if mw > 0.0 and (i - a9) >= min_len:
                        cx, cy = mx / mw, my / mw
                        d2 = ((p9[0] - cx) ** 2
                              + (p9[1] - cy) ** 2)
                        if d2 > th2:
                            flush9(a9, i - 1)  # 입모양 변화 → 분할
                            a9 = i
                            mx = my = mw = 0.0
                    w9 = max(0.05, opens[i])
                    mx += p9[0] * w9
                    my += p9[1] * w9
                    mw += w9
                i += 1
            flush9(a9, i - 1)
    s.lipsync_open = json.dumps(opens)
    s.lipsync_start = start
    s.lipsync_idx = 0
    try:
        sc9f = bpy.context.scene
        s.lipsync_fps = sc9f.render.fps / sc9f.render.fps_base
    except Exception:
        pass


class FSKR_UL_lipsegs(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index):
        row = layout.row(align=True)
        op = row.operator("fskr.lipsync_seek", text="%d" % item.fs,
                          emboss=False)
        op.idx = index
        sub = row.row(align=True)
        sub.ui_units_x = 3.4
        sub.prop(item, "vowel", text="")
        row.label(text="%d fr" % (item.fe - item.fs + 1))


_VOWEL_COLORS = {'_A': (1.0, 0.35, 0.30), '_I': (1.0, 0.85, 0.30),
                 '_U': (0.35, 0.60, 1.0), '_E': (0.40, 0.90, 0.40),
                 '_O': (0.90, 0.50, 1.0)}


_LIPSRV = {"srv": None, "thread": None, "port": 0,
           "lock": threading.Lock(), "queue": [],
           "init": "{}", "state": "{}", "html": "", "rev": 0}


def _lipsync_sync_off():
    """웹 오디오 동기 재생 종료: 블렌더 재생 정지 + 씬 오디오 복원."""
    if not _LIPSRV.get("sync"):
        return
    _LIPSRV["sync"] = False
    try:
        _stop_playback()
    except Exception:
        pass
    try:
        bpy.context.scene.use_audio = bool(_LIPSRV.get("aud_prev", True))
    except Exception:
        pass
    try:
        pm9 = _LIPSRV.get("sync_prev_mode")
        if pm9:
            bpy.context.scene.sync_mode = pm9
        _LIPSRV["sync_prev_mode"] = None
    except Exception:
        pass


def _lipsrv_stop():
    _lipsync_sync_off()
    if _LIPSRV.get("pad_mute"):
        try:
            sc9 = bpy.context.scene
            pad9, _v9 = _lipsync_padinfo(sc9.fskr, sc9.fskr.rig)
            if pad9 is not None:
                dp9 = 'pose.bones["%s"].location' % pad9.name
                for fc9 in _action_fcurves(
                        sc9.fskr.rig.animation_data):
                    if fc9.data_path == dp9:
                        fc9.mute = False
        except Exception:
            pass
        _LIPSRV["pad_mute"] = False
    srv = _LIPSRV.get("srv")
    if srv is not None:
        try:
            srv.shutdown()
        except Exception:
            pass
        try:
            srv.server_close()
        except Exception:
            pass
    _LIPSRV["srv"] = None
    _LIPSRV["thread"] = None


_MK_PREFIX = "LS_"


def _lipsync_clusters(s, gap=8, mn9=2):
    """개방도 배열에서 말소리 덩어리 [(시작프레임, 끝프레임)] 추출.

    gap 이하로 떨어진 소리는 하나로 합치고, mn9보다 짧은 덩어리는 버린다.
    """
    try:
        opens = json.loads(s.lipsync_open or "[]")
    except Exception:
        opens = []
    if not opens:
        return []
    start = int(s.lipsync_start)
    gap = max(1, int(gap))
    mn9 = max(1, int(mn9))
    th9 = 0.02
    runs = []
    i9 = 0
    n9 = len(opens)
    while i9 < n9:
        if opens[i9] <= th9:
            i9 += 1
            continue
        a9 = i9
        while i9 < n9 and opens[i9] > th9:
            i9 += 1
        runs.append((a9, i9 - 1))
    if not runs:
        return []
    merged = [list(runs[0])]
    for a9, b9 in runs[1:]:
        if a9 - merged[-1][1] - 1 <= gap:
            merged[-1][1] = b9
        else:
            merged.append([a9, b9])
    return [(start + a9, start + b9) for a9, b9 in merged
            if (b9 - a9 + 1) >= mn9]


def _lipsync_markers_clear(scene):
    """이 애드온이 만든 마커만 제거 (사용자 마커는 보존)."""
    n9 = 0
    try:
        for mk9 in list(scene.timeline_markers):
            if mk9.name.startswith(_MK_PREFIX):
                scene.timeline_markers.remove(mk9)
                n9 += 1
    except Exception:
        pass
    return n9


def _mk_names(ab9, i9):
    """클러스터 항목에서 시작/끝 마커 이름 결정.

    둘 다 비어 있으면 LS_01A / LS_01B, 한쪽만 적었으면 그 이름을
    양쪽에 같이 쓴다. 애드온 마커임을 알 수 있도록 접두사를 붙인다.
    """
    def cl9n(v9):
        v9 = str(v9 or "").strip()
        return v9[:56]
    a9 = cl9n(ab9[2] if len(ab9) > 2 else "")
    b9 = cl9n(ab9[3] if len(ab9) > 3 else "")
    if not a9 and not b9:
        return ("%s%02dA" % (_MK_PREFIX, i9),
                "%s%02dB" % (_MK_PREFIX, i9))
    if not a9:
        a9 = b9
    if not b9:
        b9 = a9
    pf9 = _MK_PREFIX
    return (a9 if a9.startswith(pf9) else pf9 + a9,
            b9 if b9.startswith(pf9) else pf9 + b9)


def _lipsync_markers_build(s, scene):
    """편집기에서 만든 클러스터의 시작/끝에 타임라인 마커 생성.

    애드온이 만든 마커(LS_)만 지우고 다시 만들므로 사용자 마커는 보존.
    """
    _lipsync_markers_clear(scene)
    try:
        cl9 = json.loads(s.lipsync_clus or "[]")
    except Exception:
        cl9 = []
    n9 = 0
    for i9, ab9 in enumerate(cl9, 1):
        try:
            a9, b9 = int(ab9[0]), int(ab9[1])
        except Exception:
            continue
        na9, nb9 = _mk_names(ab9, i9)
        try:
            scene.timeline_markers.new(na9, frame=a9)
            scene.timeline_markers.new(nb9, frame=b9)
            n9 += 2
        except Exception:
            pass
    return n9


def _lipsync_audio_dur(s):
    """립싱크 오디오 길이(초). 알 수 없으면 None."""
    import os as _os
    ap9 = str(getattr(s, "lipsync_audio", ""))
    if not ap9:
        return None
    apf = bpy.path.abspath(ap9)
    if not _os.path.exists(apf):
        return None
    if apf.lower().endswith(".wav"):
        try:
            import wave
            wf9 = wave.open(apf, 'rb')
            try:
                sr9 = wf9.getframerate()
                nf9 = wf9.getnframes()
            finally:
                wf9.close()
            if sr9:
                return float(nf9) / float(sr9)
        except Exception:
            pass
    # 시퀀서 사운드 스트립에서 회수
    try:
        for snd9 in bpy.data.sounds:
            if bpy.path.abspath(snd9.filepath) == apf:
                import aud as _aud
                return float(_aud.Sound(apf).length)
    except Exception:
        pass
    return None


def _lipsync_resample(s, scene):
    """씬 프레임 레이트 변경을 립싱크에 반영 (시간 기준 재배치).

    개방도 배열을 새 fps로 리샘플하고 구간·키프레임 범위를 옮긴다.
    변경이 있었으면 True (호출자가 다시 굽기를 실행해야 함).
    """
    new9 = scene.render.fps / scene.render.fps_base
    old9 = float(getattr(s, "lipsync_fps", 0.0) or 0.0)
    if old9 <= 0.0:
        # 구파일: 분석 fps 기록이 없음 → 오디오 길이로 역산
        # (개방도 배열은 분석 당시 fps로 프레임당 1개)
        try:
            opens0 = json.loads(s.lipsync_open or "[]")
        except Exception:
            opens0 = []
        dur0 = _lipsync_audio_dur(s)
        if opens0 and dur0 and dur0 > 0.05:
            est0 = len(opens0) / dur0
            # 흔한 프레임 레이트로 스냅 (분석 오차 흡수)
            for c0 in (23.976, 24.0, 25.0, 29.97, 30.0, 48.0,
                       50.0, 59.94, 60.0):
                if abs(est0 - c0) / c0 < 0.02:
                    est0 = c0
                    break
            old9 = est0
        else:
            s.lipsync_fps = new9  # 판단 불가: 현재 fps를 기준으로 기록
            return False
    if abs(new9 - old9) < 1e-6:
        return False
    try:
        opens = json.loads(s.lipsync_open or "[]")
    except Exception:
        opens = []
    n_old = len(opens)
    if n_old == 0:
        s.lipsync_fps = new9
        return False
    start = int(s.lipsync_start)
    r9 = new9 / old9
    n_new = max(1, int(round(n_old * r9)))
    res9 = []
    for i9 in range(n_new):
        t9 = i9 / r9  # 옛 인덱스 공간에서의 위치
        i0 = min(int(t9), n_old - 1)
        i1 = min(i0 + 1, n_old - 1)
        f9 = t9 - int(t9)
        res9.append(round(opens[i0] * (1.0 - f9) + opens[i1] * f9, 4))
    # 옛 범위의 립싱크 키 제거 (다시 굽기 전 정리)
    try:
        for adid, dp9, ix9 in _lipsync_channels(s, s.rig):
            for fc9 in _action_fcurves(
                    adid.animation_data if adid else None):
                if fc9.data_path == dp9 and fc9.array_index == ix9:
                    pts9 = fc9.keyframe_points
                    for j9 in range(len(pts9) - 1, -1, -1):
                        if start <= pts9[j9].co[0] <= start + n_old - 1:
                            pts9.remove(pts9[j9], fast=True)
                    fc9.update()
    except Exception:
        pass
    for it in s.lipsync_segs:
        fs9 = start + int(round((it.fs - start) * r9))
        fe9 = start + int(round((it.fe - start) * r9))
        it.fs = fs9
        it.fe = max(fs9, fe9)
    s.lipsync_open = json.dumps(res9)
    s.lipsync_fps = new9
    try:  # 클러스터도 같은 비율로 이동 후 마커 갱신
        cl9 = json.loads(s.lipsync_clus or "[]")
        s.lipsync_clus = json.dumps(
            [[start + int(round((int(e9[0]) - start) * r9)),
              start + int(round((int(e9[1]) - start) * r9)),
              str(e9[2]) if len(e9) > 2 else "",
              str(e9[3]) if len(e9) > 3 else ""]
             for e9 in cl9])
        if cl9:
            _lipsync_markers_build(s, scene)
    except Exception:
        pass
    return True


def _lipsync_channels(s, rig):
    """립싱크가 굽는 채널 목록 [(id, data_path, index)] (중복 제거)."""
    out = []
    if rig is None:
        return out
    for it in s.mocap_map:
        if not it.arkit.startswith('_'):
            continue
        if it.tgt == 'KEY':
            nm = str(it.mesh)
            mo = (bpy.data.objects.get(nm)
                  if nm and nm != "__DEF__" else s.mesh)
            kb = (mo.data.shape_keys.key_blocks.get(it.key)
                  if (mo and mo.type == 'MESH'
                      and mo.data.shape_keys) else None)
            if kb is not None and it.key != NONE:
                out.append((kb.id_data, kb.path_from_id() + ".value", 0))
            continue
        pb = rig.pose.bones.get(it.ctl)
        if pb is None:
            continue
        c = it.comp
        ctype = str(pb.get("fskr_type", 'SLD_H'))
        if c in ('VAL', 'VALN'):
            if ctype not in ('SLD_H', 'SLD_V'):
                continue
            axis = 1 if ctype == 'SLD_V' else 0
        elif c in ('XP', 'XN'):
            axis = 0
        elif c in ('YP', 'YN'):
            axis = 1
        else:
            continue
        out.append((rig, 'pose.bones["%s"].location' % pb.name, axis))
    seen = set()
    res = []
    for t in out:
        k = (id(t[0]), t[1], t[2])
        if k not in seen:
            seen.add(k)
            res.append(t)
    return res


def _lipsrv_tick():
    """서버 큐 처리 + 상태 스냅샷 (메인 스레드 타이머)."""
    if _LIPSRV.get("srv") is None:
        return None
    try:
        s = bpy.context.scene.fskr
    except Exception:
        return 0.033
    with _LIPSRV["lock"]:
        q = _LIPSRV["queue"]
        _LIPSRV["queue"] = []
    stop = False
    need_ref = False
    for path, pl in q:
        try:
            if path == "/frame":
                f9w = int(pl.get("f", 0))
                sync9f = bool(_LIPSRV.get("sync"))
                if sync9f:
                    # 실제 재생 중이 아니면 동기 모드가 낡은 것 → 해제
                    pl9f = False
                    try:
                        for w9f in bpy.context.window_manager.windows:
                            if getattr(w9f.screen,
                                       "is_animation_playing", False):
                                pl9f = True
                                break
                    except Exception:
                        pass
                    if not pl9f:
                        _lipsync_sync_off()
                        sync9f = False
                if sync9f:
                    # 자체 재생 중: 크게 어긋날 때만 드물게 보정
                    import time as _t9
                    dif9 = abs(int(bpy.context.scene.frame_current)
                               - f9w)
                    if dif9 > 4 and (_t9.time()
                                     - _LIPSRV.get("corr_t", 0.0)
                                     > 0.25):
                        _LIPSRV["corr_t"] = _t9.time()
                        try:
                            bpy.context.scene.frame_set(f9w)
                        except Exception:
                            pass
                else:
                    try:
                        bpy.context.scene.frame_set(f9w)
                    except Exception:
                        bpy.context.scene.frame_current = f9w
            elif path == "/play":
                try:
                    playing = bool(
                        bpy.context.screen
                        and bpy.context.screen.is_animation_playing)
                except Exception:
                    playing = False
                if playing:
                    _stop_playback()
                else:
                    _start_playback()
            elif path == "/wplay":
                sc9w = bpy.context.scene
                try:
                    sc9w.frame_set(int(pl.get("f", sc9w.frame_current)))
                except Exception:
                    pass
                if not _LIPSRV.get("sync"):
                    _LIPSRV["sync"] = True
                    _LIPSRV["aud_prev"] = bool(sc9w.use_audio)
                    sc9w.use_audio = False  # 브라우저와 이중 재생(에코) 방지
                    try:
                        _LIPSRV["sync_prev_mode"] = str(sc9w.sync_mode)
                        sc9w.sync_mode = 'FRAME_DROP'
                    except Exception:
                        pass
                pl9w = False
                try:
                    for w9w in bpy.context.window_manager.windows:
                        if getattr(w9w.screen,
                                   "is_animation_playing", False):
                            pl9w = True
                            break
                except Exception:
                    pass
                if not pl9w:
                    _start_playback()
            elif path == "/pad":
                pad9, _v9 = _lipsync_padinfo(s, s.rig)
                if pad9 is not None:
                    try:
                        if not _LIPSRV.get("pad_mute"):
                            # 키프레임이 덮어쓰지 않게 드래그 중 음소거
                            _LIPSRV["pad_mute"] = True
                            dp9 = ('pose.bones["%s"].location'
                                   % pad9.name)
                            for fc9 in _action_fcurves(
                                    s.rig.animation_data):
                                if fc9.data_path == dp9:
                                    fc9.mute = True
                        pad9.location[0] = float(pl.get("x", 0.0)) * PAD
                        pad9.location[1] = float(pl.get("y", 0.0)) * PAD
                    except Exception:
                        pass
            elif path == "/padend":
                pad9, _v9 = _lipsync_padinfo(s, s.rig)
                if pad9 is not None:
                    try:
                        pad9.location[0] = 0.0
                        pad9.location[1] = 0.0
                        dp9 = ('pose.bones["%s"].location' % pad9.name)
                        for fc9 in _action_fcurves(s.rig.animation_data):
                            if fc9.data_path == dp9:
                                fc9.mute = False
                    except Exception:
                        pass
                _LIPSRV["pad_mute"] = False
                need_ref = True
            elif path == "/trim":
                try:
                    _lipsync_trim(s, int(pl.get("a", 0)),
                                  int(pl.get("b", 0)))
                    _LIPSRV["rev"] += 1
                    need_ref = True
                except Exception:
                    pass
            elif path == "/silence":
                try:
                    _lipsync_silence(s, int(pl.get("a", 0)),
                                     int(pl.get("b", 0)))
                    _LIPSRV["rev"] += 1
                    need_ref = True
                except Exception:
                    pass
            elif path == "/volume":
                try:
                    _lipsync_volume(s, int(pl.get("a", 0)),
                                    int(pl.get("b", 0)),
                                    float(pl.get("g", 1.0)),
                                    bool(pl.get("rc", 1)))
                    _LIPSRV["rev"] += 1
                    need_ref = True
                except Exception:
                    pass
            elif path == "/aundo":
                try:
                    ah9 = _LIPSRV.get("ahist") or []
                    idx9 = _LIPSRV.get("ahidx", len(ah9) - 1)
                    if ah9 and idx9 > 0:
                        _LIPSRV["ahidx"] = idx9 - 1
                        _lipsync_restore(s, ah9[idx9 - 1])
                        _LIPSRV["rev"] += 1
                        need_ref = True
                except Exception:
                    pass
            elif path == "/goto":
                try:
                    i9g = int(pl.get("i", -1))
                    ah9 = _LIPSRV.get("ahist") or []
                    if 0 <= i9g < len(ah9):
                        _LIPSRV["ahidx"] = i9g
                        _lipsync_restore(s, ah9[i9g])
                        _LIPSRV["rev"] += 1
                        need_ref = True
                except Exception:
                    pass
            elif path == "/hdel":
                try:
                    i9d = int(pl.get("i", -1))
                    ah9 = _LIPSRV.get("ahist") or []
                    idx9 = _LIPSRV.get("ahidx", len(ah9) - 1)
                    if 0 <= i9d < len(ah9) and i9d != idx9:
                        apd9 = str(ah9[i9d].get("audio", ""))
                        try:
                            others9 = [str(e9.get("audio", ""))
                                       for j9, e9 in enumerate(ah9)
                                       if j9 != i9d]
                            cur9 = str(getattr(s, "lipsync_audio", ""))
                            if (apd9 and "fskr_lipsync" in apd9
                                    and apd9 not in others9
                                    and apd9 != cur9):
                                import os as _os9
                                _os9.remove(bpy.path.abspath(apd9))
                        except Exception:
                            pass
                        ah9.pop(i9d)
                        if i9d < idx9:
                            _LIPSRV["ahidx"] = idx9 - 1
                        try:
                            init9d = json.loads(
                                _LIPSRV.get("init") or "{}")
                            (init9d["hist"],
                             init9d["hidx"]) = _lipsync_hist_json()
                            with _LIPSRV["lock"]:
                                _LIPSRV["init"] = json.dumps(init9d)
                        except Exception:
                            pass
                        _LIPSRV["rev"] += 1
                except Exception:
                    pass
            elif path == "/movea":
                try:
                    _lipsync_move(s, int(pl.get("a", 0)),
                                  int(pl.get("b", 0)),
                                  int(pl.get("d", 0)))
                    _LIPSRV["rev"] += 1
                    need_ref = True
                except Exception:
                    pass
            elif path == "/ontop":
                _LIPSRV["ontop"] = bool(pl.get("on", 1))
                _LIPSRV["top_wait"] = 0.0  # 백오프 무시
                _LIPSRV["top_miss"] = 0
                _LIPSRV["hwnd"] = None  # 창을 새로 찾아 확실히 적용
                try:
                    _lipsync_topmost_try(_LIPSRV["ontop"])
                except Exception:
                    pass
            elif path == "/clus":
                try:
                    cl9 = [[int(e9[0]), int(e9[1]),
                            str(e9[2]) if len(e9) > 2 else "",
                            str(e9[3]) if len(e9) > 3 else ""]
                           for e9 in (pl.get("clus") or [])]
                    s.lipsync_clus = json.dumps(cl9)
                    if pl.get("gap"):
                        s.lipsync_mk_gap = max(1, int(pl.get("gap")))
                    if pl.get("mark"):
                        _lipsync_markers_build(s, bpy.context.scene)
                except Exception:
                    pass
            elif path == "/blend":
                try:
                    s.lipsync_blend = max(0, min(12,
                                                 int(pl.get("b", 2))))
                except Exception:
                    pass
            elif path == "/favs":
                try:
                    s.lipsync_favs = json.dumps(pl.get("favs") or [])
                except Exception:
                    pass
            elif path == "/wpause":
                _lipsync_sync_off()
                try:
                    bpy.context.scene.frame_set(
                        int(pl.get("f",
                                   bpy.context.scene.frame_current)))
                except Exception:
                    pass
            elif path in ("/segs", "/apply"):
                if pl.get("clus") is not None:
                    try:
                        s.lipsync_clus = json.dumps(
                            [[int(e9[0]), int(e9[1]),
                              str(e9[2]) if len(e9) > 2 else "",
                              str(e9[3]) if len(e9) > 3 else ""]
                             for e9 in (pl.get("clus") or [])])
                        if pl.get("gap"):
                            s.lipsync_mk_gap = max(1, int(pl.get("gap")))
                        if path == "/apply":
                            _lipsync_markers_build(s, bpy.context.scene)
                    except Exception:
                        pass
                segs = pl.get("segs") or []
                s.lipsync_segs.clear()
                for e in segs:
                    it = s.lipsync_segs.add()
                    it.fs = int(e.get("fs", 0))
                    it.fe = int(e.get("fe", 0))
                    try:
                        it.px = float(e.get("px", 999.0))
                        it.py = float(e.get("py", 999.0))
                    except (TypeError, ValueError):
                        pass
                    try:
                        it.vowel = str(e.get("v", "_A"))
                    except TypeError:
                        pass
                if path == "/apply":
                    try:
                        bpy.ops.fskr.lipsync_apply(refresh=False)
                    except Exception:
                        pass
                    _LIPSRV["rev"] += 1
                    need_ref = True
            elif path == "/seqr":
                try:
                    rr9 = [[int(e9[0]), int(e9[1]), str(e9[2])]
                           for e9 in (pl.get("r") or [])]
                    s.lipsync_seqr = json.dumps(rr9, ensure_ascii=False)
                    init9q = json.loads(_LIPSRV.get("init") or "{}")
                    init9q["seqr"] = rr9
                    with _LIPSRV["lock"]:
                        _LIPSRV["init"] = json.dumps(init9q)
                except Exception:
                    pass
                if not pl.get("noapply"):
                    try:
                        bpy.ops.fskr.lipsync_apply(refresh=False)
                    except Exception:
                        pass
                    _LIPSRV["rev"] += 1
                    need_ref = True
            elif path == "/start":
                nf = int(pl.get("f", s.lipsync_start))
                old9 = int(s.lipsync_start)
                if nf != old9:
                    try:
                        opens9 = json.loads(s.lipsync_open or "[]")
                    except Exception:
                        opens9 = []
                    n9 = len(opens9)
                    # 기존 위치의 립싱크 키 제거
                    for adid, dp9, ix9 in _lipsync_channels(s, s.rig):
                        for fc9 in _action_fcurves(
                                adid.animation_data if adid else None):
                            if (fc9.data_path == dp9
                                    and fc9.array_index == ix9):
                                pts9 = fc9.keyframe_points
                                for i9 in range(len(pts9) - 1, -1, -1):
                                    if old9 <= pts9[i9].co[0] <= \
                                            old9 + n9 - 1:
                                        pts9.remove(pts9[i9], fast=True)
                                fc9.update()
                    d9 = nf - old9
                    for it in s.lipsync_segs:
                        it.fs += d9
                        it.fe += d9
                    s.lipsync_start = nf
                    try:
                        se9 = bpy.context.scene.sequence_editor
                        coll9b = ((getattr(se9, "sequences", None)
                                   or getattr(se9, "strips", None))
                                  if se9 else None)
                        for st9 in (coll9b or []):
                            if st9.name.startswith("FSKR_lipsync"):
                                st9.frame_start = nf
                    except Exception:
                        pass
                    try:
                        bpy.ops.fskr.lipsync_apply(refresh=False)
                    except Exception:
                        pass
                    _LIPSRV["rev"] += 1
                    need_ref = True
                    try:
                        init9t = json.loads(
                            _LIPSRV.get("init") or "{}")
                        init9t["start"] = int(s.lipsync_start)
                        init9t["segs"] = [
                            {"fs": int(it.fs), "fe": int(it.fe),
                             "v": it.vowel, "px": float(it.px),
                             "py": float(it.py)}
                            for it in s.lipsync_segs]
                        with _LIPSRV["lock"]:
                            _LIPSRV["init"] = json.dumps(init9t)
                    except Exception:
                        pass
            elif path == "/close":
                _lipsync_sync_off()
                stop = True
        except Exception:
            pass
    import time as _t9t
    now9t = _t9t.time()
    if "poll_t" not in _LIPSRV:
        _LIPSRV["poll_t"] = now9t  # 첫 접속 전 유예
    if (not q and not stop
            and now9t - _LIPSRV.get("poll_t", now9t) > 2.0):
        # 편집기가 상태를 폴링하지 않는 동안: 상태 재구성/창 관리/서명
        # 검사 전부 생략 (뷰포트 렉 방지). 다시 열면 즉시 복귀.
        return 0.25
    if now9t - _LIPSRV.get("fps_t", 0.0) > 1.0:
        _LIPSRV["fps_t"] = now9t
        try:
            sc9r = bpy.context.scene
            old9r = float(getattr(s, "lipsync_fps", 0.0) or 0.0)
            if _lipsync_resample(s, sc9r):
                try:
                    bpy.ops.fskr.lipsync_apply(refresh=False)
                except Exception:
                    pass
                new9r = sc9r.render.fps / sc9r.render.fps_base
                init9r = json.loads(_LIPSRV.get("init") or "{}")
                init9r["fps"] = new9r
                init9r["opens"] = json.loads(s.lipsync_open or "[]")
                init9r["start"] = int(s.lipsync_start)
                init9r["segs"] = [
                    {"fs": int(it.fs), "fe": int(it.fe),
                     "v": it.vowel, "px": float(it.px),
                     "py": float(it.py)} for it in s.lipsync_segs]
                with _LIPSRV["lock"]:
                    _LIPSRV["init"] = json.dumps(init9r)
                _LIPSRV["rev"] += 1
                _LIPSRV["padsig"] = None
                try:
                    _LIPSRV["err"] = (
                        _tr("프레임 레이트가 %.4g → %.4g로 바뀌어 "
                            "립싱크를 재배치했습니다") % (old9r, new9r))
                    print("[FSKR] fps %.4g -> %.4g: lipsync re-timed"
                          % (old9r, new9r))
                except Exception:
                    pass
        except Exception:
            pass
    if now9t - _LIPSRV.get("top_t", 0.0) > 0.25:
        _LIPSRV["top_t"] = _t9t.time()
        try:
            _lipsync_topmost_try(_LIPSRV.get("ontop", True))
        except Exception:
            pass
    if need_ref:
        _LIPSRV["padsig"] = None  # 자체 굽기는 외부 편집으로 안 봄
        try:
            bpy.context.scene.frame_set(
                bpy.context.scene.frame_current)
        except Exception:
            pass
        try:
            for win9 in bpy.context.window_manager.windows:
                for ar9 in win9.screen.areas:
                    ar9.tag_redraw()
        except Exception:
            pass
    try:
        playing = bool(bpy.context.screen
                       and bpy.context.screen.is_animation_playing)
    except Exception:
        playing = False
    import time as _t9s
    if (not playing and not _LIPSRV.get("pad_mute")
            and _t9s.time() - _LIPSRV.get("sig_t", 0.0) > 2.0):
        _LIPSRV["sig_t"] = _t9s.time()
        try:
            sig9 = _lipsync_pad_sig(s)
            if (sig9 is not None
                    and _LIPSRV.get("padsig") is not None
                    and sig9 != _LIPSRV.get("padsig")):
                # 돕시트/타임라인에서 키가 수정됨 → 역산해 반영
                if _lipsync_segs_from_curves(s):
                    init9s = json.loads(_LIPSRV.get("init") or "{}")
                    init9s["segs"] = [
                        {"fs": int(it.fs), "fe": int(it.fe),
                         "v": it.vowel, "px": float(it.px),
                         "py": float(it.py)}
                        for it in s.lipsync_segs]
                    with _LIPSRV["lock"]:
                        _LIPSRV["init"] = json.dumps(init9s)
                    _LIPSRV["rev"] += 1
            _LIPSRV["padsig"] = sig9
        except Exception:
            pass
    vals9 = {}
    try:
        pad9v, vmap9v = _lipsync_padinfo(s, s.rig)
        if pad9v is not None:
            mo9 = _ctl_mesh_get(pad9v) or s.mesh
            kd9 = (mo9.data.shape_keys
                   if mo9 and mo9.type == 'MESH' else None)
            if kd9:
                for vw9v, pos9v in vmap9v.items():
                    sl9v = _lipsync_slot_of(pos9v[0], pos9v[1])
                    nm9v = str(pad9v.get("fskr_" + sl9v, ""))
                    kb9v = kd9.key_blocks.get(nm9v) if nm9v else None
                    if kb9v is not None:
                        vals9[vw9v] = round(float(kb9v.value), 4)
    except Exception:
        pass
    hj9, hx9 = _lipsync_hist_json()
    st_d = {"frame": bpy.context.scene.frame_current,
            "playing": playing, "rev": _LIPSRV["rev"],
            "vals": vals9, "hist": hj9, "hidx": hx9,
            "err": str(_LIPSRV.get("err", ""))}
    with _LIPSRV["lock"]:
        _LIPSRV["state"] = json.dumps(st_d)
    if stop:
        _lipsrv_stop()
        return None
    return 0.033


class _LipsyncHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, body, ctype="application/json"):
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        with _LIPSRV["lock"]:
            if self.path == "/":
                self._send(_LIPSRV["html"], "text/html")
            elif self.path == "/init":
                import time as _t9p
                _LIPSRV["poll_t"] = _t9p.time()
                _LIPSRV["top_miss"] = 0
                _LIPSRV["top_wait"] = 0.0
                _LIPSRV["err"] = ""  # 지난 알림 정리
                self._send(_LIPSRV["init"])
            elif self.path == "/state":
                import time as _t9p
                _LIPSRV["poll_t"] = _t9p.time()
                self._send(_LIPSRV["state"])
            elif self.path == "/audio":
                data = _LIPSRV.get("audio") or b""
                mime = _LIPSRV.get("amime", "application/octet-stream")
                rng = self.headers.get("Range")
                if rng and rng.startswith("bytes=") and data:
                    try:
                        part = rng[6:].split("-")
                        st9 = int(part[0] or 0)
                        en9 = int(part[1]) if part[1] else len(data) - 1
                        en9 = min(en9, len(data) - 1)
                        chunk = data[st9:en9 + 1]
                        self.send_response(206)
                        self.send_header("Content-Type", mime)
                        self.send_header("Accept-Ranges", "bytes")
                        self.send_header(
                            "Content-Range", "bytes %d-%d/%d"
                            % (st9, en9, len(data)))
                        self.send_header("Content-Length",
                                         str(len(chunk)))
                        self.end_headers()
                        self.wfile.write(chunk)
                        return
                    except Exception:
                        pass
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404)
                self.end_headers()

    def do_POST(self):
        try:
            ln = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(ln).decode("utf-8") if ln else "{}"
            payload = json.loads(body or "{}")
        except Exception:
            payload = {}
        with _LIPSRV["lock"]:
            _LIPSRV["queue"].append((self.path, payload))
        self._send('{"ok":1}')


_LIPSYNC_HTML = """<!doctype html><html translate="no" class="notranslate"><head><meta charset="utf-8">
<meta name="google" content="notranslate">
<title>{TITLE}</title><style>
body{margin:0;background:#17171b;color:#ddd;font-family:sans-serif;
 user-select:none;overflow:hidden}
#bar{display:flex;gap:8px;align-items:center;padding:10px 12px;
 position:relative;min-height:254px}
#vs{position:absolute;left:50%;top:50%;
 transform:translate(-50%,-50%);display:flex;flex-direction:column;
 gap:6px;align-items:center}
button{border:0;border-radius:4px;padding:9px 14px;font-weight:700;
 cursor:pointer;font-size:14px}
.v{width:46px;color:#111}
#vs .v{height:34px;padding:0;font-size:16px}
#apply{background:#3d7de0;color:#fff}
#close{background:#555;color:#fff}
#loop{background:#444;color:#aaa}
#loop.on{background:#2e8f5b;color:#fff}
#akey{background:#444;color:#aaa}
#akey.on{background:#8a5ad0;color:#fff}
.lb{min-width:104px}
.cb{width:auto;min-width:0;padding:6px 12px;font-size:12px;
 background:#3a3a44;color:#eee;white-space:nowrap}
.cb:hover{background:#4a4a56}
#clbox{display:flex;flex-direction:column;gap:4px;
 background:#232329;border:1px solid #444;border-radius:6px;
 padding:6px}
#clrow{display:flex;gap:6px;align-items:center;flex-wrap:wrap;
 justify-content:flex-end}
.cni{width:104px;background:#2a2a31;color:#eee;border:1px solid #444;
 border-radius:4px;padding:5px;font-size:12px}
.cni:focus{outline:none;border-color:#ff5a50}
#on9{background:#444;color:#aaa}
#on9.on{background:#c47f2e;color:#fff}
#wmv{background:transparent;color:#6ea8ff;
 border:1px solid #6ea8ff}
#wmv.on{background:#3d7de0;color:#fff;border-color:#3d7de0}
#selm{background:transparent;color:#7fd39a;
 border:1px solid #7fd39a}
#selm.on{background:#2e8f5b;color:#fff;border-color:#2e8f5b}
#volrc{background:#c47f2e;color:#fff}
#ontop{background:transparent;color:#8a8a95;
 border:1px solid #55555f}
#ontop.on{background:#3d7de0;color:#fff;border-color:#3d7de0}

canvas{display:block}
#hint{color:#888;font-size:11px;margin-left:10px}
#pad{background:#26262c;border:1px solid #444;border-radius:6px;
 cursor:crosshair;display:none}
.fb{background:#444;color:#ddd;border:0;border-radius:4px;
 padding:3px 9px;font-size:12px;cursor:pointer}
.tb{background:#2c2c33;color:#ddd;border:1px solid #444;
 border-radius:4px;width:46px;padding:6px 0;cursor:pointer;
 font-size:14px}
.tb:hover{background:#3a3a44}
.fb{white-space:nowrap}
.fb:hover{background:#5a5a64}
.fb.on{background:#8a5ad0;color:#fff}
#fed{display:none;position:absolute;top:-10px;left:50%;
 transform:translateX(-50%);background:#2c2c33;border:1px solid #555;
 border-radius:6px;padding:8px;gap:6px;align-items:center;z-index:9}
</style></head><body>
<div style="display:flex;gap:6px;justify-content:center;
 padding:8px 0 4px">
 <button class="tb" onclick="trStep(-1)"
  title="{TR_PV}">&lt;</button>
 <button class="tb" style="background:#a04848;color:#fff"
  onclick="trStop()" title="{TR_ST}">&#9209;</button>
 <button class="tb" id="trpp"
  style="background:#2e8f5b;color:#fff"
  onclick="trToggle()" title="{TR_PL}">&#9205;</button>
 <button class="tb" onclick="trStep(1)"
  title="{TR_NX}">&gt;</button>
</div>
<canvas id="cv" height="286"></canvas>
<div id="lvbar" style="display:none;gap:6px;align-items:center;padding:6px 10px">
 <span style="opacity:.8">{LV_T}</span>
 <button class="lb" style="background:#8fa3bf;color:#111" onclick="setLevel('_U')">{LV_C}</button>
 <button class="lb" style="background:#ffd94d;color:#111" onclick="setLevel('_E')">{LV_H}</button>
 <button class="lb" style="background:#ff5a4d;color:#111" onclick="setLevel('_A')">{LV_O}</button>
 <span style="margin-left:22px;opacity:.8">{SQ_T}</span>
 <select id="seqsel" style="background:#26262c;color:#ddd;border:1px solid #444;border-radius:4px;padding:7px"></select>
 <button class="lb" style="background:#6fc3a8;color:#111" onclick="applySeq(document.getElementById('seqsel').value)">{SQ_SET}</button>
 <button class="lb" onclick="applySeq('')">{SQ_CLR}</button>
</div>
<div id="bar">
 <div style="display:flex;flex-direction:column;gap:6px">
  <div style="display:flex;gap:8px;align-items:center">
   <button id="loop" class="on lb" onclick="toggleLoop()">{LOOP}</button>
   <span style="color:#888;font-size:12px">{START}</span>
   <input id="sf" type="number" style="width:72px;background:#26262c;
    color:#ddd;border:1px solid #444;border-radius:4px;padding:7px">
  </div>
  <div style="display:flex;gap:8px;align-items:center">
   <button id="akey" class="on lb" onclick="toggleAkey()">{AKEY}</button>
   <span style="color:#888;font-size:12px">{BLEND}</span>
   <input id="bl" type="number" min="0" max="12" style="width:52px;
    background:#26262c;color:#ddd;border:1px solid #444;border-radius:4px;
    padding:7px">
  </div>
  <div style="display:flex;gap:8px;align-items:center">
   <button id="on9" class="lb" onclick="onionTgl()"
    title="{ONION}">{ONION}</button>
   <span id="onset" style="display:none;flex-direction:column;gap:4px">
    <span style="display:flex;gap:4px;align-items:center">
     <span style="color:#888;font-size:12px">{ONFR}</span>
     <input id="on_n" type="number" min="1" max="24"
      style="width:46px;background:#26262c;color:#ddd;
      border:1px solid #444;border-radius:4px;padding:7px 5px">
     <input id="on_c1" type="color" title="&#9668;" style="width:30px;
      height:30px;border:0;background:none;padding:0;cursor:pointer">
     <input id="on_c2" type="color" title="&#9658;" style="width:30px;
      height:30px;border:0;background:none;padding:0;cursor:pointer">
    </span>
    <span style="display:flex;gap:4px;align-items:center">
     <span style="color:#888;font-size:12px">{ONAL}</span>
     <input id="on_a" type="number" min="0.05" max="1" step="0.05"
      style="width:58px;background:#26262c;color:#ddd;
      border:1px solid #444;border-radius:4px;padding:7px 5px">
    </span>
   </span>
  </div>
 </div>
 <div id="vs">
  <div id="fed">
   <input id="fed_n" style="width:90px;background:#1d1d22;color:#ddd;
    border:1px solid #555;border-radius:4px;padding:4px 6px">
   <input id="fed_c" type="color" style="width:34px;height:26px;
    border:0;background:none;padding:0;cursor:pointer">
   <button class="fb" onclick="fedPos()">{FV_POS}</button>
   <button class="fb" onclick="fedDel()">{FV_DEL}</button>
   <button class="fb" onclick="fedOk()">{FV_OK}</button>
  </div>
  <div style="display:flex;gap:8px;justify-content:center">
   <button class="v" style="background:#555;color:#eee"
    onclick="addSeg()">+</button>
   <button class="v" style="background:#555;color:#eee"
    onclick="delSeg()">&minus;</button>
   <span style="position:relative;display:inline-flex">
    <button class="v" style="background:#a04848;color:#fff;
     border-radius:4px 0 0 4px" onclick="cutSel()"
     title="{CUT}">&#9986;</button>
    <button style="background:#7d3838;color:#fff;border:0;
     border-radius:0 4px 4px 0;width:16px;padding:0;cursor:pointer"
     onclick="cutMenu(event)">&#9662;</button>
    <div id="cmenu" style="display:none;position:absolute;top:110%;
     left:0;background:#2c2c33;border:1px solid #555;border-radius:6px;
     padding:6px;z-index:9;flex-direction:column;gap:4px;
     white-space:nowrap">
     <button class="fb" onclick="cutPick(0)">&#9986; {CUT_A}</button>
     <button class="fb" onclick="cutPick(1)">&#9986; {CUT_B}</button>
    </div>
   </span>
   <button class="v" id="wmv"
    onclick="wavTgl()" title="{WMV}">&#9835;</button>
   <button class="v" id="selm"
    onclick="selmTgl()" title="{SELM}">&#9634;</button>
   <span title="{VOL}" style="color:#c9a35e;font-size:16px;
    align-self:center">&#128265;</span>
   <input id="volp" type="number" min="10" max="300" value="100"
    style="width:56px;background:#26262c;color:#ddd;
    border:1px solid #444;border-radius:4px;padding:7px 5px"
    title="%">
   <button class="v" style="background:#2e8f5b;color:#fff"
    onclick="volApply()" title="{VOL}">&#10003;</button>
   <button class="v" id="volrc"
    onclick="recalcApply()" title="{VOLRC}">&#8635;</button>
  </div>
  <div id="fv" style="display:flex;gap:4px;justify-content:center">
  </div>
  <div style="display:flex;gap:10px;align-items:center">
   <div id="vwl" style="width:76px;font-size:12px;color:#ccc;
    text-align:right;display:flex;flex-direction:column;gap:3px"></div>
   <canvas id="pad" width="240" height="160"></canvas>
   <div id="vwr" style="width:76px;font-size:12px;color:#ccc;
    display:flex;flex-direction:column;gap:3px"></div>
  </div>
 </div>
 <span style="flex:1"></span>
 <div style="display:flex;flex-direction:column;gap:6px;
  align-items:flex-end;align-self:stretch;
  justify-content:space-between">
  <div id="hpanel" style="display:flex;background:#232329;
   border:1px solid #444;border-radius:6px;padding:6px;
   flex-direction:column;gap:4px;white-space:nowrap;
   max-height:158px;overflow-y:auto;min-width:210px"></div>
  <div id="clbox">
   <div style="color:#888;font-size:10px;text-align:right">
    {CL_HEAD}</div>
   <div id="clrow">
    <span style="color:#aaa;font-size:11px">{CL_GAP_L}</span>
    <input id="cgap" type="number" min="1" max="120" value="8"
     title="{CL_GAP}" onchange="clusGen()"
     style="width:54px;background:#2a2a31;color:#eee;
     border:1px solid #444;border-radius:4px;padding:5px;
     text-align:center">
    <button class="cb" id="clgen" onclick="clusGen()"
     title="{CL_TIP}">{CL_GEN}</button>
    <button class="cb" id="clclr" onclick="clusClear()"
     title="{CL_CLR}">{CL_CLR_L}</button>
   </div>
   <div id="clrow">
    <button class="cb" id="clsel" onclick="clusFromSel()"
     title="{CL_SEL}">{CL_SEL_L}</button>
    <button class="cb" id="clspl" onclick="clusSplit()"
     title="{CL_SPL}">{CL_SPL_L}</button>
    <button class="cb" id="cldel" onclick="clusDelSel()"
     title="{CL_DEL}">{CL_DEL_L}</button>
   </div>
   <div id="clnm" style="display:flex;gap:6px;align-items:center;
    justify-content:flex-end;border-top:1px solid #3a3a44;
    padding-top:5px">
    <span id="clnmh" style="color:#666;font-size:11px">{CL_PICK}</span>
    <input id="cna" class="cni" placeholder="{CL_NA}" title="{CL_NM}"
     style="display:none">
    <input id="cnb" class="cni" placeholder="{CL_NB}" title="{CL_NM}"
     style="display:none">
   </div>
  </div>
  <div style="display:flex;gap:8px">
   <button class="v" id="ontop" onclick="ontopTgl()"
    title="{ONTOP}">&#128204;</button>
   <button id="apply" onclick="applySegs()">{APPLY}</button>
   <button id="close" onclick="closeWin()">{CLOSE}</button>
  </div>
 </div>
</div>
<div style="text-align:center;color:#888;font-size:11px;
 padding:0 12px 8px">{HINT}</div>
<audio id="au" src="/audio" preload="auto"></audio>
<script>
let D=null,sel=0,frame=0;
let clSel=null;  // 선택된 클러스터 인덱스
let v0=0,v1=1,selA=null,selB=null,loop=true;
let bl={f:0,t:0,playing:false};
let autoKey=true;
let hist=[],redoS=[];
let lastRev=null,localEdit=0,lastHist='',lastErr='',lastStF=null;
let clipSeg=null,sbound=null;
let mvSegs=null,mvOrig=null,mvAnchor=0,mvSelO=null;
let panX=0,panV0=0,selPx0=0,seekT=0;
let wavMv=false;
try{wavMv=localStorage.getItem('fskr_wavmv')==='1';}catch(e){}
let selMode=true,scrubT=0;
try{selMode=localStorage.getItem('fskr_selmode')!=='0';}catch(e){}
function selmTgl(){selMode=!selMode;
 try{localStorage.setItem('fskr_selmode',selMode?'1':'0');}catch(e){}
 document.getElementById('selm').classList.toggle('on',selMode);
 if(!selMode){selA=null;selB=null;draw();}}
function wavTgl(){wavMv=!wavMv;
 try{localStorage.setItem('fskr_wavmv',wavMv?'1':'0');}catch(e){}
 document.getElementById('wmv').classList.toggle('on',wavMv);}
function carveKeep(a,b,keepSet){const out=[];
 D.segs.forEach(sg=>{if(keepSet.has(sg)){out.push(sg);return;}
  if(sg.fe<a||sg.fs>b){out.push(sg);return;}
  if(sg.fs<a)out.push({fs:sg.fs,fe:a-1,v:sg.v,px:sg.px,py:sg.py});
  if(sg.fe>b)out.push({fs:b+1,fe:sg.fe,v:sg.v,px:sg.px,py:sg.py});});
 D.segs=out.sort((p,q)=>p.fs-q.fs);}
let cutMode=0;
try{cutMode=parseInt(localStorage.getItem('fskr_cutmode')||'0')||0;}
catch(e){}

const HOPS={orig:'{H_OR}',cut:'{H_CU}',move:'{H_MV}',
 sil:'{H_SI}',vol:'{H_VO}',rec:'{H_RC}'};
function histRender(){const d=document.getElementById('hpanel');
 const hs=(D&&D.hist)||[];
 if(!hs.length){d.innerHTML='<span style="color:#888;font-size:12px;'+
  'padding:2px 6px">&ndash;</span>';return;}
 let h='';
 hs.forEach((e,i)=>{
  const cur=(i===D.hidx);
  h+='<span style="display:flex;gap:6px;align-items:center">'+
   '<button class="fb" style="flex:1;text-align:left'+
   (cur?';background:#3d7de0;color:#fff':'')+'" '+
   'onclick="histGo('+i+')">'+(cur?'\u25cf ':'\u25cb ')+
   String(HOPS[e.op]||e.op).replace(/[<>&]/g,'')+
   ' \u00b7 '+e.t+'</button>'+
   (cur?'':'<button class="fb" onclick="histDel('+i+')">'+
    '\u2715</button>')+'</span>';});
 d.innerHTML=h;}
function histGo(i){if(!D||i===D.hidx)return;
 post('/goto',{i:i}).then(()=>{
  setTimeout(()=>{saveView();location.reload();},300);});}
function histDel(i){post('/hdel',{i:i}).then(async()=>{
 try{const r=await fetch('/init');const ni=await r.json();
  D.hist=ni.hist;D.hidx=ni.hidx;}catch(e){}
 histRender();});}
function cutMenu(ev){ev.stopPropagation();
 const d=document.getElementById('cmenu');
 d.style.display=(d.style.display==='flex')?'none':'flex';}
function cutPick(m){cutMode=m;
 try{localStorage.setItem('fskr_cutmode',''+m);}catch(e){}
 document.getElementById('cmenu').style.display='none';
 cutSel();}
let onTop=true;
try{onTop=localStorage.getItem('fskr_ontop')!=='0';}catch(e){}
function ontopApply(){document.getElementById('ontop')
 .classList.toggle('on',onTop);post('/ontop',{on:onTop?1:0});}
function ontopTgl(){onTop=!onTop;
 try{localStorage.setItem('fskr_ontop',onTop?'1':'0');}catch(e){}
 ontopApply();}
const T_PL='{TR_PL}',T_PA='{TR_PA}';
function trUpd(){const b=document.getElementById('trpp');
 if(!b)return;
 const pg=(D&&D.has_audio)?!au.paused:!!(bl&&bl.playing);
 b.innerHTML=pg?'&#9208;':'&#9205;';
 b.style.background=pg?'#c4a52e':'#2e8f5b';
 b.style.color=pg?'#111':'#fff';
 b.title=pg?T_PA:T_PL;}
function trToggle(){if(!D)return;
 if(!D.has_audio){post('/play');return;}
 if(au.paused)trPlay();else trPause();}
function trPlay(){if(!D)return;
 if(!D.has_audio){post('/play');return;}
 if(au.paused){
  if(selA!==null&&selB!==null)
   au.currentTime=f2t(Math.min(selA,selB));
  au.play().then(()=>post('/wplay',
   {f:Math.round(t2f(au.currentTime))})).catch(()=>post('/play'));}}
function trPause(){if(!D)return;
 if(D.has_audio){if(!au.paused){au.pause();
  post('/wpause',{f:Math.round(frame)});bl.playing=false;}}
 else post('/play');}
function trStop(){if(!D)return;trPause();seek(D.start);draw();}
function trStep(d){if(!D)return;
 const end=D.start+D.opens.length-1;
 seek(Math.max(D.start,Math.min(end,Math.round(frame)+d)));}
function volRange(){
 if(selA!==null&&selB!==null){
  const a=Math.min(selA,selB),b=Math.max(selA,selB)-1;
  return b<a?null:[a,b];}
 return [D.start,D.start+D.opens.length-1];}
function volApply(){if(!D)return;
 let g=parseFloat(document.getElementById('volp').value);
 if(isNaN(g))g=100;g=Math.max(10,Math.min(300,g))/100;
 const r=volRange();if(!r)return;
 post('/volume',{a:r[0],b:r[1],g:g,rc:0}).then(()=>{
  setTimeout(()=>{saveView();location.reload();},300);});}
function recalcApply(){if(!D)return;
 const r=volRange();if(!r)return;
 post('/volume',{a:r[0],b:r[1],g:1.0,rc:1}).then(()=>{
  setTimeout(()=>{saveView();location.reload();},300);});}
function cutSel(){if(!D)return;
 if(selA!==null&&selB!==null){
  const a=Math.min(selA,selB),b=Math.max(selA,selB)-1;
  if(b<a)return;
  if(cutMode!==1){selA=null;selB=null;}
  post(cutMode===1?'/silence':'/trim',{a:a,b:b}).then(()=>{
   setTimeout(()=>{saveView();location.reload();},300);});
  return;}
 const fr=Math.floor(frame);
 const i=D.segs.findIndex(sg=>sg.fs<fr&&fr<=sg.fe);
 if(i<0)return;
 pushHist();const sg=D.segs[i];
 D.segs.push({fs:fr,fe:sg.fe,v:sg.v,px:sg.px,py:sg.py});
 sg.fe=fr-1;
 D.segs.sort((p,q)=>p.fs-q.fs);
 draw();pushSegs();}
function snap(){return {s:JSON.parse(JSON.stringify(D.segs)),
 c:JSON.parse(JSON.stringify(D.clus||[]))};}
function restore(sn){if(!sn)return;
 if(Array.isArray(sn)){D.segs=sn;return;}  // 옛 형식
 D.segs=sn.s;D.clus=sn.c||[];
 if(clSel!==null&&clSel>=D.clus.length)clSel=null;}
function pushHist(){hist.push(snap());
 if(hist.length>50)hist.shift();redoS=[];}
function undo(){if(!D)return;
 if(!hist.length){
  if((D.hidx||0)>0){post('/aundo').then(()=>{
   setTimeout(()=>{saveView();location.reload();},300);});}
  return;}
 redoS.push(snap());
 restore(hist.pop());
 sel=Math.max(0,Math.min(sel,D.segs.length-1));
 draw();pushSegs();clusPush(true);}
function redoFn(){if(!redoS.length||!D)return;hist.push(snap());
 restore(redoS.pop());
 sel=Math.max(0,Math.min(sel,D.segs.length-1));
 draw();pushSegs();clusPush(true);}
const FVC=['#ff5a4d','#ffd94d','#5a99ff','#66e666',
 '#e680ff','#ff9a3d','#4dd6c9','#c9c9c9','#b28cff','#7fe08a'];
function favNorm(){D.favs=(D.favs||[]).map((f,i)=>Array.isArray(f)
 ?{n:'F'+(i+1),c:FVC[i%FVC.length],x:f[0],y:f[1]}:f);}
let favEditMode=false,favAct=-1;
function favActive(){const sg=D&&D.segs[sel];if(!sg)return -1;
 const p=segPos(sg);if(!p)return -1;favNorm();
 for(let i=0;i<(D.favs||[]).length;i++){const f=D.favs[i];
  if(Math.abs(f.x-p[0])<0.015&&Math.abs(f.y-p[1])<0.015)return i;}
 return -1;}
function favRender(){const d=document.getElementById('fv');
 if(!D||!D.haspad){d.innerHTML='';return;}
 favNorm();
 let h='<button class="fb" onclick="favAdd()">\u2605+</button>'+
  '<button class="fb'+(favEditMode?' on':'')+'" '+
  'onclick="favEditTgl()" title="{FV_EDT}">\u270e</button>';
 D.favs.forEach((f,i)=>{
  const st9=(i===favAct)
   ?'background:'+f.c+';color:#111;border:1px solid '+f.c
   :'background:transparent;color:'+f.c+';border:1px solid '+f.c;
  h+='<button class="fb" style="'+st9+'" '+
   'onclick="favClick('+i+')" '+
   'oncontextmenu="return favEditCtx('+i+',event)" '+
   'title="'+f.x.toFixed(2)+', '+f.y.toFixed(2)+'">'+
   String(f.n).replace(/[<>&"]/g,'')+'</button>';});
 d.innerHTML=h;}
function favEditTgl(){favEditMode=!favEditMode;
 if(!favEditMode)document.getElementById('fed').style.display='none';
 favRender();}
function favClick(i){if(favEditMode)favEdit(i);else favUse(i);}
function favEditCtx(i,ev){ev.preventDefault();favEdit(i);return false;}
function favAdd(){const sg=D&&D.segs[sel];if(!sg)return;
 const p=segPos(sg);if(!p)return;favNorm();
 if(D.favs.length>=10)return;
 let nm=prompt('{FV_ASK}','F'+(D.favs.length+1));
 if(nm===null)return;nm=nm.trim()||('F'+(D.favs.length+1));
 D.favs.push({n:nm,c:FVC[D.favs.length%FVC.length],
  x:Math.round(p[0]*10000)/10000,y:Math.round(p[1]*10000)/10000});
 post('/favs',{favs:D.favs});favRender();}
function favUse(i){const sg=D&&D.segs[sel];if(!sg)return;
 favNorm();const f=D.favs[i];if(!f)return;
 pushHist();sg.px=f.x;sg.py=f.y;sg.v=nearestV(f.x,f.y);
 draw();pushSegs();post('/padend',{});}
function favEdit(i){favNorm();
 const f=D.favs[i];if(!f)return;
 const ed=document.getElementById('fed');
 ed.style.display='flex';ed.dataset.i=i;
 document.getElementById('fed_n').value=f.n;
 document.getElementById('fed_c').value=f.c;}
function fedF(){return D.favs[parseInt(
 document.getElementById('fed').dataset.i)];}
function fedPos(){const f=fedF(),sg=D&&D.segs[sel];
 if(!f||!sg)return;const p=segPos(sg);if(!p)return;
 f.x=Math.round(p[0]*10000)/10000;f.y=Math.round(p[1]*10000)/10000;}
function fedDel(){const i=parseInt(
 document.getElementById('fed').dataset.i);
 D.favs.splice(i,1);post('/favs',{favs:D.favs});
 document.getElementById('fed').style.display='none';favRender();}
function fedOk(){const f=fedF();if(f){
 f.n=document.getElementById('fed_n').value.trim()||f.n;
 f.c=document.getElementById('fed_c').value;
 post('/favs',{favs:D.favs});}
 document.getElementById('fed').style.display='none';favRender();}
let dragMode=null,dragAnchor=0,lastPost=0;
let dragIdx=0,dragSide='fs',dragOff=0,dragMoved=false;
const COLORS={'_A':'#ff5a4d','_I':'#ffd94d','_U':'#5a99ff',
 '_E':'#66e666','_O':'#e680ff','_N':'#8a8a8a'};
const cv=document.getElementById('cv'),ctx=cv.getContext('2d');
const pad=document.getElementById('pad'),px9=pad.getContext('2d');
let padDrag=false,lastPad=0;
let onion={on:false,n:5,c1:'#ff5555',c2:'#5588ff',a:0.5};
try{const o9=JSON.parse(localStorage.getItem('fskr_onion')||'null');
 if(o9&&typeof o9==='object')onion=Object.assign(onion,o9);}catch(e){}
function onionSave(){try{localStorage.setItem('fskr_onion',
 JSON.stringify(onion));}catch(e){}}
function onionBtn(){document.getElementById('on9')
 .classList.toggle('on',onion.on);
 document.getElementById('onset').style.display=
  onion.on?'inline-flex':'none';
 document.getElementById('on_n').value=onion.n;
 document.getElementById('on_c1').value=onion.c1;
 document.getElementById('on_c2').value=onion.c2;
 document.getElementById('on_a').value=onion.a;}
function onionTgl(){onion.on=!onion.on;onionSave();onionBtn();draw();}
['on_n','on_c1','on_c2','on_a'].forEach(id=>{
 document.getElementById(id).addEventListener('input',()=>{
  onion.n=Math.max(1,Math.min(24,parseInt(
   document.getElementById('on_n').value)||5));
  onion.c1=document.getElementById('on_c1').value;
  onion.c2=document.getElementById('on_c2').value;
  onion.a=Math.max(0.05,Math.min(1,parseFloat(
   document.getElementById('on_a').value)||0.5));
  onionSave();draw();});});
function p2c(x,y){return [120+x*104,80-y*64];}
function c2p(e){const r=pad.getBoundingClientRect();
 let x=((e.clientX-r.left)-120)/104,y=(80-(e.clientY-r.top))/64;
 return [Math.max(-1,Math.min(1,x)),Math.max(-1,Math.min(1,y))];}
function nearestV(x,y){let bv='_A',bd=1e9;
 for(const k in (D.vmap||{})){const v=D.vmap[k];
  const d=(v[0]-x)*(v[0]-x)+(v[1]-y)*(v[1]-y);
  if(d<bd){bd=d;bv=k;}}return bv;}
function padSlots(){const sl={};
 for(const k in (D.vmap||{})){const q=D.vmap[k];
  const sx=Math.abs(q[0])<0.35?0:(q[0]>0?1:-1);
  const sy=Math.abs(q[1])<0.35?0:(q[1]>0?1:-1);
  const nm=sy>0?(sx>0?'UR':(sx<0?'UL':'U'))
   :(sy<0?(sx>0?'DR':(sx<0?'DL':'D')):(sx>0?'R':'L'));
  sl[nm]=k;}
 return sl;}
function padWeights(x,y){const sl=padSlots();
 const ex=n=>sl[n]?1:0;
 const u=Math.max(-1,Math.min(1,x)),v=Math.max(-1,Math.min(1,y));
 const ar=Math.max(0,u),al=Math.max(0,-u);
 const bu=Math.max(0,v),bn=Math.max(0,-v);
 const au=Math.abs(u),av=Math.abs(v);
 const w={R:ar*(1-av),L:al*(1-av),U:bu*(1-au),D:bn*(1-au),
  UR:ar*bu,UL:al*bu,DR:ar*bn,DL:al*bn};
 const o=Object.assign({},w);
 [['UR','R','U'],['UL','L','U'],['DR','R','D'],['DL','L','D']]
 .forEach(q=>{if(!ex(q[0])&&w[q[0]]>0){
  if(ex(q[1]))o[q[1]]+=w[q[0]];
  if(ex(q[2]))o[q[2]]+=w[q[0]];o[q[0]]=0;}});
 [['R','UR','DR',(v+1)/2],['L','UL','DL',(v+1)/2],
  ['U','UR','UL',(u+1)/2],['D','DR','DL',(u+1)/2]]
 .forEach(q=>{if(!ex(q[0])&&w[q[0]]>0){
  if(ex(q[1]))o[q[1]]+=w[q[0]]*q[3];
  if(ex(q[2]))o[q[2]]+=w[q[0]]*(1-q[3]);o[q[0]]=0;}});
 const res={};
 for(const nm in sl){
  const m9=(D.pmul&&D.pmul[nm]!==undefined)?D.pmul[nm]:1;
  res[sl[nm]]=(o[nm]||0)*m9;}
 return res;}
function updVowels(p){
 const l9=document.getElementById('vwl'),
  r9=document.getElementById('vwr');
 if(!D||!D.haspad){l9.innerHTML='';r9.innerHTML='';return;}
 const wts=(!padDrag&&bl.vals&&Object.keys(bl.vals).length)
  ?bl.vals:(p?padWeights(p[0],p[1]):null);
 const ent=Object.keys(D.vmap||{});
 ent.sort((a,b)=>D.vmap[b][1]-D.vmap[a][1]);
 let hl='',hr='';
 for(const k of ent){
  const val=wts?(wts[k]||0):0;
  const row='<span><b style="color:'+(COLORS[k]||'#888')+'">'
   +k.slice(1)+'</b> '+val.toFixed(3)+'</span>';
  if(D.vmap[k][0]<0)hl+=row;else hr+=row;}
 l9.innerHTML=hl;r9.innerHTML=hr;}
function bakedPos(fr){
 // 현재 프레임의 패드 위치: 굽기 폴리라인 재현
 const bl=(D.blend===undefined?2:D.blend);
 const blz=Math.max(bl,0.5);
 const items=[];
 for(const sg of D.segs){
  let px,py;
  if(sg.px!==undefined&&sg.px!==null&&sg.px<900){px=sg.px;py=sg.py;}
  else{const vp=D.vmap&&D.vmap[sg.v];if(!vp)continue;
   let amp=0;const a2=Math.max(0,sg.fs-D.start),
    b2=Math.min(D.opens.length-1,sg.fe-D.start);
   for(let i2=a2;i2<=b2;i2++)amp=Math.max(amp,D.opens[i2]);
   px=vp[0]*amp;py=vp[1]*amp;}
  items.push({fs:sg.fs,fe:sg.fe,x:px,y:py});}
 items.sort((q,w)=>q.fs-w.fs);
 const ptsx=[],ptsy=[];
 for(let i=0;i<items.length;i++){
  const it=items[i],ln=it.fe-it.fs+1;
  const h=Math.min(bl*0.5,(ln-1)/2);
  if(i===0){ptsx.push([it.fs-blz,0]);ptsy.push([it.fs-blz,0]);}
  else{const pv=items[i-1],g=it.fs-pv.fe-1;
   if(g>=blz){const z1=pv.fe+blz,z2=it.fs-blz;
    if(z1>=z2){const m=(z1+z2)/2;ptsx.push([m,0]);ptsy.push([m,0]);}
    else{ptsx.push([z1,0],[z2,0]);ptsy.push([z1,0],[z2,0]);}}}
  ptsx.push([it.fs+h,it.x],[it.fe-h,it.x]);
  ptsy.push([it.fs+h,it.y],[it.fe-h,it.y]);
  if(i===items.length-1){ptsx.push([it.fe+blz,0]);
   ptsy.push([it.fe+blz,0]);}}
 function ev(pts,f){if(!pts.length)return 0;
  if(f<=pts[0][0])return pts[0][1];
  for(let i=1;i<pts.length;i++){
   if(f<=pts[i][0]){const q=pts[i-1],w=pts[i];
    if(w[0]<=q[0])return w[1];
    return q[1]+(w[1]-q[1])*(f-q[0])/(w[0]-q[0]);}}
  return pts[pts.length-1][1];}
 return [Math.max(-1,Math.min(1,ev(ptsx,fr))),
  Math.max(-1,Math.min(1,ev(ptsy,fr)))];}
function segPos(sg){if(sg.px!==undefined&&sg.px!==null&&sg.px<900)
  return [sg.px,sg.py];
 return (D.vmap&&D.vmap[sg.v])||null;}
function segLabel(sg){if(D&&D.sprite)return '';
 if(sg.v==='_N')return '-';
 const vp=D.vmap&&D.vmap[sg.v];
 if(vp&&sg.px!==undefined&&sg.px!==null&&sg.px<900){
  if(Math.hypot(vp[0]-sg.px,vp[1]-sg.py)>0.02)return '\u00b7';}
 return sg.v.slice(1);}
function drawPad(){if(!D||!D.haspad)return;
 px9.clearRect(0,0,240,160);
 px9.strokeStyle='#3a3a42';px9.strokeRect(8,8,224,144);
 px9.beginPath();px9.moveTo(120,8);px9.lineTo(120,152);
 px9.moveTo(8,80);px9.lineTo(232,80);px9.stroke();
 px9.font='bold 12px sans-serif';
 for(const k in (D.vmap||{})){const c=p2c(D.vmap[k][0],D.vmap[k][1]);
  px9.fillStyle=COLORS[k]||'#888';
  px9.fillText(k.slice(1),c[0]-4,c[1]+4);}
 if(onion.on&&D.segs.length){const fr9=Math.round(frame);
  for(let k=onion.n;k>=1;k--){
   const al=onion.a*(1-(k-1)/onion.n);
   px9.globalAlpha=al;
   let q=bakedPos(fr9-k),c9o=p2c(q[0],q[1]);
   px9.fillStyle=onion.c1;
   px9.beginPath();px9.arc(c9o[0],c9o[1],4,0,6.3);px9.fill();
   q=bakedPos(fr9+k);c9o=p2c(q[0],q[1]);
   px9.fillStyle=onion.c2;
   px9.beginPath();px9.arc(c9o[0],c9o[1],4,0,6.3);px9.fill();}
  px9.globalAlpha=1;}
 const sg=D.segs[sel];
 const p=sg?segPos(sg):null;
 const bp=bakedPos(Math.round(frame));
 updVowels(padDrag&&p?p:bp);
 const a9f=favActive();
 if(a9f!==favAct){favAct=a9f;favRender();}
 // 현재 프레임의 실제 입 위치 (작은 점)
 const cb=p2c(bp[0],bp[1]);
 px9.fillStyle='rgba(255,255,255,0.45)';px9.beginPath();
 px9.arc(cb[0],cb[1],3,0,6.3);px9.fill();
 if(!p)return;
 const c=p2c(p[0],p[1]);
 px9.strokeStyle='#fff';px9.lineWidth=2;px9.beginPath();
 px9.arc(c[0],c[1],6,0,6.3);px9.stroke();px9.lineWidth=1;}
function padMove(e){const sg=D.segs[sel];if(!sg)return;
 let p=c2p(e);p=snapPos(p[0],p[1]);
 sg.px=p[0];sg.py=p[1];sg.v=nearestV(p[0],p[1]);
 const now=performance.now();
 if(now-lastPad>50){lastPad=now;post('/pad',{x:p[0],y:p[1]});}
 draw();}
pad.addEventListener('mousedown',e=>{if(!D)return;
 const fr=Math.round(frame);
 let i=D.segs.findIndex(sg=>sg.fs<=fr&&fr<=sg.fe);
 pushHist();
 if(i<0){ // 타임바 위치에 구간이 없으면 자동 생성
  const len=Math.max(2,Math.round(D.fps*0.15));
  const end=D.start+D.opens.length-1;
  let a=Math.min(fr,end),b=Math.min(a+len-1,end);if(b<a)b=a;
  carve(a,b);D.segs.push({fs:a,fe:b,v:'_N',px:999,py:999});
  D.segs.sort((p,q)=>p.fs-q.fs);
  i=D.segs.findIndex(s9=>s9.fs===a);}
 if(i<0){hist.pop();return;}
 sel=i;padDrag=true;padMove(e);});

window.addEventListener('mousemove',e=>{if(padDrag)padMove(e);});
window.addEventListener('mouseup',()=>{if(padDrag){padDrag=false;
 pushSegs();post('/padend',{});}});
const au=document.getElementById('au');
function layout(){
 if(cv.width!==window.innerWidth)cv.width=window.innerWidth;
 return {W:cv.width,H:cv.height,
  wave:{x:10,y:26,w:cv.width-20,h:158},
  seg:{x:10,y:194,w:cv.width-20,h:48},
  sbar:{x:10,y:266,w:cv.width-20,h:14}};}
function span(){return Math.max(1,v1-v0);}
function f2x(f,r){return r.x+(f-v0)/span()*r.w;}
function x2f(x,r){return D.start+ (x-r.x)/r.w*span()+ (v0-D.start);}
function x2fi(x,r){return Math.round(Math.min(D.start+D.opens.length,
 Math.max(D.start,v0+(x-r.x)/r.w*span())));}
function f2t(f){return (f-D.start)/D.fps;}
function t2f(t){return D.start+t*D.fps;}
function saveView(){try{sessionStorage.setItem('fskr_view',
 JSON.stringify({v0:v0,v1:v1,f:frame,sa:selA,sb:selB,
  vp:document.getElementById('volp').value}));}catch(e){}}
function clampView(){const n=D.opens.length;
 let sp=Math.min(Math.max(span(),D.fps*0.25),n);
 v0=Math.max(D.start,Math.min(v0,D.start+n-sp));v1=v0+sp;}
function draw(){if(!D)return;const L=layout();
 ctx.fillStyle='#17171b';ctx.fillRect(0,0,L.W,L.H);
 ctx.fillStyle='#202027';ctx.fillRect(L.wave.x,L.wave.y,L.wave.w,L.wave.h);
 ctx.fillRect(L.seg.x,L.seg.y,L.seg.w,L.seg.h);
 // 구간 선택 하이라이트
 if(selA!==null&&selB!==null){
  const a=Math.min(selA,selB),b=Math.max(selA,selB);
  const xa=f2x(a,L.wave),xb=f2x(b,L.wave);
  ctx.fillStyle='rgba(120,180,255,0.18)';
  ctx.fillRect(xa,L.wave.y,xb-xa,L.wave.h);
  ctx.strokeStyle='rgba(140,200,255,0.8)';
  ctx.strokeRect(xa,L.wave.y,xb-xa,L.wave.h);}
 // 모음 구간
 const selLo=(selA!==null&&selB!==null)?Math.min(selA,selB):null;
 const selHi=(selA!==null&&selB!==null)?Math.max(selA,selB)-1:null;
 D.segs.forEach((sg,i)=>{
  const x0=f2x(sg.fs,L.wave),x1=f2x(sg.fe+1,L.wave);
  if(x1<L.wave.x||x0>L.wave.x+L.wave.w)return;
  ctx.globalAlpha=0.13;ctx.fillStyle=COLORS[sg.v];
  ctx.fillRect(x0,L.wave.y,x1-x0,L.wave.h);
  ctx.globalAlpha=(i==sel)?1:0.62;
  ctx.fillRect(x0,L.seg.y+3,Math.max(2,x1-x0-1),L.seg.h-6);
  ctx.globalAlpha=1;
  if(selLo!==null&&sg.fe>=selLo&&sg.fs<=selHi){
   // 선택 범위에 포함된 구간: 아래 획 강조
   ctx.fillStyle='#8cc8ff';
   ctx.fillRect(x0,L.seg.y+L.seg.h-4,Math.max(2,x1-x0-1),3);}
  if(x1-x0>13){ctx.fillStyle='#111';ctx.font='bold 13px sans-serif';
   ctx.fillText(segLabel(sg),
    (x0+x1)/2-4,L.seg.y+L.seg.h/2+5);}
  if(i==sel){ctx.strokeStyle='#fff';ctx.lineWidth=2;
   ctx.strokeRect(x0,L.seg.y+3,Math.max(2,x1-x0-1),L.seg.h-6);
   ctx.lineWidth=1;}});
 // 시퀀스 트랙 (스프라이트): 구간 아래 얇은 띠에 지정 시퀀스 이름
 if(D.sprite){const ty=L.seg.y+L.seg.h+2,th=18;
  ctx.fillStyle='#202027';ctx.fillRect(L.seg.x,ty,L.seg.w,th);
  (D.seqr||[]).forEach(r=>{const x0=f2x(r.fs,L.wave),x1=f2x(r.fe+1,L.wave);
   if(x1<L.wave.x||x0>L.wave.x+L.wave.w)return;
   const k=Math.max(0,(D.seqn||[]).indexOf(r.n));
   ctx.fillStyle=SEQC[k%SEQC.length];ctx.globalAlpha=0.85;
   ctx.fillRect(x0,ty+1,Math.max(2,x1-x0-1),th-2);ctx.globalAlpha=1;
   if(x1-x0>24){ctx.save();ctx.beginPath();
    ctx.rect(x0,ty,x1-x0-2,th);ctx.clip();
    ctx.fillStyle='#111';ctx.font='bold 11px sans-serif';
    ctx.fillText(r.n,x0+4,ty+13);ctx.restore();}});}
 // 파형 (보이는 범위만)
 ctx.strokeStyle='#73bff2';ctx.beginPath();
 const n=D.opens.length,cy=L.wave.y+L.wave.h/2;
 for(let px=0;px<L.wave.w;px++){
  const f=v0+px/L.wave.w*span();
  const i=Math.min(n-1,Math.max(0,Math.floor(f-D.start)));
  const v=D.opens[i];
  const hh=Math.max(1,v*L.wave.h*0.48);
  ctx.moveTo(L.wave.x+px+0.5,cy-hh);ctx.lineTo(L.wave.x+px+0.5,cy+hh);}
 ctx.stroke();
 // 클러스터 (시작/끝 조절 가능) + 블렌더식 마커 표시
 if(D.clus&&D.clus.length){
  const my=L.seg.y+L.seg.h;  // 마커 줄 (립싱크 바 아래)
  D.clus.forEach((c,i)=>{
   const x0=f2x(c.a,L.wave),x1=f2x(c.b+1,L.wave);
   if(x1<L.wave.x-60||x0>L.wave.x+L.wave.w+60)return;
   const on=(i===clSel);
   ctx.fillStyle=on?'rgba(255,90,80,0.20)':'rgba(255,90,80,0.10)';
   ctx.fillRect(x0,L.wave.y,x1-x0,L.wave.h);
   ctx.strokeStyle=on?'#ff5a50':'rgba(255,90,80,0.75)';
   ctx.lineWidth=on?2:1.5;
   ctx.strokeRect(x0,L.wave.y+1,x1-x0,L.wave.h-2);
   ctx.lineWidth=1;
   // 양 끝 점선 + 삼각형 + 이름 (블렌더 마커처럼, 립싱크 바 아래)
   const nm=(i+1<10?'0':'')+(i+1);
   const dfa='LS_'+nm+'A',dfb='LS_'+nm+'B';
   let la=(c.na||'').trim(),lb=(c.nb||'').trim();
   if(!la&&!lb){la=dfa;lb=dfb;}
   else{if(!la)la=lb;if(!lb)lb=la;
    if(!la.startsWith('LS_'))la='LS_'+la;
    if(!lb.startsWith('LS_'))lb='LS_'+lb;}
   [[x0,la],[x1,lb]].forEach(([xx,sfx])=>{
    if(xx<L.wave.x-40||xx>L.wave.x+L.wave.w+40)return;
    ctx.save();
    ctx.setLineDash([3,3]);
    ctx.strokeStyle=on?'rgba(255,255,255,0.85)'
     :'rgba(255,160,150,0.55)';
    ctx.beginPath();ctx.moveTo(xx,L.wave.y);
    ctx.lineTo(xx,my-8);ctx.stroke();
    ctx.restore();
    ctx.fillStyle=on?'#fff':'#ffb0aa';
    ctx.beginPath();
    ctx.moveTo(xx,my-8);ctx.lineTo(xx-5,my);
    ctx.lineTo(xx+5,my);ctx.closePath();ctx.fill();
    ctx.font=(on?'bold ':'')+'10px sans-serif';
    ctx.fillStyle=on?'#fff':'#d9a8a2';
    ctx.fillText(sfx,xx+7,my-1);});});}
 // 초 눈금 (줌 레벨에 맞춰)
 ctx.font='10px sans-serif';
 const secSpan=span()/D.fps;
 const step=secSpan>20?5:(secSpan>8?2:(secSpan>3?1:0.5));
 let t=Math.ceil(f2t(v0)/step)*step;
 for(;t2f(t)<=v1;t+=step){
  const x=f2x(t2f(t),L.wave);
  ctx.strokeStyle='rgba(255,255,255,0.10)';
  ctx.beginPath();ctx.moveTo(x,L.wave.y);
  ctx.lineTo(x,L.wave.y+L.wave.h);ctx.stroke();
  ctx.fillStyle='#888';ctx.fillText(t+'s',x+3,L.wave.y+12);}
 // 가로 스크롤바
 ctx.fillStyle='#202027';
 ctx.fillRect(L.sbar.x,L.sbar.y,L.sbar.w,L.sbar.h);
 {const n2=D.opens.length;
  const tx=L.sbar.x+(v0-D.start)/n2*L.sbar.w;
  const tw=Math.max(16,span()/n2*L.sbar.w);
  ctx.fillStyle='#55555f';
  ctx.fillRect(tx,L.sbar.y+2,Math.min(tw,L.sbar.w),L.sbar.h-4);}
 // 재생 헤드 (현재 프레임 한 칸을 반투명 빨강으로)
 const fi=Math.floor(frame);
 const x=f2x(fi,L.wave),x2=f2x(fi+1,L.wave);
 if(x2>=L.wave.x-2&&x<=L.wave.x+L.wave.w+2){
  const fw=Math.max(2,x2-x),fh=L.seg.y+L.seg.h-L.wave.y;
  ctx.fillStyle='rgba(255,75,64,0.30)';
  ctx.fillRect(x,L.wave.y,fw,fh);
  ctx.strokeStyle='rgba(255,75,64,0.85)';
  ctx.strokeRect(x,L.wave.y,fw,fh);
  ctx.fillStyle='#ff7b70';
  ctx.fillText(fi,x+4,L.wave.y-3);}
 drawPad();
}
let chain=Promise.resolve();
function post(p,o){chain=chain.then(()=>fetch(p,{method:'POST',
 body:JSON.stringify(o||{})})).catch(()=>{});return chain;}
function postFrame(f,force){const now=performance.now();
 seekT=now;  // 이동 직후 폴링이 옛 프레임으로 되돌리지 못하게
 if(force||now-lastPost>30){lastPost=now;post('/frame',{f:Math.round(f)});}}
function carveExcept(a,b,keep){const out=[];
 D.segs.forEach(sg=>{if(sg===keep){out.push(sg);return;}
  if(sg.fe<a||sg.fs>b){out.push(sg);return;}
  if(sg.fs<a)out.push({fs:sg.fs,fe:a-1,v:sg.v,px:sg.px,py:sg.py});
  if(sg.fe>b)out.push({fs:b+1,fe:sg.fe,v:sg.v,px:sg.px,py:sg.py});});
 D.segs=out.sort((p,q)=>p.fs-q.fs);}
function carve(a,b){const out=[];
 D.segs.forEach(sg=>{
  if(sg.fe<a||sg.fs>b){out.push(sg);return;}
  if(sg.fs<a)out.push({fs:sg.fs,fe:a-1,v:sg.v,px:sg.px,py:sg.py});
  if(sg.fe>b)out.push({fs:b+1,fe:sg.fe,v:sg.v,px:sg.px,py:sg.py});});
 D.segs=out.sort((p,q)=>p.fs-q.fs);}
function snapPos(x,y){const r=D.snap||0;if(r<=0)return [x,y];
 let bx=x,by=y,bd=r;const cand=[];
 for(const gx of [-1,0,1])for(const gy of [-1,0,1])cand.push([gx,gy]);
 for(const k in (D.vmap||{}))cand.push(D.vmap[k]);
 for(const c of cand){const d=Math.hypot(x-c[0],y-c[1]);
  if(d<bd){bd=d;bx=c[0];by=c[1];}}
 return [bx,by];}
function clusNames(){  // 선택 상태에 맞춰 이름칸 갱신
 const h=document.getElementById('clnmh');
 const ia=document.getElementById('cna');
 const ib=document.getElementById('cnb');
 if(!D||clSel===null||!D.clus[clSel]){
  h.style.display='';ia.style.display='none';ib.style.display='none';
  return;}
 const c=D.clus[clSel];
 h.style.display='none';ia.style.display='';ib.style.display='';
 if(document.activeElement!==ia)ia.value=c.na||'';
 if(document.activeElement!==ib)ib.value=c.nb||'';
 const nm='LS_'+((clSel+1<10?'0':'')+(clSel+1));
 ia.placeholder=nm+'A';ib.placeholder=nm+'B';}
function clusName(which,v){
 if(!D||clSel===null||!D.clus[clSel])return;
 D.clus[clSel][which]=(v||'').trim();
 clusPush(true);draw();}
function clusFromSel(){  // 선택 영역으로 클러스터 만들기
 if(!D)return;
 if(selA===null||selB===null){alert('{CL_NOSEL}');return;}
 const a=Math.min(selA,selB),b=Math.max(selA,selB)-1;
 if(b<a)return;
 pushHist();
 D.clus=D.clus||[];
 D.clus.push({a:a,b:b,na:'',nb:''});
 D.clus.sort((p,q)=>p.a-q.a);
 clSel=D.clus.findIndex(c=>c.a===a&&c.b===b);
 clusPush(true);clusNames();draw();}
function clusSplit(){  // 재생 헤드 위치에서 클러스터 쪼개기
 if(!D||!(D.clus||[]).length)return;
 const f=Math.round(frame);
 let i=-1;
 for(let k=0;k<D.clus.length;k++){
  const c=D.clus[k];
  if(c.a<f&&f<=c.b){i=k;break;}}
 if(i<0){alert('{CL_NOSPL}');return;}
 pushHist();
 const c=D.clus[i];
 const left={a:c.a,b:f-1,na:c.na||'',nb:''};
 const right={a:f,b:c.b,na:'',nb:c.nb||''};
 D.clus.splice(i,1,left,right);
 clSel=i+1;clusPush(true);clusNames();draw();}
function clusDelSel(){  // 선택한 클러스터만 삭제
 if(!D)return;
 if(clSel===null){alert('{CL_NOPICK}');return;}
 clusDel(clSel);clusNames();}
function clusGap(){let g=parseInt(
  document.getElementById('cgap').value);
 if(isNaN(g)||g<1)g=8;return g;}
function clusPush(mark){if(!D)return;
 post('/clus',{clus:D.clus.map(c=>[c.a,c.b,c.na||'',c.nb||'']),
  gap:clusGap(),mark:!!mark});}
function clusGen(){if(!D)return;
 pushHist();
 const g=clusGap(),th=0.02,n=D.opens.length,runs=[];
 let i=0;
 while(i<n){if(D.opens[i]<=th){i++;continue;}
  const a=i;while(i<n&&D.opens[i]>th)i++;runs.push([a,i-1]);}
 const out=[];
 runs.forEach(r=>{
  if(out.length&&r[0]-out[out.length-1][1]-1<=g)
   out[out.length-1][1]=r[1];
  else out.push([r[0],r[1]]);});
 const lo=D.start,hi=D.start+n-1,bl9=(D.blend||0);
 D.clus=out.filter(r=>r[1]-r[0]+1>=2)
  .map(r=>({a:D.start+r[0],b:D.start+r[1]}));
 // 실제로 구워지는 키 범위(구간 + 블렌딩)까지 넓혀 마커와 키를 맞춤
 D.clus.forEach(c=>{
  (D.segs||[]).forEach(sg=>{
   if(sg.fe>=c.a-1&&sg.fs<=c.b+1){
    c.a=Math.min(c.a,sg.fs-bl9);c.b=Math.max(c.b,sg.fe+bl9);}});
  c.a=Math.max(lo,c.a);c.b=Math.min(hi,c.b);});
 // 넓히면서 겹친 것 병합
 D.clus.sort((p,q)=>p.a-q.a);
 const mg=[];
 D.clus.forEach(c=>{
  if(mg.length&&c.a<=mg[mg.length-1].b+1)
   mg[mg.length-1].b=Math.max(mg[mg.length-1].b,c.b);
  else mg.push(c);});
 D.clus=mg;
 clSel=null;clusPush(true);clusNames();draw();}
function clusClear(){if(!D||!(D.clus||[]).length)return;
 pushHist();
 D.clus=[];clSel=null;clusPush(true);clusNames();draw();}
function clusDel(i){if(!D||i===null||!D.clus[i])return;
 pushHist();
 D.clus.splice(i,1);clSel=null;clusPush(true);clusNames();draw();}
function applySegs(){post('/apply',{segs:D.segs,
 clus:(D.clus||[]).map(c=>[c.a,c.b,c.na||'',c.nb||'']),
 gap:clusGap()});}
function toggleLoop(){loop=!loop;
 document.getElementById('loop').classList.toggle('on',loop);}
function toggleAkey(){autoKey=!autoKey;
 document.getElementById('akey').classList.toggle('on',autoKey);}
function pushSegs(){localEdit=performance.now();
 post(autoKey?'/apply':'/segs',{segs:D.segs});}
const SEQC=['#6fc3a8','#c39bff','#ffa35c','#7fb2ff','#f07aa8','#c8d65a'];
function seqRange(){if(selA!==null&&selB!==null&&selA!==selB)
  return [Math.min(selA,selB),Math.max(selA,selB)-1];
 const sg=D.segs[sel];if(sg)return [sg.fs,sg.fe];
 const f=Math.round(frame);return [f,f];}
function applySeq(nm){if(!D)return;const [a,b]=seqRange();if(b<a)return;
 const out=[];(D.seqr||[]).forEach(r=>{
  if(r.fe<a||r.fs>b){out.push(r);return;}
  if(r.fs<a)out.push({fs:r.fs,fe:a-1,n:r.n});
  if(r.fe>b)out.push({fs:b+1,fe:r.fe,n:r.n});});
 if(nm)out.push({fs:a,fe:b,n:nm});
 out.sort((p,q)=>p.fs-q.fs);D.seqr=out;
 localEdit=performance.now();
 post('/seqr',{r:D.seqr.map(r=>[r.fs,r.fe,r.n])});draw();}
function seqFill(){const el=document.getElementById('seqsel');if(!el)return;
 el.innerHTML='';(D.seqn||[]).forEach(n=>{const o=document.createElement('option');
  o.value=n;o.textContent=n;el.appendChild(o);});}
function setLevel(v){if(!D)return;
 const fr=Math.round(frame);pushHist();
 let i=(sel>=0&&D.segs[sel]&&D.segs[sel].fs<=fr&&fr<=D.segs[sel].fe)?sel:
  D.segs.findIndex(sg=>sg.fs<=fr&&fr<=sg.fe);
 if(i<0&&sel>=0&&D.segs[sel])i=sel;
 if(i<0){const len=Math.max(2,Math.round(D.fps*0.15));
  const end=D.start+D.opens.length-1;
  let a=Math.min(fr,end),b=Math.min(a+len-1,end);if(b<a)b=a;
  carve(a,b);D.segs.push({fs:a,fe:b,v:v,px:999,py:999});
  D.segs.sort((p,q)=>p.fs-q.fs);
  i=D.segs.findIndex(s9=>s9.fs===a);}
 if(i<0){hist.pop();return;}
 sel=i;const sg=D.segs[i];sg.v=v;sg.px=999;sg.py=999;
 pushSegs();draw();}
function addSeg(){if(!D)return;
 pushHist();
 let a,b;
 if(selA!==null&&selB!==null){
  a=Math.min(selA,selB);b=Math.max(selA,selB)-1;
  if(b<a)b=a;selA=null;selB=null;}
 else{const len=Math.max(2,Math.round(D.fps*0.15));
  const end=D.start+D.opens.length-1;
  a=Math.round(frame);b=a+len-1;
  if(a>end)a=end;if(b>end)b=end;if(b<a)b=a;}
 carve(a,b);D.segs.push({fs:a,fe:b,v:'_N',px:999,py:999});
 D.segs.sort((p,q)=>p.fs-q.fs);
 sel=D.segs.findIndex(s9=>s9.fs===a);
 draw();pushSegs();}
function delSeg(){if(!D||!D.segs[sel])return;
 pushHist();
 D.segs.splice(sel,1);sel=Math.max(0,sel-1);
 draw();pushSegs();}
function closeWin(){post('/close');
 setTimeout(()=>{try{window.close()}catch(e){}
  document.body.innerHTML='<p style="padding:30px">{CLOSED}</p>';},250);}
function seek(f){frame=f;seekT=performance.now();
 au.currentTime=Math.max(0,f2t(f));
 postFrame(f,true);draw();}
cv.addEventListener('mousedown',e=>{if(!D)return;
 const L=layout(),x=e.offsetX,y=e.offsetY;
 if(e.button===1){e.preventDefault();
  dragMode='pan';panX=x;panV0=v0;return;}
 if(e.button!==0)return;
 if(y>=L.sbar.y&&y<=L.sbar.y+L.sbar.h){
  const n2=D.opens.length;
  const tx=L.sbar.x+(v0-D.start)/n2*L.sbar.w;
  const tw=Math.max(16,span()/n2*L.sbar.w);
  if(x>=tx&&x<=tx+tw){dragMode='sbar';dragOff=x-tx;}
  else{const sp=span();
   v0=D.start+(x-L.sbar.x)/L.sbar.w*n2-sp/2;
   v1=v0+sp;clampView();dragMode='sbar';
   dragOff=Math.max(16,sp/n2*L.sbar.w)/2;}
  draw();return;}
 const mky=L.seg.y+L.seg.h;
 if(D.clus&&D.clus.length&&y>=mky-9&&y<=mky+10){
  for(let i=0;i<D.clus.length;i++){const c=D.clus[i];
   const x0=f2x(c.a,L.wave),x1=f2x(c.b+1,L.wave);
   if(Math.abs(x-x0)<8){dragMode='cedge';dragIdx=i;dragSide='a';
    clSel=i;dragMoved=false;pushHist();clusNames();draw();return;}
   if(Math.abs(x-x1)<8){dragMode='cedge';dragIdx=i;dragSide='b';
    clSel=i;dragMoved=false;pushHist();clusNames();draw();return;}}}
 if(y>=L.seg.y&&y<=L.seg.y+L.seg.h){
  const f=x2fi(x,L.wave);
  for(let i=0;i<D.segs.length;i++){const sg=D.segs[i];
   const x0=f2x(sg.fs,L.wave),x1=f2x(sg.fe+1,L.wave);
   if(Math.abs(x-x0)<5){dragMode='edge';dragIdx=i;dragSide='fs';
    dragMoved=false;sel=i;pushHist();draw();return;}
   if(Math.abs(x-x1)<5){dragMode='edge';dragIdx=i;dragSide='fe';
    dragMoved=false;sel=i;pushHist();draw();return;}}
  for(let i=0;i<D.segs.length;i++){const sg=D.segs[i];
   if(sg.fs<=f&&f<=sg.fe){sel=i;dragMode='segmove';dragIdx=i;
    dragOff=f-sg.fs;dragMoved=false;pushHist();draw();return;}}
  return;}
 else if(y>=L.wave.y&&y<=L.wave.y+L.wave.h){
  // 클러스터 가장자리 = 크기 조절, 위쪽 띠 = 선택
  if(D.clus&&D.clus.length){
   for(let i=0;i<D.clus.length;i++){const c=D.clus[i];
    const x0=f2x(c.a,L.wave),x1=f2x(c.b+1,L.wave);
    if(Math.abs(x-x0)<6){dragMode='cedge';dragIdx=i;
     dragSide='a';clSel=i;dragMoved=false;pushHist();clusNames();draw();return;}
    if(Math.abs(x-x1)<6){dragMode='cedge';dragIdx=i;
     dragSide='b';clSel=i;dragMoved=false;pushHist();clusNames();draw();return;}}
   if(y<=L.wave.y+14){
    const f9=x2fi(x,L.wave);let hit=null;
    for(let i=0;i<D.clus.length;i++)
     if(D.clus[i].a<=f9&&f9<=D.clus[i].b){hit=i;break;}
    if(hit!==null){clSel=(clSel===hit)?null:hit;
     clusNames();draw();return;}}}
  if(D.has_audio&&!au.paused){au.pause();
   post('/wpause',{f:Math.round(frame)});bl.playing=false;}
  const f0=x2fi(x,L.wave);
  if(!selMode){dragMode='scrub';selA=null;selB=null;seek(f0);}
  else if(selA!==null&&selB!==null
   &&f0>=Math.min(selA,selB)&&f0<Math.max(selA,selB)){
   pushHist();dragMode='rangemove';dragMoved=false;
   const a=Math.min(selA,selB),b=Math.max(selA,selB);
   mvAnchor=f0;
   mvSegs=D.segs.filter(sg=>sg.fe>=a&&sg.fs<=b-1);
   mvOrig=mvSegs.map(sg=>[sg.fs,sg.fe]);
   mvSelO=[a,b];}
  else{dragMode='selmk';dragAnchor=f0;selPx0=x;
   dragMoved=false;}}});
cv.addEventListener('mousemove',e=>{if(!D)return;
 const L=layout();const x=e.offsetX,y=e.offsetY;
 if(!dragMode){let cur='default';
  const mky2=L.seg.y+L.seg.h;
  if(D.clus&&((y>=L.wave.y&&y<=L.wave.y+L.wave.h)
   ||(y>=mky2-9&&y<=mky2+10))){
   const tol=(y>=mky2-9)?8:6;
   for(const c of D.clus){
    const x0=f2x(c.a,L.wave),x1=f2x(c.b+1,L.wave);
    if(Math.abs(x-x0)<tol||Math.abs(x-x1)<tol){
     cur='col-resize';break;}}}
  if(y>=L.seg.y&&y<=L.seg.y+L.seg.h){
   for(const sg of D.segs){
    const x0=f2x(sg.fs,L.wave),x1=f2x(sg.fe+1,L.wave);
    if(Math.abs(x-x0)<5||Math.abs(x-x1)<5){cur='ew-resize';break;}}}
  cv.style.cursor=cur;return;}
 const f=x2fi(x,L.wave);
 if(dragMode==='scrub'){frame=f;
  if(D.has_audio){au.currentTime=Math.max(0,f2t(f));
   au.play().catch(()=>{});
   clearTimeout(scrubT);
   scrubT=setTimeout(()=>{if(dragMode!=='scrub')return;
    au.pause();},140);}
  postFrame(f);draw();}
 else if(dragMode==='selmk'){
  if(Math.abs(x-selPx0)>4&&f!==dragAnchor){
   selA=dragAnchor;selB=f;dragMoved=true;}
  draw();}
 else if(dragMode==='cedge'){const c=D.clus[dragIdx];
  if(c){const f9=x2fi(x,L.wave);dragMoved=true;
   if(dragSide==='a')c.a=Math.min(f9,c.b);
   else c.b=Math.max(f9,c.a);
   // 드래그 중에도 블렌더 마커를 따라오게 (과도한 요청 방지)
   const t9=performance.now();
   if(t9-(window._clT||0)>120){window._clT=t9;clusPush(true);}
   draw();}}
 else if(dragMode==='edge'){const sg=D.segs[dragIdx];
  if(!sbound){sbound=[];const th=0.06;
   let pv=D.opens[0]>th;
   for(let i2=1;i2<D.opens.length;i2++){const cu=D.opens[i2]>th;
    if(cu!==pv){sbound.push(D.start+i2);pv=cu;}}}
  const tol=Math.max(1,Math.round(span()*6/L.wave.w));
  let bb=null,bd=tol+1;
  for(const b2 of sbound){const d2=Math.abs(f-b2);
   if(d2<bd){bd=d2;bb=b2;}}
  const f2=(bb===null)?f:bb;
  if(dragSide==='fs'){sg.fs=Math.max(D.start,Math.min(f2,sg.fe-1));}
  else{sg.fe=Math.min(D.start+D.opens.length-1,Math.max(f2,sg.fs+1));}
  dragMoved=true;draw();}
 else if(dragMode==='rangemove'){
  let df=f-mvAnchor;
  let mn=1e9,mx=-1e9;
  mvOrig.forEach(o9=>{mn=Math.min(mn,o9[0]);mx=Math.max(mx,o9[1]);});
  const end=D.start+D.opens.length-1;
  df=Math.max(D.start-mn,Math.min(df,end-mx));
  if(df!==0)dragMoved=true;
  mvSegs.forEach((sg,i2)=>{sg.fs=mvOrig[i2][0]+df;
   sg.fe=mvOrig[i2][1]+df;});
  selA=mvSelO[0]+df;selB=mvSelO[1]+df;
  draw();}
 else if(dragMode==='pan'){
  const sp=span();
  v0=panV0+(panX-x)/L.wave.w*sp;v1=v0+sp;clampView();draw();}
 else if(dragMode==='sbar'){const n2=D.opens.length;
  const sp=span();
  v0=D.start+(x-L.sbar.x-dragOff)/L.sbar.w*n2;
  v1=v0+sp;clampView();draw();}
 else if(dragMode==='segmove'){const sg=D.segs[dragIdx];
  const len=sg.fe-sg.fs;let nf=f-dragOff;
  nf=Math.max(D.start,Math.min(nf,D.start+D.opens.length-1-len));
  if(nf!==sg.fs){sg.fs=nf;sg.fe=nf+len;
   dragMoved=true;}draw();}});
window.addEventListener('mouseup',()=>{
 if(dragMode==='rangemove'&&D&&mvSegs){
  if(!dragMoved){hist.pop();selA=null;selB=null;
   mvSegs=null;seek(mvAnchor);draw();}
  else if(wavMv){
   const d9=Math.min(selA,selB)-mvSelO[0];
   mvSegs=null;
   post('/movea',{a:mvSelO[0],b:mvSelO[1]-1,d:d9}).then(()=>{
    setTimeout(()=>{saveView();location.reload();},300);});}
  else{const set9=new Set(mvSegs);
   let mn=1e9,mx=-1e9;
   mvSegs.forEach(sg=>{mn=Math.min(mn,sg.fs);mx=Math.max(mx,sg.fe);});
   carveKeep(mn,mx,set9);
   D.segs.sort((p,q)=>p.fs-q.fs);
   mvSegs=null;pushSegs();draw();}}
 if(dragMode==='cedge'&&D){
  if(dragMoved){const c=D.clus[dragIdx];
   D.clus.sort((p,q)=>p.a-q.a);
   clSel=D.clus.indexOf(c);clusPush(true);clusNames();}
  else hist.pop();
  dragMode=null;draw();}
 if(dragMode==='selmk'&&D){
  if(!dragMoved||(selA!==null&&Math.abs(selB-selA)<2)){
   selA=null;selB=null;seek(dragAnchor);draw();}}
 if(dragMode==='scrub'&&D&&D.has_audio){au.pause();}
 if((dragMode==='edge'||dragMode==='segmove')&&D){
  if(!dragMoved)hist.pop();
  if(dragMoved){const sg=D.segs[dragIdx];
   if(sg){carveExcept(sg.fs,sg.fe,sg);
    dragIdx=D.segs.indexOf(sg);sel=dragIdx;}
   pushSegs();}
  else if(dragMode==='segmove'){const sg=D.segs[dragIdx];
   if(sg){const mid=Math.round((sg.fs+sg.fe)/2);
    frame=mid;postFrame(mid,true);
    if(D.has_audio)au.currentTime=Math.max(0,f2t(mid));}}
  draw();}
 dragMode=null;});
cv.addEventListener('wheel',e=>{if(!D)return;e.preventDefault();
 const L=layout();
 if(e.shiftKey){const d=span()*0.12*(e.deltaY>0?1:-1);
  v0+=d;v1+=d;clampView();draw();return;}
 const fAt=v0+(e.offsetX-L.wave.x)/L.wave.w*span();
 const k=e.deltaY>0?1.25:0.8;
 v0=fAt-(fAt-v0)*k;v1=fAt+(v1-fAt)*k;clampView();draw();},{passive:false});
window.addEventListener('keydown',e=>{
 if((e.ctrlKey||e.metaKey)&&(e.code==='KeyZ'||e.code==='KeyY')){
  e.preventDefault();
  if(e.code==='KeyY'||e.shiftKey)redoFn();else undo();return;}
 if((e.ctrlKey||e.metaKey)&&e.code==='KeyC'){
  const sg=D&&D.segs[sel];
  if(sg)clipSeg=JSON.parse(JSON.stringify(sg));return;}
 if((e.ctrlKey||e.metaKey)&&e.code==='KeyV'){
  if(!clipSeg||!D)return;e.preventDefault();pushHist();
  const len=clipSeg.fe-clipSeg.fs;
  const end=D.start+D.opens.length-1;
  let a=Math.min(Math.round(frame),end),b=Math.min(a+len,end);
  carve(a,b);
  D.segs.push({fs:a,fe:b,v:clipSeg.v,px:clipSeg.px,py:clipSeg.py});
  D.segs.sort((p,q)=>p.fs-q.fs);
  sel=D.segs.findIndex(s9=>s9.fs===a);
  draw();pushSegs();return;}
 if(e.code==='Delete'||e.code==='Backspace'){
  if(!D)return;
  if(clSel!==null){clusDel(clSel);return;}
  pushHist();
  if(selA!==null&&selB!==null){
   carve(Math.min(selA,selB),Math.max(selA,selB)-1);
   selA=null;selB=null;}
  else if(D.segs[sel]){D.segs.splice(sel,1);
   sel=Math.max(0,sel-1);}
  draw();pushSegs();return;}
 if(e.code==='Space'){e.preventDefault();
  if(!D.has_audio){post('/play');return;}
  if(au.paused){
   if(selA!==null&&selB!==null)
    au.currentTime=f2t(Math.min(selA,selB));
   au.play().then(()=>post('/wplay',
     {f:Math.round(t2f(au.currentTime))})).catch(()=>post('/play'));}
  else{au.pause();post('/wpause',{f:Math.round(frame)});
   bl.playing=false;}}});
window.addEventListener('resize',()=>draw());
window.addEventListener('beforeunload',()=>{
 try{if(D&&D.has_audio&&!au.paused)
  navigator.sendBeacon('/wpause',
   JSON.stringify({f:Math.round(frame)}));}catch(e){}});
document.addEventListener('click',e=>{
 const cm=document.getElementById('cmenu');
 if(cm&&cm.style.display==='flex'
  &&!cm.parentNode.contains(e.target))cm.style.display='none';});
document.addEventListener('mousedown',e=>{
 if(selA===null||!D)return;
 const tn=e.target.tagName;
 if(tn==='CANVAS'||tn==='BUTTON'||tn==='INPUT')return;
 selA=null;selB=null;draw();});
au.addEventListener('play',trUpd);
au.addEventListener('pause',trUpd);
au.addEventListener('ended',()=>{if(!D)return;
 if(!loop){post('/wpause',{f:Math.round(frame)});bl.playing=false;return;}
 const a=(selA!==null&&selB!==null)?Math.min(selA,selB):D.start;
 au.currentTime=f2t(a);frame=a;
 const sp=span();v0=a;v1=a+sp;clampView();
 au.play().catch(()=>{});});
function resync(){try{lastStF=null;lastRev=null;}catch(e){}}
document.addEventListener('visibilitychange',()=>{
 if(document.visibilityState==='visible')resync();});
window.addEventListener('focus',resync);
function tick(){
 if(D&&D.has_audio&&!au.paused&&dragMode!=='scrub'){
  frame=t2f(au.currentTime);
  // 구간 루프
  if(loop&&selA!==null&&selB!==null){
   const a=Math.min(selA,selB),b=Math.max(selA,selB);
   if(frame>=b){au.currentTime=f2t(a);frame=a;}}
  // 끝 도달
  if(frame>=D.start+D.opens.length){
   if(loop){au.currentTime=f2t(D.start);frame=D.start;
    const sp=span();v0=D.start;v1=D.start+sp;clampView();}
   else{au.pause();post('/wpause',{f:Math.round(frame)});
    bl.playing=false;}}
  // 뷰 자동 이동
  const L=layout();
  if(f2x(frame,L.wave)>L.wave.x+L.wave.w){const sp=span();v0=frame;v1=v0+sp;clampView();}
  postFrame(frame);draw();}
 else if(D&&bl.playing&&!D.has_audio&&!dragMode){
  // 블렌더 쪽 재생: 폴링 사이를 보간해 부드럽게
  frame=bl.f+(performance.now()-bl.t)/1000*D.fps;
  const L=layout();
  if(f2x(frame,L.wave)>L.wave.x+L.wave.w){const sp=span();v0=frame;v1=v0+sp;clampView();}
  draw();}
 requestAnimationFrame(tick);}
async function poll(){try{const r=await fetch('/state');
 const st=await r.json();
 bl={f:st.frame,t:performance.now(),playing:!!st.playing,
  vals:st.vals||null};
 try{trUpd();}catch(e){}
 // 1) 블렌더 프레임이 '변했을 때만' 따라감 (되돌림 원천 차단)
 try{
  if(lastStF===null)lastStF=st.frame;
  else if(st.frame!==lastStF){lastStF=st.frame;
   // 블렌더에서 스크러빙/프레임 이동 → 편집기가 따라감
   if(au.paused&&!bl.playing
    &&(!dragMode||dragMode==='cedge')
    &&performance.now()-seekT>120){
    frame=st.frame;
    if(frame<v0||frame>v1){const sp=span();
     v0=frame-sp/2;v1=v0+sp;clampView();}
    draw();}}}catch(e){}
 try{
  if(st.err&&st.err!==lastErr){lastErr=st.err;
   console.error(st.err);alert(st.err);}}catch(e){}
 try{
  const hj=JSON.stringify(st.hist||[])+'|'+st.hidx;
  if(hj!==lastHist){lastHist=hj;
   D.hist=st.hist||[];D.hidx=st.hidx;histRender();}}catch(e){}
 try{
  if(lastRev===null)lastRev=st.rev;
  else if(st.rev!==lastRev){lastRev=st.rev;
   if(performance.now()-localEdit>1500){
    const ri=await fetch('/init');const ni=await ri.json();
    D.segs=ni.segs;D.opens=ni.opens;sbound=null;
    if(ni.clus){D.clus=ni.clus.map(c=>({a:c[0],b:c[1],
     na:c[2]||'',nb:c[3]||''}));clusNames();}
    if(typeof ni.fps==='number'&&ni.fps>0)D.fps=ni.fps;
    if(typeof ni.start==='number'){D.start=ni.start;
     document.getElementById('sf').value=D.start;}
    D.hist=ni.hist;D.hidx=ni.hidx;histRender();
    sel=Math.max(0,Math.min(sel,D.segs.length-1));draw();}}}catch(e){}
 }catch(e){}
 setTimeout(poll,60);}
document.getElementById('bl').addEventListener('change',e=>{
 if(!D)return;let b=parseInt(e.target.value);
 if(isNaN(b))b=2;b=Math.max(0,Math.min(12,b));e.target.value=b;
 D.blend=b;post('/blend',{b:b});pushSegs();});
document.getElementById('sf').addEventListener('change',e=>{
 if(!D)return;localEdit=performance.now();
 const nf=parseInt(e.target.value);
 if(isNaN(nf)){e.target.value=D.start;return;}
 const d=nf-D.start;if(!d)return;
 D.start=nf;D.segs.forEach(sg=>{sg.fs+=d;sg.fe+=d;});sbound=null;
 if(D.seqr&&D.seqr.length){D.seqr.forEach(r=>{r.fs+=d;r.fe+=d;});
  post('/seqr',{r:D.seqr.map(r=>[r.fs,r.fe,r.n]),noapply:1});}
 v0+=d;v1+=d;frame+=d;
 if(selA!==null&&selB!==null){selA+=d;selB+=d;}
 post('/start',{f:nf});draw();});
(async()=>{const r=await fetch('/init');D=await r.json();
 D.clus=(D.clus||[]).map(c=>({a:c[0],b:c[1],
  na:c[2]||'',nb:c[3]||''}));
 if(D.cgap)document.getElementById('cgap').value=D.cgap;
 ['cna','cnb'].forEach((id,k)=>{
  const el=document.getElementById(id);
  el.addEventListener('change',e=>clusName(k?'nb':'na',e.target.value));
  el.addEventListener('keydown',e=>{
   e.stopPropagation();
   if(e.key==='Enter')e.target.blur();});});
 clusNames();
 if(D.haspad)pad.style.display='block';
 D.seqr=(D.seqr||[]).map(r=>Array.isArray(r)?{fs:r[0],fe:r[1],n:r[2]}:r);
 if(D.sprite){document.getElementById('lvbar').style.display='flex';seqFill();
  COLORS['_U']='#8fa3bf';COLORS['_E']='#ffd94d';COLORS['_A']='#ff5a4d';}
 favRender();onionBtn();
 document.getElementById('wmv').classList.toggle('on',wavMv);
 document.getElementById('selm').classList.toggle('on',selMode);
 ontopApply();
 setTimeout(()=>{if(onTop)post('/ontop',{on:1});},1500);
 histRender();
 v0=D.start;v1=D.start+D.opens.length;
 try{const vw=JSON.parse(sessionStorage.getItem('fskr_view')||'null');
  sessionStorage.removeItem('fskr_view');
  if(vw&&typeof vw.v0==='number'){v0=vw.v0;v1=vw.v1;clampView();
   if(typeof vw.f==='number')frame=vw.f;
   if(typeof vw.sa==='number'&&typeof vw.sb==='number'){
    selA=vw.sa;selB=vw.sb;}
   if(vw.vp!==undefined&&vw.vp!=='')
    document.getElementById('volp').value=vw.vp;}}catch(e){}
 document.getElementById('sf').value=D.start;
 document.getElementById('bl').value=(D.blend===undefined?2:D.blend);
 draw();poll();requestAnimationFrame(tick);})();
</script></body></html>"""


def _lipsync_html():
    h = _LIPSYNC_HTML
    h = h.replace("{TITLE}", _tr(_tr("립싱크 편집기")))
    h = h.replace("{HINT}",
                  _tr(_tr("드래그 = 범위 선택 · 클릭 = 이동/선택 해제 · "
                      "선택 드래그 = 범위 이동 · + = 구간 추가 · "
                      "✂ = 잘라내기 · 패드 = 입모양 · "
                      "★ = 즐겨찾기 (우클릭 편집) · Ctrl+Z = 실행취소 · "
                      "Ctrl+C/V = 복사/붙여넣기 · Del = 삭제 · "
                      "Space = 재생 · 휠 = 줌 · 휠 클릭 = 패닝")))
    h = h.replace("{FV_ASK}", _tr(_tr("즐겨찾기 이름:")))
    h = h.replace("{LV_T}", _tr("입 벌림 (선택한 구간):"))
    h = h.replace("{SQ_T}", _tr("시퀀스:"))
    h = h.replace("{SQ_SET}", _tr("선택 범위에 지정"))
    h = h.replace("{SQ_CLR}", _tr("지정 해제 (표정 따라)"))
    h = h.replace("{LV_C}", _tr("닫힘"))
    h = h.replace("{LV_H}", _tr("반"))
    h = h.replace("{LV_O}", _tr("열림"))
    h = h.replace("{FV_POS}", _tr(_tr("위치 갱신")))
    h = h.replace("{FV_EDT}", _tr(_tr("즐겨찾기 수정")))
    h = h.replace("{FV_DEL}", _tr(_tr("삭제")))
    h = h.replace("{FV_OK}", _tr(_tr("확인")))
    h = h.replace("{APPLYING}", _tr(_tr("적용 중...")))
    h = h.replace("{APPLY}", _tr(_tr("적용 (다시 굽기)")))
    h = h.replace("{CLOSE}", _tr(_tr("닫기")))
    h = h.replace("{LOOP}", _tr(_tr("루프")))
    h = h.replace("{AKEY}", _tr(_tr("오토 키")))
    h = h.replace("{START}", _tr(_tr("시작 프레임")))
    h = h.replace("{BLEND}", _tr(_tr("블렌딩")))
    h = h.replace("{ONION}", _tr(_tr("어니언 스킨")))
    h = h.replace("{ONFR}", _tr(_tr("프레임 범위")))
    h = h.replace("{ONAL}", _tr(_tr("투명도")))
    h = h.replace("{H_OR}", _tr(_tr("원본")))
    h = h.replace("{H_CU}", _tr(_tr("잘라내기")))
    h = h.replace("{H_MV}", _tr(_tr("이동")))
    h = h.replace("{H_SI}", _tr(_tr("무음화")))
    h = h.replace("{H_VO}", _tr(_tr("볼륨")))
    h = h.replace("{H_RC}", _tr(_tr("재계산")))
    h = h.replace("{VOL}",
                  _tr(_tr("선택 범위 볼륨 조절 (선택 없으면 전체) · "
                      "립싱크 재계산")))
    h = h.replace("{ONTOP}", _tr(_tr("항상 위")))
    h = h.replace("{CL_GEN}", _tr(_tr("클러스터 생성")))
    h = h.replace("{CL_TIP}",
                  _tr(_tr("말소리 덩어리를 자동으로 찾아 표시합니다. "
                      "양 끝을 드래그해 조절하고, 위쪽 띠를 클릭해 "
                      "선택 후 Del로 삭제할 수 있습니다. "
                      "'적용'을 누르면 블렌더 타임라인에 마커로 "
                      "만들어집니다")))
    h = h.replace("{CL_GAP}",
                  _tr(_tr("클러스터 간격 (프레임): 이만큼 이하로 떨어진 "
                      "소리는 한 덩어리로 봅니다")))
    h = h.replace("{CL_CLR}", _tr(_tr("클러스터 모두 지우기")))
    h = h.replace("{CL_CLR_L}", _tr(_tr("클러스터 제거")))
    h = h.replace("{CL_GAP_L}", _tr(_tr("간격")))
    h = h.replace("{CL_HEAD}", _tr(_tr("클러스터 (프레임 단위)")))
    h = h.replace("{CL_PICK}",
                  _tr(_tr("클러스터를 클릭하면 이름을 지정할 수 있습니다")))
    h = h.replace("{CL_SEL_L}", _tr(_tr("영역으로 생성")))
    h = h.replace("{CL_SEL}",
                  _tr(_tr("드래그로 선택한 범위를 클러스터로 만듭니다")))
    h = h.replace("{CL_SPL_L}", _tr(_tr("쪼개기")))
    h = h.replace("{CL_SPL}",
                  _tr(_tr("재생 헤드(빨간 세로선) 위치에서 클러스터를 "
                      "둘로 나눕니다")))
    h = h.replace("{CL_DEL_L}", _tr(_tr("선택 삭제")))
    h = h.replace("{CL_DEL}", _tr(_tr("선택한 클러스터 하나만 삭제")))
    h = h.replace("{CL_NOSEL}",
                  _tr(_tr("먼저 파형에서 범위를 드래그해 선택하세요")))
    h = h.replace("{CL_NOSPL}",
                  _tr(_tr("재생 헤드가 클러스터 안에 있어야 합니다")))
    h = h.replace("{CL_NOPICK}",
                  _tr(_tr("먼저 클러스터를 클릭해 선택하세요")))
    h = h.replace("{CL_NA}", _tr(_tr("시작 이름")))
    h = h.replace("{CL_NB}", _tr(_tr("끝 이름")))
    h = h.replace("{CL_NM}",
                  _tr(_tr("마커 이름. 한쪽만 적으면 반대쪽도 같은 이름이 "
                      "됩니다. 비우면 기본 이름(LS_01A/B)")))
    h = h.replace("{TR_PL}", _tr(_tr("재생")))
    h = h.replace("{TR_PA}", _tr(_tr("일시정지")))
    h = h.replace("{TR_ST}", _tr(_tr("정지")))
    h = h.replace("{TR_PV}", _tr(_tr("1프레임 뒤로")))
    h = h.replace("{TR_NX}", _tr(_tr("1프레임 앞으로")))
    h = h.replace("{VOLRC}",
                  _tr(_tr("선택 범위 립싱크 재계산 (선택 없으면 전체)")))
    h = h.replace("{WMV}", _tr(_tr("파형 함께 이동")))
    h = h.replace("{CUT_A}", _tr(_tr("잘라내기 (길이 단축)")))
    h = h.replace("{CUT_B}", _tr(_tr("무음화 (길이 유지)")))
    h = h.replace("{SELM}",
                  _tr(_tr("영역 선택 모드 (끄면 드래그 = 스크럽)")))
    h = h.replace("{CUT}",
                  _tr(_tr("선택 범위 잘라내기 (오디오 포함) · "
                      "선택 없으면 타임바에서 분할")))
    h = h.replace("{CLOSED}",
                  _tr(_tr("편집기가 종료되었습니다. 탭을 닫아 주세요.")))
    return h


def _lipsync_topmost_try(on=True):
    """편집기 창의 항상 위 설정/해제. 핸들 캐시로 열거 비용 제거."""
    try:
        import ctypes
        u32 = ctypes.windll.user32
    except Exception:
        return True  # 비 윈도우: 재시도 불필요
    import time as _t9

    def _apply(h9):
        try:
            ex9 = u32.GetWindowLongW(ctypes.c_void_p(h9), -20)
            if bool(ex9 & 0x8) == bool(on):
                return  # 이미 원하는 상태 (반복 적용 방지)
        except Exception:
            pass
        try:
            # TOPMOST(-1)/NOTOPMOST(-2), NOMOVE|NOSIZE|NOACTIVATE
            u32.SetWindowPos(ctypes.c_void_p(h9),
                             ctypes.c_void_p(-1 if on else -2),
                             0, 0, 0, 0, 0x2 | 0x1 | 0x10)
        except Exception:
            pass

    # 캐시된 창 핸들이 살아있으면 열거 없이 즉시 처리
    hc9 = _LIPSRV.get("hwnd")
    if hc9:
        try:
            if u32.IsWindow(ctypes.c_void_p(hc9)):
                _apply(hc9)
                return True
        except Exception:
            pass
        _LIPSRV["hwnd"] = None
    # 열거 백오프: 못 찾으면 2초간 재열거 안 함
    if _t9.time() < _LIPSRV.get("top_wait", 0.0):
        return False
    titles = (_tr("립싱크 편집기"), "Lipsync Editor",
              "リップシンクエディター", "口型编辑器")
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def _cb(hwnd, _lp):
        try:
            ln = u32.GetWindowTextLengthW(hwnd)
            if ln:
                buf = ctypes.create_unicode_buffer(ln + 1)
                u32.GetWindowTextW(hwnd, buf, ln + 1)
                if any(t9 in buf.value for t9 in titles):
                    found.append(hwnd)
        except Exception:
            pass
        return True

    try:
        u32.EnumWindows(_cb, 0)
    except Exception:
        return True
    if not found:
        n9m = _LIPSRV.get("top_miss", 0) + 1
        _LIPSRV["top_miss"] = n9m
        # 3회 연속 못 찾으면 창이 닫힌 것 → 열거 중단 (/init·/ontop이 재개)
        _LIPSRV["top_wait"] = _t9.time() + (2.0 if n9m < 3 else 600.0)
        return False
    _LIPSRV["top_miss"] = 0
    _LIPSRV["hwnd"] = found[-1]  # 가장 최근 생성 창
    for h9 in found:
        _apply(h9)
    return True


def _lipsync_topmost_tick():
    _LIPSRV["top_tries"] = _LIPSRV.get("top_tries", 0) + 1
    if (_lipsync_topmost_try(_LIPSRV.get("ontop", True))
            or _LIPSRV["top_tries"] > 40):
        return None
    return 0.25


def _open_editor_window(url):
    """크롬/엣지 앱 모드(주소창 없는 팝업 창)로 열기, 실패 시 기본 브라우저."""
    import subprocess
    import shutil
    import os as _os
    cands = []
    for nm in ("chrome", "msedge", "brave", "chromium"):
        p9 = shutil.which(nm)
        if p9:
            cands.append(p9)
    for p9 in (
        _os.path.expandvars(
            r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        _os.path.expandvars(
            r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        _os.path.expandvars(
            r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        _os.path.expandvars(
            r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        _os.path.expandvars(
            r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
    ):
        if _os.path.exists(p9):
            cands.append(p9)
    import tempfile
    prof = _os.path.join(tempfile.gettempdir(), "fskr_lipsync_profile")
    for exe in cands:
        try:
            subprocess.Popen([exe, "--app=" + url,
                              "--user-data-dir=" + prof,
                              "--window-size=1180,660",
                              "--window-position=120,120",
                              "--no-first-run"])
            return True
        except Exception:
            pass
    import webbrowser
    webbrowser.open(url)
    return False


def _rdp_indices(pts, eps):
    """단순화 후 유지할 인덱스 (Ramer-Douglas-Peucker, 수직 오차 기준)."""
    n = len(pts)
    if n <= 2:
        return list(range(n))
    keep = [0, n - 1]
    stack = [(0, n - 1)]
    while stack:
        a, b = stack.pop()
        x0, y0 = pts[a]
        x1, y1 = pts[b]
        dx = x1 - x0
        worst = -1.0
        wi = -1
        for i in range(a + 1, b):
            x, y = pts[i]
            yl = y0 + ((y1 - y0) * (x - x0) / dx if dx else 0.0)
            d = abs(y - yl)
            if d > worst:
                worst = d
                wi = i
        if wi >= 0 and worst > eps:
            keep.append(wi)
            stack.append((a, wi))
            stack.append((wi, b))
    return sorted(set(keep))


def _simplify_fcurve(fc, eps):
    """F-커브 키프레임을 오차 한도 안에서 제거. 제거 개수 반환."""
    pts = [(kp.co[0], kp.co[1]) for kp in fc.keyframe_points]
    if len(pts) <= 2:
        return 0
    keep = set(_rdp_indices(pts, eps))
    removed = 0
    for i in range(len(pts) - 1, -1, -1):
        if i not in keep:
            fc.keyframe_points.remove(fc.keyframe_points[i], fast=True)
            removed += 1
    if removed:
        fc.update()
    return removed


_persist_handlers_img = []


_OWNER = object()  # 모듈 인스턴스 식별용 (중복 오버레이 방지)


def draw_add(space, fn, args, region, kind, key):
    """뷰포트 그리기 핸들러 등록 (같은 key로 남아 있던 옛 핸들러는 먼저 제거).

    애드온을 업데이트·재활성화할 때 옛 모듈의 핸들러가 남으면 화면에 같은
    글자가 두 번 겹쳐 그려진다. 핸들은 모듈이 바뀌어도 유지되는 드라이버
    네임스페이스에 기록해 두고 다음 등록 때 확실히 지운다.
    """
    ns = bpy.app.driver_namespace.setdefault("fskr_draw_handles", {})
    old = ns.pop(key, None)
    if old is not None:
        try:
            old[0].draw_handler_remove(old[1], old[2])
        except Exception:
            pass
    h = space.draw_handler_add(fn, args, region, kind)
    ns[key] = (space, h, region)
    return h


def draw_remove(key):
    ns = bpy.app.driver_namespace.get("fskr_draw_handles") or {}
    old = ns.pop(key, None)
    if old is not None:
        try:
            old[0].draw_handler_remove(old[1], old[2])
        except Exception:
            pass


def app_handler_add(lst, fn):
    """bpy.app.handlers 목록에 추가 (옛 모듈이 남긴 같은 함수는 먼저 제거)."""
    tail = (getattr(fn, "__module__", "") or "").rsplit(".", 1)[-1]
    for x in list(lst):
        if x is fn:
            continue
        try:
            if getattr(x, "__name__", None) == fn.__name__ and \
                    (getattr(x, "__module__", "") or "").rsplit(".", 1)[-1] \
                    == tail and "face_shapekey_rig" in \
                    (getattr(x, "__module__", "") or ""):
                lst.remove(x)
        except Exception:
            pass
    if fn not in lst:
        lst.append(fn)


def other_copies():
    """함께 켜져 있는 다른 Face Shape Key Rig 사본 (모듈 이름 목록)."""
    me = __package__ or ""
    out = []
    try:
        for k in bpy.context.preferences.addons.keys():
            if "face_shapekey_rig" in k and k != me:
                out.append(k)
    except Exception:
        pass
    return out


def _is_owner():
    """이 모듈이 최신 등록인지 (업데이트로 남은 옛 핸들러는 그리지 않음)."""
    try:
        return bpy.app.driver_namespace.get("fskr_owner") is _OWNER
    except Exception:
        return True


def _fskr_ns_install():
    """드라이버 네임스페이스 함수 설치 (가장 먼저, 실패해도 계속)."""
    try:
        bpy.app.driver_namespace["fskr_owner"] = _OWNER
        bpy.app.driver_namespace["fskr_pad"] = _pad_eval
        bpy.app.driver_namespace["fskr_pofs"] = _pad_ofs
        bpy.app.driver_namespace["fskr_ssnap"] = _sld_snap
        bpy.app.driver_namespace["fskr_z"] = _zero_snap
    except Exception:
        pass


def _fskr_refresh_drivers():
    """재활성화 직후 드라이버 오류 캐시를 강제로 재평가해 해소."""
    _fskr_ns_install()
    try:
        for sc9 in bpy.data.scenes:
            s9 = getattr(sc9, "fskr", None)
            if s9 is not None and s9.rig is not None:
                _fskr_apply_locks(s9.rig, bool(s9.arrange))
    except Exception:
        pass
    try:
        for ob9 in bpy.data.objects:
            if ob9.type == 'ARMATURE':
                ob9.update_tag()
        sc9 = bpy.context.scene
        sc9.frame_set(sc9.frame_current)
    except Exception:
        pass
    return None


# ------------------------------------------------------------------
# 번역 보강 (1.0.217): 빠져 있던 영어·일본어·중국어 문구
# ------------------------------------------------------------------

_EN.update({
    "   ('입' 태그의 '입 (시퀀스·립싱크)'가 켜져 있어야 함)": "   (the '입/Mouth' tag needs 'Mouth (sequence · lip sync)' turned on)",
    ' (대칭)': ' (sym)',
    ' (적용됨)': ' (applied)',
    '%d개': '%d',
    "'%s' 마커를 만들고 '%s' 태그와 연결": "Create marker '%s' and link tag '%s'",
    "'%s' 마커를 만들고 '%s' 태그와 연결합니다 (태그가 없으면 같이 만듦)": "Creates marker '%s' and links it to tag '%s' (creates the tag too if missing)",
    "'머리카락 위로' 복사본 메시를 와이어로 표시합니다 (머리카락 앞에 있는지 확인용)": "Show the 'Over hair' copy mesh as wireframe (to check it sits in front of the hair)",
    "'머리카락 위로' 파츠 자리에서 지금 보는 쪽으로 광선을 쏴서 앞머리까지의 거리를 재고, 앞으로 당기는 거리를 그보다 조금 크게 맞춥니다": "Casts a ray from the 'Over hair' parts toward the current view, measures the distance to the bangs, and sets the pull-forward distance slightly larger",
    "'머리카락 위로' 파츠가 뷰포트 시점을 따라갑니다. 화면을 돌리는 동안에는 가볍게 두었다가 멈추면 바로 맞춥니다 (렌더와는 무관)": "'Over hair' parts follow the viewport view. While orbiting they stay light and snap into place when you stop (does not affect rendering)",
    "'머리카락 위로' 파츠가 뷰포트 시점을 얼마나 자주 따라갈지 (렌더와는 무관)": "How often 'Over hair' parts follow the viewport view (does not affect rendering)",
    "'머리카락 위로' 파츠가 없거나 시점을 찾지 못했습니다": "No 'Over hair' parts, or the view could not be found",
    "'머리카락 위로' 파츠를 보는 쪽으로 얼마나 앞당길지. 앞머리보다 앞에 올 만큼만 (너무 크면 옆모습에서 반대쪽 파츠가 머리를 뚫고 보일 수 있음)": "How far to pull 'Over hair' parts toward the viewer. Just enough to sit in front of the bangs (too much and the far-side parts can show through the head in profile)",
    "'원래 색'이 '바꿀 색'이 되도록 색조·채도·명도 값을 계산해 넣습니다. 비슷한 색의 명암도 같이 따라 바뀜": "Calculates hue, saturation and value so that 'Original color' becomes 'New color'. Shades of similar colors follow along",
    "'찍기'를 누르면 화면이 얼굴 정면(숫자패드 1과 같음)으로 바뀝니다. 얼굴을 클릭하세요": "Pressing 'Place' switches to the face front view (same as Numpad 1). Click on the face",
    '(고급) 별도 데칼': '(Advanced) Separate decal',
    '(고급) 별도 입 데칼에 시트 추가': '(Advanced) Add sheet to a separate mouth decal',
    '(고급) 선택한 메시를 그대로 캔버스로': '(Advanced) Use the selected mesh as a canvas',
    '(예전) 머리카락 위 불투명도': '(Legacy) Over-hair opacity',
    '+ 로 마커를 만들고 이름을 붙이세요 (예: 눈, 입, 볼)': 'Create markers with + and name them (e.g. Eyes, Mouth, Cheek)',
    "+ 로 태그를 만들거나, 파츠를 추가할 때 '새 태그'로 바로 만드세요": "Create tags with +, or use 'New tag' when adding a part",
    '+ 로 파츠와 태그를 고르면 그 태그의 기준 마커 위치에 놓입니다': "Pick a part and tag with + and it is placed at that tag's marker",
    '0-1, 2-3, 4-5행... 두 행씩 묶어서, 위 칸 = 열림, 아래 칸 = 닫힘 시퀀스를 만듭니다. 두 칸 모두 그림이 있는 곳만 (투명 배경 이미지 기준)': 'Pairs rows 0-1, 2-3, 4-5... and makes sequences with top cell = open, bottom cell = closed. Only where both cells have a drawing (for transparent-background images)',
    "1. ②에서 '입' 마커를 입 위치에 찍기": "1. In ②, place the 'Mouth' marker on the mouth",
    '100% 가까이면 앞뒤가 겹쳐 깜빡일 수 있습니다': 'Near 100% the front and back can overlap and flicker',
    '2. ③에서 입 모양 시트 불러오기 (칸마다 입 모양 하나)': '2. In ③, load a mouth-shape sheet (one mouth shape per cell)',
    "3. ④에서 + → 그 시트의 입 모양 → 태그 '입' → OK": "3. In ④, + → a mouth shape from that sheet → tag 'Mouth' → OK",
    '4. 여기에 입 시트가 생기면 시퀀스(닫힘·반·열림) → 립싱크 순서로 설정': '4. When the mouth sheet appears here, set up sequences (closed · half · open), then lip sync',
    'Face Rig 캔버스 파일이 아닙니다': 'Not a Face Rig canvas file',
    'Language / 언어': 'Language / 언어',
    'N패널': 'N panel',
    'OK를 누르면 정면 뷰로 바뀌고 바로 얼굴을 클릭해 위치를 찍습니다': 'Press OK to switch to the front view, then click on the face to place it',
    'UV %d곳을 이어 붙이고 얼굴에 다시 붙였습니다': 'Joined %d UV areas and re-attached to the face',
    'UV Warp 모디파이어': 'UV Warp modifier',
    'UV Warp를 이 그룹에만 적용 (얼굴 메시 일부일 때)': 'Apply UV Warp only to this group (when it is part of the face mesh)',
    'UV 투영을 알아내지 못했습니다': 'Could not determine the UV projection',
    '①에서 리그를 먼저 지정하세요': 'Set the rig in ① first',
    '①에서 캔버스와 리그를 먼저 정하세요': 'Set the canvas and rig in ① first',
    '②에서 마커를 먼저 만들면 기준점으로 고를 수 있습니다': 'Create markers in ② first to pick them as anchors',
    '④ 입 파츠에 이 시트 연결': 'Link this sheet to the ④ mouth part',
    "④·⑥에서 파츠를 고친 뒤 '저장하고 끝내기'": "Edit parts in ④·⑥, then 'Save and finish'",
    '④에 입 파츠가 없습니다': 'There is no mouth part in ④',
    "④에서 + → 이 시트의 입 모양 → '입' 태그로 입 파츠를 만드세요": "In ④, + → a mouth shape from this sheet → 'Mouth' tag to create a mouth part",
    '④에서 파츠를 배치한 뒤 표정으로 저장합니다': 'Arrange parts in ④, then save them as an expression',
    '④의 입 파츠가 이 시트를 그리도록 연결합니다 (시퀀스·미리보기·립싱크가 화면에 보이려면 필요)': 'Links the ④ mouth part to draw this sheet (needed for sequences, preview and lip sync to show)',
    '✓ 확정': '✓ Apply',
    '✕ 취소': '✕ Cancel',
    '가리는 메시: %s, 최대 %.4g → 거리 %.4g': 'Occluding mesh: %s, max %.4g → distance %.4g',
    '가림 거리 재서 맞추기': 'Measure occlusion distance',
    '가볍게': 'Light',
    '가장자리 흰 선 제거': 'Remove white fringe',
    '각 칸의 테두리를 이만큼 투명하게 잘라냅니다. 칸 모서리의 번호 글씨나 가이드선이 보일 때 사용 (그림이 칸 가운데 있어야 함)': "Makes this much of each cell's border transparent. Use when cell numbers or guide lines show at the edges (drawings must be centered in their cells)",
    '감정표현 Plane · 머리 본: %s': 'Emote plane · head bone: %s',
    '감정표현 Plane 만들기': 'Create emote plane',
    '감정표현 Plane: 켜면 면이 항상 활성 카메라 정면을 봅니다 (위치는 머리를 따라감). 끄면 머리 정면에 고정': 'Emote plane: when on, it always faces the active camera (position follows the head). When off, it is fixed to the front of the head',
    '감정표현 Plane을 만들었습니다: ': 'Created emote plane: ',
    '값 = 캔버스 크기 대비 거리 (0.03 = 3%)': 'Value = distance relative to canvas size (0.03 = 3%)',
    '같은 태그로 같은 자리에 폴더를 하나 더 만들면 둘 중 하나만 켜집니다': 'Another folder with the same tag in the same place makes only one of them active',
    '격자로 그린 스프라이트 시트 이미지': 'Sprite sheet image drawn on a grid',
    '격자로 그린 스프라이트 시트 이미지를 불러와 행·열로 자르고 파츠 번호를 매깁니다': 'Loads a grid sprite sheet, slices it into rows and columns and numbers the parts',
    '격자로 그린 시트 이미지를 고르고 행·열 수를 넣으세요 (파일 창 오른쪽)': 'Pick the grid sheet image and enter the row and column counts (right side of the file browser)',
    '겹치기': 'Overlap',
    '고른 눈의 시선 패드와 칸 값을 그대로 씁니다 (같은 이름의 파츠끼리). 오른쪽 눈을 왼쪽 눈에 연결할 때': "Uses the chosen eye's gaze pad and cell values as-is (between parts with the same name). For linking the right eye to the left eye",
    '고른 칸이 키프레임과 상관없이 계속 보입니다. 끝나면 꼭 끄세요': 'The chosen cell stays visible regardless of keyframes. Be sure to turn it off when done',
    '그 메시 선택 → Tab (편집 모드)': 'Select that mesh → Tab (Edit Mode)',
    '그 색으로 칠함 (명암 없어짐)': 'Paints with that color (shading is lost)',
    '그룹 선택 무시하고 전부 적용': 'Ignore group selection and apply to all',
    '그룹만 적용': 'Group only',
    '그림': 'Image',
    '그림 가로 크기 (종횡비 고정을 끈 경우)': 'Drawing width (when aspect lock is off)',
    '그림 세로 크기 (종횡비 고정을 끈 경우)': 'Drawing height (when aspect lock is off)',
    '그림에서 찾기': 'Pick from image',
    '그림을 데칼 위에서 위아래로 이동 (칸 높이 대비 %)': 'Move the drawing up/down on the decal (% of cell height)',
    '그림을 데칼 위에서 좌우로 이동 (칸 너비 대비 %)': 'Move the drawing left/right on the decal (% of cell width)',
    '그림이 있는 칸만 번호가 매겨져 파츠가 됩니다': 'Only cells with a drawing get numbered and become parts',
    '기준점 ⊕ 드래그 = 기준점 옮기기   ·   Ctrl+Z 한 단계 되돌리기   ·   Enter 확정   ·   Esc 취소   ·   원근 뷰가 되면 확정': 'Drag pivot ⊕ = move pivot   ·   Ctrl+Z = step back   ·   Enter apply   ·   Esc cancel   ·   Switching to perspective applies',
    '기준점 만들기 · 찍기': 'Create and place anchors',
    '깊이 (패럴랙스)': 'Depth (parallax)',
    '깊이 있는 파츠 %d개': '%d parts with depth',
    '내보내기': 'Export',
    '내보내기 실패: ': 'Export failed: ',
    '내보낸 .zip을 지금 고른 캔버스에 덮어씁니다. 이 캔버스의 기존 파츠·프리셋·입 시트·컨트롤러는 지워집니다 (Ctrl+Z로 되돌릴 수 있음)': "Overwrites the selected canvas with an exported .zip. This canvas's existing parts, presets, mouth sheets and controllers are removed (undo with Ctrl+Z)",
    '내보냈습니다 (시트 %d장): ': 'Exported (%d sheets): ',
    '누를 메시를 선택하세요': 'Select the meshes to flatten',
    '눈 데칼의 UV를 0~1 정사각형 안에 꽉 차게 맞춥니다 (가로세로 비율 유지, 가운데 정렬). 파츠 위치/크기의 기준이 데칼 전체가 됩니다': "Fits the eye decal's UVs to fill the 0-1 square (keeps aspect, centered). Part position/size then refer to the whole decal",
    '눈·눈썹·입·감정표현 태그와 눈·입 마커를 없는 것만 추가합니다': 'Adds the Eyes, Brows, Mouth and Emote tags and the Eyes/Mouth markers that are missing',
    '눈썹 위~턱까지 얼굴 앞면을 면 선택': 'Face-select the front of the face from above the brows to the chin',
    '다른 레이어와 같은 칸 번호를 씁니다 (예: 속눈썹이 흰자의 깜빡임 단계를 따라감). 두 시트의 칸 배치가 같아야 합니다': "Uses the same cell number as another layer (e.g. lashes follow the white's blink steps). Both sheets must share the same cell layout",
    '다른 스프라이트 시트의 행(표정)을 그대로 따라갑니다. 얼굴 표정과 범고래 표정을 한 번에 바꿀 때 사용': "Follows another sprite sheet's row (expression). Use to change e.g. the face and a hat's expression together",
    '다른 캔버스를 따라가는 캔버스는 지원하지 않습니다': 'Canvases that follow another canvas are not supported',
    '다른 파일로': 'Other file',
    '다른 파일로 바꾸기': 'Replace with another file',
    '다시 만들기': 'Rebuild',
    '다시 불러오기': 'Reload',
    '다시 불러왔습니다: ': 'Reloaded: ',
    '다시 자르기': 'Re-slice',
    '다음 키까지 값 그대로 (뚝 바뀜)': 'Holds the value until the next key (instant change)',
    '단계': 'Step',
    '닫힘/반/열림 단계마다 칸의 크기와 위치를 따로 보정': 'Adjust cell size and position separately for the closed/half/open steps',
    '대사 길이에 맞춰 씬 끝 프레임을 %d로 늘렸습니다': 'Extended the scene end frame to %d to fit the dialogue',
    '대상 본': 'Target bone',
    '대칭': 'Symmetric',
    '대칭 태그가 쓰는 마커는 한쪽만 찍으면 반대쪽이 따라갑니다': 'For markers used by symmetric tags, place one side and the other follows',
    '덮기': 'Normal',
    '덮어쓰기': 'Overwrite',
    '데칼 가운데를 기준으로 반대쪽에 거울처럼 하나 더 그립니다 (땀방울, 빗금 등)': 'Draws a mirrored copy on the other side of the decal center (sweat drops, blush lines, etc.)',
    '데칼 머티리얼을 이미지 알파로 투명하게 만듭니다 (Transparent + Mix Shader 삽입, Blended 렌더, 그림자 끄기). 얼굴 본체 머티리얼에는 쓰지 마세요': 'Makes the decal material transparent via image alpha (inserts Transparent + Mix Shader, Blended render, shadows off). Do not use on the main face material',
    '데칼 오브젝트용. 머티리얼을 건드리지 않음': 'For decal objects. Leaves the material untouched',
    '데칼 위에서 그림이 보이는 크기. 줄여도 옆 칸이 침범하지 않습니다 (칸 밖은 투명 처리). 투명 배경 설정이 되어 있어야 잘림이 적용됩니다': "How large the drawing appears on the decal. Shrinking it won't reveal the neighbor cell (outside the cell is transparent). Clipping needs the transparent-background setup",
    '도프시트·그래프 에디터에서 선택해 둔 키프레임만 (이 입)': 'Only keyframes selected in the Dope Sheet / Graph Editor (this mouth)',
    '도프시트·그래프 에디터에서 선택해 둔 키프레임만 (이 파츠)': 'Only keyframes selected in the Dope Sheet / Graph Editor (this part)',
    '돌리는 동안은 그대로, 멈추면 맞춤 (가장 가벼움)': 'Stays put while orbiting, aligns when you stop (lightest)',
    '드라이버 방식처럼 모음마다 지정한 입 칸으로 바뀝니다': 'Like driver mode, switches to the mouth cell set for each vowel',
    '디스크의 시트 이미지 파일을 다시 읽습니다 (다른 프로그램에서 고친 뒤 사용)': 'Re-reads the sheet image file from disk (after editing it in another program)',
    '따라가는 눈의 시선 좌우를 뒤집습니다 (데칼 UV가 좌우 반전되어 있을 때)': "Flips the followed eye's gaze horizontally (when the decal UVs are mirrored)",
    '렌더 카메라 기준: 다른 각도로 보면 납작해 보임': 'Based on the render camera: looks flat from other angles',
    '리그 바인드(ARP 등)할 때 캔버스는 빼고 얼굴 메시만 바인드하세요': 'When binding the rig (ARP etc.), bind only the face mesh, not the canvas',
    '리그가 설정되지 않았습니다': 'No rig is set',
    '립싱크가 열만 바꿉니다. 표정마다 닫힘/반/열림을 가로로 배치': 'Lip sync only changes the column. Lay out closed/half/open horizontally per expression',
    '마커': 'Marker',
    '마커 기준': 'Marker',
    '마커 없이 캔버스 가운데 기준': 'No marker, canvas center',
    '마커 추가 창에서: 이 태그의 기준을 새 마커로': "From the add-marker window: use the new marker as this tag's anchor",
    '마커 표시': 'Show markers',
    '마커를 옮기면 그 마커에 붙은 파츠가 전부 따라갑니다': 'Moving a marker moves every part attached to it',
    '마커를 지웁니다. 이 마커를 쓰던 태그는 얼굴 가운데 기준이 됩니다': 'Removes the marker. Tags that used it fall back to the face center',
    '만든 뒤 한중일 입력 창을 띄워 이름을 씁니다 (Blender에서 한글 입력이 안 될 때)': "After creating, opens the CJK input window to type the name (when CJK input doesn't work in Blender)",
    '만들기': 'Create',
    '만들기/갱신': 'Create/Update',
    '말하는 중 소리가 작을 때 (행, 열). -1 = 표정 칸 그대로': 'While talking at low volume (row, col). -1 = keep the expression cell',
    '말할 때 입은 ⑥ 시퀀스·립싱크로 바뀝니다': 'While talking, the mouth is driven by ⑥ sequences · lip sync',
    "말할 때도 이 입을 그대로 둡니다 (뻐끔거리지 않음). '나머지 표정 전부'의 입으로 바뀌지 않게 할 때 사용": "Keeps this mouth while talking (no flapping). Use so it doesn't switch to the 'all other expressions' mouth",
    '매 프레임 따라감. 가장 부드럽지만 화면을 돌릴 때마다 씬 전체가 다시 계산되어 무거움': 'Follows every frame. Smoothest, but the whole scene recalculates whenever you orbit, so it is heavy',
    '머리 납작하게 (카메라 기준)': 'Head flatten (camera-based)',
    '머리 납작하게 지우기': 'Remove head flatten',
    '머리 납작하게: %d개 메시': 'Head flatten: %d meshes',
    '머리 본을 고르세요': 'Pick the head bone',
    '머리를 카메라 시선 방향으로 눌러 2D 그림처럼 보이게 합니다 (캔버스 파츠도 같이)': 'Squashes the head along the camera view so it reads like a 2D drawing (canvas parts too)',
    '머리카락 위 불투명도': 'Over-hair opacity',
    '머리카락 위로': 'Over hair',
    '머리카락 위로 보이는 부분의 진하기 (1 = 완전히 위, 0.5 = 머리카락이 비쳐 보임)': 'Strength of the part shown over the hair (1 = fully on top, 0.5 = hair shows through)',
    '머리카락 위로 보이는 부분의 진하기 (1 = 완전히 위, 0.5 = 머리카락이 비쳐 보임). 가려지지 않은 부분은 그대로': 'Strength of the part shown over the hair (1 = fully on top, 0.5 = hair shows through). Unoccluded areas are unchanged',
    '머티리얼 Mapping 노드': 'Material Mapping node',
    '메시 수정 후 정리': 'Clean up after mesh edit',
    '면을 더하거나(Shift+클릭) 빼고 적용': 'Add faces (Shift+click) or remove them, then apply',
    '명암은 두고 색상·채도만 바꿈': 'Keeps shading and changes only hue and saturation',
    '몇 초 동안 애드온이 쓰는 시간을 함수별로 잽니다. 누른 뒤 렉이 나는 동작(화면 돌리기·재생·컨트롤러 끌기 등)을 평소처럼 하세요. 결과는 블렌드 파일 옆 fskr_perf.txt와 텍스트 편집기의 FSKR_perf.txt에 저장됩니다': 'Measures, per function, how much time the add-on uses for a few seconds. After pressing, do whatever lags as usual (orbiting, playback, dragging controllers...). Results are saved to fskr_perf.txt next to the .blend and to FSKR_perf.txt in the Text Editor',
    '모두 보이기': 'Show all',
    "모든 '머리카락 위로' 파츠 공통": "Shared by all 'Over hair' parts",
    '모든 레이어의 깊이(패럴랙스)에 곱하는 값. 0이면 끔': "Multiplier for every layer's depth (parallax). 0 = off",
    '모든 메시에서 납작하게 모디파이어를 지웁니다': 'Removes the flatten modifier from all meshes',
    '모든 입 칸에 공통으로 적용되는 배치 값 펼치기': 'Expand placement values shared by all mouth cells',
    '모든 파츠 보이기': 'Show all parts',
    '모든 파츠를 보이게 합니다': 'Makes every part visible',
    '모음별로 다른 칸': 'A different cell per vowel',
    '모자 얼굴처럼 표정·시선을 따로 움직일 얼굴이 하나 더 있을 때': 'When there is another face with its own expressions and gaze (e.g. a face on a hat)',
    '목록 위에 있을수록 앞에 그려집니다 (▲▼로 순서)': 'Higher in the list draws in front (reorder with ▲▼)',
    '목록에 모든 파츠를 보여 줍니다 (보이기는 그대로)': 'Shows all parts in the list (visibility unchanged)',
    '목록에 이 그룹 파츠만 표시': "Show only this group's parts in the list",
    '목록에서 누르면 바로 그 표정으로 바뀝니다 (키 없음)': 'Click in the list to switch to that expression right away (no key)',
    '바꾸면 자동 키': 'Auto-key on change',
    '바꿀 색': 'New color',
    '바인드에 실패했습니다 (얼굴 메시 모양을 확인하세요)': 'Binding failed (check the face mesh shape)',
    '반전 그림을 둘 칸. 보통 이미지에서 비어 있는 칸': 'Cell to hold the flipped drawing. Usually an empty cell in the image',
    '배치 (마커 기준)': 'Placement (marker-based)',
    '배치 모드 끄기': 'Exit arrange mode',
    '배치 모드 끔': 'Arrange mode off',
    '배치 모드를 끕니다 (ESC 또는 우클릭)': 'Exits arrange mode (ESC or right-click)',
    '배치 켜기 (머티리얼 다시 만들기)': 'Enable placement (rebuild material)',
    "배치를 마치면 '프리셋 저장'으로 표정을 만드세요": "When placement is done, create an expression with 'Save preset'",
    '범위': 'Range',
    '보간은 태그마다 따로 저장됩니다 (같은 태그 파츠끼리 공유)': 'Interpolation is stored per tag (shared by parts with the same tag)',
    '보이기': 'Visible',
    '보통': 'Normal',
    '복제: ': 'Duplicated: ',
    '부드럽게': 'Smooth',
    '부드럽게 가속·감속 (Bezier)': 'Smooth ease in/out (Bezier)',
    '부모': 'Parent',
    '부모 따라감': 'Follows parent',
    '부모 파츠를 고르면 부모의 위치·회전·크기·불투명도·색(HSV·색 덮기)·시선을 그대로 따라갑니다 (자식은 부모 바로 위에 그려짐). 지정할 때 그림은 제자리 유지': "With a parent part set, this part follows the parent's position, rotation, scale, opacity, color (HSV, color overlay) and gaze (the child draws right above the parent). The drawing stays in place when assigned",
    '부모(%s)의 위치·시선을 따라갑니다': 'Follows the position and gaze of the parent (%s)',
    '부모만 켜면 자식(홍채·하이라이트)은 같이 움직입니다': 'Turn on only the parent and its children (iris, highlights) move along',
    '분노 마크처럼 얼굴 밖으로 나가는 연출용 평면 (머리 본을 따라감)': 'A plane for effects that go outside the face, like anger marks (follows the head bone)',
    '불러오기 (덮어쓰기)': 'Import (overwrite)',
    '불러오기 실패: ': 'Import failed: ',
    '불러왔습니다 (시트 %d장). 뷰포트 컨트롤러는 컨트롤러 탭에서 다시 만드세요': 'Imported (%d sheets). Rebuild the viewport controllers in the Controllers tab',
    '뷰포트 가볍게': 'Lighter viewport',
    '뷰포트 컨트롤러 (시선 패드)': 'Viewport controller (gaze pad)',
    '뷰포트 컨트롤러의 격자 아래에 이 시퀀스 전용 슬라이더를 추가합니다 (닫힘/반/열림, 단일 입이면 끔/켬). 메인 시퀀스는 항상 표시됩니다': 'Adds a slider for this sequence under the viewport controller grid (closed/half/open, or off/on for a single mouth). The main sequence is always shown',
    '뷰포트에 네모 패드와 가운데 십자 손잡이를 만듭니다': 'Creates a square pad with a center cross handle in the viewport',
    '뷰포트에 시선 패드(눈동자 컨트롤러)를 만들거나 다시 만들거나 지웁니다': 'Creates, rebuilds or removes the gaze pad (pupil controller) in the viewport',
    '뷰포트에 위치 마커를 표시합니다': 'Shows position markers in the viewport',
    '뷰포트에 이 파츠의 시트 격자를 띄웁니다. 노란 테두리를 끌면 칸이 바뀝니다 (칸이 2개 이상인 파츠만)': "Shows this part's sheet grid in the viewport. Drag the yellow frame to change cells (parts with 2+ cells only)",
    '뷰포트에 표정 목록 컨트롤러를 만들거나 다시 만들거나 지웁니다. 손잡이를 끌어 표정을 고릅니다': 'Creates, rebuilds or removes the expression list controller. Drag the handle to pick an expression',
    '뷰포트에서 얼굴 캔버스 위를 클릭해 이 마커의 위치를 정합니다 (정면 뷰 권장)': 'Click on the face canvas in the viewport to set this marker (front view recommended)',
    '뷰포트에서 자유 변형': 'Free transform in viewport',
    '뷰포트에서 자유 변형 (Ctrl+T)': 'Free transform in viewport (Ctrl+T)',
    '뷰포트의 Show Overlays를 꺼도 컨트롤러(표정 목록/시선 패드 등)를 보이게 합니다. 화면 표시용이며 렌더에는 나오지 않습니다': 'Keeps controllers (expression list, gaze pad, ...) visible even with viewport overlays off. Display only, not rendered',
    '블렌드 파일 기준 상대 경로로 저장 (폴더째 옮겨도 유지)': 'Store as a path relative to the .blend (survives moving the whole folder)',
    '비우면 자동 (태그 이름 + 번호)': 'Leave empty for automatic (tag name + number)',
    '비우면 활성 UV 맵': 'Empty = active UV map',
    "비워 두면 '태그 이름 + 번호'로 자동으로 붙습니다": "If left empty, it is named 'tag name + number' automatically",
    '상대 경로': 'Relative path',
    '상하': 'Vertical',
    '새 캔버스 만들기': 'Create new canvas',
    '새 파츠 레이어를 맨 앞에 추가합니다': 'Adds a new part layer at the front',
    '새 파츠 크기 (1 = 캔버스 전체)': 'New part size (1 = whole canvas)',
    '새 파츠를 마커보다 위(+)/아래(-)에 놓기': 'Place new parts above (+) / below (-) the marker',
    '새 파츠를 이 태그의 가장 아래 파츠 모양으로 클리핑하고 그 바로 위에 놓습니다 (예: 눈동자 → 흰자 태그)': "Clips new parts to the shape of this tag's bottom-most part and places them right above it (e.g. iris → the eye-white tag)",
    "새 파츠의 '대칭 복사'를 켠 채로 추가": "Add new parts with 'Symmetry copy' on",
    "새 파츠의 '시선 따라 이동'을 켠 채로 추가": "Add new parts with 'Follow gaze' on",
    '새 폴더': 'New folder',
    '새 폴더 (지금 보이는 파츠로)': 'New folder (from visible parts)',
    '색': 'Color',
    '색 덮기': 'Color overlay',
    '색 맞추기': 'Color match',
    '색 칸을 누르면 Hex(784343 등)로 입력할 수 있습니다': 'Click a color field to enter a hex value (e.g. 784343)',
    '색상만': 'Color only',
    '색조 %+.0f°, 채도 ×%.2f, 명도 ×%.2f': 'Hue %+.0f°, saturation ×%.2f, value ×%.2f',
    '색조 이동 (-0.5~0.5 = -180°~180°)': 'Hue shift (-0.5–0.5 = -180°–180°)',
    '색조/채도/명도 계산': 'Calculate hue/saturation/value',
    '색조/채도/명도 초기화': 'Reset hue/saturation/value',
    '선택 범위에 지정': 'Assign to selection',
    '선택 영역 수정': 'Edit selection area',
    '선택 영역 수정 중': 'Editing selection area',
    '선택 영역 적용': 'Apply selection area',
    '선택 영역을 복사하지 못했습니다': 'Could not copy the selection',
    '선택된 면이 없습니다': 'No faces selected',
    '선택한 메시 추가': 'Add selected meshes',
    '선택한 메시(얼굴·머리카락·모자 등)를 카메라 시선 방향으로 눌러 2D 그림처럼 보이게 합니다. 캔버스 파츠도 같이 눌립니다. 렌더 카메라 기준 연출': 'Squashes the selected meshes (face, hair, hat...) along the camera view so they read like a 2D drawing. Canvas parts are squashed too. Based on the render camera',
    '선택한 키프레임이 없습니다 (도프시트·그래프 에디터에서 키를 선택하세요)': 'No keyframes selected (select keys in the Dope Sheet / Graph Editor)',
    "선택한 파츠 자리에 폴더를 만들고 그 파츠를 넣습니다. 같은 태그·같은 자리의 폴더끼리는 하나만 켜져서, 예를 들어 '일반 눈'과 '폭소 눈' 폴더를 눈 하나로 전환할 수 있습니다": "Creates a folder in place of the selected part and puts the part in it. Only one folder with the same tag and spot is on at a time, so e.g. 'normal eyes' and 'laughing eyes' folders can be switched as one eye",
    '선택한 파츠: ': 'Selected part: ',
    '선택한 파츠를 그림·값·키프레임까지 똑같이 복제해 바로 위에 놓습니다 (이름 뒤에 .001)': 'Duplicates the selected part, including image, values and keyframes, right above it (name gets .001)',
    '성능 측정': 'Profile performance',
    '성능 측정 (8초)': 'Profile performance (8 s)',
    '세기': 'Strength',
    '세기는 리그 프로퍼티라 키를 넣을 수 있습니다 (I)': 'Strength is a rig property, so it can be keyed (I)',
    "손잡이를 끌면 '시선'을 켠 파츠가 따라 움직입니다": "Drag the handle and parts with 'Gaze' on move along",
    '순서 바꾸기': 'Reorder',
    '숫자패드 1처럼 얼굴 정면 뷰로 바꾸고 캔버스를 화면 가운데로 (얼굴 방향 설정 반영)': 'Switches to the face front view like Numpad 1 and centers the canvas (respects the face axis)',
    '쉼표로 구분 (예: 기본, 화남, 반짝, 당황)': 'Comma-separated (e.g. Default, Angry, Sparkle, Flustered)',
    '쉼표로 구분 (예: 닫힘, 반, 열림)': 'Comma-separated (e.g. Closed, Half, Open)',
    '시선 미리보기': 'Gaze preview',
    '시선 이동량 배율 (하이라이트를 덜/더 움직일 때)': 'Gaze movement multiplier (to move highlights less/more)',
    '시선 추가 이동': 'Extra gaze movement',
    '시선 컨트롤러': 'Gaze controller',
    '시선 컨트롤러 만들기': 'Create gaze controller',
    '시선 패드를 움직이면 이 레이어가 따라 움직입니다 (눈동자, 하이라이트)': 'This layer moves with the gaze pad (pupils, highlights)',
    '시선을 따라가는 파츠': 'Parts that follow the gaze',
    '시점 따라가기': 'Follow view',
    '시퀀스 %d개를 옮겼습니다': 'Moved %d sequences',
    '시퀀스(닫힘·반·열림) → 립싱크 순서로 설정하세요': 'Set up sequences (closed · half · open), then lip sync',
    '시퀀스:': 'Sequence:',
    "시퀀스를 '%s' 시트로 옮기기 (추천)": "Move sequences to the '%s' sheet (recommended)",
    '시퀀스를 입 파츠의 시트로 옮기기': "Move sequences to the mouth part's sheet",
    '시퀀스를 하나 이상 만들면 쓸 수 있습니다': 'Available once you create at least one sequence',
    '시트 불러오기 · 자르기': 'Load and slice sheets',
    '시트 삭제': 'Remove sheet',
    '시트 이미지를 찾을 수 없습니다': 'Sheet image not found',
    '시트를 목록에서 뺍니다 (이미 배치한 파츠는 그대로)': 'Removes the sheet from the list (parts already placed stay)',
    '시트에서 파츠를 고르고 태그를 정해 캔버스에 올립니다. 태그의 기준 마커 위치에 놓입니다': "Pick a part from a sheet, choose a tag and put it on the canvas. It is placed at the tag's marker",
    '시트의 칸 하나를 골라 배치': 'Pick one cell from a sheet and place it',
    '썸네일에서 칸을 고릅니다': 'Pick a cell from the thumbnails',
    '씬에 활성 카메라가 없습니다': 'The scene has no active camera',
    "씬에 활성 카메라가 없습니다. 카메라를 정한 뒤 '카메라 다시 연결'을 누르세요": "The scene has no active camera. Set one, then press 'Reconnect camera'",
    '아 (행, 열)': 'A (row, col)',
    '아래': 'Down',
    '아래 레이어들과 섞는 방식 (포토샵 레이어 혼합 모드)': 'How it mixes with the layers below (Photoshop blend modes)',
    '아래 버튼 → 머리 본 확인': 'Button below → check the head bone',
    '아래 버튼 누르기': 'Press the button below',
    '아래 버튼 누르기 → 새 캔버스로 전환됨': 'Press the button below → switches to the new canvas',
    '아래 범위': 'Down range',
    '아래 화살표로 끝까지 밀어 보며 맞추세요': 'Push it all the way with the down arrow while adjusting',
    '아래서': 'From bottom',
    '아마추어': 'Armature',
    '안쪽 드래그 = 이동 (Shift 45°)   ·   방향키 (Shift ×10)   ·   모서리/변 = 크기 (Shift 비율, Alt 기준점)   ·   바깥/○ = 회전 (Shift 15°)': 'Drag inside = move (Shift 45°)   ·   Arrow keys (Shift ×10)   ·   Corners/edges = scale (Shift ratio, Alt pivot)   ·   Outside/○ = rotate (Shift 15°)',
    '앞머리 등 다른 메시에 가려져도 이 파츠가 위로 보입니다 (눈썹 등). 보는 쪽으로 살짝 앞당긴 복사본을 그립니다': 'This part shows on top even when hidden by other meshes like bangs (brows etc.). Draws a copy pulled slightly toward the viewer',
    '앞으로 당기는 거리': 'Pull-forward distance',
    '앞쪽 복사본 위치 보기': 'Show front copy position',
    '애니메이션 키가 들어갈 아마추어(리그)를 고르세요': 'Pick the armature (rig) that will hold the animation keys',
    '어둡게 물들임': 'Darkening tint',
    '어떤 표정에서 말하든 이 시퀀스의 입을 씁니다 (전용 시퀀스가 있는 표정만 예외). 메인은 하나만 가능': "Uses this sequence's mouths when talking in any expression (except expressions with their own sequence). Only one main",
    '얼굴 메시 선택 → Tab (편집 모드)': 'Select the face mesh → Tab (Edit Mode)',
    '얼굴 메시 편집 모드에서 새로 고른 면으로 캔버스 메시만 바꿉니다. 파츠·마커·프리셋·설정과 그림 위치는 그대로 (같은 정면 UV를 이어서 씀)': "Replaces only the canvas mesh with the faces newly selected in the face mesh's Edit Mode. Parts, markers, presets, settings and drawing positions stay (the same front UV continues)",
    '얼굴 메시와 분리된, 눈·입이 그려질 메시를 만듭니다': 'Creates a mesh, separate from the face mesh, where the eyes and mouth are drawn',
    '얼굴 앞에 머리보다 넓은 평면 캔버스를 만들어 머리 본에 붙입니다. 분노 마크처럼 얼굴 밖으로 나가는 감정표현용. 파츠·태그·프리셋은 다른 캔버스와 같이 씁니다': 'Creates a flat canvas, wider than the head, in front of the face and parents it to the head bone. For emotes that go outside the face, like anger marks. Parts, tags and presets work like any other canvas',
    '얼굴 앞쪽으로 띄우는 거리 (Plane 크기 대비). 앞머리보다 앞에 오게': 'Distance in front of the face (relative to plane size). Put it in front of the bangs',
    '얼굴 움직임에 다시 붙이기': 'Re-attach to face motion',
    '얼굴 캔버스 레이어': 'Face canvas layer',
    "얼굴 캔버스 입은 ④ 입 파츠의 '배치 (이 칸만)'에서 칸별로 맞추는 것을 권합니다": "For face-canvas mouths, adjusting per cell in the ④ mouth part's 'Placement (this cell)' is recommended",
    '얼굴 캔버스 크기의 몇 배로 만들지': 'How many times the face canvas size',
    "얼굴 캔버스의 '입' 레이어로 그립니다. 모디파이어/노드를 따로 만들지 않고 캔버스 머티리얼이 이 시트를 읽습니다": "Drawn as the face canvas's 'Mouth' layer. No separate modifier/nodes; the canvas material reads this sheet",
    '얼굴 캔버스의 입 레이어로 그려집니다 (배치는 얼굴 캔버스 패널에서)': "Drawn as the face canvas's mouth layer (placement in the face canvas panel)",
    '얼굴 표면보다 얼마나 안쪽(+)/바깥쪽(-)에 있는 것처럼 보일지. 고개를 돌리면 깊은 레이어가 표면보다 덜 따라와 입체감이 생깁니다 (예: 홍채 0.01, 동공 0.02, 하이라이트 -0.005). 자식은 부모 깊이에 더해집니다': "How far inside (+) / outside (-) the face surface it appears. When the head turns, deeper layers lag behind the surface for a sense of depth (e.g. iris 0.01, pupil 0.02, highlight -0.005). Children add to their parent's depth",
    '얼굴 표면에서 띄우는 거리 (선택 영역 높이 대비 %). 깜빡이면(Z-fighting) 조금 올리세요': 'Distance from the face surface (% of the selection height). Raise it a little if it flickers (Z-fighting)',
    '얼굴(%s) 움직임을 따라가게 붙였습니다': 'Attached to follow the face (%s)',
    '얼굴·머리카락·모자 등 같이 눌릴 메시를 선택': 'Select meshes to squash together (face, hair, hat...)',
    '얼굴·머리카락·모자 등 같이 눌릴 메시를 선택하고 누르세요': 'Select meshes to squash together (face, hair, hat...) and press',
    '얼굴에서 띄우기': 'Lift from face',
    '얼굴이 +X를 봄 (정면 = 숫자패드 3)': 'Face looks along +X (front = Numpad 3)',
    '얼굴이 +Y를 봄 (정면 = Ctrl+숫자패드 1)': 'Face looks along +Y (front = Ctrl+Numpad 1)',
    '얼굴이 -X를 봄 (정면 = Ctrl+숫자패드 3)': 'Face looks along -X (front = Ctrl+Numpad 3)',
    '얼굴이 -Y를 봄 (정면 = 숫자패드 1). Blender 기본': 'Face looks along -Y (front = Numpad 1). Blender default',
    '에 (행, 열)': 'E (row, col)',
    '여기 %는 칸 창 안에서 확대라 100%를 넘기면 가장자리가 잘릴 수 있습니다': 'These % values zoom inside the cell window, so going over 100% can clip the edges',
    '여기 값은 모든 칸에 똑같이 적용되고, 키·애니메이션은 이 값에 들어갑니다': 'These values apply to every cell, and keys/animation go into these values',
    '여러 파츠를 골라 속성을 한꺼번에 조절합니다': 'Pick several parts and adjust their properties at once',
    '영역 수정을 그만두고 캔버스를 다시 보이게 합니다': 'Stops editing the area and shows the canvas again',
    '옆모습일수록 더': 'More in profile',
    '옆모습일수록 더 누르기 (0 = 각도와 상관없이 같게)': 'Squash more the closer to profile (0 = same at any angle)',
    "예전 '반전 칸 만들기'로 다른 칸 그림을 가져다 쓰던 칸을 모두 원래 칸으로 되돌립니다 (그 칸의 크기·위치도 지움)": "Restores every cell that borrowed another cell's drawing via the old 'Make flipped cell' (also clears those cells' size/position)",
    '오 (행, 열)': 'O (row, col)',
    '오디오 립싱크를 굽을 때 이 시트의 열(입)에도 키를 넣습니다': "Also keys this sheet's column (mouth) when baking audio lip sync",
    '오른쪽': 'Right',
    '오른쪽 범위': 'Right range',
    '오른쪽에서': 'From right',
    '오버레이가 아직 없습니다': 'No overlay yet',
    '왼쪽': 'Left',
    '왼쪽 범위': 'Left range',
    '왼쪽에서': 'From left',
    '우 (행, 열)': 'U (row, col)',
    '움직이는 범위 (끝까지 밀었을 때)': 'Movement range (when pushed all the way)',
    '움직임': 'Motion',
    '원근 뷰가 되어 자유 변형을 확정하고 끝냈습니다': 'Switched to perspective view; free transform applied and ended',
    '원래 색': 'Original color',
    '원래 색: #%02X%02X%02X': 'Original color: #%02X%02X%02X',
    "원래 색이 무채색이라 색조를 바꿀 수 없습니다 (색 덮기 '색상만'을 쓰세요)": "The original color is neutral, so its hue can't be shifted (use Color overlay 'Color only')",
    '위': 'Up',
    "위 '배치'는 이 값 + 칸별 보정입니다": "'Placement' above = these values + per-cell adjustments",
    '위 범위': 'Up range',
    '위아래 같게': 'Same up and down',
    '위에 있을수록 앞에 그려집니다': 'Higher items draw in front',
    '위에서': 'From top',
    '위치': 'Position',
    '위치 0, 크기 1, 회전 0, 불투명도 1로 되돌립니다': 'Resets to position 0, size 1, rotation 0, opacity 1',
    '음량으로 닫힘/반 열림/열림 전환': 'Switches closed/half/open by volume',
    '음소거': 'Mute',
    '이 (행, 열)': 'I (row, col)',
    '이 개방도 이상이면 반 열림': 'Half open at or above this openness',
    '이 개방도 이상이면 열림': 'Open at or above this openness',
    '이 레이어 그림을 데칼 안에서 좌우로 뒤집습니다': "Flips this layer's drawing horizontally within the decal",
    '이 레이어가 보일 영역. 고른 레이어(예: 흰자)의 지금 칸 모양 안에서만 보입니다': 'Where this layer is visible: only inside the current cell shape of the chosen layer (e.g. the eye white)',
    '이 레이어로 그릴 입 스프라이트 시트': 'Mouth sprite sheet drawn by this layer',
    '이 마커 사용': 'Use this marker',
    "이 시퀀스의 단계를 지금 바로 보여 줍니다 (키는 넣지 않음). 기준 칸으로 표정이 바뀌며, '끄기'로 말하기를 끕니다": "Shows this sequence's step right now (no key). The expression switches to the base cell; 'Off' stops talking",
    '이 시트를 그리는 입 파츠가 없습니다 — 미리보기·시퀀스가 화면에 안 보입니다': "No mouth part draws this sheet — preview and sequences won't show",
    '이 시트의 시퀀스를 ④ 입 파츠가 그리는 시트로 옮기고, 이 시트는 지웁니다 (같은 입 그림을 쓰는 시트끼리)': "Moves this sheet's sequences to the sheet the ④ mouth part draws, and removes this sheet (between sheets using the same mouth image)",
    '이 시트의 이미지를 다른 파일로 바꿉니다. 이 시트에서 올린 파츠와 입 시퀀스도 새 이미지를 씁니다': "Replaces this sheet's image with another file. Parts and mouth sequences from this sheet use the new image too",
    "이 입 모양을 지금 바로 보여 줍니다 (키는 넣지 않음). '끄기'로 표정 칸으로 돌아갑니다": "Shows this mouth shape right now (no key). 'Off' returns to the expression cell",
    '이 입 키 넣기': 'Key this mouth',
    '이 입의 모든 키': 'All keys of this mouth',
    '이 입의 위치·크기·회전·불투명도·크롭 키 전부': 'All position, size, rotation, opacity and crop keys of this mouth',
    '이 칸 %d-%d': 'This cell %d-%d',
    '이 칸 배치 되돌리기': "Reset this cell's placement",
    '이 칸에 그림이 없습니다': 'This cell has no drawing',
    '이 칸을 일괄 조절할 칸으로 체크합니다. 지금 칸의 배치를 바꾸면 체크한 칸들도 같이 바뀝니다 (크기는 같은 비율, 위치·회전은 움직인 만큼)': "Checks this cell for batch editing. Changing the current cell's placement changes the checked cells too (size by the same ratio, position/rotation by the same amount)",
    '이 칸을 일괄 조절할 칸으로 체크합니다. 지금 칸의 크기·위치를 바꾸면 체크한 칸들도 같이 바뀝니다 (크기는 같은 비율, 위치는 움직인 만큼)': "Checks this cell for batch editing. Changing the current cell's size/position changes the checked cells too (size by the same ratio, position by the same amount)",
    '이 칸을 지금 칸으로 만들어 뷰포트에 바로 보여 줍니다 (자동 키가 켜져 있으면 키도 들어감). 배치는 이 칸 기준으로 조절됩니다': 'Makes this the current cell and shows it in the viewport (also keys it if auto-key is on). Placement is then adjusted for this cell',
    '이 칸을 지금 칸으로 만들어 뷰포트에 바로 보여 줍니다 (자동 키가 켜져 있으면 키도 들어감). 크기·위치는 이 칸 기준으로 조절됩니다': 'Makes this the current cell and shows it in the viewport (also keys it if auto-key is on). Size/position are then adjusted for this cell',
    '이 칸이 표정으로 선택되어 있을 때 (행, 열)': 'When this cell is selected as the expression (row, col)',
    '이 컨트롤러는 크기를 바꿀 수 없습니다 (위치만 옮길 수 있음)': "This controller can't be resized (it can only be moved)",
    '이 태그 파츠가 앞머리 등에 가려져도 위로 보이게 (지금 있는 파츠에도 바로 적용)': "Show this tag's parts on top even when hidden by bangs etc. (applies to existing parts right away)",
    '이 태그 파츠는 ⑥의 입 시퀀스·립싱크로 칸이 바뀝니다': "This tag's parts change cells via the ⑥ mouth sequences · lip sync",
    '이 태그 파츠에 키를 넣을 때 쓸 보간 방법 (위치·크기·회전·불투명도·크롭). 태그마다 따로 저장. 칸(그림) 키는 항상 Constant': "Interpolation used when keying this tag's parts (position, size, rotation, opacity, crop). Stored per tag. Cell (image) keys are always Constant",
    '이 태그 파츠의 위치 X/Y가 이 마커로부터의 거리가 됩니다': "This tag's parts' Position X/Y becomes the offset from this marker",
    '이 탭의 컨트롤러만 배치 모드로: 틀을 선택해 옮길 수 있습니다. 다시 누르거나 ESC/우클릭으로 끕니다': 'Arrange mode for controllers: select frames to move them. Press again or ESC/right-click to exit',
    '이 파츠 키 넣기': 'Key this part',
    '이 파츠에 이미 넣은 키 전부(위치·크기·회전·불투명도·크롭)를 지금 고른 보간 방법으로 바꿉니다': 'Changes all existing keys on this part (position, size, rotation, opacity, crop) to the chosen interpolation',
    '이 파츠의 스프라이트 시트 (칸 = 파츠의 상태)': "This part's sprite sheet (cells = part states)",
    '이 파츠의 위치·크기·회전·불투명도·크롭 키 전부': 'All position, size, rotation, opacity and crop keys of this part',
    '이 파츠의 지금 값 전부(칸·위치·크기·회전·불투명도·크롭)를 현재 프레임에 키로 넣습니다': 'Keys all current values of this part (cell, position, size, rotation, opacity, crop) on the current frame',
    '이 폴더 삭제': 'Remove this folder',
    '이 폴더 키 넣기': 'Key this folder',
    '이 폴더로 전환': 'Switch to this folder',
    "이 폴더를 켜고 같은 태그·같은 자리의 다른 폴더는 끕니다 ('바꾸면 자동 키'가 켜져 있으면 키도 넣음)": "Turns this folder on and other folders with the same tag and spot off (also keys if 'Auto-key on change' is on)",
    "이 폴더의 파츠만 보이게 전환합니다 ('바꾸면 자동 키'가 켜져 있으면 키도 넣음)": "Switches so that only this folder's parts are visible (also keys if 'Auto-key on change' is on)",
    '이 표정을 적용하고 현재 프레임에 키를 넣습니다 (이 프레임부터 표정이 바뀜)': 'Applies this expression and keys it on the current frame (the expression changes from this frame)',
    '이름을 정해 새로 만듭니다': 'Create a new one with a name',
    '이미 넣은 입 배치 키에 지금 고른 보간 방법을 적용합니다 (선택한 키프레임만 / 이 입의 모든 키)': 'Applies the chosen interpolation to existing mouth placement keys (selected keyframes only / all keys of this mouth)',
    '이미 넣은 키에 지금 고른 보간 방법을 적용합니다 (선택한 키프레임만 / 이 파츠의 모든 키)': 'Applies the chosen interpolation to existing keys (selected keyframes only / all keys of this part)',
    "이미 있는 '%s' 마커에 '%s' 태그를 연결합니다": "Existing marker '%s': link tag '%s'",
    '이미지 다시 불러오기': 'Reload image',
    '이미지 텍스처 앞에 Mapping 노드를 넣어 이동': 'Inserts a Mapping node before the image texture to move it',
    '이미지를 바꿨습니다: ': 'Image replaced: ',
    '이미지를 찾지 못해 빠졌습니다: ': 'Left out because the image was not found: ',
    '일괄 조절할 칸': 'Cells to batch adjust',
    '일정한 속도로 변함': 'Changes at a constant rate',
    '입 (시퀀스·립싱크)': 'Mouth (sequence · lip sync)',
    '입 모양이 이보다 짧게 바뀌면 앞 모양에 합칩니다. 2 = 애니메이션식 on twos': "Mouth shapes shorter than this merge into the previous shape. 2 = animation-style 'on twos'",
    '입 벌림 (선택한 구간):': 'Mouth opening (selected range):',
    '입 스프라이트 시트를 그대로 그림 (시퀀스·립싱크·뷰포트 컨트롤러가 그대로 동작)': 'Draws the mouth sprite sheet as is (sequences, lip sync and viewport controllers keep working)',
    '입 시퀀스 · 표정 목록 · 시선 패드를 뷰포트에 만듭니다': 'Creates the mouth sequence, expression list and gaze pad in the viewport',
    '입 전체 배치': 'Whole-mouth placement',
    '입 칸을 고르거나 입 배치(위치·크기·회전·불투명도·크롭), 시퀀스 선택·말하기 값을 바꾸면 현재 프레임에 키를 바로 넣습니다 (꺼져 있어도 Blender 자동 키가 켜져 있으면 칸은 삽입)': "Keys the current frame right away when you pick a mouth cell or change mouth placement (position, size, rotation, opacity, crop), sequence choice or talk value (even when off, cells are keyed if Blender's auto-keying is on)",
    '입 키 넣기': 'Key mouth',
    '입 키를 넣을 때 쓸 보간 방법 (입 전체의 위치·크기·회전·불투명도·크롭). 칸·시퀀스·말하기 키는 항상 Constant': 'Interpolation for mouth keys (whole-mouth position, size, rotation, opacity, crop). Cell, sequence and talk keys are always Constant',
    '입 파츠 추가 방법': 'How to add a mouth part',
    "입 파츠는 '%s' 시트를 그리고 있습니다. 옮기면 이 시트는 지워집니다": "The mouth part draws the '%s' sheet. Moving removes this sheet",
    '입 파츠는 지원하지 않습니다': 'Not supported for mouth parts',
    '입 파츠에 연결': 'Link to mouth part',
    '자동 (표정 따라)': 'Auto (follow expression)',
    '자식 펼치기': 'Expand children',
    "자식에서 켜면 부모 위에 '추가로' 더 움직임 (배율로 양 조절)": "On a child, moves 'in addition' to the parent (amount via the multiplier)",
    '자유 변형 (Ctrl+T)': 'Free transform (Ctrl+T)',
    '자유 변형 시작 실패: ': 'Free transform failed to start: ',
    '자유 변형이 중단되었습니다 (Undo·파일 열기·파츠 삭제)': 'Free transform was interrupted (undo, file open, or part deleted)',
    '작게 벌린 칸 (행, 열). -1 = 기준 칸 그대로': 'Slightly open cell (row, col). -1 = keep the base cell',
    '저장하고 끝내기': 'Save and finish',
    '저장하지 않고 끝냅니다 (멈췄던 키프레임을 되살림)': 'Finish without saving (restores the paused keyframes)',
    '적용': 'Apply',
    '적용할 메시: ': 'Meshes to apply: ',
    '전부 지우기': 'Remove all',
    '전체': 'All',
    '전체 배치 (모든 칸 공통)': 'Overall placement (shared by all cells)',
    '전체 보기': 'Show all',
    '전체 보기 (폴더 없이)': 'Show all (no folder)',
    '전환': 'Switch',
    '정렬': 'Arrange',
    '종횡비 고정 (이 칸)': 'Lock aspect (this cell)',
    '종횡비 고정 중: 세로를 바꾸면 가로도 같은 비율로': 'Aspect locked: changing the height changes the width by the same ratio',
    '좌우': 'Horizontal',
    '좌우 같게': 'Same left and right',
    '중간 칸 (행, 열). -1 = 열림 칸 사용': 'Middle cell (row, col). -1 = use the open cell',
    '중심 다시 잡기': 'Recenter',
    '지금 고른 캔버스의 파츠·태그·마커·시트·표정 프리셋·입 시퀀스·립싱크 설정과 속성값, 시트 이미지(원본 해상도)를 .zip 하나로 저장합니다 (키프레임 제외)': "Saves the selected canvas's parts, tags, markers, sheets, expression presets, mouth sequences, lip sync settings, property values and sheet images (original resolution) into one .zip (no keyframes)",
    '지금 보이는 칸의 그림으로 파츠 중심을 다시 계산합니다 (그림 위치는 그대로)': 'Recalculates the part center from the drawing in the visible cell (drawing position unchanged)',
    '지금 보이는 파츠 배치(칸·위치·크기·회전·불투명도, 입 칸)를 표정으로 저장합니다': 'Saves the current part layout (cells, position, size, rotation, opacity, mouth cell) as an expression',
    '지금 보이는 파츠들로 새 폴더를 만듭니다': 'Creates a new folder from the currently visible parts',
    '지금 보이는 파츠로 덮어쓰기': 'Overwrite with visible parts',
    '지금 선택된 칸을 기준 칸으로 하는 시퀀스를 추가합니다 (열림 = 기준 칸). 닫힘 칸을 지정해 주세요': 'Adds a sequence with the selected cell as its base (open = base cell). Set the closed cell',
    '지금 시점에서는 파츠를 가리는 메시가 없습니다 (가려지는 각도에서 다시 눌러 보세요)': 'No mesh covers the parts from this view (try again from an angle where they are hidden)',
    '지금 씬의 활성 카메라를 기준으로 누르게 합니다': "Uses the scene's current active camera for flattening",
    "지금 칸 그림에서 가장 많이 쓰인 색을 '원래 색'으로 넣습니다 (스포이트는 화면 색이라 조명·색 관리 때문에 틀릴 수 있음)": "Sets 'Original color' to the most-used color in the current cell's drawing (the eyedropper reads screen colors, which lighting and color management can skew)",
    '지금 칸(빨간 버튼)의 배치를 바꾸면 체크한 칸도 같이 바뀝니다': "Changing the current cell's (red button) placement also changes the checked cells",
    '지금 칸만 종횡비를 고정하거나 풉니다 (칸마다 따로). 일괄 조절로 체크한 칸에도 같이 적용': 'Locks or unlocks the aspect for the current cell only (per cell). Also applies to cells checked for batch adjust',
    '지금 칸에 저장된 크기·위치·반전과 다른 칸 그림 연결을 모두 지우고, 이미지에 그려진 원래 칸으로 되돌립니다 (이미지 파일은 건드리지 않음)': "Clears the current cell's stored size, position, flip and cell link, returning it to the original cell drawn in the image (the image file is untouched)",
    '지금 칸의 그림 크기 (칸마다 따로가 꺼져 있으면 공통)': "Drawing size of the current cell (shared if 'Per cell' is off)",
    '지금 칸의 그림을 뒤집어서 다른 칸 번호로 씁니다. 이미지에 반전 그림을 따로 그릴 필요가 없습니다': "Uses a flipped copy of the current cell's drawing as another cell number. No need to draw flipped versions in the image",
    '지금 칸의 그림을 위아래로 뒤집습니다': "Flips the current cell's drawing vertically",
    '지금 칸의 그림을 좌우로 뒤집습니다': "Flips the current cell's drawing horizontally",
    '지금 칸의 칸별 배치(위치·크기·회전·불투명도·크롭)를 지워 전체 배치 값으로 되돌립니다 (일괄 조절로 체크한 칸도 같이)': "Clears the current cell's per-cell placement (position, size, rotation, opacity, crop), returning to the overall placement (also for checked cells)",
    '지금 칸의 크기/위치를 공통값으로 만들고 다른 칸의 개별 설정을 모두 지웁니다': "Makes the current cell's size/position the shared value and clears every other cell's individual settings",
    "지금 캔버스 영역(면 %d개)을 선택해 두었습니다. 면을 더하거나 빼고 '적용'을 누르세요": "The current canvas area (%d faces) is selected. Add or remove faces, then press 'Apply'",
    '지금 캔버스 영역이 선택되어 있습니다': 'The current canvas area is selected',
    '지금 캔버스의 UV 투영을 알아내지 못했습니다': "Could not determine the current canvas's UV projection",
    '지금 파츠 상태를 이 프리셋에 덮어쓰고, 멈췄던 키프레임을 되살립니다': 'Overwrites this preset with the current part state and restores the paused keyframes',
    '지금 폴더를 지금 보이는 파츠들로 덮어씁니다': 'Overwrites the current folder with the visible parts',
    '지금 폴더를 지웁니다 (파츠는 그대로)': 'Removes the current folder (parts stay)',
    '지우기': 'Remove',
    '지정 해제 (표정 따라)': 'Clear (follow expression)',
    '초': 's',
    '초당 약 12번 따라감 (조금 끊겨 보이지만 가벼움)': 'Follows about 12 times per second (a bit choppy but light)',
    '취소': 'Cancel',
    '측정 중 (%d초) — 렉이 나는 동작을 해 주세요': 'Profiling (%d s) — do the actions that lag',
    '측정 중…': 'Profiling…',
    '카메라 다시 연결': 'Reconnect camera',
    '카메라 시선 방향으로 머리를 누르는 정도': 'How much to squash the head along the camera view',
    '카메라: ': 'Camera: ',
    '칸': 'Cell',
    '칸 가운데(= 마커 + 위치)를 기준으로 크기·회전': 'Scale/rotate around the cell center (= marker + position)',
    '칸 배치가 같아야 파츠 번호가 유지됩니다': 'Part numbers are kept only if the cell layout is the same',
    '칸 썸네일 격자를 펼쳐 일괄 조절할 칸을 고릅니다': 'Expand the cell thumbnail grid to pick cells for batch adjust',
    '칸 안에 그려진 그림의 가운데를 기준으로 크기·회전': 'Scale/rotate around the center of the drawing inside the cell',
    '칸 하나를 표정으로 고르고, 말할 때 입은 모음 또는 시퀀스로 지정합니다': 'Pick one cell as the expression, and set talking mouths by vowel or sequence',
    '칸별 배치': 'Per-cell placement',
    '칸이 바뀔 오브젝트 (입 데칼, 범고래 얼굴 등)': 'Object whose cells change (mouth decal, a hat face, etc.)',
    '캐릭터 얼굴이 바라보는 축. 캔버스 정면 투영 UV와 마커 찍기 화면 방향의 기준이 됩니다': "The axis the character's face looks along. Used for the canvas front-projected UVs and the marker-placing view",
    '캔버스': 'Canvas',
    '캔버스 가장자리 여백 (파츠가 테두리에 잘리지 않게)': "Margin at the canvas edge (so parts aren't clipped at the border)",
    '캔버스 내보내기': 'Export canvas',
    '캔버스 메시를 직접 고친 뒤(Extrude·정점 이동 등) 누르세요. 늘린 면에 같은 정면 UV를 이어 주고, 얼굴에 다시 붙입니다. 기존 파츠·마커 위치는 그대로': 'Press after editing the canvas mesh yourself (extrude, moving vertices...). Extends the same front UVs onto new faces and re-attaches to the face. Existing parts and markers stay in place',
    '캔버스 불러오기 (덮어쓰기)': 'Import canvas (overwrite)',
    '캔버스 영역을 바꿨습니다 (면 %d개)': 'Canvas area changed (%d faces)',
    '캔버스 위 위치 (0~1, 정면 기준). 다시 찍거나 숫자로 조절': 'Position on the canvas (0–1, front view). Re-place or adjust numerically',
    '캔버스 추가 (모자 얼굴 · 감정표현 Plane)': 'Add canvas (hat face · emote plane)',
    '캔버스(%s)를 선택하면 켜집니다': 'Enabled when the canvas (%s) is selected',
    '캔버스가 붙은 얼굴 메시를 찾지 못했습니다': 'Could not find the face mesh the canvas is attached to',
    '캔버스가 아니라 얼굴 메시(원본)를 편집 모드로 열고 면을 고르세요': 'Open the face mesh (source), not the canvas, in Edit Mode and select faces',
    '캔버스가 얼굴 메시의 최종 모양(아마추어·셰이프 키)을 그대로 따라가게 다시 붙입니다. 리그에 캔버스를 따로 바인드해서 일그러질 때 누르세요 (캔버스의 아마추어 모디파이어는 지워짐)': "Re-attaches the canvas so it follows the face mesh's final shape (armature, shape keys). Press when the canvas distorts because it was bound to the rig separately (the canvas's Armature modifier is removed)",
    '캔버스가 얼굴과 따로 움직일 수 있습니다. 위 버튼으로 다시 붙이세요': 'The canvas may move separately from the face. Re-attach it with the button above',
    '캔버스가 얼굴의 서브디비전 없이 같은 변형(아마추어·셰이프 키)만 따라가게 합니다. 리그를 움직이거나 재생할 때 훨씬 가볍고(얼굴 GPU 서브디비전도 다시 켜짐), 렌더에서는 지금처럼 실제 얼굴 표면에 딱 맞습니다. 뷰포트에서는 파츠가 얼굴에서 아주 살짝 더 떠 보일 수 있습니다': "Makes the canvas follow the same deformation (armature, shape keys) without the face's subdivision. Much lighter when posing or playing back (face GPU subdivision turns back on), and renders still fit the real face surface. In the viewport, parts may float very slightly off the face",
    '캔버스는 얼굴을 따라가므로 고르지 않아도 됩니다': 'The canvas follows the face, so no need to select it',
    '캔버스로 쓸 앞면을 면 선택': 'Face-select the front faces to use as the canvas',
    '캔버스를 얼굴 표면에서 띄우는 거리. 비스듬히 볼 때 피부가 줄무늬처럼 비쳐 보이면(Z-fighting) 조금 올리세요': 'Distance the canvas floats above the face surface. Raise it a little if skin shows through as stripes at grazing angles (Z-fighting)',
    "캔버스를 잠시 숨기고 얼굴 메시를 편집 모드로 엽니다. 지금 캔버스 영역이 미리 선택되어 있으니 면을 더하거나 빼고 '적용'을 누르세요": "Temporarily hides the canvas and opens the face mesh in Edit Mode. The current canvas area is preselected; add or remove faces and press 'Apply'",
    '캔버스를 찾지 못했습니다': 'Canvas not found',
    '컨트롤러 위치 옮기기 (배치 모드)': 'Move controllers (arrange mode)',
    '컨트롤러가 생기거나 크기가 바뀌면 기본 배치로 다시 쌓습니다. 직접 옮긴 자리를 지키려면 끄세요': 'Re-stacks controllers into the default layout when one is added or resized. Turn off to keep positions you moved by hand',
    '켜면 아래 범위 = 위 범위 (보통 아래를 조금 더 크게)': 'When on, down range = up range (usually make down a bit larger)',
    "켜면 아래에서 고른 그룹(태그)만 바꿉니다 ('화난 눈 + 웃는 입'처럼 섞기). 끄면 표정 전체를 바꿉니다": "When on, only the groups (tags) chosen below change (mix like 'angry eyes + smiling mouth'). When off, the whole expression changes",
    '켜면 왼쪽 범위 = 오른쪽 범위': 'When on, left range = right range',
    '켜면 이 눈은 자기 파츠 목록 대신 따라가는 눈의 파츠 전체를 좌우로 뒤집어 씁니다. 왼눈만 세팅하면 됩니다': "When on, this eye uses all of the followed eye's parts mirrored instead of its own list. Only the left eye needs setting up",
    '켜면 지금 가로세로 비율을 그대로 지킨 채 가로·세로가 같이 커지고 작아집니다. 꺼도 모양은 그대로': 'When on, width and height scale together, keeping the current aspect. Turning it off keeps the shape',
    '켜면 지금 가로세로 비율을 그대로 지킨 채 가로나 세로를 바꿀 때 둘이 같이 커지고 작아집니다 (이 입 칸만)': 'When on, changing width or height scales both together, keeping the current aspect (this mouth cell only)',
    '켜면 크기 하나로 가로·세로를 같이, 끄면 따로 조절': 'On: one size controls width and height together. Off: adjust separately',
    '켜면 크기/위치를 칸마다 따로 기억합니다 (손대지 않은 칸은 공통값). 끄면 모든 칸이 공통값을 씁니다': 'When on, size/position are remembered per cell (untouched cells use the shared value). When off, all cells use the shared value',
    '켜면 키프레임을 무시하고 고른 칸을 계속 보여 줍니다 (칸을 골라도 키가 들어가지 않음). 칸별 배치를 조절할 때 켜고, 끝나면 끄세요': 'When on, ignores keyframes and keeps showing the chosen cell (picking cells adds no keys). Turn on while adjusting per-cell placement and off when done',
    '켜져 있음': 'On',
    '켜짐': 'On',
    '켜짐/꺼짐은 키·표정 프리셋에 들어갑니다': 'On/off is stored in keys and expression presets',
    '크게 벌린 칸 (행, 열). -1 = 반 열림 칸 사용': 'Wide-open cell (row, col). -1 = use the half-open cell',
    '크기 (얼굴 대비)': 'Size (relative to face)',
    '크기·위치는 오브젝트를 직접 옮기거나 S로 조절해도 됩니다': 'You can also move the object or scale it with S to adjust size and position',
    '크기·회전 기준': 'Scale/rotate pivot',
    '크기는 같은 비율로, 위치·회전은 움직인 만큼': 'Size by the same ratio, position/rotation by the same amount',
    '크롭': 'Crop',
    '크롭 (그림 영역 기준으로 잘라내기)': 'Crop (relative to the drawing area)',
    '키 보간': 'Key interpolation',
    '키 삽입': 'Insert key',
    '키 삽입: ': 'Keyed: ',
    '키프레임 멈춤': 'Keyframes paused',
    '키프레임은 잠시 멈춰 있고, 키는 들어가지 않습니다': 'Keyframes are paused and no keys are inserted',
    "키프레임을 잠시 멈추고 고른 프리셋(표정)의 파츠를 그대로 고칩니다. 끝나면 '저장하고 끝내기' 또는 '취소'": "Pauses keyframes so you can edit the chosen preset's (expression's) parts directly. When done, 'Save and finish' or 'Cancel'",
    '키프레임을 잠시 멈추고 이 프리셋의 파츠를 고칩니다. 그동안 키는 들어가지 않습니다': "Pauses keyframes to edit this preset's parts. No keys are inserted meanwhile",
    "태그를 지웁니다. 이 태그였던 파츠는 '태그 없음'(얼굴 가운데 기준)이 됩니다": "Removes the tag. Parts that had it become 'No tag' (face-center based)",
    '투명 픽셀 %d개의 색을 채웠습니다': 'Filled the color of %d transparent pixels',
    '파일에서 스프라이트 시트 이미지를 불러와 바로 적용합니다 (대상 머티리얼의 기존 시트 이미지도 교체)': 'Loads a sprite sheet image from a file and applies it right away (also replaces the existing sheet image in the target material)',
    '파츠 가장자리에 얇은 흰 선이 보일 때. 투명한 곳에 숨어 있는 흰색을 그림 색으로 채웁니다 (그림·투명도는 그대로). 고친 이미지는 .blend 안에 저장됩니다': "For thin white lines around parts. Fills the white hidden in transparent pixels with the drawing's color (drawing and transparency unchanged). The fixed image is stored inside the .blend",
    '파츠 격자·입·표정 목록·시선 패드를 뷰포트에 만들거나 갱신하거나 정렬하거나 지웁니다': 'Creates, updates, arranges or removes the part grids, mouth, expression list and gaze pad in the viewport',
    '파츠 그룹(태그)을 만듭니다. 기준 마커와 새 파츠의 기본값(대칭·시선·입·크기)을 정합니다': 'Creates a part group (tag). Sets its anchor marker and defaults for new parts (symmetry, gaze, mouth, size)',
    '파츠 그룹. 그 태그의 기준 마커 위치에 놓입니다': "Part group. Placed at that tag's anchor marker",
    '파츠 그림 위에 한 색을 덮습니다 (모양·투명도는 그대로)': "Covers the part's drawing with one color (shape and transparency unchanged)",
    '파츠 보이기/숨기기. 키를 넣을 수 있고(Constant) 표정 프리셋에도 저장됩니다. 부모를 숨기면 자식도 숨겨집니다': 'Show/hide the part. Keyable (Constant) and stored in expression presets. Hiding a parent hides its children too',
    '파츠 복제': 'Duplicate part',
    '파츠 올리기': 'Add parts',
    '파츠 이름': 'Part name',
    '파츠 중심': 'Part center',
    '파츠 키를 넣을 때 쓸 보간 방법 (위치·크기·회전·불투명도·크롭). 칸(그림) 키는 항상 Constant': 'Interpolation used for part keys (position, size, rotation, opacity, crop). Cell (image) keys are always Constant',
    '파츠 폴더': 'Part folders',
    "파츠를 고른 뒤 '부모'를 이 폴더로 바꾸면 들어옵니다": "Select a part and set its 'Parent' to this folder to put it inside",
    '파츠를 놓을 기준점을 추가합니다. 눈·눈썹·입·감정표현을 고르거나 + 로 이름을 직접 정합니다': 'Adds an anchor for placing parts. Choose Eyes, Brows, Mouth or Emote, or name it yourself with +',
    '파츠를 묶는 폴더 (그림 없음). 같은 태그·같은 자리의 폴더끼리는 하나만 켜집니다': 'A folder that groups parts (no image). Only one folder with the same tag and spot is on at a time',
    '파츠의 칸·위치·크기·회전·불투명도·크롭이나 시선, 표정을 바꾸면 현재 프레임에 키를 바로 넣습니다': "Keys the current frame right away when you change a part's cell, position, size, rotation, opacity, crop, the gaze or the expression",
    '패드를 끝까지 밀어 범위를 확인합니다 (키는 넣지 않음)': 'Pushes the pad to the end to check the range (no keys)',
    '패드를 아래 끝까지 밀었을 때 눈동자가 움직이는 거리 (캔버스 높이 대비)': 'How far the pupils move with the pad pushed fully down (relative to canvas height)',
    '패드를 오른쪽 끝까지 밀었을 때 눈동자가 움직이는 거리 (캔버스 폭 대비. 0.03 = 3%)': 'How far the pupils move with the pad pushed fully right (relative to canvas width; 0.03 = 3%)',
    '패드를 왼쪽 끝까지 밀었을 때 눈동자가 움직이는 거리 (캔버스 폭 대비. 0.03 = 3%)': 'How far the pupils move with the pad pushed fully left (relative to canvas width; 0.03 = 3%)',
    '패드를 위 끝까지 밀었을 때 눈동자가 움직이는 거리 (캔버스 높이 대비)': 'How far the pupils move with the pad pushed fully up (relative to canvas height)',
    '패럴랙스 강도': 'Parallax strength',
    '편 캔버스를 원래 모양으로 되돌렸습니다': 'Restored the flattened canvas to its original shape',
    '편집 모드': 'Edit mode',
    '편집 모드 (키프레임 무시)': 'Edit mode (ignore keyframes)',
    '편집 모드 켜짐 (%d-%d 고정)': 'Edit mode on (%d-%d pinned)',
    "편집 모드에서 고른 얼굴 면을 복사해 살짝 띄운 '얼굴 캔버스'를 만듭니다. 정면 투영 UV, 얼굴과 같은 변형(아마추어·셰이프 키)을 따라가며, 눈·입 파츠를 이 메시 하나에 조립합니다": "Copies the face polygons selected in Edit Mode into a slightly lifted 'face canvas'. It has front-projected UVs, follows the face's deformation (armature, shape keys), and eye/mouth parts are assembled on this one mesh",
    '편집 시작': 'Start editing',
    '편집할 프리셋을 고르세요': 'Pick a preset to edit',
    '포토샵 Ctrl+T처럼 뷰포트에서 파츠를 옮기고(안쪽 드래그), 크기를 바꾸고(모서리·변), 돌립니다(위 동그라미·바깥). Enter 확정 · Esc 취소. Shift = 비율 유지/15° 단위, Alt = 기준점 기준 크기': "Like Photoshop's Ctrl+T: move parts in the viewport (drag inside), scale them (corners/edges) and rotate them (top circle/outside). Enter apply · Esc cancel. Shift = keep ratio / 15° steps, Alt = scale around the pivot",
    '폴더': 'Folder',
    '폴더 안 파츠': 'Parts in folder',
    '폴더 이름': 'Folder name',
    '표시': 'Show',
    '표정 저장 · 적용': 'Save & apply expressions',
    '표정 칸 피커에서 지금 고른 칸을 이 모음의 입으로 지정합니다': "Sets the cell currently picked in the expression-cell picker as this vowel's mouth",
    '표정 프리셋을 적용할 때 이 그룹 포함': 'Include this group when applying expression presets',
    '프리셋 저장: ': 'Preset saved: ',
    '프리셋 적용 + 키': 'Apply preset + key',
    '프리셋 편집': 'Edit preset',
    '프리셋 편집 중: ': 'Editing preset: ',
    '프리셋을 하나 이상 저장하면 만들 수 있습니다': 'Available once you save at least one preset',
    '한국어': 'Korean',
    '한중일 입력 창(작은 브라우저)을 띄워 이 칸에 글자를 씁니다. 넣으면 이 창의 칸에 바로 들어갑니다': 'Opens the CJK input window (a small browser) to type into this field. The text goes straight into the field',
    '함께 전환되는 폴더: ': 'Folders switched together: ',
    '함께 조절': 'Adjust together',
    '함께 켜져 있는 다른 버전의 Face Shape Key Rig를 끕니다. 두 개가 켜져 있으면 안내 글자·표시가 겹쳐 그려집니다': 'Disables another enabled version of Face Shape Key Rig. With two enabled, hints and overlays draw twice',
    '항상 카메라를 봄': 'Always face camera',
    '행·열을 바꾼 뒤 칸을 다시 잘라 파츠 번호를 매깁니다': 'After changing rows/columns, re-slices the cells and renumbers the parts',
    "현재 칸 번호에 Constant 키를 삽입합니다. 키는 데칼이 아니라 리그 오브젝트에 들어가므로, 타임라인에서 보려면 리그를 선택하거나 'Only Show Selected'를 끄세요": "Inserts a Constant key on the current cell number. Keys go on the rig object, not the decal, so select the rig or turn off 'Only Show Selected' to see them in the timeline",
    '현재 프레임에 Constant 키를 넣어 이 프레임부터 표정이 바뀌게 합니다': 'Inserts a Constant key on the current frame so the expression changes from this frame',
    '현재 프레임에 입 키를 넣습니다: 칸(그림)·시퀀스·말하기 (Constant) + 입 전체 배치 (고른 보간). 키는 리그 오브젝트에 들어갑니다': 'Keys the mouth on the current frame: cell (image), sequence, talk (Constant) + whole-mouth placement (chosen interpolation). Keys go on the rig object',
    '현재 프레임에 키를 넣습니다': 'Inserts keys on the current frame',
    '화면': 'View',
    '화면 돌릴 때': 'While orbiting',
    '🔑 = 그 표정으로 바꾸고 현재 프레임에 키 넣기': '🔑 = switch to that expression and key the current frame',
})

_JA.update({
    "   ('입' 태그의 '입 (시퀀스·립싱크)'가 켜져 있어야 함)": '   (「口」タグの「口（シーケンス・リップシンク）」がオンである必要があります)',
    ' (대칭)': ' (対称)',
    ' (상하 반전)': ' (上下反転)',
    ' (적용됨)': ' (適用済み)',
    ' (좌우 반전)': ' (左右反転)',
    ' 파츠 전체를 좌우 반전해서 사용': ' のパーツ全体を左右反転して使用',
    '%d개': '%d個',
    "'%s' 마커를 만들고 '%s' 태그와 연결": 'マーカー「%s」を作成してタグ「%s」に接続',
    "'%s' 마커를 만들고 '%s' 태그와 연결합니다 (태그가 없으면 같이 만듦)": 'マーカー「%s」を作成し、タグ「%s」に接続します（タグがなければ一緒に作成）',
    "'머리카락 위로' 복사본 메시를 와이어로 표시합니다 (머리카락 앞에 있는지 확인용)": '「髪の上に」コピーメッシュをワイヤーで表示します（髪より手前にあるか確認用）',
    "'머리카락 위로' 파츠 자리에서 지금 보는 쪽으로 광선을 쏴서 앞머리까지의 거리를 재고, 앞으로 당기는 거리를 그보다 조금 크게 맞춥니다": '「髪の上に」パーツの位置から視点方向にレイを飛ばして前髪までの距離を測り、手前に引く距離をそれより少し大きく設定します',
    "'머리카락 위로' 파츠가 뷰포트 시점을 따라갑니다. 화면을 돌리는 동안에는 가볍게 두었다가 멈추면 바로 맞춥니다 (렌더와는 무관)": '「髪の上に」パーツがビューポートの視点に追従します。回転中は軽く保ち、止まるとすぐ合わせます（レンダーには影響しません）',
    "'머리카락 위로' 파츠가 뷰포트 시점을 얼마나 자주 따라갈지 (렌더와는 무관)": '「髪の上に」パーツがビューポートの視点に追従する頻度（レンダーには影響しません）',
    "'머리카락 위로' 파츠가 없거나 시점을 찾지 못했습니다": '「髪の上に」パーツがないか、視点が見つかりません',
    "'머리카락 위로' 파츠를 보는 쪽으로 얼마나 앞당길지. 앞머리보다 앞에 올 만큼만 (너무 크면 옆모습에서 반대쪽 파츠가 머리를 뚫고 보일 수 있음)": '「髪の上に」パーツを視点側へどれだけ手前に出すか。前髪より手前に来る程度に（大きすぎると横顔で反対側のパーツが頭を突き抜けて見えることがあります）',
    "'원래 색'이 '바꿀 색'이 되도록 색조·채도·명도 값을 계산해 넣습니다. 비슷한 색의 명암도 같이 따라 바뀜": '「元の色」が「変更後の色」になるように色相・彩度・明度を計算して入れます。似た色の明暗も一緒に変わります',
    "'찍기'를 누르면 화면이 얼굴 정면(숫자패드 1과 같음)으로 바뀝니다. 얼굴을 클릭하세요": '「配置」を押すと顔の正面ビュー（テンキー1と同じ）に切り替わります。顔をクリックしてください',
    '(고급) 별도 데칼': '（上級）別デカール',
    '(고급) 별도 입 데칼에 시트 추가': '（上級）別の口デカールにシートを追加',
    '(고급) 선택한 메시를 그대로 캔버스로': '（上級）選択したメッシュをそのままキャンバスに',
    '(예전) 머리카락 위 불투명도': '（旧）髪の上の不透明度',
    '(자체 행)': '（自身の行）',
    '+ 로 마커를 만들고 이름을 붙이세요 (예: 눈, 입, 볼)': '＋でマーカーを作成して名前を付けてください（例：目、口、頬）',
    "+ 로 태그를 만들거나, 파츠를 추가할 때 '새 태그'로 바로 만드세요": '＋でタグを作成するか、パーツ追加時に「新規タグ」で直接作成してください',
    '+ 로 파츠와 태그를 고르면 그 태그의 기준 마커 위치에 놓입니다': '＋でパーツとタグを選ぶと、そのタグの基準マーカー位置に配置されます',
    '+ 새 태그': '+ 新規タグ',
    '0-1, 2-3, 4-5행... 두 행씩 묶어서, 위 칸 = 열림, 아래 칸 = 닫힘 시퀀스를 만듭니다. 두 칸 모두 그림이 있는 곳만 (투명 배경 이미지 기준)': '0-1、2-3、4-5行…と2行ずつまとめ、上のセル＝開き、下のセル＝閉じのシーケンスを作ります。両方のセルに絵がある所のみ（透明背景画像が前提）',
    "1. ②에서 '입' 마커를 입 위치에 찍기": '1. ②で「口」マーカーを口の位置に配置',
    '1. 얼굴 메시 선택 → Tab(편집 모드)': '1. 顔メッシュを選択 → Tab（編集モード）',
    '100% 가까이면 앞뒤가 겹쳐 깜빡일 수 있습니다': '100%近くでは前後が重なってちらつくことがあります',
    '2. ③에서 입 모양 시트 불러오기 (칸마다 입 모양 하나)': '2. ③で口の形のシートを読み込む（セルごとに口の形1つ）',
    '2. 눈썹 위~턱까지 얼굴 앞면을 면 선택': '2. 眉の上～あごまで顔の前面を面選択',
    "3. ④에서 + → 그 시트의 입 모양 → 태그 '입' → OK": '3. ④で＋ → そのシートの口の形 → タグ「口」 → OK',
    '3. 얼굴 캔버스 만들기': '3. 顔キャンバスを作成',
    '4. 여기에 입 시트가 생기면 시퀀스(닫힘·반·열림) → 립싱크 순서로 설정': '4. ここに口シートが現れたら、シーケンス（閉じ・半開き・開き）→ リップシンクの順に設定',
    'Blender에 연결할 수 없습니다': 'Blenderに接続できません',
    'Constant 정리: 키 %d개': 'Constant整理：キー%d個',
    'Face Rig 캔버스 파일이 아닙니다': 'Face Rigのキャンバスファイルではありません',
    'Language / 언어': 'Language / 言語',
    'N패널': 'Nパネル',
    'OK를 누르면 정면 뷰로 바뀌고 바로 얼굴을 클릭해 위치를 찍습니다': 'OKを押すと正面ビューに切り替わり、すぐに顔をクリックして位置を指定します',
    'Tab으로 편집 모드에 들어가 캔버스로 쓸 얼굴 앞면(눈썹 위~턱)을 면 선택한 뒤 다시 누르세요.': 'Tabで編集モードに入り、キャンバスにする顔の前面（眉の上～あご）を面選択してから、もう一度押してください。',
    'UV %d곳을 이어 붙이고 얼굴에 다시 붙였습니다': 'UVを%d箇所つなぎ、顔に貼り直しました',
    'UV Warp 모디파이어': 'UVワープモディファイアー',
    'UV Warp를 이 그룹에만 적용 (얼굴 메시 일부일 때)': 'UVワープをこのグループだけに適用（顔メッシュの一部の場合）',
    'UV 맞춤 완료 (루프 %d개)': 'UV合わせ完了（ループ%d個）',
    'UV 맵': 'UVマップ',
    'UV 여백': 'UV余白',
    'UV 투영을 알아내지 못했습니다': 'UV投影を特定できませんでした',
    '① 얼굴 캔버스': '① 顔キャンバス',
    '① 얼굴 캔버스 · ② 위치 마커 · ③ 스프라이트 시트': '① 顔キャンバス · ② 位置マーカー · ③ スプライトシート',
    '①에서 리그를 먼저 지정하세요': '先に①でリグを指定してください',
    '①에서 캔버스와 리그를 먼저 정하세요': '先に①でキャンバスとリグを決めてください',
    '② 위치 마커': '② 位置マーカー',
    '②에서 마커를 먼저 만들면 기준점으로 고를 수 있습니다': '先に②でマーカーを作ると基準点として選べます',
    '③ 스프라이트 시트': '③ スプライトシート',
    '④ 입 파츠에 이 시트 연결': '④の口パーツにこのシートを接続',
    '④ 캔버스 레이어 (파츠 배치)': '④ キャンバスレイヤー（パーツ配置）',
    "④·⑥에서 파츠를 고친 뒤 '저장하고 끝내기'": '④・⑥でパーツを修正してから「保存して終了」',
    '④에 입 파츠가 없습니다': '④に口パーツがありません',
    "④에서 + → 이 시트의 입 모양 → '입' 태그로 입 파츠를 만드세요": '④で＋ → このシートの口の形 → 「口」タグで口パーツを作ってください',
    '④에서 파츠를 배치한 뒤 표정으로 저장합니다': '④でパーツを配置してから表情として保存します',
    '④의 입 파츠가 이 시트를 그리도록 연결합니다 (시퀀스·미리보기·립싱크가 화면에 보이려면 필요)': '④の口パーツがこのシートを描くように接続します（シーケンス・プレビュー・リップシンクを表示するのに必要）',
    '⑤ 표정 프리셋': '⑤ 表情プリセット',
    '⑥ 입 (시퀀스·립싱크)': '⑥ 口（シーケンス・リップシンク）',
    '⑥ 입 시퀀스 · 립싱크': '⑥ 口シーケンス · リップシンク',
    '✓ 확정': '✓ 確定',
    '✕ 취소': '✕ キャンセル',
    '가리는 메시: %s, 최대 %.4g → 거리 %.4g': '遮るメッシュ：%s、最大 %.4g → 距離 %.4g',
    '가림 거리 재서 맞추기': '遮り距離を測って合わせる',
    '가볍게': '軽く',
    '가운데': '中央',
    '가장자리 잘라내기': '端を切り取る',
    '가장자리 흰 선 제거': '縁の白い線を除去',
    '각 칸의 테두리를 이만큼 투명하게 잘라냅니다. 칸 모서리의 번호 글씨나 가이드선이 보일 때 사용 (그림이 칸 가운데 있어야 함)': '各セルの縁をこの分だけ透明に切り取ります。セルの隅の番号やガイド線が見えるときに使用（絵がセルの中央にある必要があります）',
    '감정표현': '感情表現',
    '감정표현 Plane · 머리 본: %s': '感情表現プレーン · 頭ボーン：%s',
    '감정표현 Plane 만들기': '感情表現プレーンを作成',
    '감정표현 Plane: 켜면 면이 항상 활성 카메라 정면을 봅니다 (위치는 머리를 따라감). 끄면 머리 정면에 고정': '感情表現プレーン：オンにすると常にアクティブカメラの正面を向きます（位置は頭に追従）。オフで頭の正面に固定',
    '감정표현 Plane을 만들었습니다: ': '感情表現プレーンを作成しました：',
    '값 = 캔버스 크기 대비 거리 (0.03 = 3%)': '値＝キャンバスサイズに対する距離（0.03＝3%）',
    '값을 바꾸면 그 단계가 미리보기됩니다': '値を変えるとその段階がプレビューされます',
    '같은 태그로 같은 자리에 폴더를 하나 더 만들면 둘 중 하나만 켜집니다': '同じタグで同じ場所にフォルダーをもう一つ作ると、どちらか一方だけがオンになります',
    '격자 (행=표정, 열=입)': 'グリッド（行＝表情、列＝口）',
    '격자 이미지 칸 전환 (텍스처 표정·립싱크)': 'グリッド画像のセル切り替え（テクスチャ表情・リップシンク）',
    '격자로 그린 스프라이트 시트 이미지': 'グリッドで描いたスプライトシート画像',
    '격자로 그린 스프라이트 시트 이미지를 불러와 행·열로 자르고 파츠 번호를 매깁니다': 'グリッドで描いたスプライトシート画像を読み込み、行・列で切ってパーツ番号を付けます',
    '격자로 그린 시트 이미지를 고르고 행·열 수를 넣으세요 (파일 창 오른쪽)': 'グリッドで描いたシート画像を選び、行・列数を入力してください（ファイル画面の右側）',
    '겹치기': '重なり',
    '고른 눈의 시선 패드와 칸 값을 그대로 씁니다 (같은 이름의 파츠끼리). 오른쪽 눈을 왼쪽 눈에 연결할 때': '選んだ目の視線パッドとセル値をそのまま使います（同じ名前のパーツ同士）。右目を左目に接続するとき',
    '고른 칸이 키프레임과 상관없이 계속 보입니다. 끝나면 꼭 끄세요': '選んだセルがキーフレームに関係なく表示され続けます。終わったら必ずオフにしてください',
    '곱하기': '乗算',
    '공통값 (움직이면 이 칸만 저장)': '共通値（動かすとこのセルだけに保存）',
    '괄호 = 그 태그가 지금 쓰는 마커': '括弧＝そのタグが今使っているマーカー',
    '그 메시 선택 → Tab (편집 모드)': 'そのメッシュを選択 → Tab（編集モード）',
    '그 색으로 칠함 (명암 없어짐)': 'その色で塗ります（明暗はなくなります）',
    '그래도 일괄 조절할까요? 크기는 같은 비율로, 위치는 움직인 만큼 바뀝니다.': 'それでも一括調整しますか？サイズは同じ比率で、位置は動かした分だけ変わります。',
    '그룹 선택 무시하고 전부 적용': 'グループ選択を無視してすべてに適用',
    '그룹만 적용': 'グループのみ適用',
    '그림': '絵',
    '그림 가로 크기 (종횡비 고정을 끈 경우)': '絵の横サイズ（縦横比固定がオフの場合）',
    '그림 세로 크기 (종횡비 고정을 끈 경우)': '絵の縦サイズ（縦横比固定がオフの場合）',
    '그림 크기': '絵のサイズ',
    '그림에서 찾기': '絵から取得',
    '그림을 데칼 위에서 위아래로 이동 (칸 높이 대비 %)': '絵をデカール上で上下に移動（セルの高さに対する%）',
    '그림을 데칼 위에서 좌우로 이동 (칸 너비 대비 %)': '絵をデカール上で左右に移動（セルの幅に対する%）',
    '그림이 있는 칸만 번호가 매겨져 파츠가 됩니다': '絵があるセルだけに番号が付いてパーツになります',
    '글자 칸 위에서 실행하세요': '文字入力欄の上で実行してください',
    '기본': '基本',
    '기본 위치 Y': '基本位置Y',
    '기본 크기': '基本サイズ',
    '기존 메시를 캔버스로': '既存メッシュをキャンバスに',
    '기준 마커': '基準マーカー',
    '기준 칸': '基準セル',
    '기준: ': '基準：',
    '기준점 ⊕ 드래그 = 기준점 옮기기   ·   Ctrl+Z 한 단계 되돌리기   ·   Enter 확정   ·   Esc 취소   ·   원근 뷰가 되면 확정': '基準点⊕ドラッグ＝基準点を移動   ·   Ctrl+Z 一段階戻す   ·   Enter 確定   ·   Esc キャンセル   ·   透視ビューになると確定',
    '기준점 만들기 · 찍기': '基準点の作成・配置',
    '기초 태그 %d개 추가': '基本タグを%d個追加',
    '기초 태그 넣기': '基本タグを追加',
    '깊이 (패럴랙스)': '深度（視差）',
    '깊이 있는 파츠 %d개': '深度のあるパーツ%d個',
    '끄기': 'オフ',
    '내보내기': 'エクスポート',
    '내보내기 실패: ': 'エクスポート失敗：',
    '내보낸 .zip을 지금 고른 캔버스에 덮어씁니다. 이 캔버스의 기존 파츠·프리셋·입 시트·컨트롤러는 지워집니다 (Ctrl+Z로 되돌릴 수 있음)': 'エクスポートした.zipを今選んでいるキャンバスに上書きします。このキャンバスの既存のパーツ・プリセット・口シート・コントローラーは削除されます（Ctrl+Zで戻せます）',
    '내보냈습니다 (시트 %d장): ': 'エクスポートしました（シート%d枚）：',
    '넣었습니다. 창을 닫아도 됩니다': '入力しました。ウィンドウを閉じても大丈夫です',
    '누를 메시를 선택하세요': '押しつぶすメッシュを選択してください',
    '눈 데칼의 UV를 0~1 정사각형 안에 꽉 차게 맞춥니다 (가로세로 비율 유지, 가운데 정렬). 파츠 위치/크기의 기준이 데칼 전체가 됩니다': '目のデカールのUVを0～1の正方形いっぱいに合わせます（縦横比維持・中央揃え）。パーツの位置・サイズの基準がデカール全体になります',
    '눈 머티리얼·시선 패드를 지우고 원래 머티리얼로 되돌립니다 (키는 유지)': '目のマテリアルと視線パッドを削除し、元のマテリアルに戻します（キーは維持）',
    '눈 삭제': '目を削除',
    '눈·눈썹·입·감정표현 태그와 눈·입 마커를 없는 것만 추가합니다': '目・眉・口・感情表現のタグと目・口マーカーのうち、ないものだけ追加します',
    '눈썹 위~턱까지 얼굴 앞면을 면 선택': '眉の上～あごまで顔の前面を面選択',
    '다른 눈 따라가기': '他の目に追従',
    '다른 레이어와 같은 칸 번호를 씁니다 (예: 속눈썹이 흰자의 깜빡임 단계를 따라감). 두 시트의 칸 배치가 같아야 합니다': '他のレイヤーと同じセル番号を使います（例：まつ毛が白目のまばたき段階に追従）。両シートのセル配置が同じである必要があります',
    '다른 버전의 이 애드온이 함께 켜져 있습니다': 'このアドオンの別バージョンも有効になっています',
    '다른 사본 끄기': '他のコピーを無効化',
    '다른 사본을 껐습니다: ': '他のコピーを無効にしました：',
    '다른 스프라이트 시트의 행(표정)을 그대로 따라갑니다. 얼굴 표정과 범고래 표정을 한 번에 바꿀 때 사용': '他のスプライトシートの行（表情）にそのまま追従します。顔の表情と帽子などの表情を一度に変えるときに使用',
    '다른 칸 그림': '他のセルの絵',
    '다른 칸 그림 연결 모두 비우기': '他セル絵の接続をすべてクリア',
    '다른 칸 그림 연결 모두 비우기 (%d칸)': '他セル絵の接続をすべてクリア（%dセル）',
    '다른 캔버스를 따라가는 캔버스는 지원하지 않습니다': '他のキャンバスに追従するキャンバスには対応していません',
    '다른 파일로': '別ファイルに',
    '다른 파일로 바꾸기': '別ファイルに置き換え',
    '다시 만들기': '作り直す',
    '다시 불러오기': '再読み込み',
    '다시 불러왔습니다: ': '再読み込みしました：',
    '다시 자르기': '切り直す',
    '다시 찍기': '再配置',
    '다음 키까지 값 그대로 (뚝 바뀜)': '次のキーまで値をそのまま保持（パッと切り替わる）',
    '단계': '段階',
    '단계 크기/위치': '段階サイズ/位置',
    '단일 입': '単一の口',
    '닫힘/반/열림 단계마다 칸의 크기와 위치를 따로 보정': '閉じ／半開き／開きの段階ごとにセルのサイズと位置を個別に補正',
    '닷지': '覆い焼きカラー',
    '대사 길이에 맞춰 씬 끝 프레임을 %d로 늘렸습니다': 'セリフの長さに合わせてシーンの終了フレームを%dに延ばしました',
    '대상 머티리얼에서 바꿀 시트 이미지를 찾지 못했습니다. 이미지 텍스처 노드에 직접 연결해 주세요': '対象マテリアルで置き換えるシート画像が見つかりませんでした。画像テクスチャノードに直接接続してください',
    '대상 본': '対象ボーン',
    '대상 오브젝트': '対象オブジェクト',
    '대상의 UV(버텍스 그룹이 있으면 그 부분만)를 좌상단 첫 칸 크기로 맞춥니다': '対象のUV（頂点グループがあればその部分だけ）を左上の最初のセルのサイズに合わせます',
    '대상이 메시가 아닙니다': '対象がメッシュではありません',
    '대칭': '対称',
    '대칭 복사': '対称コピー',
    '대칭 태그가 쓰는 마커는 한쪽만 찍으면 반대쪽이 따라갑니다': '対称タグが使うマーカーは、片側だけ配置すれば反対側が追従します',
    '더하기 (선형 닷지)': '加算（覆い焼きリニア）',
    '덮기': '塗りつぶし',
    '덮어쓰기': '上書き',
    '데칼 UV를 0~1로 펴기': 'デカールUVを0～1に広げる',
    '데칼 UV를 0~1로 폈습니다': 'デカールUVを0～1に広げました',
    '데칼 가운데를 기준으로 반대쪽에 거울처럼 하나 더 그립니다 (땀방울, 빗금 등)': 'デカールの中央を基準に反対側へ鏡のようにもう一つ描きます（汗、斜線など）',
    '데칼 머티리얼을 이미지 알파로 투명하게 만듭니다 (Transparent + Mix Shader 삽입, Blended 렌더, 그림자 끄기). 얼굴 본체 머티리얼에는 쓰지 마세요': 'デカールのマテリアルを画像アルファで透明にします（Transparent＋Mix Shaderを挿入、Blendedレンダー、影オフ）。顔本体のマテリアルには使わないでください',
    '데칼 오브젝트용. 머티리얼을 건드리지 않음': 'デカールオブジェクト用。マテリアルは変更しません',
    '데칼 위에서 그림이 보이는 크기. 줄여도 옆 칸이 침범하지 않습니다 (칸 밖은 투명 처리). 투명 배경 설정이 되어 있어야 잘림이 적용됩니다': 'デカール上で絵が見えるサイズ。小さくしても隣のセルははみ出しません（セル外は透明）。切り抜きには透明背景の設定が必要です',
    '도프시트·그래프 에디터에서 선택해 둔 키프레임만 (이 입)': 'ドープシート・グラフエディターで選択したキーフレームのみ（この口）',
    '도프시트·그래프 에디터에서 선택해 둔 키프레임만 (이 파츠)': 'ドープシート・グラフエディターで選択したキーフレームのみ（このパーツ）',
    '돌리는 동안은 그대로, 멈추면 맞춤 (가장 가벼움)': '回転中はそのまま、止まると合わせる（最も軽い）',
    '드라이버 방식처럼 모음마다 지정한 입 칸으로 바뀝니다': 'ドライバー方式のように母音ごとに指定した口のセルに切り替わります',
    '드라이버·모디파이어·노드와 리그 값을 모두 제거합니다 (키프레임은 유지)': 'ドライバー・モディファイアー・ノードとリグの値をすべて削除します（キーフレームは維持）',
    '디스크의 시트 이미지 파일을 다시 읽습니다 (다른 프로그램에서 고친 뒤 사용)': 'ディスク上のシート画像ファイルを読み直します（他のソフトで修正した後に使用）',
    '따라가는 눈의 시선 좌우를 뒤집습니다 (데칼 UV가 좌우 반전되어 있을 때)': '追従する目の視線の左右を反転します（デカールUVが左右反転しているとき）',
    '따라가는 눈의 파츠를 전부 좌우 반전해서 사용': '追従する目のパーツをすべて左右反転して使用',
    '따라갈 때 좌우 반전': '追従時に左右反転',
    '띄우기': '浮かせる',
    '렌더 카메라 기준: 다른 각도로 보면 납작해 보임': 'レンダーカメラ基準：他の角度から見ると平たく見えます',
    '리그 바인드(ARP 등)할 때 캔버스는 빼고 얼굴 메시만 바인드하세요': 'リグをバインド（ARPなど）するときはキャンバスを除き、顔メッシュだけをバインドしてください',
    '리그가 설정되지 않았습니다': 'リグが設定されていません',
    '리그를 먼저 지정하세요': '先にリグを指定してください',
    '립싱크 방식': 'リップシンク方式',
    '립싱크가 열만 바꿉니다. 표정마다 닫힘/반/열림을 가로로 배치': 'リップシンクは列だけを変えます。表情ごとに閉じ／半開き／開きを横に並べます',
    '마커': 'マーカー',
    '마커 기준': 'マーカー基準',
    '마커 삭제': 'マーカーを削除',
    '마커 없이 캔버스 가운데 기준': 'マーカーなし、キャンバス中央基準',
    '마커 찍기': 'マーカーを配置',
    '마커 추가': 'マーカーを追加',
    '마커 추가 창에서: 이 태그의 기준을 새 마커로': 'マーカー追加ウィンドウから：このタグの基準を新しいマーカーに',
    '마커 표시': 'マーカーを表示',
    '마커를 옮기면 그 마커에 붙은 파츠가 전부 따라갑니다': 'マーカーを動かすと、そのマーカーに付いたパーツがすべて追従します',
    '마커를 지웁니다. 이 마커를 쓰던 태그는 얼굴 가운데 기준이 됩니다': 'マーカーを削除します。このマーカーを使っていたタグは顔の中央基準になります',
    '마커를 찍었습니다: ': 'マーカーを配置しました：',
    '만든 뒤 한중일 입력 창을 띄워 이름을 씁니다 (Blender에서 한글 입력이 안 될 때)': '作成後に日中韓入力ウィンドウを開いて名前を入力します（Blenderで日本語入力ができないとき）',
    '만들 칸 (행, 열)': '作成するセル（行、列）',
    '만들기': '作成',
    '만들기/갱신': '作成／更新',
    '말하기': '話す',
    '말하기 미리보기': '話すプレビュー',
    '말하는 중': '話し中',
    '말하는 중 소리가 작을 때 (행, 열). -1 = 표정 칸 그대로': '話し中で音が小さいとき（行、列）。-1＝表情のセルのまま',
    '말할 때 쓸 입:': '話すときの口：',
    '말할 때 입': '話すときの口',
    '말할 때 입은 ⑥ 시퀀스·립싱크로 바뀝니다': '話すときの口は⑥シーケンス・リップシンクで切り替わります',
    '말할 때도 이 입 그대로 (뻐끔 안 함)': '話すときもこの口のまま（パクパクしない）',
    "말할 때도 이 입을 그대로 둡니다 (뻐끔거리지 않음). '나머지 표정 전부'의 입으로 바뀌지 않게 할 때 사용": '話すときもこの口のままにします（パクパクしない）。「残りの表情すべて」の口に切り替わらないようにするときに使用',
    '맞출 UV가 없습니다': '合わせるUVがありません',
    '매 프레임 따라감. 가장 부드럽지만 화면을 돌릴 때마다 씬 전체가 다시 계산되어 무거움': '毎フレーム追従。最も滑らかですが、画面を回すたびにシーン全体が再計算されて重くなります',
    '머리 납작하게 (카메라 기준)': '頭を平たく（カメラ基準）',
    '머리 납작하게 지우기': '頭を平たくを削除',
    '머리 납작하게: %d개 메시': '頭を平たく：メッシュ%d個',
    '머리 본을 고르세요': '頭のボーンを選んでください',
    '머리를 카메라 시선 방향으로 눌러 2D 그림처럼 보이게 합니다 (캔버스 파츠도 같이)': '頭をカメラの視線方向に押しつぶして2Dの絵のように見せます（キャンバスのパーツも一緒に）',
    '머리카락 위 불투명도': '髪の上の不透明度',
    '머리카락 위로': '髪の上に',
    '머리카락 위로 보이는 부분의 진하기 (1 = 완전히 위, 0.5 = 머리카락이 비쳐 보임)': '髪の上に見える部分の濃さ（1＝完全に上、0.5＝髪が透けて見える）',
    '머리카락 위로 보이는 부분의 진하기 (1 = 완전히 위, 0.5 = 머리카락이 비쳐 보임). 가려지지 않은 부분은 그대로': '髪の上に見える部分の濃さ（1＝完全に上、0.5＝髪が透けて見える）。隠れていない部分はそのまま',
    '머티리얼 Mapping 노드': 'マテリアルのマッピングノード',
    '머티리얼에서 이미지 텍스처를 찾지 못했습니다': 'マテリアルに画像テクスチャが見つかりませんでした',
    '먼저 ①에서 얼굴 캔버스를 만드세요': '先に①で顔キャンバスを作ってください',
    '먼저 ③에서 스프라이트 시트를 추가하세요': '先に③でスプライトシートを追加してください',
    '메시 수정 후 정리': 'メッシュ修正後に整理',
    '메인': 'メイン',
    '메인으로 사용': 'メインとして使用',
    '면을 더하거나(Shift+클릭) 빼고 적용': '面を追加（Shift＋クリック）または除外してから適用',
    '명도': '明度',
    '명암은 두고 색상·채도만 바꿈': '明暗はそのままで色相・彩度だけ変更',
    '몇 초 동안 애드온이 쓰는 시간을 함수별로 잽니다. 누른 뒤 렉이 나는 동작(화면 돌리기·재생·컨트롤러 끌기 등)을 평소처럼 하세요. 결과는 블렌드 파일 옆 fskr_perf.txt와 텍스트 편집기의 FSKR_perf.txt에 저장됩니다': '数秒間、アドオンが使う時間を関数ごとに計測します。押した後、重くなる操作（画面の回転・再生・コントローラーのドラッグなど）をいつも通りしてください。結果は.blendファイルの横のfskr_perf.txtとテキストエディターのFSKR_perf.txtに保存されます',
    '모두 보이기': 'すべて表示',
    "모든 '머리카락 위로' 파츠 공통": 'すべての「髪の上に」パーツ共通',
    '모든 레이어의 깊이(패럴랙스)에 곱하는 값. 0이면 끔': '全レイヤーの深度（視差）に掛ける値。0でオフ',
    '모든 메시에서 납작하게 모디파이어를 지웁니다': 'すべてのメッシュから平たくするモディファイアーを削除します',
    '모든 입 칸에 공통으로 적용되는 배치 값 펼치기': 'すべての口セル共通の配置値を展開',
    '모든 파츠 보이기': 'すべてのパーツを表示',
    '모든 파츠를 보이게 합니다': 'すべてのパーツを表示します',
    '모음 (A/I/U/E/O)': '母音（A/I/U/E/O）',
    '모음별로 다른 칸': '母音ごとに別のセル',
    '모자 얼굴처럼 표정·시선을 따로 움직일 얼굴이 하나 더 있을 때': '帽子の顔のように、表情・視線を別に動かす顔がもう一つあるとき',
    '목록 위에 있을수록 앞에 그려집니다 (▲▼로 순서)': 'リストの上にあるほど手前に描かれます（▲▼で順序）',
    '목록에 모든 파츠를 보여 줍니다 (보이기는 그대로)': 'リストにすべてのパーツを表示します（表示状態はそのまま）',
    '목록에 이 그룹 파츠만 표시': 'リストにこのグループのパーツだけ表示',
    '목록에서 누르면 바로 그 표정으로 바뀝니다 (키 없음)': 'リストで押すとすぐにその表情に切り替わります（キーなし）',
    '미리보기 중 (프레임을 옮기면 꺼짐)': 'プレビュー中（フレームを移動するとオフ）',
    '바꾸면 자동 키': '変更時に自動キー',
    '바꿀 색': '変更後の色',
    '바인드에 실패했습니다 (얼굴 메시 모양을 확인하세요)': 'バインドに失敗しました（顔メッシュの形を確認してください）',
    '반': '半開き',
    '반 열림 기준': '半開きの基準',
    '반전 그림을 둘 칸. 보통 이미지에서 비어 있는 칸': '反転した絵を置くセル。通常は画像内の空きセル',
    '반전 칸 만들기': '反転セルを作成',
    '반전 칸 만들기: %d-%d → %d-%d': '反転セルを作成：%d-%d → %d-%d',
    '밝게': '比較（明）',
    '방식': '方式',
    '배치': '配置',
    '배치 (마커 기준)': '配置（マーカー基準）',
    '배치 모드 끄기': '配置モードを終了',
    '배치 모드 끔': '配置モードを終了しました',
    '배치 모드를 끕니다 (ESC 또는 우클릭)': '配置モードを終了します（ESCまたは右クリック）',
    '배치 모드에서 G로 옮기고 Ctrl로 다른 틀에 붙입니다. 시트 격자는 크기 고정': '配置モードではGで移動、Ctrlで他の枠に吸着します。シートのグリッドはサイズ固定',
    '배치 초기화': '配置をリセット',
    '배치 켜기 (머티리얼 다시 만들기)': '配置を有効化（マテリアルを作り直す）',
    "배치를 마치면 '프리셋 저장'으로 표정을 만드세요": '配置が終わったら「プリセット保存」で表情を作ってください',
    '버텍스 그룹': '頂点グループ',
    '번': '焼き込みカラー',
    '벌림 3단계': '開き3段階',
    '범위': '範囲',
    '보간': '補間',
    '보간 적용': '補間を適用',
    '보간은 태그마다 따로 저장됩니다 (같은 태그 파츠끼리 공유)': '補間はタグごとに保存されます（同じタグのパーツ同士で共有）',
    '보이기': '表示',
    '보통': '普通',
    '복제: ': '複製：',
    '부드럽게': '滑らか',
    '부드럽게 가속·감속 (Bezier)': '滑らかに加速・減速（ベジェ）',
    '부모': '親',
    '부모 따라감': '親に追従',
    '부모 파츠를 고르면 부모의 위치·회전·크기·불투명도·색(HSV·색 덮기)·시선을 그대로 따라갑니다 (자식은 부모 바로 위에 그려짐). 지정할 때 그림은 제자리 유지': '親パーツを選ぶと、親の位置・回転・サイズ・不透明度・色（HSV・カラーオーバーレイ）・視線にそのまま追従します（子は親のすぐ上に描かれます）。指定時に絵はその場に保持',
    '부모(%s)의 위치·시선을 따라갑니다': '親（%s）の位置・視線に追従します',
    '부모만 켜면 자식(홍채·하이라이트)은 같이 움직입니다': '親だけオンにすれば子（虹彩・ハイライト）も一緒に動きます',
    '부모에게서 물려받음: ': '親から継承：',
    '분노 마크처럼 얼굴 밖으로 나가는 연출용 평면 (머리 본을 따라감)': '怒りマークのように顔の外へはみ出す演出用の平面（頭のボーンに追従）',
    '불러오기 (덮어쓰기)': 'インポート（上書き）',
    '불러오기 실패: ': 'インポート失敗：',
    '불러왔습니다 (시트 %d장). 뷰포트 컨트롤러는 컨트롤러 탭에서 다시 만드세요': 'インポートしました（シート%d枚）。ビューポートコントローラーはコントローラータブで作り直してください',
    '불투명도': '不透明度',
    '뷰포트 가볍게': 'ビューポートを軽く',
    '뷰포트 리그에 표시': 'ビューポートのリグに表示',
    '뷰포트 컨트롤러 (시선 패드)': 'ビューポートコントローラー（視線パッド）',
    '뷰포트 컨트롤러 (표정 목록)': 'ビューポートコントローラー（表情リスト）',
    '뷰포트 컨트롤러: ': 'ビューポートコントローラー：',
    '뷰포트 컨트롤러의 격자 아래에 이 시퀀스 전용 슬라이더를 추가합니다 (닫힘/반/열림, 단일 입이면 끔/켬). 메인 시퀀스는 항상 표시됩니다': 'ビューポートコントローラーのグリッドの下にこのシーケンス専用のスライダーを追加します（閉じ／半開き／開き、単一の口ならオフ／オン）。メインシーケンスは常に表示されます',
    '뷰포트에 네모 패드와 가운데 십자 손잡이를 만듭니다': 'ビューポートに四角いパッドと中央の十字ハンドルを作成します',
    '뷰포트에 시선 패드(눈동자 컨트롤러)를 만들거나 다시 만들거나 지웁니다': 'ビューポートに視線パッド（瞳コントローラー）を作成・再作成・削除します',
    '뷰포트에 위치 마커를 표시합니다': 'ビューポートに位置マーカーを表示します',
    '뷰포트에 이 파츠의 시트 격자를 띄웁니다. 노란 테두리를 끌면 칸이 바뀝니다 (칸이 2개 이상인 파츠만)': 'ビューポートにこのパーツのシートグリッドを表示します。黄色い枠をドラッグするとセルが変わります（セルが2つ以上のパーツのみ）',
    '뷰포트에 표정 목록 컨트롤러를 만들거나 다시 만들거나 지웁니다. 손잡이를 끌어 표정을 고릅니다': 'ビューポートに表情リストコントローラーを作成・再作成・削除します。ハンドルをドラッグして表情を選びます',
    '뷰포트에서 얼굴 캔버스 위를 클릭해 이 마커의 위치를 정합니다 (정면 뷰 권장)': 'ビューポートで顔キャンバスをクリックしてこのマーカーの位置を決めます（正面ビュー推奨）',
    '뷰포트에서 자유 변형': 'ビューポートで自由変形',
    '뷰포트에서 자유 변형 (Ctrl+T)': 'ビューポートで自由変形（Ctrl+T）',
    '뷰포트의 Show Overlays를 꺼도 컨트롤러(표정 목록/시선 패드 등)를 보이게 합니다. 화면 표시용이며 렌더에는 나오지 않습니다': 'ビューポートのオーバーレイをオフにしてもコントローラー（表情リスト・視線パッドなど）を表示します。画面表示用でレンダーには出ません',
    '블렌드 파일 기준 상대 경로로 저장 (폴더째 옮겨도 유지)': 'blendファイル基準の相対パスで保存（フォルダーごと移動しても維持）',
    '비우면 자동 (태그 이름 + 번호)': '空欄なら自動（タグ名＋番号）',
    '비우면 활성 UV 맵': '空欄ならアクティブなUVマップ',
    "비워 두면 '태그 이름 + 번호'로 자동으로 붙습니다": '空欄のままなら「タグ名＋番号」で自動的に付きます',
    '빼기': '減算',
    '상대 경로': '相対パス',
    '상하': '上下',
    '새 캔버스 만들기': '新規キャンバスを作成',
    '새 태그 이름': '新規タグ名',
    '새 파츠 기본값': '新規パーツの初期値',
    '새 파츠 레이어를 맨 앞에 추가합니다': '新しいパーツレイヤーを最前面に追加します',
    '새 파츠 크기 (1 = 캔버스 전체)': '新規パーツのサイズ（1＝キャンバス全体）',
    '새 파츠를 마커보다 위(+)/아래(-)에 놓기': '新規パーツをマーカーより上（+）／下（-）に置く',
    '새 파츠를 이 태그의 가장 아래 파츠 모양으로 클리핑하고 그 바로 위에 놓습니다 (예: 눈동자 → 흰자 태그)': '新規パーツをこのタグの一番下のパーツの形でクリッピングし、そのすぐ上に置きます（例：瞳 → 白目タグ）',
    "새 파츠의 '대칭 복사'를 켠 채로 추가": '新規パーツを「対称コピー」オンで追加',
    "새 파츠의 '시선 따라 이동'을 켠 채로 추가": '新規パーツを「視線に追従して移動」オンで追加',
    '새 폴더': '新規フォルダー',
    '새 폴더 (지금 보이는 파츠로)': '新規フォルダー（今見えているパーツで）',
    '새 표정': '新しい表情',
    '색': '色',
    '색 덮기': 'カラーオーバーレイ',
    '색 맞추기': '色合わせ',
    '색 칸을 누르면 Hex(784343 등)로 입력할 수 있습니다': '色の欄を押すとHex（784343など）で入力できます',
    '색상만': 'カラーのみ',
    '색조': '色相',
    '색조 %+.0f°, 채도 ×%.2f, 명도 ×%.2f': '色相 %+.0f°、彩度 ×%.2f、明度 ×%.2f',
    '색조 이동 (-0.5~0.5 = -180°~180°)': '色相シフト（-0.5～0.5＝-180°～180°）',
    '색조/채도/명도': '色相／彩度／明度',
    '색조/채도/명도 계산': '色相／彩度／明度を計算',
    '색조/채도/명도 초기화': '色相／彩度／明度をリセット',
    '선택 범위에 지정': '選択範囲に指定',
    '선택 영역 수정': '選択範囲を修正',
    '선택 영역 수정 중': '選択範囲を修正中',
    '선택 영역 적용': '選択範囲を適用',
    '선택 영역을 복사하지 못했습니다': '選択範囲をコピーできませんでした',
    '선택된 면이 없습니다': '選択された面がありません',
    '선택된 면이 없습니다.': '選択された面がありません。',
    '선택된 면이 없습니다. 얼굴 앞면을 면 선택하세요': '選択された面がありません。顔の前面を面選択してください',
    '선택한 눈 데칼 메시에 파츠 레이어 합성 머티리얼을 만듭니다': '選択した目デカールメッシュにパーツレイヤー合成マテリアルを作成します',
    '선택한 메시 추가': '選択したメッシュを追加',
    '선택한 메시(얼굴·머리카락·모자 등)를 카메라 시선 방향으로 눌러 2D 그림처럼 보이게 합니다. 캔버스 파츠도 같이 눌립니다. 렌더 카메라 기준 연출': '選択したメッシュ（顔・髪・帽子など）をカメラの視線方向に押しつぶして2Dの絵のように見せます。キャンバスのパーツも一緒に押しつぶされます。レンダーカメラ基準の演出',
    '선택한 오브젝트(입/눈 데칼 등)에 격자 이미지 칸 전환을 추가합니다': '選択したオブジェクト（口／目のデカールなど）にグリッド画像のセル切り替えを追加します',
    '선택한 키프레임만': '選択したキーフレームのみ',
    '선택한 키프레임이 없습니다 (도프시트·그래프 에디터에서 키를 선택하세요)': '選択したキーフレームがありません（ドープシート・グラフエディターでキーを選択してください）',
    "선택한 파츠 자리에 폴더를 만들고 그 파츠를 넣습니다. 같은 태그·같은 자리의 폴더끼리는 하나만 켜져서, 예를 들어 '일반 눈'과 '폭소 눈' 폴더를 눈 하나로 전환할 수 있습니다": '選択したパーツの位置にフォルダーを作り、そのパーツを入れます。同じタグ・同じ位置のフォルダーは一つだけオンになるので、例えば「通常の目」と「爆笑の目」フォルダーを一つの目として切り替えられます',
    '선택한 파츠: ': '選択したパーツ：',
    '선택한 파츠를 그림·값·키프레임까지 똑같이 복제해 바로 위에 놓습니다 (이름 뒤에 .001)': '選択したパーツを絵・値・キーフレームまで同じに複製し、すぐ上に置きます（名前の後ろに.001）',
    '선형 라이트': 'リニアライト',
    '성능 측정': 'パフォーマンス計測',
    '성능 측정 (8초)': 'パフォーマンス計測（8秒）',
    '세기': '強さ',
    '세기는 리그 프로퍼티라 키를 넣을 수 있습니다 (I)': '強さはリグのプロパティなのでキーを打てます（I）',
    '셰이프 키 슬라이더/패드 컨트롤러 (기존 Face Rig)': 'シェイプキーのスライダー／パッドコントローラー（従来のFace Rig）',
    '소프트 라이트': 'ソフトライト',
    "손잡이를 끌면 '시선'을 켠 파츠가 따라 움직입니다": 'ハンドルをドラッグすると「視線」をオンにしたパーツが追従します',
    '순서 바꾸기': '順序を変更',
    '숫자패드 1처럼 얼굴 정면 뷰로 바꾸고 캔버스를 화면 가운데로 (얼굴 방향 설정 반영)': 'テンキー1のように顔の正面ビューに切り替え、キャンバスを画面中央に（顔の向き設定を反映）',
    '쉼표로 구분 (예: 기본, 화남, 반짝, 당황)': 'カンマ区切り（例：基本, 怒り, キラキラ, 焦り）',
    '쉼표로 구분 (예: 닫힘, 반, 열림)': 'カンマ区切り（例：閉じ, 半開き, 開き）',
    '스크린': 'スクリーン',
    '스프라이트 립싱크: %d개 굽기': 'スプライトリップシンク：%d個ベイク',
    '스프라이트 방식 작업 단계': 'スプライト方式の作業段階',
    '스프라이트 시트 적용: ': 'スプライトシートを適用：',
    '스프라이트 시트 키를 모두 Constant 보간으로 바꿉니다 (칸 사이가 섞이는 문제 방지)': 'スプライトシートのキーをすべてConstant補間にします（セル間が混ざるのを防止）',
    '시선 (눈동자 이동)': '視線（瞳の移動）',
    '시선 미리보기': '視線プレビュー',
    '시선 이동량 배율 (하이라이트를 덜/더 움직일 때)': '視線の移動量の倍率（ハイライトを少なめ／多めに動かすとき）',
    '시선 초기화': '視線をリセット',
    '시선 추가 이동': '視線の追加移動',
    '시선 컨트롤러': '視線コントローラー',
    '시선 컨트롤러 만들기': '視線コントローラーを作成',
    '시선 패드를 움직이면 이 레이어가 따라 움직입니다 (눈동자, 하이라이트)': '視線パッドを動かすとこのレイヤーが追従します（瞳、ハイライト）',
    '시선을 따라가는 파츠': '視線に追従するパーツ',
    '시점 따라가기': '視点に追従',
    '시퀀스 %d개 생성': 'シーケンスを%d個作成',
    '시퀀스 %d개를 옮겼습니다': 'シーケンスを%d個移動しました',
    '시퀀스 미리보기': 'シーケンスのプレビュー',
    '시퀀스 삭제': 'シーケンスを削除',
    '시퀀스(닫힘·반·열림) → 립싱크 순서로 설정하세요': 'シーケンス（閉じ・半開き・開き）→ リップシンクの順に設定してください',
    '시퀀스:': 'シーケンス：',
    "시퀀스를 '%s' 시트로 옮기기 (추천)": 'シーケンスを「%s」シートへ移動（推奨）',
    '시퀀스를 입 파츠의 시트로 옮기기': 'シーケンスを口パーツのシートへ移動',
    '시퀀스를 하나 이상 만들면 쓸 수 있습니다': 'シーケンスを一つ以上作ると使えます',
    '시트': 'シート',
    '시트 불러오기 · 자르기': 'シートの読み込み・切り分け',
    '시트 삭제': 'シートを削除',
    '시트 이미지를 찾을 수 없습니다': 'シート画像が見つかりません',
    '시트 추가': 'シートを追加',
    '시트를 목록에서 뺍니다 (이미 배치한 파츠는 그대로)': 'シートをリストから外します（配置済みのパーツはそのまま）',
    '시트에서 파츠를 고르고 태그를 정해 캔버스에 올립니다. 태그의 기준 마커 위치에 놓입니다': 'シートからパーツを選び、タグを決めてキャンバスに配置します。タグの基準マーカー位置に置かれます',
    "시트의 '립싱크에 사용'을 켜 주세요": 'シートの「リップシンクに使用」をオンにしてください',
    '시트의 칸 하나를 골라 배치': 'シートのセルを一つ選んで配置',
    '썸네일에서 칸을 고릅니다': 'サムネイルからセルを選びます',
    '쓰는 태그: ': '使用中のタグ：',
    '씬에 활성 카메라가 없습니다': 'シーンにアクティブカメラがありません',
    "씬에 활성 카메라가 없습니다. 카메라를 정한 뒤 '카메라 다시 연결'을 누르세요": 'シーンにアクティブカメラがありません。カメラを設定してから「カメラを再接続」を押してください',
    '아 (행, 열)': 'ア（行、列）',
    '아래': '下',
    '아래 레이어들과 섞는 방식 (포토샵 레이어 혼합 모드)': '下のレイヤーとの混ぜ方（Photoshopのレイヤー描画モード）',
    '아래 버튼 → 머리 본 확인': '下のボタン → 頭のボーンを確認',
    '아래 버튼 누르기': '下のボタンを押す',
    '아래 버튼 누르기 → 새 캔버스로 전환됨': '下のボタンを押す → 新しいキャンバスに切り替わる',
    '아래 범위': '下の範囲',
    '아래 화살표로 끝까지 밀어 보며 맞추세요': '下矢印で端まで動かしながら合わせてください',
    '아래서': '下から',
    '아마추어': 'アーマチュア',
    '안내 글자·표시가 겹쳐 보이는 원인입니다. 하나만 켜 두세요': '案内文字・表示が二重に見える原因です。一つだけ有効にしてください',
    '안쪽 드래그 = 이동 (Shift 45°)   ·   방향키 (Shift ×10)   ·   모서리/변 = 크기 (Shift 비율, Alt 기준점)   ·   바깥/○ = 회전 (Shift 15°)': '内側ドラッグ＝移動（Shift 45°）   ·   矢印キー（Shift ×10）   ·   角／辺＝サイズ（Shift 比率、Alt 基準点）   ·   外側／○＝回転（Shift 15°）',
    '앞머리 등 다른 메시에 가려져도 이 파츠가 위로 보입니다 (눈썹 등). 보는 쪽으로 살짝 앞당긴 복사본을 그립니다': '前髪など他のメッシュに隠れてもこのパーツが上に見えます（眉など）。視点側へ少し手前に出したコピーを描きます',
    '앞으로': '前へ',
    '앞으로 당기는 거리': '手前に出す距離',
    '앞쪽 복사본 위치 보기': '手前コピーの位置を表示',
    '애니메이션 키가 들어갈 아마추어(리그)를 고르세요': 'アニメーションキーを入れるアーマチュア（リグ）を選んでください',
    '어둡게': '比較（暗）',
    '어둡게 물들임': '暗く色付け',
    '어떤 표정에서 말하든 이 시퀀스의 입을 씁니다 (전용 시퀀스가 있는 표정만 예외). 메인은 하나만 가능': 'どの表情で話してもこのシーケンスの口を使います（専用シーケンスのある表情は例外）。メインは一つだけ',
    '어떤 표정에서 말하든 이 입을 씀': 'どの表情で話してもこの口を使う',
    '얼굴 가운데': '顔の中央',
    '얼굴 메시 선택 → Tab (편집 모드)': '顔メッシュを選択 → Tab（編集モード）',
    '얼굴 메시 편집 모드에서 눈~입 면을 고르고 누르세요': '顔メッシュの編集モードで目～口の面を選んで押してください',
    '얼굴 메시 편집 모드에서 새로 고른 면으로 캔버스 메시만 바꿉니다. 파츠·마커·프리셋·설정과 그림 위치는 그대로 (같은 정면 UV를 이어서 씀)': '顔メッシュの編集モードで新しく選んだ面でキャンバスメッシュだけを置き換えます。パーツ・マーカー・プリセット・設定と絵の位置はそのまま（同じ正面UVを引き継ぎ）',
    '얼굴 메시를 먼저 선택하세요.': '先に顔メッシュを選択してください。',
    '얼굴 메시와 분리된, 눈·입이 그려질 메시를 만듭니다': '顔メッシュとは別の、目・口が描かれるメッシュを作ります',
    '얼굴 방향': '顔の向き',
    '얼굴 앞에 머리보다 넓은 평면 캔버스를 만들어 머리 본에 붙입니다. 분노 마크처럼 얼굴 밖으로 나가는 감정표현용. 파츠·태그·프리셋은 다른 캔버스와 같이 씁니다': '顔の前に頭より広い平面キャンバスを作り、頭のボーンに付けます。怒りマークのように顔の外へはみ出す感情表現用。パーツ・タグ・プリセットは他のキャンバスと同じように使います',
    '얼굴 앞쪽으로 띄우는 거리 (Plane 크기 대비). 앞머리보다 앞에 오게': '顔の前方に浮かせる距離（プレーンサイズに対して）。前髪より手前に来るように',
    '얼굴 영역이 지정되지 않았습니다.': '顔の範囲が指定されていません。',
    '얼굴 움직임에 다시 붙이기': '顔の動きに付け直す',
    '얼굴 정면 보기': '顔の正面を見る',
    '얼굴 캔버스': '顔キャンバス',
    '얼굴 캔버스 (눈·입 파츠)': '顔キャンバス（目・口パーツ）',
    '얼굴 캔버스 레이어': '顔キャンバスレイヤー',
    '얼굴 캔버스 만들기': '顔キャンバスを作成',
    "얼굴 캔버스 입은 ④ 입 파츠의 '배치 (이 칸만)'에서 칸별로 맞추는 것을 권합니다": '顔キャンバスの口は④口パーツの「配置（このセルのみ）」でセルごとに合わせることをおすすめします',
    '얼굴 캔버스 크기의 몇 배로 만들지': '顔キャンバスの何倍のサイズにするか',
    '얼굴 캔버스를 만들었습니다: ': '顔キャンバスを作成しました：',
    "얼굴 캔버스의 '입' 레이어로 그립니다. 모디파이어/노드를 따로 만들지 않고 캔버스 머티리얼이 이 시트를 읽습니다": '顔キャンバスの「口」レイヤーとして描きます。モディファイアー／ノードは別に作らず、キャンバスのマテリアルがこのシートを読みます',
    '얼굴 캔버스의 입 레이어로 그려집니다 (배치는 얼굴 캔버스 패널에서)': '顔キャンバスの口レイヤーとして描かれます（配置は顔キャンバスパネルで）',
    '얼굴 표면보다 얼마나 안쪽(+)/바깥쪽(-)에 있는 것처럼 보일지. 고개를 돌리면 깊은 레이어가 표면보다 덜 따라와 입체감이 생깁니다 (예: 홍채 0.01, 동공 0.02, 하이라이트 -0.005). 자식은 부모 깊이에 더해집니다': '顔の表面よりどれだけ内側（+）／外側（-）にあるように見せるか。顔を回すと深いレイヤーが表面より遅れて追従し、立体感が出ます（例：虹彩0.01、瞳孔0.02、ハイライト-0.005）。子は親の深度に加算されます',
    '얼굴 표면에서 띄우는 거리 (선택 영역 높이 대비 %). 깜빡이면(Z-fighting) 조금 올리세요': '顔の表面から浮かせる距離（選択範囲の高さに対する%）。ちらつく（Zファイティング）場合は少し上げてください',
    '얼굴(%s) 움직임을 따라가게 붙였습니다': '顔（%s）の動きに追従するように付けました',
    '얼굴·머리카락·모자 등 같이 눌릴 메시를 선택': '顔・髪・帽子など一緒に押しつぶすメッシュを選択',
    '얼굴·머리카락·모자 등 같이 눌릴 메시를 선택하고 누르세요': '顔・髪・帽子など一緒に押しつぶすメッシュを選択して押してください',
    '얼굴에서 띄우기': '顔から浮かせる',
    '얼굴이 +X를 봄 (정면 = 숫자패드 3)': '顔が+Xを向く（正面＝テンキー3）',
    '얼굴이 +Y를 봄 (정면 = Ctrl+숫자패드 1)': '顔が+Yを向く（正面＝Ctrl＋テンキー1）',
    '얼굴이 -X를 봄 (정면 = Ctrl+숫자패드 3)': '顔が-Xを向く（正面＝Ctrl＋テンキー3）',
    '얼굴이 -Y를 봄 (정면 = 숫자패드 1). Blender 기본': '顔が-Yを向く（正面＝テンキー1）。Blenderの標準',
    '없음': 'なし',
    '없음 (-1)': 'なし（-1）',
    '에 (행, 열)': 'エ（行、列）',
    '여기 %는 칸 창 안에서 확대라 100%를 넘기면 가장자리가 잘릴 수 있습니다': 'ここの%はセル枠内での拡大なので、100%を超えると端が切れることがあります',
    '여기 값은 모든 칸에 똑같이 적용되고, 키·애니메이션은 이 값에 들어갑니다': 'ここの値はすべてのセルに同じように適用され、キー・アニメーションはこの値に入ります',
    '여러 파츠를 골라 속성을 한꺼번에 조절합니다': '複数のパーツを選んでプロパティを一括で調整します',
    '열 (가로 칸 수)': '列（横のセル数）',
    '열 이름': '列の名前',
    '열림 기준': '開きの基準',
    '영역 수정을 그만두고 캔버스를 다시 보이게 합니다': '範囲の修正をやめてキャンバスを再表示します',
    '옆모습일수록 더': '横顔ほど強く',
    '옆모습일수록 더 누르기 (0 = 각도와 상관없이 같게)': '横顔に近いほど強く押しつぶす（0＝角度に関係なく同じ）',
    "예전 '반전 칸 만들기'로 다른 칸 그림을 가져다 쓰던 칸을 모두 원래 칸으로 되돌립니다 (그 칸의 크기·위치도 지움)": '以前の「反転セルを作成」で他のセルの絵を使っていたセルをすべて元に戻します（そのセルのサイズ・位置も消去）',
    '오 (행, 열)': 'オ（行、列）',
    '오디오 립싱크를 굽을 때 이 시트의 열(입)에도 키를 넣습니다': 'オーディオリップシンクをベイクするときにこのシートの列（口）にもキーを入れます',
    '오른쪽': '右',
    '오른쪽 범위': '右の範囲',
    '오른쪽에서': '右から',
    '오버레이': 'オーバーレイ',
    '오버레이가 아직 없습니다': 'オーバーレイがまだありません',
    '완료': '完了',
    '왼쪽': '左',
    '왼쪽 범위': '左の範囲',
    '왼쪽에서': '左から',
    '우 (행, 열)': 'ウ（行、列）',
    '움직이는 범위 (끝까지 밀었을 때)': '動く範囲（端まで動かしたとき）',
    '움직임': '動き',
    '원근 뷰가 되어 자유 변형을 확정하고 끝냈습니다': '透視ビューになったため自由変形を確定して終了しました',
    '원래 색': '元の色',
    '원래 색: #%02X%02X%02X': '元の色：#%02X%02X%02X',
    "원래 색이 무채색이라 색조를 바꿀 수 없습니다 (색 덮기 '색상만'을 쓰세요)": '元の色が無彩色なので色相を変えられません（カラーオーバーレイの「カラーのみ」を使ってください）',
    '원본 칸: ': '元のセル：',
    '원본과 다른 칸을 고르세요': '元とは別のセルを選んでください',
    '위': '上',
    "위 '배치'는 이 값 + 칸별 보정입니다": '上の「配置」はこの値＋セルごとの補正です',
    '위 범위': '上の範囲',
    '위가 앞 (위에 있을수록 앞에 그려짐)': '上が手前（上にあるほど手前に描かれる）',
    '위아래 같게': '上下を同じに',
    '위에 있을수록 앞에 그려집니다': '上にあるほど手前に描かれます',
    '위에서': '上から',
    '위쪽 칸별 크기/위치와 같은 값': '上のセルごとのサイズ／位置と同じ値',
    '위치': '位置',
    '위치 0, 크기 1, 회전 0, 불투명도 1로 되돌립니다': '位置0、サイズ1、回転0、不透明度1に戻します',
    '위치 X': '位置X',
    '위치 Y': '位置Y',
    '음량으로 닫힘/반 열림/열림 전환': '音量で閉じ／半開き／開きを切り替え',
    '음소거': 'ミュート',
    '이 (행, 열)': 'イ（行、列）',
    '이 값을 모든 칸에': 'この値をすべてのセルに',
    '이 개방도 이상이면 반 열림': 'この開き度以上で半開き',
    '이 개방도 이상이면 열림': 'この開き度以上で開き',
    '이 레이어 그림을 데칼 안에서 좌우로 뒤집습니다': 'このレイヤーの絵をデカール内で左右反転します',
    '이 레이어가 보일 영역. 고른 레이어(예: 흰자)의 지금 칸 모양 안에서만 보입니다': 'このレイヤーが見える範囲。選んだレイヤー（例：白目）の今のセルの形の中だけで見えます',
    '이 레이어로 그릴 입 스프라이트 시트': 'このレイヤーで描く口のスプライトシート',
    '이 마커 사용': 'このマーカーを使用',
    '이 마커를 쓸 태그 (선택 안 해도 됨)': 'このマーカーを使うタグ（選ばなくても可）',
    '이 시퀀스를 메인으로 사용': 'このシーケンスをメインとして使用',
    "이 시퀀스의 단계를 지금 바로 보여 줍니다 (키는 넣지 않음). 기준 칸으로 표정이 바뀌며, '끄기'로 말하기를 끕니다": 'このシーケンスの段階を今すぐ表示します（キーは入れません）。基準セルの表情に切り替わり、「オフ」で話すのを止めます',
    '이 시트를 그리는 입 파츠가 없습니다 — 미리보기·시퀀스가 화면에 안 보입니다': 'このシートを描く口パーツがありません — プレビュー・シーケンスが画面に表示されません',
    '이 시트의 뷰포트 컨트롤러를 지웁니다 (칸 키는 유지)': 'このシートのビューポートコントローラーを削除します（セルのキーは維持）',
    '이 시트의 시퀀스를 ④ 입 파츠가 그리는 시트로 옮기고, 이 시트는 지웁니다 (같은 입 그림을 쓰는 시트끼리)': 'このシートのシーケンスを④口パーツが描くシートへ移し、このシートは削除します（同じ口の絵を使うシート同士）',
    '이 시트의 이미지를 다른 파일로 바꿉니다. 이 시트에서 올린 파츠와 입 시퀀스도 새 이미지를 씁니다': 'このシートの画像を別のファイルに置き換えます。このシートから配置したパーツと口シーケンスも新しい画像を使います',
    '이 시트의 칸을 뷰포트에서 고르는 격자 패드(+ 말하기 슬라이더)를 드라이버 방식 패널에 만듭니다': 'このシートのセルをビューポートで選ぶグリッドパッド（＋話すスライダー）をコントローラーパネルに作成します',
    "이 입 모양을 지금 바로 보여 줍니다 (키는 넣지 않음). '끄기'로 표정 칸으로 돌아갑니다": 'この口の形を今すぐ表示します（キーは入れません）。「オフ」で表情のセルに戻ります',
    '이 입 키 넣기': 'この口にキーを入れる',
    '이 입의 모든 키': 'この口のすべてのキー',
    '이 입의 위치·크기·회전·불투명도·크롭 키 전부': 'この口の位置・サイズ・回転・不透明度・クロップのキーすべて',
    '이 입의 크기/위치': 'この口のサイズ／位置',
    '이 칸 %d-%d': 'このセル %d-%d',
    '이 칸 = %d-%d 그림': 'このセル＝%d-%d の絵',
    '이 칸 배치 되돌리기': 'このセルの配置を戻す',
    '이 칸 보기': 'このセルを表示',
    '이 칸 전용 값': 'このセル専用の値',
    '이 칸에 그림이 없습니다': 'このセルに絵がありません',
    '이 칸에 넣을 글자를 작은 입력 창에서 씁니다 (Blender에서 한글·일본어·중국어 입력이 안 될 때). 엔터 = 넣기, Esc = 취소': 'この欄に入れる文字を小さな入力ウィンドウで書きます（Blenderで日本語・中国語・韓国語が入力できないとき）。Enter＝入力、Esc＝キャンセル',
    '이 칸은 글자를 넣을 수 없습니다': 'この欄には文字を入れられません',
    '이 칸을 일괄 조절할 칸으로 체크합니다. 지금 칸의 배치를 바꾸면 체크한 칸들도 같이 바뀝니다 (크기는 같은 비율, 위치·회전은 움직인 만큼)': 'このセルを一括調整の対象にします。今のセルの配置を変えるとチェックしたセルも一緒に変わります（サイズは同じ比率、位置・回転は動かした分）',
    '이 칸을 일괄 조절할 칸으로 체크합니다. 지금 칸의 크기·위치를 바꾸면 체크한 칸들도 같이 바뀝니다 (크기는 같은 비율, 위치는 움직인 만큼)': 'このセルを一括調整の対象にします。今のセルのサイズ・位置を変えるとチェックしたセルも一緒に変わります（サイズは同じ比率、位置は動かした分）',
    '이 칸을 지금 칸으로 만들어 뷰포트에 바로 보여 줍니다 (자동 키가 켜져 있으면 키도 들어감). 배치는 이 칸 기준으로 조절됩니다': 'このセルを今のセルにしてビューポートにすぐ表示します（自動キーがオンならキーも入ります）。配置はこのセル基準で調整されます',
    '이 칸을 지금 칸으로 만들어 뷰포트에 바로 보여 줍니다 (자동 키가 켜져 있으면 키도 들어감). 크기·위치는 이 칸 기준으로 조절됩니다': 'このセルを今のセルにしてビューポートにすぐ表示します（自動キーがオンならキーも入ります）。サイズ・位置はこのセル基準で調整されます',
    '이 칸이 표정으로 선택되어 있을 때 (행, 열)': 'このセルが表情として選ばれているとき（行、列）',
    '이 컨트롤러는 크기를 바꿀 수 없습니다 (위치만 옮길 수 있음)': 'このコントローラーはサイズを変えられません（位置の移動のみ）',
    '이 태그 파츠가 앞머리 등에 가려져도 위로 보이게 (지금 있는 파츠에도 바로 적용)': 'このタグのパーツが前髪などに隠れても上に見えるように（既存のパーツにもすぐ適用）',
    '이 태그 파츠는 ⑥의 입 시퀀스·립싱크로 칸이 바뀝니다': 'このタグのパーツは⑥の口シーケンス・リップシンクでセルが切り替わります',
    '이 태그 파츠에 키를 넣을 때 쓸 보간 방법 (위치·크기·회전·불투명도·크롭). 태그마다 따로 저장. 칸(그림) 키는 항상 Constant': 'このタグのパーツにキーを入れるときの補間方法（位置・サイズ・回転・不透明度・クロップ）。タグごとに保存。セル（絵）のキーは常にConstant',
    '이 태그 파츠의 위치 X/Y가 이 마커로부터의 거리가 됩니다': 'このタグのパーツの位置X/Yがこのマーカーからの距離になります',
    '이 탭의 컨트롤러만 배치 모드로: 틀을 선택해 옮길 수 있습니다. 다시 누르거나 ESC/우클릭으로 끕니다': 'コントローラーを配置モードに：枠を選んで移動できます。もう一度押すかESC／右クリックで終了',
    '이 파츠 키 넣기': 'このパーツにキーを入れる',
    '이 파츠에 이미 넣은 키 전부(위치·크기·회전·불투명도·크롭)를 지금 고른 보간 방법으로 바꿉니다': 'このパーツにすでに入れたキーすべて（位置・サイズ・回転・不透明度・クロップ）を今選んだ補間方法に変えます',
    '이 파츠의 모든 키': 'このパーツのすべてのキー',
    '이 파츠의 스프라이트 시트 (칸 = 파츠의 상태)': 'このパーツのスプライトシート（セル＝パーツの状態）',
    '이 파츠의 위치·크기·회전·불투명도·크롭 키 전부': 'このパーツの位置・サイズ・回転・不透明度・クロップのキーすべて',
    '이 파츠의 지금 값 전부(칸·위치·크기·회전·불투명도·크롭)를 현재 프레임에 키로 넣습니다': 'このパーツの今の値すべて（セル・位置・サイズ・回転・不透明度・クロップ）を現在のフレームにキーとして入れます',
    '이 폴더 삭제': 'このフォルダーを削除',
    '이 폴더 키 넣기': 'このフォルダーにキーを入れる',
    '이 폴더로 전환': 'このフォルダーに切り替え',
    "이 폴더를 켜고 같은 태그·같은 자리의 다른 폴더는 끕니다 ('바꾸면 자동 키'가 켜져 있으면 키도 넣음)": 'このフォルダーをオンにし、同じタグ・同じ位置の他のフォルダーはオフにします（「変更時に自動キー」がオンならキーも入れる）',
    "이 폴더의 파츠만 보이게 전환합니다 ('바꾸면 자동 키'가 켜져 있으면 키도 넣음)": 'このフォルダーのパーツだけが見えるように切り替えます（「変更時に自動キー」がオンならキーも入れる）',
    '이 표정을 적용하고 현재 프레임에 키를 넣습니다 (이 프레임부터 표정이 바뀜)': 'この表情を適用して現在のフレームにキーを入れます（このフレームから表情が変わる）',
    '이 표정일 때만 사용': 'この表情のときだけ使用',
    '이동 배율': '移動倍率',
    '이름': '名前',
    '이름을 정해 새로 만듭니다': '名前を決めて新しく作ります',
    '이름을 직접 정하는 마커': '名前を自分で決めるマーカー',
    '이미 넣은 입 배치 키에 지금 고른 보간 방법을 적용합니다 (선택한 키프레임만 / 이 입의 모든 키)': '既存の口の配置キーに今選んだ補間方法を適用します（選択したキーフレームのみ／この口のすべてのキー）',
    '이미 넣은 키에 지금 고른 보간 방법을 적용합니다 (선택한 키프레임만 / 이 파츠의 모든 키)': '既存のキーに今選んだ補間方法を適用します（選択したキーフレームのみ／このパーツのすべてのキー）',
    '이미 변형된 값이 있는 칸입니다': 'すでに変形された値があるセルです',
    "이미 있는 '%s' 마커에 '%s' 태그를 연결합니다": '既存のマーカー「%s」にタグ「%s」を接続します',
    '이미지': '画像',
    '이미지 다시 불러오기': '画像を再読み込み',
    '이미지 불러오기': '画像を開く',
    '이미지 불러오기: ': '画像を読み込み：',
    '이미지 없음 (썸네일 불가)': '画像なし（サムネイル不可）',
    '이미지 텍스처 앞에 Mapping 노드를 넣어 이동': '画像テクスチャの前にマッピングノードを入れて移動',
    '이미지 파일을 고르세요': '画像ファイルを選んでください',
    '이미지를 고르세요': '画像を選んでください',
    '이미지를 바꿨습니다: ': '画像を置き換えました：',
    '이미지를 찾지 못해 빠졌습니다: ': '画像が見つからず除外されました：',
    '이미지를 칸 단위로 잘라 선택 그리드 썸네일을 만듭니다': '画像をセル単位で切り分けて選択グリッドのサムネイルを作ります',
    '이전/다음 칸': '前／次のセル',
    '일괄 조절': '一括調整',
    '일괄 조절하기': '一括調整する',
    '일괄 조절할 칸': '一括調整するセル',
    '일반': '通常',
    '일정한 속도로 변함': '一定の速度で変化',
    '입 (스프라이트 시트)': '口（スプライトシート）',
    '입 (시퀀스·립싱크)': '口（シーケンス・リップシンク）',
    '입 모양이 이보다 짧게 바뀌면 앞 모양에 합칩니다. 2 = 애니메이션식 on twos': '口の形がこれより短く切り替わると前の形にまとめます。2＝アニメ風の2コマ打ち',
    '입 벌림 (선택한 구간):': '口の開き（選択した区間）：',
    '입 스프라이트 시트를 그대로 그림 (시퀀스·립싱크·뷰포트 컨트롤러가 그대로 동작)': '口のスプライトシートをそのまま描く（シーケンス・リップシンク・ビューポートコントローラーがそのまま動作）',
    '입 시퀀스': '口シーケンス',
    '입 시퀀스 · 표정 목록 · 시선 패드를 뷰포트에 만듭니다': '口シーケンス・表情リスト・視線パッドをビューポートに作成します',
    '입 시트': '口シート',
    '입 전체 배치': '口全体の配置',
    '입 칸을 고르거나 입 배치(위치·크기·회전·불투명도·크롭), 시퀀스 선택·말하기 값을 바꾸면 현재 프레임에 키를 바로 넣습니다 (꺼져 있어도 Blender 자동 키가 켜져 있으면 칸은 삽입)': '口のセルを選んだり、口の配置（位置・サイズ・回転・不透明度・クロップ）、シーケンス選択・話す値を変えると、現在のフレームにすぐキーを入れます（オフでもBlenderの自動キーがオンならセルは挿入）',
    '입 키 넣기': '口にキーを入れる',
    '입 키를 넣을 때 쓸 보간 방법 (입 전체의 위치·크기·회전·불투명도·크롭). 칸·시퀀스·말하기 키는 항상 Constant': '口にキーを入れるときの補間方法（口全体の位置・サイズ・回転・不透明度・クロップ）。セル・シーケンス・話すキーは常にConstant',
    '입 파츠 추가 방법': '口パーツの追加方法',
    "입 파츠는 '%s' 시트를 그리고 있습니다. 옮기면 이 시트는 지워집니다": '口パーツは「%s」シートを描いています。移すとこのシートは削除されます',
    '입 파츠는 지원하지 않습니다': '口パーツには対応していません',
    '입 파츠에 연결': '口パーツに接続',
    '입력 창으로 이름 쓰기': '入力ウィンドウで名前を入力',
    '입력 창을 열 수 없습니다': '入力ウィンドウを開けません',
    '자동 (표정 따라)': '自動（表情に追従）',
    '자동 정렬': '自動整列',
    '자동 클리핑': '自動クリッピング',
    '자식 펼치기': '子を展開',
    "자식에서 켜면 부모 위에 '추가로' 더 움직임 (배율로 양 조절)": '子でオンにすると親の動きに「追加で」さらに動く（倍率で量を調整）',
    '자유 배치': '自由配置',
    '자유 변형 (Ctrl+T)': '自由変形（Ctrl+T）',
    '자유 변형 시작 실패: ': '自由変形の開始に失敗：',
    '자유 변형이 중단되었습니다 (Undo·파일 열기·파츠 삭제)': '自由変形が中断されました（Undo・ファイルを開く・パーツ削除）',
    '자체 칸': '自身のセル',
    '작게 벌린 칸 (행, 열). -1 = 기준 칸 그대로': '少し開いたセル（行、列）。-1＝基準セルのまま',
    '작업 방식': '作業方式',
    '저장하고 끝내기': '保存して終了',
    '저장하지 않고 끝냅니다 (멈췄던 키프레임을 되살림)': '保存せずに終了します（止めていたキーフレームを戻す）',
    '적용': '適用',
    '적용 (머티리얼 재구성)': '適用（マテリアルを再構成）',
    '적용할 메시: ': '適用するメッシュ：',
    '전부 지우기': 'すべて削除',
    '전체': 'すべて',
    '전체 배치 (모든 칸 공통)': '全体の配置（全セル共通）',
    '전체 보기': '全体表示',
    '전체 보기 (폴더 없이)': '全体表示（フォルダーなし）',
    '전환': '切り替え',
    '정렬': '整列',
    '정면 뷰에서 얼굴의 %s 위치를 클릭하세요 · 우클릭/ESC 취소': '正面ビューで顔の%sの位置をクリックしてください · 右クリック／ESCでキャンセル',
    '종류': '種類',
    '종횡비 고정': '縦横比を固定',
    '종횡비 고정 (이 칸)': '縦横比を固定（このセル）',
    '종횡비 고정 중: 세로를 바꾸면 가로도 같은 비율로': '縦横比固定中：縦を変えると横も同じ比率で変わります',
    '좌우': '左右',
    '좌우 같게': '左右を同じに',
    '중간 칸 (행, 열). -1 = 열림 칸 사용': '中間のセル（行、列）。-1＝開きのセルを使用',
    '중심 다시 잡기': '中心を取り直す',
    '지금 고른 캔버스의 파츠·태그·마커·시트·표정 프리셋·입 시퀀스·립싱크 설정과 속성값, 시트 이미지(원본 해상도)를 .zip 하나로 저장합니다 (키프레임 제외)': '今選んでいるキャンバスのパーツ・タグ・マーカー・シート・表情プリセット・口シーケンス・リップシンク設定とプロパティ値、シート画像（元の解像度）を一つの.zipに保存します（キーフレームは除く）',
    '지금 보이는 칸의 그림으로 파츠 중심을 다시 계산합니다 (그림 위치는 그대로)': '今見えているセルの絵でパーツの中心を計算し直します（絵の位置はそのまま）',
    '지금 보이는 파츠 배치(칸·위치·크기·회전·불투명도, 입 칸)를 표정으로 저장합니다': '今見えているパーツの配置（セル・位置・サイズ・回転・不透明度、口のセル）を表情として保存します',
    '지금 보이는 파츠들로 새 폴더를 만듭니다': '今見えているパーツで新しいフォルダーを作ります',
    '지금 보이는 파츠로 덮어쓰기': '今見えているパーツで上書き',
    '지금 선택된 칸을 기준 칸으로 하는 시퀀스를 추가합니다 (열림 = 기준 칸). 닫힘 칸을 지정해 주세요': '今選んでいるセルを基準セルとするシーケンスを追加します（開き＝基準セル）。閉じのセルを指定してください',
    '지금 시점에서는 파츠를 가리는 메시가 없습니다 (가려지는 각도에서 다시 눌러 보세요)': '今の視点ではパーツを隠すメッシュがありません（隠れる角度でもう一度押してください）',
    '지금 씬의 활성 카메라를 기준으로 누르게 합니다': '今のシーンのアクティブカメラを基準に押しつぶします',
    "지금 칸 그림에서 가장 많이 쓰인 색을 '원래 색'으로 넣습니다 (스포이트는 화면 색이라 조명·색 관리 때문에 틀릴 수 있음)": '今のセルの絵で最も多く使われている色を「元の色」に入れます（スポイトは画面の色なので照明・カラーマネジメントでずれることがあります）',
    '지금 칸(빨간 버튼)의 배치를 바꾸면 체크한 칸도 같이 바뀝니다': '今のセル（赤いボタン）の配置を変えると、チェックしたセルも一緒に変わります',
    '지금 칸(빨간 버튼)의 크기·위치·반전을 바꾸면 체크한 칸도 같이 바뀝니다': '今のセル（赤いボタン）のサイズ・位置・反転を変えると、チェックしたセルも一緒に変わります',
    '지금 칸만 종횡비를 고정하거나 풉니다 (칸마다 따로). 일괄 조절로 체크한 칸에도 같이 적용': '今のセルだけ縦横比を固定／解除します（セルごとに別）。一括調整でチェックしたセルにも適用',
    '지금 칸에 저장된 크기·위치·반전과 다른 칸 그림 연결을 모두 지우고, 이미지에 그려진 원래 칸으로 되돌립니다 (이미지 파일은 건드리지 않음)': '今のセルに保存されたサイズ・位置・反転と他セル絵の接続をすべて消し、画像に描かれた元のセルに戻します（画像ファイルは変更しません）',
    '지금 칸으로 지정': '今のセルに指定',
    '지금 칸의 그림 크기 (칸마다 따로가 꺼져 있으면 공통)': '今のセルの絵のサイズ（「セルごとに別」がオフなら共通）',
    '지금 칸의 그림을 뒤집어서 다른 칸 번호로 씁니다. 이미지에 반전 그림을 따로 그릴 필요가 없습니다': '今のセルの絵を反転して別のセル番号として使います。画像に反転した絵を別に描く必要がありません',
    '지금 칸의 그림을 위아래로 뒤집습니다': '今のセルの絵を上下反転します',
    '지금 칸의 그림을 좌우로 뒤집습니다': '今のセルの絵を左右反転します',
    '지금 칸의 칸별 배치(위치·크기·회전·불투명도·크롭)를 지워 전체 배치 값으로 되돌립니다 (일괄 조절로 체크한 칸도 같이)': '今のセルのセルごとの配置（位置・サイズ・回転・不透明度・クロップ）を消して全体の配置値に戻します（一括調整でチェックしたセルも一緒に）',
    '지금 칸의 크기/위치를 공통값으로 만들고 다른 칸의 개별 설정을 모두 지웁니다': '今のセルのサイズ／位置を共通値にして、他のセルの個別設定をすべて消します',
    "지금 캔버스 영역(면 %d개)을 선택해 두었습니다. 면을 더하거나 빼고 '적용'을 누르세요": '今のキャンバス範囲（面%d個）を選択しておきました。面を追加・除外して「適用」を押してください',
    '지금 캔버스 영역이 선택되어 있습니다': '今のキャンバス範囲が選択されています',
    '지금 캔버스의 UV 투영을 알아내지 못했습니다': '今のキャンバスのUV投影を特定できませんでした',
    '지금 파츠 상태를 이 프리셋에 덮어쓰고, 멈췄던 키프레임을 되살립니다': '今のパーツの状態をこのプリセットに上書きし、止めていたキーフレームを戻します',
    '지금 폴더를 지금 보이는 파츠들로 덮어씁니다': '今のフォルダーを今見えているパーツで上書きします',
    '지금 폴더를 지웁니다 (파츠는 그대로)': '今のフォルダーを削除します（パーツはそのまま）',
    '지우기': '削除',
    '지정 해제 (표정 따라)': '指定を解除（表情に追従）',
    '찍기': '配置',
    '차이': '差の絶対値',
    '채도': '彩度',
    '초': '秒',
    '초당 약 12번 따라감 (조금 끊겨 보이지만 가벼움)': '毎秒約12回追従（少しカクつきますが軽い）',
    '최소 유지 (프레임)': '最小保持（フレーム）',
    '추가하고 바로 찍기': '追加してすぐ配置',
    '취소': 'キャンセル',
    '측정 중 (%d초) — 렉이 나는 동작을 해 주세요': '計測中（%d秒）— 重くなる操作をしてください',
    '측정 중…': '計測中…',
    '카메라 다시 연결': 'カメラを再接続',
    '카메라 시선 방향으로 머리를 누르는 정도': 'カメラの視線方向に頭を押しつぶす度合い',
    '카메라: ': 'カメラ：',
    '칸': 'セル',
    '칸 %d개를 비웠습니다': 'セルを%d個クリアしました',
    '칸 가운데(= 마커 + 위치)를 기준으로 크기·회전': 'セルの中央（＝マーカー＋位置）を基準にサイズ・回転',
    '칸 따라가기': 'セルに追従',
    '칸 배치가 같아야 파츠 번호가 유지됩니다': 'セル配置が同じでないとパーツ番号は維持されません',
    '칸 번호 버튼 = 그 칸을 뷰포트에 보기 · 체크 = 일괄 조절': 'セル番号ボタン＝そのセルをビューポートに表示 · チェック＝一括調整',
    '칸 번호가 범위를 벗어났습니다': 'セル番号が範囲外です',
    '칸 비우기': 'セルをクリア',
    '칸 비우기로 해제': 'セルをクリアで解除',
    '칸 수/이미지가 바뀌었습니다. 컨트롤러를 갱신하세요': 'セル数／画像が変わりました。コントローラーを更新してください',
    '칸 썸네일 격자를 펼쳐 일괄 조절할 칸을 고릅니다': 'セルのサムネイルグリッドを展開して一括調整するセルを選びます',
    '칸 안에 그려진 그림의 가운데를 기준으로 크기·회전': 'セル内に描かれた絵の中央を基準にサイズ・回転',
    '칸 하나를 표정으로 고르고, 말할 때 입은 모음 또는 시퀀스로 지정합니다': 'セルを一つ表情として選び、話すときの口は母音またはシーケンスで指定します',
    '칸마다 따로': 'セルごとに別',
    '칸별 배치': 'セルごとの配置',
    '칸은 입 시트(시퀀스·립싱크·뷰포트 컨트롤러)로 바뀝니다': 'セルは口シート（シーケンス・リップシンク・ビューポートコントローラー）で切り替わります',
    '칸을 잘라 파츠 번호를 매기는 중…': 'セルを切り分けてパーツ番号を付けています…',
    '칸이 2개 이상인 파츠만 표시할 수 있습니다': 'セルが2つ以上のパーツだけ表示できます',
    '칸이 바뀔 오브젝트 (입 데칼, 범고래 얼굴 등)': 'セルが切り替わるオブジェクト（口のデカール、帽子の顔など）',
    '캐릭터 얼굴이 바라보는 축. 캔버스 정면 투영 UV와 마커 찍기 화면 방향의 기준이 됩니다': 'キャラクターの顔が向いている軸。キャンバスの正面投影UVとマーカー配置画面の向きの基準になります',
    '캔버스': 'キャンバス',
    '캔버스 가장자리 여백 (파츠가 테두리에 잘리지 않게)': 'キャンバスの端の余白（パーツが縁で切れないように）',
    '캔버스 내보내기': 'キャンバスをエクスポート',
    '캔버스 메시를 직접 고친 뒤(Extrude·정점 이동 등) 누르세요. 늘린 면에 같은 정면 UV를 이어 주고, 얼굴에 다시 붙입니다. 기존 파츠·마커 위치는 그대로': 'キャンバスメッシュを直接修正した後（押し出し・頂点移動など）に押してください。増えた面に同じ正面UVをつなげ、顔に貼り直します。既存のパーツ・マーカーの位置はそのまま',
    '캔버스 불러오기 (덮어쓰기)': 'キャンバスをインポート（上書き）',
    '캔버스 영역을 바꿨습니다 (면 %d개)': 'キャンバス範囲を変更しました（面%d個）',
    '캔버스 위 위치 (0~1, 정면 기준). 다시 찍거나 숫자로 조절': 'キャンバス上の位置（0～1、正面基準）。再配置するか数値で調整',
    '캔버스 위를 클릭하세요': 'キャンバスの上をクリックしてください',
    '캔버스 추가 (모자 얼굴 · 감정표현 Plane)': 'キャンバスを追加（帽子の顔 · 感情表現プレーン）',
    '캔버스(%s)를 선택하면 켜집니다': 'キャンバス（%s）を選択すると有効になります',
    '캔버스가 붙은 얼굴 메시를 찾지 못했습니다': 'キャンバスが付いている顔メッシュが見つかりませんでした',
    '캔버스가 아니라 얼굴 메시(원본)를 편집 모드로 열고 면을 고르세요': 'キャンバスではなく顔メッシュ（元）を編集モードで開いて面を選んでください',
    '캔버스가 얼굴 메시의 최종 모양(아마추어·셰이프 키)을 그대로 따라가게 다시 붙입니다. 리그에 캔버스를 따로 바인드해서 일그러질 때 누르세요 (캔버스의 아마추어 모디파이어는 지워짐)': 'キャンバスが顔メッシュの最終形状（アーマチュア・シェイプキー）にそのまま追従するように付け直します。キャンバスをリグに別途バインドして歪んだときに押してください（キャンバスのアーマチュアモディファイアーは削除）',
    '캔버스가 얼굴과 따로 움직일 수 있습니다. 위 버튼으로 다시 붙이세요': 'キャンバスが顔と別に動く可能性があります。上のボタンで付け直してください',
    '캔버스가 얼굴의 서브디비전 없이 같은 변형(아마추어·셰이프 키)만 따라가게 합니다. 리그를 움직이거나 재생할 때 훨씬 가볍고(얼굴 GPU 서브디비전도 다시 켜짐), 렌더에서는 지금처럼 실제 얼굴 표면에 딱 맞습니다. 뷰포트에서는 파츠가 얼굴에서 아주 살짝 더 떠 보일 수 있습니다': 'キャンバスが顔のサブディビジョンなしで同じ変形（アーマチュア・シェイプキー）だけに追従するようにします。リグを動かしたり再生したりするときにずっと軽く（顔のGPUサブディビジョンも再びオン）、レンダーでは今まで通り実際の顔の表面にぴったり合います。ビューポートではパーツが顔からほんの少し浮いて見えることがあります',
    '캔버스는 얼굴을 따라가므로 고르지 않아도 됩니다': 'キャンバスは顔に追従するので選ばなくても大丈夫です',
    '캔버스로 쓸 앞면을 면 선택': 'キャンバスにする前面を面選択',
    '캔버스로 쓸 얼굴 앞면(눈썹 위~턱)을 면 선택한 뒤 다시 누르세요. (점·선만 선택하면 면이 잡히지 않습니다)': 'キャンバスにする顔の前面（眉の上～あご）を面選択してから、もう一度押してください。（点・辺だけ選ぶと面は選ばれません）',
    '캔버스를 만들지 못했습니다': 'キャンバスを作成できませんでした',
    '캔버스를 얼굴 표면에서 띄우는 거리. 비스듬히 볼 때 피부가 줄무늬처럼 비쳐 보이면(Z-fighting) 조금 올리세요': 'キャンバスを顔の表面から浮かせる距離。斜めから見て肌が縞模様に透けて見える（Zファイティング）なら少し上げてください',
    "캔버스를 잠시 숨기고 얼굴 메시를 편집 모드로 엽니다. 지금 캔버스 영역이 미리 선택되어 있으니 면을 더하거나 빼고 '적용'을 누르세요": 'キャンバスを一時的に隠し、顔メッシュを編集モードで開きます。今のキャンバス範囲があらかじめ選択されているので、面を追加・除外して「適用」を押してください',
    '캔버스를 찾지 못했습니다': 'キャンバスが見つかりませんでした',
    '컨트롤러 위치 옮기기 (배치 모드)': 'コントローラーの位置を移動（配置モード）',
    '컨트롤러가 생기거나 크기가 바뀌면 기본 배치로 다시 쌓습니다. 직접 옮긴 자리를 지키려면 끄세요': 'コントローラーが追加されたりサイズが変わったりすると基本配置で積み直します。手動で動かした位置を保つならオフにしてください',
    '켜면 아래 범위 = 위 범위 (보통 아래를 조금 더 크게)': 'オンで下の範囲＝上の範囲（通常は下を少し大きめに）',
    "켜면 아래에서 고른 그룹(태그)만 바꿉니다 ('화난 눈 + 웃는 입'처럼 섞기). 끄면 표정 전체를 바꿉니다": 'オンにすると下で選んだグループ（タグ）だけ変えます（「怒った目＋笑った口」のように混ぜる）。オフで表情全体を変えます',
    '켜면 왼쪽 범위 = 오른쪽 범위': 'オンで左の範囲＝右の範囲',
    '켜면 이 눈은 자기 파츠 목록 대신 따라가는 눈의 파츠 전체를 좌우로 뒤집어 씁니다. 왼눈만 세팅하면 됩니다': 'オンにするとこの目は自分のパーツリストの代わりに、追従する目のパーツ全体を左右反転して使います。左目だけ設定すれば済みます',
    '켜면 지금 가로세로 비율을 그대로 지킨 채 가로·세로가 같이 커지고 작아집니다. 꺼도 모양은 그대로': 'オンにすると今の縦横比を保ったまま横・縦が一緒に大きく・小さくなります。オフにしても形はそのまま',
    '켜면 지금 가로세로 비율을 그대로 지킨 채 가로나 세로를 바꿀 때 둘이 같이 커지고 작아집니다 (이 입 칸만)': 'オンにすると今の縦横比を保ったまま、横か縦を変えると両方一緒に大きく・小さくなります（この口のセルのみ）',
    '켜면 크기 하나로 가로·세로를 같이, 끄면 따로 조절': 'オンで一つのサイズで横・縦を一緒に、オフで別々に調整',
    '켜면 크기/위치를 칸마다 따로 기억합니다 (손대지 않은 칸은 공통값). 끄면 모든 칸이 공통값을 씁니다': 'オンにするとサイズ／位置をセルごとに記憶します（触っていないセルは共通値）。オフで全セルが共通値を使います',
    '켜면 키프레임을 무시하고 고른 칸을 계속 보여 줍니다 (칸을 골라도 키가 들어가지 않음). 칸별 배치를 조절할 때 켜고, 끝나면 끄세요': 'オンにするとキーフレームを無視して選んだセルを表示し続けます（セルを選んでもキーは入りません）。セルごとの配置を調整するときにオンにし、終わったらオフにしてください',
    '켜져 있음': 'オン',
    '켜짐': 'オン',
    '켜짐/꺼짐은 키·표정 프리셋에 들어갑니다': 'オン／オフはキー・表情プリセットに入ります',
    '크게 벌린 칸 (행, 열). -1 = 반 열림 칸 사용': '大きく開いたセル（行、列）。-1＝半開きのセルを使用',
    '크기 (얼굴 대비)': 'サイズ（顔に対して）',
    '크기·위치는 오브젝트를 직접 옮기거나 S로 조절해도 됩니다': 'サイズ・位置はオブジェクトを直接動かしたりSで調整しても構いません',
    '크기·회전 기준': 'サイズ・回転の基準',
    '크기는 같은 비율로, 위치·회전은 움직인 만큼': 'サイズは同じ比率で、位置・回転は動かした分だけ',
    '크기는 같은 비율로, 위치는 움직인 만큼': 'サイズは同じ比率で、位置は動かした分だけ',
    '크롭': 'クロップ',
    '크롭 (그림 영역 기준으로 잘라내기)': 'クロップ（絵の範囲を基準に切り取り）',
    '클리핑 마스크': 'クリッピングマスク',
    '키 넣기': 'キーを入れる',
    '키 보간': 'キーの補間',
    '키 삽입': 'キーを挿入',
    '키 삽입: ': 'キー挿入：',
    "키 삽입: '%s' 오브젝트 (프레임 %d)": 'キー挿入：オブジェクト「%s」（フレーム%d）',
    '키프레임 멈춤': 'キーフレーム停止中',
    '키프레임은 잠시 멈춰 있고, 키는 들어가지 않습니다': 'キーフレームは一時停止中で、キーは入りません',
    "키프레임을 잠시 멈추고 고른 프리셋(표정)의 파츠를 그대로 고칩니다. 끝나면 '저장하고 끝내기' 또는 '취소'": 'キーフレームを一時停止し、選んだプリセット（表情）のパーツを直接修正します。終わったら「保存して終了」または「キャンセル」',
    '키프레임을 잠시 멈추고 이 프리셋의 파츠를 고칩니다. 그동안 키는 들어가지 않습니다': 'キーフレームを一時停止してこのプリセットのパーツを修正します。その間キーは入りません',
    '태그': 'タグ',
    '태그 (그룹)': 'タグ（グループ）',
    '태그 삭제': 'タグを削除',
    '태그 없음': 'タグなし',
    '태그 추가': 'タグを追加',
    "태그를 지웁니다. 이 태그였던 파츠는 '태그 없음'(얼굴 가운데 기준)이 됩니다": 'タグを削除します。このタグだったパーツは「タグなし」（顔の中央基準）になります',
    '탭': 'タブ',
    '투명 배경 설정 완료 (머티리얼 %d개)': '透明背景の設定完了（マテリアル%d個）',
    '투명 배경 설정을 눌러야 칸 밖이 잘립니다': '「透明背景を設定」を押すとセルの外が切り取られます',
    '투명 픽셀 %d개의 색을 채웠습니다': '透明ピクセル%d個の色を埋めました',
    '파일에서 스프라이트 시트 이미지를 불러와 바로 적용합니다 (대상 머티리얼의 기존 시트 이미지도 교체)': 'ファイルからスプライトシート画像を読み込んですぐ適用します（対象マテリアルの既存のシート画像も置き換え）',
    '파츠 %d개': 'パーツ%d個',
    '파츠 가장자리에 얇은 흰 선이 보일 때. 투명한 곳에 숨어 있는 흰색을 그림 색으로 채웁니다 (그림·투명도는 그대로). 고친 이미지는 .blend 안에 저장됩니다': 'パーツの縁に細い白い線が見えるとき。透明な部分に隠れている白を絵の色で埋めます（絵・透明度はそのまま）。修正した画像は.blendの中に保存されます',
    '파츠 격자·입·표정 목록·시선 패드를 뷰포트에 만들거나 갱신하거나 정렬하거나 지웁니다': 'パーツグリッド・口・表情リスト・視線パッドをビューポートに作成・更新・整列・削除します',
    '파츠 그룹(태그)을 만듭니다. 기준 마커와 새 파츠의 기본값(대칭·시선·입·크기)을 정합니다': 'パーツグループ（タグ）を作ります。基準マーカーと新規パーツの初期値（対称・視線・口・サイズ）を決めます',
    '파츠 그룹. 그 태그의 기준 마커 위치에 놓입니다': 'パーツグループ。そのタグの基準マーカー位置に置かれます',
    '파츠 그림 위에 한 색을 덮습니다 (모양·투명도는 그대로)': 'パーツの絵の上に一色をかぶせます（形・透明度はそのまま）',
    '파츠 보이기/숨기기. 키를 넣을 수 있고(Constant) 표정 프리셋에도 저장됩니다. 부모를 숨기면 자식도 숨겨집니다': 'パーツの表示／非表示。キーを入れられ（Constant）、表情プリセットにも保存されます。親を隠すと子も隠れます',
    '파츠 복제': 'パーツを複製',
    '파츠 삭제': 'パーツを削除',
    '파츠 올리기': 'パーツを配置',
    '파츠 이름': 'パーツ名',
    '파츠 중심': 'パーツの中心',
    '파츠 키를 넣을 때 쓸 보간 방법 (위치·크기·회전·불투명도·크롭). 칸(그림) 키는 항상 Constant': 'パーツにキーを入れるときの補間方法（位置・サイズ・回転・不透明度・クロップ）。セル（絵）のキーは常にConstant',
    '파츠 폴더': 'パーツフォルダー',
    '파츠: ': 'パーツ：',
    '파츠가 없습니다. + 로 흰자부터 추가하세요': 'パーツがありません。＋で白目から追加してください',
    "파츠를 고른 뒤 '부모'를 이 폴더로 바꾸면 들어옵니다": 'パーツを選んで「親」をこのフォルダーにすると中に入ります',
    '파츠를 놓을 기준점을 추가합니다. 눈·눈썹·입·감정표현을 고르거나 + 로 이름을 직접 정합니다': 'パーツを置く基準点を追加します。目・眉・口・感情表現を選ぶか、＋で名前を自分で決めます',
    '파츠를 묶는 폴더 (그림 없음). 같은 태그·같은 자리의 폴더끼리는 하나만 켜집니다': 'パーツをまとめるフォルダー（絵なし）。同じタグ・同じ位置のフォルダーは一つだけオンになります',
    '파츠의 칸·위치·크기·회전·불투명도·크롭이나 시선, 표정을 바꾸면 현재 프레임에 키를 바로 넣습니다': 'パーツのセル・位置・サイズ・回転・不透明度・クロップや視線、表情を変えると現在のフレームにすぐキーを入れます',
    '패드를 끝까지 밀어 범위를 확인합니다 (키는 넣지 않음)': 'パッドを端まで動かして範囲を確認します（キーは入れません）',
    '패드를 아래 끝까지 밀었을 때 눈동자가 움직이는 거리 (캔버스 높이 대비)': 'パッドを下端まで動かしたときに瞳が動く距離（キャンバスの高さに対して）',
    '패드를 오른쪽 끝까지 밀었을 때 눈동자가 움직이는 거리 (캔버스 폭 대비. 0.03 = 3%)': 'パッドを右端まで動かしたときに瞳が動く距離（キャンバスの幅に対して。0.03＝3%）',
    '패드를 왼쪽 끝까지 밀었을 때 눈동자가 움직이는 거리 (캔버스 폭 대비. 0.03 = 3%)': 'パッドを左端まで動かしたときに瞳が動く距離（キャンバスの幅に対して。0.03＝3%）',
    '패드를 위 끝까지 밀었을 때 눈동자가 움직이는 거리 (캔버스 높이 대비)': 'パッドを上端まで動かしたときに瞳が動く距離（キャンバスの高さに対して）',
    '패럴랙스 강도': '視差の強さ',
    '편 캔버스를 원래 모양으로 되돌렸습니다': '平らにしたキャンバスを元の形に戻しました',
    '편집 모드': '編集モード',
    '편집 모드 (키프레임 무시)': '編集モード（キーフレーム無視）',
    '편집 모드 켜짐 (%d-%d 고정)': '編集モード オン（%d-%d 固定）',
    "편집 모드에서 고른 얼굴 면을 복사해 살짝 띄운 '얼굴 캔버스'를 만듭니다. 정면 투영 UV, 얼굴과 같은 변형(아마추어·셰이프 키)을 따라가며, 눈·입 파츠를 이 메시 하나에 조립합니다": '編集モードで選んだ顔の面をコピーし、少し浮かせた「顔キャンバス」を作ります。正面投影UVで、顔と同じ変形（アーマチュア・シェイプキー）に追従し、目・口のパーツをこのメッシュ一つに組み立てます',
    '편집 시작': '編集開始',
    '편집할 프리셋을 고르세요': '編集するプリセットを選んでください',
    '포토샵 Ctrl+T처럼 뷰포트에서 파츠를 옮기고(안쪽 드래그), 크기를 바꾸고(모서리·변), 돌립니다(위 동그라미·바깥). Enter 확정 · Esc 취소. Shift = 비율 유지/15° 단위, Alt = 기준점 기준 크기': 'PhotoshopのCtrl+Tのように、ビューポートでパーツを移動（内側ドラッグ）、サイズ変更（角・辺）、回転（上の丸・外側）します。Enter 確定 · Esc キャンセル。Shift＝比率維持／15°単位、Alt＝基準点基準のサイズ',
    '폴더': 'フォルダー',
    '폴더 안 파츠': 'フォルダー内のパーツ',
    '폴더 이름': 'フォルダー名',
    '표시': '表示',
    '표정 저장 · 적용': '表情の保存・適用',
    '표정 칸 피커에서 지금 고른 칸을 이 모음의 입으로 지정합니다': '表情セルピッカーで今選んでいるセルをこの母音の口に指定します',
    '표정 칸마다 닫힘/반/열림 칸 시퀀스를 번갈아 씁니다': '表情のセルごとに閉じ／半開き／開きのセルシーケンスを交互に使います',
    '표정 칸을 고른 뒤 + 로 시퀀스 추가, 또는 마법봉으로 위아래 자동 생성': '表情のセルを選んで＋でシーケンスを追加、または魔法の杖で上下を自動作成',
    '표정 컨트롤러': '表情コントローラー',
    '표정 프리셋을 적용할 때 이 그룹 포함': '表情プリセットを適用するときにこのグループを含める',
    '프리셋 저장: ': 'プリセット保存：',
    '프리셋 적용 + 키': 'プリセット適用＋キー',
    '프리셋 편집': 'プリセットを編集',
    '프리셋 편집 중: ': 'プリセット編集中：',
    '프리셋을 먼저 저장하세요': '先にプリセットを保存してください',
    '프리셋을 하나 이상 저장하면 만들 수 있습니다': 'プリセットを一つ以上保存すると作成できます',
    '한중일 입력': '日中韓入力',
    '한중일 입력 창(작은 브라우저)을 띄워 이 칸에 글자를 씁니다. 넣으면 이 창의 칸에 바로 들어갑니다': '日中韓入力ウィンドウ（小さなブラウザ）を開いてこの欄に文字を書きます。入力するとこの欄にすぐ入ります',
    '할 일': 'やること',
    '함께 전환되는 폴더: ': '一緒に切り替わるフォルダー：',
    '함께 조절': '一緒に調整',
    '함께 켜져 있는 다른 버전의 Face Shape Key Rig를 끕니다. 두 개가 켜져 있으면 안내 글자·표시가 겹쳐 그려집니다': '同時に有効になっている別バージョンのFace Shape Key Rigを無効にします。二つ有効だと案内文字・表示が重なって描かれます',
    '합성 모드': '合成モード',
    '항상 카메라를 봄': '常にカメラを向く',
    '행 (세로 칸 수)': '行（縦のセル数）',
    '행 따라가기': '行に追従',
    '행 이름': '行の名前',
    '행·열을 바꾼 뒤 칸을 다시 잘라 파츠 번호를 매깁니다': '行・列を変えた後、セルを切り直してパーツ番号を付けます',
    '행을 따라감: ': '行に追従：',
    '현재 립싱크 구간으로 입 칸 키만 다시 굽습니다': '現在のリップシンク区間で口セルのキーだけ再ベイクします',
    '현재 설정대로 모디파이어/노드와 드라이버를 다시 만듭니다': '現在の設定でモディファイアー／ノードとドライバーを作り直します',
    '현재 칸 기준으로 시퀀스 추가': '現在のセル基準でシーケンスを追加',
    "현재 칸 번호에 Constant 키를 삽입합니다. 키는 데칼이 아니라 리그 오브젝트에 들어가므로, 타임라인에서 보려면 리그를 선택하거나 'Only Show Selected'를 끄세요": '現在のセル番号にConstantキーを挿入します。キーはデカールではなくリグオブジェクトに入るので、タイムラインで見るにはリグを選択するか「選択のみ表示」をオフにしてください',
    '현재 프레임에 Constant 키를 넣어 이 프레임부터 표정이 바뀌게 합니다': '現在のフレームにConstantキーを入れて、このフレームから表情が変わるようにします',
    '현재 프레임에 입 키를 넣습니다: 칸(그림)·시퀀스·말하기 (Constant) + 입 전체 배치 (고른 보간). 키는 리그 오브젝트에 들어갑니다': '現在のフレームに口のキーを入れます：セル（絵）・シーケンス・話す（Constant）＋口全体の配置（選んだ補間）。キーはリグオブジェクトに入ります',
    '현재 프레임에 키를 넣습니다': '現在のフレームにキーを入れます',
    '화면': '画面',
    '화면 돌릴 때': '画面を回すとき',
    '회전': '回転',
    '🔑 = 그 표정으로 바꾸고 현재 프레임에 키 넣기': '🔑＝その表情に切り替えて現在のフレームにキーを入れる',
})

_ZH.update({
    "   ('입' 태그의 '입 (시퀀스·립싱크)'가 켜져 있어야 함)": '   （需要开启“嘴”标签的“嘴（序列·口型同步）”）',
    ' (대칭)': ' (对称)',
    ' (상하 반전)': ' (上下翻转)',
    ' (적용됨)': ' (已应用)',
    ' (좌우 반전)': ' (左右翻转)',
    ' 파츠 전체를 좌우 반전해서 사용': ' 的全部部件左右翻转后使用',
    '%d개': '%d个',
    "'%s' 마커를 만들고 '%s' 태그와 연결": '创建标记“%s”并关联标签“%s”',
    "'%s' 마커를 만들고 '%s' 태그와 연결합니다 (태그가 없으면 같이 만듦)": '创建标记“%s”并关联到标签“%s”（标签不存在时一并创建）',
    "'머리카락 위로' 복사본 메시를 와이어로 표시합니다 (머리카락 앞에 있는지 확인용)": '以线框显示“显示在头发上”的副本网格（用于确认是否在头发前方）',
    "'머리카락 위로' 파츠 자리에서 지금 보는 쪽으로 광선을 쏴서 앞머리까지의 거리를 재고, 앞으로 당기는 거리를 그보다 조금 크게 맞춥니다": '从“显示在头发上”部件的位置向当前视角发射射线，测量到刘海的距离，并把前移距离设置得稍大一些',
    "'머리카락 위로' 파츠가 뷰포트 시점을 따라갑니다. 화면을 돌리는 동안에는 가볍게 두었다가 멈추면 바로 맞춥니다 (렌더와는 무관)": '“显示在头发上”部件跟随视口视角。旋转视图时保持轻量，停止后立即对齐（不影响渲染）',
    "'머리카락 위로' 파츠가 뷰포트 시점을 얼마나 자주 따라갈지 (렌더와는 무관)": '“显示在头发上”部件跟随视口视角的频率（不影响渲染）',
    "'머리카락 위로' 파츠가 없거나 시점을 찾지 못했습니다": '没有“显示在头发上”部件，或找不到视角',
    "'머리카락 위로' 파츠를 보는 쪽으로 얼마나 앞당길지. 앞머리보다 앞에 올 만큼만 (너무 크면 옆모습에서 반대쪽 파츠가 머리를 뚫고 보일 수 있음)": '“显示在头发上”部件向观察方向前移的距离。只需移到刘海前方即可（过大时侧面可能看到另一侧部件穿出头部）',
    "'원래 색'이 '바꿀 색'이 되도록 색조·채도·명도 값을 계산해 넣습니다. 비슷한 색의 명암도 같이 따라 바뀜": '计算色相、饱和度、明度，使“原始颜色”变为“目标颜色”。相近颜色的明暗也会随之变化',
    "'찍기'를 누르면 화면이 얼굴 정면(숫자패드 1과 같음)으로 바뀝니다. 얼굴을 클릭하세요": '按“放置”后视图切换为面部正视图（与小键盘1相同）。请点击面部',
    '(고급) 별도 데칼': '（高级）单独贴花',
    '(고급) 별도 입 데칼에 시트 추가': '（高级）为单独的嘴部贴花添加图集',
    '(고급) 선택한 메시를 그대로 캔버스로': '（高级）将所选网格直接用作画布',
    '(예전) 머리카락 위 불투명도': '（旧）头发上方不透明度',
    '(자체 행)': '（自身行）',
    '+ 로 마커를 만들고 이름을 붙이세요 (예: 눈, 입, 볼)': '用 + 创建标记并命名（例如：眼睛、嘴、脸颊）',
    "+ 로 태그를 만들거나, 파츠를 추가할 때 '새 태그'로 바로 만드세요": '用 + 创建标签，或在添加部件时用“新标签”直接创建',
    '+ 로 파츠와 태그를 고르면 그 태그의 기준 마커 위치에 놓입니다': '用 + 选择部件和标签后，会放在该标签的基准标记位置',
    '+ 새 태그': '+ 新标签',
    '0-1, 2-3, 4-5행... 두 행씩 묶어서, 위 칸 = 열림, 아래 칸 = 닫힘 시퀀스를 만듭니다. 두 칸 모두 그림이 있는 곳만 (투명 배경 이미지 기준)': '将第0-1、2-3、4-5行……每两行一组，上格＝张开、下格＝闭合，创建序列。仅限两格都有图的位置（以透明背景图像为准）',
    "1. ②에서 '입' 마커를 입 위치에 찍기": '1. 在②中将“嘴”标记放到嘴的位置',
    '1. 얼굴 메시 선택 → Tab(편집 모드)': '1. 选择面部网格 → Tab（编辑模式）',
    '100% 가까이면 앞뒤가 겹쳐 깜빡일 수 있습니다': '接近100%时前后可能重叠并闪烁',
    '2. ③에서 입 모양 시트 불러오기 (칸마다 입 모양 하나)': '2. 在③中载入嘴型图集（每格一个嘴型）',
    '2. 눈썹 위~턱까지 얼굴 앞면을 면 선택': '2. 面选择从眉毛上方到下巴的面部正面',
    "3. ④에서 + → 그 시트의 입 모양 → 태그 '입' → OK": '3. 在④中 + → 该图集的嘴型 → 标签“嘴” → OK',
    '3. 얼굴 캔버스 만들기': '3. 创建面部画布',
    '4. 여기에 입 시트가 생기면 시퀀스(닫힘·반·열림) → 립싱크 순서로 설정': '4. 此处出现嘴部图集后，按序列（闭合·半开·张开）→ 口型同步的顺序设置',
    'Blender에 연결할 수 없습니다': '无法连接到 Blender',
    'Constant 보간 정리': '整理为常量插值',
    'Constant 정리: 키 %d개': '常量整理：%d 个关键帧',
    'Face Rig 캔버스 파일이 아닙니다': '不是 Face Rig 画布文件',
    'Language / 언어': 'Language / 语言',
    'N패널': 'N 面板',
    'OK를 누르면 정면 뷰로 바뀌고 바로 얼굴을 클릭해 위치를 찍습니다': '按 OK 后切换到正视图，然后直接点击面部指定位置',
    'Tab으로 편집 모드에 들어가 캔버스로 쓸 얼굴 앞면(눈썹 위~턱)을 면 선택한 뒤 다시 누르세요.': '按 Tab 进入编辑模式，面选择用作画布的面部正面（眉毛上方到下巴）后再按一次。',
    'UV %d곳을 이어 붙이고 얼굴에 다시 붙였습니다': '已连接 %d 处 UV 并重新附着到面部',
    'UV Warp 모디파이어': 'UV 扭曲修改器',
    'UV Warp를 이 그룹에만 적용 (얼굴 메시 일부일 때)': '仅对该顶点组应用 UV 扭曲（为面部网格一部分时）',
    'UV 맞춤 완료 (루프 %d개)': 'UV 适配完成（%d 个循环）',
    'UV 맵': 'UV 贴图',
    'UV 여백': 'UV 边距',
    'UV 투영을 알아내지 못했습니다': '无法确定 UV 投影',
    'UV를 첫 칸에 맞추기': '将 UV 适配到第一格',
    '① 얼굴 캔버스': '① 面部画布',
    '① 얼굴 캔버스 · ② 위치 마커 · ③ 스프라이트 시트': '① 面部画布 · ② 位置标记 · ③ 精灵图集',
    '①에서 리그를 먼저 지정하세요': '请先在①中指定绑定',
    '①에서 캔버스와 리그를 먼저 정하세요': '请先在①中设置画布和绑定',
    '② 위치 마커': '② 位置标记',
    '②에서 마커를 먼저 만들면 기준점으로 고를 수 있습니다': '先在②中创建标记，即可选作基准点',
    '③ 스프라이트 시트': '③ 精灵图集',
    '④ 입 파츠에 이 시트 연결': '将此图集关联到④的嘴部部件',
    '④ 캔버스 레이어 (파츠 배치)': '④ 画布图层（部件布局）',
    "④·⑥에서 파츠를 고친 뒤 '저장하고 끝내기'": '在④·⑥中修改部件后点“保存并结束”',
    '④에 입 파츠가 없습니다': '④中没有嘴部部件',
    "④에서 + → 이 시트의 입 모양 → '입' 태그로 입 파츠를 만드세요": '在④中 + → 此图集的嘴型 → 用“嘴”标签创建嘴部部件',
    '④에서 파츠를 배치한 뒤 표정으로 저장합니다': '在④中布置部件后保存为表情',
    '④의 입 파츠가 이 시트를 그리도록 연결합니다 (시퀀스·미리보기·립싱크가 화면에 보이려면 필요)': '关联④的嘴部部件以绘制此图集（序列、预览、口型同步显示所需）',
    '⑤ 표정 프리셋': '⑤ 表情预设',
    '⑥ 입 (시퀀스·립싱크)': '⑥ 嘴（序列·口型同步）',
    '⑥ 입 시퀀스 · 립싱크': '⑥ 嘴部序列 · 口型同步',
    '✓ 확정': '✓ 确定',
    '✕ 취소': '✕ 取消',
    '가리는 메시: %s, 최대 %.4g → 거리 %.4g': '遮挡网格：%s，最大 %.4g → 距离 %.4g',
    '가림 거리 재서 맞추기': '测量遮挡距离并适配',
    '가볍게': '轻量',
    '가운데': '中间',
    '가장자리 잘라내기': '裁去边缘',
    '가장자리 흰 선 제거': '去除边缘白线',
    '각 칸의 테두리를 이만큼 투명하게 잘라냅니다. 칸 모서리의 번호 글씨나 가이드선이 보일 때 사용 (그림이 칸 가운데 있어야 함)': '将每格边框按此宽度裁成透明。格角的编号或参考线露出时使用（图需位于格中央）',
    '감정표현': '情绪表现',
    '감정표현 Plane · 머리 본: %s': '情绪表现平面 · 头部骨骼：%s',
    '감정표현 Plane 만들기': '创建情绪表现平面',
    '감정표현 Plane: 켜면 면이 항상 활성 카메라 정면을 봅니다 (위치는 머리를 따라감). 끄면 머리 정면에 고정': '情绪表现平面：开启后始终正对活动摄像机（位置跟随头部）。关闭则固定在头部正面',
    '감정표현 Plane을 만들었습니다: ': '已创建情绪表现平面：',
    '값 = 캔버스 크기 대비 거리 (0.03 = 3%)': '数值＝相对画布大小的距离（0.03＝3%）',
    '값을 바꾸면 그 단계가 미리보기됩니다': '修改数值会预览该阶段',
    '같은 태그로 같은 자리에 폴더를 하나 더 만들면 둘 중 하나만 켜집니다': '在同一位置用同一标签再建一个文件夹时，两者只会开启一个',
    '격자 (행=표정, 열=입)': '网格（行＝表情，列＝嘴）',
    '격자 이미지 칸 전환 (텍스처 표정·립싱크)': '网格图像格切换（纹理表情·口型同步）',
    '격자로 그린 스프라이트 시트 이미지': '按网格绘制的精灵图集图像',
    '격자로 그린 스프라이트 시트 이미지를 불러와 행·열로 자르고 파츠 번호를 매깁니다': '载入按网格绘制的精灵图集，按行列切分并为部件编号',
    '격자로 그린 시트 이미지를 고르고 행·열 수를 넣으세요 (파일 창 오른쪽)': '选择按网格绘制的图集图像并输入行列数（文件窗口右侧）',
    '겹치기': '叠加',
    '고른 눈의 시선 패드와 칸 값을 그대로 씁니다 (같은 이름의 파츠끼리). 오른쪽 눈을 왼쪽 눈에 연결할 때': '直接使用所选眼睛的视线面板和格值（同名部件之间）。用于将右眼关联到左眼',
    '고른 칸이 키프레임과 상관없이 계속 보입니다. 끝나면 꼭 끄세요': '所选格会无视关键帧持续显示。完成后务必关闭',
    '곱하기': '正片叠底',
    '공통값 (움직이면 이 칸만 저장)': '共用值（修改后仅保存到此格）',
    '괄호 = 그 태그가 지금 쓰는 마커': '括号＝该标签当前使用的标记',
    '그 메시 선택 → Tab (편집 모드)': '选择该网格 → Tab（编辑模式）',
    '그 색으로 칠함 (명암 없어짐)': '用该颜色填充（明暗消失）',
    '그래도 일괄 조절할까요? 크기는 같은 비율로, 위치는 움직인 만큼 바뀝니다.': '仍要批量调整吗？大小按相同比例、位置按移动量变化。',
    '그룹 선택 무시하고 전부 적용': '忽略组选择并全部应用',
    '그룹만 적용': '仅应用组',
    '그림': '图像',
    '그림 가로 크기 (종횡비 고정을 끈 경우)': '图像宽度（关闭宽高比锁定时）',
    '그림 세로 크기 (종횡비 고정을 끈 경우)': '图像高度（关闭宽高比锁定时）',
    '그림 크기': '图像大小',
    '그림에서 찾기': '从图像获取',
    '그림을 데칼 위에서 위아래로 이동 (칸 높이 대비 %)': '在贴花上上下移动图像（相对格高的%）',
    '그림을 데칼 위에서 좌우로 이동 (칸 너비 대비 %)': '在贴花上左右移动图像（相对格宽的%）',
    '그림이 있는 칸만 번호가 매겨져 파츠가 됩니다': '只有有图的格会被编号并成为部件',
    '글자 칸 위에서 실행하세요': '请在文本框上执行',
    '기본': '基础',
    '기본 위치 Y': '默认位置 Y',
    '기본 크기': '默认大小',
    '기존 메시를 캔버스로': '将现有网格用作画布',
    '기준 마커': '基准标记',
    '기준 칸': '基准格',
    '기준: ': '基准：',
    '기준점 ⊕ 드래그 = 기준점 옮기기   ·   Ctrl+Z 한 단계 되돌리기   ·   Enter 확정   ·   Esc 취소   ·   원근 뷰가 되면 확정': '拖动轴心点⊕＝移动轴心   ·   Ctrl+Z 撤销一步   ·   Enter 确定   ·   Esc 取消   ·   切到透视视图时确定',
    '기준점 만들기 · 찍기': '创建与放置基准点',
    '기초 태그 %d개 추가': '已添加 %d 个基础标签',
    '기초 태그 넣기': '添加基础标签',
    '깊이 (패럴랙스)': '深度（视差）',
    '깊이 있는 파츠 %d개': '%d 个有深度的部件',
    '끄기': '关闭',
    '내보내기': '导出',
    '내보내기 실패: ': '导出失败：',
    '내보낸 .zip을 지금 고른 캔버스에 덮어씁니다. 이 캔버스의 기존 파츠·프리셋·입 시트·컨트롤러는 지워집니다 (Ctrl+Z로 되돌릴 수 있음)': '用导出的 .zip 覆盖当前所选画布。此画布现有的部件、预设、嘴部图集和控制器将被删除（可用 Ctrl+Z 撤销）',
    '내보냈습니다 (시트 %d장): ': '已导出（%d 张图集）：',
    '넣었습니다. 창을 닫아도 됩니다': '已输入。可以关闭窗口',
    '누를 메시를 선택하세요': '请选择要压扁的网格',
    '눈 데칼의 UV를 0~1 정사각형 안에 꽉 차게 맞춥니다 (가로세로 비율 유지, 가운데 정렬). 파츠 위치/크기의 기준이 데칼 전체가 됩니다': '将眼部贴花的 UV 铺满 0~1 正方形（保持宽高比，居中）。部件的位置/大小以整个贴花为基准',
    '눈 머티리얼·시선 패드를 지우고 원래 머티리얼로 되돌립니다 (키는 유지)': '删除眼部材质和视线面板并恢复原材质（保留关键帧）',
    '눈 삭제': '删除眼睛',
    '눈·눈썹·입·감정표현 태그와 눈·입 마커를 없는 것만 추가합니다': '仅添加缺少的眼睛、眉毛、嘴、情绪表现标签及眼睛/嘴标记',
    '눈썹 위~턱까지 얼굴 앞면을 면 선택': '面选择从眉毛上方到下巴的面部正面',
    '다른 눈 따라가기': '跟随另一只眼睛',
    '다른 레이어와 같은 칸 번호를 씁니다 (예: 속눈썹이 흰자의 깜빡임 단계를 따라감). 두 시트의 칸 배치가 같아야 합니다': '与其他图层使用相同的格编号（例如睫毛跟随眼白的眨眼阶段）。两个图集的格布局必须相同',
    '다른 버전의 이 애드온이 함께 켜져 있습니다': '此插件的另一个版本也已启用',
    '다른 사본 끄기': '停用其他副本',
    '다른 사본을 껐습니다: ': '已停用其他副本：',
    '다른 스프라이트 시트의 행(표정)을 그대로 따라갑니다. 얼굴 표정과 범고래 표정을 한 번에 바꿀 때 사용': '直接跟随另一个精灵图集的行（表情）。用于同时切换面部和其他（如帽子）的表情',
    '다른 칸 그림': '其他格的图像',
    '다른 칸 그림 연결 모두 비우기': '清除所有格图像关联',
    '다른 칸 그림 연결 모두 비우기 (%d칸)': '清除所有格图像关联（%d 格）',
    '다른 캔버스를 따라가는 캔버스는 지원하지 않습니다': '不支持跟随其他画布的画布',
    '다른 파일로': '换文件',
    '다른 파일로 바꾸기': '替换为其他文件',
    '다시 만들기': '重新创建',
    '다시 불러오기': '重新载入',
    '다시 불러왔습니다: ': '已重新载入：',
    '다시 자르기': '重新切分',
    '다시 찍기': '重新放置',
    '다음 키까지 값 그대로 (뚝 바뀜)': '保持数值直到下一个关键帧（瞬间切换）',
    '단계': '阶段',
    '단계 크기/위치': '阶段大小/位置',
    '단일 입': '单一嘴型',
    '닫힘': '闭合',
    '닫힘/반/열림 단계마다 칸의 크기와 위치를 따로 보정': '为闭合/半开/张开各阶段分别调整格的大小和位置',
    '닷지': '颜色减淡',
    '대사 길이에 맞춰 씬 끝 프레임을 %d로 늘렸습니다': '已按台词长度将场景结束帧延长到 %d',
    '대상 머티리얼에서 바꿀 시트 이미지를 찾지 못했습니다. 이미지 텍스처 노드에 직접 연결해 주세요': '在目标材质中找不到要替换的图集图像。请手动连接到图像纹理节点',
    '대상 본': '目标骨骼',
    '대상 오브젝트': '目标物体',
    '대상의 UV(버텍스 그룹이 있으면 그 부분만)를 좌상단 첫 칸 크기로 맞춥니다': '将目标的 UV（若有顶点组则仅该部分）适配到左上第一格的大小',
    '대상이 메시가 아닙니다': '目标不是网格',
    '대칭': '对称',
    '대칭 복사': '对称复制',
    '대칭 태그가 쓰는 마커는 한쪽만 찍으면 반대쪽이 따라갑니다': '对称标签使用的标记只需放置一侧，另一侧会跟随',
    '더하기 (선형 닷지)': '相加（线性减淡）',
    '덮기': '覆盖',
    '덮어쓰기': '覆盖保存',
    '데칼 UV를 0~1로 펴기': '将贴花 UV 展开到 0~1',
    '데칼 UV를 0~1로 폈습니다': '已将贴花 UV 展开到 0~1',
    '데칼 가운데를 기준으로 반대쪽에 거울처럼 하나 더 그립니다 (땀방울, 빗금 등)': '以贴花中心为基准在另一侧镜像再画一个（汗滴、斜线等）',
    '데칼 머티리얼을 이미지 알파로 투명하게 만듭니다 (Transparent + Mix Shader 삽입, Blended 렌더, 그림자 끄기). 얼굴 본체 머티리얼에는 쓰지 마세요': '用图像 Alpha 让贴花材质透明（插入透明 + 混合着色器，混合渲染，关闭阴影）。请勿用于面部本体材质',
    '데칼 오브젝트용. 머티리얼을 건드리지 않음': '用于贴花物体。不修改材质',
    '데칼 위에서 그림이 보이는 크기. 줄여도 옆 칸이 침범하지 않습니다 (칸 밖은 투명 처리). 투명 배경 설정이 되어 있어야 잘림이 적용됩니다': '图像在贴花上显示的大小。缩小时不会露出相邻格（格外透明）。需设置透明背景才能裁切',
    '도프시트·그래프 에디터에서 선택해 둔 키프레임만 (이 입)': '仅摄影表/曲线编辑器中选中的关键帧（此嘴部）',
    '도프시트·그래프 에디터에서 선택해 둔 키프레임만 (이 파츠)': '仅摄影表/曲线编辑器中选中的关键帧（此部件）',
    '돌리는 동안은 그대로, 멈추면 맞춤 (가장 가벼움)': '旋转时保持不动，停止后对齐（最轻量）',
    '드라이버 방식처럼 모음마다 지정한 입 칸으로 바뀝니다': '与驱动器模式一样，按每个元音切换到指定的嘴型格',
    '드라이버·모디파이어·노드와 리그 값을 모두 제거합니다 (키프레임은 유지)': '删除所有驱动器、修改器、节点和绑定数值（保留关键帧）',
    '디스크의 시트 이미지 파일을 다시 읽습니다 (다른 프로그램에서 고친 뒤 사용)': '从磁盘重新读取图集图像文件（在其他软件中修改后使用）',
    '따라가는 눈의 시선 좌우를 뒤집습니다 (데칼 UV가 좌우 반전되어 있을 때)': '左右翻转所跟随眼睛的视线（贴花 UV 左右镜像时）',
    '따라가는 눈의 파츠를 전부 좌우 반전해서 사용': '将所跟随眼睛的部件全部左右翻转后使用',
    '따라갈 때 좌우 반전': '跟随时左右翻转',
    '띄우기': '偏移',
    '렌더 카메라 기준: 다른 각도로 보면 납작해 보임': '以渲染摄像机为基准：从其他角度看会显得扁平',
    '리그 바인드(ARP 등)할 때 캔버스는 빼고 얼굴 메시만 바인드하세요': '绑定（ARP 等）时请只绑定面部网格，不要包含画布',
    '리그가 설정되지 않았습니다': '未设置绑定',
    '리그를 먼저 지정하세요': '请先指定绑定',
    '립싱크 방식': '口型同步方式',
    '립싱크가 열만 바꿉니다. 표정마다 닫힘/반/열림을 가로로 배치': '口型同步只改变列。每个表情横向排列闭合/半开/张开',
    '립싱크에 사용': '用于口型同步',
    '마스크': '遮罩',
    '마커': '标记',
    '마커 기준': '以标记为基准',
    '마커 삭제': '删除标记',
    '마커 없이 캔버스 가운데 기준': '无标记，以画布中心为基准',
    '마커 찍기': '放置标记',
    '마커 추가': '添加标记',
    '마커 추가 창에서: 이 태그의 기준을 새 마커로': '在添加标记窗口中：将此标签的基准设为新标记',
    '마커 표시': '显示标记',
    '마커를 옮기면 그 마커에 붙은 파츠가 전부 따라갑니다': '移动标记时，附着在该标记上的部件全部跟随',
    '마커를 지웁니다. 이 마커를 쓰던 태그는 얼굴 가운데 기준이 됩니다': '删除标记。使用该标记的标签将改为以面部中心为基准',
    '마커를 찍었습니다: ': '已放置标记：',
    '만든 뒤 한중일 입력 창을 띄워 이름을 씁니다 (Blender에서 한글 입력이 안 될 때)': '创建后打开中日韩输入窗口输入名称（当 Blender 中无法输入中文时）',
    '만들 칸 (행, 열)': '要创建的格（行，列）',
    '만들기': '创建',
    '만들기/갱신': '创建/更新',
    '말하기': '说话',
    '말하기 미리보기': '说话预览',
    '말하는 중': '说话中',
    '말하는 중 소리가 작을 때 (행, 열). -1 = 표정 칸 그대로': '说话时音量较小时（行，列）。-1＝保持表情格',
    '말할 때 쓸 입:': '说话时使用的嘴：',
    '말할 때 입': '说话时的嘴',
    '말할 때 입은 ⑥ 시퀀스·립싱크로 바뀝니다': '说话时的嘴由⑥序列·口型同步切换',
    '말할 때도 이 입 그대로 (뻐끔 안 함)': '说话时也保持此嘴型（不开合）',
    "말할 때도 이 입을 그대로 둡니다 (뻐끔거리지 않음). '나머지 표정 전부'의 입으로 바뀌지 않게 할 때 사용": '说话时也保持此嘴型（不开合）。用于避免切换到“其余所有表情”的嘴型',
    '맞출 UV가 없습니다': '没有可适配的 UV',
    '매 프레임 따라감. 가장 부드럽지만 화면을 돌릴 때마다 씬 전체가 다시 계산되어 무거움': '每帧跟随。最流畅，但每次旋转视图都会重算整个场景，较卡',
    '머리 납작하게 (카메라 기준)': '压扁头部（以摄像机为基准）',
    '머리 납작하게 지우기': '移除压扁头部',
    '머리 납작하게: %d개 메시': '压扁头部：%d 个网格',
    '머리 본을 고르세요': '请选择头部骨骼',
    '머리를 카메라 시선 방향으로 눌러 2D 그림처럼 보이게 합니다 (캔버스 파츠도 같이)': '沿摄像机视线方向压扁头部，使其看起来像 2D 画（画布部件也一起）',
    '머리카락 위 불투명도': '头发上方不透明度',
    '머리카락 위로': '显示在头发上',
    '머리카락 위로 보이는 부분의 진하기 (1 = 완전히 위, 0.5 = 머리카락이 비쳐 보임)': '显示在头发上部分的浓度（1＝完全在上，0.5＝透出头发）',
    '머리카락 위로 보이는 부분의 진하기 (1 = 완전히 위, 0.5 = 머리카락이 비쳐 보임). 가려지지 않은 부분은 그대로': '显示在头发上部分的浓度（1＝完全在上，0.5＝透出头发）。未被遮挡的部分不变',
    '머티리얼 Mapping 노드': '材质映射节点',
    '머티리얼에서 이미지 텍스처를 찾지 못했습니다': '在材质中找不到图像纹理',
    '먼저 ①에서 얼굴 캔버스를 만드세요': '请先在①中创建面部画布',
    '먼저 ③에서 스프라이트 시트를 추가하세요': '请先在③中添加精灵图集',
    '메시 수정 후 정리': '修改网格后整理',
    '메인': '主',
    '메인으로 사용': '用作主序列',
    '면을 더하거나(Shift+클릭) 빼고 적용': '加选（Shift+点击）或减选面后应用',
    '명도': '明度',
    '명암은 두고 색상·채도만 바꿈': '保留明暗，只改变色相和饱和度',
    '몇 초 동안 애드온이 쓰는 시간을 함수별로 잽니다. 누른 뒤 렉이 나는 동작(화면 돌리기·재생·컨트롤러 끌기 등)을 평소처럼 하세요. 결과는 블렌드 파일 옆 fskr_perf.txt와 텍스트 편집기의 FSKR_perf.txt에 저장됩니다': '在几秒内按函数统计插件耗时。按下后照常进行卡顿的操作（旋转视图、播放、拖动控制器等）。结果保存在 .blend 旁的 fskr_perf.txt 和文本编辑器中的 FSKR_perf.txt',
    '모두 보이기': '全部显示',
    "모든 '머리카락 위로' 파츠 공통": '所有“显示在头发上”部件共用',
    '모든 레이어의 깊이(패럴랙스)에 곱하는 값. 0이면 끔': '乘到所有图层深度（视差）上的值。0 为关闭',
    '모든 메시에서 납작하게 모디파이어를 지웁니다': '从所有网格移除压扁修改器',
    '모든 입 칸에 공통으로 적용되는 배치 값 펼치기': '展开所有嘴部格共用的布局值',
    '모든 파츠 보이기': '显示全部部件',
    '모든 파츠를 보이게 합니다': '使全部部件可见',
    '모음 (A/I/U/E/O)': '元音（A/I/U/E/O）',
    '모음별로 다른 칸': '每个元音使用不同的格',
    '모자 얼굴처럼 표정·시선을 따로 움직일 얼굴이 하나 더 있을 때': '当还有另一张需要单独控制表情和视线的脸时（如帽子上的脸）',
    '목록 위에 있을수록 앞에 그려집니다 (▲▼로 순서)': '列表中越靠上越靠前绘制（用 ▲▼ 调整顺序）',
    '목록에 모든 파츠를 보여 줍니다 (보이기는 그대로)': '在列表中显示全部部件（可见性不变）',
    '목록에 이 그룹 파츠만 표시': '列表中只显示此组的部件',
    '목록에서 누르면 바로 그 표정으로 바뀝니다 (키 없음)': '在列表中点击即切换到该表情（不插帧）',
    '미리보기 중 (프레임을 옮기면 꺼짐)': '预览中（移动帧后关闭）',
    '바꾸면 자동 키': '修改时自动插帧',
    '바꿀 색': '目标颜色',
    '바인드에 실패했습니다 (얼굴 메시 모양을 확인하세요)': '绑定失败（请检查面部网格形状）',
    '반': '半开',
    '반 열림': '半开',
    '반 열림 기준': '半开阈值',
    '반전 그림을 둘 칸. 보통 이미지에서 비어 있는 칸': '放置翻转图像的格。通常是图像中的空格',
    '반전 칸 만들기': '创建翻转格',
    '반전 칸 만들기: %d-%d → %d-%d': '创建翻转格：%d-%d → %d-%d',
    '밝게': '变亮',
    '방식': '方式',
    '배치': '布局',
    '배치 (마커 기준)': '布局（以标记为基准）',
    '배치 모드 끄기': '退出布局模式',
    '배치 모드 끔': '已退出布局模式',
    '배치 모드를 끕니다 (ESC 또는 우클릭)': '退出布局模式（ESC 或右键）',
    '배치 모드에서 G로 옮기고 Ctrl로 다른 틀에 붙입니다. 시트 격자는 크기 고정': '布局模式下用 G 移动，按 Ctrl 吸附到其他框。图集网格大小固定',
    '배치 방식': '布局方式',
    '배치 초기화': '重置布局',
    '배치 켜기 (머티리얼 다시 만들기)': '启用布局（重建材质）',
    "배치를 마치면 '프리셋 저장'으로 표정을 만드세요": '布局完成后用“保存预设”创建表情',
    '버텍스 그룹': '顶点组',
    '번': '颜色加深',
    '벌림 3단계': '张口三阶段',
    '범위': '范围',
    '보간': '插值',
    '보간 적용': '应用插值',
    '보간은 태그마다 따로 저장됩니다 (같은 태그 파츠끼리 공유)': '插值按标签分别保存（同标签部件共用）',
    '보이기': '可见',
    '보통': '普通',
    '복제: ': '已复制：',
    '부드럽게': '平滑',
    '부드럽게 가속·감속 (Bezier)': '平滑加速/减速（贝塞尔）',
    '부모': '父级',
    '부모 따라감': '跟随父级',
    '부모 파츠를 고르면 부모의 위치·회전·크기·불투명도·색(HSV·색 덮기)·시선을 그대로 따라갑니다 (자식은 부모 바로 위에 그려짐). 지정할 때 그림은 제자리 유지': '选择父部件后，会跟随父级的位置、旋转、大小、不透明度、颜色（HSV、颜色叠加）和视线（子级绘制在父级正上方）。指定时图像保持原位',
    '부모(%s)의 위치·시선을 따라갑니다': '跟随父级（%s）的位置和视线',
    '부모만 켜면 자식(홍채·하이라이트)은 같이 움직입니다': '只开启父级，子级（虹膜、高光）也会一起移动',
    '부모에게서 물려받음: ': '继承自父级：',
    '분노 마크처럼 얼굴 밖으로 나가는 연출용 평면 (머리 본을 따라감)': '用于怒气符号等超出面部的演出平面（跟随头部骨骼）',
    '불러오기 (덮어쓰기)': '导入（覆盖）',
    '불러오기 실패: ': '导入失败：',
    '불러왔습니다 (시트 %d장). 뷰포트 컨트롤러는 컨트롤러 탭에서 다시 만드세요': '已导入（%d 张图集）。请在控制器标签页重建视口控制器',
    '불투명도': '不透明度',
    '뷰포트 가볍게': '视口轻量化',
    '뷰포트 리그에 표시': '在视口绑定上显示',
    '뷰포트 컨트롤러 (시선 패드)': '视口控制器（视线面板）',
    '뷰포트 컨트롤러 (표정 목록)': '视口控制器（表情列表）',
    '뷰포트 컨트롤러: ': '视口控制器：',
    '뷰포트 컨트롤러의 격자 아래에 이 시퀀스 전용 슬라이더를 추가합니다 (닫힘/반/열림, 단일 입이면 끔/켬). 메인 시퀀스는 항상 표시됩니다': '在视口控制器网格下方添加此序列专用滑块（闭合/半开/张开，单一嘴型则为关/开）。主序列始终显示',
    '뷰포트에 네모 패드와 가운데 십자 손잡이를 만듭니다': '在视口创建方形面板和中心十字手柄',
    '뷰포트에 시선 패드(눈동자 컨트롤러)를 만들거나 다시 만들거나 지웁니다': '在视口中创建、重建或删除视线面板（瞳孔控制器）',
    '뷰포트에 위치 마커를 표시합니다': '在视口显示位置标记',
    '뷰포트에 이 파츠의 시트 격자를 띄웁니다. 노란 테두리를 끌면 칸이 바뀝니다 (칸이 2개 이상인 파츠만)': '在视口显示此部件的图集网格。拖动黄色框切换格（仅限 2 格以上的部件）',
    '뷰포트에 표정 목록 컨트롤러를 만들거나 다시 만들거나 지웁니다. 손잡이를 끌어 표정을 고릅니다': '在视口中创建、重建或删除表情列表控制器。拖动手柄选择表情',
    '뷰포트에서 얼굴 캔버스 위를 클릭해 이 마커의 위치를 정합니다 (정면 뷰 권장)': '在视口中点击面部画布设置此标记位置（建议正视图）',
    '뷰포트에서 자유 변형': '在视口中自由变换',
    '뷰포트에서 자유 변형 (Ctrl+T)': '在视口中自由变换（Ctrl+T）',
    '뷰포트의 Show Overlays를 꺼도 컨트롤러(표정 목록/시선 패드 등)를 보이게 합니다. 화면 표시용이며 렌더에는 나오지 않습니다': '即使关闭视口叠加层也显示控制器（表情列表、视线面板等）。仅用于显示，不会渲染',
    '블렌드 파일 기준 상대 경로로 저장 (폴더째 옮겨도 유지)': '以相对 .blend 的路径保存（整个文件夹移动后仍有效）',
    '비우면 자동 (태그 이름 + 번호)': '留空则自动（标签名 + 编号）',
    '비우면 활성 UV 맵': '留空则使用活动 UV 贴图',
    "비워 두면 '태그 이름 + 번호'로 자동으로 붙습니다": '留空则自动命名为“标签名 + 编号”',
    '빼기': '相减',
    '상대 경로': '相对路径',
    '상하': '上下',
    '새 캔버스 만들기': '创建新画布',
    '새 태그 이름': '新标签名',
    '새 파츠 기본값': '新部件默认值',
    '새 파츠 레이어를 맨 앞에 추가합니다': '在最前面添加新的部件图层',
    '새 파츠 크기 (1 = 캔버스 전체)': '新部件大小（1＝整个画布）',
    '새 파츠를 마커보다 위(+)/아래(-)에 놓기': '将新部件放在标记上方（+）/下方（-）',
    '새 파츠를 이 태그의 가장 아래 파츠 모양으로 클리핑하고 그 바로 위에 놓습니다 (예: 눈동자 → 흰자 태그)': '用此标签最底层部件的形状剪贴新部件，并放在其正上方（例如：瞳孔 → 眼白标签）',
    "새 파츠의 '대칭 복사'를 켠 채로 추가": '添加新部件时开启“对称复制”',
    "새 파츠의 '시선 따라 이동'을 켠 채로 추가": '添加新部件时开启“随视线移动”',
    '새 폴더': '新文件夹',
    '새 폴더 (지금 보이는 파츠로)': '新文件夹（使用当前可见部件）',
    '새 표정': '新表情',
    '색': '颜色',
    '색 덮기': '颜色叠加',
    '색 맞추기': '颜色匹配',
    '색 칸을 누르면 Hex(784343 등)로 입력할 수 있습니다': '点击颜色框可输入十六进制值（如 784343）',
    '색상만': '仅色相',
    '색조': '色相',
    '색조 %+.0f°, 채도 ×%.2f, 명도 ×%.2f': '色相 %+.0f°，饱和度 ×%.2f，明度 ×%.2f',
    '색조 이동 (-0.5~0.5 = -180°~180°)': '色相偏移（-0.5~0.5＝-180°~180°）',
    '색조/채도/명도': '色相/饱和度/明度',
    '색조/채도/명도 계산': '计算色相/饱和度/明度',
    '색조/채도/명도 초기화': '重置色相/饱和度/明度',
    '선택 범위에 지정': '指定到选区',
    '선택 영역 수정': '修改选区',
    '선택 영역 수정 중': '正在修改选区',
    '선택 영역 적용': '应用选区',
    '선택 영역을 복사하지 못했습니다': '无法复制选区',
    '선택된 면이 없습니다': '没有选中的面',
    '선택된 면이 없습니다.': '没有选中的面。',
    '선택된 면이 없습니다. 얼굴 앞면을 면 선택하세요': '没有选中的面。请面选择面部正面',
    '선택한 눈 데칼 메시에 파츠 레이어 합성 머티리얼을 만듭니다': '在所选眼部贴花网格上创建部件图层合成材质',
    '선택한 메시 추가': '添加所选网格',
    '선택한 메시(얼굴·머리카락·모자 등)를 카메라 시선 방향으로 눌러 2D 그림처럼 보이게 합니다. 캔버스 파츠도 같이 눌립니다. 렌더 카메라 기준 연출': '沿摄像机视线方向压扁所选网格（脸、头发、帽子等），使其看起来像 2D 画。画布部件也一起压扁。以渲染摄像机为基准',
    '선택한 오브젝트(입/눈 데칼 등)에 격자 이미지 칸 전환을 추가합니다': '为所选物体（嘴/眼贴花等）添加网格图像格切换',
    '선택한 키프레임만': '仅所选关键帧',
    '선택한 키프레임이 없습니다 (도프시트·그래프 에디터에서 키를 선택하세요)': '没有选中的关键帧（请在摄影表/曲线编辑器中选择关键帧）',
    "선택한 파츠 자리에 폴더를 만들고 그 파츠를 넣습니다. 같은 태그·같은 자리의 폴더끼리는 하나만 켜져서, 예를 들어 '일반 눈'과 '폭소 눈' 폴더를 눈 하나로 전환할 수 있습니다": '在所选部件的位置创建文件夹并放入该部件。同一标签、同一位置的文件夹只会开启一个，例如可将“普通眼”和“大笑眼”文件夹作为一只眼睛切换',
    '선택한 파츠: ': '所选部件：',
    '선택한 파츠를 그림·값·키프레임까지 똑같이 복제해 바로 위에 놓습니다 (이름 뒤에 .001)': '完整复制所选部件（图像、数值、关键帧）并放在其正上方（名称后加 .001）',
    '선형 라이트': '线性光',
    "설정이 바뀌었습니다. '적용'을 눌러 주세요": '设置已更改。请按“应用”',
    '성능 측정': '性能测量',
    '성능 측정 (8초)': '性能测量（8 秒）',
    '세기': '强度',
    '세기는 리그 프로퍼티라 키를 넣을 수 있습니다 (I)': '强度是绑定属性，可以插入关键帧（I）',
    '셰이프 키 슬라이더/패드 컨트롤러 (기존 Face Rig)': '形态键滑块/面板控制器（经典 Face Rig）',
    '소프트 라이트': '柔光',
    "손잡이를 끌면 '시선'을 켠 파츠가 따라 움직입니다": '拖动手柄，开启“视线”的部件会随之移动',
    '순서 바꾸기': '调整顺序',
    '숫자패드 1처럼 얼굴 정면 뷰로 바꾸고 캔버스를 화면 가운데로 (얼굴 방향 설정 반영)': '像小键盘 1 一样切到面部正视图并将画布居中（遵循面部朝向设置）',
    '쉼표로 구분 (예: 기본, 화남, 반짝, 당황)': '以逗号分隔（如：默认, 生气, 闪亮, 慌张）',
    '쉼표로 구분 (예: 닫힘, 반, 열림)': '以逗号分隔（如：闭合, 半开, 张开）',
    '스크린': '滤色',
    '스프라이트 립싱크 다시 굽기': '重新烘焙精灵口型同步',
    '스프라이트 립싱크: %d개 굽기': '精灵口型同步：已烘焙 %d 个',
    '스프라이트 방식 작업 단계': '精灵模式工作步骤',
    '스프라이트 시트 적용: ': '已应用精灵图集：',
    '스프라이트 시트 키를 모두 Constant 보간으로 바꿉니다 (칸 사이가 섞이는 문제 방지)': '将所有精灵图集关键帧改为常量插值（防止格之间混合）',
    '시선 (눈동자 이동)': '视线（瞳孔移动）',
    '시선 따라 이동': '随视线移动',
    '시선 미리보기': '视线预览',
    '시선 이동량 배율 (하이라이트를 덜/더 움직일 때)': '视线移动量倍率（让高光少移动/多移动时）',
    '시선 초기화': '重置视线',
    '시선 추가 이동': '视线额外移动',
    '시선 컨트롤러': '视线控制器',
    '시선 컨트롤러 만들기': '创建视线控制器',
    '시선 패드를 움직이면 이 레이어가 따라 움직입니다 (눈동자, 하이라이트)': '移动视线面板时此图层随之移动（瞳孔、高光）',
    '시선을 따라가는 파츠': '跟随视线的部件',
    '시점 따라가기': '跟随视角',
    '시퀀스': '序列',
    '시퀀스 %d개 생성': '已创建 %d 个序列',
    '시퀀스 %d개를 옮겼습니다': '已移动 %d 个序列',
    '시퀀스 미리보기': '序列预览',
    '시퀀스 삭제': '删除序列',
    '시퀀스(닫힘·반·열림) → 립싱크 순서로 설정하세요': '请按序列（闭合·半开·张开）→ 口型同步的顺序设置',
    '시퀀스:': '序列：',
    "시퀀스를 '%s' 시트로 옮기기 (추천)": '将序列移到“%s”图集（推荐）',
    '시퀀스를 입 파츠의 시트로 옮기기': '将序列移到嘴部部件的图集',
    '시퀀스를 하나 이상 만들면 쓸 수 있습니다': '创建至少一个序列后可用',
    '시트': '图集',
    '시트 불러오기 · 자르기': '载入与切分图集',
    '시트 삭제': '删除图集',
    '시트 이미지를 찾을 수 없습니다': '找不到图集图像',
    '시트 추가': '添加图集',
    '시트를 목록에서 뺍니다 (이미 배치한 파츠는 그대로)': '从列表中移除图集（已布置的部件保持不变）',
    '시트에서 파츠를 고르고 태그를 정해 캔버스에 올립니다. 태그의 기준 마커 위치에 놓입니다': '从图集中选择部件并指定标签后放到画布上。会放在标签的基准标记位置',
    "시트의 '립싱크에 사용'을 켜 주세요": '请开启图集的“用于口型同步”',
    '시트의 칸 하나를 골라 배치': '从图集选一个格进行布置',
    '썸네일에서 칸을 고릅니다': '从缩略图中选择格',
    '쓰는 태그: ': '使用的标签：',
    '씬에 활성 카메라가 없습니다': '场景中没有活动摄像机',
    "씬에 활성 카메라가 없습니다. 카메라를 정한 뒤 '카메라 다시 연결'을 누르세요": '场景中没有活动摄像机。设置摄像机后请按“重新连接摄像机”',
    '아 (행, 열)': 'A（行，列）',
    '아래': '下',
    '아래 레이어들과 섞는 방식 (포토샵 레이어 혼합 모드)': '与下方图层的混合方式（Photoshop 图层混合模式）',
    '아래 버튼 → 머리 본 확인': '下方按钮 → 确认头部骨骼',
    '아래 버튼 누르기': '按下方按钮',
    '아래 버튼 누르기 → 새 캔버스로 전환됨': '按下方按钮 → 切换到新画布',
    '아래 범위': '向下范围',
    '아래 화살표로 끝까지 밀어 보며 맞추세요': '用下方向键推到底并同时调整',
    '아래서': '从下',
    '아마추어': '骨架',
    '안내 글자·표시가 겹쳐 보이는 원인입니다. 하나만 켜 두세요': '这是提示文字/显示重叠的原因。请只启用一个',
    '안쪽 드래그 = 이동 (Shift 45°)   ·   방향키 (Shift ×10)   ·   모서리/변 = 크기 (Shift 비율, Alt 기준점)   ·   바깥/○ = 회전 (Shift 15°)': '内侧拖动＝移动（Shift 45°）   ·   方向键（Shift ×10）   ·   角/边＝缩放（Shift 比例，Alt 轴心）   ·   外侧/○＝旋转（Shift 15°）',
    '앞머리 등 다른 메시에 가려져도 이 파츠가 위로 보입니다 (눈썹 등). 보는 쪽으로 살짝 앞당긴 복사본을 그립니다': '即使被刘海等其他网格遮挡也显示在上方（眉毛等）。绘制一个向观察方向稍微前移的副本',
    '앞으로': '向前',
    '앞으로 당기는 거리': '前移距离',
    '앞쪽 복사본 위치 보기': '显示前方副本位置',
    '애니메이션 키가 들어갈 아마추어(리그)를 고르세요': '请选择存放动画关键帧的骨架（绑定）',
    '어둡게': '变暗',
    '어둡게 물들임': '变暗着色',
    '어떤 표정에서 말하든 이 시퀀스의 입을 씁니다 (전용 시퀀스가 있는 표정만 예외). 메인은 하나만 가능': '无论哪种表情说话都使用此序列的嘴型（有专用序列的表情除外）。主序列只能有一个',
    '어떤 표정에서 말하든 이 입을 씀': '任何表情说话时都用此嘴型',
    '얼굴 가운데': '面部中心',
    '얼굴 메시 선택 → Tab (편집 모드)': '选择面部网格 → Tab（编辑模式）',
    '얼굴 메시 편집 모드에서 눈~입 면을 고르고 누르세요': '在面部网格编辑模式中选择眼到嘴的面后按下',
    '얼굴 메시 편집 모드에서 새로 고른 면으로 캔버스 메시만 바꿉니다. 파츠·마커·프리셋·설정과 그림 위치는 그대로 (같은 정면 UV를 이어서 씀)': '仅用在面部网格编辑模式中新选的面替换画布网格。部件、标记、预设、设置和图像位置保持不变（沿用同一正面 UV）',
    '얼굴 메시를 먼저 선택하세요.': '请先选择面部网格。',
    '얼굴 메시와 분리된, 눈·입이 그려질 메시를 만듭니다': '创建与面部网格分离、用于绘制眼睛和嘴的网格',
    '얼굴 방향': '面部朝向',
    '얼굴 앞에 머리보다 넓은 평면 캔버스를 만들어 머리 본에 붙입니다. 분노 마크처럼 얼굴 밖으로 나가는 감정표현용. 파츠·태그·프리셋은 다른 캔버스와 같이 씁니다': '在面部前方创建比头部更宽的平面画布并附加到头部骨骼。用于怒气符号等超出面部的情绪表现。部件、标签、预设的用法与其他画布相同',
    '얼굴 앞쪽으로 띄우는 거리 (Plane 크기 대비). 앞머리보다 앞에 오게': '向面部前方偏移的距离（相对平面大小）。使其位于刘海前方',
    '얼굴 영역이 지정되지 않았습니다.': '未指定面部区域。',
    '얼굴 움직임에 다시 붙이기': '重新附着到面部运动',
    '얼굴 정면 보기': '查看面部正面',
    '얼굴 캔버스': '面部画布',
    '얼굴 캔버스 (눈·입 파츠)': '面部画布（眼、嘴部件）',
    '얼굴 캔버스 레이어': '面部画布图层',
    '얼굴 캔버스 만들기': '创建面部画布',
    "얼굴 캔버스 입은 ④ 입 파츠의 '배치 (이 칸만)'에서 칸별로 맞추는 것을 권합니다": '面部画布的嘴建议在④嘴部部件的“布局（仅此格）”中逐格调整',
    '얼굴 캔버스 크기의 몇 배로 만들지': '设为面部画布大小的几倍',
    '얼굴 캔버스를 만들었습니다: ': '已创建面部画布：',
    "얼굴 캔버스의 '입' 레이어로 그립니다. 모디파이어/노드를 따로 만들지 않고 캔버스 머티리얼이 이 시트를 읽습니다": '作为面部画布的“嘴”图层绘制。不单独创建修改器/节点，由画布材质读取此图集',
    '얼굴 캔버스의 입 레이어로 그려집니다 (배치는 얼굴 캔버스 패널에서)': '作为面部画布的嘴图层绘制（布局在面部画布面板中）',
    '얼굴 표면보다 얼마나 안쪽(+)/바깥쪽(-)에 있는 것처럼 보일지. 고개를 돌리면 깊은 레이어가 표면보다 덜 따라와 입체감이 생깁니다 (예: 홍채 0.01, 동공 0.02, 하이라이트 -0.005). 자식은 부모 깊이에 더해집니다': '看起来位于面部表面内侧（+）/外侧（-）多远。转头时较深的图层跟随得比表面慢，产生立体感（例：虹膜 0.01，瞳孔 0.02，高光 -0.005）。子级会叠加父级深度',
    '얼굴 표면에서 띄우는 거리 (선택 영역 높이 대비 %). 깜빡이면(Z-fighting) 조금 올리세요': '距面部表面的偏移距离（相对选区高度的%）。若闪烁（Z-fighting）请稍微调高',
    '얼굴(%s) 움직임을 따라가게 붙였습니다': '已附着以跟随面部（%s）运动',
    '얼굴·머리카락·모자 등 같이 눌릴 메시를 선택': '选择要一起压扁的网格（脸、头发、帽子等）',
    '얼굴·머리카락·모자 등 같이 눌릴 메시를 선택하고 누르세요': '选择要一起压扁的网格（脸、头发、帽子等）后按下',
    '얼굴에서 띄우기': '离开面部距离',
    '얼굴이 +X를 봄 (정면 = 숫자패드 3)': '面部朝向 +X（正面＝小键盘 3）',
    '얼굴이 +Y를 봄 (정면 = Ctrl+숫자패드 1)': '面部朝向 +Y（正面＝Ctrl+小键盘 1）',
    '얼굴이 -X를 봄 (정면 = Ctrl+숫자패드 3)': '面部朝向 -X（正面＝Ctrl+小键盘 3）',
    '얼굴이 -Y를 봄 (정면 = 숫자패드 1). Blender 기본': '面部朝向 -Y（正面＝小键盘 1）。Blender 默认',
    '없음': '无',
    '없음 (-1)': '无（-1）',
    '에 (행, 열)': 'E（行，列）',
    '여기 %는 칸 창 안에서 확대라 100%를 넘기면 가장자리가 잘릴 수 있습니다': '此处的%是在格窗口内放大，超过100%时边缘可能被裁切',
    '여기 값은 모든 칸에 똑같이 적용되고, 키·애니메이션은 이 값에 들어갑니다': '此处数值同样应用于所有格，关键帧/动画记录在这些值上',
    '여러 파츠를 골라 속성을 한꺼번에 조절합니다': '选择多个部件并一次性调整属性',
    '열 (가로 칸 수)': '列（横向格数）',
    '열 이름': '列名称',
    '열림': '张开',
    '열림 기준': '张开阈值',
    '영역 수정을 그만두고 캔버스를 다시 보이게 합니다': '停止修改区域并重新显示画布',
    '옆모습일수록 더': '越侧面越强',
    '옆모습일수록 더 누르기 (0 = 각도와 상관없이 같게)': '越接近侧面压得越扁（0＝与角度无关）',
    "예전 '반전 칸 만들기'로 다른 칸 그림을 가져다 쓰던 칸을 모두 원래 칸으로 되돌립니다 (그 칸의 크기·위치도 지움)": '将所有通过旧版“创建翻转格”借用其他格图像的格恢复原样（同时清除其大小/位置）',
    '오 (행, 열)': 'O（行，列）',
    '오디오 립싱크': '音频口型同步',
    '오디오 립싱크를 굽을 때 이 시트의 열(입)에도 키를 넣습니다': '烘焙音频口型同步时也为此图集的列（嘴）插入关键帧',
    '오른쪽': '右',
    '오른쪽 범위': '向右范围',
    '오른쪽에서': '从右',
    '오버레이': '叠加',
    '오버레이가 아직 없습니다': '尚无叠加副本',
    '완료': '完成',
    '왼쪽': '左',
    '왼쪽 범위': '向左范围',
    '왼쪽에서': '从左',
    '우 (행, 열)': 'U（行，列）',
    '움직이는 범위 (끝까지 밀었을 때)': '移动范围（推到底时）',
    '움직임': '运动',
    '원근 뷰가 되어 자유 변형을 확정하고 끝냈습니다': '已切换到透视视图，自由变换已确定并结束',
    '원래 색': '原始颜色',
    '원래 색: #%02X%02X%02X': '原始颜色：#%02X%02X%02X',
    "원래 색이 무채색이라 색조를 바꿀 수 없습니다 (색 덮기 '색상만'을 쓰세요)": '原始颜色为无彩色，无法改变色相（请使用颜色叠加的“仅色相”）',
    '원본 칸: ': '源格：',
    '원본과 다른 칸을 고르세요': '请选择与源格不同的格',
    '위': '上',
    "위 '배치'는 이 값 + 칸별 보정입니다": '上方“布局”＝这些值 + 逐格修正',
    '위 범위': '向上范围',
    '위가 앞 (위에 있을수록 앞에 그려짐)': '上方在前（越靠上越靠前绘制）',
    '위아래 같게': '上下相同',
    '위아래 시퀀스 자동 생성': '自动生成上下序列',
    '위에 있을수록 앞에 그려집니다': '越靠上越靠前绘制',
    '위에서': '从上',
    '위쪽 칸별 크기/위치와 같은 값': '与上方逐格大小/位置相同的值',
    '위치': '位置',
    '위치 0, 크기 1, 회전 0, 불투명도 1로 되돌립니다': '重置为位置 0、大小 1、旋转 0、不透明度 1',
    '위치 X': '位置 X',
    '위치 Y': '位置 Y',
    '음량으로 닫힘/반 열림/열림 전환': '按音量切换闭合/半开/张开',
    '음소거': '静音',
    '이 (행, 열)': 'I（行，列）',
    '이 값을 모든 칸에': '将此值应用到所有格',
    '이 개방도 이상이면 반 열림': '开度达到此值以上为半开',
    '이 개방도 이상이면 열림': '开度达到此值以上为张开',
    '이 레이어 그림을 데칼 안에서 좌우로 뒤집습니다': '在贴花内左右翻转此图层的图像',
    '이 레이어가 보일 영역. 고른 레이어(예: 흰자)의 지금 칸 모양 안에서만 보입니다': '此图层的可见区域：仅在所选图层（如眼白）当前格的形状内可见',
    '이 레이어로 그릴 입 스프라이트 시트': '此图层绘制的嘴部精灵图集',
    '이 마커 사용': '使用此标记',
    '이 마커를 쓸 태그 (선택 안 해도 됨)': '使用此标记的标签（可不选）',
    '이 시퀀스를 메인으로 사용': '将此序列用作主序列',
    "이 시퀀스의 단계를 지금 바로 보여 줍니다 (키는 넣지 않음). 기준 칸으로 표정이 바뀌며, '끄기'로 말하기를 끕니다": '立即显示此序列的阶段（不插帧）。表情切换到基准格，“关闭”停止说话',
    '이 시트를 그리는 입 파츠가 없습니다 — 미리보기·시퀀스가 화면에 안 보입니다': '没有绘制此图集的嘴部部件 —— 预览和序列不会显示',
    '이 시트의 뷰포트 컨트롤러를 지웁니다 (칸 키는 유지)': '删除此图集的视口控制器（保留格关键帧）',
    '이 시트의 시퀀스를 ④ 입 파츠가 그리는 시트로 옮기고, 이 시트는 지웁니다 (같은 입 그림을 쓰는 시트끼리)': '将此图集的序列移到④嘴部部件绘制的图集，并删除此图集（用于使用相同嘴部图像的图集之间）',
    '이 시트의 이미지를 다른 파일로 바꿉니다. 이 시트에서 올린 파츠와 입 시퀀스도 새 이미지를 씁니다': '将此图集的图像替换为其他文件。来自此图集的部件和嘴部序列也会使用新图像',
    '이 시트의 칸을 뷰포트에서 고르는 격자 패드(+ 말하기 슬라이더)를 드라이버 방식 패널에 만듭니다': '在控制器面板中创建用于在视口选择此图集格的网格面板（+ 说话滑块）',
    "이 입 모양을 지금 바로 보여 줍니다 (키는 넣지 않음). '끄기'로 표정 칸으로 돌아갑니다": '立即显示此嘴型（不插帧）。“关闭”返回表情格',
    '이 입 키 넣기': '为此嘴部插帧',
    '이 입의 모든 키': '此嘴部的所有关键帧',
    '이 입의 위치·크기·회전·불투명도·크롭 키 전부': '此嘴部所有位置、大小、旋转、不透明度、裁剪关键帧',
    '이 입의 크기/위치': '此嘴部的大小/位置',
    '이 칸 %d-%d': '此格 %d-%d',
    '이 칸 = %d-%d 그림': '此格＝%d-%d 的图像',
    '이 칸 배치 되돌리기': '重置此格布局',
    '이 칸 보기': '显示此格',
    '이 칸 전용 값': '此格专用值',
    '이 칸에 그림이 없습니다': '此格没有图像',
    '이 칸에 넣을 글자를 작은 입력 창에서 씁니다 (Blender에서 한글·일본어·중국어 입력이 안 될 때). 엔터 = 넣기, Esc = 취소': '在小输入窗口中输入此框的文字（当 Blender 无法输入中日韩文字时）。Enter＝输入，Esc＝取消',
    '이 칸은 글자를 넣을 수 없습니다': '此框不能输入文字',
    '이 칸을 일괄 조절할 칸으로 체크합니다. 지금 칸의 배치를 바꾸면 체크한 칸들도 같이 바뀝니다 (크기는 같은 비율, 위치·회전은 움직인 만큼)': '勾选此格用于批量调整。修改当前格的布局时已勾选的格也一起变化（大小按相同比例，位置/旋转按移动量）',
    '이 칸을 일괄 조절할 칸으로 체크합니다. 지금 칸의 크기·위치를 바꾸면 체크한 칸들도 같이 바뀝니다 (크기는 같은 비율, 위치는 움직인 만큼)': '勾选此格用于批量调整。修改当前格的大小/位置时已勾选的格也一起变化（大小按相同比例，位置按移动量）',
    '이 칸을 지금 칸으로 만들어 뷰포트에 바로 보여 줍니다 (자동 키가 켜져 있으면 키도 들어감). 배치는 이 칸 기준으로 조절됩니다': '将此格设为当前格并立即在视口显示（开启自动插帧时也会插帧）。布局以此格为基准调整',
    '이 칸을 지금 칸으로 만들어 뷰포트에 바로 보여 줍니다 (자동 키가 켜져 있으면 키도 들어감). 크기·위치는 이 칸 기준으로 조절됩니다': '将此格设为当前格并立即在视口显示（开启自动插帧时也会插帧）。大小/位置以此格为基准调整',
    '이 칸이 표정으로 선택되어 있을 때 (행, 열)': '当此格被选为表情时（行，列）',
    '이 컨트롤러는 크기를 바꿀 수 없습니다 (위치만 옮길 수 있음)': '此控制器无法调整大小（只能移动位置）',
    '이 태그 파츠가 앞머리 등에 가려져도 위로 보이게 (지금 있는 파츠에도 바로 적용)': '让此标签的部件即使被刘海等遮挡也显示在上方（立即应用到现有部件）',
    '이 태그 파츠는 ⑥의 입 시퀀스·립싱크로 칸이 바뀝니다': '此标签的部件通过⑥的嘴部序列·口型同步切换格',
    '이 태그 파츠에 키를 넣을 때 쓸 보간 방법 (위치·크기·회전·불투명도·크롭). 태그마다 따로 저장. 칸(그림) 키는 항상 Constant': '为此标签部件插帧时使用的插值方式（位置、大小、旋转、不透明度、裁剪）。按标签分别保存。格（图像）关键帧始终为常量',
    '이 태그 파츠의 위치 X/Y가 이 마커로부터의 거리가 됩니다': '此标签部件的位置 X/Y 将是相对此标记的偏移',
    '이 탭의 컨트롤러만 배치 모드로: 틀을 선택해 옮길 수 있습니다. 다시 누르거나 ESC/우클릭으로 끕니다': '控制器布局模式：选择框即可移动。再次按下或 ESC/右键退出',
    '이 파츠 키 넣기': '为此部件插帧',
    '이 파츠에 이미 넣은 키 전부(위치·크기·회전·불투명도·크롭)를 지금 고른 보간 방법으로 바꿉니다': '将此部件已有的所有关键帧（位置、大小、旋转、不透明度、裁剪）改为当前选择的插值方式',
    '이 파츠의 모든 키': '此部件的所有关键帧',
    '이 파츠의 스프라이트 시트 (칸 = 파츠의 상태)': '此部件的精灵图集（格＝部件状态）',
    '이 파츠의 위치·크기·회전·불투명도·크롭 키 전부': '此部件所有位置、大小、旋转、不透明度、裁剪关键帧',
    '이 파츠의 지금 값 전부(칸·위치·크기·회전·불투명도·크롭)를 현재 프레임에 키로 넣습니다': '在当前帧为此部件的所有当前值（格、位置、大小、旋转、不透明度、裁剪）插帧',
    '이 폴더 삭제': '删除此文件夹',
    '이 폴더 키 넣기': '为此文件夹插帧',
    '이 폴더로 전환': '切换到此文件夹',
    "이 폴더를 켜고 같은 태그·같은 자리의 다른 폴더는 끕니다 ('바꾸면 자동 키'가 켜져 있으면 키도 넣음)": '开启此文件夹并关闭同一标签、同一位置的其他文件夹（开启“修改时自动插帧”时也会插帧）',
    "이 폴더의 파츠만 보이게 전환합니다 ('바꾸면 자동 키'가 켜져 있으면 키도 넣음)": '切换为仅显示此文件夹的部件（开启“修改时自动插帧”时也会插帧）',
    '이 표정을 적용하고 현재 프레임에 키를 넣습니다 (이 프레임부터 표정이 바뀜)': '应用此表情并在当前帧插帧（从此帧起表情改变）',
    '이 표정일 때만 사용': '仅此表情时使用',
    '이동 배율': '移动倍率',
    '이름': '名称',
    '이름을 정해 새로 만듭니다': '命名后新建',
    '이름을 직접 정하는 마커': '自定义名称的标记',
    '이미 넣은 입 배치 키에 지금 고른 보간 방법을 적용합니다 (선택한 키프레임만 / 이 입의 모든 키)': '将当前选择的插值应用到已有的嘴部布局关键帧（仅所选关键帧 / 此嘴部所有关键帧）',
    '이미 넣은 키에 지금 고른 보간 방법을 적용합니다 (선택한 키프레임만 / 이 파츠의 모든 키)': '将当前选择的插值应用到已有关键帧（仅所选关键帧 / 此部件所有关键帧）',
    '이미 변형된 값이 있는 칸입니다': '此格已有调整过的值',
    "이미 있는 '%s' 마커에 '%s' 태그를 연결합니다": '为已有标记“%s”关联标签“%s”',
    '이미지': '图像',
    '이미지 다시 불러오기': '重新载入图像',
    '이미지 불러오기': '打开图像',
    '이미지 불러오기: ': '已载入图像：',
    '이미지 없음 (썸네일 불가)': '无图像（无法显示缩略图）',
    '이미지 텍스처 앞에 Mapping 노드를 넣어 이동': '在图像纹理前插入映射节点以移动',
    '이미지 파일을 고르세요': '请选择图像文件',
    '이미지를 고르세요': '请选择图像',
    '이미지를 바꿨습니다: ': '已替换图像：',
    '이미지를 찾지 못해 빠졌습니다: ': '因找不到图像而被省略：',
    '이미지를 칸 단위로 잘라 선택 그리드 썸네일을 만듭니다': '将图像按格切分以生成选择网格缩略图',
    '이전/다음 칸': '上一格/下一格',
    '일괄 조절': '批量调整',
    '일괄 조절하기': '进行批量调整',
    '일괄 조절할 칸': '要批量调整的格',
    '일반': '正常',
    '일정한 속도로 변함': '匀速变化',
    '입 (스프라이트 시트)': '嘴（精灵图集）',
    '입 (시퀀스·립싱크)': '嘴（序列·口型同步）',
    '입 모양이 이보다 짧게 바뀌면 앞 모양에 합칩니다. 2 = 애니메이션식 on twos': '嘴型持续短于此值时并入前一个嘴型。2＝动画式“一拍二”',
    '입 벌림 (선택한 구간):': '张嘴程度（所选区间）：',
    '입 스프라이트 시트를 그대로 그림 (시퀀스·립싱크·뷰포트 컨트롤러가 그대로 동작)': '直接绘制嘴部精灵图集（序列、口型同步、视口控制器照常工作）',
    '입 시퀀스': '嘴部序列',
    '입 시퀀스 · 표정 목록 · 시선 패드를 뷰포트에 만듭니다': '在视口创建嘴部序列、表情列表和视线面板',
    '입 시트': '嘴部图集',
    '입 전체 배치': '整体嘴部布局',
    '입 칸을 고르거나 입 배치(위치·크기·회전·불투명도·크롭), 시퀀스 선택·말하기 값을 바꾸면 현재 프레임에 키를 바로 넣습니다 (꺼져 있어도 Blender 자동 키가 켜져 있으면 칸은 삽입)': '选择嘴部格或修改嘴部布局（位置、大小、旋转、不透明度、裁剪）、序列选择、说话值时立即在当前帧插帧（即使关闭，只要 Blender 自动插帧开启，格也会插帧）',
    '입 키 넣기': '为嘴部插帧',
    '입 키를 넣을 때 쓸 보간 방법 (입 전체의 위치·크기·회전·불투명도·크롭). 칸·시퀀스·말하기 키는 항상 Constant': '为嘴部插帧时的插值方式（整体嘴部位置、大小、旋转、不透明度、裁剪）。格、序列、说话关键帧始终为常量',
    '입 파츠 추가 방법': '如何添加嘴部部件',
    "입 파츠는 '%s' 시트를 그리고 있습니다. 옮기면 이 시트는 지워집니다": '嘴部部件正在绘制“%s”图集。移动后此图集将被删除',
    '입 파츠는 지원하지 않습니다': '不支持嘴部部件',
    '입 파츠에 연결': '关联到嘴部部件',
    '입력 창으로 이름 쓰기': '通过输入窗口输入名称',
    '입력 창을 열 수 없습니다': '无法打开输入窗口',
    '자동 (표정 따라)': '自动（跟随表情）',
    '자동 정렬': '自动排列',
    '자동 클리핑': '自动剪贴',
    '자식 펼치기': '展开子级',
    "자식에서 켜면 부모 위에 '추가로' 더 움직임 (배율로 양 조절)": '在子级上开启时，在父级基础上“额外”移动（用倍率调整量）',
    '자유 배치': '自由布局',
    '자유 변형 (Ctrl+T)': '自由变换（Ctrl+T）',
    '자유 변형 시작 실패: ': '自由变换启动失败：',
    '자유 변형이 중단되었습니다 (Undo·파일 열기·파츠 삭제)': '自由变换已中断（撤销、打开文件或删除部件）',
    '자체 칸': '自身格',
    '작게 벌린 칸 (행, 열). -1 = 기준 칸 그대로': '微张格（行，列）。-1＝保持基准格',
    '작업 방식': '工作方式',
    '저장하고 끝내기': '保存并结束',
    '저장하지 않고 끝냅니다 (멈췄던 키프레임을 되살림)': '不保存直接结束（恢复暂停的关键帧）',
    '적용': '应用',
    '적용 (머티리얼 재구성)': '应用（重建材质）',
    '적용할 메시: ': '要应用的网格：',
    '전부 지우기': '全部删除',
    '전체': '全部',
    '전체 배치 (모든 칸 공통)': '整体布局（所有格共用）',
    '전체 보기': '显示全部',
    '전체 보기 (폴더 없이)': '显示全部（无文件夹）',
    '전환': '切换',
    '정렬': '排列',
    '정면 뷰에서 얼굴의 %s 위치를 클릭하세요 · 우클릭/ESC 취소': '在正视图中点击面部的%s位置 · 右键/ESC 取消',
    '종류': '类型',
    '종횡비 고정': '锁定宽高比',
    '종횡비 고정 (이 칸)': '锁定宽高比（此格）',
    '종횡비 고정 중: 세로를 바꾸면 가로도 같은 비율로': '宽高比已锁定：修改高度时宽度按相同比例变化',
    '좌우': '左右',
    '좌우 같게': '左右相同',
    '중간 칸 (행, 열). -1 = 열림 칸 사용': '中间格（行，列）。-1＝使用张开格',
    '중심 다시 잡기': '重新定中心',
    '지금 고른 캔버스의 파츠·태그·마커·시트·표정 프리셋·입 시퀀스·립싱크 설정과 속성값, 시트 이미지(원본 해상도)를 .zip 하나로 저장합니다 (키프레임 제외)': '将当前所选画布的部件、标签、标记、图集、表情预设、嘴部序列、口型同步设置、属性值及图集图像（原始分辨率）保存为一个 .zip（不含关键帧）',
    '지금 보이는 칸의 그림으로 파츠 중심을 다시 계산합니다 (그림 위치는 그대로)': '根据当前可见格的图像重新计算部件中心（图像位置不变）',
    '지금 보이는 파츠 배치(칸·위치·크기·회전·불투명도, 입 칸)를 표정으로 저장합니다': '将当前可见的部件布局（格、位置、大小、旋转、不透明度、嘴部格）保存为表情',
    '지금 보이는 파츠들로 새 폴더를 만듭니다': '用当前可见的部件创建新文件夹',
    '지금 보이는 파츠로 덮어쓰기': '用当前可见部件覆盖',
    '지금 선택된 칸을 기준 칸으로 하는 시퀀스를 추가합니다 (열림 = 기준 칸). 닫힘 칸을 지정해 주세요': '添加以当前所选格为基准格的序列（张开＝基准格）。请指定闭合格',
    '지금 시점에서는 파츠를 가리는 메시가 없습니다 (가려지는 각도에서 다시 눌러 보세요)': '当前视角下没有遮挡部件的网格（请在被遮挡的角度再试）',
    '지금 씬의 활성 카메라를 기준으로 누르게 합니다': '以场景当前的活动摄像机为基准压扁',
    "지금 칸 그림에서 가장 많이 쓰인 색을 '원래 색'으로 넣습니다 (스포이트는 화면 색이라 조명·색 관리 때문에 틀릴 수 있음)": '将当前格图像中使用最多的颜色设为“原始颜色”（吸管读取的是屏幕颜色，可能受光照和色彩管理影响）',
    '지금 칸(빨간 버튼)의 배치를 바꾸면 체크한 칸도 같이 바뀝니다': '修改当前格（红色按钮）的布局时，已勾选的格也一起变化',
    '지금 칸(빨간 버튼)의 크기·위치·반전을 바꾸면 체크한 칸도 같이 바뀝니다': '修改当前格（红色按钮）的大小、位置、翻转时，已勾选的格也一起变化',
    '지금 칸만 종횡비를 고정하거나 풉니다 (칸마다 따로). 일괄 조절로 체크한 칸에도 같이 적용': '仅为当前格锁定或解锁宽高比（逐格独立）。也应用到批量调整中勾选的格',
    '지금 칸에 저장된 크기·위치·반전과 다른 칸 그림 연결을 모두 지우고, 이미지에 그려진 원래 칸으로 되돌립니다 (이미지 파일은 건드리지 않음)': '清除当前格保存的大小、位置、翻转及格图像关联，恢复为图像中绘制的原始格（不修改图像文件）',
    '지금 칸으로 지정': '设为当前格',
    '지금 칸의 그림 크기 (칸마다 따로가 꺼져 있으면 공통)': '当前格的图像大小（关闭“逐格”时为共用）',
    '지금 칸의 그림을 뒤집어서 다른 칸 번호로 씁니다. 이미지에 반전 그림을 따로 그릴 필요가 없습니다': '将当前格的图像翻转后用作另一个格编号。无需在图像中另外绘制翻转图',
    '지금 칸의 그림을 위아래로 뒤집습니다': '上下翻转当前格的图像',
    '지금 칸의 그림을 좌우로 뒤집습니다': '左右翻转当前格的图像',
    '지금 칸의 칸별 배치(위치·크기·회전·불투명도·크롭)를 지워 전체 배치 값으로 되돌립니다 (일괄 조절로 체크한 칸도 같이)': '清除当前格的逐格布局（位置、大小、旋转、不透明度、裁剪），恢复为整体布局值（已勾选的格也一起）',
    '지금 칸의 크기/위치를 공통값으로 만들고 다른 칸의 개별 설정을 모두 지웁니다': '将当前格的大小/位置设为共用值并清除其他格的单独设置',
    "지금 캔버스 영역(면 %d개)을 선택해 두었습니다. 면을 더하거나 빼고 '적용'을 누르세요": '已选中当前画布区域（%d 个面）。加选或减选面后按“应用”',
    '지금 캔버스 영역이 선택되어 있습니다': '当前画布区域已选中',
    '지금 캔버스의 UV 투영을 알아내지 못했습니다': '无法确定当前画布的 UV 投影',
    '지금 파츠 상태를 이 프리셋에 덮어쓰고, 멈췄던 키프레임을 되살립니다': '用当前部件状态覆盖此预设，并恢复暂停的关键帧',
    '지금 폴더를 지금 보이는 파츠들로 덮어씁니다': '用当前可见部件覆盖当前文件夹',
    '지금 폴더를 지웁니다 (파츠는 그대로)': '删除当前文件夹（部件保留）',
    '지우기': '删除',
    '지정 해제 (표정 따라)': '取消指定（跟随表情）',
    '찍기': '放置',
    '차이': '差值',
    '채도': '饱和度',
    '초': '秒',
    '초당 약 12번 따라감 (조금 끊겨 보이지만 가벼움)': '每秒约跟随 12 次（略有卡顿但较轻量）',
    '최소 유지 (프레임)': '最短保持（帧）',
    '추가하고 바로 찍기': '添加后立即放置',
    '취소': '取消',
    '측정 중 (%d초) — 렉이 나는 동작을 해 주세요': '测量中（%d 秒）—— 请进行卡顿的操作',
    '측정 중…': '测量中…',
    '카메라 다시 연결': '重新连接摄像机',
    '카메라 시선 방향으로 머리를 누르는 정도': '沿摄像机视线方向压扁头部的程度',
    '카메라: ': '摄像机：',
    '칸': '格',
    '칸 %d개를 비웠습니다': '已清除 %d 个格',
    '칸 가운데(= 마커 + 위치)를 기준으로 크기·회전': '以格中心（＝标记 + 位置）为基准缩放/旋转',
    '칸 따라가기': '跟随格',
    '칸 배치가 같아야 파츠 번호가 유지됩니다': '格布局相同时部件编号才会保留',
    '칸 번호 버튼 = 그 칸을 뷰포트에 보기 · 체크 = 일괄 조절': '格编号按钮＝在视口显示该格 · 勾选＝批量调整',
    '칸 번호가 범위를 벗어났습니다': '格编号超出范围',
    '칸 비우기': '清除格',
    '칸 비우기로 해제': '用“清除格”解除',
    '칸 수/이미지가 바뀌었습니다. 컨트롤러를 갱신하세요': '格数/图像已更改。请更新控制器',
    '칸 썸네일 격자를 펼쳐 일괄 조절할 칸을 고릅니다': '展开格缩略图网格以选择要批量调整的格',
    '칸 안에 그려진 그림의 가운데를 기준으로 크기·회전': '以格内图像中心为基准缩放/旋转',
    '칸 키프레임': '格关键帧',
    '칸 하나를 표정으로 고르고, 말할 때 입은 모음 또는 시퀀스로 지정합니다': '选择一个格作为表情，说话时的嘴型按元音或序列指定',
    '칸마다 따로': '逐格独立',
    '칸별 배치': '逐格布局',
    '칸은 입 시트(시퀀스·립싱크·뷰포트 컨트롤러)로 바뀝니다': '格由嘴部图集（序列、口型同步、视口控制器）切换',
    '칸을 잘라 파츠 번호를 매기는 중…': '正在切分格并为部件编号…',
    '칸이 2개 이상인 파츠만 표시할 수 있습니다': '仅能显示 2 格以上的部件',
    '칸이 바뀔 오브젝트 (입 데칼, 범고래 얼굴 등)': '切换格的物体（嘴部贴花、帽子上的脸等）',
    '캐릭터 얼굴이 바라보는 축. 캔버스 정면 투영 UV와 마커 찍기 화면 방향의 기준이 됩니다': '角色面部朝向的轴。作为画布正面投影 UV 和标记放置视图方向的基准',
    '캔버스': '画布',
    '캔버스 가장자리 여백 (파츠가 테두리에 잘리지 않게)': '画布边缘留白（避免部件在边缘被裁切）',
    '캔버스 내보내기': '导出画布',
    '캔버스 메시를 직접 고친 뒤(Extrude·정점 이동 등) 누르세요. 늘린 면에 같은 정면 UV를 이어 주고, 얼굴에 다시 붙입니다. 기존 파츠·마커 위치는 그대로': '在直接修改画布网格后（挤出、移动顶点等）按下。为新增的面延续相同的正面 UV，并重新附着到面部。现有部件和标记位置不变',
    '캔버스 불러오기 (덮어쓰기)': '导入画布（覆盖）',
    '캔버스 영역을 바꿨습니다 (면 %d개)': '已更改画布区域（%d 个面）',
    '캔버스 위 위치 (0~1, 정면 기준). 다시 찍거나 숫자로 조절': '画布上的位置（0~1，以正面为准）。重新放置或用数值调整',
    '캔버스 위를 클릭하세요': '请点击画布',
    '캔버스 추가 (모자 얼굴 · 감정표현 Plane)': '添加画布（帽子脸 · 情绪表现平面）',
    '캔버스(%s)를 선택하면 켜집니다': '选中画布（%s）后可用',
    '캔버스가 붙은 얼굴 메시를 찾지 못했습니다': '找不到画布所附着的面部网格',
    '캔버스가 아니라 얼굴 메시(원본)를 편집 모드로 열고 면을 고르세요': '请在编辑模式中打开面部网格（源），而不是画布，然后选择面',
    '캔버스가 얼굴 메시의 최종 모양(아마추어·셰이프 키)을 그대로 따라가게 다시 붙입니다. 리그에 캔버스를 따로 바인드해서 일그러질 때 누르세요 (캔버스의 아마추어 모디파이어는 지워짐)': '重新附着画布，使其直接跟随面部网格的最终形状（骨架、形态键）。当画布被单独绑定到绑定而变形时按下（会删除画布的骨架修改器）',
    '캔버스가 얼굴과 따로 움직일 수 있습니다. 위 버튼으로 다시 붙이세요': '画布可能与面部分离移动。请用上方按钮重新附着',
    '캔버스가 얼굴의 서브디비전 없이 같은 변형(아마추어·셰이프 키)만 따라가게 합니다. 리그를 움직이거나 재생할 때 훨씬 가볍고(얼굴 GPU 서브디비전도 다시 켜짐), 렌더에서는 지금처럼 실제 얼굴 표면에 딱 맞습니다. 뷰포트에서는 파츠가 얼굴에서 아주 살짝 더 떠 보일 수 있습니다': '让画布不经过面部细分、只跟随相同的变形（骨架、形态键）。摆姿势或播放时轻得多（面部 GPU 细分也会重新开启），渲染时仍与真实面部表面贴合。视口中部件可能看起来离面部稍远一点',
    '캔버스는 얼굴을 따라가므로 고르지 않아도 됩니다': '画布会跟随面部，无需选择',
    '캔버스로 쓸 앞면을 면 선택': '面选择用作画布的正面',
    '캔버스로 쓸 얼굴 앞면(눈썹 위~턱)을 면 선택한 뒤 다시 누르세요. (점·선만 선택하면 면이 잡히지 않습니다)': '面选择用作画布的面部正面（眉毛上方到下巴）后再按一次。（只选点/边不会选中面）',
    '캔버스를 만들지 못했습니다': '无法创建画布',
    '캔버스를 얼굴 표면에서 띄우는 거리. 비스듬히 볼 때 피부가 줄무늬처럼 비쳐 보이면(Z-fighting) 조금 올리세요': '画布离开面部表面的距离。斜看时若皮肤以条纹状透出（Z-fighting），请稍微调高',
    "캔버스를 잠시 숨기고 얼굴 메시를 편집 모드로 엽니다. 지금 캔버스 영역이 미리 선택되어 있으니 면을 더하거나 빼고 '적용'을 누르세요": '暂时隐藏画布并以编辑模式打开面部网格。当前画布区域已预先选中，加选或减选面后按“应用”',
    '캔버스를 찾지 못했습니다': '找不到画布',
    '컨트롤러 위치 옮기기 (배치 모드)': '移动控制器位置（布局模式）',
    '컨트롤러가 생기거나 크기가 바뀌면 기본 배치로 다시 쌓습니다. 직접 옮긴 자리를 지키려면 끄세요': '添加或改变控制器大小时重新按默认布局排列。若要保留手动调整的位置请关闭',
    '켜면 아래 범위 = 위 범위 (보통 아래를 조금 더 크게)': '开启时向下范围＝向上范围（通常向下稍大一些）',
    "켜면 아래에서 고른 그룹(태그)만 바꿉니다 ('화난 눈 + 웃는 입'처럼 섞기). 끄면 표정 전체를 바꿉니다": '开启时只改变下方所选的组（标签）（如“生气的眼睛 + 笑的嘴”混搭）。关闭则改变整个表情',
    '켜면 왼쪽 범위 = 오른쪽 범위': '开启时向左范围＝向右范围',
    '켜면 이 눈은 자기 파츠 목록 대신 따라가는 눈의 파츠 전체를 좌우로 뒤집어 씁니다. 왼눈만 세팅하면 됩니다': '开启时此眼睛不使用自己的部件列表，而是将所跟随眼睛的全部部件左右翻转使用。只需设置左眼',
    '켜면 지금 가로세로 비율을 그대로 지킨 채 가로·세로가 같이 커지고 작아집니다. 꺼도 모양은 그대로': '开启时保持当前宽高比，宽度和高度一起缩放。关闭后形状保持不变',
    '켜면 지금 가로세로 비율을 그대로 지킨 채 가로나 세로를 바꿀 때 둘이 같이 커지고 작아집니다 (이 입 칸만)': '开启时保持当前宽高比，修改宽或高时两者一起缩放（仅此嘴部格）',
    '켜면 크기 하나로 가로·세로를 같이, 끄면 따로 조절': '开启时一个大小同时控制宽高，关闭则分别调整',
    '켜면 크기/위치를 칸마다 따로 기억합니다 (손대지 않은 칸은 공통값). 끄면 모든 칸이 공통값을 씁니다': '开启时逐格记住大小/位置（未修改的格用共用值）。关闭时所有格使用共用值',
    '켜면 키프레임을 무시하고 고른 칸을 계속 보여 줍니다 (칸을 골라도 키가 들어가지 않음). 칸별 배치를 조절할 때 켜고, 끝나면 끄세요': '开启时忽略关键帧并持续显示所选格（选择格不会插帧）。调整逐格布局时开启，完成后关闭',
    '켜져 있음': '开启',
    '켜짐': '开启',
    '켜짐/꺼짐은 키·표정 프리셋에 들어갑니다': '开/关会记录到关键帧和表情预设中',
    '크게 벌린 칸 (행, 열). -1 = 반 열림 칸 사용': '大张格（行，列）。-1＝使用半开格',
    '크기 (얼굴 대비)': '大小（相对面部）',
    '크기·위치는 오브젝트를 직접 옮기거나 S로 조절해도 됩니다': '也可以直接移动物体或按 S 缩放来调整大小和位置',
    '크기·회전 기준': '缩放/旋转基准',
    '크기는 같은 비율로, 위치·회전은 움직인 만큼': '大小按相同比例，位置/旋转按移动量',
    '크기는 같은 비율로, 위치는 움직인 만큼': '大小按相同比例，位置按移动量',
    '크롭': '裁剪',
    '크롭 (그림 영역 기준으로 잘라내기)': '裁剪（以图像区域为基准）',
    '클리핑 마스크': '剪贴蒙版',
    '키 넣기': '插入关键帧',
    '키 보간': '关键帧插值',
    '키 삽입': '插入关键帧',
    '키 삽입: ': '已插帧：',
    "키 삽입: '%s' 오브젝트 (프레임 %d)": '已插帧：物体“%s”（第 %d 帧）',
    '키프레임 멈춤': '关键帧已暂停',
    '키프레임은 잠시 멈춰 있고, 키는 들어가지 않습니다': '关键帧已暂停，不会插入关键帧',
    "키프레임을 잠시 멈추고 고른 프리셋(표정)의 파츠를 그대로 고칩니다. 끝나면 '저장하고 끝내기' 또는 '취소'": '暂停关键帧并直接修改所选预设（表情）的部件。完成后点“保存并结束”或“取消”',
    '키프레임을 잠시 멈추고 이 프리셋의 파츠를 고칩니다. 그동안 키는 들어가지 않습니다': '暂停关键帧以修改此预设的部件。期间不会插入关键帧',
    '태그': '标签',
    '태그 (그룹)': '标签（组）',
    '태그 삭제': '删除标签',
    '태그 없음': '无标签',
    '태그 추가': '添加标签',
    "태그를 지웁니다. 이 태그였던 파츠는 '태그 없음'(얼굴 가운데 기준)이 됩니다": '删除标签。原属此标签的部件将变为“无标签”（以面部中心为基准）',
    '탭': '标签页',
    '투명 배경 설정': '设置透明背景',
    '투명 배경 설정 완료 (머티리얼 %d개)': '透明背景设置完成（%d 个材质）',
    '투명 배경 설정을 눌러야 칸 밖이 잘립니다': '需按“设置透明背景”才能裁去格外部分',
    '투명 픽셀 %d개의 색을 채웠습니다': '已填充 %d 个透明像素的颜色',
    '파일에서 스프라이트 시트 이미지를 불러와 바로 적용합니다 (대상 머티리얼의 기존 시트 이미지도 교체)': '从文件载入精灵图集图像并立即应用（同时替换目标材质中的现有图集图像）',
    '파츠 %d개': '%d 个部件',
    '파츠 가장자리에 얇은 흰 선이 보일 때. 투명한 곳에 숨어 있는 흰색을 그림 색으로 채웁니다 (그림·투명도는 그대로). 고친 이미지는 .blend 안에 저장됩니다': '当部件边缘出现细白线时使用。用图像颜色填充隐藏在透明像素中的白色（图像和透明度不变）。修复后的图像保存在 .blend 内',
    '파츠 격자·입·표정 목록·시선 패드를 뷰포트에 만들거나 갱신하거나 정렬하거나 지웁니다': '在视口中创建、更新、排列或删除部件网格、嘴部、表情列表和视线面板',
    '파츠 그룹(태그)을 만듭니다. 기준 마커와 새 파츠의 기본값(대칭·시선·입·크기)을 정합니다': '创建部件组（标签）。设置基准标记和新部件的默认值（对称、视线、嘴、大小）',
    '파츠 그룹. 그 태그의 기준 마커 위치에 놓입니다': '部件组。放置在该标签的基准标记位置',
    '파츠 그림 위에 한 색을 덮습니다 (모양·투명도는 그대로)': '在部件图像上覆盖一种颜色（形状和透明度不变）',
    '파츠 보이기/숨기기. 키를 넣을 수 있고(Constant) 표정 프리셋에도 저장됩니다. 부모를 숨기면 자식도 숨겨집니다': '显示/隐藏部件。可插帧（常量）并保存到表情预设中。隐藏父级时子级也会隐藏',
    '파츠 복제': '复制部件',
    '파츠 삭제': '删除部件',
    '파츠 올리기': '添加部件',
    '파츠 이름': '部件名称',
    '파츠 중심': '部件中心',
    '파츠 키를 넣을 때 쓸 보간 방법 (위치·크기·회전·불투명도·크롭). 칸(그림) 키는 항상 Constant': '为部件插帧时的插值方式（位置、大小、旋转、不透明度、裁剪）。格（图像）关键帧始终为常量',
    '파츠 폴더': '部件文件夹',
    '파츠: ': '部件：',
    '파츠가 없습니다. + 로 흰자부터 추가하세요': '没有部件。请用 + 从眼白开始添加',
    "파츠를 고른 뒤 '부모'를 이 폴더로 바꾸면 들어옵니다": '选择部件后将其“父级”设为此文件夹即可放入',
    '파츠를 놓을 기준점을 추가합니다. 눈·눈썹·입·감정표현을 고르거나 + 로 이름을 직접 정합니다': '添加用于放置部件的基准点。选择眼睛、眉毛、嘴、情绪表现，或用 + 自定义名称',
    '파츠를 묶는 폴더 (그림 없음). 같은 태그·같은 자리의 폴더끼리는 하나만 켜집니다': '用于分组部件的文件夹（无图像）。同一标签、同一位置的文件夹只会开启一个',
    '파츠의 칸·위치·크기·회전·불투명도·크롭이나 시선, 표정을 바꾸면 현재 프레임에 키를 바로 넣습니다': '修改部件的格、位置、大小、旋转、不透明度、裁剪或视线、表情时立即在当前帧插帧',
    '패드를 끝까지 밀어 범위를 확인합니다 (키는 넣지 않음)': '将面板推到底以检查范围（不插帧）',
    '패드를 아래 끝까지 밀었을 때 눈동자가 움직이는 거리 (캔버스 높이 대비)': '面板推到最下方时瞳孔移动的距离（相对画布高度）',
    '패드를 오른쪽 끝까지 밀었을 때 눈동자가 움직이는 거리 (캔버스 폭 대비. 0.03 = 3%)': '面板推到最右侧时瞳孔移动的距离（相对画布宽度，0.03＝3%）',
    '패드를 왼쪽 끝까지 밀었을 때 눈동자가 움직이는 거리 (캔버스 폭 대비. 0.03 = 3%)': '面板推到最左侧时瞳孔移动的距离（相对画布宽度，0.03＝3%）',
    '패드를 위 끝까지 밀었을 때 눈동자가 움직이는 거리 (캔버스 높이 대비)': '面板推到最上方时瞳孔移动的距离（相对画布高度）',
    '패럴랙스 강도': '视差强度',
    '편 캔버스를 원래 모양으로 되돌렸습니다': '已将展平的画布恢复为原始形状',
    '편집 모드': '编辑模式',
    '편집 모드 (키프레임 무시)': '编辑模式（忽略关键帧）',
    '편집 모드 켜짐 (%d-%d 고정)': '编辑模式已开启（固定 %d-%d）',
    "편집 모드에서 고른 얼굴 면을 복사해 살짝 띄운 '얼굴 캔버스'를 만듭니다. 정면 투영 UV, 얼굴과 같은 변형(아마추어·셰이프 키)을 따라가며, 눈·입 파츠를 이 메시 하나에 조립합니다": '复制在编辑模式中所选的面部面，创建稍微抬起的“面部画布”。使用正面投影 UV，跟随与面部相同的变形（骨架、形态键），眼睛和嘴部件都组装在这一个网格上',
    '편집 시작': '开始编辑',
    '편집할 프리셋을 고르세요': '请选择要编辑的预设',
    '포토샵 Ctrl+T처럼 뷰포트에서 파츠를 옮기고(안쪽 드래그), 크기를 바꾸고(모서리·변), 돌립니다(위 동그라미·바깥). Enter 확정 · Esc 취소. Shift = 비율 유지/15° 단위, Alt = 기준점 기준 크기': '类似 Photoshop 的 Ctrl+T：在视口中移动部件（内侧拖动）、缩放（角/边）、旋转（上方圆圈/外侧）。Enter 确定 · Esc 取消。Shift＝保持比例/15° 步进，Alt＝以轴心为基准缩放',
    '폴더': '文件夹',
    '폴더 안 파츠': '文件夹内的部件',
    '폴더 이름': '文件夹名称',
    '표시': '显示',
    '표정 저장 · 적용': '保存与应用表情',
    '표정 칸': '表情格',
    '표정 칸 피커에서 지금 고른 칸을 이 모음의 입으로 지정합니다': '将表情格选择器中当前选中的格指定为此元音的嘴型',
    '표정 칸마다 닫힘/반/열림 칸 시퀀스를 번갈아 씁니다': '每个表情格交替使用闭合/半开/张开的格序列',
    '표정 칸을 고른 뒤 + 로 시퀀스 추가, 또는 마법봉으로 위아래 자동 생성': '选择表情格后按 + 添加序列，或用魔棒自动生成上下序列',
    '표정 컨트롤러': '表情控制器',
    '표정 프리셋을 적용할 때 이 그룹 포함': '应用表情预设时包含此组',
    '프리셋 저장: ': '已保存预设：',
    '프리셋 적용 + 키': '应用预设 + 插帧',
    '프리셋 편집': '编辑预设',
    '프리셋 편집 중: ': '正在编辑预设：',
    '프리셋을 먼저 저장하세요': '请先保存预设',
    '프리셋을 하나 이상 저장하면 만들 수 있습니다': '保存至少一个预设后即可创建',
    '한중일 입력': '中日韩输入',
    '한중일 입력 창(작은 브라우저)을 띄워 이 칸에 글자를 씁니다. 넣으면 이 창의 칸에 바로 들어갑니다': '打开中日韩输入窗口（小浏览器）向此框输入文字。输入后直接填入此框',
    '할 일': '待办',
    '함께 전환되는 폴더: ': '一同切换的文件夹：',
    '함께 조절': '一起调整',
    '함께 켜져 있는 다른 버전의 Face Shape Key Rig를 끕니다. 두 개가 켜져 있으면 안내 글자·표시가 겹쳐 그려집니다': '停用同时启用的另一个版本的 Face Shape Key Rig。两个同时启用时提示文字和显示会重复绘制',
    '합성 모드': '混合模式',
    '항상 카메라를 봄': '始终朝向摄像机',
    '행 (세로 칸 수)': '行（纵向格数）',
    '행 따라가기': '跟随行',
    '행 이름': '行名称',
    '행·열을 바꾼 뒤 칸을 다시 잘라 파츠 번호를 매깁니다': '修改行列后重新切分格并为部件编号',
    '행을 따라감: ': '跟随行：',
    '현재 립싱크 구간으로 입 칸 키만 다시 굽습니다': '仅根据当前口型同步区间重新烘焙嘴部格关键帧',
    '현재 설정대로 모디파이어/노드와 드라이버를 다시 만듭니다': '按当前设置重建修改器/节点和驱动器',
    '현재 칸 기준으로 시퀀스 추가': '以当前格为基准添加序列',
    "현재 칸 번호에 Constant 키를 삽입합니다. 키는 데칼이 아니라 리그 오브젝트에 들어가므로, 타임라인에서 보려면 리그를 선택하거나 'Only Show Selected'를 끄세요": '在当前格编号上插入常量关键帧。关键帧记录在绑定物体而非贴花上，要在时间线中查看请选择绑定或关闭“仅显示所选”',
    '현재 프레임에 Constant 키를 넣어 이 프레임부터 표정이 바뀌게 합니다': '在当前帧插入常量关键帧，使表情从此帧开始改变',
    '현재 프레임에 입 키를 넣습니다: 칸(그림)·시퀀스·말하기 (Constant) + 입 전체 배치 (고른 보간). 키는 리그 오브젝트에 들어갑니다': '在当前帧为嘴部插帧：格（图像）、序列、说话（常量）+ 整体嘴部布局（所选插值）。关键帧记录在绑定物体上',
    '현재 프레임에 키를 넣습니다': '在当前帧插入关键帧',
    '화면': '视图',
    '화면 돌릴 때': '旋转视图时',
    '회전': '旋转',
    '🔑 = 그 표정으로 바꾸고 현재 프레임에 키 넣기': '🔑＝切换到该表情并在当前帧插帧',
})

# 1.0.220: 부모 색 따라가기 토글
_EN.update({
    "부모 색 따라가기": "Follow Parent Color",
    "부모 HSV": "Parent HSV",
    "부모 색 덮기": "Parent Overlay",
    "부모(조상)의 색조·채도·명도 조정을 이 파츠에도 적용합니다. 하이라이트처럼 원래 색을 지켜야 하는 파츠는 끄세요":
        "Applies the parent's (ancestors') hue/saturation/value adjustment to this part too. Turn it off for parts that must keep their own color, such as highlights",
    "부모(조상)의 색 덮기(컬러 오버레이)를 이 파츠에도 적용합니다. 켜면 이 파츠도 부모와 같은 색으로 덮입니다":
        "Applies the parent's (ancestors') color overlay to this part too. When on, this part is covered with the same color as the parent",
})
_JA.update({
    "부모 색 따라가기": "親の色に追従",
    "부모 HSV": "親のHSV",
    "부모 색 덮기": "親のカラーオーバーレイ",
    "부모(조상)의 색조·채도·명도 조정을 이 파츠에도 적용합니다. 하이라이트처럼 원래 색을 지켜야 하는 파츠는 끄세요":
        "親（祖先）の色相・彩度・明度の調整をこのパーツにも適用します。ハイライトのように元の色を保つべきパーツはオフにしてください",
    "부모(조상)의 색 덮기(컬러 오버레이)를 이 파츠에도 적용합니다. 켜면 이 파츠도 부모와 같은 색으로 덮입니다":
        "親（祖先）のカラーオーバーレイをこのパーツにも適用します。オンにするとこのパーツも親と同じ色で覆われます",
})
_ZH.update({
    "부모 색 따라가기": "跟随父级颜色",
    "부모 HSV": "父级 HSV",
    "부모 색 덮기": "父级颜色叠加",
    "부모(조상)의 색조·채도·명도 조정을 이 파츠에도 적용합니다. 하이라이트처럼 원래 색을 지켜야 하는 파츠는 끄세요":
        "将父级（祖先）的色相/饱和度/明度调整也应用到此部件。高光等需要保持原色的部件请关闭",
    "부모(조상)의 색 덮기(컬러 오버레이)를 이 파츠에도 적용합니다. 켜면 이 파츠도 부모와 같은 색으로 덮입니다":
        "将父级（祖先）的颜色叠加也应用到此部件。开启后此部件也会被父级的颜色覆盖",
})

# 1.0.225: Alt+G/R/S 컨트롤러 보호
_EN.update({
    "변형 지우기 (컨트롤러 보호)": "Clear Transform (protect controllers)",
    "선택한 본의 위치/회전/크기를 지웁니다. 캐릭터 본과 함께 선택된 Face Rig 컨트롤러(FP_…)는 그대로 둡니다. 컨트롤러만 선택했을 때는 평소처럼 지웁니다":
        "Clears location/rotation/scale of the selected bones. Face Rig controllers (FP_…) selected together with character bones are left as they are. When only controllers are selected, they are cleared as usual",
})
_JA.update({
    "변형 지우기 (컨트롤러 보호)": "トランスフォームをクリア（コントローラー保護）",
    "선택한 본의 위치/회전/크기를 지웁니다. 캐릭터 본과 함께 선택된 Face Rig 컨트롤러(FP_…)는 그대로 둡니다. 컨트롤러만 선택했을 때는 평소처럼 지웁니다":
        "選択したボーンの位置／回転／スケールをクリアします。キャラクターのボーンと一緒に選択された Face Rig コントローラー（FP_…）はそのままにします。コントローラーだけを選択した場合は通常どおりクリアします",
})
_ZH.update({
    "변형 지우기 (컨트롤러 보호)": "清除变换（保护控制器）",
    "선택한 본의 위치/회전/크기를 지웁니다. 캐릭터 본과 함께 선택된 Face Rig 컨트롤러(FP_…)는 그대로 둡니다. 컨트롤러만 선택했을 때는 평소처럼 지웁니다":
        "清除所选骨骼的位置/旋转/缩放。与角色骨骼一起选中的 Face Rig 控制器（FP_…）保持不变。只选中控制器时照常清除",
})
