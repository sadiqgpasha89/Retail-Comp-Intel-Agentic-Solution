"""Domain layer: pure, dependency-light business logic (pydantic + stdlib only).

Everything here is deterministic and independently testable. No FastAPI, no LLM, no network.
Agents may *call* this layer through registered tools; they never replace it.
"""
