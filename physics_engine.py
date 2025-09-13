"""Physics scene 'script' generator for Planck.js plus optional Matplotlib plots.

This module does not run a full physics simulation on the backend. Instead, it:
- Parses natural-language physics requests.
- Produces a JSON-serializable scene description for Planck.js (run in the browser).
- Optionally returns an instructional Matplotlib figure (e.g., free-fall y–t/v–t or projectile trajectory).

Supported triggers (case-insensitive patterns within the user input):
1) "free falling ... from <h> m" : returns a free-fall scene (ball + ground) and y–t/v–t plots.
2) "projectile ... velocity of <v> ... angle of <deg> [from <h> m]" : returns a projectile scene + trajectory plot.
3) "pulley" : returns a hard-coded double-pulley scene connecting three blocks (for structure validation).

Return contract:
- On success: ({ "planck_scene": <dict>, "matplotlib_fig": <Figure|None> }, None)
- On failure: (None, "<error message>")

Units and conventions:
- Length in meters (m), time in seconds (s), gravity G = 9.8 m/s^2 (negative y-direction in the scene).
- Positions, sizes, and parameters map directly to what `simulation.html` (Planck.js) expects.
"""

import numpy as np
import matplotlib.pyplot as plt
import re
import json

# Constant gravitational acceleration (m/s^2)
G = 9.8


