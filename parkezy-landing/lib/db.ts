import { neon } from "@neondatabase/serverless";

const databaseUrl = process.env.DATABASE_URL || process.env.DATABASE_URL_UNPOOLED;

if (!databaseUrl) {
  console.warn("WARNING: DATABASE_URL is not set. Ensure Neon env vars are loaded.");
}

export const sql = neon(databaseUrl || "");
