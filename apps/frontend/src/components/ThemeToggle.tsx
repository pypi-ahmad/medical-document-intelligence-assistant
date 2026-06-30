"use client";

import { useEffect, useState } from "react";

const KEY = "mdia_theme";

export default function ThemeToggle() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    const saved = window.localStorage.getItem(KEY);
    const shouldDark = saved ? saved === "dark" : false;
    setDark(shouldDark);
    document.documentElement.classList.toggle("dark", shouldDark);
  }, []);

  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    window.localStorage.setItem(KEY, next ? "dark" : "light");
  };

  return (
    <button
      className="card px-3 py-1.5 text-sm"
      onClick={toggle}
      type="button"
      aria-label="Toggle theme"
    >
      {dark ? "Light" : "Dark"}
    </button>
  );
}
