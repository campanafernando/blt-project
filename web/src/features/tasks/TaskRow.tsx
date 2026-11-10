import { Check, Pencil, RotateCcw, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { Status, Task } from "@/lib/types";
import { cn, formatDate } from "@/lib/utils";
import { useToggleTask } from "./hooks";

const statusLabel: Record<Status, string> = {
  todo: "To do",
  in_progress: "In progress",
  done: "Done",
};

const statusStyle: Record<Status, string> = {
  todo: "bg-muted text-primary",
  in_progress: "bg-[#fff6dd] text-[#8a5a00]",
  done: "bg-[#e6f4ec] text-[#1f6b46]",
};

export function TaskRow({
  task,
  currentUserId,
  onEdit,
  onDelete,
}: {
  task: Task;
  currentUserId: number;
  onEdit: (task: Task) => void;
  onDelete: (task: Task) => void;
}) {
  const toggle = useToggleTask();
  const done = task.status === "done";
  const assignee = task.assigned_to
    ? task.assigned_to.first_name || task.assigned_to.username
    : "—";

  return (
    <li
      className={cn(
        "flex flex-wrap items-center gap-x-4 gap-y-3 border-b border-border px-4 py-4 last:border-b-0",
        task.is_overdue && "border-l-4 border-l-accent pl-3",
        done && "bg-card/60",
      )}
    >
      <button
        type="button"
        onClick={() => toggle.mutate({ id: task.id, done })}
        disabled={toggle.isPending}
        aria-label={done ? `Reopen ${task.title}` : `Complete ${task.title}`}
        className="grid size-8 shrink-0 place-items-center rounded-lg border border-border text-muted-foreground transition hover:border-primary hover:bg-muted hover:text-primary disabled:opacity-50"
      >
        {done ? <RotateCcw className="size-4" /> : <Check className="size-4" />}
      </button>

      <div className="min-w-[12rem] flex-1">
        <p className={cn("font-medium leading-snug", done && "text-muted-foreground line-through")}>
          {task.title}
        </p>
        {task.description && (
          <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">{task.description}</p>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span
          className={cn(
            "rounded-full px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider",
            statusStyle[task.status],
          )}
        >
          {statusLabel[task.status]}
        </span>
        {task.is_overdue && (
          <span className="rounded-full bg-[#fff0e7] px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider text-accent">
            Overdue
          </span>
        )}
      </div>

      <div className="w-24 shrink-0">
        <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
          Due date
        </p>
        <p className="text-sm">{formatDate(task.due_date)}</p>
      </div>

      <div className="w-32 shrink-0">
        <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
          Assignee
        </p>
        <p className="truncate text-sm">{assignee}</p>
      </div>

      <div className="flex shrink-0 items-center gap-1">
        <Button variant="ghost" size="icon" aria-label="Edit task" onClick={() => onEdit(task)}>
          <Pencil />
        </Button>
        {task.created_by.id === currentUserId && (
          <Button
            variant="ghost"
            size="icon"
            aria-label="Delete task"
            className="hover:text-destructive"
            onClick={() => onDelete(task)}
          >
            <Trash2 />
          </Button>
        )}
      </div>
    </li>
  );
}
