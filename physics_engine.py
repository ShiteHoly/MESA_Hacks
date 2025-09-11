import numpy as np
import matplotlib.pyplot as plt
import re

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
            ax1.set_xlabel("t (s)")
            ax1.set_ylabel("y (m)")
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
            return fig, None

        #用elif加其他物理场景
        else:
            return None, "Sorry, I cannot handle this request yet."

    except Exception as e:
        return None, str(e)
