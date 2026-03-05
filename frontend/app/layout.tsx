import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TruthGuard AI — Agentic Fact-Checking",
  description:
    "Upload documents and ask questions. TruthGuard AI retrieves evidence, generates answers, extracts claims, and verifies each one against your sources.",
  keywords: ["fact-checking", "AI", "RAG", "hallucination detection", "NLI"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
