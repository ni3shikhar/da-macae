/**
 * FormattedContent — renders agent output as user-friendly formatted content.
 *
 * Handles:
 *   • Markdown (headings, bold, lists, code, links) via react-markdown
 *   • Embedded JSON objects → key-value tables / nested cards
 *   • Raw JSON strings → pretty-printed key-value tables
 *   • Collapsible sections for large JSON blocks
 *   • Checklist items (✓ / ✗ markers)
 *   • Plain text fallback with pre-wrap
 */

import React, { useMemo, useState, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  makeStyles,
  tokens,
  Caption1,
} from "@fluentui/react-components";
import {
  CheckmarkCircle24Filled,
  DismissCircle24Filled,
  Info24Regular,
  Warning24Regular,
  ChevronDown24Regular,
  ChevronRight24Regular,
  CheckmarkCircle16Filled,
  DismissCircle16Filled,
  Database24Regular,
  ArrowDownload24Regular,
} from "@fluentui/react-icons";

/* ── Styles ──────────────────────────────────────────────────────── */

const useStyles = makeStyles({
  root: {
    fontSize: tokens.fontSizeBase300,
    lineHeight: "1.6",
    color: tokens.colorNeutralForeground1,
    "& > *:first-child": { marginTop: "0" },
    "& > *:last-child": { marginBottom: "0" },
  },

  /* markdown overrides */
  markdown: {
    "& h1": {
      fontSize: tokens.fontSizeBase500,
      fontWeight: 700,
      margin: "16px 0 8px",
      color: tokens.colorNeutralForeground1,
    },
    "& h2": {
      fontSize: tokens.fontSizeBase400,
      fontWeight: 600,
      margin: "12px 0 6px",
      color: tokens.colorNeutralForeground1,
    },
    "& h3": {
      fontSize: tokens.fontSizeBase300,
      fontWeight: 600,
      margin: "10px 0 4px",
      color: tokens.colorNeutralForeground2,
    },
    "& p": {
      margin: "6px 0",
    },
    "& ul, & ol": {
      margin: "4px 0",
      paddingLeft: "20px",
    },
    "& li": {
      margin: "2px 0",
    },
    "& code": {
      backgroundColor: tokens.colorNeutralBackground4,
      padding: "1px 5px",
      borderRadius: "3px",
      fontSize: tokens.fontSizeBase200,
      fontFamily: "Consolas, 'Courier New', monospace",
    },
    "& pre": {
      backgroundColor: tokens.colorNeutralBackground4,
      padding: "10px 12px",
      borderRadius: "6px",
      overflowX: "auto",
      margin: "8px 0",
    },
    "& pre code": {
      backgroundColor: "transparent",
      padding: 0,
    },
    "& a": {
      color: tokens.colorBrandForeground1,
      textDecoration: "none",
    },
    "& a:hover": {
      textDecoration: "underline",
    },
    "& blockquote": {
      borderLeft: `3px solid ${tokens.colorBrandStroke1}`,
      margin: "8px 0",
      padding: "4px 12px",
      color: tokens.colorNeutralForeground3,
    },
    "& hr": {
      border: "none",
      borderTop: `1px solid ${tokens.colorNeutralStroke2}`,
      margin: "12px 0",
    },
    "& strong": {
      fontWeight: 600,
    },
    /* markdown tables rendered by remark-gfm */
    "& table": {
      width: "100%",
      borderCollapse: "collapse",
      margin: "8px 0",
      fontSize: tokens.fontSizeBase200,
    },
    "& thead": {
      backgroundColor: tokens.colorNeutralBackground3,
    },
    "& th": {
      padding: "8px 12px",
      fontWeight: 600,
      color: tokens.colorNeutralForeground1,
      textAlign: "left" as const,
      borderBottom: `2px solid ${tokens.colorBrandStroke1}`,
      whiteSpace: "nowrap",
    },
    "& td": {
      padding: "6px 12px",
      color: tokens.colorNeutralForeground1,
      borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
      wordBreak: "break-word" as const,
    },
    "& tbody tr:hover": {
      backgroundColor: tokens.colorNeutralBackground1Hover,
    },
    "& tbody tr:nth-child(even)": {
      backgroundColor: tokens.colorNeutralBackground3,
    },
  },

  /* columnar data table for arrays of objects */
  dataTable: {
    width: "100%",
    borderCollapse: "collapse",
    margin: "8px 0",
    fontSize: tokens.fontSizeBase200,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    borderRadius: "6px",
    overflow: "hidden",
  },
  dataTableHead: {
    backgroundColor: tokens.colorNeutralBackground3,
  },
  dataTableTh: {
    padding: "8px 12px",
    fontWeight: 600,
    color: tokens.colorNeutralForeground1,
    textAlign: "left" as const,
    borderBottom: `2px solid ${tokens.colorBrandStroke1}`,
    whiteSpace: "nowrap",
    fontSize: tokens.fontSizeBase200,
  },
  dataTableTd: {
    padding: "6px 12px",
    color: tokens.colorNeutralForeground1,
    borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
    wordBreak: "break-word" as const,
    fontSize: tokens.fontSizeBase200,
    maxWidth: "300px",
  },
  dataTableRow: {
    "&:hover": {
      backgroundColor: tokens.colorNeutralBackground1Hover,
    },
  },
  dataTableRowEven: {
    backgroundColor: tokens.colorNeutralBackground3,
  },
  dataTableWrapper: {
    overflowX: "auto" as const,
    margin: "8px 0",
    borderRadius: "6px",
    border: `1px solid ${tokens.colorNeutralStroke2}`,
  },
  dataTableCount: {
    fontSize: tokens.fontSizeBase100,
    color: tokens.colorNeutralForeground3,
    marginBottom: "4px",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },

  /* key-value table for JSON */
  kvTable: {
    width: "100%",
    borderCollapse: "collapse",
    margin: "8px 0",
    fontSize: tokens.fontSizeBase200,
  },
  kvRow: {
    borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
  },
  kvKey: {
    padding: "6px 12px 6px 0",
    fontWeight: 600,
    color: tokens.colorNeutralForeground2,
    whiteSpace: "nowrap",
    verticalAlign: "top",
    width: "1%",
  },
  kvValue: {
    padding: "6px 0",
    color: tokens.colorNeutralForeground1,
    wordBreak: "break-word",
  },

  /* status badge inline */
  statusBadge: {
    display: "inline-flex",
    alignItems: "center",
    gap: "4px",
    padding: "2px 8px",
    borderRadius: "12px",
    fontSize: tokens.fontSizeBase200,
    fontWeight: 600,
  },
  statusSuccess: {
    backgroundColor: tokens.colorPaletteGreenBackground1,
    color: tokens.colorPaletteGreenForeground1,
  },
  statusFailed: {
    backgroundColor: tokens.colorPaletteRedBackground1,
    color: tokens.colorPaletteRedForeground1,
  },
  statusInfo: {
    backgroundColor: tokens.colorNeutralBackground4,
    color: tokens.colorNeutralForeground2,
  },
  statusWarning: {
    backgroundColor: tokens.colorPaletteYellowBackground1,
    color: tokens.colorPaletteYellowForeground2,
  },

  /* nested JSON card */
  nestedCard: {
    backgroundColor: tokens.colorNeutralBackground1,
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    borderRadius: "6px",
    padding: "8px 12px",
    margin: "4px 0",
  },
  nestedTitle: {
    fontWeight: 600,
    fontSize: tokens.fontSizeBase200,
    color: tokens.colorNeutralForeground3,
    marginBottom: "4px",
    textTransform: "uppercase" as const,
    letterSpacing: "0.3px",
  },

  /* array as list */
  arrayList: {
    margin: "2px 0",
    paddingLeft: "16px",
    listStyleType: "disc",
  },
  arrayItem: {
    margin: "2px 0",
    fontSize: tokens.fontSizeBase200,
  },

  /* collapsible section */
  collapsibleHeader: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
    padding: "8px 12px",
    backgroundColor: tokens.colorNeutralBackground3,
    borderRadius: "6px",
    cursor: "pointer",
    userSelect: "none" as const,
    margin: "8px 0 4px",
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    "&:hover": {
      backgroundColor: tokens.colorNeutralBackground3Hover,
    },
  },
  collapsibleTitle: {
    fontWeight: 600,
    fontSize: tokens.fontSizeBase300,
    color: tokens.colorNeutralForeground1,
    flex: 1,
  },
  collapsibleBadge: {
    fontSize: tokens.fontSizeBase100,
    color: tokens.colorNeutralForeground3,
    backgroundColor: tokens.colorNeutralBackground4,
    padding: "1px 8px",
    borderRadius: "10px",
  },
  collapsibleBody: {
    padding: "4px 12px 12px",
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    borderTop: "none",
    borderRadius: "0 0 6px 6px",
    marginTop: "-4px",
    marginBottom: "8px",
  },

  /* section header (for top-level JSON keys like executive_summary) */
  sectionHeader: {
    fontSize: tokens.fontSizeBase300,
    fontWeight: 600,
    color: tokens.colorBrandForeground1,
    margin: "12px 0 4px",
    paddingBottom: "4px",
    borderBottom: `2px solid ${tokens.colorBrandStroke1}`,
    display: "flex",
    alignItems: "center",
    gap: "6px",
  },

  /* checklist */
  checklistItem: {
    display: "flex",
    alignItems: "flex-start",
    gap: "6px",
    margin: "3px 0",
    fontSize: tokens.fontSizeBase200,
  },
  checkDone: {
    color: tokens.colorPaletteGreenForeground1,
    flexShrink: 0,
    marginTop: "1px",
  },
  checkPending: {
    color: tokens.colorPaletteRedForeground1,
    flexShrink: 0,
    marginTop: "1px",
  },

  /* summary card for top-level discovery reports */
  summaryCard: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
    gap: "8px",
    margin: "8px 0",
  },
  summaryMetric: {
    backgroundColor: tokens.colorNeutralBackground3,
    borderRadius: "6px",
    padding: "8px 12px",
    textAlign: "center" as const,
  },
  summaryMetricValue: {
    fontSize: tokens.fontSizeBase500,
    fontWeight: 700,
    color: tokens.colorBrandForeground1,
    display: "block",
  },
  summaryMetricLabel: {
    fontSize: tokens.fontSizeBase100,
    color: tokens.colorNeutralForeground3,
    textTransform: "uppercase" as const,
    letterSpacing: "0.3px",
  },

  /* database/resource cards */
  resourceCard: {
    border: `1px solid ${tokens.colorNeutralStroke2}`,
    borderRadius: "8px",
    padding: "12px",
    margin: "6px 0",
    backgroundColor: tokens.colorNeutralBackground1,
  },
  resourceHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: "6px",
  },
  resourceName: {
    fontWeight: 600,
    fontSize: tokens.fontSizeBase300,
    color: tokens.colorNeutralForeground1,
    display: "flex",
    alignItems: "center",
    gap: "6px",
  },
  resourceMeta: {
    display: "flex",
    gap: "8px",
    flexWrap: "wrap" as const,
    marginTop: "4px",
  },
  resourceTag: {
    display: "inline-flex",
    alignItems: "center",
    gap: "3px",
    fontSize: tokens.fontSizeBase100,
    padding: "1px 6px",
    borderRadius: "3px",
    backgroundColor: tokens.colorNeutralBackground4,
    color: tokens.colorNeutralForeground3,
  },

  /* download link card for blob upload results */
  downloadCard: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    padding: "14px 18px",
    marginTop: "8px",
    marginBottom: "8px",
    borderRadius: "8px",
    backgroundColor: tokens.colorNeutralBackground1,
    border: `1px solid ${tokens.colorBrandStroke1}`,
    boxShadow: tokens.shadow2,
  },
  downloadIcon: {
    fontSize: "28px",
    color: tokens.colorBrandForeground1,
    flexShrink: 0,
  },
  downloadInfo: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "2px",
    flex: 1,
    minWidth: 0,
  },
  downloadTitle: {
    fontSize: tokens.fontSizeBase400,
    fontWeight: 600,
    color: tokens.colorNeutralForeground1,
  },
  downloadMeta: {
    fontSize: tokens.fontSizeBase200,
    color: tokens.colorNeutralForeground3,
  },
  downloadLink: {
    display: "inline-flex",
    alignItems: "center",
    gap: "6px",
    padding: "6px 16px",
    borderRadius: "6px",
    backgroundColor: tokens.colorBrandBackground,
    color: tokens.colorNeutralForegroundOnBrand,
    fontSize: tokens.fontSizeBase300,
    fontWeight: 600,
    textDecoration: "none",
    flexShrink: 0,
    ":hover": {
      backgroundColor: tokens.colorBrandBackgroundHover,
    },
  },
});

