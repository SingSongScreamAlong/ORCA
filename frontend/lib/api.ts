// Client for the ORCA backend API.
//
// Server components call the `get*` helpers to render evidence; client components use
// the mutating helpers (intake, decide, create) for analyst actions. The frontend
// holds no authority of its own — it renders what the backend returns and records
// analyst decisions the backend validates and audits.

import type {
  AuditEntry,
  Case,
  CaseDetail,
  CaseMember,
  Cluster,
  CurrentUser,
  DashboardSummary,
  Entity,
  EvidenceDecision,
  EvidenceItem,
  EvidenceVerifyResult,
  Observation,
  Relationship,
  ReviewDecision,
  ReviewItem,
  Report,
  Source,
  TimelineEvent,
  User,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";

export type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: string; status?: number };

/**
 * The acting user's header. The dev user switcher stores the username in the
 * `orca_user` cookie; we forward it as `X-ORCA-User` for both server-component reads
 * and client-component mutations so authorization is consistent.
 */
async function userHeaders(): Promise<Record<string, string>> {
  if (typeof window === "undefined") {
    try {
      // Dynamic import keeps the server-only `next/headers` out of client bundles.
      const { cookies } = await import("next/headers");
      const u = cookies().get("orca_user")?.value;
      return u ? { "X-ORCA-User": u } : {};
    } catch {
      return {};
    }
  }
  const m = typeof document !== "undefined"
    ? document.cookie.match(/(?:^|;\s*)orca_user=([^;]+)/)
    : null;
  return m ? { "X-ORCA-User": decodeURIComponent(m[1]) } : {};
}

async function apiGet<T>(path: string): Promise<ApiResult<T>> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      cache: "no-store",
      headers: { ...(await userHeaders()) },
    });
    if (!res.ok) {
      return { ok: false, status: res.status, error: `Backend responded ${res.status} for ${path}` };
    }
    return { ok: true, data: (await res.json()) as T };
  } catch {
    return {
      ok: false,
      error: `Could not reach the ORCA backend at ${API_BASE}. Is it running?`,
    };
  }
}

async function apiSend<T>(
  path: string,
  method: "POST",
  body: unknown,
): Promise<ApiResult<T>> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      method,
      headers: { "content-type": "application/json", ...(await userHeaders()) },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      let detail = `Request failed (${res.status}).`;
      try {
        const j = await res.json();
        if (j?.detail) detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
      } catch {
        /* ignore */
      }
      return { ok: false, status: res.status, error: detail };
    }
    return { ok: true, data: (await res.json()) as T };
  } catch {
    return { ok: false, error: `Could not reach the ORCA backend at ${API_BASE}.` };
  }
}

// --- reads ---------------------------------------------------------------------

export const getDashboard = () => apiGet<DashboardSummary>("/dashboard/summary");
export const getObservations = () => apiGet<Observation[]>("/observations");
export const getEntities = () => apiGet<Entity[]>("/entities");
export const getRelationships = () => apiGet<Relationship[]>("/relationships");
export const getClusters = () => apiGet<Cluster[]>("/clusters");
export const getReviewQueue = (status = "proposed") =>
  apiGet<ReviewItem[]>(`/review?status=${status}`);
export const getSources = () => apiGet<Source[]>("/sources");
export const getEvidenceList = () => apiGet<EvidenceItem[]>("/evidence");
export const getCaseEvidence = (id: string) => apiGet<EvidenceItem[]>(`/cases/${id}/evidence`);

export const getCases = () => apiGet<Case[]>("/cases");
export const getCase = (id: string) => apiGet<CaseDetail>(`/cases/${id}`);
export const getCaseObservations = (id: string) =>
  apiGet<Observation[]>(`/cases/${id}/observations`);
export const getCaseRelationships = (id: string) =>
  apiGet<Relationship[]>(`/cases/${id}/relationships`);
export const getCaseTimeline = (id: string) => apiGet<TimelineEvent[]>(`/cases/${id}/timeline`);
export const getCaseAudit = (id: string) => apiGet<AuditEntry[]>(`/cases/${id}/audit`);
export const getCaseReports = (id: string) => apiGet<Report[]>(`/cases/${id}/reports`);
export const getCaseMembers = (id: string) => apiGet<CaseMember[]>(`/cases/${id}/members`);

export const getMe = () => apiGet<CurrentUser>("/me");
export const getUsers = () => apiGet<User[]>("/users");
export const getPublishedReports = () => apiGet<Report[]>("/reports/published");
export const getReport = (id: string) => apiGet<Report>(`/reports/${id}`);

// --- mutations (browser-side analyst actions) ----------------------------------

export const decideReview = (
  itemId: string,
  decision: ReviewDecision,
  note?: string,
  override = false,
) => apiSend<ReviewItem>(`/review/${itemId}/decision`, "POST", { decision, note, override });

export const assignMember = (caseId: string, username: string) =>
  apiSend<CaseMember>(`/cases/${caseId}/members`, "POST", { username });

export const publishReport = (reportId: string) =>
  apiSend<Report>(`/reports/${reportId}/publish`, "POST", {});

export const createCase = (body: {
  title: string;
  owner: string;
  summary?: string;
  legal_notes?: string;
}) => apiSend<Case>("/cases", "POST", body);

export const generateReport = (caseId: string) =>
  apiSend<Report>(`/cases/${caseId}/report`, "POST", {});

export const createEntity = (body: { entity_type: string; value: string; confidence?: number }) =>
  apiSend<Entity>("/entities", "POST", body);

export const createRelationship = (body: {
  case_id?: string;
  source_entity_id: string;
  target_entity_id: string;
  relationship_type: string;
  confidence?: number;
  observation_ids: string[];
}) => apiSend<Relationship>("/relationships", "POST", body);

export interface EvidenceCreateBody {
  case_id: string;
  source_id: string;
  observation_id?: string;
  title: string;
  description?: string;
  evidence_type: string;
  storage_uri?: string;
  original_filename?: string;
  mime_type?: string;
  sha256?: string;
  captured_by?: string;
  access_method?: string;
  legal_flags?: {
    lawful_basis?: string;
    requires_legal_review?: boolean;
    sensitive?: boolean;
    partner_approved?: boolean;
  };
  handling_notes?: string;
  content_text?: string;
}

export const createEvidence = (body: EvidenceCreateBody) =>
  apiSend<EvidenceItem>("/evidence", "POST", body);

export const decideEvidence = (
  evidenceId: string,
  decision: EvidenceDecision,
  note?: string,
  override = false,
) => apiSend<EvidenceItem>(`/evidence/${evidenceId}/decision`, "POST", { decision, note, override });

export const verifyEvidence = (evidenceId: string) =>
  apiSend<EvidenceVerifyResult>(`/evidence/${evidenceId}/verify`, "POST", {});

export interface IntakeBody {
  case_id?: string;
  timestamp: string;
  source_id?: string;
  source?: {
    source_type: string;
    name: string;
    identifier?: string;
    reliability: string;
    description?: string;
  };
  collector: string;
  location?: string;
  notes?: string;
  confidence: number;
  entity_ids: string[];
  handling: {
    lawful_basis?: string;
    requires_legal_review: boolean;
    sensitive: boolean;
    notes?: string;
  };
}

export const intakeObservation = (body: IntakeBody) =>
  apiSend<Observation>("/observations", "POST", body);
