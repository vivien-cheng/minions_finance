from typing import List, Dict, Any, Optional, Union, Tuple
import json
import re
import os
import time
from datetime import datetime
from pydantic import BaseModel, field_validator, Field
from inspect import getsource

from minions_finance.utils.chunking import chunk_by_section
from minions_finance.prompts.minions import WORKER_PROMPT_SHORT, REMOTE_ANSWER
from minions_finance.clients.openai import OpenAIClient
from minions_finance.tools.finance_utils import extract_monetary_values, check_financial_terms
from minions_finance.tools.retriever_tool import retrieve_relevant_context
from minions_finance.utils.retrievers import bm25_retrieve_top_k_chunks
from minions_finance.tools.simple_calculator import calculate

class JobManifest(BaseModel):
    chunk: str
    task: str
    advice: Optional[str] = None
    chunk_id: Optional[int] = None
    task_id: Optional[int] = None
    job_id: Optional[int] = None

class JobOutput(BaseModel):
    explanation: str
    citation: Optional[str] = None
    answer: Optional[str] = None

class Job(BaseModel):
    manifest: JobManifest
    output: JobOutput
    sample: str
    include: Optional[bool] = None

USEFUL_IMPORTS = {
    "List": List,
    "Optional": Optional,
    "Dict": Dict,
    "Any": Any,
    "Union": Union,
    "Tuple": Tuple,
    "BaseModel": BaseModel,
    "field_validator": field_validator,
}

class Minions:
    def __init__(self, remote_client, max_rounds=5, log_dir="minions_logs", **kwargs):
        self.remote_client = remote_client
        self.max_rounds = max_rounds
        self.log_dir = log_dir
        self.worker_prompt_template = WORKER_PROMPT_SHORT
        os.makedirs(log_dir, exist_ok=True)

    def _execute_code(self, code: str, starting_globals: Dict[str, Any], fn_name: str, **kwargs):
        exec_globals = {**starting_globals}
        exec(code, exec_globals)
        if fn_name not in exec_globals:
            raise ValueError(f"Function {fn_name} not found.")
        return exec_globals[fn_name](**kwargs), code

    def run_single_agent(self, question: str, context: str, system_prompt: str, tools: Optional[List[Dict]] = None):
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{question}\n\nAnswer:"}
        ]
        try:
            response = self.remote_client.chat(messages=messages, tools=tools)
            return response[0]
        except Exception as e:
            return f"Error: {e}"

    def run_multi_agent(self, question_metadata: Dict, context: str):
        question = question_metadata["question"]
        metadata = json.dumps(question_metadata)

        orchestrator_prompt = f"""You are an orchestrator for a team of specialized agents. Your goal is to solve the user's question by delegating tasks to the appropriate agents. You have the following agents available with their descriptions and tools:

        - Retriever: This agent can retrieve relevant information from the provided context. Tools: ['retrieve_relevant_context']
        - Calculator: This agent can perform mathematical calculations. Tools: ['calculate']
        - Finance Analyst: This agent can understand and extract information from financial texts. Tools: ['extract_monetary_value', 'check_financial_term']
        - Aggregator: This agent synthesizes the answers from other agents into a final response. Tools: []

        For the question: "{question}", orchestrate the agents to find the answer. Only the agents have access to the full context provided later.

        Your goal is to have the agents work together to produce a final answer. Return the final answer when you believe it has been found.
        """

        agents = {
            "Retriever": {
                "system_prompt": "You are a highly effective information retriever. Your goal is to find relevant snippets from the provided context that can help answer the user's question. When you receive a query, search through the context and return the most relevant parts.",
                "tools": ["retrieve_relevant_context"]
            },
            "Calculator": {
                "system_prompt": "You are a precise and reliable calculator. Your role is to perform mathematical calculations accurately based on the expressions provided to you.",
                "tools": ["calculate"]
            },
            "Finance Analyst": {
                "system_prompt": "You are an expert finance analyst. Your task is to understand financial texts and extract specific information, such as monetary values or the presence of financial terms, based on the user's requests.",
                "tools": ["extract_monetary_value", "check_financial_term"]
            },
            "Aggregator": {
                "system_prompt": "You are a final aggregator. Your role is to take the information provided by the other agents and synthesize it into a concise and accurate answer to the original question.",
                "tools": []
            }
        }

        available_tools = {
            "retrieve_relevant_context": retrieve_relevant_context,
            "calculate": calculate,
            "extract_monetary_value": extract_monetary_values,
            "check_financial_term": check_financial_terms,
        }

        # --- Orchestration Logic (Simple for this example) ---
        # In a more complex scenario, the orchestrator would analyze the question
        # and decide the sequence and agents to call. For this simple case,
        # we'll make a basic decision based on keywords in the question.

        if "capital expenditure" in question.lower() or "capex" in question.lower():
            tool_to_use = "retrieve_relevant_context"
            agent_to_call = "Retriever"
        elif "what is the" in question.lower() and ("amount" in question.lower() or "value" in question.lower()):
            tool_to_use = "retrieve_relevant_context"
            agent_to_call = "Retriever"
        elif "is" in question.lower() and "ratio" in question.lower():
            tool_to_use = "retrieve_relevant_context"
            agent_to_call = "Retriever"
        elif "calculate" in question.lower():
            tool_to_use = "calculate"
            agent_to_call = "Calculator"
        elif "billion" in question.lower() or "million" in question.lower() or "$" in question:
            tool_to_use = "extract_monetary_value"
            agent_to_call = "Finance Analyst"
        elif "whether" in question.lower() or "does" in question.lower():
            tool_to_use = "check_financial_term"
            agent_to_call = "Finance Analyst"
        else:
            # Default action if no specific pattern is matched
            tool_to_use = "retrieve_relevant_context"
            agent_to_call = "Retriever"

        print(f"Orchestrator chose agent: {agent_to_call} with tool: {tool_to_use}")

        agent_prompt = f"{agents[agent_to_call]['system_prompt']}\n\nQuestion: {question}"
        tool_arguments = {}
        if tool_to_use == "retrieve_relevant_context":
            tool_arguments = {"query": question, "context": context}
        elif tool_to_use == "calculate":
            # This is a very basic way to extract an expression; a more robust method would be needed
            expression = question.replace("calculate", "").strip()
            tool_arguments = {"expression": expression}
        elif tool_to_use in ["extract_monetary_value", "check_financial_term"]:
            tool_arguments = {"text": context}
            if tool_to_use == "check_financial_term":
                term_to_check = question.lower().split("term")[-1].strip().strip("?")
                tool_arguments["terms"] = [term_to_check]

        tool_code = None
        if tool_to_use and tool_to_use in available_tools:
            tool_code = available_tools[tool_to_use]
            print(f"Calling tool: {tool_to_use} with arguments: {tool_arguments}")
            tool_result = tool_code(**tool_arguments)
            print(f"Tool result: {tool_result}")
            aggregator_prompt = f"{agents['Aggregator']['system_prompt']}\n\nQuestion: {question}\n\nInformation from {agent_to_call}: {tool_result}\n\nFinal Answer:"
            final_answer = self.run_single_agent(question=question, context=str(tool_result), system_prompt=aggregator_prompt)
            return final_answer
        else:
            aggregator_prompt = f"{agents['Aggregator']['system_prompt']}\n\nQuestion: {question}\n\nNo specific tool was used. Here's the context:\n{context}\n\nFinal Answer:"
            final_answer = self.run_single_agent(question=question, context=context, system_prompt=aggregator_prompt)
            return final_answer

    def run(self, task: str, doc_metadata: Dict, context: str, max_rounds=None, log_path=None, logging_id=None):
        # For Condition 2, we'll directly call the multi-agent system
        final_answer = self.run_multi_agent(question_metadata={"question": task, "metadata": doc_metadata}, context=context)

        conversation_log = {
            "task": task,
            "doc_metadata": doc_metadata,
            "final_answer": final_answer,
            "system": "simple_multi_agent"
        }

        # Save the conversation log
        if log_path:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(conversation_log, f, indent=4, ensure_ascii=False)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_task = re.sub(r"[^a-zA-Z0-9]", "_", task[:15])
            log_filename = f"{timestamp}_{safe_task}_multiagent.json"
            log_path = os.path.join(self.log_dir, log_filename)
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(conversation_log, f, indent=4, ensure_ascii=False)
        print(f"\n=== Multi-Agent Log Saved to {log_path} ===")
        if isinstance(final_answer, str):
            final_answer_encoded = final_answer.encode('utf-8', errors='ignore').decode('utf-8')
        else:
            final_answer_encoded = final_answer

        conversation_log["final_answer"] = final_answer_encoded
        return {"final_answer": final_answer_encoded, "log_file": log_path, "conversation_log": conversation_log}
    