/* ── Helpers ─────────────────────────────────────────────────────── */

/** Try to parse a string as JSON. Returns the parsed object or null. */
function tryParseJson(str: string): Record<string, unknown> | unknown[] | null {
  const trimmed = str.trim();
  if (
    (trimmed.startsWith("{") && trimmed.endsWith("}")) ||
    (trimmed.startsWith("[") && trimmed.endsWith("]"))
  ) {
    try {
      const parsed = JSON.parse(trimmed);
      if (typeof parsed === "object" && parsed !== null) return parsed;
    } catch {
      /* not JSON */
    }
  }
  return null;
}

/**
 * Check if a JSON object represents a blob upload result.
 * The MCP storage_upload_blob tool returns:
 *   { "status": "uploaded", "container": "...", "blob": "..." }
 */
function isBlobUploadResult(
  obj: Record<string, unknown>
): obj is { status: string; container: string; blob: string } {
  return (
    typeof obj.container === "string" &&
    typeof obj.blob === "string" &&
    (obj.status === "uploaded" || obj.status === "success")
  );
}

/**
 * Build the download URL for a blob.
 * Points at the backend proxy endpoint: GET /api/v1/blob/{container}/{blob}
 */
function blobDownloadUrl(container: string, blob: string): string {
  return `/api/v1/blob/${encodeURIComponent(container)}/${blob.split("/").map(encodeURIComponent).join("/")}`;
}

