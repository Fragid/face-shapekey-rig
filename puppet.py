"""메시 파츠 (스파인·라이브2D 방식, 실험 단계).

캔버스 셰이더 안에서 그리던 파츠 하나를 실제 메시 오브젝트로 꺼낸다.

* 메시: 그림(불투명 픽셀)이 있는 곳에 격자 삼각형 메시를 자동으로 만든다.
  이후에는 Blender 편집 모드로 점을 더하고 옮겨 자유롭게 고친다.
* 공간: 캔버스마다 '퍼펫 아마추어' 하나. 아마추어의 로컬 좌표 = 캔버스 UV를
  얼굴 정면 평면으로 펼친 좌표. 메시도 같은 공간에 놓여 뼈로 휜다.
* 얼굴에 붙이기: 지오메트리 노드가 (휜) 평면 좌표 → 캔버스 UV → 얼굴 표면
  (Sample UV Surface)으로 옮긴다. 얼굴 쉐이프키·고개를 그대로 따라감.
* 그림: 메시를 만들 때의 제자리 좌표(fskr_rest)를 저장해 두고, 머티리얼이
  그 좌표로 스프라이트 시트를 읽는다. 편집 모드에서 새로 만든 점도 자동으로
  맞는 그림 위치를 가짐.
* 핀 = 뼈 (부모 = 파츠 뿌리 뼈, Shift로 이어 찍으면 사슬). 웨이트는 거리로
  자동 계산하고 웨이트 페인트로 고친다. IK 컨트롤러는 Blender IK 제약.
"""
import bpy
from mathutils import Matrix, Vector
from bpy_extras import view3d_utils

from .core import _redraw_ui, _tr, _EN, _JA, _ZH
from . import eye as EY


ARM_PREFIX = "FSKR_Puppet_"
GN_REST = "FSKR_PartRest"
GN_STICK = "FSKR_PartStick"
GN_STICK2 = "FSKR_PartStick2"     # 1.0.241: 대칭 복사는 따로 오브젝트
GN_MIRROR = "FSKR_PartMirror"
MOD_MIRROR = "FSKR_Mirror"
MOD_REST = "FSKR_Rest"
MOD_ARM = "FSKR_Bones"
MOD_STICK = "FSKR_Stick"
MAT_PREFIX = "FSKR_PART_"
REST_ATTR = "fskr_rest"
OFFSET_BASE = 0.0004      # 얼굴 표면에서 띄우는 높이 (m)
OFFSET_STEP = 0.00008     # 레이어 한 칸마다 더 띄움 (위 레이어가 앞)


def mesh_on(L):
    return bool(getattr(L, "mesh_on", False))


def part_ob(L):
    nm = getattr(L, "mesh_ob", "")
    return bpy.data.objects.get(nm) if nm else None


def part_ob_r(L):
    """대칭 복사 쪽 메시 오브젝트 (메시를 같이 씀)."""
    nm = L.get("mesh_ob_r", "") if hasattr(L, "get") else ""
    return bpy.data.objects.get(nm) if nm else None


def _p_mpose(st, L):
    """대칭 조종 1 = 복사본 뼈가 원본 뼈를 거울로 따라감, 0 = 따로 (키 가능)."""
    k = EY._pk(L)
    return (k + "_MirrorPose") if k else "fskr_ey_%s_%s_mpose" % (st.uid,
                                                                  L.lid)


def mirror_map(arm):
    """로컬 평면에서 대칭 복사 (UV u → 1-u): p' = M·p + t. (M 2×2, t)."""
    B = arm["fskr_B"]
    b11, b12, b21, b22 = B[0], B[1], B[2], B[3]
    det = b11 * b22 - b12 * b21
    a11, a12, a21, a22 = b22 / det, -b12 / det, -b21 / det, b11 / det
    # M = A·D·B,  D = diag(-1, 1);  t = A·(1, 0)
    m11 = -a11 * b11 + a12 * b21
    m12 = -a11 * b12 + a12 * b22
    m21 = -a21 * b11 + a22 * b21
    m22 = -a21 * b12 + a22 * b22
    return (m11, m12, m21, m22), (a11, a21)


def mirror_pt(arm, x, y):
    (m11, m12, m21, m22), (tx, ty) = mirror_map(arm)
    return m11 * x + m12 * y + tx, m21 * x + m22 * y + ty


def mirror_name(name):
    return name + ".R"


def arm_name(st):
    return ARM_PREFIX + st.uid


def puppet_arm(st):
    return bpy.data.objects.get(arm_name(st))


def _canvas(st):
    ob = bpy.data.objects.get(st.target)
    return ob if ob is not None and ob.type == 'MESH' else None


def _uv_name(ob, st):
    if st.uv_map and st.uv_map in ob.data.uv_layers:
        return st.uv_map
    uvl = ob.data.uv_layers.active
    return uvl.name if uvl is not None else "UVMap"


# ------------------------------------------------------------------
# 캔버스 UV ↔ 정면 평면 (아마추어 로컬 좌표)
# ------------------------------------------------------------------

def _fit_frame(context, ob, uvname):
    """캔버스(평가된 메시)에서 world ≈ O + U·u + V·v 를 최소제곱으로."""
    import numpy as np
    dg = context.evaluated_depsgraph_get()
    oe = ob.evaluated_get(dg)
    me = oe.to_mesh()
    try:
        uvl = me.uv_layers.get(uvname) or me.uv_layers.active
        n = len(me.loops)
        uv = np.empty(n * 2, dtype=np.float64)
        uvl.data.foreach_get("uv", uv)
        uv = uv.reshape(n, 2)
        vi = np.empty(n, dtype=np.int64)
        me.loops.foreach_get("vertex_index", vi)
        co = np.empty(len(me.vertices) * 3, dtype=np.float64)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)[vi]
        mw = np.array(oe.matrix_world)
        co = co @ mw[:3, :3].T + mw[:3, 3]
        keep = (uv[:, 0] >= -0.05) & (uv[:, 0] <= 1.05) & \
            (uv[:, 1] >= -0.05) & (uv[:, 1] <= 1.05)
        if keep.sum() >= 3:
            uv, co = uv[keep], co[keep]
        A = np.c_[np.ones(len(uv)), uv]
        X, *_ = np.linalg.lstsq(A, co, rcond=None)
        # 평균 법선 (오프셋 방향 확인용)
        nrm = np.empty(len(me.vertices) * 3, dtype=np.float64)
        me.vertices.foreach_get("normal", nrm)
        nrm = nrm.reshape(-1, 3).mean(0) @ mw[:3, :3].T
    finally:
        oe.to_mesh_clear()
    O, U, V = Vector(X[0]), Vector(X[1]), Vector(X[2])
    return O, U, V, Vector(nrm)


def _frame_from(O, U, V):
    """아마추어 행렬(직교, 균일 크기)과 로컬(x,y) → UV(u,v) 2×2 변환."""
    k = U.length
    e1 = U.normalized()
    n = U.cross(V).normalized()
    e2 = n.cross(e1).normalized()
    M = Matrix.Identity(4)
    for r in range(3):
        M[r][0], M[r][1], M[r][2], M[r][3] = k * e1[r], k * e2[r], \
            k * n[r], O[r]
    # (x, y) = A·(u, v) / k,  A = [[U·e1, V·e1], [U·e2, V·e2]]
    a11, a12 = U.dot(e1) / k, V.dot(e1) / k
    a21, a22 = U.dot(e2) / k, V.dot(e2) / k
    det = a11 * a22 - a12 * a21
    if abs(det) < 1e-12:
        det = 1e-12
    B = ((a22 / det, -a12 / det), (-a21 / det, a11 / det))   # (u,v)=B·(x,y)
    return M, k, B


def _local_of_uv(arm, u, v):
    B = arm["fskr_B"]
    # B 의 역 = A
    b11, b12, b21, b22 = B[0], B[1], B[2], B[3]
    det = b11 * b22 - b12 * b21
    x = (b22 * u - b12 * v) / det
    y = (-b21 * u + b11 * v) / det
    return x, y


def _tri_verts(ob, uvname):
    """원본 메시에서 UV 가운데 근처의 삼각형 정점 3개 (부모 지정용)."""
    me = ob.data
    uvl = me.uv_layers.get(uvname) or me.uv_layers.active
    best = {}
    for li, lp in enumerate(me.loops):
        u, v = uvl.data[li].uv
        d = (u - 0.5) ** 2 + (v - 0.5) ** 2
        vi = lp.vertex_index
        if vi not in best or d < best[vi][0]:
            best[vi] = (d, u, v)
    near = sorted(best.items(), key=lambda t: t[1][0])[:16]
    if len(near) < 3:
        return None
    a = near[0]
    cand = None
    for i in range(1, len(near)):
        for j in range(i + 1, len(near)):
            b, c = near[i], near[j]
            ar = abs((b[1][1] - a[1][1]) * (c[1][2] - a[1][2])
                     - (c[1][1] - a[1][1]) * (b[1][2] - a[1][2]))
            if cand is None or ar > cand[0]:
                cand = (ar, b[0], c[0])
    if cand is None or cand[0] < 1e-10:
        return None
    return (a[0], cand[1], cand[2])


def ensure_arm(context, s, st):
    """캔버스의 퍼펫 아마추어 (없으면 만듦)."""
    arm = puppet_arm(st)
    if arm is not None:
        return arm
    ob = _canvas(st)
    if ob is None:
        return None
    uvname = _uv_name(ob, st)
    O, U, V, nrm = _fit_frame(context, ob, uvname)
    M, k, B = _frame_from(O, U, V)
    ad = bpy.data.armatures.new(arm_name(st))
    ad.display_type = 'OCTAHEDRAL'
    arm = bpy.data.objects.new(arm_name(st), ad)
    for c in ob.users_collection:
        c.objects.link(arm)
    if not arm.users_collection:
        context.scene.collection.objects.link(arm)
    arm.show_in_front = True
    arm["fskr_k"] = k
    arm["fskr_B"] = (B[0][0], B[0][1], B[1][0], B[1][1])
    n = U.cross(V)
    arm["fskr_nsign"] = 1.0 if n.dot(nrm) >= 0 else -1.0
    arm["fskr_uid"] = st.uid
    # 얼굴을 따라가게: 캔버스 정점 3개에 부모 (고개·표정 따라 이동)
    tv = _tri_verts(ob, uvname)
    if tv is not None:
        arm.parent = ob
        arm.parent_type = 'VERTEX_3'
        arm.parent_vertices = tv
        arm.matrix_parent_inverse = Matrix.Identity(4)
        arm.matrix_basis = Matrix.Identity(4)
        context.view_layer.update()
        T = arm.matrix_world.copy()
        arm.matrix_parent_inverse = T.inverted()
    arm.matrix_basis = M
    context.view_layer.update()
    return arm


# ------------------------------------------------------------------
# 지오메트리 노드
# ------------------------------------------------------------------

def _gn_rest():
    ng = bpy.data.node_groups.get(GN_REST)
    if ng is not None and ng.get("fskr_v") == 1:
        return ng
    if ng is None:
        ng = bpy.data.node_groups.new(GN_REST, 'GeometryNodeTree')
    ng.nodes.clear()
    ng.interface.clear()
    ng.interface.new_socket("Geometry", in_out='INPUT',
                            socket_type='NodeSocketGeometry')
    ng.interface.new_socket("Geometry", in_out='OUTPUT',
                            socket_type='NodeSocketGeometry')
    N, Lk = ng.nodes, ng.links
    gi = N.new('NodeGroupInput')
    go = N.new('NodeGroupOutput')
    sa = N.new('GeometryNodeStoreNamedAttribute')
    sa.data_type = 'FLOAT_VECTOR'
    sa.domain = 'POINT'
    sa.inputs["Name"].default_value = REST_ATTR
    pos = N.new('GeometryNodeInputPosition')
    Lk.new(gi.outputs[0], sa.inputs["Geometry"])
    Lk.new(pos.outputs[0], sa.inputs["Value"])
    Lk.new(sa.outputs[0], go.inputs[0])
    gi.location, pos.location, sa.location, go.location = \
        (-400, 0), (-400, -150), (-150, 0), (100, 0)
    ng["fskr_v"] = 1
    return ng


