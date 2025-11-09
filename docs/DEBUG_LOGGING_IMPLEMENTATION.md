# Debug Logging Implementation

## Overview

This document describes the decorator-based debug logging system implemented for comprehensive method tracing during the MVP development phase.

## Implementation

### Decorator Utility

Location: `src/utils/debug_logging.py`

The `@debug_log_method` decorator automatically adds comprehensive debug logging to any method:

```python
from src.utils.debug_logging import debug_log_method

class MyClass:
    @debug_log_method
    def my_method(self, param1: str, param2: int) -> str:
        return f"{param1}: {param2}"
```

### Logging Output Format

The decorator logs three types of events:

1. **Method Entry**: Shows all parameter values (truncated to 25 chars)
   ```
   DEBUG: Entering method ClassName.method_name (param1 = value1, param2 = value2)
   ```

2. **Method Exit**: Shows return value (truncated to 25 chars)
   ```
   DEBUG: Method ClassName.method_name returning (return_value)
   ```

3. **Exceptions**: Shows error message (truncated to 25 chars)
   ```
   DEBUG: Method ClassName.method_name raising error=error_message
   ```

## Files Currently Instrumented

### Phase 1 & 2 Complete (3 critical files):

1. **`src/core/game_loop.py`**
   - `execute_turn()` - Main game turn execution
   - `_perform_retrieval()` - Retrieval phase
   - `_execute_agents()` - Agent execution phase

2. **`src/core/retrieval_manager.py`**
   - `retrieve()` - Main retrieval method

3. **`src/agents/narrator.py`**
   - `process()` - Main narrator processing

## Usage

### Adding Debug Logging to a New Method

1. Import the decorator at the top of your file:
   ```python
   from ..utils.debug_logging import debug_log_method
   ```

2. Add the decorator above any method you want to trace:
   ```python
   @debug_log_method
   def my_method(self, param: str) -> str:
       # method implementation
       pass
   ```

### Viewing Debug Logs

Debug logs appear when the log level is set to DEBUG. To see them:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or in your config:
```yaml
log_level: "DEBUG"
```

## Advantages of This Approach

1. **Non-Invasive**: Single line addition, no code modification
2. **Consistent**: Guaranteed uniform logging format across all methods
3. **Reversible**: Easy to remove (just delete the decorator line)
4. **Safe**: No risk of syntax errors or indentation issues
5. **Testable**: Decorator logic is independent and tested
6. **Selective**: Can choose which methods to instrument
7. **Performance**: Minimal overhead, can be disabled in production

## Testing

All 152 tests pass with the decorator-based logging in place:

```bash
source .venv/bin/activate
python -m pytest tests/ -v
# Result: 152 passed in 29.54s
```

## Example Output

```
2025-11-09 10:15:24 [debug] Entering method RetrievalManager.retrieve (query = test query, top_k = 3, agent_name = test, use_cache = True, rewrite_query = True)
2025-11-09 10:15:24 [debug] Method RetrievalManager.retrieve returning ([])
```

## Future Expansion

To add debug logging to additional modules, follow this pattern:

1. Add `from ..utils.debug_logging import debug_log_method` to the imports
2. Add `@debug_log_method` above each public method
3. Run tests to verify no regressions

Recommended order for expansion:
1. Complete core module (session.py, base_agent.py, orchestrator.py)
2. Add to remaining agents (scene_planner.py, npc_manager.py, rules_referee.py)
3. Add to RAG module (hybrid_retriever.py, vector_retriever.py, bm25_retriever.py)
4. Add to ingestion module (pipeline.py, chunker.py, embedder.py)

## Lightweight Alternative

For methods where you only need to know when they execute (without parameter/return logging), use `@debug_log_calls` instead:

```python
from ..utils.debug_logging import debug_log_calls

@debug_log_calls
def quick_method(self):
    # Logs: "Method ClassName.quick_method executing"
    pass
```

## Value Truncation

All parameter and return values are automatically truncated to 25 characters with an ellipsis (`...`) to prevent log spam from large objects. This is handled by the internal `_truncate()` function.

## Notes

- The decorator preserves function signatures and documentation
- Works with both methods and regular functions
- Handles exceptions gracefully without suppressing them
- Skip `self` and `cls` parameters in the output automatically
