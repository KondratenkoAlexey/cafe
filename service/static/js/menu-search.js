(() => {
  const input = document.getElementById("menuSearch");
  const select = document.getElementById("menu_item_id");
  if (!input || !select) return;

  const options = Array.from(select.options).map((option) => ({
    value: option.value,
    text: option.textContent,
    search: option.textContent.toLowerCase(),
  }));

  function applyFilter() {
    const query = input.value.trim().toLowerCase();
    const previous = select.value;
    select.innerHTML = "";

    const filtered = query
      ? options.filter((option) => option.search.includes(query))
      : options;

    if (!filtered.length) {
      const empty = document.createElement("option");
      empty.value = "";
      empty.textContent = "Ничего не найдено";
      empty.disabled = true;
      empty.selected = true;
      select.appendChild(empty);
      return;
    }

    filtered.forEach((option, index) => {
      const el = document.createElement("option");
      el.value = option.value;
      el.textContent = option.text;
      if (option.value === previous || (!previous && index === 0)) {
        el.selected = true;
      }
      select.appendChild(el);
    });
  }

  input.addEventListener("input", applyFilter);
})();
