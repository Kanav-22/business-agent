import type { Metadata } from "next";
import { BRAND } from "@/lib/brand";

export const metadata: Metadata = {
  title: `${BRAND.name} — Venture Studio`,
  description: "Pressure-test ideas, route decisions, and build durable venture memory.",
};

export default function VentureLayout({ children }: { children: React.ReactNode }) {
  return children;
}
