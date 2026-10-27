"use client";

import { useEffect } from "react";

/** Pointer-driven depth, with no per-frame React work: one listener sets CSS variables.
 *  --mx / --my (-1..1, on <html>) steer the 3D core; an element with data-tilt leans toward the
 *  pointer through --rx / --ry. Off for reduced motion and for touch-only devices. */
export default function MotionEffects() {
  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const hover = window.matchMedia("(hover: hover)").matches;
    if (reduced || !hover) return;
    const root = document.documentElement;
    let frame = 0;
    let last: PointerEvent | null = null;
    let tilted: HTMLElement | null = null;
    const rest = (el: HTMLElement) => {
      el.style.removeProperty("--rx");
      el.style.removeProperty("--ry");
    };
    const apply = () => {
      frame = 0;
      const e = last;
      if (!e) return;
      root.style.setProperty("--mx", ((e.clientX / window.innerWidth) * 2 - 1).toFixed(3));
      root.style.setProperty("--my", ((e.clientY / window.innerHeight) * 2 - 1).toFixed(3));
      const target = (e.target as Element | null)?.closest?.<HTMLElement>("[data-tilt]") ?? null;
      if (tilted && tilted !== target) rest(tilted);
      tilted = target;
      if (target) {
        const box = target.getBoundingClientRect();
        const px = (e.clientX - box.left) / box.width - 0.5;
        const py = (e.clientY - box.top) / box.height - 0.5;
        target.style.setProperty("--rx", `${(-py * 12).toFixed(2)}deg`);
        target.style.setProperty("--ry", `${(px * 14).toFixed(2)}deg`);
      }
    };
    const onMove = (e: PointerEvent) => {
      last = e;
      if (!frame) frame = requestAnimationFrame(apply);
    };
    const onLeave = () => {
      if (tilted) rest(tilted);
      tilted = null;
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    document.addEventListener("pointerleave", onLeave);
    return () => {
      window.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerleave", onLeave);
      if (frame) cancelAnimationFrame(frame);
    };
  }, []);
  return null;
}
