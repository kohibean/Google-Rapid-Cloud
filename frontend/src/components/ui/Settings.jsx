import { useState } from "react";
import { getConfig, setConfig } from "../../lib/api";

export default function Settings({ onClose, onSaved }) {
  const initial = getConfig();
  const [apiBase, setApiBase] = useState(initial.apiBase);
  const [appName, setAppName] = useState(initial.appName);

  function save() {
    setConfig({ apiBase, appName });
    onClose();
    onSaved?.();
  }

  return (
    <div
      className="fixed inset-0 bg-ink/40 flex items-center justify-center z-50 px-4"
      onClick={onClose}
    >
      <div
        className="bg-paper border border-ink max-w-md w-full p-7"
        onClick={(e) => e.stopPropagation()}
      >
        <p className="smallcaps mb-1">Settings</p>
        <h2 className="font-display text-2xl font-medium mb-6">Studio Configuration</h2>

        <label className="smallcaps block mb-2">ADK API Server URL</label>
        <input
          value={apiBase}
          onChange={(e) => setApiBase(e.target.value)}
          className="field w-full mb-5 font-mono text-[13px]"
        />

        <label className="smallcaps block mb-2">App Name</label>
        <input
          value={appName}
          onChange={(e) => setAppName(e.target.value)}
          className="field w-full mb-7 font-mono text-[13px]"
        />

        <div className="flex justify-end gap-3">
          <button onClick={onClose} className="btn-ghost">Cancel</button>
          <button onClick={save} className="btn-primary">Save & Reconnect</button>
        </div>
      </div>
    </div>
  );
}
