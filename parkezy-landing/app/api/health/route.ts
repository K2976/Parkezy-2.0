import { NextResponse } from "next/server";
import { sql } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const result = await sql`
      SELECT 
        current_database() as database,
        split_part(version(), ' ', 2) as postgres_version,
        NOW() as server_time,
        current_user as db_user
    `;

    return NextResponse.json({
      status: "healthy",
      service: "Neon Postgres",
      branch: process.env.NEON_BRANCH || "production",
      database: result[0]?.database,
      version: result[0]?.postgres_version,
      timestamp: result[0]?.server_time,
      user: result[0]?.db_user,
    });
  } catch (error: any) {
    return NextResponse.json(
      {
        status: "error",
        service: "Neon Postgres",
        error: error?.message || "Database connection failed",
      },
      { status: 500 }
    );
  }
}
