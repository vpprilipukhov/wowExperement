# utils/code_validator.py
import ast
import re


class CodeValidator:
    """Продвинутая валидация генерируемого кода"""

    ALLOWED_FUNCTIONS = {'move', 'click', 'cast', 'interact'}

    def clean_code(self, raw_text):
        """Извлекает и проверяет код"""
        code = self._extract_code_block(raw_text)
        if not code:
            return None

        if not self._validate_syntax(code):
            return None

        return code

    def _extract_code_block(self, text):
        """Извлекает код из markdown-блока"""
        match = re.search(r'```python\n(.*?)\n```', text, re.DOTALL)
        return match.group(1).strip() if match else None

    def _validate_syntax(self, code):
        """Проверяет синтаксис и безопасность"""
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if not self._is_allowed_function(node):
                        return False
            return True
        except SyntaxError:
            return False

    def _is_allowed_function(self, node):
        """Проверяет, разрешена ли функция"""
        if isinstance(node.func, ast.Name):
            return node.func.id in self.ALLOWED_FUNCTIONS
        return False