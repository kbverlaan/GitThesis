"""Sweep: spatial parameters (radius, grid_size), 2 reps each."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

import yaml
from main import run_simulation, save_results

project_root = Path(__file__).parent.parent
openrouter_config = yaml.safe_load(open(project_root / "config" / "openrouter_config.yaml"))

base_params = {
    "num_agents": 10,
    "initial_resources": 25.0,
    "invest_self_cost": 0,
    "invest_self_return": 2,
    "invest_other_cost": 0,
    "invest_other_return": 5,
    "arm_cost": 0.0,
    "arm_multiplier": 2.0,
    "arm_duration": 3,
    "arm_other_contribution": 0.5,
    "arm_other_duration": 3,
    "attack_take_percent": 40.0,
    "conflict_cost": 0.0,
    "max_rounds": 10,
    "history_length": 10,
    "allow_invest_self": False,
    "initial_distribution": "equal",
    "action_order": "simultaneous",
    "spatial_enabled": True,
}

output_dir = project_root / "data" / "runs"

# Conditions: vary radius on 7x7, and try bigger grid
conditions = [
    {"label": "7x7_r1", "grid_size": 7, "interaction_radius": 1},
    {"label": "7x7_r2", "grid_size": 7, "interaction_radius": 2},  # baseline (already have 2 reps)
    {"label": "7x7_r3", "grid_size": 7, "interaction_radius": 3},
    {"label": "10x10_r2", "grid_size": 10, "interaction_radius": 2},
]

print("=== SPATIAL PARAMETER SWEEP ===")
for cond in conditions:
    for rep in range(1, 3):
        params = {
            **base_params,
            "grid_size": cond["grid_size"],
            "interaction_radius": cond["interaction_radius"],
        }
        run_id = f"spatial_{cond['label']}_rep{rep}"
        print(f"\n=== {cond['label']}, rep={rep} ===")
        state, traces, metrics = run_simulation(params, openrouter_config, run_id)
        save_results(state, traces, metrics, output_dir, run_id)

        # Print summary
        final_gini = metrics[-1]["gini"] if metrics else None
        actions = {}
        for m in metrics:
            for a, c in m["action_distribution"].items():
                actions[a] = actions.get(a, 0) + c
        total = sum(actions.values())
        print(f"  Final Gini={final_gini:.3f}")
        for a, c in sorted(actions.items(), key=lambda x: x[1], reverse=True):
            print(f"  {a}: {c} ({c/total*100:.1f}%)")
