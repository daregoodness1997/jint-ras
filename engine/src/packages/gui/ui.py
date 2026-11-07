from __future__ import annotations

from math import pi
import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import matplotlib

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from packages.models.ras import SBRobot as _EngineSBRobot
from packages.models.jint import JRobot as _EngineJRobot
from packages.core.params import ras_params
from packages.dynamics.constraints import project_velocity


class SimulationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Snakeboard Simulation")

        # Create main frame
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)


def main():
    root = tk.Tk()
    app = SimulationGUI(root)
    app.create_menu()
    root.mainloop()


if __name__ == "__main__":
    main()
