"""
Physics Scene Compiler for Planck.js (V2)

This module provides a class `PhysicsSceneCompiler` that acts as a translator,
converting a high-level, generic scene description from an MCP (Machine Control Protocol)
source into the detailed, low-level JSON format required by the 'simulation.html' frontend.

This version features comprehensive docstrings for all methods and supports a complete
set of initial state properties as defined by the Planck.js documentation.
"""

import numpy as np
from typing import Dict, Any, Optional, Tuple

class PhysicsSceneCompiler:
    """
    A generic physics scene compiler that converts high-level MCP data into the
    low-level JSON format usable by Planck.js.

    The core responsibility of this class is to "translate," not to "understand."
    It is responsible for calculating specific parameters required by the frontend
    physics engine (e.g., calculating density from mass, calculating pulley rope
    length from object positions) and passing through standard physics properties
    defined by the user in the MCP.

    Attributes:
        G (float): The default gravitational acceleration (m/s^2).
    """

    def __init__(self, gravity_g: float = 9.8):
        """
        Initializes the compiler instance.

        Args:
            gravity_g (float, optional):
                An optional parameter to set the default Y-axis gravity for the scene.
                This is useful when creating scenes that do not require standard
                gravity, such as space simulations. Defaults to 9.8.
        """
        self.G = gravity_g

    def _calculate_density(self, obj: Dict[str, Any]) -> float:
        """
        Calculates the 2D density of an object based on its mass and shape dimensions.

        The Planck.js Fixture definition requires a `density` property, whereas it is
        more intuitive for a user to provide `mass`. This method handles this conversion.

        Args:
            obj (Dict[str, Any]):
                A dictionary representing the object, which must contain keys for
                calculating the area.
                - For shape='box': requires `size: {'width': float, 'height': float}`
                - For shape='circle': requires `radius: float`
                It should also contain a `mass: float` key.

        Returns:
            float:
                The calculated density value (mass / area). If the area is zero,
                it returns 1.0 to avoid a division-by-zero error.
        """
        mass = obj.get("mass", 1.0)
        shape = obj.get("shape")

        if shape == "box":
            size = obj.get("size", {"width": 1.0, "height": 1.0})
            area = size["width"] * size["height"]
        elif shape == "circle":
            radius = obj.get("radius", 1.0)
            area = np.pi * radius ** 2
        else:
            area = 1.0  # Use a default area if the shape is unknown or missing

        if area == 0:
            return 1.0
        return mass / area

    def _prepare_pulley_joint(self, joint_mcp: Dict[str, Any], objects_map: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates the complete parameters required for a Planck.js pulley joint
        based on a simplified MCP definition.

        The user only needs to provide the IDs of the two objects and the anchor
        position of the pulley; this method will automatically calculate complex
        parameters required by the frontend physics engine, such as the initial
        rope length.

        Args:
            joint_mcp (Dict[str, Any]):
                The MCP input dictionary representing the pulley joint, containing:
                - `object_a_id` (str): The ID of the first object.
                - `object_b_id` (str): The ID of the second object.
                - `pulley_anchor_pos` (Dict): The position of the pulley in world
                  coordinates, e.g., `{'x': float, 'y': float}`.
                - `ratio` (float, optional): The pulley transmission ratio.

            objects_map (Dict[str, Any]):
                A lookup map from an object's ID to its data dictionary, used to
                quickly retrieve object position information.

        Returns:
            Dict[str, Any]:
                A dictionary containing the complete pulley joint parameters, ready
                to be used by the frontend. This includes the calculated `length_a`
                and `length_b`.

        Raises:
            ValueError: If the object_a_id or object_b_id defined in the joint
                        does not exist in the objects_map.
        """
        obj_a_id = joint_mcp["object_a_id"]
        obj_b_id = joint_mcp["object_b_id"]

        if obj_a_id not in objects_map or obj_b_id not in objects_map:
            raise ValueError(f"Object ID referenced for PulleyJoint not found: {obj_a_id} or {obj_b_id}")

        pos_a = objects_map[obj_a_id]["position"]
        pos_b = objects_map[obj_b_id]["position"]
        pulley_pos = joint_mcp["pulley_anchor_pos"]

        # Calculate initial rope lengths based on the distance from object centers to the pulley anchor
        length_a = np.sqrt((pos_a['x'] - pulley_pos['x'])**2 + (pos_a['y'] - pulley_pos['y'])**2)
        length_b = np.sqrt((pos_b['x'] - pulley_pos['x'])**2 + (pos_b['y'] - pulley_pos['y'])**2)

        # Return the complete structure required by the frontend simulation.html
        return {
            "type": "PulleyJoint",
            "object_a_id": obj_a_id,
            "object_b_id": obj_b_id,
            "ground_anchor_a": pulley_pos,
            "ground_anchor_b": pulley_pos,
            "local_anchor_a": {"x": 0, "y": 0},
            "local_anchor_b": {"x": 0, "y": 0},
            "length_a": length_a,
            "length_b": length_b,
            "ratio": joint_mcp.get("ratio", 1.0)
        }

    def compile_scene(self, mcp_data: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Compiles a generic MCP scene description into a JSON object for Planck.js.

        This is the main public method of the class. It receives a dictionary that
        conforms to the MCP format, describing all objects, joints, and world
        properties in the scene. The method handles fields that require calculation
        (like density and rope length) and passes through all other native
        Planck.js-supported physics properties directly.

        Args:
            mcp_data (Dict[str, Any]):
                A dictionary following the MCP format. Each object dictionary in its
                `objects` list, in addition to the mandatory `id`, `type`, `shape`,
                and `position`, can also contain any of the following optional
                properties that conform to the Planck.js BodyDef and FixtureDef:

                --- Body (kinematic) properties ---
                - `angle` (float, optional): Initial angle (in degrees).
                - `linearVelocity` (Dict, optional): Initial linear velocity, e.g., `{'x': 5, 'y': -2}`.
                - `angularVelocity` (float, optional): Initial angular velocity (in radians/sec).
                - `linearDamping` (float, optional): Linear damping.
                - `angularDamping` (float, optional): Angular damping.
                - `fixedRotation` (bool, optional): Whether to fix the rotation.
                - `bullet` (bool, optional): Whether it's a high-speed "bullet" type (to prevent tunneling).
                - `gravityScale` (float, optional): Gravity scale factor, for effects like anti-gravity.

                --- Fixture (material/collision) properties ---
                - `mass` (float, optional): Mass (used for automatic density calculation).
                - `density` (float, optional): Density (if provided, this takes precedence over mass).
                - `friction` (float, optional): Coefficient of friction.
                - `restitution` (float, optional): Coefficient of restitution (bounciness).
                - `isSensor` (bool, optional): Whether it's a sensor (detects collisions but has no physical response).
                - `filterGroupIndex` (int, optional): Collision filter group.
                - `filterCategoryBits` (int, optional): Collision category.
                - `filterMaskBits` (int, optional): Collision mask.

        Returns:
            Tuple[Optional[Dict[str, Any]], Optional[str]]:
                A tuple `(scene_data, error)`.
                - On success: `scene_data` is a dictionary `{"planck_scene": {...}}` that can be
                  serialized to JSON. `error` is `None`.
                - On failure: `scene_data` is `None`, and `error` is a string describing the error.
        """
        try:
            final_scene = {
                "world": mcp_data.get("world", {"gravity": {"x": 0, "y": -self.G}}),
                "objects": [],
                "joints": []
            }

            objects_map = {obj['id']: obj for obj in mcp_data.get("objects", [])}

            for obj_mcp in mcp_data.get("objects", []):
                # Copy all user-provided properties. This ensures that all Planck.js-supported attributes
                # (like angularVelocity, fixedRotation, etc.) are passed through directly.
                planck_obj = obj_mcp.copy()

                if planck_obj.get("type") == "dynamic":
                    # Only calculate density from mass if density is not directly specified.
                    if "mass" in planck_obj and "density" not in planck_obj:
                        planck_obj["density"] = self._calculate_density(planck_obj)
                    elif "density" not in planck_obj:
                        planck_obj["density"] = 1.0  # Provide a default value

                final_scene["objects"].append(planck_obj)

            for joint_mcp in mcp_data.get("joints", []):
                joint_type = joint_mcp.get("type")
                if joint_type == "PulleyJoint":
                    planck_joint = self._prepare_pulley_joint(joint_mcp, objects_map)
                    final_scene["joints"].append(planck_joint)
                else:
                    # For other joint types, pass them through directly
                    final_scene["joints"].append(joint_mcp)

            return {"planck_scene": final_scene}, None

        except (KeyError, ValueError) as e:
            return None, f"Error processing MCP data: Invalid or missing key. Details: {str(e)}"
        except Exception as e:
            return None, f"An unexpected error occurred in the scene compiler: {str(e)}"


if __name__ == '__main__':
    # 假设 PhysicsSceneCompiler 类已经在此文件前面定义好了
    compiler = PhysicsSceneCompiler()

    # 示例: 一个包含多种新增物理属性的复杂场景
    full_mcp_payload = {
        "world": {"gravity": {"x": 0, "y": -10}},
        "objects": [
            {
                "id": "fast_bullet",
                "type": "dynamic", "shape": "box", "mass": 1,
                "size": {"width": 0.5, "height": 0.5},
                "position": {"x": 10, "y": 10},
                "linearVelocity": {"x": 100, "y": 0},  # 初始速度
                "bullet": True,  # 高速物体
                "gravityScale": 0.1  # 受重力影响较小
            },
            {
                "id": "no_spin_box",
                "type": "dynamic", "shape": "box", "mass": 50,
                "size": {"width": 5, "height": 5},
                "position": {"x": 40, "y": 20},
                "fixedRotation": True,  # 固定旋转
                "friction": 0.1,
                "restitution": 0.8  # 高弹性
            },
            {
                "id": "trigger_zone",
                "type": "static", "shape": "circle", "radius": 5,
                "position": {"x": 60, "y": 15},
                "isSensor": True  # 传感器，不产生碰撞力
            },
            {"id": "ground", "type": "static", "shape": "box", "size": {"width": 80, "height": 2},
             "position": {"x": 40, "y": 1}}
        ],
        "joints": []
    }

    scene_data, error = compiler.compile_scene(full_mcp_payload)

    if error:
        print(f"编译失败: {error}")
    else:
        import json

        print("编译成功! 生成的Planck.js场景数据:")

        # 将数据格式化为带缩进的JSON字符串
        json_output = json.dumps(scene_data, indent=2)

        # 仍然在控制台打印输出
        print(json_output)

        # --- 新增的文件保存逻辑 ---
        output_filename = "scene_output.json"
        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(json_output)
            print(f"\n[成功] 输出结果已成功保存到当前路径下的文件: {output_filename}")
        except Exception as e:
            print(f"\n[错误] 保存文件时发生错误: {e}")