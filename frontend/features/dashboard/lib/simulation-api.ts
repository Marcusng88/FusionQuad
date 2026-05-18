import type {
  AgentUpdatePayload,
  DecisionLog,
  ScenarioMetadata,
  SimulationApiState,
  SimulationDayType,
} from "../types";

type StartPayload = {
  dayType: SimulationDayType;
  bessCapacityKwh: number;
  batterySoc?: number;
  startTime?: string | null;
  endTime?: string | null;
  forecastModel?: "gru_attention" | "gru";
};

const DEFAULT_API_BASE_URL = "http://localhost:8000";

function resolveBaseUrl(baseUrl?: string) {
  const candidate =
    baseUrl ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    DEFAULT_API_BASE_URL;

  return candidate.endsWith("/") ? candidate.slice(0, -1) : candidate;
}

async function requestSimulationState(
  path: string,
  init: RequestInit,
  baseUrl?: string,
): Promise<SimulationApiState> {
  const response = await fetch(`${resolveBaseUrl(baseUrl)}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init.headers || {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Simulation request failed with ${response.status}.`);
  }

  const data = await response.json();
  if (!data?.session_id || !data?.status) {
    throw new Error(`Invalid simulation response: missing required fields`);
  }
  return data as SimulationApiState;
}

export async function fetchScenarioMetadata(
  dayType: SimulationDayType,
  baseUrl?: string,
): Promise<ScenarioMetadata> {
  const response = await fetch(
    `${resolveBaseUrl(baseUrl)}/api/v1/simulation/scenarios/${dayType}/metadata`,
    { method: "GET", cache: "no-store" },
  );
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Failed to fetch metadata for ${dayType}.`);
  }
  return response.json() as Promise<ScenarioMetadata>;
}

export function startSimulation(
  payload: StartPayload,
  baseUrl?: string,
) {
  return requestSimulationState(
    "/api/v1/simulation/start",
    {
      method: "POST",
      body: JSON.stringify({
        day_type: payload.dayType,
        bess_capacity_kwh: payload.bessCapacityKwh,
        battery_soc: payload.batterySoc ?? 0.5,
        start_time: payload.startTime ?? null,
        end_time: payload.endTime ?? null,
        forecast_model: payload.forecastModel ?? "gru_attention",
      }),
    },
    baseUrl,
  );
}

export function runSimulation(sessionId: string, baseUrl?: string) {
  return requestSimulationState(
    "/api/v1/simulation/run",
    {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId }),
    },
    baseUrl,
  );
}

export function getSimulationState(sessionId: string, baseUrl?: string) {
  const params = new URLSearchParams({ session_id: sessionId });
  return requestSimulationState(
    `/api/v1/simulation/state?${params.toString()}`,
    { method: "GET" },
    baseUrl,
  );
}

export type StreamCallbacks = {
  onAgentUpdate: (payload: AgentUpdatePayload) => void;
  onStepComplete: (snapshot: SimulationApiState) => void;
  onError: (message: string) => void;
  onDone: () => void;
  onAgentStart?: (node: string, timestamp: string) => void;
  onAgentToken?: (node: string, token: string) => void;
  onAgentComplete?: (node: string, trace: DecisionLog | null) => void;
};

export function subscribeSimulationStream(
  sessionId: string,
  onAgentUpdate: StreamCallbacks["onAgentUpdate"],
  onStepComplete: StreamCallbacks["onStepComplete"],
  onError: StreamCallbacks["onError"],
  onDone: StreamCallbacks["onDone"],
  baseUrl?: string,
  extraCallbacks?: Pick<StreamCallbacks, "onAgentStart" | "onAgentToken" | "onAgentComplete">,
): () => void {
  const url = `${resolveBaseUrl(baseUrl)}/api/v1/simulation/stream/${sessionId}`;
  const es = new EventSource(url);

  es.addEventListener("agent_update", (e: MessageEvent) => {
    const parsed = JSON.parse(e.data) as AgentUpdatePayload;
    onAgentUpdate(parsed);
  });

  es.addEventListener("step_complete", (e: MessageEvent) => {
    onStepComplete(JSON.parse(e.data) as SimulationApiState);
  });

  es.addEventListener("agent_start", (e: MessageEvent) => {
    if (extraCallbacks?.onAgentStart) {
      const parsed = JSON.parse(e.data) as { node: string; timestamp: string };
      extraCallbacks.onAgentStart(parsed.node, parsed.timestamp);
    }
  });

  es.addEventListener("agent_token", (e: MessageEvent) => {
    if (extraCallbacks?.onAgentToken) {
      const parsed = JSON.parse(e.data) as { node: string; token: string };
      extraCallbacks.onAgentToken(parsed.node, parsed.token);
    }
  });

  es.addEventListener("agent_complete", (e: MessageEvent) => {
    if (extraCallbacks?.onAgentComplete) {
      const parsed = JSON.parse(e.data) as { node: string; trace: DecisionLog | null };
      extraCallbacks.onAgentComplete(parsed.node, parsed.trace);
    }
  });

  es.addEventListener("simulation_done", () => {
    es.close();
    onDone();
  });

  es.addEventListener("error", (e: Event) => {
    if (e instanceof MessageEvent) {
      const parsed = JSON.parse(e.data) as { message: string };
      onError(parsed.message);
    }
    es.close();
  });

  es.onerror = () => {
    es.close();
    onError("Stream connection lost.");
  };

  return () => es.close();
}
