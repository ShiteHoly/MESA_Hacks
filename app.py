import streamlit as st
from math_plotter import handle_math_plotting
import json
from physics_engine import handle_physics_simulation

st.title("AI Assistant for Math and Physics")
st.write("This is a simple math and physics assistant.")
user_input = st.text_input("Enter your math or physics expression:")

if user_input:
    # 意图识别模块(V1.0基于关键词）
    # 增加了 'projectile' 关键词
    physics_keywords = ["kinetic energy", "potential energy", "force", "acceleration", "velocity", "mass", "distance", "time", "free falling","free fall", "projectile"]
    intent = "plot_function"

    for keyword in physics_keywords:
        if keyword in user_input.lower():
            intent = "simulate_physics"
            break #只要找到一个物理关键词，就确定意图便能够跳出循环

    st.write(f"Detected intent: {intent}")

    #任务发放
    if intent == "simulate_physics":
        st.info("Task has been assigned to the physics engine...")
        data, error = handle_physics_simulation(user_input)
    else: #默认处理数学函数
        st.info("Task has been assigned to the math plotting engine...")
        data, error = handle_math_plotting(user_input)

    # show result
    if data:
        content_displayed = False
        # Check if there's dynamic scene to show
        if isinstance(data, dict) and "planck_scene" in data:
            st.success("Dynamic simulation scene:")
            with open("simulation.html", "r", encoding="utf-8") as f:
                html_template = f.read()

            json_data = json.dumps(data["planck_scene"])
            final_html = html_template.replace("%%SCENE_DATA%%", json_data)
            st.components.v1.html(final_html, height=620)
            content_displayed = True

        #Check if there's matplotlib figure to show
        fig_to_plot = None
        if isinstance(data, dict) and "matplotlib_fig" in data:
            st.success("Matplotlib figure:")
            fig_to_plot = data["matplotlib_fig"]
        elif not isinstance(data, dict): #Being compatible with math plotter which only returns fig
            fig_to_plot = data

        if fig_to_plot:
            st.pyplot(fig_to_plot)
            content_displayed = True

        if not content_displayed:
            st.warning("Processing is over but No content to display.")

    elif error:
        st.error(error)