"""
Generic Physics Scene Compiler for Planck.js.

This module acts as a translator, converting a high-level, generic scene
description from an MCP (Machine Control Protocol) source into the detailed,
low-level JSON format required by the 'simulation.html' frontend.

Core responsibilities:
- Validate the incoming MCP structure.
- Calculate engine-specific parameters from user-friendly inputs (e.g., density from mass).
- Compute complex joint properties (e.g., initial rope lengths for PulleyJoints).
- It does NOT contain any domain-specific logic (e.g., "free fall") or NLP.
"""

import numpy as np

# Default gravitational acceleration (m/s^2)
G = 9.8

def _calculate_density(obj: dict) -> float:
    """Calculates density from mass and shape dimensions."""
    mass = obj.get("mass", 1.0)
    if obj.get("shape") == "box":
        size = obj.get("size", {"width": 1.0, "height": 1.0})
        area = size["width"] * size["height"]
    elif obj.get("shape") == "circle":
        radius = obj.get("radius", 1.0)
        area = np.pi * radius ** 2
    else:
        area = 1.0  # Default area if shape is unknown or missing

    if area == 0:
        return 1.0
    return mass / area

def _prepare_pulley_joint(joint_mcp: dict, objects_map: dict) -> dict:
    """
    Computes the detailed parameters for a Planck.js PulleyJoint
    from a simplified MCP definition.
    """
    obj_a_id = joint_mcp["object_a_id"]
    obj_b_id = joint_mcp["object_b_id"]

    if obj_a_id not in objects_map or obj_b_id not in objects_map:
        raise ValueError(f"Object ID not found for PulleyJoint creation: {obj_a_id} or {obj_b_id}")

    pos_a = objects_map[obj_a_id]["position"]
    pos_b = objects_map[obj_b_id]["position"]
    pulley_pos = joint_mcp["pulley_anchor_pos"]

    # Calculate initial rope lengths based on distance from object centers to the pulley anchor
    length_a = np.sqrt((pos_a['x'] - pulley_pos['x'])**2 + (pos_a['y'] - pulley_pos['y'])**2)
    length_b = np.sqrt((pos_b['x'] - pulley_pos['x'])**2 + (pos_b['y'] - pulley_pos['y'])**2)

    # This detailed structure is what simulation.html's Planck.js setup expects
    return {
        "type": "PulleyJoint",
        "object_a_id": obj_a_id,
        "object_b_id": obj_b_id,
        "ground_anchor_a": pulley_pos,
        "ground_anchor_b": pulley_pos,
        "local_anchor_a": {"x": 0, "y": 0}, # Attach rope to the center of the objects
        "local_anchor_b": {"x": 0, "y": 0},
        "length_a": length_a,
        "length_b": length_b,
        "ratio": joint_mcp.get("ratio", 1.0)
    }


def build_scene_from_mcp(mcp_data: dict):
    """
    Compiles a generic MCP scene description into a Planck.js-ready JSON object.

    This is the sole public function of this module.

    Parameters
    ----------
    mcp_data : dict
        A dictionary following the generic MCP format, describing the world, objects, and joints.

    Returns
    -------
    tuple
        (scene_data_or_none, error_message_or_none)
    """
    try:
        # The final structure that will be injected into the HTML template
        final_scene = {
            "world": mcp_data.get("world", {"gravity": {"x": 0, "y": -G}}),
            "objects": [],
            "joints": []
        }

        # --- 1. Compile Objects ---
        # Create a map for quick position lookups needed by joints
        objects_map = {obj['id']: obj for obj in mcp_data.get("objects", [])}

        for obj_mcp in mcp_data.get("objects", []):
            planck_obj = obj_mcp.copy()

            # For dynamic bodies, density is required by the frontend simulation's fixture definition
            if planck_obj.get("type") == "dynamic":
                if "mass" in planck_obj and "density" not in planck_obj:
                    planck_obj["density"] = _calculate_density(planck_obj)
                elif "density" not in planck_obj:
                    planck_obj["density"] = 1.0  # Default density

            final_scene["objects"].append(planck_obj)

        # --- 2. Compile Joints ---
        for joint_mcp in mcp_data.get("joints", []):
            joint_type = joint_mcp.get("type")
            if joint_type == "PulleyJoint":
                planck_joint = _prepare_pulley_joint(joint_mcp, objects_map)
                final_scene["joints"].append(planck_joint)
            # Future joint types (e.g., RevoluteJoint, PrismaticJoint) can be added here
            else:
                # For other joint types, we might just pass them through if they don't need computation
                final_scene["joints"].append(joint_mcp)

        # Return the compiled scene data, ready for JSON serialization
        # The structure is a dictionary containing a single key "planck_scene"
        return {"planck_scene": final_scene}, None

    except (KeyError, ValueError) as e:
        return None, f"Error processing MCP data: Invalid or missing key. Details: {str(e)}"
    except Exception as e:
        return None, f"An unexpected error occurred in the scene compiler: {str(e)}"