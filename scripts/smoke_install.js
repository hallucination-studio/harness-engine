#!/usr/bin/env node

const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync } = require("child_process");

const root = path.resolve(__dirname, "..");
const installer = path.join(root, "bin", "install.js");
const target = fs.mkdtempSync(path.join(os.tmpdir(), "harness-engine-install-"));

execFileSync(process.execPath, [installer, "install", "--path", target], {
  cwd: root,
  stdio: "pipe"
});

const skill = path.join(target, "harness-engine");
const skillFile = path.join(skill, "SKILL.md");
const manager = path.join(skill, "scripts", "manage_harness.py");
const managerCli = path.join(skill, "scripts", "harness_engine", "cli.py");
const evalRunner = path.join(skill, "evals", "run_evals.py");
const evalPackageRunner = path.join(skill, "evals", "harness_engine_evals", "runner.py");

if (!fs.existsSync(skillFile)) {
  throw new Error(`Missing installed skill file: ${skillFile}`);
}

for (const requiredPath of [manager, managerCli, evalRunner, evalPackageRunner]) {
  if (!fs.existsSync(requiredPath)) {
    throw new Error(`Missing installed Python runtime file: ${requiredPath}`);
  }
}

const where = execFileSync(process.execPath, [installer, "where", "--path", target], {
  cwd: root,
  encoding: "utf8"
}).trim();

if (where !== skill) {
  throw new Error(`Unexpected where output: ${where}`);
}

const pluginBundle = path.join(target, "harness-engine-plugin");
if (fs.existsSync(pluginBundle)) {
  throw new Error(`Unexpected plugin bundle directory: ${pluginBundle}`);
}

console.log(JSON.stringify({ status: "pass", installed: skill }, null, 2));
