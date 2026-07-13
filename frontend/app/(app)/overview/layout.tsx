import type { Metadata } from "next";
import { BRAND } from "@/lib/brand";

export const metadata: Metadata = {
  title: `${BRAND.name} — Overview`,
  description: "Business performance, cash, customers, and operating priorities.",
};

export default function OverviewLayout({ children }: { children: React.ReactNode }) {
  return children;
}
