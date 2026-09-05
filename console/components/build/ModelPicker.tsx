"use client";

import React, { useState, useEffect } from "react";
import AutoAwesomeRoundedIcon from "@mui/icons-material/AutoAwesomeRounded";
import CheckRoundedIcon from "@mui/icons-material/CheckRounded";
import KeyRoundedIcon from "@mui/icons-material/KeyRounded";
import UnfoldMoreRoundedIcon from "@mui/icons-material/UnfoldMoreRounded";
import AddRoundedIcon from "@mui/icons-material/AddRounded";
import PsychologyRoundedIcon from "@mui/icons-material/PsychologyRounded";
import CodeRoundedIcon from "@mui/icons-material/CodeRounded";
import AnalyticsRoundedIcon from "@mui/icons-material/AnalyticsRounded";
import SpeedRoundedIcon from "@mui/icons-material/SpeedRounded";
import LayersRoundedIcon from "@mui/icons-material/LayersRounded";
import ShieldRoundedIcon from "@mui/icons-material/ShieldRounded";
import BoltRoundedIcon from "@mui/icons-material/BoltRounded";

import { FREE_MODELS, BYOK_MODELS, ModelDef } from "@/lib/autoroute";
import { getActiveProviders, ProviderKey, PROVIDER_META } from "@/lib/modelKeys";

interface ModelPickerProps {
  selectedModelId: string | null; // null = Auto
  onSelectModel: (modelId: string | null) => void;
  onOpenKeyModal?: () => void;
  dropdownPlacement?: "top" | "bottom";
}

// Helper to return professional icons and theme colors for models
function getModelIcon(modelId: string, provider: string) {
  if (modelId.includes("r1")) {
    return { icon: <PsychologyRoundedIcon sx={{ fontSize: 14 }} />, color: "#A855F7" }; // Reasoning - Purple
  }
  if (modelId.includes("v3") || modelId.includes("coder")) {
    return { icon: <CodeRoundedIcon sx={{ fontSize: 14 }} />, color: "#3B82F6" }; // Coding - Blue
  }
  if (modelId.includes("glm") || modelId.includes("qwen")) {
    return { icon: <AnalyticsRoundedIcon sx={{ fontSize: 14 }} />, color: "#10B981" }; // Analysis - Emerald
  }
  if (modelId.includes("mistral") || modelId.includes("8b")) {
    return { icon: <SpeedRoundedIcon sx={{ fontSize: 14 }} />, color: "#F97316" }; // Speed - Orange
  }
  if (modelId.includes("llama")) {
    return { icon: <LayersRoundedIcon sx={{ fontSize: 14 }} />, color: "#EC4899" }; // Meta Llama - Pink
  }
  if (provider === "anthropic" || modelId.includes("claude")) {
    return { icon: <ShieldRoundedIcon sx={{ fontSize: 14 }} />, color: "#F97316" }; // Anthropic - Amber/Orange
  }
  if (provider === "openai" || modelId.includes("gpt")) {
    return { icon: <BoltRoundedIcon sx={{ fontSize: 14 }} />, color: "#10B981" }; // OpenAI - Emerald
  }
  if (provider === "gemini") {
    return { icon: <AutoAwesomeRoundedIcon sx={{ fontSize: 14 }} />, color: "#3B82F6" }; // Gemini - Blue
  }

  return { icon: <AutoAwesomeRoundedIcon sx={{ fontSize: 14 }} />, color: "#E5C07B" };
}

