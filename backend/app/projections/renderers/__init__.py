"""Renderers present; the projection engine decides (D28).

Every module in this package receives a completed, clearance-filtered
Projection (projections.contract) and chooses only its shape on disk.
Structural purity is enforced in CI by test_projection_guard.py:
renderer modules import nothing beyond the standard library and
projections.contract - a renderer that can reach the database, crud, or
an HTTP client could decide content, and deciding content is the
engine's monopoly. File access is write-only: a renderer that can read
a file back could make a render an input, and renders are never inputs.

First renderer (WS2): graph.json + self-contained graph.html, ported
from graphify's export layer (MIT) with vis-network vendored inline.
"""
