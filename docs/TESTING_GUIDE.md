# Tests: Scope and Responsibilities

This test suite emphasizes layered testing, contract validation, and responsibility-driven coverage.

## Layering Principles

Test at boundaries, not through layers:

**Submodules** test behavior comprehensively: rules, edge cases, data transformations, boundary conditions, error handling. These tests document the module's contract.

**Higher-level modules** test orchestration only: call patterns, data flow, output mapping. Defer detailed logic testing to submodules.

## Writing Clear Tests

### Test Data

Tests read from fixture in `tests/_fixture` but never write to disk. Use `monkeypatch` to observe side effects without real I/O.

When tests need file inputs, prepare real files in `tests/_fixture`. Don't simulate file content with strings. Use descriptive names that reveal the fixture's purpose or state (e.g., `source_multi`, `destination_with_extra`). For nonexistent resources, use clear prefixes like `nonexistent_` to signal absence from the name itself.

For arbitrary values in test parameters that don't reference fixture, use explicit virtual prefixes (e.g., `virtual-resource`) to clarify they don't depend on actual fixture files.

### Parametrization

Use `@pytest.mark.parametrize` to express variation through parameters while keeping test structure invariant.

**One test, one contract.** Parameters enumerate conditions over which the contract holds. Parametrize by intent, not volume. Even single values can be parameters if they represent design axes.

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

- Always use `create_autospec()` over `Mock(spec=...)` for better type safety
- When mocking instance methods with `monkeypatch.setattr()`, remember the method receives `self` as first parameter
- Use `side_effect` when tracking calls or implementing custom behavior
- If the observer only passes, create the mock directly without defining a function

**Naming and assertions:**

- Name by intent: `observed_copies` not `copy_calls`
- Name observers descriptively: `observe_copy` not `copy_side_effect`
- Extract repeated access. Avoid multiple `mock.call_args.kwargs["key"]` lookups
- Use direct comparisons: `assert calls == [(a, b)]` not multi-step length checks
- Prefer semantic assertions: `mock.assert_called_once()` not manual count checks

### Fixture Organization

Keep fixture scope appropriate to usage patterns. Use hierarchical organization for complex test suites.

**Scope guidelines:**

- File-level for single test files
- Module-level for multiple files in same directory  
- Global only for truly shared utilities

**Best practices:**

- Never import `conftest.py` directly—use separate `fixture_types.py` files for fixture contracts
- Keep test directories focused: only test files, `conftest.py`, and `fixture_types.py`
- Use file-level constants for simple values that don't need sharing across files

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
