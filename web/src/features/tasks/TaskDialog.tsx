import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import type { Status, Task, TaskUser } from "@/lib/types";
import { useCreateTask, useUpdateTask } from "./hooks";

type FormValues = {
  title: string;
  description: string;
  due_date: string;
  assigned_to: string;
  status: Status;
};

const EMPTY: FormValues = {
  title: "",
  description: "",
  due_date: "",
  assigned_to: "",
  status: "todo",
};

export function TaskDialog({
  task,
  users,
  onClose,
}: {
  task: Task | null;
  users: TaskUser[];
  onClose: () => void;
}) {
  const [formError, setFormError] = useState<string | null>(null);
  const create = useCreateTask(onClose);
  const update = useUpdateTask(onClose);
  const busy = create.isPending || update.isPending;

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({ defaultValues: EMPTY });

  useEffect(() => {
    setFormError(null);
    reset(
      task
        ? {
            title: task.title,
            description: task.description,
            due_date: task.due_date ?? "",
            assigned_to: task.assigned_to ? String(task.assigned_to.id) : "",
            status: task.status,
          }
        : EMPTY,
    );
  }, [task, reset]);

  function onSubmit(values: FormValues) {
    const payload = {
      title: values.title,
      description: values.description,
      due_date: values.due_date || null,
      assigned_to: values.assigned_to ? Number(values.assigned_to) : null,
    };
    if (task) {
      update.mutate(
        { id: task.id, payload: { ...payload, status: values.status } },
        { onError: (error) => setFormError(error.message) },
      );
    } else {
      create.mutate(payload, { onError: (error) => setFormError(error.message) });
    }
  }

  return (
    <Dialog
      title={task ? "Editar tarefa" : "Nova tarefa"}
      description={
        task ? "Alterações são salvas na API e refletem no board." : "Atribuir envia e-mail via Celery."
      }
      onClose={onClose}
      busy={busy}
    >
      <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
        <label className="block space-y-1.5">
          <span className="eyebrow">Título</span>
          <input
            className="field"
            maxLength={200}
            autoFocus
            {...register("title", { required: "Informe um título." })}
          />
          {errors.title && <span className="text-xs text-destructive">{errors.title.message}</span>}
        </label>

        <label className="block space-y-1.5">
          <span className="eyebrow">Descrição</span>
          <textarea className="field min-h-24" rows={3} {...register("description")} />
        </label>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block space-y-1.5">
            <span className="eyebrow">Vencimento</span>
            <input type="date" className="field" {...register("due_date")} />
          </label>

          <label className="block space-y-1.5">
            <span className="eyebrow">Responsável</span>
            <select className="field" {...register("assigned_to")}>
              <option value="">Sem responsável</option>
              {users.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.first_name ? `${user.first_name} ${user.last_name}` : user.username}
                </option>
              ))}
            </select>
          </label>
        </div>

        {task && (
          <label className="block space-y-1.5">
            <span className="eyebrow">Status</span>
            <select className="field" {...register("status")}>
              <option value="todo">A fazer</option>
              <option value="in_progress">Em andamento</option>
              <option value="done">Concluída</option>
            </select>
          </label>
        )}

        {formError && (
          <p role="alert" className="text-sm text-destructive">
            {formError}
          </p>
        )}

        <div className="flex items-center justify-end gap-3 pt-2">
          <Button variant="ghost" onClick={onClose} disabled={busy}>
            Cancelar
          </Button>
          <Button type="submit" disabled={busy}>
            {busy ? "Salvando…" : task ? "Salvar" : "Criar tarefa"}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
