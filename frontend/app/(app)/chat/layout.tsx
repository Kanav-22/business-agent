import type { Metadata } from "next";
import { BRAND } from "@/lib/brand";

export const metadata: Metadata = {
  title: `${BRAND.name} — Chat with CEO`,
  description: "Ask the CEO agent and follow live delegation to the executive team.",
};

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  return children;
}
