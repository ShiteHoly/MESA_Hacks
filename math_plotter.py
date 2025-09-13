"""Mathematical function parsing and plotting with SymPy + NumPy + Matplotlib.

Responsibilities:
1) Optionally parse a plotting range for x (Chinese "从 … 到 …" or English "from … to …").
2) Split one or multiple function expressions (separated by commas, 'and', or '&').
3) Use SymPy to parse expressions, then lambdify them into NumPy-evaluable callables.
4) Plot the resulting functions with Matplotlib and return the figure object.

Examples:
- "Plot y = sin(x) from -3*pi to 3*pi"
- "y=x**2 and y=2*x+1, from -5 to 5"
- "从 -2 到 2, y = exp(x) & y = ln(x+3)"

Return value contract:
- Success: (Figure, None)
- Failure: (None, "<error message>")
"""

import numpy as np
import matplotlib.pyplot as plt
import re
import sympy


def handle_math_plotting(user_input):
    """Parse function expressions (optionally with a domain) and produce a Matplotlib plot.

    Parameters
    ----------
    user_input : str
        Natural-language text that may contain:
        - One or more expressions, e.g. "y = sin(x), y = cos(x)"
        - An optional domain spec in Chinese or English, e.g.
          "从 -3*pi 到 3*pi"  or  "from -3*pi to 3*pi"

    Returns
    -------
    tuple
        (figure_or_none, error_or_none)
        On success, returns (Matplotlib Figure, None).
        On failure, returns (None, "<error message>").
    """
    try:
        # Default x-range if none is specified
        x_min, x_max = -10.0, 10.0

        # Regex for extracting the range: supports "从 ... 到 ..." or "from ... to ..."
        # \s*  -> arbitrary whitespace
        # (.*?) -> non-greedy capture of any content
        range_pattern = re.compile(r"(?:从|from)\s*(.*?)\s*(?:到|to)\s*(.*)", re.IGNORECASE)
        # Take the whole input by default; if a range is found, we will remove it from this string
        match = range_pattern.search(user_input)
        expression_part = user_input  # keep a copy of the expression section

        # If a plotting range is present, parse both ends via SymPy and strip it from the expression text
        if match:
            x_min_str = match.group(1)
            x_max_str = match.group(2)

            # Allow symbolic constants like pi, e, etc.
            x_min = sympy.sympify(x_min_str).evalf()
            x_max = sympy.sympify(x_max_str).evalf()

            expression_part = range_pattern.sub('', user_input)
        else:
            expression_part = user_input

        # Split multiple expressions by comma, 'and', or '&'
        split_expressions = re.split(r'\s*and\s*|\s*&\s*|,\s*', expression_part)

        # Normalize each expression: remove optional 'y=' prefix and strip whitespace
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

        # If nothing usable was parsed, return a friendly error
        if not clean_expressions:
            return None, "Sorry, I cannot handle this request yet."

        # SymPy core: build a NumPy-evaluable function for each expression and plot it
        x_sym = sympy.symbols('x')
        x = np.linspace(float(x_min), float(x_max), 400)

        fig, ax = plt.subplots()

        # Plot each parsed function with a legend label
        for expression_str in clean_expressions:
            expression = sympy.sympify(expression_str)
            f = sympy.lambdify(x_sym, expression, 'numpy')
            y = f(x)
            # Replace infinities with NaN so Matplotlib won't draw vertical spikes
            y[np.isinf(y)] = np.nan
            ax.plot(x, y, label=f'y = {expression_str}')  # curve + legend label

        # Configure common axes details
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_title("Function Plot")
        ax.grid(True)
        ax.axhline(0, color='black', linewidth=0.5)
        ax.axvline(0, color='black', linewidth=0.5)
        ax.legend()

        return fig, None

    except Exception as e:
        # If parsing/evaluation fails, return the message for display in the UI
        return None, str(e)
