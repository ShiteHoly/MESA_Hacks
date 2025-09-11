import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import re
import sympy

# 1. 创建用户界面
st.title("AI function plotting")
st.write("Use natural language to decribe the function tou want to plot: like 'draw y = x**2'")

# 2. Get user's input
user_input = st.text_input("Enter your function description:")

if user_input:
    st.write(f"You entered: {user_input}")
    # Parse the input
    try:
        #默认范围
        x_min, x_max = -10, 10

        #定义正则表达式来找“从...到..."
        # \s* -> 匹配任意空格
        # (.*?)    -> 匹配任意字符 (非贪婪模式)，并将其捕获为一组
        range_pattern = re.compile(r"from\s*(.*?)\s*to\s*(.*)")
        match = range_pattern.search(user_input)
        expression_part = user_input# ?

        #如果找到了匹配的范围
        if match:
            # group(1)是第一个括号里的内容，group(2)是第二个
            x_min_str = match.group(1)
            x_max_str = match.group(2)

            # 使用sympy来解析数学表达式
            x_min = sympy.sympify(x_min_str).evalf()
            x_max = sympy.sympify(x_max_str).evalf()

            st.success(f"Range set to {x_min} to {x_max}")

            expression_part = range_pattern.sub('', user_input)
        else:
            expression_part = user_input
            st.info("Range not specified, using default range (-10, 10)")

        if 'y = ' in expression_part:
            expression_string = expression_part.split('y =')[-1].strip()
        else:
            expression_string = expression_part.strip()

        st.success(f"Successfully parsed expression part: y = {expression_part}")

        #使用sympy核心
        #定义符号
        x_sym = sympy.symbols('x')

        #将字符串转成sympy表达式 （sympy默认能理解cos,sin,pi,exp等等）
        expression = sympy.sympify(expression_string)

        #创建一个用于快速数值计算的函数
        #numpy参数能让它处理numpy数组
        f = sympy.lambdify(x_sym, expression, 'numpy')

        #生成x,y轴数据
        x = np.linspace(float(x_min), float(x_max), 100)
        y = f(x)
        #画图
        fig, ax = plt.subplots()
        ax.plot(x, y)
        ax.set_title(f"Graph: y = {expression_string}")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.grid(True)
        ax.axhline(0, color='black', linewidth=0.5)
        ax.axvline(0, color='black', linewidth=0.5)

        st.pyplot(fig)
        st.write("Graph generated successfully!")

    except Exception as e:
        st.error(f"Error parsing expression: {e}")