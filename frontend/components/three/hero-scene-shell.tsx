"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

import { StaticHeroFallback } from "./static-hero-fallback";

const DynamicHeroScene = dynamic(
  () => import("./hero-scene").then((module) => module.HeroScene),
  {
    ssr: false,
    // The shell keeps one static underlay in place while this chunk arrives.
    loading: () => null,
  },
);

type SceneSupport = "checking" | "ready" | "reduced-motion" | "no-webgl";

function hasWebGLSupport() {
  try {
    const canvas = document.createElement("canvas");
    const attributes: WebGLContextAttributes = {
      alpha: true,
      failIfMajorPerformanceCaveat: true,
    };
    const context =
      canvas.getContext("webgl2", attributes) ?? canvas.getContext("webgl", attributes);

    if (!context) return false;
    context.getExtension("WEBGL_lose_context")?.loseContext();
    return true;
  } catch {
    return false;
  }
}

export type HeroSceneShellProps = {
  className?: string;
  /** Increment this number to launch one ripple wave from the CEO node. */
  pulseSignal?: number;
};

/** Client boundary that keeps Three.js out of the landing page's initial chunk. */
export function HeroSceneShell({ className = "h-full w-full", pulseSignal = 0 }: HeroSceneShellProps) {
  const [support, setSupport] = useState<SceneSupport>("checking");

  useEffect(() => {
    const media = window.matchMedia?.("(prefers-reduced-motion: reduce)");
    let webglSupported: boolean | undefined;

    const updateSupport = () => {
      if (media?.matches) {
        setSupport("reduced-motion");
        return;
      }

      webglSupported ??= hasWebGLSupport();
      setSupport(webglSupported ? "ready" : "no-webgl");
    };

    updateSupport();
    media?.addEventListener?.("change", updateSupport);
    return () => media?.removeEventListener?.("change", updateSupport);
  }, []);

  const fallbackReason =
    support === "reduced-motion"
      ? "reduced-motion"
      : support === "no-webgl"
        ? "no-webgl"
        : "loading";

  return (
    <div className={`relative isolate overflow-hidden ${className}`} data-hero-support={support}>
      <div className="absolute inset-0">
        <StaticHeroFallback reason={fallbackReason} />
      </div>
      {support === "ready" ? (
        <div className="absolute inset-0">
          <DynamicHeroScene className="h-full w-full" pulseSignal={pulseSignal} />
        </div>
      ) : null}
    </div>
  );
}

export default HeroSceneShell;
