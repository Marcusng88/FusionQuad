# Agent Spec: DataLoader

## Purpose

Load CSV energy profile data for all facility scenarios. Acts as the entry point of the simulation pipeline. Produces normalized DataFrames and metadata that downstream agents (Forecasting, Planner) consume.

## Type

**Custom node** (not a Deep Agent) — deterministic file operations via `CSVLoader`.

## Position in Pipeline

```
[START] → [DataLoader] → [Forecasting] → ...
```

DataLoader runs **once** at simulation initialization, not on every tick.

---

## Input

| Source | Description |
|--------|-------------|
| `backend/data/*.csv` | 4 CSV files: SoL (solar), Mi2 (solar), SuN (holiday), E (weekday no solar) |
| `day_type: str` | "weekday" | "holiday" | "solar_duck_curve" — determines which facility to load |

---

## Output

Written to `AgentState`:

| Key | Type | Description |
|-----|------|-------------|
| `loaded_data` | `dict[str, dict]` | `{facility: {"data": df.to_dict(), "metadata": {...}}}` |
| `data_quality` | `dict[str, dict]` | `{facility: {rows, missing_kw_import, solar_kwp, facility_name}}` |
| `current_facility` | `str` | Active facility name |
| `md_limit_kw` | `float` | Maximum demand threshold (default 800 kW) |

---

## State Schema (partial)

```python
class AgentState(TypedDict):
    loaded_data: dict[str, dict] | None
    data_quality: dict[str, dict] | None
    current_facility: str | None
    md_limit_kw: float | None
    day_type: str | None  # set by simulation clock, read by DataLoader
```

---

## Logic

```
1. Receive day_type from state
2. Map day_type to CSV filename:
     weekday        → "2. Load Profile (No Solar) E.csv"
     holiday        → "3. Load Profile (No Solar) SuN.csv"
     solar_duck_curve → "1. Load Profile (With Solar Installed) SoL.csv"
3. Use existing CSVLoader.load(file_path) → pd.DataFrame
4. Use CSVLoader.extract_metadata(file_path) → ScenarioMetadata
5. Validate: check kw_import column exists, no full-row NaN
6. Write loaded_data + data_quality to state
```

---

## Tools

| Tool | Source | Purpose |
|------|--------|---------|
| `CSVLoader.load(Path) → pd.DataFrame` | Existing `app.data.csv_loader` | Parse CSV → DataFrame |
| `CSVLoader.extract_metadata(Path) → ScenarioMetadata` | Existing `app.data.csv_loader` | Extract solar_kwp, facility_name, meter_type |

---

## Edge Cases

| Scenario | Handling |
|----------|----------|
| CSV missing `kw_import` column | Raise `ValueError`, skip facility, log warning |
| CSV has all NaN rows | Skip facility, report 0 rows in data_quality |
| Unknown day_type | Default to "weekday" + log warning |
| File not found | Raise `FileNotFoundError` with path |

---

## Acceptance Criteria

- [ ] All 4 CSV files load without error
- [ ] `loaded_data[facility]["data"]` contains `datetime` and `kw_import` keys
- [ ] `data_quality` reports correct row count per facility
- [ ] `current_facility` is set based on day_type
- [ ] Node runs exactly once per simulation (not per tick)
- [ ] Existing `test_csv_loader.py` tests pass

---

## Dependencies

- Reads: `state.day_type` (set by simulation clock before DataLoader node)
- Writes: `state.loaded_data`, `state.data_quality`, `state.current_facility`
- Consumes: `backend/data/*.csv` files

---

## File Location

```
backend/app/agents/data_loader.py  # node implementation
backend/data/*.csv                  # input files
```