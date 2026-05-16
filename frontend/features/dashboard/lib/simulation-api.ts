import type {
  SimulationApiState,
  SimulationDayType,
} from "../types";

type StartPayload = {
  dayType: SimulationDayType;
  bessCapacityKwh: number;
  batterySoc?: number;
  startTime?: string | null;
  endTime?: string | null;
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

  return (await response.json()) as SimulationApiState;
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