def handle_physics_simulation(user_input):
    """Parse a natural-language physics query and produce a Planck.js scene + optional plot.

    Parameters
    ----------
    user_input : str
        Natural-language instruction describing a physics scenario, e.g.:
        - "free falling from 20 m"
        - "projectile with velocity of 12 at angle of 45 from 3 m"
        - "pulley system"

    Returns
    -------
    tuple
        (results_dict_or_none, error_or_none)
        results_dict contains:
          {
            "planck_scene": dict    # scene consumed by Planck.js in the browser
            "matplotlib_fig": Figure or None
          }
        If parsing fails or input is unsupported, returns (None, "<error message>").
    """
    try:
        # ---------------- Mode 1: Free fall ----------------
        # Trigger: contains "free falling" and a height like "from <number> m"
        match = re.search(r"from\s*(\d+\.?\d*)\s*m", user_input, re.IGNORECASE)
        if "free falling" in user_input and match:
            h0 = float(match.group(1))  # initial height in meters

            # Basic kinematics for explanatory plotting (frontend handles actual dynamics)
            t_max = np.sqrt(2*h0/G)  # total time to hit ground (y=0)
            t = np.linspace(0, t_max, 200)
            y = h0 - 0.5* G * t**2
            v = -G*t

            # Matplotlib: position–time and velocity–time graphs
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8,6))
            fig.suptitle(f"Free Falling: Initial Height = {h0:.2f} m", fontsize=16)

            # y–t graph
            ax1.plot(t, y, label="y(t)")
            ax1.set_title("Position-Time (y-t) Graph")
            ax1.set_xlabel("time (s)")
            ax1.set_ylabel("height (m)")
            ax1.grid(True)
            ax1.axhline(0, color='black', linewidth=0.5)
            ax1.axvline(0, color='black', linewidth=0.5)
            ax1.legend()

            # v–t graph
            ax2.plot(t, v, label="v(t)")
            ax2.set_title("Velocity-Time (v-t) Graph")
            ax2.set_xlabel("t (s)")
            ax2.set_ylabel("v (m/s)")
            ax2.grid(True)
            ax2.axhline(0, color='black', linewidth=0.5)
            ax2.axvline(0, color='black', linewidth=0.5)
            ax2.legend()

            plt.tight_layout(rect=[0,0,1,0.96])

            # Planck.js scene: a ground and a dynamic ball dropped from height h0
            # (Actual motion will be computed on the client-side by Planck.js.)
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

        # ---------------- Mode 2: Projectile motion ----------------
        elif "projectile" in user_input.lower():
            # Extract velocity, angle, and optional height via regex
            v_match = re.search(r"velocity\s*of\s*(\d+\.?\d*)", user_input, re.IGNORECASE)
            angle_match = re.search(r"angle\s*of\s*(\d+\.?\d*)", user_input, re.IGNORECASE)
            h_match = re.search(r"from\s*(\d+\.?\d*)\s*m", user_input, re.IGNORECASE)

            if not v_match or not angle_match:
                return None, "For projectile motion, please specify 'velocity of [number]' and 'angle of [number]'."

            v0 = float(v_match.group(1))
            angle_deg = float(angle_match.group(1))
            angle_rad = np.deg2rad(angle_deg)
            h0 = float(h_match.group(1)) if h_match else 0  # default launch height is 0

            # Initial velocity components
            v0_x = v0 * np.cos(angle_rad)
            v0_y = v0 * np.sin(angle_rad)

            # Solve y(t) = 0 -> a t^2 + b t + c = 0 for total flight time
            a = -0.5 * G
            b = v0_y
            c = h0
            discriminant = b ** 2 - 4 * a * c
            t_flight = (-b - np.sqrt(discriminant)) / (2 * a) if discriminant >= 0 else 0

            # Build trajectory arrays for plotting
            t = np.linspace(0, t_flight, 200)
            x = v0_x * t
            y = h0 + v0_y * t - 0.5 * G * t ** 2

            # Matplotlib: trajectory
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.plot(x, y)
            ax.set_title(f"Projectile Motion: v0={v0} m/s, angle={angle_deg} deg, h0={h0} m")
            ax.set_xlabel("Distance (m)")
            ax.set_ylabel("Height (m)")
            ax.grid(True)
            ax.axhline(0, color='black', linewidth=0.5)
            ax.axvline(0, color='black', linewidth=0.5)
            ax.set_aspect('equal', adjustable='box')

            # Planck.js scene: ground + a ball with initial linear velocity
            ground = {
                "id": "ground", "shape": "box", "type": "static",
                "position": {"x": 25, "y": 1}, "size": {"width": 100, "height": 1}
            }
            ball = {
                "id": "ball_1", "shape": "circle", "type": "dynamic", "radius": 1.0,
                "position": {"x": 2, "y": h0 + 2},  # start slightly above the ground
                "initial_velocity": {"x": v0_x, "y": v0_y}  # consumed by the frontend simulation
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

        # ---------------- Mode 3: Pulley system (hard-coded complex verification scene) ----------------
        elif "pulley" in user_input.lower():
            # A complex example scene with two fixed pulleys and three blocks (A, B, C).
            # The purpose is to validate JSON structure and PulleyJoint completeness.
            scene_description = {
                "surfaces": [
                    # A static ground to catch falling objects
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
                        "position": {"x": 15, "y": 30}  # left pulley
                    },
                    {
                        "id": "pulley2",
                        "position": {"x": 35, "y": 30}  # right pulley
                    }
                ],
                "objects": [
                    {
                        "id": "block_A",
                        "mass": 5,
                        "position": {"x": 15, "y": 20},  # below pulley1
                        "friction": 0.3
                    },
                    {
                        "id": "block_B",
                        "mass": 20,
                        "position": {"x": 25, "y": 15},  # between two pulleys
                        "friction": 0.3
                    },
                    {
                        "id": "block_C",
                        "mass": 5,
                        "position": {"x": 35, "y": 20},  # below pulley2
                        "friction": 0.3
                    }
                ],
                "connections": [
                    {
                        "type": "PulleyJoint",
                        "object_a": "block_A",
                        "object_b": "block_B",
                        "pulley_anchor": "pulley1"  # left pulley
                    },
                    {
                        "type": "PulleyJoint",
                        "object_a": "block_B",
                        "object_b": "block_C",
                        "pulley_anchor": "pulley2"  # right pulley
                    }
                ]
            }

            scene_data = _create_pulley_system_scene(scene_description)

            # For this scene, we do not create an explanatory Matplotlib plot
            results = {
                "planck_scene": scene_data,
                "matplotlib_fig": None
            }
            return results, None

        # Any other physics phrasing is currently unsupported
        else:
            return None, "Sorry, I cannot handle this request yet."

    except Exception as e:
        # Return the error as text so the frontend can present it, rather than raising
        return None, str(e)


