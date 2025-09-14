import asyncio
import datetime
import inspect
import json
import re
from typing import Any, List, Dict, Union, get_args, get_type_hints, Callable, Optional


class FunctionRegistry:
    """
    一个用于注册和调用函数的注册器，支持生成符合主流LLM标准的函数描述（例如：火山引擎的MCP标准）。
    """

    def __init__(self):
        self._functions = {}  # 存储函数名称到函数对象的映射
        self._function_docs = {}  # 存储函数名称到函数详细信息的映射

    def _get_json_schema_type(self, py_type: Any) -> str:
        """根据Python类型获取对应的JSON Schema类型。"""
        if py_type is str:
            return "string"
        elif py_type is int or py_type is float:
            return "number"
        elif py_type is bool:
            return "boolean"
        elif py_type is list or py_type is List:
            return "array"
        elif py_type is dict or py_type is Dict:
            return "object"
        elif py_type is type(None):
            return "null"
        # 简化对 Union 类型的处理，只取第一个非 None 的类型
        elif hasattr(py_type, '__origin__') and py_type.__origin__ is Union:
            args = [arg for arg in get_args(py_type) if arg is not type(None)]
            if args:
                return self._get_json_schema_type(args[0])
            return "string"
        return "string"

    def _parse_docstring_params(self, docstring: Optional[str]) -> Dict[str, str]:
        """
        从Google风格的docstring中解析出参数描述。
        """
        if not docstring:
            return {}

        param_descriptions = {}
        # 匹配 Args: 或 Parameters: 下面的参数描述
        params_block_match = re.search(r'(?:Args|Parameters):\s*\n(.*?)(\n\n|$)', docstring, re.DOTALL)
        if params_block_match:
            params_block = params_block_match.group(1)
            # 匹配每一行 "参数名 (类型): 描述"
            param_line_pattern = re.compile(r'^\s*(\w+)\s*\(.*?\):\s*(.*)', re.MULTILINE)
            for line in params_block.split('\n'):
                match = param_line_pattern.match(line.strip())
                if match:
                    param_name = match.group(1).strip()
                    description = match.group(2).strip()
                    param_descriptions[param_name] = description

        return param_descriptions

    def register(self, func, func_tool_type: str = "function", func_tags: Optional[list] = None,
                 require_heartbeat: bool = False, func_metadata_: Optional[dict] = None):
        """
        注册一个函数到注册器中，并生成符合主流LLM标准的工具描述。

        param func: 要注册的函数
        param func_tool_type: 工具类型，默认为 "function"。
        param func_tags: 标签列表，默认为空列表。
        param require_heartbeat: 是否需要心跳，默认为 False。
        param func_metadata_: 自定义元数据，默认为 None。
        """
        if not callable(func):
            raise TypeError(f"'{func}' 不是一个可调用的对象，无法注册。")

        func_name = func.__name__
        if func_name in self._functions:
            print(f"警告: 函数 '{func_name}' 已存在，将被覆盖。")

        # 检查是否是类方法
        signature = inspect.signature(func)
        if signature.parameters and next(iter(signature.parameters)) == "self":
            raise AssertionError("不能注册类方法！请注册普通函数或静态方法。")

        self._functions[func_name] = func

        # 获取描述和参数描述
        full_docstring = inspect.getdoc(func)
        param_descriptions = self._parse_docstring_params(full_docstring)

        # 严格检查：如果函数有参数，但docstring中没有描述，则报错
        func_params = {name for name, param in signature.parameters.items() if param.default is inspect.Parameter.empty}
        if func_params and not param_descriptions:
            raise ValueError(
                f"函数 '{func_name}' 有参数，但docstring中未提供Google风格的参数描述。请使用 'Args:' 块来描述。")

        # 获取函数主描述
        description = full_docstring.strip().split('\n')[
            0].strip() if full_docstring else f"A function named {func_name}."

        type_hints = get_type_hints(func)

        parameters_properties = {}
        parameters_required = []

        for name, param in signature.parameters.items():
            param_type = type_hints.get(name, Any)
            json_schema_type = self._get_json_schema_type(param_type)

            # 使用 docstring 或默认描述
            param_description = param_descriptions.get(name, f"Parameter {name} of type {json_schema_type}.")

            parameters_properties[name] = {
                "type": json_schema_type,
                "description": param_description
            }

            if param.default is inspect.Parameter.empty:
                parameters_required.append(name)

        # 构建完整的 JSON Schema
        json_schema = {
            "name": func_name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": parameters_properties,
                "required": parameters_required
            },
            "type": func_tool_type,
            "heartbeat": require_heartbeat
        }

        now = datetime.datetime.now(datetime.timezone.utc)
        created_at = now.isoformat()
        updated_at = now.isoformat()

        # 补全 self._function_docs
        self._function_docs[func_name] = {
            "args_json_schema": parameters_properties,
            "created_at": created_at,
            "description": description,
            "json_schema": json_schema,
            "name": func_name,
            "return_char_limit": 1000000,
            "source_code": inspect.getsource(func) if inspect.isfunction(func) else None,
            "source_type": "python",
            "tags": func_tags if func_tags is not None else [],
            "tool_type": func_tool_type,
            "updated_at": updated_at,
            "heartbeat": require_heartbeat,
            "metadata_": func_metadata_
        }
        return func

    async def async_call(self, func_name_str: str, *args, **kwargs) -> Dict:
        """根据字符串名称调用已注册的异步函数。"""
        func = self._functions.get(func_name_str)
        if func is None:
            return {"result": "error", "status": "函数未找到"}
        if not inspect.iscoroutinefunction(func):
            return {"result": "error", "status": f"'{func_name_str}' 是同步函数，请使用 sync_call"}
        try:
            result = await func(*args, **kwargs)
            return {"result": result, "status": "success"}
        except TypeError as e:
            raise e
            return {"result": None, "status": f"参数错误: {e}"}
        except Exception as e:
            return {"result": "error", "status": f"注册函数内部错误: {e}"}

    def sync_call(self, func_name_str: str, *args, **kwargs) -> Dict:
        """根据字符串名称调用已注册的同步函数。"""
        func = self._functions.get(func_name_str)
        if func is None:
            return {"result": "error", "status": "函数未找到"}
        if inspect.iscoroutinefunction(func):
            return {"result": "error", "status": f"'{func_name_str}' 是异步函数，请使用 async_call"}
        try:
            result = func(*args, **kwargs)
            return {"result": result, "status": "success"}
        except TypeError as e:
            return {"result": None, "status": f"参数错误: {e}"}
        except Exception as e:
            return {"result": "error", "status": f"注册函数内部错误: {e}"}

    def __getattr__(self, name: str) -> Callable:
        """允许通过属性访问已注册的函数。"""
        if name in self._functions:
            return self._functions[name]
        raise AttributeError(f"'{self.__class__.__name__}' 对象没有名为 '{name}' 的属性或注册函数。")

    def list_functions_for_mcp(self) -> List[Dict]:
        """
        返回一个列表，其中包含所有已注册函数的 MCP 兼容的工具描述（JSON Schema）。
        """
        ret = [{"type": "function", "function": doc["json_schema"]} for doc in self._function_docs.values()]
        # print(ret)

        return ret

    def list_functions_detailed(self):
        """
        列出注册器中所有已注册函数的Schema，以美化后的JSON格式打印。
        """
        return json.dumps(self.list_functions_for_mcp(), indent=4, ensure_ascii=False)

    @property
    def functions(self):
        return self._functions


