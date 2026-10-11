"""한중일 입력 창.

Blender 글자 칸에서 한글·일본어·중국어 조합 입력이 안 될 때, 작은
브라우저 창(Edge/Chrome 앱 창)을 띄워 거기서 입력받는다. 엔터를 누르면
글자가 Blender의 그 칸에 들어가고 창은 닫힌다.

* 애드온 안의 작은 로컬 서버(127.0.0.1, 임의 포트, 토큰 확인)가 창과 통신
* 서버 스레드는 bpy를 건드리지 않고 받은 글자를 큐에만 넣는다. 실제 값 쓰기는
  Blender 메인 스레드의 타이머가 한다.
* 쓰는 곳: N패널 이름 칸 옆 '가' 버튼, 아무 글자 칸에서 우클릭 메뉴
  '한중일 입력 창', 마우스를 칸에 올리고 Ctrl+Shift+Space.
"""

import bpy
import json
import os
import secrets
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .core import _EN, _JA, _ZH, _redraw_ui, _tr

_EN.update({
    "한중일 입력 창": "CJK input window",
    "한중일 입력": "CJK input",
    "이 칸에 넣을 글자를 작은 입력 창에서 씁니다 (Blender에서 한글·일본어·"
    "중국어 입력이 안 될 때). 엔터 = 넣기, Esc = 취소":
        "Type text for this field in a small input window (when Blender's "
        "own CJK input fails). Enter = insert, Esc = cancel",
    "글자 칸 위에서 실행하세요": "Run this over a text field",
    "이 칸은 글자를 넣을 수 없습니다": "This field can't take text",
    "입력 창을 열 수 없습니다": "Couldn't open the input window",
    "엔터 = 넣기 · Esc = 취소": "Enter = insert · Esc = cancel",
    "넣었습니다. 창을 닫아도 됩니다": "Inserted. You can close this window",
    "Blender에 연결할 수 없습니다": "Can't reach Blender",
    "넣기": "Insert",
    "입력 창으로 이름 쓰기": "Name via input window",
    "만든 뒤 한중일 입력 창을 띄워 이름을 씁니다":
        "Opens the CJK input window for the name after creating",
})
_JA.update({"한중일 입력 창": "日中韓入力ウィンドウ", "넣기": "入力",
            "엔터 = 넣기 · Esc = 취소": "Enter = 入力 · Esc = キャンセル"})
_ZH.update({"한중일 입력 창": "中日韩输入窗口", "넣기": "输入",
            "엔터 = 넣기 · Esc = 취소": "Enter = 输入 · Esc = 取消"})

_S = {"srv": None, "port": 0, "token": "", "lock": threading.Lock(),
      "queue": [], "jobs": {}, "seq": 0, "proc": None}

WIN_W, WIN_H = 520, 150     # 입력 창 크기 (CSS 픽셀)

# 데이터블록 종류 → bpy.data 컬렉션 (값 쓸 때 이름으로 다시 찾음: 실행 취소
# 뒤에도 안전하게)
_ID_COLL = {
    'SCENE': "scenes", 'OBJECT': "objects", 'MESH': "meshes",
    'MATERIAL': "materials", 'ARMATURE': "armatures", 'CURVE': "curves",
    'TEXT': "texts", 'IMAGE': "images", 'NODETREE': "node_groups",
    'COLLECTION': "collections", 'CAMERA': "cameras", 'LIGHT': "lights",
    'ACTION': "actions", 'WORLD': "worlds", 'TEXTURE': "textures",
    'FONT': "fonts", 'WINDOWMANAGER': "window_managers",
    'SCREEN': "screens", 'WORKSPACE': "workspaces", 'BRUSH': "brushes",
    'GREASEPENCIL': "grease_pencils", 'SPEAKER': "speakers",
    'SOUND': "sounds", 'LATTICE': "lattices", 'METABALL': "metaballs",
    'PALETTE': "palettes", 'LIGHT_PROBE': "lightprobes",
}

