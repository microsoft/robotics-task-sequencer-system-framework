# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import numpy as np
from tasqsym.core.common.structs import Point, Quaternion


"""
Quaternion calculations.
"""

def quaternion_multiply(q1: Quaternion, q2: Quaternion) -> Quaternion:
    x1, y1, z1, w1 = q1  # q1, q2 can be a list, tuple, etc.
    x2, y2, z2, w2 = q2
    return Quaternion(w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,  # i
                      w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,  # j
                      w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,  # k
                      w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2)

def quaternion_conjugate(q: Quaternion) -> Quaternion:
    x, y, z, w = q
    return Quaternion(-x, -y, -z, w)

def quat_mul_vec(q: Quaternion, v: Point) -> Point:
    q_ = [q[0], q[1], q[2], q[3]]
    v_ = [v[0], v[1], v[2], 0.]
    qv = quaternion_multiply(
        quaternion_multiply(q_, v_),
        quaternion_conjugate(q_)
    )[:-1]
    return Point(qv[0], qv[1], qv[2])

def quaternion_slerp(q1: Quaternion, q2: Quaternion, t: float) -> Quaternion:
    q1_n = np.array(q1) / np.linalg.norm(np.array(q1))
    q2_n = np.array(q2) / np.linalg.norm(np.array(q2))
    omega = np.arccos(np.dot(q1, q2))
    s = np.sin((1-t)*omega)/np.sin(omega) * q1_n + np.sin(t*omega)/np.sin(omega) * q2_n
    return Quaternion(s[0], s[1], s[2], s[3])

def quaternion_matrix(q: Quaternion):
    # First row of the rotation matrix
    r00 = 2 * (q[3] * q[3] + q[0] * q[0]) - 1
    r01 = 2 * (q[0] * q[1] - q[3] * q[2])
    r02 = 2 * (q[0] * q[2] + q[3] * q[1])

    # Second row of the rotation matrix
    r10 = 2 * (q[0] * q[1] + q[3] * q[2])
    r11 = 2 * (q[3] * q[3] + q[1] * q[1]) - 1
    r12 = 2 * (q[1] * q[2] - q[3] * q[0])

    # Third row of the rotation matrix
    r20 = 2 * (q[0] * q[2] - q[3] * q[1])
    r21 = 2 * (q[1] * q[2] + q[3] * q[0])
    r22 = 2 * (q[3] * q[3] + q[2] * q[2]) - 1

    return [[r00, r01, r02], [r10, r11, r12], [r20, r21, r22]]

"""Below not used in the sample codes but for convenience."""
def quaternion_from_euler(x: float, y: float, z: float) -> Quaternion:
    cx = np.cos(x*.5)
    sx = np.sin(x*.5)
    cy = np.cos(y*.5)
    sy = np.sin(y*.5)
    cz = np.cos(z*.5)
    sz = np.sin(z*.5)
    return Quaternion(sx*cy*cz - cx*sy*sz,
                      cx*sy*cz + sx*cy*sz,
                      cx*cy*sz - sx*sy*cz,
                      cx*cy*cz + sx*sy*sz)

"""Below not used in the sample codes but for convenience."""
def euler_from_matrix(m: list[list[float]]) -> tuple[float, float, float]:
    _EPS = np.finfo(float).eps * 4.0

    cy = np.sqrt(m[0][0]*m[0][0] + m[1][0]*m[1][0])
    if cy > _EPS:
        ax = np.arctan2( m[2][1], m[2][2])
        ay = np.arctan2(-m[2][0], cy)
        az = np.arctan2( m[1][0], m[0][0])
    else:
        ax = np.arctan2(-m[1][2], m[1][1])
        ay = np.arctan2(-m[2][0],  cy)
        az = 0.0
    return ax, ay, az

def euler_from_quaternion(q: Quaternion) -> tuple[float, float, float]:
    return euler_from_matrix(quaternion_matrix(q))

"""
Directions to angles.
"""

def proper_trifunc(src: int) -> int:
    if src > 1:
        return 1
    if src < -1:
        return -1
    return src

def xyz2polar(xyz: np.ndarray) -> tuple[float, float, float]:
    r = np.linalg.norm(xyz)
    dic = xyz / r
    theta = np.arccos(proper_trifunc(dic[2]))
    phi = np.arctan2(dic[1], dic[0])
    return r, theta, phi

def xyz2dist_ang(xyz: np.ndarray) -> tuple[float, float, float]:
    r = np.linalg.norm(xyz)
    dic = xyz / r
    theta = np.arcsin(proper_trifunc(dic[2]))
    phi = np.arctan2(dic[1], dic[0])
    return r, theta, phi
