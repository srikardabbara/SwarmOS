'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import type { ReactNode } from 'react';

const links = [
  { href: '/', label: 'Runs' },
  { href: '/flow', label: 'How it works' },
  { href: '/start', label: 'Instructions' },
];

function isCurrent(pathname: string, href: string) {
  if (href === '/') return pathname === '/' || pathname.startsWith('/traces');
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function SiteHeader({ actions }: { actions?: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="border-b border-slate-700/50 bg-slate-900/50 backdrop-blur">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <Link
              href="/"
              className="text-3xl font-bold bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent"
            >
              SwarmOS
            </Link>
            <p className="text-slate-400 mt-1">The handoff layer on LangGraph and LangSmith</p>
          </div>
          <nav className="flex flex-wrap items-center justify-end gap-3">
            {links.map((link) => {
              const current = isCurrent(pathname, link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  aria-current={current ? 'page' : undefined}
                  className={
                    current
                      ? 'px-4 py-2 bg-purple-500/20 border border-purple-400/40 rounded-lg text-purple-100'
                      : 'px-4 py-2 bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/50 rounded-lg text-slate-200 transition-colors'
                  }
                >
                  {link.label}
                </Link>
              );
            })}
            {actions}
          </nav>
        </div>
      </div>
    </div>
  );
}