_PAGE = """<!doctype html><html><head><meta charset="utf-8">
<title>%(title)s</title>
<meta name="viewport" content="width=device-width">
<style>
:root{color-scheme:dark}
html,body{margin:0;height:100%%;background:#2b2b2b;color:#ddd;
font-family:"Malgun Gothic","Apple SD Gothic Neo","Noto Sans CJK KR",
"Yu Gothic","Microsoft YaHei",sans-serif}
.w{box-sizing:border-box;padding:14px 16px;height:100%%;display:flex;
flex-direction:column;gap:8px}
.t{font-size:13px;color:#aaa;white-space:nowrap;overflow:hidden;
text-overflow:ellipsis}
.r{display:flex;gap:6px}
input{flex:1;min-width:0;font-size:17px;padding:7px 9px;border-radius:5px;
border:1px solid #555;background:#1d1d1d;color:#fff;outline:none}
input:focus{border-color:#4772b3}
button{font-size:14px;padding:0 14px;border-radius:5px;border:0;
background:#4772b3;color:#fff;cursor:pointer}
.h{font-size:12px;color:#888}
.ok{color:#8fd18f}.err{color:#e88}
</style></head><body><div class="w">
<div class="t">%(label)s</div>
<div class="r"><input id="v" autocomplete="off" spellcheck="false">
<button id="b">%(btn)s</button></div>
<div class="h" id="m">%(hint)s</div></div>
<script>
const J=%(job)s, T=%(token)s, V=%(value)s, W=%(w)s, H=%(h)s;
function place(){try{
 const ow=window.outerWidth-window.innerWidth, oh=window.outerHeight-window.innerHeight;
 const w=W+Math.max(0,ow), h=H+Math.max(0,oh);
 if(Math.abs(window.outerWidth-w)>2||Math.abs(window.outerHeight-h)>2)
  window.resizeTo(w,h);
 const sl=screen.availLeft||0, stp=screen.availTop||0;
 window.moveTo(Math.round(sl+(screen.availWidth-w)/2),
  Math.round(stp+(screen.availHeight-h)/2));}catch(e){}}
place(); window.addEventListener('load',place); setTimeout(place,120);
setInterval(async()=>{if(busy)return;try{const r=await fetch('/alive?j='+J+
 '&t='+T,{cache:'no-store'}); if(r.status===410){busy=true;window.close()}}
 catch(e){}},700);
const v=document.getElementById('v'), m=document.getElementById('m');
v.value=V; v.focus(); v.select();
let busy=false;
function done(){try{window.close()}catch(e){}
 setTimeout(()=>{m.className='h ok';m.textContent=%(okmsg)s},150)}
async function send(cancel){
 if(busy)return; busy=true;
 try{await fetch('/set',{method:'POST',headers:{'Content-Type':
 'application/json'},body:JSON.stringify({job:J,token:T,
 text:v.value,cancel:!!cancel})}); done()}
 catch(e){busy=false;m.className='h err';m.textContent=%(errmsg)s}}
let comp=false;
v.addEventListener('compositionstart',()=>comp=true);
v.addEventListener('compositionend',()=>comp=false);
v.addEventListener('keydown',e=>{
 if(e.key==='Enter'&&!comp&&!e.isComposing){e.preventDefault();send(false)}
 else if(e.key==='Escape'){e.preventDefault();send(true)}});
document.getElementById('b').onclick=()=>send(false);
window.addEventListener('beforeunload',()=>{if(!busy){
 navigator.sendBeacon('/set',JSON.stringify({job:J,token:T,cancel:true}))}});
</script></body></html>"""


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="text/plain; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        from urllib.parse import parse_qs, urlparse
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/alive" and q.get("t", [""])[0] == _S["token"]:
            with _S["lock"]:
                alive = q.get("j", [""])[0] in _S["jobs"]
            self._send(200 if alive else 410, "")
            return
        if u.path != "/i" or q.get("t", [""])[0] != _S["token"]:
            self._send(404, "not found")
            return
        with _S["lock"]:
            job = _S["jobs"].get(q.get("j", [""])[0])
        if job is None:
            self._send(410, "expired")
            return
        self._send(200, _PAGE % job["page"], "text/html; charset=utf-8")

    def do_POST(self):
        if self.path != "/set":
            self._send(404, "")
            return
        try:
            n = int(self.headers.get("Content-Length", "0"))
            d = json.loads(self.rfile.read(min(n, 65536)).decode("utf-8"))
        except Exception:
            self._send(400, "bad")
            return
        if d.get("token") != _S["token"]:
            self._send(403, "")
            return
        with _S["lock"]:
            job = _S["jobs"].pop(str(d.get("job", "")), None)
            if job is not None and not d.get("cancel"):
                _S["queue"].append((job, str(d.get("text", ""))))
        self._send(200, "ok")


