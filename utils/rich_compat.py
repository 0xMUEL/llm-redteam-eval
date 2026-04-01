"""
Compatibility shim for the 'rich' library.
Provides minimal fallback implementations when rich is not installed.
"""

import re

try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.panel import Panel
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

    def _strip_rich_markup(text: str) -> str:
        """Remove rich-style [markup] tags from text."""
        return re.sub(r'\[/?[a-z_ ]+\]', '', text)

    class Console:
        """Minimal Console replacement."""
        def print(self, *args, **kwargs):
            parts = []
            for a in args:
                if isinstance(a, (Panel, Table)):
                    print(str(a))
                    return
                parts.append(_strip_rich_markup(str(a)))
            print(*parts)

    class Table:
        """Minimal Table replacement."""
        def __init__(self, title="", **kwargs):
            self.title = title
            self.columns = []
            self.rows = []

        def add_column(self, name, **kwargs):
            self.columns.append(name)

        def add_row(self, *values):
            self.rows.append(values)

        def __str__(self):
            lines = []
            if self.title:
                lines.append(f"\n{'=' * 60}")
                lines.append(f"  {self.title}")
                lines.append(f"{'=' * 60}")
            # Header
            header = " | ".join(f"{c:<12}" for c in self.columns)
            lines.append(header)
            lines.append("-" * len(header))
            for row in self.rows:
                cleaned = [_strip_rich_markup(str(v)) for v in row]
                lines.append(" | ".join(f"{c:<12}" for c in cleaned))
            return "\n".join(lines)

    class Panel:
        """Minimal Panel replacement."""
        def __init__(self, content, title="", **kwargs):
            self.content = content
            self.title = title

        def __str__(self):
            lines = [f"\n--- {self.title} ---"] if self.title else ["\n---"]
            lines.append(_strip_rich_markup(str(self.content)))
            lines.append("---")
            return "\n".join(lines)

    class SpinnerColumn:
        pass

    class TextColumn:
        def __init__(self, *a, **k):
            pass

    class Progress:
        def __init__(self, *a, **k):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass
