"""Load selected functions from a numbered analysis script WITHOUT running its
top-level pipeline (which reads local CSVs and writes outputs). Keeps imports,
literal constants and the requested function definitions only."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(relpath, *names):
    src = (ROOT / relpath).read_text()
    tree = ast.parse(src)
    keep = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            keep.append(node)
        elif isinstance(node, ast.Assign):
            try:
                ast.literal_eval(node.value)
                keep.append(node)
            except ValueError:
                pass
        elif isinstance(node, ast.FunctionDef) and node.name in names:
            keep.append(node)
    ns = {"__name__": "scriptload"}
    exec(compile(ast.Module(body=keep, type_ignores=[]), relpath, "exec"), ns)
    missing = [n for n in names if n not in ns]
    assert not missing, missing
    return ns
