import fs from "node:fs";
import crypto from "node:crypto";

const pemPath = process.argv[2];
if (!pemPath) {
  console.error("Usage: node scripts/gen-ext-key.mjs path\\to\\extension.pem");
  process.exit(1);
}

const pem = fs.readFileSync(pemPath, "utf8");
const pub = crypto.createPublicKey(pem);
const der = pub.export({ type: "spki", format: "der" });

const keyB64 = der.toString("base64");

// Chrome extension id derivation (first 16 bytes of sha256, nibble->a..p)
const hash = crypto.createHash("sha256").update(der).digest();
const first16 = hash.subarray(0, 16);

let id = "";
for (const b of first16) {
  const hi = (b >> 4) & 0xf;
  const lo = b & 0xf;
  id += String.fromCharCode(97 + hi) + String.fromCharCode(97 + lo);
}

console.log(JSON.stringify({ key: keyB64, extension_id: id }, null, 2));
