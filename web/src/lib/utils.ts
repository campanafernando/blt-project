import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error.trim() || "Could not complete the request.";
  if (Array.isArray(error)) return error.map(errorMessage).join(" ");
  if (error && typeof error === "object") {
    return Object.values(error).map(errorMessage).join(" ");
  }
  return "Could not complete the request. Try again.";
}

const dateFormatter = new Intl.DateTimeFormat("en-GB", {
  day: "2-digit",
  month: "short",
  year: "numeric",
});

export function formatDate(value: string | null): string {
  if (!value) return "—";
  return dateFormatter.format(new Date(`${value}T12:00:00`));
}

const shortDateFormatter = new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short" });

export type DueCaption = { text: string; tone: "overdue" | "soon" | "muted" };

/** Short note under the due date. Day maths use local dates at noon, like formatDate, so DST
 *  and time of day never shift the count. */
export function dueCaption(
  task: { status: string; due_date: string | null; completed_at: string | null },
  today: Date = new Date(),
): DueCaption | null {
  if (task.status === "done") {
    if (!task.completed_at) return null;
    const completed = shortDateFormatter.format(new Date(task.completed_at));
    return { text: `Completed ${completed}`, tone: "muted" };
  }
  if (!task.due_date) return null;
  const due = new Date(`${task.due_date}T12:00:00`);
  const now = new Date(today.getFullYear(), today.getMonth(), today.getDate(), 12);
  const days = Math.round((due.getTime() - now.getTime()) / 86_400_000);
  if (days < 0) {
    const late = -days;
    return { text: `${late} ${late === 1 ? "day" : "days"} overdue`, tone: "overdue" };
  }
  if (days === 0) return { text: "Due today", tone: "soon" };
  if (days === 1) return { text: "Due tomorrow", tone: "soon" };
  return null;
}

export function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}
