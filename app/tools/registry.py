from __future__ import annotations

import importlib
import pkgutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.tools.base import Tool


class ToolRegistry:
    """Registry of all tools available to the agent."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        return self._tools[name]

    def list_all(self) -> list[Tool]:
        return list(self._tools.values())

    def list_openai_specs(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self._tools.values()
        ]

    def scan_package(self, package_name: str) -> None:
        """Auto-discover and register all tools in a package."""
        package = importlib.import_module(package_name)
        for _, module_name, _ in pkgutil.walk_packages(
            package.__path__, package.__name__ + "."
        ):
            if module_name == package_name + ".base" or module_name == package_name + ".registry":
                continue
            module = importlib.import_module(module_name)
            if hasattr(module, "register"):
                module.register(self)
