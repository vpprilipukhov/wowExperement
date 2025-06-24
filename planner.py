import random
from typing import List, Dict


def generate_plan(state: Dict) -> List[Dict]:
    """Генерирует последовательность действий на основе состояния"""
    plan = []

    # Простая логика принятия решений
    if not state['health']:
        return [{'type': 'revive'}]

    if state['enemies']:
        target = random.choice(state['enemies'])
        plan.extend([
            {'type': 'move_to', 'target': target},
            {'type': 'attack', 'target': target}
        ])
    elif state['npcs']:
        plan.append({'type': 'move_to', 'target': state['npcs'][0]})
    else:
        plan.append({'type': 'explore'})

    return plan


# Пример использования с LLM (раскомментировать при подключении API)
"""
from llm_provider import LLMProvider

class AIPlanner:
    def __init__(self):
        self.llm = LLMProvider()

    def generate_plan(self, state):
        prompt = f"""
# Игровое
# состояние:
# - Здоровье: {'есть' if state['health'] else 'нет'}
# - Враги: {len(state['enemies'])}
# - NPC: {len(state['npcs'])}
# Сгенерируй
# JSON - план
# действий
"""
        response = self.llm.get_completion(prompt)
        return self._parse_response(response)
"""