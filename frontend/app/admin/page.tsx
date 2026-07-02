"use client";

import { useState } from "react";
import { ShieldAlert, Users, Database } from "lucide-react";

type ClientLog = {
  tenant_id: string;
  company_name: string;
  email: string;
  ip_address: string;
  timestamp: string;
};

export default function SuperAdminPage() {
  const [secret, setSecret] = useState("");
  const [clients, setClients] = useState<ClientLog[]>([]);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      const response = await fetch(`https://richportfolio.duckdns.org/api/admin/clients?secret=${secret}`);
      if (response.ok) {
        const data = await response.json();
        setClients(data.clients);
        setIsAuthenticated(true);
      } else {
        setError("Invalid Master Password");
      }
    } catch (err) {
      setError("Failed to connect to server");
    } finally {
      setIsLoading(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
        <form onSubmit={handleLogin} className="bg-gray-800 p-8 rounded-xl shadow-2xl max-w-sm w-full border border-gray-700">
          <ShieldAlert size={48} className="text-red-500 mx-auto mb-4" />
          <h1 className="text-xl font-bold text-white text-center mb-6">SVE Super Admin</h1>
          {error && <p className="text-red-400 text-sm mb-4 text-center">{error}</p>}
          <input type="password" placeholder="Master Password" value={secret} onChange={(e) => setSecret(e.target.value)} className="w-full bg-gray-900 border border-gray-600 rounded-lg px-4 py-3 text-white mb-4 outline-none focus:border-red-500" />
          <button type="submit" disabled={isLoading} className="w-full bg-red-600 hover:bg-red-700 text-white font-bold py-3 rounded-lg transition-colors">
            {isLoading ? "Authenticating..." : "Access Legal Logs"}
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center space-x-3 mb-8">
          <Database size={32} className="text-blue-900" />
          <h1 className="text-3xl font-bold text-blue-900">Client Legal Onboarding Logs</h1>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-100 text-gray-700 border-b border-gray-200">
                <th className="p-4 font-semibold">Company Name</th>
                <th className="p-4 font-semibold">Tenant ID</th>
                <th className="p-4 font-semibold">Admin Email</th>
                <th className="p-4 font-semibold">IP Address (Legal Proof)</th>
                <th className="p-4 font-semibold">Date Accepted (UTC)</th>
              </tr>
            </thead>
            <tbody>
              {clients.map((client, i) => (
                <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="p-4 font-medium text-gray-900">{client.company_name}</td>
                  <td className="p-4 text-blue-600 font-mono text-sm">{client.tenant_id}</td>
                  <td className="p-4 text-gray-600">{client.email}</td>
                  <td className="p-4 text-gray-600 font-mono text-sm">{client.ip_address}</td>
                  <td className="p-4 text-gray-600">{new Date(client.timestamp).toLocaleString()}</td>
                </tr>
              ))}
              {clients.length === 0 && (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-gray-500">No clients onboarded yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}