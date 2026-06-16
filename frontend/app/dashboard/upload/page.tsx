"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Users,
  LayoutDashboard,
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";

const TENANT_ID = "kukreja_paris"; // Simulating the logged-in builder context

export default function UploadPanel() {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [status, setStatus] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setStatus(null); // Clear previous status messages
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setIsUploading(true);
    setStatus(null);

    // HTML forms handle files using FormData instead of standard JSON strings
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("http://144.91.127.152:8000/api/upload", {
        method: "POST",
        headers: {
          "x-tenant-id": TENANT_ID, // Passing the lock token
        },
        body: formData, // Sending raw multipart form file data
      });

      const data = await response.json();

      if (response.ok) {
        setStatus({
          type: "success",
          message:
            data.message ||
            "Document vectorized and added to your knowledge base successfully!",
        });
        setFile(null); // Clear file selector input
      } else {
        setStatus({
          type: "error",
          message: data.detail || "Failed to process the document layout.",
        });
      }
    } catch (error) {
      console.error("Upload error:", error);
      setStatus({
        type: "error",
        message: "Failed to establish a connection with the backend engine.",
      });
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col md:flex-row">
      {/* Sidebar Navigation */}
      <div className="w-full md:w-64 bg-slate-900 text-white flex flex-col p-4 shadow-xl">
        <div className="flex items-center space-x-2 mb-8 mt-2 px-2">
          <LayoutDashboard className="text-blue-400" />
          <h1 className="text-xl font-bold tracking-wider">SaaS Admin</h1>
        </div>
        <nav className="space-y-2 flex-1">
          {/* Link back to Lead Center */}
          <Link
            href="/dashboard"
            className="w-full flex items-center space-x-3 px-4 py-3 text-gray-300 hover:bg-slate-800 hover:text-white rounded-lg text-sm font-medium transition-colors"
          >
            <Users size={18} />
            <span>Lead Center</span>
          </Link>
          {/* Active Upload Tab */}
          <button className="w-full flex items-center space-x-3 px-4 py-3 bg-blue-600 text-white rounded-lg text-sm font-medium transition-colors">
            <UploadCloud size={18} />
            <span>Knowledge Base</span>
          </button>
        </nav>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 p-8 max-w-4xl">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-800">
            Knowledge Base Training
          </h2>
          <p className="text-gray-500 mt-1">
            Upload property brochures, layouts, or price lists to instantly
            retrain your AI chatbot.
          </p>
        </div>

        {/* Upload Card */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <form onSubmit={handleUpload} className="space-y-6">
            {/* Drag & Drop Visual Box */}
            <div className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center bg-gray-50 flex flex-col items-center justify-center hover:border-blue-500 transition-colors relative">
              <input
                type="file"
                accept=".txt,.pdf"
                onChange={handleFileChange}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                disabled={isUploading}
              />
              <UploadCloud size={48} className="text-gray-400 mb-3" />
              <p className="text-sm font-medium text-gray-700">
                {file
                  ? `Selected: ${file.name}`
                  : "Click or drag file here to select"}
              </p>
              <p className="text-xs text-gray-400 mt-1">
                Supports plain text (.txt) or printable PDF (.pdf)
              </p>
            </div>

            {/* Selected File Badge */}
            {file && (
              <div className="flex items-center space-x-2 p-3 bg-blue-50 rounded-lg border border-blue-100 text-blue-700 text-sm">
                <FileText size={18} />
                <span className="font-medium truncate flex-1">{file.name}</span>
                <span className="text-xs text-blue-500">
                  ({(file.size / 1024).toFixed(1)} KB)
                </span>
              </div>
            )}

            {/* Status Feedback Messages */}
            {status && (
              <div
                className={`p-4 rounded-lg flex items-start space-x-3 text-sm border ${
                  status.type === "success"
                    ? "bg-green-50 border-green-200 text-green-800"
                    : "bg-red-50 border-red-200 text-red-800"
                }`}
              >
                {status.type === "success" ? (
                  <CheckCircle2
                    size={18}
                    className="mt-0.5 text-green-600 flex-shrink-0"
                  />
                ) : (
                  <AlertCircle
                    size={18}
                    className="mt-0.5 text-red-600 flex-shrink-0"
                  />
                )}
                <span>{status.message}</span>
              </div>
            )}

            {/* Action Button */}
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={!file || isUploading}
                className="bg-blue-600 text-white font-semibold px-6 py-2.5 rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors shadow-sm"
              >
                {isUploading ? "Processing Vector Pipeline..." : "Train AI Bot"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
