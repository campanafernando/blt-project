import { useState } from "react";
import {
  ExternalLink,
  FileText,
  GitBranch,
  ListChecks,
  LoaderCircle,
  Sparkles,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/feedback";
import { PageTitle } from "@/components/ui/page-title";
import { formatDate } from "@/lib/utils";
import type { Spec, SpecCreateInput, SpecSource } from "@/lib/types";
import { useCreateSpec, usePublishSpec, useSpecConfig, useSpecs } from "./hooks";
import { SpecTasksDialog } from "./SpecTasksDialog";

function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="badge bg-soft text-link">
      {children}
    </span>
  );
}

function List({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <section>
      <h3 className="eyebrow mb-2">{title}</h3>
      <ul className="space-y-1.5 text-sm">
        {items.map((item) => (
          <li key={item} className="flex gap-2">
            <span className="mt-[7px] size-1.5 shrink-0 rounded-full bg-link/60" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

const effortLabel: Record<Spec["size"], string> = {
  S: "Small effort",
  M: "Medium effort",
  L: "Large effort",
};

// A subject spec has no source issue: show where it will be published instead of a link.
function SpecOrigin({ spec }: { spec: Spec }) {
  if (spec.source === "subject" || !spec.issue_url) {
    return (
      <p className="mt-1 inline-flex items-center gap-1 font-mono text-xs text-muted-foreground">
        <GitBranch className="size-3.5" />
        {spec.repo}
      </p>
    );
  }
  return (
    <a
      className="mt-1 inline-flex items-center gap-1 font-mono text-xs hover:underline"
      href={spec.issue_url}
      target="_blank"
      rel="noreferrer"
    >
      <GitBranch className="size-3.5" />
      {spec.repo}#{spec.issue_number}
      <ExternalLink className="size-3" />
    </a>
  );
}

function publishHint(spec: Spec, publishEnabled: boolean): string | null {
  if (!publishEnabled) return "Publishing is not available right now.";
  if (spec.source === "subject") return `Publishing creates a new issue in ${spec.repo}.`;
  return null;
}

function SpecResult({
  spec,
  publishEnabled,
  onChange,
}: {
  spec: Spec;
  publishEnabled: boolean;
  onChange: (spec: Spec) => void;
}) {
  const publish = usePublishSpec(onChange);
  const [tasksOpen, setTasksOpen] = useState(false);
  const hint = publishHint(spec, publishEnabled);

  return (
    <article className="panel p-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="eyebrow">Generated spec</p>
          <h2 className="text-xl">{spec.issue_title}</h2>
          <SpecOrigin spec={spec} />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {spec.source === "subject" && <Badge>From a subject</Badge>}
          <Badge>{effortLabel[spec.size]}</Badge>
        </div>
      </header>

      <p className="mt-4 text-sm leading-relaxed">{spec.summary}</p>
      {spec.truncated && (
        <p className="mt-2 text-xs text-muted-foreground">
          Some of the {spec.source === "subject" ? "subject" : "issue"} text was too long and was
          shortened.
        </p>
      )}

      <div className="mt-6 grid gap-6 sm:grid-cols-2">
        <List title="Acceptance criteria" items={spec.acceptance_criteria} />
        <List title="Implementation steps" items={spec.implementation_steps} />
        <List title="Risks" items={spec.risks} />
        <List title="Out of scope" items={spec.out_of_scope} />
      </div>

      <footer className="mt-6 flex flex-wrap items-center justify-end gap-3 border-t border-border pt-4">
        <Button
          variant="outline"
          onClick={() => setTasksOpen(true)}
          disabled={publish.isPending || spec.implementation_steps.length === 0}
        >
          <ListChecks />
          Create tasks
        </Button>
        {spec.published ? (
          <a
            className="inline-flex items-center gap-2 text-sm font-medium text-link"
            href={spec.published_issue_url}
            target="_blank"
            rel="noreferrer"
          >
            View published issue #{spec.published_issue_number}
            <ExternalLink className="size-4" />
          </a>
        ) : (
          <>
            {hint && (
              <p id="publish-hint" className="text-xs text-muted-foreground">
                {hint}
              </p>
            )}
            <Button
              onClick={() => publish.mutate(spec.id)}
              disabled={!publishEnabled || publish.isPending}
              aria-describedby={hint ? "publish-hint" : undefined}
            >
              {publish.isPending ? <LoaderCircle className="animate-spin" /> : <GitBranch />}
              Publish as issue
            </Button>
          </>
        )}
      </footer>
      {tasksOpen && <SpecTasksDialog spec={spec} onClose={() => setTasksOpen(false)} />}
    </article>
  );
}

type Mode = SpecSource;

const modes: { value: Mode; label: string }[] = [
  { value: "issue", label: "From an issue" },
  { value: "subject", label: "From a subject" },
];

const SUBJECT_MIN = 10;
const SUBJECT_MAX = 2000;

function ModeSwitch({
  mode,
  onChange,
  disabled,
}: {
  mode: Mode;
  onChange: (mode: Mode) => void;
  disabled: boolean;
}) {
  return (
    <div role="group" aria-label="How to start the spec" className="mb-4 flex flex-wrap gap-2">
      {modes.map(({ value, label }) => (
        <button
          key={value}
          type="button"
          aria-pressed={mode === value}
          disabled={disabled}
          onClick={() => onChange(value)}
          className={`min-h-11 rounded-lg border px-4 text-sm font-medium transition disabled:opacity-60 ${
            mode === value
              ? "border-link bg-soft text-link"
              : "border-field-border bg-background text-foreground hover:bg-soft/60"
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

function SpecForm({
  aiEnabled,
  pending,
  onSubmit,
}: {
  aiEnabled: boolean;
  pending: boolean;
  onSubmit: (input: SpecCreateInput) => void;
}) {
  const [mode, setMode] = useState<Mode>("issue");
  const [issueUrl, setIssueUrl] = useState("");
  const [subject, setSubject] = useState("");
  const url = issueUrl.trim();
  const text = subject.trim();
  const valid = mode === "issue" ? url !== "" : text.length >= SUBJECT_MIN;
  const locked = !aiEnabled || pending;

  function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!valid || locked) return;
    onSubmit(mode === "issue" ? { issue_url: url } : { subject: text });
  }

  return (
    <>
      <ModeSwitch mode={mode} onChange={setMode} disabled={pending} />
      <form className="flex flex-col gap-3 sm:flex-row" onSubmit={submit}>
        {mode === "issue" ? (
          <label className="min-w-0 flex-1 space-y-1.5">
            <span className="eyebrow">Issue link</span>
            <input
              className="field"
              placeholder="Paste the link of an issue"
              value={issueUrl}
              onChange={(event) => setIssueUrl(event.target.value)}
              disabled={locked}
            />
          </label>
        ) : (
          <div className="min-w-0 flex-1 space-y-1.5">
            <label htmlFor="spec-subject" className="eyebrow block">
              Subject
            </label>
            <textarea
              id="spec-subject"
              className="field min-h-32 resize-y"
              placeholder="Describe what you want to build or fix"
              value={subject}
              maxLength={SUBJECT_MAX}
              aria-describedby="spec-subject-count"
              onChange={(event) => setSubject(event.target.value)}
              disabled={locked}
            />
            <p id="spec-subject-count" className="text-xs text-muted-foreground">
              {text.length}/{SUBJECT_MAX} characters
              {text.length < SUBJECT_MIN && ` (at least ${SUBJECT_MIN})`}
            </p>
          </div>
        )}
        <div className={`flex items-end ${mode === "subject" ? "sm:pb-7" : ""}`}>
          <Button type="submit" disabled={locked || !valid}>
            {pending ? <LoaderCircle className="animate-spin" /> : <Sparkles />}
            {pending ? "Generating…" : "Generate spec"}
          </Button>
        </div>
      </form>
    </>
  );
}

export function SpecsPage() {
  const [current, setCurrent] = useState<Spec | null>(null);
  const config = useSpecConfig();
  const specs = useSpecs();
  const create = useCreateSpec(setCurrent);
  const aiEnabled = config.data?.ai_enabled ?? false;
  const publishEnabled = config.data?.publish_enabled ?? false;

  return (
    <div className="mx-auto w-full max-w-5xl px-4 pb-16 sm:px-6">
      <header className="py-8">
        <p className="eyebrow">AI assistant</p>
        <PageTitle>Write a spec</PageTitle>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
          Paste the link of an issue, or describe a subject in your own words, to get a
          ready-to-use spec with a summary, acceptance criteria, steps and risks.
        </p>
      </header>

      <section className="panel mb-6 p-5">
        <SpecForm
          aiEnabled={aiEnabled}
          pending={create.isPending}
          onSubmit={(input) => create.mutate(input)}
        />
        {!aiEnabled && !config.isPending && (
          <p role="alert" className="mt-3 text-sm text-destructive">
            Spec generation is not available right now.
          </p>
        )}
      </section>

      {create.isError && <ErrorState error={create.error} />}
      {current && (
        <SpecResult spec={current} publishEnabled={publishEnabled} onChange={setCurrent} />
      )}

      <section className="mt-10">
        <div className="mb-3 flex items-center gap-2">
          <FileText className="size-4 text-muted-foreground" />
          <h2 className="eyebrow">Recent specs</h2>
        </div>
        {specs.isPending && <p className="text-sm text-muted-foreground">Loading…</p>}
        {specs.isError && <ErrorState error={specs.error} retry={() => specs.refetch()} />}
        {specs.data && specs.data.results.length === 0 && (
          <p className="text-sm text-muted-foreground">No specs generated yet.</p>
        )}
        <ul className="panel divide-y divide-border overflow-hidden">
          {specs.data?.results.map((spec) => (
            <li key={spec.id}>
              <button
                type="button"
                className="flex w-full flex-wrap items-center gap-3 px-4 py-3 text-left transition hover:bg-soft/60"
                onClick={() => setCurrent(spec)}
              >
                <span className="min-w-0 flex-1 truncate text-sm font-medium">{spec.issue_title}</span>
                <Badge>{effortLabel[spec.size]}</Badge>
                <span className="font-mono text-[11px] text-muted-foreground">
                  {formatDate(spec.created_at.slice(0, 10))}
                </span>
                {spec.source === "subject" && <Badge>From a subject</Badge>}
                {spec.published && <Badge>published</Badge>}
              </button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
