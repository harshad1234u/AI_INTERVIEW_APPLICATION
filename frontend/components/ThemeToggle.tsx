"use client";

import { useSyncExternalStore } from "react";

type Theme = "light" | "dark";
const KEY = "coach.theme";

// The theme lives on <html data-theme>. An inline script in the layout sets it before the first
// paint (from the saved choice, else the device setting); this button changes it and saves the
// choice. Storage may be blocked: the choice then lasts for this visit only.
const read = (): Theme => (document.documentElement.dataset.theme === "dark" ? "dark" : "light");
const subscribe = (notify: () => void) => {
  const observer = new MutationObserver(notify);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => observer.disconnect();
};

export default function ThemeToggle() {
  const theme = useSyncExternalStore(subscribe, read, () => "light" as Theme);
  const next: Theme = theme === "dark" ? "light" : "dark";
  return (
    <button type="button" className="icon-button" aria-label={`Switch to ${next} theme`}
            title={`Switch to ${next} theme`}
            onClick={() => {
              document.documentElement.dataset.theme = next;
              try {
                window.localStorage.setItem(KEY, next);
              } catch {
                /* blocked: applies to this visit */
              }
            }}>
      <span aria-hidden="true">{theme === "dark" ? "☀" : "☾"}</span>
    </button>
  );
}
