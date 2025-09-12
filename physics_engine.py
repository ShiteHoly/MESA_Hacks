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
                "position": {"x":25, "y":1}, "size": {"width":50, "height":1}
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

        #用elif加其他物理场景
        else:
            return None, "Sorry, I cannot handle this request yet."

    except Exception as e:
        return None, str(e)
