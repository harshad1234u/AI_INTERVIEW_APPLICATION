"use client";

import { useCallback, useEffect, useState } from "react";
import { getHealth } from "@/lib/api";

type State = "checking" | "ok" | "degraded" | "unreachable";

const LABEL: Record<State, string> = {
  checking: "checking…",
  ok: "connected",
  degraded: "reachable, database unavailable",
  unreachable: "unreachable",
};

export default function BackendStatus() {
  const [state, setState] = useState<State>("checking");

  const check = useCallback(async (signal?: AbortSignal) => {
    setState("checking");
    try {
      const health = await getHealth(signal);
      setState(health.status === "ok" ? "ok" : "degraded");
    } catch {
      if (!signal?.aborted) setState("unreachable");
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch-on-mount
    check(controller.signal);
    return () => controller.abort();
  }, [check]);

  return (
    <p className="status" data-state={state} role="status" aria-live="polite">
      <span>
        Backend: <strong>{LABEL[state]}</strong>
      </span>
      {state !== "ok" && state !== "checking" && (
        <button type="button" onClick={() => check()}>
          Retry
        </button>
      )}
    </p>
  );
}
