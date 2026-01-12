# Tests: Scope and Responsibilities

This test suite is guided by a small set of principles:

- Layering principles
- Test environment constraints
- Responsibilities by layer
- Test design guidance
- Coverage intent

## Layering Principles

- Submodules test behavior and boundaries.
- Higher-level modules test connectivity and contracts, not internal detail.
- Avoid duplicate assertions across layers.

## Test Environment Constraints

- Tests should not write to the filesystem; reading files is allowed via fixtures in `tests/_fixtures`.

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
- Avoid asserting third-party tool details (e.g., schema validator error text) unless that output is an explicit contract.
- Avoid tests that reach into private helpers or module internals; test the public API behavior instead.
- Favor minimal surface-area tests for error handling: check error type and high-level message intent.
- When behavior is unclear, confirm the expected contract before adding tests.

## Coverage Intent

Coverage is driven by module responsibilities. Missing tests are addressed when
they represent a missing contract, not just an uncovered line. Tests should
reinforce module boundaries rather than mirror implementation details.
