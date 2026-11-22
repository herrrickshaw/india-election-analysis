"""Run a straight-line analysis script (no functions, top-level pipeline) against synthetic
inputs, offline, without touching the repo tree.

The script source is compiled with its REAL repo path as the code filename (so coverage is
attributed to the repo file) but is executed with `__file__` pointing into a fake tree under
`tmp_path` (use a basename different from the script's, or coverage drops the file), so scripts that derive `REPO_ROOT` from `__file__` read/write only under tmp_path.
Optional `subs` are (old, new) text substitutions; each `old` must occur exactly once. They are
used only to shrink loop sizes or redirect hard-coded absolute input paths."""
import sys
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@contextmanager
def _isolated_imports():
    """Restore sys.path / sys.modules so a script's `sys.path.insert` + `from sexcode import`
    cannot leak into other tests."""
    saved_path = list(sys.path)
    saved_sex = sys.modules.pop("sexcode", None)
    try:
        yield
    finally:
        sys.path[:] = saved_path
        sys.modules.pop("sexcode", None)
        if saved_sex is not None:
            sys.modules["sexcode"] = saved_sex


def run_script(relpath, fake_file, subs=(), name="__main__"):
    path = ROOT / relpath
    src = path.read_text()
    for old, new in subs:
        assert src.count(old) == 1, f"substitution target must occur once: {old!r}"
        src = src.replace(old, new)
    code = compile(src, relpath, "exec")
    ns = {"__name__": name, "__file__": str(fake_file)}
    with _isolated_imports():
        exec(code, ns)
    return ns
