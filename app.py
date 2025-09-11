import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import re

# 1. 创建用户界面
st.title("AI function plotting")
st.write("Use natural language to decribe the function tou want to plot: like 'draw y = x**2'")

# 2. Get user's input
user_input = st.text_input("Enter your function description:")

if user_input:
    st.write(f"You entered: {user_input}")
    # Parse the input
    try:
        # 我们假设函数表达式在 "y =" 之后
        # .split('y =') 会把字符串分成两部分, [-1] 取后一部分
        # .strip() 去掉首尾的空格
        expression_string = user_input.split("y =")[-1].strip()
        st.write(f"Expression string: {expression_string}")

        x = np.linspace(-10,10,400)
        y = eval(expression_string, {'np':np,'numpy':np, 'x':x})

        fig, ax = plt.subplots()
        ax.plot(x, y)
        ax.set_title(f"Graph: y = {expression_string}")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.grid(True)

        st.pyplot(fig)
        st.write("Graph generated successfully!")

    except Exception as e:
        st.error(f"Error parsing expression: {e}")