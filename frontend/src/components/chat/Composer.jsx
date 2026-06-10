import { useEffect, useRef, useState } from "react";

export default function Composer({ onSend, prefill, onPrefillUsed, disabled }) {
  const [text, setText] = useState("");
  const [image, setImage] = useState(null);
  const fileRef = useRef(null);
  const taRef = useRef(null);

  useEffect(() => {
    if (prefill) {
      setText(prefill);
      onPrefillUsed?.();
      taRef.current?.focus();
    }
  }, [prefill, onPrefillUsed]);

  function handleKey(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  async function submit() {
    if (disabled) return;
    const t = text.trim();
    const img = image;
    setText("");
    setImage(null);
    if (fileRef.current) fileRef.current.value = "";
    await onSend({ text: t, image: img });
  }

  return (
    <div className="border-t border-ink pt-4">
      {image && (
        <div className="mb-2 flex items-center gap-2 font-mono text-[11px] text-ink-soft">
          <span>📎 {image.name}</span>
          <button onClick={() => setImage(null)} className="text-accent hover:underline">remove</button>
        </div>
      )}
      <div className="flex items-end gap-3">
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          className="w-11 h-11 border border-ink-soft text-ink-soft hover:border-accent
                     hover:text-accent flex items-center justify-center text-lg flex-shrink-0
                     transition-colors"
          title="Attach artwork"
        >
          ⬡
        </button>
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => setImage(e.target.files?.[0] || null)}
        />
        <textarea
          ref={taRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Speak to your studio companion…"
          rows={1}
          className="field flex-1 resize-none min-h-[44px] max-h-[120px] leading-snug"
        />
        <button
          onClick={submit}
          disabled={disabled || (!text.trim() && !image)}
          className="btn-primary"
        >
          Send
        </button>
      </div>
    </div>
  );
}
