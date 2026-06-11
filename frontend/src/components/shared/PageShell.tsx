import { SideNav } from "./SideNav";

interface PageShellProps {
  children: React.ReactNode;
}

export function PageShell({ children }: PageShellProps) {
  return (
    <div className="page-shell">
      <SideNav />
      <main className="main-content fade-up">{children}</main>
    </div>
  );
}