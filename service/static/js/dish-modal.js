(() => {
  const modalEl = document.getElementById("dishDetailsModal");
  if (!modalEl || typeof bootstrap === "undefined") return;

  const titleEl = document.getElementById("dishDetailsTitle");
  const bodyEl = document.getElementById("dishDetailsBody");
  const modal = bootstrap.Modal.getOrCreateInstance(modalEl);

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function addFact(list, label, value) {
    if (!value) return;
    const li = document.createElement("li");
    li.innerHTML = `<strong>${escapeHtml(label)}:</strong> ${escapeHtml(value)}`;
    list.appendChild(li);
  }

  document.addEventListener("click", (event) => {
    const trigger = event.target.closest("[data-dish-modal]");
    if (!trigger) return;
    event.preventDefault();

    titleEl.textContent = trigger.dataset.name || "Блюдо";
    bodyEl.replaceChildren();

    if (trigger.dataset.photo) {
      const img = document.createElement("img");
      img.className = "menu-photo rounded mb-3";
      img.src = trigger.dataset.photo;
      img.alt = trigger.dataset.name || "";
      bodyEl.appendChild(img);
    }

    if (trigger.dataset.description) {
      const p = document.createElement("p");
      p.className = "mb-3";
      p.textContent = trigger.dataset.description;
      bodyEl.appendChild(p);
    }

    const list = document.createElement("ul");
    list.className = "list-unstyled dish-facts mb-0";
    addFact(list, "Выход", trigger.dataset.portion);
    addFact(list, "Состав", trigger.dataset.ingredients);
    addFact(
      list,
      "Калорийность",
      trigger.dataset.calories ? `${trigger.dataset.calories} ккал` : "",
    );
    addFact(list, "Аллергены", trigger.dataset.allergens);
    addFact(
      list,
      "Время приготовления",
      trigger.dataset.cookingTime ? `${trigger.dataset.cookingTime} мин` : "",
    );
    addFact(list, "Цена", trigger.dataset.price ? `${trigger.dataset.price} Br` : "");
    bodyEl.appendChild(list);
    modal.show();
  });
})();
