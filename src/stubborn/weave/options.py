"""Weave-time output granularity (member signatures, Javadoc)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

MemberSignaturesMode = Literal["off", "target", "neighbors", "all"]
JavadocMode = Literal["off", "summary", "full"]

_MEMBER_SIGNATURES_MODES: frozenset[str] = frozenset({"off", "target", "neighbors", "all"})
_JAVADOC_MODES: frozenset[str] = frozenset({"off", "summary", "full"})


@dataclass(frozen=True)
class WeaveOptions:
    """Controls optional weave output that increases token cost."""

    member_signatures: MemberSignaturesMode = "target"
    javadoc: JavadocMode | None = None

    def __post_init__(self) -> None:
        if self.member_signatures not in _MEMBER_SIGNATURES_MODES:
            raise ValueError(
                f"member_signatures must be one of {sorted(_MEMBER_SIGNATURES_MODES)}, "
                f"got {self.member_signatures!r}"
            )
        if self.javadoc is not None and self.javadoc not in _JAVADOC_MODES:
            raise ValueError(
                f"javadoc must be one of {sorted(_JAVADOC_MODES)}, got {self.javadoc!r}"
            )

    def effective_javadoc(self, format: str) -> JavadocMode:
        if self.javadoc is not None:
            return self.javadoc
        return "summary" if format == "java-stub" else "off"


DEFAULT_WEAVE_OPTIONS = WeaveOptions()
