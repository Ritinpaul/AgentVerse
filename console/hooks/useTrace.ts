import { useState, useEffect, useCallback } from "react";
import { apiClient, ExecutionTrace } from "@/lib/api";

export function useTrace() {
  const [traces, setTraces] = useState<ExecutionTrace[]>([]);
  const [selectedTrace, setSelectedTrace] = useState<ExecutionTrace | null>(null);
  const [loading, setLoading] = useState(true);
  const [isLiveStreaming, setIsLiveStreaming] = useState(true);

  const fetchTraces = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiClient.listTraces();
      setTraces(data);
      if (data.length > 0 && !selectedTrace) {
        setSelectedTrace(data[0]);
      }
    } finally {
      setLoading(false);
    }
  }, [selectedTrace]);

  useEffect(() => {
    fetchTraces();
  }, [fetchTraces]);

  return {
    traces,
    selectedTrace,
    setSelectedTrace,
    loading,
    isLiveStreaming,
    setIsLiveStreaming,
    fetchTraces,
  };
}
