import type { Metadata } from "next";
import { BRAND } from "@/lib/brand";

export const metadata: Metadata = {
  title: `${BRAND.name} — Business Setup`,
  description: "Teach the executive team how the business works.",
};

export default function OnboardingLayout({ children }: { children: React.ReactNode }) {
  return children;
}
