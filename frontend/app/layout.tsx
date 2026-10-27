import type { Metadata } from "next";
import AppHeader from "@/components/AppHeader";
import AuthProvider from "@/components/AuthProvider";
import MotionEffects from "@/components/MotionEffects";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Interview Coach",
  description:
    "Practice realistic, role-specific interviews and understand exactly how to improve.",
};

// Runs before the first paint so the page never flashes the wrong theme: the saved choice, else
// light (a dark theme is one click away in the header).
const THEME_SCRIPT = `try{var t=localStorage.getItem("coach.theme");if(t!=="light"&&t!=="dark"){t="light"}document.documentElement.dataset.theme=t}catch(e){document.documentElement.dataset.theme="light"}`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body>
        <div className="bg-blobs" aria-hidden="true"><span /><span /><span /></div>
        <MotionEffects />
        <AuthProvider>
          <a className="skip-link" href="#content">Skip to the content</a>
          <AppHeader />
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
