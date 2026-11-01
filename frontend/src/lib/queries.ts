"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { Access } from "./access";
import { api, ApiError, NETWORK_ERROR, unwrap, type Schemas } from "./api/client";

export const queryKeys = {
  me: ["me"] as const,
  myAccess: ["me", "permissions"] as const,
  myEmployee: (userId?: number) => ["me", "employee", userId] as const,
};

export function useMe() {
  return useQuery({
    queryKey: queryKeys.me,
    queryFn: () => unwrap(api.GET("/api/users/me/")),
  });
}

export type MyAccess = Access & { roles: Schemas["UserRole"][] };

export function useMyAccess() {
  return useQuery({
    queryKey: queryKeys.myAccess,
    queryFn: async () => (await unwrap(api.GET("/api/users/me/permissions/"))) as MyAccess,
    staleTime: 60_000,
  });
}

/** Профіль працівника поточного користувача (його може й не бути). */
export function useMyEmployee(userId?: number) {
  return useQuery({
    queryKey: queryKeys.myEmployee(userId),
    enabled: userId !== undefined,
    queryFn: async () => {
      const page = await unwrap(
        api.GET("/api/employees/employees/", {
          params: { query: { user: userId } },
        }),
      );
      return page.results[0] ?? null;
    },
  });
}

export function useUpdateMe() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: Schemas["PatchedUserRequest"]) =>
      unwrap(api.PATCH("/api/users/me/", { body })),
    onSuccess: (user) => client.setQueryData(queryKeys.me, user),
  });
}

export async function logout() {
  await fetch("/api/auth/logout", { method: "POST" });
  // Повне перезавантаження скидає кеш TanStack Query з даними користувача
  // eslint-disable-next-line @next/next/no-location-assign-relative-destination
  window.location.assign("/login");
}

// --- відпустки -----------------------------------------------------------------

type VacationQuery = NonNullable<
  import("./api/schema").operations["vacations_requests_list"]["parameters"]["query"]
>;

export function useVacations(query: VacationQuery, enabled = true) {
  return useQuery({
    queryKey: ["vacations", query],
    enabled,
    queryFn: async () =>
      (
        await unwrap(
          api.GET("/api/vacations/requests/", {
            params: { query: { page_size: 100, ...query } },
          }),
        )
      ).results,
  });
}

export function useSubmitVacation() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: Schemas["VacationRequestRequest"]) =>
      unwrap(api.POST("/api/vacations/requests/", { body })),
    onSuccess: () => client.invalidateQueries({ queryKey: ["vacations"] }),
  });
}

type VacationAction = "approve" | "reject" | "cancel";

export function useVacationAction() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      action,
      comment,
    }: {
      id: number;
      action: VacationAction;
      comment?: string;
    }) => {
      const params = { path: { id } };
      if (action === "cancel") {
        return unwrap(api.POST("/api/vacations/requests/{id}/cancel/", { params }));
      }
      const path = `/api/vacations/requests/{id}/${action}/` as const;
      return unwrap(api.POST(path, { params, body: { comment: comment ?? "" } }));
    },
    onSuccess: () => client.invalidateQueries({ queryKey: ["vacations"] }),
  });
}

// --- працівники ----------------------------------------------------------------

type EmployeeQuery = NonNullable<
  import("./api/schema").operations["employees_employees_list"]["parameters"]["query"]
>;

export function useEmployees(query: EmployeeQuery) {
  return useQuery({
    queryKey: ["employees", query],
    queryFn: () => unwrap(api.GET("/api/employees/employees/", { params: { query } })),
    placeholderData: (previous) => previous, // без мерехтіння при пошуку й пагінації
  });
}

export function useEmployee(id: number) {
  return useQuery({
    queryKey: ["employees", id],
    queryFn: () => unwrap(api.GET("/api/employees/employees/{id}/", { params: { path: { id } } })),
  });
}

