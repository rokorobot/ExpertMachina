"""The projection model contract (v1.3.0 WS0, D28).

Renderers receive a completed, clearance-filtered Projection and choose
only its shape on disk - they never query governed state, never filter,
never decide content. This module is therefore deliberately importable
with zero application dependencies: standard library only. The
projection guard (backend/test_projection_guard.py) enforces both sides
structurally: renderer modules may import nothing beyond the stdlib and
this contract, and the stamp fields below are mandatory - a render
without rendered_at + audit cursor evidence cannot exist, because the
shapes that carry a render require them.

Every dataclass is frozen: what the engine hands a renderer is
immutable by construction.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProjectionNode:
    """One governed fact as a node. Metadata + a bounded excerpt, never
    full content (scoping ruling 3: the .empkg is the content artifact,
    the graph is the structure artifact)."""
    id: str                    # stable, kind-prefixed (e.g. "asset:42")
    kind: str                  # DOCUMENT | ASSET | EXPERT_MODEL | PACKAGE | SELECTION | BINDING | PRINCIPAL
    label: str
    status: str | None = None
    domain: str | None = None  # D27 path; None = honestly unclassified
    excerpt: str | None = None # bounded; never full content
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ProjectionEdge:
    """One governed relation as an edge."""
    source_id: str
    target_id: str
    relation: str              # PROVENANCE | MEMBER_OF | CONFLICTS_WITH | SUPPORTS | SUPERSEDES | SELECTED | BOUND_TO
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Projection:
    """What the engine hands a renderer: complete, clearance-filtered,
    stamped. Exclusions are declared counts, never silent (D12)."""
    project_id: int
    clearance: str             # the clearance this projection was compiled FOR (D9)
    status_inclusion: tuple    # declared render parameter; default ("APPROVED",)
    audit_cursor: int          # max audit event id at composition time
    engine_version: str
    nodes: tuple = ()          # ProjectionNode, deterministic order
    edges: tuple = ()          # ProjectionEdge, deterministic order
    groups: dict = field(default_factory=dict)    # domain path -> node ids
    excluded: dict = field(default_factory=dict)  # declared exclusion counts
    scope: dict = field(default_factory=dict)     # e.g. {"domain_prefix": "finances"}


@dataclass(frozen=True)
class RenderManifest:
    """The stamps D28 makes mandatory on every render. rendered_at lives
    HERE and never inside projected content, so content hashes stay
    deterministic (same facts + scope + clearance = byte-identical
    output) and comparison detects real drift. The manifest's own hash
    is recorded in the PROJECTION_RENDERED ledger event - "is this file
    the render the ledger says?" stays answerable indefinitely."""
    renderer: str
    engine_version: str
    rendered_at: str           # ISO timestamp of this render
    audit_cursor: int          # the ledger moment the render projected
    clearance: str
    status_inclusion: tuple
    files: dict = field(default_factory=dict)   # filename -> sha256
    counts: dict = field(default_factory=dict)  # nodes/edges/excluded


# The stamp fields the guard asserts present, permanently. Removing one
# from the shapes above is a guard failure, not a refactor.
REQUIRED_PROJECTION_STAMPS = frozenset(
    {"clearance", "status_inclusion", "audit_cursor", "engine_version"})
REQUIRED_MANIFEST_STAMPS = frozenset(
    {"renderer", "engine_version", "rendered_at", "audit_cursor",
     "clearance", "status_inclusion", "files"})
