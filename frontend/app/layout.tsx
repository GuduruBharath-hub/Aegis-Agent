import type { Metadata } from 'next';
import './globals.css';
import { Sidebar } from '@/components/layout/Sidebar';

export const metadata: Metadata = {
  title: 'AegisAgent – AI Security Remediation',
  description: 'Autonomous AI-powered security vulnerability detection and remediation platform.',
  keywords: ['security', 'AI', 'vulnerability', 'remediation', 'SAST'],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" data-scroll-behavior="smooth">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body>
        <div className="app-root">
          <Sidebar />
          <div className="app-main">
            {children}
          </div>
        </div>
      </body>
    </html>
  );
}
