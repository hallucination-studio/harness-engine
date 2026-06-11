#!/usr/bin/env node

const fs = require("fs");
const os = require("os");
const path = require("path");

const PACKAGE_ROOT = path.resolve(__dirname, "..");
const BUNDLE_NAME = "harness-engine-plugin";
const BUNDLE_ENTRIES = [".codex-plugin", "skills"];

function printHelp() {
  console.log(`harness-engine

Usage:
  npx @hallucination-studio/harness-engine install [--local | --global | --path <dir>] [--force]
  npx @hallucination-studio/harness-engine where [--local | --global | --path <dir>]

Options:
  --local         Install into <cwd>/.codex/skills
  --global        Install into \${CODEX_HOME:-~/.codex}/skills
  --path <dir>    Install into a custom skills directory
  --force         Replace an existing installed bundle
  -h, --help      Show this help text
`);
}

function parseArgs(argv) {
  const result = {
    command: "install",
    mode: null,
    customPath: null,
    force: false
  };

  const args = [...argv];
  if (args.length > 0 && !args[0].startsWith("-")) {
    result.command = args.shift();
  }

  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === "--local") {
      result.mode = "local";
    } else if (arg === "--global") {
      result.mode = "global";
    } else if (arg === "--path") {
      result.mode = "custom";
      result.customPath = args[i + 1];
      i += 1;
    } else if (arg === "--force") {
      result.force = true;
    } else if (arg === "-h" || arg === "--help") {
      result.command = "help";
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }

  if (result.mode === "custom" && !result.customPath) {
    throw new Error("--path requires a directory value");
  }

  if (!result.mode) {
    result.mode = "local";
  }

  return result;
}

function resolveSkillsDir(mode, customPath) {
  if (mode === "local") {
    return path.join(process.cwd(), ".codex", "skills");
  }

  if (mode === "global") {
    const codexHome = process.env.CODEX_HOME || path.join(os.homedir(), ".codex");
    return path.join(codexHome, "skills");
  }

  return path.resolve(process.cwd(), customPath);
}

function copyDir(sourceDir, targetDir) {
  fs.mkdirSync(targetDir, { recursive: true });
  for (const entry of fs.readdirSync(sourceDir, { withFileTypes: true })) {
    const sourcePath = path.join(sourceDir, entry.name);
    const targetPath = path.join(targetDir, entry.name);
    const stat = fs.statSync(sourcePath);
    if (stat.isDirectory()) {
      copyDir(sourcePath, targetPath);
    } else if (entry.isSymbolicLink()) {
      const linkTarget = fs.readlinkSync(sourcePath);
      fs.symlinkSync(linkTarget, targetPath);
    } else {
      fs.copyFileSync(sourcePath, targetPath);
      fs.chmodSync(targetPath, stat.mode);
    }
  }
}

function copyEntry(sourcePath, targetPath) {
  const stat = fs.lstatSync(sourcePath);
  if (stat.isDirectory()) {
    copyDir(sourcePath, targetPath);
  } else if (stat.isSymbolicLink()) {
    fs.symlinkSync(fs.readlinkSync(sourcePath), targetPath);
  } else {
    fs.mkdirSync(path.dirname(targetPath), { recursive: true });
    fs.copyFileSync(sourcePath, targetPath);
    fs.chmodSync(targetPath, fs.statSync(sourcePath).mode);
  }
}

function assertBundleSources() {
  for (const entry of BUNDLE_ENTRIES) {
    const sourcePath = path.join(PACKAGE_ROOT, entry);
    if (!fs.existsSync(sourcePath)) {
      throw new Error(`Bundled plugin entry not found: ${sourcePath}`);
    }
  }
}

function removeIfExists(targetPath, force, label) {
  if (!fs.existsSync(targetPath)) {
    return;
  }

  if (!force) {
    throw new Error(`${label} already exists at ${targetPath}. Re-run with --force to replace it.`);
  }

  fs.rmSync(targetPath, { recursive: true, force: true });
}

function installBundle(destinationDir, force) {
  assertBundleSources();
  fs.mkdirSync(destinationDir, { recursive: true });
  const bundleTargetDir = path.join(destinationDir, BUNDLE_NAME);
  removeIfExists(bundleTargetDir, force, "Plugin bundle");

  fs.mkdirSync(bundleTargetDir, { recursive: true });
  for (const entry of BUNDLE_ENTRIES) {
    copyEntry(path.join(PACKAGE_ROOT, entry), path.join(bundleTargetDir, entry));
  }

  // Compatibility: older users invoke $harness-engine from a normal skills directory.
  // Keep a top-level skill copy in place while the plugin root carries the bundle.
  const compatTarget = path.join(destinationDir, "harness-engine");
  removeIfExists(compatTarget, force, "Compatibility skill");
  copyDir(path.join(PACKAGE_ROOT, "skills", "harness-engine"), compatTarget);

  return bundleTargetDir;
}

function main() {
  let args;
  try {
    args = parseArgs(process.argv.slice(2));
  } catch (error) {
    console.error(`Error: ${error.message}`);
    printHelp();
    process.exit(1);
  }

  if (args.command === "help") {
    printHelp();
    return;
  }

  const destinationDir = resolveSkillsDir(args.mode, args.customPath);

  if (args.command === "where") {
    console.log(path.join(destinationDir, BUNDLE_NAME));
    return;
  }

  if (args.command !== "install") {
    console.error(`Unknown command: ${args.command}`);
    printHelp();
    process.exit(1);
  }

  try {
    const installedPath = installBundle(destinationDir, args.force);
    console.log(`Installed ${BUNDLE_NAME} plugin bundle to ${installedPath}`);
    console.log("Invoke it in Codex with $harness-engine.");
  } catch (error) {
    console.error(`Install failed: ${error.message}`);
    process.exit(1);
  }
}

main();
