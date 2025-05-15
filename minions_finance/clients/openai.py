import logging
from typing import Any, Dict, List, Optional, Tuple
import os
import openai
from openai import OpenAI
import json
import sys

from minions_finance.usage import Usage

# Configure UTF-8 encoding
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

class OpenAIClient:
    def __init__(
        self,
        model_name: str = "gpt-4-turbo-preview",
        api_key: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        base_url: Optional[str] = None,
        use_responses_api: bool = False,
        tools: List[Dict[str, Any]] = None,
        reasoning_effort: str = "low",
    ):
        """
        Initialize the OpenAI client.

        Args:
            model_name: The name of the model to use (default: "gpt-4-turbo-preview")
            api_key: OpenAI API key (optional, falls back to environment variable if not provided)
            temperature: Sampling temperature (default: 0.0)
            max_tokens: Maximum number of tokens to generate (default: 4096)
            base_url: Base URL for the OpenAI API (optional, falls back to OPENAI_BASE_URL environment variable or default URL)
        """
        self.model_name = model_name
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
        self.logger = logging.getLogger("OpenAIClient")
        self.logger.setLevel(logging.INFO)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        # Initialize the client
        self.client = openai.OpenAI(api_key=self.api_key)
        if "o1-pro" in self.model_name:
            self.use_responses_api = True
        else:
            self.use_responses_api = use_responses_api
        self.tools = tools
        self.reasoning_effort = reasoning_effort

    def responses(
        self, messages: List[Dict[str, Any]], **kwargs
    ) -> Tuple[List[str], Usage]:

        assert len(messages) > 0, "Messages cannot be empty."

        if "response_format" in kwargs:
            # handle new format of structure outputs from openai
            kwargs["text"] = {"format": kwargs["response_format"]}
            del kwargs["response_format"]
            if self.tools:
                del kwargs["text"]

        try:

            # replace an messages that have "system" with "developer"
            for message in messages:
                if message["role"] == "system":
                    message["role"] = "developer"

            params = {
                "model": self.model_name,
                "messages": [{"role": msg["role"], "content": str(msg["content"]).encode('utf-8', errors='ignore').decode('utf-8')} for msg in messages],
                "max_completion_tokens": self.max_tokens,
                **kwargs,
            }
            
            if "o1" in self.model_name or "o3" in self.model_name:
                params["reasoning"] = {"effort": self.reasoning_effort}
                # delete "tools" from params
                del params["tools"]

            response = self.client.responses.create(
                **params,
            )
            output_text = response.output

        except Exception as e:
            self.logger.error(f"Error during OpenAI API call: {e}")
            raise

        outputs = [output_text[1].content[0].text]

        usage = response.usage.input_tokens

        # Extract usage information
        usage = Usage(
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
        )

        return outputs, usage

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Send a chat message to OpenAI API with proper UTF-8 encoding."""
        try:
            # Ensure all message content is properly encoded
            encoded_messages = []
            for msg in messages:
                if isinstance(msg.get("content"), str):
                    # Convert to UTF-8 if needed
                    content = msg["content"].encode("utf-8").decode("utf-8")
                    encoded_messages.append({
                        "role": msg["role"],
                        "content": content
                    })
                else:
                    encoded_messages.append(msg)

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=encoded_messages,
                **kwargs
            )
            
            # Extract and decode the response content
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                return content.encode("utf-8").decode("utf-8")
            return ""
            
        except Exception as e:
            print(f"Error in OpenAI API call: {str(e)}")
            raise

    def get_embedding(self, text: str, model: str = "text-embedding-ada-002") -> List[float]:
        """Get embeddings for a text using OpenAI's embedding model.
        
        Args:
            text: The text to get embeddings for
            messages: List of message dictionaries with 'role' and 'content' keys
            **kwargs: Additional arguments to pass to openai.chat.completions.create

        Returns:
            Tuple of (List[str], Usage) containing response strings and token usage
        """
        if self.use_responses_api:
            return self.responses(messages, **kwargs)
        else:
            assert len(messages) > 0, "Messages cannot be empty."

            try:
                params = {
                    "model": self.model_name,
                    "messages": [{"role": msg["role"], "content": msg["content"]} for msg in messages],
                    "max_completion_tokens": self.max_tokens,
                    **kwargs,
                }

                if "o1" not in self.model_name and "o3" not in self.model_name:
                    params["temperature"] = self.temperature
                if "o1" in self.model_name or "o3" in self.model_name:
                    params["reasoning_effort"] = self.reasoning_effort
                if self.tools:
                    params["tools"] = self.tools

                response = self.client.chat.completions.create(**params)
            except Exception as e:
                self.logger.error(f"Error during OpenAI API call: {e}")
                raise

            usage = Usage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
            )

            return [choice.message.content for choice in response.choices], usage

    def get_embedding(self, text: str, model: str = "text-embedding-ada-002") -> List[float]:
        """Get embeddings for a text using OpenAI's embedding model.
        
        Args:
            text: The text to get embeddings for
            model: The embedding model to use (default: text-embedding-ada-002)
            
        Returns:
            List of embedding values
        """
        try:
            response = self.client.embeddings.create(
                model=model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            raise Exception(f"Error getting embeddings: {str(e)}")