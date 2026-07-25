import { useState, useEffect, useCallback } from "react";
import * as api from "../api";

export function useSession() {
  const [languageSet, setLanguageSet] = useState("english");
  const [wordPool, setWordPool] = useState([]);
  const [stats, setStats] = useState(null);
  const [loadingStats, setLoadingStats] = useState(false);  // preserve the hero "loading…" label

  const refreshSession = useCallback(async () => {
    const data = await api.session.getSession();
    if (!data) return;                 // non-throwing apiFetch returns null on failure
    setLanguageSet(data.language_set);
    setWordPool(data.words || []);
  }, []);

  const refreshStats = useCallback(async () => {
    setLoadingStats(true);
    const data = await api.stats.getStats();
    if (data) setStats(data);
    setLoadingStats(false);
  }, []);

  const changeLanguage = useCallback(async (next) => {
    await api.session.setLanguage(next);
    setLanguageSet(next);
  }, []);

  useEffect(() => {
    refreshSession();
    refreshStats();
  }, [refreshSession, refreshStats]);

  return { languageSet, wordPool, stats, loadingStats, refreshSession, refreshStats,
           changeLanguage, setLanguageSet, setWordPool, setStats };
}