# --- Script to run Condition 2 ---
if __name__ == "__main__":
    import json
    import os

    # Replace with your actual OpenAI API key
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise ValueError("Please set the OPENAI_API_KEY environment variable.")

    remote_client = OpenAIClient(api_key=OPENAI_API_KEY, model_name="gpt-4o")
    minions_instance = Minions(remote_client=remote_client, log_dir="multiagent_logs")
    num_examples = 50

    # Load the first few examples from the dataset
    dataset = []
    with open("data/financebench_open_source.jsonl", "r") as f:
        for i, line in enumerate(f):
            if i < num_examples:
                dataset.append(json.loads(line))
            else:
                break

    predicted_answers_condition2 = {}

    for example in dataset:
        financebench_id = example["financebench_id"]
        question = example["question"]
        evidence_texts = [item["evidence_text"] for item in example["evidence"]]
        context = "\n".join(evidence_texts)
        metadata = {k: example[k] for k in example if k not in ["evidence"]}

        print(f"\n--- Processing {financebench_id} ---")
        result = minions_instance.run(task=question, doc_metadata=metadata, context=context)
        predicted_answers_condition2[financebench_id] = result["final_answer"]
        print(f"Predicted answer (Condition 2) for {financebench_id}: {result['final_answer']}")

    # Save the predicted answers for Condition 2
    with open("predicted_answers/predicted_answers_condition2.json", "w", encoding="utf-8") as f:
        json.dump(predicted_answers_condition2, f, indent=4, ensure_ascii=False)

    print("\nPredicted answers for Condition 2 saved to predicted_answers/predicted_answers_condition2.json")