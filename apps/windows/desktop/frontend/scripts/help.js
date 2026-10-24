/* 固定离线帮助内容；不读取数据库、用户文件或网络。 */
(() => {
  'use strict';
  const content = window.PDM_HELP_CONTENT;
  const page = document.getElementById('page-help');
  if (!page || !content) return;
  let tab = 'manual';
  let chapter = content.chapters[0].id;
  let licenseDocument = 'home';
  const licenseScroll = new Map();
  const escape = (value) => String(value).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
  const labels = {
    zh: {manual:'使用手册',terms:'开源许可',about:'关于',licenses:'第三方许可',contents:'手册目录',image:'操作示例',next:'下一章',previous:'上一章',contact:'打开交流群，联系管理员',back:'返回',agpl:'许可证全文',openssl:'OpenSSL 附加许可',notices:'第三方声明'},
    en: {manual:'User Guide',terms:'Open-source license',about:'About',licenses:'Third-party licenses',contents:'Guide contents',image:'Example',next:'Next',previous:'Previous',contact:'Open the group to contact an administrator',back:'Back',agpl:'Full license',openssl:'OpenSSL permission',notices:'Third-party notices'},
  };
  const licenseText = (value) => `<pre>${escape(value)}</pre>`;
  function licenseView(lang) {
    const copy = labels[lang];
    if (licenseDocument === 'home') return { title: copy.terms, body:
      `<p>${lang === 'zh' ? '小仓' : 'Cangoo'} · ${escape(content.version)}</p>${content.terms[lang]}<div class="help-license-links">` +
      [['agpl', copy.agpl], ['openssl', copy.openssl], ['third-party', copy.notices]].map(([id, label]) =>
        `<button type="button" class="btn btn-ghost" data-help-license-document="${id}">${label}</button>`).join('') + '</div>' };
    if (licenseDocument === 'third-party') return { title: copy.notices, body:
      `${content.licenseIntro[lang]}<div class="help-license-list">${content.licenses.map((entry, index) =>
        `<button type="button" class="btn btn-ghost" data-help-license-document="third-party/${index}">${escape(entry.name)}</button>`).join('')}</div>` };
    if (licenseDocument.startsWith('third-party/')) {
      const entry = content.licenses[Number(licenseDocument.split('/')[1])];
      return { title: entry.name, body: licenseText(entry.text) };
    }
    const document = content.license_documents[licenseDocument];
    return { title: document.title[lang], body: `<p>${escape(document.intro[lang])}</p>${licenseText(document.text)}` };
  }
  function openLicenseDocument(next) {
    const item = /^third-party\/(0|[1-9]\d{0,2})$/.exec(next);
    if (tab !== 'terms' || !(['home', 'agpl', 'openssl', 'third-party'].includes(next) || item && Number(item[1]) < content.licenses.length) || next === licenseDocument) return;
    const reader = page.querySelector('[data-help-license-reader]');
    if (!reader) return;
    const previous = licenseDocument;
    licenseScroll.set(previous, reader.scrollTop);
    licenseDocument = next;
    const view = licenseView(state.lang === 'en' ? 'en' : 'zh');
    page.querySelector('[data-help-license-title]').textContent = view.title;
    page.querySelector('[data-help-license-back]').disabled = next === 'home';
    reader.setAttribute('aria-label', view.title);
    reader.dataset.helpLicenseCurrent = licenseDocument;
    reader.innerHTML = view.body;
    reader.scrollTop = licenseScroll.get(next) ?? 0;
    const returnButton = (next === 'home' || next === 'third-party')
      ? reader.querySelector(`[data-help-license-document="${previous}"]`) : null;
    (returnButton || reader).focus({preventScroll: true});
  }
  window.selectHelp = (nextTab, nextChapter) => {
    if (nextTab && !['manual', 'terms', 'about'].includes(nextTab)) return;
    if (nextChapter && !content.chapters.some((item) => item.id === nextChapter)) return;
    if (nextTab && nextTab !== tab) { licenseDocument = 'home'; licenseScroll.clear(); }
    if (nextTab) tab = nextTab;
    if (nextChapter) chapter = nextChapter;
    window.renderHelp();
  };
  window.renderHelp = () => {
    const lang = state.lang === 'en' ? 'en' : 'zh';
    const copy = labels[lang];
    const active = document.activeElement;
    const focusTab = active?.dataset?.helpTab;
    const focusChapter = active?.dataset?.helpChapter;
    const focusLicenses = active?.id === 'help-licenses-toggle';
    const focusContact = active?.hasAttribute?.('data-pdm-contact');
    const focusUpdate = page.contains(active) ? active?.dataset?.updateAction : '';
    const focusRelease = active?.matches?.('.update-release summary');
    const releaseOpen = Boolean(page.querySelector('.update-release[open]'));
    const licensesOpen = Boolean(page.querySelector('.help-licenses[open]'));
    const previousReader = page.querySelector('[data-help-license-reader]');
    if (previousReader) licenseScroll.set(previousReader.dataset.helpLicenseCurrent, previousReader.scrollTop);
    const tabs = ['manual', 'terms', 'about'].map((key) =>
      `<button type="button" class="help-tab ${key === tab ? 'active' : ''}" data-help-tab="${key}" aria-pressed="${key === tab}">${copy[key]}</button>`,
    ).join('');
    let body;
    const contact = `<button type="button" class="btn btn-ghost" data-pdm-contact>${copy.contact}</button><p id="help-contact-status" role="status" aria-live="polite"></p>`;
    if (tab === 'manual') {
      const item = content.chapters.find((entry) => entry.id === chapter);
      const index = content.chapters.indexOf(item);
      const menu = content.chapters.map((entry, n) =>
        `<button type="button" data-help-chapter="${entry.id}" ${entry.id === chapter ? 'aria-current="page" class="active"' : ''}>${n + 1}. ${escape(entry.title[lang])}</button>`,
      ).join('');
      const picture = item.image ? `<figure><img src="assets/help/${item.image}_${lang}.png" alt="${escape(item.title[lang])}" loading="lazy"><figcaption>${copy.image}</figcaption></figure>` : '';
      const previous = index ? `<button type="button" class="btn btn-ghost" data-help-chapter="${content.chapters[index - 1].id}">${copy.previous}</button>` : '';
      const next = index < content.chapters.length - 1 ? `<button type="button" class="btn btn-ghost" data-help-chapter="${content.chapters[index + 1].id}">${copy.next}</button>` : '';
      body = `<div class="help-layout"><nav class="help-contents" aria-label="${copy.contents}">${menu}</nav><article class="help-article" tabindex="0" aria-label="${escape(item.title[lang])}"><h2>${escape(item.title[lang])}</h2>${item.body[lang]}${picture}<div class="help-pagination">${previous}${next}</div></article></div>`;
    } else if (tab === 'terms') {
      const view = licenseView(lang);
      body = `<section class="help-license-view"><div class="help-license-toolbar"><button type="button" class="btn btn-ghost" data-help-license-back ${licenseDocument === 'home' ? 'disabled' : ''}>${copy.back}</button><h2 data-help-license-title>${escape(view.title)}</h2></div><article class="help-article" data-help-license-reader data-help-license-current="${licenseDocument}" tabindex="0" aria-label="${escape(view.title)}">${view.body}</article></section>`;
    } else {
      const notices = content.licenses.map((license) => `<h3>${escape(license.name)}</h3>${licenseText(license.text)}`).join('');
      body = `<article class="help-article" tabindex="0" aria-label="${copy.about}">${content.about[lang].replace('{version}', escape(content.version)).replace('{author}', escape(content.author))}<section class="help-updates" data-update-panel="about"></section>${contact}<details class="help-licenses" ${licensesOpen ? 'open' : ''}><summary id="help-licenses-toggle" tabindex="0">${copy.licenses}</summary>${content.licenseIntro[lang]}${notices}</details></article>`;
    }
    page.innerHTML = `<div class="help-tabs" role="group" aria-label="${lang === 'zh' ? '帮助栏目' : 'Help sections'}">${tabs}</div>${body}`;
    const reader = page.querySelector('[data-help-license-reader]');
    if (reader) reader.scrollTop = licenseScroll.get(licenseDocument) ?? 0;
    window.renderUpdates?.();
    const release = page.querySelector('.update-release');
    if (release) release.open = releaseOpen;
    const selector = focusTab ? `[data-help-tab="${focusTab}"]` : focusChapter ? `[data-help-chapter="${focusChapter}"]` : focusLicenses ? '#help-licenses-toggle' : focusContact ? '[data-pdm-contact]' : focusUpdate ? `[data-update-action="${focusUpdate}"]` : focusRelease ? '.update-release summary' : null;
    if (selector) page.querySelector(selector)?.focus({preventScroll:true});
  };
  page.addEventListener('click', (event) => {
    const documentButton = event.target.closest('[data-help-license-document],[data-help-license-back]');
    if (documentButton) {
      if (!documentButton.disabled) openLicenseDocument(documentButton.hasAttribute('data-help-license-back')
        ? licenseDocument.startsWith('third-party/') ? 'third-party' : 'home' : documentButton.dataset.helpLicenseDocument);
      return;
    }
    if (event.target.closest('[data-pdm-contact]') && document.body.classList.contains('design-host')) {
      page.querySelector('#help-contact-status').textContent = state.lang === 'en'
        ? 'Demo: the app contact action requests opening the group.'
        : '演示：正式应用的联系入口会请求打开交流群。';
      return;
    }
    const button = event.target.closest('[data-help-tab],[data-help-chapter]');
    if (!button || button.disabled || button.dataset.pdmM4Disabled === 'true') return;
    window.selectHelp(button.dataset.helpTab, button.dataset.helpChapter);
  });
  window.renderHelp();
  // 仅设计页提供已有截图工具的固定场景，正式产品不读取这些参数。
  if (document.body.classList.contains('design-host')) {
    const preview = new URLSearchParams(location.search).get('visual-state');
    if (preview === 'help-zh' || preview === 'help-en') {
      setLang(preview === 'help-en' ? 'en' : 'zh');
      navigateTo('help');
      window.selectHelp('manual', 'backup');
    }
  }
})();
