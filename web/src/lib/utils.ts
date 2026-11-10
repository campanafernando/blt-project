import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error.trim() || "Não foi possível concluir.";
  if (Array.isArray(error)) return error.map(errorMessage).join(" ");
  if (error && typeof error === "object") {
    return Object.values(error).map(errorMessage).join(" ");
  }
  return "Não foi possível concluir. Tente novamente.";
}

const dateFormatter = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "short",
  year: "numeric",
});

export function formatDate(value: string | null): string {
  if (!value) return "—";
  return dateFormatter.format(new Date(`${value}T12:00:00`));
}

export function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}
