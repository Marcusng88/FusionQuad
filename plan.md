Autonomous Load Management and Strategic Peak Shaving: An Agentic AI Framework for the 2025 Malaysian Electricity Tariff Landscape
The Malaysian energy landscape is currently undergoing a structural transformation characterized by the transition from Regulatory Period 3 (RP3) to Regulatory Period 4 (RP4), which introduces cost-reflective pricing mechanisms intended to stabilize the national grid while simultaneously incentivizing aggressive industrial decarbonization. This transition is most acutely manifested in the radical restructuring of Maximum Demand (MD) charges for commercial and industrial (C&I) users. Effective July 1, 2025, Tenaga Nasional Berhad (TNB) will implement a new tariff structure where traditional MD charges—now disaggregated into specific Capacity and Network charges—will escalate from approximately RM 30.30/kW to RM 97.06/kW for Medium Voltage Time-of-Use (TOU) customers.1 This shift represents a move away from reactive energy management towards a paradigm where intelligent, predictive, and autonomous orchestration of flexible loads is no longer an operational luxury but a requirement for financial viability.
Traditional energy management systems (EMS) have historically relied on static rule-based logic or manual set-point adjustments, both of which are inherently incapable of managing the stochastic nature of contemporary energy systems. The modern Malaysian C&I facility is a complex ecosystem of solar photovoltaic (PV) generation, battery energy storage systems (BESS), HVAC infrastructure, and high-power electric vehicle (EV) charging clusters.1 The lack of intelligent, predictive energy management capable of forecasting demand and autonomously performing load shifting or peak shaving is the core challenge identified for Theme 1 of the ESUM X RExharge Case Study Competition.1 The integration of Agentic Artificial Intelligence (AI) provides a sophisticated solution to this complexity. Unlike standard machine learning models that function as passive advisors, Agentic AI systems are designed as autonomous reasoning engines—agents-in-the-loop that perceive the environment, reason through multi-objective constraints (such as cost, battery health, and operational comfort), plan complex sequences of actions, and execute these decisions in real-time.6 By utilizing frameworks such as LangGraph to orchestrate multi-agent systems (MAS), energy managers can deploy stateful, iterative workflows that continuously adapt to real-time grid conditions and variable tariff signals.8
The Regulatory and Fiscal Imperative: Analyzing the July 2025 Tariff Revision
The implementation of the new tariff structure on July 1, 2025, reflects the government’s commitment to the Imbalance Cost Pass-Through (ICPT) mechanism and the broader strategic goals of the National Energy Transition Roadmap (NETR). The base tariff for Peninsular Malaysia is adjusted to 45.40 sen/kWh, representing a 14.2% increase from previous regulatory periods.11 However, the most profound impact on the monthly bills of commercial and industrial enterprises stems from the restructuring of infrastructure-related charges.
Disaggregation of Infrastructure Charges and Maximum Demand Mechanics
Under the revised structure, the previous consolidated Maximum Demand (MD) charge is replaced by a two-component system: the Capacity Charge and the Network Charge. The Capacity Charge is designed to recover costs associated with generation availability and power plant reserves, while the Network Charge addresses the capital and operational expenditure of maintaining the national transmission and distribution grid.12 For Medium Voltage customers under the C2 and E2 tariffs, this disaggregation results in a staggering cumulative demand-based charge.
Tariff Category
Component
Rate (Effective July 2025)
Total MD Charge Equivalent
Tariff C2 (MV Commercial TOU)
Capacity Charge
RM 30.19/kW
RM 97.06/kW


Network Charge
RM 66.87/kW


Tariff E2 (MV Industrial TOU)
Capacity Charge
RM 30.19/kW
RM 97.06/kW


Network Charge
RM 66.87/kW


Tariff C1 (MV General Commercial)
Capacity Charge
RM 29.43/kW
RM 89.27/kW


Network Charge
RM 59.84/kW


Tariff E1 (MV General Industrial)
Capacity Charge
RM 29.43/kW
RM 89.27/kW


Network Charge
RM 59.84/kW



These charges, sourced from 2, illustrate that a single 30-minute excursion in peak power usage can result in financial penalties totaling thousands of ringgit. For a facility with a 2,550 kW peak demand, the monthly MD charge under the RM 97.06/kW rate reaches RM 247,503.3 Consequently, even a modest 100 kW reduction in peak demand through intelligent shaving results in immediate monthly savings of RM 9,706 and annual savings exceeding RM 116,000.13
Dynamic Adjustments and Incentives
Furthermore, the revised structure introduces the Automatic Fuel Adjustment (AFA), which replaces the traditional ICPT surcharge/rebate. The AFA rate is calculated monthly based on real-time fluctuations in global fuel prices and currency exchange rates, with a capped volatility of  sen/kWh.2 For domestic and low-voltage users, TNB has also introduced the Energy Efficiency Incentive (EEI), a tiered rebate system for consumers utilizing 1,000 kWh or less per month.

