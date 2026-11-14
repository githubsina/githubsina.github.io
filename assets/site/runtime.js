/*
 * Tiny runtime for pages exported from the portfolio design canvas.
 * Each page carries its template (<template id="dc-template">) and its logic
 * (<script type="text/x-dc" id="dc-logic"> class Component extends DCLogic {...}).
 * Supports {{holes}}, <sc-if value>, <sc-for list as>, on* event holes,
 * setState re-renders with an in-place DOM patch (so videos and CSS
 * animations keep running), componentDidMount / componentDidUpdate.
 */
(function () {
  'use strict';

  class DCLogic {
    constructor(props) { this.props = props || {}; this.state = {}; }
    setState(patch) {
      const next = typeof patch === 'function' ? patch(this.state, this.props) : patch;
      this.state = Object.assign({}, this.state, next);
      schedule();
    }
    forceUpdate() { schedule(); }
    renderVals() { return {}; }
  }

  const HOLE = /\{\{\s*([\w$.]+)\s*\}\}/g;
  const ONLY_HOLE = /^\s*\{\{\s*([\w$.]+)\s*\}\}\s*$/;

  function lookup(ctx, path) {
    const parts = path.split('.');
    let v = ctx;
    for (const p of parts) {
      if (v == null) return undefined;
      v = v[p];
    }
    return v;
  }
  function interp(str, ctx) {
    return str.replace(HOLE, (_, p) => {
      const v = lookup(ctx, p);
      return v == null || typeof v === 'function' ? '' : String(v);
    });
  }

  // ---------- render template -> fresh DOM ----------
  function renderChildren(tplParent, ctx, outParent) {
    for (const n of tplParent.childNodes) renderNode(n, ctx, outParent);
  }
  function renderNode(n, ctx, out) {
    if (n.nodeType === 3) { out.appendChild(document.createTextNode(n.nodeValue.indexOf('{{') < 0 ? n.nodeValue : interp(n.nodeValue, ctx))); return; }
    if (n.nodeType !== 1) return;
    const tag = n.localName;
    if (tag === 'sc-if') {
      const slot = document.createElement('dc-if');
      const m = ONLY_HOLE.exec(n.getAttribute('value') || '');
      const v = m ? lookup(ctx, m[1]) : false;
      if (v && !(Array.isArray(v) && !v.length)) renderChildren(n, ctx, slot);
      out.appendChild(slot); return;
    }
    if (tag === 'sc-for') {
      const slot = document.createElement('dc-for');
      const m = ONLY_HOLE.exec(n.getAttribute('list') || '');
      const list = (m && lookup(ctx, m[1])) || [];
      const as = n.getAttribute('as') || 'item';
      list.forEach((item, i) => {
        const c = Object.create(ctx); c[as] = item; c[as + 'Index'] = i;
        renderChildren(n, c, slot);
      });
      out.appendChild(slot); return;
    }
    const el = n.cloneNode(false);
    const handlers = {};
    for (const a of Array.from(n.attributes)) {
      const name = a.name, val = a.value;
      if (name.startsWith('hint-')) { el.removeAttribute(name); continue; }
      if (name.startsWith('on')) {
        const m = ONLY_HOLE.exec(val);
        el.removeAttribute(name);
        if (m) { const fn = lookup(ctx, m[1]); if (typeof fn === 'function') handlers[name.slice(2).toLowerCase()] = fn; }
        continue;
      }
      if (val.indexOf('{{') >= 0) el.setAttribute(name, interp(val, ctx));
    }
    el.__h = handlers;
    if (tag === 'template') { out.appendChild(el); return; }
    renderChildren(n.content ? n.content : n, ctx, el);
    out.appendChild(el);
  }

  // ---------- events: one listener per type, reads node.__h at call time ----------
  const EV = { mouseenter: 'mouseenter', mouseleave: 'mouseleave', focus: 'focus', blur: 'blur' };
  function bind(el) {
    const h = el.__h || {};
    el.__bound = el.__bound || {};
    for (const type in h) {
      if (el.__bound[type]) continue;
      el.__bound[type] = true;
      el.addEventListener(EV[type] || type, (e) => { const f = el.__h && el.__h[type]; if (f) f(e); });
    }
  }
  function bindAll(root) {
    if (root.nodeType === 1) { bind(root); root.querySelectorAll('*').forEach(bind); }
  }

  // ---------- patch existing DOM toward the new DOM ----------
  function sameKind(a, b) {
    return a.nodeType === b.nodeType && (a.nodeType !== 1 || a.namespaceURI === b.namespaceURI && a.localName === b.localName);
  }
  function patchAttrs(from, to) {
    for (const a of Array.from(from.attributes)) if (!to.hasAttribute(a.name)) from.removeAttribute(a.name);
    for (const a of Array.from(to.attributes)) if (from.getAttribute(a.name) !== a.value) from.setAttribute(a.name, a.value);
  }
  function patch(from, to) {
    if (from.nodeType === 3) { if (from.nodeValue !== to.nodeValue) from.nodeValue = to.nodeValue; return; }
    patchAttrs(from, to);
    from.__h = to.__h; bind(from);
    const fc = Array.from(from.childNodes), tc = Array.from(to.childNodes);
    const n = Math.max(fc.length, tc.length);
    for (let i = 0; i < n; i++) {
      const f = fc[i], t = tc[i];
      if (!t) { from.removeChild(f); continue; }
      if (!f) { from.appendChild(t); bindAll(t); continue; }
      if (sameKind(f, t)) patch(f, t);
      else { from.replaceChild(t, f); bindAll(t); }
    }
  }

  // ---------- boot ----------
  let comp = null, root = null, tpl = null, mounted = false, queued = false;
  function vals() {
    const v = comp.renderVals() || {};
    return v;
  }
  function render() {
    queued = false;
    const frag = document.createElement('div');
    renderChildren(tpl.content, vals(), frag);
    if (!mounted) {
      while (frag.firstChild) root.appendChild(frag.firstChild);
      bindAll(root);
      mounted = true;
      afterFirst();
      if (comp.componentDidMount) comp.componentDidMount();
    } else {
      patch(root, cloneShell(root, frag));
      if (comp.componentDidUpdate) comp.componentDidUpdate();
    }
  }
  function cloneShell(rootEl, frag) {
    const shell = rootEl.cloneNode(false);
    while (frag.firstChild) shell.appendChild(frag.firstChild);
    shell.__h = rootEl.__h;
    return shell;
  }
  function schedule() {
    if (!mounted || queued) return;
    queued = true;
    requestAnimationFrame(render);
  }
  function afterFirst() {
    // in-page anchors like #about after the content exists
    if (location.hash.length > 1) {
      const t = document.getElementById(decodeURIComponent(location.hash.slice(1)));
      if (t) setTimeout(() => t.scrollIntoView(), 60);
    }
    document.dispatchEvent(new CustomEvent('dc:mounted'));
  }

  function boot() {
    tpl = document.getElementById('dc-template');
    root = document.getElementById('dc-root');
    const src = document.getElementById('dc-logic').textContent;
    const Component = new Function('DCLogic', src + '\n;return Component;')(DCLogic);
    comp = new Component({});
    if (!comp.state) comp.state = {};
    render();
  }
  window.DCLogic = DCLogic;
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
