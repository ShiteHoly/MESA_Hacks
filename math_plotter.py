import numpy as np
import matplotlib.pyplot as plt
import re
import sympy

def handle_math_plotting(user_input):
    try:
        #默认范围
        x_min, x_max = -10.0, 10.0

        #定义正则表达式来找“从...到..."
        # \s* -> 匹配任意空格
        # (.*?)    -> 匹配任意字符，并将其捕获为一组
        range_pattern = re.compile(r"(?:从|from)\s*(.*?)\s*(?:到|to)\s*(.*)", re.IGNORECASE)
         #在用户输入中搜索范围
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

            expression_part = range_pattern.sub('', user_input)
        else:
            expression_part = user_input

        #使用正则表达式分割多个函数表达式
        split_expressions = re.split(r'\s*and\s*|\s*&\s*|,\s*', expression_part)

        #清理每个分割出的表达式
        clean_expressions = []
        for expr in split_expressions:
            if 'y =' in expr:
                clean_expr = expr.split('y =')[-1].strip()
            elif 'y=' in expr:
                clean_expr = expr.split('y=')[-1].strip()
            else:
                clean_expr = expr.strip()

            if clean_expr:
                clean_expressions.append(clean_expr)
        if not clean_expressions:
            return None, "Sorry, I cannot handle this request yet."

        #使用sympy核心
        #定义符号
        x_sym = sympy.symbols('x')
        x = np.linspace(float(x_min), float(x_max), 400)

        fig, ax = plt.subplots()

        #循环绘制每一个函数
        for expression_str in clean_expressions:
            expression = sympy.sympify(expression_str)
            f = sympy.lambdify(x_sym, expression, 'numpy')
            y = f(x)
            y[np.isinf(y)] = np.nan  #处理无穷大
            ax.plot(x, y, label=f'y = {expression_str}') #绘制曲线+标签

        #设置图像显示并显示            ax.set_title("Function Plot")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.grid(True)
        ax.axhline(0, color='black', linewidth=0.5)
        ax.axvline(0, color='black', linewidth=0.5)
        ax.legend()

        return fig, None

    except Exception as e:
        return None, str(e)