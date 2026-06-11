#!/usr/bin/env node

const fs = require("fs");
const os = require("os");
const path = require("path");

const PACKAGE_ROOT = path.resolve(__dirname, "..");
const SKILL_NAME = "harness-engine";
const SOURCE_SKILL_DIR = path.join(PACKAGE_ROOT, "skills", SKILL_NAME);

function printHelp() {
  console.log(`harness-engine

Usage:
  npx @hallucination-studio/harness-engine install [--local | --global | --path <dir>] [--force]
  npx @hallucination-studio/harness-engine where [--local | --global | --path <dir>]

Options:
  --local         Install into <cwd>/.codex/skills
  --global        Install into \${CODEX_HOME:-~/.codex}/skills
  --path <dir>    Install into a custom skills directory
  --force         Replace an existing installed skill
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
    if (entry.isDirectory()) {
      copyDir(sourcePath, targetPath);
    } else {
      fs.copyFileSync(sourcePath, targetPath);
      const stat = fs.statSync(sourcePath);
      fs.chmodSync(targetPath, stat.mode);
    }
  }
}

function installSkill(destinationDir, force) {
  const skillTargetDir = path.join(destinationDir, SKILL_NAME);
  if (!fs.existsSync(SOURCE_SKILL_DIR)) {
    throw new Error(`Bundled skill not found: ${SOURCE_SKILL_DIR}`);
  }

  if (fs.existsSync(skillTargetDir)) {
    if (!force) {
      throw new Error(`Skill already exists at ${skillTargetDir}. Re-run with --force to replace it.`);
    }
    fs.rmSync(skillTargetDir, { recursive: true, force: true });
  }

  fs.mkdirSync(destinationDir, { recursive: true });
  copyDir(SOURCE_SKILL_DIR, skillTargetDir);
  return skillTargetDir;
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
    console.log(path.join(destinationDir, SKILL_NAME));
    return;
  }

  if (args.command !== "install") {
    console.error(`Unknown command: ${args.command}`);
    printHelp();
    process.exit(1);
  }

  try {
    const installedPath = installSkill(destinationDir, args.force);
    console.log(`Installed ${SKILL_NAME} to ${installedPath}`);
    console.log("Invoke it in Codex with $harness-engine.");
  } catch (error) {
    console.error(`Install failed: ${error.message}`);
    process.exit(1);
  }
}

main();
