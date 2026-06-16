# Cogent Hooks

Lifecycle hook scripts that self-register via `cogent_hooks.register()`.

## Creating a hook

1. Create a `.py` file in this directory.
2. At module level, call `register(hook_point, fn)`:

```python
from cogent_hooks import register

async def my_hook(session_id: str, **kwargs):
    print(f"Session {session_id} started")

register("before_session_start", my_hook)
```

## Available hook points

- `before_session_start(session_id, workspace_id)`
- `after_session_end(session_id, summary)`
- `before_message(session_id, user_text)`
- `after_message(session_id, assistant_text)`
- `before_tool(session_id, tool_name, arguments)`
- `after_tool(session_id, tool_name, result)`
- `on_error(session_id, error)`
- `on_startup()`
- `on_shutdown()`

Hooks run in registration order. Failures are logged but do not
propagate — one failing hook never blocks the rest.
