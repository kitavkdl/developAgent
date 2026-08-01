"use client";

import {
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import {
  CATEGORY_INDEX_PAGES,
  CATEGORY_REUSE_THRESHOLD_REFERENCE,
  DEMO_LOOKUP,
  categoryById,
  phraseKeywords,
  type CategoryIndexPage,
  type IndustryCategorySeed,
} from "@/lib/category-memory";
import styles from "@/app/database/database.module.css";

type ScanMode = "auto" | "paused" | "manual" | "complete";
type CascadeStyle = CSSProperties & { "--node-index": number };
type EdgeState = "current" | "visited";

interface TreeEdge {
  id: string;
  path: string;
  state: EdgeState;
}

interface EdgeCanvas {
  width: number;
  height: number;
  edges: TreeEdge[];
}

interface FrontendDemoNode<T> {
  nodeId: string;
  slot: number;
  source: T;
}

const DEMO_START_DELAY_MS = 700;
const DEMO_STEP_MS = 1150;
const FRONTEND_DEMO_NODE_COUNT = 15;
const SCAN_STEPS = ["root", "range", "leaf", "payload", "token"] as const;

function createFrontendDemoNodes<T>(
  levelId: string,
  sources: readonly T[],
): FrontendDemoNode<T>[] {
  if (sources.length === 0) return [];
  return Array.from({ length: FRONTEND_DEMO_NODE_COUNT }, (_, index) => ({
    nodeId: `${levelId}-demo-${String(index + 1).padStart(2, "0")}`,
    slot: index,
    source: sources[index % sources.length],
  }));
}

function cascadeStyle(index: number): CascadeStyle {
  return { "--node-index": index };
}

function scrollLevelIntoView(node: HTMLElement | null) {
  if (!node) return;
  const reducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)",
  ).matches;
  requestAnimationFrame(() => {
    node.scrollIntoView({
      block: "nearest",
      behavior: reducedMotion ? "auto" : "smooth",
    });
  });
}

function ScanCursor({ label }: { label: string }) {
  return (
    <span className={styles.scanCursor} aria-hidden="true">
      <i />
      AI · {label}
    </span>
  );
}

