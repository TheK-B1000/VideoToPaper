"""
Interactive component bundle for generated Inquiry Engine papers.

Week 9 goal:
- Keep generated HTML self-contained.
- Use vanilla JavaScript only.
- Preserve readability when JavaScript is disabled.
- Add accessible claim cards, evidence filtering, and reading-list filtering.
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class InteractiveAssets:
    """
    Self-contained assets injected into the generated HTML paper.

    json_island:
        Structured payload embedded into the document.

    css:
        Inline stylesheet for the interactive components.

    js:
        Inline vanilla JavaScript used to hydrate the components.
    """

    json_island: str
    css: str
    js: str


def render_json_island(
    payload: Mapping[str, Any],
    *,
    element_id: str = "inquiry-interactive-data",
) -> str:
    """
    Render a safe JSON island for client-side hydration.

    The JSON island allows the assembled HTML paper to carry structured
    component data without requiring a server or external file.
    """

    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")

    if not element_id.strip():
        raise ValueError("element_id must not be empty")

    safe_id = html.escape(element_id, quote=True)

    json_payload = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    # Prevent accidental closing of the script tag inside JSON strings.
    json_payload = json_payload.replace("</", "<\\/")

    return (
        f'<script id="{safe_id}" type="application/json">'
        f"{json_payload}"
        "</script>"
    )


def render_interactive_css() -> str:
    """
    Return inline CSS for Week 9 interactive components.

    Design goals:
    - restrained and readable
    - keyboard focus visible
    - progressive enhancement friendly
    """

    return """
<style>
  .inquiry-controls {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    margin: 1rem 0;
  }

  .inquiry-control {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.95rem;
  }

  .claim-card,
  .evidence-panel,
  .reading-item {
    border: 1px solid rgba(20, 20, 20, 0.18);
    border-radius: 0.75rem;
    padding: 1rem;
    margin: 1rem 0;
    background: #ffffff;
  }

  .claim-card__header,
  .evidence-panel__header {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: flex-start;
  }

  .claim-card__toggle,
  .claim-card__mode,
  .evidence-filter,
  .reading-filter {
    border: 1px solid rgba(20, 20, 20, 0.25);
    border-radius: 999px;
    background: #f8f8f8;
    color: #111111;
    padding: 0.45rem 0.75rem;
    cursor: pointer;
  }

  .claim-card__toggle:hover,
  .claim-card__mode:hover,
  .evidence-filter:hover,
  .reading-filter:hover {
    background: #eeeeee;
  }

  .claim-card__toggle:focus-visible,
  .claim-card__mode:focus-visible,
  .evidence-filter:focus-visible,
  .reading-filter:focus-visible,
  .source-detail-toggle:focus-visible {
    outline: 3px solid #111111;
    outline-offset: 3px;
  }

  .claim-card__details[hidden],
  .claim-card__quote[hidden],
  .claim-card__adjudication[hidden],
  .evidence-record[hidden],
  .reading-item[hidden],
  .source-detail[hidden] {
    display: none;
  }

  .evidence-record {
    border-top: 1px solid rgba(20, 20, 20, 0.12);
    padding-top: 0.75rem;
    margin-top: 0.75rem;
  }

  .source-detail-toggle {
    border: none;
    background: transparent;
    text-decoration: underline;
    cursor: pointer;
    padding: 0;
    color: #111111;
  }

  .inquiry-js-status {
    font-size: 0.9rem;
    color: #333333;
  }

  noscript .noscript-note {
    border: 1px solid rgba(20, 20, 20, 0.25);
    border-radius: 0.75rem;
    padding: 1rem;
    background: #fff8dc;
    color: #111111;
  }
</style>
""".strip()


def render_interactive_js() -> str:
    """
    Return self-contained vanilla JavaScript for Week 9 components.

    Components hydrated:
    - ClaimCard
    - EvidencePanel
    - ReadingList
    """

    return """
