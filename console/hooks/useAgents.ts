import { useState, useEffect, useCallback, useMemo } from "react";
import { apiClient, AgentListing } from "@/lib/api";

export function useAgents() {
  const [agents, setAgents] = useState<AgentListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("All");

  const refreshAgents = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiClient.listAgents();
      setAgents(data);
    } catch {
      // Handled via apiClient fallback
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshAgents();
  }, [refreshAgents]);

  const filteredAgents = useMemo(() => {
    return agents.filter((agent) => {
      const matchesSearch =
        agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        agent.slug.toLowerCase().includes(searchQuery.toLowerCase()) ||
        agent.description.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesCategory =
        selectedCategory === "All" ||
        (agent.category || "").toLowerCase().includes(selectedCategory.toLowerCase());
      return matchesSearch && matchesCategory;
    });
  }, [agents, searchQuery, selectedCategory]);

  const categories = useMemo(() => ["All", "Security", "Finance", "DevOps"], []);

  return {
    agents: filteredAgents,
    allAgents: agents,
    loading,
    categories,
    searchQuery,
    setSearchQuery,
    selectedCategory,
    setSelectedCategory,
    refreshAgents,
  };
}
