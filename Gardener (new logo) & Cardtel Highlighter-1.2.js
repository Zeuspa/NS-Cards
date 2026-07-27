// ==UserScript==
// @name         Gardener (new logo) & Cardtel Highlighter
// @version      1.2
// @namespace    dithpri.RCES
// @description  Adds The Card Gardening Society's and The Cardtel's icons besides members and their puppets during auctions, works with main displayer script
// @author       dithpri
// @contributor  zeuspa
// @noframes
// @match        https://www.nationstates.net/*page=deck*/*card=*
// @match        https://www.nationstates.net/*card=*/*page=deck*
// @grant        GM.xmlHttpRequest
// @grant        GM.setValue
// @grant        GM.getValue
// @connect      docs.google.com
// @connect      googleusercontent.com
// ==/UserScript==

/*
 * Copyright (c) 2020 dithpri (Racoda) <dithpri@gmail.com>
 * This file is part of RCES: https://github.com/dithpri/RCES and licensed under
 * the MIT license. See LICENSE.md or
 * https://github.com/dithpri/RCES/blob/master/LICENSE.md for more details.
 *
 * Modified by zeuspa
 */

/* Permissions:
 *
 * GM.xmlHttpRequest, `connect docs.google.com`, `connect googleusercontent.com`:
 *     to automatically fetch and update members' nations.
 *
 * GM.setValue, GM.getValue:
 *     to save and load members' nations locally.
 */

(function () {
    "use strict";

    function GM_addStyle(style) {
        const node = document.createElement("style");
        node.innerHTML = style;
        document.getElementsByTagName("head")[0].appendChild(node);
    }

    const gardener_icon_base64 =
	"data:image/png;base64,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";
    const cardtel_icon_base64 =
	"data:image/png;base64,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";

    const orgs = [
        {
            key: "cardgardens",
            lastupdate_key: "cardgardens-lastupdate",
            sheet_url: "https://docs.google.com/spreadsheets/d/1mqQRESG_HrMF6aToHqUF40eHNkLE6XbusoeZHFUMTKQ/export?format=tsv&id=1mqQRESG_HrMF6aToHqUF40eHNkLE6XbusoeZHFUMTKQ&gid=641340461",
            css_class: "rces-cl-cardgardens",
            icon_base64: gardener_icon_base64,
            inset: 8,
        },
        {
            key: "cardtel",
            lastupdate_key: "cardtel-lastupdate",
            sheet_url: "https://docs.google.com/spreadsheets/d/e/2PACX-1vThf2cwCdk9k_NaKIlyu1cU_JDpWcEhdo-f8FqvvABiE2tpB7c9Ifbj7Ufb13XBt4t4E89ySQYzcGKm/pub?gid=0&single=true&output=tsv",
            css_class: "rces-cl-cardtel",
            icon_base64: cardtel_icon_base64,
            inset: 32,
        },
    ];

    function canonicalFromHref(href) {
        if (!href) return null;
        const m = href.replace(/^\//, "").match(/^nation=([a-z0-9_-]+)$/i);
        if (!m) return null;
        return m[1].replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
    }

    function resolveMainNation(cell) {
        const mainLink = cell.querySelector("a.rces-main-nation");
        if (mainLink) {
            return canonicalFromHref(mainLink.getAttribute("href")) || mainLink.textContent.trim();
        }
        const link = cell.querySelector("a.nlink");
        if (!link) return null;
        return canonicalFromHref(link.getAttribute("href")) || link.textContent.trim();
    }

    const update_auctiontable = async function () {
        const members_by_org = {};
        for (const org of orgs) {
            const stored = await GM.getValue(org.key, "");
            members_by_org[org.key] = stored.split("\n");
        }

        document.querySelectorAll("#cardauctiontable > tbody > tr > td > p > a.nlink").forEach(function (el) {
            const cell = el.closest("td");
            if (!cell) return;
            const row = cell.parentNode;
            const mainNation = resolveMainNation(cell);

            // Create canonical name for matching (lowercase with underscores)
            const canonical_nname = mainNation
                ? mainNation.toLowerCase().replace(/ /g, "_")
                : el.getAttribute("href").replace(/^.*nation=/, "").toLowerCase();

            orgs.forEach(function (org) {
                const existing_icon = cell.querySelector(":scope > ." + org.css_class + "-icon");
                if (members_by_org[org.key].includes(canonical_nname)) {
                    cell.classList.add(org.css_class + "-cell");
                    cell.classList.toggle(org.css_class + "-cell-left", cell === row.firstElementChild);
                    cell.classList.toggle(org.css_class + "-cell-right", cell === row.lastElementChild);
                    if (!existing_icon) {
                        const icon = document.createElement("span");
                        icon.classList.add(org.css_class + "-icon");
                        cell.appendChild(icon);
                    }
                } else {
                    cell.classList.remove(org.css_class + "-cell", org.css_class + "-cell-left", org.css_class + "-cell-right");
                    if (existing_icon) existing_icon.remove();
                }
            });
        });
    };

    if (document.getElementById("auctiontablebox")) {
        // Run update logic
        (async () => {
            for (const org of orgs) {
                const lastUpdate = await GM.getValue(org.lastupdate_key, 0);
                if (lastUpdate + 12 * 60 * 60 * 1000 < new Date().getTime()) {
                    GM.xmlHttpRequest({
                        method: "GET",
                        url: org.sheet_url,
                        onload: async function (data) {
                            console.info("Updated members for: " + org.key);
                            const processedData = data.responseText
                                .split("\n")
                                .slice(1) // Skip header
                                .map(line => {
                                    const parts = line.split("\t");
                                    return parts[1] ? parts[1].trim().toLowerCase().replace(/ /g, "_") : "";
                                })
                                .filter(name => name.length > 0)
                                .join("\n");

                            await GM.setValue(org.key, processedData);
                            await GM.setValue(org.lastupdate_key, new Date().getTime());
                            update_auctiontable();
                        },
                    });
                }
            }
        })();

        const target_node = document.getElementById("auctiontablebox");
        const observerOptions = { subtree: true, childList: true };

        let observer = new MutationObserver(function () {
            observer.disconnect();
            update_auctiontable().finally(() => {
                observer.observe(target_node, observerOptions);
            });
        });

        update_auctiontable().finally(() => {
            observer.observe(target_node, observerOptions);
        });

        GM_addStyle(`
            .rces-cl-cardgardens-cell, .rces-cl-cardtel-cell { position: relative; }
            .rces-cl-cardgardens-icon, .rces-cl-cardtel-icon {
                position: absolute;
                top: 50%;
                width: 22px;
                height: 22px;
                transform: translateY(-50%);
                background-size: contain;
                background-repeat: no-repeat;
                pointer-events: none;
                z-index: 10;
            }
            .rces-cl-cardgardens-icon { background-image: url('${gardener_icon_base64}'); }
            .rces-cl-cardtel-icon { background-image: url('${cardtel_icon_base64}'); }
            .rces-cl-cardgardens-cell-left > .rces-cl-cardgardens-icon { left: 8px; }
            .rces-cl-cardgardens-cell-right > .rces-cl-cardgardens-icon { right: 8px; }
            .rces-cl-cardtel-cell-left > .rces-cl-cardtel-icon { left: 32px; }
            .rces-cl-cardtel-cell-right > .rces-cl-cardtel-icon { right: 32px; }
        `);
    }
})();