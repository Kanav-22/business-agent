import { Sidebar } from "@/components/sidebar";

export default function ProductLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh bg-slate-950">
      <Sidebar />
      <main id="main-content" className="min-w-0 flex-1">
        {children}
      </main>
    </div>
  );
}
