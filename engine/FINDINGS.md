# RAS/JINT/LORENZ/ROSSLER Periodicity Tuning — Findings

## Core finding

**Two notions of "periodic":**

1. **Section-periodic** — Poincare return map on a section collapses to one fixed point (the observed variable repeats).
2. **Fully-periodic** — Lyapunov spectrum has exactly one zero exponent, rest negative, Kaplan-Yorke dimension ≈ 1, classification "Periodic (Limit Cycle)".

A system can be section-periodic (rotor repeats on the Poincare section) but still chaotic in the full state (positive Lyapunov exponents in unobserved dimensions). This is why a config can report a clean Poincare fixed point yet classify as "Chaotic".

## Algorithms (now follow the reference implementation)

### Lyapunov exponents (`lyapunov.py`)
1. Integrate a **transient** to settle onto the attractor; use final state as IC.
2. Propagate tangent vectors with **forward-Euler**: `V <- V + dt * (J @ V)`.
3. **QR reorthonormalize** each step; accumulate `log|diag(R)|`.
4. Divide by **total compute time** at the end.
5. Classification:
   - >0 positive exponents + negative sum + non-integer dim → "Chaotic (Fractal Attractor)"
   - exactly 1 zero, 0 positive, integer dim → "Periodic (Limit Cycle)"
   - all negative, integer dim → "Stable (Fixed Point)"

### Bifurcation diagrams (`bifurcate.py`)
1. **Transient integration** (`t_transient`) → settle onto attractor.
2. **Compute integration** (`t_compute`) from transient end state.
3. Find **local maxima of x₀** via `dx/dt` sign change:
   `maxima_idx = np.where((dx_dt[:-1] > 0) & (dx_dt[1:] < 0))[0]`
4. Plot **parameter vs local maxima of x₀**.

### Poincare section (`poincare.py`)
1. **Transient integration** → settle onto attractor.
2. **Compute integration** → sample attractor.
3. Detect plane crossings with **linear interpolation** (reference style).
4. Project onto other dimensions.

## Verified classifications

| Model | Params | Exponents | Dimension | Classification |
|-------|--------|-----------|-----------|----------------|
| ROSSLER | a=0.2, b=0.2, c=2.5 | [-0.056, -0.019, -2.96] | 0.0 | Periodic (Limit Cycle) |
| ROSSLER | a=0.2, b=0.2, c=5.7 | [0.190, 0.020, -8.36] | 2.03 | Chaotic (Fractal Attractor) |
| LORENZ | sigma=10, rho=28, beta=8/3 | [1.74, 0.67, -22.86] | 2.11 | Chaotic (Fractal Attractor) |
| LORENZ | sigma=10, rho=10, beta=8/3 | [-0.62, -0.58, -19.2] | 0.0 | Stable (Fixed Point) |

## Parameter tuning rules

**For all models:**
- `rho_deg_s = 0` — any drift makes it quasi-periodic, not periodic
- Use `transient` to let the system settle before analysis
- Sweep parameters to find where Lyapunov classification flips

**For RAS/JINT snakeboards:**
- Lower `A_deg` reduces stopper impacts (main chaos source)
- Higher `Kp`/`Kd` tracks the sinusoidal rotor reference tighter
- Lower `Ks` softens stopper collisions
- Sweep `f` around 1.0–1.4 Hz for resonance lock-in

**For ROSSLER:**
- `c` is the main bifurcation parameter: small c (~2–4) periodic, c≈4.2+ period-doubling to chaos, c=5.7 classic chaotic
- `a` and `b` also affect the route to chaos

**For LORENZ:**
- `rho` is the main bifurcation parameter: rho < ~24.7 stable fixed points, rho > ~24.7 chaos

## Files

- `tune_generic.py` — single-config run: Poincare + Lyapunov, saves PNGs. Supports `--transient`.
- `bifurcate.py` — bifurcation diagrams (local maxima of x₀ vs parameter). Supports `--t-transient`, `--t-compute`.
- `poincare_create_section()` — reference-style Poincare section API.
- PNGs: `poincare_*.png`, `lyapunov_*.png`, `bifurcation_*.png`

## Example commands

```bash
# Generic tuning (any model) with transient
PYTHONPATH=src poetry run python tune_generic.py --model ROSSLER --a 0.2 --b 0.2 --c 2.5 --transient 50 --duration 50 --tag rossler_periodic

# Bifurcation: Rossler vs c (period-doubling route to chaos)
PYTHONPATH=src poetry run python bifurcate.py --model ROSSLER --param c --start 2 --stop 7 --step 0.1 --a 0.2 --b 0.2 --t-transient 10 --t-compute 30 --dt 0.01 --tag rossler_c

# Bifurcation: Lorenz vs rho
PYTHONPATH=src poetry run python bifurcate.py --model LORENZ --param rho --start 20 --stop 100 --step 1 --sigma 10 --beta 2.6667 --t-transient 10 --t-compute 30 --dt 0.01 --tag lorenz_rho

# Bifurcation: RAS vs amplitude (Poincare radius via local maxima of x0)
PYTHONPATH=src poetry run python bifurcate.py --model RAS --param A_deg --start 5 --stop 30 --step 2 --f 1.2 --Kp 30 --Kd 1.5 --Ks 200 --Bs 5 --rho-deg-s 0 --t-transient 10 --t-compute 30 --dt 0.01 --tag ras_A
```
