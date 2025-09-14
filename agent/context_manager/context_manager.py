# context_manager.py

import json
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# print(sys.path)

# 其他工具函数
from mcp_availible_functions_for_wao.customer_management import (
    send_message,
)
from prompt_src import WAO_INSTRUCTIONS, WAO_EXAMPLES, WAO_KNOWLEDGE_, WAO_MEMORY_, \
    WAO_tool_results, WAO_TOOLS_
# 导入必要的模块和类
from ..function_call.FunctionCallExecutor import FunctionCallExecutor
from ..function_call.FunctionRegistry import FunctionRegistry
from ..src.LuminiLLMRecvDataParsed import LuminiLLMRecvDataParsed, LuminiFunctionCall
from ..src.listctl import OpenaiMessctl

# WAO后台服务
# from LLM_Module.Wao_Order.Wao import WaoOrderController
# 导入你的 OrderManagement 类
# from mcp_availible_functions_for_wao.OrderManagement import OrderManagement


class ContextManager:
    """
    负责管理会话状态、聊天历史和动态生成 LLM Prompt。
    同时负责订单json的维护。
    """

    def __init__(self, _function_executor: FunctionCallExecutor):
        """
        初始化 ContextManager 实例。
        Args:
            _function_executor (FunctionCallExecutor): 一个function executor实例。
        """
        # self.wao_order_controller = WaoOrderController(
        #     qrcode_base_dir=r'/home/gulee/Documents/GitHub/hikari_mirror/tmp_for_qrcode')
        # self.menu_dict = self.wao_order_controller.get_products_list()

        # self.order_manager = OrderManagement(_wao_order_controller=self.wao_order_controller)
        self.function_executor = _function_executor

        # 注册所有工具函数


        # 注册其他独立的函数
        self.function_executor.registry.register(send_message, func_tool_type="user_interact",
                                                 func_tags=["interact_with_user"], require_heartbeat=True)

        self.function_desc_list = self.function_executor.registry.list_functions_for_mcp()
        # 封装 OpenaiMessctl 来管理聊天历史
        # wao_tools = WAO_TOOLS_ + json.dumps(self.function_executor.registry.list_functions_for_mcp()) + "\n<\\TOOLS>"
        wao_tools = "You **MUST** use tools to reply or demonstrate to the user. Your reply without using tools are for **thinking only, will not be seen by the user**"

        wao_memory = WAO_MEMORY_ + "<\\MEMORY>"

        system_context = WAO_INSTRUCTIONS + "\n" + WAO_EXAMPLES + "\n" + "\n" + wao_memory + "\n" + WAO_tool_results + "\n" + wao_tools
        # print(f"debug: system_context: \n{system_context}")
        self._chat_history = OpenaiMessctl(
            definition=[{"role": "system", "content": system_context}]
        )

        # with open("mcp_funcs.json", "w") as f:
        #     json.dump(self.function_executor.registry.list_functions_for_mcp(), f, indent=4, ensure_ascii=False)
        # print("dumped mcp_funcs.json")

    def add_user_question(self, question: str):
        """
        添加用户的最新问题到聊天历史中。
        """
        # 记录用户提问的时间戳和内容，便于后续追踪
        formatted_question = f"{question}"
        self._chat_history.user_list_add(formatted_question, 'u')

    def add_assistant_response(self, response: str):
        """
        添加助手的最终回复到聊天历史中。
        """
        self._chat_history.user_list_add(response, 'a')

    def add_tool_call(self, tool_name: str, tool_input: dict):
        """
        将大模型发起的工具调用添加到历史中。
        这有助于大模型在多轮对话中理解自己的“行为”。
        """
        # 这是一个可选的步骤，但对于复杂的对话很有用
        self._chat_history.chat_list.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [{"function": {"name": tool_name, "arguments": json.dumps(tool_input)}}]
        })

    def add_tool_result(self, tool_result_str: str,
                        tool_call_id: str):
        """
        将工具调用结果封装成一个消息并添加到历史中，作为 LLM 的下一步输入。
        # todo: rebuild that shabi messagectl
        """
        appendance = {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": tool_result_str
        }
        self._chat_history.send_list.append(appendance)
        print(f"debug: done a tool call, append_tool_result: {appendance}")

    def get_prompt_for_llm(self) -> list:
        """
        生成最终用于发送给 LLM 的 Prompt 列表。
        """
        prompt = self._chat_history.send_list

        return prompt

    def clear_session(self):
        """
        清空当前会话的所有状态，为新会话做准备。
        system info excepted, sure! :p
        """
        self._chat_history.chat_list.clear()
        print("[CONTEXT] 会话状态已清空。")


if __name__ == '__main__':
    registry = FunctionRegistry()
    function_executor = FunctionCallExecutor(registry)
    context_manager = ContextManager(function_executor)
    print("here lies a master dark soul")
