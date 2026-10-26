// Build the sortable Excel view of the guide index from its CSV source.
//
// Usage: node build_index_xlsx.mjs <library-dir> [index.csv] [index.xlsx]
//
// The CSV stays the single source of truth (scripts/update_index.py writes it),
// and this script turns it into a filtering/sorting-friendly workbook. Run it
// after every delivery, next to update_index.py.

import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

// This script lives in the skill folder, where there is no node_modules, so a
// bare "@oai/artifact-tool" import cannot resolve. Load it from the bundled
// runtime instead (override with ARTIFACT_TOOL_NODE_MODULES if it moves).
const RUNTIME_CANDIDATES = [
  process.env.ARTIFACT_TOOL_NODE_MODULES,
  process.env.USERPROFILE
    ? path.join(process.env.USERPROFILE, ".cache", "codex-runtimes",
                "codex-primary-runtime", "dependencies", "node", "node_modules")
    : null,
].filter(Boolean);

async function loadArtifactTool() {
  const require = createRequire(import.meta.url);
  for (const root of RUNTIME_CANDIDATES) {
    try {
      const entry = require.resolve("@oai/artifact-tool", { paths: [root] });
      return await import(pathToFileURL(entry).href);
    } catch {
      /* try the next candidate */
    }
  }
  throw new Error("cannot resolve @oai/artifact-tool; set ARTIFACT_TOOL_NODE_MODULES");
}

const { SpreadsheetFile, Workbook } = await loadArtifactTool();

const [libraryArg, csvArg, xlsxArg] = process.argv.slice(2);
if (!libraryArg) {
  console.error("usage: node build_index_xlsx.mjs <library-dir> [index.csv] [index.xlsx]");
  process.exit(2);
}

const library = path.resolve(libraryArg);
const csvPath = csvArg ? path.resolve(csvArg) : path.join(library, "安装教程索引.csv");
const xlsxPath = xlsxArg ? path.resolve(xlsxArg) : path.join(library, "安装教程索引.xlsx");

const raw = await fs.readFile(csvPath, "utf8");
// Workbook.fromCSV keeps a leading BOM inside the first header cell; strip it.
const csvText = raw.replace(/^\uFEFF/, "");
const workbook = await Workbook.fromCSV(csvText, { sheetName: "安装指南索引" });
const sheet = workbook.worksheets.getItemAt(0);

const values = sheet.getRange("A1:G200").values;
const rows = values.filter((row) => row.some((cell) => cell !== null && String(cell).trim() !== ""));
const lastRow = rows.length;
const lastCol = rows[0].length;
const bodyRange = sheet.getRange(`A1:${String.fromCharCode(64 + lastCol)}${lastRow}`);

// 页数 is a count, not text: sorting a text column yields 10 < 17 < 2.
const pageCol = rows[0].indexOf("页数") + 1;
if (pageCol > 0) {
  const pageRange = sheet.getRange(`${String.fromCharCode(64 + pageCol)}2:${String.fromCharCode(64 + pageCol)}${lastRow}`);
  pageRange.values = rows.slice(1).map((row) => [Number(row[pageCol - 1]) || null]);
  pageRange.format.numberFormat = "0";
}

// Source links stay plain text on purpose: this authoring engine has no
// hyperlink API, and writing `=HYPERLINK(...)` produces the literal string
// "HYPERLINK is not implemented ..." in the cells (verified, not theoretical).

const header = sheet.getRange(`A1:${String.fromCharCode(64 + lastCol)}1`);
header.format.fill = "#087E75";
header.format.font = { name: "Arial", size: 10, bold: true, color: "#FFFFFF" };
header.format.horizontalAlignment = "center";
header.format.rowHeight = 22;

bodyRange.format.font = { name: "Arial", size: 10, color: "#263238" };
bodyRange.format.wrapText = true;
bodyRange.format.borders = { preset: "all", style: "thin", color: "#D9D9D9" };
sheet.getRange(`C2:C${lastRow}`).format.horizontalAlignment = "left";
if (pageCol > 0) {
  sheet.getRange(`${String.fromCharCode(64 + pageCol)}2:${String.fromCharCode(64 + pageCol)}${lastRow}`)
    .format.horizontalAlignment = "center";
}
const dateCol = rows[0].indexOf("生成日期") + 1;
if (dateCol > 0) {
  sheet.getRange(`${String.fromCharCode(64 + dateCol)}2:${String.fromCharCode(64 + dateCol)}${lastRow}`)
    .format.horizontalAlignment = "center";
}

const widths = [24, 10, 42, 8, 60, 12, 34];
widths.forEach((width, i) => {
  if (i < lastCol) sheet.getRange(`${String.fromCharCode(65 + i)}:${String.fromCharCode(65 + i)}`).format.columnWidth = width;
});

const table = sheet.tables.add(`A1:${String.fromCharCode(64 + lastCol)}${lastRow}`, true, "GuideIndex");
table.style = "TableStyleLight9";
table.showFilterButton = true;

sheet.freezePanes.freezeRows(1);
workbook.recalculate();

const out = await SpreadsheetFile.exportXlsx(workbook);
await out.save(xlsxPath);

// The tooling dumps an "<file>.inspect.ndjson" diagnostic next to the workbook
// even without an explicit inspect() call. Park it in the temp directory so the
// user's guide library only ever holds the index and the PDFs.
for (const side of [xlsxPath + ".inspect.ndjson", csvPath + ".inspect.ndjson"]) {
  try {
    await fs.rename(side, path.join(os.tmpdir(), path.basename(side)));
    console.log("side file moved to temp: " + path.basename(side));
  } catch {
    /* nothing to move */
  }
}

console.log("wrote " + xlsxPath + " (" + (lastRow - 1) + " guides, " + lastCol + " columns, sheet '" + sheet.name + "')");
for (const row of rows) {
  console.log("  " + row.slice(0, 4).join(" | "));
}
