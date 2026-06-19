// Thin client for the ORCA backend API.
//
// Server components call `apiGet` to render evidence; the review screen uses
// `decideReview` from the browser. The frontend holds no authority of its own — it
// renders what the backend returns and records analyst decisions the backend audits.

import type {
  Cluster,
  DashboardSummary,
  Entity,
  Evidence,
  Observation,
  Relationship,
  ReviewDecision,
  ReviewItem,
  Source,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";

/** Result of a fetch: either data, or a reason the backend could not be reached. */
export type ApiResult<T> = { ok: true; data: T } | { ok: false; error: string };

async function apiGet<T>(path: string): Promise<ApiResult<T>> {
  try {
    const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
    if (!res.ok) {
      return { ok: false, error: `Backend responded ${res.status} for ${path}` };
    }
    return { ok: true, data: (await res.json()) as T };
  } catch {
    return {
      ok: false,
      error: `Could not reach the ORCA backend at ${API_BASE}. Is it running?`,
    };
  }
}

export const getDashboard = () => apiGet<DashboardSummary>("/dashboard/summary");
export const getObservations = () => apiGet<Observation[]>("/observations");
export const getEntities = () => apiGet<Entity[]>("/entities");
export const getRelationships = () => apiGet<Relationship[]>("/relationships");
export const getClusters = () => apiGet<Cluster[]>("/clusters");
export const getReviewQueue = () => apiGet<ReviewItem[]>("/review");
export const getSources = () => apiGet<Source[]>("/sources");
export const getEvidenceList = () => apiGet<Evidence[]>("/evidence");

/** Submit an analyst decision on a review item (browser-side). */
export async function decideReview(
  itemId: string,
  decision: ReviewDecision,
  note?: string,
): Promise<ApiResult<ReviewItem>> {
  try {
    const res = await fetch(`${API_BASE}/review/${itemId}/decision`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ decision, note }),
    });
    if (!res.ok) {
      return { ok: false, error: `Decision failed (${res.status}).` };
    }
    return { ok: true, data: (await res.json()) as ReviewItem };
  } catch {
    return { ok: false, error: "Could not reach the ORCA backend." };
  }
}
