import asyncio
import inspect
from typing import Dict, Any
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import FunctionRegistry
from ..src.LuminiLLMRecvDataParsed import LuminiFunctionCall


class FunctionCallExecutor:
    """
    负责接收函数调用指令，并委托给 FunctionRegistry 来执行具体的函数。
    它封装了完整的 MCP 工具调用和结果处理逻辑，支持同步和异步调用。
    """

    def __init__(self, registry: FunctionRegistry):
        self._registry = registry

    async def execute_function_call(self, function_call_data: LuminiFunctionCall) -> Dict[str, Any]:
        # print(f"debug: FCR recv type: {type(function_call_data)}")
        tool_name = function_call_data.tool_name
        tool_input = function_call_data.tool_input
        tool_calls_id = function_call_data.tool_calls_id
        tool_calls_type = function_call_data.tool_calls_type

        return_dict: Dict[str, Any] = {
            "tool_name": tool_name,
            "status": "error",
            "result": f"错误：注册器中找不到名为 '{tool_name}' 的工具。"
        }
        print(f"v v v\n\tdebug - func call exec：{function_call_data}")

        # 检查函数是否存在
        if tool_name not in self._registry.functions:
            return return_dict

        func_to_call = self._registry.functions[tool_name]

        try:
            # 根据函数类型选择调用方式
            if inspect.iscoroutinefunction(func_to_call):
                # 如果是异步函数，使用 await 直接调用
                result = await self._registry.async_call(tool_name, **tool_input)
            else:
                # 如果是同步函数，使用 asyncio.to_thread 在后台线程中运行，以避免阻塞事件循环
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    None,  # 默认的线程池执行器
                    lambda: self._registry.sync_call(tool_name, **tool_input)
                )

            # 封装并返回结果
            # those 2 lines look a kind of tang, but i am too lazy to optimize it xoxo
            return_dict["result"] = result["result"]
            return_dict["status"] = result["status"]

            print(f"\tdebug - func call exec result：{result}\n^ ^ ^")

            return return_dict
        except Exception as e:
            # 捕获调用过程中发生的任何错误
            print(f"执行器：调用工具 '{tool_name}' 时发生意外错误: {e}")
            raise e
            return_dict["result"] = e
            return return_dict

    @property
    def registry(self):
        return self._registry

# # --- 使用示例 ---
# # 为了测试方便，我们定义一个独立的执行器主函数
# async def executor_main():
#     """
#     演示如何使用 FunctionCallExecutor。
#     """
#     print("--- 演示 FunctionCallExecutor ---")
#
#     # 1. 准备 FunctionRegistry 和一些函数
#     my_registry = FunctionRegistry()
#
#     def add(a: int, b: int) -> int:
#         """加法函数"""
#         return a + b
#
#     my_registry.register(add, func_tool_type="custom", func_tags=[], require_heartbeat=False)
#
#     async def fetch_data(url: str):
#         """异步函数，模拟网络请求"""
#         print("正在异步获取数据...")
#         await asyncio.sleep(0.5)
#         return {"data": "这是异步获取的数据"}
#
#     my_registry.register(fetch_data, func_tool_type="custom", func_tags=[], require_heartbeat=True)
#
#     # 2. 创建 FunctionCallExecutor 实例，并注入注册器
#     executor = FunctionCallExecutor(registry=my_registry)
#
#     # 3. 模拟 LLM 解析出的工具调用数据（LuminiFunctionCall）
#     sync_call_data = LuminiFunctionCall(
#         tool_name="add",
#         tool_input={"a": 10, "b": 20},
#         heartbeat=False
#     )
#     async_call_data = LuminiFunctionCall(
#         tool_name="fetch_data",
#         tool_input={"url": "http://example.com/api"},
#         heartbeat=True
#     )
#     invalid_call_data = LuminiFunctionCall(
#         tool_name="non_existent_tool",
#         tool_input={},
#         heartbeat=False
#     )
#
#     # 4. 执行函数调用并获取 MCP 格式的结果
#     print("\n-- 测试同步函数调用 --")
#     sync_result = await executor.execute_function_call(sync_call_data)
#     print("返回的 MCP 结果:", sync_result)
#
#     print("\n-- 测试异步函数调用 --")
#     async_result = await executor.execute_function_call(async_call_data)
#     print("返回的 MCP 结果:", async_result)
#
#     print("\n-- 测试不存在的函数调用 --")
#     invalid_result = await executor.execute_function_call(invalid_call_data)
#     print("返回的 MCP 结果:", invalid_result)
#
#
# if __name__ == "__main__":
#     asyncio.run(executor_main())