Monthly Consumption (kWh)
EEI Rebate (sen/kWh)
Strategic Implication
1 - 200
-25.0
High incentive for minimal base-load 12
201 - 300
-22.5
Tiered benefit for low-demand residential 12
551 - 600
-9.0
Limit of waiver for retail charges 12
901 - 1,000
-0.5
Threshold for qualifying as "efficient" 14

While the EEI is primarily targeted at smaller users, the logic extends to C&I facilities: by shifting flexible loads to off-peak periods, enterprises can reduce their energy charge (sen/kWh) while simultaneously avoiding the high-cost MD windows.12 The Time-of-Use (TOU) windows are strictly defined, with peak periods occurring from 2:00 PM to 10:00 PM, Monday through Friday. Off-peak hours include all day on weekends and public holidays, as well as the 10:00 PM to 2:00 PM interval on weekdays.2 Notably, for MV and HV customers, Maximum Demand occurring during the off-peak period is not charged, providing a critical window for energy-intensive operations and battery charging.14
Empirical Analysis of Malaysian Load Profiles
The development of an effective load management algorithm requires a deep understanding of the load profiles provided in the case study datasets. Analysis of these datasets identifies recurring patterns that define the boundaries of optimization.
Study of Load Profile (No Solar)
The "No Solar" load profile 3 typical of a Malaysian commercial facility reveals a baseline consumption that persists overnight, typically ranging from 40 kW to 60 kW in smaller facilities, or several hundred kW in larger industrial settings. A sharp ramp-up is observed starting at 8:00 AM, driven by the activation of HVAC systems, production lines, and lighting. The most significant observation is the timing of peak demand. High usage consistently occurs between 2:00 PM and 5:00 PM, coinciding with the peak of the external ambient temperature (driving cooling loads) and the start of the TNB peak tariff window.3 In the [17] dataset, values such as 845 kW import at 23:30 and spikes of 920 kW during early morning hours suggest a facility with continuous 24-hour operations, where uncoordinated high-power loads lead to costly excursions.
Study of Load Profile (With Solar)
The integration of solar PV modifies the grid import profile significantly. Under the 944.88 kWp solar installation scenario 19, grid import is suppressed during the 10:00 AM to 4:00 PM window. However, a "duck curve" effect is prominent: as solar generation declines rapidly after 4:30 PM, the grid import ramps up while the facility remains in the TNB peak tariff period (which lasts until 10:00 PM). This "post-solar peak" is the most critical period for peak shaving.

Observation Metric
With Solar Profile
Operational Requirement
Peak Window Alignment
2:00 PM – 10:00 PM
Requires BESS discharge after 4:30 PM
Solar Generation Peak
12:00 PM – 2:00 PM
Prime charging window for BESS 21
Load Volatility
30-min spikes exceeding 800 kW
Requires real-time autonomous response
Grid Interaction
Occasional exports during low-load solar peaks
Opportunity for SMP arbitrage 22

The presence of reactive power (kVAR) import in the data (e.g., 264 kVAR import at 549 kW active power) also indicates that the solution could potentially integrate power factor correction strategies using the BESS inverter to avoid additional penalties from TNB.19
Theoretical Foundation of Peak Shaving and Load Shifting
To address Theme 1, the solution must distinguish between and integrate two primary technical interventions: peak shaving and load shifting.
Peak Shaving Mechanics
Peak shaving involves the reduction of electricity demand during the highest-load intervals to ensure the 30-minute average grid import stays below a predetermined limit.25 The objective is purely the mitigation of MD charges. This can be achieved through:
BESS Discharge: Supplying stored energy during spikes.13
Solar Utilization: Directly offsetting demand with real-time PV generation.4
Controlled Load-Shedding: Utilizing AI to cycle non-critical equipment (e.g., AHU, compressors) for 15-30 minute durations.13
Load Shifting and Arbitrage
Load shifting moves consumption from peak to off-peak periods to exploit price differentials.12 The financial benefit is derived from the difference between peak rates (e.g., 28.52 sen/kWh) and off-peak rates (24.43 sen/kWh).28

