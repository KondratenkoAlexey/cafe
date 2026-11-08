(() => {
  const modalEl = document.getElementById("confirmActionModal");
  if (!modalEl || typeof bootstrap === "undefined") return;

  const titleEl = document.getElementById("confirmActionTitle");
  const bodyEl = document.getElementById("confirmActionBody");
  const okBtn = document.getElementById("confirmActionOk");
  const modal = bootstrap.Modal.getOrCreateInstance(modalEl);

  let pendingForm = null;

  function openConfirm(form) {
    pendingForm = form;
    titleEl.textContent = form.dataset.confirmTitle || "Подтвердите действие";
    bodyEl.textContent =
      form.dataset.confirmMessage || "Это действие нельзя будет отменить.";
    okBtn.textContent = form.dataset.confirmButton || "Удалить";
    modal.show();
  }

  document.addEventListener(
    "submit",
    (event) => {
      const form = event.target;
      if (!(form instanceof HTMLFormElement)) return;
      if (!form.dataset.confirmMessage) return;
      if (form.dataset.confirmed === "1") {
        delete form.dataset.confirmed;
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      openConfirm(form);
    },
    true,
  );

  okBtn.addEventListener("click", () => {
    if (!pendingForm) return;
    const form = pendingForm;
    pendingForm = null;
    form.dataset.confirmed = "1";
    modal.hide();
    form.requestSubmit ? form.requestSubmit() : form.submit();
  });

  modalEl.addEventListener("hidden.bs.modal", () => {
    pendingForm = null;
  });
})();
