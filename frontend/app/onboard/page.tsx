"use client";

import { useState } from "react";
import { ShieldCheck, Building, Mail, CheckCircle } from "lucide-react";

export default function OnboardingPage() {
  const [formData, setFormData] = useState({
    company_name: "",
    project_name: "",
    email: "",
    agreed_to_terms: false,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.agreed_to_terms) {
      setError("You must agree to the Master Subscription Agreement to proceed.");
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      const response = await fetch("https://richportfolio.duckdns.org/api/onboard", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        setIsSuccess(true);
      } else {
        const data = await response.json();
        setError(data.detail || "Something went wrong.");
      }
    } catch (err) {
      setError("Failed to connect to the server.");
    } finally {
      setIsLoading(false);
    }
  };

  if (isSuccess) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-xl shadow-lg p-8 text-center border border-gray-200">
          <CheckCircle size={64} className="text-green-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Registration Complete</h2>
          <p className="text-gray-600 mb-6">
            Your legal agreement has been recorded. Your unique Tenant ID, dashboard links, and widget integration code have been emailed to <strong>{formData.email}</strong>.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="max-w-2xl w-full bg-white rounded-xl shadow-xl overflow-hidden border border-gray-200">
        <div className="bg-blue-900 p-6 text-white flex items-center space-x-3">
          <ShieldCheck size={32} />
          <div>
            <h1 className="text-2xl font-bold">Client Onboarding Portal</h1>
            <p className="text-blue-200 text-sm">Shree Vinayak Enterprises AI Infrastructure</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="p-8 space-y-6">
          {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm font-medium border border-red-200">{error}</div>}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-sm font-bold text-gray-700 flex items-center"><Building size={16} className="mr-2"/> Legal Company Name</label>
              <input required type="text" className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none text-black" value={formData.company_name} onChange={(e) => setFormData({...formData, company_name: e.target.value})} placeholder="e.g. Godrej Properties Ltd" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-bold text-gray-700 flex items-center"><Building size={16} className="mr-2"/> Real Estate Project Name</label>
              <input required type="text" className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none text-black" value={formData.project_name} onChange={(e) => setFormData({...formData, project_name: e.target.value})} placeholder="e.g. Splendour Phase 2" />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-bold text-gray-700 flex items-center"><Mail size={16} className="mr-2"/> Administrator Email</label>
            <input required type="email" className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none text-black" value={formData.email} onChange={(e) => setFormData({...formData, email: e.target.value})} placeholder="salesdirector@company.com" />
          </div>

          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mt-6">
            <div className="flex items-start space-x-3">
              <input required type="checkbox" id="legal_agree" className="mt-1 w-5 h-5 text-blue-600" checked={formData.agreed_to_terms} onChange={(e) => setFormData({...formData, agreed_to_terms: e.target.checked})} />
              <label htmlFor="legal_agree" className="text-sm text-gray-700 leading-relaxed cursor-pointer">
                I hereby declare that I am an authorized representative of the Company. I have read, understood, and agree to the <a href="/msa_agreement.pdf" target="_blank" className="text-blue-600 underline font-bold">Master Subscription Agreement (PDF)</a>. I acknowledge that Shree Vinayak Enterprises operates strictly as a Data Processor, and the Company retains full liability for all uploaded content and end-user data under DPDPA 2023 and RERA.
              </label>
            </div>
          </div>

          <button type="submit" disabled={isLoading || !formData.agreed_to_terms} className="w-full bg-blue-600 text-white font-bold rounded-lg px-4 py-4 hover:bg-blue-700 disabled:bg-gray-400 transition-colors">
            {isLoading ? "Generating Secure Infrastructure..." : "Accept Terms & Generate Infrastructure"}
          </button>
        </form>
      </div>
    </div>
  );
}