def _gn_stick():
    """(휜) 평면 좌표 → 캔버스 UV → 얼굴 표면 + 법선 방향 오프셋."""
    ng = bpy.data.node_groups.get(GN_STICK)
    if ng is not None and ng.get("fskr_v") == 1:
        return ng
    if ng is None:
        ng = bpy.data.node_groups.new(GN_STICK, 'GeometryNodeTree')
    ng.nodes.clear()
    ng.interface.clear()
    I = ng.interface
    I.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    I.new_socket("Canvas", in_out='INPUT', socket_type='NodeSocketObject')
    I.new_socket("UV Map", in_out='INPUT', socket_type='NodeSocketString')
    I.new_socket("Row U", in_out='INPUT', socket_type='NodeSocketVector')
    I.new_socket("Row V", in_out='INPUT', socket_type='NodeSocketVector')
    I.new_socket("Offset", in_out='INPUT', socket_type='NodeSocketFloat')
    I.new_socket("Mirror", in_out='INPUT', socket_type='NodeSocketBool')
    I.new_socket("Geometry", in_out='OUTPUT',
                 socket_type='NodeSocketGeometry')
    N, Lk = ng.nodes, ng.links
    gi = N.new('NodeGroupInput')
    gi.location = (-1200, 0)
    go = N.new('NodeGroupOutput')
    go.location = (900, 0)

    def nd(tp, x, y, **kw):
        n = N.new(tp)
        n.location = (x, y)
        for k9, v9 in kw.items():
            setattr(n, k9, v9)
        return n
    # 1) 평면 좌표 → UV
    pos = nd('GeometryNodeInputPosition', -1000, -200)
    du = nd('ShaderNodeVectorMath', -800, -150, operation='DOT_PRODUCT')
    dv = nd('ShaderNodeVectorMath', -800, -300, operation='DOT_PRODUCT')
    Lk.new(pos.outputs[0], du.inputs[0])
    Lk.new(gi.outputs["Row U"], du.inputs[1])
    Lk.new(pos.outputs[0], dv.inputs[0])
    Lk.new(gi.outputs["Row V"], dv.inputs[1])
    cu = nd('ShaderNodeCombineXYZ', -600, -200)
    Lk.new(du.outputs["Value"], cu.inputs[0])
    Lk.new(dv.outputs["Value"], cu.inputs[1])
    sp = nd('GeometryNodeSetPosition', -400, 0)
    Lk.new(gi.outputs["Geometry"], sp.inputs["Geometry"])
    Lk.new(cu.outputs[0], sp.inputs["Position"])
    # 2) 대칭 복사: UV 가운데 기준 u → 1-u (그림도 거울)
    tf = nd('GeometryNodeTransform', -200, -150)
    Lk.new(sp.outputs[0], tf.inputs["Geometry"])
    tf.inputs["Translation"].default_value = (1.0, 0.0, 0.0)
    tf.inputs["Scale"].default_value = (-1.0, 1.0, 1.0)
    ff = nd('GeometryNodeFlipFaces', 0, -150)
    Lk.new(tf.outputs[0], ff.inputs["Mesh"])
    jn = nd('GeometryNodeJoinGeometry', 200, -50)
    Lk.new(ff.outputs[0], jn.inputs[0])
    Lk.new(sp.outputs[0], jn.inputs[0])
    sw = nd('GeometryNodeSwitch', 350, 0, input_type='GEOMETRY')
    Lk.new(gi.outputs["Mirror"], sw.inputs["Switch"])
    Lk.new(sp.outputs[0], sw.inputs["False"])
    Lk.new(jn.outputs[0], sw.inputs["True"])
    # 3) UV → 얼굴 표면
    oi = nd('GeometryNodeObjectInfo', -400, 400, transform_space='RELATIVE')
    Lk.new(gi.outputs["Canvas"], oi.inputs["Object"])
    na = nd('GeometryNodeInputNamedAttribute', -400, 250,
            data_type='FLOAT_VECTOR')
    Lk.new(gi.outputs["UV Map"], na.inputs["Name"])
    cpos = nd('GeometryNodeInputPosition', -400, 150)
    cnrm = nd('GeometryNodeInputNormal', -400, 100)
    p9 = nd('GeometryNodeInputPosition', -200, 50)
    outs = []
    for i9, src in enumerate((cpos, cnrm)):
        su = nd('GeometryNodeSampleUVSurface', 0, 400 - 200 * i9,
                data_type='FLOAT_VECTOR')
        Lk.new(oi.outputs["Geometry"], su.inputs["Mesh"])
        Lk.new(src.outputs[0], su.inputs["Value"])
        Lk.new(na.outputs["Attribute"], su.inputs["Source UV Map"])
        Lk.new(p9.outputs[0], su.inputs["Sample UV"])
        outs.append(su.outputs["Value"])
    nn = nd('ShaderNodeVectorMath', 250, 250, operation='NORMALIZE')
    Lk.new(outs[1], nn.inputs[0])
    sc = nd('ShaderNodeVectorMath', 400, 250, operation='SCALE')
    Lk.new(nn.outputs[0], sc.inputs[0])
    Lk.new(gi.outputs["Offset"], sc.inputs["Scale"])
    ad = nd('ShaderNodeVectorMath', 550, 300, operation='ADD')
    Lk.new(outs[0], ad.inputs[0])
    Lk.new(sc.outputs[0], ad.inputs[1])
    sp2 = nd('GeometryNodeSetPosition', 700, 0)
    Lk.new(sw.outputs[0], sp2.inputs["Geometry"])
    Lk.new(ad.outputs[0], sp2.inputs["Position"])
    Lk.new(sp2.outputs[0], go.inputs[0])
    ng["fskr_v"] = 1
    return ng


def _gn_stick2():
    """평면 좌표 → 캔버스 UV → 얼굴 표면 (+ 보이기). 대칭은 오브젝트로."""
    ng = bpy.data.node_groups.get(GN_STICK2)
    if ng is not None and ng.get("fskr_v") == 1:
        return ng
    if ng is None:
        ng = bpy.data.node_groups.new(GN_STICK2, 'GeometryNodeTree')
    ng.nodes.clear()
    ng.interface.clear()
    I = ng.interface
    I.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    I.new_socket("Canvas", in_out='INPUT', socket_type='NodeSocketObject')
    I.new_socket("UV Map", in_out='INPUT', socket_type='NodeSocketString')
    I.new_socket("Row U", in_out='INPUT', socket_type='NodeSocketVector')
    I.new_socket("Row V", in_out='INPUT', socket_type='NodeSocketVector')
    I.new_socket("Offset", in_out='INPUT', socket_type='NodeSocketFloat')
    sv = I.new_socket("Visible", in_out='INPUT', socket_type='NodeSocketBool')
    sv.default_value = True
    I.new_socket("Geometry", in_out='OUTPUT',
                 socket_type='NodeSocketGeometry')
    N, Lk = ng.nodes, ng.links
    gi = N.new('NodeGroupInput')
    gi.location = (-1200, 0)
    go = N.new('NodeGroupOutput')
    go.location = (1100, 0)

    def nd(tp, x, y, **kw):
        n = N.new(tp)
        n.location = (x, y)
        for k9, v9 in kw.items():
            setattr(n, k9, v9)
        return n
    pos = nd('GeometryNodeInputPosition', -1000, -200)
    du = nd('ShaderNodeVectorMath', -800, -150, operation='DOT_PRODUCT')
    dv = nd('ShaderNodeVectorMath', -800, -300, operation='DOT_PRODUCT')
    Lk.new(pos.outputs[0], du.inputs[0])
    Lk.new(gi.outputs["Row U"], du.inputs[1])
    Lk.new(pos.outputs[0], dv.inputs[0])
    Lk.new(gi.outputs["Row V"], dv.inputs[1])
    cu = nd('ShaderNodeCombineXYZ', -600, -200)
    Lk.new(du.outputs["Value"], cu.inputs[0])
    Lk.new(dv.outputs["Value"], cu.inputs[1])
    sp = nd('GeometryNodeSetPosition', -400, 0)
    Lk.new(gi.outputs["Geometry"], sp.inputs["Geometry"])
    Lk.new(cu.outputs[0], sp.inputs["Position"])
    oi = nd('GeometryNodeObjectInfo', -400, 400, transform_space='RELATIVE')
    Lk.new(gi.outputs["Canvas"], oi.inputs["Object"])
    na = nd('GeometryNodeInputNamedAttribute', -400, 250,
            data_type='FLOAT_VECTOR')
    Lk.new(gi.outputs["UV Map"], na.inputs["Name"])
    cpos = nd('GeometryNodeInputPosition', -400, 150)
    cnrm = nd('GeometryNodeInputNormal', -400, 100)
    p9 = nd('GeometryNodeInputPosition', -200, 50)
    outs = []
    for i9, src in enumerate((cpos, cnrm)):
        su = nd('GeometryNodeSampleUVSurface', 0, 400 - 200 * i9,
                data_type='FLOAT_VECTOR')
        Lk.new(oi.outputs["Geometry"], su.inputs["Mesh"])
        Lk.new(src.outputs[0], su.inputs["Value"])
        Lk.new(na.outputs["Attribute"], su.inputs["Source UV Map"])
        Lk.new(p9.outputs[0], su.inputs["Sample UV"])
        outs.append(su.outputs["Value"])
    nn = nd('ShaderNodeVectorMath', 250, 250, operation='NORMALIZE')
    Lk.new(outs[1], nn.inputs[0])
    sc = nd('ShaderNodeVectorMath', 400, 250, operation='SCALE')
    Lk.new(nn.outputs[0], sc.inputs[0])
    Lk.new(gi.outputs["Offset"], sc.inputs["Scale"])
    ad = nd('ShaderNodeVectorMath', 550, 300, operation='ADD')
    Lk.new(outs[0], ad.inputs[0])
    Lk.new(sc.outputs[0], ad.inputs[1])
    sp2 = nd('GeometryNodeSetPosition', 700, 0)
    Lk.new(sp.outputs[0], sp2.inputs["Geometry"])
    Lk.new(ad.outputs[0], sp2.inputs["Position"])
    sw = nd('GeometryNodeSwitch', 900, 0, input_type='GEOMETRY')
    Lk.new(gi.outputs["Visible"], sw.inputs["Switch"])
    Lk.new(sp2.outputs[0], sw.inputs["True"])
    Lk.new(sw.outputs[0], go.inputs[0])
    ng["fskr_v"] = 1
    return ng


def _gn_mirror():
    """대칭 복사 쪽: 제자리 저장 뒤, 뼈 전에 평면 좌표를 거울로."""
    ng = bpy.data.node_groups.get(GN_MIRROR)
    if ng is not None and ng.get("fskr_v") == 1:
        return ng
    if ng is None:
        ng = bpy.data.node_groups.new(GN_MIRROR, 'GeometryNodeTree')
    ng.nodes.clear()
    ng.interface.clear()
    I = ng.interface
    I.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    I.new_socket("Row X", in_out='INPUT', socket_type='NodeSocketVector')
    I.new_socket("Row Y", in_out='INPUT', socket_type='NodeSocketVector')
    I.new_socket("Offset", in_out='INPUT', socket_type='NodeSocketVector')
    I.new_socket("Geometry", in_out='OUTPUT',
                 socket_type='NodeSocketGeometry')
    N, Lk = ng.nodes, ng.links
    gi = N.new('NodeGroupInput')
    go = N.new('NodeGroupOutput')
    pos = N.new('GeometryNodeInputPosition')
    dx = N.new('ShaderNodeVectorMath')
    dx.operation = 'DOT_PRODUCT'
    dy = N.new('ShaderNodeVectorMath')
    dy.operation = 'DOT_PRODUCT'
    Lk.new(pos.outputs[0], dx.inputs[0])
    Lk.new(gi.outputs["Row X"], dx.inputs[1])
    Lk.new(pos.outputs[0], dy.inputs[0])
    Lk.new(gi.outputs["Row Y"], dy.inputs[1])
    cb = N.new('ShaderNodeCombineXYZ')
    Lk.new(dx.outputs["Value"], cb.inputs[0])
    Lk.new(dy.outputs["Value"], cb.inputs[1])
    ad = N.new('ShaderNodeVectorMath')
    ad.operation = 'ADD'
    Lk.new(cb.outputs[0], ad.inputs[0])
    Lk.new(gi.outputs["Offset"], ad.inputs[1])
    spn = N.new('GeometryNodeSetPosition')
    Lk.new(gi.outputs["Geometry"], spn.inputs["Geometry"])
    Lk.new(ad.outputs[0], spn.inputs["Position"])
    Lk.new(spn.outputs[0], go.inputs[0])
    for i, n in enumerate((gi, pos, dx, dy, cb, ad, spn, go)):
        n.location = (-700 + 180 * i, 0)
    ng["fskr_v"] = 1
    return ng


