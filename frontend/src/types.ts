export interface RunSummary {
  id: string;
  request_text: string;
  intent: string | null;
  status: string;
  started_at: string;
}

export interface RunEvent {
  sequence: number;
  event_type: string;
  payload_json: Record<string, unknown>;
  created_at: string;
}

export interface RunDetail extends RunSummary {
  final_response_json: Record<string, unknown> | null;
  events: RunEvent[];
  action: {
    id: string;
    tool_name: string;
    arguments_json: Record<string, unknown>;
    status: string;
    result_json: Record<string, unknown> | null;
  } | null;
}

export interface Vehicle {
  id: string;
  title: string;
  scenario: string;
  description: string;
  vehicle: {
    brand: string;
    model: string;
    year: number;
    km: number;
    fuel: string;
    gearbox: string;
    price_try: number | null;
    city: string;
    painted_parts: string[] | null;
    replaced_parts: string[];
    damage_record_try: number | null;
    inspection_days_remaining: number | null;
    spare_key: boolean | null;
    advert_title?: string;
    source?: {
      kind: string;
      url: string;
      listing_id: string;
      captured_at: string;
      photo_angles: string;
      photo_resolution_scope: string;
    };
  };
  photos: {
    angle: string;
    width: number;
    height: number;
    url?: string;
    resolution_scope?: string;
  }[];
}

export interface ReviewResult {
  listing: Vehicle;
  workflow: string;
  verdict: string;
  mode: string;
  embedding_space: string;
  latency_ms: number;
  findings: {
    code: string;
    severity: string;
    title: string;
    detail: string;
    question: string;
    source_id: string;
  }[];
  narrative: { summary: string; seller_message: string; questions: string[] };
  sources: {
    id: string;
    title: string;
    body: string;
    url: string | null;
    kind: string;
    version: string;
  }[];
  error?: string;
}

export interface ReviewTask {
  id: string;
  listing_id: string;
  status: string;
  created_at: string;
}

export interface Readiness {
  status: "ready" | "unavailable";
  database?: string;
  vector_extension?: boolean;
}