export function ModelPicker({
  selectedModelId,
  onSelectModel,
  onOpenKeyModal,
  dropdownPlacement = "top",
}: ModelPickerProps) {
  const [open, setOpen] = useState(false);
  const [activeProviders, setActiveProviders] = useState<ProviderKey[]>([]);

  useEffect(() => {
    setActiveProviders(getActiveProviders());
  }, [open]);

  const isAuto = selectedModelId === null;
  const currentModel = [...FREE_MODELS, ...BYOK_MODELS].find((m) => m.id === selectedModelId);

  const displayLabel = isAuto ? "Auto (Smart Router)" : currentModel?.label ?? selectedModelId;
  const activeIconInfo = isAuto
    ? { icon: <AutoAwesomeRoundedIcon sx={{ fontSize: 13, color: "#E5C07B" }} />, color: "#E5C07B" }
    : getModelIcon(currentModel?.id ?? "", currentModel?.provider ?? "");

  const popoverPosClass =
    dropdownPlacement === "bottom" ? "top-full mt-2 left-0" : "bottom-full mb-2 left-0";

  return (
    <div className="relative font-sans inline-block">
      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[#16161C] border border-[#272732] hover:border-[#3F3F4E] text-neutral-200 text-xs font-sans font-medium rounded-full transition-all cursor-pointer shadow-xs max-w-[150px] sm:max-w-[220px] min-w-0"
      >
        <span className="truncate font-semibold text-white min-w-0 flex-1 text-left">{displayLabel}</span>
        {isAuto && (
          <span className="text-[9px] font-bold px-1.5 py-0.2 bg-[#E5C07B]/15 text-[#E5C07B] rounded border border-[#E5C07B]/30 uppercase shrink-0">
            FREE
          </span>
        )}
        <UnfoldMoreRoundedIcon sx={{ fontSize: 13, color: "#71717A" }} className="shrink-0" />
      </button>

      {/* Popover Dropdown Menu */}
      {open && (
        <div
          className={`absolute ${popoverPosClass} w-72 bg-[#121318] border border-[#272732] rounded-xl shadow-2xl p-1.5 z-[100] animate-in fade-in zoom-in-95 duration-100 max-h-[210px] overflow-y-auto`}
        >
          {/* AUTO ROUTE OPTION */}
          <div className="px-2.5 py-1 text-[10px] uppercase font-bold text-neutral-500 tracking-wider font-sans border-b border-[#1E1E28] mb-1 flex justify-between items-center">
            <span>SMART ROUTER</span>
            <span className="text-[9px] text-[#E5C07B] font-mono font-bold">RECOMMENDED</span>
          </div>

          <button
            type="button"
            onClick={() => {
              onSelectModel(null);
              setOpen(false);
            }}
            className={`w-full text-left px-2.5 py-2 text-xs rounded-lg flex items-center justify-between transition-all ${
              isAuto
                ? "bg-[#1C1C26] text-white font-bold border border-[#E5C07B]/40"
                : "text-neutral-300 hover:text-white hover:bg-[#161620]"
            }`}
          >
            <div>
              <div className="font-semibold text-white">Auto (Smart Router)</div>
              <div className="text-[10px] text-neutral-400 font-normal">
                Auto-routes to best model for prompt
              </div>
            </div>
            {isAuto && <CheckRoundedIcon sx={{ fontSize: 14, color: "#10B981" }} />}
          </button>

          {/* FREE MODELS TIER */}
          <div className="px-2.5 py-1 text-[10px] uppercase font-bold text-neutral-400 tracking-wider font-sans border-b border-[#1E1E28] mt-2.5 mb-1 flex justify-between items-center">
            <span>FREE MODELS (DAILY CREDIT TIER)</span>
            <span className="text-[9px] text-[#10B981] font-mono font-bold">50K DAILY</span>
          </div>

          {FREE_MODELS.map((model) => {
            const isSelected = selectedModelId === model.id;

            return (
              <button
                key={model.id}
                type="button"
                onClick={() => {
                  onSelectModel(model.id);
                  setOpen(false);
                }}
                className={`w-full text-left px-2.5 py-1.5 text-xs rounded-lg flex items-center justify-between transition-all ${
                  isSelected
                    ? "bg-[#1C1C26] text-white font-bold border border-[#272732]"
                    : "text-neutral-400 hover:text-white hover:bg-[#161620]"
                }`}
              >
                <span className="truncate">{model.label}</span>
                <div className="flex items-center gap-1.5 shrink-0">
                  <span className="text-[9px] px-1.5 py-0.2 bg-[#10B981]/15 text-[#10B981] rounded border border-[#10B981]/30 font-bold font-mono">
                    FREE
                  </span>
                  {isSelected && <CheckRoundedIcon sx={{ fontSize: 14, color: "#10B981" }} />}
                </div>
              </button>
            );
          })}

          {/* BYOK MODELS TIER */}
          <div className="px-2.5 py-1 text-[10px] uppercase font-bold text-neutral-500 tracking-wider font-sans border-b border-[#1E1E28] mt-2.5 mb-1 flex justify-between items-center">
            <span>BYOK MODELS (YOUR KEYS)</span>
            <span className="text-[9px] text-neutral-400 font-mono">
              {activeProviders.length} active
            </span>
          </div>

          {BYOK_MODELS.map((model) => {
            const isSelected = selectedModelId === model.id;
            const hasKeyForProvider = activeProviders.includes(model.provider as ProviderKey);
            const providerInfo = PROVIDER_META.find((p) => p.id === model.provider);

            return (
              <button
                key={model.id}
                type="button"
                onClick={() => {
                  onSelectModel(model.id);
                  setOpen(false);
                }}
                className={`w-full text-left px-2.5 py-1.5 text-xs rounded-lg flex items-center justify-between transition-all ${
                  isSelected
                    ? "bg-[#1C1C26] text-white font-bold border border-[#272732]"
                    : "text-neutral-400 hover:text-white hover:bg-[#161620]"
                }`}
              >
                <span className="truncate">{model.label}</span>
                <div className="flex items-center gap-1.5 shrink-0">
                  {hasKeyForProvider ? (
                    <span className="text-[9px] text-[#10B981] font-mono flex items-center gap-0.5 font-bold">
                      <KeyRoundedIcon sx={{ fontSize: 10 }} /> ACTIVE
                    </span>
                  ) : (
                    <span
                      className="text-[9px] px-1.5 py-0.2 rounded border font-mono"
                      style={{
                        color: providerInfo?.color ?? "#888",
                        borderColor: `${providerInfo?.color ?? "#888"}40`,
                        backgroundColor: `${providerInfo?.color ?? "#888"}15`,
                      }}
                    >
                      KEY REQ
                    </span>
                  )}
                  {isSelected && <CheckRoundedIcon sx={{ fontSize: 14, color: "#10B981" }} />}
                </div>
              </button>
            );
          })}

          {/* ADD KEY CTA BUTTON */}
          <div className="pt-2 border-t border-[#1E1E28] mt-1.5">
            <button
              type="button"
              onClick={() => {
                setOpen(false);
                onOpenKeyModal?.();
              }}
              className="w-full py-1.5 px-2 bg-[#1A1A24] hover:bg-[#222230] border border-[#2A2A3A] text-[#38D9A9] text-xs font-semibold rounded-lg transition-all flex items-center justify-center gap-1.5"
            >
              <AddRoundedIcon sx={{ fontSize: 14 }} /> Add / Manage API Keys
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
