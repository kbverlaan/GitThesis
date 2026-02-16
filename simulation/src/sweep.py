"""
Generic parameter sweep runner.
Supports single-param sweeps and factorial (grid) designs.

Usage:
    python src/sweep.py experiments/baseline_replicability.yaml
    python src/sweep.py experiments/prompt_framing_factorial.yaml
"""

import sys
import json
import yaml
import time
import copy
import re
from itertools import product
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from main import run_simulation, save_results, load_config
from analysis.metrics import cooperation_ratio, first_attack_round


def load_experiment(spec_path: str) -> dict:
    """Load and validate experiment spec YAML."""
    with open(spec_path, 'r') as f:
        spec = yaml.safe_load(f)

    required = ['name', 'reps', 'base_params', 'sweep']
    for key in required:
        if key not in spec:
            raise ValueError(f"Experiment spec missing required key: '{key}'")

    sweep = spec['sweep']
    if 'grid' not in sweep:
        # Single-param mode: require param + values
        if 'param' not in sweep or 'values' not in sweep:
            raise ValueError("sweep must have 'param' and 'values', or 'grid'")

    return spec


def _sanitize_value(value) -> str:
    """Make a sweep value safe for use in run IDs."""
    s = str(value)
    # Strip common URL-like prefixes from model names
    s = s.split('/')[-1] if '/' in s else s
    # Replace unsafe characters
    s = re.sub(r'[^a-zA-Z0-9._-]', '_', s)
    return s


def generate_conditions(sweep: dict) -> list:
    """
    Generate list of conditions from sweep spec.

    Each condition is a list of dicts:
        [{'param': ..., 'target': ..., 'value': ...}, ...]

    For single-param sweeps, each condition has one entry.
    For grid sweeps, each condition is one combination from the Cartesian product.
    """
    if 'grid' in sweep:
        # Factorial design
        axes = sweep['grid']
        axis_values = []
        for axis in axes:
            param = axis['param']
            target = axis.get('target', 'game_params')
            values = axis['values']
            axis_values.append([
                {'param': param, 'target': target, 'value': v}
                for v in values
            ])
        # Cartesian product of all axes
        return [list(combo) for combo in product(*axis_values)]
    else:
        # Single-param sweep
        param = sweep['param']
        target = sweep.get('target', 'game_params')
        return [
            [{'param': param, 'target': target, 'value': v}]
            for v in sweep['values']
        ]


def condition_label(condition: list) -> str:
    """Human-readable label for a condition."""
    parts = []
    for entry in condition:
        parts.append(f"{entry['param']}={entry['value']}")
    return ", ".join(parts)


def condition_run_id(condition: list, rep: int) -> str:
    """Generate a run ID from a condition and rep number."""
    parts = []
    for entry in condition:
        parts.append(f"{entry['param']}_{_sanitize_value(entry['value'])}")
    return "_".join(parts) + f"_rep{rep}"


def apply_condition(condition: list, base_params: dict,
                    openrouter_config: dict) -> tuple:
    """
    Apply a condition's parameter overrides to copies of base_params
    and openrouter_config.

    Returns (game_params, openrouter_config) with overrides applied.
    """
    params = copy.deepcopy(base_params)
    or_config = copy.deepcopy(openrouter_config)

    for entry in condition:
        target = entry['target']
        param = entry['param']
        value = entry['value']

        if target == 'game_params':
            params[param] = value
        elif target == 'openrouter':
            or_config[param] = value
        elif target == 'prompt_config':
            if 'prompt_config' not in or_config:
                or_config['prompt_config'] = {}
            or_config['prompt_config'][param] = value
        else:
            raise ValueError(f"Unknown target '{target}' for param '{param}'")

    return params, or_config


