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
    /* Every enquiry action also sends GA4's recommended lead event,
       so one key event ("generate_lead") counts all enquiries. */
    var LEADS = { whatsapp_click: 'whatsapp', email_click: 'email', quote_form_submit: 'form', discovery_call_click: 'booking' };
    if (LEADS[name]) {
      try { gtag('event', 'generate_lead', { lead_method: LEADS[name], link_location: params.link_location || '', page_path: params.page_path }); } catch (e) {}
    }
  }

  /* ===== 2. Contact prefill ===== */
  var SITE_LABEL = 'Zera Technologies (zeratech.io)';
  var WA_NUMBER = '918893585348';
  var EMAIL = 'hello@zeratech.io';
  var pageName = (document.title || location.pathname).split('|')[0].trim();
  var pageUrl = location.origin + location.pathname;
  var cameFrom = document.referrer ? document.referrer : 'Direct visit / typed URL';
  var root = document.documentElement;
  function region() { return root.classList.contains('r-intl') ? 'intl' : (root.classList.contains('r-in') ? 'in' : ''); }
  var isIndia = root.getAttribute('data-audience') ? root.getAttribute('data-audience') === 'india' : region() !== 'intl';

  function waText(topic) {
    var greet = isIndia ? 'Namaste Zera Technologies,' : 'Hi Zera Technologies,';
    return greet + ' I found you on ' + SITE_LABEL + '.\n' +
      'Page: ' + pageName + ' (' + pageUrl + ')\n' +
      (topic ? 'Interested in: ' + topic + '\n' : '') +
      'I would like to discuss my project.';
  }

  function setWaLinks() {
    document.querySelectorAll('a[href*="wa.me/"]').forEach(function (a) {
      if (a.hasAttribute('data-fixed')) return;
      a.href = 'https://wa.me/' + WA_NUMBER + '?text=' + encodeURIComponent(waText(a.getAttribute('data-topic') || ''));
    });
  }

  /* ===== Region switch: India (₹) / International ($) ===== */
  function initRegion() {
    var btns = document.querySelectorAll('[data-set-region]');
    function paint() {
      var r = region();
      document.querySelectorAll('.region [data-set-region]').forEach(function (b) {
        b.setAttribute('aria-pressed', b.getAttribute('data-set-region') === r ? 'true' : 'false');
      });
    }
    paint();
    btns.forEach(function (b) {
      b.addEventListener('click', function (e) {
        var to = b.getAttribute('data-set-region');
        if (b.tagName === 'A') e.preventDefault();
        try { localStorage.setItem('zt_region', to); } catch (err) {}
        track('region_switch', { region: to, link_location: b.closest('.region') ? 'header' : 'body' });
        var aud = root.getAttribute('data-audience');
        if (aud && (aud === 'india' ? 'in' : 'intl') !== to) {
          location.href = root.getAttribute('data-alt') || '/';
          return;
        }
        if (region() === to) return;
        root.classList.remove('r-in', 'r-intl', 'r-all');
        root.classList.add('r-' + to);
        root.setAttribute('data-region', to);
        isIndia = to === 'in';
        paint();
        setWaLinks();
        var m = document.getElementById('main');
        if (m) { m.classList.remove('region-flash'); void m.offsetWidth; m.classList.add('region-flash'); }
        document.dispatchEvent(new CustomEvent('zt:region', { detail: to }));
      });
    });

    // Single-audience page but the visitor seems to be from the other region: suggest, never force.
    var sug = root.getAttribute('data-suggest');
    var dismissed = false;
    try { dismissed = sessionStorage.getItem('zt_note') === '1'; } catch (err) {}
    if (sug && !dismissed && root.getAttribute('data-alt')) {
      var bar = document.createElement('div');
      bar.className = 'region-note';
      bar.setAttribute('role', 'note');
      bar.innerHTML = '<div class="wrap"><span>' + (sug === 'intl'
        ? 'Outside India? We also build for clients worldwide, with prices in US dollars.'
        : 'In India? See our services with prices in ₹ (GST invoice).') +
        '</span><a href="' + root.getAttribute('data-alt') + '" data-note-go>' + (sug === 'intl' ? 'International site →' : 'India site →') +
        '</a><button type="button" aria-label="Dismiss">×</button></div>';
      var header = document.querySelector('.site-header');
      header.parentNode.insertBefore(bar, header);
      bar.querySelector('[data-note-go]').addEventListener('click', function () {
        try { localStorage.setItem('zt_region', sug); } catch (err) {}
        track('region_switch', { region: sug, link_location: 'suggestion' });
      });
      bar.querySelector('button').addEventListener('click', function () {
        bar.remove();
        try { sessionStorage.setItem('zt_note', '1'); } catch (err) {}
      });
    }
  }

  function init() {
    initRegion();
    document.querySelectorAll('[data-track-book]').forEach(function (a) {
      a.addEventListener('click', function () { track('discovery_call_click', { region: a.getAttribute('data-track-book'), page_path: location.pathname }); });
    });
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
            track('pricing_view', { currency: isIndia ? 'INR' : 'USD', region: region() || 'all' });
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
