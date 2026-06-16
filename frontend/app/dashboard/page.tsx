"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import {
  Users,
  LayoutDashboard,
  Download,
  RefreshCw,
  UploadCloud,
} from "lucide-react";

// Define the shape of the data we expect from the API
type Lead = {
  id: number;
  name: string;
  email: string;
  phone: string;
  created_at: string;
};

export default function Dashboard() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Builder / Tenant ID
  const TENANT_ID = "kukreja_paris";

  // Function to fetch leads from the FastAPI backend
  const fetchLeads = async () => {
    setIsLoading(true);

    try {
      const response = await fetch("http://144.91.127.152:8000/api/leads", {
        headers: {
          "x-tenant-id": TENANT_ID,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to fetch leads");
      }

      const data = await response.json();
      setLeads(data);
    } catch (error) {
      console.error("Error fetching leads:", error);
    } finally {
      setIsLoading(false);
    }
  };

  // Function to convert the leads array into a downloadable CSV file
  const exportToCSV = () => {
    if (leads.length === 0) {
      alert("No leads to export.");
      return;
    }

    // CSV Headers
    const headers = ["ID", "Name", "Email", "Phone", "Date Captured"];

    // CSV Rows
    const csvRows = leads.map((lead) => {
      return [
        lead.id,
        `"${lead.name}"`,
        `"${lead.email}"`,
        `"${lead.phone}"`,
        `"${new Date(lead.created_at).toLocaleDateString()}"`,
      ].join(",");
    });

    // Combine Headers + Data
    const csvContent = [headers.join(","), ...csvRows].join("\n");

    // Create Downloadable File
    const blob = new Blob([csvContent], {
      type: "text/csv;charset=utf-8;",
    });

    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.setAttribute(
      "download",
      `leads_export_${new Date().toISOString().split("T")[0]}.csv`,
    );

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    URL.revokeObjectURL(url);
  };

  // Runs once when page loads
  useEffect(() => {
    fetchLeads();
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col md:flex-row">
      {/* Sidebar Navigation */}
      <div className="w-full md:w-64 bg-slate-900 text-white flex flex-col p-4 shadow-xl">
        <div className="flex items-center space-x-2 mb-8 mt-2 px-2">
          <LayoutDashboard className="text-blue-400" />
          <h1 className="text-xl font-bold tracking-wider">SaaS Admin</h1>
        </div>

        <nav className="space-y-2 flex-1">
          {/* Active Lead Center */}
          <button className="w-full flex items-center space-x-3 px-4 py-3 bg-blue-600 rounded-lg text-sm font-medium transition-colors">
            <Users size={18} />
            <span>Lead Center</span>
          </button>
          {/* Clickable Link to Upload Knowledge Base */}
          <Link
            href="/dashboard/upload"
            className="w-full flex items-center space-x-3 px-4 py-3 text-gray-300 hover:bg-slate-800 hover:text-white rounded-lg text-sm font-medium transition-colors"
          >
            <UploadCloud size={18} />
            <span>Knowledge Base</span>
          </Link>
        </nav>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 p-8">
        {/* Dashboard Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h2 className="text-3xl font-bold text-gray-800">Captured Leads</h2>
            <p className="text-gray-500 mt-1">
              Manage and analyze prospective homebuyers.
            </p>
          </div>

          <div className="flex space-x-3">
            <button
              onClick={fetchLeads}
              className="flex items-center space-x-2 bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors shadow-sm"
            >
              <RefreshCw
                size={16}
                className={isLoading ? "animate-spin" : ""}
              />
              <span>Refresh</span>
            </button>

            <button
              onClick={exportToCSV}
              className="flex items-center space-x-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
            >
              <Download size={16} />
              <span>Export CSV</span>
            </button>
          </div>
        </div>

        {/* Leads Data Table */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200 text-sm text-gray-500 uppercase tracking-wider">
                  <th className="p-4 font-medium">ID</th>
                  <th className="p-4 font-medium">Name</th>
                  <th className="p-4 font-medium">Contact Info</th>
                  <th className="p-4 font-medium">Captured Date</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-gray-200">
                {isLoading ? (
                  <tr>
                    <td colSpan={4} className="p-8 text-center text-gray-500">
                      Loading leads...
                    </td>
                  </tr>
                ) : leads.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="p-8 text-center text-gray-500">
                      No leads captured yet.
                    </td>
                  </tr>
                ) : (
                  leads.map((lead) => (
                    <tr
                      key={lead.id}
                      className="hover:bg-gray-50 transition-colors"
                    >
                      <td className="p-4 text-gray-500">#{lead.id}</td>

                      <td className="p-4 font-medium text-gray-900">
                        {lead.name}
                      </td>

                      <td className="p-4">
                        <div className="text-gray-900">{lead.email}</div>
                        <div className="text-gray-500 text-sm">
                          {lead.phone}
                        </div>
                      </td>

                      <td className="p-4 text-gray-500">
                        {new Date(lead.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
