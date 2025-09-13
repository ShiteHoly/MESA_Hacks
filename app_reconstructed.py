"""AI-driven Math & Physics Visualization Assistant (Streamlit app)

This module is the top-level "orchestrator" that:
1) Presents a Streamlit UI for user input and visual outputs.
2) Performs intent detection to route the request to the correct engine:
   - If the input is a valid JSON matching the MCP format, it is sent to the physics engine.
   - Otherwise, it is sent to the math plotter.
3) Renders results as:
   - A dynamic Planck.js simulation by injecting JSON into `simulation.html`.
   - A static Matplotlib figure shown via `st.pyplot`.
If neither a scene nor a figure is produced, a warning is displayed.
"""

import streamlit as st
import json
from math_plotter import handle_math_plotting
from physics_engine_reconstructed_MCP_tools import build_scene_from_mcp

# Page title and short description for the app UI
st.title("AI Assistant for Math and Physics")
st.write("Enter a math function (e.g., 'y = sin(x) from -pi to pi') or a physics scene in MCP JSON format.")

# Multi-line text area is better for inputting JSON scene descriptions
user_input = st.text_area("Enter your math expression or physics scene description:")

if user_input:
    data, error = None, None
    intent = "unknown"

    # --- Intent Detection (V2.0: JSON-based) ---
    # Try to parse the input as JSON. If it works and has the right keys,
    # it's a physics request. Otherwise, it's a math request.
    try:
        mcp_payload = json.loads(user_input)
        # Validate that it looks like our MCP scene format
        if isinstance(mcp_payload, dict) and "world" in mcp_payload and "objects" in mcp_payload:
            intent = "simulate_physics_mcp"
    except json.JSONDecodeError:
        # If it's not valid JSON, it must be a math expression
        intent = "plot_function"

    st.write(f"Detected intent: {intent}")

    # --- Task Dispatch: physics engine vs. math plotter ---
    if intent == "simulate_physics_mcp":
        st.info("Task has been assigned to the physics scene compiler...")
        # The `build_scene_from_mcp` function directly returns the data dict and error
        data, error = build_scene_from_mcp(mcp_payload)
    else:  # Default path: process as a math function plotting request
        st.info("Task has been assigned to the math plotting engine...")
        fig, math_error = handle_math_plotting(user_input)
        if fig:
            # Standardize the output: wrap the figure in a dictionary
            # to make the rendering logic consistent.
            data = {"matplotlib_fig": fig}
        error = math_error

    # --- Render results, if any ---
    # This rendering logic is largely unchanged from the original version.
    if data:
        content_displayed = False

        # If a dynamic Planck.js scene is present, inject it into the HTML template and embed
        if isinstance(data, dict) and "planck_scene" in data:
            st.success("Dynamic simulation scene:")
            try:
                with open("simulation.html", "r", encoding="utf-8") as f:
                    html_template = f.read()

                # Replace placeholder with JSON-serialized scene data
                json_data = json.dumps(data["planck_scene"])
                final_html = html_template.replace("%%SCENE_DATA%%", json_data)

                # Show the interactive simulation in the Streamlit app
                st.components.v1.html(final_html, height=620)
                content_displayed = True
            except FileNotFoundError:
                st.error("Error: simulation.html template not found.")
            except Exception as e:
                st.error(f"An error occurred while rendering the simulation: {e}")

        # If a Matplotlib figure is present, render it
        if isinstance(data, dict) and "matplotlib_fig" in data:
            st.success("Matplotlib figure:")
            st.pyplot(data["matplotlib_fig"])
            content_displayed = True

        # If we received data but nothing was renderable, show a friendly message
        if not content_displayed:
            st.warning("Processing is over but No content to display.")

    elif error:
        # Show any error messages returned by the backends
        st.error(f"An error occurred: {error}")