(function () {
  "use strict";

  /* ---------------------------------------------------------------------
   * Currency auto-conversion
   * Detect visitor's country via free IP geolocation, map to a currency,
   * fetch live USD exchange rates, and convert every [data-usd] price.
   * Falls back silently to USD if anything fails.
   * ------------------------------------------------------------------- */
  var COUNTRY_TO_CCY = {
    US:"USD",GB:"GBP",IE:"EUR",DE:"EUR",FR:"EUR",ES:"EUR",IT:"EUR",NL:"EUR",BE:"EUR",AT:"EUR",
    PT:"EUR",FI:"EUR",GR:"EUR",LU:"EUR",SK:"EUR",SI:"EUR",EE:"EUR",LV:"EUR",LT:"EUR",CY:"EUR",
    MT:"EUR",HR:"EUR",IN:"INR",CA:"CAD",AU:"AUD",NZ:"NZD",SG:"SGD",AE:"AED",SA:"SAR",QA:"QAR",
    KW:"KWD",BH:"BHD",OM:"OMR",PK:"PKR",BD:"BDT",LK:"LKR",NP:"NPR",CN:"CNY",HK:"HKD",TW:"TWD",
    JP:"JPY",KR:"KRW",TH:"THB",VN:"VND",PH:"PHP",MY:"MYR",ID:"IDR",BR:"BRL",MX:"MXN",AR:"ARS",
    CL:"CLP",CO:"COP",PE:"PEN",ZA:"ZAR",NG:"NGN",KE:"KES",EG:"EGP",CH:"CHF",SE:"SEK",NO:"NOK",
    DK:"DKK",PL:"PLN",CZ:"CZK",HU:"HUF",RO:"RON",BG:"BGN",TR:"TRY",RU:"RUB",UA:"UAH",IL:"ILS",
    NP:"NPR",BT:"INR",MM:"MMK",KH:"KHR",LA:"LAK",MN:"MNT",KZ:"KZT",UZ:"UZS"
  };
  var FALLBACK_CCY = "USD";
  var CACHE_KEY = "zera_ccy_v1";

  function fmtMoney(amount, code) {
    try {
      return new Intl.NumberFormat(undefined, {
        style: "currency",
        currency: code,
        maximumFractionDigits: amount >= 1000 ? 0 : 2
      }).format(amount);
    } catch (e) {
      return "$" + Math.round(amount).toLocaleString();
    }
  }

  function applyCurrency(code, rate) {
    var els = document.querySelectorAll("[data-usd]");
    els.forEach(function (el) {
      var usd = parseFloat(el.getAttribute("data-usd"));
      if (isNaN(usd)) return;
      var converted = code === "USD" ? usd : usd * rate;
      var suffix = el.getAttribute("data-suffix") || "";
      el.textContent = fmtMoney(converted, code) + suffix;
    });
    var notes = document.querySelectorAll(".js-currency-note");
    notes.forEach(function (el) {
      if (code === "USD") {
        el.textContent = "Prices shown in USD.";
      } else {
        el.textContent = "Prices auto-converted to " + code + " from USD at today's exchange rate.";
      }
    });
  }

  function initCurrency() {
    if (!document.querySelector("[data-usd]")) return;
    try {
      var cached = sessionStorage.getItem(CACHE_KEY);
      if (cached) {
        var d = JSON.parse(cached);
        applyCurrency(d.code, d.rate);
        return;
      }
    } catch (e) {}

    applyCurrency("USD", 1); // paint USD immediately, upgrade if geo/fx succeed

    fetch("https://ipwho.is/")
      .then(function (r) { return r.json(); })
      .then(function (geo) {
        var cc = geo && geo.country_code;
        var code = COUNTRY_TO_CCY[cc] || FALLBACK_CCY;
        if (code === "USD") {
          try { sessionStorage.setItem(CACHE_KEY, JSON.stringify({ code: "USD", rate: 1 })); } catch (e) {}
          return;
        }
        return fetch("https://open.er-api.com/v6/latest/USD")
          .then(function (r) { return r.json(); })
          .then(function (fx) {
            var rate = fx && fx.rates && fx.rates[code];
            if (!rate) { code = "USD"; rate = 1; }
            applyCurrency(code, rate);
            try { sessionStorage.setItem(CACHE_KEY, JSON.stringify({ code: code, rate: rate })); } catch (e) {}
          });
      })
      .catch(function () { /* stay on USD */ });
  }

  /* ---------------------------------------------------------------------
   * Lead capture form -> Google Apps Script Web App -> Google Sheet
   * ------------------------------------------------------------------- */
  var LEAD_ENDPOINT = "https://script.google.com/macros/s/AKfycbxTaVnmZo4C2s2mFgfWDfK0Xirpc0CofkUfPf2SmZZDf9ZYih-9uZIC3le_LNaVsIHNOQ/exec";

  function initLeadForm() {
    var form = document.getElementById("lead-form");
    if (!form) return;

    // Best-effort country prefill using the same geolocation call.
    var countryField = form.querySelector('[name="country"]');
    if (countryField && !countryField.value) {
      fetch("https://ipwho.is/")
        .then(function (r) { return r.json(); })
        .then(function (geo) {
          if (geo && geo.country) countryField.value = geo.country;
        })
        .catch(function () {});
    }

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var statusEl = document.getElementById("form-status");
      var btn = form.querySelector('button[type="submit"]');
      var data = {
        name: form.name.value.trim(),
        email: form.email.value.trim(),
        phone: form.phone.value.trim(),
        country: form.country.value.trim(),
        service: form.service.value,
        budget: form.budget.value,
        message: form.message.value.trim()
      };

      if (!data.name || !data.email) {
        statusEl.textContent = "Please fill in your name and email.";
        statusEl.className = "form-status err";
        return;
      }

      if (btn) { btn.disabled = true; btn.textContent = "Sending..."; }

      fetch(LEAD_ENDPOINT, {
        method: "POST",
        mode: "no-cors",
        headers: { "Content-Type": "text/plain;charset=utf-8" },
        body: JSON.stringify(data)
      }).then(function () {
        statusEl.textContent = "Thanks! We've received your request and will reply within 24 hours. You can also message us on WhatsApp for a faster response.";
        statusEl.className = "form-status ok";
        form.reset();
        if (btn) { btn.disabled = false; btn.textContent = "Send request"; }
      }).catch(function () {
        statusEl.textContent = "Something went wrong. Please try WhatsApp instead.";
        statusEl.className = "form-status err";
        if (btn) { btn.disabled = false; btn.textContent = "Send request"; }
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initCurrency();
    initLeadForm();
  });
})();
