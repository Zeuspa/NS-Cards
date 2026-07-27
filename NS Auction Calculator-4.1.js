// ==UserScript==
// @name         NS Auction Calculator
// @namespace    ns-card-tax-calc
// @version      4.1
// @author       zeuspa
// @description  A side table that lists current matches on an NS card page, netted to each account's main nation if the Main Auction Displayer script is present.
// @match        https://www.nationstates.net/*/page=deck/*
// @match        https://www.nationstates.net/page=deck/*
// @grant        none
// ==/UserScript==

(function () {
  'use strict';

  const TAX_RATE = 0.10;
  const TAX_THRESHOLD = 10.00;

  let panel = null;
  let toggleBtn = null;
  let panelClosed = false;

  // ---- YOUR NATION -------------------------------------------------------
  // Bolded wherever it appears in the Net Position list.
  const MY_NATION_NAME = '';
  // -----------------------------------------------------------------------

  function netAfterTax(price) {
    return price > TAX_THRESHOLD ? price * (1 - TAX_RATE) : price;
  }

  function isPriceText(text) {
    return /^-?\d+\.\d{2}$/.test(text.trim());
  }

  function canonicalFromHref(href) {
    if (!href) return null;
    const m = href.replace(/^\//, '').match(/^nation=([a-z0-9_\-]+)$/i);
    if (!m) return null;
    return m[1].replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  }

  function resolveMainName(nameTd) {
    const rawLink = nameTd.querySelector('a.nlink:not(.rces-main-nation)') || nameTd.querySelector('a.nlink');
    const rawName = rawLink
      ? canonicalFromHref(rawLink.getAttribute('href')) || rawLink.textContent.trim()
      : null;

    const mainLink = nameTd.querySelector('a.rces-main-nation');
    if (mainLink) {
      return canonicalFromHref(mainLink.getAttribute('href')) || mainLink.textContent.trim();
    }

    return rawName;
  }

  function parseRow(tr) {
    const tds = Array.from(tr.children).filter((el) => el.tagName === 'TD');
    const nameTds = [];
    const priceTds = [];
    tds.forEach((td) => {
      if (td.querySelector('a.nlink')) {
        nameTds.push(td);
      } else if (isPriceText(td.textContent)) {
        priceTds.push(td);
      }
    });

    if (priceTds.length !== 3) return null;

    const matchPrice = parseFloat(priceTds[1].textContent.trim());
    const seller = nameTds.length > 0 ? resolveMainName(nameTds[0]) : null;
    const buyer = nameTds.length > 1 ? resolveMainName(nameTds[nameTds.length - 1]) : null;

    return { price: matchPrice, seller, buyer };
  }

  function collect() {
    const table = document.getElementById('cardauctiontable');
    if (!table) return null;

    const rows = Array.from(table.querySelectorAll('tbody > tr'));
    return rows.map(parseRow).filter(Boolean).sort((a, b) => b.price - a.price);
  }

  function computeNetPositions(rows) {
    const net = new Map();
    const add = (name, delta) => {
      if (!name) return;
      net.set(name, (net.get(name) || 0) + delta);
    };
    rows.forEach((r) => {
      add(r.seller, netAfterTax(r.price));
      add(r.buyer, -r.price);
    });
    return Array.from(net.entries())
      .map(([name, total]) => ({ name, total }))
      .sort((a, b) => b.total - a.total);
  }

  function run() {
    const rows = collect();
    if (rows === null) return false;
    const netPositions = computeNetPositions(rows);
    renderPanel(rows, netPositions);
    return true;
  }

  function ensureToggleButton() {
    if (toggleBtn) return;
    toggleBtn = document.createElement('div');
    toggleBtn.id = 'ns-tax-calc-toggle';
    toggleBtn.textContent = '$';
    toggleBtn.title = 'Toggle NS Tax Calculator';
    toggleBtn.style.cssText = `
      position: fixed; bottom: 20px; right: 20px; width: 36px; height: 36px; border-radius: 50%;
      background: #333; color: #fff; display: flex; align-items: center; justify-content: center;
      cursor: pointer; z-index: 100000; box-shadow: 0 2px 6px rgba(0,0,0,.5); font-size: 16px; font-weight: bold;
      border: 1px solid #666; user-select: none;
    `;
    toggleBtn.addEventListener('click', () => {
      panelClosed = !panelClosed;
      applyVisibility();
    });
    document.body.appendChild(toggleBtn);
  }

  function applyVisibility() {
    if (panel) panel.style.display = panelClosed ? 'none' : 'block';
  }

  function renderPanel(rows, netPositions) {
    ensureToggleButton();

    if (!panel) {
      panel = document.createElement('div');
      panel.id = 'ns-tax-calc-panel';
      panel.style.cssText = `
        position: fixed; top: 150px; right: 10px; width: 380px; max-height: 80vh; overflow-y: auto;
        background: #1b1b1b; color: #eee; border: 1px solid #555; border-radius: 6px;
        font-family: sans-serif; font-size: 12px; z-index: 99999; padding: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,.6);
      `;
      document.body.appendChild(panel);
    }

    let html = `
      <div style="font-weight:bold; margin-bottom:6px; display:flex; justify-content:space-between;">
        <span>NS Auction Calculator</span>
        <span id="ns-tax-close" style="cursor:pointer;">&#10005;</span>
      </div>`;

    const totalTax = rows.reduce((sum, r) => {
      const tax = r.price - netAfterTax(r.price);
      return sum + tax;
    }, 0);

    if (netPositions && netPositions.length > 0) {
      html += `
        <table style="width:100%; border-collapse:collapse;">
          <tr style="color:#aaa; text-align:left;"><th>Account</th><th style="text-align:right;">Net</th></tr>`;
      netPositions.forEach((p) => {
        const color = p.total > 0 ? '#7CFC00' : p.total < 0 ? '#FF6666' : '#eee';
        const isMe = p.name && p.name.toLowerCase() === MY_NATION_NAME.toLowerCase();
        const nameHtml = isMe ? `<b>${p.name}</b>` : p.name;
        html += `
          <tr style="border-top:1px solid #333;">
            <td>${nameHtml}</td>
            <td style="text-align:right; color:${color};">${p.total >= 0 ? '+' : ''}${p.total.toFixed(2)}</td>
          </tr>`;
      });
      html += `</table>
        <div style="margin-top:6px; color:#aaa;">Total tax collected: <b>${totalTax.toFixed(2)}</b> bank</div>
        <div style="color:#888; font-size:11px; margin-top:4px;">
        </div>`;
    } else {
      html += `<div style="color:#999;">No matched auctions found this round.</div>`;
    }

    panel.innerHTML = html;
    document.getElementById('ns-tax-close').addEventListener('click', () => {
      panelClosed = true;
      applyVisibility();
    });
    applyVisibility();
  }

  let attempts = 0;
  const bootInterval = setInterval(() => {
    attempts++;
    if (run() || attempts > 40) clearInterval(bootInterval);
  }, 500);

  let debounceTimer = null;
  const observer = new MutationObserver((mutations) => {
    const relevant = mutations.some((m) => {
      if (panel && panel.contains(m.target)) return false;
      if (toggleBtn && toggleBtn.contains(m.target)) return false;
      return true;
    });
    if (!relevant) return;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(run, 300);
  });
  observer.observe(document.body, { childList: true, subtree: true });
})();