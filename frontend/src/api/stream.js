import { useEffect, useRef } from "react";
import { BASE_URL } from "./client";

// Subscribes to the backend's live WebSocket feed
// and calls onMessage for every parsed event.
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

      console.log("Connecting WebSocket:", wsUrl);

      socket = new WebSocket(wsUrl);
      wsRef.current = socket;

      socket.onopen = () => {
        console.log("WebSocket connected:", wsUrl);
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          console.log("WebSocket message:", data);

          onMessageRef.current(data);
        } catch (e) {
          console.error("Failed to parse live update:", e);
          console.error("Raw WebSocket message:", event.data);
        }
      };

      socket.onerror = (error) => {
        console.error("WebSocket error:", error);
      };

      socket.onclose = (event) => {
        console.log(
          "WebSocket disconnected",
          "code:",
          event.code,
          "reason:",
          event.reason
        );

        if (!cancelled) {
          reconnectTimer = setTimeout(() => {
            connect();
          }, 2000);
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