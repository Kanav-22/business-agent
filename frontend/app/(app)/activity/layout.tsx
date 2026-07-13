import type { Metadata } from "next";
import { BRAND } from "@/lib/brand";

export const metadata: Metadata = {
  title: `${BRAND.name} — Agent Activity`,
  description: "Inspect agent runs, delegation, tools, token use, and cost.",
};

export default function ActivityLayout({ children }: { children: React.ReactNode }) {
  return children;
}
