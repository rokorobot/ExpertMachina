"""Projection engine (v1.3.0, D28 - The Projection Rule).

A projection is a governed lens over the knowledge system, never
another knowledge system. Code in this package may READ governed facts
and EMIT render artifacts and PROJECTION_* audit events - it may not
write governed state, define schema, or read a rendered artifact back.
Those rules are enforced structurally, in CI, permanently, by
backend/test_projection_guard.py (the D24/D25/D26 guard pattern applied
a fourth time). Renderers live under projections/renderers/ and may
import only the standard library and projections.contract.

Module plan (docs/projection-engine-v1.3.md):
  engine.py     (WS1) - composes clearance-filtered projections from
                governed facts; the only emitter of PROJECTION_* events
  contract.py   (WS0) - the model renderers receive; stamps mandatory
  renderers/    (WS2) - graph.json + self-contained graph.html first
"""

# The one durable trace projection work may leave (user-ratified WS0
# gate wording): the ledger event recording that a render happened.
# The guard sweeps the whole app - this family may originate only from
# modules inside this package.
EVENT_FAMILY_PREFIX = "PROJECTION_"
RENDERED_EVENT = "PROJECTION_RENDERED"

# Renders land here (the EM_PACKAGE_DIR pattern). Referenced ONLY
# inside this package - the guard fails any other module that names it.
PROJECTION_DIR_ENV = "EM_PROJECTION_DIR"
