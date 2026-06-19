"use client";

import Link from "next/link";
import { useCan } from "./UserContext";

/** A link that renders only when the current user's role grants ``cap``. */
export function CapLink({
  cap,
  href,
  className,
  children,
}: {
  cap: string;
  href: string;
  className?: string;
  children: React.ReactNode;
}) {
  if (!useCan(cap)) return null;
  return (
    <Link href={href} className={className}>
      {children}
    </Link>
  );
}
