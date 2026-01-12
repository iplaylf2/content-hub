# Tests: Scope and Responsibilities

This test suite follows a layered approach. Lower-level modules own functional
correctness and edge cases. Higher-level modules verify wiring and contracts
between layers.

## Layering Principles

- Submodules test behavior and boundaries.
- Higher-level modules test connectivity and contracts, not internal detail.
- Avoid duplicate assertions across layers.

## Responsibilities by Layer

### Submodules

Focus on rules, edge cases, and data transformations. These tests should be
comprehensive for their module and act as the primary specification of
behavior.

### Higher-level Modules

Focus on orchestration only. Assertions should be about:

- which calls happen
- what data is passed through
- what summary output or error mapping is produced

Do not re-test submodule logic here.

## Test Design Guidance

- If a test needs prepared files, use fixtures in `tests/_fixtures`.
- If a test needs to observe side effects, use `monkeypatch` to avoid real I/O.
- Prefer tests that express contract intent over incidental implementation.
- When behavior is unclear, confirm the expected contract before adding tests.

## Coverage Intent

Coverage is driven by module responsibilities. Missing tests are addressed when
they represent a missing contract, not just an uncovered line.
