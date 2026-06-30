"use client";

import Panel from "@/components/Panel";

export default function SettingsPage() {
  return (
    <Panel title="Settings" subtitle="Privacy-first defaults and safety constraints.">
      <ul className="space-y-2 text-sm">
        <li>Runtime mode: Offline by default</li>
        <li>Data policy: Documents remain local unless explicitly exported</li>
        <li>Safety policy: No diagnosis/treatment/prescription recommendations</li>
        <li>Memory policy: Configurable TTL + manual clear controls</li>
      </ul>
      <p className="text-xs text-amber-700">
        Educational use only. Always consult qualified healthcare professionals for medical decisions.
      </p>
    </Panel>
  );
}
