"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { Send, Bot, User, ArrowRight, ShieldAlert } from "lucide-react";
import { useSearchParams } from "next/navigation";

type Message = {
  role: "user" | "assistant";
  content: string;
};

// --- THE CHAT WIDGET COMPONENT ---
function ChatWidget() {
  const searchParams = useSearchParams();
  const activeTenant = searchParams.get("tenant") || "kukreja_paris";

  const [isLeadCaptured, setIsLeadCaptured] = useState(false);
  const [leadForm, setLeadForm] = useState({ name: "", phone: "", email: "" });
  
  // LEGAL UPDATE: State for the mandatory consent checkbox
  const [consentGiven, setConsentGiven] = useState(false);

  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: `Hello! I am your Virtual Assistant. How can I help you with your property search today?`,
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const chatContainerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTo({
        top: chatContainerRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleLeadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!consentGiven) return; // Double protection
    
    setIsLoading(true);

    try {
      const response = await fetch("https://richportfolio.duckdns.org/api/leads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tenant: activeTenant,
          name: leadForm.name,
          phone: leadForm.phone,
          email: leadForm.email,
        }),
      });

      if (response.ok) {
        setIsLeadCaptured(true);
      } else {
        alert("Something went wrong. Please try again.");
      }
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

    const userMessage: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage, { role: "assistant", content: "" }]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch("https://richportfolio.duckdns.org/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-tenant-id": activeTenant,
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
            const updatedMessages = [...prev];
            const lastIndex = updatedMessages.length - 1;
            updatedMessages[lastIndex] = {
              ...updatedMessages[lastIndex],
              content: updatedMessages[lastIndex].content + chunk,
            };
            return updatedMessages;
          });
        }
      }
    } catch (error) {
      console.error("Error:", error);
      setMessages((prev) => {
          const updatedMessages = [...prev];
          updatedMessages[updatedMessages.length - 1] = { 
            role: "assistant", 
            content: "Server connection failed." 
          };
          return updatedMessages;
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl bg-white rounded-xl shadow-xl flex flex-col h-[85vh] max-h-[800px] overflow-hidden border border-gray-200 relative">
        
        <div className="bg-blue-900 text-white p-4 flex items-center shadow-md z-10">
          <Bot className="mr-2" size={24} />
          <h1 className="text-xl font-bold">Property Assistant</h1>
        </div>

        {!isLeadCaptured ? (
          <div className="flex-1 flex flex-col justify-center items-center p-8 bg-gray-50 overflow-y-auto">
            <Bot size={48} className="text-blue-600 mb-4" />
            <h2 className="text-2xl font-bold text-gray-800 mb-2">Welcome</h2>
            <p className="text-gray-600 mb-8 text-center text-sm">
              Enter your details to chat with our AI property assistant.
            </p>

            <form onSubmit={handleLeadSubmit} className="w-full max-w-sm space-y-4">
              <input required type="text" placeholder="Full Name" className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 outline-none text-black" value={leadForm.name} onChange={(e) => setLeadForm({ ...leadForm, name: e.target.value })} />
              <input required type="email" placeholder="Email Address" className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 outline-none text-black" value={leadForm.email} onChange={(e) => setLeadForm({ ...leadForm, email: e.target.value })} />
              <input required type="tel" placeholder="Phone Number" className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 outline-none text-black" value={leadForm.phone} onChange={(e) => setLeadForm({ ...leadForm, phone: e.target.value })} />
              
              {/* LEGAL UPDATE 1: DPDPA Consent Checkbox */}
              <div className="flex items-start space-x-2 pt-2">
                <input required type="checkbox" id="user_consent" className="mt-1 w-4 h-4 cursor-pointer" checked={consentGiven} onChange={(e) => setConsentGiven(e.target.checked)} />
                <label htmlFor="user_consent" className="text-xs text-gray-600 cursor-pointer leading-tight">
                  I consent to being contacted regarding this property inquiry via phone, WhatsApp, or email by the authorized sales team.
                </label>
              </div>

              {/* LEGAL UPDATE 2: Lead Capture Disclaimer */}
              <div className="bg-blue-50 p-3 rounded-lg flex items-start space-x-2 border border-blue-100">
                <ShieldAlert size={14} className="text-blue-600 flex-shrink-0 mt-0.5" />
                <p className="text-[10px] text-gray-600 leading-tight">
                  This chatbot uses Artificial Intelligence to answer queries based on developer-provided materials. It does not constitute a legally binding offer.
                </p>
              </div>

              <button type="submit" disabled={isLoading || !consentGiven} className="w-full bg-blue-600 text-white font-bold rounded-lg px-4 py-3 hover:bg-blue-700 disabled:bg-gray-400 transition-colors flex justify-center items-center mt-2">
                {isLoading ? "Starting Chat..." : "Start Chatting"} <ArrowRight size={18} className="ml-2" />
              </button>
            </form>
          </div>
        ) : (
          <>
            <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
              {messages.map((msg, index) => (
                <div key={index} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`flex max-w-[80%] rounded-lg p-3 ${msg.role === "user" ? "bg-blue-600 text-white" : "bg-white border border-gray-200 text-gray-800 shadow-sm"}`}>
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
                  <div className="bg-white border border-gray-200 shadow-sm rounded-lg p-4 flex items-center space-x-2">
                    <Bot size={16} className="text-blue-600" />
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="bg-white border-t border-gray-200 flex flex-col">
              <form onSubmit={sendMessage} className="p-4 flex pb-2">
                <input type="text" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about pricing, amenities..." disabled={isLoading} className="flex-1 border border-gray-300 rounded-l-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 text-black" />
                <button type="submit" disabled={isLoading || !input.trim()} className="bg-blue-600 text-white px-4 py-2 rounded-r-lg hover:bg-blue-700 disabled:bg-blue-300 transition-colors">
                  <Send size={18} />
                </button>
              </form>
              
              {/* LEGAL UPDATE 3: Permanent Chat "Safe Harbor" Footer */}
              <div className="px-4 pb-3 text-center">
                <p className="text-[10px] text-gray-400 leading-tight">
                  Responses are AI-generated for informational purposes. Please verify all pricing, availability, and RERA details with the official sales team.
                </p>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <Suspense fallback={<div className="p-10 text-center min-h-screen flex items-center justify-center">Loading Chat Experience...</div>}>
      <ChatWidget />
    </Suspense>
  );
}