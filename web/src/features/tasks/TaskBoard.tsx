import { useEffect, useState } from "react";
import { Plus, SlidersHorizontal } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { ErrorState, Loading } from "@/components/ui/feedback";
import { PageTitle } from "@/components/ui/page-title";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { emptyFilters, type Task, type TaskFilters } from "@/lib/types";
import { TaskDialog } from "./TaskDialog";
import { TaskRow } from "./TaskRow";
import { PAGE_SIZE } from "./api";
import { useDebouncedValue, useDeleteTask, useSummary, useTasks, useUsers } from "./hooks";

export function TaskBoard() {
  const { user } = useAuth();
  const [filters, setFilters] = useState<TaskFilters>(emptyFilters);
  const [searchText, setSearchText] = useState("");
  const debouncedSearch = useDebouncedValue(searchText, 300);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Task | null>(null);
  const [deleting, setDeleting] = useState<Task | null>(null);

  const tasks = useTasks(filters);
  const summary = useSummary();
  const users = useUsers();
  const remove = useDeleteTask();

  function update<K extends keyof TaskFilters>(key: K, value: TaskFilters[K]) {
    setFilters((current) => ({ ...current, [key]: value, page: 1 }));
  }

  useEffect(() => {
    setFilters((current) =>
      current.search === debouncedSearch ? current : { ...current, search: debouncedSearch, page: 1 },
    );
  }, [debouncedSearch]);

  if (!user) return null;

  const totalPages = tasks.data ? Math.max(1, Math.ceil(tasks.data.count / PAGE_SIZE)) : 1;

  return (
    <div className="mx-auto w-full max-w-6xl px-4 pb-16 sm:px-6">
      <header className="flex flex-wrap items-end justify-between gap-4 py-8">
        <div>
          <p className="eyebrow">Dashboard</p>
          <PageTitle>My tasks</PageTitle>
          <p className="mt-1 max-w-xl text-sm text-muted-foreground">
            Create, assign and track deadlines.
          </p>
        </div>
        <Button onClick={() => setCreating(true)}>
          <Plus />
          New task
        </Button>
      </header>

      <section className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-5">
        {[
          ["Total", summary.data?.total],
          ["To do", summary.data?.todo],
          ["In progress", summary.data?.in_progress],
          ["Done", summary.data?.done],
          ["Overdue", summary.data?.overdue],
        ].map(([label, value]) => (
          <div key={String(label)} className="panel px-4 py-3">
            <p className="eyebrow text-[11px]">{label}</p>
            <p className="stat-value mt-2">{value ?? "—"}</p>
          </div>
        ))}
      </section>

      <section className="panel mb-5 p-4">
        <div className="mb-3 flex items-center gap-2 text-muted-foreground">
          <SlidersHorizontal className="size-4" />
          <span className="eyebrow">Filters</span>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <label className="space-y-1.5">
            <span className="eyebrow">Status</span>
            <select
              className="field"
              value={filters.status}
              onChange={(event) => update("status", event.target.value)}
            >
              <option value="">All</option>
              <option value="todo">To do</option>
              <option value="in_progress">In progress</option>
              <option value="done">Done</option>
            </select>
          </label>
          <label className="space-y-1.5">
            <span className="eyebrow">From</span>
            <input
              type="date"
              className="field"
              value={filters.due_date_after}
              onChange={(event) => update("due_date_after", event.target.value)}
            />
          </label>
          <label className="space-y-1.5">
            <span className="eyebrow">Until</span>
            <input
              type="date"
              className="field"
              value={filters.due_date_before}
              onChange={(event) => update("due_date_before", event.target.value)}
            />
          </label>
          <label className="space-y-1.5 lg:col-span-1">
            <span className="eyebrow">Search</span>
            <input
              type="search"
              className="field"
              placeholder="Title or description"
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
            />
          </label>
          <label className="flex items-end gap-2 pb-2.5 text-sm text-muted-foreground">
            <input
              type="checkbox"
              className="size-4 accent-link"
              checked={filters.overdue}
              onChange={(event) => update("overdue", event.target.checked)}
            />
            Overdue only
          </label>
        </div>
      </section>

      {tasks.isPending && <Loading />}
      {tasks.isError && <ErrorState error={tasks.error} retry={() => tasks.refetch()} />}

      {tasks.data && (
        <>
          {tasks.data.results.length === 0 ? (
            <div className="panel px-6 py-14 text-center">
              <p className="eyebrow">Nothing here</p>
              <p className="mt-1 text-sm text-muted-foreground">
                No tasks match these filters.
              </p>
            </div>
          ) : (
            <div role="table" aria-label="Tasks" className="panel overflow-hidden">
              <div
                role="row"
                className="task-grid border-b border-border py-3 max-lg:sr-only"
              >
                {["Complete", "Task", "Status", "Due date", "Assignee", "Actions"].map((name, i) => (
                  <div
                    key={name}
                    role="columnheader"
                    className="eyebrow min-w-0 text-[11px]"
                  >
                    {/* The check and actions columns have no visible title; the cell keeps its grid slot. */}
                    <span className={cn((i === 0 || i === 5) && "sr-only")}>{name}</span>
                  </div>
                ))}
              </div>
              {tasks.data.results.map((task) => (
                <TaskRow
                  key={task.id}
                  task={task}
                  currentUserId={user.id}
                  onEdit={setEditing}
                  onDelete={setDeleting}
                />
              ))}
            </div>
          )}

          <div className="mt-4 flex items-center justify-between gap-3 text-sm text-muted-foreground">
            <span className="font-mono text-xs">{tasks.data.count} task(s)</span>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={filters.page <= 1}
                onClick={() => setFilters((current) => ({ ...current, page: current.page - 1 }))}
              >
                Previous
              </Button>
              <span className="font-mono text-xs">
                {filters.page} / {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={filters.page >= totalPages}
                onClick={() => setFilters((current) => ({ ...current, page: current.page + 1 }))}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      )}

      {creating && (
        <TaskDialog task={null} users={users.data ?? []} onClose={() => setCreating(false)} />
      )}
      {editing && (
        <TaskDialog task={editing} users={users.data ?? []} onClose={() => setEditing(null)} />
      )}
      {deleting && (
        <Dialog title="Delete task?" onClose={() => setDeleting(null)} busy={remove.isPending}>
          <p className="text-sm text-muted-foreground">
            “{deleting.title}” will be permanently removed.
          </p>
          <div className="mt-6 flex justify-end gap-3">
            <Button variant="ghost" onClick={() => setDeleting(null)} disabled={remove.isPending}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={remove.isPending}
              onClick={() =>
                remove.mutate(deleting.id, { onSuccess: () => setDeleting(null) })
              }
            >
              {remove.isPending ? "Deleting…" : "Delete"}
            </Button>
          </div>
        </Dialog>
      )}
    </div>
  );
}
