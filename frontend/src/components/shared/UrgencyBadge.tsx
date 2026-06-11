import type { UrgencyLevel } from "../../core/entities/triage";
import { URGENCY_LABELS } from "../../core/constants/urgency";

interface UrgencyBadgeProps {
  level: UrgencyLevel;
  label?: string;
  showDot?: boolean;
}

export function UrgencyBadge({ level, label, showDot = true }: UrgencyBadgeProps) {
  return (
    <span className={`badge badge-urgency-${level}`}>
      {showDot && (
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: "currentColor",
            display: "inline-block",
            flexShrink: 0,
          }}
        />
      )}
      {label ?? URGENCY_LABELS[level]}
    </span>
  );
}