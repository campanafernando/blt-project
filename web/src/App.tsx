import { useState } from "react";
import { FileText, ListTodo, LogOut } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Loading } from "@/components/ui/feedback";
import { LoginPage } from "@/features/auth/LoginPage";
import { SpecsPage } from "@/features/specs/SpecsPage";
import { TaskBoard } from "@/features/tasks/TaskBoard";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

type View = "tasks" | "specs";

export default function App() {
  const { user, loading, logout } = useAuth();
  const [view, setView] = useState<View>("tasks");

  if (loading) {
    return (
      <div className="grid min-h-dvh place-items-center">
        <Loading label="Carregando sessão…" />
      </div>
    );
  }

  if (!user) return <LoginPage />;

  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-10 border-b border-border bg-background/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <a className="flex items-baseline gap-2.5" href="/">
            <span className="rounded-lg bg-foreground px-2.5 py-0.5 font-display text-lg font-bold tracking-tight text-white">
              BLT
            </span>
            <span className="text-xs text-muted-foreground">Backlog, Lists &amp; Tasks</span>
          </a>

          <nav className="flex flex-wrap items-center gap-1 text-sm">
            <button
              type="button"
              onClick={() => setView("tasks")}
              className={cn(
                "inline-flex items-center gap-2 rounded-lg px-3 py-2 transition",
                view === "tasks"
                  ? "bg-muted font-medium text-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              <ListTodo className="size-4" />
              Tarefas
            </button>
            <button
              type="button"
              onClick={() => setView("specs")}
              className={cn(
                "inline-flex items-center gap-2 rounded-lg px-3 py-2 transition",
                view === "specs"
                  ? "bg-muted font-medium text-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              <FileText className="size-4" />
              Spec
            </button>
            <a
              className="ml-2 text-muted-foreground hover:text-foreground"
              href="/app/"
            >
              HTMX
            </a>
            <a
              className="text-muted-foreground hover:text-foreground"
              href="/api/docs/"
              target="_blank"
              rel="noreferrer"
            >
              API
            </a>
            <span className="mx-1 hidden text-muted-foreground sm:inline">
              {user.first_name || user.username}
            </span>
            <Button variant="ghost" size="sm" onClick={logout}>
              <LogOut />
              Sair
            </Button>
          </nav>
        </div>
      </header>
      {view === "tasks" ? <TaskBoard /> : <SpecsPage />}
    </div>
  );
}
