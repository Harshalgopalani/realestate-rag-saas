"use client";
import { useState } from "react";
import { UploadCloud, CheckCircle, AlertCircle, Shield } from "lucide-react";

export default function UploadAdmin() {
  const [tenant, setTenant] = useState("");
  const [secret, setSecret] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<"idle" | "uploading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");
  const [overwrite, setOverwrite] = useState(false);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !tenant || !secret) return;

    setStatus("uploading");
    
    // We must use FormData to send files to the backend
    const formData = new FormData();
    formData.append("file", file);
    formData.append("tenant_id", tenant.toLowerCase().replace(/\s+/g, '_'));
    formData.append("secret", secret);
    formData.append("overwrite", overwrite.toString());

    try {
      const response = await fetch("https://richportfolio.duckdns.org/api/upload", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (data.status === "success") {
        setStatus("success");
        setMessage(data.message);
        setFile(null);
      } else {
        setStatus("error");
        setMessage(data.message);
      }
    } catch (error) {
      setStatus("error");
      setMessage("Failed to connect to the server.");
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center p-6 font-sans">
      <div className="max-w-md w-full bg-gray-800 rounded-2xl shadow-2xl p-8 border border-gray-700">
        <div className="flex items-center justify-center mb-6 text-blue-400">
          <Shield size={40} />
        </div>
        <h1 className="text-2xl font-bold text-center mb-2">Master Admin Portal</h1>
        <p className="text-gray-400 text-center mb-8 text-sm">Upload real estate brochures to train the RAG AI.</p>

        <form onSubmit={handleUpload} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Tenant ID (e.g., godrej_properties)</label>
            <input
              required
              type="text"
              value={tenant}
              onChange={(e) => setTenant(e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 outline-none text-white"
              placeholder="Client Name"
            />
          </div>

          <div className="flex items-center mt-2">
            <input
              type="checkbox"
              id="overwrite"
              checked={overwrite}
              onChange={(e) => setOverwrite(e.target.checked)}
              className="w-4 h-4 text-blue-600 bg-gray-900 border-gray-700 rounded focus:ring-blue-500 focus:ring-2"
            />
            <label
              htmlFor="overwrite"
              className="ml-2 text-sm font-medium text-gray-400"
            >
              Overwrite existing data for this client
            </label>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Master Password</label>
            <input
              required
              type="password"
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 outline-none text-white"
              placeholder="Enter admin secret"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">PDF Brochure</label>
            <input
              required
              type="file"
              accept=".pdf"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700"
            />
          </div>

          <button
            type="submit"
            disabled={status === "uploading"}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-lg transition-colors flex items-center justify-center disabled:bg-blue-800 disabled:cursor-not-allowed mt-4"
          >
            {status === "uploading" ? (
              <span className="animate-pulse">Vectorizing Document...</span>
            ) : (
              <>
                <UploadCloud size={20} className="mr-2" /> Train AI
              </>
            )}
          </button>
        </form>

        {}
        {status === "success" && (
          <div className="mt-6 bg-green-900/50 border border-green-800 text-green-300 p-4 rounded-lg flex items-start">
            <CheckCircle size={20} className="mr-2 mt-0.5 flex-shrink-0" />
            <p className="text-sm">{message}</p>
          </div>
        )}

        {status === "error" && (
          <div className="mt-6 bg-red-900/50 border border-red-800 text-red-300 p-4 rounded-lg flex items-start">
            <AlertCircle size={20} className="mr-2 mt-0.5 flex-shrink-0" />
            <p className="text-sm">{message}</p>
          </div>
        )}
      </div>
    </div>
  );
}