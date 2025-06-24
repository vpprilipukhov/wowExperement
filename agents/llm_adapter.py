# agents/llm_adapter.py
from langchain_core.runnables import Runnable
from typing import Any, Dict, List, Optional

class YandexLLMAdapter(Runnable):
    def __init__(self, llm_provider):
        self.llm_provider = llm_provider

    def invoke(self, input: Dict[str, Any], config: Optional[Dict] = None) -> Dict[str, Any]:
        messages = input.get("messages", [])
        response = self.llm_provider.get_completion(messages)
        return {
            "content": response["result"]["alternatives"][0]["message"]["text"],
            "response": response
        }