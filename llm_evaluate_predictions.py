import json
import os
from datetime import datetime

def evaluate_predictions():
    # Load the gold answers
    with open("data/financebench_open_source.jsonl", "r") as f:
        gold_answers = {json.loads(line)["financebench_id"]: json.loads(line)["answer"] for line in f}

    # Load the predicted answers for both conditions
    with open("predicted_answers/predicted_answers_condition1.json", "r") as f:
        baseline_predictions = json.load(f)
    
    with open("predicted_answers/predicted_answers_condition2.json", "r") as f:
        minions_predictions = json.load(f)

    # Create evaluation logs directory if it doesn't exist
    os.makedirs("eval_logs", exist_ok=True)

    # Evaluate baseline predictions
    baseline_correct = 0
    baseline_total = 0
    baseline_eval_log = []

    for financebench_id, predicted_answer in baseline_predictions.items():
        if financebench_id in gold_answers:
            baseline_total += 1
            gold_answer = gold_answers[financebench_id]
            
            # Create evaluation prompt
            eval_prompt = f"""Please evaluate if the predicted answer is a valid and reasonable response to the gold answer.

            Gold Answer: {gold_answer}
            Predicted Answer: {predicted_answer}

            Consider:
            1. Is the predicted answer contextually appropriate and does it capture the essential meaning or intent of the gold answer?
            2. Ignore differences in format, units, wording, order, or minor factual details if the overall meaning is preserved.
            3. Accept answers that are close, approximate, or paraphrased, as long as they are not misleading or fundamentally incorrect.
            4. For all types of questions (numeric, categorical, yes/no, explanation, etc.), focus on whether the response would be acceptable to a reasonable human evaluator.

            Return your evaluation as a JSON object with the following structure:
            {{
                "is_correct": true/false,
                "explanation": "Brief explanation of your evaluation"
            }}

            Note: An answer should be considered correct if it is a reasonable, contextually valid response to the gold answer, even if it is not exact. Use your best judgment to decide if the predicted answer is acceptable.
            """

            # Get evaluation from LLM
            try:
                from minions_finance.clients.openai import OpenAIClient
                client = OpenAIClient()
                response = client.chat(messages=[{"role": "user", "content": eval_prompt}])
                # Handle tuple (response, usage)
                if isinstance(response, tuple):
                    response = response[0]
                eval_json_str = None
                if isinstance(response, list):
                    if len(response) > 0:
                        if isinstance(response[0], dict) and "content" in response[0]:
                            eval_json_str = response[0]["content"]
                        elif isinstance(response[0], str):
                            eval_json_str = response[0]
                elif isinstance(response, dict) and "content" in response:
                    eval_json_str = response["content"]
                if eval_json_str is None:
                    print(f"DEBUG: Unexpected response format for {financebench_id}: {response}")
                    raise ValueError("Unexpected response format from OpenAIClient.chat")
                # Strip markdown code block if present
                if eval_json_str.strip().startswith("```json"):
                    eval_json_str = eval_json_str.strip().lstrip("`json").strip()
                    if eval_json_str.startswith("\n"):
                        eval_json_str = eval_json_str[1:]
                    if eval_json_str.endswith("```"):
                        eval_json_str = eval_json_str[:-3].strip()
                elif eval_json_str.strip().startswith("```"):
                    eval_json_str = eval_json_str.strip().lstrip("`").strip()
                    if eval_json_str.startswith("json"):
                        eval_json_str = eval_json_str[4:].strip()
                    if eval_json_str.endswith("```"):
                        eval_json_str = eval_json_str[:-3].strip()
                eval_result = json.loads(eval_json_str)
                
                if eval_result["is_correct"]:
                    baseline_correct += 1
                
                baseline_eval_log.append({
                    "financebench_id": financebench_id,
                    "gold_answer": gold_answer,
                    "predicted_answer": predicted_answer,
                    "is_correct": eval_result["is_correct"],
                    "explanation": eval_result["explanation"]
                })
            except Exception as e:
                print(f"Error evaluating {financebench_id}: {e}")

    # Evaluate minions predictions
    minions_correct = 0
    minions_total = 0
    minions_eval_log = []

    for financebench_id, predicted_answer in minions_predictions.items():
        if financebench_id in gold_answers:
            minions_total += 1
            gold_answer = gold_answers[financebench_id]
            
            # Create evaluation prompt
            eval_prompt = f"""Please evaluate if the predicted answer is a valid and reasonable response to the gold answer.

            Gold Answer: {gold_answer}
            Predicted Answer: {predicted_answer}

            Consider:
            1. Is the predicted answer contextually appropriate and does it capture the essential meaning or intent of the gold answer?
            2. Ignore differences in format, units, wording, order, or minor factual details if the overall meaning is preserved.
            3. Accept answers that are close, approximate, or paraphrased, as long as they are not misleading or fundamentally incorrect.
            4. For all types of questions (numeric, categorical, yes/no, explanation, etc.), focus on whether the response would be acceptable to a reasonable human evaluator.

            Return your evaluation as a JSON object with the following structure:
            {{
                "is_correct": true/false,
                "explanation": "Brief explanation of your evaluation"
            }}

            Note: An answer should be considered correct if it is a reasonable, contextually valid response to the gold answer, even if it is not exact. Use your best judgment to decide if the predicted answer is acceptable.
            """

            # Get evaluation from LLM
            try:
                from minions_finance.clients.openai import OpenAIClient
                client = OpenAIClient()
                response = client.chat(messages=[{"role": "user", "content": eval_prompt}])
                # Handle tuple (response, usage)
                if isinstance(response, tuple):
                    response = response[0]
                eval_json_str = None
                if isinstance(response, list):
                    if len(response) > 0:
                        if isinstance(response[0], dict) and "content" in response[0]:
                            eval_json_str = response[0]["content"]
                        elif isinstance(response[0], str):
                            eval_json_str = response[0]
                elif isinstance(response, dict) and "content" in response:
                    eval_json_str = response["content"]
                if eval_json_str is None:
                    print(f"DEBUG: Unexpected response format for {financebench_id}: {response}")
                    raise ValueError("Unexpected response format from OpenAIClient.chat")
                # Strip markdown code block if present
                if eval_json_str.strip().startswith("```json"):
                    eval_json_str = eval_json_str.strip().lstrip("`json").strip()
                    if eval_json_str.startswith("\n"):
                        eval_json_str = eval_json_str[1:]
                    if eval_json_str.endswith("```"):
                        eval_json_str = eval_json_str[:-3].strip()
                elif eval_json_str.strip().startswith("```"):
                    eval_json_str = eval_json_str.strip().lstrip("`").strip()
                    if eval_json_str.startswith("json"):
                        eval_json_str = eval_json_str[4:].strip()
                    if eval_json_str.endswith("```"):
                        eval_json_str = eval_json_str[:-3].strip()
                eval_result = json.loads(eval_json_str)
                
                if eval_result["is_correct"]:
                    minions_correct += 1
                
                minions_eval_log.append({
                    "financebench_id": financebench_id,
                    "gold_answer": gold_answer,
                    "predicted_answer": predicted_answer,
                    "is_correct": eval_result["is_correct"],
                    "explanation": eval_result["explanation"]
                })
            except Exception as e:
                print(f"Error evaluating {financebench_id}: {e}")

    # Calculate accuracies
    baseline_accuracy = baseline_correct / baseline_total if baseline_total > 0 else 0
    minions_accuracy = minions_correct / minions_total if minions_total > 0 else 0

    # Print results
    print(f"\nBaseline accuracy: {baseline_correct}/{baseline_total} ({baseline_accuracy:.1%})")
    print(f"Minions accuracy: {minions_correct}/{minions_total} ({minions_accuracy:.1%})")

    # Save evaluation logs
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    baseline_log_path = f"eval_logs/baseline_eval_{timestamp}.json"
    with open(baseline_log_path, "w") as f:
        json.dump({
            "accuracy": baseline_accuracy,
            "correct": baseline_correct,
            "total": baseline_total,
            "evaluations": baseline_eval_log
        }, f, indent=2)
    
    minions_log_path = f"eval_logs/minions_eval_{timestamp}.json"
    with open(minions_log_path, "w") as f:
        json.dump({
            "accuracy": minions_accuracy,
            "correct": minions_correct,
            "total": minions_total,
            "evaluations": minions_eval_log
        }, f, indent=2)

    print(f"\nEvaluation logs saved to:")
    print(f"- Baseline: {baseline_log_path}")
    print(f"- Minions: {minions_log_path}")

if __name__ == "__main__":
    evaluate_predictions() 