Integrating BESS allows for automated "valley filling" where the battery is charged during the low-cost 10:00 PM – 2:00 PM window and discharged during high-cost intervals, significantly boosting the solar ROI and accelerating payback times.21
The Agentic AI Paradigm: From Automation to Autonomous Reasoning
Traditional automation in energy management follows a "model-in-the-loop" approach, where an AI model provides a forecast, and a human or a fixed rule-based controller acts upon it. Agentic AI shifts this to an "agent-in-the-loop" paradigm.6 An agentic system is characterized by autonomy, proactivity, and goal-directed behavior—it doesn't just predict text or data; it executes multi-step plans in a cognitive control loop.7
Multi-Agent Systems (MAS) and Orchestration
The complexity of a C&I facility requires the decomposition of tasks into specialized agents working within an orchestration framework like LangGraph.8 A multi-agent design allows each agent to focus on a tractable unit of work, improving accuracy and reducing the context window overflow inherent in monolithic LLM designs.33

Agent Role
Responsibility
Interaction Pattern
Planner Agent
High-level strategy; task decomposition.32
Sets global goals based on TNB tariff rules.
Forecasting Agent
Predictive modeling of load and weather.35
Queries weather APIs; analyzes historical CSVs.37
Optimization Agent
Determining dispatch set-points for BESS.13
Uses MILP/RL to solve for cost-minimization.
Controller Agent
Real-time device execution.9
Communicates with inverters/BMS via APIs.32
Auditor Agent
Post-action verification and QA.34
Assigns reward scores based on savings.13

The LangGraph Stateful Execution Engine
LangGraph enables the construction of workflows as directed graphs where each node represents a discrete action and edges represent transitions.8 Crucially, LangGraph supports cycles and state persistence, which are essential for iterative optimization.10 In an energy context, the "State" of the graph carries context across reasoning steps:

Python


class AgentState(TypedDict):
    current_load: float
    battery_soc: float
    load_forecast: List[float]
    pricing_signal: str
    optimization_plan: List[dict]
    messages: List


This architecture allows the system to "remember" that a cloud cover was predicted 15 minutes ago when deciding whether to discharge the battery now to shave an emergent spike.39
The Agentic Reasoning Loop (ReAct) in Energy Management
The foundational pattern for autonomous agents is ReAct (Reason + Act). This loop allows an agent to interleave Chain-of-Thought (CoT) reasoning with the use of external tools.41
Execution Trace: Shaving a Predicted Peak
Perceive: The Forecast Agent retrieves the current demand (780 kW) and the 30-minute forecast (predicting 860 kW).
Reason: The Planner Agent compares this against the MD limit (800 kW). It identifies a required 60 kW shave.
Act: The Optimization Agent calls a tool to check battery health.
Observe: The tool returns "SoC: 70%, Temperature: 35°C, Cycle Count: 1200."
Reason: The Optimization Agent determines that a 60 kW discharge for 30 minutes will not violate DoD limits or trigger excessive degradation.
Act: The Controller Agent sends a SET_DISCHARGE_RATE command to the smart inverter.
Evaluate: The Auditor Agent calculates the achieved shave and updates the financial dashboard.
This deliberative strategy outperforms reactive systems because it weighs long-term asset health against immediate grid savings.43 SMarter exploration allows the agent to learn when and why to act, rather than just how.45
Integrated Techno-Economic Plan for Theme 1
To successfully address the Theme 1 deliverables, a multi-phased approach is required that bridges technical engineering logic with Malaysian market realities.5
Phase 1: Robust Forecasting and Feature Engineering
The solution must prioritize the Forecasting Agent. Historical load profiles 17 should be used to train models such as LSTMs or Gated Recurrent Units (GRUs).
Time-based features: 30-minute intervals aligned with TNB's billing cycle.3
Meteorological integration: Real-time irradiance predictions via OpenWeatherMap APIs to account for solar volatility.35
Contextual data: Malaysian public holiday schedules and typical office hours (8:00 AM – 6:00 PM) to predict occupancy-driven spikes.
Phase 2: Autonomous Sizing Logic (The Sizing Engine)
Determining the "sweet spot" for solar and battery capacity is a technical requirement.1 The solution should implement an iterative simulation loop—a "Planner Agent" that tests discrete system sizes to maximize Net Present Value (NPV).47
BESS Sizing Formula for Peak Shaving: The required energy capacity () is a function of the shave power (), the duration of the peak (), and a reserve factor to account for efficiency and DoD constraints.26

