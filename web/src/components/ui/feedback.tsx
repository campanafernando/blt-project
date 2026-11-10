import { AlertCircle, LoaderCircle } from "lucide-react";

import { errorMessage } from "@/lib/utils";
import { Button } from "./button";

export function Loading({ label = "Carregando tarefas…" }: { label?: string }) {
  return (
    <div
      role="status"
      className="flex items-center justify-center gap-3 p-10 text-sm text-muted-foreground"
    >
      <LoaderCircle className="size-5 animate-spin" />
      {label}
    </div>
  );
}

export function ErrorState({ error, retry }: { error: unknown; retry?: () => void }) {
  return (
    <div
      role="alert"
      className="flex flex-wrap items-center gap-3 rounded-2xl border border-destructive/20 bg-destructive/5 p-5 text-sm"
    >
      <AlertCircle className="size-5 shrink-0 text-destructive" />
      <p className="min-w-0 flex-1">{errorMessage(error)}</p>
      {retry && (
        <Button variant="outline" onClick={retry}>
          Tentar de novo
        </Button>
      )}
    </div>
  );
}
