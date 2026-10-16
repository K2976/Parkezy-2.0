import { NextResponse } from "next/server";
import { sql } from "@/lib/db";

export const dynamic = "force-dynamic";

type Status = "healthy" | "unhealthy" | "unreachable";

// Public endpoint: report up/down only. Database user, version and URLs stay out of the response.
export async function GET() {
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "https://parkezy-api.onrender.com";

  let backend: Status = "unreachable";
  try {
    const res = await fetch(`${backendUrl}/health/ready`, {
      signal: AbortSignal.timeout(4000),
      cache: "no-store",
    });
    backend = res.ok ? "healthy" : "unhealthy";
  } catch (err) {
    console.error("health: backend check failed", err);
  }

  let database: Status = "unreachable";
  try {
    await sql`SELECT 1`;
    database = "healthy";
  } catch (err) {
    console.error("health: database check failed", err);
  }

  const healthy = backend === "healthy" && database === "healthy";
  return NextResponse.json(
    {
      status: healthy ? "healthy" : "degraded",
      timestamp: new Date().toISOString(),
      services: { frontend: "healthy", backend, database },
    },
    { status: healthy ? 200 : 503 }
  );
}
