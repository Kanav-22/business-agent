import type { Metadata } from "next";
import "./globals.css";
import { BRAND } from "@/lib/brand";

const FAVICON = `data:image/svg+xml,${encodeURIComponent(
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#0a0f1a"/><path d="M24 5 41 14.8v18.4L24 43 7 33.2V14.8L24 5Z" fill="none" stroke="#a78bfa" stroke-width="2"/><path d="m24 15 8 4.6v8.8L24 33l-8-4.6v-8.8L24 15Z" fill="none" stroke="#22d3ee" stroke-width="1.5"/><circle cx="24" cy="24" r="4" fill="#a78bfa"/></svg>',
)}`;

export const metadata: Metadata = {
  title: BRAND.name,
  description: BRAND.tagline,
  icons: { icon: [{ url: FAVICON, type: "image/svg+xml" }] },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <a
          href="#main-content"
          className="fixed left-3 top-3 z-[100] -translate-y-20 rounded-lg bg-violet-400 px-4 py-3 text-sm font-semibold text-slate-950 transition-transform focus:translate-y-0 motion-reduce:transition-none"
        >
          Skip to content
        </a>
        {children}
      </body>
    </html>
  );
}
