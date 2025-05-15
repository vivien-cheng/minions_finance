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
        os.makedirs(log_dir, exist_ok=True)
        self.conversation_log = []

    ORCHESTRATOR_PROMPT = """You are an Orchestrator managing a team of specialized financial agents to answer a user's question.
    Your role is to break down complex financial questions into subtasks and coordinate specialized agents to answer them.

    Available agents:
    1. RetrieverAgent: Finds relevant text snippets from a large document context.
    2. SimpleFinanceAgent: Understands basic financial terms and can identify relevant line items from context.
    3. CalculatorAgent: Performs arithmetic calculations on given numbers.
    4. AggregatorAgent: Synthesizes information to provide the final answer.

    Your task is to:
    1. Analyze the question and break it down into subtasks
    2. Plan a sequence of agent calls to solve these subtasks
    3. Coordinate the agents' responses
    4. Ensure the final answer is concise and accurate

    Return your decision as a JSON object with the following structure:
    {
        "agent": "RetrieverAgent" | "SimpleFinanceAgent" | "CalculatorAgent" | "AggregatorAgent",
        "subtask": "Specific task for the agent to perform",
        "explanation": "Why this agent and subtask are needed"
    }"""

    RETRIEVER_AGENT_PROMPT = """You are a Retriever Agent. Your role is to find and return the most relevant sections of text from the provided financial document (context) that can help answer a given sub-question or main question.

    When searching for relevant text:
    1. Focus on precision and relevance
    2. Look for specific financial metrics, numbers, and facts
    3. Consider the context of the question
    4. Return only the most relevant sections

    Format your response as a JSON object:
    {
        "relevant_text": "The most relevant text found",
        "explanation": "Why this text is relevant"
    }"""

    SIMPLE_FINANCE_AGENT_PROMPT = """You are a Simple Finance Agent. You have knowledge of basic financial concepts and metrics. You can explain terms or identify relevant financial statement line items based on a query and provided context.

    When analyzing financial information:
    1. Identify relevant financial terms and concepts
    2. Explain financial metrics and their meaning
    3. Connect terms to specific line items in statements
    4. Provide clear, concise explanations

    Format your response as a JSON object:
    {
        "analysis": "Your analysis of the financial information",
        "explanation": "Explanation of your analysis"
    }"""

    CALCULATOR_AGENT_PROMPT = """You are a Calculator Agent. Your role is to perform numerical calculations based on extracted numbers and a specific mathematical operation requested.

    When performing calculations:
    1. Only perform calculations when explicitly asked
    2. Show all steps clearly
    3. Use proper financial formulas
    4. Handle unit conversions accurately

    STRICT RESPONSE FORMAT:
    You MUST return a JSON object with exactly these fields:
    {
        "calculation": "Brief description of the calculation",
        "result": "The numerical result (as a string)",
        "explanation": "Brief explanation of the calculation"
    }

    VALIDATION RULES:
    1. The response MUST be valid JSON
    2. All fields must be strings
    3. The result must be a string representation of a number
    4. Keep explanations concise
    5. Do not include any text outside the JSON object
    6. Do not include markdown formatting
    7. Do not include LaTeX formulas

    Example valid response:
    {
        "calculation": "Percentage change in FCF Conversion Rate",
        "result": "8.91",
        "explanation": "FCF Conversion Rate increased by 8.91% from 2021 to 2022"
    }

    If no calculation is needed, respond with:
    {
        "calculation": "No calculation needed",
        "result": "0",
        "explanation": "No calculation was required for this task"
    }"""

    AGGREGATOR_AGENT_PROMPT = """You are an Aggregator Agent. Your role is to synthesize information from previous agent turns and the original question to formulate a final, concise answer.

    When synthesizing information:
    1. Combine relevant information from all agents
    2. Ensure the answer is complete and accurate
    3. Format the answer appropriately
    4. Provide a clear, concise response

    STRICT FORMATTING RULES:
    - For dollar values: Add $ symbol and round to 2 decimal places (e.g., $81.00)
    - For percentages: Include % symbol and round to 1 decimal place
    - For numerical values: Use appropriate precision
    - For segment names or specific items, always include the relevant numerical value (e.g., "Consumer segment shrunk by 0.9%")
    - Always include the correct unit or scale (e.g., million, billion, %, $) as appropriate
    - If the question specifies "answer in USD million/billion", do NOT include million/billion in your answer as it's already in the question
    - For yes/no questions, ALWAYS provide a brief explanation of your reasoning
    - Pay attention to the magnitude and format (e.g., $2.22 million, $1.00 billion, 2.22%)
    - Pay close attention to the exact format of the question and match it in your answer
    - If you do not follow these rules, your answer will be considered incorrect.

    VALIDATION CHECKLIST (perform all before finalizing your answer):
    1. Does the answer match the required format (currency, percent, etc.)?
    2. Are there any extra or missing units?
    3. For yes/no, is there a brief explanation?
    4. Is the answer complete and directly responsive to the question?
    5. If the question specifies a unit, do NOT repeat it in the answer.

    Format your response as a JSON object:
    {
        "final_answer": "The final answer (strictly formatted)",
        "explanation": "Brief explanation of how you arrived at this answer",
        "validation": "How you validated the answer",
        "confidence": "high|medium|low"
    }
    """

    def _extract_json_string(self, response):
        """Extract a JSON string from an OpenAI LLM response, handling tuples, lists, and markdown code blocks."""
        # If response is a tuple, take the first element
        if isinstance(response, tuple):
            response = response[0]
        # If response is a list, take the first element
        if isinstance(response, list):
            response = response[0]
        # If response is a dict with 'content', use that
        if isinstance(response, dict) and "content" in response:
            response = response["content"]
        # Remove markdown code blocks
        if isinstance(response, str):
            if "```json" in response:
                response = response.split("```json")[1].split("```", 1)[0].strip()
            elif "```" in response:
                response = response.split("```", 1)[1].split("```", 1)[0].strip()
            # Remove any LaTeX formulas
            response = re.sub(r'\\\[.*?\\\]', '', response)
            response = re.sub(r'\$.*?\$', '', response)
            # Remove any remaining non-JSON text
            response = re.sub(r'^[^{]*', '', response)
            response = re.sub(r'[^}]*$', '', response)
        return response

    def run_multi_agent(self, question: str, question_metadata: Dict[str, Any], context: str) -> str:
        """Run the multi-agent system to answer a question."""
        self.conversation_log = []
        current_context = context
        agent_responses = []
        round_count = 0
        
        while round_count < self.max_rounds:
            round_count += 1
            
            # Orchestrator step
            orchestrator_response = self.remote_client.chat(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": self.ORCHESTRATOR_PROMPT},
                    {"role": "user", "content": f"User's question: {question}\n\nMetadata: {json.dumps(question_metadata)}\n\nPrevious responses: {json.dumps(agent_responses)}"}
                ]
            )
            
            # Extract and parse orchestrator response
            response_text = self._extract_json_string(orchestrator_response)
            try:
                orchestrator_decision = json.loads(response_text)
            except Exception as e:
                print(f"[ERROR] Could not parse orchestrator response: {e}\nRaw: {response_text}")
                return f"Error in orchestrator: {e}"
                
            self.conversation_log.append({"type": "orchestrator_response", "content": orchestrator_decision})
            selected_agent = orchestrator_decision.get("agent", "")
            subtask = orchestrator_decision.get("subtask", "")
            
            # Agent step
            if selected_agent == "RetrieverAgent":
                agent_response = self.remote_client.chat(
                    model="gpt-4-turbo-preview",
                    messages=[
                        {"role": "system", "content": self.RETRIEVER_AGENT_PROMPT},
                        {"role": "user", "content": f"Context:\n{current_context}\n\nSubtask:\n{subtask}"}
                    ]
                )
                response_text = self._extract_json_string(agent_response)
                try:
                    agent_result = json.loads(response_text)
                    current_context = agent_result.get("relevant_text", "")
                    agent_responses.append({"agent": "RetrieverAgent", "result": agent_result})
                except Exception as e:
                    print(f"[ERROR] Could not parse RetrieverAgent response: {e}\nRaw: {response_text}")
                    return "Error: Could not parse RetrieverAgent response"
                    
            elif selected_agent == "SimpleFinanceAgent":
                agent_response = self.remote_client.chat(
                    model="gpt-4-turbo-preview",
                    messages=[
                        {"role": "system", "content": self.SIMPLE_FINANCE_AGENT_PROMPT},
                        {"role": "user", "content": f"Context:\n{current_context}\n\nSubtask:\n{subtask}"}
                    ]
                )
                response_text = self._extract_json_string(agent_response)
                try:
                    agent_result = json.loads(response_text)
                    agent_responses.append({"agent": "SimpleFinanceAgent", "result": agent_result})
                except Exception as e:
                    print(f"[ERROR] Could not parse SimpleFinanceAgent response: {e}\nRaw: {response_text}")
                    return "Error: Could not parse SimpleFinanceAgent response"
                    
            elif selected_agent == "CalculatorAgent":
                agent_response = self.remote_client.chat(
                    model="gpt-4-turbo-preview",
                    messages=[
                        {"role": "system", "content": self.CALCULATOR_AGENT_PROMPT},
                        {"role": "user", "content": f"Context:\n{current_context}\n\nSubtask:\n{subtask}"}
                    ]
                )
                response_text = self._extract_json_string(agent_response)
                try:
                    agent_result = json.loads(response_text)
                    # Validate the response format
                    required_fields = ["calculation", "result", "explanation"]
                    if not all(field in agent_result for field in required_fields):
                        raise ValueError("Missing required fields in calculator response")
                    if not isinstance(agent_result["result"], str):
                        agent_result["result"] = str(agent_result["result"])
                    agent_responses.append({"agent": "CalculatorAgent", "result": agent_result})
                except Exception as e:
                    print(f"[ERROR] Could not parse CalculatorAgent response: {e}\nRaw: {response_text}")
                    # Provide a fallback response
                    fallback_result = {
                        "calculation": "Error in calculation",
                        "result": "0",
                        "explanation": f"Failed to parse calculator response: {str(e)}"
                    }
                    agent_responses.append({"agent": "CalculatorAgent", "result": fallback_result})
                    return "Error: Could not parse CalculatorAgent response"
                    
            elif selected_agent == "AggregatorAgent":
                agent_response = self.remote_client.chat(
                    model="gpt-4-turbo-preview",
                    messages=[
                        {"role": "system", "content": self.AGGREGATOR_AGENT_PROMPT},
                        {"role": "user", "content": f"Original Question: {question}\n\nPrevious Responses: {json.dumps(agent_responses)}\n\nSubtask: {subtask}"}
                    ]
                )
                response_text = self._extract_json_string(agent_response)
                try:
                    agent_result = json.loads(response_text)
                    final_answer = agent_result.get("final_answer", "Error: No final answer provided")
                    return final_answer
                except Exception as e:
                    print(f"[ERROR] Could not parse AggregatorAgent response: {e}\nRaw: {response_text}")
                    return "Error: Could not parse AggregatorAgent response"
            else:
                print(f"[ERROR] Invalid agent selected: {selected_agent}")
                return "Error: Invalid agent selected"
                
            self.conversation_log.append({"type": "agent_response", "content": agent_responses})
            
        return "Error: Maximum number of rounds exceeded without reaching a final answer"

    def run(self, task: str, doc_metadata: Dict, context: str, max_rounds=None, log_path=None, logging_id=None):
        """Main entry point for running the multi-agent system."""
        final_answer = self.run_multi_agent(question=task, question_metadata=doc_metadata, context=context)

        # Save the conversation log
        if log_path:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "w") as f:
                json.dump(self.conversation_log, f, indent=2)
        
        return final_answer

# --- Script to run Condition 2 ---
if __name__ == "__main__":
    import json
    import os

    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise ValueError("Please set the OPENAI_API_KEY environment variable.")

    remote_client = OpenAIClient(api_key=OPENAI_API_KEY, model_name="gpt-4o")
    minions_instance = Minions(remote_client=remote_client, log_dir="multiagent_logs")
    num_examples = 50
    
    # Load the first few examples from the dataset
    dataset = []
    with open("data/financebench_open_source.jsonl", "r", encoding="utf-8") as f:
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
        try:
            result = minions_instance.run(task=question, doc_metadata=metadata, context=context)
            predicted_answers_condition2[financebench_id] = result
            print(f"Predicted answer (Condition 2) for {financebench_id}: {result}")
        except Exception as e:
            print(f"Error processing {financebench_id}: {str(e)}")
            predicted_answers_condition2[financebench_id] = f"Error: {str(e)}"

    # Save the predicted answers for Condition 2
    with open("predicted_answers/predicted_answers_condition2.json", "w", encoding="utf-8") as f:
        json.dump(predicted_answers_condition2, f, indent=4, ensure_ascii=False)

    print("\nPredicted answers for Condition 2 saved to predicted_answers/predicted_answers_condition2.json")