export function useUpdateEmployee(id: number) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: Schemas["PatchedEmployeeRequest"]) =>
      unwrap(
        api.PATCH("/api/employees/employees/{id}/", {
          params: { path: { id } },
          body,
        }),
      ),
    onSuccess: (employee) => {
      client.setQueryData(["employees", id], employee);
      client.invalidateQueries({ queryKey: ["employees"] });
      client.invalidateQueries({ queryKey: ["career-history", id] });
    },
  });
}

/** Довідники для фільтрів і форм (невеликі — одна сторінка до 100). */
export function usePositions(enabled = true) {
  return useQuery({
    queryKey: ["positions"],
    enabled,
    staleTime: 5 * 60_000,
    queryFn: async () =>
      (
        await unwrap(
          api.GET("/api/employees/positions/", {
            params: { query: { page_size: 100 } },
          }),
        )
      ).results,
  });
}

export function useUnits(enabled = true) {
  return useQuery({
    queryKey: ["units"],
    enabled,
    staleTime: 5 * 60_000,
    queryFn: async () =>
      (
        await unwrap(
          api.GET("/api/company/units/", {
            params: { query: { page_size: 100 } },
          }),
        )
      ).results,
  });
}

export function useCareerHistory(employeeId: number) {
  return useQuery({
    queryKey: ["career-history", employeeId],
    queryFn: async () =>
      (
        await unwrap(
          api.GET("/api/employees/career-history/", {
            params: { query: { employee: employeeId, page_size: 100 } },
          }),
        )
      ).results,
  });
}

export function useDocuments(employeeId: number) {
  return useQuery({
    queryKey: ["documents", employeeId],
    queryFn: async () =>
      (
        await unwrap(
          api.GET("/api/employees/documents/", {
            params: { query: { employee: employeeId, page_size: 100 } },
          }),
        )
      ).results,
  });
}

export function useUploadDocument(employeeId: number) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (form: FormData) => {
      form.set("employee", String(employeeId));
      // multipart напряму: браузер сам виставить boundary у Content-Type
      let response: Response;
      try {
        response = await fetch("/api/backend/api/employees/documents/", {
          method: "POST",
          body: form,
        });
      } catch {
        throw new ApiError(0, { detail: NETWORK_ERROR });
      }
      const body = await response.json().catch(() => null);
      if (!response.ok) throw new ApiError(response.status, body);
      return body as Schemas["EmployeeDocument"];
    },
    onSuccess: () => client.invalidateQueries({ queryKey: ["documents", employeeId] }),
  });
}

export function useDeleteDocument(employeeId: number) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      unwrap(
        api.DELETE("/api/employees/documents/{id}/", {
          params: { path: { id } },
        }),
      ),
    onSuccess: () => client.invalidateQueries({ queryKey: ["documents", employeeId] }),
  });
}

// --- оргструктура --------------------------------------------------------------

export function useUnitTree(enabled = true) {
  return useQuery({
    queryKey: ["unit-tree"],
    enabled,
    queryFn: () => unwrap(api.GET("/api/company/units/tree/")),
  });
}

export function useUnitHistory(id: number | undefined) {
  return useQuery({
    queryKey: ["unit-history", id],
    enabled: id !== undefined,
    queryFn: () =>
      unwrap(
        api.GET("/api/company/units/{id}/history/", {
          params: { path: { id: id! }, query: { limit: 20 } },
        }),
      ),
  });
}

function useInvalidateUnits() {
  const client = useQueryClient();
  return () =>
    Promise.all(
      ["unit-tree", "units", "unit-history", "employees"].map((key) =>
        client.invalidateQueries({ queryKey: [key] }),
      ),
    );
}

export function useCreateUnit() {
  const invalidate = useInvalidateUnits();
  return useMutation({
    mutationFn: (body: Schemas["StructuralUnitRequest"]) =>
      unwrap(api.POST("/api/company/units/", { body })),
    onSuccess: invalidate,
  });
}

