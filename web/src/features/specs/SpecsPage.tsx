import { useState } from "react";
import { ExternalLink, FileText, GitBranch, LoaderCircle, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/feedback";
import { formatDate } from "@/lib/utils";
import type { Spec } from "@/lib/types";
import { useCreateSpec, usePublishSpec, useSpecConfig, useSpecs } from "./hooks";

function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full bg-muted px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider text-primary">
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
            <span className="mt-[7px] size-1.5 shrink-0 rounded-full bg-primary/60" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function SpecResult({ spec, onChange }: { spec: Spec; onChange: (spec: Spec) => void }) {
  const publish = usePublishSpec(onChange);

  return (
    <article className="panel p-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="eyebrow">Spec gerada</p>
          <h2 className="font-display text-xl font-semibold tracking-tight">{spec.issue_title}</h2>
          <a
            className="mt-1 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
            href={spec.issue_url}
            target="_blank"
            rel="noreferrer"
          >
            <GitBranch className="size-3.5" />
            {spec.repo}#{spec.issue_number}
            <ExternalLink className="size-3" />
          </a>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge>size {spec.size}</Badge>
          <Badge>{spec.latency_ms} ms</Badge>
          {spec.truncated && <Badge>input truncado</Badge>}
        </div>
      </header>

      <p className="mt-4 text-sm leading-relaxed">{spec.summary}</p>

      <div className="mt-6 grid gap-6 sm:grid-cols-2">
        <List title="Critérios de aceite" items={spec.acceptance_criteria} />
        <List title="Passos de implementação" items={spec.implementation_steps} />
        <List title="Riscos" items={spec.risks} />
        <List title="Fora de escopo" items={spec.out_of_scope} />
      </div>

      <footer className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
        <p className="font-mono text-[11px] text-muted-foreground">
          {spec.model} · {spec.prompt_version} · {spec.input_chars} chars de entrada
        </p>
        {spec.published ? (
          <a
            className="inline-flex items-center gap-2 text-sm font-medium text-primary"
            href={spec.published_issue_url}
            target="_blank"
            rel="noreferrer"
          >
            Ver issue publicada #{spec.published_issue_number}
            <ExternalLink className="size-4" />
          </a>
        ) : (
          <Button
            onClick={() => publish.mutate(spec.id)}
            disabled={publish.isPending}
            className="bg-foreground hover:bg-foreground/90"
          >
            {publish.isPending ? <LoaderCircle className="animate-spin" /> : <GitBranch />}
            Publicar como issue
          </Button>
        )}
      </footer>
    </article>
  );
}

export function SpecsPage() {
  const [issueUrl, setIssueUrl] = useState("");
  const [current, setCurrent] = useState<Spec | null>(null);
  const config = useSpecConfig();
  const specs = useSpecs();
  const create = useCreateSpec(setCurrent);
  const aiEnabled = config.data?.ai_enabled ?? false;

  return (
    <div className="mx-auto w-full max-w-5xl px-4 pb-16 sm:px-6">
      <header className="py-8">
        <p className="eyebrow">GenAI</p>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Spec a partir de issue</h1>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
          A única entrada é a URL de uma issue. O prompt é fixo no servidor, a saída é validada
          por contrato e nada é executado a partir do texto da issue.
        </p>
      </header>

      <section className="panel mb-6 p-5">
        <form
          className="flex flex-col gap-3 sm:flex-row"
          onSubmit={(event) => {
            event.preventDefault();
            if (issueUrl.trim()) create.mutate(issueUrl.trim());
          }}
        >
          <label className="min-w-0 flex-1 space-y-1.5">
            <span className="eyebrow">URL da issue</span>
            <input
              className="field"
              placeholder="https://github.com/owner/repo/issues/123"
              value={issueUrl}
              onChange={(event) => setIssueUrl(event.target.value)}
              disabled={!aiEnabled || create.isPending}
            />
          </label>
          <div className="flex items-end">
            <Button type="submit" disabled={!aiEnabled || create.isPending || !issueUrl.trim()}>
              {create.isPending ? <LoaderCircle className="animate-spin" /> : <Sparkles />}
              {create.isPending ? "Gerando…" : "Gerar spec"}
            </Button>
          </div>
        </form>
        <p className="mt-3 font-mono text-[11px] text-muted-foreground">
          {config.data
            ? `${config.data.model} · ${config.data.prompt_version} · até ${config.data.max_input_chars} chars da issue`
            : "Carregando configuração…"}
          {config.data && !config.data.publish_enabled && " · publicação desabilitada (sem GITHUB_TOKEN)"}
        </p>
        {!aiEnabled && config.data && (
          <p className="mt-2 text-sm text-destructive">
            Geração desabilitada: defina OPENCODE_API_KEY no servidor.
          </p>
        )}
      </section>

      {create.isError && <ErrorState error={create.error} />}
      {current && <SpecResult spec={current} onChange={setCurrent} />}

      <section className="mt-10">
        <div className="mb-3 flex items-center gap-2">
          <FileText className="size-4 text-muted-foreground" />
          <h2 className="eyebrow">Specs recentes</h2>
        </div>
        {specs.isPending && <p className="text-sm text-muted-foreground">Carregando…</p>}
        {specs.isError && <ErrorState error={specs.error} retry={() => specs.refetch()} />}
        {specs.data && specs.data.results.length === 0 && (
          <p className="text-sm text-muted-foreground">Nenhuma spec gerada ainda.</p>
        )}
        <ul className="panel divide-y divide-border overflow-hidden">
          {specs.data?.results.map((spec) => (
            <li key={spec.id}>
              <button
                type="button"
                className="flex w-full flex-wrap items-center gap-3 px-4 py-3 text-left transition hover:bg-muted/60"
                onClick={() => setCurrent(spec)}
              >
                <span className="min-w-0 flex-1 truncate text-sm font-medium">{spec.issue_title}</span>
                <Badge>size {spec.size}</Badge>
                <span className="font-mono text-[11px] text-muted-foreground">
                  {formatDate(spec.created_at.slice(0, 10))}
                </span>
                {spec.published && <Badge>publicada</Badge>}
              </button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
