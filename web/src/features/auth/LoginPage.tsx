import { useState } from "react";
import { useForm } from "react-hook-form";
import { LogIn } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";

type FormValues = { username: string; password: string };

export function LoginPage() {
  const { login } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const { register, handleSubmit } = useForm<FormValues>({
    defaultValues: { username: "", password: "" },
  });

  async function onSubmit(values: FormValues) {
    setBusy(true);
    setError(null);
    try {
      await login(values.username, values.password);
    } catch {
      setError("Invalid username or password.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="grid min-h-dvh place-items-center px-4 py-10">
      <section className="panel w-full max-w-sm p-7">
        <p className="eyebrow">BLT</p>
        <h1 className="text-3xl">Sign <span className="text-link">in</span></h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Sign in to manage your tasks.
        </p>

        <form className="mt-6 space-y-4" onSubmit={handleSubmit(onSubmit)}>
          <label className="block space-y-1.5">
            <span className="eyebrow">Username</span>
            <input className="field" autoComplete="username" autoFocus {...register("username")} />
          </label>
          <label className="block space-y-1.5">
            <span className="eyebrow">Password</span>
            <input
              type="password"
              className="field"
              autoComplete="current-password"
              {...register("password")}
            />
          </label>

          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}

          <Button type="submit" className="w-full" disabled={busy}>
            <LogIn />
            {busy ? "Signing in…" : "Sign in"}
          </Button>
        </form>
      </section>
    </main>
  );
}
