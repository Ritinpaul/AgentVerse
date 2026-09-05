import { NextRequest, NextResponse } from "next/server";
import { STORE_API_URL } from "@/lib/api";
import { STARTER_TEMPLATES, StarterTemplate } from "@/lib/templates";

export const dynamic = "force-dynamic";

/**
 * GET /api/templates
 * Fetches dynamic templates with capability tagging from AgentStore.
 * Falls back seamlessly to local STARTER_TEMPLATES if AgentStore is offline.
 */
export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const category = searchParams.get("category");
  const capability = searchParams.get("capability");
  const search = searchParams.get("search");

  try {
    const storeQuery = new URLSearchParams();
    if (category) storeQuery.set("category", category);
    if (capability) storeQuery.set("capability", capability);
    if (search) storeQuery.set("search", search);
    storeQuery.set("include_files", "true");

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2500); // 2.5s quick timeout

    const storeRes = await fetch(`${STORE_API_URL}/api/v1/registry/templates?${storeQuery.toString()}`, {
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
      },
      next: { revalidate: 60 }, // Cache 60s
    });

    clearTimeout(timeoutId);

    if (storeRes.ok) {
      const storeData = await storeRes.json();
      if (Array.isArray(storeData) && storeData.length > 0) {
        return NextResponse.json({
          source: "agentstore",
          templates: storeData,
        });
      }
    }
  } catch (err) {
    // AgentStore offline or timeout — fall back gracefully to local catalog
  }

  // Local fallback transformation
  let localList: StarterTemplate[] = Object.values(STARTER_TEMPLATES);

  if (category && category.toLowerCase() !== "all") {
    localList = localList.filter((t) =>
      t.category.toLowerCase().includes(category.toLowerCase())
    );
  }

  if (capability) {
    const capLower = capability.toLowerCase();
    localList = localList.filter((t) =>
      t.capabilities.some((c) => c.toLowerCase().includes(capLower))
    );
  }

  if (search) {
    const sLower = search.toLowerCase();
    localList = localList.filter(
      (t) =>
        t.name.toLowerCase().includes(sLower) ||
        t.description.toLowerCase().includes(sLower) ||
        t.capabilities.some((c) => c.toLowerCase().includes(sLower))
    );
  }

  return NextResponse.json({
    source: "local-fallback",
    templates: localList,
  });
}

/**
 * POST /api/templates
 * 1-Click Fork: Interpolates template files with agent name and slug.
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { templateId, name, slug } = body;

    if (!templateId || !name) {
      return NextResponse.json(
        { error: "templateId and name are required." },
        { status: 400 }
      );
    }

    const agentSlug = (slug || name).trim().toLowerCase().replace(/\s+/g, "-");

    // Try server-side fork on AgentStore first
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2500);

      const storeRes = await fetch(`${STORE_API_URL}/api/v1/registry/templates/${templateId}/fork`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, slug: agentSlug }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (storeRes.ok) {
        const forked = await storeRes.json();
        return NextResponse.json(forked);
      }
    } catch {
      // Fall through to local fallback fork
    }

    // Local fallback fork
    const tpl = STARTER_TEMPLATES[templateId] || STARTER_TEMPLATES.custom;
    const generatedFiles = tpl.files(name.trim(), agentSlug);

    return NextResponse.json({
      id: agentSlug,
      name: name.trim(),
      slug: agentSlug,
      category: tpl.category,
      template_id: templateId,
      recommended_model: tpl.recommendedModel || "gemini-2.0-flash",
      files: generatedFiles,
      message: `Agent '${name}' successfully forked from template '${templateId}'.`,
    });
  } catch (error: any) {
    return NextResponse.json(
      { error: error?.message || "Failed to fork template." },
      { status: 500 }
    );
  }
}