def _server():
    if _S["srv"] is not None:
        return _S["port"]
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    srv.daemon_threads = True
    _S["srv"] = srv
    _S["port"] = srv.server_address[1]
    _S["token"] = secrets.token_urlsafe(16)
    th = threading.Thread(target=srv.serve_forever, daemon=True,
                          name="FSKR-IME")
    th.start()
    return _S["port"]


def _browser():
    """주소창 없는 작은 앱 창을 띄울 수 있는 브라우저 (Edge/Chrome 계열)."""
    cands = []
    if sys.platform.startswith("win"):
        for env in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA"):
            base = os.environ.get(env)
            if not base:
                continue
            cands += [os.path.join(base, "Microsoft", "Edge", "Application",
                                   "msedge.exe"),
                      os.path.join(base, "Google", "Chrome", "Application",
                                   "chrome.exe")]
    elif sys.platform == "darwin":
        cands += ["/Applications/Google Chrome.app/Contents/MacOS/"
                  "Google Chrome",
                  "/Applications/Microsoft Edge.app/Contents/MacOS/"
                  "Microsoft Edge",
                  "/Applications/Chromium.app/Contents/MacOS/Chromium"]
    else:
        for n in ("google-chrome", "google-chrome-stable", "chromium",
                  "chromium-browser", "microsoft-edge"):
            p = shutil.which(n)
            if p:
                cands.append(p)
    for p in cands:
        if p and os.path.exists(p):
            return p
    return None


def _profile_dir():
    """입력 창 전용 브라우저 프로필 (평소 쓰는 Edge/Chrome과 분리).

    따로 실행된 브라우저 프로세스라 창 크기·위치 옵션이 항상 적용되고,
    새 입력 창을 열 때 이전 창을 확실히 닫을 수 있다.
    """
    try:
        base = bpy.utils.user_resource('CONFIG')
    except Exception:
        base = None
    if not base:
        import tempfile
        base = tempfile.gettempdir()
    d = os.path.join(base, "fskr_ime_browser")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass
    return d


def _screen_center(w, h):
    """주 화면 가운데에 놓을 창 왼쪽 위 좌표 (DIP). 모르면 None."""
    if not sys.platform.startswith("win"):
        return None
    try:
        import ctypes
        u = ctypes.windll.user32
        sw, sh = u.GetSystemMetrics(0), u.GetSystemMetrics(1)
        dpi = 96
        try:
            dpi = u.GetDpiForSystem() or 96
        except Exception:
            pass
        sc = dpi / 96.0
        # Blender는 DPI 인식 프로세스라 실제 픽셀 → 브라우저 단위(DIP)로
        sw, sh = sw / sc, sh / sc
        return int((sw - w) / 2), int((sh - h) / 2)
    except Exception:
        return None


def kill_prev():
    """열려 있는 이전 입력 창을 닫고 그 입력은 취소."""
    with _S["lock"]:
        _S["jobs"].clear()          # 남은 창은 스스로 닫힘 (/alive = 410)
    p = _S.get("proc")
    _S["proc"] = None
    if p is not None and p.poll() is None:
        try:
            p.terminate()
            try:
                p.wait(timeout=1.5)
            except Exception:
                p.kill()
        except Exception:
            pass


def _launch(url):
    exe = _browser()
    if exe:
        try:
            kw = {}
            if sys.platform.startswith("win"):
                kw["creationflags"] = 0x00000200  # 새 프로세스 그룹
            args = [exe, "--app=" + url,
                    "--user-data-dir=" + _profile_dir(),
                    "--window-size=%d,%d" % (WIN_W + 16, WIN_H + 40),
                    "--no-first-run", "--no-default-browser-check",
                    "--disable-extensions", "--disable-sync",
                    "--disable-features=Translate,msEdgeSidebarV2,"
                    "msUndersideButton,EdgeCollections"]
            pos = _screen_center(WIN_W + 16, WIN_H + 40)
            if pos is not None:
                args.append("--window-position=%d,%d" % pos)
            _S["proc"] = subprocess.Popen(
                args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, close_fds=True, **kw)
            return True
        except Exception as e:
            print("FSKR ime launch:", e)
    try:
        import webbrowser
        return bool(webbrowser.open(url, new=1))
    except Exception:
        return False


