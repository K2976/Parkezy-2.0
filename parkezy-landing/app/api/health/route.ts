import { NextResponse } from "next/server";
import { sql } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET() {
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "https://parkezy-api.onrender.com";
  let backendStatus: any = { status: "unknown" };

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 4000);
    const res = await fetch(`${backendUrl}/health/ready`, {
      signal: controller.signal,
      cache: "no-store",
    });
    clearTimeout(timeout);
    if (res.ok) {
      backendStatus = {
        status: "healthy",
        url: backendUrl,
        response: await res.json(),
      };
    } else {
      backendStatus = {
        status: "unhealthy",
        statusCode: res.status,
        url: backendUrl,
      };
    }
  } catch (err: any) {
    backendStatus = {
      status: "unreachable",
      url: backendUrl,
      error: err?.message,
    };
  }

  let dbStatus: any = { status: "unknown" };
  try {
    const result = await sql`
      SELECT 
        current_database() as database,
        split_part(version(), ' ', 2) as postgres_version,
        NOW() as server_time,
        current_user as db_user
    `;
    dbStatus = {
      status: "healthy",
      service: "Neon Postgres",
      branch: process.env.NEON_BRANCH || "production",
      database: result[0]?.database,
      version: result[0]?.postgres_version,
      timestamp: result[0]?.server_time,
      user: result[0]?.db_user,
    };
  } catch (error: any) {
    dbStatus = {
      status: "error",
      service: "Neon Postgres",
      error: error?.message || "Database connection failed",
    };
  }

  const overallHealthy = dbStatus.status === "healthy" && backendStatus.status === "healthy";

  return NextResponse.json(
    {
      status: overallHealthy ? "healthy" : "degraded",
      timestamp: new Date().toISOString(),
      services: {
        frontend: {
          platform: "Vercel",
          status: "healthy",
        },
        backend: backendStatus,
        database: dbStatus,
      },
    },
    { status: overallHealthy ? 200 : 207 }
  );
}
