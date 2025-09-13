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

        #用elif加其他物理场景
        else:
            return None, "Sorry, I cannot handle this request yet."

    except Exception as e:
        return None, str(e)