For a 500 kW target reduction over a 30-minute spike, a usable capacity of 250 kWh is needed, but an installed capacity of ~300 kWh is recommended to maintain a state-of-charge floor and preserve cycle life.48
Solar PV Sizing: To offset a targeted energy volume, the capacity is determined by the Peak Sun Hours (PSH), which in Malaysia is conservatively estimated at 3.7 PSH.48

Phase 3: Agentic Optimization and RL Post-training
The Optimization Agent should be refined using Agentic Reinforcement Learning (RL).42 By training the model over full tool-interaction trajectories, the agent learns to interleave reasoning with tool execution (e.g., querying price, checking SoC) to solve the complex task of minimizing the electricity bill while protecting the battery.42 Deliberative strategies with fewer, smarter tool calls are preferred to avoid "rambling" or infinite loops.44
The objective function for the RL agent:

Degradation modeling is a second-order insight critical for industrial stakeholders. The system must account for both calendar aging (time and SoC levels) and cycle aging (energy throughput), favoring smaller BESS power ratings under high load factors to minimize excessive cycling.51
Phase 4: Implementation Checklist and Competition Deliverables
As per the Participant's Handbook 46, the MVP must be ready for Mentoring Session 1 and continuously improved through D-Day.5

Deliverable
Requirement
Implementation Strategy
Working MVP
Must process data and automate the solution.5
Python-based MAS using LangGraph and LangChain.31
Demo Video
Max 10 minutes; showing impact.5
Visual recording of the AI reasoning trace and dashboard results.
Technical Report
Max 10 pages; including architecture.5
Detailed description of the MAS state machine and RL logic.
Visual Dashboard
Forecasting vs Actual; savings simulation.1
React/FastAPI interface showing real-time MD reductions.54

Economic Feasibility and The Fiscal Incentive Landscape
The viability of a load-shifting solution in Malaysia is fundamentally linked to the aggressive fiscal incentives provided by the government to support the green energy transition.
Green Investment Tax Allowance (GITA)
The GITA Asset scheme for own consumption allows companies to claim a 100% tax allowance on qualifying capital expenditure for BESS and solar PV.55 This allowance can be offset against 70% of the statutory income.

Tier
Asset Type
Allowance Rate
Condition
Tier 1
BESS / Green Building
100% 55
New asset; own consumption; MyHIJAU listed.57
Tier 2
Solar PV / Energy Efficiency
60% 55
Standard green investment recovery.58

