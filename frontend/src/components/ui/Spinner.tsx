interface SpinnerProps {
  size?: "sm" | "lg";
  label?: string;
}

export function Spinner({ size, label }: SpinnerProps) {
  return (
    <span
      style={{ display: "inline-flex", alignItems: "center", gap: 10 }}
      aria-label={label ?? "Loading"}
    >
      <span className={`spinner${size === "lg" ? " spinner-lg" : ""}`} />
      {label && (
        <span style={{ fontSize: "0.875rem", color: "var(--text-secondary)" }}>
          {label}
        </span>
      )}
    </span>
  );
}