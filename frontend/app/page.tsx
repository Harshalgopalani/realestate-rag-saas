"use client";

import { useState } from "react";
import { Send, Bot, User, ArrowRight } from "lucide-react";

// 1. THIS IS OUR SIMULATED WIDGET INSTALLATION
// Change this to "godrej" later to watch the UI break/change!
const TENANT_ID = "kukreja_paris";

type Message = {
  role: "user" | "assistant";
  content: string;
};

export default function Home() {
  const [isLeadCaptured, setIsLeadCaptured] = useState(false);
  const [leadForm, setLeadForm] = useState({ name: "", phone: "", email: "" });

  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Hello! I am your Virtual Assistant. How can I help you with your new home today?",
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
        headers: {
          "Content-Type": "application/json",
          "x-tenant-id": TENANT_ID, // <-- PASSING THE BADGE
        },
        body: JSON.stringify(leadForm),
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
    
    // 1. Add the user's message AND an empty bot message immediately
    setMessages((prev) => [
      ...prev, 
      userMessage,
      { role: "assistant", content: "" } // Placeholder for the stream
    ]);
    
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
      
      // 2. The Streaming Receiver (The Magic Part)
      if (!response.body) throw new Error("No response body");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let isDone = false;

      // Keep reading chunks of text until the AI finishes
      while (!isDone) {
        const { value, done } = await reader.read();
        isDone = done;
        
        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          
          // Update the very last message in the array (the bot's message) by appending the new chunk
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
          const lastIndex = updatedMessages.length - 1;
          // If it fails, overwrite the placeholder with the error
          updatedMessages[lastIndex] = { role: "assistant", content: "Server connection failed." };
          return updatedMessages;
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl bg-white rounded-xl shadow-xl flex flex-col h-[85vh] max-h-[800px]">
        <div className="bg-blue-900 text-white p-4 flex items-center shadow-md z-10">
          <Bot className="mr-2" size={24} />
          <h1 className="text-xl font-bold">Property Assistant</h1>
        </div>

        {!isLeadCaptured ? (
          <div className="flex-1 flex flex-col justify-center items-center p-8 bg-gray-50 overflow-y-auto">
            <Bot size={48} className="text-blue-600 mb-4" />
            <h2 className="text-2xl font-bold text-gray-800 mb-2">Welcome</h2>
            <p className="text-gray-600 mb-8 text-center">
              Please enter your details to chat with our AI property assistant.
            </p>

            <form
              onSubmit={handleLeadSubmit}
              className="w-full max-w-sm space-y-4"
            >
              <input
                required
                type="text"
                placeholder="Full Name"
                className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 outline-none text-black"
                value={leadForm.name}
                onChange={(e) =>
                  setLeadForm({ ...leadForm, name: e.target.value })
                }
              />
              <input
                required
                type="email"
                placeholder="Email Address"
                className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 outline-none text-black"
                value={leadForm.email}
                onChange={(e) =>
                  setLeadForm({ ...leadForm, email: e.target.value })
                }
              />
              <input
                required
                type="tel"
                placeholder="Phone Number"
                className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 outline-none text-black"
                value={leadForm.phone}
                onChange={(e) =>
                  setLeadForm({ ...leadForm, phone: e.target.value })
                }
              />
              <button
                type="submit"
                disabled={isLoading}
                className="w-full bg-blue-600 text-white font-bold rounded-lg px-4 py-3 hover:bg-blue-700 transition-colors flex justify-center items-center"
              >
                {isLoading ? "Starting Chat..." : "Start Chatting"}{" "}
                <ArrowRight size={18} className="ml-2" />
              </button>
            </form>
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
              {messages.map((msg, index) => (
                <div
                  key={index}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`flex max-w-[80%] rounded-lg p-3 ${msg.role === "user" ? "bg-blue-600 text-white" : "bg-white border border-gray-200 text-gray-800 shadow-sm"}`}
                  >
                    <div className="mr-2 mt-1">
                      {msg.role === "user" ? (
                        <User size={16} />
                      ) : (
                        <Bot size={16} className="text-blue-600" />
                      )}
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
                    <Bot
                      size={16}
                      className="mr-2 text-blue-600 animate-pulse"
                    />{" "}
                    Thinking...
                  </div>
                </div>
              )}
            </div>

            <form
              onSubmit={sendMessage}
              className="p-4 bg-white border-t border-gray-200 flex"
            >
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about pricing, amenities..."
                disabled={isLoading}
                className="flex-1 border border-gray-300 rounded-l-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 text-black"
              />
              <button
                type="submit"
                disabled={isLoading || !input.trim()}
                className="bg-blue-600 text-white px-4 py-2 rounded-r-lg hover:bg-blue-700 disabled:bg-blue-300 transition-colors"
              >
                <Send size={18} />
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
