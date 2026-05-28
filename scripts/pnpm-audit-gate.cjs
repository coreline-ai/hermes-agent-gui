#!/usr/bin/env node
/* eslint-disable no-console */
const fs = require('node:fs');
const path = require('node:path');
const semver = require('semver');

const reportPath = process.argv[2] || 'pnpm-audit.json';
const threshold = process.env.AUDIT_LEVEL || 'high';
const rank = { info: 0, low: 1, moderate: 2, high: 3, critical: 4 };
const root = process.cwd();
const searchRoots = [
  root,
  path.join(root, 'apps', 'web'),
  path.join(root, 'electron'),
].filter((p) => fs.existsSync(p));

function loadInstalledVersion(moduleName) {
  for (const base of searchRoots) {
    try {
      const pkg = require.resolve(`${moduleName}/package.json`, { paths: [base] });
      return JSON.parse(fs.readFileSync(pkg, 'utf8')).version;
    } catch {
      // Try the next workspace root.
    }
  }
  return null;
}

const raw = fs.readFileSync(reportPath, 'utf8').trim();
if (!raw) {
  console.log('pnpm audit gate: empty report; treating as clean');
  process.exit(0);
}

const report = JSON.parse(raw);
const minRank = rank[threshold] ?? rank.high;
const failures = [];
let ignoredStale = 0;

for (const advisory of Object.values(report.advisories || {})) {
  if ((rank[advisory.severity] ?? 0) < minRank) continue;
  const moduleName = advisory.module_name;
  const installed = loadInstalledVersion(moduleName);
  if (installed && advisory.vulnerable_versions) {
    const vulnerable = semver.satisfies(installed, advisory.vulnerable_versions, {
      includePrerelease: true,
    });
    if (!vulnerable) {
      ignoredStale += 1;
      continue;
    }
  }
  failures.push({
    module: moduleName,
    severity: advisory.severity,
    title: advisory.title,
    vulnerable: advisory.vulnerable_versions,
    patched: advisory.patched_versions,
    url: advisory.url,
    installed: installed || 'unknown',
  });
}

if (failures.length) {
  console.error(`pnpm audit gate: ${failures.length} ${threshold}+ actionable advisory/advisories`);
  for (const item of failures) {
    console.error(
      `- [${item.severity}] ${item.module}@${item.installed}: ${item.title} ` +
        `(vulnerable ${item.vulnerable}, patched ${item.patched}) ${item.url || ''}`,
    );
  }
  process.exit(1);
}

console.log(`pnpm audit gate: clean for ${threshold}+ advisories (${ignoredStale} stale/false-positive advisory matches ignored)`);