def _ref(ptr):
    """값을 쓸 대상을 (데이터블록 종류, 이름, 경로) 로 기억."""
    idb = getattr(ptr, "id_data", None)
    if idb is None:
        return {"ptr": ptr}
    try:
        path = ptr.path_from_id() if ptr != idb else ""
    except Exception:
        return {"ptr": ptr}
    coll = _ID_COLL.get(getattr(idb, "id_type", ""))
    if coll is None:
        return {"ptr": ptr}
    return {"coll": coll, "name": idb.name,
            "lib": getattr(getattr(idb, "library", None), "filepath", None),
            "path": path}


def _resolve(ref):
    if "ptr" in ref:
        return ref["ptr"]
    coll = getattr(bpy.data, ref["coll"], None)
    if coll is None:
        return None
    idb = None
    for x in coll:
        if x.name == ref["name"] and \
                getattr(getattr(x, "library", None), "filepath",
                        None) == ref["lib"]:
            idb = x
            break
    if idb is None:
        return None
    return idb.path_resolve(ref["path"]) if ref["path"] else idb


def _label_for(ptr, attr):
    try:
        rna = ptr.bl_rna.properties[attr]
        nm = rna.name or attr
    except Exception:
        nm = attr
    owner = ""
    try:
        if attr != "name" and hasattr(ptr, "name"):
            owner = str(ptr.name)
    except Exception:
        pass
    nm = _tr(nm)
    return ("%s — %s" % (owner, nm)) if owner and owner != nm else nm


def open_for(ptr, attr, label=None):
    """ptr.attr 에 넣을 글자를 입력 창에서 받는다. 성공하면 ""."""
    try:
        rna = ptr.bl_rna.properties[attr]
    except Exception:
        return _tr("이 칸은 글자를 넣을 수 없습니다")
    if rna.type != 'STRING' or rna.is_readonly:
        return _tr("이 칸은 글자를 넣을 수 없습니다")
    try:
        cur = str(getattr(ptr, attr) or "")
    except Exception:
        cur = ""
    port = _server()
    kill_prev()
    with _S["lock"]:
        _S["seq"] += 1
        jid = "j%d" % _S["seq"]
        title = _tr("한중일 입력 창")
        _S["jobs"][jid] = {
            "ref": _ref(ptr), "attr": attr,
            "maxlen": int(getattr(rna, "length_max", 0) or 0),
            "page": {
                "title": _html(title),
                "label": _html(label or _label_for(ptr, attr)),
                "btn": _html(_tr("넣기")),
                "hint": _html(_tr("엔터 = 넣기 · Esc = 취소")),
                "okmsg": json.dumps(_tr("넣었습니다. 창을 닫아도 됩니다")),
                "errmsg": json.dumps(_tr("Blender에 연결할 수 없습니다")),
                "job": json.dumps(jid), "token": json.dumps(_S["token"]),
                "w": str(WIN_W), "h": str(WIN_H),
                "value": json.dumps(cur),
            }}
    url = "http://127.0.0.1:%d/i?j=%s&t=%s" % (port, jid, _S["token"])
    if not _launch(url):
        with _S["lock"]:
            _S["jobs"].pop(jid, None)
        return _tr("입력 창을 열 수 없습니다")
    if not bpy.app.timers.is_registered(_poll):
        bpy.app.timers.register(_poll, first_interval=0.2, persistent=True)
    return ""


