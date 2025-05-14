# Minions Finance

A multi-agent system for financial document analysis and question answering, built using OpenAI's GPT models.

## Overview

This project implements two approaches for answering financial questions:
1. Baseline: A single GPT model approach
2. Minions: A multi-agent system with specialized agents for different tasks

## Setup

1. Clone the repository:
```bash
git clone git@github.com:vivien-cheng/minions_finance.git
cd minions_finance
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your OpenAI API key:
```bash
export OPENAI_API_KEY='your-api-key-here'
```

## Usage

### Running the Baseline Model
```bash
python baseline.py
```

### Running the Minions Multi-Agent System
```bash
python minions.py
```

### Evaluating Results
```bash
python evaluate_predictions.py
```

## Project Structure

- `baseline.py`: Implementation of the single-model approach
- `minions.py`: Implementation of the multi-agent system
- `evaluate_predictions.py`: Script for evaluating model predictions
- `minions_finance/`: Core package containing:
  - `clients/`: API client implementations
  - `prompts/`: System and task prompts
  - `tools/`: Utility functions and tools
  - `utils/`: Helper functions and utilities

## Output

Results are saved in the following directories:
- `predicted_answers/`: Contains model predictions
- `eval_logs/`: Contains evaluation results
- `minions_logs/`: Contains detailed logs from the multi-agent system
- `multiagent_logs/`: Contains logs from agent interactions

## License

MIT License
