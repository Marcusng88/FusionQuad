"use client";

import {
  startTransition,
  useCallback,
  useRef,
  useState,
} from "react";

import { DAY_SCENARIOS } from "../data/day-scenarios";
import {
  addOrUpdateTab,
  closeTab as closeTabFn,
  createDayTab,
  createSimulationViewModel,
  handleAgentComplete as handleAgentCompleteFn,
  handleAgentStart as handleAgentStartFn,
  handleAgentToken as handleAgentTokenFn,
  mergeAgentUpdate,
  mergeSimulationSnapshot,
  togglePinTab as togglePinTabFn,
} from "../lib/live-simulation";
import {
  fetchScenarioMetadata,
  startSimulation,
  subscribeSimulationStream,
} from "../lib/simulation-api";
import type {
  DayTab,
  ScenarioMetadata,
  SimulationApiState,
  SimulationDayType,
  SimulationViewModel,
} from "../types";

function resolveDayOptions(scenarios: SimulationApiState["scenarios"]) {
  if (scenarios && scenarios.length > 0) {
    return scenarios.map((s) => ({ key: s.key as SimulationDayType, label: s.label, blurb: s.blurb }));
  }
  return DAY_SCENARIOS;
}

export function useSimulationController() {
  const [selectedDayType, setSelectedDayType] =
    useState<SimulationDayType>("weekday");
  const [forecastModel, setForecastModel] = useState<"gru_attention" | "gru">("gru_attention");
  const [bessCapacityKwh, setBessCapacityKwh] = useState(1000);
  const [batterySoc, setBatterySoc] = useState(0.5);
  const [timeRange, setTimeRange] = useState<{ start: string | null; end: string | null }>({
    start: null,
    end: null,
  });
  const [scenarioMetadata, setScenarioMetadata] = useState<ScenarioMetadata | null>(null);
  const [metadataLoading, setMetadataLoading] = useState(false);
  const [simulation, setSimulation] = useState<SimulationViewModel>(() =>
    createSimulationViewModel("weekday"),
  );
  const [isBusy, setIsBusy] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [activeAgentNode, setActiveAgentNode] = useState<string | null>(null);
  const [tabs, setTabs] = useState<DayTab[]>([]);
  const [activeTabId, setActiveTabId] = useState<string | null>(null);
  const activeTabIdRef = useRef<string | null>(null);
  const streamCleanupRef = useRef<(() => void) | null>(null);

  const dayOptions = resolveDayOptions(simulation.scenarios);

  const applySnapshot = useCallback(async (
    executor: () => Promise<SimulationApiState>,
    reset = false,
    dayType = selectedDayType,
  ) => {
    setIsBusy(true);
    setErrorMessage(null);

    try {
      const snapshot = await executor();
      startTransition(() => {
        setSimulation((current) =>
          mergeSimulationSnapshot(
            reset ? createSimulationViewModel(dayType) : current,
            snapshot,
          ),
        );
      });
      return snapshot;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Simulation request failed.";
      setErrorMessage(message);
      return null;
    } finally {
      setIsBusy(false);
    }
  }, [selectedDayType]);

  async function bootstrapSimulation(
    dayType = selectedDayType,
    capacityKwh = bessCapacityKwh,
    soc = batterySoc,
    range?: { start: string | null; end: string | null },
    model: "gru_attention" | "gru" = forecastModel,
  ) {
    streamCleanupRef.current?.();
    streamCleanupRef.current = null;

    const started = await applySnapshot(
      () =>
        startSimulation({
          dayType,
          bessCapacityKwh: capacityKwh,
          batterySoc: soc,
          startTime: range?.start,
          endTime: range?.end,
          forecastModel: model,
        }),
      true,
      dayType,
    );

    if (!started) {
      return null;
    }

    // Create new day tab for this run
    const newTab = createDayTab(started.session_id, dayType, started.current_time);
    setTabs((t) => addOrUpdateTab(t, newTab));
    setActiveTabId(newTab.id);
    activeTabIdRef.current = newTab.id;

    setIsBusy(true);
    setErrorMessage(null);

    return new Promise<SimulationApiState | null>((resolve) => {
      const cleanup = subscribeSimulationStream(
        started.session_id,
        (payload) => {
          setActiveAgentNode(payload.node);
          startTransition(() => {
            setSimulation((current) => mergeAgentUpdate(current, payload));
          });
        },
        (snapshot) => {
          startTransition(() => {
            setSimulation((current) => mergeSimulationSnapshot(current, snapshot));
          });
        },
        (message) => {
          setErrorMessage(message);
          setActiveAgentNode(null);
          setIsBusy(false);
          streamCleanupRef.current = null;
          resolve(null);
        },
        () => {
          setActiveAgentNode(null);
          setIsBusy(false);
          streamCleanupRef.current = null;
          resolve(started);
        },
        undefined,
        {
          onAgentStart: (node, timestamp) => {
            const tabId = activeTabIdRef.current;
            if (!tabId) return;
            setTabs((t) => handleAgentStartFn(t, tabId, node, timestamp));
          },
          onAgentToken: (node, token) => {
            const tabId = activeTabIdRef.current;
            if (!tabId) return;
            setTabs((t) => handleAgentTokenFn(t, tabId, node, token));
          },
          onAgentComplete: (node, trace) => {
            const tabId = activeTabIdRef.current;
            if (!tabId) return;
            setTabs((t) => handleAgentCompleteFn(t, tabId, node, trace));
          },
        },
      );
      streamCleanupRef.current = cleanup;
    });
  }

  async function handleDayTypeChange(dayType: SimulationDayType) {
    setSelectedDayType(dayType);
    setTimeRange({ start: null, end: null });
    setSimulation(createSimulationViewModel(dayType));
    setErrorMessage(null);
    setScenarioMetadata(null);
    setMetadataLoading(true);
    try {
      const metadata = await fetchScenarioMetadata(dayType);
      setScenarioMetadata(metadata);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to load scenario metadata.";
      setErrorMessage(message);
    } finally {
      setMetadataLoading(false);
    }
  }

  async function runOptimization() {
    await bootstrapSimulation(selectedDayType, bessCapacityKwh, batterySoc, timeRange, forecastModel);
  }

  const canRun = !isBusy && timeRange.start !== null && timeRange.end !== null;

  const selectTab = useCallback((id: string) => {
    setActiveTabId(id);
    activeTabIdRef.current = id;
  }, []);

  const closeTab = useCallback((id: string) => {
    setTabs((t) => closeTabFn(t, id));
    setActiveTabId((current) => {
      if (current !== id) return current;
      const remaining = tabs.filter((t) => t.id !== id || t.pinned);
      return remaining.length > 0 ? remaining[remaining.length - 1].id : null;
    });
  }, [tabs]);

  const togglePinTab = useCallback((id: string) => {
    setTabs((t) => togglePinTabFn(t, id));
  }, []);

  return {
    dayOptions,
    selectedDayType,
    forecastModel,
    setForecastModel,
    bessCapacityKwh,
    setBessCapacityKwh,
    batterySoc,
    setBatterySoc,
    simulation,
    isBusy,
    errorMessage,
    activeAgentNode,
    handleDayTypeChange,
    runOptimization,
    timeRange,
    setTimeRange,
    scenarioMetadata,
    metadataLoading,
    canRun,
    tabs,
    activeTabId,
    selectTab,
    closeTab,
    togglePinTab,
  };
}
