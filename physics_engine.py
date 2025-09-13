import numpy as np
import matplotlib.pyplot as plt
import re
import json

G = 9.8

def handle_physics_simulation(user_input):
    try:
        # 意图1: 自由落体; 用正则从"from...m high"中提取高度
        match = re.search(r"from\s*(\d+\.?\d*)\s*m", user_input, re.IGNORECASE)
        if "free falling" in user_input and match:
            h0 = float(match.group(1)) #initial height

            # physical calculations
            t_max = np.sqrt(2*h0/G)
            t = np.linspace(0, t_max, 200)
            y = h0 - 0.5* G * t**2
            v = -G*t

            # plot
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8,6))
            fig.suptitle(f"Free Falling: Initial Height = {h0:.2f} m", fontsize=16)

            #y-t graph
            ax1.plot(t, y, label="y(t)")
            ax1.set_title("Position-Time (y-t) Graph")
            ax1.set_xlabel("time (s)")
            ax1.set_ylabel("height (m)")
            ax1.grid(True)
            ax1.axhline(0, color='black', linewidth=0.5)
            ax1.axvline(0, color='black', linewidth=0.5)
            ax1.legend()

            #v-t graph
            ax2.plot(t, v, label="v(t)")
            ax2.set_title("Velocity-Time (v-t) Graph")
            ax2.set_xlabel("t (s)")
            ax2.set_ylabel("v (m/s)")
            ax2.grid(True)
            ax2.axhline(0, color='black', linewidth=0.5)
            ax2.axvline(0, color='black', linewidth=0.5)
            ax2.legend()

            plt.tight_layout(rect=[0,0,1,0.96])

            #生成planck.js场景描述
            scale = 10
            ground = {
                "id": "ground", "shape":"box", "type":"static",
                "position": {"x":25, "y":1}, "size": {"width":100, "height":1}
            }
            ball = {
                "id": "ball_1", "shape":"circle", "type":"dynamic","radius": 1.0*scale/10,
                "position": {"x":25, "y":h0*scale/10+1}
            }
            scene_data = {
                "world":{"gravity": {"x":0, "y":-G}},
                "objects":[ground, ball]
            }

            results = {
                "planck_scene": scene_data,
                "matplotlib_fig":fig
            }

            return results, None

        elif "projectile" in user_input.lower():
            # 使用正则表达式提取速度、角度和可选的高度
            v_match = re.search(r"velocity\s*of\s*(\d+\.?\d*)", user_input, re.IGNORECASE)
            angle_match = re.search(r"angle\s*of\s*(\d+\.?\d*)", user_input, re.IGNORECASE)
            h_match = re.search(r"from\s*(\d+\.?\d*)\s*m", user_input, re.IGNORECASE)

            if not v_match or not angle_match:
                return None, "For projectile motion, please specify 'velocity of [number]' and 'angle of [number]'."

            v0 = float(v_match.group(1))
            angle_deg = float(angle_match.group(1))
            angle_rad = np.deg2rad(angle_deg)
            h0 = float(h_match.group(1)) if h_match else 0  # 如果没有指定高度，默认为0

            # 物理计算 (用于绘图)
            v0_x = v0 * np.cos(angle_rad)
            v0_y = v0 * np.sin(angle_rad)

            # 计算飞行总时间 t_flight
            # y(t) = h0 + v0_y * t - 0.5 * G * t^2 = 0
            # 使用二次方程求根公式: t = [-b ± sqrt(b^2 - 4ac)] / 2a
            a = -0.5 * G
            b = v0_y
            c = h0
            discriminant = b ** 2 - 4 * a * c
            t_flight = (-b - np.sqrt(discriminant)) / (2 * a) if discriminant >= 0 else 0

            t = np.linspace(0, t_flight, 200)
            x = v0_x * t
            y = h0 + v0_y * t - 0.5 * G * t ** 2

            # 绘图
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.plot(x, y)
            ax.set_title(f"Projectile Motion: v0={v0} m/s, angle={angle_deg} deg, h0={h0} m")
            ax.set_xlabel("Distance (m)")
            ax.set_ylabel("Height (m)")
            ax.grid(True)
            ax.axhline(0, color='black', linewidth=0.5)
            ax.axvline(0, color='black', linewidth=0.5)
            ax.set_aspect('equal', adjustable='box')

            # 生成planck.js场景描述
            ground = {
                "id": "ground", "shape": "box", "type": "static",
                "position": {"x": 25, "y": 1}, "size": {"width": 100, "height": 1}
            }
            ball = {
                "id": "ball_1", "shape": "circle", "type": "dynamic", "radius": 1.0,
                "position": {"x": 2, "y": h0 + 2},  # +2是为了让球在地面之上
                "initial_velocity": {"x": v0_x, "y": v0_y}  # <<< 新增：传递初始速度
            }
            scene_data = {
                "world": {"gravity": {"x": 0, "y": -G}},
                "objects": [ground, ball]
            }

            results = {
                "planck_scene": scene_data,
                "matplotlib_fig": fig
            }

            return results, None

        elif "pulley" in user_input.lower():
            # 这是一个用于测试的、硬编码的场景描述。
            # [新场景]：一个涉及三个物体和两个滑轮的复杂系统。
            #
            # 场景描述：一个双定滑轮系统
            # - 左侧有一个滑轮 pulley1，右侧有一个滑轮 pulley2。
            # - 物块A(5kg)和物块B(20kg)通过滑轮1连接。
            # - 物块B(20kg)和物块C(5kg)通过滑轮2连接。
            # - 预期结果：物块B下降，同时拉起物块A和物块C。
            scene_description = {
                "surfaces": [
                    # 为防止物体掉落太远，在底部增加一个地面
                    {
                        "id": "ground",
                        "position": {"x": 25, "y": 1},
                        "size": {"width": 100, "height": 1},
                        "angle": 0
                    }
                ],
                "pulleys": [
                    {
                        "id": "pulley1",
                        "position": {"x": 15, "y": 30}  # 左侧滑轮
                    },
                    {
                        "id": "pulley2",
                        "position": {"x": 35, "y": 30}  # 右侧滑轮
                    }
                ],
                "objects": [
                    {
                        "id": "block_A",
                        "mass": 5,
                        "position": {"x": 15, "y": 20},  # 位于滑轮1正下方
                        "friction": 0.3
                    },
                    {
                        "id": "block_B",
                        "mass": 20,
                        "position": {"x": 25, "y": 15},  # 位于两滑轮之间
                        "friction": 0.3
                    },
                    {
                        "id": "block_C",
                        "mass": 5,
                        "position": {"x": 35, "y": 20},  # 位于滑轮2正下方
                        "friction": 0.3
                    }
                ],
                "connections": [
                    {
                        "type": "PulleyJoint",
                        "object_a": "block_A",
                        "object_b": "block_B",
                        "pulley_anchor": "pulley1"  # 使用左侧滑轮
                    },
                    {
                        "type": "PulleyJoint",
                        "object_a": "block_B",
                        "object_b": "block_C",
                        "pulley_anchor": "pulley2"  # 使用右侧滑轮
                    }
                ]
            }

            scene_data = _create_pulley_system_scene(scene_description)

            # 对于这个场景，我们暂时不生成matplotlib图表
            results = {
                "planck_scene": scene_data,
                "matplotlib_fig": None
            }
            return results, None

        #用elif加其他物理场景
        else:
            return None, "Sorry, I cannot handle this request yet."

    except Exception as e:
        return None, str(e)


