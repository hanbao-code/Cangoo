/* 备份与设备发送共用的记录选择页；数据和已选集合由调用方持有。 */
(() => {
  'use strict';
  const TEXT = {
    ZH: {title:'选择记录',search:'搜索密码或记事',all:'全部',passwords:'密码',notes:'记事',
      selectAll:'全选当前筛选',unselectAll:'取消全选',clear:'清除全部选择',empty:'没有符合条件的记录',cancel:'取消',done:'完成',
      previous:'上一页',next:'下一页',limit:'搜索内容不能超过128个字符或包含空字符。',
      loading:'正在读取记录…',failure:'无法读取或更新选择，请重试。',expired:'选择已失效，请返回后重新选择。',
      changed:'所选记录有变化，已移出当前选择，请重新核对。',
      count:(passwords,notes) => `密码 ${passwords} · 记事 ${notes}`,page:(first,last,total) => `${first}–${last} / ${total}`},
    EN: {title:'Choose records',search:'Search passwords or notes',all:'All',passwords:'Passwords',notes:'Notes',
      selectAll:'Select all filtered',unselectAll:'Deselect all',clear:'Clear all selections',empty:'No matching records',cancel:'Cancel',done:'Done',
      previous:'Previous',next:'Next',limit:'Use up to 128 characters without null characters.',
      loading:'Loading records…',failure:'Could not read or update this selection. Try again.',expired:'This selection expired. Go back and choose again.',
      changed:'Changed records were removed from this selection. Review your choices.',
      count:(passwords,notes) => `${passwords} passwords · ${notes} notes`,page:(first,last,total) => `${first}–${last} / ${total}`},
  };
  function counts(items) {
    if (!Array.isArray(items)) return {passwordCount:items?.passwordCount || 0,noteCount:items?.noteCount || 0};
    return {passwordCount:items.filter(item => item.kind === 'PASSWORD').length,
      noteCount:items.filter(item => item.kind === 'NOTE').length};
  }
  function create(container,onAction,language = 'ZH') {
    let w = TEXT[language === 'EN' ? 'EN' : 'ZH'];
    const returnFocus = document.activeElement;
    const suspended = [...container.children].map(node => [node,node.inert]);
    suspended.forEach(([node]) => { node.inert = true; node.classList.add('export-selection-background'); });
    const root = document.createElement('section'); root.className = 'export-selection';
    root.setAttribute('aria-label',w.title);
    root.innerHTML = `<header class="modal-header"><h2 class="modal-title"></h2></header>
      <div class="export-selection-tools"><input type="search" class="modal-field-input" autocomplete="off" spellcheck="false">
        <div class="export-selection-filter-row"><div class="segment" role="group">
          <button type="button" data-export-kind="ALL"></button><button type="button" data-export-kind="PASSWORD"></button><button type="button" data-export-kind="NOTE"></button>
        </div><div class="export-selection-tools-actions"><button type="button" class="btn btn-sm" data-export-action="all"></button><button type="button" class="btn btn-sm btn-ghost" data-export-action="clear"></button></div></div>
        <p class="export-selection-feedback" role="status" aria-live="polite"></p></div>
      <div class="export-selection-list" role="list"></div><p class="export-selection-empty" hidden></p>
      <div class="export-selection-pager"><span></span><button type="button" class="btn btn-sm" data-export-action="previous"></button><button type="button" class="btn btn-sm" data-export-action="next"></button></div>
      <footer class="modal-footer"><strong class="export-selection-count" role="status" aria-live="polite"></strong><div class="modal-footer-right"><button type="button" class="btn btn-sm" data-export-action="cancel"></button><button type="button" class="btn btn-primary btn-sm" data-export-action="done"></button></div></footer>`;
    container.append(root);
    const input = root.querySelector('input');
    input.dataset.pdmNativeFocusKey = 'export-selection:search';
    const list = root.querySelector('.export-selection-list');
    const empty = root.querySelector('.export-selection-empty');
    const feedback = root.querySelector('.export-selection-feedback');
    const buttons = Object.fromEntries([...root.querySelectorAll('[data-export-action]')].map(node => [node.dataset.exportAction,node]));
    root.querySelectorAll('[data-export-kind]').forEach(node => { node.dataset.pdmNativeFocusKey = `export-selection:kind:${node.dataset.exportKind}`; });
    Object.entries(buttons).forEach(([action,node]) => { node.dataset.pdmNativeFocusKey = `export-selection:action:${action}`; });
    const rows = new Map();
    let state = null, alive = true, requestedQuery = null;
    function labels() {
      root.setAttribute('aria-label',w.title); root.querySelector('h2').textContent = w.title;
      input.placeholder = w.search; input.setAttribute('aria-label',w.search);
      root.querySelector('.segment').setAttribute('aria-label',w.all);
      for (const [kind,key] of [['ALL','all'],['PASSWORD','passwords'],['NOTE','notes']]) root.querySelector(`[data-export-kind="${kind}"]`).textContent = w[key];
      for (const [action,key] of [['all','selectAll'],['clear','clear'],['previous','previous'],['next','next'],['cancel','cancel'],['done','done']]) buttons[action].textContent = w[key];
      empty.textContent = w.empty;
    }
    labels();
    function validQuery() {
      const valid = Array.from(input.value).length <= 128 && !input.value.includes('\0');
      input.setAttribute('aria-invalid',String(!valid)); feedback.textContent = valid ? state?.error || state?.notice || '' : w.limit;
      return valid;
    }
    function query(event) {
      if (event?.isComposing || !state || !validQuery()) return;
      requestedQuery = {query:input.value,kind:requestedQuery.kind};
      onAction('query',{...requestedQuery});
    }
    function click(event) {
      const button = event.target.closest('button');
      if (!state || !button || !root.contains(button) || button.disabled) return;
      if (button.dataset.exportKind && validQuery()) {
        requestedQuery = {query:input.value,kind:button.dataset.exportKind};
        onAction('query',{...requestedQuery});
      }
      else if (button.dataset.exportAction && (button.dataset.exportAction !== 'all' || validQuery())) onAction(button.dataset.exportAction);
    }
    function key(event) {
      if (event.isComposing) return;
      if (event.key === 'Escape') { event.preventDefault(); event.stopImmediatePropagation(); onAction('cancel'); }
      if (event.key !== 'Tab') return;
      const targets = [...root.querySelectorAll('input:not(:disabled),button:not(:disabled)')].filter(node => node.getClientRects().length);
      const first = targets[0], last = targets.at(-1);
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    }
    root.addEventListener('click',click); root.addEventListener('keydown',key);
    input.addEventListener('input',query); input.addEventListener('compositionend',query);
    input.focus({preventScroll:true});
    return {
      project(value) {
        if (!alive) return;
        if (!requestedQuery) requestedQuery = {query:value.query,kind:value.kind};
        state = value;
        if (document.activeElement !== input) input.value = requestedQuery.query;
        validQuery();
        root.querySelectorAll('[data-export-kind]').forEach(node => {
          const active = node.dataset.exportKind === requestedQuery.kind;
          node.classList.toggle('active',active); node.setAttribute('aria-pressed',String(active));
        });
        const currentQuery = value.query === requestedQuery.query && value.kind === requestedQuery.kind;
        const items = currentQuery ? value.items : [];
        const loading = Boolean(value.busy) || !currentQuery;
        const keys = new Set(items.map(item => `${item.kind}:${item.id}`));
        for (const [id,node] of rows) if (!keys.has(id)) { node.remove(); rows.delete(id); }
        items.forEach((item,index) => {
          const id = `${item.kind}:${item.id}`;
          let node = rows.get(id);
          if (!node) {
            node = document.createElement('label'); node.className = 'export-selection-item'; node.setAttribute('role','listitem');
            const check = document.createElement('input'); check.type = 'checkbox';
            check.dataset.pdmNativeFocusKey = `export-selection:record:${id}`;
            const info = document.createElement('span'); info.className = 'export-selection-info';
            const title = document.createElement('strong'); const detail = document.createElement('span'); info.append(title,detail);
            const kind = document.createElement('span'); kind.className = 'export-selection-kind'; node.append(check,info,kind);
            check.addEventListener('change',() => onAction('toggle',{...node._record,selected:check.checked}));
            rows.set(id,node);
          }
          node._record = {kind:item.kind,id:item.id,revision:item.revision};
          node.dataset.exportRecord = id;
          node.firstElementChild.checked = item.selected; node.firstElementChild.disabled = Boolean(value.busy);
          const info = node.children[1]; info.firstElementChild.textContent = item.title; info.firstElementChild.title = item.title;
          info.lastElementChild.textContent = item.detail; info.lastElementChild.hidden = !item.detail;
          node.lastElementChild.textContent = item.kind === 'PASSWORD' ? w.passwords : w.notes;
          node.lastElementChild.hidden = value.kind !== 'ALL';
          if (list.children[index] !== node) list.insertBefore(node,list.children[index] || null);
        });
        empty.textContent = value.error ? '' : loading && !items.length ? w.loading : w.empty;
        empty.hidden = items.length > 0; list.hidden = !items.length;
        root.querySelector('.export-selection-count').textContent = w.count(value.passwordCount,value.noteCount);
        buttons.done.disabled = loading || Boolean(value.error) || value.passwordCount + value.noteCount === 0;
        buttons.clear.disabled = Boolean(value.busy) || value.passwordCount + value.noteCount === 0;
        buttons.all.textContent = currentQuery && value.total > 0 && value.allSelected ? w.unselectAll : w.selectAll;
        buttons.all.disabled = loading || Boolean(value.error) || value.total === 0;
        const pager = root.querySelector('.export-selection-pager'); pager.hidden = !currentQuery || value.total <= value.limit;
        pager.firstElementChild.textContent = w.page(value.total ? value.offset + 1 : 0,value.offset + value.items.length,value.total);
        buttons.previous.disabled = Boolean(value.busy) || value.offset === 0;
        buttons.next.disabled = Boolean(value.busy) || value.offset + value.items.length >= value.total;
      },
      appearance(language) {
        w = TEXT[language === 'EN' ? 'EN' : 'ZH']; labels();
        if (state) this.project(state);
      },
      dispose() {
        if (!alive) return;
        alive = false; state = null; rows.clear(); root.remove();
        suspended.forEach(([node,inert]) => { node.inert = inert; node.classList.remove('export-selection-background'); });
        if (returnFocus?.isConnected) returnFocus.focus({preventScroll:true});
      },
    };
  }
  function validInfo(value) {
    return value && typeof value.selectionTicket === 'string' && /^[A-Za-z0-9_-]{0,64}$/.test(value.selectionTicket) &&
      ['passwordCount','noteCount'].every(key => Number.isSafeInteger(value[key]) && value[key] >= 0) && value.passwordCount + value.noteCount <= 100000;
  }
  function validPage(value) {
    return validInfo(value) && value.selectionTicket.length >= 16 &&
      typeof value.query === 'string' && Array.from(value.query).length <= 128 && !value.query.includes('\0') &&
      ['ALL','PASSWORD','NOTE'].includes(value.kind) && ['offset','total','changedCount'].every(key => Number.isSafeInteger(value[key]) && value[key] >= 0 && value[key] <= 100000) &&
      typeof value.allSelected === 'boolean' && (!value.allSelected || value.total > 0) &&
      Number.isSafeInteger(value.limit) && value.limit >= 1 && value.limit <= 100 && Array.isArray(value.items) && value.items.length <= value.limit &&
      value.items.every(item => item && ['PASSWORD','NOTE'].includes(item.kind) && Number.isSafeInteger(item.id) && item.id > 0 && item.id <= 2147483647 &&
        typeof item.revision === 'string' && /^[0-9a-f]{16,64}$/.test(item.revision) && typeof item.title === 'string' && item.title.length <= 512 &&
        typeof item.detail === 'string' && item.detail.length <= 1024 && typeof item.selected === 'boolean');
  }
  function openNative(container,bridge,pageEpoch,sessionEpoch,language,confirmed,onDone) {
    let w = TEXT[language === 'EN' ? 'EN' : 'ZH'];
    const pending = new Map();
    let alive = true, busy = true, ticket = '', queuedQuery = null, finishing = false;
    let queryIntent = {query:'',kind:'ALL'};
    let lastError = '';
    let current = {query:'',kind:'ALL',offset:0,limit:20,total:0,allSelected:false,items:[],changedCount:0,...counts(confirmed)};
    const view = create(container,action,language);
    function render() { if (alive) view.project({...current,busy,error:lastError ? errorText(lastError) : '',notice:current.changedCount ? w.changed : ''}); }
    function errorText(code) { return code === 'SELECTION_EXPIRED' ? w.expired : code === 'REVISION_CONFLICT' ? w.changed : w.failure; }
    function request(method,args = []) {
      const id = crypto.randomUUID(), signal = bridge[method.slice(0,-2) + 'CompletedV1'];
      return new Promise((resolve,reject) => {
        if (!signal?.connect || typeof bridge[method] !== 'function') { reject('INTERNAL_FAILURE'); return; }
        function settle(error,result) {
          if (!pending.has(id)) return;
          signal.disconnect(completed); pending.delete(id);
          if (error) reject(error); else resolve(result);
        }
        function completed(requestId,page,session,code,_argument,_retry,result) {
          if (requestId !== id) return;
          settle(page !== pageEpoch || session !== sessionEpoch ? 'STALE_SESSION' : code === 'OK' ? '' : code,result);
        }
        pending.set(id,method); signal.connect(completed);
        try {
          bridge[method](id,pageEpoch,sessionEpoch,...args,ack => {
            if (!ack?.accepted) settle(ack?.errorCode || 'INTERNAL_FAILURE');
          });
        } catch (_) { settle('INTERNAL_FAILURE'); }
      });
    }
    function dispose() {
      if (!alive) return;
      alive = false; view.dispose();
      for (const [id,method] of pending) {
        if (method === 'listExportSelectionV1' || method === 'changeExportSelectionV1')
          bridge.cancelRequestV1?.(crypto.randomUUID(),pageEpoch,id,() => {});
      }
      if (ticket && !finishing) request('finishExportSelectionV1',[ticket,'CANCEL']).catch(() => {});
    }
    async function pageRequest(method,args) {
      busy = true; lastError = ''; render();
      try {
        const result = await request(method,args);
        if (!alive) return;
        if (!validPage(result)) throw 'INTERNAL_FAILURE';
        if (method === 'listExportSelectionV1' && (result.query !== args[1] || result.kind !== args[2])) throw 'INTERNAL_FAILURE';
        current = result;
        if (result.query !== queryIntent.query || result.kind !== queryIntent.kind) queuedQuery = {...queryIntent};
      } catch (code) {
        if (alive) {
          lastError = code;
          if (method === 'listExportSelectionV1' && !queuedQuery) current = {...current,...queryIntent,items:[],total:0,offset:0};
        }
      }
      finally {
        busy = false;
        if (finishing) return;
        if (alive && queuedQuery) {
          const next = queuedQuery; queuedQuery = null;
          pageRequest('listExportSelectionV1',[ticket,next.query,next.kind,0,current.limit]);
        } else render();
      }
    }
    async function finish(action) {
      if (finishing) return;
      if (!ticket) { dispose(); onDone(null); return; }
      finishing = true; queuedQuery = null; busy = true; render();
      try {
        const result = await request('finishExportSelectionV1',[ticket,action]);
        if (!alive) return;
        if (!validInfo(result)) throw 'INTERNAL_FAILURE';
        dispose(); onDone(action === 'CONFIRM' ? result : null);
      } catch (code) { if (alive) { lastError = code; busy = false; finishing = false; render(); } }
    }
    function action(name,value) {
      if (!alive || finishing) return;
      if (name === 'cancel') { finish('CANCEL'); return; }
      if (name === 'query') {
        queryIntent = {...value};
        if (busy) { queuedQuery = value; render(); return; }
        pageRequest('listExportSelectionV1',[ticket,value.query,value.kind,0,current.limit]); return;
      }
      if (busy) return;
      if (name === 'done') { finish('CONFIRM'); return; }
      if (name === 'toggle') pageRequest('changeExportSelectionV1',[ticket,value.selected ? 'ADD' : 'REMOVE',value.kind,value.id,value.revision]);
      else if (name === 'all' || name === 'clear') pageRequest('changeExportSelectionV1',
        [ticket,name === 'all' ? current.allSelected ? 'REMOVE_FILTERED' : 'ALL' : 'CLEAR','ALL',0,'']);
      else if (name === 'previous' || name === 'next') pageRequest('listExportSelectionV1',[ticket,current.query,current.kind,
        Math.max(0,current.offset + (name === 'next' ? current.limit : -current.limit)),current.limit]);
    }
    render();
    request('beginExportSelectionV1').then(result => {
      if (!validInfo(result) || result.selectionTicket.length < 16) throw 'INTERNAL_FAILURE';
      ticket = result.selectionTicket;
      if (!alive) { request('finishExportSelectionV1',[ticket,'CANCEL']).catch(() => {}); return; }
      current = {...current,...result};
      const query = queuedQuery || queryIntent; queuedQuery = null;
      pageRequest('listExportSelectionV1',[ticket,query.query,query.kind,0,current.limit]);
    }).catch(code => { if (alive) { busy = false; lastError = code; render(); } });
    return {dispose,appearance(language) {
      w = TEXT[language === 'EN' ? 'EN' : 'ZH']; view.appearance(language); render();
    }};
  }
  window.PdmExportSelection = Object.freeze({create,counts,openNative});
})();
