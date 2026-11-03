import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ForgotPasswordForm } from "./forgot-password/forgot-password-form";
import { SetPasswordForm } from "./set-password-form";

let searchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useSearchParams: () => searchParams,
}));

function json(body: unknown, status: number) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

async function fill(password: string, confirm = password) {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Новий пароль"), password);
  await user.type(screen.getByLabelText("Повторіть пароль"), confirm);
  await user.click(screen.getByRole("button", { name: "Зберегти пароль" }));
}

describe("SetPasswordForm", () => {
  beforeEach(() => {
    searchParams = new URLSearchParams({ uid: "MQ", token: "abc-123" });
  });
  afterEach(() => vi.unstubAllGlobals());

  it("checks that both passwords match before calling the server", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<SetPasswordForm kind="reset" />);

    await fill("Long-enough-1", "Long-enough-2");

    expect(screen.getByText("Паролі не збігаються")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("sends uid, token and password to the invite endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<SetPasswordForm kind="invite" />);

    await fill("Long-enough-1");

    expect(await screen.findByText("Пароль збережено")).toBeInTheDocument();
    const request = fetchMock.mock.calls[0][0] as Request;
    expect(new URL(request.url).pathname).toBe("/api/backend/api/users/invite/accept/");
    expect(await request.json()).toEqual({ uid: "MQ", token: "abc-123", password: "Long-enough-1" });
    expect(screen.getByRole("link", { name: "Увійти" })).toHaveAttribute("href", "/login");
  });

  it("shows server password rules next to the field", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(json({ password: ["Пароль надто простий."] }, 400)),
    );
    render(<SetPasswordForm kind="reset" />);

    await fill("12345678");

    expect(await screen.findByText("Пароль надто простий.")).toBeInTheDocument();
  });

  it("explains an expired link and offers a new one", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(json({ token: ["Посилання недійсне або застаріло."] }, 400)),
    );
    render(<SetPasswordForm kind="reset" />);

    await fill("Long-enough-1");

    expect(await screen.findByText("Посилання не діє")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "запросити нове посилання" })).toHaveAttribute(
      "href",
      "/forgot-password",
    );
  });

  it("rejects a link without token right away", () => {
    searchParams = new URLSearchParams({ uid: "MQ" });
    render(<SetPasswordForm kind="invite" />);
    expect(screen.getByText("Посилання не діє")).toBeInTheDocument();
  });
});

describe("ForgotPasswordForm", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows the same confirmation whether or not the account exists", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
    render(<ForgotPasswordForm />);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("Робоча пошта"), "olena@company.com");
    await user.click(screen.getByRole("button", { name: "Надіслати посилання" }));

    expect(await screen.findByText("Перевірте пошту")).toBeInTheDocument();
    expect(screen.getByText(/Якщо для olena@company.com є обліковий запис/)).toBeInTheDocument();
  });

  it("shows the rate-limit message from the server", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(json({ detail: "Забагато запитів. Спробуйте за 60 хв." }, 429)),
    );
    render(<ForgotPasswordForm />);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("Робоча пошта"), "olena@company.com");
    await user.click(screen.getByRole("button", { name: "Надіслати посилання" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Забагато запитів");
  });
});
