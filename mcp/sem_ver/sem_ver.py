from __future__ import annotations

import re
from enum import Enum
from typing import Annotated, Any, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

mcp = FastMCP("sem_ver")

# SemVer 2.0.0 (allows optional prerelease/build). This is intentionally strict.
_SEMVER_PATTERN = (
    r"^(0|[1-9]\\d*)\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\\.[0-9A-Za-z-]+)*))?"
    r"(?:\\+([0-9A-Za-z-]+(?:\\.[0-9A-Za-z-]+)*))?$"
)
_SEMVER_RE = re.compile(_SEMVER_PATTERN)


class BumpPart(str, Enum):
    major = "major"
    minor = "minor"
    patch = "patch"


class CompareOp(str, Enum):
    lt = "lt"
    lte = "lte"
    eq = "eq"
    gte = "gte"
    gt = "gt"


class BumpVersionArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    version: Annotated[
        str,
        Field(
            description="Current version (SemVer 2.0.0). Examples: 1.2.3, 1.2.3-alpha.1, v1.2.3",
            min_length=1,
        ),
    ]
    part: Annotated[BumpPart, Field(description="Which part of the version to bump")]
    dry_run: Annotated[
        bool,
        Field(description="Compute the change without writing", default=True),
    ]
    allow_v_prefix: Annotated[
        bool,
        Field(description="Allow a leading 'v' prefix (e.g. v1.2.3)", default=True),
    ]
    keep_prerelease: Annotated[
        bool,
        Field(
            description="If true, preserve prerelease/build; otherwise clear them when bumping",
            default=False,
        ),
    ]

    @field_validator("version")
    @classmethod
    def _validate_version(cls, value: str, info: Any) -> str:
        allow_v_prefix = True
        if info.data and "allow_v_prefix" in info.data:
            allow_v_prefix = bool(info.data["allow_v_prefix"])

        candidate = value
        if allow_v_prefix and candidate.startswith("v"):
            candidate = candidate[1:]

        if not _SEMVER_RE.match(candidate):
            raise ValueError("version must be a valid SemVer 2.0.0 string")

        # Preserve original formatting (including 'v') for display, but downstream code will normalize.
        return value


class CompareVersionsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    left: Annotated[str, Field(description="Left SemVer (e.g. 1.2.3)", min_length=1)]
    right: Annotated[str, Field(description="Right SemVer (e.g. 2.0.0-alpha.1)", min_length=1)]
    op: Annotated[CompareOp, Field(description="Comparison operator")]
    allow_v_prefix: Annotated[
        bool,
        Field(description="Allow a leading 'v' prefix (e.g. v1.2.3)", default=True),
    ]

    @field_validator("left", "right")
    @classmethod
    def _validate_semver(cls, value: str, info: Any) -> str:
        allow_v_prefix = True
        if info.data and "allow_v_prefix" in info.data:
            allow_v_prefix = bool(info.data["allow_v_prefix"])

        candidate = value
        if allow_v_prefix and candidate.startswith("v"):
            candidate = candidate[1:]

        if not _SEMVER_RE.match(candidate):
            raise ValueError("version must be a valid SemVer 2.0.0 string")

        return value


def _parse_semver(value: str, *, allow_v_prefix: bool) -> tuple[int, int, int, Optional[list[str]], Optional[str]]:
    candidate = value
    if allow_v_prefix and candidate.startswith("v"):
        candidate = candidate[1:]

    match = _SEMVER_RE.match(candidate)
    if not match:
        raise ValueError("version must be a valid SemVer 2.0.0 string")

    major_s, minor_s, patch_s, prerelease_s, build_s = match.groups()
    prerelease = prerelease_s.split(".") if prerelease_s else None
    return int(major_s), int(minor_s), int(patch_s), prerelease, build_s


def _format_semver(
    major: int,
    minor: int,
    patch: int,
    prerelease: Optional[list[str]] = None,
    build: Optional[str] = None,
) -> str:
    base = f"{major}.{minor}.{patch}"
    if prerelease:
        base += "-" + ".".join(prerelease)
    if build:
        base += "+" + build
    return base


def _cmp_ident(a: str, b: str) -> int:
    a_is_num = a.isdigit()
    b_is_num = b.isdigit()

    if a_is_num and b_is_num:
        ai = int(a)
        bi = int(b)
        return -1 if ai < bi else (1 if ai > bi else 0)

    if a_is_num and not b_is_num:
        return -1
    if not a_is_num and b_is_num:
        return 1

    return -1 if a < b else (1 if a > b else 0)


def _compare_semver(
    left: str,
    right: str,
    *,
    allow_v_prefix: bool,
) -> int:
    l_major, l_minor, l_patch, l_pre, _l_build = _parse_semver(left, allow_v_prefix=allow_v_prefix)
    r_major, r_minor, r_patch, r_pre, _r_build = _parse_semver(right, allow_v_prefix=allow_v_prefix)

    if (l_major, l_minor, l_patch) != (r_major, r_minor, r_patch):
        return -1 if (l_major, l_minor, l_patch) < (r_major, r_minor, r_patch) else 1

    # If majors/minors/patch equal: a version without prerelease has higher precedence.
    if l_pre is None and r_pre is None:
        return 0
    if l_pre is None:
        return 1
    if r_pre is None:
        return -1

    # Both have prerelease identifiers.
    for a, b in zip(l_pre, r_pre):
        c = _cmp_ident(a, b)
        if c != 0:
            return c

    if len(l_pre) == len(r_pre):
        return 0
    return -1 if len(l_pre) < len(r_pre) else 1


@mcp.tool()
def bump_version(args: BumpVersionArgs) -> dict[str, object]:
    """Bump a SemVer 2.0.0 version.

    Demonstrates strict, structured tool inputs using Pydantic + Enums.

    Notes:
        This demo returns a computed result only (even when dry_run is false).
    """

    major, minor, patch, prerelease, build = _parse_semver(
        args.version,
        allow_v_prefix=args.allow_v_prefix,
    )

    if args.part == BumpPart.major:
        major += 1
        minor = 0
        patch = 0
    elif args.part == BumpPart.minor:
        minor += 1
        patch = 0
    else:
        patch += 1

    if not args.keep_prerelease:
        prerelease = None
        build = None

    new_version = _format_semver(major, minor, patch, prerelease=prerelease, build=build)

    return {
        "old": args.version,
        "new": new_version,
        "dryRun": args.dry_run,
    }


@mcp.tool()
def compare_versions(args: CompareVersionsArgs) -> dict[str, object]:
    """Compare two SemVer 2.0.0 versions.

    Another structured-tool example using Enums to constrain allowed operators.
    """

    cmp_value = _compare_semver(args.left, args.right, allow_v_prefix=args.allow_v_prefix)

    op_to_bool = {
        CompareOp.lt: cmp_value < 0,
        CompareOp.lte: cmp_value <= 0,
        CompareOp.eq: cmp_value == 0,
        CompareOp.gte: cmp_value >= 0,
        CompareOp.gt: cmp_value > 0,
    }

    return {
        "left": args.left,
        "right": args.right,
        "op": args.op.value,
        "result": op_to_bool[args.op],
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
