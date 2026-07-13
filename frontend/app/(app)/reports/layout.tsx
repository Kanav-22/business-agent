import type { Metadata } from "next";
import { BRAND } from "@/lib/brand";

export const metadata: Metadata = {
  title: `${BRAND.name} — Reports`,
  description: "Read business reports, briefings, reviews, and control checks.",
};

export default function ReportsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