export function CategoryMemoryBTree() {
  const [mode, setMode] = useState<ScanMode>("auto");
  const [demoStep, setDemoStep] = useState(0);
  const [selectedPageNodeId, setSelectedPageNodeId] = useState<string | null>(
    null,
  );
  const [selectedPageId, setSelectedPageId] = useState<string | null>(null);
  const [selectedLeafNodeId, setSelectedLeafNodeId] = useState<string | null>(
    null,
  );
  const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(
    null,
  );
  const [selectedPhraseNodeId, setSelectedPhraseNodeId] = useState<
    string | null
  >(null);
  const [selectedPhrase, setSelectedPhrase] = useState<string | null>(null);
  const [selectedKeywordNodeId, setSelectedKeywordNodeId] = useState<
    string | null
  >(null);
  const [selectedKeyword, setSelectedKeyword] = useState<string | null>(null);

  const treeRef = useRef<HTMLElement>(null);
  const leafLevelRef = useRef<HTMLDivElement>(null);
  const phraseLevelRef = useRef<HTMLDivElement>(null);
  const keywordLevelRef = useRef<HTMLDivElement>(null);
  const [edgeCanvas, setEdgeCanvas] = useState<EdgeCanvas>({
    width: 0,
    height: 0,
    edges: [],
  });

  const selectedPage = useMemo(
    () =>
      CATEGORY_INDEX_PAGES.find((page) => page.pageId === selectedPageId) ??
      null,
    [selectedPageId],
  );
  const pageNodes = useMemo(
    () => createFrontendDemoNodes("internal", CATEGORY_INDEX_PAGES),
    [],
  );
  const leafNodes = useMemo(() => {
    if (!selectedPage) return [];
    const categories = selectedPage.categoryIds
      .map((categoryId) => categoryById(categoryId))
      .filter((category): category is IndustryCategorySeed => Boolean(category));
    return createFrontendDemoNodes(
      `leaf-${selectedPage.pageId}`,
      categories,
    );
  }, [selectedPage]);
  const selectedCategory = useMemo(
    () => (selectedCategoryId ? categoryById(selectedCategoryId) : undefined),
    [selectedCategoryId],
  );
  const phraseNodes = useMemo(
    () =>
      selectedCategory
        ? createFrontendDemoNodes(
            `payload-${selectedCategory.categoryId}`,
            selectedCategory.centroidPhrases,
          )
        : [],
    [selectedCategory],
  );
  const tokenNodes = useMemo(
    () =>
      selectedPhrase
        ? createFrontendDemoNodes(
            "token",
            phraseKeywords(selectedPhrase),
          )
        : [],
    [selectedPhrase],
  );

  const visibleDepth = selectedKeywordNodeId
    ? 4
    : selectedPhraseNodeId
      ? 3
      : selectedLeafNodeId
        ? 2
        : selectedPageNodeId
          ? 1
          : 0;

  useEffect(() => {
    if (mode !== "auto") return;

    const delay = demoStep === 0 ? DEMO_START_DELAY_MS : DEMO_STEP_MS;
    const timer = window.setTimeout(() => {
      const nextStep = demoStep + 1;

      if (nextStep === 1) {
        const target = pageNodes.find(
          (node) => node.source.pageId === DEMO_LOOKUP.branchId,
        );
        if (target) {
          setSelectedPageNodeId(target.nodeId);
          setSelectedPageId(target.source.pageId);
        }
      }
      if (nextStep === 2) {
        const target = leafNodes.find(
          (node) => node.source.categoryId === DEMO_LOOKUP.categoryId,
        );
        if (target) {
          setSelectedLeafNodeId(target.nodeId);
          setSelectedCategoryId(target.source.categoryId);
        }
      }
      if (nextStep === 3) {
        const target = phraseNodes.find(
          (node) => node.source === DEMO_LOOKUP.phrase,
        );
        if (target) {
          setSelectedPhraseNodeId(target.nodeId);
          setSelectedPhrase(target.source);
        }
      }
      if (nextStep === 4) {
        const target = tokenNodes.find(
          (node) => node.source === DEMO_LOOKUP.keyword,
        );
        if (target) {
          setSelectedKeywordNodeId(target.nodeId);
          setSelectedKeyword(target.source);
        }
      }

      if (nextStep <= 4) setDemoStep(nextStep);
      else setMode("complete");
    }, delay);

    return () => window.clearTimeout(timer);
  }, [demoStep, leafNodes, mode, pageNodes, phraseNodes, tokenNodes]);

  useEffect(() => {
    if (selectedPageId) scrollLevelIntoView(leafLevelRef.current);
  }, [selectedPageId]);

  useEffect(() => {
    if (selectedCategoryId) scrollLevelIntoView(phraseLevelRef.current);
  }, [selectedCategoryId]);

  useEffect(() => {
    if (selectedPhrase) scrollLevelIntoView(keywordLevelRef.current);
  }, [selectedPhrase]);

  useLayoutEffect(() => {
    const currentTree = treeRef.current;
    if (!currentTree) return;
    const treeElement: HTMLElement = currentTree;

    function updateEdges() {
      const treeRect = treeElement.getBoundingClientRect();
      const groups: Array<{ parentId: string; state: EdgeState }> = [
        {
          parentId: "index-root",
          state: selectedPageNodeId ? "visited" : "current",
        },
      ];

      if (selectedPageNodeId) {
        groups.push({
          parentId: selectedPageNodeId,
          state: selectedLeafNodeId ? "visited" : "current",
        });
      }
      if (selectedLeafNodeId) {
        groups.push({
          parentId: selectedLeafNodeId,
          state: selectedPhraseNodeId ? "visited" : "current",
        });
      }
      if (selectedPhraseNodeId) {
        groups.push({
          parentId: selectedPhraseNodeId,
          state: selectedKeywordNodeId ? "visited" : "current",
        });
      }

      const edges = groups.flatMap(({ parentId, state }) => {
        const parent = treeElement.querySelector<HTMLElement>(
          `[data-edge-node="${parentId}"]`,
        );
        const children = Array.from(
          treeElement.querySelectorAll<HTMLElement>(
            `[data-edge-parent="${parentId}"]`,
          ),
        ).filter((child) => {
          const childRect = child.getBoundingClientRect();
          return (
            childRect.right > treeRect.left && childRect.left < treeRect.right
          );
        });
        if (!parent || children.length === 0) return [];

        const parentRect = parent.getBoundingClientRect();
        const parentX = parentRect.left - treeRect.left + parentRect.width / 2;
        const parentY = parentRect.bottom - treeRect.top;

        return children.map((child, index) => {
          const childRect = child.getBoundingClientRect();
          const childX = childRect.left - treeRect.left + childRect.width / 2;
          const childY = childRect.top - treeRect.top;
          const splitY = parentY + Math.max(22, (childY - parentY) * 0.42);
          return {
            id: `${parentId}-${index}`,
            path: `M ${parentX} ${parentY} V ${splitY} H ${childX} V ${childY}`,
            state,
          };
        });
      });

      setEdgeCanvas({
        width: Math.round(treeElement.clientWidth),
        height: Math.round(treeElement.scrollHeight),
        edges,
      });
    }

    updateEdges();
    const resizeObserver = new ResizeObserver(updateEdges);
    resizeObserver.observe(treeElement);
    window.addEventListener("resize", updateEdges);
    const scrollContainers = Array.from(
      treeElement.querySelectorAll<HTMLElement>("[data-edge-scroll]"),
    );
    scrollContainers.forEach((container) =>
      container.addEventListener("scroll", updateEdges, { passive: true }),
    );
    const animationFrame = requestAnimationFrame(updateEdges);
    const settledAnimation = window.setTimeout(updateEdges, 800);

    return () => {
      resizeObserver.disconnect();
      window.removeEventListener("resize", updateEdges);
      scrollContainers.forEach((container) =>
        container.removeEventListener("scroll", updateEdges),
      );
      cancelAnimationFrame(animationFrame);
      window.clearTimeout(settledAnimation);
    };
  }, [
    selectedKeywordNodeId,
    selectedLeafNodeId,
    selectedPageNodeId,
    selectedPhraseNodeId,
  ]);

  function selectPage(node: FrontendDemoNode<CategoryIndexPage>) {
    setMode("manual");
    setSelectedPageNodeId(node.nodeId);
    setSelectedPageId(node.source.pageId);
    setSelectedLeafNodeId(null);
    setSelectedCategoryId(null);
    setSelectedPhraseNodeId(null);
    setSelectedPhrase(null);
    setSelectedKeywordNodeId(null);
    setSelectedKeyword(null);
  }

  function selectCategory(node: FrontendDemoNode<IndustryCategorySeed>) {
    setMode("manual");
    setSelectedLeafNodeId(node.nodeId);
    setSelectedCategoryId(node.source.categoryId);
    setSelectedPhraseNodeId(null);
    setSelectedPhrase(null);
    setSelectedKeywordNodeId(null);
    setSelectedKeyword(null);
  }

  function selectPhrase(node: FrontendDemoNode<string>) {
    setMode("manual");
    setSelectedPhraseNodeId(node.nodeId);
    setSelectedPhrase(node.source);
    setSelectedKeywordNodeId(null);
    setSelectedKeyword(null);
  }

  function selectKeyword(node: FrontendDemoNode<string>) {
    setMode("manual");
    setSelectedKeywordNodeId(node.nodeId);
    setSelectedKeyword(node.source);
  }

  function replayDemo() {
    setSelectedPageNodeId(null);
    setSelectedPageId(null);
    setSelectedLeafNodeId(null);
    setSelectedCategoryId(null);
    setSelectedPhraseNodeId(null);
    setSelectedPhrase(null);
    setSelectedKeywordNodeId(null);
    setSelectedKeyword(null);
    setDemoStep(0);
    setMode("auto");
    const reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    window.scrollTo({
      top: 0,
      behavior: reducedMotion ? "auto" : "smooth",
    });
  }

  const statusText =
    mode === "paused"
      ? "Scan paused"
      : mode === "manual"
        ? "Manual inspection · autoplay stopped"
        : mode === "complete"
          ? "Leaf payload match · 앰플"
          : [
              "Reading root separator keys",
              "Following child pointer 0x0118",
              "Comparing BEAUTY_PERSONAL_CARE",
              "Probing centroid source text",
              "Semantic token hit · 앰플",
            ][demoStep];

  return (
    <section
      className={styles.tree}
      ref={treeRef}
      aria-labelledby="category-index-title"
    >
      {edgeCanvas.width > 0 ? (
        <svg
          className={styles.edgeLayer}
          width={edgeCanvas.width}
          height={edgeCanvas.height}
          viewBox={`0 0 ${edgeCanvas.width} ${edgeCanvas.height}`}
          aria-hidden="true"
        >
          <defs>
            <marker
              id="tree-edge-arrow"
              markerWidth="7"
              markerHeight="7"
              refX="5.5"
              refY="3.5"
              orient="auto"
            >
              <path d="M 0 0 L 7 3.5 L 0 7 z" fill="#7fbe98" />
            </marker>
          </defs>
          {edgeCanvas.edges.map((edge) => (
            <path
              key={edge.id}
              d={edge.path}
              data-edge-id={edge.id}
              data-state={edge.state}
              markerEnd="url(#tree-edge-arrow)"
            />
          ))}
        </svg>
      ) : null}
      <div className={styles.scanConsole}>
        <div className={styles.scanIdentity}>
          <span className={styles.scanLamp} data-mode={mode} />
          <div>
            <span>Deterministic demo</span>
            <strong>AI index scan</strong>
          </div>
        </div>
        <div className={styles.scanQuery}>
          <span>LOOKUP</span>
          <code>category_id = &apos;BEAUTY_PERSONAL_CARE&apos;</code>
        </div>
        <div className={styles.scanControls}>
          {mode === "auto" || mode === "paused" ? (
            <button
              type="button"
              onClick={() => setMode(mode === "auto" ? "paused" : "auto")}
            >
              {mode === "auto" ? "Pause" : "Resume"}
            </button>
          ) : null}
          <button type="button" onClick={replayDemo}>
            Replay
          </button>
        </div>
        <p className={styles.scanStatus} aria-live="polite">
          <span>{String(visibleDepth + 1).padStart(2, "0")}/05</span>
          {statusText}
        </p>
        <ol className={styles.scanProgress} aria-label="Index scan progress">
          {SCAN_STEPS.map((step, index) => (
            <li
              key={step}
              data-state={
                index < visibleDepth
                  ? "visited"
                  : index === visibleDepth
                    ? "current"
                    : "waiting"
              }
            >
              <span>{String(index + 1).padStart(2, "0")}</span>
              {step}
            </li>
          ))}
        </ol>
      </div>

      <div className={styles.treeLevel}>
        <header className={styles.levelHeader}>
          <span>LEVEL 00 · INDEX ROOT</span>
          <p>Compare separator keys, then follow one child pointer.</p>
        </header>
        <article
          className={`${styles.dbPage} ${styles.rootPage} ${
            selectedPageNodeId ? styles.nodeVisited : styles.nodeCurrent
          }`}
          data-edge-node="index-root"
        >
          <div className={styles.pageChrome}>
            <span>ROOT PAGE</span>
            <code>blk 0x0100 · slots 02</code>
          </div>
          <h1 id="category-index-title">industry_category_pkey</h1>
          <div className={styles.rootSlots}>
            <span>ptr 00</span>
            <strong>&lt; FASHION_APPAREL</strong>
            <span>ptr 01</span>
            <strong>&lt; PET</strong>
            <span>ptr 02</span>
          </div>
          {!selectedPageNodeId ? <ScanCursor label="ROOT PROBE" /> : null}
        </article>
      </div>

      <div className={styles.edgeGap} aria-hidden="true" />

      <div className={styles.treeLevel}>
        <header className={styles.levelHeader}>
          <span>LEVEL 01 · INTERNAL PAGES</span>
          <p>Key ranges route the lookup without scanning every record.</p>
        </header>
        <ol className={styles.branchFan} data-edge-scroll>
          {pageNodes.map((node, index) => {
            const page = node.source;
            const isSelected = selectedPageNodeId === node.nodeId;
            return (
              <li key={node.nodeId} style={cascadeStyle(index)}>
                <button
                  type="button"
                  className={`${styles.dbPage} ${styles.branchPage} ${
                    isSelected
                      ? selectedLeafNodeId
                        ? styles.nodeVisited
                        : styles.nodeCurrent
                      : ""
                  }`}
                  aria-pressed={isSelected}
                  onClick={() => selectPage(node)}
                  data-edge-parent="index-root"
                  data-edge-node={node.nodeId}
                >
                  <span className={styles.pageChrome}>
                    <span>DEMO PAGE {String(index + 1).padStart(2, "0")}</span>
                    <code>{page.blockAddress}</code>
                  </span>
                  <strong>[ {page.keyRange} ]</strong>
                  <small>frontend-only · {page.categoryIds.length} seed refs</small>
                  <code>ptr → {node.nodeId}</code>
                  {isSelected && !selectedLeafNodeId ? (
                    <ScanCursor label="RANGE HIT" />
                  ) : null}
                </button>
              </li>
            );
          })}
        </ol>
      </div>

      {selectedPage ? (
        <>
          <div className={styles.edgeGap} aria-hidden="true" />
          <div className={styles.treeLevel} ref={leafLevelRef}>
            <header className={styles.levelHeader}>
              <span>LEVEL 02 · LINKED LEAF PAGE</span>
              <p>
                {selectedPage.pageId} · key range {selectedPage.keyRange} ·
                15 frontend-only nodes · horizontally scrollable
              </p>
            </header>
            <ol className={styles.leafChain} data-edge-scroll>
              {leafNodes.map((node, index) => {
                const category = node.source;
                const isSelected = selectedLeafNodeId === node.nodeId;
                return (
                  <li key={node.nodeId} style={cascadeStyle(index)}>
                    <button
                      type="button"
                      className={`${styles.dbPage} ${styles.leafPage} ${
                        isSelected
                          ? selectedPhraseNodeId
                            ? styles.nodeVisited
                            : styles.nodeCurrent
                          : ""
                      }`}
                      aria-pressed={isSelected}
                      onClick={() => selectCategory(node)}
                      data-edge-parent={selectedPageNodeId ?? ""}
                      data-edge-node={node.nodeId}
                    >
                      <span className={styles.pageChrome}>
                        <span>DEMO LEAF {String(index + 1).padStart(2, "0")}</span>
                        <code>tid ({index + 11},1)</code>
                      </span>
                      <strong>{category.label}</strong>
                      <code>{category.categoryId}</code>
                      <small>
                        frontend-only · seed_ref={category.categoryId}
                      </small>
                      {isSelected && !selectedPhraseNodeId ? (
                        <ScanCursor label="LEAF HIT" />
                      ) : null}
                    </button>
                  </li>
                );
              })}
            </ol>
          </div>
        </>
      ) : null}

      {selectedCategory ? (
        <>
          <div className={styles.edgeGap} aria-hidden="true" />
          <div className={styles.treeLevel} ref={phraseLevelRef}>
            <header className={styles.levelHeader}>
              <span>LEVEL 03 · CENTROID PAYLOAD</span>
              <p>
                Semantic probes from {selectedCategory.categoryId}; not a B+
                tree child page.
              </p>
            </header>
            {selectedCategory.centroidPhrases.length ? (
              <ol className={styles.payloadGrid} data-edge-scroll>
                {phraseNodes.map((node, index) => {
                  const phrase = node.source;
                  const isSelected = selectedPhraseNodeId === node.nodeId;
                  return (
                    <li key={node.nodeId} style={cascadeStyle(index)}>
                      <button
                        type="button"
                        className={`${styles.payloadRecord} ${
                          isSelected
                            ? selectedKeywordNodeId
                              ? styles.nodeVisited
                              : styles.nodeCurrent
                            : ""
                        }`}
                        aria-pressed={isSelected}
                        onClick={() => selectPhrase(node)}
                        data-edge-parent={selectedLeafNodeId ?? ""}
                        data-edge-node={node.nodeId}
                      >
                        <span>
                          demo payload {String(index + 1).padStart(2, "0")}
                        </span>
                        <strong>{phrase}</strong>
                        <code>frontend-only · cosine candidate</code>
                        {isSelected && !selectedKeywordNodeId ? (
                          <ScanCursor label="PAYLOAD PROBE" />
                        ) : null}
                      </button>
                    </li>
                  );
                })}
              </ol>
            ) : (
              <div className={styles.emptyPage}>
                <strong>No centroid phrase</strong>
                <p>UNCATEGORIZED is the pipeline fallback record.</p>
              </div>
            )}
          </div>
        </>
      ) : null}

      {selectedPhrase ? (
        <>
          <div className={styles.edgeGap} aria-hidden="true" />
          <div className={styles.treeLevel} ref={keywordLevelRef}>
            <header className={styles.levelHeader}>
              <span>LEVEL 04 · SEMANTIC TOKEN LEAVES</span>
              <p>{selectedPhrase}</p>
            </header>
            <ol className={styles.tokenChain} data-edge-scroll>
              {tokenNodes.map((node, index) => {
                const keyword = node.source;
                const isSelected = selectedKeywordNodeId === node.nodeId;
                return (
                  <li key={node.nodeId} style={cascadeStyle(index)}>
                    <button
                      type="button"
                      className={`${styles.tokenRecord} ${
                        isSelected ? styles.nodeHit : ""
                      }`}
                      aria-pressed={isSelected}
                      onClick={() => selectKeyword(node)}
                      data-edge-parent={selectedPhraseNodeId ?? ""}
                      data-edge-node={node.nodeId}
                    >
                      <span>{String(index + 1).padStart(2, "0")}</span>
                      <strong>{keyword}</strong>
                      <code>frontend-only</code>
                    </button>
                  </li>
                );
              })}
            </ol>
            {selectedKeyword ? (
              <div className={styles.matchReceipt} role="status">
                <span>MATCH FOUND</span>
                <strong>{selectedKeyword}</strong>
                <code>leaf payload resolved · demo complete</code>
              </div>
            ) : null}
          </div>
        </>
      ) : null}

      <aside className={styles.projectionNote}>
        <div>
          <span>INDEX CONTRACT</span>
          <strong>PK lookup projection</strong>
        </div>
        <p>
          B+ tree styling describes the category_id lookup path. The persisted
          category table is flat; centroid similarity uses a separate IVFFlat
          vector index.
        </p>
        <dl>
          <div>
            <dt>rows</dt>
            <dd>13 seed + UNCATEGORIZED</dd>
          </div>
          <div>
            <dt>demo fanout</dt>
            <dd>15 frontend-only nodes per level</dd>
          </div>
          <div>
            <dt>centroid</dt>
            <dd>vector(1536)</dd>
          </div>
          <div>
            <dt>reuse ref.</dt>
            <dd>
              {CATEGORY_REUSE_THRESHOLD_REFERENCE} · unverified initial value
            </dd>
          </div>
        </dl>
      </aside>
    </section>
  );
}
