// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

// Ported from frontend_references/src/components/knowledge_graph/GraphControls.tsx.

import { Maximize, Minimize, Minus, Plus, RotateCcw } from "lucide-react";

interface GraphControlsProps {
  onZoom: (direction: "in" | "out" | "reset") => void;
  onFullscreen: () => void;
  isFullscreen: boolean;
}

const buttonClass =
  "grid size-8 place-items-center rounded-lg text-neutral-400 hover:bg-neutral-800 hover:text-white transition-colors cursor-pointer";

export function GraphControls({ onZoom, onFullscreen, isFullscreen }: GraphControlsProps) {
  return (
    <div className="flex flex-col rounded-xl border border-[#2E2E2E] bg-[#161616]/95 p-1 shadow-2xl backdrop-blur-md">
      <button type="button" className={buttonClass} title="Perbesar" onClick={() => onZoom("in")}>
        <Plus size={15} />
      </button>
      <button type="button" className={buttonClass} title="Perkecil" onClick={() => onZoom("out")}>
        <Minus size={15} />
      </button>
      <button type="button" className={buttonClass} title="Atur ulang tampilan" onClick={() => onZoom("reset")}>
        <RotateCcw size={15} />
      </button>
      <button type="button" className={buttonClass} title="Layar penuh" onClick={onFullscreen}>
        {isFullscreen ? <Minimize size={15} /> : <Maximize size={15} />}
      </button>
    </div>
  );
}