def _drv_simple(id9, path, expr, pairs):
    """id9.path 에 드라이버 (pairs: [(이름, ID, data_path)])."""
    fc = id9.driver_add(path)
    d = fc.driver
    d.type = 'SCRIPTED'
    for v in list(d.variables):
        d.variables.remove(v)
    for vn, idv, dp in pairs:
        v = d.variables.new()
        v.name = vn
        v.targets[0].id = idv
        v.targets[0].data_path = dp
    d.expression = expr
    return fc


def _mod_input(mod, ident):
    """지오메트리 노드 모디파이어 입력 (5.x: properties.inputs.<id>)."""
    try:
        return getattr(mod.properties.inputs, ident)
    except Exception:
        return None


def _mod_set(mod, ident, value):
    it = _mod_input(mod, ident)
    if it is not None:
        it.value = value
    else:
        mod[ident] = value          # 예전 버전 (idprop)
    # 값만 바꾸면 뷰포트가 다시 계산하지 않을 때가 있어 직접 알림
    try:
        mod.id_data.update_tag()
    except Exception:
        pass


def _mod_path(mod, ident):
    it = _mod_input(mod, ident)
    if it is not None:
        return it.path_from_id("value")
    return 'modifiers["%s"]["%s"]' % (mod.name, ident)


def _sock_id(ng, name):
    for it in ng.interface.items_tree:
        if getattr(it, "in_out", None) == 'INPUT' and it.name == name:
            return it.identifier
    return None


# ------------------------------------------------------------------
# 메시 만들기
# ------------------------------------------------------------------

def _cell_alpha(s, st, L):
    """지금 칸 알파 (H, W) 배열, 칸 공간 0~1 과 같은 방향 (아래 → 위)."""
    import numpy as np
    img = EY._layer_image(s, L)
    cols, rows = EY._layer_grid(s, L)
    idx = max(0, min(cols * rows - 1, int(EY._cell_now(s, st, L))))
    w, h = img.size
    a = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    a = a.reshape(h, w, 4)[:, :, 3]
    r, c = idx // cols, idx % cols
    cw, ch = w / cols, h / rows
    x0, x1 = int(round(c * cw)), int(round((c + 1) * cw))
    y0, y1 = int(round(h - (r + 1) * ch)), int(round(h - r * ch))
    return a[y0:y1, x0:x1].copy()


def grid_mesh(alpha, res):
    """그림이 있는 곳만 덮는 격자 삼각형 메시 (칸 공간 q 좌표)."""
    import numpy as np
    H, W = alpha.shape
    ys, xs = np.nonzero(alpha > 0.02)
    if not len(xs):
        return [], []
    bx0, bx1, by0, by1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    g = max(bx1 - bx0, by1 - by0) / float(max(2, res))
    g = max(g, 2.0)
    nx = int(np.ceil((bx1 - bx0) / g)) + 2
    ny = int(np.ceil((by1 - by0) / g)) + 2
    ox, oy = bx0 - g, by0 - g
    pad = g * 0.5
    keep = {}
    for j in range(ny):
        for i in range(nx):
            px0 = int(max(0, ox + i * g - pad))
            px1 = int(min(W, ox + (i + 1) * g + pad))
            py0 = int(max(0, oy + j * g - pad))
            py1 = int(min(H, oy + (j + 1) * g + pad))
            if px1 <= px0 or py1 <= py0:
                continue
            if alpha[py0:py1, px0:px1].max() > 0.02:
                keep[(i, j)] = True
    vid = {}
    verts, faces = [], []

    def v(i, j):
        k = (i, j)
        if k not in vid:
            vid[k] = len(verts)
            verts.append(((ox + i * g) / W, (oy + j * g) / H))
        return vid[k]
    for (i, j) in sorted(keep):
        a, b, c, d = v(i, j), v(i + 1, j), v(i + 1, j + 1), v(i, j + 1)
        if (i + j) % 2 == 0:
            faces += [(a, b, c), (a, c, d)]
        else:
            faces += [(a, b, d), (b, c, d)]
    return verts, faces


def _layer_rank(st, L):
    """위 레이어일수록 큰 값 (목록 위가 앞)."""
    n = len(st.layers)
    for i, x in enumerate(st.layers):
        if x == L:
            return n - i
    return 0


def _part_mat(s, st, L, aff):
    """메시 파츠 머티리얼: 제자리 좌표 → 칸 공간 → 시트 칸. 칸 바꾸기·
    불투명도·보이기(키 가능)·HSV 반영."""
    rig = s.rig
    name = MAT_PREFIX + st.uid + "_" + L.lid
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    if nt.animation_data is not None:
        for fc in list(nt.animation_data.drivers):
            nt.animation_data.drivers.remove(fc)
    nt.nodes.clear()
    for attr, val in (("surface_render_method", 'DITHERED'),
                      ("blend_method", 'HASHED'),
                      ("use_backface_culling", False)):
        try:
            setattr(mat, attr, val)
        except Exception:
            pass
    N, Lk = nt.nodes, nt.links

    def nd(tp, x, y, **kw):
        n = N.new(tp)
        n.location = (x, y)
        for k9, v9 in kw.items():
            setattr(n, k9, v9)
        return n

    def mth(op, a, b, x, y):
        n = nd('ShaderNodeMath', x, y, operation=op)
        for i, v in enumerate((a, b)):
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                Lk.new(v, n.inputs[i])
        return n.outputs[0]
    at = nd('ShaderNodeAttribute', -1400, 0, attribute_type='GEOMETRY',
            attribute_name=REST_ATTR)
    # 제자리 (x, y) → 그림 칸 공간 (반전 포함):  q = R·(x, y) + o
    (r11, r12, o1), (r21, r22, o2) = aff
    dq = []
    for i9, (ra, rb, oo) in enumerate(((r11, r12, o1), (r21, r22, o2))):
        dn = nd('ShaderNodeVectorMath', -1200, 60 - 120 * i9,
                operation='DOT_PRODUCT')
        Lk.new(at.outputs["Vector"], dn.inputs[0])
        dn.inputs[1].default_value = (ra, rb, 0.0)
        dq.append(mth('ADD', dn.outputs["Value"], oo, -1050, 60 - 120 * i9))
    cq = nd('ShaderNodeCombineXYZ', -900, 0)
    Lk.new(dq[0], cq.inputs[0])
    Lk.new(dq[1], cq.inputs[1])
    # 칸 범위(0~1) 밖은 투명
    ins = None
    for ax in (0, 1):
        t = mth('MULTIPLY', mth('GREATER_THAN', dq[ax], 0.0, -900, -200 - 60 * ax),
                mth('LESS_THAN', dq[ax], 1.0, -900, -230 - 60 * ax),
                -800, -200 - 60 * ax)
        ins = t if ins is None else mth('MULTIPLY', ins, t, -700, -230)
    cols, rows = EY._layer_grid(s, L)
    n = cols * rows
    cst, cL = EY._cell_source(s, st, L)
    cp = EY._prop_cell(cst, cL)
    EY._ensure_prop(rig, cp, EY._ncells(cL))
    EY._pv_cell_ensure(rig, cp, n)
    k = "min(max(floor((c if pv<0 else pv)+0.5),0),%d)" % (n - 1)
    cv = [("c", rig, '["%s"]' % cp), ("pv", rig, '["%s"]' % EY._prop_cell_pv(cp))]
    cm = nd('ShaderNodeMapping', -700, 0, vector_type='POINT')
    Lk.new(cq.outputs[0], cm.inputs["Vector"])
    cm.inputs["Scale"].default_value = (1.0 / cols, 1.0 / rows, 1.0)
    EY._drv_vars(cm.inputs["Location"], 0,
                 "(%s-floor(%s/%d)*%d)/%d" % (k, k, cols, cols, cols), cv)
    EY._drv_vars(cm.inputs["Location"], 1,
                 "1-(floor(%s/%d)+1)/%d" % (k, cols, rows), cv)
    tex = nd('ShaderNodeTexImage', -500, 0)
    tex.image = EY._layer_image(s, L)
    tex.extension = 'CLIP'
    tex.interpolation = 'Linear'
    Lk.new(cm.outputs[0], tex.inputs["Vector"])
    # 색조/채도/명도 + 색 덮기 (캔버스와 같은 순서·같은 노드 이름이라
    # 패널에서 값을 바꾸면 바로 반영됨). 부모 것도 캔버스처럼 받음
    col = tex.outputs["Color"]
    xx = -300
    for X in [L] + EY.layer_ancestors(st, L):
        own = X is L
        sfx = "" if own else ".in" + L.lid
        if own or L.inh_hsv:
            h9 = nd('ShaderNodeHueSaturation', xx, 100)
            h9.name = EY._hsv_node_name(st, X) + sfx
            h9.inputs["Hue"].default_value = 0.5 + X.hue
            h9.inputs["Saturation"].default_value = X.sat
            h9.inputs["Value"].default_value = X.val
            Lk.new(col, h9.inputs["Color"])
            col = h9.outputs[0]
            xx += 60
        if getattr(X, "ov_on", False) and (own or L.inh_ov):
            o9 = nd('ShaderNodeMix', xx, 100)
            o9.data_type = 'RGBA'
            o9.blend_type = {'MIX': 'MIX', 'COLOR': 'COLOR',
                             'MULTIPLY': 'MULTIPLY'}.get(X.ov_mode, 'MIX')
            o9.clamp_result = True
            o9.name = EY._ov_node_name(st, X) + sfx
            o9.inputs[0].default_value = X.ov_fac
            Lk.new(col, o9.inputs[6])
            o9.inputs[7].default_value = EY._lin4(X.ov_color)
            col = o9.outputs[2]
            xx += 60
    ov = nd('ShaderNodeValue', -500, -300)
    ov.label = "opacity × visible"
    EY._drv_vars(ov.outputs[0], None, "op*(vis>=0.5)",
                 [("op", rig, '["%s"]' % EY._p_op(st, L)),
                  ("vis", rig, '["%s"]' % EY._p_vis(st, L))])
    a = mth('MULTIPLY', tex.outputs["Alpha"], ins, -250, -150)
    a = mth('MULTIPLY', a, ov.outputs[0], -100, -150)
    em = nd('ShaderNodeEmission', 0, 100)
    Lk.new(col, em.inputs["Color"])
    tr = nd('ShaderNodeBsdfTransparent', 0, -50)
    mx = nd('ShaderNodeMixShader', 200, 0)
    Lk.new(a, mx.inputs[0])
    Lk.new(tr.outputs[0], mx.inputs[1])
    Lk.new(em.outputs[0], mx.inputs[2])
    out = nd('ShaderNodeOutputMaterial', 400, 0)
    Lk.new(mx.outputs[0], out.inputs["Surface"])
    try:
        nt.nodes.active = out
    except Exception:
        pass
    return mat


def _mode_obj(context):
    try:
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
    except Exception:
        pass


def _edit_bones(context, arm, fn):
    """아마추어 편집 모드에서 fn(edit_bones) 실행 후 오브젝트 모드로."""
    _mode_obj(context)
    vl = context.view_layer
    prev = vl.objects.active
    hid = arm.hide_get()
    arm.hide_set(False)
    vl.objects.active = arm
    arm.select_set(True)
    out = None
    try:
        with context.temp_override(active_object=arm, object=arm):
            bpy.ops.object.mode_set(mode='EDIT')
            out = fn(arm.data.edit_bones)
            bpy.ops.object.mode_set(mode='OBJECT')
    finally:
        if prev is not None and prev != arm:
            vl.objects.active = prev
        arm.hide_set(hid)
    return out


WGT_PREFIX = "FSKR_WGT_"


def _widget(kind):
    """뼈 모양 (선만 있는 메시). Pin = 원, Root = 십자 사각형, IK = 마름모.
    뼈 공간: Y = 뼈 방향, X = 옆, 원점 = 뼈 머리 (핀 자리)."""
    import math as m
    name = WGT_PREFIX + kind
    ob = bpy.data.objects.get(name)
    if ob is not None and ob.type == 'MESH':
        return ob
    vs, es = [], []

    def loop(pts):
        b = len(vs)
        vs.extend(pts)
        es.extend((b + i, b + (i + 1) % len(pts)) for i in range(len(pts)))
    if kind == "Pin":
        n = 24
        loop([(0.6 * m.cos(2 * m.pi * i / n), 0.6 * m.sin(2 * m.pi * i / n),
               0.0) for i in range(n)])
        loop([(0.25 * m.cos(2 * m.pi * i / 12),
               0.25 * m.sin(2 * m.pi * i / 12), 0.0) for i in range(12)])
    elif kind == "Root":
        loop([(-0.5, -0.5, 0.0), (0.5, -0.5, 0.0), (0.5, 0.5, 0.0),
              (-0.5, 0.5, 0.0)])
        b = len(vs)
        vs.extend([(-0.75, 0.0, 0.0), (0.75, 0.0, 0.0), (0.0, -0.75, 0.0),
                   (0.0, 1.0, 0.0)])
        es.extend([(b, b + 1), (b + 2, b + 3)])
    else:   # IK
        loop([(0.0, 0.7, 0.0), (0.7, 0.0, 0.0), (0.0, -0.7, 0.0),
              (-0.7, 0.0, 0.0)])
        loop([(0.0, 0.35, 0.0), (0.35, 0.0, 0.0), (0.0, -0.35, 0.0),
              (-0.35, 0.0, 0.0)])
    me = bpy.data.meshes.new(name)
    me.from_pydata(vs, es, [])
    ob = bpy.data.objects.new(name, me)
    ob.use_fake_user = True
    return ob


