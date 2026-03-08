"""Utilities for parsing Python source using the standard library AST and chunking it for AI documentation.

This module provides a robust way to extract classes and functions (including methods)
as meaningful 'chunks' from Python source code. Each chunk contains positional info,
source code, and the extracted docstring.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type


@dataclass
class CodeChunk:
    """Represents a chunk of code (class or function)."""

    name: str
    type: str  # 'class' | 'function' | 'async_function'
    source: str
    docstring: Optional[str]
    start_line: int
    end_line: int
    parent_name: Optional[str] = None
    children: List[CodeChunk] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the chunk (and its children) to a dictionary."""
        return asdict(self)


class ChunkVisitor(ast.NodeVisitor):
    """AST visitor to collect classes and functions as hierarchical chunks."""

    def __init__(self, source: str):
        self.source = source
        self.chunks: List[CodeChunk] = []
        self._stack: List[CodeChunk] = []

    def _get_source(self, node: ast.AST) -> str:
        """Extract source segment for a node."""
        try:
            return ast.get_source_segment(self.source, node) or ""
        except (AttributeError, ValueError):
            # Fallback for Python < 3.8 or nodes without line info
            if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                lines = self.source.splitlines()
                # ast lines are 1-indexed
                return "\n".join(lines[node.lineno - 1 : node.end_lineno])
            return ""

    def _visit_definition(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
        node_type: str,
    ):
        """Common logic for visiting classes and functions."""
        chunk = CodeChunk(
            name=node.name,
            type=node_type,
            source=self._get_source(node),
            docstring=ast.get_docstring(node),
            start_line=node.lineno,
            end_line=getattr(node, "end_lineno", node.lineno),
            parent_name=self._stack[-1].name if self._stack else None,
        )

        if self._stack:
            self._stack[-1].children.append(chunk)
        else:
            self.chunks.append(chunk)

        self._stack.append(chunk)
        self.generic_visit(node)
        self._stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef):
        self._visit_definition(node, "class")

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._visit_definition(node, "function")

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._visit_definition(node, "async_function")


def parse_source(source: str) -> Tuple[ast.Module, str]:
    """Parse Python source into an AST Module."""
    return ast.parse(source), source


def parse_file(path: Path | str) -> Tuple[ast.Module, str]:
    """Read and parse a Python file."""
    p = Path(path)
    source = p.read_text(encoding="utf-8")
    return parse_source(source)


def get_chunks(source: str, hierarchical: bool = True) -> List[Dict[str, Any]]:
    """Extract class and function chunks from Python source.

    Args:
        source: The Python source code.
        hierarchical: If True, returns a tree-like structure. If False, returns a flat list.

    Returns:
        A list of dictionaries representing code chunks.
    """
    visitor = ChunkVisitor(source)
    tree = ast.parse(source)
    visitor.visit(tree)

    if hierarchical:
        return [c.to_dict() for c in visitor.chunks]

    # Flatten the tree if requested
    flat_list = []

    def _flatten(chunks: List[CodeChunk]):
        for c in chunks:
            # We copy but clear children for the flat representation
            data = asdict(c)
            data["children"] = []
            flat_list.append(data)
            _flatten(c.children)

    _flatten(visitor.chunks)
    return flat_list


def get_chunks_from_file(
    path: Path | str, hierarchical: bool = True
) -> List[Dict[str, Any]]:
    """Extract class and function chunks from a Python file."""
    source = Path(path).read_text(encoding="utf-8")
    return get_chunks(source, hierarchical)


# if __name__ == "__main__":
#     import sys
#     import json
#     import os
#     from pathlib import Path
#     # Simple CLI for testing
#     # if len(sys.argv) > 1:
#     target_path = Path(__file__).parent / "extraction.py"
#     chunks = get_chunks_from_file(target_path)
#     print(type(chunks))
#     # else:
#         # Self-test
#         # source = Path(__file__).read_text()
#         # chunks = get_chunks(source)
#         # print(f"Extracted {len(chunks)} top-level chunks from this file.")
#         # for chunk in chunks:
#         #     print(f"- {chunk['type'].capitalize()}: {chunk['name']} (Lines {chunk['start_line']}-{chunk['end_line']})")
