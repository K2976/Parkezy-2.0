export type DocLink = { slug: string; title: string; summary: string; group: string };

export const DOCS: DocLink[] = [
  { slug: "", title: "Overview", summary: "What Parkezy is and how the pieces fit together", group: "Start here" },
  { slug: "architecture", title: "Architecture", summary: "Services, data stores, deployment and the life of a request", group: "Start here" },
  { slug: "system-design", title: "System design notes", summary: "Which classic system design ideas we used, and where", group: "Start here" },
  { slug: "booking", title: "Booking engine", summary: "State machine, zero double-booking and idempotent retries", group: "Core flows" },
  { slug: "search", title: "Proximity search", summary: "PostGIS, geohash cells and a cache nearby users share", group: "Core flows" },
  { slug: "payments", title: "Payments & ledger", summary: "Razorpay, webhooks, reconciliation and double-entry accounting", group: "Core flows" },
  { slug: "access", title: "QR & PIN access", summary: "Contactless check-in with one-time QR tokens and offline PINs", group: "Core flows" },
  { slug: "notifications", title: "Outbox & notifications", summary: "Transactional outbox, workers, retries and email", group: "Core flows" },
  { slug: "security", title: "Security", summary: "Passwords, sessions, rate limits and login abuse protection", group: "Quality" },
  { slug: "reliability", title: "Load tests & reliability", summary: "What we measured, what broke, and what we fixed", group: "Quality" },
  { slug: "mobile", title: "Mobile app & interfaces", summary: "The Expo app, its screens and how it talks to the API", group: "Clients" },
  { slug: "api", title: "API reference", summary: "Every endpoint group, the error contract and examples", group: "Clients" },
];

export const docHref = (slug: string) => (slug ? `/docs/${slug}` : "/docs");

export function neighbours(slug: string) {
  const i = DOCS.findIndex((d) => d.slug === slug);
  return { prev: i > 0 ? DOCS[i - 1] : null, next: i >= 0 && i < DOCS.length - 1 ? DOCS[i + 1] : null };
}
