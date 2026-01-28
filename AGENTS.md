# Agent Guidelines for buildkite-test-collector

Coding guidelines for the buildkite-test-collector Python project - a pytest plugin that collects test execution data and sends it to Buildkite Test Engine.

**Tech Stack**: Python >=3.9, pytest >=7, uv for dependency management

## Build/Lint/Test Commands

### Setup
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh  # Install uv
uv sync --all-extras  # Install dependencies
```

### Testing
```bash
uv run pytest  # Run all tests
uv run pytest tests/buildkite_test_collector/collector/test_api.py  # Single file
uv run pytest tests/.../test_api.py::test_submit_local_returns_none  # Single test
uv run pytest -v  # Verbose output
uv run pytest -s  # Show print statements
```

### Linting
```bash
uv run pylint src/  # Lint all (required before PR merge)
uv run pylint src/buildkite_test_collector/collector/api.py  # Single file
```

### Building
```bash
uv build  # Build distribution packages
```

## Code Style Guidelines

### Imports
- **Order**: Standard library → Third-party → Local imports (blank line between groups)
- **Style**: Absolute imports preferred; relative imports (`..`) acceptable within package

### Formatting
- **Indentation**: 4 spaces (never tabs); **Line endings**: LF; **Quotes**: Double (`"`)
- **Trailing whitespace**: Remove all; **Final newline**: Always include

### Type Hints
- **Required**: All new code must include type hints
- **Common types**: `Optional`, `Dict`, `List`, `Tuple`, `Literal`, `Mapping`, `Generator`
- **Type aliases**: Use for complex types (e.g., `JsonValue`, `JsonDict`)

### Naming Conventions
- **Classes**: `PascalCase` (e.g., `BuildkitePlugin`, `TestData`)
- **Functions/methods**: `snake_case` (e.g., `pytest_runtest_logstart`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `ENV_TOKEN`, `DEFAULT_API_URL`)
- **Private methods**: `_single_underscore` prefix; **Special**: `__double_underscore__` only

### Docstrings
- **Required**: All modules, classes, and public methods
- **Style**: Imperative mood (e.g., "Submit a payload" not "Submits a payload")
- **Format**: Triple quotes, concise one-liner preferred

### Dataclasses - Critical Pattern
- **Default**: Use `@dataclass(frozen=True)` for immutability
- **Import**: `from dataclasses import dataclass, replace, field`
- **Modification**: Use `replace()` to create modified copies
- **Validation**: Use `__post_init__` for input validation
```python
@dataclass(frozen=True)
class TestData:
    id: UUID
    scope: str
    name: str
    
    def passed(self):
        """Return new instance with passed status"""
        return replace(self, result=TestResultPassed())
```

### Error Handling
- **Specific exceptions**: Catch specific exceptions when possible
- **Broad exceptions**: Use `except Exception:` with `# pylint: disable=broad-except` comment
- **Logging**: Always log warnings/errors with `logger.warning()`
- **Example**:
```python
try:
    response = post(url, json=data, timeout=60)
    response.raise_for_status()
except HTTPError as err:
    logger.warning("Failed to upload test results to buildkite")
    logger.warning(err)
except Exception:  # pylint: disable=broad-except
    logger.warning(traceback.format_exc())
```

### Testing Conventions
- **Test files**: `test_*.py` prefix (e.g., `test_api.py`)
- **Test functions**: `test_*` prefix (e.g., `test_submit_local_returns_none`)
- **Fixtures**: Define in `conftest.py`, use extensively
- **Assertions**: Simple `assert` statements
- **HTTP mocking**: Use `@responses.activate` decorator with `responses` library
- **Conditional tests**: `@pytest.mark.skipif` for version-specific tests

### Pylint Directives
Use inline disables sparingly with specific error codes:
- `# pylint: disable=too-few-public-methods` - simple data classes
- `# pylint: disable=broad-except` - generic exception catching
- `# pylint: disable=unused-argument` - required but unused pytest hook parameters
- Place at end of line or on line before the violation

## Project-Specific Patterns

### Immutable State Management
TestData and related objects are frozen dataclasses. Always reassign after modifications:
```python
test_data = self.in_flight[nodeid]
test_data = test_data.passed()  # Returns NEW instance
self.in_flight[nodeid] = test_data  # MUST reassign
```

### Pytest Hook Callbacks
Follow pytest naming strictly. Document which hook you're implementing:
```python
def pytest_runtest_logreport(self, report):
    """pytest_runtest_logreport hook callback to get test outcome after test call"""
    # Implementation
```

Key hooks: `pytest_configure`, `pytest_runtest_logstart`, `pytest_runtest_logreport`, `pytest_runtest_makereport`

### Environment Variables
Define as class constants and access safely:
```python
class API:
    ENV_TOKEN = "BUILDKITE_ANALYTICS_TOKEN"
    DEFAULT_API_URL = "https://analytics-api.buildkite.com/v1"
    
    def __init__(self, env: Mapping[str, Optional[str]]):
        self.token = env.get(self.ENV_TOKEN)
        self.api_url = env.get(self.ENV_API_URL) or self.DEFAULT_API_URL
```

## Common Pitfalls

1. **Forgetting to reassign frozen dataclasses**: `test_data.passed()` returns new instance - must reassign
2. **Missing type hints**: All new code requires type hints
3. **Wrong import order**: Standard library → Third-party → Local (with blank lines)
4. **Skipping docstrings**: All public modules/classes/methods need docstrings

## Release Process

1. Update version in `pyproject.toml`
2. Create PR with `[release]` in title
3. Merge triggers automated PyPI release
4. Create GitHub release tag manually
