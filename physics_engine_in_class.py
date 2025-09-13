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
    一个通用的物理场景编译器，将高阶MCP数据转换为Planck.js可用的低阶JSON格式。

    该类的核心职责是“翻译”，而非“理解”。它负责计算前端物理引擎所需的
    具体参数（例如，根据质量计算密度，根据物体位置计算滑轮绳长），并将用户
    在MCP中定义的标准物理属性直接传递给输出。

    Attributes:
        G (float): 默认的重力加速度 (m/s^2)。
    """

    def __init__(self, gravity_g: float = 9.8):
        """
        初始化编译器实例。

        Args:
            gravity_g (float, optional):
                一个可选参数，用于设定场景的默认Y轴重力。
                在创建不需要标准重力的场景（如太空模拟）时非常有用。
                默认为 9.8。
        """
        self.G = gravity_g

    def _calculate_density(self, obj: Dict[str, Any]) -> float:
        """
        根据物体的质量和形状尺寸计算其二维密度。

        Planck.js 的 Fixture 定义需要 `density` 属性，而用户提供 `mass` 更为直观。
        此方法负责完成这一转换。

        Args:
            obj (Dict[str, Any]):
                一个代表物体的字典，必须包含用于计算面积的键。
                - 对于 shape='box': 需要 `size: {'width': float, 'height': float}`
                - 对于 shape='circle': 需要 `radius: float`
                同时应包含 `mass: float` 键。

        Returns:
            float:
                计算出的密度值 (mass / area)。如果面积为零，则返回1.0以避免除零错误。
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
            area = 1.0  # 如果形状未知或缺失，则使用默认面积

        if area == 0:
            return 1.0
        return mass / area

    def _prepare_pulley_joint(self, joint_mcp: Dict[str, Any], objects_map: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据简化的MCP定义，计算Planck.js滑轮关节所需的完整参数。

        用户只需提供两个物体的ID和滑轮的锚点位置，此方法会自动计算出初始绳长等
        前端物理引擎必需的复杂参数。

        Args:
            joint_mcp (Dict[str, Any]):
                代表滑轮关节的MCP输入字典，包含:
                - `object_a_id` (str): 第一个物体的ID。
                - `object_b_id` (str): 第二个物体的ID。
                - `pulley_anchor_pos` (Dict): 滑轮在世界坐标系中的位置，如 `{'x': float, 'y': float}`。
                - `ratio` (float, optional): 滑轮传动比。

            objects_map (Dict[str, Any]):
                一个从对象ID映射到对象数据字典的查找表，用于快速获取物体的位置信息。

        Returns:
            Dict[str, Any]:
                一个包含完整滑轮关节参数的字典，可直接被前端使用。包括计算出的
                `length_a` 和 `length_b`。

        Raises:
            ValueError: 如果关节定义的 object_a_id 或 object_b_id 在 objects_map 中不存在。
        """
        obj_a_id = joint_mcp["object_a_id"]
        obj_b_id = joint_mcp["object_b_id"]

        if obj_a_id not in objects_map or obj_b_id not in objects_map:
            raise ValueError(f"为滑轮关节引用的对象ID不存在: {obj_a_id} 或 {obj_b_id}")

        pos_a = objects_map[obj_a_id]["position"]
        pos_b = objects_map[obj_b_id]["position"]
        pulley_pos = joint_mcp["pulley_anchor_pos"]

        # 根据物体中心到滑轮锚点的距离计算初始绳长
        length_a = np.sqrt((pos_a['x'] - pulley_pos['x'])**2 + (pos_a['y'] - pulley_pos['y'])**2)
        length_b = np.sqrt((pos_b['x'] - pulley_pos['x'])**2 + (pos_b['y'] - pulley_pos['y'])**2)

        # 返回前端 simulation.html 所需的完整结构
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
        将一个通用的MCP场景描述编译成一个可直接用于Planck.js的JSON对象。

        这是该类的主要公共方法。它接收一个符合MCP格式的字典，该字典描述了场景中
        所有物体、关节和世界属性。方法会处理需要计算的字段（如密度和绳长），并
        将所有其他Planck.js原生支持的物理属性直接传递。

        Args:
            mcp_data (Dict[str, Any]):
                一个遵循MCP格式的字典。其 `objects` 列表中的每个对象字典，除了
                必须的 `id`, `type`, `shape`, `position` 外，还可以包含以下
                所有符合 Planck.js BodyDef 和 FixtureDef 的可选属性:

                --- Body (运动学) 属性 ---
                - `angle` (float, optional): 初始角度 (单位: 度)。
                - `linearVelocity` (Dict, optional): 初始线速度, e.g., `{'x': 5, 'y': -2}`。
                - `angularVelocity` (float, optional): 初始角速度 (弧度/秒)。
                - `linearDamping` (float, optional): 线性阻尼。
                - `angularDamping` (float, optional): 角度阻尼。
                - `fixedRotation` (bool, optional): 是否固定旋转。
                - `bullet` (bool, optional): 是否为高速移动的“子弹”类型（用于防止穿透）。
                - `gravityScale` (float, optional): 重力缩放因子，可用于模拟反重力等效果。

                --- Fixture (材质/碰撞) 属性 ---
                - `mass` (float, optional): 质量（用于自动计算密度）。
                - `density` (float, optional): 密度（若提供，则优先于质量计算）。
                - `friction` (float, optional): 摩擦系数。
                - `restitution` (float, optional): 恢复系数（弹性）。
                - `isSensor` (bool, optional): 是否为传感器（可检测碰撞但不产生物理响应）。
                - `filterGroupIndex` (int, optional): 碰撞过滤组。
                - `filterCategoryBits` (int, optional): 碰撞类别。
                - `filterMaskBits` (int, optional): 碰撞掩码。

        Returns:
            Tuple[Optional[Dict[str, Any]], Optional[str]]:
                一个元组 `(scene_data, error)`。
                - 成功时: `scene_data` 是一个字典 `{"planck_scene": {...}}`，可被序列化为JSON。`error` 为 `None`。
                - 失败时: `scene_data` 为 `None`，`error` 是一个描述错误的字符串。
        """
        try:
            final_scene = {
                "world": mcp_data.get("world", {"gravity": {"x": 0, "y": -self.G}}),
                "objects": [],
                "joints": []
            }

            objects_map = {obj['id']: obj for obj in mcp_data.get("objects", [])}

            for obj_mcp in mcp_data.get("objects", []):
                # 复制所有用户提供的属性。这能确保所有Planck.js支持的属性
                # (如 angularVelocity, fixedRotation 等) 都能被直接传递。
                planck_obj = obj_mcp.copy()

                if planck_obj.get("type") == "dynamic":
                    # 仅当密度未被直接指定时，才根据质量计算密度。
                    if "mass" in planck_obj and "density" not in planck_obj:
                        planck_obj["density"] = self._calculate_density(planck_obj)
                    elif "density" not in planck_obj:
                        planck_obj["density"] = 1.0  # 提供一个默认值

                final_scene["objects"].append(planck_obj)

            for joint_mcp in mcp_data.get("joints", []):
                joint_type = joint_mcp.get("type")
                if joint_type == "PulleyJoint":
                    planck_joint = self._prepare_pulley_joint(joint_mcp, objects_map)
                    final_scene["joints"].append(planck_joint)
                else:
                    # 对于其他类型的关节，直接传递
                    final_scene["joints"].append(joint_mcp)

            return {"planck_scene": final_scene}, None

        except (KeyError, ValueError) as e:
            return None, f"处理MCP数据时出错：无效或缺失的键。详情: {str(e)}"
        except Exception as e:
            return None, f"场景编译器发生意外错误: {str(e)}"