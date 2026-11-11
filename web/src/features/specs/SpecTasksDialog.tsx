import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { useUsers } from "@/features/tasks/hooks";
import type { Spec } from "@/lib/types";
import { useCreateSpecTasks } from "./hooks";

const MAX_TASKS = 10;
const MAX_TITLE = 200;

type Row = { checked: boolean; title: string };

export function SpecTasksDialog({ spec, onClose }: { spec: Spec; onClose: () => void }) {
  const [rows, setRows] = useState<Row[]>(() =>
    spec.implementation_steps.map((step) => ({
      checked: true,
      title: step.trim().slice(0, MAX_TITLE),
    })),
  );
  const [assignedTo, setAssignedTo] = useState("");
  const [dueDate, setDueDate] = useState("");
  const users = useUsers();
  const create = useCreateSpecTasks(spec.id, onClose);

  const selected = rows.filter((row) => row.checked);
  const tooMany = selected.length > MAX_TASKS;
  const hasBlank = selected.some((row) => !row.title.trim());
  const canSubmit =
    selected.length > 0 && !tooMany && !hasBlank && !create.isPending;

  function updateRow(index: number, change: Partial<Row>) {
    setRows((current) => current.map((row, i) => (i === index ? { ...row, ...change } : row)));
  }

  function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!canSubmit) return;
    create.mutate({
      tasks: selected.map((row) => ({
        title: row.title.trim(),
        due_date: dueDate || null,
        assigned_to: assignedTo ? Number(assignedTo) : null,
      })),
    });
  }

  return (
    <Dialog
      title="Create tasks"
      description="Pick the steps to turn into tasks. You can edit each title first."
      onClose={onClose}
      busy={create.isPending}
    >
      <form className="space-y-4" onSubmit={submit}>
        <ul className="space-y-2">
          {rows.map((row, index) => (
            <li key={index} className="flex items-center gap-3">
              <input
                type="checkbox"
                className="size-5 shrink-0 accent-primary"
                aria-label={`Include step ${index + 1}`}
                checked={row.checked}
                onChange={(event) => updateRow(index, { checked: event.target.checked })}
              />
              <input
                className="field min-w-0 flex-1"
                aria-label={`Title for step ${index + 1}`}
                maxLength={MAX_TITLE}
                value={row.title}
                disabled={!row.checked}
                onChange={(event) => updateRow(index, { title: event.target.value })}
              />
            </li>
          ))}
        </ul>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block space-y-1.5">
            <span className="eyebrow">Assign all to</span>
            <select
              className="field"
              value={assignedTo}
              onChange={(event) => setAssignedTo(event.target.value)}
            >
              <option value="">Unassigned</option>
              {users.data?.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.first_name ? `${user.first_name} ${user.last_name}` : user.username}
                </option>
              ))}
            </select>
          </label>

          <label className="block space-y-1.5">
            <span className="eyebrow">Due date</span>
            <input
              type="date"
              className="field"
              value={dueDate}
              onChange={(event) => setDueDate(event.target.value)}
            />
          </label>
        </div>

        {tooMany && (
          <p role="alert" className="text-sm text-destructive">
            Select up to {MAX_TASKS} steps.
          </p>
        )}
        {create.isError && (
          <p role="alert" className="text-sm text-destructive">
            {create.error.message}
          </p>
        )}

        <div className="flex items-center justify-end gap-3 pt-2">
          <Button variant="ghost" onClick={onClose} disabled={create.isPending}>
            Cancel
          </Button>
          <Button type="submit" disabled={!canSubmit}>
            {create.isPending
              ? "Creating…"
              : `Create ${selected.length} ${selected.length === 1 ? "task" : "tasks"}`}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
