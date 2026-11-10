import { useState } from "react";
import { Plus, SlidersHorizontal } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { ErrorState, Loading } from "@/components/ui/feedback";
import { useAuth } from "@/lib/auth";
import { emptyFilters, type Task, type TaskFilters } from "@/lib/types";
import { TaskDialog } from "./TaskDialog";
import { TaskRow } from "./TaskRow";
import { useDeleteTask, useSummary, useTasks, useUsers } from "./hooks";

const PAGE_SIZE = 10;

export function TaskBoard() {
  const { user } = useAuth();
  const [filters, setFilters] = useState<TaskFilters>(emptyFilters);
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

  if (!user) return null;

  const totalPages = tasks.data ? Math.max(1, Math.ceil(tasks.data.count / PAGE_SIZE)) : 1;
  const usersList = users.data?.map((item) => ({
    id: item.id,
    username: item.username,
    first_name: item.first_name,
    last_name: item.last_name,
  })) ?? [];

  return (
    <div className="mx-auto w-full max-w-6xl px-4 pb-16 sm:px-6">
      <header className="flex flex-wrap items-end justify-between gap-4 py-8">
        <div>
          <p className="eyebrow">Painel</p>
          <h1 className="font-display text-3xl font-semibold tracking-tight">Minhas tarefas</h1>
          <p className="mt-1 max-w-xl text-sm text-muted-foreground">
            Crie, atribua e acompanhe prazos. Cliente React sobre a API Django com JWT.
          </p>
        </div>
        <Button onClick={() => setCreating(true)}>
          <Plus />
          Nova tarefa
        </Button>
      </header>

      <section className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          ["Total", summary.data?.total],
          ["A fazer", summary.data?.todo],
          ["Em andamento", summary.data?.in_progress],
          ["Atrasadas", summary.data?.overdue],
        ].map(([label, value]) => (
          <div key={String(label)} className="panel px-4 py-3">
            <p className="font-display text-2xl font-semibold leading-none">{value ?? "—"}</p>
            <p className="mt-1 text-xs text-muted-foreground">{label}</p>
          </div>
        ))}
      </section>

      <section className="panel mb-5 p-4">
        <div className="mb-3 flex items-center gap-2 text-muted-foreground">
          <SlidersHorizontal className="size-4" />
          <span className="eyebrow">Filtros</span>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <label className="space-y-1.5">
            <span className="eyebrow">Status</span>
            <select
              className="field"
              value={filters.status}
              onChange={(event) => update("status", event.target.value)}
            >
              <option value="">Todos</option>
              <option value="todo">A fazer</option>
              <option value="in_progress">Em andamento</option>
              <option value="done">Concluídas</option>
            </select>
          </label>
          <label className="space-y-1.5">
            <span className="eyebrow">De</span>
            <input
              type="date"
              className="field"
              value={filters.due_date_after}
              onChange={(event) => update("due_date_after", event.target.value)}
            />
          </label>
          <label className="space-y-1.5">
            <span className="eyebrow">Até</span>
            <input
              type="date"
              className="field"
              value={filters.due_date_before}
              onChange={(event) => update("due_date_before", event.target.value)}
            />
          </label>
          <label className="space-y-1.5 lg:col-span-1">
            <span className="eyebrow">Buscar</span>
            <input
              type="search"
              className="field"
              placeholder="Título ou descrição"
              value={filters.search}
              onChange={(event) => update("search", event.target.value)}
            />
          </label>
          <label className="flex items-end gap-2 pb-2.5 text-sm text-muted-foreground">
            <input
              type="checkbox"
              className="size-4 accent-primary"
              checked={filters.overdue}
              onChange={(event) => update("overdue", event.target.checked)}
            />
            Só atrasadas
          </label>
        </div>
      </section>

      {tasks.isPending && <Loading />}
      {tasks.isError && <ErrorState error={tasks.error} retry={() => tasks.refetch()} />}

      {tasks.data && (
        <>
          {tasks.data.results.length === 0 ? (
            <div className="panel px-6 py-14 text-center">
              <p className="eyebrow">Nada aqui</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Nenhuma tarefa encontrada com esses filtros.
              </p>
            </div>
          ) : (
            <ul className="panel overflow-hidden">
              {tasks.data.results.map((task) => (
                <TaskRow
                  key={task.id}
                  task={task}
                  currentUserId={user.id}
                  onEdit={setEditing}
                  onDelete={setDeleting}
                />
              ))}
            </ul>
          )}

          <div className="mt-4 flex items-center justify-between gap-3 text-sm text-muted-foreground">
            <span className="font-mono text-xs">{tasks.data.count} tarefa(s)</span>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={filters.page <= 1}
                onClick={() => setFilters((current) => ({ ...current, page: current.page - 1 }))}
              >
                Anterior
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
                Próxima
              </Button>
            </div>
          </div>
        </>
      )}

      {creating && (
        <TaskDialog task={null} users={usersList} onClose={() => setCreating(false)} />
      )}
      {editing && (
        <TaskDialog task={editing} users={usersList} onClose={() => setEditing(null)} />
      )}
      {deleting && (
        <Dialog title="Excluir tarefa?" onClose={() => setDeleting(null)} busy={remove.isPending}>
          <p className="text-sm text-muted-foreground">
            “{deleting.title}” será removida permanentemente.
          </p>
          <div className="mt-6 flex justify-end gap-3">
            <Button variant="ghost" onClick={() => setDeleting(null)} disabled={remove.isPending}>
              Cancelar
            </Button>
            <Button
              variant="destructive"
              disabled={remove.isPending}
              onClick={() =>
                remove.mutate(deleting.id, { onSuccess: () => setDeleting(null) })
              }
            >
              {remove.isPending ? "Excluindo…" : "Excluir"}
            </Button>
          </div>
        </Dialog>
      )}
    </div>
  );
}
