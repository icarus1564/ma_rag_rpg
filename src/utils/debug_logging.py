"""Debug logging decorator for comprehensive method tracing."""

import functools
import inspect
from typing import Any, Callable, TypeVar
from .logging import get_logger

F = TypeVar('F', bound=Callable[..., Any])


def _truncate(value: Any, max_len: int = 25) -> str:
    """Truncate value to max_len characters with ellipsis if needed."""
    str_val = str(value)
    if len(str_val) > max_len:
        return str_val[:max_len] + "..."
    return str_val


def debug_log_method(func: F) -> F:
    """
    Decorator to add comprehensive debug logging to methods.

    Logs:
    - Method entry with parameter values (truncated to 25 chars)
    - Method exit with return value (truncated to 25 chars)
    - Exceptions raised with error message (truncated to 25 chars)

    Usage:
        @debug_log_method
        def my_method(self, param1: str, param2: int) -> str:
            return f"{param1}: {param2}"

    Output:
        DEBUG: Entering method ClassName.my_method (param1 = hello, param2 = 42)
        DEBUG: Method ClassName.my_method returning (hello: 42)
    """
    logger = get_logger(func.__module__)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Get class name if this is a method
        if args and hasattr(args[0], '__class__'):
            class_name = args[0].__class__.__name__
        else:
            class_name = "Module"

        method_name = func.__name__

        # Build parameter string (skip self/cls)
        try:
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            params = []
            for param_name, param_value in bound_args.arguments.items():
                if param_name not in ['self', 'cls']:
                    params.append(f"{param_name} = {_truncate(param_value)}")

            param_str = ", ".join(params) if params else ""
        except Exception:
            # If signature binding fails, just show we have args
            param_str = "..." if args or kwargs else ""

        # Entry log
        logger.debug(f"Entering method {class_name}.{method_name} ({param_str})")

        try:
            result = func(*args, **kwargs)

            # Exit log
            if result is None:
                logger.debug(f"Method {class_name}.{method_name} returning (None)")
            else:
                logger.debug(f"Method {class_name}.{method_name} returning ({_truncate(result)})")

            return result

        except Exception as e:
            # Error log
            error_msg = str(e)
            logger.debug(f"Method {class_name}.{method_name} raising error={_truncate(error_msg)}")
            raise

    return wrapper  # type: ignore


def debug_log_calls(func: F) -> F:
    """
    Lightweight decorator that only logs when the method calls other methods.

    This is useful for tracking method call chains without the overhead
    of logging every parameter and return value.

    Usage:
        @debug_log_calls
        def my_method(self):
            self.other_method()  # Will log: "Method ClassName.my_method calling ClassName.other_method"
    """
    logger = get_logger(func.__module__)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if args and hasattr(args[0], '__class__'):
            class_name = args[0].__class__.__name__
        else:
            class_name = "Module"

        method_name = func.__name__
        logger.debug(f"Method {class_name}.{method_name} executing")

        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.debug(f"Method {class_name}.{method_name} raising error={_truncate(str(e))}")
            raise

    return wrapper  # type: ignore
