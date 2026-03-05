"use client";

interface ConfidenceBarProps {
    score: number; // 0 to 1
}

export default function ConfidenceBar({ score }: ConfidenceBarProps) {
    const pct = Math.round(score * 100);

    const color =
        pct >= 75
            ? "var(--supported)"
            : pct >= 45
                ? "var(--unsupported)"
                : "var(--contradicted)";

    const label =
        pct >= 75 ? "High Confidence" : pct >= 45 ? "Moderate Confidence" : "Low Confidence";

    return (
        <div>
            <div
                style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "8px",
                }}
            >
                <span style={{ fontSize: "13px", color: "var(--text-secondary)", fontWeight: 500 }}>
                    Confidence Score
                </span>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span
                        style={{
                            fontSize: "13px",
                            color,
                            fontWeight: 600,
                            fontFamily: "'JetBrains Mono', monospace",
                        }}
                    >
                        {pct}%
                    </span>
                    <span
                        style={{
                            fontSize: "11px",
                            color,
                            background: `${color}20`,
                            padding: "2px 8px",
                            borderRadius: "20px",
                            fontWeight: 500,
                        }}
                    >
                        {label}
                    </span>
                </div>
            </div>

            <div
                style={{
                    width: "100%",
                    height: "8px",
                    background: "var(--border)",
                    borderRadius: "4px",
                    overflow: "hidden",
                }}
            >
                <div
                    style={{
                        width: `${pct}%`,
                        height: "100%",
                        background: `linear-gradient(90deg, ${color}80, ${color})`,
                        borderRadius: "4px",
                        transition: "width 0.8s cubic-bezier(0.4, 0, 0.2, 1)",
                        boxShadow: `0 0 8px ${color}60`,
                    }}
                />
            </div>
        </div>
    );
}