# =================================================================
# ======== Pulley system scene builder (START) ====================
# =================================================================
def _create_pulley_system_scene(scene_description: dict):
    """Build a Planck.js-ready scene dict for a pulley system from a high-level description.

    Ensures PulleyJoint definitions include all required fields seen by the frontend:
    - groundAnchorA/B, localAnchorA/B, lengthA/B, ratio
    - Bodies/surfaces include essential geometry and basic physical parameters.

    Parameters
    ----------
    scene_description : dict
        Structured scene specification with keys like:
        {
          "surfaces": [ {id, position{x,y}, size{width,height}, angle? }, ... ],
          "pulleys":  [ {id, position{x,y}}, ... ],
          "objects":  [ {id, mass, position{x,y}, friction?}, ... ],
          "connections": [
            { "type": "PulleyJoint", "object_a": "...", "object_b": "...", "pulley_anchor": "...", "ratio"? },
            ...
          ]
        }

    Returns
    -------
    dict
        A Planck.js scene dictionary ready to be serialized and consumed by `simulation.html`.
    """
    planck_objects = []
    planck_joints = []

    # Helper for Euclidean distance between two points p1 and p2 with 'x' and 'y'
    def get_distance(p1, p2):
        return np.sqrt((p1['x'] - p2['x']) ** 2 + (p1['y'] - p2['y']) ** 2)

    # Standardized block dimensions (used to compute density and for on-screen size)
    BLOCK_WIDTH = 2.0
    BLOCK_HEIGHT = 2.0
    BLOCK_AREA = BLOCK_WIDTH * BLOCK_HEIGHT

    # 1) Static surfaces (e.g., ground)
    if 'surfaces' in scene_description:
        for surface in scene_description['surfaces']:
            planck_objects.append({
                "id": surface['id'], "shape": "box", "type": "static",
                "position": surface['position'], "size": surface['size'],
                "angle": surface.get('angle', 0)
            })

    # 2) Pulleys (rendered as small static circles; visual anchors only)
    pulley_positions = {p['id']: p['position'] for p in scene_description.get('pulleys', [])}
    if 'pulleys' in scene_description:
        for pulley in scene_description['pulleys']:
            planck_objects.append({
                "id": pulley["id"], "shape": "circle", "type": "static",
                "radius": 0.1, "position": pulley["position"]
            })

    # 3) Dynamic objects (blocks with mass; density derived from mass/area)
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

    # 4) Connections (PulleyJoint definitions with computed rope lengths)
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

                    # Initial rope lengths measured from block centers to the pulley anchor
                    length_a = get_distance(pos_a, pulley_pos)
                    length_b = get_distance(pos_b, pulley_pos)

                    planck_joints.append({
                        "type": "PulleyJoint",
                        "object_a_id": obj_a_id,
                        "object_b_id": obj_b_id,
                        # Using the same physical pulley point for both ground anchors in this simplified model
                        "ground_anchor_a": pulley_pos,
                        "ground_anchor_b": pulley_pos,
                        # Rope attachments at block local centers (0, 0) for simplicity
                        "local_anchor_a": {"x": 0, "y": 0},
                        "local_anchor_b": {"x": 0, "y": 0},
                        "length_a": length_a,
                        "length_b": length_b,
                        "ratio": conn.get('ratio', 1.0)
                    })

    # 5) Final scene bundle returned to the caller (to be JSON-serialized upstream)
    scene_data = {
        "world": {"gravity": {"x": 0, "y": -G}},
        "objects": planck_objects,
        "joints": planck_joints
    }

    return scene_data
# =================================================================
# ======== Pulley system scene builder (END) ======================
# =================================================================
