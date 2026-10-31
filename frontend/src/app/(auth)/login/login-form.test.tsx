import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { LoginForm } from "./login-form";

const replace = vi.fn();
let searchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, refresh: vi.fn() }),
  useSearchParams: () => searchParams,
}));

async function fillAndSubmit(email = "olena@company.com", password = "secret") {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Робоча пошта"), email);
  await user.type(screen.getByLabelText("Пароль"), password);
  await user.click(screen.getByRole("button", { name: "Увійти" }));
}

describe("LoginForm", () => {
  beforeEach(() => {
    searchParams = new URLSearchParams();
    replace.mockReset();
  });
  afterEach(() => vi.unstubAllGlobals());

  it("validates fields before calling the server", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<LoginForm />);

    await userEvent.setup().click(screen.getByRole("button", { name: "Увійти" }));

    expect(await screen.findByText(/Введіть робочу пошту/)).toBeInTheDocument();
    expect(screen.getByText("Введіть пароль")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows a clear message for wrong credentials", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 400 })));
    render(<LoginForm />);

    await fillAndSubmit();

    expect(await screen.findByRole("alert")).toHaveTextContent("Невірна пошта або пароль.");
    expect(replace).not.toHaveBeenCalled();
  });

  it("returns to the requested internal page after login", async () => {
    searchParams = new URLSearchParams({ next: "/employees?page=2" });
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<LoginForm />);

    await fillAndSubmit();

    expect(fetchMock).toHaveBeenCalledWith("/api/auth/login", expect.objectContaining({ method: "POST" }));
    expect(replace).toHaveBeenCalledWith("/employees?page=2");
  });

  it("ignores external redirect targets", async () => {
    searchParams = new URLSearchParams({ next: "//evil.example" });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 200 })));
    render(<LoginForm />);

    await fillAndSubmit();

    expect(replace).toHaveBeenCalledWith("/");
  });
});
