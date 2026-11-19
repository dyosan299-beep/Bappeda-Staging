import { Volume2, Square } from "lucide-react";
import { useA11y } from "@/context/AccessibilityContext";

export function Speak({ text, label = "Bacakan", voice = "alloy", testid = "speak-btn", className = "" }) {
  const { speak, stop, speaking } = useA11y();
  return (
    <button
      type="button"
      data-testid={testid}
      onClick={() => (speaking ? stop() : speak(text, voice))}
      aria-label={speaking ? "Hentikan pembacaan" : label}
      className={`inline-flex items-center gap-2 rounded-full border-2 border-primary px-4 py-2 text-sm font-semibold text-primary transition-colors hover:bg-primary hover:text-primary-foreground focus:outline-none ${className}`}
    >
      {speaking ? <Square className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
      {speaking ? "Berhenti" : label}
    </button>
  );
}
