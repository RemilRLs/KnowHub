import { useState, useCallback, useRef } from "react";
import { createStreamConnection } from "../api/chat.api";
import type { Message, MessageMetadata } from "../types";
import { createMessageId } from "../types";

export function useChat(selectedCollection: string) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "Hello. I am the KnowHub Assistant. Please select a collection to begin.",
      timestamp: new Date(),
    },
  ]);

  const [isLoading, setIsLoading] = useState(false);
  const activeStreamRef = useRef<EventSource | null>(null);

  const startStream = useCallback(
    (messageId: string, query: string) => {
      // close any existing stream
      if (activeStreamRef.current) {
        activeStreamRef.current.close();
      }

      const stream = createStreamConnection({
        query,
        collection: selectedCollection,
        k: "4",
      });

      activeStreamRef.current = stream;

      let buffer = "";
      let flushTimer: number | null = null;

      const flush = () => {
        if (!buffer) return;
        const textToAppend = buffer;

        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === messageId
              ? { ...msg, content: msg.content + textToAppend, isPending: false }
              : msg
          )
        );

        buffer = "";
        flushTimer = null;
      };

      stream.onopen = () => {
        // console.log("Stream connection opened");
      };

      stream.onmessage = (event) => {
        if (!event.data) return;

        try {
          const parsed = JSON.parse(event.data);
          const token = parsed?.token;

          if (token) {
            buffer += token;
            if (flushTimer === null) {
              flushTimer = window.setTimeout(flush, 50);
            }
          }
        } catch {
          console.warn("Received non-JSON message in stream:", event.data);
        }
      };

      stream.addEventListener("done", (event: MessageEvent) => {
        if (flushTimer !== null) {
          window.clearTimeout(flushTimer);
        }
        flush();

        let metadata: MessageMetadata | undefined;

        try {
          const data = JSON.parse(event.data);
          metadata = {
            sources: data.sources,
            retrieved_chunks: data.retrieved_chunks,
            retrieval_time_ms: data.retrieval_time_ms,
            generation_time_ms: data.generation_time_ms,
            total_time_ms: data.total_time_ms,
            temperature: data.temperature,
            max_tokens: data.max_tokens,
            k: data.k,
          };
        } catch (error) {
          console.warn("Could not parse metadata from done event:", error);
        }

        stream.close();
        activeStreamRef.current = null;

        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === messageId
              ? {
                  ...msg,
                  content: msg.content || "No response received.",
                  isPending: false,
                  metadata,
                }
              : msg
          )
        );

        setIsLoading(false);
      });

      stream.onerror = (err) => {
        console.error("Stream error:", err);
        if (flushTimer !== null) window.clearTimeout(flushTimer);
        flush();

        stream.close();
        activeStreamRef.current = null;

        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === messageId
              ? {
                  ...msg,
                  content: msg.content || "Unable to connect to the server.",
                  isPending: false,
                }
              : msg
          )
        );

        setIsLoading(false);
      };
    },
    [selectedCollection]
  );

  const sendMessage = useCallback(
    (input: string) => {
      if (!input.trim() || isLoading || !selectedCollection) return;

      const userMessage: Message = {
        id: createMessageId(),
        role: "user",
        content: input,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);

      const assistantMessageId = createMessageId();
      const assistantMessage: Message = {
        id: assistantMessageId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
        isPending: true,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      try {
        startStream(assistantMessageId, input);
      } catch (error) {
        console.error("Submission error:", error);

        setMessages((prev) => [
          ...prev,
          {
            id: createMessageId(),
            role: "assistant",
            content: "Unable to connect to the server.",
            timestamp: new Date(),
          },
        ]);

        setIsLoading(false);
      }
    },
    [isLoading, selectedCollection, startStream]
  );

  const cleanup = useCallback(() => {
    if (activeStreamRef.current) {
      activeStreamRef.current.close();
      activeStreamRef.current = null;
    }
  }, []);

  return { messages, isLoading, sendMessage, cleanup };
}
