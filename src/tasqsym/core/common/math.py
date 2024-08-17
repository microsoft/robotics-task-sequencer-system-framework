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
def euler_from_quaternion(q: Quaternion) -> tuple[float, float, float]:
    x, y, z, w = q
    sinx_cosy = 2*(w*x + y*z)
    cosx_cosy = 1 - 2*(x*x + y*y)
    siny = np.sqrt(1 + 2*(w*y - x*z))
    cosy = np.sqrt(1 - 2*(w*y - x*z))
    sinz_cosy = 2*(w*z + x*y)
    cosz_cosy = 1 - 2*(y*y + z*z)
    return (np.arctan2(sinx_cosy, cosx_cosy),
            2*np.arctan2(siny, cosy) - np.pi*.5,
            np.arctan2(sinz_cosy, cosz_cosy))


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
