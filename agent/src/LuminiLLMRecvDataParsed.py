from typing import Optional, Dict, Any, Union, Tuple


class LuminiFunctionCall:
    """
    用于封装函数调用信息的子类，作为 LuminiLLMRecvDataParsed 的一部分。
    这个类可以直接传递给 FunctionCallExecutor。
    """

    def __init__(self,
                 tool_name: str,
                 tool_input: Dict[str, Any],
                 tool_calls_id: str,
                 tool_calls_type: str,
                 heartbeat: bool = True):
        """
        初始化 LuminiFunctionCall 实例。

        Args:
            tool_name (str): 大模型请求调用的函数名。
            tool_input (Dict[str, Any]): 函数调用的参数字典。
            tool_calls_id: parsed from LLM reply.
            tool_calls_type: only function for now, parsed from LLM reply.
            heartbeat (bool): 是否需要框架在执行此函数后发送后续请求给大模型。
                                          默认为 True，即只在明确需要时设为 False。
        """
        if not isinstance(tool_name, str) or not tool_name:
            raise ValueError("tool_name 必须是非空的字符串。")
        if not isinstance(tool_input, dict):
            raise TypeError("tool_input 必须是字典。")

        self.tool_name = tool_name
        self.tool_input = tool_input
        self.tool_calls_id = tool_calls_id
        self.tool_calls_type = tool_calls_type
        self.need_following_request = heartbeat

    def to_dict(self) -> Dict[str, Any]:
        """将实例转换为字典，方便序列化或调试。"""
        return {
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "need_following_request": self.need_following_request
        }

    def __repr__(self) -> str:
        return (f"LuminiFunctionCall(Name: '{self.tool_name}', "
                f"Params: {self.tool_input}, Need Follow-up: {self.need_following_request})")


class LuminiLLMRecvDataParsed:
    """
    统一的数据传输类，用于封装LLMParser解析后的数据。
    它可以包含 LuminiFunctionCall 子类实例。
    """

    def __init__(self,
                 response_type: str,
                 content: Dict[str, list],
                 tool_calls: Union[Tuple[LuminiFunctionCall, ...], LuminiFunctionCall, None] = None,
                 error_message: Optional[str] = None):
        if response_type not in ["text_response", "function_call", "multi_call", "error"]:
            raise ValueError("response_type must be one of 'text_response', 'function_call', 'multi_call', or 'error'")

        self.response_type = response_type
        self.content = content
        self.error_message = error_message

        # 严格校验 tool_calls 的类型
        if tool_calls is None:
            self.tool_calls = tuple()
        elif isinstance(tool_calls, LuminiFunctionCall):
            self.tool_calls = (tool_calls,)
        elif isinstance(tool_calls, (list, tuple)):
            for call in tool_calls:
                if not isinstance(call, LuminiFunctionCall):
                    raise TypeError("tool_calls 列表或元组中的所有元素都必须是 LuminiFunctionCall 实例。")
            self.tool_calls = tuple(tool_calls)
        else:
            raise TypeError(
                "tool_calls 必须是 LuminiFunctionCall 实例、可迭代的 LuminiFunctionCall 列表/元组，或 None。")

    def has_text_response(self) -> bool:
        """检查是否为文本回复。"""
        return self.response_type in ("text_response", "multi_call")

    def has_function_calls(self) -> bool:
        """检查是否包含函数调用。"""
        return self.response_type in ("function_call", "multi_call")

    def is_error(self) -> bool:
        """检查是否为错误。"""
        return self.response_type == "error"

    def to_dict(self) -> Dict[str, Any]:
        """将实例转换为字典，方便序列化或调试。"""
        data = {
            "response_type": self.response_type
        }
        if self.content is not None:
            data["content"] = str(self.content)
        if self.tool_calls:
            data["tool_calls"] = str(call.to_dict() for call in self.tool_calls)
        if self.error_message is not None:
            data["error_message"] = self.error_message
        return data

    def __repr__(self) -> str:
        return "\nLuminiLLMRecvDataParsed Instance Printed:\n" + self.to_dict().__repr__()+"\n"