interface BlobRef {
  container: string;
  blob: string;
  raw: string; // original JSON text for removal
}

/**
 * Scan text for blob upload result JSON objects.
 * Matches inline `{"status":"uploaded","container":"...","blob":"..."}`
 * as well as standalone JSON blocks.
 */
function extractBlobUploads(text: string): BlobRef[] {
  const results: BlobRef[] = [];
  // Match any JSON-like object in the text
  const regex = /\{[^{}]*"(?:status|container|blob)"[^{}]*\}/g;
  let m: RegExpExecArray | null;
  while ((m = regex.exec(text)) !== null) {
    const parsed = tryParseJson(m[0]);
    if (parsed && !Array.isArray(parsed) && isBlobUploadResult(parsed)) {
      results.push({ container: parsed.container, blob: parsed.blob, raw: m[0] });
    }
  }
  return results;
}

/** Remove blob upload JSON snippets from text so the rest can be rendered normally. */
function removeBlobJsonFromText(text: string, blobs: BlobRef[]): string {
  let result = text;
  for (const b of blobs) {
    result = result.replace(b.raw, "");
  }
  return result.trim();
}

/** Humanise a snake_case / camelCase key into Title Case. */
function humaniseKey(key: string): string {
  return key
    .replace(/([a-z])([A-Z])/g, "$1 $2") // camelCase → camel Case
    .replace(/[_-]/g, " ") // snake_case → snake case
    .replace(/\b\w/g, (c) => c.toUpperCase()) // capitalise words
    .replace(/\bId\b/g, "ID")
    .replace(/\bUrl\b/g, "URL")
    .replace(/\bFqdn\b/g, "FQDN")
    .replace(/\bSku\b/g, "SKU")
    .replace(/\bHns\b/g, "HNS")
    .replace(/\bTls\b/g, "TLS")
    .replace(/\bSql\b/g, "SQL")
    .replace(/\bAdf\b/g, "ADF");
}

/** Check if a string value looks like a status. */
function getStatusType(
  key: string,
  value: unknown
): "success" | "failed" | "warning" | "info" | null {
  const k = String(key).toLowerCase();
  const v = String(value).toLowerCase();
  if (k === "status" || k === "provisioning_state" || k === "state" || k === "discovery_status") {
    if (
      v === "success" ||
      v === "succeeded" ||
      v === "created" ||
      v === "created_or_updated" ||
      v === "running" ||
      v === "ready" ||
      v === "active" ||
      v === "fully accessible" ||
      v === "completed"
    )
      return "success";
    if (v === "failed" || v === "error" || v === "deleted" || v === "inaccessible") return "failed";
    if (v === "warning" || v === "degraded" || v === "partial" || v.includes("partial")) return "warning";
    return "info";
  }
  // Boolean-ish keys
  if (k === "accessible" || k === "schema_discovered" || k === "relationships_discovered" || k === "tables_discovered") {
    if (value === true) return "success";
    if (value === false) return "failed";
  }
  if (k === "fallback_used" && value === true) return "warning";
  return null;
}

/** Keys that represent section headers when at top level of a JSON object. */
const SECTION_KEYS = new Set([
  "executive_summary", "summary", "recommendations", "discovery_gaps",
  "data_architecture_insights", "data_quality_observations", "technical_notes",
  "next_steps", "conclusion", "discovery_metadata", "system_catalog_analysis",
  "relationship_patterns", "schema_structure", "deployment_pattern",
]);

/** Keys whose values should be rendered as summary metrics. */
const METRIC_KEYS = new Set([
  "total_databases", "user_databases", "system_databases", "total_size_mb",
  "databases_examined", "databases_accessible", "total_tables_found",
  "schemas_discovered", "tables_with_schema", "total_columns_discovered",
  "relationships_discovered", "completeness_score", "accessible_data_percentage",
  "total_foreign_keys", "user_defined_relationships",
]);

/** Keys whose array items look like a database/resource listing. */
function isResourceArray(key: string, arr: unknown[]): boolean {
  if (key === "databases" || key === "resources" || key === "servers" || key === "services") {
    return arr.length > 0 && arr.every(
      (item) => typeof item === "object" && item !== null && ("name" in item || "database_name" in item)
    );
  }
  return false;
}

/** Check if an array contains checklist-style items (starting with ✓ or ✗). */
function isChecklist(arr: unknown[]): boolean {
  return arr.length > 0 && arr.every(
    (item) => typeof item === "string" && (/^[✓✗✔✘☑☐]/.test(item) || /^[•\-\*]\s/.test(item))
  );
}

/** Count the total number of keys in a nested object (for sizing). */
function countKeys(obj: unknown, depth: number = 0): number {
  if (depth > 4 || typeof obj !== "object" || obj === null) return 0;
  if (Array.isArray(obj)) return obj.reduce((acc: number, item) => acc + countKeys(item, depth + 1), 0);
  const entries = Object.entries(obj as Record<string, unknown>);
  return entries.reduce((acc, [, v]) => acc + 1 + countKeys(v, depth + 1), 0);
}

