import type { Metadata } from "next";
import Link from "next/link";
import { DatabaseSchemaExplorer } from "@/components/database/DatabaseSchemaExplorer";
import { DATABASE_RELATIONS, DATABASE_TABLES } from "@/lib/database-schema";
import styles from "./database.module.css";

export const metadata: Metadata = {
  title: "COUNTER — Database Contract",
  description:
    "Logical persistence map for COUNTER's evidence memory and research lineage.",
};

export default function DatabasePage() {
  return (
    <main className={styles.page}>
      <div className={styles.atmosphere} aria-hidden="true" />

      <nav className={styles.nav} aria-label="Database view navigation">
        <Link href="/" className={styles.wordmark}>
          COUNTER
        </Link>
        <Link href="/" className={styles.backLink}>
          <span aria-hidden="true">←</span> Research workspace
        </Link>
      </nav>

      <header className={styles.hero}>
        <div className={styles.heroCopy}>
          <span className={styles.sectionIndex}>01 / Persistence contract</span>
          <h1>Evidence has a memory.</h1>
          <p>
            Nine logical tables preserve the path from a private research job
            to public source snapshots, evaluated evidence, versioned verdicts,
            and cited answers.
          </p>
        </div>

        <dl className={styles.metrics}>
          <div>
            <dt>Tables</dt>
            <dd>{DATABASE_TABLES.length}</dd>
          </div>
          <div>
            <dt>Relations</dt>
            <dd>{DATABASE_RELATIONS.length}</dd>
          </div>
          <div>
            <dt>Storage</dt>
            <dd>Postgres + pgvector</dd>
          </div>
        </dl>
      </header>

      <DatabaseSchemaExplorer />

      <aside className={styles.contractNote} aria-labelledby="contract-note-title">
        <span className={styles.sectionIndex}>03 / Boundary</span>
        <div>
          <h2 id="contract-note-title">Logical contract, not migration DDL</h2>
          <p>
            This map reproduces the major fields and persistence boundaries in
            SERVICE_ARCHITECTURE §7. It intentionally does not invent SQL types,
            nullability, indexes, or undeclared foreign-key constraints.
          </p>
        </div>
      </aside>
    </main>
  );
}
