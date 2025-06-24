import ast


class SecurityError(Exception):
    pass


def validate_code(code):
    """Проверяет безопасность сгенерированного кода"""
    allowed_functions = {'move_to', 'click', 'cast_spell', 'loot'}

    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id not in allowed_functions:
                    raise SecurityError(f"Запрещенная функция: {node.func.id}")
        return code
    except SyntaxError:
        return ""
    except SecurityError as e:
        print(f"Ошибка безопасности: {e}")
        return ""