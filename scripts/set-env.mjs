import fs from "node:fs";
import path from "node:path";

const env = process.argv[2] || "production";
console.log(`Setting up environment for: ${env}`);

const extConfigSrc = path.resolve(process.cwd(), `../extension/config.${env}.js`);
const extConfigDst = path.resolve(process.cwd(), "../extension/config.js");

const extWidgetConfigDst = path.resolve(process.cwd(), "../extension/widget/config.js");
const publicConfigDst = path.resolve(process.cwd(), "public/config.js");

if (!fs.existsSync(extConfigSrc)) {
    console.error(`Config file not found: ${extConfigSrc}`);
    process.exit(1);
}

// 1. extension直下の config.js を上書き
fs.copyFileSync(extConfigSrc, extConfigDst);
console.log(`Copied ${extConfigSrc} -> ${extConfigDst}`);

// 2. vite起動用（public/config.js）としてコピー（dev用）
fs.mkdirSync(path.dirname(publicConfigDst), { recursive: true });
fs.copyFileSync(extConfigSrc, publicConfigDst);
console.log(`Copied ${extConfigSrc} -> ${publicConfigDst}`);

// 3. build後用（extension/widget/config.js）としてコピー
fs.mkdirSync(path.dirname(extWidgetConfigDst), { recursive: true });
fs.copyFileSync(extConfigSrc, extWidgetConfigDst);
console.log(`Copied ${extConfigSrc} -> ${extWidgetConfigDst}`);
