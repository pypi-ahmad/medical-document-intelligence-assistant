"use client";

import { FormEvent, useMemo, useState } from "react";
import { bootstrapAdmin, clearTokens, getAccessToken, login } from "@/lib/api";

export default function AuthPanel() {
  const [email, setEmail] = useState("admin@local");
  const [name, setName] = useState("Local Admin");
  const [password, setPassword] = useState("ChangeMeNow123!");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loggedIn, setLoggedIn] = useState<boolean>(() => Boolean(getAccessToken()));

  const buttonLabel = useMemo(() => (busy ? "Working..." : loggedIn ? "Logout" : "Login / Bootstrap"), [busy, loggedIn]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setBusy(true);

    try {
      if (loggedIn) {
        clearTokens();
        setLoggedIn(false);
        return;
      }
      try {
        await bootstrapAdmin({ email, full_name: name, password });
      } catch {
        // bootstrap may fail after first-run; login path then used.
        await login({ email, password });
      }
      setLoggedIn(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="card flex flex-wrap items-center gap-2 px-3 py-2" onSubmit={submit}>
      {!loggedIn && (
        <>
          <input
            className="rounded-md border px-2 py-1 text-sm text-black"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="Email"
            type="email"
            required
          />
          <input
            className="rounded-md border px-2 py-1 text-sm text-black"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Full name"
            type="text"
            required
          />
          <input
            className="rounded-md border px-2 py-1 text-sm text-black"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Password"
            type="password"
            required
          />
        </>
      )}
      <button className="rounded-md bg-teal-700 px-3 py-1.5 text-sm font-medium text-white" type="submit" disabled={busy}>
        {buttonLabel}
      </button>
      <span className={`text-xs ${loggedIn ? "text-emerald-600" : "text-amber-600"}`}>
        {loggedIn ? "Authenticated" : "Not authenticated"}
      </span>
      {error ? <p className="w-full text-xs text-red-600">{error}</p> : null}
    </form>
  );
}
