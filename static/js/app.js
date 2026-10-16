(function () {
  "use strict";

  /* ---------- sidebar toggle ---------- */
  var body = document.body;
  var toggle = document.getElementById("menu-toggle");
  var backdrop = document.getElementById("sidebar-backdrop");

  function setNav(open) {
    body.classList.toggle("nav-open", open);
    if (toggle) {
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    }
  }

  if (toggle) {
    toggle.addEventListener("click", function () {
      setNav(!body.classList.contains("nav-open"));
    });
  }
  if (backdrop) {
    backdrop.addEventListener("click", function () {
      setNav(false);
    });
  }
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      setNav(false);
    }
  });
  window.addEventListener("resize", function () {
    if (window.innerWidth > 900) {
      setNav(false);
    }
  });

  /* ---------- dismissible alerts ---------- */
  var closeButtons = document.querySelectorAll(".alert-close");
  for (var i = 0; i < closeButtons.length; i++) {
    closeButtons[i].addEventListener("click", function (event) {
      var alertBox = event.currentTarget.closest(".alert");
      if (alertBox) {
        alertBox.remove();
      }
    });
  }

  /* ---------- order-item form: price autofill and line total ---------- */
  var form = document.querySelector('form[data-entity="order-items"]');
  if (!form) {
    return;
  }

  var priceSource = form.querySelector("select[data-price-source]");
  var priceTarget = form.querySelector("input[data-price-target]");
  var qtyInput = form.querySelector('[name="Quantity"]');
  var discountInput = form.querySelector('[name="Discount"]');
  var preview = document.getElementById("line-total-preview");

  function fillPrice(onlyIfEmpty) {
    if (!priceSource || !priceTarget) {
      return;
    }
    var option = priceSource.options[priceSource.selectedIndex];
    if (!option || !option.getAttribute("data-price")) {
      return;
    }
    var autofill = priceSource.getAttribute("data-autofill") === "true";
    var empty = priceTarget.value.trim() === "";
    if (empty || (autofill && !onlyIfEmpty)) {
      var price = parseFloat(option.getAttribute("data-price"));
      if (!isNaN(price)) {
        priceTarget.value = price.toFixed(2);
      }
    }
  }

  function formatMoney(symbol, value) {
    var fixed = value.toFixed(2);
    var parts = fixed.split(".");
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    return symbol + parts.join(".");
  }

  function updateTotal() {
    if (!preview) {
      return;
    }
    var symbol = preview.getAttribute("data-symbol") || "";
    var qtyText = qtyInput ? qtyInput.value.trim() : "";
    var priceText = priceTarget ? priceTarget.value.trim() : "";
    var discountText = discountInput ? discountInput.value.trim() : "";

    var qty = Number(qtyText);
    var price = Number(priceText);
    var discount = discountText === "" ? 0 : Number(discountText);

    var invalid =
      qtyText === "" || priceText === "" ||
      isNaN(qty) || isNaN(price) || isNaN(discount) ||
      qty <= 0 || price <= 0 || discount < 0 || discount > 100;

    if (invalid) {
      preview.textContent = "\u2014";
      return;
    }
    var total = Math.round(qty * price * (100 - discount)) / 100;
    preview.textContent = formatMoney(symbol, total);
  }

  if (priceSource) {
    priceSource.addEventListener("change", function () {
      fillPrice(false);
      updateTotal();
    });
  }

  var calcInputs = form.querySelectorAll("input[data-calc]");
  for (var j = 0; j < calcInputs.length; j++) {
    calcInputs[j].addEventListener("input", updateTotal);
  }

  fillPrice(true);
  updateTotal();
})();

(function () {
  "use strict";
  var btn = document.querySelector("[data-pw-toggle]");
  var input = document.getElementById("password");
  if (!btn || !input) {
    return;
  }
  btn.addEventListener("click", function () {
    var show = input.type === "password";
    input.type = show ? "text" : "password";
    btn.setAttribute("aria-pressed", show ? "true" : "false");
    btn.setAttribute("aria-label", show ? "Hide password" : "Show password");
    btn.classList.toggle("is-on", show);
    input.focus();
  });
})();