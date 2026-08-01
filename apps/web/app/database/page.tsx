import type { Metadata } from "next";
import Link from "next/link";
import { CategoryMemoryBTree } from "@/components/database/CategoryMemoryBTree";
import styles from "./database.module.css";

export const metadata: Metadata = {
  title: "COUNTER — AI Index Scan",
  description:
    "Automatic B+ tree inspired traversal of COUNTER's category memory.",
};

export default function DatabasePage() {
  return (
    <main className={styles.page}>
      <div className={styles.atmosphere} aria-hidden="true" />

      <nav className={styles.nav} aria-label="Category memory navigation">
        <Link href="/" className={styles.wordmark}>
          COUNTER
        </Link>
        <div className={styles.navMeta}>
          <span>DB / B+ TREE DEMO</span>
          <Link href="/">← Research workspace</Link>
        </div>
      </nav>

      <header className={styles.intro}>
        <div>
          <span>REMOTE MAIN · INDUSTRY_CATEGORY</span>
          <strong>Watch the index resolve a category leaf.</strong>
        </div>
        <p>
          The deterministic demo follows Beauty → 뷰티 → 앰플, selecting one
          node per level as child leaves appear.
        </p>
      </header>

      <CategoryMemoryBTree />

      <footer className={styles.sourceFooter}>
        <span>REFERENCE</span>
        <a
          href="https://github.com/kitavkdl/developAgent/blob/main/db/migrations/001_init.sql"
          target="_blank"
          rel="noreferrer"
        >
          001_init.sql
        </a>
        <a
          href="https://github.com/kitavkdl/developAgent/blob/main/db/migrations/002_seed_static.sql"
          target="_blank"
          rel="noreferrer"
        >
          002_seed_static.sql
        </a>
        <a
          href="https://github.com/kitavkdl/developAgent/blob/main/counter/bootstrap.py"
          target="_blank"
          rel="noreferrer"
        >
          bootstrap.py
        </a>
      </footer>
    </main>
  );
}
