import { useState, useRef, type KeyboardEvent } from "react";

interface TagInputProps {
  value: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
  label?: string;
  /** "accent" (default) or "danger" for allergy-style red pills */
  variant?: "accent" | "danger";
}

export function TagInput({
  value,
  onChange,
  placeholder,
  label,
  variant = "accent",
}: TagInputProps) {
  const [input, setInput] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const [focused, setFocused] = useState(false);

  const addTag = () => {
    const trimmed = input.trim();
    if (trimmed.length < 1) { setInput(""); return; }
    if (!value.includes(trimmed)) {
      onChange([...value, trimmed]);
    }
    setInput("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === "Tab" || e.key === ",") {
      e.preventDefault();
      addTag();
    }
    if (e.key === "Backspace" && input === "" && value.length > 0) {
      onChange(value.slice(0, -1));
    }
  };

  const removeTag = (tag: string) => {
    onChange(value.filter((t) => t !== tag));
  };

  const pillStyle =
    variant === "danger"
      ? {
          background: "rgba(212,58,58,0.1)",
          color: "#e07272",
          border: "1px solid rgba(212,58,58,0.25)",
        }
      : {
          background: "var(--accent-dim)",
          color: "var(--accent)",
          border: "1px solid rgba(59,158,221,0.25)",
        };

  return (
    <div className="field">
      {label && <label>{label}</label>}
      <div
        onClick={() => inputRef.current?.focus()}
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 6,
          padding: "8px 10px",
          background: "var(--bg-base)",
          border: `1px solid ${focused ? "var(--accent)" : "var(--border-strong)"}`,
          borderRadius: "var(--r-md)",
          cursor: "text",
          minHeight: 46,
          alignItems: "center",
          transition: "border-color 0.15s, box-shadow 0.15s",
          boxShadow: focused ? "0 0 0 3px var(--accent-dim)" : "none",
        }}
      >
        {value.map((tag) => (
          <span
            key={tag}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 5,
              padding: "3px 10px 3px 10px",
              borderRadius: "var(--r-pill)",
              fontSize: "0.8rem",
              fontWeight: 500,
              flexShrink: 0,
              ...pillStyle,
            }}
          >
            {variant === "danger" && (
              <span style={{ fontSize: "0.65rem", opacity: 0.7 }}>⚠</span>
            )}
            {tag}
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                removeTag(tag);
              }}
              style={{
                background: "none",
                border: "none",
                color: "inherit",
                cursor: "pointer",
                padding: "0 0 0 2px",
                lineHeight: 1,
                opacity: 0.65,
                fontSize: "1rem",
                display: "flex",
                alignItems: "center",
              }}
            >
              ×
            </button>
          </span>
        ))}
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={() => { setFocused(false); addTag(); }}
          onFocus={() => setFocused(true)}
          placeholder={value.length === 0 ? placeholder : "Add more…"}
          style={{
            border: "none",
            outline: "none",
            background: "transparent",
            color: "var(--text-primary)",
            fontSize: "0.9rem",
            flex: 1,
            minWidth: 140,
            padding: "2px 0",
          }}
        />
      </div>
      <p className="field-hint">
        Press <kbd style={{ background: "var(--bg-overlay)", padding: "1px 5px", borderRadius: 3, fontSize: "0.7rem", border: "1px solid var(--border-strong)" }}>Enter</kbd> or <kbd style={{ background: "var(--bg-overlay)", padding: "1px 5px", borderRadius: 3, fontSize: "0.7rem", border: "1px solid var(--border-strong)" }}>,</kbd> to add · Backspace to remove last
      </p>
    </div>
  );
}