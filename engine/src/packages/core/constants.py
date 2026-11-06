"""Shared constants and state layout."""

from __future__ import annotations

import numpy as np

# State layout: [q; qd], q = [X_i, Y_i, Q_i, O_i] for bodies 0..3
N_BODIES = 4
DOF_PER_BODY = 4
Q_START = 0
QD_START = 16
STATE_DIM = 32

# Indices
X0_IDX, Y0_IDX, Q0_IDX, O0_IDX = 0, 1, 2, 3
X1_IDX, Y1_IDX, Q1_IDX, O1_IDX = 4, 5, 6, 7
X2_IDX, Y2_IDX, Q2_IDX, O2_IDX = 8, 9, 10, 11
X3_IDX, Y3_IDX, Q3_IDX, O3_IDX = 12, 13, 14, 15

O3_IDX = 15
DO3_IDX = 31
Q0_IDX = 2
DQ0_IDX = 18

DEG = np.pi / 180.0
RAD = 180.0 / np.pi
