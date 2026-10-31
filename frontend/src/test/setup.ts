import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Без `globals: true` Testing Library не прибирає DOM між тестами сама
afterEach(() => cleanup());
