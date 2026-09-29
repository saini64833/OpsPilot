import { useEffect, useRef } from "react";
import { BASE_URL } from "./client";

export function useLiveStream(onMessage) {
  const wsRef = useRef(null);
  const onMessageRef = useRef(onMessage);

  onMessageRef.current = onMessage;

  useEffect(() => {
    const getWsUrl = () => {
      if (BASE_URL.startsWith("http")) {
        return BASE_URL.replace(/^http/, "ws") + "/ws";
      }
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      return `${protocol}//${window.location.host}${BASE_URL}/ws`;
    };

    const wsUrl = getWsUrl();
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
          onMessageRef.current(data);
        } catch (e) {
          console.error("Failed to parse live update:", e);
        }
      };

      socket.onerror = (error) => {
        console.error("WebSocket error:", error);
      };

      socket.onclose = (event) => {
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
      if (reconnectTimer) clearTimeout(reconnectTimer);
      
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