def run_sweep(spec_path: str):
    """Run a full parameter sweep from an experiment spec."""
    load_dotenv()

    project_root = Path(__file__).parent.parent
    spec = load_experiment(spec_path)

    name = spec['name']
    reps = spec['reps']
    base_params = spec['base_params']
    description = spec.get('description', '')

    # Load OpenRouter config
    openrouter_config = load_config(project_root / "config" / "openrouter_config.yaml")

    # Apply base_openrouter overrides if present
    if 'base_openrouter' in spec:
        for key, value in spec['base_openrouter'].items():
            openrouter_config[key] = value

    # Generate conditions
    conditions = generate_conditions(spec['sweep'])

    # Output directory for this experiment
    output_dir = project_root / "data" / "runs" / name
    output_dir.mkdir(parents=True, exist_ok=True)

    total_runs = len(conditions) * reps

    print(f"\n{'='*70}")
    print(f"EXPERIMENT: {name}")
    print(f"{'='*70}")
    print(f"Description: {description}")
    print(f"Conditions: {len(conditions)}")
    print(f"Reps per condition: {reps}")
    print(f"Total runs: {total_runs}")
    print(f"Output: {output_dir}")
    print(f"{'='*70}\n")

    # Build sweep info for manifest
    sweep_info = spec['sweep']
    if 'grid' not in sweep_info:
        # Single-param: preserve old manifest fields for backward compat
        sweep_param = sweep_info['param']
        sweep_values = sweep_info['values']
    else:
        sweep_param = 'grid'
        sweep_values = [condition_label(c) for c in conditions]

    # Manifest tracks all runs
    manifest = {
        'name': name,
        'description': description,
        'sweep_param': sweep_param,
        'sweep_values': sweep_values,
        'sweep_spec': sweep_info,
        'reps': reps,
        'base_params': base_params,
        'started_at': datetime.now().isoformat(),
        'runs': [],
    }

    experiment_start = time.time()

    for condition in conditions:
        label = condition_label(condition)

        print(f"\n{'#'*70}")
        print(f"# CONDITION: {label}")
        print(f"{'#'*70}")

        condition_metrics = []

        for rep in range(1, reps + 1):
            run_id = condition_run_id(condition, rep)

            # Build params for this run
            params, or_config = apply_condition(
                condition, base_params, openrouter_config
            )

            print(f"\n--- {run_id} ---")
            run_start = time.time()

            state, traces, round_metrics = run_simulation(
                params, or_config, run_id
            )

            run_elapsed = time.time() - run_start

            # Save results into experiment subdirectory
            save_results(state, traces, round_metrics, output_dir, run_id)

            # Track in manifest
            final_gini = round_metrics[-1]['gini'] if round_metrics else None
            final_stability = round_metrics[-1].get('action_stability')

            # Aggregate action distribution across all rounds
            total_actions = {}
            for m in round_metrics:
                for action, count in m['action_distribution'].items():
                    total_actions[action] = total_actions.get(action, 0) + count

            top_action = max(total_actions, key=total_actions.get) if total_actions else None

            # Compute run-level metrics from history
            history = state.history
            coop_ratio = cooperation_ratio(history)
            first_attack = first_attack_round(history)

            # Condition value for manifest (backward compat for single-param)
            if len(condition) == 1:
                cond_value = condition[0]['value']
            else:
                cond_value = {e['param']: e['value'] for e in condition}

            manifest['runs'].append({
                'run_id': run_id,
                'condition': {e['param']: e['value'] for e in condition},
                'condition_value': cond_value,
                'rep': rep,
                'final_gini': final_gini,
                'final_stability': final_stability,
                'top_action': top_action,
                'cooperation_ratio': coop_ratio,
                'first_attack_round': first_attack,
                'elapsed_seconds': round(run_elapsed, 1),
                'timestamp': datetime.now().isoformat(),
            })

            condition_metrics.append({
                'gini': final_gini,
                'stability': final_stability,
                'top_action': top_action,
                'cooperation_ratio': coop_ratio,
            })

        # Print condition summary
        ginis = [m['gini'] for m in condition_metrics if m['gini'] is not None]
        stabilities = [m['stability'] for m in condition_metrics if m['stability'] is not None]
        coop_ratios = [m['cooperation_ratio'] for m in condition_metrics]

        print(f"\n--- Summary for {label} ---")
        if ginis:
            print(f"  Gini:      mean={sum(ginis)/len(ginis):.3f}  "
                  f"min={min(ginis):.3f}  max={max(ginis):.3f}")
        if stabilities:
            print(f"  Stability: mean={sum(stabilities)/len(stabilities):.3f}  "
                  f"min={min(stabilities):.3f}  max={max(stabilities):.3f}")
        if coop_ratios:
            print(f"  Coop ratio: mean={sum(coop_ratios)/len(coop_ratios):.3f}")

        # Action counts across reps
        action_counts = {}
        for m in condition_metrics:
            a = m['top_action']
            action_counts[a] = action_counts.get(a, 0) + 1
        print(f"  Top actions: {action_counts}")

    manifest['completed_at'] = datetime.now().isoformat()
    manifest['total_elapsed_seconds'] = round(time.time() - experiment_start, 1)

    # Save manifest
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest saved to {manifest_path}")

    print(f"\n{'='*70}")
    print(f"EXPERIMENT COMPLETE: {name}")
    print(f"Total time: {manifest['total_elapsed_seconds']:.0f}s")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python src/sweep.py <experiment_spec.yaml>")
        print("Example: python src/sweep.py experiments/baseline_replicability.yaml")
        sys.exit(1)

    run_sweep(sys.argv[1])
