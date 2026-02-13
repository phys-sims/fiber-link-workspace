# AGENTS (fiber-link-workspace)

## Purpose

This repository orchestrates the **fiber-link ML + simulation ecosystem**:

- phys-pipeline
- phys-sims-utils (formerly research-utils)
- fiber-link-sim
- fiber-link-testbench

This workspace exists to:

1. Integrate deterministic simulation (fiber-link-sim)
2. Integrate ML harness + optimization (phys-sims-utils)
3. Demonstrate phys-pipeline performance and reproducibility
4. Provide an agent-operable experiment environment

This repo DOES NOT vendor dependencies.
It materializes them into `deps/` via bootstrap.

---

## Repository Roles

### 1. phys-pipeline
Core execution engine.
Provides:
- SequentialPipeline
- DAG execution
- Caching
- Deterministic stage semantics

Breakage here affects EVERYTHING downstream.

---

### 2. phys-sims-utils
ML + experiment layer.
Provides:
- ParameterSpace
- SweepSpec
- OptimizationRunner
- SimulationEvaluator
- PhysPipelineAdapter
- TestHarness

Breakage here affects:
fiber-link-testbench only.

---

### 3. fiber-link-sim
Physics layer.
Provides:
- SimulationSpec → SimulationResult contract
- simulate()
- summary metrics (post_fec_ber, snr_db, etc.)
- pipeline_execution abstraction

Breakage here affects:
fiber-link-testbench and ML adapter.

---

### 4. fiber-link-testbench
Integration layer.
Demonstrates:
- Sweeps
- Optimization
- Artifact generation
- phys-pipeline caching benchmarks
- Deterministic reproducibility

This is where ML logic lives.
DO NOT put ML logic inside fiber-link-sim.

---

## Dependency Chain (Breakage Risk Direction)

fiber-link-testbench  
    → phys-sims-utils  
    → fiber-link-sim  
    → phys-pipeline  

If you change an upstream contract, check all downstream repos.

---

## Workspace Rules

- Never commit `deps/`
- Never modify upstream repos from inside the testbench unless task explicitly requires it
- Always search downstream usages before modifying upstream APIs

---

## First Action on Any Task

1. Ensure workspace exists:
   - `ls deps/`
2. If missing:
   - `python tools/bootstrap.py`

Do not continue without a valid workspace.

---

## Where ML Logic Belongs

ML parameterization, sweep logic, and optimization must live in:

deps/fiber-link-testbench/

Adapters live there.

Do NOT:
- Modify fiber-link-sim to add ML logic
- Add experiment logic into phys-sims-utils

Keep layers clean.

---

## Adapter Contract (Critical)

The ML layer assumes:

SimulationSpec (dict-like)
    → simulate()
    → SimulationResult.summary

The Adapter must:
- Inject deterministic seed
- Extract objective
- Return EvalResult

If fiber-link-sim changes summary structure,
update adapter FIRST.

---

## Cross-Repo Change Protocol

When changing:

### phys-pipeline
Check:
- fiber-link-sim pipeline_execution.py
- Any adapter using SequentialPipeline

### fiber-link-sim
Check:
- SimulationResult.summary structure
- simulate() signature
- seed handling
- summary metric keys

Then update:
- fiber-link-testbench adapter
- ML metric_extractors

### phys-sims-utils
Check:
- Adapter signature
- EvalResult structure
- ParameterSpace encode/decode

Then update:
- fiber-link-testbench experiment scripts

---

## Performance Testing Protocol

When modifying pipeline execution:

Test:

- Sequential mode
- DAG mode
- DAG + cache warm
- Parallel sweep

Verify:
- Metrics identical across modes
- Objective identical
- Speed improvements measurable

---

## Determinism Rule

All experiments must:

- Set seed explicitly
- Propagate seed into SimulationSpec.runtime.seed
- Log config hash
- Save artifacts

If determinism breaks:
Stop and fix before continuing.

---

## Agent Efficiency

- Use ripgrep (`rg`) before opening large files
- Avoid reading schema JSON unless modifying spec
- Avoid reading artifact outputs

---

## Expected Outputs from Testbench

Each experiment must produce:

- sweep_results.csv
- optimization_history.json
- convergence_plot.png
- performance_table.json

CI must validate their existence.

---

## Meta-Repo Responsibility

This workspace is responsible for:

- Coordinating version compatibility
- Defining integration contracts
- Maintaining ML + physics boundary clarity
- Preventing architecture drift

It is NOT a dumping ground for scripts.

---

## If Unsure

Default to:

- Modify testbench layer
- Preserve physics layer purity
- Preserve pipeline abstraction
