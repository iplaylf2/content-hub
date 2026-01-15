# Tests: Scope and Responsibilities

This test suite emphasizes layered testing, contract validation, and responsibility-driven coverage.

## Layering Principles

Test at boundaries, not through layers:

**Submodules** test behavior comprehensively—rules, edge cases, data transformations, boundary conditions, error handling. These tests document the module's contract.

**Higher-level modules** test orchestration only—call patterns, data flow, output mapping. Defer detailed logic testing to submodules.

## Test Environment

**No filesystem writes.** Tests read from fixtures in `tests/_fixtures` but must not write to disk. Use `monkeypatch` to observe side effects without real I/O.

## Writing Clear Tests

### Parametrized Tests

Use `@pytest.mark.parametrize` to **separate data from logic**—make variable dimensions explicit in the signature, keep test structure invariant.

**Parametrize based on intent, not data quantity.** The goal is declaring what varies in your test, not reducing code. Even a single value can be parametrized if it represents a design dimension.

### Fixtures and Test Data

- Use fixtures in `tests/_fixtures` for prepared file inputs
- Keep test data close to the test—inline small data, factor out large or reusable datasets
- Prefer explicit construction over complex fixture chains

### Mocking and Observation

**Mock construction**:

- **Always use `spec` parameter**: enforce interface contracts with `Mock(spec=...)` or `create_autospec(...)`
- **Use `Mock` over `MagicMock`**: unless you need special magic method behavior
- **Side effects when observing**: use `side_effect` only when tracking calls or implementing custom behavior
- **Direct mocks when stubbing**: if you don't need to observe, omit `side_effect`

**Naming and assertions**:

- **Name by intent**: `observed_copies` not `copy_calls`
- **Name observers descriptively**: `observe_copy` not `copy_side_effect`
- **Extract repeated access**: avoid multiple `mock.call_args.kwargs["key"]` lookups
- **Use direct comparisons**: `assert calls == [(a, b)]` not multi-step length checks
- **Prefer semantic assertions**: `mock.assert_called_once()` not manual count checks

**What to mock**: Mock external dependencies at system boundaries. Track what matters for the contract—inputs, call order, or specific values.

### Test Scope

Express **contract intent**, not incidental implementation:

- Test public APIs, not private helpers or module internals
- Avoid asserting third-party tool output unless it's an explicit contract
- Keep error tests minimal—verify error type and high-level message intent
- Confirm contracts before testing when behavior is unclear

## Coverage Intent

**Coverage follows module responsibilities.** Add tests when they represent missing contracts, not uncovered lines.

### Modules Outside Test Scope

**`*_kit` modules**: Lightweight adapters validated indirectly through integration tests of higher-level modules.

**`utils` modules**: General-purpose utilities implicitly covered by tests of dependent modules.
