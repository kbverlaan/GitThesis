"""
Traceability system for experiment runs.

Auto-logs everything about experiment runs: git commit hash, config,
experiment metadata, per-run results, timestamps, and manual decisions.

Every run is traceable back to exact code version, config, and context.
"""

import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import sys


def get_git_info() -> Dict[str, Any]:
    """
    Get current git repository information.

    Returns:
        dict with:
        - 'commit_hash': current commit SHA (str or None)
        - 'branch': current branch name (str or None)
        - 'dirty': whether there are uncommitted changes (bool)
        - 'dirty_files': list of modified/untracked files (list of str)

    Returns dict with None values if not in a git repository.
    """
    try:
        # Get commit hash
        commit_hash = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Not in a git repo or git not installed
        return {
            'commit_hash': None,
            'branch': None,
            'dirty': False,
            'dirty_files': []
        }

    try:
        # Get branch name
        branch = subprocess.check_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
    except subprocess.CalledProcessError:
        branch = None

    try:
        # Get dirty status
        status_output = subprocess.check_output(
            ['git', 'status', '--porcelain'],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()

        dirty = len(status_output) > 0
        dirty_files = [line.strip() for line in status_output.split('\n')] if dirty else []
    except subprocess.CalledProcessError:
        dirty = False
        dirty_files = []

    return {
        'commit_hash': commit_hash,
        'branch': branch,
        'dirty': dirty,
        'dirty_files': dirty_files
    }


class RunLogger:
    """
    Automatic experiment logging for traceability.

    Creates/appends to a structured JSON-lines log file that records:
    - Git commit hash and dirty status at time of run
    - Full config (game params + openrouter config)
    - Experiment metadata (name, description, sweep spec)
    - Per-run results summary
    - Timestamps
    - Decisions and notes (manually added)
    """

    def __init__(self, log_dir: Optional[Path] = None):
        """
        Initialize logger.

        Args:
            log_dir: Directory to store log files.
                    Defaults to project_root / "data" / "experiment_log"
        """
        if log_dir is None:
            # Find project root (directory containing 'simulation' folder)
            current = Path(__file__).resolve()
            while current.parent != current:
                if (current / 'simulation').exists() or (current.parent / 'simulation').exists():
                    if (current / 'simulation').exists():
                        project_root = current
                    else:
                        project_root = current.parent
                    break
                current = current.parent
            else:
                # Fallback: use parent of parent of this file (src -> simulation -> project)
                project_root = Path(__file__).resolve().parent.parent.parent

            log_dir = project_root / "data" / "experiment_log"

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.master_log = self.log_dir / "master_log.jsonl"

        # Track active experiments by ID -> log file path
        self._experiments: Dict[str, Path] = {}

    def start_experiment(self, spec: Dict[str, Any], openrouter_config: Dict[str, Any]) -> str:
        """
        Start a new experiment and create its log file.

        Args:
            spec: Experiment specification dict (from YAML), should contain:
                  'name', 'description', and sweep parameters
            openrouter_config: OpenRouter configuration dict

        Returns:
            experiment_id (str): Unique identifier for this experiment
        """
        timestamp = datetime.now()
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")

        experiment_name = spec.get('name', 'unnamed_experiment')
        experiment_id = f"{experiment_name}_{timestamp_str}"

        # Get git information
        git_info = get_git_info()

        # Get Python version
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        # Get package versions (try to import common packages)
        package_versions = {}
        for package_name in ['numpy', 'scipy', 'pandas', 'matplotlib']:
            try:
                module = __import__(package_name)
                package_versions[package_name] = getattr(module, '__version__', 'unknown')
            except ImportError:
                package_versions[package_name] = 'not installed'

        # Create experiment metadata entry
        experiment_entry = {
            'type': 'experiment_start',
            'experiment_id': experiment_id,
            'timestamp': timestamp.isoformat(),
            'spec': spec,
            'openrouter_config': openrouter_config,
            'git': git_info,
            'python_version': python_version,
            'package_versions': package_versions
        }

        # Create experiment-specific log file
        log_file = self.log_dir / f"{experiment_id}.jsonl"
        with open(log_file, 'w') as f:
            f.write(json.dumps(experiment_entry) + '\n')

        # Also append to master log
        with open(self.master_log, 'a') as f:
            f.write(json.dumps(experiment_entry) + '\n')

        # Track this experiment
        self._experiments[experiment_id] = log_file

        return experiment_id

    def log_run(self,
                experiment_id: str,
                run_id: int,
                condition: Dict[str, Any],
                game_params: Dict[str, Any],
                openrouter_config: Dict[str, Any],
                results: Dict[str, Any]) -> None:
        """
        Log a single run result.

        Args:
            experiment_id: ID returned by start_experiment
            run_id: Sequential run number
            condition: Dict describing this condition (e.g., {'model': 'gpt-4', 'theta': 1.5})
            game_params: Full game parameters used for this run
            openrouter_config: Full OpenRouter config used
            results: Results dict (final_gini, cooperation_ratio, first_attack_round, etc.)
        """
        timestamp = datetime.now()

        run_entry = {
            'type': 'run',
            'experiment_id': experiment_id,
            'run_id': run_id,
            'timestamp': timestamp.isoformat(),
            'condition': condition,
            'game_params': game_params,
            'openrouter_config': openrouter_config,
            'results': results
        }

        # Append to experiment-specific log
        if experiment_id in self._experiments:
            log_file = self._experiments[experiment_id]
        else:
            # Try to find log file
            log_file = self.log_dir / f"{experiment_id}.jsonl"
            if not log_file.exists():
                raise ValueError(f"Unknown experiment_id: {experiment_id}. "
                               f"Did you call start_experiment first?")
            self._experiments[experiment_id] = log_file

        with open(log_file, 'a') as f:
            f.write(json.dumps(run_entry) + '\n')

        # Also append to master log
        with open(self.master_log, 'a') as f:
            f.write(json.dumps(run_entry) + '\n')

    def log_decision(self,
                     experiment_id: str,
                     decision: str,
                     reasoning: str,
                     context: Optional[Dict[str, Any]] = None) -> None:
        """
        Record a decision made during or after an experiment.

        Args:
            experiment_id: ID of the experiment this decision relates to
            decision: Brief description of the decision
            reasoning: Why this decision was made
            context: Optional additional context (e.g., metrics that prompted decision)
        """
        timestamp = datetime.now()

        decision_entry = {
            'type': 'decision',
            'experiment_id': experiment_id,
            'timestamp': timestamp.isoformat(),
            'decision': decision,
            'reasoning': reasoning,
            'context': context or {}
        }

        # Append to experiment-specific log
        if experiment_id in self._experiments:
            log_file = self._experiments[experiment_id]
        else:
            # Try to find log file
            log_file = self.log_dir / f"{experiment_id}.jsonl"
            if not log_file.exists():
                raise ValueError(f"Unknown experiment_id: {experiment_id}. "
                               f"Did you call start_experiment first?")
            self._experiments[experiment_id] = log_file

        with open(log_file, 'a') as f:
            f.write(json.dumps(decision_entry) + '\n')

        # Also append to master log
        with open(self.master_log, 'a') as f:
            f.write(json.dumps(decision_entry) + '\n')

    def get_experiment_summary(self, experiment_id: str) -> Dict[str, Any]:
        """
        Get summary of an experiment.

        Args:
            experiment_id: ID of the experiment

        Returns:
            Dict with:
            - n_runs: number of runs completed
            - conditions: list of unique conditions tested
            - mean_metrics: dict of condition -> dict of metric -> mean value
            - decisions: list of decision entries
            - git_hash: commit hash at experiment start
            - timestamp: experiment start time
        """
        log_file = self.log_dir / f"{experiment_id}.jsonl"
        if not log_file.exists():
            raise ValueError(f"No log file found for experiment_id: {experiment_id}")

        # Read all entries
        entries = []
        with open(log_file, 'r') as f:
            for line in f:
                entries.append(json.loads(line))

        # Extract experiment start info
        start_entry = next((e for e in entries if e['type'] == 'experiment_start'), None)
        if start_entry is None:
            raise ValueError(f"No experiment_start entry found in {log_file}")

        # Extract runs
        run_entries = [e for e in entries if e['type'] == 'run']

        # Extract decisions
        decision_entries = [e for e in entries if e['type'] == 'decision']

        # Compute per-condition statistics
        from collections import defaultdict
        condition_results = defaultdict(list)

        for run in run_entries:
            # Convert condition dict to a hashable key
            condition_key = json.dumps(run['condition'], sort_keys=True)
            condition_results[condition_key].append(run['results'])

        # Compute mean metrics per condition
        mean_metrics = {}
        for condition_key, results_list in condition_results.items():
            condition = json.loads(condition_key)
            condition_str = json.dumps(condition, sort_keys=True)

            # Collect all metric values
            metric_values = defaultdict(list)
            for results in results_list:
                for metric, value in results.items():
                    if isinstance(value, (int, float)):
                        metric_values[metric].append(value)

            # Compute means
            mean_metrics[condition_str] = {
                metric: sum(values) / len(values)
                for metric, values in metric_values.items()
            }

        return {
            'experiment_id': experiment_id,
            'n_runs': len(run_entries),
            'conditions': [json.loads(k) for k in condition_results.keys()],
            'mean_metrics': mean_metrics,
            'decisions': [
                {
                    'timestamp': d['timestamp'],
                    'decision': d['decision'],
                    'reasoning': d['reasoning'],
                    'context': d.get('context', {})
                }
                for d in decision_entries
            ],
            'git_hash': start_entry['git']['commit_hash'],
            'git_dirty': start_entry['git']['dirty'],
            'timestamp': start_entry['timestamp'],
            'spec': start_entry['spec']
        }

    def search_runs(self, **filters) -> List[Dict[str, Any]]:
        """
        Search across all experiment logs for runs matching filters.

        Args:
            **filters: Key-value pairs to filter runs. Supports:
                - model: filter by model name (str)
                - min_<metric>: minimum value for a metric
                - max_<metric>: maximum value for a metric
                - start_date: ISO date string (YYYY-MM-DD)
                - end_date: ISO date string (YYYY-MM-DD)
                - git_hash: specific commit hash
                - condition_<key>: filter by condition parameter value

        Returns:
            List of run entries matching all filters
        """
        matching_runs = []

        # Read master log
        if not self.master_log.exists():
            return []

        with open(self.master_log, 'r') as f:
            for line in f:
                entry = json.loads(line)

                # Only consider run entries
                if entry['type'] != 'run':
                    continue

                # Apply filters
                match = True

                for filter_key, filter_value in filters.items():
                    if filter_key == 'model':
                        # Check in openrouter_config
                        if entry.get('openrouter_config', {}).get('model') != filter_value:
                            match = False
                            break

                    elif filter_key.startswith('min_'):
                        metric = filter_key[4:]
                        if metric not in entry.get('results', {}):
                            match = False
                            break
                        if entry['results'][metric] < filter_value:
                            match = False
                            break

                    elif filter_key.startswith('max_'):
                        metric = filter_key[4:]
                        if metric not in entry.get('results', {}):
                            match = False
                            break
                        if entry['results'][metric] > filter_value:
                            match = False
                            break

                    elif filter_key == 'start_date':
                        timestamp = datetime.fromisoformat(entry['timestamp'])
                        filter_date = datetime.fromisoformat(filter_value)
                        if timestamp.date() < filter_date.date():
                            match = False
                            break

                    elif filter_key == 'end_date':
                        timestamp = datetime.fromisoformat(entry['timestamp'])
                        filter_date = datetime.fromisoformat(filter_value)
                        if timestamp.date() > filter_date.date():
                            match = False
                            break

                    elif filter_key == 'git_hash':
                        # Need to look up experiment_start entry
                        # For simplicity, skip this filter for now
                        # (would require reading experiment-specific logs)
                        pass

                    elif filter_key.startswith('condition_'):
                        condition_key = filter_key[10:]
                        if entry.get('condition', {}).get(condition_key) != filter_value:
                            match = False
                            break

                if match:
                    matching_runs.append(entry)

        return matching_runs
