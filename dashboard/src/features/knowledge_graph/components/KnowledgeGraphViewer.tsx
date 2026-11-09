// SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
// SPDX-License-Identifier: Apache-2.0

// Ported from frontend_references/src/features/knowledge_graph/components/KnowledgeGraphViewer.tsx.

import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { SigmaContainer, useRegisterEvents, useSetSettings, useSigma } from "@react-sigma/core";
import { EdgeRectangleProgram, NodeCircleProgram, NodePointProgram } from "sigma/rendering";
import { NodeBorderProgram } from "@sigma/node-border";
import { createEdgeCurveProgram } from "@sigma/edge-curve";
import forceAtlas2 from "graphology-layout-forceatlas2";
import ForceAtlas2Supervisor from "graphology-layout-forceatlas2/worker";
import NoverlapSupervisor from "graphology-layout-noverlap/worker";
import { GraphControls } from "@/components/knowledge_graph/GraphControls";
import { GraphLegend } from "@/components/knowledge_graph/GraphLegend";
import { GraphProperties } from "@/components/knowledge_graph/GraphProperties";
import { KnowledgeGraphHeader } from "@/components/knowledge_graph/KnowledgeGraphHeader";
import { sigmaGraphFromRaw, type SigmaGraph } from "../graph";
import { useKnowledgeGraphStore } from "../store";
import type { EdgeDisplayData, NodeDisplayData } from "../types";
import { useKnowledgeGraph } from "../useKnowledgeGraph";
import "@react-sigma/core/lib/style.css";

const EDGE_PERFORMANCE_LIMIT = 5_000;
const LABEL_PERFORMANCE_LIMIT = 2_000;
// ForceAtlas2 never stops on its own, so we poll node positions and stop once
// the layout has settled (mean per-poll movement below SETTLE_THRESHOLD of the
// graph extent for SETTLE_POLLS polls in a row). Noverlap stops itself.
const LAYOUT_POLL_MS = 100;
const SETTLE_THRESHOLD = 0.005;
const SETTLE_POLLS = 5;
// ponytail: hard cap for graphs that oscillate and never settle; raise if large graphs get cut off.
const MAX_LAYOUT_MS = 60_000;
const NOVERLAP_SETTINGS = { margin: 10, expansion: 1.1, gridSize: 1, ratio: 1, speed: 3 };
const ZOOM_STEP = { in: 0.65, out: 1.55 };
const ZOOM_MS = 180;

// Dark theme palette, as in frontend_references.
const LABEL_COLOR_DARK = "#00E5FF";
const NODE_COLOR_DISABLED = "#333333";
const NODE_BORDER_COLOR_SELECTED = "#E72C0E";
const EDGE_COLOR_DARK = "#555555";
const EDGE_COLOR_SELECTED = "#E72C0E";
const EDGE_COLOR_HIGHLIGHTED_DARK = "#E72C0E";

type LayoutSupervisor = { start: () => void; stop: () => void; kill: () => void; isRunning: () => boolean };

// Mean node movement since the previous call, relative to the graph extent.
function layoutMovement(graph: SigmaGraph, previous: Float64Array): number {
  let moved = 0;
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;
  let i = 0;
  graph.forEachNode((_, { x, y }) => {
    moved += Math.abs(x - previous[i]) + Math.abs(y - previous[i + 1]);
    previous[i++] = x;
    previous[i++] = y;
    minX = Math.min(minX, x);
    maxX = Math.max(maxX, x);
    minY = Math.min(minY, y);
    maxY = Math.max(maxY, y);
  });
  return moved / graph.order / (Math.max(maxX - minX, maxY - minY) || 1);
}

function sigmaSettings(enableEdgeEvents: boolean, useCurvedEdges: boolean) {
  return {
    allowInvalidContainer: true,
    defaultNodeType: "border",
    defaultEdgeType: useCurvedEdges ? "curvedNoArrow" : "rect",
    defaultEdgeColor: EDGE_COLOR_DARK,
    hideEdgesOnMove: true,
    enableEdgeEvents,
    labelRenderedSizeThreshold: 6,
    labelGridCellSize: 60,
    labelSize: 12,
    renderEdgeLabels: false,
    labelColor: { color: LABEL_COLOR_DARK, attribute: "labelColor" },
    edgeProgramClasses: {
      rect: EdgeRectangleProgram,
      curvedNoArrow: createEdgeCurveProgram(),
    },
    nodeProgramClasses: {
      default: NodePointProgram,
      circle: NodeCircleProgram,
      border: NodeBorderProgram,
    },
  };
}

