// Ownership the user asked for since the page was loaded, by entry identifier.
// Sent to Python in full at each click, so a click whose event is coalesced
// with the next one is not lost.
const desiredOwnership = {};

const MARKABLE_STATES = new Set(["missing", "owned"]);

export default function (component) {
  const { data, parentElement, setStateValue } = component;

  let root = parentElement.querySelector(".pokemon-grid-root");
  if (!root) {
    root = document.createElement("div");
    root.className = "pokemon-grid-root";
    parentElement.appendChild(root);
  }
  root.replaceChildren(...data.groups.map((group) => renderGroup(group, data.icon_base_url)));

  root.onclick = (event) => {
    const tile = event.target.closest(".tile.markable");
    if (!tile) {
      return;
    }
    const isOwned = !tile.classList.contains("state-owned");
    desiredOwnership[tile.dataset.entryId] = isOwned;
    applyState(tile, isOwned ? "owned" : "missing");
    setStateValue("desired_ownership", { ...desiredOwnership });
  };
}

function renderGroup(group, iconBaseUrl) {
  const groupElement = document.createElement("section");

  const header = document.createElement("div");
  header.className = "region-header";
  header.append(
    createText("span", "region-title", group.title),
    createText("span", "region-summary", group.summary),
  );
  groupElement.appendChild(header);

  for (const section of group.sections) {
    if (section.title) {
      groupElement.appendChild(createText("div", "section-title", section.title));
    }
    const tiles = document.createElement("div");
    tiles.className = "tiles";
    tiles.append(...section.entries.map((entry) => renderTile(entry, iconBaseUrl)));
    groupElement.appendChild(tiles);
  }
  return groupElement;
}

function renderTile(entry, iconBaseUrl) {
  const tile = document.createElement("div");
  tile.dataset.entryId = entry.id;
  tile.title = `#${entry.dex} ${entry.name}`;

  if (entry.icon) {
    const image = document.createElement("img");
    image.src = `${iconBaseUrl}/${entry.icon}`;
    image.alt = entry.name;
    image.loading = "lazy";
    tile.appendChild(image);
  } else {
    tile.appendChild(createText("div", "no-icon", "?"));
  }
  tile.appendChild(createText("span", "dex-number", `#${entry.dex}`));

  let state = entry.state;
  // A click not yet reflected in the data Python sent keeps its effect.
  if (MARKABLE_STATES.has(state) && entry.id in desiredOwnership) {
    state = desiredOwnership[entry.id] ? "owned" : "missing";
  }
  applyState(tile, state);
  return tile;
}

function applyState(tile, state) {
  tile.className = `tile state-${state}`;
  if (MARKABLE_STATES.has(state)) {
    tile.classList.add("markable");
  }
}

function createText(tagName, className, text) {
  const element = document.createElement(tagName);
  element.className = className;
  element.textContent = text;
  return element;
}
