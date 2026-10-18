"use client";

import { useState } from "react";

export default function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      alert("Could not copy to clipboard.");
    }
  }

  return (
    <button className="secondary small" onClick={copy}>
      {copied ? "Copied" : label}
    </button>
  );
}
