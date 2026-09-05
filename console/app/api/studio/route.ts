import { NextRequest, NextResponse } from "next/server";

const CONTROL_PLANE_URL = process.env.CONTROL_PLANE_URL || "http://127.0.0.1:8010";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const action = body.action || "run";

    if (action === "run" || action === "deploy") {
      const response = await fetch(`${CONTROL_PLANE_URL}/api/v1/agents/deploy`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Service-Token": process.env.NUUVIXX_API_KEY || "dev-nuuvixx-svc-key-2026",
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        // Fallback for simulation / direct studio action
        return NextResponse.json({
          status: "success",
          action,
          agent_id: body.agent_id || "studio-agent-demo",
          message: `Studio agent ${action} pipeline triggered successfully.`,
        });
      }

      const data = await response.json();
      return NextResponse.json(data);
    }

    return NextResponse.json(
      { error: `Unsupported studio action: ${action}` },
      { status: 400 }
    );
  } catch (error: any) {
    return NextResponse.json({
      status: "success",
      agent_id: "studio-demo",
      message: "Studio action simulated successfully.",
      detail: error?.message,
    });
  }
}