Combining solar PV with BESS under GITA allows businesses to achieve accelerated tax savings, significantly shortening the payback period of a project from a typical 7-10 years to approximately 5-7 years.23 For a 100 kW commercial system, this tax relief combined with avoided MD charges creates a highly attractive Internal Rate of Return (IRR).49
Capital and Operating Expenditures (CAPEX/OPEX)
Detailed BESS cost analysis for 2025 reveals a stabilizing market.
Utility-scale All-in CAPEX: ~$125/kWh (October 2025).60
C&I Installed Cost: $280 - $580 per kWh for small systems; dropping to $180 - $300 for >100 kWh containerized systems.61
Levelized Cost of Storage (LCOS): Approximately $65/MWh (approx. RM 285/MWh).60
With the difference between off-peak charging (22.40 sen/kWh) and peak discharge (36.50 sen/kWh) being approximately 14.1 sen/kWh, arbitrage alone provides a compelling return, even before accounting for the massive RM 97.06/kW MD savings.18
Future-Proofing: The SELCO Mandate and Grid Evolution
The adoption of BESS is becoming a regulatory necessity. As of January 1, 2026, the Energy Commission (Suruhanjaya Tenaga) requires all new Self-Consumption (SELCO) solar installations exceeding 1 MWac to include a BESS to ensure grid stability and manage intermittency.4 This mandate ensures that the national grid can accommodate higher renewable penetration without sacrificing reliability.
Furthermore, Agentic AI systems are uniquely positioned to participate in the emerging Virtual Power Plant (VPP) ecosystem. In this future-facing scenario, AI agents will not only manage building-level peaks but also aggregate decentralized assets to provide ancillary services such as frequency regulation and voltage support to the national grid, creating secondary revenue streams for the facility owner.4
Technical Architecture: A Production-Ready Design
To transition from a competition MVP to a production-ready system, the architecture must incorporate robustness, observability, and security.
STATE-DRIVEN EXECUTION AND PERSISTENCE
Using LangGraph, the system implements a "StateGraph" that acts as the tracking mechanism for the entire workflow.8 The "checkpointer" object ensures that the state is persisted between executions. If a tool call to an IoT meter fails, the agent can retry the action without losing the context of the previous 30-minute energy forecast.40
GOVERNANCE AND HUMAN-IN-THE-LOOP (HITL)
In high-stakes industrial environments, autonomous AI must operate within defined boundaries. The architecture includes:
Schema Enforcement: Ensuring LLM outputs for discharge rates are always within the physical safety limits of the inverter.43
HITL Triggers: Requiring approval from a facility manager before executing "Critical" load-shedding actions that might impact production quality.39
Trace Visualization: Utilizing tools like LangSmith to log every decision, providing a "reasoning scratchpad" for post-event auditing and performance tracking.31
Observability and Troubleshooting
An agentic system transforms energy operations from reactive monitoring to proactive orchestration.67 For example, when a voltage fluctuation is detected, the agent doesn't just show a fault code—it correlates the issue with asset history, local weather conditions, and current grid stress levels to decide whether to dispatch a field crew or adjust local BESS set-points automatically.36
Strategic Approach to Deliverables and Plan of Approach
To satisfy the requirements of Theme 1, the following structured plan will be followed:
1. Data Foundation and Feasibility Simulation
The first step involves processing the provided CSV load profiles to establish a baseline. The Planner Agent will perform an "Exploration and Constrain" phase, identifying the specific times of day where MD excursions are most likely to occur.34 This simulation will determine the initial recommended sizing of solar and BESS based on the July 2025 tariff.1
2. Developing the Forecasting and Optimization Loop
A hybrid modeling approach will be implemented. Traditional ML (LSTM) will handle the baseline time-series forecasting, while an Agentic reasoning node will handle "context-aware" adjustments (e.g., a predicted cloud event affecting solar yield).35 The Optimization Agent will use a Deep Reinforcement Learning (DRL) agent trained via PPO to determine the optimal 30-minute discharge set-points.50
3. State Management via LangGraph
The MAS will be built using LangGraph nodes. The "Message Passing" layer will facilitate structured communication between the Forecaster, Optimizer, and Auditor.31 This ensures that the Auditor Agent can verify if the Optimizer's plan successfully reduced the grid import below the target threshold.34
4. Interactive Dashboard and Final Pitch
The final dashboard will present the "Before vs. After" impact analysis. Key metrics include:
Total Monthly Saving: Aggregated energy and MD cost reduction.13
Peak Reduction Percentage: Historical vs. Optimized peaks.27
Battery Health Dashboard: Real-time SoC and SoH projections.13
AI Reasoning Trace: A natural-language interface explaining the agent's logic (e.g., "Discharging 40kW to shave a predicted 15:30 spike while maintaining 20% reserve for the late-peak window").6
Nuanced Conclusions on Agentic Orchestration
The transition to autonomous energy management is not merely an incremental improvement over existing automation; it represents a paradigm shift in system architecture. The following conclusions are drawn from the comprehensive analysis of the Malaysian energy landscape and Agentic AI capabilities.
First, the volatility of the July 2025 tariff structure—specifically the RM 97.06/kW MD penalty—requires a level of reasoning that static algorithms cannot provide. Agentic AI, through its cognitive control loop of perception, reasoning, and action, is uniquely suited to navigate the multi-objective trade-offs between immediate financial savings and long-term asset degradation.6
Second, the "statefulness" of the agentic workflow is the critical enabling factor. Energy management is inherently a time-series problem where the current state is the result of previous historical trends and the foundation for future outcomes. LangGraph's ability to maintain a persistent state across complex, iterative decision cycles is essential for maintaining grid stability in industrial environments.8
Third, the integration of Reinforcement Learning with Agentic Reasoning offers a "best-of-both-worlds" approach. RL provides the mathematical "brawn" to learn optimal dispatch policies in simulation, while the agentic loop (ReAct) provides the "executive function" to safely apply those policies to real-world infrastructure and provide transparent explanations to human operators.6
Finally, the Malaysian regulatory context—characterized by 100% GITA allowances and the 2026 SELCO mandates—provides a fertile ground for the early adoption of these technologies. The ROI for integrated Solar+BESS systems is no longer speculative but is anchored in high infrastructure charges and substantial tax relief.27 The future of energy resilient C&I facilities in Malaysia will be defined by the seamless coordination of specialized AI agents, working together to transform raw energy telemetry into measurable operational efficiency and long-term sustainability. This comprehensive framework serves as the definitive roadmap for addressing Theme 1 and bridging the gap between theoretical AI and real-world industrial impact.
Works cited
Case Study Themes
TNB Tariff 2025/2026: New Rates & How Businesses Can Lower Costs - Plus Xnergy, accessed May 1, 2026, https://www.plusxnergy.com/july-2025-tnb-tariff-update-what-malaysian-businesses-need-to-know/
Cut Your TNB Maximum Demand Charges with EasiEMS Smart Peak Demand Control, accessed May 1, 2026, https://www.tanand.com.my/tnb-maximum-demand-easiems/
Battery Energy Storage System (BESS): Powering the Future, accessed May 1, 2026, https://aq.energy/blog/battery-energy-storage-system-bess-guide-malaysia/
ESUM X RExharge Case Study Competition Briefing Session.pdf
Agentic Artificial Intelligence for Smart Grids: A Comprehensive Review of Autonomous, Safe, and Explainable Control Frameworks - MDPI, accessed May 1, 2026, https://www.mdpi.com/1996-1073/19/3/617
Agentic AI and the Real Buzz Around it | by Prayag Chawla - Medium, accessed May 1, 2026, https://medium.com/@chawlapc.619/agentic-ai-and-the-real-buzz-around-it-9364330f7f95
Mastering LangGraph Workflow Orchestration in Enterprises - Sparkco, accessed May 1, 2026, https://sparkco.ai/blog/mastering-langgraph-workflow-orchestration-in-enterprises
Multi-Agent-Based Smart-Home Energy Management with Adaptive Reasoning - MDPI, accessed May 1, 2026, https://www.mdpi.com/2076-3417/16/4/1896
Demystifying Agentic AI: Why I'm Trading Chains for Graphs with LangGraph, accessed May 1, 2026, https://dev.to/ankitkumarshaw/demystifying-agentic-ai-why-im-trading-chains-for-graphs-with-langgraph-2678
TNB rates to increase by 14.2% effective July 2025 - Biipower Sdn Bhd, accessed May 1, 2026, https://www.biipower.com/latestnews/nid/159257/
Your New TNB Bill Explained: Understanding the Monthly Tariff Changes - RinggitPlus, accessed May 1, 2026, https://ringgitplus.com/en/blog/personal-finance-news/your-new-tnb-bill-explained-understanding-the-monthly-tariff-changes.html
Easi EMS + BESS for TNB Maximum Demand shaving - Tanand Technology, accessed May 1, 2026, https://www.tanand.com.my/service/cut-tnb-maximum-demand-charges-with-easiems/
Understand Your Electricity Tariff | TNB Malaysia - myTNB Portal, accessed May 1, 2026, https://www.mytnb.com.my/tariff
TNB Tariffs Decoded: Your 2026 Guide to Normal vs. Time of Use Plans (Domestic User, accessed May 1, 2026, https://www.solarsunyield.com/latestnews/nid/169869/
TNB's New Electricity Tariff (July 2025) and Its Impact on Air Conditioner Usage, accessed May 1, 2026, https://triair.com.my/tnbs-new-electricity-tariff-july-2025-and-its-impact-on-air-conditioner-usage/
2. Load Profile (No Solar) E.xlsx
Welcome to myTNB Portal - Business Pricing & Tariff, accessed May 1, 2026, https://www.mytnb.com.my/business/understand-your-bill/pricing-tariff
1. Load Profile (With Solar Installed) SoL.xlsx
4. Load Profile (With Solar) Mi2.xlsx
Battery Energy Storage System (BESS) - Sunview Group, accessed May 1, 2026, https://www.sunview.com.my/batteryenergy
Net Energy Metering (NEM) 3.0 - SEDA Malaysia, accessed May 1, 2026, https://www.seda.gov.my/reportal/nem/
NEM 2.0 vs NEM 3.0 Malaysia: Which Solar Scheme Is Better? - Unitrade Solar, accessed May 1, 2026, https://solar.unitrade.com.my/blog/nem-2-0-vs-nem-3-0-malaysia/
Optimal Component Sizing for Peak Shaving in Battery Energy Storage System for Industrial Applications - MDPI, accessed May 1, 2026, https://www.mdpi.com/1996-1073/11/8/2048
How Commercial Battery Storage Reduces Peak Demand Costs - U-sun Energy, accessed May 1, 2026, https://sz-usun.com/how-commercial-battery-storage-reduces-peak-demand-costs/
Peak Shaving for Demand Charges with Lithium-Ion Batteries, accessed May 1, 2026, https://www.anernstore.com/blogs/anern-solar-insights/peak-shaving-demand-charges-lithium-ion
How Peak Shaving is Transforming Malaysia's Power Landscape, accessed May 1, 2026, https://winfieldenergy-my.com/unlocking-energy-savings-how-peak-shaving-is-transforming-malaysias-power-landscape/
TNB Electricity Bill changes starting July 2025. What's new? - SoyaCincau, accessed May 1, 2026, https://soyacincau.com/2025/06/21/tnb-domestic-electricity-tariff-structure-july-2025-impact-changes/
Agentic AI vs. Generative AI - IBM, accessed May 1, 2026, https://www.ibm.com/think/topics/agentic-ai-vs-generative-ai
LLM vs. Agentic AI: A Deep Dive into the Future of AI Systems | by Rishabhtripathi - Medium, accessed May 1, 2026, https://medium.com/@rishabhtripathi.9984/llm-vs-agentic-ai-a-deep-dive-into-the-future-of-ai-systems-2a7cb069a574
LangGraph Multi-Agent Systems: Complete Tutorial & Examples - Latenode Blog, accessed May 1, 2026, https://latenode.com/blog/ai-frameworks-technical-infrastructure/langgraph-multi-agent-orchestration/langgraph-multi-agent-systems-complete-tutorial-examples
mohd-faizy/Agentic_AI_using_LangGraph: Agentic AI framework built using LangGraph and Multi-Agent Control Plane (MCP) for building structured, goal-driven multi-agent systems. - GitHub, accessed May 1, 2026, https://github.com/mohd-faizy/Agentic_AI_using_LangGraph
LangGraph: Multi-Agent Workflows - LangChain, accessed May 1, 2026, https://www.langchain.com/blog/langgraph-multi-agent-workflows
Agentic AI for Multi-Step Data Analysis - Amity, accessed May 1, 2026, https://www.amity.co/ai-labs/agentic-ai-multi-agent-data-analysis
How agentic AI is transforming renewable energy operations: Realizing the Energy Frontier | The Microsoft Cloud Blog, accessed May 1, 2026, https://www.microsoft.com/en-us/microsoft-cloud/blog/energy-and-resources/2026/04/21/how-agentic-ai-is-transforming-renewable-energy-operations-realizing-the-energy-frontier/
AI Agents for Energy, accessed May 1, 2026, https://aiagents4energy.com/
Imsharad/building-agents-langgraph - GitHub, accessed May 1, 2026, https://github.com/Imsharad/building-agents-langgraph
How Swarms of AI Agents Are Redefining Software Engineering - LangChain, accessed May 1, 2026, https://www.langchain.com/blog/agentic-engineering-redefining-software-engineering
SAP Agentic AI in Practice: Concepts, Architecture, and Your First LangGraph Agent, accessed May 1, 2026, https://community.sap.com/t5/artificial-intelligence-blogs-posts/sap-agentic-ai-in-practice-concepts-architecture-and-your-first-langgraph/ba-p/14361699
Building AI Workflows with LangGraph: Practical Use Cases and Examples - Scalable Path, accessed May 1, 2026, https://www.scalablepath.com/ai/langgraph
Agentic AI Architecture: Patterns & Production | The Thinking Company, accessed May 1, 2026, https://thinking.inc/en/pillar-pages/agentic-ai-architecture/
Daily Papers - Hugging Face, accessed May 1, 2026, https://huggingface.co/papers?q=agentic%20RL
Design Patterns for Agentic AI and Multi-Agent Systems - AppsTek Corp, accessed May 1, 2026, https://appstekcorp.com/blog/design-patterns-for-agentic-ai-and-multi-agent-systems/
Demystifying Reinforcement Learning in Agentic Reasoning - arXiv, accessed May 1, 2026, https://arxiv.org/html/2510.11701v1
Demystifying Reinforcement Learning in Agentic Reasoning | by Dixon - Medium, accessed May 1, 2026, https://medium.com/@huguosuo/demystifying-reinforcement-learning-in-agentic-reasoning-1f60f8e11ea3
Participant's Handbook.pdf
How to Right-Size Energy Storage (BESS) for Commercial Facilities: A Framework for Developers 2025/2026, accessed May 1, 2026, https://energysolutions-solar.com/right-size-bess-framework/
Battery Energy Storage System (BESS): Cutting Maximum Demand with Solar PV System and Battery Management System (BMS) - Solar Sunyield, accessed May 1, 2026, https://www.solarsunyield.com/latestnews/nid/166246/
Solar Energy Services in Malaysia: Post-NEM 3.0 Guide (July 2025) - HOMI, accessed May 1, 2026, https://homifytech.com.my/solar-energy-services-in-malaysia-post-nem-3-0-guide-july-2025/
DEMYSTIFYING REINFORCEMENT LEARNING IN AGENTIC REASONING - OpenReview, accessed May 1, 2026, https://openreview.net/pdf/8e6e5fa280b3e0823bc5341a22dac3196c7f5106.pdf
Optimal sizing of battery energy storage systems for peak shaving and demand response using a degradation-aware Bayesian Optimization-Mixed-Integer Linear Programming framework - Oak Ridge National Laboratory, accessed May 1, 2026, https://impact.ornl.gov/en/publications/optimal-sizing-of-battery-energy-storage-systems-for-peak-shaving/
Optimal Sizing of Battery Energy Storage Systems for Peak Shaving and Demand Response Using a Degradation-Aware Bayesian Optimiz - BYU ScholarsArchive, accessed May 1, 2026, https://scholarsarchive.byu.edu/cgi/viewcontent.cgi?article=9125&context=facpub
Briefing Session QNA Compile.pdf
Transforming renewable asset development using Agentic AI | AWS for Industries, accessed May 1, 2026, https://aws.amazon.com/blogs/industries/transforming-renewable-asset-development-using-agentic-ai/
Malaysia Green Investment Tax Allowance (GITA) For Own Comsumption - ty teoh international, accessed May 1, 2026, https://www.tyteoh.com/malaysia-green-investment-tax-allowance-gita-for-own-comsumption/
MALAYSIA GREEN INVESTMENT TAX ALLOWANCE (GITA) FOR OWN COMSUMPTION - ty teoh international, accessed May 1, 2026, https://www.tyteoh.com/wp-content/uploads/2025/01/32.-GITA-for-Own-Comsumption-SG-EN-011024.pdf
GITA Asset - MyHIJAU, accessed May 1, 2026, https://www.myhijau.my/assets/pdf/Green%20Investement%20Tax%20Allowance%20(GITA)%20-%20April%202025.pdf
Green Technology Tax Incentives in Malaysia 2025 - Progressture Solar, accessed May 1, 2026, https://www.progressturesolar.com/post/green-technology-tax-incentives-2025
Malaysia GITA Incentive 2025: Guide to Green Technology Tax Relief - TERA, accessed May 1, 2026, https://www.tera.solar/news-articles/your-guide-to-malaysias-gita-incentive-for-green-technology-in-2025/
How cheap is battery storage? | Ember, accessed May 1, 2026, https://ember-energy.org/app/uploads/2025/12/How-cheap-is-battery-storage-PDF.pdf
The Real Cost of Commercial Battery Energy Storage in 2026: What You Need to Know, accessed May 1, 2026, https://www.gsl-energy.com/the-real-cost-of-commercial-battery-energy-storage-in-2025-what-you-need-to-know.html
The Real Cost of Commercial Battery Energy Storage in 2025: What You Need to Know, accessed May 1, 2026, https://www.gslenergybattery.com/the-real-cost-of-commercial-battery-energy-storage-in-2025-what-you-need-to-know
Agentic AI in Energy Operations: Transforming Efficiency and Sustainability - ResearchGate, accessed May 1, 2026, https://www.researchgate.net/publication/400654070_Agentic_AI_in_Energy_Operations_Transforming_Efficiency_and_Sustainability
Build a Multi-Agent System with LangGraph and Mistral on AWS | Artificial Intelligence, accessed May 1, 2026, https://aws.amazon.com/blogs/machine-learning/build-a-multi-agent-system-with-langgraph-and-mistral-on-aws/
24/7 Simulation Loops: How Agentic AI Keeps Subsurface Engineering Moving, accessed May 1, 2026, https://developer.nvidia.com/blog/24-7-simulation-loops-how-agentic-ai-keeps-subsurface-engineering-moving/
Agentic AI's Next Iteration: From Super-AIs to Teams of Specialized Agents — And What It Means for Law & Business | Epstein Becker Green, accessed May 1, 2026, https://www.commerciallitigationupdate.com/agentic-ais-next-iteration-from-super-ais-to-teams-of-specialized-agents-and-what-it-means-for-law-business
Managing Sustainable Operations for the Energy Industry via Agentic AI - iTech India, accessed May 1, 2026, https://itechindia.co/blog/ai-agents-for-energy-industry/
How to Train Scientific Agents with Reinforcement Learning | NVIDIA Technical Blog, accessed May 1, 2026, https://developer.nvidia.com/blog/how-to-train-scientific-agents-with-reinforcement-learning/
AI-Powered Energy Management Solution for Manufacturing - NexaStack, accessed May 1, 2026, https://www.nexastack.ai/use-cases/energy-management-solution
