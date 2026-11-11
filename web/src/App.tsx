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

const navItem = (active: boolean) =>
  cn(
    "inline-flex items-center gap-2 rounded-md border px-[11px] py-[7px] font-mono text-[13px] font-medium transition",
    active
      ? "border-border bg-card text-foreground"
      : "border-transparent text-muted-foreground hover:text-foreground",
  );

export default function App() {
  const { user, loading, logout } = useAuth();
  const [view, setView] = useState<View>("tasks");

  if (loading) {
    return (
      <div className="grid min-h-dvh place-items-center">
        <Loading label="Loading session…" />
      </div>
    );
  }

  if (!user) return <LoginPage />;

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-10 border-b border-border bg-background/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <a className="flex items-baseline gap-2.5 hover:no-underline" href="/">
            <span className="rounded-md bg-foreground px-2.5 py-0.5 text-lg font-bold tracking-[-0.02em] text-white">
              BLT
            </span>
            <span className="font-mono text-xs text-muted-foreground">Backlog, Lists &amp; Tasks</span>
          </a>

          <nav className="flex flex-wrap items-center gap-1">
            <button
              type="button"
              onClick={() => setView("tasks")}
              className={navItem(view === "tasks")}
            >
              <ListTodo className="size-4" />
              Tasks
            </button>
            <button
              type="button"
              onClick={() => setView("specs")}
              className={navItem(view === "specs")}
            >
              <FileText className="size-4" />
              Specs
            </button>
            {import.meta.env.DEV && (
              <>
                <a className={cn(navItem(false), "ml-2")} href="/app/">
                  HTMX
                </a>
                <a
                  className={navItem(false)}
                  href="/api/docs/"
                  target="_blank"
                  rel="noreferrer"
                >
                  API
                </a>
              </>
            )}
            <span className="mx-1 hidden font-mono text-[13px] text-muted-foreground sm:inline">
              {user.first_name || user.username}
            </span>
            <Button variant="ghost" size="sm" onClick={logout}>
              <LogOut />
              Sign out
            </Button>
          </nav>
        </div>
      </header>
      <main className="flex-1">{view === "tasks" ? <TaskBoard /> : <SpecsPage />}</main>
      <footer className="bg-footer text-sm text-footer-foreground">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-6 sm:px-6">
          <p>Create, assign and track deadlines.</p>
          <p className="font-mono text-xs">BLT · Backlog, Lists &amp; Tasks</p>
        </div>
      </footer>
    </div>
  );
}
