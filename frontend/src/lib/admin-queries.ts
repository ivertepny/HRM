"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap, type Schemas } from "./api/client";
import type { operations } from "./api/schema";

// --- облікові записи -----------------------------------------------------------

type UserQuery = NonNullable<operations["users_profile_list"]["parameters"]["query"]>;

export function useUsers(query: UserQuery) {
  return useQuery({
    queryKey: ["users", query],
    queryFn: () => unwrap(api.GET("/api/users/profile/", { params: { query } })),
    placeholderData: (previous) => previous,
  });
}

export function useUser(id: number) {
  return useQuery({
    queryKey: ["users", id],
    queryFn: () => unwrap(api.GET("/api/users/profile/{id}/", { params: { path: { id } } })),
  });
}

export function useCreateUser() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: Schemas["RegisterRequest"]) =>
      unwrap(api.POST("/api/users/register/", { body })),
    onSuccess: () => client.invalidateQueries({ queryKey: ["users"] }),
  });
}

export function useUpdateUser(id: number) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: Schemas["PatchedUserAdminRequest"]) =>
      unwrap(api.PATCH("/api/users/profile/{id}/", { params: { path: { id } }, body })),
    onSuccess: () => client.invalidateQueries({ queryKey: ["users"] }),
  });
}

export function useDeleteUser() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      unwrap(api.DELETE("/api/users/profile/{id}/", { params: { path: { id } } })),
    onSuccess: () => client.invalidateQueries({ queryKey: ["users"] }),
  });
}

/** Прийом на роботу — створення профілю працівника для облікового запису. */
export function useHire() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: Schemas["EmployeeRequest"]) =>
      unwrap(api.POST("/api/employees/employees/", { body })),
    onSuccess: () =>
      Promise.all([
        client.invalidateQueries({ queryKey: ["users"] }),
        client.invalidateQueries({ queryKey: ["employees"] }),
        client.invalidateQueries({ queryKey: ["unit-tree"] }),
      ]),
  });
}

// --- ролі та призначення -------------------------------------------------------

export function useRoles(enabled = true) {
  return useQuery({
    queryKey: ["roles"],
    enabled,
    queryFn: async () =>
      (await unwrap(api.GET("/api/access/roles/", { params: { query: { page_size: 100 } } })))
        .results,
  });
}

export function usePermissionCatalog() {
  return useQuery({
    queryKey: ["permission-catalog"],
    staleTime: 10 * 60_000,
    queryFn: () => unwrap(api.GET("/api/access/permissions/")),
  });
}

function useInvalidateAccess() {
  const client = useQueryClient();
  // Зміна ролей може змінити й власні права — оновлюємо і меню
  return () =>
    Promise.all(
      [["roles"], ["user-roles"], ["me", "permissions"]].map((queryKey) =>
        client.invalidateQueries({ queryKey }),
      ),
    );
}

export function useSaveRole(id?: number) {
  const invalidate = useInvalidateAccess();
  return useMutation({
    mutationFn: (body: Schemas["RoleRequest"]) =>
      id
        ? unwrap(api.PATCH("/api/access/roles/{id}/", { params: { path: { id } }, body }))
        : unwrap(api.POST("/api/access/roles/", { body })),
    onSuccess: invalidate,
  });
}

export function useDeleteRole() {
  const invalidate = useInvalidateAccess();
  return useMutation({
    mutationFn: (id: number) =>
      unwrap(api.DELETE("/api/access/roles/{id}/", { params: { path: { id } } })),
    onSuccess: invalidate,
  });
}

export function useUserRoles(userId: number, enabled = true) {
  return useQuery({
    queryKey: ["user-roles", userId],
    enabled,
    queryFn: async () =>
      (
        await unwrap(
          api.GET("/api/access/user-roles/", {
            params: { query: { user: userId, page_size: 100 } },
          }),
        )
      ).results,
  });
}

export function useGrantRole() {
  const invalidate = useInvalidateAccess();
  return useMutation({
    mutationFn: (body: Schemas["UserRoleRequest"]) =>
      unwrap(api.POST("/api/access/user-roles/", { body })),
    onSuccess: invalidate,
  });
}

export function useRevokeRole() {
  const invalidate = useInvalidateAccess();
  return useMutation({
    mutationFn: (id: number) =>
      unwrap(api.DELETE("/api/access/user-roles/{id}/", { params: { path: { id } } })),
    onSuccess: invalidate,
  });
}
