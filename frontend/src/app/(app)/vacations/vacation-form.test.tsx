import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { VacationForm } from "./vacation-form";

vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

function renderForm() {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <VacationForm />
    </QueryClientProvider>,
  );
}

async function fill(start: string, end: string) {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Перший день"), start);
  await user.type(screen.getByLabelText("Останній день"), end);
  return user;
}

describe("VacationForm", () => {
  it("shows a Ukrainian message when the server is unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    renderForm();

    const user = await fill("2099-01-12", "2099-01-16");
    await user.click(screen.getByRole("button", { name: "Подати заявку" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Немає з'єднання з сервером");
  });

  afterEach(() => vi.unstubAllGlobals());

  it("counts calendar days as dates are entered", async () => {
    renderForm();
    await fill("2099-01-12", "2099-01-16");
    expect(screen.getByText("5 календарних днів")).toBeInTheDocument();
  });

  it("rejects an end date before the start without calling the API", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    renderForm();

    const user = await fill("2099-01-16", "2099-01-12");
    await user.click(screen.getByRole("button", { name: "Подати заявку" }));

    expect(await screen.findByText("Остання дата не може бути раніше першої")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("keeps a non-field server error visible next to the button", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({ non_field_errors: ["Перетин з іншою заявкою, що очікує розгляду або вже схвалена."] }),
          { status: 400, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );
    renderForm();

    const user = await fill("2099-01-12", "2099-01-16");
    await user.click(screen.getByRole("button", { name: "Подати заявку" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Перетин з іншою заявкою");
  });
});