<script>
(function () {
  "use strict";

  function setExpanded(button, target, expanded) {
    button.setAttribute("aria-expanded", String(expanded));
    target.hidden = !expanded;
  }

  function hydrateClaimCards(root) {
    var cards = root.querySelectorAll("[data-component='claim-card']");

    cards.forEach(function (card) {
      var toggle = card.querySelector("[data-action='toggle-claim']");
      var details = card.querySelector("[data-claim-details]");

      if (toggle && details) {
        toggle.setAttribute("aria-expanded", "false");
        details.hidden = true;

        toggle.addEventListener("click", function () {
          var expanded = toggle.getAttribute("aria-expanded") === "true";
          setExpanded(toggle, details, !expanded);
        });
      }

      var modeButton = card.querySelector("[data-action='toggle-claim-mode']");
      var quote = card.querySelector("[data-claim-quote]");
      var adjudication = card.querySelector("[data-claim-adjudication]");

      if (modeButton && quote && adjudication) {
        quote.hidden = false;
        adjudication.hidden = true;
        modeButton.setAttribute("aria-pressed", "false");

        modeButton.addEventListener("click", function () {
          var showingAdjudication = modeButton.getAttribute("aria-pressed") === "true";
          var nextShowingAdjudication = !showingAdjudication;

          modeButton.setAttribute("aria-pressed", String(nextShowingAdjudication));
          quote.hidden = nextShowingAdjudication;
          adjudication.hidden = !nextShowingAdjudication;
          modeButton.textContent = nextShowingAdjudication
            ? "Show speaker quote"
            : "Show adjudication";
        });
      }
    });
  }

  function hydrateEvidencePanels(root) {
    var panels = root.querySelectorAll("[data-component='evidence-panel']");

    panels.forEach(function (panel) {
      var stanceSelect = panel.querySelector("[data-filter='evidence-stance']");
      var tierSelect = panel.querySelector("[data-filter='evidence-tier']");
      var records = panel.querySelectorAll("[data-evidence-record]");

      function applyFilters() {
        var stance = stanceSelect ? stanceSelect.value : "all";
        var tier = tierSelect ? tierSelect.value : "all";

        records.forEach(function (record) {
          var recordStance = record.getAttribute("data-stance") || "";
          var recordTier = record.getAttribute("data-tier") || "";

          var stanceMatches = stance === "all" || recordStance === stance;
          var tierMatches = tier === "all" || recordTier === tier;

          record.hidden = !(stanceMatches && tierMatches);
        });
      }

      if (stanceSelect) {
        stanceSelect.addEventListener("change", applyFilters);
      }

      if (tierSelect) {
        tierSelect.addEventListener("change", applyFilters);
      }

      panel.querySelectorAll("[data-action='toggle-source-detail']").forEach(function (button) {
        var targetId = button.getAttribute("aria-controls");
        var target = targetId ? panel.querySelector("#" + CSS.escape(targetId)) : null;

        if (!target) {
          return;
        }

        button.setAttribute("aria-expanded", "false");
        target.hidden = true;

        button.addEventListener("click", function () {
          var expanded = button.getAttribute("aria-expanded") === "true";
          setExpanded(button, target, !expanded);
        });
      });

      applyFilters();
    });
  }

  function hydrateReadingLists(root) {
    var lists = root.querySelectorAll("[data-component='reading-list']");

    lists.forEach(function (list) {
      var topicSelect = list.querySelector("[data-filter='reading-topic']");
      var tierSelect = list.querySelector("[data-filter='reading-tier']");
      var sortSelect = list.querySelector("[data-sort='reading-accessibility']");
      var itemsContainer = list.querySelector("[data-reading-items]");
      var items = Array.prototype.slice.call(list.querySelectorAll("[data-reading-item]"));

      function applyReadingFilters() {
        var topic = topicSelect ? topicSelect.value : "all";
        var tier = tierSelect ? tierSelect.value : "all";

        items.forEach(function (item) {
          var itemTopic = item.getAttribute("data-topic") || "";
          var itemTier = item.getAttribute("data-tier") || "";

          var topicMatches = topic === "all" || itemTopic === topic;
          var tierMatches = tier === "all" || itemTier === tier;

          item.hidden = !(topicMatches && tierMatches);
        });
      }

      function sortReadingItems() {
        if (!itemsContainer || !sortSelect) {
          return;
        }

        if (sortSelect.value !== "open-access-first") {
          return;
        }

        items
          .slice()
          .sort(function (a, b) {
            var aOpen = a.getAttribute("data-open-access") === "true" ? 0 : 1;
            var bOpen = b.getAttribute("data-open-access") === "true" ? 0 : 1;
            return aOpen - bOpen;
          })
          .forEach(function (item) {
            itemsContainer.appendChild(item);
          });
      }

      [topicSelect, tierSelect].forEach(function (select) {
        if (select) {
          select.addEventListener("change", applyReadingFilters);
        }
      });

      if (sortSelect) {
        sortSelect.addEventListener("change", function () {
          sortReadingItems();
          applyReadingFilters();
        });
      }

      sortReadingItems();
      applyReadingFilters();
    });
  }

  function markHydrated(root) {
    var status = root.querySelector("[data-inquiry-js-status]");
    if (status) {
      status.textContent = "Interactive controls enabled.";
    }
  }

  function hydrate() {
    var root = document;
    hydrateClaimCards(root);
    hydrateEvidencePanels(root);
    hydrateReadingLists(root);
    markHydrated(root);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", hydrate);
  } else {
    hydrate();
  }
})();
</script>
""".strip()


def render_interactive_assets(payload: Mapping[str, Any]) -> InteractiveAssets:
    """
    Render all Week 9 interactive assets.
    """

    return InteractiveAssets(
        json_island=render_json_island(payload),
        css=render_interactive_css(),
        js=render_interactive_js(),
    )


def render_no_script_notice() -> str:
    """
    Render a progressive-enhancement notice.

    The document should remain readable without JavaScript, but this notice
    tells readers that filters and toggles require JS.
    """

    return """
<noscript>
  <div class="noscript-note">
    JavaScript is disabled. The paper remains readable, but claim expansion,
    evidence filters, and reading-list sorting are unavailable.
  </div>
</noscript>
""".strip()
