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
            eval_prompt = """You are an expert evaluator of financial question answering systems. Your task is to evaluate whether a predicted answer matches the gold answer, considering the following criteria:

            1. Numerical Accuracy:
            - For numerical answers, allow a 10% tolerance margin
            - Accept answers with or without units (e.g., "8.74" is equivalent to "$8.74 billion")
            - Accept answers with different scales (e.g., "1577" is equivalent to "$1,577 million")
            - Accept answers with or without currency symbols
            - Accept answers with or without thousands separators
            - Accept answers with different decimal places

            2. Unit Consistency:
            - Accept any unit format as long as the number is correct
            - Accept abbreviations (e.g., "M" for million, "B" for billion)
            - Accept answers with or without units
            - Accept answers with different unit scales (e.g., "million" vs "billion")
            - Accept answers with or without currency symbols

            3. Format Consistency:
            - Accept any format as long as the meaning is preserved
            - Accept answers with or without punctuation
            - Accept answers with different capitalization
            - Accept answers with or without spaces
            - Accept answers with different number formats (e.g., "1,577" vs "1577")

            4. Semantic Equivalence:
            - Accept answers that convey the same meaning, even if expressed differently
            - Accept answers that include additional context or explanation
            - Accept answers that use different but equivalent terminology
            - Accept answers that provide more detail than the gold answer
            - Accept answers that use different but equivalent expressions

            5. Segment Names and Categories:
            - Accept partial matches for segment names (e.g., "Consumer" is equivalent to "Consumer segment")
            - Accept answers that use different but equivalent category names
            - Accept answers that provide more context about the segment
            - Accept answers that use different but equivalent terminology

            6. Yes/No Questions:
            - Accept answers that include explanation as long as the yes/no is correct
            - Accept answers that provide additional context
            - Accept answers that use different but equivalent expressions
            - Accept answers that include supporting metrics or reasoning

            7. Percentage Changes:
            - Accept answers that focus on the direction of change rather than exact numbers
            - Accept answers that provide additional context about the change
            - Accept answers that use different but equivalent expressions
            - Accept answers that include supporting metrics or reasoning

            8. General Guidelines:
            - Be very lenient in accepting answers that are semantically correct
            - Focus on the meaning and correctness of the answer rather than exact formatting
            - Accept answers that provide additional context or explanation
            - Accept answers that use different but equivalent expressions
            - Accept answers that include supporting metrics or reasoning

            Examples of acceptable variations:
            - "8.74" is equivalent to "$8.74 billion"
            - "1577" is equivalent to "$1,577 million"
            - "Consumer" is equivalent to "Consumer segment"
            - "Yes, because..." is equivalent to "Yes"
            - "The operating margin decreased by 5%" is equivalent to "-5%"
            - "The company has a healthy liquidity position" is equivalent to "Yes"

            For each example, evaluate whether the predicted answer matches the gold answer based on these criteria. If the answers are semantically equivalent, even if expressed differently, mark it as correct.

            Output Format:
            {
                "overall_accuracy": <float between 0 and 1>,
                "num_correct": <integer>,
                "total": <integer>,
                "evaluations": [
                    {
                        "financebench_id": <string>,
                        "gold_answer": <string>,
                        "predicted_answer": <string>,
                        "is_correct": <boolean>,
                        "explanation": <string>
                    },
                    ...
                ]
            }"""

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
            eval_prompt = """You are an expert evaluator of financial question answering systems. Your task is to evaluate whether a predicted answer matches the gold answer, considering the following criteria:

            1. Numerical Accuracy:
            - For numerical answers, allow a 10% tolerance margin
            - Accept answers with or without units (e.g., "8.74" is equivalent to "$8.74 billion")
            - Accept answers with different scales (e.g., "1577" is equivalent to "$1,577 million")
            - Accept answers with or without currency symbols
            - Accept answers with or without thousands separators
            - Accept answers with different decimal places

            2. Unit Consistency:
            - Accept any unit format as long as the number is correct
            - Accept abbreviations (e.g., "M" for million, "B" for billion)
            - Accept answers with or without units
            - Accept answers with different unit scales (e.g., "million" vs "billion")
            - Accept answers with or without currency symbols

            3. Format Consistency:
            - Accept any format as long as the meaning is preserved
            - Accept answers with or without punctuation
            - Accept answers with different capitalization
            - Accept answers with or without spaces
            - Accept answers with different number formats (e.g., "1,577" vs "1577")

            4. Semantic Equivalence:
            - Accept answers that convey the same meaning, even if expressed differently
            - Accept answers that include additional context or explanation
            - Accept answers that use different but equivalent terminology
            - Accept answers that provide more detail than the gold answer
            - Accept answers that use different but equivalent expressions

            5. Segment Names and Categories:
            - Accept partial matches for segment names (e.g., "Consumer" is equivalent to "Consumer segment")
            - Accept answers that use different but equivalent category names
            - Accept answers that provide more context about the segment
            - Accept answers that use different but equivalent terminology

            6. Yes/No Questions:
            - Accept answers that include explanation as long as the yes/no is correct
            - Accept answers that provide additional context
            - Accept answers that use different but equivalent expressions
            - Accept answers that include supporting metrics or reasoning

            7. Percentage Changes:
            - Accept answers that focus on the direction of change rather than exact numbers
            - Accept answers that provide additional context about the change
            - Accept answers that use different but equivalent expressions
            - Accept answers that include supporting metrics or reasoning

            8. General Guidelines:
            - Be very lenient in accepting answers that are semantically correct
            - Focus on the meaning and correctness of the answer rather than exact formatting
            - Accept answers that provide additional context or explanation
            - Accept answers that use different but equivalent expressions
            - Accept answers that include supporting metrics or reasoning

            Examples of acceptable variations:
            - "8.74" is equivalent to "$8.74 billion"
            - "1577" is equivalent to "$1,577 million"
            - "Consumer" is equivalent to "Consumer segment"
            - "Yes, because..." is equivalent to "Yes"
            - "The operating margin decreased by 5%" is equivalent to "-5%"
            - "The company has a healthy liquidity position" is equivalent to "Yes"

            For each example, evaluate whether the predicted answer matches the gold answer based on these criteria. If the answers are semantically equivalent, even if expressed differently, mark it as correct.

            Output Format:
            {
                "overall_accuracy": <float between 0 and 1>,
                "num_correct": <integer>,
                "total": <integer>,
                "evaluations": [
                    {
                        "financebench_id": <string>,
                        "gold_answer": <string>,
                        "predicted_answer": <string>,
                        "is_correct": <boolean>,
                        "explanation": <string>
                    },
                    ...
                ]
            }"""

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