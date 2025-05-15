import json
import os
from openai import OpenAI

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Please set the OPENAI_API_KEY environment variable.")

client = OpenAI(api_key=OPENAI_API_KEY)
model_name = "gpt-4o"
num_examples = 50
predicted_answers_condition1 = {}

dataset = []
with open("data/financebench_open_source.jsonl", "r") as f:
    for i, line in enumerate(f):
        if i < num_examples:
            dataset.append(json.loads(line))
        else:
            break

print(f"Loaded {len(dataset)} examples.")

for example in dataset:
    financebench_id = example["financebench_id"]
    question = example["question"]
    evidence_texts = [item["evidence_text"] for item in example["evidence"]]
    context = "\n".join(evidence_texts)

    prompt = f"""Based on the following information, answer the question concisely and exactly as asked:

    Context:
    {context}

    Question:
    {question}

    Guidelines:
    - Provide a direct, concise answer that exactly matches the question format
    - For dollar values: Add $ symbol and round to 2 decimal places (e.g., $81.00)
    - For numerical values, just state the number
    - For yes/no questions, provide a brief explanation of your reasoning
    - Always include the correct unit or scale (e.g., million, billion, %, $) as appropriate
    - Pay attention to the magnitude and format (e.g., $2.22 million, $1.00 billion, 2.22%)
    - If the question specifies "answer in USD million/billion", do not include million/billion in your answer as it's already in the question
    - Avoid unnecessary explanations unless specifically asked for
    - Pay close attention to the exact format of the question and match it in your answer

    Answer:"""

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
        )
        predicted_answer = response.choices[0].message.content
        predicted_answers_condition1[financebench_id] = predicted_answer
        print(f"Processed {financebench_id}: Predicted answer - {predicted_answer}")

    except Exception as e:
        print(f"Error processing {financebench_id}: {e}")
        predicted_answers_condition1[financebench_id] = "Error"

# Save the predicted answers with UTF-8 encoding
with open("predicted_answers/predicted_answers_condition1.json", "w", encoding="utf-8") as f:
    json.dump(predicted_answers_condition1, f, indent=4, ensure_ascii=False)

print("\nPredicted answers for Condition 1 saved to predicted_answers/predicted_answers_condition1.json")