import type { Metadata } from "next";
import Link from "next/link";
import { CategoryMemoryPyramid } from "@/components/database/CategoryMemoryPyramid";
import styles from "./database.module.css";

export const metadata: Metadata = {
  title: "COUNTER — Category Memory",
  description:
    "Interactive projection of COUNTER's industry category vector memory.",
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
          <span>DB / category projection</span>
          <Link href="/">← Research workspace</Link>
        </div>
      </nav>

      <header className={styles.intro}>
        <span>Remote main · industry_category</span>
        <p>
          Select one partition. Its centroid language unfolds below, one level
          at a time.
        </p>
      </header>

      <CategoryMemoryPyramid />

      <footer className={styles.sourceFooter}>
        <span>Reference</span>
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