# =================================================================
# ======== 新增代码：滑轮系统场景生成模块 (START) =========
# =================================================================
# physics_engine.py
def _create_pulley_system_scene(scene_description: dict):
    """
    根据结构化的场景描述，生成用于Planck.js的场景和关节数据。
    [V4 - 最终修复] 遵循官方文档，增加 localAnchor 和 length 的计算。
    # scene_description
    """
    planck_objects = []
    planck_joints = []

    # 辅助函数用于计算两点间距离
    def get_distance(p1, p2):
        return np.sqrt((p1['x'] - p2['x']) ** 2 + (p1['y'] - p2['y']) ** 2)

    # 标准化物块尺寸
    BLOCK_WIDTH = 2.0
    BLOCK_HEIGHT = 2.0
    BLOCK_AREA = BLOCK_WIDTH * BLOCK_HEIGHT

    # 1. 处理平面
    if 'surfaces' in scene_description:
        for surface in scene_description['surfaces']:
            planck_objects.append({
                "id": surface['id'], "shape": "box", "type": "static",
                "position": surface['position'], "size": surface['size'],
                "angle": surface.get('angle', 0)
            })

    # 2. 处理滑轮
    pulley_positions = {p['id']: p['position'] for p in scene_description.get('pulleys', [])}
    if 'pulleys' in scene_description:
        for pulley in scene_description['pulleys']:
            planck_objects.append({
                "id": pulley["id"], "shape": "circle", "type": "static",
                "radius": 0.1, "position": pulley["position"]
            })

    # 3. 处理物体
    object_positions = {obj['id']: obj['position'] for obj in scene_description.get('objects', [])}
    if 'objects' in scene_description:
        for obj in scene_description['objects']:
            density = obj['mass'] / BLOCK_AREA
            planck_objects.append({
                "id": obj['id'], "shape": "box", "type": "dynamic",
                "position": obj['position'],
                "size": {"width": BLOCK_WIDTH, "height": BLOCK_HEIGHT},
                "density": density, "friction": obj.get('friction', 0.3)
            })

    # 4. 处理连接关系 (核心修改)
    if 'connections' in scene_description:
        for conn in scene_description['connections']:
            if conn['type'] == 'PulleyJoint':
                obj_a_id = conn['object_a']
                obj_b_id = conn['object_b']
                pulley_id = conn['pulley_anchor']

                if obj_a_id in object_positions and obj_b_id in object_positions and pulley_id in pulley_positions:
                    pos_a = object_positions[obj_a_id]
                    pos_b = object_positions[obj_b_id]
                    pulley_pos = pulley_positions[pulley_id]

                    # 计算初始绳长
                    length_a = get_distance(pos_a, pulley_pos)
                    length_b = get_distance(pos_b, pulley_pos)

                    planck_joints.append({
                        "type": "PulleyJoint",
                        "object_a_id": obj_a_id,
                        "object_b_id": obj_b_id,
                        # 假设只有一个物理滑轮，因此两个地面锚点是同一点
                        "ground_anchor_a": pulley_pos,
                        "ground_anchor_b": pulley_pos,
                        # 假设绳索连接在物体的中心
                        "local_anchor_a": {"x": 0, "y": 0},
                        "local_anchor_b": {"x": 0, "y": 0},
                        "length_a": length_a,
                        "length_b": length_b,
                        "ratio": conn.get('ratio', 1.0)
                    })

    # 5. 组装最终场景数据
    scene_data = {
        "world": {"gravity": {"x": 0, "y": -G}},
        "objects": planck_objects,
        "joints": planck_joints
    }

    return scene_data
# ===============================================================
# ======== 新增代码：滑轮系统场景生成模块 (END) ===========
# ===============================================================