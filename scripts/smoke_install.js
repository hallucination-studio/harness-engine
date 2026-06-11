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

if (!fs.existsSync(skillFile)) {
  throw new Error(`Missing installed skill file: ${skillFile}`);
}

if (!fs.existsSync(manager)) {
  throw new Error(`Missing installed manager script: ${manager}`);
}

const where = execFileSync(process.execPath, [installer, "where", "--path", target], {
  cwd: root,
  encoding: "utf8"
}).trim();

if (where !== skill) {
  throw new Error(`Unexpected where output: ${where}`);
}

console.log(JSON.stringify({ status: "pass", installed: skill }, null, 2));
