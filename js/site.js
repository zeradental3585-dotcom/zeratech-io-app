/* Zera Technologies — shared script for every zeratech.io page.
   1. GA4 (G-YWPLDN029K)
   2. Prefills every WhatsApp + email link with the page the visitor is on
   3. GA4 events: whatsapp_click, email_click, quote_form_submit, pricing_view, portfolio_click
   4. Lead / audit forms -> Google Apps Script -> Google Sheet
   5. Mobile menu, footer year                                                     */
(function () {
  'use strict';

  /* ===== 1. GA4 ===== */
  var GA_ID = 'G-YWPLDN029K';
  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function () { window.dataLayer.push(arguments); };
  var s = document.createElement('script');
  s.async = true;
  s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
  document.head.appendChild(s);
  gtag('js', new Date());
  gtag('config', GA_ID);

  function track(name, params) {
    params = params || {};
    params.page_path = location.pathname;
    try { gtag('event', name, params); } catch (e) {}
  }

  /* ===== 2. Contact prefill ===== */
  var SITE_LABEL = 'Zera Technologies (zeratech.io)';
  var WA_NUMBER = '918893585348';
  var EMAIL = 'hello@zeratech.io';
  var pageName = (document.title || location.pathname).split('|')[0].trim();
  var pageUrl = location.origin + location.pathname;
  var cameFrom = document.referrer ? document.referrer : 'Direct visit / typed URL';
  var isIndia = document.documentElement.getAttribute('data-audience') === 'india';

  function waText(topic) {
    var greet = isIndia ? 'Namaste Zera Technologies,' : 'Hi Zera Technologies,';
    return greet + ' I found you on ' + SITE_LABEL + '.\n' +
      'Page: ' + pageName + ' (' + pageUrl + ')\n' +
      (topic ? 'Interested in: ' + topic + '\n' : '') +
      'I would like to discuss my project.';
  }

  function init() {
    document.querySelectorAll('a[href*="wa.me/"]').forEach(function (a) {
      var topic = a.getAttribute('data-topic') || '';
      a.href = 'https://wa.me/' + WA_NUMBER + '?text=' + encodeURIComponent(waText(topic));
      a.target = '_blank';
      a.rel = 'noopener';
      a.addEventListener('click', function () {
        track('whatsapp_click', { link_location: a.getAttribute('data-loc') || 'body', topic: topic });
      });
    });

    document.querySelectorAll('a[href^="mailto:"]').forEach(function (a) {
      var topic = a.getAttribute('data-topic') || '';
      var subject = 'Project enquiry from ' + SITE_LABEL + (topic ? ' – ' + topic : '');
      var body = 'Hello Zera Technologies,\n\nSite: ' + SITE_LABEL + '\nPage: ' + pageName + ' (' + pageUrl + ')\n' +
        'Came from: ' + cameFrom + '\n\nAbout my project:\n- Business / company:\n- What I need:\n- Budget:\n- Timeline:\n\nThanks,';
      a.href = 'mailto:' + EMAIL + '?subject=' + encodeURIComponent(subject) + '&body=' + encodeURIComponent(body);
      a.addEventListener('click', function () {
        track('email_click', { link_location: a.getAttribute('data-loc') || 'body', topic: topic });
      });
    });

    /* ===== 3. Other events ===== */
    document.querySelectorAll('[data-portfolio]').forEach(function (el) {
      el.addEventListener('click', function () {
        track('portfolio_click', { project: el.getAttribute('data-portfolio') });
      });
    });

    var pricing = document.querySelectorAll('[data-track="pricing"]');
    if (pricing.length && 'IntersectionObserver' in window) {
      var seen = false;
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (en.isIntersecting && !seen) {
            seen = true;
            track('pricing_view', { currency: isIndia ? 'INR' : 'USD' });
            io.disconnect();
          }
        });
      }, { threshold: 0.3 });
      pricing.forEach(function (p) { io.observe(p); });
    }

    /* ===== 4. Lead forms ===== */
    var LEAD_ENDPOINT = 'https://script.google.com/macros/s/AKfycbxTaVnmZo4C2s2mFgfWDfK0Xirpc0CofkUfPf2SmZZDf9ZYih-9uZIC3le_LNaVsIHNOQ/exec';

    document.querySelectorAll('form[data-quote-form]').forEach(function (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var statusEl = form.querySelector('.form-status');
        var btn = form.querySelector('button[type="submit"]');
        var label = btn ? btn.textContent : 'Send';
        var data = {};
        Array.prototype.forEach.call(form.elements, function (el) {
          if (el.name) data[el.name] = (el.value || '').trim();
        });
        // Sheet columns: name, email, phone, country, service, budget, message
        if (data.website) data.message = 'Website to audit: ' + data.website + '\n' + (data.message || '');
        data.message = (data.message || '') + '\n[Page: ' + pageUrl + ']';
        delete data.website;

        if (!data.name || (!data.email && !data.phone)) {
          statusEl.textContent = 'Please add your name and an email or WhatsApp number.';
          statusEl.className = 'form-status err';
          return;
        }
        if (btn) { btn.disabled = true; btn.textContent = 'Sending…'; }

        fetch(LEAD_ENDPOINT, {
          method: 'POST',
          mode: 'no-cors',
          headers: { 'Content-Type': 'text/plain;charset=utf-8' },
          body: JSON.stringify(data)
        }).then(function () {
          statusEl.textContent = 'Thank you! Your request has reached us. For a faster reply, message on WhatsApp too.';
          statusEl.className = 'form-status ok';
          track('quote_form_submit', { form: form.getAttribute('data-quote-form') || 'quote', service: data.service || '' });
          form.reset();
        }).catch(function () {
          statusEl.textContent = 'Something went wrong. Please message us on WhatsApp instead.';
          statusEl.className = 'form-status err';
        }).then(function () {
          if (btn) { btn.disabled = false; btn.textContent = label; }
        });
      });
    });

    /* ===== 5. Mobile menu + year ===== */
    var btnMenu = document.querySelector('.menu-btn');
    var nav = document.getElementById('nav');
    if (btnMenu && nav) {
      btnMenu.addEventListener('click', function () {
        var open = nav.classList.toggle('open');
        btnMenu.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
    }
    document.querySelectorAll('[data-year]').forEach(function (el) { el.textContent = new Date().getFullYear(); });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
