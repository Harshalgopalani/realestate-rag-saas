"use client";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

export default function ClientLeads() {
  const searchParams = useSearchParams();
  const tenant = searchParams.get("tenant");
  const secret = searchParams.get("secret");
  const [leads, setLeads] = useState([]);

  useEffect(() => {
    if (tenant && secret) {
      // Securely fetch leads from your Python backend
      fetch(`https://richportfolio.duckdns.org/api/leads?tenant=${tenant}&secret=${secret}`)
        .then((res) => res.json())
        .then((data) => {
          if (data.status === "success") setLeads(data.leads);
        });
    }
  }, [tenant, secret]);

  if (!tenant || !secret) return <div className="p-10 text-center text-gray-500">Unauthorized Access. Missing credentials.</div>;

  return (
    <div className="min-h-screen bg-gray-50 p-10 font-sans">
      <div className="max-w-5xl mx-auto bg-white p-8 rounded-xl shadow-sm border border-gray-100">
        <h1 className="text-3xl font-bold text-gray-800 mb-2 capitalize">{tenant.replace("_", " ")}</h1>
        <p className="text-gray-500 mb-8">Live AI Lead Generation Dashboard</p>
        
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200 text-sm font-semibold text-gray-600">
              <th className="p-4">Date</th>
              <th className="p-4">Name</th>
              <th className="p-4">Phone (WhatsApp)</th>
              <th className="p-4">Email</th>
            </tr>
          </thead>
          <tbody>
            {leads.map((lead: any, i: number) => (
              <tr key={i} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                <td className="p-4 text-sm text-gray-500">{new Date(lead.date).toLocaleString()}</td>
                <td className="p-4 font-medium text-gray-800">{lead.name}</td>
                <td className="p-4 text-blue-600 font-medium">{lead.phone}</td>
                <td className="p-4 text-gray-600">{lead.email}</td>
              </tr>
            ))}
            {leads.length === 0 && (
              <tr><td colSpan={4} className="p-8 text-center text-gray-500">No leads captured yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}