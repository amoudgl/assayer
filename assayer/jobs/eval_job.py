import importlib
import importlib.util
import os


def load_evaluator_func_from_path(ref: str):
    """
    Loads evaluator function from either:
    - path/to/file.py:func_name
    - module.path.func_name
    """
    if ":" in ref:
        file_path, func_name = ref.split(":")
        file_path = os.path.abspath(file_path)

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        spec = importlib.util.spec_from_file_location("user_module", file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot import from {file_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    else:
        parts = ref.split(".")
        module_path = ".".join(parts[:-1])
        func_name = parts[-1]
        module = importlib.import_module(module_path)
    try:
        return getattr(module, func_name)
    except AttributeError:
        raise ImportError(f"Function '{func_name}' not found in module")


def launch_eval(evaluator_path, checkpoint_path):
    evaluator_fn = load_evaluator_func_from_path(evaluator_path)
    metrics = evaluator_fn(checkpoint_path)
    return metrics
