import { Check, Pencil, RotateCcw, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { Status, Task } from "@/lib/types";
import { cn, dueCaption, formatDate, initials } from "@/lib/utils";
import { useToggleTask } from "./hooks";

const statusLabel: Record<Status, string> = {
  todo: "To do",
  in_progress: "In progress",
  done: "Done",
};

const statusStyle: Record<Status, string> = {
  todo: "bg-soft text-link",
  in_progress: "bg-warning-soft text-warning",
  done: "bg-success-soft text-success",
};

const captionTone = {
  overdue: "text-overdue",
  soon: "text-warning",
  muted: "text-muted-foreground",
};

function MobileLabel({ children }: { children: string }) {
  return (
    <p aria-hidden="true" className="eyebrow mb-1 text-[11px] lg:hidden">
      {children}
    </p>
  );
}

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
  const caption = dueCaption(task);
  const { assigned_to: assignee, created_by: creator } = task;
  const assigneeFull = assignee
    ? `${assignee.first_name} ${assignee.last_name}`.trim() || assignee.username
    : "";
  const assigneeIsMe = assignee?.id === currentUserId;
  const showCreator = creator.id !== currentUserId && creator.id !== assignee?.id;
  const cell = "col-start-2 min-w-0 lg:col-start-auto";

  return (
    <div
      role="row"
      className={cn(
        "task-grid task-row",
        task.is_overdue && "shadow-[inset_4px_0_0_var(--primary)]",
        toggle.isPending && "pointer-events-none opacity-60",
      )}
    >
      <div role="cell">
        <button
          type="button"
          onClick={() => toggle.mutate({ id: task.id, done })}
          disabled={toggle.isPending}
          aria-label={done ? `Reopen ${task.title}` : `Complete ${task.title}`}
          title={done ? "Reopen task" : "Mark as done"}
          className="grid size-11 place-items-center rounded-lg text-muted-foreground transition hover:bg-soft hover:text-link disabled:opacity-50"
        >
          {done ? <RotateCcw className="size-4" /> : <Check className="size-4" />}
        </button>
      </div>

      <div role="cell" className="min-w-0">
        <p
          title={task.title}
          className={cn("truncate font-medium", done && "text-muted-foreground line-through")}
        >
          {task.title}
        </p>
        {task.description && (
          <p title={task.description} className="mt-0.5 truncate text-xs text-muted-foreground">
            {task.description}
          </p>
        )}
      </div>

      <div role="cell" className={cell}>
        <MobileLabel>Status</MobileLabel>
        <span className={cn("badge", statusStyle[task.status])}>{statusLabel[task.status]}</span>
      </div>

      <div role="cell" className={cell}>
        <MobileLabel>Due date</MobileLabel>
        {task.due_date ? (
          <p className={cn("text-sm", done && "text-muted-foreground")}>
            {formatDate(task.due_date)}
          </p>
        ) : (
          <p className="text-sm text-muted-foreground">No due date</p>
        )}
        {caption && (
          <p className={cn("font-mono text-[11px]", captionTone[caption.tone])}>{caption.text}</p>
        )}
      </div>

      <div role="cell" className={cell}>
        <MobileLabel>Assignee</MobileLabel>
        {assignee ? (
          <div className="flex min-w-0 items-center gap-2">
            <span
              aria-hidden="true"
              className="grid size-6 shrink-0 place-items-center rounded-full bg-soft font-mono text-[10px] font-medium text-link"
            >
              {initials(assigneeFull)}
            </span>
            <span title={assigneeFull} className="min-w-0 truncate text-sm">
              {assignee.first_name || assignee.username}
            </span>
            {assigneeIsMe && (
              <span className="shrink-0 font-mono text-[11px] text-muted-foreground">You</span>
            )}
          </div>
        ) : (
          <div className="flex min-w-0 items-center gap-2">
            <span
              aria-hidden="true"
              className="size-6 shrink-0 rounded-full border border-dashed border-field-border"
            />
            <span className="truncate pr-1 text-sm italic text-muted-foreground">Unassigned</span>
          </div>
        )}
        {showCreator && (
          <p
            title={`Created by ${`${creator.first_name} ${creator.last_name}`.trim() || creator.username}`}
            className="mt-0.5 truncate pl-8 font-mono text-[11px] text-muted-foreground"
          >
            from {creator.first_name || creator.username}
          </p>
        )}
      </div>

      <div role="cell" className={cn(cell, "flex justify-end")}>
        <Button
          variant="ghost"
          size="icon"
          aria-label={`Edit ${task.title}`}
          title="Edit task"
          className="row-action text-foreground"
          onClick={() => onEdit(task)}
        >
          <Pencil />
        </Button>
        {creator.id === currentUserId ? (
          <Button
            variant="ghost"
            size="icon"
            aria-label={`Delete ${task.title}`}
            title="Delete task"
            className="row-action text-foreground hover:text-destructive"
            onClick={() => onDelete(task)}
          >
            <Trash2 />
          </Button>
        ) : (
          <span aria-hidden="true" className="size-11 shrink-0" />
        )}
      </div>
    </div>
  );
}