def apply_shapes(arm):
    """이 애드온이 만든 뼈에 전용 모양·색 (캐릭터 리그 뼈와 구분)."""
    look = (("fskr_pin", "Pin", 'THEME09', 1.0),
            ("fskr_root", "Root", 'THEME04', 1.0),
            ("fskr_ik", "IK", 'THEME01', 1.0))
    for pb in arm.pose.bones:
        b = pb.bone
        for flag, kind, pal, sc in look:
            if not b.get(flag):
                continue
            try:
                pb.custom_shape = _widget(kind)
                # 사슬이면 뼈 길이가 핀 사이 거리라, 길이와 상관없는 고정 크기
                sz = float(b.get("fskr_size", 0.0)) or b.length
                pb.use_custom_shape_bone_size = False
                pb.custom_shape_scale_xyz = (sz * sc, sz * sc, sz * sc)
                try:
                    pb.custom_shape_wire_width = 2.5
                except Exception:
                    pass
                b.show_wire = True
                pb.color.palette = pal
                b.color.palette = pal
            except Exception as e:
                print("FSKR bone shape:", e)
            break


def _uniq_bone(arm, name):
    if name not in arm.data.bones:
        return name
    i = 2
    while "%s.%d" % (name, i) in arm.data.bones:
        i += 1
    return "%s.%d" % (name, i)


def make_mesh_part(context, s, st, L, res=14):
    """파츠 L을 메시 오브젝트로. 오류 문자열 또는 None."""
    import numpy as np
    from . import face_ui as FU
    rig = s.rig
    if rig is None:
        return _tr("리그를 먼저 지정하세요")
    if L.kind == 'MOUTH' or EY._layer_atlas(s, L) is not None:
        return _tr("입 파츠는 아직 메시로 만들 수 없습니다")
    if EY._layer_image(s, L) is None:
        return _tr("이미지를 고르세요")
    if EY._mirror_all(s, st):
        return _tr("다른 캔버스를 따라가는 캔버스는 지원하지 않습니다")
    cob = _canvas(st)
    if cob is None:
        return _tr("대상이 메시가 아닙니다")
    # 1) 지금 배치 그대로: q → 캔버스 UV (자유 변형과 같은 계산)
    sp = FU.part_space(context, s, st, L)
    if sp is None:
        return _tr("대상이 메시가 아닙니다")
    alpha = _cell_alpha(s, st, L)
    qv, faces = grid_mesh(alpha, res)
    if not faces:
        return _tr("그림이 비어 있습니다")
    arm = ensure_arm(context, s, st)
    if arm is None:
        return _tr("대상이 메시가 아닙니다")
    f = 1.0 if float(rig.get(EY._p_flip(st, L), 0.0)) >= 0.5 else 0.0
    # 그림 칸 공간(반전 후) → 반전 전 q → UV → 로컬
    def q2loc(qx, qy):
        qx9 = f + (1.0 - 2.0 * f) * qx      # 반전은 자기 자신의 역
        uv = sp._q2uv((qx9, qy))
        return _local_of_uv(arm, uv.x, uv.y)
    verts = [q2loc(x, y) for x, y in qv]
    # 로컬 → 그림 칸 공간 (아핀, 세 점으로 구함)
    P = np.array([q2loc(0, 0), q2loc(1, 0), q2loc(0, 1)])
    Q = np.array([(0, 0), (1, 0), (0, 1)], dtype=float)
    A9 = np.c_[P, np.ones(3)]
    X9 = np.linalg.solve(A9, Q)       # [x y 1]·X = q
    aff = ((X9[0, 0], X9[1, 0], X9[2, 0]), (X9[0, 1], X9[1, 1], X9[2, 1]))
    # 2) 메시 오브젝트
    nm = "%s (%s)" % (L.name, _tr("메시"))
    old = part_ob(L)
    me = bpy.data.meshes.new(nm)
    me.from_pydata([(x, y, 0.0) for x, y in verts], [], faces)
    me.update()
    if old is not None:
        old.data = me
        ob = old
    else:
        ob = bpy.data.objects.new(nm, me)
        for c in arm.users_collection:
            c.objects.link(ob)
    ob.parent = arm
    ob.parent_type = 'OBJECT'
    ob.matrix_parent_inverse = Matrix.Identity(4)
    ob.matrix_basis = Matrix.Identity(4)
    # 3) 뿌리 뼈 (파츠 전체 이동·회전·크기)
    cx = sum(v[0] for v in verts) / len(verts)
    cy = sum(v[1] for v in verts) / len(verts)
    hy = max(v[1] for v in verts) - min(v[1] for v in verts)
    root = L.get("pp_root", "")
    if not root or root not in arm.data.bones:
        root = _uniq_bone(arm, L.name)

        def mk(eb):
            b = eb.new(root)
            b.head = (cx, cy, 0.0)
            b.tail = (cx, cy + max(hy * 0.6, 0.02), 0.0)
            b.use_deform = True
            b["fskr_root"] = True
            return b.name
        root = _edit_bones(context, arm, mk)
        L["pp_root"] = root
        apply_shapes(arm)
    # 4) 모디파이어: 제자리 저장 → 뼈 → 얼굴에 붙이기
    _setup_mods(ob, s, st, L, arm, cob, mirror=False)
    # 5) 웨이트 (핀이 없으면 뿌리 뼈에 전부)
    ob["fskr_uid"], ob["fskr_lid"] = st.uid, L.lid
    L.mesh_ob = ob.name
    recompute_weights(arm, ob, L)
    # 6) 머티리얼
    mat = _part_mat(s, st, L, aff)
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    ob["fskr_aff"] = [aff[0][0], aff[0][1], aff[0][2],
                      aff[1][0], aff[1][1], aff[1][2]]
    # 6-b) 대칭 복사 파츠면 반대쪽 메시·뼈도 (리깅은 같이, 조종은 대칭/개별)
    if EY.sym_built(L):
        ensure_mirror(context, s, st, L)
    # 7) 캔버스에서는 빼기 (eye_build 가 앞뒤 높이도 다시 맞춤)
    L.mesh_on = True
    EY.eye_build(s, st)
    return None


def _setup_mods(ob, s, st, L, arm, cob, mirror=False):
    """제자리 저장 → (대칭이면 거울) → 뼈 → 얼굴에 붙이기 + 보이기 드라이버.
    보이기: 대칭 복사(키)와 보일 쪽(양쪽/원본만/복사본만)을 따름."""
    rig = s.rig
    for m in list(ob.modifiers):
        ob.modifiers.remove(m)
    if ob.animation_data is not None:
        for fc in list(ob.animation_data.drivers):
            ob.animation_data.drivers.remove(fc)
    m1 = ob.modifiers.new(MOD_REST, 'NODES')
    m1.node_group = _gn_rest()
    if mirror:
        mm = ob.modifiers.new(MOD_MIRROR, 'NODES')
        g9 = _gn_mirror()
        mm.node_group = g9
        (m11, m12, m21, m22), (tx, ty) = mirror_map(arm)
        _mod_set(mm, _sock_id(g9, "Row X"), (m11, m12, 0.0))
        _mod_set(mm, _sock_id(g9, "Row Y"), (m21, m22, 0.0))
        _mod_set(mm, _sock_id(g9, "Offset"), (tx, ty, 0.0))
    m2 = ob.modifiers.new(MOD_ARM, 'ARMATURE')
    m2.object = arm
    m3 = ob.modifiers.new(MOD_STICK, 'NODES')
    ng = _gn_stick2()
    m3.node_group = ng
    B = arm["fskr_B"]
    _mod_set(m3, _sock_id(ng, "Canvas"), cob)
    _mod_set(m3, _sock_id(ng, "UV Map"), _uv_name(cob, st))
    _mod_set(m3, _sock_id(ng, "Row U"), (B[0], B[1], 0.0))
    _mod_set(m3, _sock_id(ng, "Row V"), (B[2], B[3], 0.0))
    vid = _sock_id(ng, "Visible")
    pairs = [("m", rig, '["%s"]' % EY._p_sym(st, L)),
             ("sd", rig, '["%s"]' % EY._p_side(st, L))]
    # 보일 쪽: 0 = 양쪽, 1 = 원본만, 2 = 복사본만
    expr = "(m>=0.5)*(abs(sd-1)>0.5)" if mirror else "1-(m>=0.5)*(sd>1.5)"
    try:
        EY._ensure_anim_props(rig, st, L)
        _drv_simple(ob, _mod_path(m3, vid), expr, pairs)
    except Exception as e:
        print("FSKR part visible driver:", e)


def arm_r_name(st):
    """1.0.241에서 쓰던 복사본 전용 아마추어 (지금은 옮겨 담고 지움)."""
    return ARM_PREFIX + st.uid + "_R"


def puppet_arm_r(st):
    return bpy.data.objects.get(arm_r_name(st))


def _drop_old_arm_r(context, st, L):
    """1.0.241 방식(별도 아마추어)의 이 파츠 뼈를 지우고, 비면 아마추어도."""
    ar = puppet_arm_r(st)
    if ar is None:
        return
    root = L.get("pp_root", "")
    if root and root in ar.data.bones:
        def rm(eb):
            b = eb.get(root)
            if b is None:
                return
            for c in list(b.children_recursive):
                eb.remove(c)
            eb.remove(b)
        _edit_bones(context, ar, rm)
    if not len(ar.data.bones):
        ad = ar.data
        bpy.data.objects.remove(ar)
        if ad.users == 0:
            bpy.data.armatures.remove(ad)


def _part_tree(arm, root):
    """뿌리부터 (부모 먼저) 이 파츠의 뼈 이름들."""
    out = []
    b = arm.data.bones.get(root) if root else None
    if b is None:
        return out

    def walk(x):
        out.append(x.name)
        for c in x.children:
            walk(c)
    walk(b)
    return out


def _mirror_cons(arm, name, rig, prop):
    """복사본 뼈(name.R)가 원본 뼈(name)를 거울로 따라감.
    세기 = 대칭 조종 (리그 프로퍼티, 키 가능)."""
    rn = mirror_name(name)
    pb = arm.pose.bones.get(rn)
    if pb is None:
        return
    if any(c.name == "FSKR mirror loc" for c in pb.constraints):
        return
    cl = pb.constraints.new('COPY_LOCATION')
    cl.name = "FSKR mirror loc"
    cl.invert_x = True
    cr = pb.constraints.new('COPY_ROTATION')
    cr.name = "FSKR mirror rot"
    cr.invert_y = True
    cr.invert_z = True
    cs = pb.constraints.new('COPY_SCALE')
    cs.name = "FSKR mirror scale"
    for c in (cl, cr, cs):
        c.target = arm
        c.subtarget = name
        c.owner_space = 'LOCAL'
        c.target_space = 'LOCAL'
        try:
            _drv_simple(arm, 'pose.bones["%s"].constraints["%s"].influence'
                        % (rn, c.name), "min(max(m,0),1)",
                        [("m", rig, '["%s"]' % prop)])
        except Exception as e:
            print("FSKR mirror influence:", e)


def sync_mirror_mesh(L):
    """복사본 메시 = 원본 메시 복사 + 정점 그룹 이름만 .R 뼈로.
    (Blender는 정점 그룹 이름을 메시에 저장해서 같이 쓸 수 없음)"""
    ob, obr = part_ob(L), part_ob_r(L)
    if ob is None or obr is None:
        return
    old = obr.data
    me = ob.data.copy()
    me.name = ob.data.name + ".R"
    obr.data = me
    for g in obr.vertex_groups:
        g.name = mirror_name(g.name)
    if old is not None and old != ob.data and old.users == 0:
        bpy.data.meshes.remove(old)
    obr.update_tag()


