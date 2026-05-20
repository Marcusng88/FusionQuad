# FusionQuad Fix Plan

## Priority Order
Critical → High → Medium. Fix in this order.

---

## CRITICAL #1 — Sync `workflow.invoke` blocks event loop

**File:** `backend/app/services/simulation.py:172`

**Problem:** `self._workflow.invoke(state, config=...)` is synchronous. Called inside `async def step()`, blocks entire FastAPI event loop — no other requests served while agents run.

**Fix A (quick — 5 min):** Use `ainvoke` (LangGraph native async coroutine)

```python
# Before (line 172)
result = self._workflow.invoke(state, config={"configurable": {"thread_id": session.session_id}})

# After
result = await self._workflow.ainvoke(state, config={"configurable": {"thread_id": session.session_id}})
```

**Fix B (recommended — adds real-time streaming to demo):** Use `astream` SSE

LangGraph `astream()` is an async generator that yields per-node state updates. Each agent (forecaster, planner, controller, auditor) emits a chunk as it completes. Frontend can display agent decisions in real-time instead of waiting for full step.

### SSE Streaming Plan

**Backend — new SSE endpoint:**

```
GET /api/v1/simulation/stream/{session_id}
Content-Type: text/event-stream
```

Implementation in `simulation.py`:
```python
async def step_stream(self, session_id: str):
    """Async generator yielding SSE chunks per agent node."""
    async with session.lock:
        # ... same setup as step() ...
        async for chunk in self._workflow.astream(state, config=...):
            node_name = list(chunk.keys())[0]
            node_state = chunk[node_name]
            yield {"event": "agent_update", "node": node_name, "data": node_state}
        
        # after all nodes done, update session state and yield final snapshot
        yield {"event": "step_complete", "data": self._build_snapshot(session)}
```

New endpoint in `endpoints/simulation.py`:
```python
from fastapi.responses import StreamingResponse

@router.get("/stream/{session_id}")
async def stream_simulation_step(session_id: str, service = Depends(get_simulation_service)):
    async def event_generator():
        async for chunk in service.step_stream(session_id):
            event = chunk.pop("event")
            data = json.dumps(chunk)
            yield f"event: {event}\ndata: {data}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**Frontend — replace polling with EventSource:**

New function in `simulation-api.ts`:
```typescript
export function subscribeSimulationStream(
  sessionId: string,
  onAgentUpdate: (node: string, data: unknown) => void,
  onStepComplete: (snapshot: SimulationApiState) => void,
): () => void {
  const url = `${DEFAULT_API_BASE_URL}/api/v1/simulation/stream/${sessionId}`;
  const es = new EventSource(url);
  
  es.addEventListener("agent_update", (e) => {
    const parsed = JSON.parse(e.data);
    onAgentUpdate(parsed.node, parsed);
  });
  
  es.addEventListener("step_complete", (e) => {
    onStepComplete(JSON.parse(e.data));
    es.close();
  });
  
  es.onerror = () => es.close();
  return () => es.close(); // cleanup fn
}
```

In `use-simulation-controller.ts` — replace `setInterval` poll with `subscribeSimulationStream` when status is "playing".

---

## CRITICAL #2 — `BatteryState` value object used as dict

**File:** `backend/app/services/simulation.py:270-281`

**Problem:** `battery = state.get("battery") or {}` then `battery.get("soc", 0.5)`. After first step, `battery` is a `BatteryState` Pydantic model — no `.get()` method → `AttributeError`.

**Fix:**
```python
# line 270
battery_raw = state.get("battery") or {}
battery: dict = battery_raw.model_dump() if hasattr(battery_raw, "model_dump") else dict(battery_raw)
```

---

## HIGH #3 — Sync `data_loader_node` in async `start()`

**File:** `backend/app/services/simulation.py:71`

**Problem:** Reads files from disk synchronously inside `async def start()`. Blocks event loop.

**Fix:**
```python
import asyncio
loop = asyncio.get_event_loop()
loaded = await loop.run_in_executor(None, data_loader_node, {"day_type": day_type})
```

---

## HIGH #4 — Sync file I/O in `_append_tick_log` (hot path)

**File:** `backend/app/services/simulation.py:309+`

**Problem:** Called every step. Reads entire JSON log + writes back synchronously. O(n²) disk I/O.

**Fix:** Buffer in memory, flush only on finalize.

```python
# SimulationSession — add field:
tick_buffer: list[dict] = field(default_factory=list)

