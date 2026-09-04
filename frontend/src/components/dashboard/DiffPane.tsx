import type { AttemptDetail } from "@/lib/api";

interface DiffPaneProps {
  attempt: AttemptDetail;
}

interface DiffRow {
  kind: "context" | "changed";
  oldLine: number | null;
  newLine: number | null;
  oldText: string;
  newText: string;
}

interface DiffFile {
  path: string;
  rows: DiffRow[];
}

export function DiffPane({ attempt }: DiffPaneProps) {
  const files = parseUnifiedDiff(attempt.diff ?? "");
  const stats = [
    `${attempt.files_changed ?? 0} ${attempt.files_changed === 1 ? "file" : "files"}`,
    `+${attempt.lines_added ?? 0}`,
    `−${attempt.lines_removed ?? 0}`,
  ].join(" · ");

  return (
    <section aria-labelledby="diff-heading" className="min-h-[420px] min-w-0 border border-zinc-800 bg-zinc-950">
      <div className="flex items-center justify-between gap-4 border-b border-zinc-800 px-4 py-3">
        <div>
          <p className="font-mono text-[9px] uppercase tracking-[0.2em] text-zinc-600">
            Candidate artifact
          </p>
          <h3 id="diff-heading" className="mt-1 text-sm font-medium text-zinc-300">
            Proposed diff
          </h3>
        </div>
        <p className="font-mono text-[10px] text-zinc-500">{stats}</p>
      </div>

      {files.length ? (
        <div className="max-h-[650px] overflow-auto">
          {files.map((file) => (
            <div key={file.path}>
              <div className="sticky top-0 z-10 border-y border-zinc-800 bg-zinc-900/95 px-4 py-2 font-mono text-[11px] text-zinc-300 backdrop-blur">
                {file.path}
              </div>
              <div className="min-w-[760px] font-mono text-[11px] leading-5">
                {file.rows.map((row, index) => (
                  <div className="grid grid-cols-2" key={`${file.path}-${index}`}>
                    <DiffCell line={row.oldLine} side="old" text={row.oldText} tone={row.kind === "changed" ? "removed" : "context"} />
                    <DiffCell line={row.newLine} side="new" text={row.newText} tone={row.kind === "changed" ? "added" : "context"} />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="px-4 py-8 font-mono text-xs text-zinc-600">
          {attempt.decision === "in_progress"
            ? "Diff artifact will appear after policy validation."
            : "No textual diff artifact was recorded."}
        </p>
      )}
    </section>
  );
}

interface DiffCellProps {
  line: number | null;
  side: "old" | "new";
  text: string;
  tone: "added" | "removed" | "context";
}

function DiffCell({ line, side, text, tone }: DiffCellProps) {
  const color = {
    added: side === "new" ? "bg-emerald-500/10 text-emerald-100" : "bg-zinc-950 text-zinc-700",
    removed: side === "old" ? "bg-rose-500/10 text-rose-100" : "bg-zinc-950 text-zinc-700",
    context: "bg-zinc-950 text-zinc-400",
  }[tone];
  const marker = tone === "added" && side === "new" ? "+" : tone === "removed" && side === "old" ? "−" : " ";

  return (
    <div className={`grid min-w-0 grid-cols-[42px_18px_1fr] border-r border-zinc-900 ${color}`}>
      <span className="select-none border-r border-zinc-900 px-2 text-right text-zinc-700">
        {line ?? ""}
      </span>
      <span className="select-none text-center opacity-70">{marker}</span>
      <code className="block overflow-hidden whitespace-pre px-1">{text}</code>
    </div>
  );
}

function parseUnifiedDiff(diff: string): DiffFile[] {
  const lines = diff.split("\n");
  const files: DiffFile[] = [];
  let current: DiffFile | null = null;
  let oldLine = 0;
  let newLine = 0;

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    if (line.startsWith("--- ") && lines[index + 1]?.startsWith("+++ ")) {
      const nextPath = lines[index + 1].slice(4);
      const oldPath = line.slice(4);
      current = {
        path: cleanPath(nextPath === "/dev/null" ? oldPath : nextPath),
        rows: [],
      };
      files.push(current);
      index += 1;
      continue;
    }
    const hunk = line.match(/^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
    if (hunk) {
      oldLine = Number(hunk[1]);
      newLine = Number(hunk[2]);
      continue;
    }
    if (!current || line.startsWith("\\ No newline")) continue;

    if (line.startsWith(" ")) {
      current.rows.push({
        kind: "context",
        oldLine,
        newLine,
        oldText: line.slice(1),
        newText: line.slice(1),
      });
      oldLine += 1;
      newLine += 1;
      continue;
    }
    if (line.startsWith("-")) {
      const removed: string[] = [];
      while (index < lines.length && lines[index].startsWith("-") && !lines[index].startsWith("--- ")) {
        removed.push(lines[index].slice(1));
        index += 1;
      }
      const added: string[] = [];
      while (index < lines.length && lines[index].startsWith("+") && !lines[index].startsWith("+++ ")) {
        added.push(lines[index].slice(1));
        index += 1;
      }
      index -= 1;
      const rowCount = Math.max(removed.length, added.length);
      for (let row = 0; row < rowCount; row += 1) {
        current.rows.push({
          kind: "changed",
          oldLine: row < removed.length ? oldLine++ : null,
          newLine: row < added.length ? newLine++ : null,
          oldText: removed[row] ?? "",
          newText: added[row] ?? "",
        });
      }
      continue;
    }
    if (line.startsWith("+")) {
      current.rows.push({
        kind: "changed",
        oldLine: null,
        newLine: newLine++,
        oldText: "",
        newText: line.slice(1),
      });
    }
  }
  return files;
}

function cleanPath(path: string): string {
  return path.startsWith("a/") || path.startsWith("b/") ? path.slice(2) : path;
}
