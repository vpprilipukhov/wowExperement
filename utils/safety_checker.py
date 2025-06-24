import ast


class SecurityError(Exception):
    pass


class SafeCodeExecutor:
    def __init__(self):
        self.allowed_functions = {
            'move_to', 'click', 'cast_spell', 'loot'
        }

    def validate_code(self, code):
        if not code.strip():
            return ""

        try:
            tree = ast.parse(code)
            self.check_node(tree)
            return code
        except SyntaxError:
            return ""
        except SecurityError as e:
            print(f"Security violation: {e}")
            return ""

    def check_node(self, node):
        if isinstance(node, ast.Call):
            func_name = self.get_func_name(node.func)
            if func_name not in self.allowed_functions:
                raise SecurityError(f"Disallowed function: {func_name}")

        for child in ast.iter_child_nodes(node):
            self.check_node(child)

    def get_func_name(self, node):
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return ""


if __name__ == "__main__":
    # Тест валидатора кода
    checker = SafeCodeExecutor()

    safe_code = "move_to(0.5, 0.5)"
    unsafe_code = "import os; os.remove('important_file')"

    print(f"Safe code test: {checker.validate_code(safe_code)}")
    print(f"Unsafe code test: {checker.validate_code(unsafe_code)}")