def sync_mirror(context, s, st, L):
    """원본 쪽 뼈(이 파츠)를 같은 아마추어에 .R 로 거울 복사:
    없는 뼈 만들기, 위치 갱신, 원본에서 지운 뼈 지우기, 거울 제약·IK.
    복사본 메시도 원본에 맞춤."""
    if part_ob_r(L) is None:
        return
    arm = puppet_arm(st)
    if arm is None:
        return
    rig = s.rig
    root = L.get("pp_root", "")
    names = _part_tree(arm, root)
    old = set(_part_tree(arm, mirror_name(root)))
    want = {mirror_name(n) for n in names}
    info = []
    for nm in names:
        b = arm.data.bones[nm]
        info.append((nm, b.parent.name if b.parent is not None and nm != root
                     else None,
                     mirror_pt(arm, b.head_local.x, b.head_local.y),
                     mirror_pt(arm, b.tail_local.x, b.tail_local.y),
                     b.use_deform,
                     {k9: b[k9] for k9 in ("fskr_pin", "fskr_root", "fskr_ik",
                                           "fskr_size") if k9 in b}))

    def mk(eb):
        for rn in old - want:
            x = eb.get(rn)
            if x is not None:
                eb.remove(x)
        for nm, par, h, t, dfm, props in info:
            rn = mirror_name(nm)
            r = eb.get(rn) or eb.new(rn)
            r.head = (h[0], h[1], 0.0)
            r.tail = (t[0], t[1], 0.0)
            r.roll = 0.0
            r.parent = eb.get(mirror_name(par)) if par else None
            r.use_connect = False
            r.use_deform = dfm
            for k9, v9 in props.items():
                r[k9] = v9
            r["fskr_mirror_of"] = nm
    _edit_bones(context, arm, mk)
    apply_shapes(arm)
    prop = _p_mpose(st, L)
    EY._ensure_float(rig, prop, 1.0, 0.0, 1.0)
    for nm in names:
        _mirror_cons(arm, nm, rig, prop)
        src = arm.pose.bones.get(nm)
        dst = arm.pose.bones.get(mirror_name(nm))
        if src is None or dst is None:
            continue
        for c in list(dst.constraints):
            if c.type == 'IK':
                dst.constraints.remove(c)
        for c in src.constraints:
            if c.type == 'IK':
                c2 = dst.constraints.new('IK')
                c2.target = arm
                c2.subtarget = mirror_name(c.subtarget)
                c2.chain_count = c.chain_count
    sync_mirror_mesh(L)


def ensure_mirror(context, s, st, L):
    """대칭 복사 쪽 메시 오브젝트와 뼈 (같은 아마추어, 이름 .R)."""
    arm, ob = puppet_arm(st), part_ob(L)
    if arm is None or ob is None:
        return None
    _drop_old_arm_r(context, st, L)
    obr = part_ob_r(L)
    if obr is None:
        obr = bpy.data.objects.new(ob.name + ".R", ob.data.copy())
        for c in ob.users_collection:
            c.objects.link(obr)
    obr.parent = arm
    obr.parent_type = 'OBJECT'
    obr.matrix_parent_inverse = Matrix.Identity(4)
    obr.matrix_basis = Matrix.Identity(4)
    obr["fskr_uid"], obr["fskr_lid"], obr["fskr_mirror"] = st.uid, L.lid, 1
    L["mesh_ob_r"] = obr.name
    _setup_mods(obr, s, st, L, arm, _canvas(st), mirror=True)
    sync_mirror(context, s, st, L)
    return obr


# 원본 메시를 편집 모드·웨이트 페인트로 고치면 잠시 뒤 복사본에 반영
_MSYNC = {"pending": set(), "timer": False}


def _msync_tick():
    _MSYNC["timer"] = False
    pend, _MSYNC["pending"] = _MSYNC["pending"], set()
    try:
        ctx = bpy.context
        if ctx.mode == 'EDIT_MESH':      # 편집 중엔 끝날 때까지 기다림
            _MSYNC["pending"] |= pend
            _MSYNC["timer"] = True
            return 0.5
        s = ctx.scene.fskr
        for st in s.eyes:
            for L in st.layers:
                ob = part_ob(L)
                if ob is not None and ob.data.name in pend and \
                        part_ob_r(L) is not None:
                    sync_mirror_mesh(L)
    except Exception as e:
        print("FSKR mirror mesh sync:", e)
    return None


@bpy.app.handlers.persistent
def _msync_depsgraph(scene, depsgraph):
    try:
        for u in depsgraph.updates:
            idb = u.id
            if not isinstance(idb, bpy.types.Mesh) or not u.is_updated_geometry:
                continue
            _MSYNC["pending"].add(idb.name)   # 아래에서 원본 파츠만 남김
        if _MSYNC["pending"] and not _MSYNC["timer"]:
            known = set()
            for st in scene.fskr.eyes:
                for L in st.layers:
                    ob = part_ob(L)
                    if ob is not None and part_ob_r(L) is not None:
                        known.add(ob.data.name)
            _MSYNC["pending"] &= known
            if _MSYNC["pending"]:
                _MSYNC["timer"] = True
                bpy.app.timers.register(_msync_tick, first_interval=0.4)
    except Exception:
        pass


def _canvas_gap(st):
    """캔버스가 얼굴 피부에서 떠 있는 높이 (m)."""
    cob = _canvas(st)
    if cob is None:
        return 0.0
    w = cob.modifiers.get("FSKR_Canvas_Wrap")
    if w is None:
        return 0.0
    sc = cob.matrix_world.to_scale()
    return abs(float(w.offset)) * (abs(sc.x) + abs(sc.y) + abs(sc.z)) / 3.0


def _box_hit(a, b):
    return a[0] < b[1] and b[0] < a[1] and a[2] < b[3] and b[2] < a[3]


def _mirror_box(bx):
    return (1.0 - bx[1], 1.0 - bx[0], bx[2], bx[3])


def _layer_uv_boxes(context, s, st, X):
    """캔버스 파츠 X가 캔버스 UV에서 차지하는 영역들 (대칭 복사 포함)."""
    from . import face_ui as FU
    try:
        sp = FU.part_space(context, s, st, X)
    except Exception:
        sp = None
    if sp is None:
        return []
    bb = None
    try:
        if EY._layer_atlas(s, X) is None:
            bb = EY.cell_bbox(s, st, X)
    except Exception:
        bb = None
    u0, u1, v0, v1 = bb if bb else (0.0, 1.0, 0.0, 1.0)
    try:
        if float(s.rig.get(EY._p_flip(st, X), 0.0)) >= 0.5:
            u0, u1 = 1.0 - u1, 1.0 - u0
    except Exception:
        pass
    pts = [sp._q2uv((qu, qv)) for qu in (u0, u1) for qv in (v0, v1)]
    bx = (min(p.x for p in pts), max(p.x for p in pts),
          min(p.y for p in pts), max(p.y for p in pts))
    out = [bx]
    if EY.sym_built(X):
        out.append(_mirror_box(bx))
    return out


def _mesh_uv_boxes(arm, ob, L):
    B = arm["fskr_B"]
    us, vs = [], []
    for v in ob.data.vertices:
        us.append(B[0] * v.co.x + B[1] * v.co.y)
        vs.append(B[2] * v.co.x + B[3] * v.co.y)
    if not us:
        return []
    bx = (min(us), max(us), min(vs), max(vs))
    out = [bx]
    if EY.sym_built(L):
        out.append(_mirror_box(bx))
    return out


def auto_back(context, s, st, L, arm, ob):
    """자동 앞뒤: 아래쪽 캔버스 파츠와 겹치면 앞(그 위에 보여야 함),
    아래와는 안 겹치고 위쪽 캔버스 파츠와만 겹치면 뒤."""
    mine = _mesh_uv_boxes(arm, ob, L)
    layers = list(st.layers)
    idx = next((i for i, X in enumerate(layers) if X == L), 0)
    below = above = False
    for i, X in enumerate(layers):
        if X == L or mesh_on(X) or EY._layer_image(s, X) is None:
            continue
        hit = any(_box_hit(a, b) for a in mine
                  for b in _layer_uv_boxes(context, s, st, X))
        if not hit:
            continue
        if i > idx:
            below = True
        else:
            above = True
    return above and not below


def update_offsets(s, st, context=None):
    """메시 파츠의 얼굴 표면 높이. 캔버스는 한 장이라 메시 파츠는 캔버스
    그림 전체의 앞이나 뒤에만 놓일 수 있다.
      앞 = 캔버스 위, 뒤 = 피부와 캔버스 사이.
    자동: 아래쪽 캔버스 파츠와 겹치면 앞, 위쪽 파츠와만 겹치면 뒤."""
    context = context or bpy.context
    arm = puppet_arm(st)
    if arm is None:
        return
    k = float(arm.get("fskr_k", 1.0)) or 1.0
    sg = float(arm.get("fskr_nsign", 1.0))
    gap = _canvas_gap(st)
    # 예전(1.0.237) 뼈에도 표시를 달고 전용 모양 적용
    try:
        for L in st.layers:
            r9 = L.get("pp_root", "")
            if r9 and r9 in arm.data.bones:
                arm.data.bones[r9]["fskr_root"] = True
        for b in arm.data.bones:
            if b.name.endswith(".IK") and not b.use_deform:
                b["fskr_ik"] = True
        if any(pb.custom_shape is None and (pb.bone.get("fskr_pin")
               or pb.bone.get("fskr_root") or pb.bone.get("fskr_ik"))
               for pb in arm.pose.bones):
            apply_shapes(arm)
    except Exception as e:
        print("FSKR bone shapes:", e)
    for L in list(st.layers):
        ob = part_ob(L) if mesh_on(L) else None
        if ob is None:
            continue
        m = ob.modifiers.get(MOD_STICK)
        if m is None or m.node_group is None:
            continue
        mode = getattr(L, "mesh_depth", 'AUTO')
        if mode == 'BACK':
            back = True
        elif mode == 'FRONT':
            back = False
        else:
            try:
                back = auto_back(context, s, st, L, arm, ob)
            except Exception as e:
                print("FSKR mesh depth:", e)
                back = False
        back = back and gap > 1e-6
        rank = _layer_rank(st, L)
        if back:
            # 피부와 캔버스 사이 (위 레이어일수록 캔버스 쪽)
            off = -gap * 0.6 + min(OFFSET_STEP * rank, gap * 0.4)
        else:
            off = OFFSET_BASE + OFFSET_STEP * rank
        L["mesh_back"] = back
        _mod_set(m, _sock_id(m.node_group, "Offset"), off / k * sg)
        ob.update_tag()
        obr = part_ob_r(L)
        mr = obr.modifiers.get(MOD_STICK) if obr is not None else None
        if mr is not None and mr.node_group is not None:
            _mod_set(mr, _sock_id(mr.node_group, "Offset"), off / k * sg)
            obr.update_tag()
    try:
        for win in bpy.context.window_manager.windows:
            for ar in win.screen.areas:
                if ar.type == 'VIEW_3D':
                    ar.tag_redraw()
    except Exception:
        pass


def _depth_cb(self, context):
    st = EY._owner(self)
    if st is None:
        return
    try:
        update_offsets(context.scene.fskr, st, context)
    except Exception as e:
        print("FSKR mesh depth:", e)
    _redraw_ui(context)


def pin_bones(arm, L):
    """이 파츠의 핀 뼈 이름들 (뿌리 아래, IK 대상 제외)."""
    root = L.get("pp_root", "")
    b = arm.data.bones.get(root)
    if b is None:
        return []
    out = []
    for c in b.children_recursive:
        if c.get("fskr_pin"):
            out.append(c.name)
    return out


