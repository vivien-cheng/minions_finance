import json
import re
import os

# Create directories if they don't exist
os.makedirs('eval_logs', exist_ok=True)
os.makedirs('predicted_answers', exist_ok=True)

# Load expected answers from raw data
expected_answers = {}
with open('data/financebench_open_source.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        item = json.loads(line)
        expected_answers[item['financebench_id']] = item['answer']

# Load predicted answers
with open('predicted_answers/predicted_answers_condition1.json', 'r', encoding='utf-8') as f:
    pred1 = json.load(f)
with open('predicted_answers/predicted_answers_condition2.json', 'r', encoding='utf-8') as f:
    pred2 = json.load(f)

# Helper functions for fuzzy matching

def normalize_number(s):
    s = s.replace(',', '').replace('$', '').replace('%', '').strip()
    try:
        return float(re.findall(r'[-+]?[0-9]*\.?[0-9]+', s)[0])
    except Exception:
        return None

def is_numeric_match(pred, gold):
    pred_num = normalize_number(pred)
    gold_num = normalize_number(gold)
    if pred_num is not None and gold_num is not None:
        return abs(pred_num - gold_num) < 0.05 * abs(gold_num) or abs(pred_num - gold_num) < 0.1
    return False

def is_text_match(pred, gold):
    pred = pred.lower().strip()
    gold = gold.lower().strip()
    return gold in pred or pred in gold

def is_correct(pred, gold):
    # Try numeric match first
    if is_numeric_match(pred, gold):
        return True
    # Otherwise, use text match
    return is_text_match(pred, gold)

# Evaluate
results = {'condition1': {'correct': 0, 'total': 0}, 'condition2': {'correct': 0, 'total': 0}}

for fid, gold in expected_answers.items():
    # Condition 1
    pred1_ans = pred1.get(fid, None)
    if pred1_ans is not None:
        results['condition1']['total'] += 1
        if is_correct(pred1_ans, gold):
            results['condition1']['correct'] += 1
    # Condition 2
    pred2_ans = pred2.get(fid, None)
    if pred2_ans is not None:
        # Condition 2 predictions are lists
        pred2_text = pred2_ans[0] if isinstance(pred2_ans, list) and pred2_ans else pred2_ans
        results['condition2']['total'] += 1
        if is_correct(pred2_text, gold):
            results['condition2']['correct'] += 1

# Print results
for cond in ['condition1', 'condition2']:
    correct = results[cond]['correct']
    total = results[cond]['total']
    acc = 100.0 * correct / total if total > 0 else 0.0
    print(f"{cond}: {correct}/{total} correct ({acc:.1f}%)")

# Save evaluation logs
with open('eval_logs/evaluation_results.txt', 'w', encoding='utf-8') as f:
    f.write("Evaluation Results:\n")
    for cond in ['condition1', 'condition2']:
        correct = results[cond]['correct']
        total = results[cond]['total']
        acc = 100.0 * correct / total if total > 0 else 0.0
        f.write(f"{cond}: {correct}/{total} correct ({acc:.1f}%)\n")

# Save predicted answers
with open('predicted_answers/predicted_answers_condition1.json', 'w', encoding='utf-8') as f:
    json.dump(pred1, f, indent=4)
with open('predicted_answers/predicted_answers_condition2.json', 'w', encoding='utf-8') as f:
    json.dump(pred2, f, indent=4)

# After the evaluation loop, add the following code to print detailed results

print("\nDetailed Results:")
for cond in ['condition1', 'condition2']:
    print(f"\n{cond}:")
    for fid, gold in expected_answers.items():
        pred_ans = pred1.get(fid, None) if cond == 'condition1' else pred2.get(fid, None)
        if pred_ans is not None:
            pred_text = pred_ans[0] if isinstance(pred_ans, list) and pred_ans else pred_ans
            is_correct_ans = is_correct(pred_text, gold)
            status = "✓" if is_correct_ans else "✗"
            print(f"{status} {fid}: Expected: {gold}, Predicted: {pred_text}") 