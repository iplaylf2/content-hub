# Tests: Scope and Responsibilities

This test suite emphasizes layered testing, contract validation, and responsibility-driven coverage.

## Layering Principles

Test at boundaries, not through layers:

- **Submodules** test behavior comprehensively—rules, edge cases, data transformations
- **Higher-level modules** test orchestration only—which calls happen, what data passes through
- **Avoid duplicate assertions** across layers; defer detailed logic testing to submodules

## Test Environment

**No filesystem writes.** Tests read from fixtures in `tests/_fixtures` but must not write to disk. Use `monkeypatch` to observe side effects without real I/O.

## Responsibilities by Layer

### Submodules

Comprehensive testing of module behavior:

- Rules and edge cases
- Data transformations and validations
- Boundary conditions
- Error handling

These tests document the module's contract.

### Higher-level Modules

Test orchestration contracts:

- **Call patterns**: which functions are invoked, in what order
- **Data flow**: what arguments are passed through
- **Output mapping**: how results are summarized or errors are reported

Defer detailed logic testing to submodule tests.

## Writing Clear Tests

### Parametrized Tests

Use `@pytest.mark.parametrize` to **separate data from logic**—declare which values are variables, which parts are invariant test structure.

Parametrization makes the test's variable dimensions explicit in the signature. When you see `@pytest.mark.parametrize("verbose", [True])`, you immediately know `verbose` is a design parameter the test depends on, not a hardcoded constant. The test body becomes the invariant framework; the parameter list becomes the variable data.

**When to use**:

- Making variable dimensions explicit (flags, modes, orderings, path variations)
- Covering boundary conditions or domain samples (empty lists, single items, multiple items)
- Showing how outputs vary predictably with inputs

### Fixtures and Test Data

- Use fixtures in `tests/_fixtures` for prepared file inputs
- Keep test data close to the test—inline small data, factor out large or reusable datasets
- Prefer explicit construction over complex fixture chains

### Mocking and Observation

Use `monkeypatch` to intercept side effects and avoid real I/O.

**Semantic clarity**:

- **Name by intent, not mechanism**: `copied_files` not `copy_calls`, `execute_calls` not `executed`
- **Name helpers descriptively**: `track_copy` not `copy_side_effect`, `track_mkdir` not `mkdir_tracker`
- **Extract repeated access**: `call_kwargs = mock.call_args.kwargs` when accessing multiple keys
- **Use direct comparisons**: `assert calls == [(a, b)]` not `assert len(calls) == 1; assert calls[0] == (a, b)`
- **Prefer semantic assertions**: `mock.assert_called_once()` not `assert mock.call_count == 1`

**When mocking**:

- Mock at the boundary of the system under test—intercept external dependencies, not internal helpers
- Track what matters for the contract—inputs, call order, or specific values
- Verify behavior, not implementation—focus on observable effects

### Test Scope

Express **contract intent**, not incidental implementation:

- **Test public APIs**, not private helpers or module internals
- **Avoid asserting third-party tool output** (e.g., validator error text) unless it's an explicit contract
- **Keep error tests minimal**: verify error type and high-level message intent
- **Confirm contracts before testing**: when behavior is unclear, clarify the expected contract first

## Coverage Intent

**Coverage follows module responsibilities.** Add tests when they represent missing contracts, not uncovered lines. Reinforce boundaries, not implementation.

### Modules Outside Test Scope

Some modules are intentionally excluded from direct testing:

**`*_kit` modules**: Lightweight adapters or composition layers. Validated indirectly through integration tests of higher-level modules.

**`utils` modules**: General-purpose utilities with narrow responsibilities. Implicitly covered by tests of dependent modules. Direct testing would duplicate assertions without clarifying contracts.
