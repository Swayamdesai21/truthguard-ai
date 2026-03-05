"use client";

import { useState, useCallback } from "react";

interface UploadedFileInfo {
    name: string;
    chunks: number;
}

interface UploadZoneProps {
    sessionId: string | null;
    onSessionReady: (sessionId: string, totalChunks: number, filename: string) => void;
    onError: (error: string) => void;
}

const SUPPORTED_EXTENSIONS = [".pdf", ".docx", ".doc", ".pptx", ".ppt", ".txt", ".md", ".csv"];

export default function UploadZone({ sessionId, onSessionReady, onError }: UploadZoneProps) {
    const [isDragging, setIsDragging] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadedFiles, setUploadedFiles] = useState<UploadedFileInfo[]>([]);

    const handleFiles = useCallback(async (files: FileList) => {
        if (!files || files.length === 0) return;

        setIsUploading(true);
        try {
            const formData = new FormData();
            for (let i = 0; i < files.length; i++) {
                formData.append("files", files[i]);
            }
            if (sessionId) formData.append("session_id", sessionId);

            // Upload directly to backend to bypass Next.js proxy 10MB body limit
            const uploadUrl = process.env.NEXT_PUBLIC_API_URL
                ? `${process.env.NEXT_PUBLIC_API_URL}/api/upload`
                : "http://localhost:8000/api/upload";
            const res = await fetch(uploadUrl, { method: "POST", body: formData });

            // Handle non-JSON error responses (e.g. 500 Internal Server Error)
            const contentType = res.headers.get("content-type") || "";
            if (!res.ok) {
                if (contentType.includes("application/json")) {
                    const errData = await res.json();
                    throw new Error(errData.detail || `Upload failed (${res.status})`);
                } else {
                    const text = await res.text();
                    throw new Error(text || `Upload failed (${res.status})`);
                }
            }

            const data = await res.json();

            const newFiles: UploadedFileInfo[] = (data.files || []).map(
                (f: { filename: string; chunks: number }) => ({
                    name: f.filename,
                    chunks: f.chunks,
                })
            );

            setUploadedFiles((prev) => [...prev, ...newFiles]);
            onSessionReady(
                data.session_id,
                data.total_chunks,
                files.length === 1 ? files[0].name : `${files.length} files`
            );
        } catch (err: unknown) {
            onError(err instanceof Error ? err.message : "Upload failed");
        } finally {
            setIsUploading(false);
        }
    }, [sessionId, onSessionReady, onError]);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        if (e.dataTransfer.files.length > 0) handleFiles(e.dataTransfer.files);
    }, [handleFiles]);

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) handleFiles(e.target.files);
    };

    return (
        <div
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            style={{
                border: `2px dashed ${isDragging ? "var(--accent-primary)" : "var(--border-bright)"}`,
                borderRadius: "16px",
                padding: "2rem",
                textAlign: "center",
                background: isDragging ? "var(--glow-primary)" : "var(--bg-card)",
                transition: "all 0.2s ease",
                cursor: "pointer",
                position: "relative",
            }}
            onClick={() => document.getElementById("file-input")?.click()}
        >
            <input
                id="file-input"
                type="file"
                accept={SUPPORTED_EXTENSIONS.join(",")}
                multiple
                onChange={handleInputChange}
                style={{ display: "none" }}
            />

            {isUploading ? (
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "12px" }}>
                    <div className="spinner" />
                    <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>Indexing documents…</p>
                </div>
            ) : uploadedFiles.length > 0 ? (
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "10px" }}>
                    <div style={{ fontSize: "28px" }}>✅</div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", justifyContent: "center" }}>
                        {uploadedFiles.map((f, i) => (
                            <span
                                key={i}
                                style={{
                                    fontSize: "12px",
                                    color: "var(--accent-emerald)",
                                    background: "var(--supported-bg)",
                                    border: "1px solid rgba(16, 185, 129, 0.2)",
                                    padding: "3px 10px",
                                    borderRadius: "20px",
                                    fontWeight: 500,
                                }}
                            >
                                📄 {f.name} ({f.chunks} chunks)
                            </span>
                        ))}
                    </div>
                    <p style={{ color: "var(--text-muted)", fontSize: "12px", marginTop: "4px" }}>
                        Click or drop to add more documents
                    </p>
                </div>
            ) : (
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "12px" }}>
                    <div style={{ fontSize: "40px", opacity: 0.7 }}>📄</div>
                    <div>
                        <p style={{ color: "var(--text-primary)", fontWeight: 600, marginBottom: "4px" }}>
                            Drop your documents here
                        </p>
                        <p style={{ color: "var(--text-muted)", fontSize: "13px" }}>
                            PDF, DOCX, PPTX, TXT, MD, CSV — multiple files supported
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
}
