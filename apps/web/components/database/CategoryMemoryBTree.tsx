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
  DEMO_CREATED_CATEGORY_ID,
  DEMO_LOOKUP,
  categoryById,
  pageForCategory,
  phraseKeywords,
} from "@/lib/category-memory";
import styles from "@/app/database/database.module.css";

type ScanMode = "auto" | "paused" | "manual" | "complete";
type DemoPhase =
  | "probe"
  | "create-leaf"
  | "spawn-phrase"
  | "spawn-token"
  | "done";
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

/** Pointer hop / spawn beat length (phase2). */
const LEVEL_HOLD_MS = 5000;
const SCAN_STEPS = ["root", "range", "leaf", "payload", "token"] as const;

function cascadeStyle(index: number): CascadeStyle {
  return { "--node-index": index };
}

/** Extra downward shift as a fraction of the viewport (all stages except level 4). */
const LEVEL_SCROLL_EXTRA_RATIO = 0.1;
/** One-shot nudge when the database demo first mounts. */
const INITIAL_SCROLL_RATIO = 0.15;

function scrollLevelIntoView(
  node: HTMLElement | null,
  options?: {
    block?: ScrollLogicalPosition;
    /** Extra downward shift as a fraction of the viewport height. */
    extraDownRatio?: number;
  },
) {
  if (!node) return;
  const { block = "nearest", extraDownRatio = 0 } = options ?? {};
  const reducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)",
  ).matches;

  requestAnimationFrame(() => {
    const rect = node.getBoundingClientRect();
    const viewH = window.innerHeight;
    let delta = 0;

    if (block === "center") {
      delta = rect.top + rect.height / 2 - viewH / 2;
    } else if (block === "start") {
      delta = rect.top;
    } else if (block === "end") {
      delta = rect.bottom - viewH;
    } else if (rect.top < 0) {
      delta = rect.top;
    } else if (rect.bottom > viewH) {
      delta = rect.bottom - viewH;
    }

    delta += viewH * extraDownRatio;
    if (Math.abs(delta) < 1) return;

    window.scrollBy({
      top: delta,
      behavior: reducedMotion ? "auto" : "smooth",
    });
  });
}