# --- 使用示例 ---
if __name__ == "__main__":
    my_registry = FunctionRegistry()


    def get_weather(city: str, date: str):
        """
        获取指定城市和日期的天气信息。
        :param city: 城市名称，如 "北京"、"上海"。
        :param date: 日期，格式为 "YYYY-MM-DD"。
        """
        print("执行同步函数 get_weather")
        return f"{city}在{date}的天气很好。"


    async def fetch_data(url: str):
        """
        模拟一个异步网络请求。
        :param url: 要请求的URL。
        """
        print(f"异步函数 fetch_data 开始执行，URL: {url}")
        await asyncio.sleep(1)
        print("异步函数执行完毕")
        return f"从 {url} 成功获取数据，耗时1秒。"


    # 注册函数，使用默认参数
    my_registry.register(get_weather)
    my_registry.register(fetch_data, require_heartbeat=True)

    print("\n--- 列出所有已注册函数的详细 Schema ---")
    print(my_registry.list_functions_detailed())

    # --- 测试调用 ---
    print("\n--- 测试同步调用 ---")
    sync_result = my_registry.sync_call("get_weather", city="北京", date="2025-08-05")
    print(sync_result)


    async def main():
        print("\n--- 测试异步调用 ---")
        async_result = await my_registry.async_call("fetch_data", url="http://example.com")
        print(async_result)


    asyncio.run(main())
