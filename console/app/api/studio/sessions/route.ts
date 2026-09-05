import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export const dynamic = "force-dynamic";

const MAX_FREE_AGENTS = 5;

// Data directory for persistent server-side sessions storage
const STORAGE_DIR = process.env.STUDIO_STORAGE_DIR || path.join(process.cwd(), ".studio_storage");

function getStorageFilePath(userId: string): string {
  const safeId = userId.replace(/[^a-zA-Z0-9_-]/g, "_");
  return path.join(STORAGE_DIR, `user_${safeId}.json`);
}

interface UserStorageData {
  sessions: any[];
  files: Record<string, Record<string, string>>;
  tier: "Free" | "Pro" | "Enterprise";
  updatedAt: number;
}

function readUserData(userId: string): UserStorageData {
  try {
    if (!fs.existsSync(STORAGE_DIR)) {
      fs.mkdirSync(STORAGE_DIR, { recursive: true });
    }
    const filePath = getStorageFilePath(userId);
    if (!fs.existsSync(filePath)) {
      return { sessions: [], files: {}, tier: "Free", updatedAt: Date.now() };
    }
    const raw = fs.readFileSync(filePath, "utf-8");
    return JSON.parse(raw);
  } catch (err) {
    console.warn(`Failed reading studio data for user ${userId}:`, err);
    return { sessions: [], files: {}, tier: "Free", updatedAt: Date.now() };
  }
}

function writeUserData(userId: string, data: UserStorageData): void {
  try {
    if (!fs.existsSync(STORAGE_DIR)) {
      fs.mkdirSync(STORAGE_DIR, { recursive: true });
    }
    const filePath = getStorageFilePath(userId);
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2), "utf-8");
  } catch (err) {
    console.error(`Failed writing studio data for user ${userId}:`, err);
  }
}

function resolveUserId(req: NextRequest, bodyOrQuery?: any): { userId: string; tier: "Free" | "Pro" | "Enterprise" } {
  // 1. From Authorization Header or Custom X-User-Id
  const customUser = req.headers.get("x-user-id") || req.headers.get("x-user-email");
  const customTier = (req.headers.get("x-user-tier") as any) || "Free";
  if (customUser) {
    return { userId: customUser.trim(), tier: customTier === "Pro" || customTier === "Enterprise" ? customTier : "Free" };
  }

  // 2. From body or query params
  if (bodyOrQuery?.userId) {
    return {
      userId: String(bodyOrQuery.userId).trim(),
      tier: bodyOrQuery.tier === "Pro" || bodyOrQuery.tier === "Enterprise" ? bodyOrQuery.tier : "Free",
    };
  }

  const url = new URL(req.url);
  const qUser = url.searchParams.get("userId");
  const qTier = url.searchParams.get("tier") as any;
  if (qUser) {
    return { userId: qUser.trim(), tier: qTier === "Pro" || qTier === "Enterprise" ? qTier : "Free" };
  }

  return { userId: "default_workspace_user", tier: "Free" };
}

/**
 * GET /api/studio/sessions
 * Returns all sessions and files for the authenticated user
 */
export async function GET(req: NextRequest) {
  try {
    const { userId, tier } = resolveUserId(req);
    const data = readUserData(userId);

    return NextResponse.json({
      success: true,
      userId,
      tier: data.tier || tier,
      maxFreeAgents: MAX_FREE_AGENTS,
      sessions: data.sessions || [],
      files: data.files || {},
    });
  } catch (err: any) {
    return NextResponse.json(
      { success: false, error: err?.message || "Failed to fetch studio sessions" },
      { status: 500 }
    );
  }
}

/**
 * POST /api/studio/sessions
 * Creates or updates a studio session and its workspace files.
 * Enforces Free plan limit of 5 agents.
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { session, files, isNew } = body;
    const { userId, tier } = resolveUserId(req, body);

    if (!session || !session.id) {
      return NextResponse.json({ error: "Session payload with id is required" }, { status: 400 });
    }

    const userData = readUserData(userId);
    const currentSessions = userData.sessions || [];
    const isExisting = currentSessions.some((s) => s.id === session.id);

    // Enforce 5-agent Free Plan Limit on new creations
    const effectiveTier = body.tier || userData.tier || tier;
    if (effectiveTier === "Free" && (isNew || !isExisting)) {
      if (currentSessions.length >= MAX_FREE_AGENTS) {
        return NextResponse.json(
          {
            error: `Free plan limit reached. You can create a maximum of ${MAX_FREE_AGENTS} agents on the Free plan. Upgrade to Pro for unlimited agents.`,
            code: "TIER_LIMIT_REACHED",
            currentCount: currentSessions.length,
            limit: MAX_FREE_AGENTS,
          },
          { status: 403 }
        );
      }
    }

    // Upsert session
    const idx = currentSessions.findIndex((s) => s.id === session.id);
    let updatedSessions: any[];
    if (idx >= 0) {
      updatedSessions = [...currentSessions];
      updatedSessions[idx] = { ...updatedSessions[idx], ...session, updatedAt: Date.now() };
    } else {
      updatedSessions = [{ ...session, createdAt: Date.now(), updatedAt: Date.now() }, ...currentSessions];
    }

    // Upsert files if provided
    const userFiles = userData.files || {};
    if (files && typeof files === "object") {
      userFiles[session.id] = files;
    }

    const newData: UserStorageData = {
      sessions: updatedSessions,
      files: userFiles,
      tier: effectiveTier,
      updatedAt: Date.now(),
    };

    writeUserData(userId, newData);

    return NextResponse.json({
      success: true,
      message: `Session ${session.id} synced successfully`,
      session: updatedSessions.find((s) => s.id === session.id),
      totalSessions: updatedSessions.length,
      maxFreeAgents: MAX_FREE_AGENTS,
    });
  } catch (err: any) {
    return NextResponse.json(
      { success: false, error: err?.message || "Failed to save studio session" },
      { status: 500 }
    );
  }
}

/**
 * DELETE /api/studio/sessions?id=<sessionId>
 * Deletes a studio session and its workspace files
 */
export async function DELETE(req: NextRequest) {
  try {
    const url = new URL(req.url);
    const sessionId = url.searchParams.get("id");
    const { userId } = resolveUserId(req);

    if (!sessionId) {
      return NextResponse.json({ error: "Session id query parameter is required" }, { status: 400 });
    }

    const userData = readUserData(userId);
    const currentSessions = userData.sessions || [];
    const updatedSessions = currentSessions.filter((s) => s.id !== sessionId);

    const userFiles = userData.files || {};
    delete userFiles[sessionId];

    const newData: UserStorageData = {
      ...userData,
      sessions: updatedSessions,
      files: userFiles,
      updatedAt: Date.now(),
    };

    writeUserData(userId, newData);

    return NextResponse.json({
      success: true,
      message: `Session ${sessionId} removed successfully`,
      totalSessions: updatedSessions.length,
    });
  } catch (err: any) {
    return NextResponse.json(
      { success: false, error: err?.message || "Failed to delete studio session" },
      { status: 500 }
    );
  }
}
