# Contributing to Multi-Agent RAG RPG

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Getting Started

1. **Fork and clone** the repository
2. **Follow the setup** in [QUICKSTART.md](QUICKSTART.md)
3. **Create a branch** for your feature: `git checkout -b feature/your-feature-name`
4. **Make your changes** following the guidelines below
5. **Test your changes** thoroughly
6. **Submit a pull request**

## Development Setup

### Virtual Environment (MANDATORY)

Always use the project's virtual environment:

```bash
# Create and activate virtual environment
make setup
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
```

Never commit code without activating the venv first.

### Install Development Dependencies

```bash
# After activating venv
pip install pylint black ruff mypy pytest-cov
```

## Code Standards

### Python Version
- Target: Python 3.11+
- Use modern Python features (type hints, dataclasses, match statements)

### Type Hints (REQUIRED)
All function signatures must include type hints:

```python
from typing import List, Dict, Optional

def process_data(
    items: List[Dict[str, Any]],
    threshold: float = 0.5
) -> Dict[str, int]:
    """Process data with given threshold."""
    # Implementation
    return {"processed": len(items)}
```

### Docstrings (REQUIRED)
Use Google-style docstrings for all public functions and classes:

```python
def retrieve(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
    """Retrieve relevant chunks for a query.

    Args:
        query: The search query string
        top_k: Number of results to return (default: 10)

    Returns:
        List of RetrievalResult objects sorted by relevance

    Raises:
        ValueError: If query is empty or top_k < 1

    Example:
        >>> results = retriever.retrieve("Gandalf", top_k=5)
        >>> len(results)
        5
    """
    # Implementation
```

### Code Style

**Formatting:**
```bash
# Format code before committing
black src/ tests/
```

**Linting:**
```bash
# Check for issues
ruff check src/ tests/
```

**Type Checking:**
```bash
# Verify type hints
mypy src/
```

## Testing Requirements

### Test Coverage

- **All new code must have tests**
- Target: 80%+ coverage for new code
- Use pytest for all tests

### Writing Tests

```python
import pytest
from src.agents.narrator import NarratorAgent

class TestNarratorAgent:
    @pytest.fixture
    def agent(self):
        """Fixture providing configured agent."""
        config = AgentConfig(name="Narrator", ...)
        return NarratorAgent(config, mock_retrieval_manager)

    def test_generates_description(self, agent):
        """Test that narrator generates scene descriptions."""
        # Arrange
        context = AgentContext(...)

        # Act
        result = agent.process(context)

        # Assert
        assert isinstance(result, AgentOutput)
        assert len(result.content) > 0
        assert len(result.citations) > 0
```

### Running Tests

Before submitting a PR, ensure:

```bash
# All tests pass
make test

# Check coverage
make test-coverage
# Review htmlcov/index.html

# Run specific test suites
make test-core       # Core framework
make test-agents     # Agents
make test-rag        # RAG pipeline
```

## Architecture Guidelines

### Agent Implementation

All agents must:
1. Inherit from `BaseAgent`
2. Implement the `process(context: AgentContext) -> AgentOutput` method
3. Follow the retrieval-first pattern
4. Return structured output with citations
5. Handle errors gracefully with fallbacks

See [docs/AGENT_IMPLEMENTATION_DESIGN.md](docs/AGENT_IMPLEMENTATION_DESIGN.md) for details.

### Corpus Grounding

**IMPORTANT:** All agent outputs must be grounded in the corpus via RAG:
- Retrieve relevant chunks before generation
- Include citations in responses
- Validate facts against corpus (RulesReferee)

### Stateless Design

Agents should be stateless:
- No mutable instance variables
- All context passed via `AgentContext`
- Session state managed externally
- Exception: persona cache in session state

## Project Structure

```
src/
├── agents/          # Agent implementations
├── core/            # Core framework
├── rag/             # Retrieval components
├── ingestion/       # Data pipeline
├── api/             # FastAPI endpoints
└── utils/           # Utilities

tests/
├── test_agents/     # Agent tests
├── test_core.py     # Core tests
└── test_rag_pipeline.py  # RAG tests
```

**Do not modify** code outside your feature scope without discussion.

## Git Workflow

### Branching

- `main` - Stable releases
- `feature/feature-name` - New features
- `bugfix/bug-name` - Bug fixes
- `docs/doc-name` - Documentation updates

### Commit Messages

Use clear, descriptive commit messages:

```
Add NPC persona extraction caching

- Implement session-level caching for extracted personas
- Reduces LLM calls from 2 to 1 per NPC interaction
- Add tests for cache hit/miss scenarios
- Update documentation
```

### Pull Request Process

1. **Update documentation** if needed
2. **Add tests** for new functionality
3. **Ensure all tests pass**: `make test`
4. **Clean up code**: `make clean`
5. **Update CHANGELOG** if applicable
6. **Submit PR** with clear description

**PR Description Template:**

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] All existing tests pass
- [ ] New tests added
- [ ] Coverage maintained/improved

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

## Common Tasks

### Adding a New Agent

1. Create `src/agents/my_agent.py` inheriting from `BaseAgent`
2. Add prompts to `src/agents/prompt_templates.py`
3. Add configuration to `config/agents.yaml.example`
4. Write tests in `tests/test_agents/test_my_agent.py`
5. Update orchestrator to include new agent
6. Document in `docs/`

### Adding a New Retriever

1. Create retriever class implementing `BaseRetriever`
2. Add configuration options
3. Write comprehensive tests
4. Update documentation

### Adding a New Vector DB Provider

1. Implement `BaseVectorDB` interface
2. Add to factory in `src/rag/vector_db/factory.py`
3. Add configuration examples
4. Update documentation

## Documentation

### When to Update Documentation

- Adding new features
- Changing APIs or interfaces
- Modifying configuration options
- Adding new dependencies

### Documentation Files

- `README.md` - Main project documentation
- `QUICKSTART.md` - Getting started guide
- `docs/*.md` - Design documents
- Code docstrings - Function/class documentation

## Security Considerations

- **Never commit secrets** (.env files should be in .gitignore)
- **Validate all input** especially in API endpoints
- **Use parameterized queries** to prevent injection
- **Review dependencies** for security vulnerabilities
- **Handle errors safely** without exposing internals

## Code Review Process

All PRs require:
1. ✅ All tests passing
2. ✅ Code review approval
3. ✅ Documentation updated
4. ✅ No merge conflicts
5. ✅ Clean commit history

## Questions or Issues?

- Check [README.md](README.md) for documentation
- Review existing [issues](../../issues)
- Check [design documents](docs/)
- Ask in PR comments

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
