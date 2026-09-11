// Signs the request the way Lucky verifies it:
// HMAC-SHA256 over METHOD, path, canonical query and canonical body, joined by newlines.
// Canonical form sorts top-level keys and escapes forward slashes.
// Reads the secret from x-private-key and fills x-sign, without writing to the environment.
try {
  var secret = pm.environment.get("x-private-key") || pm.variables.get("x-private-key") || "";
  if (!secret) { console.log("[sign] x-private-key is empty, the signature will not match"); }

  function canonical(source) {
    var value = source || {};
    var sorted = {};
    Object.keys(value).sort().forEach(function (key) { sorted[key] = value[key]; });
    return JSON.stringify(sorted).replace(/\//g, "\\/");
  }

  // Path only: no host, no query, no {{baseUrl}} prefix.
  var path = "";
  try { path = pm.request.url.getPath(); } catch (e) { path = ""; }
  if (!path || path.indexOf("{{") !== -1 || path.indexOf("://") !== -1) {
    var full = String(pm.request.url).split("?")[0];
    full = full.replace(/^\{\{[^}]*\}\}/, "").replace(/^[a-zA-Z][a-zA-Z0-9+.-]*:\/\/[^/]+/, "");
    path = full || path;
  }
  if (path.charAt(0) !== "/") { path = "/" + path; }

  var query = {};
  try {
    pm.request.url.query.each(function (p) { if (p && p.key && !p.disabled) { query[p.key] = p.value; } });
  } catch (e) { query = {}; }

  var body = {};
  try {
    var raw = (pm.request.body && pm.request.body.raw) ? pm.request.body.raw : "";
    body = raw ? JSON.parse(raw) : {};
  } catch (e) { body = {}; }

  var method = String(pm.request.method || "GET").toUpperCase();
  var payload = [method, path, canonical(query), canonical(body)].join("\n");

  // The global crypto object is the supported one; CryptoJS stays as a fallback
  // for older runtimes and warns as deprecated where crypto exists.
  var signature;
  if (typeof crypto !== "undefined" && crypto && typeof crypto.createHmac === "function") {
    signature = crypto.createHmac("sha256", secret).update(payload).digest("hex");
  } else {
    var CJS = (typeof CryptoJS !== "undefined" && CryptoJS) ? CryptoJS : require("crypto-js");
    signature = CJS.HmacSHA256(payload, secret).toString(CJS.enc.Hex);
  }

  pm.variables.set("x-sign", signature);
  console.log("[sign] " + method + " " + path + " -> " + signature.substring(0, 16) + "…");
} catch (err) {
  console.log("[sign] script failed: " + (err && err.message ? err.message : err));
}
