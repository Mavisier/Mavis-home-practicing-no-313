import type {
  Readiness,
  ReviewTask,
  RunDetail,
  RunSummary,
  Vehicle,
} from "./types";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
    signal: AbortSignal.timeout(55000),
  });
  if (!response.ok) {
    if (response.status === 401)
      throw new Error(
        "Demo bağlantısı yapılandırılmamış. Sunucu token ayarını kontrol edin.",
      );
    if (response.status === 404)
      throw new Error("Bu talep bulunamadı. Listeyi yenileyin.");
    if (response.status === 403)
      throw new Error(
        "İnceleyici kimliği doğrulanamadı. Demo sunucu ayarını kontrol edin.",
      );
    if (response.status === 409)
      throw new Error(
        "Kayıt veya onay durumu değişti. Yeni bir kontrol çalıştırın.",
      );
    if (response.status === 422)
      throw new Error("Talep 3–4000 karakter olmalı.");
    throw new Error(
      "Servise ulaşılamadı. Backend ve veritabanı bağlantısını kontrol edin.",
    );
  }
  return response.json() as Promise<T>;
}

export const api = {
  vehicles: () => request<Vehicle[]>("/api/vehicles"),
  meta: () => request<{ generation: string; embedding: string }>("/api/meta"),
  tasks: () => request<ReviewTask[]>("/api/review-tasks"),
  review: (listing_id: string, workflow: string, request_text: string) =>
    request<RunDetail>("/api/reviews", {
      method: "POST",
      body: JSON.stringify({ listing_id, workflow, request_text }),
    }),
  updateDescription: (id: string, description: string) =>
    request<Vehicle>(`/api/vehicles/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ description }),
    }),
  decide: (id: string, decision: "approve" | "reject") =>
    request(`/api/actions/${id}/${decision}`, { method: "POST" }),
  readiness: () => request<Readiness>("/health/ready"),
  list: () => request<RunSummary[]>("/api/runs"),
  detail: (id: string) => request<RunDetail>(`/api/runs/${id}`),
  create: (request_text: string) =>
    request<RunDetail>("/api/runs", {
      method: "POST",
      body: JSON.stringify({ request_text }),
    }),
};
