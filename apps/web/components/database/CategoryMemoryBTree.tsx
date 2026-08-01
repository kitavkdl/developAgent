"use client";

import {
  useEffect,
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
  pageForCategory,
  phraseKeywords,
} from "@/lib/category-memory";
import styles from "@/app/database/database.module.css";

type ScanMode = "auto" | "paused" | "manual" | "complete";
type CascadeStyle = CSSProperties & { "--node-index": number };

const DEMO_START_DELAY_MS = 700;
const DEMO_STEP_MS = 1150;
const SCAN_STEPS = ["root", "range", "leaf", "payload", "token"] as const;

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
  const [selectedPageId, setSelectedPageId] = useState<string | null>(null);
  const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(
    null,
  );
  const [selectedPhrase, setSelectedPhrase] = useState<string | null>(null);
  const [selectedKeyword, setSelectedKeyword] = useState<string | null>(null);

  const leafLevelRef = useRef<HTMLDivElement>(null);
  const phraseLevelRef = useRef<HTMLDivElement>(null);
  const keywordLevelRef = useRef<HTMLDivElement>(null);

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
  const keywords = useMemo(
    () => (selectedPhrase ? phraseKeywords(selectedPhrase) : []),
    [selectedPhrase],
  );

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

    const delay = demoStep === 0 ? DEMO_START_DELAY_MS : DEMO_STEP_MS;
    const timer = window.setTimeout(() => {
      const nextStep = demoStep + 1;

      if (nextStep === 1) setSelectedPageId(DEMO_LOOKUP.branchId);
      if (nextStep === 2) setSelectedCategoryId(DEMO_LOOKUP.categoryId);
      if (nextStep === 3) setSelectedPhrase(DEMO_LOOKUP.phrase);
      if (nextStep === 4) setSelectedKeyword(DEMO_LOOKUP.keyword);

      if (nextStep <= 4) setDemoStep(nextStep);
      else setMode("complete");
    }, delay);

    return () => window.clearTimeout(timer);
  }, [demoStep, mode]);

  useEffect(() => {
    if (selectedPageId) scrollLevelIntoView(leafLevelRef.current);
  }, [selectedPageId]);

  useEffect(() => {
    if (selectedCategoryId) scrollLevelIntoView(phraseLevelRef.current);
  }, [selectedCategoryId]);

  useEffect(() => {
    if (selectedPhrase) scrollLevelIntoView(keywordLevelRef.current);
  }, [selectedPhrase]);

  function selectPage(pageId: string) {
    setMode("manual");
    setSelectedPageId(pageId);
    setSelectedCategoryId(null);
    setSelectedPhrase(null);
    setSelectedKeyword(null);
  }

  function selectCategory(categoryId: string) {
    setMode("manual");
    setSelectedPageId(pageForCategory(categoryId)?.pageId ?? null);
    setSelectedCategoryId(categoryId);
    setSelectedPhrase(null);
    setSelectedKeyword(null);
  }

  function selectPhrase(phrase: string) {
    setMode("manual");
    setSelectedPhrase(phrase);
    setSelectedKeyword(null);
  }

  function selectKeyword(keyword: string) {
    setMode("manual");
    setSelectedKeyword(keyword);
  }

  function replayDemo() {
    setSelectedPageId(null);
    setSelectedCategoryId(null);
    setSelectedPhrase(null);
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
    <section className={styles.tree} aria-labelledby="category-index-title">
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
            selectedPageId ? styles.nodeVisited : styles.nodeCurrent
          }`}
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
          {!selectedPageId ? <ScanCursor label="ROOT PROBE" /> : null}
        </article>
      </div>

      <div className={styles.verticalPointer} aria-hidden="true">
        <span />
        <i>child ptr</i>
      </div>

      <div className={styles.treeLevel}>
        <header className={styles.levelHeader}>
          <span>LEVEL 01 · INTERNAL PAGES</span>
          <p>Key ranges route the lookup without scanning every record.</p>
        </header>
        <ol className={styles.branchFan}>
          {CATEGORY_INDEX_PAGES.map((page, index) => {
            const isSelected = selectedPageId === page.pageId;
            return (
              <li key={page.pageId} style={cascadeStyle(index)}>
                <button
                  type="button"
                  className={`${styles.dbPage} ${styles.branchPage} ${
                    isSelected
                      ? selectedCategoryId
                        ? styles.nodeVisited
                        : styles.nodeCurrent
                      : ""
                  }`}
                  aria-pressed={isSelected}
                  onClick={() => selectPage(page.pageId)}
                >
                  <span className={styles.pageChrome}>
                    <span>INTERNAL {String(index + 1).padStart(2, "0")}</span>
                    <code>{page.blockAddress}</code>
                  </span>
                  <strong>[ {page.keyRange} ]</strong>
                  <small>{page.categoryIds.length} leaf tuples</small>
                  <code>ptr → {page.pageId}</code>
                  {isSelected && !selectedCategoryId ? (
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
          <div className={styles.verticalPointer} aria-hidden="true">
            <span />
            <i>{selectedPage.blockAddress}</i>
          </div>
          <div className={styles.treeLevel} ref={leafLevelRef}>
            <header className={styles.levelHeader}>
              <span>LEVEL 02 · LINKED LEAF PAGE</span>
              <p>
                {selectedPage.pageId} · key range {selectedPage.keyRange} ·
                sibling pointers remain at leaf level
              </p>
            </header>
            <ol className={styles.leafChain}>
              {selectedPage.categoryIds.map((categoryId, index) => {
                const category = categoryById(categoryId);
                if (!category) return null;
                const isSelected = categoryId === selectedCategoryId;
                return (
                  <li key={categoryId} style={cascadeStyle(index)}>
                    <button
                      type="button"
                      className={`${styles.dbPage} ${styles.leafPage} ${
                        isSelected
                          ? selectedPhrase
                            ? styles.nodeVisited
                            : styles.nodeCurrent
                          : ""
                      }`}
                      aria-pressed={isSelected}
                      onClick={() => selectCategory(categoryId)}
                    >
                      <span className={styles.pageChrome}>
                        <span>LEAF SLOT {String(index).padStart(2, "0")}</span>
                        <code>tid ({index + 11},1)</code>
                      </span>
                      <strong>{category.label}</strong>
                      <code>{category.categoryId}</code>
                      <small>
                        created_by={category.createdBy} · centroid=vector(1536)
                      </small>
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

      {selectedCategory ? (
        <>
          <div className={styles.verticalPointer} aria-hidden="true">
            <span />
            <i>row payload</i>
          </div>
          <div className={styles.treeLevel} ref={phraseLevelRef}>
            <header className={styles.levelHeader}>
              <span>LEVEL 03 · CENTROID PAYLOAD</span>
              <p>
                Semantic probes from {selectedCategory.categoryId}; not a B+
                tree child page.
              </p>
            </header>
            {selectedCategory.centroidPhrases.length ? (
              <ol className={styles.payloadGrid}>
                {selectedCategory.centroidPhrases.map((phrase, index) => {
                  const isSelected = phrase === selectedPhrase;
                  return (
                    <li key={phrase} style={cascadeStyle(index)}>
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
                      >
                        <span>vector probe {String(index + 1).padStart(2, "0")}</span>
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
                <strong>No centroid phrase</strong>
                <p>UNCATEGORIZED is the pipeline fallback record.</p>
              </div>
            )}
          </div>
        </>
      ) : null}

      {selectedPhrase ? (
        <>
          <div className={styles.verticalPointer} aria-hidden="true">
            <span />
            <i>token scan</i>
          </div>
          <div className={styles.treeLevel} ref={keywordLevelRef}>
            <header className={styles.levelHeader}>
              <span>LEVEL 04 · SEMANTIC TOKEN LEAVES</span>
              <p>{selectedPhrase}</p>
            </header>
            <ol className={styles.tokenChain}>
              {keywords.map((keyword, index) => {
                const isSelected = keyword === selectedKeyword;
                return (
                  <li key={keyword} style={cascadeStyle(index)}>
                    <button
                      type="button"
                      className={`${styles.tokenRecord} ${
                        isSelected ? styles.nodeHit : ""
                      }`}
                      aria-pressed={isSelected}
                      onClick={() => selectKeyword(keyword)}
                    >
                      <span>{String(index).padStart(2, "0")}</span>
                      <strong>{keyword}</strong>
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
