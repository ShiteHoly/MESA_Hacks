from fastapi import FastAPI
from pydantic import BaseModel

from agent.context_manager.context_manager import ContextManager
from agent.function_call.FunctionCallExecutor import FunctionCallExecutor
from agent.function_call.FunctionRegistry import FunctionRegistry
func_registry = FunctionRegistry()
from physics_engine_in_class import PhysicsSceneCompiler
psc = PhysicsSceneCompiler()
func_registry.register(psc.compile_scene, "function", ["Visualize"], True)
func_executor = FunctionCallExecutor(registry=func_registry)
context_manager = ContextManager(_function_executor=func_executor)

for i in context_manager.function_desc_list:
    del i['function']["heartbeat"]
    del i['function']['type']

from openai import OpenAI

client = OpenAI(
    api_key="AIzaSyBfp6ltZJY5n8awibzocZ4H6rWGl5XI5h4",
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

import json
def execute_function_call(function_call):
    """
    执行函数调用，并返回结果字符串。
    Args:
        function_call (LuminiFunctionCall): 包含函数名称和参数的对象。
    Returns:
        str: 函数执行结果的字符串表示。
    """
    arguments, name = function_call.to_dict()['function'].values()
    if name == "send_message":
        return name, json.loads(arguments)['content']
    elif name == "compile_scene":
        args = json.loads(json.loads(arguments)['mcp_data'])
        result, err = psc.compile_scene(args)
        assert err is None, f"compile_scene error: {err}"
        return name, result

# --- FastAPI 应用设置 ---
app = FastAPI(lifespan=None)
from fastapi.middleware.cors import CORSMiddleware
# 添加CORS中间件
app.add_middleware(
CORSMiddleware,
allow_origins=["*"],
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
)
class query_request(BaseModel):
    query: str

@app.post("/api/assist")
async def query(req: query_request):
    q = (req.query or "").strip()
    if not q:
        return {"error": "Empty query"}
    context_manager.add_user_question(q)
    response = client.chat.completions.create(
        model="gemini-2.5-pro",
        messages=context_manager.get_prompt_for_llm(),
        tools=context_manager.function_desc_list,
        tool_choice="required"
    )
    response_json = dict()
    for tool_call in response.choices[0].message.tool_calls:
        name, result = execute_function_call(tool_call)
        response_json[name] = result
        # context_manager.add_tool_result(result, tool_call.id)

    # context_manager.add_assistant_response(response.choices[0].message.content or "")
    print(response_json)
    return response_json if response else {"error": "No response from LLM"}


# 运行：uvicorn main:app --host
# ===========================
if __name__ == "__main__":
    import uvicorn
    # 建议与 Vite 代理保持一致（vite.config.ts -> 127.0.0.1:5001）
    uvicorn.run(app, host="127.0.0.1", port=5001)
