# Migration Guide: From setup.py to uv

This document outlines the migration from the traditional `setup.py` and pip-based workflow to [uv](https://docs.astral.sh/uv/), a modern Python package manager.

## What Changed

### Package Configuration
- **Before**: `setup.py` with setuptools
- **After**: `pyproject.toml` with hatchling build backend

### Dependency Management
- **Before**: Dependencies defined in `setup.py` and installed with `pip`
- **After**: Dependencies defined in `pyproject.toml` and managed with `uv`

### Virtual Environment Management
- **Before**: Manual `python -m venv` or system-level pip installs
- **After**: Automatic virtual environment management with `uv`

### Lock File
- **Before**: No lock file (version resolution at install time)
- **After**: `uv.lock` file ensures reproducible installs

## Migration Steps Completed

### 1. Created `pyproject.toml`
Replaced `setup.py` with modern `pyproject.toml` configuration:
- Project metadata (name, version, description, authors)
- Dependencies (runtime and optional)
- Build system configuration
- Entry points for pytest plugin

### 2. Generated Lock File
Created `uv.lock` to ensure reproducible dependency resolution across environments.

### 3. Updated CI/CD
- **GitHub Actions**: Updated to use `astral-sh/setup-uv` action
- **Buildkite**: Updated release pipeline to use `uv build` and `uv run`
- **Tox**: Updated to use `uv sync --all-extras`

### 4. Updated Development Environment
- **DevContainer**: Added uv installation to postCreateCommand
- **Documentation**: Updated README with uv-based installation instructions

### 5. Updated Tool Versions
Added `uv 0.7.21` to `.tool-versions` file.

## For Users

### Installation (Before)
```python
# In setup.py
extras_require={
    "dev": [
        "buildkite-test-collector"
    ]
}
```

```bash
pip install -e '.[dev]'
```

### Installation (After)
```bash
# Add to project
uv add --dev buildkite-test-collector
```

Or in `pyproject.toml`:
```toml
[project.optional-dependencies]
dev = [
    "buildkite-test-collector"
]
```

### Running Tests (Before)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
pytest
```

### Running Tests (After)
```bash
uv sync --all-extras
uv run pytest
```

## For Contributors

### Development Setup (Before)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
pytest
```

### Development Setup (After)
```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies and run tests
uv sync --all-extras
uv run pytest
```

### Building (Before)
```bash
python -m build
```

### Building (After)
```bash
uv build
```

## Benefits of uv

1. **Speed**: Significantly faster package resolution and installation
2. **Reliability**: Lock file ensures consistent environments
3. **Simplicity**: Unified tool for dependency management and virtual environments
4. **Modern**: Built with modern Python packaging standards
5. **Compatibility**: Works with existing Python packaging ecosystem

## Backwards Compatibility

- The `setup.py` file has been kept for now to maintain compatibility
- All existing functionality remains the same
- Users can continue using pip if they prefer, though uv is recommended

## Troubleshooting

### Common Issues

1. **"uv: command not found"**
   - Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Add to PATH: `source $HOME/.local/bin/env`

2. **Dependencies not found**
   - Use `uv sync --all-extras` instead of `uv sync --dev`
   - This ensures both dev and optional dependencies are installed

3. **Version conflicts**
   - Delete `.venv` and `uv.lock`, then run `uv sync --all-extras`
   - This will regenerate the lock file with current dependencies

### Getting Help

- [uv Documentation](https://docs.astral.sh/uv/)
- [Python Packaging User Guide](https://packaging.python.org/)
- [Buildkite Test Collector Issues](https://github.com/buildkite/test-collector-python/issues)