import type { DemoScenarioId, JobSnapshot } from "@/types/domain";
import type { ResearchEvent } from "@/types/events";
import {
  buildScenarioEvents,
  inferScenarioFromQuery,
} from "./demo-scenarios";

export type Unsubscribe = () => void;

export interface ResearchClient {
  createJob(input: {
    query: string;
    scenarioHint?: DemoScenarioId;
  }): Promise<{ job_id: string }>;
  getJob(jobId: string): Promise<JobSnapshot>;
  subscribeEvents(
    jobId: string,
    onEvent: (event: ResearchEvent) => void,
  ): Unsubscribe;
}

interface StoredJob {
  job_id: string;
  query: string;
  scenario: DemoScenarioId;
  events: ResearchEvent[];
}

export class DummyResearchClient implements ResearchClient {
  private jobs = new Map<string, StoredJob>();
  private stepMs: number;

  constructor(stepMs = 420) {
    this.stepMs = stepMs;
  }

  async createJob(input: {
    query: string;
    scenarioHint?: DemoScenarioId;
  }): Promise<{ job_id: string }> {
    const job_id = `job_${Math.random().toString(36).slice(2, 10)}`;
    const scenario = inferScenarioFromQuery(input.query, input.scenarioHint);
    const events = buildScenarioEvents(job_id, input.query, scenario);
    this.jobs.set(job_id, {
      job_id,
      query: input.query,
      scenario,
      events,
    });
    return { job_id };
  }

  async getJob(jobId: string): Promise<JobSnapshot> {
    const job = this.jobs.get(jobId);
    if (!job) {
      throw new Error(`Unknown job: ${jobId}`);
    }
    return {
      job_id: job.job_id,
      query: job.query,
      status: "streaming",
    };
  }

  subscribeEvents(
    jobId: string,
    onEvent: (event: ResearchEvent) => void,
  ): Unsubscribe {
    const job = this.jobs.get(jobId);
    if (!job) {
      return () => undefined;
    }

    let cancelled = false;
    const timers: ReturnType<typeof setTimeout>[] = [];

    job.events.forEach((event, index) => {
      const timer = setTimeout(() => {
        if (!cancelled) onEvent(event);
      }, index * this.stepMs);
      timers.push(timer);
    });

    return () => {
      cancelled = true;
      for (const timer of timers) clearTimeout(timer);
    };
  }
}

let singleton: ResearchClient | null = null;

export function getResearchClient(): ResearchClient {
  if (!singleton) {
    singleton = new DummyResearchClient();
  }
  return singleton;
}