def _html(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _clip_bytes(text, maxlen):
    """Blender 이름 칸 길이(바이트) 안으로 자르기 (글자 중간을 자르지 않음)."""
    if maxlen <= 0:
        return text
    lim = maxlen - 1
    b = text.encode("utf-8")
    if len(b) <= lim:
        return text
    return b[:lim].decode("utf-8", "ignore")


def _poll():
    with _S["lock"]:
        items = list(_S["queue"])
        _S["queue"].clear()
        waiting = bool(_S["jobs"])
    changed = False
    for job, text in items:
        text = text.replace("\r", " ").replace("\n", " ")
        try:
            obj = _resolve(job["ref"])
            if obj is None:
                continue
            setattr(obj, job["attr"], _clip_bytes(text, job["maxlen"]))
            changed = True
        except Exception as e:
            print("FSKR ime set:", e)
    if not waiting:
        # 입력이 끝났으면 전용 브라우저 프로세스도 정리 (창은 이미 닫힘)
        try:
            bpy.app.timers.register(_reap, first_interval=0.8)
        except Exception:
            pass
    if changed:
        try:
            bpy.ops.ed.undo_push(message=_tr("한중일 입력"))
        except Exception:
            pass
        try:
            _redraw_ui(bpy.context)
        except Exception:
            pass
    return 0.2 if waiting or items else None


def _reap():
    with _S["lock"]:
        busy = bool(_S["jobs"])
    if not busy:
        p = _S.get("proc")
        if p is not None and p.poll() is None:
            try:
                p.terminate()
            except Exception:
                pass
        _S["proc"] = None
    return None


def _btn_target(context):
    """마우스 아래(또는 우클릭한) 글자 칸 → (데이터, 속성 이름)."""
    ptr = getattr(context, "button_pointer", None)
    prop = getattr(context, "button_prop", None)
    if ptr is not None and prop is not None:
        return ptr, prop.identifier
    pr = getattr(context, "property", None)
    if pr:
        try:
            owner, path, _idx = pr
            if "." in path or "[" in path:
                head, _, attr = path.rpartition(".")
                return owner.path_resolve(head) if head else owner, attr
            return owner, path
        except Exception:
            pass
    return None, None


class FSKR_OT_ime_input(bpy.types.Operator):
    bl_idname = "fskr.ime_input"
    bl_label = "한중일 입력 창"
    bl_description = ("이 칸에 넣을 글자를 작은 입력 창에서 씁니다 (Blender에서 "
                      "한글·일본어·중국어 입력이 안 될 때). 엔터 = 넣기, "
                      "Esc = 취소")
    bl_options = {'REGISTER', 'INTERNAL'}

    path: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    attr: bpy.props.StringProperty(default="name",
                                   options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, context):
        if self.path:
            try:
                ptr = context.scene.path_resolve(self.path)
            except Exception:
                ptr = None
            attr = self.attr
        else:
            ptr, attr = _btn_target(context)
        if ptr is None or not attr:
            self.report({'WARNING'}, _tr("글자 칸 위에서 실행하세요"))
            return {'CANCELLED'}
        err = open_for(ptr, attr)
        if err:
            self.report({'WARNING'}, err)
            return {'CANCELLED'}
        return {'FINISHED'}


def ime_btn(layout, owner, attr="name"):
    """이름 칸 옆 '가' 버튼. owner는 scene 아래 데이터."""
    try:
        p = owner.path_from_id()
    except Exception:
        return
    if getattr(owner, "id_data", None) is not None and \
            getattr(owner.id_data, "id_type", "") != 'SCENE':
        return
    op = layout.operator("fskr.ime_input", text="", icon='FONTPREVIEW')
    op.path = p
    op.attr = attr


def _menu(self, context):
    ptr, attr = _btn_target(context)
    if ptr is None or not attr:
        return
    try:
        rna = ptr.bl_rna.properties[attr]
    except Exception:
        return
    if rna.type != 'STRING' or rna.is_readonly:
        return
    self.layout.separator()
    self.layout.operator("fskr.ime_input", text=_tr("한중일 입력 창"),
                         icon='FONTPREVIEW')


ime_classes = (FSKR_OT_ime_input,)
_KM = []


def ime_register():
    try:
        bpy.types.UI_MT_button_context_menu.append(_menu)
    except Exception:
        try:
            bpy.types.WM_MT_button_context.append(_menu)
        except Exception:
            pass
    try:
        kc = bpy.context.window_manager.keyconfigs.addon
        if kc:
            km = kc.keymaps.new(name="User Interface", space_type='EMPTY')
            kmi = km.keymap_items.new("fskr.ime_input", 'SPACE', 'PRESS',
                                      ctrl=True, shift=True)
            _KM.append((km, kmi))
    except Exception as e:
        print("FSKR ime keymap:", e)


def ime_unregister():
    for m in ("UI_MT_button_context_menu", "WM_MT_button_context"):
        try:
            getattr(bpy.types, m).remove(_menu)
        except Exception:
            pass
    for km, kmi in _KM:
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            pass
    _KM.clear()
    srv = _S["srv"]
    if srv is not None:
        try:
            srv.shutdown()
            srv.server_close()
        except Exception:
            pass
    _S["srv"] = None
    kill_prev()
    _S["queue"].clear()
    try:
        if bpy.app.timers.is_registered(_poll):
            bpy.app.timers.unregister(_poll)
    except Exception:
        pass