export function KnowledgeGraphViewer({ databaseId }: { databaseId: string }) {
  const dataVersion = useKnowledgeGraphStore((state) => state.dataVersion);
  const rawGraph = useKnowledgeGraphStore((state) => state.rawGraph);
  const isLayoutRunning = useKnowledgeGraphStore((state) => state.isLayoutRunning);
  const { loading, error, reload } = useKnowledgeGraph(databaseId);
  const edgeCount = rawGraph?.edges.length ?? 0;
  const edgeEvents = edgeCount <= EDGE_PERFORMANCE_LIMIT;
  const useCurvedEdges = edgeCount > 0 && edgeCount <= EDGE_PERFORMANCE_LIMIT;

  const rendererSettings = useMemo(() => sigmaSettings(edgeEvents, useCurvedEdges), [edgeEvents, useCurvedEdges]);

  // Rebuilt from scratch on every new dataset; see sigmaGraphFromRaw.
  const graph = useMemo(
    () => sigmaGraphFromRaw(useKnowledgeGraphStore.getState().rawGraph ?? { nodes: [], edges: [] }),
    // Deliberately narrow deps: dataVersion changes exactly when rawGraph is replaced.
    [dataVersion],
  );

  return (
    // `knowledge-graph` scopes the preflight these copied components expect; see globals.css.
    <div className="knowledge-graph relative h-full w-full overflow-hidden bg-[#141414]">
      <SigmaContainer
        key={`${dataVersion}-${edgeEvents}-${useCurvedEdges}`}
        graph={graph}
        settings={rendererSettings}
        className="!size-full !bg-[#141414]"
      >
        <GraphCanvas graph={graph} edgeEvents={edgeEvents} />
      </SigmaContainer>
      {(loading || isLayoutRunning) && (
        <StatusOverlay>
          <span className="mx-auto mb-2 block size-7 animate-spin rounded-full border-4 border-[#ffb5a0] border-t-transparent" />
          {loading ? "Memuat data graf…" : "Menghitung tata letak…"}
        </StatusOverlay>
      )}
      {!loading && !error && rawGraph?.nodes.length === 0 && (
        <StatusOverlay>Belum ada term atau tabel. Jalankan Ingest ulang di Pengaturan → Operasi.</StatusOverlay>
      )}
      {error && <ErrorOverlay message={error} onRetry={reload} />}
    </div>
  );
}

