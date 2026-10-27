"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import AccountBar from "@/components/AccountBar";
import { useAuth } from "@/components/AuthProvider";
import ThemeToggle from "@/components/ThemeToggle";

/** The top bar on every page: brand, where you can go, theme, and who is signed in. */
export default function AppHeader() {
  const { candidate } = useAuth();
  const path = usePathname();
  const link = (href: string, label: string) => (
    <Link href={href} className="nav-link" aria-current={path === href ? "page" : undefined}>
      {label}
    </Link>
  );
  return (
    <header className="app-header">
      <div className="app-header-inner">
        <Link href="/" className="brand" aria-label="AI Interview Coach, home">
          <span className="brand-mark" aria-hidden="true">AI</span>
          <span className="brand-name">Interview Coach</span>
        </Link>
        {candidate && (
          <nav className="nav" aria-label="Main">
            {link("/", "Profile")}
            {link("/interview", "Interviews")}
          </nav>
        )}
        <div className="header-end">
          <ThemeToggle />
          <AccountBar />
        </div>
      </div>
    </header>
  );
}
