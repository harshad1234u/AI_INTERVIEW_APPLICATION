import type { CSSProperties } from "react";

export type CoreState = "idle" | "speaking" | "listening";

/** A decorative 3D "AI core": a glossy sphere, three tilted rings and six orbiting shards, built
 * from plain CSS 3D transforms (no WebGL, no library), so it renders on any device. It follows the
 * pointer a little and reacts to `state` (the interviewer speaking or listening). Its size is the
 * element's font-size: everything inside is in em. */
export default function Core3D({ state = "idle", className = "" }: { state?: CoreState; className?: string }) {
  return (
    <div className={`core3d ${className}`.trim()} data-state={state} aria-hidden="true">
      <div className="core3d-scene">
        <div className="core3d-halo" />
        <div className="core3d-ring r1" />
        <div className="core3d-ring r2" />
        <div className="core3d-ring r3" />
        <div className="core3d-orbit">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <span key={i} className="core3d-shard" style={{ "--i": i } as CSSProperties} />
          ))}
        </div>
        <div className="core3d-sphere"><span className="core3d-gloss" /></div>
      </div>
    </div>
  );
}