function scrollDownByViewportRatio(ratio: number) {
  const reducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)",
  ).matches;
  const dy = window.innerHeight * ratio;
  if (Math.abs(dy) < 1) return;
  window.scrollBy({
    top: dy,
    behavior: reducedMotion ? "auto" : "smooth",
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

function phaseStatus(
  phase: DemoPhase,
  leafProbeIndex: number | null,
  initialLeafCount: number,
): string {
  switch (phase) {
    case "probe":
      return `Leaf probe · slot ${String((leafProbeIndex ?? 0) + 1).padStart(2, "0")}/${String(initialLeafCount).padStart(2, "0")}`;
    case "create-leaf":
      return "Create leaf · 뷰티";
    case "spawn-phrase":
      return "Spawn payload · 앰플";
    case "spawn-token":
      return "Spawn token · 앰플";
    case "done":
      return "Leaf payload match · 앰플";
  }
}

export function CategoryMemoryBTree() {
  const [mode, setMode] = useState<ScanMode>("auto");
  const [demoPhase, setDemoPhase] = useState<DemoPhase>("probe");
  const [leafProbeIndex, setLeafProbeIndex] = useState<number | null>(0);
  const [createdCategoryIds, setCreatedCategoryIds] = useState<string[]>([]);
  const [spawnedPhrases, setSpawnedPhrases] = useState<string[]>([]);
  const [spawnedKeywords, setSpawnedKeywords] = useState<string[]>([]);

  const [selectedPageId, setSelectedPageId] = useState<string | null>(
    DEMO_LOOKUP.branchId,
  );
  const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(
    null,
  );
  const [selectedPhrase, setSelectedPhrase] = useState<string | null>(null);
  const [selectedKeyword, setSelectedKeyword] = useState<string | null>(null);

  const treeRef = useRef<HTMLElement>(null);
  const leafLevelRef = useRef<HTMLDivElement>(null);
  const phraseLevelRef = useRef<HTMLDivElement>(null);
  const keywordLevelRef = useRef<HTMLDivElement>(null);
  const leafLevelOpenedRef = useRef(false);
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
  const selectedCategory = useMemo(
    () => (selectedCategoryId ? categoryById(selectedCategoryId) : undefined),
    [selectedCategoryId],
  );

  const visibleLeafIds = useMemo(() => {
    if (!selectedPage) return [];
    const extras =
      selectedPage.pageId === DEMO_LOOKUP.branchId ? createdCategoryIds : [];
    return [
      ...selectedPage.categoryIds,
      ...extras.filter((id) => !selectedPage.categoryIds.includes(id)),
    ];
  }, [selectedPage, createdCategoryIds]);

  const initialLeafCount = selectedPage?.categoryIds.length ?? 0;

  const phrasesToShow = useMemo(() => {
    if (mode === "manual") return selectedCategory?.centroidPhrases ?? [];
    return spawnedPhrases;
  }, [mode, selectedCategory, spawnedPhrases]);

  const keywordsToShow = useMemo(() => {
    if (mode === "manual") {
      return selectedPhrase ? phraseKeywords(selectedPhrase) : [];
    }
    return spawnedKeywords;
  }, [mode, selectedPhrase, spawnedKeywords]);

  const selectedPhraseNodeId =
    selectedPhrase && phrasesToShow.includes(selectedPhrase)
      ? `phrase-${phrasesToShow.indexOf(selectedPhrase)}`
      : null;

  const showLeafLevel = selectedPage !== null;
  const showPhraseLevel =
    mode === "manual"
      ? selectedCategory !== undefined
      : demoPhase === "spawn-phrase" ||
        demoPhase === "spawn-token" ||
        demoPhase === "done" ||
        spawnedPhrases.length > 0;
  const showTokenLevel =
    mode === "manual"
      ? selectedPhrase !== null
      : demoPhase === "spawn-token" ||
        demoPhase === "done" ||
        spawnedKeywords.length > 0;

  const visibleDepth = selectedKeyword
    ? 4
    : selectedPhrase
      ? 3
      : selectedCategoryId
        ? 2
        : selectedPageId
          ? 1
          : 0;

  useEffect(() => {
    if (mode !== "auto") return;
    if (demoPhase === "done") {
      setMode("complete");
      return;
    }

    const timer = window.setTimeout(() => {
      if (demoPhase === "probe") {
        const nextIndex = (leafProbeIndex ?? 0) + 1;
        if (nextIndex < initialLeafCount) {
          setLeafProbeIndex(nextIndex);
          return;
        }
        setLeafProbeIndex(null);
        setCreatedCategoryIds([DEMO_CREATED_CATEGORY_ID]);
        setSelectedCategoryId(DEMO_CREATED_CATEGORY_ID);
        setDemoPhase("create-leaf");
        return;
      }

      if (demoPhase === "create-leaf") {
        setSpawnedPhrases([DEMO_LOOKUP.phrase]);
        setSelectedPhrase(DEMO_LOOKUP.phrase);
        setDemoPhase("spawn-phrase");
        return;
      }

      if (demoPhase === "spawn-phrase") {
        setSpawnedKeywords([DEMO_LOOKUP.keyword]);
        setSelectedKeyword(DEMO_LOOKUP.keyword);
        setDemoPhase("spawn-token");
        return;
      }

      if (demoPhase === "spawn-token") {
        setDemoPhase("done");
        setMode("complete");
      }
    }, LEVEL_HOLD_MS);

    return () => window.clearTimeout(timer);
  }, [demoPhase, initialLeafCount, leafProbeIndex, mode]);

  useEffect(() => {
    if (!showLeafLevel) {
      leafLevelOpenedRef.current = false;
      return;
    }
    if (leafLevelOpenedRef.current) return;
    leafLevelOpenedRef.current = true;
    scrollLevelIntoView(leafLevelRef.current, {
      extraDownRatio: LEVEL_SCROLL_EXTRA_RATIO,
    });
  }, [showLeafLevel]);

  useEffect(() => {
    if (showPhraseLevel) {
      scrollLevelIntoView(phraseLevelRef.current, {
        extraDownRatio: LEVEL_SCROLL_EXTRA_RATIO,
      });
    }
  }, [showPhraseLevel]);

  useEffect(() => {
    if (showTokenLevel) {
      scrollLevelIntoView(keywordLevelRef.current, { block: "center" });
    }
  }, [showTokenLevel]);

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      scrollDownByViewportRatio(INITIAL_SCROLL_RATIO);
    });
    return () => cancelAnimationFrame(frame);
  }, []);

  useLayoutEffect(() => {
    const currentTree = treeRef.current;
    if (!currentTree) return;
    const treeElement: HTMLElement = currentTree;

    function updateEdges() {
      const treeRect = treeElement.getBoundingClientRect();
      const groups: Array<{ parentId: string; state: EdgeState }> = [
        {
          parentId: "index-root",
          state: selectedPageId ? "visited" : "current",
        },
      ];

      if (showLeafLevel && selectedPageId) {
        groups.push({
          parentId: selectedPageId,
          state:
            selectedCategoryId || leafProbeIndex !== null
              ? selectedCategoryId
                ? "visited"
                : "current"
              : "current",
        });
      }
      if (showPhraseLevel && selectedCategoryId) {
        groups.push({
          parentId: selectedCategoryId,
          state: selectedPhrase ? "visited" : "current",
        });
      }
      if (showTokenLevel && selectedPhraseNodeId) {
        groups.push({
          parentId: selectedPhraseNodeId,
          state: selectedKeyword ? "visited" : "current",
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
        );
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
    const animationFrame = requestAnimationFrame(updateEdges);
    const settledAnimation = window.setTimeout(updateEdges, 800);

    return () => {
      resizeObserver.disconnect();
      window.removeEventListener("resize", updateEdges);
      cancelAnimationFrame(animationFrame);
      window.clearTimeout(settledAnimation);
    };
  }, [
    createdCategoryIds,
    leafProbeIndex,
    selectedCategoryId,
    selectedKeyword,
    selectedPageId,
    selectedPhrase,
    selectedPhraseNodeId,
    showLeafLevel,
    showPhraseLevel,
    showTokenLevel,
    spawnedKeywords,
    spawnedPhrases,
  ]);

  function selectPage(pageId: string) {
    setMode("manual");
    setSelectedPageId(pageId);
    setSelectedCategoryId(null);
    setSelectedPhrase(null);
    setSelectedKeyword(null);
    setLeafProbeIndex(null);
    setCreatedCategoryIds([]);
    setSpawnedPhrases([]);
    setSpawnedKeywords([]);
  }

  function selectCategory(categoryId: string) {
    setMode("manual");
    setSelectedPageId(pageForCategory(categoryId)?.pageId ?? selectedPageId);
    setSelectedCategoryId(categoryId);
    setSelectedPhrase(null);
    setSelectedKeyword(null);
    setLeafProbeIndex(null);
    setSpawnedPhrases([]);
    setSpawnedKeywords([]);
  }

  function selectPhrase(phrase: string) {
    setMode("manual");
    setSelectedPhrase(phrase);
    setSelectedKeyword(null);
    setSpawnedKeywords([]);
  }

  function selectKeyword(keyword: string) {
    setMode("manual");
    setSelectedKeyword(keyword);
  }

  function replayDemo() {
    setSelectedPageId(DEMO_LOOKUP.branchId);
    setSelectedCategoryId(null);
    setSelectedPhrase(null);
    setSelectedKeyword(null);
    setCreatedCategoryIds([]);
    setSpawnedPhrases([]);
    setSpawnedKeywords([]);
    setLeafProbeIndex(0);
    setDemoPhase("probe");
    leafLevelOpenedRef.current = false;
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
          : phaseStatus(demoPhase, leafProbeIndex, initialLeafCount);

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
            <span>Phase2 · create-on-miss</span>
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
            selectedPageId ? styles.nodeVisited : styles.nodeCurrent
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
            <strong>&lt; Edu</strong>
            <span>ptr 01</span>
            <strong>&lt; Fashion</strong>
            <span>ptr 02</span>
            <strong>&lt; Life</strong>
            <span>ptr 03</span>
          </div>
          {!selectedPageId ? <ScanCursor label="ROOT PROBE" /> : null}
        </article>
      </div>

      <div className={styles.edgeGap} aria-hidden="true" />

      <div className={styles.treeLevel}>
        <header className={styles.levelHeader}>
          <span>LEVEL 01 · INTERNAL PAGES</span>
          <p>Key ranges route the lookup without scanning every record.</p>
        </header>
        <ol className={styles.branchFan}>
          {CATEGORY_INDEX_PAGES.map((page, index) => {
            const isSelected = selectedPageId === page.pageId;
            const leafCount =
              page.pageId === DEMO_LOOKUP.branchId
                ? page.categoryIds.length + createdCategoryIds.length
                : page.categoryIds.length;
            return (
              <li key={page.pageId} style={cascadeStyle(index)}>
                <button
                  type="button"
                  className={`${styles.dbPage} ${styles.branchPage} ${
                    isSelected
                      ? selectedCategoryId || leafProbeIndex !== null
                        ? styles.nodeVisited
                        : styles.nodeCurrent
                      : ""
                  }`}
                  aria-pressed={isSelected}
                  onClick={() => selectPage(page.pageId)}
                  data-edge-parent="index-root"
                  data-edge-node={page.pageId}
                >
                  <span className={styles.pageChrome}>
                    <span>INTERNAL {String(index + 1).padStart(2, "0")}</span>
                    <code>{page.blockAddress}</code>
                  </span>
                  <strong>{page.label}</strong>
                  <small>{leafCount} leaf tuples</small>
                  <code>ptr → {page.pageId}</code>
                  {isSelected &&
                  leafProbeIndex === null &&
                  !selectedCategoryId ? (
                    <ScanCursor label="RANGE HIT" />
                  ) : null}
                </button>
              </li>
            );
          })}
        </ol>
      </div>

      {showLeafLevel && selectedPage ? (
        <>
          <div className={styles.edgeGap} aria-hidden="true" />
          <div className={styles.treeLevel} ref={leafLevelRef}>
            <header className={styles.levelHeader}>
              <span>LEVEL 02 · LINKED LEAF PAGE</span>
              <p>
                {selectedPage.pageId} · key range {selectedPage.keyRange} ·
                {createdCategoryIds.length
                  ? " runtime insert after miss"
                  : " probe existing slots"}
              </p>
            </header>
            <ol className={styles.leafChain}>
              {visibleLeafIds.map((categoryId, index) => {
                const category = categoryById(categoryId);
                if (!category) return null;
                const isCreated = createdCategoryIds.includes(categoryId);
                const isProbed =
                  mode !== "manual" &&
                  demoPhase === "probe" &&
                  leafProbeIndex === index;
                const isSelected = categoryId === selectedCategoryId;
                const isCurrent = isSelected || isProbed;
                return (
                  <li
                    key={`${categoryId}-${isCreated ? "created" : "seed"}`}
                    style={cascadeStyle(index)}
                  >
                    <button
                      type="button"
                      className={`${styles.dbPage} ${styles.leafPage} ${
                        isCurrent
                          ? selectedPhrase
                            ? styles.nodeVisited
                            : styles.nodeCurrent
                          : ""
                      }`}
                      aria-pressed={isSelected || isProbed}
                      onClick={() => selectCategory(categoryId)}
                      data-edge-parent={selectedPage.pageId}
                      data-edge-node={categoryId}
                    >
                      <span className={styles.pageChrome}>
                        <span>
                          {isCreated ? "NEW LEAF" : "LEAF SLOT"}{" "}
                          {String(index).padStart(2, "0")}
                        </span>
                        <code>tid ({index + 11},1)</code>
                      </span>
                      <strong>{category.label}</strong>
                      <code>{category.categoryId}</code>
                      <small>
                        created_by={isCreated ? "runtime" : category.createdBy}{" "}
                        · centroid=vector(1536)
                      </small>
                      {isProbed ? <ScanCursor label="LEAF PROBE" /> : null}
                      {isSelected && !selectedPhrase ? (
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

      {showPhraseLevel && selectedCategory ? (
        <>
          <div className={styles.edgeGap} aria-hidden="true" />
          <div className={styles.treeLevel} ref={phraseLevelRef}>
            <header className={styles.levelHeader}>
              <span>LEVEL 03 · CENTROID PAYLOAD</span>
              <p>
                Semantic probes from {selectedCategory.categoryId}; spawn one
                payload node on miss.
              </p>
            </header>
            {phrasesToShow.length ? (
              <ol className={styles.payloadGrid}>
                {phrasesToShow.map((phrase, index) => {
                  const isSelected = phrase === selectedPhrase;
                  return (
                    <li
                      key={`spawn-phrase-${phrase}`}
                      style={cascadeStyle(index)}
                    >
                      <button
                        type="button"
                        className={`${styles.payloadRecord} ${
                          isSelected
                            ? selectedKeyword
                              ? styles.nodeVisited
                              : styles.nodeCurrent
                            : ""
                        }`}
                        aria-pressed={isSelected}
                        onClick={() => selectPhrase(phrase)}
                        data-edge-parent={selectedCategory.categoryId}
                        data-edge-node={`phrase-${index}`}
                      >
                        <span>
                          vector probe {String(index + 1).padStart(2, "0")}
                        </span>
                        <strong>{phrase}</strong>
                        <code>cosine candidate</code>
                        {isSelected && !selectedKeyword ? (
                          <ScanCursor label="PAYLOAD PROBE" />
                        ) : null}
                      </button>
                    </li>
                  );
                })}
              </ol>
            ) : (
              <div className={styles.emptyPage}>
                <strong>No centroid phrase yet</strong>
                <p>Waiting for runtime spawn…</p>
              </div>
            )}
          </div>
        </>
      ) : null}

      {showTokenLevel && selectedPhrase ? (
        <>
          <div className={styles.edgeGap} aria-hidden="true" />
          <div className={styles.treeLevel} ref={keywordLevelRef}>
            <header className={styles.levelHeader}>
              <span>LEVEL 04 · SEMANTIC TOKEN LEAVES</span>
              <p>{selectedPhrase}</p>
            </header>
            {keywordsToShow.length ? (
              <ol className={styles.tokenChain}>
                {keywordsToShow.map((keyword, index) => {
                  const isSelected = keyword === selectedKeyword;
                  return (
                    <li
                      key={`spawn-token-${keyword}`}
                      style={cascadeStyle(index)}
                    >
                      <button
                        type="button"
                        className={`${styles.tokenRecord} ${
                          isSelected ? styles.nodeHit : ""
                        }`}
                        aria-pressed={isSelected}
                        onClick={() => selectKeyword(keyword)}
                        data-edge-parent={selectedPhraseNodeId ?? ""}
                        data-edge-node={`token-${index}`}
                      >
                        <span>{String(index).padStart(2, "0")}</span>
                        <strong>{keyword}</strong>
                      </button>
                    </li>
                  );
                })}
              </ol>
            ) : (
              <div className={styles.emptyPage}>
                <strong>No token leaf yet</strong>
                <p>Waiting for runtime spawn…</p>
              </div>
            )}
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
          Phase2 demo: miss on leaf page inserts 뷰티, then spawns one payload
          and one token node down the path.
        </p>
        <dl>
          <div>
            <dt>rows</dt>
            <dd>probe → create · 1 node / deeper level</dd>
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
