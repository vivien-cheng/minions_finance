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
num_examples = 50

# Load the first few examples from the dataset
dataset = []
with open("data/financebench_open_source.jsonl", "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        if i < num_examples:
            dataset.append(json.loads(line))
        else:
            break

print(f"Loaded {len(dataset)} examples.")

predicted_answers_condition1 = {}

for example in dataset:
    financebench_id = example["financebench_id"]
    question = example["question"]
    evidence_texts = [item["evidence_text"] for item in example["evidence"]]
    context = "\n".join(evidence_texts)
    metadata = {k: example[k] for k in example if k not in ["evidence"]}

    print(f"\n--- Processing {financebench_id} ---")
    try:
        response = remote_client.chat(
            messages=[
                {"role": "system", "content": "You are a helpful assistant that answers questions based on the provided context."},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
            ]
        )
        predicted_answers_condition1[financebench_id] = response
        print(f"Predicted answer (Condition 1) for {financebench_id}: {response}")
    except Exception as e:
        print(f"Error processing {financebench_id}: {str(e)}")
        predicted_answers_condition1[financebench_id] = f"Error: {str(e)}"

# Save the predicted answers for Condition 1
with open("predicted_answers/predicted_answers_condition1.json", "w", encoding="utf-8") as f:
    json.dump(predicted_answers_condition1, f, indent=4, ensure_ascii=False)

print("\nPredicted answers for Condition 1 saved to predicted_answers/predicted_answers_condition1.json")