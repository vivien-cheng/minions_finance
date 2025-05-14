def calculate(expression: str) -> str:
    """Evaluates a simple mathematical expression."""
    try:
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"Error: {e}"