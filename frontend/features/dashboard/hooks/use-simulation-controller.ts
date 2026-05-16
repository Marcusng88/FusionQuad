"use client";

import {
  startTransition,
  useCallback,
  useEffect,
  useEffectEvent,
  useMemo,
  useState,
} from "react";

import {
  DAY_SCENARIOS,
  PLAYBACK_SPEEDS,
  type PlaybackSpeedLabel,
} from "../data/day-scenarios";
import {
  createSimulationViewModel,
  mergeSimulationSnapshot,
} from "../lib/live-simulation";
import {
  getSimulationState,
  pauseSimulation,
  playSimulation,
  startSimulation,
  stepSimulation,
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
  const [playbackSpeed, setPlaybackSpeed] =
    useState<PlaybackSpeedLabel>("10x");
  const [timeRange, setTimeRange] = useState<{ start: string | null; end: string | null }>({
    start: null,
    end: null,
  });
  const [simulation, setSimulation] = useState<SimulationViewModel>(() =>
    createSimulationViewModel("weekday"),
  );
  const [isBusy, setIsBusy] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const dayOptions = resolveDayOptions(simulation.scenarios);

  const speed = useMemo(
    () =>
      PLAYBACK_SPEEDS.find((item) => item.label === playbackSpeed) ??
      PLAYBACK_SPEEDS[1],
    [playbackSpeed],
  );

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

  const pollSimulationState = useEffectEvent(async (sessionId: string) => {
    await applySnapshot(() => getSimulationState(sessionId));
  });

  async function bootstrapSimulation(
    dayType = selectedDayType,
    capacityKwh = bessCapacityKwh,
    timeRange?: { start: string | null; end: string | null },
  ) {
    const started = await applySnapshot(
      () =>
        startSimulation({
          dayType,
          bessCapacityKwh: capacityKwh,
          batterySoc: 0.5,
          startTime: timeRange?.start,
          endTime: timeRange?.end,
        }),
      true,
      dayType,
    );

    if (!started) {
      return null;
    }

    const stepped = await applySnapshot(
      () => stepSimulation(started.session_id),
      false,
      dayType,
    );

    return stepped ?? started;
  }

  async function handleDayTypeChange(dayType: SimulationDayType) {
    setSelectedDayType(dayType);
    await bootstrapSimulation(dayType, bessCapacityKwh, timeRange);
  }

  async function handleTimeRangeChange(range: { start: string | null; end: string | null }) {
    setTimeRange(range);
    if (simulation.sessionId) {
      const snapshot = await applySnapshot(
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
      void snapshot;
    }
  }

  async function runOptimization() {
    await bootstrapSimulation();
  }

  async function stepForward() {
    if (!simulation.sessionId) {
      await bootstrapSimulation();
      return;
    }

    await applySnapshot(() => stepSimulation(simulation.sessionId!));
  }

  async function play() {
    let sessionId = simulation.sessionId;
    if (!sessionId) {
      const snapshot = await bootstrapSimulation();
      sessionId = snapshot?.session_id ?? null;
    }

    if (!sessionId) {
      return;
    }

    await applySnapshot(() => playSimulation(sessionId!, speed.intervalMs));
  }

  async function pause() {
    if (!simulation.sessionId) {
      return;
    }

    await applySnapshot(() => pauseSimulation(simulation.sessionId!));
  }

  function applySizingRecommendation() {
    const recommended =
      simulation.sizingRecommendation?.recommended_bess_capacity_kwh;
    if (recommended) {
      setBessCapacityKwh(recommended);
    }
  }

  useEffect(() => {
    if (simulation.status !== "playing" || !simulation.sessionId) {
      return;
    }

    const intervalId = window.setInterval(() => {
      void pollSimulationState(simulation.sessionId!);
    }, speed.intervalMs);

    return () => window.clearInterval(intervalId);
  }, [simulation.status, simulation.sessionId, speed.intervalMs]);

  return {
    dayOptions,
    selectedDayType,
    bessCapacityKwh,
    setBessCapacityKwh,
    playbackSpeed,
    setPlaybackSpeed,
    simulation,
    isBusy,
    errorMessage,
    applySizingRecommendation,
    handleDayTypeChange,
    handleTimeRangeChange,
    runOptimization,
    stepForward,
    play,
    pause,
    timeRange,
    setTimeRange,
  };
}
