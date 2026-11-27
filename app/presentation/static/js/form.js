"use strict";
// Prevent submission until persistence is connected.
document.getElementById("site-form").addEventListener("submit", (event) => {
  event.preventDefault();
});
