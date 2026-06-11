interface DrugFlagBannerProps {
  summary: string;
}

export function DrugFlagBanner({ summary }: DrugFlagBannerProps) {
  return (
    <div
      className="alert alert-warning"
      style={{ display: "flex", gap: 10, alignItems: "flex-start" }}
    >
      <span style={{ fontSize: "1rem", flexShrink: 0 }}>⚠</span>
      <div>
        <strong style={{ fontSize: "0.8rem", display: "block", marginBottom: 2 }}>
          Drug Interaction Alert
        </strong>
        {summary}
      </div>
    </div>
  );
}