"use client";

import { useState } from "react";

interface WebSource {
    title: string;
    url: string;
    snippet: string;
}

interface Claim {
    claim: string;
    verdict: "supported" | "contradicted" | "unsupported";
    confidence: number;
    reasoning: string;
    evidence: string[];
    hallucination_risk?: "high" | "medium" | "low";
    cross_contradiction?: boolean;
    web_verdict?: "supported" | "contradicted" | "inconclusive";
    web_confidence?: number;
    web_reasoning?: string;
    web_sources?: WebSource[];
}

interface ClaimTableProps {
    claims: Claim[];
}

const VERDICT_CONFIG = {
    supported: {
        label: "✅ Supported",
        color: "var(--supported)",
        bg: "var(--supported-bg)",
        border: "rgba(16, 185, 129, 0.2)",
    },
    contradicted: {
        label: "❌ Contradicted",
        color: "var(--contradicted)",
        bg: "var(--contradicted-bg)",
        border: "rgba(244, 63, 94, 0.2)",
    },
    unsupported: {
        label: "⚠️ Unverified",
        color: "var(--unsupported)",
        bg: "var(--unsupported-bg)",
        border: "rgba(245, 158, 11, 0.2)",
    },
};

const RISK_COLORS = {
    high: "var(--contradicted)",
    medium: "var(--unsupported)",
    low: "var(--supported)",
};

