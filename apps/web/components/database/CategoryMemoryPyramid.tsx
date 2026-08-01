"use client";

import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import {
  CATEGORY_REUSE_THRESHOLD_REFERENCE,
  INDUSTRY_CATEGORY_SEEDS,
  phraseKeywords,
} from "@/lib/category-memory";
import styles from "@/app/database/database.module.css";

type CascadeStyle = CSSProperties & { "--node-index": number };

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

export function CategoryMemoryPyramid() {
  const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(
    null,
  );
  const [selectedPhrase, setSelectedPhrase] = useState<string | null>(null);
  const phraseLevelRef = useRef<HTMLDivElement>(null);
  const keywordLevelRef = useRef<HTMLDivElement>(null);

  const selectedCategory = useMemo(
    () =>
      INDUSTRY_CATEGORY_SEEDS.find(
        (category) => category.categoryId === selectedCategoryId,
      ) ?? null,
    [selectedCategoryId],
  );
  const keywords = useMemo(
    () => (selectedPhrase ? phraseKeywords(selectedPhrase) : []),
    [selectedPhrase],
  );

  useEffect(() => {
    if (selectedCategoryId) scrollLevelIntoView(phraseLevelRef.current);
  }, [selectedCategoryId]);

  useEffect(() => {
    if (selectedPhrase) scrollLevelIntoView(keywordLevelRef.current);
  }, [selectedPhrase]);

  function selectCategory(categoryId: string) {
    setSelectedCategoryId(categoryId);
    setSelectedPhrase(null);
  }

  return (
    <section className={styles.pyramid} aria-labelledby="category-memory-title">
      <div className={styles.rootLevel}>
        <article className={styles.memoryNode}>
          <span>Postgres + pgvector</span>
          <h1 id="category-memory-title">Industry memory</h1>
          <p>Vector partition root</p>
          <code>industry_category</code>
        </article>
      </div>

      <div className={styles.levelConnector} aria-hidden="true">
        <span />
        <i />
      </div>

      <div className={styles.categoryLevel}>
        <header className={styles.levelHeader}>
          <span>Level 01</span>
          <h2>Industry partitions</h2>
          <p>13 seed industries + one fallback</p>
        </header>
        <div className={styles.categoryFan}>
          {INDUSTRY_CATEGORY_SEEDS.map((category, index) => (
            <button
              key={category.categoryId}
              type="button"
              className={`${styles.categoryNode} ${
                selectedCategoryId === category.categoryId
                  ? styles.nodeSelected
                  : ""
              }`}
              style={cascadeStyle(index)}
              aria-pressed={selectedCategoryId === category.categoryId}
              onClick={() => selectCategory(category.categoryId)}
            >
              <span>{String(index + 1).padStart(2, "0")}</span>
              <strong>{category.label}</strong>
              <code>{category.categoryId}</code>
              <small>{category.createdBy}</small>
            </button>
          ))}
        </div>
      </div>

      {selectedCategory ? (
        <>
          <div className={styles.levelConnector} aria-hidden="true">
            <span />
            <i />
          </div>
          <div
            className={styles.phraseLevel}
            ref={phraseLevelRef}
            aria-live="polite"
          >
            <header className={styles.levelHeader}>
              <span>Level 02 · {selectedCategory.label}</span>
              <h2>Centroid phrases</h2>
              <p>Exact representative text from remote main bootstrap</p>
            </header>

            {selectedCategory.centroidPhrases.length > 0 ? (
              <div className={styles.phraseFan}>
                {selectedCategory.centroidPhrases.map((phrase, index) => (
                  <button
                    key={`${selectedCategory.categoryId}:${phrase}`}
                    type="button"
                    className={`${styles.phraseNode} ${
                      selectedPhrase === phrase ? styles.nodeSelected : ""
                    }`}
                    style={cascadeStyle(index)}
                    aria-pressed={selectedPhrase === phrase}
                    onClick={() => setSelectedPhrase(phrase)}
                  >
                    <span>0{index + 1}</span>
                    <strong>{phrase}</strong>
                    <small>centroid source</small>
                  </button>
                ))}
              </div>
            ) : (
              <div className={styles.emptyLevel}>
                <strong>No centroid phrase</strong>
                <p>
                  `UNCATEGORIZED` is the pipeline fallback when classification
                  cannot be resolved.
                </p>
              </div>
            )}
          </div>
        </>
      ) : null}

      {selectedPhrase ? (
        <>
          <div className={styles.levelConnector} aria-hidden="true">
            <span />
            <i />
          </div>
          <div className={styles.keywordLevel} ref={keywordLevelRef}>
            <header className={styles.levelHeader}>
              <span>Level 03 · Semantic leaves</span>
              <h2>Phrase keywords</h2>
              <p>{selectedPhrase}</p>
            </header>
            <div className={styles.keywordFan} role="list">
              {keywords.map((keyword, index) => (
                <div
                  key={`${selectedCategoryId}:${selectedPhrase}:${keyword}`}
                  role="listitem"
                  className={styles.keywordNode}
                  style={cascadeStyle(index)}
                >
                  <span>{keyword}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      ) : null}

      <aside className={styles.projectionNote}>
        <div>
          <span>DB contract</span>
          <strong>Flat vector partition</strong>
        </div>
        <p>
          The vertical levels are a visual projection of seed rows and centroid
          phrases, not persisted parent/child foreign keys.
        </p>
        <dl>
          <div>
            <dt>created_by</dt>
            <dd>seed | agent_generated</dd>
          </div>
          <div>
            <dt>centroid</dt>
            <dd>vector(1536)</dd>
          </div>
          <div>
            <dt>reuse reference</dt>
            <dd>
              {CATEGORY_REUSE_THRESHOLD_REFERENCE} · unverified initial value
            </dd>
          </div>
        </dl>
      </aside>
    </section>
  );
}
