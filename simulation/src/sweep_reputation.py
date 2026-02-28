"""Sweep: 2x2 reputation factorial (resource visibility x reputation summary), 30 agents spatial."""
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
    "num_agents": 30,
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
    "interaction_radius": 2,
}

output_dir = project_root / "data" / "runs"

# 2x2: resource visibility x reputation summary
conditions = [
    {"label": "vis_norep",  "hide_resources": False, "show_reputation": False},
    {"label": "vis_rep",    "hide_resources": False, "show_reputation": True},
    {"label": "hid_norep",  "hide_resources": True,  "show_reputation": False},
    {"label": "hid_rep",    "hide_resources": True,  "show_reputation": True},
]

print("=== REPUTATION 2x2 FACTORIAL SWEEP (30 agents, spatial) ===")
for cond in conditions:
    for rep in range(1, 3):
        params = {**base_params}
        or_config = {**openrouter_config}
        or_config["prompt_config"] = {
            **openrouter_config.get("prompt_config", {}),
            "hide_resources": cond["hide_resources"],
            "show_reputation": cond["show_reputation"],
        }

        run_id = f"rep_{cond['label']}_rep{rep}"
        print(f"\n=== {cond['label']} (hide_resources={cond['hide_resources']}, show_reputation={cond['show_reputation']}), rep={rep} ===")
        state, traces, metrics = run_simulation(params, or_config, run_id)
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
