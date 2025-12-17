from __future__ import annotations

import math
from typing import Union

from mcp.server.fastmcp import FastMCP

Number = Union[int, float]

mcp = FastMCP("demosquare")


@mcp.tool()
def square(n: Number) -> float:
    """Return n squared."""
    return float(n) * float(n)


@mcp.tool()
def sqrt(n: Number) -> float:
    """Return the (principal) square root of n.

    Raises:
        ValueError: if n is negative.
    """
    value = float(n)
    if value < 0:
        raise ValueError("sqrt is only defined for non-negative numbers")
    return math.sqrt(value)


if __name__ == "__main__":
    # FastMCP runs over stdio by default in the Python MCP SDK.
    # Using stdio transport is required for VS Code MCP server integration.
    mcp.run(transport="stdio")