export default function ClaimTable({ claims }: ClaimTableProps) {
    const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

    if (!claims || claims.length === 0) return null;

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {claims.map((claim, i) => {
                const config = VERDICT_CONFIG[claim.verdict] || VERDICT_CONFIG.unsupported;
                const isExpanded = expandedIndex === i;

                return (
                    <div
                        key={i}
                        style={{
                            background: "var(--bg-card)",
                            border: `1px solid ${isExpanded ? config.border : "var(--border)"}`,
                            borderRadius: "12px",
                            overflow: "hidden",
                            transition: "border-color 0.2s ease",
                        }}
                    >
                        {/* Header Row */}
                        <div
                            onClick={() => setExpandedIndex(isExpanded ? null : i)}
                            style={{
                                display: "flex",
                                alignItems: "center",
                                gap: "12px",
                                padding: "14px 16px",
                                cursor: "pointer",
                                userSelect: "none",
                            }}
                        >
                            {/* Index */}
                            <span
                                style={{
                                    minWidth: "24px",
                                    height: "24px",
                                    borderRadius: "6px",
                                    background: "var(--border)",
                                    color: "var(--text-muted)",
                                    fontSize: "11px",
                                    fontWeight: 700,
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    fontFamily: "'JetBrains Mono', monospace",
                                }}
                            >
                                {i + 1}
                            </span>

                            {/* Claim text */}
                            <span
                                style={{
                                    flex: 1,
                                    fontSize: "14px",
                                    color: "var(--text-primary)",
                                    lineHeight: 1.4,
                                }}
                            >
                                {claim.claim}
                            </span>

                            {/* Verdict badge */}
                            <span
                                style={{
                                    fontSize: "11px",
                                    fontWeight: 600,
                                    color: config.color,
                                    background: config.bg,
                                    border: `1px solid ${config.border}`,
                                    padding: "3px 10px",
                                    borderRadius: "20px",
                                    whiteSpace: "nowrap",
                                    flexShrink: 0,
                                }}
                            >
                                {config.label}
                            </span>

                            {/* Confidence */}
                            <span
                                style={{
                                    fontSize: "12px",
                                    color: "var(--text-muted)",
                                    fontFamily: "'JetBrains Mono', monospace",
                                    flexShrink: 0,
                                }}
                            >
                                {Math.round(claim.confidence * 100)}%
                            </span>

                            {/* Risk badge */}
                            {claim.hallucination_risk && claim.hallucination_risk !== "low" && (
                                <span
                                    style={{
                                        fontSize: "10px",
                                        color: RISK_COLORS[claim.hallucination_risk],
                                        background: `${RISK_COLORS[claim.hallucination_risk]}15`,
                                        padding: "2px 8px",
                                        borderRadius: "20px",
                                        flexShrink: 0,
                                        fontWeight: 600,
                                    }}
                                >
                                    {claim.hallucination_risk.toUpperCase()} RISK
                                </span>
                            )}

                            {/* Expand arrow */}
                            <span
                                style={{
                                    color: "var(--text-muted)",
                                    fontSize: "12px",
                                    transform: isExpanded ? "rotate(180deg)" : "rotate(0deg)",
                                    transition: "transform 0.2s ease",
                                    flexShrink: 0,
                                }}
                            >
                                ▼
                            </span>
                        </div>

                        {/* Expanded Detail Panel */}
                        {isExpanded && (
                            <div
                                style={{
                                    padding: "0 16px 16px 52px",
                                    borderTop: "1px solid var(--border)",
                                    paddingTop: "14px",
                                    display: "flex",
                                    flexDirection: "column",
                                    gap: "12px",
                                }}
                            >
                                {/* Reasoning */}
                                {claim.reasoning && (
                                    <div>
                                        <p
                                            style={{
                                                fontSize: "11px",
                                                color: "var(--text-muted)",
                                                fontWeight: 600,
                                                textTransform: "uppercase",
                                                letterSpacing: "0.05em",
                                                marginBottom: "6px",
                                            }}
                                        >
                                            AI Reasoning
                                        </p>
                                        <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                                            {claim.reasoning}
                                        </p>
                                    </div>
                                )}

                                {/* Evidence */}
                                {claim.evidence && claim.evidence.length > 0 && (
                                    <div>
                                        <p
                                            style={{
                                                fontSize: "11px",
                                                color: "var(--text-muted)",
                                                fontWeight: 600,
                                                textTransform: "uppercase",
                                                letterSpacing: "0.05em",
                                                marginBottom: "8px",
                                            }}
                                        >
                                            Evidence Passages
                                        </p>
                                        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                                            {claim.evidence.map((ev, j) => (
                                                <div
                                                    key={j}
                                                    style={{
                                                        fontSize: "12px",
                                                        color: "var(--text-secondary)",
                                                        background: "var(--bg-secondary)",
                                                        border: "1px solid var(--border)",
                                                        borderRadius: "8px",
                                                        padding: "10px 12px",
                                                        lineHeight: 1.5,
                                                        borderLeft: `3px solid ${config.color}`,
                                                    }}
                                                >
                                                    "{ev.length > 300 ? ev.slice(0, 300) + "…" : ev}"
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Cross-contradiction warning */}
                                {claim.cross_contradiction && (
                                    <div
                                        style={{
                                            fontSize: "12px",
                                            color: "var(--contradicted)",
                                            background: "var(--contradicted-bg)",
                                            border: "1px solid rgba(244, 63, 94, 0.2)",
                                            borderRadius: "8px",
                                            padding: "8px 12px",
                                        }}
                                    >
                                        ⚡ This claim contradicts another claim in the answer.
                                    </div>
                                )}

                                {/* Web Verification */}
                                {claim.web_verdict && (
                                    <div style={{
                                        borderTop: "1px solid var(--border)",
                                        paddingTop: "12px",
                                        display: "flex",
                                        flexDirection: "column",
                                        gap: "8px",
                                    }}>
                                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                            <p style={{
                                                fontSize: "11px",
                                                color: "var(--text-muted)",
                                                fontWeight: 600,
                                                textTransform: "uppercase",
                                                letterSpacing: "0.05em",
                                            }}>
                                                🌐 Web Verification
                                            </p>
                                            <span style={{
                                                fontSize: "10px",
                                                fontWeight: 600,
                                                padding: "2px 8px",
                                                borderRadius: "20px",
                                                color: claim.web_verdict === "supported" ? "var(--supported)"
                                                    : claim.web_verdict === "contradicted" ? "var(--contradicted)"
                                                        : "var(--unsupported)",
                                                background: claim.web_verdict === "supported" ? "var(--supported-bg)"
                                                    : claim.web_verdict === "contradicted" ? "var(--contradicted-bg)"
                                                        : "var(--unsupported-bg)",
                                            }}>
                                                {claim.web_verdict === "supported" ? "✅ Web Confirmed"
                                                    : claim.web_verdict === "contradicted" ? "❌ Web Contradicts"
                                                        : "⚠️ Inconclusive"}
                                                {claim.web_confidence ? ` (${Math.round(claim.web_confidence * 100)}%)` : ""}
                                            </span>
                                        </div>

                                        {claim.web_reasoning && (
                                            <p style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                                                {claim.web_reasoning}
                                            </p>
                                        )}

                                        {claim.web_sources && claim.web_sources.length > 0 && (
                                            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                                                {claim.web_sources.map((ws, j) => (
                                                    <a
                                                        key={j}
                                                        href={ws.url}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        style={{
                                                            fontSize: "12px",
                                                            color: "var(--accent-cyan)",
                                                            background: "rgba(6, 182, 212, 0.06)",
                                                            border: "1px solid rgba(6, 182, 212, 0.15)",
                                                            borderRadius: "8px",
                                                            padding: "8px 12px",
                                                            textDecoration: "none",
                                                            display: "block",
                                                            lineHeight: 1.4,
                                                            transition: "border-color 0.2s",
                                                        }}
                                                    >
                                                        <span style={{ fontWeight: 600 }}>🔗 {ws.title}</span>
                                                        <br />
                                                        <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                                                            {ws.snippet?.length > 150 ? ws.snippet.slice(0, 150) + "…" : ws.snippet}
                                                        </span>
                                                    </a>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                );
            })}
        </div>
    );
}
