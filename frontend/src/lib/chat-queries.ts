"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap, type Schemas } from "./api/client";

export type Exchange = Schemas["AIQuery"];

export function useChatSessions() {
  return useQuery({
    queryKey: ["chat-sessions"],
    queryFn: async () =>
      (await unwrap(api.GET("/api/ai/chat/sessions/", { params: { query: { page_size: 50 } } })))
        .results,
  });
}

export function useChatMessages(sessionId: string | undefined) {
  return useQuery({
    queryKey: ["chat-messages", sessionId],
    enabled: !!sessionId,
    queryFn: async () =>
      (
        await unwrap(
          api.GET("/api/ai/chat/sessions/{session_id}/messages/", {
            params: { path: { session_id: sessionId! }, query: { page_size: 100 } },
          }),
        )
      ).results,
  });
}

export function useSendMessage() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: Schemas["ChatRequestRequest"]) =>
      unwrap(api.POST("/api/ai/chat/", { body })),
    onSuccess: (result) => {
      // Додаємо обмін у кеш одразу, без повторного запиту
      client.setQueryData<Exchange[]>(["chat-messages", result.session_id], (old) => [
        ...(old ?? []),
        result.query,
      ]);
      return client.invalidateQueries({ queryKey: ["chat-sessions"] });
    },
  });
}

export function useRenameSession() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ sessionId, name }: { sessionId: string; name: string }) =>
      unwrap(
        api.PATCH("/api/ai/chat/sessions/{session_id}/", {
          params: { path: { session_id: sessionId } },
          body: { name },
        }),
      ),
    onSuccess: () => client.invalidateQueries({ queryKey: ["chat-sessions"] }),
  });
}

export function useDeleteSession() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) =>
      unwrap(
        api.DELETE("/api/ai/chat/sessions/{session_id}/", {
          params: { path: { session_id: sessionId } },
        }),
      ),
    onSuccess: () => client.invalidateQueries({ queryKey: ["chat-sessions"] }),
  });
}

/** Назва нової розмови — початок першого питання. */
export function sessionNameFrom(message: string, max = 60) {
  const text = message.trim().replace(/\s+/g, " ");
  return text.length <= max ? text : `${text.slice(0, max - 1).trimEnd()}…`;
}

export const TOOL_NOTES: Record<string, string> = {
  get_company_structure: "Відповідь спирається на оргструктуру компанії (у межах ваших прав).",
};
