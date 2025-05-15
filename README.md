# FinanceBench Experiment

A multi-agent system for financial question answering, built to evaluate and improve financial analysis capabilities.

## Overview

This project implements a multi-agent system for answering financial questions using specialized agents:
- RetrieverAgent: Finds relevant text snippets from financial documents
- SimpleFinanceAgent: Understands basic financial terms and identifies relevant line items
- CalculatorAgent: Performs arithmetic calculations on financial data
- AggregatorAgent: Synthesizes information to provide final answers

## Setup

1. Clone the repository:
```bash
git clone [your-repo-url]
cd financebench-experiment
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
export OPENAI_API_KEY="your-api-key"
```

## Usage

The project includes three main scripts:

1. `baseline.py`: Runs the baseline model for comparison
2. `minions.py`: Runs the multi-agent system
3. `llm_evaluate_predictions.py`: Evaluates the predictions from both approaches

To run the full evaluation pipeline:
```bash
python baseline.py && python minions.py && python llm_evaluate_predictions.py
```

## Project Structure

```
financebench-experiment/
├── data/
│   └── financebench_open_source.jsonl
├── minions_finance/
│   ├── clients/
│   ├── prompts/
│   ├── tools/
│   └── utils/
├── predicted_answers/
├── eval_logs/
├── baseline.py
├── minions.py
└── llm_evaluate_predictions.py
```

## Evaluation

The system evaluates answers based on:
- Semantic equivalence
- Numerical accuracy
- Format consistency
- Reasoning quality

Results are saved in the `eval_logs` directory with timestamps.

## License

[Your chosen license]