# _append_tick_log — replace file I/O with:
session.tick_buffer.append(tick_entry)

# _finalize_log — flush:
import aiofiles
async with aiofiles.open(log_path, "w") as f:
    await f.write(json.dumps(session.tick_buffer, default=str, indent=2))
```

---

## HIGH #5 — No session TTL (unbounded memory)

**File:** `backend/app/services/simulation.py` — `_sessions` dict

**Problem:** Sessions never evicted. Unlimited growth per server lifetime.

**Fix:**
```python
MAX_SESSIONS = 20

def _register_session(self, session: SimulationSession) -> None:
    if len(self._sessions) >= MAX_SESSIONS:
        oldest_key = next(iter(self._sessions))
        old = self._sessions.pop(oldest_key)
        if old.task and not old.task.done():
            old.task.cancel()
    self._sessions[session.session_id] = session
```

Replace direct `self._sessions[session_id] = session` assignments with `self._register_session(session)`.

---

## HIGH #6 — `useEffectEvent` experimental React API

**File:** `frontend/features/dashboard/hooks/use-simulation-controller.ts:7,95`

**Problem:** `useEffectEvent` not in React 18 stable. Breaks on version change.

**Fix:** Replace with `useRef` stable callback pattern.

```typescript
// Remove useEffectEvent import

// Replace lines 95-97:
const applySnapshotRef = useRef(applySnapshot);
useEffect(() => { applySnapshotRef.current = applySnapshot; });

const pollSimulationState = useCallback(async (sessionId: string) => {
  await applySnapshotRef.current(() => getSimulationState(sessionId));
}, []);
```

---

## MEDIUM #7 — Unsafe API response cast

**File:** `frontend/features/dashboard/lib/simulation-api.ts`

**Problem:** `(await response.json()) as SimulationApiState` — runtime data not validated.

**Fix (minimal):**
```typescript
const data = await response.json();
if (!data?.session_id || !data?.status) {
  throw new Error(`Invalid simulation response: missing required fields`);
}
return data as SimulationApiState;
```

---

## MEDIUM #8 — Dead code

**File:** `frontend/features/dashboard/hooks/use-simulation-controller.ts:150`

```typescript
void snapshot; // delete this line
```

---

## MEDIUM #9 — `import json` in hot-path method

**File:** `backend/app/services/simulation.py:~312`

Move `import json` to top of file with other imports.

---

## Implementation Order

| Priority | Issue | File | Time |
|----------|-------|------|------|
| 1st | #2 BatteryState crash fix | simulation.py:270 | 5 min |
| 2nd | #1a ainvoke (unblock loop) | simulation.py:172 | 5 min |
| 3rd | #1b SSE endpoint | simulation.py + endpoints | 45 min |
| 4th | #1c Frontend EventSource | simulation-api.ts + hook | 30 min |
| 5th | #3 async data_loader | simulation.py:71 | 10 min |
| 6th | #4 buffer tick log | simulation.py:309 | 20 min |
| 7th | #5 session eviction | simulation.py | 10 min |
| 8th | #6 remove useEffectEvent | use-simulation-controller.ts | 15 min |
| 9th | #7 API validation | simulation-api.ts | 10 min |
| 10th | #8 dead code | use-simulation-controller.ts | 2 min |
| 11th | #9 import json | simulation.py | 2 min |

**Start: #2 (prevent crash) → #1a (unblock server) → #1b+1c (streaming).**
