"use client";

import { useState, useRef } from "react";
import UploadZone from "@/components/UploadZone";
import ClaimTable from "@/components/ClaimTable";
import ConfidenceBar from "@/components/ConfidenceBar";

interface ClaimVerdict {
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
  web_sources?: { title: string; url: string; snippet: string }[];
}

interface PipelineResult {
  session_id: string;
  query: string;
  draft_answer: string;
  refined_answer: string;
  confidence_score: number;
  document_confidence: number;
  web_confidence: number;
  claims: ClaimVerdict[];
  sources: string[];
  web_sources: { title: string; url: string; snippet: string }[];
  removed_claims: string[];
}

type Tab = "refined" | "draft";

export default function Home() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [uploadInfo, setUploadInfo] = useState<{ filename: string; chunks: number } | null>(null);
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("refined");
  const resultsRef = useRef<HTMLDivElement>(null);

  const handleSessionReady = (sid: string, chunkCount: number, filename: string) => {
    setSessionId(sid);
    setUploadInfo({ filename, chunks: chunkCount });
    setError(null);
  };

  const handleAsk = async () => {
    if (!query.trim() || !sessionId || isLoading) return;
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      // Bypass Next.js proxy for the ask endpoint to prevent timeouts
      const askUrl = process.env.NEXT_PUBLIC_API_URL
        ? `${process.env.NEXT_PUBLIC_API_URL}/api/ask`
        : "http://localhost:8000/api/ask";

      const res = await fetch(askUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, query: query.trim() }),
      });

      // Handle non-JSON error responses (e.g. 500 Internal Server Error)
      const contentType = res.headers.get("content-type") || "";
      if (!res.ok) {
        if (contentType.includes("application/json")) {
          const errData = await res.json();
          throw new Error(errData.detail || `Request failed (${res.status})`);
        } else {
          const text = await res.text();
          throw new Error(text || `Request failed (${res.status})`);
        }
      }

      const data = await res.json();
      setResult(data);
      setActiveTab("refined");
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setIsLoading(false);
    }
  };

  const supported = result?.claims.filter((c) => c.verdict === "supported").length ?? 0;
  const contradicted = result?.claims.filter((c) => c.verdict === "contradicted").length ?? 0;
  const unsupported = result?.claims.filter((c) => c.verdict === "unsupported").length ?? 0;

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg-primary)" }}>
      {/* ── Background Orbs ──────────────────────────────────────────────── */}
      <div style={{ position: "fixed", inset: 0, pointerEvents: "none", overflow: "hidden", zIndex: 0 }}>
        <div style={{
          position: "absolute", top: "-20%", left: "-10%",
          width: "600px", height: "600px", borderRadius: "50%",
          background: "radial-gradient(circle, rgba(99,102,241,0.08) 0%, transparent 70%)",
        }} />
        <div style={{
          position: "absolute", bottom: "-20%", right: "-10%",
          width: "500px", height: "500px", borderRadius: "50%",
          background: "radial-gradient(circle, rgba(139,92,246,0.06) 0%, transparent 70%)",
        }} />
      </div>

      <div style={{ position: "relative", zIndex: 1, maxWidth: "900px", margin: "0 auto", padding: "0 24px 80px" }}>

        {/* ── Header ────────────────────────────────────────────────────── */}
        <header style={{ padding: "48px 0 40px", textAlign: "center" }}>
          <div style={{
            display: "inline-flex", alignItems: "center", gap: "8px",
            background: "rgba(99,102,241,0.1)", border: "1px solid rgba(99,102,241,0.2)",
            borderRadius: "20px", padding: "6px 16px", marginBottom: "20px",
          }}>
            <span style={{ fontSize: "12px", color: "var(--accent-primary)", fontWeight: 600, letterSpacing: "0.05em" }}>
              AGENTIC FACT-CHECKING
            </span>
          </div>
          <h1 style={{
            fontSize: "clamp(2rem, 5vw, 3.5rem)",
            fontWeight: 800,
            background: "linear-gradient(135deg, #f1f1f5 0%, #9191a8 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
            lineHeight: 1.1,
            marginBottom: "16px",
          }}>
            Truth<span style={{
              background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}>Guard</span> AI
          </h1>
          <p style={{ fontSize: "16px", color: "var(--text-secondary)", maxWidth: "480px", margin: "0 auto" }}>
            Upload a document, ask a question. Every claim in the answer gets verified against your sources.
          </p>
        </header>

        {/* ── Step 1: Upload ────────────────────────────────────────────── */}
        <section style={{ marginBottom: "24px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "14px" }}>
            <StepBadge n={1} done={!!sessionId} />
            <h2 style={{ fontSize: "15px", fontWeight: 600, color: "var(--text-primary)" }}>Upload Your Document</h2>
          </div>
          <UploadZone
            sessionId={sessionId}
            onSessionReady={handleSessionReady}
            onError={setError}
          />
          {uploadInfo && (
            <div style={{
              marginTop: "10px", fontSize: "12px", color: "var(--accent-emerald)",
              display: "flex", gap: "16px",
            }}>
              <span>📎 {uploadInfo.filename}</span>
              <span>🧩 {uploadInfo.chunks} chunks indexed</span>
              <span style={{ color: "var(--text-muted)" }}>Session: {sessionId?.slice(0, 8)}…</span>
            </div>
          )}
        </section>

        {/* ── Step 2: Query ─────────────────────────────────────────────── */}
        <section style={{ marginBottom: "32px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "14px" }}>
            <StepBadge n={2} done={!!result} />
            <h2 style={{ fontSize: "15px", fontWeight: 600, color: "var(--text-primary)" }}>Ask a Question</h2>
          </div>

          <div style={{ display: "flex", gap: "10px" }}>
            <input
              id="query-input"
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAsk()}
              placeholder={sessionId ? "What does the document say about…" : "Upload a document first"}
              disabled={!sessionId || isLoading}
              style={{
                flex: 1,
                background: "var(--bg-card)",
                border: "1px solid var(--border-bright)",
                borderRadius: "12px",
                padding: "14px 18px",
                color: "var(--text-primary)",
                fontSize: "15px",
                outline: "none",
                transition: "border-color 0.2s ease",
                fontFamily: "inherit",
              }}
            />
            <button
              id="ask-button"
              onClick={handleAsk}
              disabled={!sessionId || !query.trim() || isLoading}
              style={{
                padding: "14px 28px",
                background: sessionId && query.trim() && !isLoading
                  ? "linear-gradient(135deg, #6366f1, #8b5cf6)"
                  : "var(--border)",
                color: "white",
                border: "none",
                borderRadius: "12px",
                fontWeight: 600,
                fontSize: "15px",
                cursor: sessionId && query.trim() && !isLoading ? "pointer" : "not-allowed",
                transition: "all 0.2s ease",
                whiteSpace: "nowrap",
                fontFamily: "inherit",
              }}
            >
              {isLoading ? "Verifying…" : "Fact-Check →"}
            </button>
          </div>

          {/* Loading animation */}
          {isLoading && (
            <div style={{
              marginTop: "16px",
              display: "flex",
              flexDirection: "column",
              gap: "8px",
            }}>
              {[
                "🔍 Retrieving relevant passages…",
                "🤖 Generating answer…",
                "⚗️ Extracting claims…",
                "🧪 Verifying each claim…",
                "🌐 Cross-checking via web search…",
                "✍️ Refining answer with citations…",
              ].map((step, i) => (
                <div key={i} style={{
                  fontSize: "13px",
                  color: "var(--text-muted)",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  animation: `fadeIn 0.4s ease ${i * 0.4}s both`,
                }}>
                  {step}
                </div>
              ))}
            </div>
          )}
        </section>

        {/* ── Error ─────────────────────────────────────────────────────── */}
        {error && (
          <div style={{
            background: "var(--contradicted-bg)",
            border: "1px solid rgba(244, 63, 94, 0.2)",
            borderRadius: "12px",
            padding: "14px 18px",
            marginBottom: "24px",
            color: "var(--contradicted)",
            fontSize: "14px",
          }}>
            ❌ {error}
          </div>
        )}

        {/* ── Results ───────────────────────────────────────────────────── */}
        {result && (
          <div ref={resultsRef}>

            {/* Stat strip */}
            <div style={{
              display: "grid",
              gridTemplateColumns: "repeat(4, 1fr)",
              gap: "12px",
              marginBottom: "24px",
            }}>
              <StatCard label="Claims" value={result.claims.length} color="var(--accent-primary)" />
              <StatCard label="Supported" value={supported} color="var(--supported)" />
              <StatCard label="Issues" value={contradicted + unsupported} color={contradicted > 0 ? "var(--contradicted)" : "var(--unsupported)"} />
              <StatCard label="Confidence" value={`${Math.round(result.confidence_score * 100)}%`} color={result.confidence_score > 0.7 ? "var(--supported)" : result.confidence_score > 0.4 ? "var(--unsupported)" : "var(--contradicted)"} />
            </div>

            {/* Confidence Scores — triple bar */}
            <div style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderRadius: "16px",
              padding: "20px",
              marginBottom: "20px",
            }}>
              <h3 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-primary)", marginBottom: "16px" }}>
                🎯 Confidence Scores
              </h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                    <span style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: 500 }}>
                      📊 Overall Confidence
                    </span>
                    <span style={{ fontSize: "12px", fontFamily: "'JetBrains Mono', monospace", color: "var(--text-primary)", fontWeight: 600 }}>
                      {Math.round(result.confidence_score * 100)}%
                    </span>
                  </div>
                  <ConfidenceBar score={result.confidence_score} />
                </div>
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                    <span style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: 500 }}>
                      📄 Document Confidence
                    </span>
                    <span style={{ fontSize: "12px", fontFamily: "'JetBrains Mono', monospace", color: "var(--text-primary)", fontWeight: 600 }}>
                      {Math.round((result.document_confidence ?? result.confidence_score) * 100)}%
                    </span>
                  </div>
                  <ConfidenceBar score={result.document_confidence ?? result.confidence_score} />
                </div>
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                    <span style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: 500 }}>
                      🌐 Web Confidence
                    </span>
                    <span style={{ fontSize: "12px", fontFamily: "'JetBrains Mono', monospace", color: "var(--text-primary)", fontWeight: 600 }}>
                      {Math.round((result.web_confidence ?? 0) * 100)}%
                    </span>
                  </div>
                  <ConfidenceBar score={result.web_confidence ?? 0} />
                </div>
              </div>
            </div>

            {/* Answer tabs */}
            <div style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderRadius: "16px",
              marginBottom: "20px",
              overflow: "hidden",
            }}>
              {/* Tab header */}
              <div style={{
                display: "flex",
                borderBottom: "1px solid var(--border)",
              }}>
                {(["refined", "draft"] as Tab[]).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    style={{
                      padding: "14px 20px",
                      background: activeTab === tab ? "var(--bg-card-hover)" : "transparent",
                      border: "none",
                      borderBottom: activeTab === tab ? "2px solid var(--accent-primary)" : "2px solid transparent",
                      color: activeTab === tab ? "var(--text-primary)" : "var(--text-muted)",
                      fontWeight: activeTab === tab ? 600 : 400,
                      fontSize: "14px",
                      cursor: "pointer",
                      fontFamily: "inherit",
                      transition: "all 0.2s",
                    }}
                  >
                    {tab === "refined" ? "✅ Verified Answer" : "📝 Draft Answer"}
                  </button>
                ))}
              </div>

              {/* Answer body */}
              <div style={{ padding: "20px" }}>
                <p style={{
                  fontSize: "15px",
                  color: "var(--text-primary)",
                  lineHeight: 1.7,
                  whiteSpace: "pre-wrap",
                }}>
                  {activeTab === "refined" ? result.refined_answer : result.draft_answer}
                </p>

                {/* Removed claims notice */}
                {activeTab === "refined" && result.removed_claims.length > 0 && (
                  <div style={{
                    marginTop: "16px",
                    padding: "12px 16px",
                    background: "var(--unsupported-bg)",
                    border: "1px solid rgba(245,158,11,0.2)",
                    borderRadius: "10px",
                  }}>
                    <p style={{ fontSize: "12px", color: "var(--unsupported)", fontWeight: 600, marginBottom: "8px" }}>
                      ⚠️ Removed {result.removed_claims.length} unverified claim{result.removed_claims.length > 1 ? "s" : ""}:
                    </p>
                    <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "4px" }}>
                      {result.removed_claims.map((c, i) => (
                        <li key={i} style={{ fontSize: "12px", color: "var(--text-secondary)" }}>• {c}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>

            {/* Claims table */}
            <div style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderRadius: "16px",
              padding: "20px",
              marginBottom: "20px",
            }}>
              <h3 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-primary)", marginBottom: "14px" }}>
                🧩 Claim-by-Claim Verification
              </h3>
              <ClaimTable claims={result.claims} />
            </div>

            {/* Sources */}
            {result.sources.length > 0 && (
              <div style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                borderRadius: "16px",
                padding: "20px",
                marginBottom: "20px",
              }}>
                <h3 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-primary)", marginBottom: "12px" }}>
                  📚 Document Sources
                </h3>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                  {result.sources.map((s, i) => (
                    <span key={i} style={{
                      fontSize: "12px",
                      color: "var(--accent-cyan)",
                      background: "rgba(6, 182, 212, 0.1)",
                      border: "1px solid rgba(6, 182, 212, 0.2)",
                      padding: "4px 12px",
                      borderRadius: "20px",
                    }}>
                      📄 {s}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Web Sources */}
            {result.web_sources && result.web_sources.length > 0 && (
              <div style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                borderRadius: "16px",
                padding: "20px",
              }}>
                <h3 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-primary)", marginBottom: "12px" }}>
                  🌐 Web Sources ({result.web_sources.length})
                </h3>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {result.web_sources.map((ws, i) => (
                    <a
                      key={i}
                      href={ws.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        fontSize: "13px",
                        color: "var(--accent-cyan)",
                        background: "rgba(6, 182, 212, 0.06)",
                        border: "1px solid rgba(6, 182, 212, 0.12)",
                        borderRadius: "10px",
                        padding: "12px 16px",
                        textDecoration: "none",
                        display: "block",
                        lineHeight: 1.5,
                        transition: "border-color 0.2s, background 0.2s",
                      }}
                    >
                      <span style={{ fontWeight: 600, display: "block", marginBottom: "4px" }}>🔗 {ws.title}</span>
                      <span style={{ fontSize: "11px", color: "var(--text-muted)", display: "block", marginBottom: "4px" }}>
                        {ws.url.length > 80 ? ws.url.slice(0, 80) + "…" : ws.url}
                      </span>
                      <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                        {ws.snippet?.length > 200 ? ws.snippet.slice(0, 200) + "…" : ws.snippet}
                      </span>
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(4px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .spinner {
          width: 32px;
          height: 32px;
          border: 3px solid var(--border);
          border-top-color: var(--accent-primary);
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        input:focus {
          border-color: var(--accent-primary) !important;
          box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
        }
      `}</style>
    </div>
  );
}

function StepBadge({ n, done }: { n: number; done: boolean }) {
  return (
    <div style={{
      width: "26px",
      height: "26px",
      borderRadius: "8px",
      background: done ? "linear-gradient(135deg, #6366f1, #8b5cf6)" : "var(--border)",
      color: done ? "white" : "var(--text-muted)",
      fontSize: "12px",
      fontWeight: 700,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      flexShrink: 0,
    }}>
      {done ? "✓" : n}
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div style={{
      background: "var(--bg-card)",
      border: "1px solid var(--border)",
      borderRadius: "12px",
      padding: "16px",
      textAlign: "center",
    }}>
      <p style={{ fontSize: "22px", fontWeight: 700, color, marginBottom: "4px", fontFamily: "'JetBrains Mono', monospace" }}>
        {value}
      </p>
      <p style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.05em" }}>
        {label}
      </p>
    </div>
  );
}
