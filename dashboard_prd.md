I reviewed your original plan and the uploaded research. The product should be framed as a **simulation-first AI energy optimization dashboard**, not a real-time control system yet. The research basis is: Malaysian C&I users face high Maximum Demand charges, especially around the RM97.06/kW MV TOU figure; peak TOU is 2 PM–10 PM on weekdays; and the system should use forecasting, BESS dispatch, and load shifting to reduce MD risk. 

---

# PRD: Agentic AI Peak Shaving Dashboard

## 1. Product Name

**GridWise AI**

Alternative names:

```text
PeakGuard AI
DemandPilot
GridMind AI
```

---

## 2. Product Goal

Build a web dashboard that lets users upload electricity load data, simulate AI-based peak shaving, and compare electricity cost before and after optimization.

The system should answer:

```text
When does the building hit peak demand?
How expensive is that peak?
Can battery discharge reduce the peak?
Can flexible loads be shifted?
How much money is saved?
Why did the AI make each decision?
```

---

## 3. Core User

Primary user:

```text
Facility manager / energy consultant / building owner
```

They want to reduce monthly electricity bills caused by high Maximum Demand.

---

## 4. Core Problem

Under the Malaysian tariff structure, a short high-power spike can cause expensive monthly Maximum Demand charges. The system must reduce the highest grid import peak using:

```text
Solar
Battery Energy Storage System
Load shifting
AI decision logic
```

---

## 5. MVP Scope

## Included

```text
CSV upload
Tariff configuration
Battery configuration
Baseline peak analysis
AI optimization simulation
Original vs optimized chart
Battery SoC chart
Savings calculation
AI decision log
```

## Not included in MVP

```text
Real inverter control
Real IoT meter integration
SCADA integration
Live TNB billing integration
Real-time weather API
Actual production load shedding
```

---

# 6. App Flow

```text
1. User uploads CSV
   ↓
2. User configures tariff, demand limit, and battery settings
   ↓
3. System calculates original grid import and baseline Maximum Demand
   ↓
4. System runs 30-minute interval simulation
   ↓
5. AI forecasts upcoming peak risk
   ↓
6. AI decides:
      - discharge battery
      - preserve battery
      - charge battery
      - shift flexible load
   ↓
7. System generates optimized grid import curve
   ↓
8. Dashboard compares before vs after
   ↓
9. AI explains actions and estimated savings
```

---

# 7. Input Requirements

## CSV Required Columns

```csv
timestamp,load_kw,solar_kw
2026-01-01 14:00,850,320
2026-01-01 14:30,930,250
```

## Optional Columns

```csv
ev_load_kw,flexible_load_kw,battery_soc
```

## User Configuration

| Setting          |    Default |
| ---------------- | ---------: |
| Demand limit     |     800 kW |
| MD rate          | RM97.06/kW |
| Peak period      | 2 PM–10 PM |
| Battery capacity |    500 kWh |
| Max discharge    |     100 kW |
| Max charge       |     100 kW |
| Min SoC          |        20% |
| Max SoC          |        90% |
| Interval         | 30 minutes |

---

# 8. Core Calculations

## Grid Import

```text
Grid Import = Load - Solar - Battery Discharge + Battery Charge
```

## Maximum Demand

```text
Maximum Demand = highest Grid Import in billing period
```

## MD Cost

```text
MD Cost = Maximum Demand × MD Rate
```

Example:

```text
950 kW × RM97.06/kW = RM92,207
```

## Required Peak Reduction

```text
Required Reduction = Forecasted Grid Import - Demand Limit
```

Example:

```text
920 kW - 800 kW = 120 kW
```

## Optimized Grid Import

```text
Optimized Grid Import = Original Grid Import - Battery Discharge - Shifted Load
```

Example:

```text
950 kW - 70 kW - 80 kW = 800 kW
```

## MD Savings

```text
MD Savings = Original MD Cost - Optimized MD Cost
```

or:

```text
MD Savings = (Original MD - Optimized MD) × MD Rate
```

Example:

```text
(950 kW - 800 kW) × RM97.06/kW = RM14,559
```

---

# 9. Main Pages

## Page 1: Upload and Setup

Purpose:

```text
Let user upload data and configure simulation settings.
```

Components:

```text
CSV upload box
Tariff settings form
Battery settings form
Demand limit input
Run simulation button
```

Required UI fields:

```text
MD rate
Peak start time
Peak end time
Demand limit
Battery capacity
Max discharge power
Max charge power
Minimum SoC
Maximum SoC
```

---

## Page 2: Baseline Analysis

Purpose:

```text
Show the original problem before AI optimization.
```

Widgets:

```text
Original Maximum Demand
Original MD Cost
Peak time
Average load
Solar offset
Number of peak-risk intervals
```

Charts:

```text
Original load curve
Solar generation curve
Grid import curve
Demand limit line
Peak period shading
```

---

## Page 3: AI Simulation Dashboard

Purpose:

```text
Show the optimized result after AI decisions.
```

Widgets:

```text
Original MD
Optimized MD
Peak reduction
MD savings
Battery energy used
Final battery SoC
Shifted load amount
```

Charts:

```text
Original vs optimized grid import
Battery SoC over time
Battery charge/discharge power
Solar generation
Flexible load shifted
```

---

## Page 4: AI Decision Timeline

Purpose:

```text
Show explainability.
```

Each decision log should show:

```text
Timestamp
Agent name
Problem detected
Action taken
Reason
Expected impact
Savings estimate
Battery SoC before and after
```

Example:

```text
15:30 — Forecasting Agent detected predicted grid import of 920 kW.

Planner Agent:
Demand limit is 800 kW. Required reduction is 120 kW.

Optimization Agent:
Shift 50 kW flexible load and discharge 70 kW from battery.

Auditor Agent:
Optimized grid import reduced to 800 kW.
Estimated MD saving: RM11,647.20.
```

---

# 10. AI Agent Roles

## 1. Forecasting Agent

Purpose:

```text
Predict upcoming grid import.
```

Input:

```text
Historical load
Solar profile
Current timestamp
Previous intervals
```

Output:

```json
{
  "forecast_grid_import_kw": 920,
  "forecast_horizon_minutes": 30
}
```

---

## 2. Planner Agent

Purpose:

```text
Decide high-level strategy.
```

Example:

```text
Solar is dropping after 4:30 PM. Preserve battery for evening peak.
```

---

## 3. Optimization Agent

Purpose:

```text
Calculate battery discharge and load shifting amount.
```

Output:

```json
{
  "battery_discharge_kw": 70,
  "shifted_load_kw": 50,
  "target_grid_import_kw": 800
}
```

---

## 4. Controller Agent

Purpose:

```text
Apply the simulated action to the dataset.
```

For MVP, it does not control hardware. It only modifies the simulated optimized curve.

---

## 5. Auditor Agent

Purpose:

```text
Check whether the action worked.
```

Output:

```json
{
  "original_grid_import_kw": 920,
  "optimized_grid_import_kw": 800,
  "reduction_kw": 120,
  "estimated_saving_rm": 11647.2
}
```

---

# 11. Backend API Contract

## Upload Dataset

```http
POST /api/datasets/upload
```

Response:

```json
{
  "dataset_id": "dataset_001",
  "rows": 17520,
  "interval_minutes": 30,
  "columns": ["timestamp", "load_kw", "solar_kw"]
}
```

---

## Run Simulation

```http
POST /api/simulations/run
```

Request:

```json
{
  "dataset_id": "dataset_001",
  "demand_limit_kw": 800,
  "md_rate_rm_per_kw": 97.06,
  "peak_start": "14:00",
  "peak_end": "22:00",
  "battery_capacity_kwh": 500,
  "max_discharge_kw": 100,
  "max_charge_kw": 100,
  "min_soc_percent": 20,
  "max_soc_percent": 90,
  "enable_battery": true,
  "enable_load_shifting": true
}
```

Response:

```json
{
  "simulation_id": "sim_001",
  "summary": {
    "original_md_kw": 950,
    "optimized_md_kw": 800,
    "peak_reduction_kw": 150,
    "original_md_cost_rm": 92207,
    "optimized_md_cost_rm": 77648,
    "md_savings_rm": 14559,
    "battery_energy_used_kwh": 35,
    "final_soc_percent": 63
  }
}
```

---

## Get Simulation Results

```http
GET /api/simulations/{simulation_id}
```

Response:

```json
{
  "summary": {
    "original_md_kw": 950,
    "optimized_md_kw": 800,
    "md_savings_rm": 14559
  },
  "timeseries": [
    {
      "timestamp": "2026-01-01 15:00",
      "load_kw": 950,
      "solar_kw": 0,
      "original_grid_import_kw": 950,
      "optimized_grid_import_kw": 800,
      "battery_power_kw": -70,
      "battery_soc_percent": 63,
      "shifted_load_kw": 80,
      "demand_limit_kw": 800,
      "is_peak_period": true
    }
  ],
  "decision_logs": [
    {
      "timestamp": "2026-01-01 15:00",
      "agent": "Optimization Agent",
      "decision": "Discharge battery and shift EV charging",
      "reason": "Forecasted demand exceeded demand limit by 150 kW.",
      "battery_discharge_kw": 70,
      "shifted_load_kw": 80,
      "expected_reduction_kw": 150,
      "estimated_saving_rm": 14559
    }
  ]
}
```

---

# 12. Frontend Requirements

## Tech Stack

```text
Next.js
TypeScript
TailwindCSS
ShadCN UI
Plotly.js / react-plotly.js
Zustand or React Context
```

Use Plotly for charts.

---

## Visual Style

```text
Clean energy-tech dashboard
Dark mode preferred
Professional but not too enterprise-heavy
Cards, charts, timeline, upload panel
Green/blue energy theme
Clear before-vs-after comparison
```

---

# 13. Dashboard Components

## KPI Cards

```text
Original Maximum Demand
Optimized Maximum Demand
Peak Reduction
Estimated MD Savings
Battery Energy Used
Final SoC
```

## Charts

```text
Original vs optimized grid import
Battery SoC
Solar generation
Battery dispatch power
Load shifting events
```

## AI Decision Feed

```text
Chronological timeline
Agent labels
Reason
Action
Impact
```

## Scenario Tabs

```text
Baseline
Solar Only
Battery Only
Load Shifting Only
Battery + Load Shifting
```

---

# 14. Acceptance Criteria

The MVP is acceptable when:

```text
User can upload or use sample CSV data.
User can edit tariff and battery settings.
Dashboard shows original Maximum Demand.
Dashboard shows optimized Maximum Demand.
Dashboard shows original vs optimized load curve.
Dashboard shows MD savings in RM.
Dashboard shows battery SoC over time.
Dashboard shows AI decision logs.
Frontend works even with mock data before backend is ready.
```

---

# Frontend AI Agent Prompt

Copy this into your frontend AI agent:

```text
You are building the frontend for an AI-powered energy peak shaving simulation dashboard.

Project name: GridWise AI

Goal:
Build a polished web dashboard that lets users upload building electricity CSV data, configure tariff and battery settings, run an AI optimization simulation, and compare original vs optimized grid demand.

Use this stack:
- Next.js 15
- TypeScript
- TailwindCSS
- ShadCN UI
- Plotly.js or react-plotly.js for charts
- Zustand or React Context for app state

Important:
This is a simulation-first MVP. Do not build real IoT control. The frontend should work with mock data first, but structure the code so it can call real backend APIs later.

Core app flow:
1. Upload CSV
2. Configure tariff and battery settings
3. Show baseline Maximum Demand analysis
4. Run AI optimization simulation
5. Show before/after dashboard
6. Show AI decision timeline

Pages or main sections:

1. Upload & Configuration Page
Components:
- CSV upload card
- sample dataset button
- tariff settings form
- battery settings form
- demand limit input
- run simulation button

Default configuration:
- demand_limit_kw: 800
- md_rate_rm_per_kw: 97.06
- peak_start: "14:00"
- peak_end: "22:00"
- battery_capacity_kwh: 500
- max_discharge_kw: 100
- max_charge_kw: 100
- min_soc_percent: 20
- max_soc_percent: 90
- interval_minutes: 30
- enable_battery: true
- enable_load_shifting: true

2. Baseline Analysis Section
Show these KPI cards:
- Original Maximum Demand: 950 kW
- Original MD Cost: RM92,207
- Peak Time: 3:00 PM
- Peak Risk Intervals: 6
- Solar Offset: 320 kW

Charts:
- Original load curve
- Solar generation curve
- Original grid import curve
- Demand limit line
- Peak period shading from 2 PM to 10 PM

3. Optimization Dashboard Section
Show these KPI cards:
- Original MD: 950 kW
- Optimized MD: 800 kW
- Peak Reduction: 150 kW
- Estimated MD Savings: RM14,559
- Battery Energy Used: 35 kWh
- Final Battery SoC: 63%

Charts:
- Original vs optimized grid import
- Battery SoC over time
- Battery charge/discharge power
- Solar generation
- Shifted flexible load

4. AI Decision Timeline
Create a timeline component with agent-labelled logs:
- Forecasting Agent
- Planner Agent
- Optimization Agent
- Controller Agent
- Auditor Agent

Each log item should show:
- timestamp
- agent name
- decision
- reason
- action
- expected impact

Example decision log:
15:00 — Forecasting Agent detected predicted grid import of 950 kW.
Planner Agent calculated demand limit breach of 150 kW.
Optimization Agent shifted 80 kW flexible load and discharged 70 kW battery.
Auditor Agent confirmed optimized grid import is 800 kW and estimated MD saving is RM14,559.

5. Scenario Tabs
Create tabs:
- Baseline
- Solar Only
- Battery Only
- Load Shifting Only
- Battery + Load Shifting

The most important scenario is Battery + Load Shifting.

Data model:
Use this mock timeseries data shape:

type EnergyPoint = {
  timestamp: string;
  load_kw: number;
  solar_kw: number;
  original_grid_import_kw: number;
  optimized_grid_import_kw: number;
  battery_power_kw: number;
  battery_soc_percent: number;
  shifted_load_kw: number;
  demand_limit_kw: number;
  is_peak_period: boolean;
};

type SimulationSummary = {
  original_md_kw: number;
  optimized_md_kw: number;
  peak_reduction_kw: number;
  original_md_cost_rm: number;
  optimized_md_cost_rm: number;
  md_savings_rm: number;
  battery_energy_used_kwh: number;
  final_soc_percent: number;
};

type DecisionLog = {
  timestamp: string;
  agent: "Forecasting Agent" | "Planner Agent" | "Optimization Agent" | "Controller Agent" | "Auditor Agent";
  decision: string;
  reason: string;
  action: string;
  expected_reduction_kw?: number;
  estimated_saving_rm?: number;
};

API contract for future backend:

POST /api/datasets/upload
Response:
{
  "dataset_id": "dataset_001",
  "rows": 17520,
  "interval_minutes": 30,
  "columns": ["timestamp", "load_kw", "solar_kw"]
}

POST /api/simulations/run
Request:
{
  "dataset_id": "dataset_001",
  "demand_limit_kw": 800,
  "md_rate_rm_per_kw": 97.06,
  "peak_start": "14:00",
  "peak_end": "22:00",
  "battery_capacity_kwh": 500,
  "max_discharge_kw": 100,
  "max_charge_kw": 100,
  "min_soc_percent": 20,
  "max_soc_percent": 90,
  "enable_battery": true,
  "enable_load_shifting": true
}

GET /api/simulations/{simulation_id}
Response:
{
  "summary": SimulationSummary,
  "timeseries": EnergyPoint[],
  "decision_logs": DecisionLog[]
}

Design requirements:
- Use a dark dashboard layout.
- Use clear cards for the main metrics.
- Use Plotly for interactive charts.
- Make before-vs-after comparison visually obvious.
- Use badges for Peak, Off-Peak, Battery Discharge, Load Shift.
- Add a left sidebar with sections:
  - Setup
  - Baseline
  - Simulation
  - AI Decisions
  - Scenarios
- Make the layout responsive.
- Use clean spacing and professional energy-tech UI.

Do not add unnecessary marketing copy.
Do not make it look like a generic SaaS landing page.
This should look like a working hackathon MVP dashboard for an energy optimization system.
```

---

# Build Priority

Build in this order:

```text
1. Mock dashboard with sample data
2. Upload/configuration UI
3. KPI cards
4. Original vs optimized Plotly chart
5. Battery SoC chart
6. AI decision timeline
7. API integration later
```

For the hackathon/demo, the most important screen is:

```text
Original MD: 950 kW
Optimized MD: 800 kW
Savings: RM14,559
AI action: battery discharge + load shifting
```