def recompute_weights(arm, ob, L):
    """뼈까지 거리로 자동 웨이트 (가까운 뼈 4개, 정규화)."""
    import numpy as np
    root = L.get("pp_root", "")
    pins = pin_bones(arm, L)
    names = pins if pins else ([root] if root else [])
    for vg in list(ob.vertex_groups):
        ob.vertex_groups.remove(vg)
    if not names:
        return
    me = ob.data
    co = np.array([(v.co.x, v.co.y) for v in me.vertices], dtype=float)
    segs = []
    for nm in names:
        b = arm.data.bones[nm]
        h, t = b.head_local, b.tail_local
        segs.append(((h.x, h.y), (t.x, t.y)))
    D = np.empty((len(co), len(segs)))
    for j, ((hx, hy), (tx, ty)) in enumerate(segs):
        ax, ay = tx - hx, ty - hy
        l2 = ax * ax + ay * ay
        if l2 < 1e-12:
            tt = np.zeros(len(co))
        else:
            tt = np.clip(((co[:, 0] - hx) * ax + (co[:, 1] - hy) * ay) / l2,
                         0.0, 1.0)
        px, py = hx + tt * ax, hy + tt * ay
        D[:, j] = (co[:, 0] - px) ** 2 + (co[:, 1] - py) ** 2
    # 1/거리² (너무 날카로우면 뼈 사이가 찢어진 듯 꺾임)
    W = 1.0 / (D + 1e-5)
    if W.shape[1] > 4:
        thr = -np.sort(-W, axis=1)[:, 3:4]
        W[W < thr] = 0.0
    W /= W.sum(1, keepdims=True)
    groups = [ob.vertex_groups.new(name=nm) for nm in names]
    for j, g in enumerate(groups):
        for i in range(len(co)):
            if W[i, j] > 1e-4:
                g.add([i], float(W[i, j]), 'REPLACE')
    if len(names) > 1:
        smooth_weights(ob, 0.5, 4)   # 뼈 사이를 부드럽게 이어 줌
    if part_ob_r(L) is not None:
        sync_mirror_mesh(L)


def remove_mesh_part(context, s, st, L):
    ob = part_ob(L)
    arm = puppet_arm(st)
    obr = part_ob_r(L)
    if obr is not None:
        mr = obr.data
        bpy.data.objects.remove(obr)
        if mr is not None and mr.users == 0:
            bpy.data.meshes.remove(mr)
    L["mesh_ob_r"] = ""
    if ob is not None:
        me = ob.data
        bpy.data.objects.remove(ob)
        if me is not None and me.users == 0:
            bpy.data.meshes.remove(me)
    mat = bpy.data.materials.get(MAT_PREFIX + st.uid + "_" + L.lid)
    if mat is not None and mat.users == 0:
        bpy.data.materials.remove(mat)
    root = L.get("pp_root", "")
    _drop_old_arm_r(context, st, L)
    roots = [r9 for r9 in (root, mirror_name(root))
             if root and arm is not None and r9 in arm.data.bones]
    if roots:
        def rm(eb):
            for r9 in roots:
                b = eb.get(r9)
                if b is None:
                    continue
                for c in list(b.children_recursive):
                    eb.remove(c)
                # IK 대상 뼈 (뿌리에 붙어 있음)도 위에서 같이 지워짐
                eb.remove(b)
        _edit_bones(context, arm, rm)
    L["pp_root"] = ""
    L["pp_root_r"] = ""
    L.mesh_ob = ""
    L.mesh_on = False
    EY.eye_build(s, st)


# ------------------------------------------------------------------
# 오퍼레이터
# ------------------------------------------------------------------

def _ctx(op9, context):
    s = context.scene.fskr
    st = EY._find(s, op9.uid)
    L = EY._layer(st, op9.lid) if st else None
    return s, st, L


class FSKR_OT_mesh_make(bpy.types.Operator):
    bl_idname = "fskr.mesh_make"
    bl_label = "메시로 만들기"
    bl_description = ("이 파츠를 메시 오브젝트로 꺼냅니다. 그림이 있는 곳에 "
                      "메시가 자동으로 생기고, 핀(뼈)으로 휠 수 있습니다. "
                      "지금 위치·크기·회전·칸이 그대로 옮겨집니다")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    lid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, context):
        s, st, L = _ctx(self, context)
        if L is None:
            return {'CANCELLED'}
        try:
            err = make_mesh_part(context, s, st, L, int(L.mesh_res))
        except Exception as e:
            import traceback
            traceback.print_exc()
            err = repr(e)
        if err:
            self.report({'ERROR'}, err)
            return {'CANCELLED'}
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_mesh_remove(bpy.types.Operator):
    bl_idname = "fskr.mesh_remove"
    bl_label = "메시 해제"
    bl_description = ("메시 오브젝트와 이 파츠의 뼈를 지우고 캔버스 그림으로 "
                      "되돌립니다")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    lid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        s, st, L = _ctx(self, context)
        if L is None:
            return {'CANCELLED'}
        remove_mesh_part(context, s, st, L)
        _redraw_ui(context)
        return {'FINISHED'}


class FSKR_OT_mesh_weights(bpy.types.Operator):
    bl_idname = "fskr.mesh_weights"
    bl_label = "웨이트 자동 계산"
    bl_description = ("핀(뼈)까지의 거리로 웨이트를 다시 계산합니다. 웨이트 "
                      "페인트로 고친 값은 덮어씁니다")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    lid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, context):
        s, st, L = _ctx(self, context)
        ob, arm = part_ob(L) if L else None, puppet_arm(st) if st else None
        if ob is None or arm is None:
            return {'CANCELLED'}
        _mode_obj(context)
        recompute_weights(arm, ob, L)
        return {'FINISHED'}


class FSKR_OT_mesh_mode(bpy.types.Operator):
    bl_idname = "fskr.mesh_mode"
    bl_label = "메시 파츠 모드"
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    lid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    mode: bpy.props.EnumProperty(items=(
        ('EDIT', "메시 편집", ""), ('WEIGHT', "웨이트 칠하기", ""),
        ('POSE', "뼈 움직이기", ""), ('OBJECT', "끝내기", "")),
        options={'HIDDEN', 'SKIP_SAVE'})

    @classmethod
    def description(cls, context, props):
        return {
            'EDIT': _tr("메시를 편집 모드로 엽니다. 점을 더하고 옮겨 메시를 "
                        "나누는 방식을 고칩니다 (새 점도 그림 위치가 자동)"),
            'WEIGHT': _tr("웨이트 페인트 모드. Ctrl+클릭으로 뼈를 골라 그 "
                          "뼈의 영향 범위를 칠합니다"),
            'POSE': _tr("포즈 모드. 핀(뼈)을 G·R로 움직이고 I로 키를 넣습니다"),
            'OBJECT': _tr("오브젝트 모드로 돌아갑니다"),
        }.get(props.mode, "")

    def execute(self, context):
        s, st, L = _ctx(self, context)
        ob, arm = part_ob(L) if L else None, puppet_arm(st) if st else None
        if ob is None or arm is None:
            return {'CANCELLED'}
        _mode_obj(context)
        vl = context.view_layer
        for o in context.selected_objects:
            o.select_set(False)
        if self.mode == 'EDIT':
            ob.hide_set(False)
            ob.select_set(True)
            vl.objects.active = ob
            bpy.ops.object.mode_set(mode='EDIT')
            # 메시 평면을 정면·직교로 보고, 뷰가 돌아가면 편집 모드 해제
            area = context.area if context.area is not None and \
                context.area.type == 'VIEW_3D' else next(
                    (a for a in context.screen.areas if a.type == 'VIEW_3D'),
                    None)
            if area is not None:
                face_view(context, area, arm, ob)
                reg = next((r for r in area.regions if r.type == 'WINDOW'),
                           None)
                try:
                    with context.temp_override(area=area, region=reg):
                        bpy.ops.fskr.mesh_edit_guard('INVOKE_DEFAULT')
                except Exception as e:
                    print("FSKR edit guard:", e)
        elif self.mode == 'WEIGHT':
            ob.hide_set(False)
            arm.hide_set(False)
            arm.select_set(True)
            ob.select_set(True)
            vl.objects.active = ob
            bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
        elif self.mode == 'POSE':
            arm.hide_set(False)
            arm.select_set(True)
            vl.objects.active = arm
            bpy.ops.object.mode_set(mode='POSE')
        return {'FINISHED'}


def _face_quat(arm):
    """메시 평면을 정면에서 보는 뷰 회전 (위 = 평면 +Y, 앞 = 얼굴 바깥)."""
    mw = arm.matrix_world.to_3x3()
    y = (mw @ Vector((0.0, 1.0, 0.0))).normalized()
    z = (mw @ Vector((0.0, 0.0, 1.0))).normalized() * \
        float(arm.get("fskr_nsign", 1.0))
    x = y.cross(z).normalized()
    y = z.cross(x).normalized()
    M = Matrix((x, y, z)).transposed()
    return M.to_quaternion()


def face_view(context, area, arm, ob):
    """정면·직교로 맞추고 X-Ray를 켬 (편집 끝나면 되돌림)."""
    sp = area.spaces.active
    rv3d = sp.region_3d
    rv3d.view_rotation = _face_quat(arm)
    rv3d.view_perspective = 'ORTHO'
    try:
        me = ob.data
        if len(me.vertices):
            c = sum((v.co for v in me.vertices), Vector()) / len(me.vertices)
            rv3d.view_location = arm.matrix_world @ c
    except Exception:
        pass
    area.tag_redraw()


class FSKR_OT_mesh_edit_guard(bpy.types.Operator):
    """메시 파츠 편집 중: 뷰가 돌아가거나 원근이 되면 편집 모드를 끝냄.
    편집 중에는 X-Ray (뒤에 가린 점도 보이게)."""
    bl_idname = "fskr.mesh_edit_guard"
    bl_label = "메시 편집 정면 고정"
    bl_options = {'INTERNAL'}

    def invoke(self, context, event):
        self.area = context.area
        if self.area is None or self.area.type != 'VIEW_3D':
            return {'CANCELLED'}
        sp = self.area.spaces.active
        self.quat = sp.region_3d.view_rotation.copy()
        self.xray = None
        try:
            sh = sp.shading
            attr = "show_xray_wireframe" if sh.type == 'WIREFRAME' \
                else "show_xray"
            self.xray = (attr, getattr(sh, attr))
            setattr(sh, attr, True)
        except Exception:
            pass
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def _end(self, context, leave):
        try:
            if self.xray is not None:
                setattr(self.area.spaces.active.shading, *self.xray)
        except Exception:
            pass
        if leave and context.mode == 'EDIT_MESH':
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except Exception:
                pass
            self.report({'INFO'}, _tr("뷰가 돌아가 메시 편집을 끝냈습니다"))
        try:
            self.area.tag_redraw()
        except Exception:
            pass
        return {'FINISHED', 'PASS_THROUGH'}

    def modal(self, context, ev):
        if context.mode != 'EDIT_MESH':
            return self._end(context, False)
        try:
            rv3d = self.area.spaces.active.region_3d
        except Exception:
            return {'FINISHED', 'PASS_THROUGH'}
        if rv3d.view_perspective != 'ORTHO' or \
                rv3d.view_rotation.rotation_difference(self.quat).angle > 0.01:
            return self._end(context, True)
        return {'PASS_THROUGH'}


class FSKR_OT_mesh_weight_smooth(bpy.types.Operator):
    bl_idname = "fskr.mesh_weight_smooth"
    bl_label = "웨이트 부드럽게"
    bl_description = ("이웃한 점끼리 웨이트를 섞어 경계를 부드럽게 합니다 "
                      "(모든 뼈, 합은 1로 맞춤)")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    lid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    factor: bpy.props.FloatProperty(name="세기", default=0.5, min=0.0,
                                    max=1.0)
    repeat: bpy.props.IntProperty(name="반복", default=3, min=1, max=50)

    def execute(self, context):
        s, st, L = _ctx(self, context)
        ob = part_ob(L) if L else None
        if ob is None:
            return {'CANCELLED'}
        mode = context.mode
        if mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')
        n = smooth_weights(ob, self.factor, self.repeat)
        if part_ob_r(L) is not None:
            sync_mirror_mesh(L)
        if mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')
        ob.update_tag()
        self.report({'INFO'}, _tr("웨이트 부드럽게: ") + "%d" % n)
        return {'FINISHED'}


def smooth_weights(ob, factor=0.5, repeat=3):
    """라플라시안: w ← (1-f)·w + f·(이웃 평균). 끝나면 점마다 합 = 1."""
    import numpy as np
    me = ob.data
    groups = list(ob.vertex_groups)
    if not groups or not len(me.vertices):
        return 0
    nv, ng = len(me.vertices), len(groups)
    W = np.zeros((nv, ng))
    gi = {g.index: j for j, g in enumerate(groups)}
    for v in me.vertices:
        for e in v.groups:
            j = gi.get(e.group)
            if j is not None:
                W[v.index, j] = e.weight
    ed = np.array([e.vertices[:] for e in me.edges], dtype=np.int64)
    if not len(ed):
        return 0
    deg = np.zeros(nv)
    np.add.at(deg, ed[:, 0], 1)
    np.add.at(deg, ed[:, 1], 1)
    deg = np.maximum(deg, 1)
    for _ in range(max(1, int(repeat))):
        S = np.zeros_like(W)
        np.add.at(S, ed[:, 0], W[ed[:, 1]])
        np.add.at(S, ed[:, 1], W[ed[:, 0]])
        W = (1.0 - factor) * W + factor * (S / deg[:, None])
    tot = W.sum(1, keepdims=True)
    W = np.where(tot > 1e-9, W / np.maximum(tot, 1e-9), W)
    for j, g in enumerate(groups):
        idx = np.nonzero(W[:, j] > 1e-4)[0]
        zero = np.nonzero(W[:, j] <= 1e-4)[0]
        if len(zero):
            g.remove(zero.tolist())
        for i in idx:
            g.add([int(i)], float(W[i, j]), 'REPLACE')
    return ng


