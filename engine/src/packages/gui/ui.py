from __future__ import annotations

from math import pi
import numpy as np
from PySide6 import QtCore, QtWidgets, QtGui
import sys
import os
import random

from packages.models.ras import SBRobot as _EngineSBRobot
from packages.models.jint import JRobot as _EngineJRobot
from packages.core.params import ras_params
from packages.dynamics.constraints import project_velocity


class SimulationGUI(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Snakeboard Simulation")

        self.hello = ["Hallo Welt", "Hei maailma", "Hola Mundo", "Привет мир"]

        self.button = QtWidgets.QPushButton("Click me!")
        self.text = QtWidgets.QLabel("Hello World", alignment=QtCore.Qt.AlignCenter)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.text)
        self.layout.addWidget(self.button)

        # Create main frame


def main():
    app = QtWidgets.QApplication([])
    gui = SimulationGUI()
    gui.resize(800, 600)
    gui.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
