"use client";

import { Sparkles } from "lucide-react";

interface AvatarProps {
  isThinking?: boolean;
}

export default function Avatar({ isThinking = false }: AvatarProps) {
  return (
    <div className="relative">
      <div
        className={`
          w-32 h-32
          rounded-full
          bg-gradient-to-br
          from-amber-400
          to-amber-600
          flex
          items-center
          justify-center
          shadow-lg
          ${isThinking ? "animate-pulse" : ""}
        `}
      >
        <span className="text-5xl">🤖</span>
      </div>

      {isThinking && (
        <div
          className="
            absolute
            -top-2
            -right-2
            bg-white
            rounded-full
            p-2
            shadow
          "
        >
          <Sparkles
            size={18}
            className="
              text-amber-600
              animate-spin
            "
          />
        </div>
      )}
    </div>
  );
}
