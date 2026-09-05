"use client";

import React, { useState, useEffect } from "react";
import CloseRoundedIcon from "@mui/icons-material/CloseRounded";
import KeyRoundedIcon from "@mui/icons-material/KeyRounded";
import DeleteRoundedIcon from "@mui/icons-material/DeleteRounded";
import ShieldRoundedIcon from "@mui/icons-material/ShieldRounded";
import CheckRoundedIcon from "@mui/icons-material/CheckRounded";
import LaunchRoundedIcon from "@mui/icons-material/Launch";
import {
  PROVIDER_META,
  ProviderKey,
  getStoredKeys,
  addKey,
  removeKey,
  KeyEntry,
} from "@/lib/modelKeys";

interface KeyManagementModalProps {
  open: boolean;
  onClose: () => void;
}

export function KeyManagementModal({ open, onClose }: KeyManagementModalProps) {
  const [keys, setKeys] = useState<KeyEntry[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<ProviderKey>("openai");
  const [inputKey, setInputKey] = useState("");
  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    if (open) {
      setKeys(getStoredKeys());
      setInputKey("");
    }
  }, [open]);

  if (!open) return null;

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputKey.trim()) return;
    addKey(selectedProvider, inputKey.trim());
    setKeys(getStoredKeys());
    setInputKey("");
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2000);
  };

  const handleRemove = (provider: ProviderKey) => {
    removeKey(provider);
    setKeys(getStoredKeys());
  };

  const selectedMeta = PROVIDER_META.find((p) => p.id === selectedProvider);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 font-sans animate-in fade-in duration-150">
      <div className="w-full max-w-lg bg-[#0E0E12] border border-[#272732] rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="h-14 px-5 border-b border-[#1E1E28] bg-[#121218] flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#38D9A9]/10 border border-[#38D9A9]/30 flex items-center justify-center text-[#38D9A9]">
              <KeyRoundedIcon sx={{ fontSize: 18 }} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white">Model API Keys (BYOK)</h3>
              <p className="text-[11px] text-neutral-400">Zero-Trust Local Storage • Keys Never Leave Your Browser</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-neutral-400 hover:text-white hover:bg-[#1E1E28] transition-colors"
          >
            <CloseRoundedIcon sx={{ fontSize: 18 }} />
          </button>
        </div>

        <div className="p-5 space-y-5 overflow-y-auto max-h-[70vh]">
          {/* Active Keys List */}
          <div>
            <div className="text-[11px] font-bold uppercase tracking-wider text-neutral-400 mb-2">
              Active Keys ({keys.length})
            </div>
            {keys.length === 0 ? (
              <div className="p-4 bg-[#14141A] border border-[#22222A] rounded-xl text-center text-xs text-neutral-500">
                No custom keys added yet. You are using the Free Tier (50,000 tokens/day).
              </div>
            ) : (
              <div className="space-y-2">
                {keys.map((k) => {
                  const meta = PROVIDER_META.find((p) => p.id === k.provider);
                  return (
                    <div
                      key={k.provider}
                      className="flex items-center justify-between p-3 bg-[#14141C] border border-[#22222C] rounded-xl text-xs"
                    >
                      <div className="flex items-center gap-2.5">
                        <span
                          className="w-2.5 h-2.5 rounded-full"
                          style={{ backgroundColor: meta?.color ?? "#10B981" }}
                        />
                        <div>
                          <div className="font-bold text-white flex items-center gap-2">
                            <span>{k.label}</span>
                            <span className="font-mono text-[10px] text-neutral-400 font-normal">
                              {k.masked}
                            </span>
                          </div>
                          <div className="text-[10px] text-neutral-500">
                            Added {new Date(k.addedAt).toLocaleDateString()}
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={() => handleRemove(k.provider)}
                        className="p-1.5 text-neutral-500 hover:text-[#E5252A] hover:bg-red-950/30 rounded-lg transition-colors"
                        title="Remove key"
                      >
                        <DeleteRoundedIcon sx={{ fontSize: 16 }} />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Add Key Form */}
          <form onSubmit={handleAdd} className="space-y-3 pt-3 border-t border-[#1E1E28]">
            <div className="text-[11px] font-bold uppercase tracking-wider text-neutral-400">
              Add New Provider Key
            </div>

            <div className="grid grid-cols-2 gap-2">
              {PROVIDER_META.map((provider) => {
                const isSelected = selectedProvider === provider.id;
                const isAdded = keys.some((k) => k.provider === provider.id);
                return (
                  <button
                    key={provider.id}
                    type="button"
                    onClick={() => setSelectedProvider(provider.id)}
                    className={`p-2.5 rounded-xl border text-left flex items-center justify-between transition-all ${
                      isSelected
                        ? "bg-[#1C1C26] border-[#38D9A9] text-white"
                        : "bg-[#14141A] border-[#22222A] text-neutral-400 hover:text-neutral-200 hover:bg-[#181820]"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: provider.color }}
                      />
                      <span className="text-xs font-semibold">{provider.label}</span>
                    </div>
                    {isAdded && <CheckRoundedIcon sx={{ fontSize: 14, color: "#10B981" }} />}
                  </button>
                );
              })}
            </div>

            <div className="space-y-1.5 pt-1">
              <div className="flex justify-between items-center text-xs">
                <label className="font-semibold text-neutral-300">
                  {selectedMeta?.label} API Key
                </label>
                {selectedMeta?.docsUrl && (
                  <a
                    href={selectedMeta.docsUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="text-[11px] text-[#38D9A9] hover:underline flex items-center gap-0.5 font-medium"
                  >
                    Get Key <LaunchRoundedIcon sx={{ fontSize: 11 }} />
                  </a>
                )}
              </div>
              <input
                type="password"
                value={inputKey}
                onChange={(e) => setInputKey(e.target.value)}
                placeholder={selectedMeta?.placeholder}
                className="w-full bg-[#14141C] border border-[#272732] focus:border-[#38D9A9] text-xs text-white placeholder-neutral-600 rounded-xl px-3.5 py-2.5 outline-none font-mono"
              />
            </div>

            <button
              type="submit"
              disabled={!inputKey.trim()}
              className="w-full py-2.5 bg-[#38D9A9] hover:bg-[#2EB88F] disabled:opacity-40 disabled:cursor-not-allowed text-black text-xs font-bold rounded-xl transition-all flex items-center justify-center gap-2 shadow-lg shadow-[#38D9A9]/20"
            >
              {savedSuccess ? (
                <>
                  <CheckRoundedIcon sx={{ fontSize: 16 }} /> Key Saved Encrypted Locally!
                </>
              ) : (
                <>
                  <KeyRoundedIcon sx={{ fontSize: 16 }} /> Save {selectedMeta?.label} Key
                </>
              )}
            </button>
          </form>

          {/* Privacy Note */}
          <div className="p-3 bg-[#10B981]/5 border border-[#10B981]/20 rounded-xl flex items-start gap-2.5 text-xs text-neutral-300">
            <ShieldRoundedIcon sx={{ fontSize: 18, color: "#10B981" }} />
            <div>
              <span className="font-bold text-[#10B981]">Zero-Trust Security Guarantee: </span>
              Your API keys stay in your browser's localStorage. AgentVerse servers only proxy the requests directly to the LLM provider.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
