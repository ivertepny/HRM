import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { sessionNameFrom } from "@/lib/chat-queries";

import { Composer } from "./composer";

function Harness({ onSend, pending = false }: { onSend: (text: string) => void; pending?: boolean }) {
  const [value, setValue] = useState("");
  return <Composer value={value} onChange={setValue} pending={pending} onSend={() => onSend(value)} />;
}

describe("Composer", () => {
  it("sends on Enter and inserts a new line on Shift+Enter", async () => {
    const onSend = vi.fn();
    render(<Harness onSend={onSend} />);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("Питання асистенту"), "Рядок 1{Shift>}{Enter}{/Shift}Рядок 2{Enter}");

    expect(onSend).toHaveBeenCalledWith("Рядок 1\nРядок 2");
  });

  it("does not send empty or whitespace-only questions", async () => {
    const onSend = vi.fn();
    render(<Harness onSend={onSend} />);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("Питання асистенту"), "   {Enter}");

    expect(onSend).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Надіслати" })).toBeDisabled();
  });

  it("blocks sending while the assistant is answering", () => {
    render(<Composer value="Питання" onChange={() => {}} pending onSend={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Асистент відповідає…" })).toBeDisabled();
  });
});

describe("sessionNameFrom", () => {
  it("uses the question, collapsing whitespace and truncating long text", () => {
    expect(sessionNameFrom("  Скільки   днів\nвідпустки?  ")).toBe("Скільки днів відпустки?");
    const long = "а".repeat(80);
    expect(sessionNameFrom(long)).toHaveLength(60);
    expect(sessionNameFrom(long).endsWith("…")).toBe(true);
  });
});
