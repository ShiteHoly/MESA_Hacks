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
    api_key="AIzaSyANrcs-0RmCb3gdZEfTW8uocIWn7OGNPGU",
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
        result = psc.compile_scene(args)
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

@app.post("/api/query")
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
    response_json = []
    for tool_call in response.choices[0].message.tool_calls:
        name, result = execute_function_call(tool_call)
        response_json.append({name: result})
        context_manager.add_tool_result(result, tool_call.id)

    context_manager.add_assistant_response(response.choices[0].message.content or "")
    return response_json if response else {"error": "No response from LLM"}


# 兼容前端的 /api/assist 接口：返回 { "planck_scene": {...} }
class AssistRequest(BaseModel):
    query: str

@app.post("/api/assist")
async def assist(req: AssistRequest):
    q = (req.query or "").strip()
    if not q:
        return {"error": "Empty query"}

    # 将用户问题写入上下文
    context_manager.add_user_question(q)

    # 让 LLM 必须使用工具
    response = client.chat.completions.create(
        model="gemini-2.5-pro",
        messages=context_manager.get_prompt_for_llm(),
        tools=context_manager.function_desc_list,
        tool_choice="required"
    )

    planck_scene = None
    raw_results = []

    # 执行所有工具调用，并尝试抓取 compile_scene 的结果
    for tool_call in response.choices[0].message.tool_calls:
        name, result = execute_function_call(tool_call)
        raw_results.append({name: result})
        context_manager.add_tool_result(str(result), tool_call.id)

        if name == "compile_scene":
            try:
                scene_obj, err = result  # 由 PhysicsSceneCompiler.compile_scene 返回 (dict_or_none, err_or_none)
                if err is None and isinstance(scene_obj, dict):
                    # 既支持直接返回 planck_scene，也支持包在 {"planck_scene": {...}} 的形式
                    planck_scene = scene_obj.get("planck_scene") or scene_obj
            except Exception:
                # 忽略解析错误，继续尝试其它 tool_calls
                pass

    # 把助手回复也写入上下文（即使内容为空）
    context_manager.add_assistant_response(response.choices[0].message.content or "")

    if planck_scene is not None:
        return {"planck_scene": planck_scene}
    else:
        # 兜底：便于排错
        return {"error": "No planck_scene in tool results", "raw": raw_results}

    


# 运行：uvicorn main:app --host
# ===========================
if __name__ == "__main__":
    import uvicorn
    # 建议与 Vite 代理保持一致（vite.config.ts -> 127.0.0.1:5001）
    uvicorn.run(app, host="127.0.0.1", port=5001)