export function useUpdateUnit(id: number) {
  const invalidate = useInvalidateUnits();
  return useMutation({
    mutationFn: (body: Schemas["PatchedStructuralUnitRequest"]) =>
      unwrap(
        api.PATCH("/api/company/units/{id}/", {
          params: { path: { id } },
          body,
        }),
      ),
    onSuccess: invalidate,
  });
}

export function useCloseUnit() {
  const invalidate = useInvalidateUnits();
  return useMutation({
    mutationFn: (id: number) =>
      unwrap(api.DELETE("/api/company/units/{id}/", { params: { path: { id } } })),
    onSuccess: invalidate,
  });
}

// --- обладнання ----------------------------------------------------------------

type EquipmentQuery = NonNullable<
  import("./api/schema").operations["equipment_items_list"]["parameters"]["query"]
>;
type AssignmentQuery = NonNullable<
  import("./api/schema").operations["equipment_assignments_list"]["parameters"]["query"]
>;

export function useEquipmentList(query: EquipmentQuery) {
  return useQuery({
    queryKey: ["equipment", "list", query],
    queryFn: () => unwrap(api.GET("/api/equipment/items/", { params: { query } })),
    placeholderData: (previous) => previous,
  });
}

export function useEquipmentItem(id: number) {
  return useQuery({
    queryKey: ["equipment", "item", id],
    queryFn: () => unwrap(api.GET("/api/equipment/items/{id}/", { params: { path: { id } } })),
  });
}

export function useAssignments(query: AssignmentQuery, enabled = true) {
  return useQuery({
    queryKey: ["equipment", "assignments", query],
    enabled,
    queryFn: async () =>
      (
        await unwrap(
          api.GET("/api/equipment/assignments/", {
            params: { query: { page_size: 100, ...query } },
          }),
        )
      ).results,
  });
}

function useInvalidateEquipment() {
  const client = useQueryClient();
  return () => client.invalidateQueries({ queryKey: ["equipment"] });
}

export function useCreateEquipment() {
  const invalidate = useInvalidateEquipment();
  return useMutation({
    mutationFn: (body: Schemas["EquipmentRequest"]) =>
      unwrap(api.POST("/api/equipment/items/", { body })),
    onSuccess: invalidate,
  });
}

export function useUpdateEquipment(id: number) {
  const invalidate = useInvalidateEquipment();
  return useMutation({
    mutationFn: (body: Schemas["PatchedEquipmentRequest"]) =>
      unwrap(
        api.PATCH("/api/equipment/items/{id}/", {
          params: { path: { id } },
          body,
        }),
      ),
    onSuccess: invalidate,
  });
}

export function useDeleteEquipment() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      unwrap(api.DELETE("/api/equipment/items/{id}/", { params: { path: { id } } })),
    // Картку видаленої одиниці не перезапитуємо (було б 404)
    onSuccess: (_, id) => {
      client.removeQueries({ queryKey: ["equipment", "item", id] });
      return client.invalidateQueries({ queryKey: ["equipment", "list"] });
    },
  });
}

type EquipmentOperation =
  | { action: "assign"; body: Schemas["AssignRequest"] }
  | { action: "return"; body: Schemas["ReturnRequest"] }
  | { action: "write-off"; body: Schemas["WriteOffRequest"] };

export function useEquipmentOperation(id: number) {
  const invalidate = useInvalidateEquipment();
  return useMutation({
    mutationFn: (operation: EquipmentOperation) => {
      const params = { path: { id } };
      switch (operation.action) {
        case "assign":
          return unwrap(
            api.POST("/api/equipment/items/{id}/assign/", {
              params,
              body: operation.body,
            }),
          );
        case "return":
          return unwrap(
            api.POST("/api/equipment/items/{id}/return/", {
              params,
              body: operation.body,
            }),
          );
        case "write-off":
          return unwrap(
            api.POST("/api/equipment/items/{id}/write-off/", {
              params,
              body: operation.body,
            }),
          );
      }
    },
    onSuccess: invalidate,
  });
}
