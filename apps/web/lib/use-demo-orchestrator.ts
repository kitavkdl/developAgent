"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { DemoScenarioId } from "@/types/domain";
import { PLAYBACK_STEP_MS } from "@/types/domain";
import {
  applyResearchEvent,
  createInitialJobView,
  type JobViewModel,
} from "./job-reducer";
import { getResearchClient } from "./research-client";

export function useDemoOrchestrator() {
  const [model, setModel] = useState<JobViewModel>(() => createInitialJobView());
  const [scenario, setScenario] = useState<DemoScenarioId>("miss");
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);
  const unsubscribeRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    return () => {
      unsubscribeRef.current?.();
    };
  }, []);

  const reset = useCallback(() => {
    unsubscribeRef.current?.();
    unsubscribeRef.current = null;
    setSelectedEntityId(null);
    setModel(createInitialJobView());
  }, []);

  const submit = useCallback(
    async (query: string) => {
      const trimmed = query.trim();
      if (!trimmed) return;

      unsubscribeRef.current?.();
      setSelectedEntityId(null);
      setModel({
        ...createInitialJobView(trimmed),
        status: "submitting",
      });

      const client = getResearchClient();
      client.setStepMs?.(PLAYBACK_STEP_MS.slow);

      const { job_id } = await client.createJob({
        query: trimmed,
        scenarioHint: scenario,
      });

      setModel((prev) => ({
        ...prev,
        jobId: job_id,
        status: "streaming",
      }));

      unsubscribeRef.current = client.subscribeEvents(job_id, (event) => {
        setModel((prev) => applyResearchEvent(prev, event));
      });
    },
    [scenario],
  );

  return {
    model,
    scenario,
    setScenario,
    selectedEntityId,
    setSelectedEntityId,
    submit,
    reset,
  };
}
