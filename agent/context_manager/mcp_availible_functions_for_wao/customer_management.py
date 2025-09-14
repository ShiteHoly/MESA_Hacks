# customer_management.py

# --- MCP 工具函数 ---
def send_message(content: str) -> str:
    """Show a message to the user, it is also the only way to let the user see your text response

    当大模型需要对用户说话时，必须调用此函数。此函数会终止与大模型的交互，
    并将 'content' 文本转换为语音并播放给顾客，直到顾客再次输入，交互才回到大模型。

    Args:
        content (str): What you want to response to the user.

    Returns:
        dict: A dict about sending status, for instance: {'status': 'success'}。
    """
    print(f"[CUSTOMER_MGMT] 发送消息: {content}")
    # this function in-fact is a mockup, by identifying it's called by MCP, llm_module itself sent the message.
    # ...
    return content


# --- 测试部分 ---
if __name__ == "__main__":
    from LLM_Module.agent.function_call.FunctionRegistry import FunctionRegistry

    print("===== 开始 customer_management.py 功能测试 =====")

    my_registry = FunctionRegistry()

    print("\n--- 注册 customer_management 函数 ---")

    my_registry.register(
        send_message,
        func_tool_type="customer_management",
        require_heartbeat=True,
        func_tags=["顾客交互", "语音输出"],
        func_metadata_={"purpose": "大模型对顾客说话", "output_channel": "voice"}
    )
    my_registry.register(
        guide_customer_queue,
        require_heartbeat=True,
        func_tool_type="customer_management",
        func_tags=["顾客交互", "排队", "疏导"],
        func_metadata_={"purpose": "引导过多顾客排队", "trigger_condition": "user_count_high"}
    )

    print("\n--- 注册器中的详细函数信息 (JSON Schema) ---")
    my_registry.list_functions_detailed()

    print("\n--- 通过注册器调用 customer_management 函数示例 ---")

    # 调用 display_menu
    print("\n调用 display_menu():")
    menu_result = my_registry.sync_call("display_menu")
    print(f"菜单内容获取成功: {menu_result.get('status')}")
    # print(json.dumps(menu_result.get('return'), indent=2, ensure_ascii=False)) # 如果需要打印完整菜单

    # 调用 send_message
    print("\n调用 send_message('您好，请问有什么可以帮助您的？'):")
    message_result = my_registry.sync_call("send_message", content="您好，请问有什么可以帮助您的？")
    print(f"消息发送状态: {message_result.get('status')}")

    print("\n调用 send_message('请看屏幕上的特价优惠哦！', data={'image': 'special_offer.jpg'}):")
    message_with_data_result = my_registry.sync_call("send_message", content="请看屏幕上的特价优惠哦！",
                                                     data={'image': 'special_offer.jpg'})
    print(f"带数据消息发送状态: {message_with_data_result.get('status')}")

    # 调用 guide_customer_queue
    print("\n调用 guide_customer_queue(3):")
    queue_result = my_registry.sync_call("guide_customer_queue", current_user_count=3)
    print(f"排队引导状态: {queue_result.get('status')}")

    print("\n--- customer_management 功能测试完成 ---")
