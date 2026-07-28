// ==UserScript==
// @name         Gardener & Cardtel Highlighter (Old Logo)
// @version      1.3
// @namespace    dithpri.RCES
// @description  Adds The Card Gardening Society's and The Cardtel's icons besides members during auctions, with main-nation support & clean alignment.
// @author       dithpri
// @contributor  zeuspa
// @contributor  arlizplot
// @noframes
// @match        https://www.nationstates.net/*page=deck*/*card=*
// @match        https://www.nationstates.net/*card=*/*page=deck*
// @grant        GM.xmlHttpRequest
// @grant        GM.setValue
// @grant        GM.getValue
// @connect      docs.google.com
// @connect      googleusercontent.com
// ==/UserScript==

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
        },
        {
            key: "cardtel",
            lastupdate_key: "cardtel-lastupdate",
            sheet_url: "https://docs.google.com/spreadsheets/d/e/2PACX-1vThf2cwCdk9k_NaKIlyu1cU_JDpWcEhdo-f8FqvvABiE2tpB7c9Ifbj7Ufb13XBt4t4E89ySQYzcGKm/pub?gid=0&single=true&output=tsv",
            css_class: "rces-cl-cardtel",
            icon_base64: cardtel_icon_base64,
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
            const isLeft = (cell === row.firstElementChild);

            const mainNation = resolveMainNation(cell);
            const canonical_nname = mainNation
                ? mainNation.toLowerCase().replace(/ /g, "_")
                : el.getAttribute("href").replace(/^.*nation=/, "").toLowerCase();

            // Ensure single flexbox container exists inside cell
            let container = cell.querySelector(".rces-icon-container");
            if (!container) {
                container = document.createElement("span");
                container.className = "rces-icon-container";
                cell.appendChild(container);
            }

            if (isLeft) {
                container.classList.add("rces-pos-left");
                container.classList.remove("rces-pos-right");
            } else {
                container.classList.add("rces-pos-right");
                container.classList.remove("rces-pos-left");
            }

            orgs.forEach(function (org) {
                let existing_icon = container.querySelector("." + org.css_class + "-icon");

                if (members_by_org[org.key].includes(canonical_nname)) {
                    if (!existing_icon) {
                        existing_icon = document.createElement("span");
                        existing_icon.classList.add("rces-org-icon", org.css_class + "-icon");
                        container.appendChild(existing_icon);
                    }
                } else {
                    if (existing_icon) existing_icon.remove();
                }
            });
        });
    };

    if (document.getElementById("auctiontablebox")) {
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
                                .slice(1)
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
            #cardauctiontable td { position: relative; }
            .rces-icon-container {
                position: absolute;
                top: 50%;
                transform: translateY(-50%);
                display: flex;
                align-items: center;
                gap: 4px;
                pointer-events: none;
                z-index: 10;
            }
            .rces-pos-left { left: 8px; flex-direction: row; }
            .rces-pos-right { right: 8px; flex-direction: row-reverse; }
            .rces-org-icon {
                width: 22px;
                height: 22px;
                background-size: contain;
                background-repeat: no-repeat;
                display: inline-block;
            }
            .rces-cl-cardgardens-icon { background-image: url('${gardener_icon_base64}'); }
            .rces-cl-cardtel-icon { background-image: url('${cardtel_icon_base64}'); }
        `);
    }
})();
