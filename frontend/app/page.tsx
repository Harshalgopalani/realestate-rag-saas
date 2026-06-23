"use client";

import { useState, Suspense } from "react";
import { Send, Bot, User, ArrowRight } from "lucide-react";
import { useSearchParams } from "next/navigation";

// The actual chat interface
function ChatWidget() {
  const searchParams = useSearchParams();
  // 1. DYNAMIC TENANT ID: It reads the URL! If no URL param, it defaults to a test mode.
  const TENANT_ID = searchParams.get("tenant") || "test_mode";

  const [isLeadCaptured, setIsLeadCaptured] = useState(false);
  const [leadForm, setLeadForm] = useState({ name: "", phone: "", email: "" });
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: `Hello! I am your Virtual Assistant. How can I help you today?`,
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleLeadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const response = await fetch("https://richportfolio.duckdns.org/api/leads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tenant: TENANT_ID, 
          name: leadForm.name,
          phone: leadForm.phone,
          email: leadForm.email,
        }),
      });

      if (response.ok) setIsLeadCaptured(true);
      else alert("Something went wrong. Please try again.");
    } catch (error) {
      console.error("Error:", error);
      alert("Failed to connect to the server.");
    } finally {
      setIsLoading(false);
    }
  };

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage, { role: "assistant", content: "" }]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch("https://richportfolio.duckdns.org/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-tenant-id": TENANT_ID,
        },
        body: JSON.stringify({ question: userMessage.content }),
      });

      if (!response.ok) throw new Error("Failed to connect to the backend.");
      if (!response.body) throw new Error("No response body");
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let isDone = false;

      while (!isDone) {
        const { value, done } = await reader.read();
        isDone = done;
        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1].content += chunk;
            return updated;
          });
        }
      }
    } catch (error) {
      setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = { role: "assistant", content: "Server connection failed." };
          return updated;
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="h-screen w-full bg-transparent flex flex-col font-sans">
      <div className="w-full bg-white shadow-xl flex flex-col h-full border border-gray-200 rounded-lg overflow-hidden">
        <div className="bg-blue-900 text-white p-4 flex items-center shadow-md z-10">
          <Bot className="mr-2" size={24} />
          <h1 className="text-xl font-bold">Property Assistant</h1>
        </div>

        {!isLeadCaptured ? (
          <div className="flex-1 flex flex-col justify-center items-center p-6 bg-gray-50 overflow-y-auto">
            <Bot size={48} className="text-blue-600 mb-4" />
            <h2 className="text-xl font-bold text-gray-800 mb-2 text-center">Welcome</h2>
            <p className="text-gray-600 mb-6 text-center text-sm">
              Please enter your details to start chatting.
            </p>

            <form onSubmit={handleLeadSubmit} className="w-full space-y-4">
              <input
                required type="text" placeholder="Full Name"
                className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none text-black text-sm"
                value={leadForm.name} onChange={(e) => setLeadForm({ ...leadForm, name: e.target.value })}
              />
              <input
                required type="email" placeholder="Email Address"
                className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none text-black text-sm"
                value={leadForm.email} onChange={(e) => setLeadForm({ ...leadForm, email: e.target.value })}
              />
              <input
                required type="tel" placeholder="Phone Number"
                className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none text-black text-sm"
                value={leadForm.phone} onChange={(e) => setLeadForm({ ...leadForm, phone: e.target.value })}
              />
              <button
                type="submit" disabled={isLoading}
                className="w-full bg-blue-600 text-white font-bold rounded-lg px-4 py-3 hover:bg-blue-700 transition-colors flex justify-center items-center text-sm"
              >
                {isLoading ? "Loading..." : "Start Chatting"} <ArrowRight size={16} className="ml-2" />
              </button>
            </form>
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
              {messages.map((msg, index) => (
                <div key={index} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`flex max-w-[85%] rounded-lg p-3 ${msg.role === "user" ? "bg-blue-600 text-white" : "bg-white border border-gray-200 text-gray-800 shadow-sm"}`}>
                    <div className="mr-2 mt-1">
                      {msg.role === "user" ? <User size={16} /> : <Bot size={16} className="text-blue-600" />}
                    </div>
                    <div className="text-sm leading-relaxed whitespace-pre-wrap text-black">
                      {msg.content}
                    </div>
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-white border border-gray-200 text-gray-500 shadow-sm rounded-lg p-3 text-sm flex items-center">
                    <Bot size={16} className="mr-2 text-blue-600 animate-pulse" /> Thinking...
                  </div>
                </div>
              )}
            </div>

            <form onSubmit={sendMessage} className="p-3 bg-white border-t border-gray-200 flex">
              <input
                type="text" value={input} onChange={(e) => setInput(e.target.value)}
                placeholder="Ask a question..." disabled={isLoading}
                className="flex-1 border border-gray-300 rounded-l-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 text-black text-sm"
              />
              <button
                type="submit" disabled={isLoading || !input.trim()}
                className="bg-blue-600 text-white px-4 py-2 rounded-r-lg hover:bg-blue-700 disabled:bg-blue-300 transition-colors"
              >
                <Send size={16} />
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}

// Next.js requires search params to be in a Suspense boundary
export default function Home() {
  return (
    <Suspense fallback={<div className="h-screen w-full flex items-center justify-center text-black">Loading Chat...</div>}>
      <ChatWidget />
    </Suspense>
  );
}