import fs from "node:fs";
import path from "node:path";

const src = path.resolve(process.cwd(), "../extension/config.js");
const dst = path.resolve(process.cwd(), "../extension/widget/config.js");

fs.mkdirSync(path.dirname(dst), { recursive: true });
fs.copyFileSync(src, dst);
console.log("Copied config.js -> extension/widget/config.js");
