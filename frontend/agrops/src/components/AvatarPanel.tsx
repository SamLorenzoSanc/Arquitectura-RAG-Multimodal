"use client";

import { useRef, useState } from "react";
import Avatar from "./Avatar";
import { Mic, MicOff, Volume2, Loader2 } from "lucide-react";

interface AvatarPanelProps {
  organizationName: string;
  model: string;
  tenantId: string;
  knowledgeBaseId: string;
  onAssistantResponse?: (text: string) => void;
}

export default function AvatarPanel({
  organizationName,
  model,
  tenantId,
  knowledgeBaseId,
  onAssistantResponse,
}: AvatarPanelProps) {
  const [isListening, setIsListening] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [partialText, setPartialText] = useState("");

  const websocket = useRef<WebSocket | null>(null);
  const mediaRecorder = useRef<MediaRecorder | null>(null);

  const speak = (text: string) => {
    if (!window.speechSynthesis) return;

    const utterance = new SpeechSynthesisUtterance(text);

    utterance.lang = "es-ES";
    utterance.rate = 1;

    window.speechSynthesis.speak(utterance);
  };

  const startVoice = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });

      const ws = new WebSocket(
        `ws://localhost:8000/speech/transcribe?tenant_id=${tenantId}&knowledge_base_id=${knowledgeBaseId}`,
      );

      websocket.current = ws;

      ws.onopen = () => {
        const recorder = new MediaRecorder(stream, {
          mimeType: "audio/webm",
        });

        mediaRecorder.current = recorder;

        recorder.ondataavailable = async (event) => {
          if (event.data.size > 0 && ws.readyState === WebSocket.OPEN) {
            const buffer = await event.data.arrayBuffer();

            ws.send(buffer);
          }
        };

        recorder.start(250);
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        switch (data.type) {
          case "partial":
            setPartialText(data.text);

            break;

          case "thinking":
            setIsThinking(true);

            break;

          case "assistant":
            setIsThinking(false);

            setPartialText("");

            onAssistantResponse?.(data.text);

            speak(data.text);

            break;
        }
      };

      setIsListening(true);
    } catch (error) {
      console.error("Error audio", error);
    }
  };

  const stopVoice = () => {
    mediaRecorder.current?.stop();

    websocket.current?.close();

    mediaRecorder.current = null;
    websocket.current = null;

    setIsListening(false);
    setPartialText("");
  };

  return (
    <aside
      className="
        w-[260px]
        shrink-0
        border-r
        border-gray-200
        bg-white
        flex
        flex-col
        items-center
        justify-center
        p-6
      "
    >
      <Avatar isThinking={isThinking} />

      <h3
        className="
          mt-6
          text-sm
          font-bold
          text-slate-900
        "
      >
        Asistente IA
      </h3>

      <p
        className="
          mt-1
          text-xs
          text-gray-500
          text-center
        "
      >
        {organizationName}
      </p>

      <div
        className="
          mt-5
          w-full
          rounded-lg
          bg-amber-50
          border
          border-amber-200
          px-3
          py-2
          text-center
        "
      >
        <p
          className="
            text-[10px]
            uppercase
            font-bold
            text-amber-600
          "
        >
          Modelo activo
        </p>

        <p
          className="
            text-xs
            font-semibold
            text-slate-700
            truncate
          "
        >
          {model}
        </p>
      </div>

      <button
        onClick={isListening ? stopVoice : startVoice}
        className={`
          mt-6
          flex
          items-center
          gap-2
          px-4
          py-3
          rounded-xl
          text-sm
          font-semibold
          transition

          ${
            isListening
              ? "bg-red-100 text-red-700 border border-red-200"
              : "bg-amber-600 text-white hover:bg-amber-700"
          }

        `}
      >
        {isListening ? (
          <>
            <MicOff size={18} />
            Detener
          </>
        ) : (
          <>
            <Mic size={18} />
            Hablar
          </>
        )}
      </button>

      {isThinking && (
        <div
          className="
          mt-4
          flex
          items-center
          gap-2
          text-xs
          text-gray-500
          "
        >
          <Loader2 size={14} className="animate-spin" />
          Pensando...
        </div>
      )}

      {partialText && (
        <div
          className="
          mt-4
          text-xs
          text-gray-500
          text-center
          italic
          "
        >
          "{partialText}"
        </div>
      )}

      <div
        className="
          mt-6
          flex
          items-center
          gap-2
          text-[11px]
          text-gray-400
          text-center
        "
      >
        <Volume2 size={13} />
        Voz activa
      </div>
    </aside>
  );
}