/**
 * Convert structured list data into markdown tables.
 *
 * Detects patterns like:
 *   ### Heading (N items)\n\n
 *   name - value\n
 *   name - value\n
 *
 * or bullet lists:
 *   - name - value\n
 *   - name - value\n
 *
 * And converts them to GFM table syntax so remarkGfm renders real tables.
 */
function convertListsToTables(text: string): string {
  // Split into lines for processing
  const lines = text.split("\n");
  const result: string[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Detect a heading line (# or ## or ### or **bold heading**)
    const headingMatch = line.match(/^(#{1,4})\s+(.+)/) ||
      line.match(/^\*\*(.+?)\*\*\s*$/);

    if (headingMatch) {
      // Look ahead to collect list items after this heading
      // Skip blank lines between heading and list
      let j = i + 1;
      while (j < lines.length && lines[j].trim() === "") j++;

      // Collect consecutive lines that look like "name - value" or "- name - value"
      const listItems: Array<{ name: string; value: string }> = [];
      const sepPattern = /^(?:[-•*]\s+)?(.+?)\s+[-–—]\s+(.+)$/;
      // Also match lines like "name (detail) - value"
      const sepPattern2 = /^(?:[-•*]\s+)?(.+?)\s*[-–—]+\s+(\d[\d,]*\s*rows?.*)$/i;

      while (j < lines.length) {
        const itemLine = lines[j].trim();
        if (itemLine === "") {
          // Allow one blank line in the middle of a list
          if (j + 1 < lines.length && lines[j + 1].trim() !== "" &&
              (sepPattern.test(lines[j + 1].trim()) || sepPattern2.test(lines[j + 1].trim()))) {
            j++;
            continue;
          }
          break;
        }
        // Stop if we hit another heading
        if (/^#{1,4}\s/.test(itemLine) || /^\*\*[^*]+\*\*\s*$/.test(itemLine)) break;

        const m = itemLine.match(sepPattern2) || itemLine.match(sepPattern);
        if (m) {
          listItems.push({ name: m[1].trim(), value: m[2].trim() });
          j++;
        } else {
          // Non-matching line — stop collecting
          break;
        }
      }

      // If we collected enough items, convert to table
      if (listItems.length >= 3) {
        result.push(line); // Keep the heading
        result.push(""); // Blank line before table

        // Determine column headers from context
        const hasRowCounts = listItems.some((it) => /\d+\s*rows?/i.test(it.value));
        const col1 = hasRowCounts ? "Table" : "Name";
        const col2 = hasRowCounts ? "Row Count" : "Details";

        result.push(`| ${col1} | ${col2} |`);
        result.push(`| --- | --- |`);
        for (const item of listItems) {
          // Escape pipe chars in values
          const name = item.name.replace(/\|/g, "\\|");
          const value = item.value.replace(/\|/g, "\\|");
          result.push(`| ${name} | ${value} |`);
        }
        result.push(""); // Blank line after table
        i = j;
        continue;
      }
    }

    // No table detected — pass line through as-is
    result.push(line);
    i++;
  }

  return result.join("\n");
}

/** Check if content has any markdown indicators. */
function hasMarkdownSyntax(text: string): boolean {
  return /^#{1,6}\s|^\*\s|^-\s|^\d+\.\s|\*\*|__|\[.*\]\(|```|^\|.*\|/m.test(text);
}

/**
 * Check if an array of objects is suitable for columnar data-table rendering.
 * Returns the common column keys if suitable, or null if not.
 * Criteria: ≥2 items, all are objects, and they share a reasonable set of common keys.
 */
function getDataTableColumns(arr: unknown[]): string[] | null {
  if (arr.length < 2) return null;
  // All items must be plain objects
  if (!arr.every((item) => typeof item === "object" && item !== null && !Array.isArray(item))) return null;

  // Collect all keys across all items
  const allKeys = new Map<string, number>();
  for (const item of arr) {
    for (const key of Object.keys(item as Record<string, unknown>)) {
      allKeys.set(key, (allKeys.get(key) || 0) + 1);
    }
  }

  // Keep keys that appear in at least 50% of items
  const threshold = Math.ceil(arr.length * 0.5);
  const columns = Array.from(allKeys.entries())
    .filter(([, count]) => count >= threshold)
    .map(([key]) => key);

  // Need at least 2 columns to be tabular
  if (columns.length < 2) return null;

  // Check that values are mostly scalar (strings, numbers, booleans, null)
  // Allow up to 2 columns with complex values (objects/arrays)
  let complexCount = 0;
  for (const col of columns) {
    const hasComplex = arr.some((item) => {
      const val = (item as Record<string, unknown>)[col];
      return val !== null && val !== undefined && typeof val === "object";
    });
    if (hasComplex) complexCount++;
  }
  if (complexCount > 2) return null;

  return columns;
}

/**
 * Format a cell value for display in a data table.
 * Returns a string representation or a React element for complex values.
 */
function formatCellValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "✓ Yes" : "✗ No";
  if (typeof value === "number") return String(value);
  if (typeof value === "string") return value;
  if (Array.isArray(value)) {
    if (value.length === 0) return "—";
    if (value.every((v) => typeof v !== "object" || v === null)) return value.join(", ");
    return `[${value.length} items]`;
  }
  if (typeof value === "object") {
    const keys = Object.keys(value as Record<string, unknown>);
    if (keys.length <= 3) {
      return keys
        .map((k) => `${k}: ${formatCellValue((value as Record<string, unknown>)[k])}`)
        .join(", ");
    }
    return `{${keys.length} fields}`;
  }
  return String(value);
}

/* ── Sub-components ──────────────────────────────────────────────── */

/** Renders a status badge with icon. */
const StatusBadge = ({
  status,
  statusType,
}: {
  status: string;
  statusType: "success" | "failed" | "warning" | "info";
}) => {
  const styles = useStyles();
  const cls =
    statusType === "success"
      ? styles.statusSuccess
      : statusType === "failed"
      ? styles.statusFailed
      : statusType === "warning"
      ? styles.statusWarning
      : styles.statusInfo;
  const icon =
    statusType === "success" ? (
      <CheckmarkCircle24Filled style={{ fontSize: 14 }} />
    ) : statusType === "failed" ? (
      <DismissCircle24Filled style={{ fontSize: 14 }} />
    ) : statusType === "warning" ? (
      <Warning24Regular style={{ fontSize: 14 }} />
    ) : (
      <Info24Regular style={{ fontSize: 14 }} />
    );
  return (
    <span className={`${styles.statusBadge} ${cls}`}>
      {icon} {String(status)}
    </span>
  );
};

/** Collapsible section wrapper. */
const CollapsibleSection = ({
  title,
  badge,
  defaultOpen,
  children,
}: {
  title: string;
  badge?: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) => {
  const styles = useStyles();
  const [isOpen, setIsOpen] = useState(defaultOpen ?? false);
  const toggle = useCallback(() => setIsOpen((o: boolean) => !o), []);
  return (
    <div>
      <div className={styles.collapsibleHeader} onClick={toggle} role="button" tabIndex={0}>
        {isOpen ? <ChevronDown24Regular style={{ fontSize: 16 }} /> : <ChevronRight24Regular style={{ fontSize: 16 }} />}
        <span className={styles.collapsibleTitle}>{title}</span>
        {badge && <span className={styles.collapsibleBadge}>{badge}</span>}
      </div>
      {isOpen && <div className={styles.collapsibleBody}>{children}</div>}
    </div>
  );
};

/** Renders summary metrics as a grid of cards. */
const SummaryMetrics = ({ data }: { data: Record<string, unknown> }) => {
  const styles = useStyles();
  const metrics = Object.entries(data).filter(
    ([k, v]) => METRIC_KEYS.has(k) && (typeof v === "number" || typeof v === "string")
  );
  if (metrics.length === 0) return null;
  return (
    <div className={styles.summaryCard}>
      {metrics.map(([k, v]) => (
        <div key={k} className={styles.summaryMetric}>
          <span className={styles.summaryMetricValue}>{String(v)}</span>
          <span className={styles.summaryMetricLabel}>{humaniseKey(k)}</span>
        </div>
      ))}
    </div>
  );
};

/** Renders a checklist-style array (items starting with ✓ / ✗). */
const Checklist = ({ items }: { items: string[] }) => {
  const styles = useStyles();
  return (
    <div>
      {items.map((item, i) => {
        const isDone = /^[✓✔☑]/.test(item);
        const isPending = /^[✗✘☐]/.test(item);
        const text = item.replace(/^[✓✗✔✘☑☐•\-\*]\s*/, "");
        return (
          <div key={i} className={styles.checklistItem}>
            {isDone ? (
              <CheckmarkCircle16Filled className={styles.checkDone} />
            ) : isPending ? (
              <DismissCircle16Filled className={styles.checkPending} />
            ) : (
              <span style={{ width: 16 }}>•</span>
            )}
            <span>{text}</span>
          </div>
        );
      })}
    </div>
  );
};

/** Renders a resource/database card. */
const ResourceCard = ({ item }: { item: Record<string, unknown> }) => {
  const styles = useStyles();
  const name = String(item.name || item.database_name || "Unknown");
  const status = item.status ? String(item.status) : item.accessible !== undefined ? (item.accessible ? "Accessible" : "Inaccessible") : undefined;
  const statusType = status ? getStatusType("status", status) : null;
  const sizeMb = item.size_mb ?? item.size_bytes;
  const type = item.type ? String(item.type) : item.description ? String(item.description) : undefined;

  // Collect tags
  const tags: Array<{ label: string; value: string }> = [];
  if (sizeMb !== undefined) tags.push({ label: "Size", value: typeof item.size_mb === "number" ? `${item.size_mb} MB` : `${item.size_bytes} bytes` });
  if (item.table_count !== undefined) tags.push({ label: "Tables", value: String(item.table_count) });
  if (item.schema_count !== undefined) tags.push({ label: "Schemas", value: String(item.schema_count) });

  // Remaining details to show
  const skipKeys = new Set(["name", "database_name", "status", "accessible", "size_mb", "size_bytes", "type", "description", "table_count", "schema_count"]);
  const details = Object.entries(item).filter(([k]) => !skipKeys.has(k));

  return (
    <div className={styles.resourceCard}>
      <div className={styles.resourceHeader}>
        <div className={styles.resourceName}>
          <Database24Regular style={{ fontSize: 18 }} />
          {name}
        </div>
        {status && statusType && <StatusBadge status={status} statusType={statusType} />}
      </div>
      {type && <Caption1 style={{ color: tokens.colorNeutralForeground3 }}>{type}</Caption1>}
      {tags.length > 0 && (
        <div className={styles.resourceMeta}>
          {tags.map((t) => (
            <span key={t.label} className={styles.resourceTag}>
              <strong>{t.label}:</strong> {t.value}
            </span>
          ))}
        </div>
      )}
      {details.length > 0 && details.some(([, v]) => v !== null && v !== undefined) && (
        <div style={{ marginTop: 6 }}>
          {details.map(([k, v]) => {
            if (v === null || v === undefined) return null;
            return (
              <div key={k} style={{ marginTop: 4 }}>
                <JsonValue keyName={k} value={v} />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

/** Renders an array of objects as a proper columnar data table. */
const DataTable = ({
  data,
  columns,
  title,
}: {
  data: Array<Record<string, unknown>>;
  columns: string[];
  title?: string;
}) => {
  const styles = useStyles();
  const [collapsed, setCollapsed] = useState(data.length > 20);
  const displayData = collapsed ? data.slice(0, 20) : data;

  return (
    <div>
      {title && (
        <div className={styles.dataTableCount}>
          <span>
            <strong>{title}</strong> — {data.length} {data.length === 1 ? "row" : "rows"}
          </span>
        </div>
      )}
      {!title && data.length > 5 && (
        <div className={styles.dataTableCount}>
          <span>{data.length} rows</span>
        </div>
      )}
      <div className={styles.dataTableWrapper}>
        <table className={styles.dataTable}>
          <thead className={styles.dataTableHead}>
            <tr>
              {columns.map((col) => (
                <th key={col} className={styles.dataTableTh}>
                  {humaniseKey(col)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {displayData.map((row, rowIdx) => {
              const cellValue = (col: string) => {
                const val = row[col];
                const statusType = getStatusType(col, val);
                if (statusType) {
                  return <StatusBadge status={String(val)} statusType={statusType} />;
                }
                if (typeof val === "boolean") {
                  return (
                    <span
                      style={{
                        color: val
                          ? tokens.colorPaletteGreenForeground1
                          : tokens.colorPaletteRedForeground1,
                        fontWeight: 600,
                      }}
                    >
                      {val ? "✓ Yes" : "✗ No"}
                    </span>
                  );
                }
                return <span>{formatCellValue(val)}</span>;
              };

              return (
                <tr
                  key={rowIdx}
                  className={`${styles.dataTableRow} ${
                    rowIdx % 2 === 1 ? styles.dataTableRowEven : ""
                  }`}
                >
                  {columns.map((col) => (
                    <td key={col} className={styles.dataTableTd}>
                      {cellValue(col)}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {data.length > 20 && (
        <div style={{ textAlign: "center", margin: "4px 0" }}>
          <span
            style={{
              color: tokens.colorBrandForeground1,
              cursor: "pointer",
              fontSize: tokens.fontSizeBase200,
            }}
            onClick={() => setCollapsed(!collapsed)}
          >
            {collapsed
              ? `Show all ${data.length} rows ▼`
              : `Show fewer ▲`}
          </span>
        </div>
      )}
    </div>
  );
};

/** Renders a download card for a blob upload result. */
const BlobDownloadLink = ({
  container,
  blob,
}: {
  container: string;
  blob: string;
}) => {
  const styles = useStyles();
  const fileName = blob.includes("/") ? blob.split("/").pop()! : blob;
  const url = blobDownloadUrl(container, blob);

  return (
    <div className={styles.downloadCard}>
      <ArrowDownload24Regular className={styles.downloadIcon} />
      <div className={styles.downloadInfo}>
        <span className={styles.downloadTitle}>{fileName}</span>
        <span className={styles.downloadMeta}>
          {container} / {blob}
        </span>
      </div>
      <a
        href={url}
        download={fileName}
        className={styles.downloadLink}
        target="_blank"
        rel="noopener noreferrer"
      >
        <ArrowDownload24Regular style={{ fontSize: 16 }} />
        Download
      </a>
    </div>
  );
};

/** Renders a JSON value as appropriate UI. */
const JsonValue = ({ keyName, value }: { keyName: string; value: unknown }): React.ReactElement | null => {
  const styles = useStyles();

  // null / undefined
  if (value === null || value === undefined) {
    return <Caption1 style={{ color: tokens.colorNeutralForeground4 }}>—</Caption1>;
  }

  // boolean — render as status badge for relevant keys
  if (typeof value === "boolean") {
    const statusType = getStatusType(keyName, value);
    if (statusType) {
      return <StatusBadge status={value ? "Yes" : "No"} statusType={statusType} />;
    }
    return (
      <span style={{ color: value ? tokens.colorPaletteGreenForeground1 : tokens.colorPaletteRedForeground1 }}>
        {value ? "Yes" : "No"}
      </span>
    );
  }

  // status-like string values
  if (typeof value === "string" || typeof value === "number") {
    const statusType = getStatusType(keyName, value);
    if (statusType) {
      return <StatusBadge status={String(value)} statusType={statusType} />;
    }
    // Percentage strings
    if (typeof value === "string" && /^\d+%$/.test(value)) {
      const pct = parseInt(value, 10);
      const color = pct >= 70 ? tokens.colorPaletteGreenForeground1 : pct >= 40 ? tokens.colorPaletteYellowForeground2 : tokens.colorPaletteRedForeground1;
      return <span style={{ fontWeight: 600, color }}>{value}</span>;
    }
    return <span>{String(value)}</span>;
  }

  // nested object
  if (typeof value === "object" && !Array.isArray(value)) {
    const obj = value as Record<string, unknown>;
    const entries = Object.entries(obj).filter(([, v]) => v !== null && v !== undefined);
    if (entries.length === 0) return <Caption1 style={{ color: tokens.colorNeutralForeground4 }}>—</Caption1>;

    // If it has many keys, use a collapsible card
    const totalKeys = countKeys(obj);
    if (totalKeys > 8) {
      return (
        <CollapsibleSection title={humaniseKey(keyName)} badge={`${entries.length} fields`} defaultOpen={false}>
          <table className={styles.kvTable}>
            <tbody>
              {entries.map(([k, v]) => (
                <tr key={k} className={styles.kvRow}>
                  <td className={styles.kvKey}>{humaniseKey(k)}</td>
                  <td className={styles.kvValue}>
                    <JsonValue keyName={k} value={v} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CollapsibleSection>
      );
    }

    return (
      <div className={styles.nestedCard}>
        <table className={styles.kvTable}>
          <tbody>
            {entries.map(([k, v]) => (
              <tr key={k} className={styles.kvRow}>
                <td className={styles.kvKey}>{humaniseKey(k)}</td>
                <td className={styles.kvValue}>
                  <JsonValue keyName={k} value={v} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  // array
  if (Array.isArray(value)) {
    if (value.length === 0) return <Caption1 style={{ color: tokens.colorNeutralForeground4 }}>—</Caption1>;

    // Checklist items (✓ / ✗ markers)
    if (value.every((v) => typeof v === "string") && isChecklist(value as string[])) {
      return <Checklist items={value as string[]} />;
    }

    // Array of objects → prefer columnar data table when possible
    const tableColumns = getDataTableColumns(value);
    if (tableColumns) {
      return (
        <DataTable
          data={value as Array<Record<string, unknown>>}
          columns={tableColumns}
          title={humaniseKey(keyName)}
        />
      );
    }

    // Resource/database cards (only when not suitable for data table)
    if (isResourceArray(keyName, value)) {
      return (
        <div>
          {value.map((item, i) => (
            <ResourceCard key={i} item={item as Record<string, unknown>} />
          ))}
        </div>
      );
    }

    // array of simple values → bullet list
    if (value.every((v) => typeof v !== "object" || v === null)) {
      return (
        <ul className={styles.arrayList}>
          {value.map((item: unknown, i: number) => (
            <li key={i} className={styles.arrayItem}>
              {String(item)}
            </li>
          ))}
        </ul>
      );
    }
    // array of objects (too varied for table) → stacked cards
    return (
      <div>
        {value.map((item: unknown, i: number) => (
          <div key={i} className={styles.nestedCard} style={{ marginBottom: 6 }}>
            <div className={styles.nestedTitle}>
              {typeof item === "object" && item !== null && "name" in item
                ? String((item as Record<string, unknown>).name)
                : `Item ${i + 1}`}
            </div>
            <JsonValue keyName={`${keyName}[${i}]`} value={item} />
          </div>
        ))}
      </div>
    );
  }

  // fallback
  return <span>{String(value)}</span>;
};

/** Renders a top-level JSON object with sections, metrics, and smart layout. */
const JsonTable = ({ data, isTopLevel }: { data: Record<string, unknown>; isTopLevel?: boolean }) => {
  const styles = useStyles();
  const entries = Object.entries(data).filter(([, v]) => v !== null && v !== undefined);
  if (entries.length === 0) return null;

  // Blob upload result → render as download card instead of table
  if (isBlobUploadResult(data)) {
    return <BlobDownloadLink container={data.container as string} blob={data.blob as string} />;
  }

  // For top-level discovery reports, render with section structure
  if (isTopLevel && entries.length > 5) {
    // Separate simple fields (strings/numbers/booleans) from complex fields (objects/arrays)
    const simple: Array<[string, unknown]> = [];
    const sections: Array<[string, unknown]> = [];

    for (const [k, v] of entries) {
      if (typeof v === "object" && v !== null) {
        sections.push([k, v]);
      } else {
        simple.push([k, v]);
      }
    }

    return (
      <div>
        {/* Render simple key-values as a compact table first */}
        {simple.length > 0 && (
          <table className={styles.kvTable}>
            <tbody>
              {simple.map(([k, v]) => (
                <tr key={k} className={styles.kvRow}>
                  <td className={styles.kvKey}>{humaniseKey(k)}</td>
                  <td className={styles.kvValue}>
                    <JsonValue keyName={k} value={v} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Render complex fields as sections */}
        {sections.map(([k, v]) => {
          const isSection = SECTION_KEYS.has(k);
          const obj = v as Record<string, unknown>;

          // Summary objects with metric keys → render as metric grid
          if (k === "summary" && typeof v === "object" && !Array.isArray(v)) {
            const metricEntries = Object.entries(obj).filter(([mk]) => METRIC_KEYS.has(mk));
            const otherEntries = Object.entries(obj).filter(([mk]) => !METRIC_KEYS.has(mk));
            return (
              <div key={k}>
                <div className={styles.sectionHeader}>{humaniseKey(k)}</div>
                {metricEntries.length > 0 && <SummaryMetrics data={obj} />}
                {otherEntries.length > 0 && otherEntries.map(([sk, sv]) => (
                  <div key={sk} style={{ marginTop: 4 }}>
                    <JsonValue keyName={sk} value={sv} />
                  </div>
                ))}
              </div>
            );
          }

          // Arrays → prefer data table, fallback to resource cards
          if (Array.isArray(v) && v.length > 0) {
            const arrCols = getDataTableColumns(v);
            if (arrCols) {
              return (
                <div key={k}>
                  <div className={styles.sectionHeader}>
                    <Database24Regular style={{ fontSize: 18 }} />
                    {humaniseKey(k)}
                  </div>
                  <DataTable
                    data={v as Array<Record<string, unknown>>}
                    columns={arrCols}
                  />
                </div>
              );
            }
            if (isResourceArray(k, v)) {
              return (
                <div key={k}>
                  <div className={styles.sectionHeader}>
                    <Database24Regular style={{ fontSize: 18 }} />
                    {humaniseKey(k)} ({v.length})
                  </div>
                  {v.map((item: unknown, i: number) => (
                    <ResourceCard key={i} item={item as Record<string, unknown>} />
                  ))}
                </div>
              );
            }
          }

          // Section header + collapsible content for large sections
          if (isSection && typeof v === "object" && !Array.isArray(v)) {
            const totalKeys = countKeys(v);
            if (totalKeys > 10) {
              return (
                <CollapsibleSection
                  key={k}
                  title={humaniseKey(k)}
                  badge={`${Object.keys(obj).length} items`}
                  defaultOpen={k === "executive_summary" || k === "conclusion"}
                >
                  <table className={styles.kvTable}>
                    <tbody>
                      {Object.entries(obj).filter(([, sv]) => sv !== null && sv !== undefined).map(([sk, sv]) => (
                        <tr key={sk} className={styles.kvRow}>
                          <td className={styles.kvKey}>{humaniseKey(sk)}</td>
                          <td className={styles.kvValue}>
                            <JsonValue keyName={sk} value={sv} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CollapsibleSection>
              );
            }
            return (
              <div key={k}>
                <div className={styles.sectionHeader}>{humaniseKey(k)}</div>
                <table className={styles.kvTable}>
                  <tbody>
                    {Object.entries(obj).filter(([, sv]) => sv !== null && sv !== undefined).map(([sk, sv]) => (
                      <tr key={sk} className={styles.kvRow}>
                        <td className={styles.kvKey}>{humaniseKey(sk)}</td>
                        <td className={styles.kvValue}>
                          <JsonValue keyName={sk} value={sv} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          }

          // Default: collapsible for large, inline for small
          const totalKeys = countKeys(v);
          if (totalKeys > 12) {
            return (
              <CollapsibleSection key={k} title={humaniseKey(k)} badge={Array.isArray(v) ? `${v.length} items` : `${Object.keys(obj).length} fields`}>
                <JsonValue keyName={k} value={v} />
              </CollapsibleSection>
            );
          }

          return (
            <div key={k} style={{ marginTop: 8 }}>
              <div className={styles.sectionHeader}>{humaniseKey(k)}</div>
              <JsonValue keyName={k} value={v} />
            </div>
          );
        })}
      </div>
    );
  }

  // Simple flat table for non-top-level or small objects
  return (
    <table className={styles.kvTable}>
      <tbody>
        {entries.map(([k, v]) => (
          <tr key={k} className={styles.kvRow}>
            <td className={styles.kvKey}>{humaniseKey(k)}</td>
            <td className={styles.kvValue}>
              <JsonValue keyName={k} value={v} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

/** Renders a top-level array — prefers data table when items are uniform objects. */
const JsonArray = ({ data }: { data: unknown[] }) => {
  const styles = useStyles();

  // Try data table first for arrays of uniform objects
  const columns = getDataTableColumns(data);
  if (columns) {
    return (
      <DataTable
        data={data as Array<Record<string, unknown>>}
        columns={columns}
      />
    );
  }

  // Fallback: stacked cards
  return (
    <div>
      {data.map((item: unknown, i: number) => {
        if (typeof item === "object" && item !== null && !Array.isArray(item)) {
          return (
            <div key={i} className={styles.nestedCard} style={{ marginBottom: 8 }}>
              <JsonTable data={item as Record<string, unknown>} isTopLevel />
            </div>
          );
        }
        return (
          <div key={i} className={styles.arrayItem}>
            {String(item)}
          </div>
        );
      })}
    </div>
  );
};

/* ── Main Component ──────────────────────────────────────────────── */

interface FormattedContentProps {
  content: string;
  /** Compact mode reduces spacing (used in sidebar step output). */
  compact?: boolean;
}

/**
 * Renders agent content as user-friendly formatted output.
 *
 * Detection order:
 *  1. Pure JSON string → table / card rendering
 *  2. Mixed content with ```json blocks → markdown + inline JSON tables
 *  3. Markdown-containing text → rendered markdown
 *  4. Plain text → pre-wrap text
 */
const FormattedContent: React.FC<FormattedContentProps> = ({ content, compact }) => {
  const styles = useStyles();

  const rendered = useMemo(() => {
    if (!content || !content.trim()) return null;
    let trimmed = content.trim();

    // ── 0. Scan for blob upload results → download links ──────
    const blobUploads = extractBlobUploads(trimmed);
    if (blobUploads.length > 0) {
      // If the entire content is just blob upload JSON(s), render download cards only
      // Otherwise, render the rest of the content normally and append download cards
      const withoutBlobs = removeBlobJsonFromText(trimmed, blobUploads);
      const downloadCards = blobUploads.map((b, i) => (
        <BlobDownloadLink key={`dl-${i}`} container={b.container} blob={b.blob} />
      ));
      if (!withoutBlobs.trim()) {
        return <>{downloadCards}</>;
      }
      // Render remaining content normally, then append download cards
      return (
        <>
          <FormattedContent content={withoutBlobs} />
          {downloadCards}
        </>
      );
    }

    // ── 0. Convert structured lists into GFM tables ──────────
    trimmed = convertListsToTables(trimmed);

    // ── 1. Pure JSON ────────────────────────────────────────────
    const jsonData = tryParseJson(trimmed);
    if (jsonData) {
      if (Array.isArray(jsonData)) {
        return <JsonArray data={jsonData} />;
      }
      return <JsonTable data={jsonData} isTopLevel />;
    }

    // ── 2. Mixed content: markdown text interleaved with JSON blocks
    //       Split on ```json ... ``` fenced blocks ──────────────
    const jsonBlockRegex = /```json\s*\n([\s\S]*?)```/g;
    const hasJsonBlocks = jsonBlockRegex.test(trimmed);
    if (hasJsonBlocks) {
      // Reset regex
      jsonBlockRegex.lastIndex = 0;
      const parts: React.ReactNode[] = [];
      let lastIndex = 0;
      let match: RegExpExecArray | null;
      let partIdx = 0;

      while ((match = jsonBlockRegex.exec(trimmed)) !== null) {
        // Text before the JSON block
        const textBefore = trimmed.slice(lastIndex, match.index);
        if (textBefore.trim()) {
          parts.push(
            <div key={`md-${partIdx}`} className={styles.markdown}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{textBefore}</ReactMarkdown>
            </div>
          );
        }
        // The JSON block itself
        const innerJson = tryParseJson(match[1]);
        if (innerJson) {
          if (Array.isArray(innerJson)) {
            parts.push(<JsonArray key={`json-${partIdx}`} data={innerJson} />);
          } else {
            parts.push(<JsonTable key={`json-${partIdx}`} data={innerJson as Record<string, unknown>} isTopLevel />);
          }
        } else {
          // Couldn't parse — render as code block via markdown
          parts.push(
            <div key={`code-${partIdx}`} className={styles.markdown}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{match[0]}</ReactMarkdown>
            </div>
          );
        }
        lastIndex = match.index + match[0].length;
        partIdx++;
      }
      // Remaining text
      const remaining = trimmed.slice(lastIndex);
      if (remaining.trim()) {
        parts.push(
          <div key={`md-tail`} className={styles.markdown}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{remaining}</ReactMarkdown>
          </div>
        );
      }
      return <>{parts}</>;
    }

    // ── 3. Text that contains inline JSON objects (single line or multi-line)
    //       e.g. "Resource created: {"status": "success", ...}"
    const inlineJsonRegex = /(\{[\s\S]*?\})/g;
    const inlineMatches = trimmed.match(inlineJsonRegex);
    if (inlineMatches) {
      // Check if any match is valid JSON
      const hasInlineJson = inlineMatches.some((m) => tryParseJson(m) !== null);
      if (hasInlineJson) {
        const parts: React.ReactNode[] = [];
        let remaining = trimmed;
        let partIdx = 0;

        for (const m of inlineMatches) {
          const parsed = tryParseJson(m);
          if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
            const idx = remaining.indexOf(m);
            const before = remaining.slice(0, idx);
            if (before.trim()) {
              parts.push(
                <div key={`text-${partIdx}`} className={styles.markdown}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{before}</ReactMarkdown>
                </div>
              );
            }
            parts.push(
              <JsonTable key={`json-${partIdx}`} data={parsed as Record<string, unknown>} isTopLevel />
            );
            remaining = remaining.slice(idx + m.length);
            partIdx++;
          }
        }
        if (remaining.trim()) {
          parts.push(
            <div key={`text-tail`} className={styles.markdown}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{remaining}</ReactMarkdown>
            </div>
          );
        }
        if (parts.length > 0) return <>{parts}</>;
      }
    }

    // ── 4. Markdown text ────────────────────────────────────────
    if (hasMarkdownSyntax(trimmed)) {
      return (
        <div className={styles.markdown}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{trimmed}</ReactMarkdown>
        </div>
      );
    }

    // ── 5. Plain text fallback ──────────────────────────────────
    return <span style={{ whiteSpace: "pre-wrap" }}>{trimmed}</span>;
  }, [content, styles]);

  return (
    <div
      className={styles.root}
      style={compact ? { fontSize: tokens.fontSizeBase200, lineHeight: "1.4" } : undefined}
    >
      {rendered}
    </div>
  );
};

export default FormattedContent;
