# Multi-Agent Coordination Game Simulation

LLM agent simulation for testing semantic reasoning in resource coordination games.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure OpenRouter API:
```bash
cp .env.example .env
# Edit .env and add your OpenRouter API key
```

3. Adjust game parameters in `config/game_params.yaml`

4. Run simulation:
```bash
python src/main.py
```

## Structure

- `src/game/` - Game engine and state management
- `src/agents/` - Agent implementations (LLM, future RL)
- `config/` - Configuration files for game parameters and API settings
- `data/` - Simulation outputs and logs
- `src/analysis/` - Analysis and visualization tools
