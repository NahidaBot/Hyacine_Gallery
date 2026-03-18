"use client";

import { useCallback, useEffect, useState } from "react";
import {
  adminFetchBotSettings,
  adminUpdateBotSettings,
} from "@/lib/admin-api";
import type { BotSetting } from "@/types";

const KNOWN_KEYS = [
  {
    key: "notification_interval",
    label: "Notification Interval (seconds)",
    description: "Anti-spam: disable notifications if posting within this interval",
    default: "600",
  },
  {
    key: "message_tail_text",
    label: "Message Tail Text",
    description: "Text appended to every channel post caption",
    default: "",
  },
];

export default function BotSettingsPage() {
  const [settings, setSettings] = useState<BotSetting[]>([]);
  const [values, setValues] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const data = await adminFetchBotSettings();
      setSettings(data);
      const map: Record<string, string> = {};
      for (const s of data) map[s.key] = s.value;
      // Fill in defaults for known keys not yet in DB
      for (const k of KNOWN_KEYS) {
        if (!(k.key in map)) map[k.key] = k.default;
      }
      setValues(map);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleSave = async () => {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      await adminUpdateBotSettings(values);
      setSuccess("Settings saved.");
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <p className="text-neutral-500">Loading...</p>;

  // Merge known keys with any extra keys from DB
  const extraKeys = Object.keys(values).filter(
    (k) => !KNOWN_KEYS.some((kk) => kk.key === k),
  );

  return (
    <div className="max-w-2xl">
      <h1 className="mb-6 text-2xl font-bold">Bot Settings</h1>

      {error && (
        <p className="mb-4 text-sm text-red-600">{error}</p>
      )}
      {success && (
        <p className="mb-4 text-sm text-green-600">{success}</p>
      )}

      <div className="space-y-6">
        {KNOWN_KEYS.map((k) => (
          <div key={k.key}>
            <label className="block text-sm font-medium">{k.label}</label>
            <p className="mb-1 text-xs text-neutral-500">{k.description}</p>
            <input
              type="text"
              value={values[k.key] ?? ""}
              onChange={(e) =>
                setValues((v) => ({ ...v, [k.key]: e.target.value }))
              }
              className="w-full rounded border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
            />
          </div>
        ))}

        {extraKeys.map((k) => (
          <div key={k}>
            <label className="block text-sm font-medium">{k}</label>
            <input
              type="text"
              value={values[k] ?? ""}
              onChange={(e) =>
                setValues((v) => ({ ...v, [k]: e.target.value }))
              }
              className="w-full rounded border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
            />
          </div>
        ))}
      </div>

      <button
        onClick={handleSave}
        disabled={saving}
        className="mt-6 rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {saving ? "Saving..." : "Save Settings"}
      </button>
    </div>
  );
}
