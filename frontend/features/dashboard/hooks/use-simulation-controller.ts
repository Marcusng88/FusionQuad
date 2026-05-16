"use client";

import {
  startTransition,
  useCallback,
  useRef,
  useState,
} from "react";

import { DAY_SCENARIOS } from "../data/day-scenarios";
import {
  createSimulationViewModel,
  mergeSimulationSnapshot,
} from "../lib/live-simulation";
import {
  startSimulation,
  subscribeSimulationStream,
} from "../lib/simulation-api";
import type {
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
  const [bessCapacityKwh, setBessCapacityKwh] = useState(1000);
  const [timeRange, setTimeRange] = useState<{ start: string | null; end: string | null }>({
    start: null,
    end: null,
  });
  const [simulation, setSimulation] = useState<SimulationViewModel>(() =>
    createSimulationViewModel("weekday"),
  );
  const [isBusy, setIsBusy] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [activeAgentNode, setActiveAgentNode] = useState<string | null>(null);
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
    range?: { start: string | null; end: string | null },
  ) {
    // Cancel any in-flight stream before starting a new one
    streamCleanupRef.current?.();
    streamCleanupRef.current = null;

    const started = await applySnapshot(
      () =>
        startSimulation({
          dayType,
          bessCapacityKwh: capacityKwh,
          batterySoc: 0.5,
          startTime: range?.start,
          endTime: range?.end,
        }),
      true,
      dayType,
    );

    if (!started) {
      return null;
    }

    setIsBusy(true);
    setErrorMessage(null);

    return new Promise<SimulationApiState | null>((resolve) => {
      const cleanup = subscribeSimulationStream(
        started.session_id,
        (node) => {
          setActiveAgentNode(node);
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
      );
      streamCleanupRef.current = cleanup;
    });
  }

  function handleDayTypeChange(dayType: SimulationDayType) {
    setSelectedDayType(dayType);
    setTimeRange({ start: null, end: null });
  }

  async function handleTimeRangeChange(range: { start: string | null; end: string | null }) {
    setTimeRange(range);
    if (simulation.sessionId) {
      await applySnapshot(
        () =>
          startSimulation({
            dayType: selectedDayType,
            bessCapacityKwh: bessCapacityKwh,
            batterySoc: 0.5,
            startTime: range.start,
            endTime: range.end,
          }),
        true,
        selectedDayType,
      );
    }
  }

  async function runOptimization() {
    await bootstrapSimulation(selectedDayType, bessCapacityKwh, timeRange);
  }

  function applySizingRecommendation() {
    const recommended =
      simulation.sizingRecommendation?.recommended_bess_capacity_kwh;
    if (recommended) {
      setBessCapacityKwh(recommended);
    }
  }

  return {
    dayOptions,
    selectedDayType,
    bessCapacityKwh,
    setBessCapacityKwh,
    simulation,
    isBusy,
    errorMessage,
    activeAgentNode,
    applySizingRecommendation,
    handleDayTypeChange,
    handleTimeRangeChange,
    runOptimization,
    timeRange,
    setTimeRange,
  };
}
