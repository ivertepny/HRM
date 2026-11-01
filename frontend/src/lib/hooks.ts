"use client";

import { useEffect, useState } from "react";

/** Значення з затримкою — щоб пошук не смикав API на кожну літеру. */
export function useDebounced<T>(value: T, delay = 300) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}
