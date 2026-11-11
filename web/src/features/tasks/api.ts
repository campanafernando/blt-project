import { apiFetch } from "@/lib/api";
import type { Paginated, Status, Summary, Task, TaskFilters, TaskUser } from "@/lib/types";

export type TaskPayload = {
  title: string;
  description: string;
  due_date: string | null;
  assigned_to: number | null;
  status?: Status;
};

export const PAGE_SIZE = 10;

function queryString(filters: TaskFilters): string {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.due_date_after) params.set("due_date_after", filters.due_date_after);
  if (filters.due_date_before) params.set("due_date_before", filters.due_date_before);
  if (filters.search) params.set("search", filters.search);
  if (filters.overdue) params.set("overdue", "true");
  params.set("page", String(filters.page));
  params.set("page_size", String(PAGE_SIZE));
  return params.toString();
}

export function listTasks(filters: TaskFilters) {
  return apiFetch<Paginated<Task>>(`/tasks/?${queryString(filters)}`);
}

export function getSummary() {
  return apiFetch<Summary>("/tasks/summary/");
}

export function listUsers() {
  return apiFetch<TaskUser[]>("/auth/users/");
}

export function createTask(payload: TaskPayload) {
  return apiFetch<Task>("/tasks/", { method: "POST", body: JSON.stringify(payload) });
}

export function updateTask(id: number, payload: Partial<TaskPayload>) {
  return apiFetch<Task>(`/tasks/${id}/`, { method: "PATCH", body: JSON.stringify(payload) });
}

export function completeTask(id: number) {
  return apiFetch<Task>(`/tasks/${id}/complete/`, { method: "POST" });
}

export function reopenTask(id: number) {
  return apiFetch<Task>(`/tasks/${id}/reopen/`, { method: "POST" });
}

export function deleteTask(id: number) {
  return apiFetch<void>(`/tasks/${id}/`, { method: "DELETE" });
}
