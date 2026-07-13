import type { Metadata } from "next";
import { BRAND } from "@/lib/brand";

export const metadata: Metadata = {
  title: `${BRAND.name} — Approvals`,
  description: "Review and approve outward-facing work before publication.",
};

export default function ApprovalsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
