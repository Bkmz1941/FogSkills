// Regression by group on a regress stand: node regress.mjs dev|prod|local [group...]
// Groups: stand, wallets, bets, bonuses, admin, launches (launches needs provider names: launches:"Provider A","Provider B").
// Without a group runs stand, wallets, bets, bonuses and admin. Prints each probe's tally and a summary; exit 1 on any failure.
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const GROUPS = {
  stand: [["regress-run.mjs"]],
  wallets: [["wallet-rules-regress.mjs"], ["admin-transactions-regress.mjs"]],
  bets: [["regress-edge.mjs"]],
  bonuses: [["bonus-regress.mjs"]],
  admin: [["admin-regress.mjs"]],
  launches: [["games-launch-regress.mjs"]],
};
const DEFAULT = ["stand", "wallets", "bets", "bonuses", "admin"];

const [envName, ...requested] = process.argv.slice(2);
if (!["dev", "prod", "local"].includes(envName ?? "")) {
  console.log(`usage: node regress.mjs dev|prod|local [${Object.keys(GROUPS).join("|")}]...`);
  process.exit(2);
}
const runs = (requested.length ? requested : DEFAULT).flatMap((entry) => {
  const [group, extra] = entry.split(/:(.*)/s);
  if (!GROUPS[group]) { console.log(`unknown group ${group}`); process.exit(2); }
  const args = extra ? extra.split(",").map((value) => value.trim()).filter(Boolean) : [];
  if (group === "launches" && !args.length) { console.log("launches needs providers: launches:\"Provider A\",\"Provider B\""); process.exit(2); }
  return GROUPS[group].map(([script]) => ({ group, script, args }));
});

const summary = [];
for (const run of runs) {
  console.log(`\n### ${run.group}: ${run.script}`);
  const result = spawnSync(process.execPath, [join(here, run.script), envName, ...run.args], { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
  const output = `${result.stdout ?? ""}${result.stderr ?? ""}`;
  process.stdout.write(output);
  const tally = [...output.matchAll(/(\d+)\/(\d+) passed/g)].pop();
  summary.push({ ...run, ok: result.status === 0, tally: tally ? `${tally[1]}/${tally[2]}` : "no tally" });
}

console.log(`\n== ${envName} summary`);
for (const run of summary) console.log(`${run.ok ? "PASS" : "FAIL"} ${run.group.padEnd(8)} ${run.script.padEnd(32)} ${run.tally}`);
process.exitCode = summary.every((run) => run.ok) ? 0 : 1;
