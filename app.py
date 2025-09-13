"""AI-driven Math & Physics Visualization Assistant (Streamlit app)

This module is the top-level "orchestrator" that:
1) Presents a Streamlit UI for natural-language input and visual outputs.
2) Performs a simple keyword-based intent detection to route the request
   to either the math plotter or the physics scene builder.
3) Renders results as:
   - A dynamic Planck.js simulation by injecting JSON into `simulation.html`.
   - A static Matplotlib figure shown via `st.pyplot`.
If neither a scene nor a figure is produced, a warning is displayed.
"""

import streamlit as st
from math_plotter import handle_math_plotting
import json
from physics_engine import handle_physics_simulation

# Page title and short description for the app UI
st.title("AI Assistant for Math and Physics")
st.write("This is a simple math and physics assistant.")

# Single-line natural-language input used to request either math plots or physics simulations
user_input = st.text_input("Enter your math or physics expression:")

if user_input:
    # Intent detection module (V1.0: keyword-based)
    # If any of these physics-related keywords are present, route to physics simulation.
    physics_keywords = ["kinetic energy", "potential energy", "force", "acceleration",
                        "velocity", "mass", "distance", "time", "free falling",
                        "free fall", "projectile", "pulley"]  # includes 'pulley'
    intent = "plot_function"

    for keyword in physics_keywords:
        if keyword in user_input.lower():
            intent = "simulate_physics"
            break  # As soon as one physics keyword is found, we can stop searching

    st.write(f"Detected intent: {intent}")

    # Task dispatch: physics engine vs. math plotter
    if intent == "simulate_physics":
        st.info("Task has been assigned to the physics engine...")
        data, error = handle_physics_simulation(user_input)
    else:  # Default path: process as a math function plotting request
        st.info("Task has been assigned to the math plotting engine...")
        data, error = handle_math_plotting(user_input)

    # Render results, if any
    if data:
        content_displayed = False

        # If a dynamic Planck.js scene is present, inject it into the HTML template and embed
        if isinstance(data, dict) and "planck_scene" in data:
            st.success("Dynamic simulation scene:")
            with open("simulation.html", "r", encoding="utf-8") as f:
                html_template = f.read()

            # Replace placeholder with JSON-serialized scene data
            json_data = json.dumps(data["planck_scene"])
            final_html = html_template.replace("%%SCENE_DATA%%", json_data)

            # Show the interactive simulation in the Streamlit app
            st.components.v1.html(final_html, height=620)
            content_displayed = True

        # If a Matplotlib figure is present, render it
        fig_to_plot = None
        if isinstance(data, dict) and "matplotlib_fig" in data:
            st.success("Matplotlib figure:")
            fig_to_plot = data["matplotlib_fig"]
        elif not isinstance(data, dict):  # Back-compat: math_plotter may return just a Figure
            fig_to_plot = data

        if fig_to_plot:
            st.pyplot(fig_to_plot)
            content_displayed = True

        # If we received data but nothing was renderable, show a friendly message
        if not content_displayed:
            st.warning("Processing is over but No content to display.")

    elif error:
        # Show any error messages returned by the backends
        st.error(error)
