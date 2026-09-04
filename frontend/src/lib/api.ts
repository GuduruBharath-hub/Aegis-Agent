export type FinalDecision =
  | "verified"
  | "escalated"
  | "policy_rejected"
  | "failed";

export type JobState =
  | "received"
  | "scanning"
  | "finding_identified"
  | "reproducing"
  | "reproduced"
  | "context_building"
  | "generating_patch"
  | "validating_patch"
  | "sandboxing"
  | "verifying_security"
  | "verifying_regression"
  | "post_scanning"
  | "integrity_check"
  | "retrying"
  | "verified"
  | "creating_pr"
  | "completed"
  | "escalated"
  | "policy_rejected"
  | "failed";

export interface Finding {
  id: string;
  cwe: string;
  category: string;
  severity: string;
  file: string;
  line: number;
  symbol: string;
  scanner: string;
  message: string;
}

export interface Job {
  id: string;
  repository: string;
  repository_url: string;
  base_sha: string;
  mode: "demo" | "live";
  scenario: string | null;
  state: JobState;
  current_attempt: number;
  max_attempts: number;
  sandbox_tier: string | null;
  final_decision: FinalDecision | null;
  final_reason: string | null;
  branch_name: string | null;
  pr_url: string | null;
  pr_number: number | null;
  finding: Finding | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface JobRef {
  job_id: string;
  status: JobState;
  stream_url: string;
}

export interface JobCreate {
  repository_url: string;
  commit_sha?: string;
  mode?: "demo" | "live";
  scenario?: string;
}

export interface JobEvent {
  seq: number;
  job_id: string;
  ts: string;
  type: string;
  severity: "info" | "success" | "warning" | "critical";
  attempt: number | null;
  title: string;
  message: string | null;
  data: Record<string, unknown> | null;
}

export interface AttemptSummary {
  attempt: number;
  model: string | null;
  decision: "in_progress" | "rejected" | "verified";
  summary: string | null;
  files_changed: number | null;
  lines_added: number | null;
  lines_removed: number | null;
  failure_gate: string | null;
  failure_reason: string | null;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
}

export interface GateResult {
  passed?: boolean;
  reason?: string;
  [key: string]: unknown;
}

export interface LineRationale {
  path: string;
  changed_lines: number[];
  change_kind:
    | "parameterize"
    | "escape"
    | "allowlist"
    | "argv"
    | "guard"
    | "reorder"
    | "other";
  why: string;
  earns: string;
}

export interface PatchRationale {
  vulnerability_mechanism: string;
  fix_mechanism: string;
  line_rationales: LineRationale[];
  behaviour_preservation: Array<{
    behaviour: string;
    preserved_by: string;
    proven_by: string;
  }>;
  rejected_alternatives: Array<{ approach: string; why_not: string }>;
  residual_risk: string[];
  reviewer_must_confirm: string[];
}

export interface AttemptDetail extends AttemptSummary {
  diff: string | null;
  gates: Record<
    "policy" | "security" | "regression" | "post_scan" | "integrity" | "explain",
    GateResult
  >;
  rationale: PatchRationale | null;
  raw: Record<"pytest" | "bandit" | "harness", string | null>;
  tree_hash_pre: string | null;
  tree_hash_post: string | null;
}

interface ErrorEnvelope {
  error: {
    kind: "technical" | "policy" | "escalation" | "reproduction" | "validation";
    code: string;
    message: string;
    job_id: string | null;
    retryable: boolean;
  };
}

export class ApiClientError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly detail?: ErrorEnvelope["error"],
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

export function listJobs(signal?: AbortSignal): Promise<Job[]> {
  return request<Job[]>("/api/jobs", { signal });
}

export function getJob(jobId: string, signal?: AbortSignal): Promise<Job> {
  return request<Job>(`/api/jobs/${encodeURIComponent(jobId)}`, { signal });
}

export function getJobEvents(
  jobId: string,
  after = 0,
  signal?: AbortSignal,
): Promise<JobEvent[]> {
  return request<JobEvent[]>(
    `/api/jobs/${encodeURIComponent(jobId)}/events?after=${after}`,
    { signal },
  );
}

export function listJobAttempts(
  jobId: string,
  signal?: AbortSignal,
): Promise<AttemptSummary[]> {
  return request<AttemptSummary[]>(
    `/api/jobs/${encodeURIComponent(jobId)}/attempts`,
    { signal },
  );
}

export function getJobAttempt(
  jobId: string,
  attempt: number,
  signal?: AbortSignal,
): Promise<AttemptDetail> {
  return request<AttemptDetail>(
    `/api/jobs/${encodeURIComponent(jobId)}/attempts/${attempt}`,
    { signal },
  );
}

export function createJob(payload: JobCreate): Promise<JobRef> {
  return request<JobRef>("/api/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function startDemo(scenario: string): Promise<JobRef> {
  return request<JobRef>(`/api/demo/${encodeURIComponent(scenario)}`, {
    method: "POST",
  });
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { Accept: "application/json", ...init?.headers },
    cache: "no-store",
  });
  if (response.ok) {
    return (await response.json()) as T;
  }

  let detail: ErrorEnvelope["error"] | undefined;
  try {
    const envelope = (await response.json()) as ErrorEnvelope;
    detail = envelope.error;
  } catch {
    // A proxy failure may not use the backend envelope; preserve its HTTP status.
  }
  throw new ApiClientError(
    detail?.message ?? `API request failed with HTTP ${response.status}`,
    response.status,
    detail,
  );
}
