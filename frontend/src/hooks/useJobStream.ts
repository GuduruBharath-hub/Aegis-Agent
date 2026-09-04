"use client";

import { useEffect, useRef, useState } from "react";

import { getJobEvents, type JobEvent } from "@/lib/api";

export type StreamStatus = "connecting" | "live" | "reconnecting" | "closed";

export interface JobStreamState {
  events: JobEvent[];
  status: StreamStatus;
  error: string | null;
}

const EVENT_TYPES = [
  "job_created",
  "state_changed",
  "scan_started",
  "scan_completed",
  "finding_detected",
  "reproduction_started",
  "reproduction_confirmed",
  "context_built",
  "injection_detected",
  "technical_error",
  "patch_generated",
  "policy_passed",
  "policy_failed",
  "sandbox_started",
  "sandbox_completed",
  "security_passed",
  "security_failed",
  "regression_passed",
  "regression_failed",
  "post_scan_passed",
  "post_scan_failed",
  "integrity_passed",
  "integrity_failed",
  "explain_passed",
  "explain_failed",
  "candidate_rejected",
  "verified",
] as const;

const TERMINAL_STATES = new Set([
  "completed",
  "escalated",
  "policy_rejected",
  "failed",
]);

export function useJobStream(
  jobId: string,
  onEvent?: (event: JobEvent) => void,
): JobStreamState {
  const [state, setState] = useState<JobStreamState>({
    events: [],
    status: "connecting",
    error: null,
  });
  const onEventRef = useRef(onEvent);

  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    const controller = new AbortController();
    let source: EventSource | null = null;
    let disposed = false;

    async function connect() {
      setState({ events: [], status: "connecting", error: null });
      try {
        const history = await getJobEvents(jobId, 0, controller.signal);
        if (disposed) return;

        let lastSequence = history.at(-1)?.seq ?? 0;
        if (history.some(isTerminalStateEvent)) {
          setState({ events: history, status: "closed", error: null });
          return;
        }
        setState({ events: history, status: "connecting", error: null });
        source = new EventSource(
          `/api/jobs/${encodeURIComponent(jobId)}/stream?after=${lastSequence}`,
        );
        source.onopen = () => {
          setState((current) => ({ ...current, status: "live", error: null }));
        };
        const receive = (message: MessageEvent<string>) => {
          const event = JSON.parse(message.data) as JobEvent;
          if (event.seq <= lastSequence) return;
          lastSequence = event.seq;
          setState((current) => ({
            ...current,
            events: [...current.events, event],
          }));
          onEventRef.current?.(event);
          if (
            isTerminalStateEvent(event)
          ) {
            source?.close();
            setState((current) => ({ ...current, status: "closed" }));
          }
        };
        for (const eventType of EVENT_TYPES) {
          source.addEventListener(eventType, receive as EventListener);
        }
        source.onerror = () => {
          if (disposed) return;
          setState((current) => ({
            ...current,
            status: source?.readyState === EventSource.CLOSED ? "closed" : "reconnecting",
            error:
              source?.readyState === EventSource.CLOSED
                ? "Event stream closed"
                : "Connection interrupted; retrying",
          }));
        };
      } catch (error) {
        if (disposed || controller.signal.aborted) return;
        setState({
          events: [],
          status: "closed",
          error: error instanceof Error ? error.message : "Unable to load events",
        });
      }
    }

    void connect();
    return () => {
      disposed = true;
      controller.abort();
      source?.close();
    };
  }, [jobId]);

  return state;
}

function isTerminalStateEvent(event: JobEvent): boolean {
  return (
    event.type === "state_changed" &&
    TERMINAL_STATES.has(String(event.data?.state))
  );
}
