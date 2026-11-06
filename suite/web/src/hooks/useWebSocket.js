import { useEffect, useState, useCallback } from "react";

export function useWebSocket(url, onMessage) {
  const [online, setOnline] = useState(false);

  useEffect(() => {
    if (!url) return;
    const socket = new WebSocket(url);
    socket.onopen = () => setOnline(true);
    socket.onclose = () => setOnline(false);
    socket.onmessage = (ev) => {
      if (onMessage) onMessage(ev.data);
    };
    return () => socket.close();
  }, [url, onMessage]);

  const send = useCallback(
    (data) => {
      // eslint-disable-next-line no-undef
      if (typeof WebSocket !== "undefined") {
        // no-op placeholder; messages are pushed by the server
      }
    },
    []
  );

  return { online };
}