function GraphCanvas({ graph, edgeEvents }: { graph: SigmaGraph; edgeEvents: boolean }) {
  const sigma = useSigma<NodeDisplayData, EdgeDisplayData>();
  const registerEvents = useRegisterEvents<NodeDisplayData, EdgeDisplayData>();
  const setSettings = useSetSettings<NodeDisplayData, EdgeDisplayData>();
  const selectedNode = useKnowledgeGraphStore((state) => state.selectedNode);
  const selectedEdge = useKnowledgeGraphStore((state) => state.selectedEdge);
  const focusedNode = useKnowledgeGraphStore((state) => state.focusedNode);
  const focusedEdge = useKnowledgeGraphStore((state) => state.focusedEdge);
  const moveToSelectedNode = useKnowledgeGraphStore((state) => state.moveToSelectedNode);
  const selectNode = useKnowledgeGraphStore((state) => state.selectNode);
  const selectEdge = useKnowledgeGraphStore((state) => state.selectEdge);
  const focusNode = useKnowledgeGraphStore((state) => state.focusNode);
  const focusEdge = useKnowledgeGraphStore((state) => state.focusEdge);
  const clearSelection = useKnowledgeGraphStore((state) => state.clearSelection);
  const setLayoutRunning = useKnowledgeGraphStore((state) => state.setLayoutRunning);
  const updateNodePosition = useKnowledgeGraphStore((state) => state.updateNodePosition);
  const supervisor = useRef<LayoutSupervisor | null>(null);
  const layoutTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    const sync = () => setIsFullscreen(document.fullscreenElement === sigma.getContainer());
    document.addEventListener("fullscreenchange", sync);
    return () => document.removeEventListener("fullscreenchange", sync);
  }, [sigma]);

  const stopLayout = useCallback(() => {
    if (layoutTimer.current) clearInterval(layoutTimer.current);
    layoutTimer.current = null;
    try {
      supervisor.current?.stop();
      supervisor.current?.kill();
    } catch {
      // The worker already closed.
    }
    supervisor.current = null;
    setLayoutRunning(false);
  }, [setLayoutRunning]);

  const runLayout = useCallback(
    (next: () => LayoutSupervisor, onDone?: () => void) => {
      stopLayout();
      try {
        supervisor.current = next();
        sigma.setCustomBBox(null);
        supervisor.current.start();
        setLayoutRunning(true);
        const deadline = performance.now() + MAX_LAYOUT_MS;
        const previous = new Float64Array(graph.order * 2);
        layoutMovement(graph, previous);
        let stillPolls = 0;
        layoutTimer.current = setInterval(() => {
          stillPolls = layoutMovement(graph, previous) < SETTLE_THRESHOLD ? stillPolls + 1 : 0;
          if (supervisor.current?.isRunning() && stillPolls < SETTLE_POLLS && performance.now() < deadline) return;
          stopLayout();
          sigma.refresh();
          onDone?.();
        }, LAYOUT_POLL_MS);
      } catch {
        stopLayout();
      }
    },
    [graph, setLayoutRunning, sigma, stopLayout],
  );

  useEffect(() => {
    // SigmaContainer is remounted (via `key`) whenever the data changes, so
    // this component mounts fresh with `graph` already fully built and bound.
    // ForceAtlas2, then remove overlaps, once per mount.
    if (graph.order > 1) {
      runLayout(
        () => new ForceAtlas2Supervisor(graph as never, { settings: forceAtlas2.inferSettings(graph.order) }),
        () => runLayout(() => new NoverlapSupervisor(graph as never, { settings: NOVERLAP_SETTINGS })),
      );
    }
    return stopLayout;
    // Deliberately empty deps: once per mount, as explained above.
  }, []);

  useEffect(() => {
    if (!moveToSelectedNode) return;
    // Camera works in Sigma's normalized (framed) space, not raw graph x/y --
    // passing layout coordinates flies the camera off-graph (blank canvas).
    const position = selectedNode ? sigma.getNodeDisplayData(selectedNode) : undefined;
    if (position) sigma.getCamera().animate({ x: position.x, y: position.y, ratio: 0.45 }, { duration: 250 });
    // A camera move is a one-shot search action. Normal node clicks select the
    // node for the properties panel but keep the current view.
    selectNode(selectedNode);
  }, [graph, moveToSelectedNode, selectNode, selectedNode, sigma]);

  // Focused node: it and its neighbours are highlighted, everything else is
  // greyed and unrelated edges are hidden. Focused edge (no node focus): its
  // endpoints are highlighted and the edge itself is coloured.
  useEffect(() => {
    const activeNode = focusedNode ?? selectedNode;
    const activeEdge = edgeEvents ? (focusedEdge ?? selectedEdge) : null;
    const nodeFocusValid = Boolean(activeNode && graph.hasNode(activeNode));
    const edgeFocusValid = !nodeFocusValid && Boolean(activeEdge && graph.hasEdge(activeEdge));
    const focusing = nodeFocusValid || edgeFocusValid;

    const neighbours = new Set<string>();
    if (nodeFocusValid && activeNode) graph.forEachNeighbor(activeNode, (node) => neighbours.add(node));
    const edgeEnds = edgeFocusValid && activeEdge ? [graph.source(activeEdge), graph.target(activeEdge)] : [];

    setSettings({
      enableEdgeEvents: edgeEvents,
      renderLabels: graph.order <= LABEL_PERFORMANCE_LIMIT,
      nodeReducer: focusing
        ? (node, data) => {
              const next = { ...data, highlighted: false, labelColor: LABEL_COLOR_DARK };
              const isActive = nodeFocusValid ? node === activeNode || neighbours.has(node) : edgeEnds.includes(node);
              if (!isActive) return { ...next, color: NODE_COLOR_DISABLED };
              next.highlighted = true;
              next.labelColor = data.color;
              if (edgeFocusValid) next.size = 3;
              if (node === selectedNode) next.borderColor = NODE_BORDER_COLOR_SELECTED;
              return next;
            }
          : null,
      edgeReducer: focusing
        ? (edge, data) => {
              const next = { ...data, hidden: false, color: EDGE_COLOR_DARK };
              if (nodeFocusValid) {
                const touchesActive = graph.source(edge) === activeNode || graph.target(edge) === activeNode;
                if (!touchesActive) next.hidden = true;
              } else if (edge === selectedEdge) next.color = EDGE_COLOR_SELECTED;
              else if (edge === activeEdge) next.color = EDGE_COLOR_HIGHLIGHTED_DARK;
              else next.hidden = true;
              return next;
            }
          : null,
    });
  }, [edgeEvents, focusedEdge, focusedNode, graph, selectedEdge, selectedNode, setSettings]);

  useEffect(() => {
    registerEvents({
      enterNode: ({ node }) => focusNode(node),
      leaveNode: () => focusNode(null),
      clickNode: ({ node }) => selectNode(node),
      clickStage: () => clearSelection(),
      ...(edgeEvents
        ? {
            enterEdge: ({ edge }) => focusEdge(graph.getEdgeAttribute(edge, "rawId")),
            leaveEdge: () => focusEdge(null),
            clickEdge: ({ edge }) => selectEdge(graph.getEdgeAttribute(edge, "rawId")),
          }
        : {}),
    });
  }, [clearSelection, edgeEvents, focusEdge, focusNode, graph, registerEvents, selectEdge, selectNode]);

  const zoom = (direction: "in" | "out" | "reset") => {
    const camera = sigma.getCamera();
    if (direction === "reset") {
      sigma.setCustomBBox(null);
      camera.animatedReset();
    } else {
      camera.animate({ ratio: camera.ratio * ZOOM_STEP[direction] }, { duration: ZOOM_MS });
    }
  };

  return (
    <>
      <GraphDrag onPosition={updateNodePosition} />
      <KnowledgeGraphHeader />
      <GraphProperties />
      <div className="absolute bottom-5 left-5 z-20 flex items-end gap-3">
        <GraphControls
          onZoom={zoom}
          isFullscreen={isFullscreen}
          onFullscreen={() => toggleFullscreen(sigma.getContainer(), setIsFullscreen)}
        />
        <div className="pointer-events-none select-none pb-1 font-mono text-xs tracking-wide text-neutral-400">
          Node: {graph.order} · Relasi: {graph.size}
        </div>
      </div>
      <div className="absolute bottom-5 right-5 z-20">
        <GraphLegend />
      </div>
    </>
  );
}

