import sys
import json
import os
from datetime import datetime

# Configure UTF-8 encoding
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Please set the OPENAI_API_KEY environment variable.")

from minions_finance.clients.openai import OpenAIClient

remote_client = OpenAIClient(api_key=OPENAI_API_KEY, model_name="gpt-4o")

# Load the dataset
dataset = []
with open("data/financebench_open_source.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        dataset.append(json.loads(line))

# Load predicted answers
with open("predicted_answers/predicted_answers_condition1.json", "r", encoding="utf-8") as f:
    predicted_answers_condition1 = json.load(f)

with open("predicted_answers/predicted_answers_condition2.json", "r", encoding="utf-8") as f:
    predicted_answers_condition2 = json.load(f)

# Create evaluation logs directory if it doesn't exist
os.makedirs("eval_logs", exist_ok=True)

# Initialize counters
baseline_correct = 0
minions_correct = 0
total = 0

# Initialize evaluation logs
baseline_eval_log = []
minions_eval_log = []

for example in dataset:
    financebench_id = example["financebench_id"]
    gold_answer = example["answer"]
    
    # Skip if we don't have predictions for this example
    if financebench_id not in predicted_answers_condition1 or financebench_id not in predicted_answers_condition2:
        continue
    
    total += 1
    predicted_answer_condition1 = predicted_answers_condition1[financebench_id]
    predicted_answer_condition2 = predicted_answers_condition2[financebench_id]
    
    print(f"\n--- Processing {financebench_id} ---")
    
    # Evaluate Condition 1 (Baseline)
    try:
        response = remote_client.chat(
            messages=[
                {"role": "system", "content": """You are an evaluator that determines if a predicted answer matches a gold answer.
                Consider the following criteria:
                1. Numerical Accuracy: Allow 10% tolerance margin for numerical answers
                2. Unit Consistency: Accept answers with or without units, different scales (e.g., million vs billion), and various formats
                3. Format Flexibility: Accept different formats (e.g., with/without punctuation, different capitalization)
                4. Semantic Equivalence: Accept different expressions of the same meaning
                5. Partial Matches: Accept partial matches if the key information is correct
                6. Direction of Change: For percentage changes, focus on the direction rather than exact numbers
                
                Examples of acceptable variations:
                - "$1.5M" = "$1,500,000" = "1.5 million dollars"
                - "Yes, because..." = "Yes" = "Affirmative"
                - "20%" = "20 percent" = "0.2"
                - "Q2 2023" = "Second quarter of 2023" = "2023 Q2"
                
                Respond with a JSON object containing:
                {
                    "is_correct": true/false,
                    "explanation": "Brief explanation of your decision"
                }"""},
                {"role": "user", "content": f"Gold Answer: {gold_answer}\nPredicted Answer: {predicted_answer_condition1}"}
            ]
        )
        eval_result = json.loads(response)
        if eval_result["is_correct"]:
            baseline_correct += 1
        baseline_eval_log.append({
            "financebench_id": financebench_id,
            "gold_answer": gold_answer,
            "predicted_answer": predicted_answer_condition1,
            "is_correct": eval_result["is_correct"],
            "explanation": eval_result["explanation"]
        })
    except Exception as e:
        print(f"Error evaluating {financebench_id}: {str(e)}")
        baseline_eval_log.append({
            "financebench_id": financebench_id,
            "gold_answer": gold_answer,
            "predicted_answer": predicted_answer_condition1,
            "is_correct": False,
            "explanation": f"Error during evaluation: {str(e)}"
        })
    
    # Evaluate Condition 2 (Minions)
    try:
        response = remote_client.chat(
            messages=[
                {"role": "system", "content": """You are an evaluator that determines if a predicted answer matches a gold answer.
                Consider the following criteria:
                1. Numerical Accuracy: Allow 10% tolerance margin for numerical answers
                2. Unit Consistency: Accept answers with or without units, different scales (e.g., million vs billion), and various formats
                3. Format Flexibility: Accept different formats (e.g., with/without punctuation, different capitalization)
                4. Semantic Equivalence: Accept different expressions of the same meaning
                5. Partial Matches: Accept partial matches if the key information is correct
                6. Direction of Change: For percentage changes, focus on the direction rather than exact numbers
                
                Examples of acceptable variations:
                - "$1.5M" = "$1,500,000" = "1.5 million dollars"
                - "Yes, because..." = "Yes" = "Affirmative"
                - "20%" = "20 percent" = "0.2"
                - "Q2 2023" = "Second quarter of 2023" = "2023 Q2"
                
                Respond with a JSON object containing:
                {
                    "is_correct": true/false,
                    "explanation": "Brief explanation of your decision"
                }"""},
                {"role": "user", "content": f"Gold Answer: {gold_answer}\nPredicted Answer: {predicted_answer_condition2}"}
            ]
        )
        eval_result = json.loads(response)
        if eval_result["is_correct"]:
            minions_correct += 1
        minions_eval_log.append({
            "financebench_id": financebench_id,
            "gold_answer": gold_answer,
            "predicted_answer": predicted_answer_condition2,
            "is_correct": eval_result["is_correct"],
            "explanation": eval_result["explanation"]
        })
    except Exception as e:
        print(f"Error evaluating {financebench_id}: {str(e)}")
        minions_eval_log.append({
            "financebench_id": financebench_id,
            "gold_answer": gold_answer,
            "predicted_answer": predicted_answer_condition2,
            "is_correct": False,
            "explanation": f"Error during evaluation: {str(e)}"
        })

print(f"\nBaseline accuracy: {baseline_correct}/{total} ({baseline_correct/total*100:.1f}%)")
print(f"Minions accuracy: {minions_correct}/{total} ({minions_correct/total*100:.1f}%)")

# Save evaluation logs
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
baseline_log_path = f"eval_logs/baseline_eval_{timestamp}.json"
minions_log_path = f"eval_logs/minions_eval_{timestamp}.json"

with open(baseline_log_path, "w", encoding="utf-8") as f:
    json.dump(baseline_eval_log, f, indent=4, ensure_ascii=False)

with open(minions_log_path, "w", encoding="utf-8") as f:
    json.dump(minions_eval_log, f, indent=4, ensure_ascii=False)

print("\nEvaluation logs saved to:")
print(f"- Baseline: {baseline_log_path}")
print(f"- Minions: {minions_log_path}") 