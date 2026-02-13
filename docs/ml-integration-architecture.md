# ML Integration Architecture

Full technical reference:
See deep research report: 

This document defines the integration contract between:

- fiber-link-sim (physics)
- phys-sims-utils (ML)
- phys-pipeline (execution engine)
- fiber-link-testbench (integration layer)

---

# 1. System Model

SimulationSpec
    → simulate()
    → SimulationResult
        → summary dict
            → metrics

ML layer operates ONLY on:

- SimulationSpec inputs
- summary outputs

No other internal state may be assumed.

---

# 2. ML Integration Contract

The adapter must:

1. Accept:
   - config (dict)
   - seed (int)

2. Inject seed into:
   spec.runtime.seed

3. Call:
   simulate(spec)

4. Extract:
   summary["errors"]["post_fec_ber"] → objective
   summary["snr_db"]
   summary["evm_rms"]
   summary["latency_s"]

5. Return:
   EvalResult

If summary structure changes,
adapter must be updated.

---

# 3. Sweep Mode

Uses:
- InMemoryTestHarness
- SweepSpec

Produces:
- sweep_results.csv
- heatmap plots

Purpose:
Demonstrate deterministic param exploration.

---

# 4. Optimization Mode

Uses:
- ParameterSpace
- OptimizationRunner
- RandomStrategy / SobolStrategy / CMAESStrategy

Produces:
- optimization_history.json
- convergence_plot.png

Purpose:
Demonstrate ML-driven improvement of post_fec_ber.

---

# 5. phys-pipeline Demonstration Mode

Must benchmark:

- Sequential
- DAG
- DAG + warm cache
- Parallel sweep

Verify:
- Identical metrics
- Reduced runtime

---

# 6. Version Change Handling

When upstream changes:

## fiber-link-sim changes:
Re-run:
- single deterministic test case
- compare summary keys

If keys differ:
Update adapter mapping.

## phys-sims-utils changes:
Re-run:
- sweep
- optimization
Ensure EvalResult contract intact.

## phys-pipeline changes:
Re-run:
- performance benchmark
Ensure deterministic equivalence.

---

# 7. Design Philosophy

Physics is deterministic.
ML is external exploration.
Pipeline is execution abstraction.

Do not mix responsibilities.
