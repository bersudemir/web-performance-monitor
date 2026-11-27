"use strict";
const form = document.getElementById("site-form");
form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  const name = document.getElementById("site-name").value.trim();
  if (!name) {
    document.getElementById("site-name").setCustomValidity("Lütfen bir site adı girin.");
    form.reportValidity();
    return;
  }
  const url = document.getElementById("site-url").value;
  const interval = document.getElementById("site-interval").value;
  document.getElementById("preview-content").textContent = `${name} · ${url} · ${interval} dakika. Bu bilgiler yalnızca bu sayfada gösterilir; site listesine eklenmedi.`;
  document.getElementById("form-preview").hidden = false;
});
document.getElementById("site-name").addEventListener("input", (event) => event.target.setCustomValidity(""));
form.addEventListener("input", () => { document.getElementById("form-preview").hidden = true; });
document.getElementById("preview-button").disabled = false;
