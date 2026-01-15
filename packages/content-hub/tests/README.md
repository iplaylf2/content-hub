# Tests: Scope and Responsibilities

This test suite emphasizes layered testing, contract validation, and responsibility-driven coverage.

## Layering Principles

Test at boundaries, not through layers:

**Submodules** test behavior comprehensively—rules, edge cases, data transformations, boundary conditions, error handling. These tests document the module's contract.

**Higher-level modules** test orchestration only—call patterns, data flow, output mapping. Defer detailed logic testing to submodules.

## Writing Clear Tests

### Test Data

Tests read from fixtures in `tests/_fixtures` but never write to disk. Use `monkeypatch` to observe side effects without real I/O.

- Keep test data close to tests. Inline small data, factor out large or reusable datasets
- Prefer explicit construction over complex fixture chains

### Parametrization

Use `@pytest.mark.parametrize` to express variation through parameters while keeping test logic invariant.

**One test, one contract.** Parameters enumerate conditions over which the contract holds—parametrize by intent, not volume. Even single values can be parameters if they represent design axes.

**When to parametrize:**

- Input shape or type variations
- Boundary conditions
- Configuration modes
- Different inputs yielding equivalent outcomes

**When to write separate tests:**

- Different responsibilities
- Different contracts
- Different orchestration paths

### Mocking and Observation

Mock external dependencies at system boundaries. Track what matters for the contract—inputs, call order, or specific values.

**Mock construction:**

- Always use `spec` parameter to enforce interface contracts with `Mock(spec=...)` or `create_autospec(...)`
- Use `Mock` over `MagicMock` unless you need special magic method behavior
- Use `side_effect` only when tracking calls or implementing custom behavior
- If you don't need to observe, omit `side_effect`

**Naming and assertions:**

- Name by intent: `observed_copies` not `copy_calls`
- Name observers descriptively: `observe_copy` not `copy_side_effect`
- Extract repeated access. Avoid multiple `mock.call_args.kwargs["key"]` lookups
- Use direct comparisons: `assert calls == [(a, b)]` not multi-step length checks
- Prefer semantic assertions: `mock.assert_called_once()` not manual count checks

### Test Scope

Test the contract, not the implementation:

- Test public APIs, not private helpers or module internals
- Avoid asserting third-party tool output unless it's an explicit contract
- Keep error tests minimal. Verify error type and message intent, not exact wording

### Coverage

Coverage follows module responsibilities. Add tests for missing contracts, not uncovered lines.

**Modules outside test scope:**

- `*_kit` modules—lightweight adapters validated indirectly through integration tests
- `utils` modules—general-purpose utilities implicitly covered by dependent module tests
