import React, { useState, useCallback, useEffect } from "react";
import { listRuns } from "../lib/api";

export function useRuns() {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { runs: data } = await listRuns();
      setRuns(data || []);
    } catch (e) {
      setRuns([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const refetch = useCallback(() => { load(); }, [load]);
  return { runs, loading, refetch };
}
