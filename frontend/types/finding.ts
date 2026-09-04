import type { Severity, FindingStatus } from './api';

export interface Finding {
  id: string;
  job_id: string;
  title: string;
  description: string;
  severity: Severity;
  status: FindingStatus;
  cwe_id?: string;
  cve_id?: string;
  file_path: string;
  line_start: number;
  line_end: number;
  rule_id: string;
  scanner: string;
  raw_output?: string;
  patch?: Patch;
  created_at: string;
  updated_at: string;
}

export interface Patch {
  id: string;
  finding_id: string;
  original_code: string;
  patched_code: string;
  diff: string;
  language: string;
  applied: boolean;
  applied_at?: string;
  validated: boolean;
  validation_score?: number;
  explanation?: string;
}

export interface FindingGroup {
  severity: Severity;
  count: number;
  findings: Finding[];
}