# ------------------------------------------------------------------
# 사슬 표시: 이어 찍은 핀끼리 화살표 (부모 핀 → 자식 핀)
# ------------------------------------------------------------------

_CHAIN = {"h": None}


def _chain_draw():
    import gpu
    import math as m
    from gpu_extras.batch import batch_for_shader
    ctx = bpy.context
    reg, rv3d = ctx.region, ctx.region_data
    if reg is None or rv3d is None:
        return
    segs = []
    try:
        objs = [o for o in ctx.visible_objects
                if o.type == 'ARMATURE' and o.name.startswith(ARM_PREFIX)]
    except Exception:
        return
    for arm in objs:
        mw = arm.matrix_world
        for pb in arm.pose.bones:
            par = pb.parent
            if par is None or not pb.bone.get("fskr_pin") or \
                    not par.bone.get("fskr_pin"):
                continue
            a = view3d_utils.location_3d_to_region_2d(reg, rv3d,
                                                      mw @ par.head)
            b = view3d_utils.location_3d_to_region_2d(reg, rv3d,
                                                      mw @ pb.head)
            if a is None or b is None:
                continue
            d = b - a
            ln = d.length
            if ln < 16:
                continue
            u = d / ln
            # 고리 바깥에서 시작·끝 (고리와 겹치지 않게)
            a2 = a + u * 8
            b2 = b - u * 10
            nrm = Vector((-u.y, u.x))
            h = 9.0
            segs.append((a2, b2, b2 - u * h + nrm * h * 0.55,
                         b2 - u * h - nrm * h * 0.55))
    if not segs:
        return
    sh = gpu.shader.from_builtin('UNIFORM_COLOR')
    gpu.state.blend_set('ALPHA')
    gpu.state.line_width_set(2.0)
    lines, tris = [], []
    for a2, b2, l9, r9 in segs:
        lines += [tuple(a2), tuple(b2)]
        tris += [tuple(b2), tuple(l9), tuple(r9)]
    sh.bind()
    sh.uniform_float("color", (1.0, 0.75, 0.15, 0.95))
    batch_for_shader(sh, 'LINES', {"pos": lines}).draw(sh)
    batch_for_shader(sh, 'TRIS', {"pos": tris}).draw(sh)
    gpu.state.line_width_set(1.0)
    gpu.state.blend_set('NONE')


def puppet_register():
    if _msync_depsgraph not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_msync_depsgraph)
    if _CHAIN["h"] is None:
        _CHAIN["h"] = bpy.types.SpaceView3D.draw_handler_add(
            _chain_draw, (), 'WINDOW', 'POST_PIXEL')


def puppet_unregister():
    for h in list(bpy.app.handlers.depsgraph_update_post):
        if getattr(h, "__name__", "") == "_msync_depsgraph":
            bpy.app.handlers.depsgraph_update_post.remove(h)
    if _CHAIN["h"] is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_CHAIN["h"], 'WINDOW')
        except Exception:
            pass
        _CHAIN["h"] = None
    _pin_cleanup()


def _plane_hit(context, arm, mp):
    """화면 좌표 → 아마추어 로컬 평면(z=0) 위 점 (x, y) 또는 None."""
    from mathutils.geometry import intersect_line_plane
    reg, rv3d = context.region, context.region_data
    if reg is None or rv3d is None:
        return None
    o = view3d_utils.region_2d_to_origin_3d(reg, rv3d, mp)
    d = view3d_utils.region_2d_to_vector_3d(reg, rv3d, mp)
    mw = arm.matrix_world
    po = mw.translation
    pn = (mw.to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()
    hit = intersect_line_plane(o, o + d, po, pn)
    if hit is None:
        return None
    lo = mw.inverted() @ hit
    return lo.x, lo.y


def _pin_len(arm, L):
    """핀 뼈 길이: 파츠 크기의 1/6 정도 (작은 파츠에 큰 뼈가 안 생기게)."""
    b = arm.data.bones.get(L.get("pp_root", ""))
    if b is None:
        return 0.01
    return max(b.length / 3.0, 0.002)


def _to_source_side(arm, ob, L, hit):
    """대칭 복사 쪽을 클릭했으면 원본 쪽 좌표로 (핀은 원본에 만들고 거울로)."""
    if part_ob_r(L) is None or not len(ob.data.vertices):
        return hit
    x, y = hit
    mx, my = mirror_pt(arm, x, y)

    def dmin(px, py):
        return min((v.co.x - px) ** 2 + (v.co.y - py) ** 2
                   for v in ob.data.vertices)
    return (mx, my) if dmin(mx, my) < dmin(x, y) else hit


def add_pin(context, arm, ob, L, x, y, parent=None):
    """핀 뼈 하나 추가 (부모 = parent 핀이면 사슬, 아니면 뿌리)."""
    root = L.get("pp_root", "")
    n = len(pin_bones(arm, L)) + 1
    name = _uniq_bone(arm, "%s.Pin%d" % (root, n))
    def mk(eb):
        b = eb.new(name)
        b.head = (x, y, 0.0)
        ln = _pin_len(arm, L)
        b.tail = (x, y + ln, 0.0)
        par = eb.get(parent) if parent else None
        if par is not None:
            # 사슬: 부모 핀 꼬리를 새 핀 머리로 (IK가 끝을 끌 수 있게)
            par.tail = (x, y, 0.0)
            d = Vector((x, y, 0.0)) - par.head
            if d.length > 1e-6:
                b.tail = b.head + d.normalized() * ln
            b.parent = par
        else:
            b.parent = eb.get(root)
        b.use_connect = False
        b.use_deform = True
        b["fskr_pin"] = True
        b["fskr_size"] = ln
        return b.name
    nm = _edit_bones(context, arm, mk)
    apply_shapes(arm)
    recompute_weights(arm, ob, L)
    st9 = EY._owner(L)
    if st9 is not None:
        sync_mirror(context, context.scene.fskr, st9, L)
    return nm


_PIN = {"h": None, "op": None}


def _pin_draw():
    op = _PIN.get("op")
    if op is None:
        return
    try:
        op.draw_px(bpy.context)
    except Exception as e:
        print("FSKR pin draw:", e)


def _pin_cleanup():
    _PIN["op"] = None
    if _PIN["h"] is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_PIN["h"], 'WINDOW')
        except Exception:
            pass
        _PIN["h"] = None


class FSKR_OT_mesh_pin(bpy.types.Operator):
    """뷰포트에서 클릭해 핀(뼈) 찍기."""
    bl_idname = "fskr.mesh_pin"
    bl_label = "핀 찍기"
    bl_description = ("뷰포트에서 그림을 클릭하면 그 자리에 핀(뼈)이 생깁니다. "
                      "Shift+클릭 = 앞 핀에 이어 찍기(사슬, IK용). "
                      "Enter·Esc = 끝내고 포즈 모드로")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    lid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    def invoke(self, context, event):
        s, st, L = _ctx(self, context)
        if L is None or part_ob(L) is None or puppet_arm(st) is None:
            self.report({'WARNING'}, _tr("먼저 메시로 만드세요"))
            return {'CANCELLED'}
        if context.area is None or context.area.type != 'VIEW_3D':
            self.report({'WARNING'}, _tr("3D 뷰포트에서 실행하세요"))
            return {'CANCELLED'}
        _mode_obj(context)
        self.last = None
        self.added = []
        self.area = context.area
        self.mp = None
        context.area.header_text_set(_tr(
            "핀 찍기: 클릭 = 핀 · Shift+클릭 = 앞 핀에 이어 찍기 · "
            "Ctrl+Z = 마지막 핀 지우기 · Enter/Esc = 끝내기"))
        try:
            context.window.cursor_modal_set('CROSSHAIR')
        except Exception:
            pass
        _pin_cleanup()
        _PIN["op"] = self
        _PIN["h"] = bpy.types.SpaceView3D.draw_handler_add(
            _pin_draw, (), 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def draw_px(self, context):
        import gpu
        import blf
        import math as m
        from gpu_extras.batch import batch_for_shader
        if context.area is None or context.area != self.area:
            return
        s, st, L = _ctx(self, context)
        arm = puppet_arm(st) if st else None
        if arm is None or L is None:
            return
        reg, rv3d = context.region, context.region_data
        try:
            ui = float(context.preferences.system.ui_scale)
        except Exception:
            ui = 1.0
        sh = gpu.shader.from_builtin('UNIFORM_COLOR')
        gpu.state.blend_set('ALPHA')
        sh.bind()
        # 이 파츠의 핀 (노란 점 + 번호), 이어 찍기 기준 핀은 주황
        mw = arm.matrix_world
        pts = []
        for nm in pin_bones(arm, L):
            b = arm.data.bones[nm]
            p = view3d_utils.location_3d_to_region_2d(
                reg, rv3d, mw @ b.head_local)
            if p is not None:
                pts.append((nm, p))
        for nm, p in pts:
            r = 7.0 * ui
            tris = []
            for i in range(16):
                a1, a2 = i / 16 * 2 * m.pi, (i + 1) / 16 * 2 * m.pi
                tris += [(p.x, p.y), (p.x + r * m.cos(a1), p.y + r * m.sin(a1)),
                         (p.x + r * m.cos(a2), p.y + r * m.sin(a2))]
            bt = batch_for_shader(sh, 'TRIS', {"pos": tris})
            sh.uniform_float("color", (1.0, 0.55, 0.1, 1.0)
                             if nm == self.last else (1.0, 0.85, 0.2, 1.0))
            bt.draw(sh)
        # 마우스 위치 십자
        if self.mp is not None:
            x, y = self.mp
            r = 10.0 * ui
            bl = batch_for_shader(sh, 'LINES', {"pos": [
                (x - r, y), (x + r, y), (x, y - r), (x, y + r)]})
            sh.uniform_float("color", (1.0, 0.85, 0.2, 1.0))
            bl.draw(sh)
        # 위: 지금 상태, 아래: 도움말
        title = _tr("핀 찍기 중") + "  ·  " + L.name + "  ·  " + \
            _tr("핀") + " %d" % len(pts)
        tips = (_tr("클릭 = 핀 꽂기   ·   Shift+클릭 = 앞 핀(주황)에 이어 "
                    "찍기 (사슬, IK용)"),
                _tr("Ctrl+Z = 마지막 핀 지우기   ·   Enter / Esc / 우클릭 = "
                    "끝내고 포즈 모드로"))
        fid = 0
        for lines, top in (((title,), True), (tips, False)):
            fs = (17 if top else 15) * ui
            blf.size(fid, fs)
            lh = fs * 1.55
            pad = 10 * ui
            ws = [blf.dimensions(fid, t9)[0] for t9 in lines]
            bw = max(ws) + pad * 2
            bh = lh * len(lines) + pad * 1.2
            bx0 = (reg.width - bw) / 2
            by0 = reg.height - bh - 60 * ui if top else 60 * ui
            gpu.state.blend_set('ALPHA')
            bg = batch_for_shader(sh, 'TRIS', {"pos": [
                (bx0, by0), (bx0 + bw, by0), (bx0 + bw, by0 + bh),
                (bx0, by0), (bx0 + bw, by0 + bh), (bx0, by0 + bh)]})
            sh.bind()
            sh.uniform_float("color", (0.75, 0.45, 0.05, 0.85) if top
                             else (0.06, 0.06, 0.08, 0.75))
            bg.draw(sh)
            gpu.state.blend_set('NONE')
            for i, t9 in enumerate(reversed(lines)):
                w = ws[len(lines) - 1 - i]
                blf.color(fid, 1, 1, 1, 1)
                blf.position(fid, (reg.width - w) / 2,
                             by0 + pad * 0.8 + i * lh, 0)
                blf.draw(fid, t9)
        gpu.state.blend_set('NONE')

    def _finish(self, context):
        _pin_cleanup()
        try:
            context.window.cursor_modal_restore()
        except Exception:
            pass
        try:
            context.area.header_text_set(None)
            context.area.tag_redraw()
        except Exception:
            pass
        s, st, L = _ctx(self, context)
        arm = puppet_arm(st) if st else None
        if arm is not None and self.added:
            vl = context.view_layer
            for o in context.selected_objects:
                o.select_set(False)
            arm.select_set(True)
            vl.objects.active = arm
            try:
                bpy.ops.object.mode_set(mode='POSE')
                for pb in arm.pose.bones:
                    pb.bone.select = pb.name in self.added
                arm.data.bones.active = arm.data.bones.get(self.added[-1])
            except Exception:
                pass
        _redraw_ui(context)
        return {'FINISHED'}

    def modal(self, context, ev):
        if _PIN.get("op") is not self:
            return self._finish(context)
        if ev.type in ('ESC', 'RET', 'NUMPAD_ENTER', 'RIGHTMOUSE') and \
                ev.value == 'PRESS':
            return self._finish(context)
        if ev.type == 'MOUSEMOVE':
            self.mp = (ev.mouse_region_x, ev.mouse_region_y)
            try:
                self.area.tag_redraw()
            except Exception:
                pass
            return {'PASS_THROUGH'}
        if ev.type == 'Z' and (ev.ctrl or ev.oskey) and ev.value == 'PRESS':
            if self.added:
                s, st, L = _ctx(self, context)
                arm, ob = puppet_arm(st), part_ob(L)
                nm = self.added.pop()

                def rm(eb):
                    b = eb.get(nm)
                    if b is not None:
                        eb.remove(b)
                _edit_bones(context, arm, rm)
                recompute_weights(arm, ob, L)
                self.last = self.added[-1] if self.added else None
            return {'RUNNING_MODAL'}
        if ev.type == 'LEFTMOUSE' and ev.value == 'PRESS':
            reg = context.region
            mp = (ev.mouse_region_x, ev.mouse_region_y)
            if reg is None or not (0 <= mp[0] <= reg.width
                                   and 0 <= mp[1] <= reg.height):
                return {'PASS_THROUGH'}
            s, st, L = _ctx(self, context)
            arm, ob = puppet_arm(st), part_ob(L)
            hit = _plane_hit(context, arm, mp)
            if hit is None:
                return {'RUNNING_MODAL'}
            hit = _to_source_side(arm, ob, L, hit)
            par = self.last if ev.shift else None
            nm = add_pin(context, arm, ob, L, hit[0], hit[1], par)
            self.added.append(nm)
            self.last = nm
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}
        return {'PASS_THROUGH'}


