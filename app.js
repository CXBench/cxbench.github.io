"use strict";

const video = document.querySelector("#intro-video");
const videoFrame = document.querySelector(".video-frame");
video.controls = false;
videoFrame.classList.add("has-start");
document.querySelector(".video-start").addEventListener("click", async () => {
  video.controls = true;
  videoFrame.classList.remove("has-start");
  video.focus();
  try {
    await video.play();
  } catch {
    // Native controls remain available if playback is interrupted or deferred.
  }
});

const menu = document.querySelector(".menu-toggle");
const navigation = document.querySelector("#navigation");
function closeMenu() {
  menu.setAttribute("aria-expanded", "false");
  menu.setAttribute("aria-label", "Open navigation");
  navigation.classList.remove("open");
}
menu.addEventListener("click", () => {
  const open = menu.getAttribute("aria-expanded") !== "true";
  menu.setAttribute("aria-expanded", String(open));
  menu.setAttribute(
    "aria-label",
    open ? "Close navigation" : "Open navigation",
  );
  navigation.classList.toggle("open", open);
});
navigation.addEventListener("click", (event) => {
  if (event.target.closest("a")) closeMenu();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && navigation.classList.contains("open")) {
    closeMenu();
    menu.focus();
  }
});

const figures = {
  example: {
    file: "figure1",
    number: 1,
    caption: "Two traces with the same final state.",
    alt: "Two dispute-filing traces with the same final state; the second omits the required written-confirmation notice.",
    note: "In the banking example, the written-confirmation disclosure follows Regulation E when applicable. Draft confirmation is a separate CXBench runtime control.",
  },
  pipeline: {
    file: "figure2",
    number: 2,
    caption: "The CXBench evaluation pipeline.",
    alt: "The customer simulator and agent interact with a task environment, mediated runtime, and tools; the resulting trace and final state feed separate outcome and hybrid process graders.",
    note: "The simulator supplies customer facts and confirmations. The runtime checks the confirmation fields before submission; the grader then evaluates the recorded execution.",
  },
  grading: {
    file: "figure3",
    number: 3,
    caption: "From regulatory requirements to process evaluation.",
    alt: "Cited statute, rule card, required trace event, and grader condition, followed by the conjunction of deterministic rules and a semantic trace judge.",
    note: "Formal process verdicts require both deterministic hard rules and the LLM judge to pass. The source figure illustrates how a missing disclosure yields a false-pass despite a correct outcome.",
  },
  task: {
    file: "figure4",
    number: 4,
    caption: "Task specification, tools, and grading configuration.",
    alt: "An executable task specification with customer goals, business states, tool interfaces, confirmation fields, and grading requirements.",
    note: "Each task packages its customer context, allowed tools, initial business state, confirmation contract, and outcome and process requirements.",
  },
};

function connectTabs(selector, activate) {
  const tabs = Array.from(document.querySelectorAll(selector));
  function select(tab) {
    for (const item of tabs) {
      item.setAttribute("aria-selected", String(item === tab));
      item.tabIndex = item === tab ? 0 : -1;
    }
    activate(tab);
  }
  for (const tab of tabs) {
    tab.addEventListener("click", () => select(tab));
    tab.addEventListener("keydown", (event) => {
      let next = tabs.indexOf(tab);
      if (["ArrowRight", "ArrowDown"].includes(event.key)) next++;
      else if (["ArrowLeft", "ArrowUp"].includes(event.key)) next--;
      else if (event.key === "Home") next = 0;
      else if (event.key === "End") next = tabs.length - 1;
      else return;
      event.preventDefault();
      const target = tabs[(next + tabs.length) % tabs.length];
      select(target);
      target.focus();
    });
  }
}

connectTabs("[data-figure]", (tab) => {
  const figure = figures[tab.dataset.figure];
  const image = document.querySelector("#framework-image");
  image.src = `assets/figures/${figure.file}.webp`;
  image.alt = `Paper Figure ${figure.number}: ${figure.alt}`;
  image.removeAttribute("width");
  image.removeAttribute("height");
  const link = document.querySelector("#framework-image-link");
  link.href = image.src;
  link.dataset.caption = `Figure ${figure.number}. ${figure.caption}`;
  const number = document.createElement("strong");
  number.textContent = `Figure ${figure.number}.`;
  document
    .querySelector("#framework-caption")
    .replaceChildren(number, ` ${figure.caption}`);
  document.querySelector("#framework-pdf").href =
    `assets/figures/${figure.file}.pdf`;
  document.querySelector("#framework-note").textContent = figure.note;
  document
    .querySelector("#framework-panel")
    .setAttribute("aria-labelledby", tab.id);
});
connectTabs("[data-result]", (tab) => {
  for (const panel of document.querySelectorAll(".result-panel")) {
    panel.hidden = panel.id !== tab.getAttribute("aria-controls");
  }
});

const dialog = document.querySelector("#figure-dialog");
const canvas = document.querySelector(".dialog-canvas");
const zoom = document.querySelector("#figure-zoom");
let figureTrigger;
function resetZoom() {
  canvas.classList.remove("zoomed");
  zoom.setAttribute("aria-pressed", "false");
  zoom.textContent = "Zoom in";
  canvas.scrollTo(0, 0);
}
for (const link of document.querySelectorAll("[data-lightbox]")) {
  link.addEventListener("click", (event) => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey)
      return;
    event.preventDefault();
    figureTrigger = link;
    document.querySelector("#dialog-image").src = link.href;
    document.querySelector("#dialog-image").alt = link.querySelector("img").alt;
    document.querySelector("#dialog-caption").textContent =
      link.dataset.caption;
    document.querySelector("#figure-download").href = link.href;
    resetZoom();
    dialog.showModal();
    document.querySelector("#figure-close").focus();
  });
}
zoom.addEventListener("click", () => {
  const zoomed = canvas.classList.toggle("zoomed");
  zoom.setAttribute("aria-pressed", String(zoomed));
  zoom.textContent = zoomed ? "Fit to window" : "Zoom in";
});
document
  .querySelector("#figure-close")
  .addEventListener("click", () => dialog.close());
dialog.addEventListener("click", (event) => {
  if (event.target !== dialog) return;
  const bounds = dialog.getBoundingClientRect();
  if (
    event.clientX < bounds.left ||
    event.clientX > bounds.right ||
    event.clientY < bounds.top ||
    event.clientY > bounds.bottom
  )
    dialog.close();
});
dialog.addEventListener("close", () => figureTrigger?.focus());

const copyButton = document.querySelector("#copy-citation");
copyButton.addEventListener("click", async () => {
  const citation = document.querySelector("#citation");
  try {
    await navigator.clipboard.writeText(citation.textContent);
    copyButton.textContent = "Copied";
    document.querySelector("#copy-status").textContent =
      "Citation copied to clipboard.";
  } catch {
    const range = document.createRange();
    range.selectNodeContents(citation);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    copyButton.textContent = "Selected";
    document.querySelector("#copy-status").textContent =
      "Citation selected. Use your keyboard to copy.";
  }
  window.setTimeout(() => {
    copyButton.textContent = "Copy";
  }, 2500);
});
