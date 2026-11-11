import { apiFetch } from "@/lib/api";
import type {
  Paginated,
  Spec,
  SpecConfig,
  SpecTasksRequest,
  SpecTasksResponse,
} from "@/lib/types";

export function getSpecConfig() {
  return apiFetch<SpecConfig>("/specs/config/");
}

export function listSpecs() {
  return apiFetch<Paginated<Spec>>("/specs/?page_size=10");
}

export function createSpec(issueUrl: string) {
  return apiFetch<Spec>("/specs/", {
    method: "POST",
    body: JSON.stringify({ issue_url: issueUrl }),
  });
}

export function publishSpec(id: number) {
  return apiFetch<Spec>(`/specs/${id}/publish/`, { method: "POST" });
}

export function createSpecTasks(specId: number, payload: SpecTasksRequest) {
  return apiFetch<SpecTasksResponse>(`/specs/${specId}/tasks/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
