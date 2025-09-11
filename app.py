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
        #默认范围
        x_min, x_max = -10, 10

        #定义正则表达式来找“从...到..."
        # \s* -> 匹配任意空格
        # (.*?)    -> 匹配任意字符 (非贪婪模式)，并将其捕获为一组
        range_pattern = re.compile(r"from\s*(.*?)\s*to\s*(.*)")
        match = range_pattern.search(user_input)

        #如果找到了匹配的范围
        if match:
            # group(1)是第一个括号里的内容，group(2)是第二个
            x_min_str = match.group(1)
            x_max_str = match.group(2)

            # 为了能处理像 'pi' 或 '-2*pi' 这样的输入, 我们用eval来计算范围值
            # 注意：这里我们信任用户输入的范围是安全的数学表达式
            x_min = eval(x_min_str, {'np': np, 'numpy': np, 'pi': np.pi})
            x_max = eval(x_max_str, {'np': np, 'numpy': np, 'pi': np.pi})

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

        x = np.linspace(float(x_min), float(x_max), 400)
        y = eval(expression_string, {'np': np, 'numpy': np, 'x':x, 'pi': np.pi})

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