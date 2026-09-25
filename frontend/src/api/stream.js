import { useEffect, useRef } from "react";
import { BASE_URL } from "./client";

// Subscribes to the backend's live WebSocket feed (rider position/status
// updates) and calls onMessage for every parsed event. Reconnects on drop.
export function useLiveStream(onMessage) {
  const wsRef = useRef(null);
  const onMessageRef = useRef(onMessage);

  onMessageRef.current = onMessage;

  useEffect(() => {
    const wsUrl = BASE_URL.replace(/^http/, "ws") + "/ws";

    let socket = null;
    let reconnectTimer = null;
    let cancelled = false;

    function connect() {
      if (cancelled) return;

      socket = new WebSocket(wsUrl);
      wsRef.current = socket;

      socket.onopen = () => {
        console.log("WebSocket connected:", wsUrl);
      };

      socket.onmessage = (event) => {
        try {
          onMessageRef.current(JSON.parse(event.data));
        } catch (e) {
          console.error("Failed to parse live update", e);
        }
      };

      socket.onclose = () => {
        console.log("WebSocket disconnected");

        if (!cancelled) {
          reconnectTimer = setTimeout(connect, 2000);
        }
      };

      socket.onerror = () => {
        console.error("WebSocket error");

        // Don't manually close an already closed socket.
        if (
          socket.readyState === WebSocket.CONNECTING ||
          socket.readyState === WebSocket.OPEN
        ) {
          socket.close();
        }
      };
    }

    connect();

    return () => {
      cancelled = true;

      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }

      if (
        socket &&
        socket.readyState !== WebSocket.CLOSED &&
        socket.readyState !== WebSocket.CLOSING
      ) {
        socket.close();
      }

      wsRef.current = null;
    };
  }, []);
}
