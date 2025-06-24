from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_community.llms import YandexGPT
from utils.config_loader import ConfigLoader
from utils.safety_checker import SafeCodeExecutor
import re


class DecisionEngine:
    def __init__(self):
        self.config = ConfigLoader()
        self.llm = self.init_llm()
        self.prompt_template = self.create_prompt_template()
        self.safe_executor = SafeCodeExecutor()

    def init_llm(self):
        provider = self.config.get('llm.provider')
        model = self.config.get('llm.model')
        api_key = self.config.get('llm.api_key')

        if provider == "yandex":
            return YandexGPT(
                model_name=model,
                api_key=api_key,
                temperature=0.3
            )
        raise ValueError(f"Unsupported provider: {provider}")

    def create_prompt_template(self):
        return PromptTemplate(
            input_variables=["state"],
            template="""
            Ты - AI агент в World of Warcraft. Текущее состояние:
            {state}

            Сгенерируй ОДНО простое действие для тестирования системы.
            Формат ответа: ```python
            # Только один вызов функции
            ```
            """
        )

    def generate_action(self, game_state):
        chain = LLMChain(llm=self.llm, prompt=self.prompt_template)
        response = chain.invoke({"state": str(game_state)})
        action_code = self.extract_code(response['text'])
        return self.safe_executor.validate_code(action_code)

    def extract_code(self, text):
        pattern = r"```python(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL)
        return matches[0].strip() if matches else text


if __name__ == "__main__":
    # Тест движка решений
    engine = DecisionEngine()
    test_state = {"health": 100, "target": "Training Dummy"}
    action = engine.generate_action(test_state)
    print(f"Generated action: {action}")