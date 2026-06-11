interface SkeletonProps {
  height?: number | string;
  width?: number | string;
  borderRadius?: number | string;
  style?: React.CSSProperties;
}

export function Skeleton({ height = 20, width = "100%", borderRadius = 6, style }: SkeletonProps) {
  return (
    <div
      className="pulse"
      style={{
        height,
        width,
        borderRadius,
        background: "var(--bg-overlay)",
        ...style,
      }}
    />
  );
}

export function PatientCardSkeleton() {
  return (
    <div
      className="card"
      style={{ display: "flex", flexDirection: "column", gap: "var(--s-3)" }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Skeleton height={18} width={180} />
        <Skeleton height={22} width={70} borderRadius={100} />
      </div>
      <Skeleton height={13} width={120} />
      <Skeleton height={13} width="60%" />
    </div>
  );
}