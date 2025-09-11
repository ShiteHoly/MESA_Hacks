import streamlit as st
from math_plotter import handle_math_plotting

# 我们稍后会从 physics_engine 导入函数
from physics_engine import handle_physics_simulation

st.title("AI Assistant for Math and Physics")
st.write("This is a simple math and physics assistant.")
user_input = st.text_input("Enter your math or physics expression:")

if user_input:
    # 意图识别模块(V1.0基于关键词）
    physics_keywords = ["kinetic energy", "potential energy", "force", "acceleration", "velocity", "mass", "distance", "time", "free falling", "projectile"]
    intent = "plot_function"

    for keyword in physics_keywords:
        if keyword in user_input:
            intent = "simulate_physics"
            break #只要找到一个物理关键词，就确定意图便能够跳出循环

    st.write(f"Detected intent: {intent}")

    #任务发放
    if intent == "simulate_physics":
        st.info("Task has been assigned to the physics engine...")
        fig, error = handle_physics_simulation(user_input)
    else: #默认处理数学函数
        st.info("Task has been assigned to the math plotting engine...")
        fig, error = handle_math_plotting(user_input)

    # show result
    if fig:
        st.pyplot(fig)
        st.success("Plotting completed successfully.")
    elif error:
        st.error(error)