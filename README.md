# fiber-link-workspace

Meta-repository for orchestrating the fiber-link simulation + ML ecosystem.

This workspace coordinates four repositories:

- `phys-pipeline` (execution engine)
- `fiber-link-sim` (deterministic physics simulation)
- `phys-sims-utils` (ML + optimization utilities)
- `fiber-link-testbench` (integration and experiment layer)

The workspace itself does **not** vendor those repositories; it bootstraps them into `deps/`.

## Architecture at a glance

Core integration contract:

```text
SimulationSpec
  -> simulate()
  -> SimulationResult.summary
```

The ML layer operates on `SimulationSpec` inputs and summary metrics outputs. The adapter is responsible for:

1. Accepting `config` + `seed`
2. Injecting deterministic seed (`spec.runtime.seed`)
3. Calling `simulate(spec)`
4. Extracting objective and metrics from `summary`
5. Returning `EvalResult`

Layer boundaries:

- Physics remains in `fiber-link-sim`
- ML logic and experiment orchestration live in `fiber-link-testbench`
- Execution/caching abstractions come from `phys-pipeline`

## Workspace setup

Bootstrap all dependencies into `deps/`:

```bash
python tools/bootstrap.py
```

If your network does not allow GitHub access, bootstrap may fail with partial checkout status.

## Recommended experiment modes

### 1) Sweep mode

Uses `InMemoryTestHarness` + `SweepSpec` to perform deterministic parameter exploration.

Expected artifacts include:

- `sweep_results.csv`
- heatmap plots

### 2) Optimization mode

Uses `ParameterSpace` + `OptimizationRunner` with a strategy such as Random, Sobol, or CMA-ES.

Expected artifacts include:

- `optimization_history.json`
- `convergence_plot.png`

### 3) Pipeline performance mode

Compare execution modes:

- Sequential
- DAG
- DAG + warm cache
- Parallel sweep

Validation goals:

- identical metrics/objective values across modes
- measurable runtime improvement from caching and parallelism

## Determinism and validation checklist

For reproducible runs:

- always set an explicit seed
- propagate seed into `SimulationSpec.runtime.seed`
- log configuration hash
- save generated artifacts

When upstream contracts change, re-validate downstream integrations:

- `fiber-link-sim` changes -> verify `SimulationResult.summary` keys and update adapter mapping if needed
- `phys-sims-utils` changes -> rerun sweep + optimization and verify `EvalResult` compatibility
- `phys-pipeline` changes -> rerun pipeline benchmarks and determinism checks

## Documentation

- Architecture and contract details: `docs/ml-integration-architecture.md`
- Integration plan and implementation guidance: `docs/integration-report.md`

These documents are the source of truth for boundaries, adapter expectations, and demonstration goals in this workspace.
