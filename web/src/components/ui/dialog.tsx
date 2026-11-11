import { useEffect, useId, useRef } from "react";
import { X } from "lucide-react";

import { Button } from "./button";

export function Dialog({
  title,
  description,
  children,
  onClose,
  busy = false,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
  onClose: () => void;
  busy?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const descriptionId = useId();

  useEffect(() => {
    ref.current?.showModal();
  }, []);

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      aria-describedby={description ? descriptionId : undefined}
      aria-busy={busy || undefined}
      onClose={onClose}
      onPointerDown={(event) => {
        if (busy || event.target !== event.currentTarget) return;
        const { left, right, top, bottom } = event.currentTarget.getBoundingClientRect();
        if (
          event.clientX < left ||
          event.clientX > right ||
          event.clientY < top ||
          event.clientY > bottom
        ) {
          event.preventDefault();
          ref.current?.close();
        }
      }}
      onCancel={(event) => {
        if (busy) event.preventDefault();
      }}
      className="m-auto max-h-[88dvh] w-[calc(100%-2rem)] max-w-xl overflow-y-auto rounded-xl border border-border bg-card p-5 text-foreground backdrop:bg-foreground/45 backdrop:backdrop-blur-sm sm:p-7"
    >
      <div className="mb-5 flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1 break-words">
          <h2 id={titleId} className="text-xl">
            {title}
          </h2>
          {description && (
            <p id={descriptionId} className="mt-2 text-sm leading-relaxed text-muted-foreground">
              {description}
            </p>
          )}
        </div>
        <Button
          variant="ghost"
          size="icon"
          aria-label="Close"
          disabled={busy}
          onClick={() => ref.current?.close()}
        >
          <X />
        </Button>
      </div>
      {children}
    </dialog>
  );
}