class FSKR_OT_mesh_ik(bpy.types.Operator):
    bl_idname = "fskr.mesh_ik"
    bl_label = "IK 컨트롤러 만들기"
    bl_description = ("포즈 모드에서 고른 핀(사슬 끝)에 IK 컨트롤러를 만듭니다. "
                      "컨트롤러를 끌면 사슬 전체가 따라 굽습니다")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    lid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, context):
        s, st, L = _ctx(self, context)
        arm = puppet_arm(st) if st else None
        ob = part_ob(L) if L else None
        if arm is None or ob is None:
            return {'CANCELLED'}
        b = arm.data.bones.active
        pins = set(pin_bones(arm, L))
        if b is not None and b.get("fskr_mirror_of"):
            b = arm.data.bones.get(b["fskr_mirror_of"])   # 복사본 → 원본
        if b is None or b.name not in pins:
            self.report({'WARNING'}, _tr("포즈 모드에서 이 파츠의 핀을 "
                                         "하나 고르세요"))
            return {'CANCELLED'}
        chain = []
        p = b.parent
        while p is not None and p.name in pins:
            chain.append(p.name)
            p = p.parent
        if not chain:
            self.report({'WARNING'}, _tr("사슬 끝 핀을 고르세요 "
                                         "(Shift+클릭으로 이어 찍은 핀)"))
            return {'CANCELLED'}
        end, owner = b.name, chain[0]
        root = L.get("pp_root", "")
        tname = _uniq_bone(arm, end + ".IK")

        def mk(eb):
            e = eb.get(end)
            t = eb.new(tname)
            t.head = e.head.copy()
            t.tail = e.head + Vector((0.0, _pin_len(arm, L) * 1.5, 0.0))
            t.parent = eb.get(root)
            t.use_deform = False
            t["fskr_ik"] = True
            t["fskr_size"] = _pin_len(arm, L) * 1.5
            return t.name
        tname = _edit_bones(context, arm, mk)
        apply_shapes(arm)
        pb = arm.pose.bones[owner]
        c = pb.constraints.new('IK')
        c.target = arm
        c.subtarget = tname
        c.chain_count = len(chain)
        sync_mirror(context, s, st, L)
        vl = context.view_layer
        vl.objects.active = arm
        try:
            bpy.ops.object.mode_set(mode='POSE')
            for pb9 in arm.pose.bones:
                pb9.bone.select = pb9.name == tname
            arm.data.bones.active = arm.data.bones[tname]
        except Exception:
            pass
        self.report({'INFO'}, _tr("IK 컨트롤러: ") + tname)
        return {'FINISHED'}


class FSKR_OT_mesh_mirror_pose(bpy.types.Operator):
    bl_idname = "fskr.mesh_mirror_pose"
    bl_label = "대칭 조종"
    bl_description = ("켜면 복사본 쪽 뼈가 원본 쪽 뼈를 거울로 따라갑니다. "
                      "끄면 양쪽을 따로 움직입니다 (윙크 등). 끌 때 지금 "
                      "모양을 복사본 뼈에 옮겨 두어 튀지 않습니다. "
                      "리그 프로퍼티라 키를 넣을 수 있습니다")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    lid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, context):
        s, st, L = _ctx(self, context)
        arm = puppet_arm(st) if st else None
        if arm is None or L is None or s.rig is None:
            return {'CANCELLED'}
        rig = s.rig
        p = _p_mpose(st, L)
        EY._ensure_float(rig, p, 1.0, 0.0, 1.0)
        on = float(rig.get(p, 1.0)) >= 0.5
        if on:
            bake_mirror_pose(arm, L)
        rig[p] = 0.0 if on else 1.0
        if getattr(st, "autokey", False):
            try:
                EY.kfi(rig, data_path='["%s"]' % p, group="Face Parts")
            except Exception:
                pass
        rig.update_tag()
        arm.update_tag()
        _redraw_ui(context)
        return {'FINISHED'}


def bake_mirror_pose(arm, L):
    """대칭 조종을 끄기 전: 복사본 뼈 자체 값 = 지금 거울 모양 (튀지 않게)."""
    for nm in _part_tree(arm, L.get("pp_root", "")):
        sp = arm.pose.bones.get(nm)
        pb = arm.pose.bones.get(mirror_name(nm))
        if sp is None or pb is None:
            continue
        loc = sp.location
        pb.location = (-loc.x, loc.y, loc.z)
        q = sp.matrix_basis.to_quaternion()
        rq = (q.w, q.x, -q.y, -q.z)
        if pb.rotation_mode == 'QUATERNION':
            pb.rotation_quaternion = rq
        else:
            from mathutils import Quaternion
            pb.rotation_euler = Quaternion(rq).to_euler(pb.rotation_mode)
        pb.scale = sp.scale.copy()


class FSKR_OT_mesh_mirror_make(bpy.types.Operator):
    bl_idname = "fskr.mesh_mirror_make"
    bl_label = "대칭 복사 메시 만들기"
    bl_description = ("대칭 복사가 켜진 파츠의 반대쪽 메시와 뼈를 만듭니다 "
                      "(리깅은 원본을 그대로 따라감)")
    bl_options = {'REGISTER', 'UNDO'}

    uid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    lid: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, context):
        s, st, L = _ctx(self, context)
        if L is None or part_ob(L) is None:
            return {'CANCELLED'}
        ob = part_ob(L)
        # 예전(1.0.240 이전) 방식의 원본 모디파이어도 새 방식으로
        _setup_mods(ob, s, st, L, puppet_arm(st), _canvas(st), mirror=False)
        ensure_mirror(context, s, st, L)
        update_offsets(s, st, context)
        _redraw_ui(context)
        return {'FINISHED'}


def draw_mesh_box(layout, s, st, L):
    """선택한 파츠: 메시 파츠 (실험) 상자."""
    if s.rig is None or L.kind == 'MOUTH':
        return
    b = layout.box().column(align=True)
    r = b.row()
    r.label(text=_tr("메시 파츠 (실험)"), icon='MESH_GRID')
    if not mesh_on(L) or part_ob(L) is None:
        r = b.row(align=True)
        r.prop(L, "mesh_res", text=_tr("메시 촘촘함"))
        r = b.row()
        r.scale_y = 1.4
        op = r.operator("fskr.mesh_make", icon='MESH_GRID',
                        text=_tr("메시로 만들기"))
        op.uid, op.lid = st.uid, L.lid
        return
    ob = part_ob(L)
    h = b.row()
    h.active = False
    h.label(text=ob.name, icon='OBJECT_DATA')
    r = b.row(align=True)
    r.prop(L, "mesh_depth", text="")
    h = r.row()
    h.active = False
    h.label(text=_tr("지금: 캔버스 뒤") if L.get("mesh_back")
            else _tr("지금: 캔버스 앞"))
    if EY.sym_built(L):
        r = b.row(align=True)
        if part_ob_r(L) is None or puppet_arm_r(st) is not None:
            # 없거나 1.0.241 방식(별도 아마추어)이면 새 방식으로
            op = r.operator("fskr.mesh_mirror_make", icon='MOD_MIRROR',
                            text=_tr("대칭 복사 메시 만들기"))
            op.uid, op.lid = st.uid, L.lid
        else:
            pm = _p_mpose(st, L)
            on = float(s.rig.get(pm, 1.0)) >= 0.5
            r.label(text=_tr("조종"), icon='MOD_MIRROR')
            op = r.operator("fskr.mesh_mirror_pose", depress=on,
                            text=_tr("대칭"))
            op.uid, op.lid = st.uid, L.lid
            op = r.operator("fskr.mesh_mirror_pose", depress=not on,
                            text=_tr("개별"))
            op.uid, op.lid = st.uid, L.lid
            if pm in s.rig.keys():
                # 마우스를 올리고 I = 대칭/개별 전환을 키로
                sub = r.row(align=True)
                sub.ui_units_x = 3
                sub.prop(s.rig, '["%s"]' % pm, text="")
    r = b.row()
    r.scale_y = 1.4
    op = r.operator("fskr.mesh_pin", icon='BONE_DATA', text=_tr("핀 찍기"))
    op.uid, op.lid = st.uid, L.lid
    r = b.row(align=True)
    for mode, ic, tx in (('POSE', 'POSE_HLT', "뼈 움직이기"),
                         ('EDIT', 'EDITMODE_HLT', "메시 편집"),
                         ('WEIGHT', 'WPAINT_HLT', "웨이트 칠하기")):
        op = r.operator("fskr.mesh_mode", icon=ic, text=_tr(tx))
        op.uid, op.lid, op.mode = st.uid, L.lid, mode
    r = b.row(align=True)
    op = r.operator("fskr.mesh_ik", icon='CON_KINEMATIC',
                    text=_tr("IK 컨트롤러 만들기"))
    op.uid, op.lid = st.uid, L.lid
    op = r.operator("fskr.mesh_weights", icon='MOD_VERTEX_WEIGHT',
                    text=_tr("웨이트 자동 계산"))
    op.uid, op.lid = st.uid, L.lid
    r = b.row(align=True)
    op = r.operator("fskr.mesh_weight_smooth", icon='MOD_SMOOTH',
                    text=_tr("웨이트 부드럽게"))
    op.uid, op.lid = st.uid, L.lid
    r = b.row(align=True)
    op = r.operator("fskr.mesh_mode", icon='OBJECT_DATAMODE',
                    text=_tr("끝내기"))
    op.uid, op.lid, op.mode = st.uid, L.lid, 'OBJECT'
    op = r.operator("fskr.mesh_remove", icon='X', text=_tr("메시 해제"))
    op.uid, op.lid = st.uid, L.lid


puppet_classes = (FSKR_OT_mesh_make, FSKR_OT_mesh_remove,
                  FSKR_OT_mesh_weights, FSKR_OT_mesh_mode, FSKR_OT_mesh_pin,
                  FSKR_OT_mesh_ik, FSKR_OT_mesh_edit_guard,
                  FSKR_OT_mesh_weight_smooth, FSKR_OT_mesh_mirror_pose,
                  FSKR_OT_mesh_mirror_make)
