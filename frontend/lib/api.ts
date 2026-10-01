const API_URL = process.env.NEXT_PUBLIC_API_URL;

export type Health = {
  status: "ok" | "degraded";
  database: "ok" | "unavailable";
};

export type Candidate = {
  id: string;
  email: string;
  name: string;
  created_at: string;
};

export type CandidateInput = { name: string; email: string };

export type ResumeStatus = "PROCESSED" | "FAILED" | "UNSUPPORTED";
export type FactCategory = "SKILL" | "PROJECT" | "EXPERIENCE" | "EDUCATION" | "CERTIFICATION";
export type FactStatus = "PENDING_REVIEW" | "APPROVED" | "REJECTED";

export type Resume = {
  id: string;
  candidate_id: string;
  status: ResumeStatus;
  message: string | null;
  page_count: number | null;
  sections: { heading: string; category: FactCategory | null; page: number }[];
  created_at: string;
};

export type Fact = {
  id: string;
  resume_id: string;
  category: FactCategory;
  fact: string;
  extracted_fact: string;
  source: "RESUME";
  source_section: string;
  source_text: string;
  status: FactStatus;
  extracted_by: "RULES" | "AI";
  created_at: string;
};

export type AIExtraction = {
  request_id: string;
  requested_provider: string;
  provider: string;
  model: string;
  fallback_used: boolean;
  attempts: number;
  latency_ms: number;
  input_tokens: number | null;
  output_tokens: number | null;
  total_tokens: number | null;
  facts_added: number;
  facts_already_listed: number;
  facts_rejected: number;
};

export type FactReview = { fact?: string; status?: "APPROVED" | "REJECTED" };

/** status 0 = the request never got a response (network down, backend off, misconfigured). */
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public fieldErrors: Partial<Record<string, string>> = {},
  ) {
    super(message);
  }
}

type ValidationIssue = { loc?: (string | number)[]; msg?: string };

function toApiError(status: number, body: unknown): ApiError {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (status === 422 && Array.isArray(detail)) {
    const fieldErrors: Record<string, string> = {};
    for (const issue of detail as ValidationIssue[]) {
      const field = issue.loc?.[1];
      if (typeof field === "string" && issue.msg) fieldErrors[field] ??= issue.msg;
    }
    return new ApiError(status, "Please fix the highlighted fields.", fieldErrors);
  }
  // 503 details are written for users (DB down, AI unavailable); other 5xx stay generic.
  if (typeof detail === "string" && (status < 500 || status === 503)) {
    return new ApiError(status, detail);
  }
  if (status === 503) return new ApiError(status, "Service temporarily unavailable. Please try again.");
  return new ApiError(status, "Something went wrong on our side. Please try again.");
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (!API_URL) throw new ApiError(0, "App is misconfigured: NEXT_PUBLIC_API_URL is not set.");
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      // FormData bodies must let the browser set the multipart Content-Type (with its boundary).
      headers:
        typeof init.body === "string"
          ? { "Content-Type": "application/json", ...init.headers }
          : init.headers,
      cache: "no-store",
    });
  } catch (err) {
    if (init.signal?.aborted) throw err;
    throw new ApiError(0, "Can't reach the server. Check your connection and try again.");
  }
  if (res.status === 204) return undefined as T;
  const body: unknown = await res.json().catch(() => null);
  if (!res.ok) throw toApiError(res.status, body);
  return body as T;
}

export async function getHealth(signal?: AbortSignal): Promise<Health> {
  if (!API_URL) throw new Error("NEXT_PUBLIC_API_URL is not configured");
  const res = await fetch(`${API_URL}/api/health`, { signal, cache: "no-store" });
  // 503 still carries a well-formed Health body (database unavailable).
  if (!res.ok && res.status !== 503) throw new Error(`Unexpected status ${res.status}`);
  return (await res.json()) as Health;
}

export const createCandidate = (input: CandidateInput) =>
  request<Candidate>("/api/candidates", { method: "POST", body: JSON.stringify(input) });

export const getCandidate = (id: string, signal?: AbortSignal) =>
  request<Candidate>(`/api/candidates/${encodeURIComponent(id)}`, { signal });

export const updateCandidate = (id: string, changes: Partial<CandidateInput>) =>
  request<Candidate>(`/api/candidates/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(changes),
  });

export const deleteCandidate = (id: string) =>
  request<void>(`/api/candidates/${encodeURIComponent(id)}`, { method: "DELETE" });

export function uploadResume(candidateId: string, file: File) {
  const body = new FormData();
  body.append("candidate_id", candidateId);
  body.append("file", file);
  return request<Resume>("/api/resumes", { method: "POST", body });
}

export const listResumes = (candidateId: string, signal?: AbortSignal) =>
  request<Resume[]>(`/api/candidates/${encodeURIComponent(candidateId)}/resumes`, { signal });

export const getResumeFacts = (resumeId: string, signal?: AbortSignal) =>
  request<Fact[]>(`/api/resumes/${encodeURIComponent(resumeId)}/facts`, { signal });

export const reviewFact = (resumeId: string, factId: string, review: FactReview) =>
  request<Fact>(
    `/api/resumes/${encodeURIComponent(resumeId)}/facts/${encodeURIComponent(factId)}`,
    { method: "PATCH", body: JSON.stringify(review) },
  );

export const runAiExtraction = (resumeId: string) =>
  request<AIExtraction>(`/api/resumes/${encodeURIComponent(resumeId)}/ai-extraction`, {
    method: "POST",
  });

export const deleteResume = (resumeId: string) =>
  request<void>(`/api/resumes/${encodeURIComponent(resumeId)}`, { method: "DELETE" });
