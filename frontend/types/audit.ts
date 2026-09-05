import type { GateStatus, Severity } from './api';

export interface AuditDossier {
  id: string;
  job_id: string;
  generated_at: string;
  overall_score: number;
  security_oracle: SecurityOracle;
  regression_results: RegressionResult[];
  post_scan_results: PostScanResult;
  integrity_results: IntegrityResult;
  security_gates: SecurityGate[];
  summary: AuditSummary;
}

export interface SecurityOracle {
  id: string;
  dossier_id: string;
  verdict: 'approved' | 'rejected' | 'needs_review';
  confidence: number;
  reasoning: string;
  risk_level: Severity;
  recommendations: string[];
  evaluated_at: string;
}

export interface RegressionResult {
  id: string;
  test_name: string;
  test_suite: string;
  status: 'passed' | 'failed' | 'skipped' | 'error';
  duration_ms: number;
  error_message?: string;
  before_status?: string;
  after_status?: string;
  is_regression: boolean;
}

export interface PostScanResult {
  scanner: string;
  scanned_at: string;
  total_findings: number;
  new_findings: number;
  resolved_findings: number;
  net_delta: number;
  findings_by_severity: Record<string, number>;
  scan_passed: boolean;
}

export interface IntegrityResult {
  checks_total: number;
  checks_passed: number;
  checks_failed: number;
  file_hash_valid: boolean;
  signature_valid: boolean;
  dependency_scan_clean: boolean;
  secret_scan_clean: boolean;
  integrity_score: number;
  issues: IntegrityIssue[];
}

export interface IntegrityIssue {
  check_name: string;
  severity: Severity;
  message: string;
  file_path?: string;
}

export interface SecurityGate {
  id: string;
  name: string;
  description: string;
  status: GateStatus;
  required: boolean;
  blocking: boolean;
  evaluated_at?: string;
  message?: string;
}

export interface AuditSummary {
  total_vulnerabilities_found: number;
  vulnerabilities_patched: number;
  vulnerabilities_failed: number;
  patch_success_rate: number;
  regression_tests_run: number;
  regression_tests_passed: number;
  security_gates_passed: number;
  security_gates_total: number;
  time_to_remediate_seconds: number;
}