function GraphDrag({ onPosition }: { onPosition: (nodeId: string, position: { x: number; y: number }) => void }) {
  const sigma = useSigma<NodeDisplayData, EdgeDisplayData>();
  const registerEvents = useRegisterEvents<NodeDisplayData, EdgeDisplayData>();
  const [draggedNode, setDraggedNode] = useState<string | null>(null);
  useEffect(() => {
    registerEvents({
      downNode: ({ node }) => {
        setDraggedNode(node);
        sigma.getGraph().setNodeAttribute(node, "highlighted", true);
      },
      mousemovebody: (event) => {
        if (!draggedNode) return;
        sigma.getGraph().mergeNodeAttributes(draggedNode, sigma.viewportToGraph(event));
        event.preventSigmaDefault();
        event.original.preventDefault();
        event.original.stopPropagation();
      },
      mouseup: () => {
        if (!draggedNode) return;
        const position = sigma.getGraph().getNodeAttributes(draggedNode);
        sigma.getGraph().removeNodeAttribute(draggedNode, "highlighted");
        onPosition(draggedNode, position);
        setDraggedNode(null);
      },
      mousedown: ({ original }) => {
        // Pin the frame so the view does not re-fit while a node is dragged.
        if ((original as MouseEvent).buttons !== 0 && !sigma.getCustomBBox()) sigma.setCustomBBox(sigma.getBBox());
      },
    });
  }, [draggedNode, onPosition, registerEvents, sigma]);
  return null;
}

function toggleFullscreen(container: HTMLElement, setFullscreen: (value: boolean) => void): void {
  if (document.fullscreenElement) {
    void document.exitFullscreen().then(() => setFullscreen(false)).catch(() => undefined);
    return;
  }
  void container.requestFullscreen().then(() => setFullscreen(true)).catch(() => undefined);
}

function StatusOverlay({ children }: { children: ReactNode }) {
  return (
    <div className="absolute inset-0 z-30 grid place-items-center bg-[#1c1b1b]/80 backdrop-blur-sm">
      <div className="max-w-sm px-6 text-center text-sm text-white">{children}</div>
    </div>
  );
}

function ErrorOverlay({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="absolute inset-0 z-40 grid place-items-center bg-[#1c1b1b]/90 p-6 text-center backdrop-blur-sm">
      <div className="max-w-sm space-y-3">
        <p className="text-sm text-white">{message}</p>
        <button
          type="button"
          onClick={onRetry}
          className="rounded bg-[#ffb5a0] px-3 py-1.5 text-sm font-semibold text-white"
        >
          Coba lagi
        </button>
      </div>
    </div>
  );
}
