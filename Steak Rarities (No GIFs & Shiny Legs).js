// ==UserScript==
// @name         Steak Rarities (Modified)
// @namespace    zeuspa.RCES
// @version      1.0
// @description  Steak Rarities with S4 legendary gradient support
// @author       zeuspa
// @license      MIT
// @match        https://www.nationstates.net/*page=deck*
// @downloadURL  
// @grant        none
// ==/UserScript==

/*
 * Originally created by dithpri (Racoda) <dithpri@gmail.com>
 * Source: https://github.com/dithpri/RCES
 * Licensed under the MIT license:
 * https://github.com/dithpri/RCES/blob/master/LICENSE.md
 *
 * Modified by zeuspa:
 * - Fixed S4 legendary card gradient support
 * - Removed duplicate/dead CSS rules
 * - Added MutationObserver for dynamic card loading
 * - Added shine effect on legendary cards
 * - Fixed S3 legendary card background
 * - Fixed gradient misalignment by offsetting per-element backgrounds
 * - Added GIF disabling via fetch + createImageBitmap
 */

(function () {
  "use strict";

  const G = "linear-gradient(112deg,#b45c8b 0%,rgb(255,255,0) 100%)";
  const GT = "linear-gradient(112deg,rgba(180,92,139,.5) 0%,rgba(255,255,0,.5) 100%)";

  const css = [
    ".deckcard-category-legendary .deckcard-category::before{content:'LEGENDARY'}",
    ".deckcard-season-2 .deckcard-stripe,.deckcard-season-4 .deckcard-stripe,",
    ".deckcard-season-2 .deckcard-category,.deckcard-season-4 .deckcard-category{background:none}",
    `.minicard-season-4.deckcard-category-legendary,`,
    `.minicard-season-4.deckcard-category-legendary .minicard-category,`,
    `.deckcard-token.deckcard-category-legendary{background:${G}}`,
    ".deckcard-category-legendary .s3-lower .deckcard-govt-collection{background:transparent!important}",
    ".legendary-shine{",
    "position:absolute;",
    "inset:0;",
    "pointer-events:none;",
    "z-index:10;",
    "opacity:0;",
    "background:linear-gradient(115deg,transparent 0%,rgba(255,0,128,.15) 25%,rgba(255,255,0,.15) 40%,rgba(0,255,255,.15) 55%,rgba(128,0,255,.15) 75%,transparent 100%);",
    "background-size:200% 200%;",
    "transition:opacity .3s ease,background-position .1s ease}",
  ].join("\n");

  document.head.insertAdjacentHTML("beforeend", `<style>${css}</style>`);

  function offsetGradient(el, r) {
    if (!el) return;
    const e = el.getBoundingClientRect();
    Object.assign(el.style, {
      backgroundImage:    G,
      backgroundSize:     `${r.width}px ${r.height}px`,
      backgroundPosition: `${-(e.left - r.left)}px ${-(e.top - r.top)}px`
    });
  }

  function urlGradient(el, g, urlFirst) {
    if (!el) return;
    const url = el.style.backgroundImage.match(/url\([^)]+\)/)?.[0];
    el.style.backgroundImage = url
      ? (urlFirst ? `${url},${g}` : `${g},${url}`)
      : g;
  }

  function applyLegendaryGradients() {
    document.querySelectorAll("figure.deckcard-category-legendary").forEach(fig => {
      const r = fig.getBoundingClientRect();
      if (!r.width) return;
      Object.assign(fig.style, {
        backgroundImage:    G,
        backgroundSize:     "100% 100%",
        backgroundPosition: "0 0"
      });
      [
        ".deckcard-category",
        ".deckcard-stripe",
        ".s3-slogan",
        ".s3-lower .deckcard-lower-collection:not(.deckcard-govt-collection)",
        ".s3-lower .deckcard-govt",
      ].forEach(sel => offsetGradient(fig.querySelector(sel), r));
    });
  }

  function applyS4() {
    document.querySelectorAll(".s4-card.legendary").forEach(card => {
      card.style.setProperty("--legendary-backdrop", "transparent");
      const h = card.querySelector("header");
      const f = card.querySelector("footer");
      if (h) h.style.backgroundImage = G;
      if (f) f.style.backgroundImage = G;
      urlGradient(card.querySelector(".bottom"), GT, true);
      urlGradient(card.querySelector("main.flag"), GT, true);
      [".s4-card-wrapper", ".pretitle"].forEach(sel => {
        const el = card.querySelector(sel);
        if (el) el.style.setProperty("background", "transparent", "important");
      });
    });
  }

  function applyShine() {
    document.querySelectorAll("figure.deckcard-category-legendary").forEach(fig => {
      if (fig.dataset.shineAttached) return;
      fig.dataset.shineAttached = "1";
      const shine = Object.assign(document.createElement("div"), { className: "legendary-shine" });
      fig.appendChild(shine);
      fig.addEventListener("mousemove", e => {
        const r = fig.getBoundingClientRect();
        shine.style.backgroundPosition = `${((e.clientX - r.left) / r.width) * 100}% ${((e.clientY - r.top) / r.height) * 100}%`;
        shine.style.opacity = "1";
      });
      fig.addEventListener("mouseleave", () => { shine.style.opacity = "0"; });
    });
  }

  // Fetch src as blob → bitmap → canvas → static data URL
  async function toStaticDataURL(src) {
    const blob = await fetch(src).then(r => r.blob());
    const bitmap = await createImageBitmap(blob);
    const c = document.createElement("canvas");
    c.width = bitmap.width;
    c.height = bitmap.height;
    c.getContext("2d").drawImage(bitmap, 0, 0);
    bitmap.close();
    return c.toDataURL("image/png");
  }

  async function freezeGifImg(img) {
    if (img.dataset.gifDisabled) return;
    img.dataset.gifDisabled = "1";
    try { img.src = await toStaticDataURL(img.src); } catch(e) {}
  }

  async function freezeGifBg(el) {
    if (el.dataset.gifDisabled) return;
    el.dataset.gifDisabled = "1";
    const url = el.style.backgroundImage.match(/url\("?([^")]*\.gif[^")?]*)"?\)/i)?.[1];
    if (!url) return;
    try { el.style.backgroundImage = `url(${await toStaticDataURL(url)})`; } catch(e) {}
  }

  function disableGifs() {
    document.querySelectorAll('img[src*=".gif"]').forEach(freezeGifImg);
    document.querySelectorAll('[style*=".gif"]').forEach(freezeGifBg);
  }

  function applyAll() {
    applyLegendaryGradients();
    applyS4();
    applyShine();
    disableGifs();
  }

  requestAnimationFrame(applyAll);
  new MutationObserver(() => requestAnimationFrame(applyAll))
    .observe(document.body, { childList: true, subtree: true });

})();