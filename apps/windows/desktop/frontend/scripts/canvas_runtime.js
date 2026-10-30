/* ============================================================
   标尺刻度生成 / Ruler Ticks
   为顶部和左侧标尺生成像素刻度，主刻度 100px、次刻度 50px、小刻度 10px
   ============================================================ */
const PDM_IS_M4_ISOLATED =
  document.documentElement.dataset.pdmLaunchMode === 'm4-isolated';

function updateLabels(){
  return state.lang==='en' ? {
    title:'Software updates',automatic:'Check at startup',automaticHint:'Check automatically at startup after the interval. You can check manually anytime.',
    interval:'Check interval',intervalHint:'Elapsed days before the next startup check.',days:'days',check:'Check now',checking:'Checking…',
    idle:'Not checked yet',loading:'Reading update settings…',available:'Update available',latest:'You are up to date',ahead:'Your version is newer than the latest public stable release',none:'No public stable release',failed:'Could not finish checking',
    current:'Current version',lastAttempt:'Last attempt',lastFound:'Last verified result',published:'Published',details:'Update details',open:'Open release page',
    snooze:'Remind in 7 days',ignore:'Ignore this version',notice:'A new version is available. Use the update entry to view it.',
    snoozed:'Reminder paused until',ignored:'Automatic reminders are off for this version.',normal:'',intervalInvalid:'Enter a whole number of days from 1 to 2147483647.',
    SETTINGS_UNAVAILABLE:'Update settings could not be read. Retry to check again.',SETTINGS_WRITE_FAILED:'Update settings could not be saved. The previous values remain in effect.',
    NETWORK:'Could not connect. Check your connection and retry.',TIMEOUT:'The request timed out. Please retry.',INCOMPLETE:'The release list was incomplete. Please retry.',
    INVALID_RESPONSE:'The release information could not be verified.',RATE_LIMITED:'The service is limiting requests. Please try again later.',CANCELLED:'The check was cancelled.',
    requestFailed:'The action could not be completed. Please retry.',openFailed:'The release page could not be opened. Please retry.',
    demoOpen:'Demo: the app opens the verified release page in your browser.',
  } : {
    title:'软件更新',automatic:'启动时检查更新',automaticHint:'满设定间隔后，在下次启动时自动检查；也可随时手动检查。',
    interval:'检查间隔',intervalHint:'距离上次尝试满这些天数后再检查。',days:'天',check:'立即检查',checking:'正在检查…',
    idle:'尚未检查',loading:'正在读取更新设置…',available:'发现新版本',latest:'已是最新版本',ahead:'当前版本高于最新公开正式版',none:'暂无公开正式版',failed:'未能完成检查',
    current:'当前版本',lastAttempt:'上次尝试',lastFound:'上次有效结果',published:'发布时间',details:'更新详情',open:'查看发行页',
    snooze:'7 天后提醒',ignore:'此版本不再提醒',notice:'发现新版本，可从版本入口查看。',
    snoozed:'已暂停提醒至',ignored:'此版本不再自动提醒。',normal:'',intervalInvalid:'请输入 1 至 2147483647 之间的整数天数。',
    SETTINGS_UNAVAILABLE:'无法读取更新设置，请重试。',SETTINGS_WRITE_FAILED:'无法保存更新设置，原设置继续生效。',
    NETWORK:'无法连接，请检查网络后重试。',TIMEOUT:'查询超时，请重试。',INCOMPLETE:'发行列表未读取完整，请重试。',
    INVALID_RESPONSE:'发行信息未能通过校验。',RATE_LIMITED:'查询过于频繁，请稍后重试。',CANCELLED:'检查已取消。',
    requestFailed:'操作未完成，请重试。',openFailed:'未能打开发行页，请重试。',demoOpen:'演示：正式应用会在浏览器中打开已核验的发行页。',
  };
}

function updateDate(value){
  const date=new Date(value);
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleString(state.lang==='en'?'en-US':'zh-CN');
}

function updateVersionIsAhead(current,release){
  const valid=/^(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)$/;
  if(typeof current!=='string'||typeof release!=='string'||current.length>32||release.length>32||!valid.test(current)||!valid.test(release)) return false;
  const left=current.split('.').map(BigInt),right=release.split('.').map(BigInt);
  for(let index=0;index<3;index++) if(left[index]!==right[index]) return left[index]>right[index];
  return false;
}

function updateIntervalValue(value){
  const days=Number(value);
  return /^\d+$/.test(value)&&Number.isInteger(days)&&days>=1&&days<=2147483647 ? days : null;
}

function updatePanelMarkup(policy){
  const preferences=policy ? `<div class="setting-row" data-no-auth="true"><div class="setting-info"><div class="setting-name" data-update-label="automatic"></div><div class="setting-desc" data-update-label="automaticHint"></div></div><div class="setting-control"><button type="button" class="toggle" role="switch" aria-checked="false" data-update-action="toggle"></button></div></div><div class="setting-row" data-update-interval-row data-no-auth="true"><div class="setting-info"><label class="setting-name" for="update-interval-days" data-update-label="interval"></label><div class="setting-desc" data-update-label="intervalHint"></div></div><div class="setting-control"><div class="slider-input-row"><input id="update-interval-days" class="num-input update-days" data-update-days type="number" inputmode="numeric" min="1" max="2147483647" step="1" aria-describedby="update-settings-feedback"><span class="unit" data-update-label="days"></span></div></div></div>` : '';
  return `${preferences}<div class="setting-row update-summary" data-no-auth="true"><div class="setting-info"><div class="setting-name" data-update-status role="status" aria-live="polite"></div><div class="setting-desc" data-update-current></div></div><div class="update-actions"><button type="button" class="btn btn-sm" data-update-action="check"></button></div><div class="update-result"><div class="update-meta" data-update-meta></div><div class="update-feedback" ${policy?'id="update-settings-feedback"':''} data-update-feedback role="status" aria-live="polite"></div><details class="update-release" hidden><summary data-update-label="details"></summary><div class="update-meta" data-update-published></div><pre data-update-notes tabindex="0"></pre><div class="update-actions" data-update-reminders><button type="button" class="btn btn-primary btn-sm" data-update-action="open" data-update-label="open"></button><button type="button" class="btn btn-ghost btn-sm" data-update-action="snooze" data-update-label="snooze"></button><button type="button" class="btn btn-ghost btn-sm" data-update-action="ignore" data-update-label="ignore"></button></div></details></div></div>`;
}

function renderUpdateSurfaces(update,options={}){
  const copy=updateLabels(),pending=options.pending||new Set();
  const ready=Boolean(options.ready),available=Boolean(update?.available);
  const checking=pending.has('check');
  const setText=(node,text)=>{if(node&&node.textContent!==text) node.textContent=text;};
  document.querySelectorAll('[data-update-panel]').forEach(panel=>{
    if(!panel.firstElementChild) panel.innerHTML=updatePanelMarkup(panel.dataset.updatePanel==='settings');
    const latest=updateVersionIsAhead(update?.currentVersion,update?.releaseVersion)?copy.ahead:copy.latest;
    const status=update?.status==='FAILED' ? copy.failed : !update?.settingsReady ? copy.loading : ({IDLE:copy.idle,CHECKING:copy.checking,UPDATE_AVAILABLE:copy.available,UP_TO_DATE:latest,NO_RELEASE:copy.none}[update.status]);
    setText(panel.querySelector('[data-update-status]'),status||copy.failed);
    setText(panel.querySelector('[data-update-current]'),`${copy.current} ${update?.currentVersion||window.PDM_HELP_CONTENT?.version||''}${available?' · '+copy.available+' '+update.releaseVersion:''}`);
    const meta=[];
    if(update?.lastAttemptMs) meta.push(`${copy.lastAttempt}：${updateDate(update.lastAttemptMs)}`);
    if(available){
      meta.push(`${copy.lastFound}：${updateDate(update.resultAtMs)}`);
      if(update.reminder==='SNOOZED') meta.push(`${copy.snoozed} ${updateDate(update.remindAfterMs)}`);
      if(update.reminder==='IGNORED') meta.push(copy.ignored);
    }
    setText(panel.querySelector('[data-update-meta]'),meta.join('\n'));
    const failure=options.error||(update?.error!=='NONE'?update?.error:'');
    setText(panel.querySelector('[data-update-feedback]'),copy[failure]||'');
    const interval=panel.querySelector('[data-update-days]');
    if(interval){
      const days=String(update?.intervalDays||1);
      if(interval.dataset.updateDirty!=='true'&&document.activeElement!==interval&&interval.value!==days) interval.value=days;
      interval.setAttribute('aria-label',copy.interval);
      interval.setAttribute('aria-invalid',String(options.error==='intervalInvalid'));
      interval.disabled=!ready||!update?.settingsReady||!update?.enabled;
      interval.setAttribute('aria-busy',String(pending.has('policy')));
      interval.closest('[data-update-interval-row]').classList.toggle('is-disabled',interval.disabled);
    }
    const toggle=panel.querySelector('[data-update-action="toggle"]');
    if(toggle){toggle.classList.toggle('on',Boolean(update?.enabled));toggle.setAttribute('aria-checked',String(Boolean(update?.enabled)));toggle.setAttribute('aria-label',copy.automatic);}
    const release=panel.querySelector('.update-release');
    const releaseTag=available?update.releaseTag:'';
    if(release.dataset.updateTag!==releaseTag){release.open=false;release.dataset.updateTag=releaseTag;}
    release.hidden=!available;
    setText(panel.querySelector('[data-update-published]'),available&&update.publishedAt?`${copy.published}：${updateDate(update.publishedAt)}`:'');
    const notes=panel.querySelector('[data-update-notes]');
    notes.hidden=!available||!update.releaseNotes;
    setText(notes,available?update.releaseNotes:'');
  });
  document.querySelectorAll('[data-update-label]').forEach(node=>setText(node,copy[node.dataset.updateLabel]||''));
  document.querySelectorAll('[data-update-action]').forEach(button=>{
    const action=button.dataset.updateAction;
    let enabled=ready;
    if(action==='check'){enabled=enabled&&!checking&&!pending.has('state');setText(button,checking?copy.checking:copy.check);}
    if(action==='toggle'){
      enabled=enabled&&Boolean(update?.settingsReady);
      button.setAttribute('aria-busy',String(pending.has('policy')));
    }
    if(['open','snooze','ignore','dismiss','details'].includes(action)) enabled=enabled&&available;
    if(action==='open'){button.hidden=!available;enabled=enabled&&!pending.has('open');}
    if(['snooze','ignore','dismiss'].includes(action)) enabled=enabled&&!pending.has('reminder')&&Boolean(update?.settingsReady);
    if(action==='snooze'&&update?.reminder==='SNOOZED') enabled=false;
    if(action==='ignore'&&update?.reminder==='IGNORED') enabled=false;
    button.disabled=!enabled;
    button.setAttribute('aria-disabled',String(!enabled));
    button.dataset.pdmM4Disabled=String(!enabled);
    if(button.classList.contains('update-entry')){button.hidden=!available;setText(button,`${copy.available} ${update?.releaseVersion||''}`);button.title=button.textContent;}
  });
}

const demoUpdateState={revision:0,currentVersion:'',settingsReady:true,enabled:true,intervalDays:1,lastAttemptMs:0,status:'IDLE',available:false,releaseVersion:'',releaseTag:'',publishedAt:'',releaseNotes:'',resultAtMs:0,error:'NONE',reminder:'NORMAL',remindAfterMs:0,autoNotice:false};
let demoUpdateError='';
window.renderUpdates=()=>{
  if(PDM_IS_M4_ISOLATED) return;
  demoUpdateState.currentVersion=window.PDM_HELP_CONTENT?.version||'';
  renderUpdateSurfaces(demoUpdateState,{ready:true,error:demoUpdateError});
};
document.addEventListener('input',event=>{
  if(event.target.matches?.('[data-update-days]')) event.target.dataset.updateDirty='true';
});
function saveDemoUpdateInterval(input){
  if(PDM_IS_M4_ISOLATED||input.disabled) return;
  const days=updateIntervalValue(input.value);
  demoUpdateError='';
  if(days===null) demoUpdateError='intervalInvalid';
  else{demoUpdateState.intervalDays=days;delete input.dataset.updateDirty;}
  window.renderUpdates();
}
document.addEventListener('change',event=>{
  if(event.target.matches?.('[data-update-days]')) saveDemoUpdateInterval(event.target);
});
document.addEventListener('keydown',event=>{
  if(!PDM_IS_M4_ISOLATED&&!event.isComposing&&event.key==='Enter'&&event.target.matches?.('[data-update-days]')){
    event.preventDefault();saveDemoUpdateInterval(event.target);
  }
});
document.addEventListener('click',event=>{
  if(PDM_IS_M4_ISOLATED) return;
  const button=event.target.closest?.('[data-update-action]');
  if(!button||button.disabled) return;
  const action=button.dataset.updateAction;
  demoUpdateError='';
  if(action==='details'){
    navigateTo('help');
    if(state.currentNav==='help'){
      window.selectHelp?.('about');
      const details=$('#page-help .update-release');
      if(details&&!details.hidden){details.open=true;details.scrollIntoView({block:'nearest'});}
    }
  }
  if(action==='toggle'){
    demoUpdateState.enabled=!demoUpdateState.enabled;
    if(!demoUpdateState.enabled){
      const input=document.querySelector('[data-update-days]');
      if(input){delete input.dataset.updateDirty;input.value=String(demoUpdateState.intervalDays);}
    }
  }
  if(action==='check') Object.assign(demoUpdateState,{status:'UPDATE_AVAILABLE',lastAttemptMs:Date.now(),available:true,releaseVersion:'1.2.0',releaseTag:'windows-v1.2.0',publishedAt:'2026-10-19T00:00:00Z',releaseNotes:state.lang==='en'?'Public demo release notes.\nImproved comparison and import workflow.':'公开演示版本说明。\n改善差异比较与导入操作体验。',resultAtMs:Date.now(),error:'NONE'});
  if(action==='snooze') Object.assign(demoUpdateState,{reminder:'SNOOZED',remindAfterMs:Date.now()+7*86400000,autoNotice:false});
  if(action==='ignore') Object.assign(demoUpdateState,{reminder:'IGNORED',remindAfterMs:0,autoNotice:false});
  if(action==='dismiss') demoUpdateState.autoNotice=false;
  if(action==='open') showToast(updateLabels().demoOpen,'info');
  window.renderUpdates();
});

function buildRulers(){
  const W = 1200, H = 800;
  const top = document.getElementById('ruler-top');
  const left = document.getElementById('ruler-left');
  if(!top || !left) return;

  // 顶部：横向标尺
  for(let x = 0; x <= W; x += 10){
    const tick = document.createElement('div');
    tick.className = 'tick';
    if(x % 100 === 0){
      tick.classList.add('major');
    } else if(x % 50 === 0){
      tick.classList.add('minor');
    } else {
      // 10px 小刻度，更短更淡
      tick.style.height = '2px';
      tick.style.background = '#bcbecb';
    }
    tick.style.left = x + 'px';
    top.appendChild(tick);

    // 100px 整数处加数字标签
    if(x % 100 === 0 && x > 0){
      const label = document.createElement('div');
      label.className = 'tick-label';
      label.textContent = x;
      label.style.left = x + 'px';
      top.appendChild(label);
    }
  }

  // 左侧：纵向标尺
  for(let y = 0; y <= H; y += 10){
    const tick = document.createElement('div');
    tick.className = 'tick';
    if(y % 100 === 0){
      tick.classList.add('major');
    } else if(y % 50 === 0){
      tick.classList.add('minor');
    } else {
      tick.style.width = '2px';
      tick.style.background = '#bcbecb';
    }
    tick.style.top = y + 'px';
    left.appendChild(tick);

    if(y % 100 === 0 && y > 0){
      const label = document.createElement('div');
      label.className = 'tick-label';
      label.textContent = y;
      label.style.top = y + 'px';
      left.appendChild(label);
    }
  }
}

/* ============================================================
   模拟数据
   ============================================================ */
const passwords = [
  {id:1, platform:'GitHub', account:'dev@example.com', password:'Xk9#mP2$vL7nQw@rT5', notes:'主力代码仓库，已开启 2FA', totp_secret:'JBSWY3DPEHPK3PXP', updated_at:'2026-06-20', password_changed_at:'2026-06-20', strength:'strong', is_favorite:true},
  {id:2, platform:'Gmail', account:'myaccount@gmail.com', password:'J$8kLp2#mN9xQr4@', notes:'主邮箱，绑定大量服务', totp_secret:'GEZDGNBVGY3TQOJQ', updated_at:'2026-06-15', password_changed_at:'2026-06-15', strength:'strong', is_favorite:true},
  {id:3, platform:'微信', account:'wechat_user', password:'J$8kLp2#mN9xQr4@', notes:'社交账号（与 Gmail 共用密码，待修改）', updated_at:'2026-05-30', password_changed_at:'2026-05-30', strength:'strong', is_favorite:true},
  {id:4, platform:'旧邮箱', account:'old_user', password:'123456', notes:'待迁移的旧账号', updated_at:'2025-06-20', password_changed_at:'2025-06-20', strength:'weak', is_favorite:false},
  {id:5, platform:'知乎', account:'zhihu_user', password:'Zh1Hu#$89mNp', notes:'知识社区', updated_at:'2026-06-10', password_changed_at:'2026-06-10', strength:'strong', is_favorite:false},
  {id:6, platform:'淘宝', account:'taobao_buyer', password:'Taobao2024', notes:'购物账号', updated_at:'2026-04-22', password_changed_at:'2026-04-22', strength:'fair', is_favorite:false},
  {id:7, platform:'论坛', account:'forum123', password:'abc123', notes:'技术论坛', updated_at:'2026-03-15', password_changed_at:'2026-03-15', strength:'weak', is_favorite:false},
  {id:8, platform:'测试号', account:'test_user', password:'test1234', notes:'临时测试账号', updated_at:'2026-06-01', password_changed_at:'2025-09-01', strength:'weak', is_favorite:false},
  {id:9, platform:'Apple ID', account:'apple@icloud.com', password:'ApP1e#$2024Sec!', notes:'苹果生态账号', updated_at:'2026-06-22', password_changed_at:'2026-06-22', strength:'strong', is_favorite:true},
  {id:10, platform:'QQ', account:'123456789', password:'qq2024password', notes:'即时通讯', updated_at:'2026-05-12', password_changed_at:'2026-05-12', strength:'fair', is_favorite:false},
];

/* ============================================================
   TOTP 算法（RFC 6238）纯 JS 实现
   ============================================================
   - 输入：Base32 编码的 secret key（用户在网站 2FA 设置页复制的密钥）
   - 输出：6 位数字验证码 + 剩余秒数（30 秒周期）
   - Win 端差异：用 pyotp 库（pyotp.TOTP(secret).now()），无需自己实现
   - secret 示例：JBSWY3DPEHPK3PXP（Base32 编码）
   ============================================================ */
function base32Decode(str){
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  let bits = '', bytes = [];
  for(const c of str.toUpperCase().replace(/=+$/,'').replace(/\s/g,'')){
    const idx = alphabet.indexOf(c);
    if(idx === -1) continue;
    bits += idx.toString(2).padStart(5,'0');
  }
  for(let i=0; i+8<=bits.length; i+=8){
    bytes.push(parseInt(bits.substr(i,8),2));
  }
  return new Uint8Array(bytes);
}
function intToBytes(num){
  const bytes = new Uint8Array(8);
  let v = num;
  for(let i=7; i>=0; i--){ bytes[i] = v & 0xff; v = Math.floor(v/256); }
  return bytes;
}
/* SHA1 纯 JS 实现（HMAC-SHA1 用） */
function sha1(msg){
  const h0=0x67452301, h1=0xEFCDAB89, h2=0x98BADCFE, h3=0x10325476, h4=0xC3D2E1F0;
  const l = msg.length;
  const withOne = new Uint8Array(l + 1 + ((56 - (l + 1) % 64 + 64) % 64) + 8);
  withOne.set(msg); withOne[l] = 0x80;
  const bitLen = l * 8;
  for(let i=0; i<8; i++) withOne[withOne.length-1-i] = (bitLen >>> (i*8)) & 0xff;
  let [a,b,c,d,e] = [h0,h1,h2,h3,h4];
  const w = new Array(80);
  for(let i=0; i<withOne.length; i+=64){
    for(let j=0; j<16; j++){
      w[j] = (withOne[i+j*4]<<24) | (withOne[i+j*4+1]<<16) | (withOne[i+j*4+2]<<8) | withOne[i+j*4+3];
      w[j] >>>= 0;
    }
    for(let j=16; j<80; j++){
      w[j] = ((w[j-3]^w[j-8]^w[j-14]^w[j-16]) << 1) | ((w[j-3]^w[j-8]^w[j-14]^w[j-16]) >>> 31);
      w[j] >>>= 0;
    }
    let [aa,bb,cc,dd,ee] = [a,b,c,d,e];
    for(let j=0; j<80; j++){
      let f,k;
      if(j<20){ f=(bb&cc)|((~bb)&dd); k=0x5A827999; }
      else if(j<40){ f=bb^cc^dd; k=0x6ED9EBA1; }
      else if(j<60){ f=(bb&cc)|(bb&dd)|(cc&dd); k=0x8F1BBCDC; }
      else { f=bb^cc^dd; k=0xCA62C1D6; }
      const temp = (((aa<<5)|(aa>>>27)) + f + ee + k + w[j]) >>> 0;
      ee=dd; dd=cc; cc=(bb<<30)|(bb>>>2); dd>>>=0; cc>>>=0; bb=aa; aa=temp;
    }
    a=(a+aa)>>>0; b=(b+bb)>>>0; c=(c+cc)>>>0; d=(d+dd)>>>0; e=(e+ee)>>>0;
  }
  const result = new Uint8Array(20);
  [a,b,c,d,e].forEach((v,i)=>{
    result[i*4] = (v>>>24)&0xff; result[i*4+1] = (v>>>16)&0xff;
    result[i*4+2] = (v>>>8)&0xff; result[i*4+3] = v&0xff;
  });
  return result;
}
function hmacSha1(key, msg){
  const blockSize = 64;
  if(key.length > blockSize) key = sha1(key);
  const paddedKey = new Uint8Array(blockSize);
  paddedKey.set(key);
  const oKeyPad = new Uint8Array(blockSize), iKeyPad = new Uint8Array(blockSize);
  for(let i=0; i<blockSize; i++){
    oKeyPad[i] = paddedKey[i] ^ 0x5c;
    iKeyPad[i] = paddedKey[i] ^ 0x36;
  }
  const innerInput = new Uint8Array(iKeyPad.length + msg.length);
  innerInput.set(iKeyPad); innerInput.set(msg, iKeyPad.length);
  const innerHash = sha1(innerInput);
  const outerInput = new Uint8Array(oKeyPad.length + innerHash.length);
  outerInput.set(oKeyPad); outerInput.set(innerHash, oKeyPad.length);
  return sha1(outerInput);
}
function hotp(secret, counter, digits=6){
  const key = base32Decode(secret);
  const msg = intToBytes(counter);
  const hash = hmacSha1(key, msg);
  const offset = hash[hash.length-1] & 0xf;
  const binary = (((hash[offset] & 0x7f) << 24) |
                 ((hash[offset+1] & 0xff) << 16) |
                 ((hash[offset+2] & 0xff) << 8) |
                 (hash[offset+3] & 0xff)) >>> 0;
  return (binary % 1000000).toString().padStart(digits, '0');
}
/* 生成当前 TOTP 码 + 剩余秒数 */
function generateTOTP(secret){
  if(!secret) return null;
  const time = Math.floor(Date.now()/1000);
  const counter = Math.floor(time/30);
  return { code: hotp(secret, counter), remaining: 30 - (time % 30) };
}
/* 格式化 6 位码为 "123 456" 两组（易读） */
function formatTOTPCode(code){
  if(!code || code.length !== 6) return code;
  return code.slice(0,3) + ' ' + code.slice(3);
}

const notes = [
  {id:1, title:'银行卡信息', content:'招商银行储蓄卡\n卡号: 6225-8810-****-1234\n有效期: 08/28\nCVV: ***\n背面签名已设置', updated_at:'2026-06-18', is_favorite:true},
  {id:2, title:'WiFi 密码', content:'家庭路由器: TP-Link AX3000\nSSID: Home_5G\n密码: Wifi#2024$Secure\n管理后台: 192.168.1.1 / admin', updated_at:'2026-06-12', is_favorite:false},
  {id:3, title:'密保问题', content:'Q1: 您的小学名称？\nA1: 光明小学\n\nQ2: 第一只宠物的名字？\nA2: 旺财\n\nQ3: 出生地城市？\nA3: 杭州', updated_at:'2026-05-28', is_favorite:true},
  {id:4, title:'服务器配置', content:'生产服务器: 47.96.x.x\nSSH端口: 22\n用户: deploy\n密钥: ~/.ssh/id_rsa_prod\n备份策略: 每日凌晨3点增量', updated_at:'2026-06-22', is_favorite:false},
  {id:5, title:'灵感笔记', content:'产品设计灵感：\n1. 用渐变色卡片区分密码强度\n2. Quick Bar 全局唤出体验\n3. 手风琴交互减少页面跳转\n4. 安全体检像体检报告一样直观', updated_at:'2026-06-25', is_favorite:false},
];

/* 仅供 notes-cards 视觉状态使用的公开夹具；不接入产品数据或 Bridge。 */
const NOTES_CARDS_FIXTURE = [
  {id:101, title:'周末出行备忘', content:'周六 09:30 出发\n带上雨伞、充电器和薄外套\n车票放在随身包里\n到站后联系民宿\n返程：周日 18:00', updated_at:'2026-09-11', is_favorite:true},
  {id:102, title:'阅读摘记', content:'把复杂的事拆成可执行的小步。\n一次只处理一件事。\n完成比反复规划更重要。', updated_at:'2026-09-09', is_favorite:false},
  {id:103, title:'电脑重装备忘', content:'先备份文档和照片\n核对浏览器书签\n记录已安装的软件\n准备离线安装包\n完成后检查驱动\n恢复常用目录\n逐项核对备份内容\n保留旧备份一周\n另外需要清理临时文件和桌面\n确认系统更新已完成\n重新登录常用服务\n最后重启一次', updated_at:'2026-09-10', is_favorite:false},
  {id:104, title:'本周待办', content:'周三取快递\n周五整理书桌\n周末给绿植换水', updated_at:'2026-09-09', is_favorite:false},
  {id:105, title:'常用收件信息', content:'收件人：林小满（示例）\n地址：青禾路 18 号\n工作日优先放门口收纳箱', updated_at:'2026-09-11', is_favorite:true},
  {id:106, title:'家庭设备记录', content:'路由器放在书房柜子上层\n电视遥控器使用七号电池\n扫地机滤网：每月清理一次\n备用配件放在储物间', updated_at:'2026-09-10', is_favorite:true},
];

/* last_connected 为毫秒时间戳（Date.now() 偏移），模拟 security.st 中记录的最近连接时间。
   Win 端由 SecurityService.add_recent_db_path() 在成功连接时写入，格式：加密路径|加密时间 */
const _now = Date.now();
const recents = [
  {name:'pdm.db', path:'C:\\Users\\demo\\Documents\\pdm.db', last_connected: _now - 35*60*1000, icon:'database'},
  {name:'passwords.db', path:'D:\\Work\\passwords.db', last_connected: _now - 5*3600*1000, icon:'database'},
  {name:'backup.db', path:'E:\\Backup\\2024\\backup.db', last_connected: _now - 3*86400000, icon:'database'},
  {name:'shared.db', path:'\\\\NAS\\Shared\\shared.db', last_connected: _now - 8*86400000, icon:'database'},
  {name:'old.db', path:'F:\\Archive\\old.db', last_connected: _now - 16*86400000, icon:'database'},
];

/* SVG 图标库：分两类
   - 线条类（Lucide, ISC 许可, 24×24 viewBox, stroke 风格）
   - 填充类（Phosphor Bold, MIT 许可, 256×256 viewBox, fill 风格）
   Phosphor Bold 比 Lucide 视觉更醒目，适合密码管理器"安全可靠"调性
*/
const SVG_ICONS_STROKE = {
  briefcase: '<rect width="20" height="14" x="2" y="7" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
  database: '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5V19A9 3 0 0 0 21 19V5"/><path d="M3 12A9 3 0 0 0 21 12"/>',
};
const SVG_ICONS_FILL = {
  // Phosphor Fill (MIT) - https://github.com/phosphor-icons/phosphor-icons
  // 侧边栏导航 + 锁定按钮统一使用 fill 风格，视觉稳重契合"安全"调性
  lock: 'M208,76H176V52a48,48,0,0,0-96,0V76H48A20.02292,20.02292,0,0,0,28,96V208a20.02292,20.02292,0,0,0,20,20H208a20.02292,20.02292,0,0,0,20-20V96A20.02292,20.02292,0,0,0,208,76ZM104,52a24,24,0,0,1,48,0V76H104ZM204,204H52V100H204Zm-60.01758-52a16,16,0,1,1-16-16A16.01833,16.01833,0,0,1,143.98242,152Z',
  key: 'M216.57,39.43A80,80,0,0,0,83.91,120.78L28.69,176A15.86,15.86,0,0,0,24,187.31V216a16,16,0,0,0,16,16H72a8,8,0,0,0,8-8V208H96a8,8,0,0,0,8-8V184h16a8,8,0,0,0,5.66-2.34l9.56-9.57A79.73,79.73,0,0,0,160,176h.1A80,80,0,0,0,216.57,39.43ZM180,92a16,16,0,1,1,16-16A16,16,0,0,1,180,92Z',
  notebook: 'M208,32H48A16,16,0,0,0,32,48V208a16,16,0,0,0,16,16H208a16,16,0,0,0,16-16V48A16,16,0,0,0,208,32ZM80,208H48V48H80Zm96-56H112a8,8,0,0,1,0-16h64a8,8,0,0,1,0,16Zm0-32H112a8,8,0,0,1,0-16h64a8,8,0,0,1,0,16Z',
  shield: 'M224,56v56c0,52.72-25.52,84.67-46.93,102.19-23.06,18.86-46,25.27-47,25.53a8,8,0,0,1-4.2,0c-1-.26-23.91-6.67-47-25.53C57.52,196.67,32,164.72,32,112V56A16,16,0,0,1,48,40H208A16,16,0,0,1,224,56Z',
  wrench: 'M232,96a72,72,0,0,1-100.94,66L79,222.22c-.12.14-.26.29-.39.42a32,32,0,0,1-45.26-45.26c.14-.13.28-.27.43-.39L94,124.94a72.07,72.07,0,0,1,83.54-98.78,8,8,0,0,1,3.93,13.19L144,80l5.66,26.35L176,112l40.65-37.52a8,8,0,0,1,13.19,3.93A72.6,72.6,0,0,1,232,96Z',
  gear: 'M237.94,107.21a8,8,0,0,0-3.89-5.4l-29.83-17-.12-33.62a8,8,0,0,0-2.83-6.08,111.91,111.91,0,0,0-36.72-20.67,8,8,0,0,0-6.46.59L128,41.85,97.88,25a8,8,0,0,0-6.47-.6A111.92,111.92,0,0,0,54.73,45.15a8,8,0,0,0-2.83,6.07l-.15,33.65-29.83,17a8,8,0,0,0-3.89,5.4,106.47,106.47,0,0,0,0,41.56,8,8,0,0,0,3.89,5.4l29.83,17,.12,33.63a8,8,0,0,0,2.83,6.08,111.91,111.91,0,0,0,36.72,20.67,8,8,0,0,0,6.46-.59L128,214.15,158.12,231a7.91,7.91,0,0,0,3.9,1,8.09,8.09,0,0,0,2.57-.42,112.1,112.1,0,0,0,36.68-20.73,8,8,0,0,0,2.83-6.07l.15-33.65,29.83-17a8,8,0,0,0,3.89-5.4A106.47,106.47,0,0,0,237.94,107.21ZM128,168a40,40,0,1,1,40-40A40,40,0,0,1,128,168Z',
  // 告警 + 记事图标（体检面板 + 记事条目）
  warning: 'M236.8,188.09,149.35,36.22h0a24.76,24.76,0,0,0-42.7,0L19.2,188.09a23.51,23.51,0,0,0,0,23.72A24.35,24.35,0,0,0,40.55,224h174.9a24.35,24.35,0,0,0,21.33-12.19A23.51,23.51,0,0,0,236.8,188.09ZM120,104a8,8,0,0,1,16,0v40a8,8,0,0,1-16,0Zm8,88a12,12,0,1,1,12-12A12,12,0,0,1,128,192Z',
  repeat: 'M224,48V96a8,8,0,0,1-8,8H168a8,8,0,0,1-5.66-13.66L180.65,72a79.48,79.48,0,0,0-54.72-22.09h-.45A79.52,79.52,0,0,0,69.59,72.71,8,8,0,0,1,58.41,61.27,96,96,0,0,1,192,60.7l18.36-18.36A8,8,0,0,1,224,48ZM186.41,183.29A80,80,0,0,1,75.35,184l18.31-18.31A8,8,0,0,0,88,152H40a8,8,0,0,0-8,8v48a8,8,0,0,0,13.66,5.66L64,195.3a95.42,95.42,0,0,0,66,26.76h.53a95.36,95.36,0,0,0,67.07-27.33,8,8,0,0,0-11.18-11.44Z',
  clock: 'M128,24A104,104,0,1,0,232,128,104.11,104.11,0,0,0,128,24Zm56,112H128a8,8,0,0,1-8-8V72a8,8,0,0,1,16,0v48h48a8,8,0,0,1,0,16Z',
  // 顶栏工具栏 + 视图切换 + 状态图标（全部 Phosphor Fill，风格统一）
  search: 'M168,112a56,56,0,1,1-56-56A56,56,0,0,1,168,112Zm61.66,117.66a8,8,0,0,1-11.32,0l-50.06-50.07a88,88,0,1,1,11.32-11.31l50.06,50.06A8,8,0,0,1,229.66,229.66ZM112,184a72,72,0,1,0-72-72A72.08,72.08,0,0,0,112,184Z',
  moon: 'M235.54,150.21a104.84,104.84,0,0,1-37,52.91A104,104,0,0,1,32,120,103.09,103.09,0,0,1,52.88,57.48a104.84,104.84,0,0,1,52.91-37,8,8,0,0,1,10,10,88.08,88.08,0,0,0,109.8,109.8,8,8,0,0,1,10,10Z',
  sun: 'M120,40V16a8,8,0,0,1,16,0V40a8,8,0,0,1-16,0Zm8,24a64,64,0,1,0,64,64A64.07,64.07,0,0,0,128,64ZM58.34,69.66A8,8,0,0,0,69.66,58.34l-16-16A8,8,0,0,0,42.34,53.66Zm0,116.68-16,16a8,8,0,0,0,11.32,11.32l16-16a8,8,0,0,0-11.32-11.32ZM192,72a8,8,0,0,0,5.66-2.34l16-16a8,8,0,0,0-11.32-11.32l-16,16A8,8,0,0,0,192,72Zm5.66,114.34a8,8,0,0,0-11.32,11.32l16,16a8,8,0,0,0,11.32-11.32ZM48,128a8,8,0,0,0-8-8H16a8,8,0,0,0,0,16H40A8,8,0,0,0,48,128Zm80,80a8,8,0,0,0-8,8v24a8,8,0,0,0,16,0V216A8,8,0,0,0,128,208Zm112-88H216a8,8,0,0,0,0,16h24a8,8,0,0,0,0-16Z',
  bolt: 'M213.85,125.46l-112,120a8,8,0,0,1-13.69-7l14.66-73.33L45.19,143.49a8,8,0,0,1-3-13l112-120a8,8,0,0,1,13.69,7L153.18,90.9l57.63,21.61a8,8,0,0,1,3,12.95Z',
  list: 'M208,32H48A16,16,0,0,0,32,48V208a16,16,0,0,0,16,16H208a16,16,0,0,0,16-16V48A16,16,0,0,0,208,32ZM192,184H64a8,8,0,0,1,0-16H192a8,8,0,0,1,0,16Zm0-48H64a8,8,0,0,1,0-16H192a8,8,0,0,1,0,16Zm0-48H64a8,8,0,0,1,0-16H192a8,8,0,0,1,0,16Z',
  grid: 'M120,56v48a16,16,0,0,1-16,16H56a16,16,0,0,1-16-16V56A16,16,0,0,1,56,40h48A16,16,0,0,1,120,56Zm80-16H152a16,16,0,0,0-16,16v48a16,16,0,0,0,16,16h48a16,16,0,0,0,16-16V56A16,16,0,0,0,200,40Zm-96,96H56a16,16,0,0,0-16,16v48a16,16,0,0,0,16,16h48a16,16,0,0,0,16-16V152A16,16,0,0,0,104,136Zm96,0H152a16,16,0,0,0-16,16v48a16,16,0,0,0,16,16h48a16,16,0,0,0,16-16V152A16,16,0,0,0,200,136Z',
  folders: 'M224,64H154.67L126.93,43.2a16.12,16.12,0,0,0-9.6-3.2H72A16,16,0,0,0,56,56V72H40A16,16,0,0,0,24,88V200a16,16,0,0,0,16,16H192.89A15.13,15.13,0,0,0,208,200.89V184h16.89A15.13,15.13,0,0,0,240,168.89V80A16,16,0,0,0,224,64Zm0,104H208V112a16,16,0,0,0-16-16H122.67L94.93,75.2a16.12,16.12,0,0,0-9.6-3.2H72V56h45.33L147.2,78.4A8,8,0,0,0,152,80h72Z',
  // 操作按钮图标（编辑/删除/保存/复制/生成/账号）
  pencil: 'M227.31,73.37,182.63,28.68a16,16,0,0,0-22.63,0L36.69,152A15.86,15.86,0,0,0,32,163.31V208a16,16,0,0,0,16,16H92.69A15.86,15.86,0,0,0,104,219.31L227.31,96a16,16,0,0,0,0-22.63ZM51.31,160l90.35-90.35,16.68,16.69L68,176.68ZM48,179.31,76.69,208H48Zm48,25.38L79.31,188l90.35-90.35h0l16.68,16.69Z',
  trash: 'M216,48H176V40a24,24,0,0,0-24-24H104A24,24,0,0,0,80,40v8H40a8,8,0,0,0,0,16h8V208a16,16,0,0,0,16,16H192a16,16,0,0,0,16-16V64h8a8,8,0,0,0,0-16ZM112,168a8,8,0,0,1-16,0V104a8,8,0,0,1,16,0Zm48,0a8,8,0,0,1-16,0V104a8,8,0,0,1,16,0Zm0-120H96V40a8,8,0,0,1,8-8h48a8,8,0,0,1,8,8Z',
  floppy: 'M219.31,72,184,36.69A15.86,15.86,0,0,0,172.69,32H48A16,16,0,0,0,32,48V208a16,16,0,0,0,16,16H208a16,16,0,0,0,16-16V83.31A15.86,15.86,0,0,0,219.31,72ZM208,208H184V152a16,16,0,0,0-16-16H88a16,16,0,0,0-16,16v56H48V48H172.69L208,83.31ZM160,72a8,8,0,0,1-8,8H96a8,8,0,0,1,0-16h56A8,8,0,0,1,160,72Z',
  copy: 'M216,32H88a8,8,0,0,0-8,8V80H40a8,8,0,0,0-8,8V216a8,8,0,0,0,8,8H168a8,8,0,0,0,8-8V176h40a8,8,0,0,0,8-8V40A8,8,0,0,0,216,32Zm-8,128H176V88a8,8,0,0,0-8-8H96V48H208Z',
  dice: 'M192,32H64A32,32,0,0,0,32,64V192a32,32,0,0,0,32,32H192a32,32,0,0,0,32-32V64A32,32,0,0,0,192,32ZM92,176a12,12,0,1,1,12-12A12,12,0,0,1,92,176Zm0-72a12,12,0,1,1,12-12A12,12,0,0,1,92,104Zm36,36a12,12,0,1,1,12-12A12,12,0,0,1,128,140Zm36,36a12,12,0,1,1,12-12A12,12,0,0,1,164,176Zm0-72a12,12,0,1,1,12-12A12,12,0,0,1,164,104Z',
  user: 'M230.93,220a8,8,0,0,1-6.93,4H32a8,8,0,0,1-6.92-12c15.23-26.33,38.7-45.21,66.09-54.16a72,72,0,1,1,73.66,0c27.39,8.95,50.86,27.83,66.09,54.16A8,8,0,0,1,230.93,220Z',
  // 密码显示/隐藏眼睛
  eye: 'M247.31,124.76c-.35-.79-8.82-19.58-27.65-38.41C194.57,61.26,162.88,48,128,48S61.43,61.26,36.34,86.35C17.51,105.18,9,124,8.69,124.76a8,8,0,0,0,0,6.5c.35.79,8.82,19.57,27.65,38.4C61.43,194.74,93.12,208,128,208s66.57-13.26,91.66-38.34c18.83-18.83,27.3-37.61,27.65-38.4A8,8,0,0,0,247.31,124.76ZM128,168a40,40,0,1,1,40-40A40,40,0,0,1,128,168Z',
  'eye-closed': 'M230.94,164A8,8,0,1,1,217.05,172l-19-33.2A123.23,123.23,0,0,1,162,155.46l5.87,35.22a8,8,0,0,1-6.58,9.21A8.4,8.4,0,0,1,160,200a8,8,0,0,1-7.88-6.69l-5.77-34.58a133.06,133.06,0,0,1-36.68,0l-5.77,34.58A8,8,0,0,1,96,200a8.4,8.4,0,0,1-1.32-.11,8,8,0,0,1-6.58-9.21L94,155.46a123.23,123.23,0,0,1-36.06-16.69L39,172A8,8,0,1,1,25.06,164l20-35a152.8,152.8,0,0,1-19.3-20,8,8,0,0,1,0-10.06C44.56,75.72,77.55,48,128,48s83.44,27.72,102.22,51a8,8,0,0,1,0,10.06,152.8,152.8,0,0,1-19.3,20Z',
  // 收藏星标 + 信息 + 确认 + 退出挥手
  star: 'M234.29,114.85l-45,38.83L203,211.75a16.4,16.4,0,0,1-24.5,17.82L128,198.49,77.47,229.57A16.4,16.4,0,0,1,53,211.75l13.76-58.07-45-38.83A16.46,16.46,0,0,1,31.08,86l59-4.76,22.76-55.08a16.36,16.36,0,0,1,30.27,0l22.75,55.08,59,4.76a16.46,16.46,0,0,1,9.37,28.86Z',
  'caret-down': 'M215.4,92.94A8,8,0,0,0,208,88H48a8,8,0,0,0-7.4,4.94,8.35,8.35,0,0,0,1.73,9.42l80,80a8,8,0,0,0,11.34,0l80-80A8.35,8.35,0,0,0,215.4,92.94Z',
  info: 'M128,24A104,104,0,1,0,232,128,104.11,104.11,0,0,0,128,24Zm-4,48a12,12,0,1,1-12,12A12,12,0,0,1,124,72Zm12,112a16,16,0,0,1-16-16V128a8,8,0,0,1,0-16,16,16,0,0,1,16,16v40a8,8,0,0,1,0,16Z',
  check: 'M216,40H40A16,16,0,0,0,24,56V200a16,16,0,0,0,16,16H216a16,16,0,0,0,16-16V56A16,16,0,0,0,216,40ZM205.66,85.66l-96,96a8,8,0,0,1-11.32,0l-40-40a8,8,0,0,1,11.32-11.32L104,164.69l90.34-90.35a8,8,0,0,1,11.32,11.32Z',
  wave: 'M219.31,98.46A88,88,0,1,1,67.08,186.77h0L26.15,115.88a16,16,0,0,1,27.69-16L72.4,132a8,8,0,0,0,13.86-8L47,56A16,16,0,0,1,74.69,40L114,108a8,8,0,1,0,13.85-8l-30-52a16,16,0,0,1,27.71-16L166,102.12A48.25,48.25,0,0,0,152,136a47.59,47.59,0,0,0,9.6,28.8,8,8,0,1,0,12.79-9.61A32,32,0,0,1,181,110.26a8,8,0,0,0,2.17-10.43L171.71,80a16,16,0,0,1,27.71-16l19.89,34.46Zm-29.37-57A43.74,43.74,0,0,1,216.74,62l.33.57a8,8,0,0,0,13.86-8L230.6,54a59.64,59.64,0,0,0-36.54-28,8,8,0,0,0-4.12,15.46ZM79.58,225.72A103.58,103.58,0,0,1,53.93,196a8,8,0,0,0-13.86,8,119.56,119.56,0,0,0,29.6,34.28,8,8,0,0,0,9.91-12.56Z',
  'arrow-left': 'M224,128a8,8,0,0,1-8,8H59.31l58.35,58.34a8,8,0,0,1-11.32,11.32l-72-72a8,8,0,0,1,0-11.32l72-72a8,8,0,0,1,11.32,11.32L59.31,120H216A8,8,0,0,1,224,128Z',
};

/* 根据 key 和 size 生成 SVG 字符串：fill 图标优先，否则用 stroke */
function svgIcon(key, size){
  if (SVG_ICONS_FILL[key]) {
    return `<svg class="svg-fill" width="${size}" height="${size}" viewBox="0 0 256 256" aria-hidden="true"><path d="${SVG_ICONS_FILL[key]}"/></svg>`;
  }
  const inner = SVG_ICONS_STROKE[key] || '';
  return `<svg class="svg-icon" width="${size}" height="${size}" viewBox="0 0 24 24" aria-hidden="true">${inner}</svg>`;
}

/* ============================================================
   应用状态
   ============================================================ */
const state = {
  connected:false,
  /* 启动页 modal 状态：'expanded'(展开盖住内容区) | 'minimized'(隐藏 modal+显示状态栏连接入口) | 'hidden'(已连接)。
     未连接时，切到 tools/settings 自动 minimized；切回 vault/notes/security 自动 expanded；
     用户点状态栏连接入口调 expandStartupModal() 恢复 expanded。 */
  startupMinimized:false,
  currentNav:'vault',
  viewMode:'list',
  sortMode:'updated',
  filter:'all',
  noteFilter:'all',
  noteSort:'UPDATED',
  search:'',
  settingsSearch:'',
  expandedId:null,
  splitSelectedId:1,
  passwordVisible:{},
  recoveryVisible:null,
  clipboardTimer:null,
  clipboardSeconds:0,
  quickBarVisible:false,
  quickBarIndex:0,
  quickBarResults:[],
  quickBarAutohideSec:30,
  theme:'dark',
  genCharset:{lower:true,upper:true,digit:true,symbol:true},
  genAvoidAmbiguous:false,
  genPassword:'',
  notesEditId:null,
  notesCardOpenId:null,
  notesCardEditId:null,
  notesCardDraft:null,
  notesCardsColumns:0,
  fixQueue:null,
  fixIndex:0,
  fixResults:{},
  windowMaximized:false,
  lang:'zh',  // 界面语言：'zh'（默认中文） | 'en'（English）
  /* 超时自动锁定配置 —— Win 端对应 settings.json 的 auto_lock 字段
     enabled: 是否启用，timeout: 阈值分钟数（默认 5 分钟，与 KeePass/1Password 一致）
     lastActivityTime: 最后一次用户活动时间戳，idleCheckTimer: 轮询定时器 id
     autoLockTriggered: 标记本次锁定是否由超时触发（用于 Toast 区分手动/自动） */
  autoLock:{enabled:true, timeout:5},
  lastActivityTime:Date.now(),
  idleCheckTimer:null,
  autoLockTriggered:false,
  /* QuickBar 全局热键配置 —— Win 端对应 settings.json 的 quickbar_hotkey 字段
     默认 'Alt+P'（P=Password 语义，左右手分工，不与 Win 系统/1Password/QQ/输入法冲突）
     格式：'<修饰键>+<主键>'，修饰键可组合（如 'Ctrl+Shift+P'），主键为 KeyboardEvent.key
     取值范围（见 isHotkeyMainKey）：字母/数字/F1-F12/` - = [ ] \ ; ' , . / Space Tab Enter
     历史变更：原默认 'Ctrl+Shift+Space'（与 1Password Quick Access 撞键 + 三键卡手），2026-07 改为 'Alt+P' */
  quickBarHotkey:'Alt+P',
  /* 热键录制状态机：null=未录制 / 'recording'=等待按键 / 'confirming'=待保存
     录制时临时捕获 keydown，按 Esc 取消，按合法组合则填入并提示冲突检测 */
  hotkeyRecording:null,
};

/* ============================================================
   通用工具
   ============================================================ */
const $ = (s,r=document)=>r.querySelector(s);
const $$ = (s,r=document)=>[...r.querySelectorAll(s)];

/* ============================================================
   i18n 国际化基础设施
   ============================================================
   机制：
   - HTML 元素通过 data-i18n="key" 标记（textContent）
   - data-i18n-placeholder="key" 标记输入框 placeholder
   - data-i18n-title="key" 标记 title（tooltip）
   - setLang(lang) 遍历所有标记元素，按当前语言更新内容
   - 翻译表 I18N.zh / I18N.en 由主代理（强度检测区域）+ 子代理（其他区域）共同填充
   key 命名规范：<区域>.<元素>.<用途>，如 tool.check.title、vault.button.add
   ============================================================ */
const I18N = {
  zh: {
    /* —— 强度检测区域（主代理填充）—— */
    'tool.check.title': '密码强度检测',
    'tool.tab.gen': '密码生成器',
    /* —— 工具页生成器 —— */
    'tool.gen.label.length': '密码长度',
    'tool.gen.label.charset': '字符类型',
    'tool.gen.charset.lower': '小写字母 a-z',
    'tool.gen.charset.upper': '大写字母 A-Z',
    'tool.gen.charset.digit': '数字 0-9',
    'tool.gen.charset.symbol': '特殊字符 !@#$%^&*()[]',
    'tool.gen.avoidAmbiguous': '排除易混淆字符 0O1lI',
    'tool.gen.error.length': '密码长度必须为 1–1024 的整数',
    'tool.gen.error.needCharset': '请至少选择一种字符类型',
    'tool.gen.error.tooShort': '密码长度不能小于已选字符类型数量',
    'tool.gen.output.placeholder': '点击下方按钮生成密码',
    'tool.gen.button.generate': '生成密码',
    'tool.gen.button.copy': '复制',
    'tool.gen.button.save': '保存为记录',
    'tool.gen.button.reset': '恢复默认配置',
    'tool.tab.check': '密码强度检测',
    'tool.check.input.label': '输入要检测的密码',
    'tool.check.input.placeholder': '输入密码实时检测...',
    'tool.check.platform.placeholder': '平台名（可选，如 GitHub、淘宝）',
    'tool.check.account.placeholder': '账号名（可选，如 user@example.com）',
    'tool.check.rating.label': '强度评级',
    'tool.check.level.weak': '弱',
    'tool.check.level.fair': '中',
    'tool.check.level.strong': '强',
    'tool.check.crackTime.title': '破解时间预估',
    'tool.check.crackTime.online_throttling': '在线攻击（有锁限 100/小时）',
    'tool.check.crackTime.online_no_throttling': '在线攻击（无锁限 10/秒）',
    'tool.check.crackTime.offline_slow': '离线破解（慢哈希 10⁴/秒）',
    'tool.check.crackTime.offline_fast': '离线破解（快哈希 10¹⁰/秒）',
    'tool.check.risks.title': '风险提示',
    'tool.check.suggestions.title': '改进建议',
    'tool.check.detecting': '正在检测…',
    'tool.check.error.limit': '输入超过检测上限，请缩短后重试',
    'tool.check.feedback.EMPTY': '请输入密码',
    'tool.check.feedback.TOO_SHORT': '密码长度过短',
    'tool.check.feedback.ADD_WORDS': '增加一两个单词或字符',
    'tool.check.feedback.AVOID_REPEATS': '避免重复单词和字符',
    'tool.check.feedback.AVOID_SEQUENCES': '避免顺序字符',
    'tool.check.feedback.AVOID_RECENT_YEARS': '避免近期年份',
    'tool.check.feedback.AVOID_DATES': '避免日期和相关年份',
    'tool.check.feedback.AVOID_COMMON_PASSWORD': '避免常见弱密码',
    'tool.check.feedback.AVOID_COMMON_WORD': '避免常见单词',
    'tool.check.feedback.AVOID_NAMES': '避免姓名',
    'tool.check.feedback.AVOID_USER_DATA': '避免平台名或账号等相关信息',
    'tool.check.feedback.AVOID_KEYBOARD_PATTERN': '避免键盘走位模式',
    'tool.check.feedback.AVOID_LEET_PATTERN': '可预测的字符替换不能显著提高强度',
    'tool.check.feedback.DICTIONARY_MATCH': '密码包含字典中的常见模式',
    'tool.check.bucket.INSTANT': '立即',
    'tool.check.bucket.SECONDS': '数秒',
    'tool.check.bucket.MINUTES': '数分钟',
    'tool.check.bucket.HOURS': '数小时',
    'tool.check.bucket.DAYS': '数天',
    'tool.check.bucket.MONTHS': '数月',
    'tool.check.bucket.YEARS': '数年',
    'tool.check.bucket.CENTURIES': '数百年以上',
    /* —— 设置面板语言 segment（主代理填充）—— */
    'settings.lang.name': '语言',
    'settings.lang.desc': '界面显示语言',
    'settings.lang.aria': '切换界面语言，当前中文',
    'settings.lang.title': '点击切换语言（当前：中文）',
    'settings.fontScale.name': '界面字号',
    'settings.fontScale.desc': '统一调整应用内文字大小',
    /* —— 连接面板（startup）—— */
    'startup.title': '小仓',
    'startup.subtitle': '打开已有数据库，或选择新路径创建',
    'startup.label.path': '数据库路径',
    'startup.input.path.placeholder': '输入或选择数据库路径',
    'startup.label.password': '主密码',
    'startup.input.password.placeholder': '输入主密码',
    'startup.button.connect': '连接 / 创建',
    'startup.button.browse': '浏览数据库',
    'common.password.show': '显示密码',
    'common.password.hide': '隐藏密码',
    'common.current': '{name}，当前：{value}',
    'connection.connecting': '连接中...',
    'connection.error.invalid_password': '主密码错误，还可尝试 {n} 次',
    'connection.error.locked_too_many': '密码错误次数过多，该数据库已锁定 24 小时',
    'connection.error.path_not_found': '数据库文件不存在，请重新选择；手动输入新路径可创建数据库',
    'connection.error.permission_denied': '无法访问该位置，请检查目录的读取或写入权限',
    'connection.error.corrupt_or_unreadable': '数据库文件已损坏或无法读取，请检查文件或从备份恢复',
    'connection.locked.button': '已锁定',
    'startup.divider.recent': '最近使用',
    'startup.recent.select': '选择',
    'startup.recent.remove': '移除',
    /* —— 启动页 modal 最小化提示条（未连接时切到工具/设置显示） —— */
    'startup.bar.title': '未连接数据库',
    'startup.bar.action': '点击连接',
    'startup.dependent.disabled.tip': '请先连接数据库后再使用此功能',
    'startup.empty.vault': '未连接数据库，密码记录不可见',
    'startup.empty.notes': '未连接数据库，加密记事不可见',
    'startup.empty.security': '未连接数据库，无法进行安全体检',
    /* —— 窗口标题栏 —— */
    'titlebar.app.title': '小仓',
    'app.workspace': '小仓工作区',
    'titlebar.button.minimize': '最小化',
    'titlebar.button.maximize': '最大化',
    'titlebar.button.restore': '还原',
    'titlebar.button.close': '关闭',
    /* —— 侧栏导航 —— */
    'nav.vault': '密码库',
    'nav.notes': '记事本',
    'nav.security': '体检',
    'nav.tools': '工具',
    'nav.settings': '设置',
    'nav.help': '帮助',
    'topbar.title.help': '帮助',
    'nav.lock': '锁定',
    /* —— 顶栏 —— */
    'topbar.title.connect': '连接数据库',
    'topbar.title.vault': '密码库',
    'topbar.title.notes': '记事本',
    'topbar.title.security': '安全体检',
    'topbar.title.tools': '工具',
    'topbar.title.settings': '设置',
    'topbar.search.placeholder': '搜索条目名称 / 账号...',
    'topbar.search.results': '找到 {n} 条结果',
    'topbar.search.limit': '搜索最多 128 个字符',
    'settings.search.placeholder': '搜索设置...',
    'settings.search.empty': '没有匹配的设置，请更换关键词或清空搜索',
    'topbar.button.theme': '切换主题',
    'topbar.button.quickbar': 'Quick Bar ({key})',
    /* —— QuickBar —— */
    'quickbar.input.placeholder': '搜索条目名称或输入命令 (gen 20)...',
    'quickbar.copy.pwd': '复制密码',
    'quickbar.copy.acc': '复制账号',
    'quickbar.autohide': '30 秒无操作自动隐藏',
    'quickbar.clear': '清空搜索',
    'quickbar.cmd.generate': '生成 {n} 位强密码 — 按 Enter 复制',
    'quickbar.cmd.hint': '将生成包含大小写字母、数字、特殊字符的强密码',
    'quickbar.cmd.copied': '已复制',
    'quickbar.cmd.range': '生成长度仅支持 4–1024 位',
    'quickbar.query.limit': '搜索内容最多 128 个字符，请删减后重试',
    'quickbar.results.more': '共 {n} 条，继续输入以缩小范围',
    'quickbar.hint.notfound': '未找到匹配 "{q}" 的记录',
    'quickbar.hint.empty': '输入条目名称搜索，或输入 "gen 20" 生成密码',
    /* —— 密码库面板 —— */
    'vault.filter.all': '全部',
    'vault.filter.favorite': '收藏',
    'vault.filter.weak': '弱密码',
    'vault.filter.duplicate': '重复',
    'vault.filter.similar': '相似名称',
    'vault.view.list': '列表模式',
    'vault.view.split': '分屏模式',
    'vault.sort.updated': '最近更新',
    'vault.sort.name': '名称 A-Z',
    'vault.sort.strength': '按强度',
    'vault.sort.label': '密码库排序',
    'vault.button.add': '+ 新建',
    'vault.empty': '没有匹配的记录',
    'vault.split.empty': '从左侧选择一条记录查看详情',
    'vault.strength.label': '强度',
    /* —— 密码库列表项（动态）—— */
    'vault.detail.account': '账号',
    'vault.detail.password': '密码',
    'vault.detail.notes': '备注',
    'vault.detail.updated': '更新于',
    'vault.detail.totp': '验证码',
    'vault.detail.recovery': '恢复码',
    'vault.recovery.hidden': '恢复码已遮掩',
    'vault.recovery.visible': '恢复码已显示',
    'vault.recovery.unmarked': '未标记已用',
    'vault.recovery.used': '已标记已用',
    'vault.recovery.show': '查看恢复码',
    'vault.recovery.hide': '隐藏恢复码',
    'vault.recovery.copy': '复制恢复码',
    'vault.recovery.mark': '标记已用',
    'vault.recovery.undo': '撤销已用标记',
    'vault.button.edit': '编辑',
    'vault.button.delete': '删除',
    'vault.copy.account': '复制账号',
    'vault.copy.password': '复制密码',
    'vault.copy.totp': '复制验证码',
    'vault.toggle.visible': '显示/隐藏',
    'vault.regenerate': '生成新密码',
    'vault.dup.tag': '重复组',
    'vault.similar.tag': '相似组',
    /* —— 记事本面板 —— */
    'notes.filter.all': '全部',
    'notes.filter.favorite': '收藏',
    'notes.filter.recent': '最近',
    'notes.sort.name': '标题 A-Z',
    'notes.sort.label': '记事排序',
    'notes.button.add': '+ 新建记事',
    'notes.empty': '没有记事内容',
    'notes.cards.read': '查看全文',
    'notes.cards.back': '返回卡片',
    'notes.cards.updated': '更新于',
    'notes.cards.unsaved': '请先保存或取消正在编辑的记事。',
    'notes.cards.search.placeholder': '搜索记事...',
    /* —— 记事本列表项（动态）—— */
    'notes.detail.favorite': '收藏',
    'notes.fav.yes': '已收藏',
    'notes.fav.no': '未收藏',
    'notes.toggle.favorite': '切换收藏',
    'notes.input.title': '标题',
    'notes.input.content': '输入内容...',
    'notes.button.edit': '编辑对话框',
    'notes.button.delete': '删除',
    'notes.button.save': '保存',
    'notes.default.title': '新建记事',
    'notes.default.content': '在此输入内容...',
    /* —— 安全体检面板 —— */
    'security.score.label': '健康分',
    'security.grade.excellent': '优秀',
    'security.grade.good': '良好',
    'security.grade.fair': '一般',
    'security.grade.risk': '风险',
    'security.grade.none': '待评估',
    'security.hero.title.excellent': '您的密码库非常安全',
    'security.hero.title.good': '您的密码库整体安全',
    'security.hero.title.fair': '您的密码库存在隐患',
    'security.hero.title.risk': '您的密码库风险较高',
    'security.hero.title.none': '暂无密码记录',
    'security.hero.desc': '发现 {issues}。建议尽快修复以提升安全等级。',
    'security.hero.clean': '未发现安全问题，继续保持',
    'security.hero.empty': '请先添加密码记录后再进行体检',
    'security.hero.weak': '{n} 个弱密码',
    'security.hero.dup': '{n} 组重复密码',
    'security.hero.stale': '{n} 条长期未更换记录',
    'security.issue.weak': '弱密码',
    'security.issue.duplicate': '重复密码',
    'security.issue.stale': '长期未更换',
    'security.count.weak': '3 条',
    'security.button.fixall': '逐个引导修复',
    /* —— 安全体检动态 —— */
    'security.count.group': '{n} 组',
    'security.count.items': '{n} 条',
    'security.desc.weak': '密码强度过低，建议更换为更强密码',
    'security.desc.dup': '相同密码一旦泄露会波及多个账户',
    'security.desc.dupName': '使用了相同密码',
    'security.dup.join': ' 和 ',
    'security.desc.stale': '超过 {n} 天阈值，建议尽快更新密码',
    'security.name.stale': '{n} 天未更换',
    'security.empty.weak': '无弱密码',
    'security.empty.dup': '无重复密码',
    'security.empty.stale': '无长期未更换记录',
    'security.button.fix': '修复 →',
    'security.button.view': '查看 →',
    /* —— 状态栏 —— */
    'status.disconnected': '未连接',
    'status.connect.prefix': '已连接 ',
    'status.clipboard.ready': '剪贴板: 就绪',
    'status.clipboard.group': '剪贴板状态',
    'status.clipboard.cleared': '剪贴板已清空',
    'status.clipboard.countdown': '剪贴板: {n}s 后清空',
    'status.clipboard.clearNow': '立即清空',
    /* —— Toast 提示 —— */
    'toast.connected': '已连接到 ',
    'toast.fillPath': '已填充数据库路径，请输入主密码后点击"连接/创建"',
    'toast.browse': '已打开文件选择对话框（原型演示）',
    'toast.copied.suffix': '已复制到剪贴板',
    'toast.deleted.prefix': '已删除 ',
    'toast.notFound': '未找到记录',
    'toast.located.prefix': '已定位到 ',
    'toast.located.suffix': '，即将打开编辑对话框',
    'toast.dup.shown': '已显示所有重复密码条目，相同颜色边框代表同一组',
    'toast.noIssues': '当前没有需要修复的安全问题',
    'toast.fav.added': '已添加到收藏',
    'toast.fav.removed': '已取消收藏',
    'toast.note.saved': '记事已保存',
    'toast.note.created': '已新建记事',
    /* —— 通用强度标签 —— */
    'common.strength.weak': '弱',
    'common.strength.fair': '中',
    'common.strength.strong': '强',
    'common.strength.pending': '待检测',
    'common.strength.checking': '检测中',
    'common.strength.failed': '检测失败',
    /* —— 引导修复对话框 —— */
    'fix.modal.title': '逐个引导修复',
    'fix.progress.label': '修复进度',
    'fix.progress.fixed': '已处理 {done} / {total}',
    'fix.progress.complete': '本次引导已完成',
    'fix.progress.continue': '是否继续修复下一个？',
    'fix.progress.summary': '共 {total} 项 · 已处理 {done} 项 · 跳过 {skipped} 项',
    'fix.guide.hint': '点击「前往编辑」将跳转到该记录并打开编辑对话框。<br>本引导不会自动修改任何密码，由您手动完成修改后保存。',
    'fix.guide.multiIssue': '该记录有 {n} 个问题，修改密码可同时解决：',
    'fix.button.back': '返回',
    'fix.button.skip': '跳过此项',
    'fix.button.goto': '前往编辑',
    'fix.button.finish': '完成',
    'fix.button.continue': '继续修复',
    'fix.button.prev': '上一个',
    'fix.button.skipThis': '跳过此项',
    'fix.button.abandon': '放弃引导',
    'fix.banner.title': '正在引导修复',
    'fix.banner.remaining': '剩余 {n} 项',
    'fix.banner.continue': '继续引导',
    'fix.banner.abandon': '放弃引导',
    'fix.toast.abandoned': '已放弃引导修复',
    /* —— 主题切换 Toast —— */
    'toast.theme.dark': '已切换到深色模式',
    'toast.theme.light': '已切换到浅色模式',
    'toast.theme.auto': '已切换到跟随系统',
    /* —— 生成器 Toast —— */
    'toast.gen.needCharset': '请至少选择一种字符类型',
    'toast.gen.generated': '密码已生成',
    'toast.gen.needGenFirst': '请先生成密码',
    'toast.gen.saved': '已保存为密码记录，可在密码库查看',
    'toast.gen.needCharsetTools': '请先在工具页选择字符类型',
    'toast.gen.generatedShown': '已生成新密码并显示明文',
    'toast.gen.generatedNew': '已生成新密码',
    'gen.default.platform': '新建记录',
    'gen.default.notes': '由密码生成器创建',
    /* —— 窗口控制 Toast —— */
    'toast.minimized': '已模拟最小化窗口',
    'toast.maximized': '已模拟最大化窗口',
    'toast.restored': '已模拟还原窗口',
    'toast.exited': '已模拟退出',
    /* —— 密码对话框 Toast —— */
    'toast.pwd.added': '已新增密码记录',
    'toast.pwd.updated': '已更新密码记录',
    'toast.pwd.deleted.generic': '密码记录已删除',
    'toast.note.deleted.generic': '记事已删除',
    'toast.operation.failed': '操作失败，请查看当前错误提示',
    /* —— 记事对话框 Toast —— */
    'toast.note.dialogAdded': '已新增记事',
    'toast.note.dialogNotFound': '未找到记事',
    'toast.note.dialogUpdated': '已更新记事',
    /* —— 修改密码 Toast —— */
    'toast.keyChanged': '密码修改成功，请重新连接数据库',
    /* —— 设置导出 Toast —— */
    'toast.exported': '已导出 10 条记录到 backup.json',
    /* —— 通用对话框标签 —— */
    'dialog.label.favorite': '收藏',
    'dialog.button.cancel': '取消',
    'dialog.button.save': '保存',
    'dialog.button.confirm': '确认',
    'dialog.button.delete': '删除',
    'dialog.button.close': '关闭对话框',
    'dialog.toggle.visible': '显示/隐藏',
    'dialog.generate': '生成密码',
    /* —— 密码对话框 —— */
    'dialog.pwd.title.add': '＋ 新增密码记录',
    'dialog.pwd.title.edit': '编辑密码记录',
    'dialog.pwd.label.platform': '平台',
    'dialog.pwd.label.account': '账号',
    'dialog.pwd.label.password': '密码',
    'dialog.pwd.label.notes': '备注',
    'dialog.pwd.label.totp': 'TOTP 密钥',
    'dialog.pwd.label.recovery': '恢复码（可选）',
    'dialog.pwd.recovery.empty': '一行一个。请另留一份独立安全副本；本库打不开时也无法取用。',
    'dialog.pwd.recovery.keep': '已保存 {n} 条；留空保留，输入新组则替换。原码不回填。',
    'dialog.pwd.recovery.remove': '移除整组恢复码',
    'dialog.pwd.recovery.undo': '保留已有恢复码',
    'dialog.pwd.recovery.confirm': '替换或移除整组恢复码？此操作会重置本地已用标记。',
    'dialog.pwd.recovery.invalid': '检查重复行和长度；恢复码未保存。',
    'dialog.pwd.placeholder.platform': '例如 GitHub · 个人',
    'dialog.pwd.placeholder.account': '账号或邮箱',
    'dialog.pwd.placeholder.password': '输入或点击右侧图标生成',
    'dialog.pwd.placeholder.notes': '备注信息...',
    'dialog.pwd.placeholder.totp': 'Base32 密钥（如 JBSWY3DPEHPK3PXP），留空则不启用',
    'dialog.pwd.placeholder.totpReplace': '输入新 Base32 密钥以替换',
    'dialog.pwd.totp.enabledHint': '当前已启用；留空保留，输入新 Base32 密钥则替换。',
    'dialog.pwd.totp.disabledHint': '当前未启用；输入 Base32 密钥即可启用。',
    'dialog.pwd.totp.remove': '移除现有 TOTP',
    'dialog.pwd.totp.undoRemove': '撤销移除',
    'dialog.pwd.totp.removeHint': '保存后将移除现有 TOTP；密钥不会显示在界面中。',
    'dialog.pwd.error.platformEmpty': '平台名不能为空',
    'dialog.pwd.error.platformExists': '平台名已存在，请使用不同的名称',
    'dialog.pwd.error.save_failed': '保存失败，请重试',
    'dialog.pwd.error.duplicate': '平台名已存在，请使用不同的名称',
    'dialog.pwd.error.revision_conflict': '记录已在别处发生变化。你的未提交内容仍保留；请加载最新内容后再编辑。',
    'dialog.pwd.error.delete_failed': '安全连接未完成，请退出隔离候选后重试。',
    'dialog.pwd.action.reloadLatest': '加载最新内容',
    'dialog.pwd.action.retryAuthorization': '重新取得保存权限',
    'dialog.delete.title': '删除密码',
    'dialog.delete.confirm': '确定要删除「{platform}」的密码吗？',
    'dialog.delete.desc': '删除后无法恢复。',
    /* —— 记事对话框 —— */
    'dialog.note.title.add': '＋ 新增记事',
    'dialog.note.title.edit': '编辑记事',
    'dialog.note.label.title': '标题',
    'dialog.note.label.content': '内容',
    'dialog.note.placeholder.title': '输入记事标题',
    'dialog.note.placeholder.content': '输入记事内容...',
    'dialog.note.error.titleEmpty': '标题不能为空',
    'dialog.note.error.save_failed': '保存失败，请重试',
    'notes.scroll.more': '↓ 可向下滚动查看更多',
    'notes.scroll.bottom': '✓ 已到正文底部',
    'notes.scroll.position': '位置 {0}% · 共 {1} 行',
    'dialog.note.delete.title': '删除记事',
    'dialog.note.delete.confirm': '确定要删除记事「{title}」吗？',
    'dialog.note.delete.desc': '此操作无法撤销。',
    /* —— 修改密码对话框 —— */
    'dialog.key.title': '修改数据库密码',
    'dialog.key.warning': '⚠ 修改密码后将全量重新加密所有数据，请牢记新密码。',
    'dialog.key.label.current': '当前密码',
    'dialog.key.label.new': '新密码',
    'dialog.key.label.confirm': '确认密码',
    'dialog.key.placeholder.current': '输入当前密码',
    'dialog.key.placeholder.new': '输入新密码',
    'dialog.key.placeholder.confirm': '再次输入新密码',
    'dialog.key.error.current': '当前密码不正确',
    'dialog.key.error.failed': '修改密码失败，数据库尚未修改，请重试。',
    'dialog.key.error.failed_restored': '修改密码失败，原数据库已安全恢复。请使用原密码重新连接。',
    'dialog.key.error.recovery_failed': '修改密码失败，且自动恢复未完成。请停止操作并保留数据库文件。',
    'dialog.key.changing': '正在修改…',
    'dialog.key.progress': '正在修改…',
    'dialog.key.error.unchanged': '修改未完成，原数据库未改变。请稍后重试。',
    'dialog.key.indicator.empty': '○ 密码将被清空',
    'dialog.key.indicator.match': '✓ 密码匹配',
    'dialog.key.indicator.mismatch': '✗ 密码不匹配',
    /* —— 导入导出对话框 Toast —— */
    'toast.ie.exported': '已导出 {n} 条记录到 {file}',
    'toast.ie.imported': '已导入 {added} 条，覆盖 {updated} 条，跳过 {skipped} 条',
    'toast.ie.no_changes': '没有数据发生变化',
    /* —— 导入导出对话框 —— */
    'dialog.ie.title.export': '导出数据',
    'dialog.ie.title.import': '导入数据',
    'dialog.ie.mode.export': '导出',
    'dialog.ie.mode.import': '导入',
    'dialog.ie.format.label': '格式',
    'dialog.ie.format.encrypted': 'JSON 加密备份',
    'dialog.ie.format.encrypted.hint': '使用独立密码加密，跨库迁移安全',
    'dialog.ie.scope.label': '范围',
    'dialog.ie.scope.all': '全部（密码+记事）',
    'dialog.ie.scope.passwords': '仅密码',
    'dialog.ie.scope.notes': '仅记事',
    'dialog.ie.path.label': '文件路径',
    'dialog.ie.path.placeholder.export': '选择导出保存位置...',
    'dialog.ie.path.placeholder.import': '选择备份文件路径...',
    'dialog.ie.browse': '浏览',
    'dialog.ie.browse.prompt': '请输入文件路径（演示态，Win 端使用系统文件选择器）',
    'dialog.ie.password.label': '加密密码',
    'dialog.ie.password.placeholder': '设置备份加密密码',
    'dialog.ie.password.placeholder.export': '设置备份加密密码',
    'dialog.ie.password.placeholder.import': '输入备份文件密码',
    'dialog.ie.password.hint': '此密码与数据库主密码独立，用于加密/解密备份文件，丢失后无法恢复',
    'dialog.ie.password.confirm.label': '确认密码',
    'dialog.ie.password.confirm.placeholder': '再次输入加密密码',
    'dialog.ie.password.indicator.empty': '○ 请输入并确认备份密码',
    'dialog.ie.password.indicator.match': '✓ 备份密码一致',
    'dialog.ie.password.indicator.mismatch': '✗ 两次输入的备份密码不一致',
    'dialog.ie.warning.export': '⚠️ 导出文件使用您设置的密码加密，请妥善保管密码，丢失后无法恢复',
    'dialog.ie.preview.label': '导入预览',
    'dialog.ie.preview.empty': '请选择备份文件并输入密码后点击「预览」',
    'dialog.ie.preview.button': '预览',
    'dialog.ie.preview.summary': '备份含 {total} 条记录（密码 {pw} 条，记事 {note} 条）',
    'dialog.ie.preview.conflict': '检测到 {n} 条冲突（同一条目名称已存在）',
    'dialog.ie.conflict.label': '冲突解决',
    'dialog.ie.conflict.overwrite_all': '全部覆盖',
    'dialog.ie.conflict.skip_all': '全部跳过',
    'dialog.ie.conflict.overwrite': '覆盖',
    'dialog.ie.conflict.skip': '跳过',
    'dialog.ie.conflict.undecided': '待决定',
    'dialog.ie.conflict.help': '请对照两侧内容再决定：覆盖会用右侧备份内容完整替换左侧当前记录。',
    'dialog.ie.conflict.current': '当前数据库已有内容',
    'dialog.ie.conflict.incoming': '备份文件中的内容',
    'dialog.ie.conflict.account': '账号',
    'dialog.ie.conflict.show_account': '查看完整账号',
    'dialog.ie.conflict.show_platform': '查看完整名称',
    'dialog.ie.conflict.password': '密码',
    'dialog.ie.conflict.notes': '备注',
    'dialog.ie.conflict.totp': '动态验证码',
    'dialog.ie.conflict.show_password': '查看',
    'dialog.ie.conflict.hide_password': '隐藏',
    'dialog.ie.conflict.show_notes': '查看备注',
    'dialog.ie.conflict.empty': '（空）',
    'dialog.ie.execute.export': '开始导出',
    'dialog.ie.execute.import': '开始导入',
    'dialog.ie.error.path': '请先选择文件路径',
    'dialog.ie.error.password': '请输入加密密码',
    'dialog.ie.error.mismatch': '两次输入的密码不一致',
    'dialog.ie.error.preview': '请先点击预览确认导入内容',
    'dialog.ie.error.undecided': '还有 {n} 条冲突未决定，请逐项选择覆盖或跳过',
    'dialog.ie.recovery.repreview': '导入未完成。请重新输入备份密码并点击预览后重试。',
    'dialog.ie.recovery.reselect': '预览已失效。请重新选择备份文件并预览。',
    'dialog.ie.recovery.reread': '字段查看已失效，请重新点击查看。',
    'dialog.ie.progress.export': '正在加密并写入备份，请稍候…',
    'dialog.ie.progress.import': '正在安全导入数据，请稍候…',
    /* —— 设置导入导出按钮 —— */
    'settings.db.ie.button': '打开',
    /* —— 设置面板 —— */
    'settings.group.appearance': '外观',
    'settings.group.startupWindow': '启动与窗口',
    'settings.group.quickbar': '快捷搜索',
    'settings.group.general': '通用',
    'settings.theme.name': '主题模式',
    'settings.theme.desc': '切换浅色 / 深色 / 跟随系统',
    'settings.theme.light': '浅色',
    'settings.theme.dark': '深色',
    'settings.theme.auto': '自动',
    'settings.option.current': '切换选项，当前：{value}',
    'settings.option.title': '点击切换（当前：{value}）',
    'settings.autofill.name': '启动时自动填充',
    'settings.autofill.desc': '打开应用时自动填入上次数据库路径',
    'settings.autofill.aria': '切换启动时自动填充',
    'settings.group.view': '视图',
    'settings.view.default.name': '默认视图模式',
    'settings.view.default.desc': '启动时密码库默认显示方式',
    'settings.view.list': '列表',
    'settings.view.split': '分屏',
    'settings.sidebar.text.name': '侧边栏显示文字',
    'settings.sidebar.text.desc': '在图标下方显示导航文字',
    'settings.sidebar.text.aria': '切换侧边栏文字',
    'settings.group.clipboard': '剪贴板',
    'settings.clipboard.clear.name': '清空模式',
    'settings.clipboard.clear.desc': '复制后自动倒计时清空',
    'settings.clipboard.clear.countdown': '倒计时',
    'settings.clipboard.clear.manual': '手动',
    'settings.clipboard.duration.name': '倒计时时长',
    'settings.clipboard.duration.desc': '复制后多少秒自动清空剪贴板',
    'settings.group.tray': '系统托盘',
    'settings.tray.close.name': '关闭按钮行为',
    'settings.tray.close.desc': '点击关闭时最小化到托盘或退出',
    'settings.tray.close.minimize': '最小化',
    'settings.tray.close.exit': '退出',
    'settings.tray.close.saved': '关闭行为已保存',
    'settings.tray.quickbar.name': '启用 Quick Bar',
    'settings.tray.quickbar.desc': '全局快捷键唤出快速搜索条',
    'settings.tray.quickbar.aria': '切换 Quick Bar',
    'settings.quickbar.timeout.name': 'Quick Bar 空闲隐藏',
    'settings.quickbar.timeout.desc': 'Quick Bar 无操作多少秒后自动隐藏',
    'settings.unit.seconds': '秒',
    /* —— Quick Bar 热键自定义 —— */
    'settings.hotkey.name': 'Quick Bar 热键',
    'settings.hotkey.desc': '唤出 Quick Bar 的全局快捷键，点击右侧修改',
    'settings.hotkey.modify': '修改',
    'settings.hotkey.recording': '按下组合键…（Esc 取消）',
    'settings.hotkey.canceled': '已取消热键修改',
    'settings.hotkey.invalid': '不支持的按键：{key}，请使用字母/数字/F1-F12/符号键',
    'settings.hotkey.need_modifier': '需要至少一个修饰键（Ctrl/Alt/Shift/Win）',
    'settings.hotkey.conflict': '热键 {key} 与 {app} 冲突，已保存但可能失效，建议换一个',
    'settings.hotkey.saved': '热键已设为 {key}',
    'settings.group.database': '数据库管理',
    'settings.db.current.name': '当前数据库',
    'settings.db.current.desc': '已连接的加密数据库文件',
    'settings.db.current.info': 'demo.db · 10 条记录',
    'settings.db.current.disconnected': '未连接',
    'settings.db.current.records': '条记录',
    'settings.db.changepwd.name': '修改数据库密码',
    'settings.db.changepwd.desc': '全量重新加密所有数据',
    'settings.db.changepwd.button': '修改密码',
    'settings.db.transfer.name': '设备传输',
    'settings.db.transfer.desc': '与附近设备核对连接，发送或接收密码库资料',
    'settings.db.ie.name': '导入导出数据',
    'settings.db.ie.desc': '加密备份或从备份恢复',
    'settings.group.security': '安全',
    'settings.security.stale.name': '长期未更换阈值',
    'settings.security.stale.desc': '超过该天数未更换的密码将告警',
    'settings.security.autolock.name': '超时自动锁定',
    'settings.security.autolock.desc': '无操作达到阈值时锁定；电脑睡眠始终锁定',
    'settings.security.autolock.aria': '切换超时自动锁定',
    'settings.security.autolock.timeout.name': '自动锁定阈值',
    'settings.security.autolock.timeout.desc': '无操作多少分钟后自动锁定',
    'settings.unit.days': '天',
    'settings.unit.minutes': '分',
    'toast.autolocked': '因长时间无操作已自动锁定',
    'toast.suspendLocked': '电脑进入睡眠时已安全锁定',
    /* —— 其他区域由子代理填充 —— */
  },
  en: {
    'tool.check.title': 'Password Strength Check',
    'tool.tab.gen': 'Password Generator',
    /* —— Tool Generator —— */
    'tool.gen.label.length': 'Password Length',
    'tool.gen.label.charset': 'Character Types',
    'tool.gen.charset.lower': 'Lowercase a-z',
    'tool.gen.charset.upper': 'Uppercase A-Z',
    'tool.gen.charset.digit': 'Digits 0-9',
    'tool.gen.charset.symbol': 'Symbols !@#$%^&*()[]',
    'tool.gen.avoidAmbiguous': 'Exclude ambiguous characters 0O1lI',
    'tool.gen.error.length': 'Password length must be an integer from 1 to 1024',
    'tool.gen.error.needCharset': 'Select at least one character type',
    'tool.gen.error.tooShort': 'Password length cannot be shorter than the selected character type count',
    'tool.gen.output.placeholder': 'Click the button below to generate',
    'tool.gen.button.generate': 'Generate',
    'tool.gen.button.copy': 'Copy',
    'tool.gen.button.save': 'Save as Record',
    'tool.gen.button.reset': 'Reset Defaults',
    'tool.tab.check': 'Password Strength Check',
    'tool.check.input.label': 'Enter password to check',
    'tool.check.input.placeholder': 'Type to check in real-time...',
    'tool.check.platform.placeholder': 'Platform (optional, e.g. GitHub, Taobao)',
    'tool.check.account.placeholder': 'Account (optional, e.g. user@example.com)',
    'tool.check.rating.label': 'Strength Rating',
    'tool.check.level.weak': 'Weak',
    'tool.check.level.fair': 'Fair',
    'tool.check.level.strong': 'Strong',
    'tool.check.crackTime.title': 'Crack Time Estimates',
    'tool.check.crackTime.online_throttling': 'Online (throttled 100/h)',
    'tool.check.crackTime.online_no_throttling': 'Online (no throttle 10/s)',
    'tool.check.crackTime.offline_slow': 'Offline (slow hash 10⁴/s)',
    'tool.check.crackTime.offline_fast': 'Offline (fast hash 10¹⁰/s)',
    'tool.check.risks.title': 'Risks',
    'tool.check.suggestions.title': 'Suggestions',
    'tool.check.detecting': 'Checking…',
    'tool.check.error.limit': 'Input exceeds the check limit. Shorten it and try again',
    'tool.check.feedback.EMPTY': 'Enter a password',
    'tool.check.feedback.TOO_SHORT': 'The password is too short',
    'tool.check.feedback.ADD_WORDS': 'Add another word or two',
    'tool.check.feedback.AVOID_REPEATS': 'Avoid repeated words and characters',
    'tool.check.feedback.AVOID_SEQUENCES': 'Avoid sequences',
    'tool.check.feedback.AVOID_RECENT_YEARS': 'Avoid recent years',
    'tool.check.feedback.AVOID_DATES': 'Avoid dates and related years',
    'tool.check.feedback.AVOID_COMMON_PASSWORD': 'Avoid common passwords',
    'tool.check.feedback.AVOID_COMMON_WORD': 'Avoid common words',
    'tool.check.feedback.AVOID_NAMES': 'Avoid names',
    'tool.check.feedback.AVOID_USER_DATA': 'Avoid platform or account details',
    'tool.check.feedback.AVOID_KEYBOARD_PATTERN': 'Avoid keyboard patterns',
    'tool.check.feedback.AVOID_LEET_PATTERN': 'Predictable substitutions add little strength',
    'tool.check.feedback.DICTIONARY_MATCH': 'The password contains a common dictionary pattern',
    'tool.check.bucket.INSTANT': 'Instantly',
    'tool.check.bucket.SECONDS': 'Seconds',
    'tool.check.bucket.MINUTES': 'Minutes',
    'tool.check.bucket.HOURS': 'Hours',
    'tool.check.bucket.DAYS': 'Days',
    'tool.check.bucket.MONTHS': 'Months',
    'tool.check.bucket.YEARS': 'Years',
    'tool.check.bucket.CENTURIES': 'Centuries or more',
    'settings.lang.name': 'Language',
    'settings.lang.desc': 'Interface display language',
    'settings.lang.aria': 'Switch interface language, currently English',
    'settings.lang.title': 'Switch interface language (current: English)',
    'settings.fontScale.name': 'Interface text size',
    'settings.fontScale.desc': 'Adjust all in-app text together',
    /* —— 连接面板（startup）—— */
    'startup.title': 'Cangoo',
    'startup.subtitle': 'Open an existing database, or choose a new path to create one',
    'startup.label.path': 'Database path',
    'startup.input.path.placeholder': 'Enter or choose a database path',
    'startup.label.password': 'Master password',
    'startup.input.password.placeholder': 'Enter master password',
    'startup.button.connect': 'Connect / Create',
    'startup.button.browse': 'Browse database',
    'common.password.show': 'Show password',
    'common.password.hide': 'Hide password',
    'common.current': '{name}. Current: {value}',
    'connection.connecting': 'Connecting...',
    'connection.error.invalid_password': 'Incorrect master password. {n} attempts remaining',
    'connection.error.locked_too_many': 'Too many failed attempts. This database is locked for 24 hours',
    'connection.error.path_not_found': 'The database file no longer exists. Select it again, or enter a new path to create one',
    'connection.error.permission_denied': 'This location cannot be accessed. Check the folder\'s read or write permissions',
    'connection.error.corrupt_or_unreadable': 'The database is damaged or unreadable. Check the file or restore a backup',
    'connection.locked.button': 'Locked',
    'startup.divider.recent': 'Recent',
    'startup.recent.select': 'Select',
    'startup.recent.remove': 'Remove',
    /* —— 启动页 modal 最小化提示条（未连接时切到工具/设置显示） —— */
    'startup.bar.title': 'No database connected',
    'startup.bar.action': 'Click to connect',
    'startup.dependent.disabled.tip': 'Please connect to a database first',
    'startup.empty.vault': 'No database connected, passwords are not visible',
    'startup.empty.notes': 'No database connected, encrypted notes are not visible',
    'startup.empty.security': 'No database connected, security check unavailable',
    /* —— 窗口标题栏 —— */
    'titlebar.app.title': 'Cangoo',
    'app.workspace': 'Cangoo workspace',
    'titlebar.button.minimize': 'Minimize',
    'titlebar.button.maximize': 'Maximize',
    'titlebar.button.restore': 'Restore',
    'titlebar.button.close': 'Close',
    /* —— 侧栏导航 —— */
    'nav.vault': 'Vault',
    'nav.notes': 'Notes',
    'nav.security': 'Security',
    'nav.tools': 'Tools',
    'nav.settings': 'Settings',
    'nav.help': 'Help',
    'topbar.title.help': 'Help',
    'nav.lock': 'Lock',
    /* —— 顶栏 —— */
    'topbar.title.connect': 'Connect Database',
    'topbar.title.vault': 'Vault',
    'topbar.title.notes': 'Notes',
    'topbar.title.security': 'Security Check',
    'topbar.title.tools': 'Tools',
    'topbar.title.settings': 'Settings',
    'topbar.search.placeholder': 'Search entry name / account...',
    'topbar.search.results': '{n} results found',
    'topbar.search.limit': 'Max. 128 characters',
    'settings.search.placeholder': 'Search settings...',
    'settings.search.empty': 'No matching settings. Try another keyword or clear the search.',
    'topbar.button.theme': 'Toggle theme',
    'topbar.button.quickbar': 'Quick Bar ({key})',
    /* —— QuickBar —— */
    'quickbar.input.placeholder': 'Search entry name or type command (gen 20)...',
    'quickbar.copy.pwd': 'Copy password',
    'quickbar.copy.acc': 'Copy account',
    'quickbar.autohide': 'Auto-hide after 30s of inactivity',
    'quickbar.clear': 'Clear search',
    'quickbar.cmd.generate': 'Generate {n}-char strong password — Press Enter to copy',
    'quickbar.cmd.hint': 'Will generate a strong password with upper/lower case, digits, and symbols',
    'quickbar.cmd.copied': 'Copied',
    'quickbar.cmd.range': 'Password length must be 4–1024 characters',
    'quickbar.query.limit': 'Search is limited to 128 characters. Remove some text and try again.',
    'quickbar.results.more': '{n} results — keep typing to narrow the search',
    'quickbar.hint.notfound': 'No records found matching "{q}"',
    'quickbar.hint.empty': 'Type an entry name to search, or "gen 20" to generate a password',
    /* —— 密码库面板 —— */
    'vault.filter.all': 'All',
    'vault.filter.favorite': 'Favorites',
    'vault.filter.weak': 'Weak',
    'vault.filter.duplicate': 'Duplicates',
    'vault.filter.similar': 'Similar names',
    'vault.view.list': 'List view',
    'vault.view.split': 'Split view',
    'vault.sort.updated': 'Recently updated',
    'vault.sort.name': 'Name A-Z',
    'vault.sort.strength': 'By strength',
    'vault.sort.label': 'Vault sorting',
    'vault.button.add': '+ Add',
    'vault.empty': 'No matching records',
    'vault.split.empty': 'Select a record from the left to view details',
    'vault.strength.label': 'Strength',
    /* —— 密码库列表项（动态）—— */
    'vault.detail.account': 'Account',
    'vault.detail.password': 'Password',
    'vault.detail.notes': 'Notes',
    'vault.detail.updated': 'Updated',
    'vault.detail.totp': 'TOTP',
    'vault.detail.recovery': 'Recovery codes',
    'vault.recovery.hidden': 'Recovery code hidden',
    'vault.recovery.visible': 'Recovery code visible',
    'vault.recovery.unmarked': 'Not marked used',
    'vault.recovery.used': 'Marked used',
    'vault.recovery.show': 'Show recovery code',
    'vault.recovery.hide': 'Hide recovery code',
    'vault.recovery.copy': 'Copy recovery code',
    'vault.recovery.mark': 'Mark used',
    'vault.recovery.undo': 'Undo used mark',
    'vault.button.edit': 'Edit',
    'vault.button.delete': 'Delete',
    'vault.copy.account': 'Copy account',
    'vault.copy.password': 'Copy password',
    'vault.copy.totp': 'Copy TOTP code',
    'vault.toggle.visible': 'Show/Hide',
    'vault.regenerate': 'Generate new password',
    'vault.dup.tag': 'Group',
    'vault.similar.tag': 'Similar group ',
    /* —— 记事本面板 —— */
    'notes.filter.all': 'All',
    'notes.filter.favorite': 'Favorites',
    'notes.filter.recent': 'Recent',
    'notes.sort.name': 'Title A-Z',
    'notes.sort.label': 'Note sorting',
    'notes.button.add': '+ Add note',
    'notes.empty': 'No notes',
    'notes.cards.read': 'Read full note',
    'notes.cards.back': 'Back to cards',
    'notes.cards.updated': 'Updated',
    'notes.cards.unsaved': 'Save or cancel the note being edited first.',
    'notes.cards.search.placeholder': 'Search notes...',
    /* —— 记事本列表项（动态）—— */
    'notes.detail.favorite': 'Favorite',
    'notes.fav.yes': 'Favorited',
    'notes.fav.no': 'Not favorited',
    'notes.toggle.favorite': 'Toggle favorite',
    'notes.input.title': 'Title',
    'notes.input.content': 'Type content...',
    'notes.button.edit': 'Edit dialog',
    'notes.button.delete': 'Delete',
    'notes.button.save': 'Save',
    'notes.default.title': 'New note',
    'notes.default.content': 'Type here...',
    /* —— 安全体检面板 —— */
    'security.score.label': 'Health score',
    'security.grade.excellent': 'Excellent',
    'security.grade.good': 'Good',
    'security.grade.fair': 'Fair',
    'security.grade.risk': 'At risk',
    'security.grade.none': 'N/A',
    'security.hero.title.excellent': 'Your vault is very secure',
    'security.hero.title.good': 'Your vault is generally secure',
    'security.hero.title.fair': 'Your vault has issues',
    'security.hero.title.risk': 'Your vault is at high risk',
    'security.hero.title.none': 'No passwords yet',
    'security.hero.desc': 'Found {issues}. Fix them soon to improve security.',
    'security.hero.clean': 'No security issues found. Keep it up!',
    'security.hero.empty': 'Please add passwords before checking security',
    'security.hero.weak': '{n} weak passwords',
    'security.hero.dup': '{n} duplicate groups',
    'security.hero.stale': '{n} long-unchanged records',
    'security.issue.weak': 'Weak passwords',
    'security.issue.duplicate': 'Duplicate passwords',
    'security.issue.stale': 'Long-unseen',
    'security.count.weak': '3 items',
    'security.button.fixall': 'Fix one by one',
    /* —— 安全体检动态 —— */
    'security.count.group': '{n} group(s)',
    'security.count.items': '{n} item(s)',
    'security.desc.weak': 'Password too weak, consider a stronger one',
    'security.desc.dup': 'A shared password puts multiple accounts at risk',
    'security.desc.dupName': 'share the same password',
    'security.dup.join': ' and ',
    'security.desc.stale': 'Exceeds {n}-day threshold, update soon',
    'security.name.stale': 'Unchanged for {n} days',
    'security.empty.weak': 'No weak passwords',
    'security.empty.dup': 'No duplicate passwords',
    'security.empty.stale': 'No long-unseen records',
    'security.button.fix': 'Fix →',
    'security.button.view': 'View →',
    /* —— 状态栏 —— */
    'status.disconnected': 'Disconnected',
    'status.connect.prefix': 'Connected ',
    'status.clipboard.ready': 'Clipboard: Ready',
    'status.clipboard.group': 'Clipboard status',
    'status.clipboard.cleared': 'Clipboard cleared',
    'status.clipboard.countdown': 'Clipboard: clears in {n}s',
    'status.clipboard.clearNow': 'Clear now',
    /* —— Toast 提示 —— */
    'toast.connected': 'Connected to ',
    'toast.fillPath': 'Database path filled. Enter master password and click "Connect / Create".',
    'toast.browse': 'File dialog opened (prototype demo)',
    'toast.copied.suffix': ' copied to clipboard',
    'toast.deleted.prefix': 'Deleted ',
    'toast.notFound': 'Record not found',
    'toast.located.prefix': 'Located ',
    'toast.located.suffix': ', opening edit dialog',
    'toast.dup.shown': 'Showing all duplicate entries. Same-colored borders indicate the same group.',
    'toast.noIssues': 'No security issues to fix',
    'toast.fav.added': 'Added to favorites',
    'toast.fav.removed': 'Removed from favorites',
    'toast.note.saved': 'Note saved',
    'toast.note.created': 'Note created',
    /* —— 通用强度标签 —— */
    'common.strength.weak': 'Weak',
    'common.strength.fair': 'Fair',
    'common.strength.strong': 'Strong',
    'common.strength.pending': 'Pending',
    'common.strength.checking': 'Checking',
    'common.strength.failed': 'Check failed',
    /* —— 引导修复对话框 —— */
    'fix.modal.title': 'Fix one by one',
    'fix.progress.label': 'Progress',
    'fix.progress.fixed': 'Processed {done} / {total}',
    'fix.progress.complete': 'Guide complete',
    'fix.progress.continue': 'Continue to next?',
    'fix.progress.summary': 'Total {total} · Processed {done} · Skipped {skipped}',
    'fix.guide.hint': 'Click "Go to edit" to jump to the record and open the edit dialog.<br>This guide will not modify any password automatically; save manually after editing.',
    'fix.guide.multiIssue': 'This record has {n} issues; changing password solves all:',
    'fix.button.back': 'Back',
    'fix.button.skip': 'Skip',
    'fix.button.goto': 'Go to edit',
    'fix.button.finish': 'Done',
    'fix.button.continue': 'Continue',
    'fix.button.prev': 'Previous',
    'fix.button.skipThis': 'Skip this',
    'fix.button.abandon': 'Abandon',
    'fix.banner.title': 'Fix guide in progress',
    'fix.banner.remaining': '{n} remaining',
    'fix.banner.continue': 'Continue',
    'fix.banner.abandon': 'Abandon',
    'fix.toast.abandoned': 'Fix guide abandoned',
    /* —— 主题切换 Toast —— */
    'toast.theme.dark': 'Switched to dark theme',
    'toast.theme.light': 'Switched to light theme',
    'toast.theme.auto': 'Theme set to follow system',
    /* —— 生成器 Toast —— */
    'toast.gen.needCharset': 'Select at least one character type',
    'toast.gen.generated': 'Password generated',
    'toast.gen.needGenFirst': 'Generate a password first',
    'toast.gen.saved': 'Saved as password record, viewable in Vault',
    'toast.gen.needCharsetTools': 'Select character types in Tools first',
    'toast.gen.generatedShown': 'New password generated and shown',
    'toast.gen.generatedNew': 'New password generated',
    'gen.default.platform': 'New record',
    'gen.default.notes': 'Created by password generator',
    /* —— 窗口控制 Toast —— */
    'toast.minimized': 'Window minimized (simulated)',
    'toast.maximized': 'Window maximized (simulated)',
    'toast.restored': 'Window restored (simulated)',
    'toast.exited': 'Exit simulated',
    /* —— 密码对话框 Toast —— */
    'toast.pwd.added': 'Password record added',
    'toast.pwd.updated': 'Password record updated',
    'toast.pwd.deleted.generic': 'Password record deleted',
    'toast.note.deleted.generic': 'Note deleted',
    'toast.operation.failed': 'Operation failed. Review the current error message.',
    /* —— 记事对话框 Toast —— */
    'toast.note.dialogAdded': 'Note added',
    'toast.note.dialogNotFound': 'Note not found',
    'toast.note.dialogUpdated': 'Note updated',
    /* —— 修改密码 Toast —— */
    'toast.keyChanged': 'Password changed, please reconnect',
    /* —— 设置导出 Toast —— */
    'toast.exported': 'Exported 10 records to backup.json',
    /* —— 通用对话框标签 —— */
    'dialog.label.favorite': 'Favorite',
    'dialog.button.cancel': 'Cancel',
    'dialog.button.save': 'Save',
    'dialog.button.confirm': 'Confirm',
    'dialog.button.delete': 'Delete',
    'dialog.button.close': 'Close dialog',
    'dialog.toggle.visible': 'Show/Hide',
    'dialog.generate': 'Generate password',
    /* —— 密码对话框 —— */
    'dialog.pwd.title.add': '＋ Add password record',
    'dialog.pwd.title.edit': 'Edit password record',
    'dialog.pwd.label.platform': 'Platform',
    'dialog.pwd.label.account': 'Account',
    'dialog.pwd.label.password': 'Password',
    'dialog.pwd.label.notes': 'Notes',
    'dialog.pwd.label.totp': 'TOTP secret',
    'dialog.pwd.label.recovery': 'Recovery codes (optional)',
    'dialog.pwd.recovery.empty': 'One code per line. Keep a separate secure copy; codes are unavailable if this vault cannot open.',
    'dialog.pwd.recovery.keep': '{n} codes stored. Leave empty to keep them or enter a new set. Existing codes are not prefilled.',
    'dialog.pwd.recovery.remove': 'Remove all recovery codes',
    'dialog.pwd.recovery.undo': 'Keep existing recovery codes',
    'dialog.pwd.recovery.confirm': 'Replace or remove all recovery codes? This resets local used marks.',
    'dialog.pwd.recovery.invalid': 'Check duplicate lines and length. Recovery codes were not saved.',
    'dialog.pwd.placeholder.platform': 'e.g. GitHub · Personal',
    'dialog.pwd.placeholder.account': 'Account or email',
    'dialog.pwd.placeholder.password': 'Type or click the icon to generate',
    'dialog.pwd.placeholder.notes': 'Notes...',
    'dialog.pwd.placeholder.totp': 'Base32 secret (e.g. JBSWY3DPEHPK3PXP), leave empty to disable',
    'dialog.pwd.placeholder.totpReplace': 'Enter a new Base32 secret to replace it',
    'dialog.pwd.totp.enabledHint': 'Currently enabled. Leave empty to keep it, or enter a new Base32 secret to replace it.',
    'dialog.pwd.totp.disabledHint': 'Currently disabled. Enter a Base32 secret to enable it.',
    'dialog.pwd.totp.remove': 'Remove current TOTP',
    'dialog.pwd.totp.undoRemove': 'Undo removal',
    'dialog.pwd.totp.removeHint': 'Saving will remove the existing TOTP. Its secret is never displayed.',
    'dialog.pwd.error.platformEmpty': 'Platform name is required',
    'dialog.pwd.error.platformExists': 'Platform name already exists, use a different name',
    'dialog.pwd.error.save_failed': 'Save failed, please try again',
    'dialog.pwd.error.duplicate': 'Platform name already exists, use a different name',
    'dialog.pwd.error.revision_conflict': 'The record changed elsewhere. Your unsaved input is preserved; load the latest version before editing again.',
    'dialog.pwd.error.delete_failed': 'The secure operation did not complete. Exit the isolated candidate and retry.',
    'dialog.pwd.action.reloadLatest': 'Load latest content',
    'dialog.pwd.action.retryAuthorization': 'Reauthorize saving',
    'dialog.delete.title': 'Delete password',
    'dialog.delete.confirm': 'Delete password for {platform}?',
    'dialog.delete.desc': 'This action cannot be undone.',
    /* —— 记事对话框 —— */
    'dialog.note.title.add': '＋ Add note',
    'dialog.note.title.edit': 'Edit note',
    'dialog.note.label.title': 'Title',
    'dialog.note.label.content': 'Content',
    'dialog.note.placeholder.title': 'Enter note title',
    'dialog.note.placeholder.content': 'Enter note content...',
    'dialog.note.error.titleEmpty': 'Title is required',
    'dialog.note.error.save_failed': 'Save failed, please retry',
    'notes.scroll.more': '↓ Scroll down for more',
    'notes.scroll.bottom': '✓ End of content',
    'notes.scroll.position': 'Position {0}% · {1} lines',
    'dialog.note.delete.title': 'Delete note',
    'dialog.note.delete.confirm': 'Delete note "{title}"?',
    'dialog.note.delete.desc': 'This action cannot be undone.',
    /* —— 修改密码对话框 —— */
    'dialog.key.title': 'Change database password',
    'dialog.key.warning': '⚠ Changing the password will re-encrypt all data. Remember the new password.',
    'dialog.key.label.current': 'Current password',
    'dialog.key.label.new': 'New password',
    'dialog.key.label.confirm': 'Confirm password',
    'dialog.key.placeholder.current': 'Enter current password',
    'dialog.key.placeholder.new': 'Enter new password',
    'dialog.key.placeholder.confirm': 'Re-enter new password',
    'dialog.key.error.current': 'Current password is incorrect',
    'dialog.key.error.failed': 'Password change failed. The database was not changed; please retry.',
    'dialog.key.error.failed_restored': 'Password change failed. The original database was safely restored; reconnect with the old password.',
    'dialog.key.error.recovery_failed': 'Password change failed and automatic recovery did not complete. Stop using the database and preserve its files.',
    'dialog.key.changing': 'Changing…',
    'dialog.key.progress': 'Changing…',
    'dialog.key.error.unchanged': 'The change did not complete. The original database is unchanged. Try again shortly.',
    'dialog.key.indicator.empty': '○ Password will be cleared',
    'dialog.key.indicator.match': '✓ Passwords match',
    'dialog.key.indicator.mismatch': '✗ Passwords do not match',
    /* —— Import/Export Dialog Toast —— */
    'toast.ie.exported': 'Exported {n} records to {file}',
    'toast.ie.imported': 'Imported {added}, overwrote {updated}, skipped {skipped}',
    'toast.ie.no_changes': 'No data changed',
    /* —— Import/Export Dialog —— */
    'dialog.ie.title.export': 'Export Data',
    'dialog.ie.title.import': 'Import Data',
    'dialog.ie.mode.export': 'Export',
    'dialog.ie.mode.import': 'Import',
    'dialog.ie.format.label': 'Format',
    'dialog.ie.format.encrypted': 'JSON Encrypted Backup',
    'dialog.ie.format.encrypted.hint': 'Encrypted with independent password, safe for cross-vault migration',
    'dialog.ie.scope.label': 'Scope',
    'dialog.ie.scope.all': 'All (Passwords + Notes)',
    'dialog.ie.scope.passwords': 'Passwords Only',
    'dialog.ie.scope.notes': 'Notes Only',
    'dialog.ie.path.label': 'File Path',
    'dialog.ie.path.placeholder.export': 'Select export destination...',
    'dialog.ie.path.placeholder.import': 'Select backup file path...',
    'dialog.ie.browse': 'Browse',
    'dialog.ie.browse.prompt': 'Enter file path (demo, Win uses native file picker)',
    'dialog.ie.password.label': 'Encryption Password',
    'dialog.ie.password.placeholder': 'Set backup encryption password',
    'dialog.ie.password.placeholder.export': 'Set backup encryption password',
    'dialog.ie.password.placeholder.import': 'Enter backup file password',
    'dialog.ie.password.hint': 'Independent from vault master password. Used to encrypt/decrypt backup. Lost password = unrecoverable',
    'dialog.ie.password.confirm.label': 'Confirm Password',
    'dialog.ie.password.confirm.placeholder': 'Re-enter encryption password',
    'dialog.ie.password.indicator.empty': '○ Enter and confirm a backup password',
    'dialog.ie.password.indicator.match': '✓ Backup passwords match',
    'dialog.ie.password.indicator.mismatch': '✗ Backup passwords do not match',
    'dialog.ie.warning.export': '⚠️ The export file is encrypted with your password. Keep it safe — lost password = unrecoverable',
    'dialog.ie.preview.label': 'Import Preview',
    'dialog.ie.preview.empty': 'Select a backup file and enter password, then click Preview',
    'dialog.ie.preview.button': 'Preview',
    'dialog.ie.preview.summary': 'Backup contains {total} records ({pw} passwords, {note} notes)',
    'dialog.ie.preview.conflict': 'Detected {n} conflicts (same entry name already exists)',
    'dialog.ie.conflict.label': 'Conflict Resolution',
    'dialog.ie.conflict.overwrite_all': 'Overwrite All',
    'dialog.ie.conflict.skip_all': 'Skip All',
    'dialog.ie.conflict.overwrite': 'Overwrite',
    'dialog.ie.conflict.skip': 'Skip',
    'dialog.ie.conflict.undecided': 'Undecided',
    'dialog.ie.conflict.help': 'Compare both sides before deciding. Overwrite fully replaces the current record on the left with the backup record on the right.',
    'dialog.ie.conflict.current': 'CURRENT DATABASE',
    'dialog.ie.conflict.incoming': 'BACKUP FILE',
    'dialog.ie.conflict.account': 'Account',
    'dialog.ie.conflict.show_account': 'Show full account',
    'dialog.ie.conflict.show_platform': 'Show full name',
    'dialog.ie.conflict.password': 'Password',
    'dialog.ie.conflict.notes': 'Notes',
    'dialog.ie.conflict.totp': 'TOTP',
    'dialog.ie.conflict.show_password': 'Show',
    'dialog.ie.conflict.hide_password': 'Hide',
    'dialog.ie.conflict.show_notes': 'Show notes',
    'dialog.ie.conflict.empty': '(empty)',
    'dialog.ie.execute.export': 'Start Export',
    'dialog.ie.execute.import': 'Start Import',
    'dialog.ie.error.path': 'Please select file path first',
    'dialog.ie.error.password': 'Please enter encryption password',
    'dialog.ie.error.mismatch': 'Passwords do not match',
    'dialog.ie.error.preview': 'Please click Preview to confirm import content first',
    'dialog.ie.error.undecided': '{n} conflict(s) undecided. Choose Overwrite or Skip for each',
    'dialog.ie.recovery.repreview': 'Import did not complete. Re-enter the backup password, preview, then try again.',
    'dialog.ie.recovery.reselect': 'The preview is no longer available. Select the backup file again and preview it.',
    'dialog.ie.recovery.reread': 'The field view expired. Select it again to view it.',
    'dialog.ie.progress.export': 'Encrypting and writing backup…',
    'dialog.ie.progress.import': 'Importing data safely…',
    /* —— 设置导入导出按钮 —— */
    'settings.db.ie.button': 'Open',
    /* —— Settings Panel —— */
    'settings.group.appearance': 'Appearance',
    'settings.group.startupWindow': 'Startup & window',
    'settings.group.quickbar': 'Quick search',
    'settings.group.general': 'General',
    'settings.theme.name': 'Theme mode',
    'settings.theme.desc': 'Switch between Light / Dark / System',
    'settings.theme.light': 'Light',
    'settings.theme.dark': 'Dark',
    'settings.theme.auto': 'Auto',
    'settings.option.current': 'Toggle option. Current: {value}',
    'settings.option.title': 'Toggle option (current: {value})',
    'settings.autofill.name': 'Auto-fill on startup',
    'settings.autofill.desc': 'Auto-fill last database path on launch',
    'settings.autofill.aria': 'Toggle auto-fill on startup',
    'settings.group.view': 'View',
    'settings.view.default.name': 'Default view mode',
    'settings.view.default.desc': 'Default vault display on startup',
    'settings.view.list': 'List',
    'settings.view.split': 'Split',
    'settings.sidebar.text.name': 'Show sidebar text',
    'settings.sidebar.text.desc': 'Show navigation text below icons',
    'settings.sidebar.text.aria': 'Toggle sidebar text',
    'settings.group.clipboard': 'Clipboard',
    'settings.clipboard.clear.name': 'Clear mode',
    'settings.clipboard.clear.desc': 'Auto-clear after countdown',
    'settings.clipboard.clear.countdown': 'Countdown',
    'settings.clipboard.clear.manual': 'Manual',
    'settings.clipboard.duration.name': 'Countdown duration',
    'settings.clipboard.duration.desc': 'Seconds before auto-clearing clipboard',
    'settings.group.tray': 'System tray',
    'settings.tray.close.name': 'Close button behavior',
    'settings.tray.close.desc': 'Minimize to tray or exit on close',
    'settings.tray.close.minimize': 'Minimize',
    'settings.tray.close.exit': 'Exit',
    'settings.tray.close.saved': 'Close behavior saved',
    'settings.tray.quickbar.name': 'Enable Quick Bar',
    'settings.tray.quickbar.desc': 'Global hotkey to invoke Quick Bar',
    'settings.tray.quickbar.aria': 'Toggle Quick Bar',
    'settings.quickbar.timeout.name': 'Quick Bar idle hide',
    'settings.quickbar.timeout.desc': 'Hide Quick Bar after this many idle seconds',
    'settings.unit.seconds': 's',
    /* —— Quick Bar hotkey customization —— */
    'settings.hotkey.name': 'Quick Bar Hotkey',
    'settings.hotkey.desc': 'Global shortcut to invoke Quick Bar, click to modify',
    'settings.hotkey.modify': 'Modify',
    'settings.hotkey.recording': 'Press combo… (Esc to cancel)',
    'settings.hotkey.canceled': 'Hotkey modification canceled',
    'settings.hotkey.invalid': 'Unsupported key: {key}, use letters/digits/F1-F12/symbols',
    'settings.hotkey.need_modifier': 'At least one modifier key required (Ctrl/Alt/Shift/Win)',
    'settings.hotkey.conflict': 'Hotkey {key} conflicts with {app}, saved but may not work, consider another',
    'settings.hotkey.saved': 'Hotkey set to {key}',
    'settings.group.database': 'Database management',
    'settings.db.current.name': 'Current database',
    'settings.db.current.desc': 'Connected encrypted database file',
    'settings.db.current.info': 'demo.db · 10 records',
    'settings.db.current.disconnected': 'Not connected',
    'settings.db.current.records': 'records',
    'settings.db.changepwd.name': 'Change database password',
    'settings.db.changepwd.desc': 'Re-encrypt all data',
    'settings.db.changepwd.button': 'Change password',
    'settings.db.transfer.name': 'Device transfer',
    'settings.db.transfer.desc': 'Verify a nearby device to send or receive vault contents',
    'settings.db.ie.name': 'Import / Export',
    'settings.db.ie.desc': 'Encrypted backup or restore from backup',
    'settings.group.security': 'Security',
    'settings.security.stale.name': 'Long-unseen threshold',
    'settings.security.stale.desc': 'Passwords unchanged beyond this many days will trigger an alert',
    'settings.security.autolock.name': 'Auto-lock on idle',
    'settings.security.autolock.desc': 'Lock after inactivity; system sleep always locks',
    'settings.security.autolock.aria': 'Toggle auto-lock on idle',
    'settings.security.autolock.timeout.name': 'Auto-lock threshold',
    'settings.security.autolock.timeout.desc': 'Minutes of inactivity before auto-lock',
    'settings.unit.days': 'days',
    'settings.unit.minutes': 'min',
    'toast.autolocked': 'Auto-locked due to inactivity',
    'toast.suspendLocked': 'Locked when the computer entered sleep',
  }
};

/* 破解时间翻译表（zxcvbn 返回英文，需翻译为中文；英文原样返回） */
const CRACK_TIME_I18N = {
  zh: {
    'less than a second': '小于一秒',
    'instant': '即时',
    'centuries': '数百年',
    '100+ years': '100 年以上',
  },
  en: {}
};
const CRACK_TIME_UNIT_I18N = {
  zh: { second:'秒', minute:'分钟', hour:'小时', day:'天', month:'个月', year:'年' },
  en: {}
};

/* 翻译函数：当前语言 → 中文 → key 本身（兜底，便于发现遗漏） */
function t(key){
  const lang = state.lang || 'zh';
  return I18N[lang]?.[key] || I18N.zh?.[key] || key;
}

function setStaticPasswordVisibility(inputId,eyeId,visible){
  const input=$('#'+inputId),eye=$('#'+eyeId),button=eye?.closest('button');
  if(!(input instanceof HTMLInputElement)||!eye||!button) return;
  input.type=visible?'text':'password';
  eye.innerHTML=svgIcon(visible?'eye-closed':'eye',16);
  const label=t(visible?'common.password.hide':'common.password.show');
  button.setAttribute('aria-label',label);
  button.setAttribute('aria-pressed',String(visible));
  button.title=label;
}

function toggleStaticPasswordVisibility(inputId,eyeId){
  const input=$('#'+inputId);
  if(input instanceof HTMLInputElement){
    setStaticPasswordVisibility(inputId,eyeId,input.type!=='text');
  }
}

function syncBinarySegmentAccessibility(segment){
  if(!segment) return;
  const active=segment.querySelector('button.active');
  const name=segment.closest('.setting-row')?.querySelector('.setting-name')?.textContent.trim()||'';
  const value=active?.textContent.trim()||'';
  segment.setAttribute('aria-label',t('common.current').replace('{name}',name).replace('{value}',value));
  segment.title=t('settings.option.title').replace('{value}',value);
}

function syncThemeAccessibility(){
  const segment=$('#theme-segment');
  if(!segment) return;
  segment.setAttribute('aria-label',t('settings.theme.name'));
  segment.querySelectorAll('button').forEach(button=>{
    button.setAttribute('aria-pressed',String(button.classList.contains('active')));
  });
}

function syncStaticAccessibility(){
  setStaticPasswordVisibility('db-password','startup-eye',$('#db-password')?.type==='text');
  setStaticPasswordVisibility('check-input','check-eye',$('#check-input')?.type==='text');
  ['view-default-segment','tray-close-segment','clip-clear-segment','ui-font-scale-segment'].forEach(id=>
    syncBinarySegmentAccessibility($('#'+id)));
  syncThemeAccessibility();
  syncSortDropdownAccessibility('sort-dropdown');
  syncSortDropdownAccessibility('note-sort-dropdown');
  syncOpenModalAccessibility();
}

function setUiFontScale(value){
  const scale=['90','100','110','125'].includes(String(value))?String(value):'100';
  document.documentElement.dataset.pdmUiFontScale=scale;
  document.documentElement.style.setProperty('--pdm-ui-font-scale',String(Number(scale)/100));
  document.querySelectorAll('#ui-font-scale-segment button').forEach(button=>{
    const active=button.dataset.pdmUiFontScale===scale;
    button.classList.toggle('active',active);
    button.setAttribute('aria-pressed',String(active));
  });
  syncBinarySegmentAccessibility($('#ui-font-scale-segment'));
}

/* 破解时间翻译：完全匹配 → 数字+单位匹配 → 原样返回 */
function translateCrackTime(str){
  if(!str) return '';
  const lang = state.lang || 'zh';
  if(lang === 'en') return str;
  if(CRACK_TIME_I18N.zh[str]) return CRACK_TIME_I18N.zh[str];
  const m = str.match(/^(\d+(?:\.\d+)?)\s+(second|minute|hour|day|month|year)s?$/);
  if(m){
    return `${m[1]} ${CRACK_TIME_UNIT_I18N.zh[m[2]]}`;
  }
  return str;
}

/* 语言切换：在 zh/en 之间二选一切换（点击整个 lang-segment 触发） */
function toggleLang(){
  setLang(state.lang === 'zh' ? 'en' : 'zh');
}

/* 二选一段控件：整体点击切换（适用于只有 2 个互斥选项的 segment）
   - 切换 active 视觉态到另一个 button
   - 同步 aria-label / title 反映当前选项
   - 业务配置写入由 Win 端 settings.json 处理，原型仅视觉占位 */
function toggleBinarySegment(seg){
  const btns = $$('button', seg);
  if(btns.length !== 2) return;
  const curIdx = btns[0].classList.contains('active') ? 0 : 1;
  const nextIdx = curIdx === 0 ? 1 : 0;
  btns.forEach((b, i) => b.classList.toggle('active', i === nextIdx));
  syncBinarySegmentAccessibility(seg);
}

/* 语言切换：更新 state.lang + 遍历所有 data-i18n 元素 + 触发动态内容重渲染 */
function setLang(lang, options={}){
  state.lang = lang;
  if (typeof window.renderHelp === 'function') window.renderHelp();
  clearOperationStatus();
  document.documentElement.lang = lang === 'en' ? 'en' : 'zh-CN';
  /* 1. 更新所有 [data-i18n] 元素的 textContent */
  document.querySelectorAll('[data-i18n]').forEach(el => {
    el.textContent = t(el.getAttribute('data-i18n'));
  });
  /* 1.5 特殊处理：gen-output 已生成密码时保留明文，避免被占位提示覆盖 */
  if(state.genPassword && $('#gen-output')){
    $('#gen-output').textContent = state.genPassword;
  }
  /* 2. 更新 [data-i18n-placeholder] 的 placeholder */
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    el.placeholder = t(el.getAttribute('data-i18n-placeholder'));
  });
  /* 3. 更新 [data-i18n-title] 的 title（tooltip） */
  document.querySelectorAll('[data-i18n-title]').forEach(el => {
    const label = t(el.getAttribute('data-i18n-title'));
    el.title = label;
    if(el.hasAttribute('aria-label')) el.setAttribute('aria-label', label);
  });
  /* 3.5 更新单独声明的可访问名称；不得依赖 title 顺带覆盖。 */
  document.querySelectorAll('[data-i18n-aria-label]').forEach(el => {
    el.setAttribute('aria-label', t(el.getAttribute('data-i18n-aria-label')));
  });
  /* 4. 更新语言 segment 激活态 + aria-label 同步当前语言 */
  const seg = $('#lang-segment');
  if(seg){
    $$('button', seg).forEach(b => {
      b.classList.toggle('active', b.dataset.lang === lang);
    });
    seg.setAttribute('aria-label', t('settings.lang.aria'));
    seg.title = t('settings.lang.title');
  }
  syncStaticAccessibility();
  document.querySelectorAll('.recent-item').forEach(item=>{
    const name=item.querySelector('.recent-name')?.textContent||'';
    const select=item.querySelector('.recent-select');
    const remove=item.querySelector('.recent-remove');
    if(select) select.setAttribute('aria-label',`${t('startup.recent.select')}: ${name}`);
    if(remove){
      remove.textContent=t('startup.recent.remove');
      remove.setAttribute('aria-label',`${t('startup.recent.remove')}: ${name}`);
    }
  });
  /* 5. 触发动态内容重新渲染（强度检测区域） */
  if(typeof checkStrength === 'function' && $('#check-input')?.value){
    checkStrength();
  }
  /* 6. 其他动态渲染函数按需扩展（子代理整合时补充） */
  if(
    !options.skipDynamicRender &&
    state.connected &&
    typeof renderAll === 'function'
  ){
    renderAll();
    /* 刷新顶栏标题（navTitles 动态文字） */
    const cur = state.currentNav;
    if(cur && $('#topbar-title')){
      $('#topbar-title').textContent = t('topbar.title.'+cur);
    }
  }
  /* 7. 同步含热键占位符的 title（如顶栏 QuickBar 按钮）
     i18n 键值含 {key} 占位符，setLang 处理 data-i18n-title 时不会替换，
     需在此手动调用 saveHotkey 同步——saveHotkey 内部会用当前热键替换 {key} */
  const qbBtn = $('#topbar-quickbar-btn');
  if(qbBtn){
    qbBtn.title = t('topbar.button.quickbar').replace('{key}', formatHotkeyDisplay(state.quickBarHotkey));
  }
  window.renderUpdates?.();
  if(state.currentNav==='settings') filterSettings();
}
/* ============================================================
   密码强度评估核心算法（基于 zxcvbn + 中文本地化字典 + user_inputs 上下文）
   评分模型：zxcvbn 熵估算（0-4 分）+ 中文字典（3552 条）+ 平台/账号上下文
   评级映射：0-2 弱 / 3 中 / 4 强（严格映射，适配 offline 10⁴/秒 慢哈希）
   Win 端对应：core/password_tools.py（zxcvbn-python 4.5.0 + pypinyin）
   ============================================================ */
/* 合并中文字典（3552 条），作为 zxcvbn user_inputs 注入，与内置 30k 字典共同参与匹配 */
const CN_DICT = [...PINYIN_DICT, ...PHRASES_DICT, ...LEAKED_CN_DICT];

const strengthMap = {weak:'弱',fair:'中',strong:'强'};
const strengthOrder = {weak:0,fair:1,strong:2};

/**
 * 密码强度评估核心算法（基于 zxcvbn + 中文本地化字典 + user_inputs 上下文）
 * 评分维度：zxcvbn 熵估算 + 中文字典 + 平台/账号上下文
 * 评级映射：0-2 弱 / 3 中 / 4 强（使用同一次完整分析结果）
 * @param {string} pw - 密码
 * @param {string} [platform=''] - 平台名（如 'GitHub'、'淘宝'），用于 user_inputs 上下文
 * @param {string} [account=''] - 账号名（如 'user@example.com'），用于 user_inputs 上下文
 * @returns {{rating:string, level:string, score:number, crackTimes:object, guesses:number, downgraded:boolean, risks:array, suggestions:array}}
 */
function evaluateStrength(pw, platform='', account=''){
  if(!pw){
    return {
      rating:'weak', level:'弱', score:0,
      crackTimes:{}, guesses:0, downgraded:false,
      risks:[{zh:'密码不能为空', en:'Password is empty'}],
      suggestions:[]
    };
  }

  /* 1. 构建 user_inputs：中文字典 + 平台/账号上下文 */
  const contextInputs = buildContextInputs(platform, account);
  const userInputs = [...CN_DICT, ...contextInputs];

  /* 2. 调用 zxcvbn（user_inputs 会作为额外字典参与匹配，并应用 l33t 还原） */
  const result = zxcvbn(pw, userInputs);

  /* 3. 评级和反馈均来自本次完整分析，不额外还原或强制降级。 */
  const rating = mapTo3Levels(result.score);
  const {risks, suggestions} = buildFeedback(result, contextInputs);

  const level = strengthMap[rating];

  return {
    rating,
    level,
    score: result.score,
    crackTimes: result.crack_times_display,
    guesses: result.guesses,
    downgraded:false,
    risks,
    suggestions
  };
}

/**
 * 构建 user_inputs 中的"平台/账号上下文"部分（不含中文字典）
 * - 中文平台/账号 → 转拼音 + 保留原中文（双重覆盖）
 * - 英文平台/账号 → 原样传入（zxcvbn 内部自动小写）
 * - 邮箱账号 → 提取本地部分（@ 前部分）+ 完整邮箱
 * - 去重、去空、去超长（>32 字符忽略，避免噪声）
 * Win 端对应：core/password_tools.py 的 _build_user_inputs（用 pypinyin.lazy_pinyin）
 */
function buildContextInputs(platform, account){
  const inputs = [];
  const seen = new Set();
  const add = (s) => {
    if(!s) return;
    s = String(s).trim();
    if(!s || s.length > 32) return;
    const key = s.toLowerCase();
    if(seen.has(key)) return;
    seen.add(key);
    inputs.push(s);
  };

  if(platform){
    add(platform);
    /* 中文平台名转拼音（pypinyin 的 lazy_pinyin 等价） */
    if(/[\u4e00-\u9fa5]/.test(platform) && typeof pinyinPro !== 'undefined'){
      try{
        const py = pinyinPro.pinyin(platform, {toneType:'none', type:'string'});
        if(py && py.replace(/\s/g,'') !== platform) add(py.replace(/\s/g,'').toLowerCase());
      }catch(e){/* pinyin-pro 加载失败时降级为仅传原中文 */}
    }
  }

  if(account){
    add(account);
    /* 邮箱账号提取本地部分 */
    if(account.includes('@')){
      add(account.split('@')[0]);
    }
    /* 中文账号名转拼音 */
    if(/[\u4e00-\u9fa5]/.test(account) && typeof pinyinPro !== 'undefined'){
      try{
        const py = pinyinPro.pinyin(account, {toneType:'none', type:'string'});
        if(py && py.replace(/\s/g,'') !== account) add(py.replace(/\s/g,'').toLowerCase());
      }catch(e){/* 降级 */}
    }
  }

  return inputs;
}

/* 整体分析分数映射；时间估算使用场景假设，不是实际破解测量。 */
function mapTo3Levels(score){
  if(score <= 2) return 'weak';
  if(score === 3) return 'fair';
  return 'strong';
}

/**
 * 构建 risks + suggestions（zxcvbn feedback 中英对照翻译 + sequence 命中模式提取）
 * 数据源：result.feedback.warning / suggestions + result.sequence
 * 返回：{risks: [{zh,en}], suggestions: [{zh,en}]}
 *   - risks：风险提示（是什么弱模式），来自 warning + sequence 命中
 *   - suggestions：改进建议（怎么改），来自 fb.suggestions
 */
function buildFeedback(result, contextInputs){
  const risks = [];
  const suggestions = [];
  const fb = result.feedback || {};
  const seenRisk = new Set();
  const seenSugg = new Set();

  const addRisk = (item) => {
    if(item && !seenRisk.has(item.zh)){
      seenRisk.add(item.zh);
      risks.push(item);
    }
  };
  const addSuggestion = (item) => {
    if(item && !seenSugg.has(item.zh)){
      seenSugg.add(item.zh);
      suggestions.push(item);
    }
  };

  /* 1. 翻译 warning → risks */
  if(fb.warning){
    addRisk(translateWarning(fb.warning, result));
  }

  /* 2. 翻译 suggestions → suggestions */
  if(fb.suggestions){
    fb.suggestions.forEach(s => addSuggestion(translateSuggestion(s)));
  }

  /* 3. 从 sequence 提取命中模式 → risks（补充 warning 未覆盖的情况） */
  if(result.sequence){
    extractPatterns(result.sequence, contextInputs).forEach(addRisk);
  }

  return {risks, suggestions};
}

/* zxcvbn warning 中英对照翻译表 */
const ZXCVBN_WARNING_MAP = {
  'This is a very common password': {zh:'命中常见弱密码', en:'This is a very common password'},
  'This is similar to a commonly used password': {zh:'与常见弱密码相似', en:'This is similar to a commonly used password'},
  'A sequence of characters': {zh:'包含顺序字符模式', en:'A sequence of characters'},
  'Short keyboard patterns are easy to guess': {zh:'包含键盘走位模式', en:'Short keyboard patterns are easy to guess'},
  'Repeats like "abcabcabc" are only slightly harder to guess than "abc"': {zh:'包含重复模式', en:'Repeats like "abcabcabc" are only slightly harder to guess than "abc"'},
  'Repeats like "aaa" are easy to guess': {zh:'包含重复字符', en:'Repeats like "aaa" are easy to guess'},
  'Sequences like abc or 6543 are easy to guess': {zh:'包含顺序字符', en:'Sequences like abc or 6543 are easy to guess'},
  'This is a top-10 common password': {zh:'命中十大最常见密码', en:'This is a top-10 common password'},
  'This is a top-100 common password': {zh:'命中百大常见密码', en:'This is a top-100 common password'},
  'Dates are often easy to guess': {zh:'包含日期', en:'Dates are often easy to guess'},
  'Names and surnames are easy to guess': {zh:'包含常见姓名', en:'Names and surnames are easy to guess'},
  'Common names and surnames are easy to guess': {zh:'包含常见姓名', en:'Common names and surnames are easy to guess'},
};

function translateWarning(warning, result){
  /* 前缀匹配：zxcvbn 可能返回带后缀的完整句 */
  let entry = null;
  for(const key in ZXCVBN_WARNING_MAP){
    if(warning === key || warning.startsWith(key)){
      entry = ZXCVBN_WARNING_MAP[key];
      break;
    }
  }
  if(!entry) return {zh: warning, en: warning};
  /* 如果是常见弱密码命中，从 sequence 提取命中的 token 追加 */
  if(warning.includes('common password') && result.sequence){
    const dictMatch = result.sequence.find(s => s.pattern === 'dictionary');
    if(dictMatch){
      return {zh: `${entry.zh}: ${dictMatch.token}`, en: `${entry.en}: ${dictMatch.token}`};
    }
  }
  return entry;
}

/* zxcvbn suggestion 中英对照翻译表 */
const ZXCVBN_SUGGESTION_MAP = {
  'Add another word or two': {zh:'增加一两个单词或字符', en:'Add another word or two. Uncommon words are better.'},
  'Use a longer keyboard pattern with more turns': {zh:'使用更长的键盘走位（含更多转向）', en:'Use a longer keyboard pattern with more turns'},
  'Avoid repeated words and characters': {zh:'避免重复单词和字符', en:'Avoid repeated words and characters'},
  'Avoid sequences': {zh:'避免顺序字符', en:'Avoid sequences'},
  "Capitalization doesn't help very much": {zh:'仅靠首字母大写帮助不大', en:"Capitalization doesn't help very much"},
  'All-uppercase is almost as easy to guess as all-lowercase': {zh:'全大写几乎和全小写一样容易猜', en:'All-uppercase is almost as easy to guess as all-lowercase'},
  "Reversed words aren't much harder to guess": {zh:'反写单词并不能显著增加强度', en:"Reversed words aren't much harder to guess"},
  "Predictable substitutions like '@' instead of 'a' don't help very much": {zh:'可预测的替换（如 @ 替换 a）帮助不大', en:"Predictable substitutions like '@' instead of 'a' don't help very much"},
  'Use a few words, avoid common phrases': {zh:'使用多个单词，避免常见短语', en:'Use a few words, avoid common phrases'},
  'No need for symbols, digits, or uppercase letters': {zh:'无需强制符号、数字或大写字母', en:'No need for symbols, digits, or uppercase letters'},
};

function translateSuggestion(s){
  /* 前缀匹配：zxcvbn 可能返回带后缀的完整句 */
  for(const key in ZXCVBN_SUGGESTION_MAP){
    if(s === key || s.startsWith(key)){
      return ZXCVBN_SUGGESTION_MAP[key];
    }
  }
  return {zh: s, en: s};
}

/**
 * 从 zxcvbn sequence 提取命中模式，生成中英对照 issues
 * 区分：中文字典命中 / 平台账号命中 / 键盘走位 / 重复 / 顺序 / 日期
 * 返回：[{zh, en}, ...]
 */
function extractPatterns(sequence, contextInputs){
  const issues = [];
  const seen = new Set();
  const contextSet = new Set(contextInputs.map(s => s.toLowerCase()));

  sequence.forEach(s => {
    if(s.pattern === 'dictionary'){
      const token = (s.token || '').toLowerCase();
      if(contextSet.has(token)){
        const key = `ctx:${token}`;
        if(!seen.has(key)){
          seen.add(key);
          issues.push({zh:`命中平台/账号相关信息: ${s.token}`, en:`Matches platform/account info: ${s.token}`});
        }
      } else if(s.dictionary_name === 'user_inputs'){
        /* 非平台/账号的 user_inputs 命中 = 中文字典命中 */
        const key = `cn:${token}`;
        if(!seen.has(key)){
          seen.add(key);
          issues.push({zh:`命中中文弱密码: ${s.token}`, en:`Matches Chinese weak password: ${s.token}`});
        }
      }
    } else if(s.pattern === 'repeat'){
      const key = `repeat:${s.token}`;
      if(!seen.has(key)){
        seen.add(key);
        issues.push({zh:`包含重复模式: ${s.token}`, en:`Contains repeat pattern: ${s.token}`});
      }
    } else if(s.pattern === 'sequence'){
      const key = `seq:${s.token}`;
      if(!seen.has(key)){
        seen.add(key);
        issues.push({zh:`包含顺序字符模式: ${s.token}`, en:`Contains sequence pattern: ${s.token}`});
      }
    } else if(s.pattern === 'spatial'){
      const key = `spatial:${s.token}`;
      if(!seen.has(key)){
        seen.add(key);
        issues.push({zh:`包含键盘走位模式: ${s.token}`, en:`Contains keyboard pattern: ${s.token}`});
      }
    } else if(s.pattern === 'date'){
      const key = `date:${s.token}`;
      if(!seen.has(key)){
        seen.add(key);
        issues.push({zh:`包含日期: ${s.token}`, en:`Contains date: ${s.token}`});
      }
    }
  });

  return issues;
}

function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}

const MAX_VISIBLE_TOASTS = 3;
let toastPresentationVisible=document.visibilityState==='visible';
function dismissToast(toast){
  if(!toast) return;
  if(toast._pdmHideTimer){clearTimeout(toast._pdmHideTimer);toast._pdmHideTimer=0}
  if(toast._pdmRemoveTimer){clearTimeout(toast._pdmRemoveTimer);toast._pdmRemoveTimer=0}
  toast.remove();
}
function pauseToast(toast){
  if(!toast) return;
  if(toast._pdmDeadline) toast._pdmRemaining=Math.max(0,toast._pdmDeadline-performance.now());
  if(toast._pdmHideTimer){clearTimeout(toast._pdmHideTimer);toast._pdmHideTimer=0}
  if(toast._pdmRemoveTimer){clearTimeout(toast._pdmRemoveTimer);toast._pdmRemoveTimer=0}
  toast._pdmDeadline=0;
  toast.style.visibility='hidden';
  toast.style.animationPlayState='paused';
}
function scheduleToast(toast){
  if(!toast?.isConnected) return;
  if(!toastPresentationVisible){pauseToast(toast);return}
  if(toast._pdmHideTimer||toast._pdmRemoveTimer) return;
  toast.style.visibility='';
  toast.style.animationPlayState='running';
  const remaining=Math.max(0,toast._pdmRemaining);
  toast._pdmDeadline=performance.now()+remaining;
  if(toast._pdmPhase==='exit'){
    toast._pdmRemoveTimer=setTimeout(()=>{toast._pdmRemoveTimer=0;dismissToast(toast)},remaining);
    return;
  }
  toast._pdmHideTimer=setTimeout(()=>{
    toast._pdmHideTimer=0;
    toast._pdmDeadline=0;
    toast._pdmPhase='exit';
    toast._pdmRemaining=300;
    toast.style.animation='toastOut .3s var(--ease) forwards';
    scheduleToast(toast);
  },remaining);
}
function setToastPresentationVisible(visible){
  if(typeof visible!=='boolean') return false;
  toastPresentationVisible=visible;
  if(!visible) clearOperationStatus();
  document.querySelectorAll('#toast-container .toast').forEach(
    toast=>visible?scheduleToast(toast):pauseToast(toast)
  );
  return true;
}

const ACCESSIBLE_OPERATION_KEYS = new Set([
  'toast.operation.failed',
]);
function clearOperationStatus(){
  const status=$('#operation-status');
  if(status) status.textContent='';
}
function announceOperationStatus(key){
  if(!ACCESSIBLE_OPERATION_KEYS.has(key)) return clearOperationStatus();
  announceOperationText(t(key));
}
function announceOperationText(text){
  const status=$('#operation-status');
  if(!status) return;
  status.textContent='';
  if(!toastPresentationVisible||document.visibilityState!=='visible') return;
  const message=String(text||'');
  queueMicrotask(()=>{
    if(status.isConnected&&toastPresentationVisible&&document.visibilityState==='visible'){
      status.textContent=message;
    }
  });
}
function showToast(message,type='info'){
  const c = $('#toast-container');
  if(!c) return;
  while(c.children.length>=MAX_VISIBLE_TOASTS) dismissToast(c.firstElementChild);
  const t = document.createElement('div');
  t.className = 'toast '+type;
  const icon = type==='success'?svgIcon('check',16):type==='error'?'✕':type==='warning'?svgIcon('warning',16):svgIcon('info',16);
  t.innerHTML = `<span class="toast-icon">${icon}</span><span>${escapeHtml(message)}</span>`;
  t._pdmPhase='show';
  t._pdmRemaining=2000;
  t._pdmDeadline=0;
  t._pdmHideTimer=0;
  t._pdmRemoveTimer=0;
  c.appendChild(t);
  scheduleToast(t);
}

/* 离线密码管理器不维护平台 logo（品牌图标会过时且无法实时更新）
   改用"首字母 + 哈希色块"作为视觉锚点 —— Bitwarden 等离线工具的行业标准
   - 任何平台都有稳定视觉标识，无需内置图标库
   - 同一平台名始终生成相同颜色（哈希稳定）
   - 完全离线可行，符合本软件"本地优先"定位 */
function platformIcon(name){
  if(!name) return '?';
  return name.charAt(0).toUpperCase();
}
function platformColor(name){
  if(!name) return '#6366f1';
  // 基于名称字符生成稳定 hash → hue，HSL→hex 以兼容 alpha 后缀（22/44）
  let hash = 0;
  for(let i=0;i<name.length;i++) hash = name.charCodeAt(i) + ((hash<<5)-hash);
  const hue = Math.abs(hash) % 360;
  const s = 0.55, l = 0.52, c = (1-Math.abs(2*l-1))*s;
  const x = c*(1-Math.abs(((hue/60)%2)-1)), m = l-c/2;
  let r,g,b;
  if(hue<60){r=c;g=x;b=0} else if(hue<120){r=x;g=c;b=0}
  else if(hue<180){r=0;g=c;b=x} else if(hue<240){r=0;g=x;b=c}
  else if(hue<300){r=x;g=0;b=c} else{r=c;g=0;b=x}
  const h = v => Math.round((v+m)*255).toString(16).padStart(2,'0');
  return `#${h(r)}${h(g)}${h(b)}`;
}

function platformColorClass(name){
  if(!name) return 'pdm-platform-hue-0';
  let hash = 0;
  for(let i=0;i<name.length;i++) hash = name.charCodeAt(i) + ((hash<<5)-hash);
  return `pdm-platform-hue-${Math.abs(hash)%360}`;
}

/* ============================================================
   启动页
   ============================================================ */
/* 相对时间格式化：依据最近一次成功连接时间与当前时间的差值渲染。
   档位规则（< 1 小时按时间差，≥ 1 小时按自然日）：
     < 60 秒        → "刚刚"
     < 60 分钟      → "N 分钟前"
     同一自然日      → "今天"
     上一自然日      → "昨天"
     2-6 自然日     → "N 天前"
     7-29 自然日    → "N 周前"（Math.floor(days / 7)）
     ≥ 30 自然日    → "N 个月前"（Math.floor(days / 30)）
   Win 端差异：Python 用 datetime.now() 取当前时间，时间戳从 security.st 解密获取。 */
function formatRelativeTime(ts){
  const now = new Date();
  const past = new Date(ts);
  const deltaSec = Math.floor((now - past) / 1000);
  const deltaMin = Math.floor(deltaSec / 60);
  if(deltaSec < 60) return '刚刚';
  if(deltaMin < 60) return `${deltaMin} 分钟前`;
  const dayStart = (d)=> new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const days = Math.round((dayStart(now) - dayStart(past)) / 86400000);
  if(days === 0) return '今天';
  if(days === 1) return '昨天';
  if(days <= 6) return `${days} 天前`;
  if(days <= 29) return `${Math.floor(days / 7)} 周前`;
  return `${Math.floor(days / 30)} 个月前`;
}

function renderRecents(){
  const list = $('#recent-list');
  list.innerHTML = recents.map(r=>`
    <li class="recent-item">
      <button type="button" class="recent-select" data-pdm-recent-action="select" data-path="${escapeHtml(r.path)}" aria-label="${escapeHtml(t('startup.recent.select'))}: ${escapeHtml(r.name)}">
        <div class="recent-icon">${svgIcon(r.icon, 16)}</div>
        <div class="recent-info">
          <div class="recent-name">${escapeHtml(r.name)}</div>
          <div class="recent-path">${escapeHtml(r.path)}</div>
        </div>
        <div class="recent-time">${escapeHtml(formatRelativeTime(r.last_connected))}</div>
      </button>
      <button type="button" class="recent-remove" data-pdm-recent-action="remove" data-path="${escapeHtml(r.path)}" aria-label="${escapeHtml(t('startup.recent.remove'))}: ${escapeHtml(r.name)}">${escapeHtml(t('startup.recent.remove'))}</button>
    </li>
  `).join('');
  /* 事件委托：路径通过 data-path 属性传递（HTML 属性中原样保留反斜杠），
     避免内联 onclick 中路径被 JS 字符串字面量转义吞掉（\U→U, \b→退格, \2→八进制） */
  list.querySelectorAll('.recent-select').forEach(button=>{
    button.addEventListener('click', ()=>connectRecent(button.dataset.path));
  });
  list.querySelectorAll('.recent-remove').forEach(button=>{
    button.addEventListener('click', ()=>{
      const index = recents.findIndex(recent=>recent.path===button.dataset.path);
      if(index >= 0) recents.splice(index,1);
      renderRecents();
    });
  });
}
renderRecents();

function connectRecent(path){
  /* 点击最近项仅填充路径栏 + 聚焦密码框，不直接连接。
     用户需确认/输入主密码后手动点"连接/创建"，避免跳过密码确认环节。 */
  $('#db-path').value=path;
  const startupCard = $('.startup-card');
  if(startupCard) startupCard.classList.remove('is-locked');
  const feedback = $('#connection-feedback');
  if(feedback){
    feedback.className = 'connection-feedback';
    feedback.textContent = '';
  }
  $('#db-password').focus();
  showToast(t('toast.fillPath'),'info');
}

function toggleStartupPassword(){
  toggleStaticPasswordVisibility('db-password','startup-eye');
}

function browseDatabase(){showToast(t('toast.browse'),'info');}

/* M2.4 键盘/IME 合同：组合输入确认键不能误触发连接；组合结束后的独立
   Enter 才与“连接 / 创建”按钮具有相同语义。M3 仍须改为类型化 Bridge 命令。 */
['db-path','db-password'].forEach(id=>{
  const input = document.getElementById(id);
  if(!input) return;
  input.addEventListener('keydown',event=>{
    if(event.isComposing || event.keyCode===229) return;
    if(event.key==='Enter'){
      event.preventDefault();
      connectDatabase();
    }
  });
});

function connectDatabase(){
  const startupCard = $('.startup-card');
  if(startupCard && startupCard.classList.contains('is-locked')){
    const password = $('#db-password');
    if(password){
      password.value = '';
      setStaticPasswordVisibility('db-password','startup-eye',false);
      password.focus();
    }
    const feedback = $('#connection-feedback');
    if(feedback){
      feedback.className = 'connection-feedback error';
      feedback.textContent = t('connection.error.locked_too_many');
    }
    return;
  }
  const p = $('#startup-page');
  const bar = $('#startup-minimized-bar');
  const dbName = $('#db-path').value.split(/[\\/]/).pop() || '数据库';
  p.classList.add('hidden');
  p.classList.remove('minimized');
  if(bar) bar.classList.remove('show');
  setTimeout(()=>{
    /* main-app 框架始终可见，无需切换 visible 类；
       这里仅切换顶栏标题为密码库（连接前显示"连接数据库"） */
    state.connected = true;
    state.startupMinimized = false;
    /* 连接成功默认切回密码库（用户可能在 tools/settings 页点 bar 唤起 modal 后连接） */
    if(state.currentNav !== 'vault') navigateTo('vault');
    $('#topbar-title').textContent = t('topbar.title.vault');
    /* 更新状态栏 */
    $('#status-dot').classList.add('connected');
    $('#status-text').innerHTML = `${t('status.connect.prefix')}<strong class="pdm-inline-1552366efe">${escapeHtml(dbName)}</strong>`;
    /* 启用数据库依赖按钮（保存为记录 / 修改数据库密码 / 导入导出数据） */
    updateDbDependentUI(true);
    /* 设置页加 .connected 类（启用所有配置项，移除未连接态灰显）。
       工具页生成器配置不需要 .connected 类——未连接时配置可用但不持久化（见 syncGenLength/toggleCharset 注释）。 */
    const settingsPage = $('#page-settings');
    if(settingsPage) settingsPage.classList.add('connected');
    /* 更新设置页"当前数据库"显示 */
    updateCurrentDbInfo(dbName);
    renderAll();
    showToast(t('toast.connected') + dbName,'success');
    /* 启动超时自动锁定检测（仅连接后启用） */
    startIdleCheck();
  },300);
}

/* 启动页 modal 状态控制：未连接时，切到 tools/settings 自动最小化（让出内容区），
   切回 vault/notes/security 自动恢复展开（盖住空内容区，引导连接）。
   用户点状态栏连接入口调 expandStartupModal() 强制恢复展开。 */
function minimizeStartupModal(){
  if(state.connected) return;
  const p = $('#startup-page');
  const bar = $('#startup-minimized-bar');
  p.classList.add('minimized');
  if(bar) bar.classList.add('show');
  state.startupMinimized = true;
}

function expandStartupModal(){
  if(state.connected) return;
  if(state.currentNav!=='vault'){
    navigateTo('vault');
    return;
  }
  const p = $('#startup-page');
  const bar = $('#startup-minimized-bar');
  const restoreFocus = bar?.contains(document.activeElement);
  p.classList.remove('minimized');
  if(bar) bar.classList.remove('show');
  state.startupMinimized = false;
  if(restoreFocus) $('#db-path')?.focus({preventScroll:true});
}

/* 数据库依赖按钮的禁用/启用切换。
   - 工具页：保存为记录（saveGenerated）
   - 设置页 · 数据库组：修改数据库密码（openChangeDbPasswordDialog）、导入导出数据（openImportExportDialog）
   未连接时禁用 + title 提示"请先连接数据库"；连接后启用。
   按钮用 data-requires-db="true" 标记，统一通过属性选择器匹配，
   避免依赖 onclick 字符串精确匹配（函数改名后选择器不会失效）。
   注：按钮用原生 [disabled] 属性，CSS 保留 pointer-events:auto 让 title tooltip 可 hover 显示。 */
function updateDbDependentUI(connected){
  const tip = connected ? '' : t('startup.dependent.disabled.tip');
  document.querySelectorAll('button[data-requires-db="true"]').forEach(btn=>{
    btn.disabled = !connected;
    btn.title = tip;
  });
}

/* 设置页"当前数据库"行：未连接显示"未连接"，连接后显示"库名 · N 条记录" */
function updateCurrentDbInfo(dbName){
  const el = document.querySelector('#page-settings .db-info');
  if(!el) return;
  if(state.connected && dbName){
    const count = (state.passwords || []).length;
    el.textContent = `${dbName} · ${count} ${t('settings.db.current.records')}`;
    el.removeAttribute('data-i18n');
  }else{
    el.textContent = t('settings.db.current.disconnected');
    el.setAttribute('data-i18n','settings.db.current.disconnected');
  }
}

function lockApp(){
  clearDemoRecovery();
  /* 安全清理：锁定时必须清空剪贴板 + 释放内存中的敏感数据
     - 剪贴板：可能残留用户复制的密码/账号/TOTP 验证码
     - 内存：解密后的 passwords/notes 数组、TOTP 实时验证码、Argon2id 派生密钥
     Win 端对应：core/security.py 的 lock() + core/clipboard.py 的 clear() +
     core/crypto.py 的 SecureKeyBuffer.zero()（用 ctypes.memset 清零内存） */
  /* 停止 idle 检测，避免锁定后重复触发（解锁后会重新启动） */
  stopIdleCheck();
  /* 清空内存中的敏感数据（原型层重置 state.passwords/notes，Win 端用 SecureKeyBuffer.zero()） */
  state.passwords = [];
  state.notes = [];
  state.expandedId = null;
  state.notesCardOpenId = null;
  state.notesCardEditId = null;
  state.notesCardDraft = null;
  state.splitSelectedId = null;
  state.totpCode = null;  /* 清空 TOTP 实时验证码 */
  /* 启动页也是会话边界：旧错误、旧密码和可见密码状态不得跨锁定残留。 */
  const connectionFeedback = $('#connection-feedback');
  if(connectionFeedback){
    connectionFeedback.className = 'connection-feedback';
    connectionFeedback.textContent = '';
  }
  const startupPassword = $('#db-password');
  if(startupPassword){
    startupPassword.value = '';
    setStaticPasswordVisibility('db-password','startup-eye',false);
  }
  const startupCard = $('.startup-card');
  if(startupCard) startupCard.classList.remove('is-connecting','is-locked');
  ['#db-path','#db-password','.browse-btn','.eye-btn','.connect-btn'].forEach(selector=>{
    const control = $(selector); if(control) control.disabled = false;
  });
  const startupConnect = $('.connect-btn');
  if(startupConnect){
    startupConnect.dataset.i18n = 'startup.button.connect';
    startupConnect.textContent = t('startup.button.connect');
  }
  /* 派生密钥清理：原型无真实密钥，Win 端调用 SecureKeyBuffer.zero() 清零 Argon2id 派生密钥 */
  /* 若由超时自动锁定触发，显示专属 Toast（区分手动锁定） */
  const triggeredByIdle = state.autoLockTriggered;
  state.autoLockTriggered = false;

  /* 同步立即切换到未连接态：必须在 setTimeout 之前完成，否则 300ms 内主显示区
     仍残留连接成功时的内容（密码列表/记事/体检结果），透过半透明遮罩可见 = 信息泄露。
     顺序：① state.connected=false（让 render* 走未连接空状态分支）
           ② updateDbDependentUI/updateCurrentDbInfo（禁用按钮 + 重置显示）
           ③ 重渲染当前页（清空 DOM 残留）
           ④ 若当前在 tools/settings，切回 vault（modal 展开盖住内容区） */
  state.connected = false;
  state.startupMinimized = false;
  updateDbDependentUI(false);
  updateCurrentDbInfo(null);
  /* 设置页移除 .connected 类（禁用配置项，防止未身份验证修改习惯配置）。
     工具页生成器配置不受影响——未连接时配置可用但不持久化。 */
  const settingsPage = $('#page-settings');
  if(settingsPage) settingsPage.classList.remove('connected');
  /* 重渲染当前页面，清空 DOM 残留（走未连接空状态分支，显示"未连接数据库"提示） */
  if(state.currentNav === 'vault') renderVault();
  else if(state.currentNav === 'notes') renderNotes();
  else if(state.currentNav === 'security') renderSecurity();
  /* 当前在 tools/settings 时切回 vault（触发 modal 展开盖住内容区） */
  if(state.currentNav !== 'vault') navigateTo('vault');
  /* Win 端在同步擦空所有 UI/明文缓存后强制清剪贴板，再最后销毁派生密钥。 */
  clearClipboard();

  setTimeout(()=>{
    /* modal 淡入动画 + 状态栏更新（数据已在同步阶段清空） */
    $('#startup-page').classList.remove('hidden');
    $('#startup-page').classList.remove('minimized');
    const bar = $('#startup-minimized-bar');
    if(bar) bar.classList.remove('show');
    $('#topbar-title').textContent = t('topbar.title.connect');
    /* 更新状态栏 */
    $('#status-dot').classList.remove('connected');
    $('#status-text').textContent = t('status.disconnected');
    if(triggeredByIdle) showToast(t('toast.autolocked'),'info');
  },300);
}

/* 关闭/刷新程序时强制清理（Win 端对应 main_window.closeEvent → lockApp 清理流程）。
   M4 产品候选由原生 Bridge 安全边界负责，禁止此 M1 夹具触碰系统剪贴板。 */
if(!PDM_IS_M4_ISOLATED){
window.addEventListener('beforeunload', ()=>{
  /* 状态数组同步清空。浏览器剪贴板 API 只能 best-effort；Win 端不能依赖
     此异步能力，而是在 closeEvent 内直接同步调用 Win32 清理。 */
  /* beforeunload 触发时文档已失焦，navigator.clipboard.writeText 会抛 NotAllowedError，
     Promise 异步异常 try/catch 捕获不到，必须用 .catch() 静默吞掉避免控制台刷红。
     Win 端无此限制（ctypes + user32.dll 直接操作剪贴板）。 */
  if(navigator.clipboard) navigator.clipboard.writeText('').catch(()=>{});
  state.passwords = [];
  state.notes = [];
  state.totpCode = null;
  /* Win 端：SecureKeyBuffer.zero() 在 closeEvent 中同步执行 */
}, {capture:true});
}

/* ============================================================
   超时自动锁定（Auto Lock）
   ------------------------------------------------------------
   原理：监听 mousemove/keydown/click/touchstart 更新 lastActivityTime，
        setInterval 每秒轮询 idle 时长，超过阈值则触发 lockApp()。
   Win 端对应：core/security.py 用 Windows API GetLastInputInfo() 获取
        系统级最后输入时间（比 Qt 事件过滤更准确，能感知应用外活动），
        QTimer 每秒轮询；QuickBar 唤出时不应触发锁定（用户在用 QuickBar 算活动）。
   配置持久化：settings.json 的 auto_lock 字段 {enabled:bool, timeout:int}。
   ============================================================ */

function startIdleCheck(){
  /* 仅在已连接且启用自动锁定时启动；未连接时无敏感数据无需检测 */
  if(!state.connected || !state.autoLock.enabled) return;
  if(state.idleCheckTimer) return;  /* 防止重复启动 */
  state.lastActivityTime = Date.now();
  state.idleCheckTimer = setInterval(()=>{
    /* 双重校验：连接断开或禁用后立即停止 */
    if(!state.connected || !state.autoLock.enabled){
      stopIdleCheck();
      return;
    }
    const idleMs = Date.now() - state.lastActivityTime;
    if(idleMs >= state.autoLock.timeout * 60 * 1000){
      state.autoLockTriggered = true;  /* 标记由超时触发，lockApp 中据此显示专属 Toast */
      lockApp();
    }
  }, 1000);
}

function stopIdleCheck(){
  if(state.idleCheckTimer){
    clearInterval(state.idleCheckTimer);
    state.idleCheckTimer = null;
  }
}

/* 用户活动事件 → 更新 lastActivityTime
   passive:true 避免阻塞滚动；捕获阶段绑定确保先于其他监听器 */
if(!PDM_IS_M4_ISOLATED){
  ['mousemove','keydown','click','touchstart'].forEach(evt=>{
    document.addEventListener(evt, ()=>{ state.lastActivityTime = Date.now(); }, {passive:true, capture:true});
  });
}

/* 设置面板：切换自动锁定开关 */
function toggleAutoLock(el){
  el.classList.toggle('on');
  state.autoLock.enabled = el.classList.contains('on');
  if(state.autoLock.enabled && state.connected) startIdleCheck();
  else stopIdleCheck();
  /* 联动禁用/启用阈值设置行：关闭时灰化不可调，开启时恢复 */
  const thresholdRow = $('#autolock-slider').closest('.setting-row');
  const disabled = !state.autoLock.enabled;
  thresholdRow.classList.toggle('is-disabled', disabled);
  $('#autolock-slider').disabled = disabled;
  $('#autolock-num').disabled = disabled;
  /* Win 端：同步写入 settings.json 的 auto_lock.enabled */
}

/* 设置面板：同步自动锁定阈值 slider 与 number 输入 */
function syncAutoLockTimeout(value, fromNum){
  value = parseInt(value) || 1;
  value = Math.max(1, Math.min(60, value));
  if(fromNum) $('#autolock-slider').value = value;
  else $('#autolock-num').value = value;
  state.autoLock.timeout = value;
  /* Win 端：同步写入 settings.json 的 auto_lock.timeout */
}

/* ============================================================
   导航
   ============================================================ */
const navTitles = {vault:'topbar.title.vault',notes:'topbar.title.notes',security:'topbar.title.security',tools:'topbar.title.tools',settings:'topbar.title.settings',help:'topbar.title.help'};
function navigateTo(nav, renderContent = true){
  if(state.currentNav==='notes' && nav!=='notes' && !canLeaveNotesCardEdit()) return;
  if(state.currentNav!==nav && (nav==='settings' || state.currentNav==='settings')){
    state.settingsSearch='';
    if(!PDM_IS_M4_ISOLATED) state.search='';
    setGlobalSearchValue('');
  }
  if(nav !== 'vault'){state.passwordVisible = {};clearDemoRecovery();}
  state.currentNav = nav;
  $$('.nav-item').forEach(n=>{
    const active = n.dataset.nav===nav;
    n.classList.toggle('active',active);
    if(active) n.setAttribute('aria-current','page');
    else n.removeAttribute('aria-current');
  });
  $$('.page').forEach(p=>p.classList.remove('active'));
  $('#page-'+nav).classList.add('active');
  const topbarTitle = $('#topbar-title');
  if(topbarTitle){
    topbarTitle.dataset.i18n = navTitles[nav];
    topbarTitle.textContent = t(navTitles[nav]);
  }
  syncNotesCardsSearchPlaceholder(nav);
  if(nav!=='vault'&&nav!=='notes') syncGlobalSearchStatus(0,'');
  /* 未连接时的启动页 modal 状态控制：
     - 切到 tools/settings：modal 最小化（让出内容区，用户可使用工具/设置）
     - 切回 vault/notes/security：modal 恢复展开（盖住空内容区，引导连接数据库）
     已连接时 modal 已 hidden，minimizeStartupModal 内部 state.connected 守卫会直接 return，无副作用。 */
  if(!state.connected){
    if(nav==='tools' || nav==='settings' || nav==='help'){
      minimizeStartupModal();
    }else{
      expandStartupModal();
    }
  }
  if(renderContent && nav==='vault') renderVault();
  if(renderContent && nav==='notes') renderNotes();
  if(renderContent && nav==='security') renderSecurity();
  /* 切到设置页时刷新"当前数据库"显示（连接后切换可能记录数已变） */
  window.renderUpdates?.();
  if(nav==='settings'){
    updateCurrentDbInfo(null);
    filterSettings();
  }
}

/* ============================================================
   搜索
   ============================================================ */
function syncGlobalSearchClear(){
  const input=$('#global-search');
  const clear=$('#global-search-clear');
  if(!input||!clear) return;
  clear.hidden=!input.value;
  clear.disabled=input.disabled;
  syncGlobalSearchValidation();
}

function globalSearchFits(value){
  let count=0;
  // 与原生 Query 按 Unicode 码点计数；每码点最多四个 UTF-8 字节。
  for(const character of value){
    if(++count>128 || character==='\0') return false;
  }
  return true;
}

function syncGlobalSearchValidation(){
  const input=$('#global-search'),error=$('#global-search-error');
  if(!input || !error) return;
  const invalid=!input.disabled && !globalSearchFits(input.value);
  input.setAttribute('aria-invalid',String(invalid));
  error.hidden=!invalid;
  error.textContent=invalid?t('topbar.search.limit'):'';
  if(invalid) $('#global-search-status').textContent='';
}

function syncGlobalSearchStatus(count,query=state.search){
  const status=$('#global-search-status');
  if(!status) return;
  if($('#global-search')?.getAttribute('aria-invalid')==='true') return;
  status.textContent=String(query||'').trim()
    ? t('topbar.search.results').replace('{n}',String(Math.max(0,Number(count)||0)))
    : '';
}

function setGlobalSearchValue(value){
  const input=$('#global-search');
  if(input) input.value=String(value??'');
  syncGlobalSearchClear();
}

function clearGlobalSearch(){
  const input=$('#global-search');
  if(!input||input.disabled) return;
  setGlobalSearchValue('');
  handleSearch('');
  input.focus({preventScroll:true});
}

function handleSearch(v){
  if(state.currentNav==='settings'){
    syncGlobalSearchClear();
    if(!globalSearchFits(v)) return;
    state.settingsSearch=v.trim().toLowerCase();
    filterSettings();
    return;
  }
  if(state.currentNav==='notes' && !canLeaveNotesCardEdit()){
    setGlobalSearchValue(state.search);
    return;
  }
  syncGlobalSearchClear();
  if(!globalSearchFits(v)) return;
  state.search = v.trim().toLowerCase();
  if(state.currentNav==='vault') renderVault();
  if(state.currentNav==='notes') renderNotes();
  syncGlobalSearchClear();
}

function settingsFieldMatches(value,query){
  const text=String(value||'').toLocaleLowerCase();
  const needle=String(query||'').toLocaleLowerCase();
  if(text.includes(needle)) return true;
  if(!/[\p{Script=Han}]/u.test(text)||typeof pinyinPro==='undefined') return false;
  let full='',initials='';
  for(const [segment] of text.matchAll(/[\p{Script=Han}]+|[^\p{Script=Han}]+/gu)){
    if(/[\p{Script=Han}]/u.test(segment)){
      const syllables=pinyinPro.pinyin(segment,{toneType:'none',type:'array'});
      if(syllables.length!==Array.from(segment).length) return false;
      full+=syllables.join('');
      initials+=syllables.map(syllable=>syllable[0]).join('');
    }else{
      full+=segment;
      initials+=segment;
    }
  }
  const normalized=needle.replaceAll('ü','v');
  return full.replaceAll('ü','v').includes(normalized)||initials.replaceAll('ü','v').includes(normalized);
}

function filterSettings(){
  const query=state.settingsSearch;
  let count=0;
  $$('#page-settings .settings-group').forEach(group=>{
    const groupName=group.querySelector('.settings-group-title').textContent;
    let visible=0;
    group.querySelectorAll('.setting-row').forEach(row=>{
      const fields=[groupName,...Array.from(row.querySelectorAll('.setting-name,.setting-desc'),el=>el.textContent)];
      row.hidden=Boolean(query && !fields.some(field=>settingsFieldMatches(field,query)));
      if(!row.hidden) visible++;
    });
    group.hidden=visible===0;
    count+=visible;
  });
  const empty=$('#settings-search-empty');
  if(empty) empty.hidden=count!==0;
  const active=document.activeElement;
  if(state.currentNav==='settings' && active?.closest('#page-settings [hidden]')){
    $('#global-search')?.focus({preventScroll:true});
  }
  if(state.currentNav==='settings') syncGlobalSearchStatus(count,query);
}

function filterPasswords(){
  let list = [...passwords];
  if(state.filter==='favorite') list = list.filter(p=>p.is_favorite);
  if(state.filter==='weak') list = list.filter(p=>p.strength==='weak');
  if(state.filter==='duplicate'){
    const dupMap = getDuplicateGroups();
    list = list.filter(p=>dupMap[p.id]);
  }
  if(state.filter==='similar'){
    const similarMap = getSimilarNameGroups();
    list = list.filter(p=>similarMap[p.id]);
  }
  if(state.search){
    list = list.filter(p=>settingsFieldMatches(p.platform,state.search)||settingsFieldMatches(p.account,state.search));
  }
  const sort = state.sortMode || 'updated';
  if(sort==='name') list.sort((a,b)=>{
    const aPlatform=String(a.platform||'').toLowerCase();
    const bPlatform=String(b.platform||'').toLowerCase();
    if(aPlatform<bPlatform) return -1;
    if(aPlatform>bPlatform) return 1;
    if(state.filter==='all' && a.is_favorite!==b.is_favorite) return a.is_favorite?-1:1;
    const aAccount=String(a.account||'').toLowerCase();
    const bAccount=String(b.account||'').toLowerCase();
    if(aAccount<bAccount) return -1;
    if(aAccount>bAccount) return 1;
    return Number(a.id)-Number(b.id);
  });
  else if(sort==='strength') list.sort((a,b)=>{
    const ar=strengthOrder[a.strength] ?? 3, br=strengthOrder[b.strength] ?? 3;
    const primary=ar-br;
    if(primary) return primary;
    if(ar===3) return Number(a.id)-Number(b.id);
    if(state.filter==='all' && a.is_favorite!==b.is_favorite) return a.is_favorite?-1:1;
    return Number(a.id)-Number(b.id);
  });
  else list.sort((a,b)=>{
    const primary=b.updated_at.localeCompare(a.updated_at);
    if(primary) return primary;
    if(state.filter==='all' && a.is_favorite!==b.is_favorite) return a.is_favorite?-1:1;
    return Number(b.id)-Number(a.id);
  });
  return list;
}

/* 获取重复密码分组：返回 {passwordId: groupNumber} */
function getDuplicateGroups(){
  // 按密码明文分组（相同密码 = 同一组，与 platform 无关）
  const groups = {};
  passwords.forEach(p=>{
    if(!p.password) return;
    if(!groups[p.password]) groups[p.password] = [];
    groups[p.password].push(p);
  });
  // 仅保留重复组（length>1），按"组内最小 id"升序分配稳定组号
  // 组号绑定到密码值：同密码值的条目永远同组；组删除某条后组号不变（最小 id 不变）
  // 原型用 id 作代理（单调递增 = 创建顺序），Win 端用 created_at 字段排序
  const dups = Object.values(groups).filter(items=>items.length>1);
  dups.sort((a,b)=> Math.min(...a.map(p=>p.id)) - Math.min(...b.map(p=>p.id)));
  const result = {};
  dups.forEach((items, idx)=>{
    items.forEach(p=>result[p.id] = idx+1);
  });
  return result;
}

/* 公开原型仅演示：JavaScript 没有 Python 完整 casefold，正式分组只信原生后端。 */
function getSimilarNameGroups(){
  const groups = {};
  passwords.forEach(p=>{
    const key = String(p.platform||'').replace(/\s/gu,'').toLowerCase();
    if(!key) return;
    (groups[key] ||= []).push(p);
  });
  const matches = Object.values(groups).filter(items=>items.length>1);
  matches.sort((a,b)=>Math.min(...a.map(p=>p.id))-Math.min(...b.map(p=>p.id)));
  const result = {};
  matches.forEach((items,index)=>items.forEach(p=>{result[p.id]=index+1}));
  return result;
}

/* ============================================================
   密码库渲染
   ============================================================ */
function demoStrengthRetry(p){
  if(p.strength!=='failed') return '';
  const label=state.lang==='en'?'Retry':'重试';
  return `<button type="button" class="item-strength-label strength-retry" data-demo-strength-retry="${p.id}" aria-label="${label} ${escapeHtml(p.platform)}">${label}</button>`;
}

function clearDemoRecovery(){
  state.recoveryVisible=null;
}
function demoRecoveryRows(p){
  const codes=Array.isArray(p.recovery_codes)?p.recovery_codes:[];
  if(!codes.length) return '';
  const label=state.lang==='zh'?`${t('vault.detail.recovery')}（${codes.length}）`:`${t('vault.detail.recovery')} (${codes.length})`;
  return `<div class="detail-row"><div class="detail-label">${label}</div>
    <div class="detail-value recovery"><div class="recovery-code-list">${codes.map((code,index)=>{
      const visible=state.recoveryVisible?.id===p.id&&state.recoveryVisible?.index===index;
      return `<div class="recovery-code-item"><span class="recovery-code-text" aria-label="${t(visible?'vault.recovery.visible':'vault.recovery.hidden')}">${visible?escapeHtml(code.value):'••••••••'}</span>
        <span class="recovery-code-status">${t(code.used?'vault.recovery.used':'vault.recovery.unmarked')}</span>
        <div class="actions"><button type="button" class="btn-icon" data-pdm-onclick="toggleDemoRecovery(${p.id},${index})" title="${t(visible?'vault.recovery.hide':'vault.recovery.show')}" aria-label="${t(visible?'vault.recovery.hide':'vault.recovery.show')}" aria-pressed="${visible}">${svgIcon(visible?'eye-closed':'eye',15)}</button>
        <button type="button" class="btn-icon" data-pdm-onclick="copyDemoRecovery(${p.id},${index})" title="${t('vault.recovery.copy')}" aria-label="${t('vault.recovery.copy')}">${svgIcon('key',15)}</button>
        <button type="button" class="btn-icon" data-pdm-onclick="markDemoRecovery(${p.id},${index})" title="${t(code.used?'vault.recovery.undo':'vault.recovery.mark')}" aria-label="${t(code.used?'vault.recovery.undo':'vault.recovery.mark')}">${svgIcon(code.used?'repeat':'check',15)}</button></div></div>`;
    }).join('')}</div></div></div>`;
}
function toggleDemoRecovery(id,index){
  if(state.recoveryVisible?.id===id&&state.recoveryVisible?.index===index) clearDemoRecovery();
  else{
    clearDemoRecovery();
    state.recoveryVisible={id,index};
  }
  renderVault();
}
function copyDemoRecovery(id,index){
  const code=passwords.find(p=>p.id===id)?.recovery_codes?.[index];
  if(code) copyText(code.value,t('vault.detail.recovery'));
}
function markDemoRecovery(id,index){
  const record=passwords.find(p=>p.id===id),code=record?.recovery_codes?.[index];
  if(!code) return;
  code.used=!code.used;
  clearDemoRecovery();
  renderVault();
}
document.addEventListener('click', (event)=>{
  const button=event.target.closest?.('[data-demo-strength-retry]');
  if(!button) return;
  event.stopPropagation();
  const record=passwords.find(p=>p.id===Number(button.dataset.demoStrengthRetry));
  if(record){ record.strength=evalStrength(record.password||'',record.platform,record.account); renderAll(); }
});

function renderVault(){
  // 未连接空状态：密码库需要数据库，未连接时显示提示（modal 已盖住，但仍渲染空状态作为背后内容）
  if(!state.connected){
    $('#count-all').textContent = '0';
    $('#count-fav').textContent = '0';
    $('#count-weak').textContent = '0';
    $('#count-dup').textContent = '0';
    $('#count-similar').textContent = '0';
    const emptyHtml = `<div class="empty-state"><div class="icon">${svgIcon('lock',40)}</div><div>${t('startup.empty.vault')}</div></div>`;
    $('#view-list').style.display='flex';
    $('#view-list').innerHTML = emptyHtml;
    $('#view-split').style.display='none';
    $('#split-list').innerHTML = '';
    $('#split-detail').innerHTML = '';
    if(state.currentNav==='vault') syncGlobalSearchStatus(0,'');
    renderFixBanner();
    return;
  }
  // 更新计数
  $('#count-all').textContent = passwords.length;
  $('#count-fav').textContent = passwords.filter(p=>p.is_favorite).length;
  $('#count-weak').textContent = passwords.filter(p=>p.strength==='weak').length;
  const dupIds = Object.keys(getDuplicateGroups());
  $('#count-dup').textContent = dupIds.length;
  $('#count-similar').textContent = Object.keys(getSimilarNameGroups()).length;
  $$('#filter-chips .chip').forEach(c=>c.classList.toggle('active',c.dataset.filter===state.filter));

  const list = filterPasswords();
  if(state.currentNav==='vault') syncGlobalSearchStatus(list.length);
  renderListView(list);
  renderSplitView(list);
  // 同步刷新引导修复横幅（流程中跳转回密码库时可见）
  renderFixBanner();
}

function renderListView(list){
  const wrap = $('#view-list');
  if(state.viewMode!=='list'){wrap.style.display='none';return}
  wrap.style.display='flex';
  if(list.length===0){
    wrap.innerHTML = `<div class="empty-state"><div class="icon">${svgIcon('search',40)}</div><div>${t('vault.empty')}</div></div>`;
    return;
  }
  const dupMap = getDuplicateGroups();
  const similarMap = getSimilarNameGroups();
  wrap.innerHTML = list.map(p=>{
    const grp = dupMap[p.id];
    const dupTag = grp?`<span class="dup-tag">${t('vault.dup.tag')}${grp}</span>`:'';
    const similar = similarMap[p.id];
    const similarTag = similar?`<span class="similar-tag">${t('vault.similar.tag')}${similar}</span>`:'';
    return `
    <div class="list-item ${state.expandedId===p.id?'expanded':''}" data-id="${p.id}">
      <div class="item-summary" data-pdm-onclick="toggleAccordionFromSummary(event,${p.id})">
        ${favStarHTML(p.id,p.is_favorite)}
        <div class="item-platform">
          <div class="platform-icon ${platformColorClass(p.platform)}">${platformIcon(p.platform)}</div>
          <div class="pdm-inline-22a08c80a9">
            <div class="platform-name"><span class="platform-name-text">${escapeHtml(p.platform)}</span>${dupTag}${similarTag}</div>
            <div class="platform-account">${escapeHtml(p.account)}</div>
          </div>
        </div>
        <div class="item-meta">
          <span class="strength-dot strength-${p.strength}"></span>
          <span class="item-strength-label ${p.strength}">${t('common.strength.'+p.strength)}</span>
          ${demoStrengthRetry(p)}
          <div class="quick-actions">
            <button class="btn-icon" data-pdm-onclick="event.stopPropagation();copyText('${escapeHtml(p.account)}','${t('vault.detail.account')}')" title="${t('vault.copy.account')}"><svg class="svg-fill" width="15" height="15" viewBox="0 0 256 256" aria-hidden="true"><path d="M230.93,220a8,8,0,0,1-6.93,4H32a8,8,0,0,1-6.92-12c15.23-26.33,38.7-45.21,66.09-54.16a72,72,0,1,1,73.66,0c27.39,8.95,50.86,27.83,66.09,54.16A8,8,0,0,1,230.93,220Z"/></svg></button>
            <button class="btn-icon" data-pdm-onclick="event.stopPropagation();copyText('${escapeHtml(p.password)}','${t('vault.detail.password')}')" title="${t('vault.copy.password')}"><svg class="svg-fill" width="15" height="15" viewBox="0 0 256 256" aria-hidden="true"><path d="M216.57,39.43A80,80,0,0,0,83.91,120.78L28.69,176A15.86,15.86,0,0,0,24,187.31V216a16,16,0,0,0,16,16H72a8,8,0,0,0,8-8V208H96a8,8,0,0,0,8-8V184h16a8,8,0,0,0,5.66-2.34l9.56-9.57A79.73,79.73,0,0,0,160,176h.1A80,80,0,0,0,216.57,39.43ZM180,92a16,16,0,1,1,16-16A16,16,0,0,1,180,92Z"/></svg></button>
          </div>
          <span class="chevron">▼</span>
        </div>
      </div>
      <div class="item-detail">
        <div class="detail-inner">
          <div class="detail-row">
            <div class="detail-label">${t('vault.detail.account')}</div>
            <div class="detail-value account">
              <span class="text" tabindex="0" role="group" aria-label="${t('vault.detail.account')}">${escapeHtml(p.account)}</span>
              <div class="actions"><button class="btn-icon" data-pdm-onclick="copyText('${escapeHtml(p.account)}','${t('vault.detail.account')}')" title="${t('vault.copy.account')}"><svg class="svg-fill" width="15" height="15" viewBox="0 0 256 256" aria-hidden="true"><path d="M230.93,220a8,8,0,0,1-6.93,4H32a8,8,0,0,1-6.92-12c15.23-26.33,38.7-45.21,66.09-54.16a72,72,0,1,1,73.66,0c27.39,8.95,50.86,27.83,66.09,54.16A8,8,0,0,1,230.93,220Z"/></svg></button></div>
            </div>
          </div>
          <div class="detail-row">
            <div class="detail-label">${t('vault.detail.password')}</div>
            <div class="detail-value password">
              <span class="text" id="pw-${p.id}" tabindex="0" role="group" aria-label="${t('vault.detail.password')}">${state.passwordVisible[p.id]?escapeHtml(p.password):(p.password?'••••••••••••':'')}</span>
              <div class="actions">
                <button class="btn-icon" data-pdm-onclick="togglePasswordVisible(${p.id})" title="${t('vault.toggle.visible')}">${state.passwordVisible[p.id]?svgIcon('eye-closed',15):svgIcon('eye',15)}</button>
                <button class="btn-icon" data-pdm-onclick="regeneratePassword(${p.id})" title="${t('vault.regenerate')}"><svg class="svg-fill" width="15" height="15" viewBox="0 0 256 256" aria-hidden="true"><path d="M192,32H64A32,32,0,0,0,32,64V192a32,32,0,0,0,32,32H192a32,32,0,0,0,32-32V64A32,32,0,0,0,192,32ZM92,176a12,12,0,1,1,12-12A12,12,0,0,1,92,176Zm0-72a12,12,0,1,1,12-12A12,12,0,0,1,92,104Zm36,36a12,12,0,1,1,12-12A12,12,0,0,1,128,140Zm36,36a12,12,0,1,1,12-12A12,12,0,0,1,164,176Zm0-72a12,12,0,1,1,12-12A12,12,0,0,1,164,104Z"/></svg></button>
                <button class="btn-icon" data-pdm-onclick="copyText('${escapeHtml(p.password)}','${t('vault.detail.password')}')" title="${t('vault.copy.password')}"><svg class="svg-fill" width="15" height="15" viewBox="0 0 256 256" aria-hidden="true"><path d="M216.57,39.43A80,80,0,0,0,83.91,120.78L28.69,176A15.86,15.86,0,0,0,24,187.31V216a16,16,0,0,0,16,16H72a8,8,0,0,0,8-8V208H96a8,8,0,0,0,8-8V184h16a8,8,0,0,0,5.66-2.34l9.56-9.57A79.73,79.73,0,0,0,160,176h.1A80,80,0,0,0,216.57,39.43ZM180,92a16,16,0,1,1,16-16A16,16,0,0,1,180,92Z"/></svg></button>
              </div>
            </div>
          </div>
          <div class="detail-row">
            <div class="detail-label">${t('vault.detail.notes')}</div>
            <div class="detail-value notes"><span class="text">${escapeHtml(p.notes)}</span></div>
          </div>
          ${p.totp_secret ? `
          <div class="detail-row">
            <div class="detail-label">${t('vault.detail.totp')}</div>
            <div class="detail-value totp">
              <span class="text" id="totp-${p.id}">${formatTOTPCode(generateTOTP(p.totp_secret).code)}</span>
              <div class="actions">
                <div class="totp-ring" id="totp-ring-${p.id}">
                  <svg width="24" height="24" viewBox="0 0 24 24">
                    <circle class="bg" cx="12" cy="12" r="10"/>
                    <circle class="fg" cx="12" cy="12" r="10" stroke-dasharray="62.83" stroke-dashoffset="0"/>
                  </svg>
                </div>
                <button class="btn-icon" data-pdm-onclick="copyTOTP(${p.id})" title="${t('vault.copy.totp')}"><svg class="svg-fill" width="15" height="15" viewBox="0 0 256 256" aria-hidden="true"><path d="M216.57,39.43A80,80,0,0,0,83.91,120.78L28.69,176A15.86,15.86,0,0,0,24,187.31V216a16,16,0,0,0,16,16H72a8,8,0,0,0,8-8V208H96a8,8,0,0,0,8-8V184h16a8,8,0,0,0,5.66-2.34l9.56-9.57A79.73,79.73,0,0,0,160,176h.1A80,80,0,0,0,216.57,39.43ZM180,92a16,16,0,1,1,16-16A16,16,0,0,1,180,92Z"/></svg></button>
              </div>
            </div>
          </div>` : ''}
          ${demoRecoveryRows(p)}
          <div class="detail-footer">
            <span class="detail-time">${t('vault.detail.updated')} ${p.updated_at}</span>
            <div class="detail-buttons">
              <button class="btn btn-sm" data-pdm-onclick="openEditPasswordDialog(${p.id})"><svg class="svg-fill" width="16" height="16" viewBox="0 0 256 256" aria-hidden="true"><path d="M227.31,73.37,182.63,28.68a16,16,0,0,0-22.63,0L36.69,152A15.86,15.86,0,0,0,32,163.31V208a16,16,0,0,0,16,16H92.69A15.86,15.86,0,0,0,104,219.31L227.31,96a16,16,0,0,0,0-22.63ZM51.31,160l90.35-90.35,16.68,16.69L68,176.68ZM48,179.31,76.69,208H48Zm48,25.38L79.31,188l90.35-90.35h0l16.68,16.69Z"/></svg> ${t('vault.button.edit')}</button>
              <button class="btn btn-danger btn-sm" data-pdm-onclick="deleteRecord(${p.id})"><svg class="svg-fill" width="16" height="16" viewBox="0 0 256 256" aria-hidden="true"><path d="M216,48H176V40a24,24,0,0,0-24-24H104A24,24,0,0,0,80,40v8H40a8,8,0,0,0,0,16h8V208a16,16,0,0,0,16,16H192a16,16,0,0,0,16-16V64h8a8,8,0,0,0,0-16ZM112,168a8,8,0,0,1-16,0V104a8,8,0,0,1,16,0Zm48,0a8,8,0,0,1-16,0V104a8,8,0,0,1,16,0Zm0-120H96V40a8,8,0,0,1,8-8h48a8,8,0,0,1,8,8Z"/></svg> ${t('vault.button.delete')}</button>
            </div>
          </div>
        </div>
      </div>
    </div>`;
  }).join('');
}

function renderSplitView(list){
  const wrap = $('#view-split');
  if(state.viewMode!=='split'){wrap.style.display='none';return}
  wrap.style.display='grid';

  const listEl = $('#split-list');
  if(list.length===0){
    listEl.innerHTML = `<div class="empty-state"><div class="icon">${svgIcon('search',40)}</div><div>${t('vault.empty')}</div></div>`;
    $('#split-detail').innerHTML = '';
    return;
  }
  const dupMap = getDuplicateGroups();
  const similarMap = getSimilarNameGroups();
  listEl.innerHTML = list.map(p=>`
    <div class="split-item ${state.splitSelectedId===p.id?'active':''}" data-pdm-onclick="selectSplitFromItem(event,${p.id})">
      ${favStarInline(p.id,p.is_favorite)}
      <div class="platform-icon ${platformColorClass(p.platform)}">${platformIcon(p.platform)}</div>
      <div class="split-name"><span class="split-name-text">${escapeHtml(p.platform)}</span>${dupMap[p.id]?`<span class="dup-tag">${t('vault.dup.tag')}${dupMap[p.id]}</span>`:''}${similarMap[p.id]?`<span class="similar-tag">${t('vault.similar.tag')}${similarMap[p.id]}</span>`:''}</div>
      <span class="strength-dot strength-${p.strength}"></span>
      ${['pending','checking','failed'].includes(p.strength)?`<span class="split-strength-status">${t('common.strength.'+p.strength)}</span>${demoStrengthRetry(p)}`:''}
    </div>
  `).join('');

  renderSplitDetail();
}

/* 分屏中使用的内联收藏星标（小尺寸） */
function favStarInline(id,isFavorite){
  return `<span class="fav-star ${isFavorite?'active':''} pdm-inline-d14923fa97" data-pdm-onclick="event.stopPropagation();toggleFavorite(${id},this)">${isFavorite?svgIcon('star',14):'<svg class="svg-fill fav-star-empty" width="14" height="14" viewBox="0 0 256 256" aria-hidden="true"><path d="' + SVG_ICONS_FILL.star + '"/></svg>'}</span>`;
}

function renderSplitDetail(){
  const p = passwords.find(x=>x.id===state.splitSelectedId);
  const d = $('#split-detail');
  if(!p){
    d.innerHTML = `<div class="split-detail-empty"><div class="icon">${svgIcon('arrow-left',40)}</div><div>${t('vault.split.empty')}</div></div>`;
    return;
  }
  d.innerHTML = `
    <div class="detail-header">
      <div class="platform-icon pdm-platform-icon-large ${platformColorClass(p.platform)}">${platformIcon(p.platform)}</div>
      <div class="pdm-inline-83725d2c6e">
        <h2><span class="platform-name-text">${escapeHtml(p.platform)}</span></h2>
        <div class="sub">${t('vault.detail.updated')} ${p.updated_at} · ${t('vault.strength.label')}: ${t('common.strength.'+p.strength)}</div>
      </div>
      ${favStarHTML(p.id,p.is_favorite)}
    </div>
    <div class="pdm-inline-022625b12b">
      <div class="detail-row pdm-inline-ab79ea2b85">
        <div class="detail-label">${t('vault.detail.account')}</div>
        <div class="detail-value account pdm-inline-83725d2c6e"><span class="text" tabindex="0" role="group" aria-label="${t('vault.detail.account')}">${escapeHtml(p.account)}</span><div class="actions"><button class="btn-icon" data-pdm-onclick="copyText('${escapeHtml(p.account)}','${t('vault.detail.account')}')" title="${t('vault.copy.account')}"><svg class="svg-fill" width="15" height="15" viewBox="0 0 256 256" aria-hidden="true"><path d="M230.93,220a8,8,0,0,1-6.93,4H32a8,8,0,0,1-6.92-12c15.23-26.33,38.7-45.21,66.09-54.16a72,72,0,1,1,73.66,0c27.39,8.95,50.86,27.83,66.09,54.16A8,8,0,0,1,230.93,220Z"/></svg></button></div></div>
      </div>
      <div class="detail-row pdm-inline-ab79ea2b85">
        <div class="detail-label">${t('vault.detail.password')}</div>
        <div class="detail-value password pdm-inline-83725d2c6e">
          <span class="text" id="split-pw" tabindex="0" role="group" aria-label="${t('vault.detail.password')}">${state.passwordVisible[p.id]?escapeHtml(p.password):(p.password?'••••••••••••':'')}</span>
          <div class="actions">
            <button class="btn-icon" data-pdm-onclick="togglePasswordVisible(${p.id})" title="${t('vault.toggle.visible')}">${state.passwordVisible[p.id]?svgIcon('eye-closed',15):svgIcon('eye',15)}</button>
            <button class="btn-icon" data-pdm-onclick="regeneratePassword(${p.id})" title="${t('vault.regenerate')}"><svg class="svg-fill" width="15" height="15" viewBox="0 0 256 256" aria-hidden="true"><path d="M192,32H64A32,32,0,0,0,32,64V192a32,32,0,0,0,32,32H192a32,32,0,0,0,32-32V64A32,32,0,0,0,192,32ZM92,176a12,12,0,1,1,12-12A12,12,0,0,1,92,176Zm0-72a12,12,0,1,1,12-12A12,12,0,0,1,92,104Zm36,36a12,12,0,1,1,12-12A12,12,0,0,1,128,140Zm36,36a12,12,0,1,1,12-12A12,12,0,0,1,164,176Zm0-72a12,12,0,1,1,12-12A12,12,0,0,1,164,104Z"/></svg></button>
            <button class="btn-icon" data-pdm-onclick="copyText('${escapeHtml(p.password)}','${t('vault.detail.password')}')" title="${t('vault.copy.password')}"><svg class="svg-fill" width="15" height="15" viewBox="0 0 256 256" aria-hidden="true"><path d="M216.57,39.43A80,80,0,0,0,83.91,120.78L28.69,176A15.86,15.86,0,0,0,24,187.31V216a16,16,0,0,0,16,16H72a8,8,0,0,0,8-8V208H96a8,8,0,0,0,8-8V184h16a8,8,0,0,0,5.66-2.34l9.56-9.57A79.73,79.73,0,0,0,160,176h.1A80,80,0,0,0,216.57,39.43ZM180,92a16,16,0,1,1,16-16A16,16,0,0,1,180,92Z"/></svg></button>
          </div>
        </div>
      </div>
      <div class="detail-row pdm-inline-ab79ea2b85">
        <div class="detail-label">${t('vault.detail.notes')}</div>
        <div class="detail-value notes pdm-inline-83725d2c6e"><span class="text">${escapeHtml(p.notes)}</span></div>
      </div>
      ${p.totp_secret ? `
      <div class="detail-row pdm-inline-ab79ea2b85">
        <div class="detail-label">${t('vault.detail.totp')}</div>
        <div class="detail-value totp pdm-inline-83725d2c6e">
          <span class="text" id="split-totp-${p.id}">${formatTOTPCode(generateTOTP(p.totp_secret).code)}</span>
          <div class="actions">
            <div class="totp-ring" id="split-totp-ring-${p.id}">
              <svg width="24" height="24" viewBox="0 0 24 24">
                <circle class="bg" cx="12" cy="12" r="10"/>
                <circle class="fg" cx="12" cy="12" r="10" stroke-dasharray="62.83" stroke-dashoffset="0"/>
              </svg>
            </div>
            <button class="btn-icon" data-pdm-onclick="copyTOTP(${p.id})" title="${t('vault.copy.totp')}"><svg class="svg-fill" width="15" height="15" viewBox="0 0 256 256" aria-hidden="true"><path d="M216.57,39.43A80,80,0,0,0,83.91,120.78L28.69,176A15.86,15.86,0,0,0,24,187.31V216a16,16,0,0,0,16,16H72a8,8,0,0,0,8-8V208H96a8,8,0,0,0,8-8V184h16a8,8,0,0,0,5.66-2.34l9.56-9.57A79.73,79.73,0,0,0,160,176h.1A80,80,0,0,0,216.57,39.43ZM180,92a16,16,0,1,1,16-16A16,16,0,0,1,180,92Z"/></svg></button>
          </div>
        </div>
      </div>` : ''}
      ${demoRecoveryRows(p)}
      <div class="pdm-inline-92f0e40814">
        <button class="btn btn-sm" data-pdm-onclick="openEditPasswordDialog(${p.id})"><svg class="svg-fill" width="16" height="16" viewBox="0 0 256 256" aria-hidden="true"><path d="M227.31,73.37,182.63,28.68a16,16,0,0,0-22.63,0L36.69,152A15.86,15.86,0,0,0,32,163.31V208a16,16,0,0,0,16,16H92.69A15.86,15.86,0,0,0,104,219.31L227.31,96a16,16,0,0,0,0-22.63ZM51.31,160l90.35-90.35,16.68,16.69L68,176.68ZM48,179.31,76.69,208H48Zm48,25.38L79.31,188l90.35-90.35h0l16.68,16.69Z"/></svg> ${t('vault.button.edit')}</button>
        <button class="btn btn-danger btn-sm" data-pdm-onclick="deleteRecord(${p.id})"><svg class="svg-fill" width="16" height="16" viewBox="0 0 256 256" aria-hidden="true"><path d="M216,48H176V40a24,24,0,0,0-24-24H104A24,24,0,0,0,80,40v8H40a8,8,0,0,0,0,16h8V208a16,16,0,0,0,16,16H192a16,16,0,0,0,16-16V64h8a8,8,0,0,0,0-16ZM112,168a8,8,0,0,1-16,0V104a8,8,0,0,1,16,0Zm48,0a8,8,0,0,1-16,0V104a8,8,0,0,1,16,0Zm0-120H96V40a8,8,0,0,1,8-8h48a8,8,0,0,1,8,8Z"/></svg> ${t('vault.button.delete')}</button>
      </div>
    </div>
  `;
}

/* ============================================================
   密码库交互
   ============================================================ */
function switchView(mode){
  state.passwordVisible = {};
  clearDemoRecovery();
  state.viewMode = mode;
  $$('.view-switcher .btn-icon').forEach(b=>b.classList.toggle('active',b.dataset.view===mode));
  renderVault();
}

function toggleAccordionFromSummary(event,id){
  if(event?.target?.closest?.('.platform-name-text')) return;
  toggleAccordion(id);
}

function toggleAccordion(id){
  state.passwordVisible = {};
  clearDemoRecovery();
  state.expandedId = state.expandedId===id?null:id;
  renderVault();
}

function selectSplit(id){
  if(state.splitSelectedId !== id){state.passwordVisible = {};clearDemoRecovery();}
  state.splitSelectedId = id;
  renderVault();
}

function selectSplitFromItem(event,id){
  if(event?.target?.closest?.('.split-name-text')) return;
  selectSplit(id);
}

function setFilter(f){
  state.filter = f;
  renderVault();
}

/* —— 自定义排序下拉组件（替代原生 <select>，完整控制弹出列表样式）—— */
function toggleSortDropdown(e,dropdownId='sort-dropdown'){
  if(e) e.stopPropagation();
  const dd = $('#'+dropdownId);
  if(!dd) return;
  if(dd.classList.contains('open')) closeSortDropdown(dropdownId);
  else openSortDropdown(dropdownId);
}
function openSortDropdown(dropdownId='sort-dropdown'){
  const dd=$('#'+dropdownId),trigger=dd?.querySelector('.sort-trigger');
  if(!dd||!trigger) return false;
  dd.classList.add('open');
  trigger.setAttribute('aria-expanded','true');
  syncSortDropdownAccessibility(dropdownId);
  const selected=[...dd.querySelectorAll('.sort-option')].find(
    option=>option.getAttribute('aria-selected')==='true')||dd.querySelector('.sort-option');
  if(!selected) return false;
  selected.tabIndex=0;
  selected.focus({preventScroll:true});
  return document.activeElement===selected;
}
function syncSortDropdownAccessibility(dropdownId){
  const dd=$('#'+dropdownId),trigger=dd?.querySelector('.sort-trigger');
  const options=[...(dd?.querySelectorAll('.sort-option')||[])];
  if(!trigger||!options.length) return;
  const selected=options.find(option=>option.classList.contains('active'))||options[0];
  options.forEach(option=>{
    option.tabIndex=-1;
    option.setAttribute('aria-selected',String(option===selected));
  });
  const name=t(dropdownId==='note-sort-dropdown'?'notes.sort.label':'vault.sort.label');
  const value=selected.querySelector('span')?.textContent.trim()||'';
  trigger.setAttribute('aria-label',t('common.current').replace('{name}',name).replace('{value}',value));
}
function projectSortDropdown(dropdownId,value){
  const dd = $('#'+dropdownId), menu = dd?.querySelector('.sort-menu');
  if(!menu) return;
  const activeOpt = [...menu.querySelectorAll('.sort-option')].find(option=>
    (option.dataset.value||option.dataset.pdmNoteSort||'').toUpperCase()===value.toUpperCase());
  menu.querySelectorAll('.sort-option').forEach(option=>{
    option.classList.toggle('active',option===activeOpt);
    option.setAttribute('aria-selected',String(option===activeOpt));
  });
  const textEl = activeOpt?.querySelector('span'), label = dd.querySelector('.sort-trigger span');
  if(textEl && label){
    label.textContent = textEl.textContent;
    label.setAttribute('data-i18n', textEl.getAttribute('data-i18n'));
  }
  syncSortDropdownAccessibility(dropdownId);
}
function selectSort(value,e){
  if(e) e.stopPropagation();
  state.sortMode = value;
  projectSortDropdown('sort-dropdown',value);
  closeSortDropdown('sort-dropdown',true);
  renderVault();
}
function closeSortDropdown(dropdownId='sort-dropdown',restoreTrigger=false){
  const dd = $('#'+dropdownId);
  if(dd) dd.classList.remove('open');
  const trig = dd?.querySelector('.sort-trigger');
  if(trig) trig.setAttribute('aria-expanded','false');
  dd?.querySelectorAll('.sort-option').forEach(option=>{option.tabIndex=-1});
  if(restoreTrigger&&trig) trig.focus({preventScroll:true});
}
function bindSortDropdownKeyboard(dropdownId,commit,canUse=()=>true){
  const dd=$('#'+dropdownId),trigger=dd?.querySelector('.sort-trigger');
  if(!dd||!trigger||dd.dataset.pdmKeyboardBound==='true') return;
  dd.dataset.pdmKeyboardBound='true';
  const options=()=>[...dd.querySelectorAll('.sort-option')];
  const composing=event=>event.isComposing||event.keyCode===229;
  const open=()=>{
    if(!canUse()) return false;
    return openSortDropdown(dropdownId);
  };
  const closeToTrigger=()=>{
    closeSortDropdown(dropdownId,true);
  };
  trigger.addEventListener('keydown',event=>{
    if(composing(event)||(event.key!=='Enter'&&event.key!==' ')) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    open();
  });
  dd.addEventListener('keydown',event=>{
    const option=event.target.closest?.('.sort-option');
    if(!option||composing(event)) return;
    const items=options(),index=items.indexOf(option);
    if(event.key==='ArrowDown'||event.key==='ArrowUp'){
      event.preventDefault();
      event.stopImmediatePropagation();
      option.tabIndex=-1;
      const next=items[(index+(event.key==='ArrowDown'?1:-1)+items.length)%items.length];
      next.tabIndex=0;
      next.focus({preventScroll:true});
    }else if(event.key==='Enter'||event.key===' '){
      event.preventDefault();
      event.stopImmediatePropagation();
      const value=option.dataset.value||option.dataset.pdmNoteSort||'';
      closeToTrigger();
      commit(value,event);
    }else if(event.key==='Escape'){
      event.preventDefault();
      event.stopImmediatePropagation();
      closeToTrigger();
    }
  });
  dd.addEventListener('focusout',event=>{
    if(!dd.contains(event.relatedTarget)) closeSortDropdown(dropdownId);
  });
}
function closeAllSortDropdowns(){
  $$('.sort-dropdown.open').forEach(dd=>closeSortDropdown(
    dd.id,
    dd.contains(document.activeElement),
  ));
}
/* 点击外部 / Esc 关闭下拉 */
function selectDemoNoteSort(value){
  if(!canLeaveNotesCardEdit()) return;
  state.noteSort=value.toUpperCase();
  projectSortDropdown('note-sort-dropdown',state.noteSort);
  closeSortDropdown('note-sort-dropdown',true);
  renderNotes();
}
document.addEventListener('click', e=>{
  if(!e.target.closest('.sort-dropdown')) closeAllSortDropdowns();
});
document.addEventListener('keydown', e=>{
  if(e.key==='Escape') closeAllSortDropdowns();
});
document.addEventListener('click', e=>{
  if(PDM_IS_M4_ISOLATED) return;
  const trigger = e.target.closest('#note-sort-trigger');
  if(trigger){
    if(!canLeaveNotesCardEdit()) return;
    toggleSortDropdown(e,'note-sort-dropdown');
    return;
  }
  const option = e.target.closest('#note-sort-menu [data-pdm-note-sort]');
  if(!option) return;
  e.stopPropagation();
  selectDemoNoteSort(option.dataset.pdmNoteSort);
});
if(!PDM_IS_M4_ISOLATED){
  bindSortDropdownKeyboard('sort-dropdown',value=>selectSort(value));
  bindSortDropdownKeyboard('note-sort-dropdown',selectDemoNoteSort,canLeaveNotesCardEdit);
}

function toggleFavorite(id,el){
  const p = passwords.find(x=>x.id===id);
  p.is_favorite = !p.is_favorite;
  if(el){el.classList.add('popping');setTimeout(()=>el.classList.remove('popping'),400)}
  setTimeout(()=>{
    renderVault();
    showToast(p.is_favorite?t('toast.fav.added'):t('toast.fav.removed'),'success');
  },50);
}

/* 对话框内收藏开关切换：仅翻转 .active 类，提交时由 saveNew/saveEdit 读取状态。
   与列表 .fav-star 共用 popping 动画 + 琥珀色高亮视觉语言。 */
function toggleModalFav(btn){
  btn.classList.add('popping');
  setTimeout(()=>btn.classList.remove('popping'),400);
  btn.classList.toggle('active');
  btn.setAttribute('aria-pressed',String(btn.classList.contains('active')));
}

/* 收藏星标 HTML（统一生成，确保所有视图一致） */
function favStarHTML(id,isFavorite){
  return `<div class="fav-star ${isFavorite?'active':''}" data-pdm-onclick="event.stopPropagation();toggleFavorite(${id},this)">${isFavorite?svgIcon('star',16):'<svg class="svg-fill fav-star-empty" width="16" height="16" viewBox="0 0 256 256" aria-hidden="true"><path d="' + SVG_ICONS_FILL.star + '"/></svg>'}</div>`;
}

function togglePasswordVisible(id){
  const show = !state.passwordVisible[id];
  state.passwordVisible = {};
  if(show) state.passwordVisible[id] = true;
  renderVault();
}

function copyText(text,label){
  if(text === '') return;
  // 实际环境用 navigator.clipboard，这里做模拟
  try{navigator.clipboard && navigator.clipboard.writeText(text)}catch(e){}
  startClipboardCountdown();
  showToast(label + t('toast.copied.suffix'),'success');
}

/* ---------- TOTP 验证码复制 + 倒计时刷新 ---------- */
function copyTOTP(id){
  const p = passwords.find(x=>x.id===id);
  if(!p || !p.totp_secret) return;
  const totp = generateTOTP(p.totp_secret);
  if(!totp) return;
  copyText(totp.code, t('vault.detail.totp'));
}

/* 每秒刷新所有可见 TOTP 显示：6 位码 + 30s 圆环倒计时
   - 圆周长 2πr = 2π*10 ≈ 62.83
   - stroke-dashoffset = CIRC * (1 - remaining/30)
   - remaining ≤ 5s 时圆环变红色（urgent 类） */
const TOTP_RING_CIRC = 62.83;
function updateTOTPDisplay(){
  document.querySelectorAll('[id^="totp-ring-"], [id^="split-totp-ring-"]').forEach(ring=>{
    const m = ring.id.match(/(?:split-)?totp-ring-(\d+)/);
    if(!m) return;
    const id = parseInt(m[1]);
    const p = passwords.find(x=>x.id===id);
    if(!p || !p.totp_secret) return;
    const totp = generateTOTP(p.totp_secret);
    if(!totp) return;
    // 更新验证码文本（同 id 下找 totp-{id} 或 split-totp-{id}）
    const prefix = ring.id.startsWith('split-') ? 'split-totp-' : 'totp-';
    const codeEl = $('#'+prefix+id);
    if(codeEl) codeEl.textContent = formatTOTPCode(totp.code);
    // 更新圆环
    const fg = ring.querySelector('.fg');
    if(fg){
      fg.style.strokeDashoffset = TOTP_RING_CIRC * (1 - totp.remaining/30);
      ring.classList.toggle('urgent', totp.remaining <= 5);
    }
  });
}
if(!PDM_IS_M4_ISOLATED){
  setInterval(updateTOTPDisplay, 1000);
}

function editRecord(id){
  openEditPasswordDialog(id);
}

function deleteRecord(id){
  openPasswordDeleteConfirm(id);
}

function openPasswordDeleteConfirm(id){
  const p = passwords.find(x=>x.id===id);
  if(!p){showToast(t('toast.notFound'),'error');return}
  openModal(`
    <div class="modal-header">
      <div class="modal-title">${t('dialog.delete.title')}</div>
      <button class="modal-close" data-pdm-onclick="closeModal()">✕</button>
    </div>
    <div class="modal-body">
      <div class="delete-confirm-icon">${svgIcon('warning',32)}</div>
      <div class="delete-confirm-text">${t('dialog.delete.confirm').replace('{platform}',escapeHtml(p.platform))}</div>
      <div class="delete-confirm-desc">${t('dialog.delete.desc')}</div>
    </div>
    <div class="modal-footer">
      <div class="modal-footer-right">
        <button class="btn btn-sm delete-cancel" data-pdm-onclick="closeModal()">${t('dialog.button.cancel')}</button>
        <button class="btn btn-danger btn-sm" data-pdm-onclick="confirmDeleteRecord(${id})">${t('dialog.button.delete')}</button>
      </div>
    </div>
  `,{closeOnBackdrop:false,initialFocusSelector:'.delete-cancel'});
}

function confirmDeleteRecord(id){
  const p = passwords.find(x=>x.id===id);
  if(!p){closeModal();return}
  const idx = passwords.findIndex(x=>x.id===id);
  passwords.splice(idx,1);
  state.expandedId = null;
  closeModal();
  renderVault();
  renderSecurity();
  showToast(t('toast.deleted.prefix') + p.platform,'success');
}

/* ============================================================
   剪贴板倒计时
   ============================================================ */
let clipboardRestoreTimer = null;

function startClipboardCountdown(){
  if(state.clipboardTimer) clearInterval(state.clipboardTimer);
  /* 清除可能存在的恢复定时器，避免倒计时中被恢复成就绪态 */
  if(clipboardRestoreTimer){clearTimeout(clipboardRestoreTimer);clipboardRestoreTimer=null}
  state.clipboardSeconds = 30;
  updateClipboardStatus();
  state.clipboardTimer = setInterval(()=>{
    state.clipboardSeconds--;
    if(state.clipboardSeconds<=0){
      clearInterval(state.clipboardTimer);
      state.clipboardTimer = null;
      $('#clipboard-status').innerHTML = `<span data-i18n="status.clipboard.cleared">${t('status.clipboard.cleared')}</span>`;
      /* 清空提示 2 秒后恢复就绪态 */
      clipboardRestoreTimer = setTimeout(restoreClipboardStatus, 2000);
    }else{
      updateClipboardStatus();
    }
  },1000);
}

function updateClipboardStatus(){
  const s = state.clipboardSeconds;
  const danger = s<=5?'danger':'';
  $('#clipboard-status').innerHTML = `
    <span class="clipboard-countdown ${danger}">${t('status.clipboard.countdown').replace('{n}',s)}</span>
    <span class="clear-clip-btn" data-pdm-onclick="clearClipboard()">${t('status.clipboard.clearNow')}</span>
  `;
}

function clearClipboard(){
  if(state.clipboardTimer){clearInterval(state.clipboardTimer);state.clipboardTimer=null}
  if(clipboardRestoreTimer){clearTimeout(clipboardRestoreTimer);clipboardRestoreTimer=null}
  state.clipboardSeconds = 0;
  try{navigator.clipboard && navigator.clipboard.writeText('')}catch(e){}
  $('#clipboard-status').innerHTML = `<span data-i18n="status.clipboard.cleared">${t('status.clipboard.cleared')}</span>`;
  showToast(t('status.clipboard.cleared'),'info');
  /* 清空提示 2 秒后恢复就绪态 */
  clipboardRestoreTimer = setTimeout(restoreClipboardStatus, 2000);
}

/* 清空提示 2 秒后恢复"剪贴板: 就绪"就绪态 */
function restoreClipboardStatus(){
  clipboardRestoreTimer = null;
  $('#clipboard-status').innerHTML = `<span data-i18n="status.clipboard.ready">${t('status.clipboard.ready')}</span>`;
}

/* ============================================================
   记事本
   ============================================================ */
function setNoteFilter(f){
  if(!canLeaveNotesCardEdit()) return;
  state.noteFilter = f;
  $$('#page-notes .chip').forEach(c=>c.classList.toggle('active',c.dataset.nfilter===f));
  renderNotes();
}

function filterNotes(){
  let list = [...notes];
  if(state.noteFilter==='favorite') list = list.filter(n=>n.is_favorite);
  if(state.noteSort==='NAME') list.sort((a,b)=>{
    const key = title => typeof pinyinPro==='undefined' ? title.toLowerCase() :
      pinyinPro.pinyin(title,{toneType:'none',type:'array'}).join('').toLowerCase().replaceAll('ü','v');
    const left=key(a.title),right=key(b.title);
    return (left<right?-1:left>right?1:0)||a.id-b.id;
  });
  else list.sort((a,b)=>b.updated_at.localeCompare(a.updated_at)||b.id-a.id);
  if(state.search) list = list.filter(n=>settingsFieldMatches(n.title,state.search)||n.content.toLowerCase().includes(state.search));
  return list;
}

function updateLongTextHint(textarea,hintId){
  const hint = typeof hintId==='string' ? $('#'+hintId) : hintId;
  if(!textarea || !hint) return;
  const maximum = Math.max(0,textarea.scrollHeight-textarea.clientHeight);
  if(maximum<=1){
    hint.classList.remove('visible');
    return;
  }
  const percent = Math.round(Math.min(maximum,textarea.scrollTop)*100/maximum);
  const lines = Math.max(1,textarea.value.split('\n').length);
  const message = hint.querySelector('.text-scroll-message');
  const position = hint.querySelector('.text-scroll-position');
  if(message) message.textContent = textarea.scrollTop>=maximum-1?t('notes.scroll.bottom'):t('notes.scroll.more');
  if(position) position.textContent = t('notes.scroll.position').replace('{0}',percent).replace('{1}',lines);
  hint.classList.add('visible');
}

function isNotesCardsDemo(){
  return document.documentElement.dataset.pdmNotesCards === 'true';
}

function syncNotesCardsSearchPlaceholder(nav){
  const search = $('#global-search');
  if(!search) return;
  const key = nav === 'settings' ? 'settings.search.placeholder'
    : nav === 'notes' ? 'notes.cards.search.placeholder' : 'topbar.search.placeholder';
  search.dataset.i18nPlaceholder = key;
  search.dataset.i18nAriaLabel = key;
  search.placeholder = t(key);
  search.setAttribute('aria-label',t(key));
}

function notesCardsColumnCount(){
  const width = $('#notes-list')?.clientWidth || 0;
  if(width >= 960) return 3;
  return width >= 620 ? 2 : 1;
}

/* 保持原始 DOM 顺序，视觉上再按横向轮次放入列；因此 Tab 顺序与视觉顺序一致。 */
function layoutNotesCards(wrap){
  const grid = wrap?.querySelector('.notes-cards');
  if(!grid) return;
  const columns = notesCardsColumnCount();
  const cards = Array.from(grid.querySelectorAll(':scope > .note-card'));
  if(!cards.length || !grid.clientWidth) return;
  const gap = 16;
  const width = (grid.clientWidth-gap*(columns-1))/columns;
  const heights = Array(columns).fill(0);
  // 先批量写宽度，再集中测量；避免每张卡写样式后立即读取高度而反复强制布局。
  cards.forEach(card=>{card.style.width=`${width}px`;});
  const overflow = cards.map(card=>{
    const text=card.querySelector('.note-card-preview, .note-card-body');
    if(!text) return false;
    const limit=text.classList.contains('note-card-preview') ? text.clientHeight :
      parseFloat(getComputedStyle(text).lineHeight)*8;
    return text.scrollHeight>limit+1 || card.dataset.previewTruncated==='true';
  });
  cards.forEach((card,index)=>{
    const toggle=card.querySelector('.note-card-actions [data-note-card-action="read"], .note-card-actions [data-note-card-action="back"]');
    if(toggle) toggle.hidden=!overflow[index];
  });
  const sizes=cards.map(card=>card.offsetHeight);
  cards.forEach((card,index)=>{
    card.style.left = `${(index%columns)*(width+gap)}px`;
    card.style.top = `${heights[index%columns]}px`;
    heights[index%columns] += sizes[index]+gap;
  });
  grid.style.height = `${Math.max(...heights)-gap}px`;
  grid.dataset.columns = String(columns);
}
window.pdmLayoutNotesCards = layoutNotesCards;

function formatNotesCardDate(value){
  return /^\d{4}-\d{2}-\d{2}$/.test(value) ? value.slice(5) : value;
}

function hasUnsavedNotesCardDraft(){
  const id = state.notesCardEditId;
  const n = notes.find(value=>value.id===id);
  const draft = noteCardDraft(id) || state.notesCardDraft;
  return Boolean(n && draft && (draft.title !== n.title || draft.content !== n.content));
}

function canLeaveNotesCardEdit(){
  if(!isNotesCardsDemo() || !hasUnsavedNotesCardDraft()) return true;
  showToast(t('notes.cards.unsaved'),'warning');
  return false;
}

function notesCardMarkup(n){
  const draft = state.notesCardDraft;
  const open = state.notesCardOpenId === n.id;
  const editing = state.notesCardEditId === n.id;
  const value = draft?.id === n.id ? draft : n;
  const dirty = value.title !== n.title || value.content !== n.content;
  const pencil = svgIcon('pencil',16);
  const star = n.is_favorite ? svgIcon('star',18) : `<svg class="svg-fill fav-star-empty" width="18" height="18" viewBox="0 0 256 256" aria-hidden="true"><path d="${SVG_ICONS_FILL.star}"/></svg>`;
  let content = `
    <div class="note-card-preview">${escapeHtml(n.content)}</div>
    <div class="note-card-actions">
      <button type="button" class="btn-link" data-note-card-action="read" data-note-card-id="${n.id}">${t('notes.cards.read')}</button>
    </div>`;
  if(open && !editing){
    content = `
      <div class="note-card-body" tabindex="0" aria-label="${escapeHtml(n.title)} ${t('dialog.note.label.content')}">${escapeHtml(n.content)}</div>
      <div class="note-card-actions">
        <button type="button" class="btn-link" data-note-card-action="back" data-note-card-id="${n.id}" hidden>${t('notes.cards.back')}</button>
      </div>`;
  }else if(editing){
    content = `
      <div class="note-card-editor">
        <input class="input" id="note-title-${n.id}" value="${escapeHtml(value.title)}" placeholder="${t('notes.input.title')}" aria-label="${t('notes.input.title')}" data-note-card-input="title" data-note-card-id="${n.id}">
        <textarea id="note-content-${n.id}" placeholder="${t('notes.input.content')}" aria-label="${t('notes.input.content')}" data-note-card-input="content" data-note-card-id="${n.id}">${escapeHtml(value.content)}</textarea>
        <div class="note-form-feedback" id="note-card-feedback-${n.id}"></div>
      </div>
      <div class="note-card-actions">
        <button type="button" class="btn btn-danger btn-sm" data-note-card-action="delete" data-note-card-id="${n.id}">${t('notes.button.delete')}</button>
        <span class="note-card-actions-spacer"></span>
        <button type="button" class="btn btn-sm" data-note-card-action="cancel" data-note-card-id="${n.id}">${t('dialog.button.cancel')}</button>
        <button type="button" class="btn btn-primary btn-sm" id="note-save-${n.id}" data-note-card-action="save" data-note-card-id="${n.id}" ${dirty?'':'disabled'}>${t('notes.button.save')}</button>
      </div>`;
  }
  return `
    <article class="note-card ${open?'is-open':''} ${editing?'is-editing':''}" data-id="${n.id}">
      <div class="note-card-heading">
        <h2 class="note-card-title">${escapeHtml(n.title)}</h2>
        <button type="button" class="note-card-favorite ${n.is_favorite?'active':''}" data-note-card-action="favorite" data-note-card-id="${n.id}" aria-pressed="${n.is_favorite}" aria-label="${t('dialog.label.favorite')}">${star}</button>
      </div>
      ${content}
      <footer class="note-card-footer"><span>${t('notes.cards.updated')} ${formatNotesCardDate(n.updated_at)}</span>${editing?'':`<button type="button" class="note-card-edit" data-note-card-action="edit" data-note-card-id="${n.id}">${pencil} ${t('vault.button.edit')}</button>`}</footer>
    </article>`;
}

function renderNotesCards(wrap,list){
  const columnCount = notesCardsColumnCount();
  state.notesCardsColumns = columnCount;
  if(list.length===0){
    wrap.innerHTML = `<div class="empty-state"><div class="icon">${svgIcon('notebook',48)}</div><div>${t('notes.empty')}</div></div>`;
    return;
  }
  wrap.innerHTML = `<div class="notes-cards notes-cards-${columnCount}" aria-label="记事卡片">${list.map(notesCardMarkup).join('')}</div>`;
  bindNotesCardsActions(wrap);
  layoutNotesCards(wrap);
  requestAnimationFrame(()=>layoutNotesCards(wrap));
}

function noteCardDraft(id){
  const title = $(`#note-title-${id}`);
  const content = $(`#note-content-${id}`);
  if(!title || !content) return null;
  return {id,title:title.value,content:content.value};
}

function updateNotesCardDraft(id){
  const n = notes.find(value=>value.id===id);
  const draft = noteCardDraft(id);
  if(!n || !draft) return;
  state.notesCardDraft = draft;
  const feedback = $(`#note-card-feedback-${id}`);
  if(feedback) feedback.textContent = '';
  const save = $(`#note-save-${id}`);
  if(save) save.disabled = draft.title === n.title && draft.content === n.content;
}

function saveNotesCard(id){
  const n = notes.find(value=>value.id===id);
  const draft = noteCardDraft(id) || state.notesCardDraft;
  if(!n || !draft) return;
  if(!draft.title.trim()){
    const feedback = $(`#note-card-feedback-${id}`);
    if(feedback) feedback.textContent = t('dialog.note.error.titleEmpty');
    $(`#note-title-${id}`)?.focus();
    return;
  }
  n.title = draft.title.trim();
  n.content = draft.content;
  n.updated_at = new Date().toISOString().slice(0,10);
  state.notesCardDraft = null;
  state.notesCardEditId = null;
  state.notesCardOpenId = id;
  state.notesCardEditReturnToOverview = false;
  // 只更新本卡内容，保持原节点和当前排序位置。
  const item = document.querySelector(`.note-card[data-id="${id}"]`);
  if(item){
    const template = document.createElement('template');
    template.innerHTML = notesCardMarkup(n);
    const updated = template.content.firstElementChild;
    item.className = updated.className;
    item.innerHTML = updated.innerHTML;
    bindNotesCardsActions(item);
    layoutNotesCards($('#notes-list'));
  }
  showToast(t('toast.note.saved'),'success');
}

function bindNotesCardsActions(wrap){
  wrap.querySelectorAll('[data-note-card-input]').forEach(input=>{
    input.addEventListener('input',()=>updateNotesCardDraft(Number(input.dataset.noteCardId)));
  });
  wrap.querySelectorAll('button[data-note-card-action]').forEach(button=>{
    button.addEventListener('click',()=>{
      const id = Number(button.dataset.noteCardId);
      const n = notes.find(value=>value.id===id);
      if(!n) return;
      if(state.notesCardEditId && state.notesCardEditId!==id && !canLeaveNotesCardEdit()) return;
      switch(button.dataset.noteCardAction){
        case 'read': state.notesCardOpenId=id; state.notesCardEditId=null; state.notesCardDraft=null; renderNotes(); break;
        case 'edit': state.notesCardEditReturnToOverview=state.notesCardOpenId!==id; state.notesCardOpenId=id; state.notesCardEditId=id; state.notesCardDraft=null; renderNotes(); break;
        case 'back': state.notesCardOpenId=null; state.notesCardEditId=null; state.notesCardDraft=null; renderNotes(); break;
        case 'cancel': if(state.notesCardEditReturnToOverview) state.notesCardOpenId=null; state.notesCardEditId=null; state.notesCardDraft=null; renderNotes(); break;
        case 'favorite': n.is_favorite=!n.is_favorite; renderNotes(); break;
        case 'save': saveNotesCard(id); break;
        case 'delete': deleteNote(id); break;
      }
    });
  });
}

function renderNotes(){
  projectSortDropdown('note-sort-dropdown',state.noteSort);
  $('#note-sort-trigger')?.setAttribute('aria-label',t('notes.sort.label'));
  // 未连接空状态：记事本需要数据库（加密记事存于 .db）
  if(!state.connected){
    const allEl = $('#ncount-all'); if(allEl) allEl.textContent = '0';
    const favEl = $('#ncount-fav'); if(favEl) favEl.textContent = '0';
    const wrap = $('#notes-list');
    if(wrap) wrap.innerHTML = `<div class="empty-state"><div class="icon">${svgIcon('lock',40)}</div><div>${t('startup.empty.notes')}</div></div>`;
    if(state.currentNav==='notes') syncGlobalSearchStatus(0,'');
    return;
  }
  const list = filterNotes();
  if(state.currentNav==='notes') syncGlobalSearchStatus(list.length);
  // 更新计数
  const allEl = $('#ncount-all'); if(allEl) allEl.textContent = notes.length;
  const favEl = $('#ncount-fav'); if(favEl) favEl.textContent = notes.filter(n=>n.is_favorite).length;
  const wrap = $('#notes-list');
  if(isNotesCardsDemo()){
    renderNotesCards(wrap,list);
    return;
  }
  if(list.length===0){
    wrap.innerHTML = `<div class="empty-state"><div class="icon">${svgIcon('notebook',48)}</div><div>${t('notes.empty')}</div></div>`;
    return;
  }
  wrap.innerHTML = list.map(n=>`
    <div class="note-item ${state.expandedId===n.id+1000?'expanded':''}" data-id="${n.id}">
      <div class="note-summary" data-pdm-onclick="toggleNote(${n.id})">
        <div class="fav-star ${n.is_favorite?'active':''}" data-pdm-onclick="event.stopPropagation();toggleNoteFavorite(${n.id},this)">${n.is_favorite?svgIcon('star',16):'<svg class="svg-fill fav-star-empty" width="16" height="16" viewBox="0 0 256 256" aria-hidden="true"><path d="' + SVG_ICONS_FILL.star + '"/></svg>'}</div>
        <div class="note-icon"><svg class="svg-fill" width="16" height="16" viewBox="0 0 256 256" aria-hidden="true"><path d="M208,32H48A16,16,0,0,0,32,48V208a16,16,0,0,0,16,16H208a16,16,0,0,0,16-16V48A16,16,0,0,0,208,32ZM80,208H48V48H80Zm96-56H112a8,8,0,0,1,0-16h64a8,8,0,0,1,0,16Zm0-32H112a8,8,0,0,1,0-16h64a8,8,0,0,1,0,16Z"/></svg></div>
        <div class="note-info">
          <div class="note-title">${escapeHtml(n.title)}</div>
          <div class="note-preview">${escapeHtml(n.content.slice(0,40))}</div>
        </div>
        <div class="note-time">${n.updated_at}</div>
        <span class="chevron">▼</span>
      </div>
      <div class="note-detail">
        <div class="note-detail-inner">
          <input class="input" id="note-title-${n.id}" value="${escapeHtml(n.title)}" placeholder="${t('notes.input.title')}" data-pdm-oninput="updateNoteSaveBtnState(${n.id})">
          <div class="text-scroll-wrap">
            <textarea class="note-textarea" id="note-content-${n.id}" placeholder="${t('notes.input.content')}" data-pdm-oninput="updateNoteSaveBtnState(${n.id});updateLongTextHint(this,'note-scroll-hint-${n.id}')" data-pdm-onscroll="updateLongTextHint(this,'note-scroll-hint-${n.id}')">${escapeHtml(n.content)}</textarea>
            <div class="text-scroll-hint" id="note-scroll-hint-${n.id}"><span class="text-scroll-message"></span><span class="text-scroll-position"></span></div>
          </div>
          <div class="note-form-feedback" id="note-feedback-${n.id}"></div>
          <div class="note-actions">
            <button class="btn btn-danger btn-sm" data-pdm-onclick="deleteNote(${n.id})"><svg class="svg-fill" width="16" height="16" viewBox="0 0 256 256" aria-hidden="true"><path d="M216,48H176V40a24,24,0,0,0-24-24H104A24,24,0,0,0,80,40v8H40a8,8,0,0,0,0,16h8V208a16,16,0,0,0,16,16H192a16,16,0,0,0,16-16V64h8a8,8,0,0,0,0-16ZM112,168a8,8,0,0,1-16,0V104a8,8,0,0,1,16,0Zm48,0a8,8,0,0,1-16,0V104a8,8,0,0,1,16,0Zm0-120H96V40a8,8,0,0,1,8-8h48a8,8,0,0,1,8,8Z"/></svg> ${t('vault.button.delete')}</button>
            <button class="btn btn-primary btn-sm" id="note-save-${n.id}" data-pdm-onmousedown="captureNoteSaveScrollAnchor(${n.id})" data-pdm-onclick="saveNote(${n.id})" disabled><svg class="svg-fill" width="16" height="16" viewBox="0 0 256 256" aria-hidden="true"><path d="M219.31,72,184,36.69A15.86,15.86,0,0,0,172.69,32H48A16,16,0,0,0,32,48V208a16,16,0,0,0,16,16H208a16,16,0,0,0,16-16V83.31A15.86,15.86,0,0,0,219.31,72ZM208,208H184V152a16,16,0,0,0-16-16H88a16,16,0,0,0-16,16v56H48V48H172.69L208,83.31ZM160,72a8,8,0,0,1-8,8H96a8,8,0,0,1,0-16h56A8,8,0,0,1,160,72Z"/></svg> ${t('notes.button.save')}</button>
          </div>
        </div>
      </div>
    </div>
  `).join('');
  requestAnimationFrame(()=>list.forEach(n=>updateLongTextHint($('#note-content-'+n.id),'note-scroll-hint-'+n.id)));
}

/* 切换记事收藏 */
function toggleNoteFavorite(id,el){
  const n = notes.find(x=>x.id===id);
  if(!n) return;
  n.is_favorite = !n.is_favorite;
  if(el){el.classList.add('popping');setTimeout(()=>el.classList.remove('popping'),400)}
  setTimeout(()=>{
    renderNotes();
    showToast(n.is_favorite?t('toast.fav.added'):t('toast.fav.removed'),'success');
  },50);
}

function toggleNote(id){
  state.expandedId = state.expandedId===(id+1000)?null:(id+1000);
  renderNotes();
}

const noteSaveScrollAnchors = new Map();
function captureNoteSaveScrollAnchor(id){
  const content = document.querySelector('.content');
  if(content) noteSaveScrollAnchors.set(id,content.scrollTop);
}
function restoreNoteSaveScrollAnchor(id){
  const content = document.querySelector('.content');
  const value = noteSaveScrollAnchors.get(id);
  noteSaveScrollAnchors.delete(id);
  if(!content || value===undefined) return;
  const restore = ()=>{content.scrollTop=value};
  restore();
  requestAnimationFrame(restore);
}

function saveNote(id){
  const n = notes.find(x=>x.id===id);
  const titleEl = $('#note-title-'+id);
  const contentEl = $('#note-content-'+id);
  const feedback = $('#note-feedback-'+id);
  const title = titleEl.value.trim();
  if(!title){
    if(feedback) feedback.textContent = t('dialog.note.error.titleEmpty');
    titleEl.focus();
    restoreNoteSaveScrollAnchor(id);
    return;
  }
  n.title = title;
  n.content = contentEl.value;
  n.updated_at = new Date().toISOString().slice(0,10);
  // 原位提交：保持当前卡片、滚动位置和展开区不动，只同步摘要/时间/按钮。
  // “最近”筛选的重排延后到下一次显式切换筛选或重新进入页面，避免内容在手下跳走。
  const item = document.querySelector(`.note-item[data-id="${id}"]`);
  if(item){
    const summaryTitle = item.querySelector('.note-title');
    const preview = item.querySelector('.note-preview');
    const time = item.querySelector('.note-time');
    if(summaryTitle) summaryTitle.textContent = n.title;
    if(preview) preview.textContent = n.content.slice(0,40);
    if(time) time.textContent = n.updated_at;
  }
  if(feedback) feedback.textContent = '';
  const saveBtn = $('#note-save-'+id);
  if(saveBtn) saveBtn.disabled = true;
  restoreNoteSaveScrollAnchor(id);
  showToast(t('toast.note.saved'),'success');
}

/* 根据输入框值与原始值对比，动态切换保存按钮禁用态。
   未修改时禁用，帮助用户快速判断是否有改动；避免无意义保存触发 updated_at 刷新。 */
function updateNoteSaveBtnState(id){
  const n = notes.find(x=>x.id===id);
  if(!n) return;
  const titleEl = $('#note-title-'+id);
  const contentEl = $('#note-content-'+id);
  const saveBtn = $('#note-save-'+id);
  const feedback = $('#note-feedback-'+id);
  if(!titleEl || !contentEl || !saveBtn) return;
  if(feedback) feedback.textContent = '';
  const changed = titleEl.value !== n.title || contentEl.value !== n.content;
  saveBtn.disabled = !changed;
}

function deleteNote(id){
  const n = notes.find(x=>x.id===id);
  if(!n){showToast(t('toast.note.dialogNotFound'),'error');return}
  openModal(`
    <div class="modal-header">
      <div class="modal-title">${t('dialog.note.delete.title')}</div>
      <button class="modal-close" data-pdm-onclick="closeModal()">✕</button>
    </div>
    <div class="modal-body">
      <div class="delete-confirm-icon">${svgIcon('warning',32)}</div>
      <div class="delete-confirm-text">${t('dialog.note.delete.confirm').replace('{title}',escapeHtml(n.title))}</div>
      <div class="delete-confirm-desc">${t('dialog.note.delete.desc')}</div>
    </div>
    <div class="modal-footer">
      <div class="modal-footer-right">
        <button class="btn btn-sm note-delete-cancel" data-pdm-onclick="closeModal()">${t('dialog.button.cancel')}</button>
        <button class="btn btn-danger btn-sm" data-pdm-onclick="confirmDeleteNote(${id})">${t('dialog.button.delete')}</button>
      </div>
    </div>
  `,{closeOnBackdrop:false,initialFocusSelector:'.note-delete-cancel'});
}

function confirmDeleteNote(id){
  const idx = notes.findIndex(x=>x.id===id);
  if(idx<0){closeModal();return}
  const n = notes[idx];
  notes.splice(idx,1);
  state.expandedId = null;
  if(state.notesCardOpenId === id) state.notesCardOpenId = null;
  if(state.notesCardEditId === id) state.notesCardEditId = null;
  if(state.notesCardDraft?.id === id) state.notesCardDraft = null;
  closeModal();
  renderNotes();
  showToast(t('toast.deleted.prefix')+n.title,'success');
}

function addNote(){
  const newId = Math.max(0,...notes.map(n=>n.id))+1;
  notes.unshift({id:newId,title:t('notes.default.title'),content:t('notes.default.content'),updated_at:new Date().toISOString().slice(0,10),is_favorite:false});
  state.expandedId = newId+1000;
  renderNotes();
  showToast(t('toast.note.created'),'success');
}

/* ============================================================
   安全体检
   ============================================================ */

/* 健康分计算（方案 B：比例 + 绝对混合 + 上限保护）
   返回 {score, grade, gradeText, title, desc, weakCount, dupGroupCount, staleCount, ...}
   - score: 0-100 整数（空库返回 null）
   - grade: 'excellent'(≥90) / 'good'(70-89) / 'fair'(50-69) / 'risk'(<50) / 'none'(空库)
   - 颜色随等级切换：excellent=绿 / good=accent / fair=琥珀 / risk=红 / none=灰
   - 单项扣分 = min(count × 单条权重, 数量上限) + min(ratio × 100, 比例上限)
     · 弱密码  ：5 分/条（上限 40）+ 比例上限 30
     · 重复组 ：4 分/组（上限 20）+ 比例上限 15
     · 长期未换：1.5 分/条（上限 15）+ 比例上限 10
   - 多维度合并一致性：同一记录命中弱密码+长期未换时，引导按 id 合并去重，
     扣分时也按 id 合并取最大单条权重（避免重复扣分导致引导数与扣分逻辑不一致） */
function calcHealthScore(){
  const total = passwords.length;
  if(total === 0){
    return {
      score:null, grade:'none', gradeText:t('security.grade.none'),
      title:t('security.hero.title.none'), desc:t('security.hero.empty'),
      weakCount:0, dupGroupCount:0, staleCount:0, color:'var(--text-weak)'
    };
  }
  const weakCount = passwords.filter(p=>p.strength==='weak').length;
  // ⚠️ getDuplicateGroups() 返回 {id: 组号}，键是条目 id 不是组数
  // 用 Set 去重组号得到真正的"重复组数"
  const dupGroupCount = new Set(Object.values(getDuplicateGroups())).size;
  const threshold = parseInt($('#stale-num')?.value || 180);
  const today = new Date();
  const staleIds = new Set(passwords.filter(p=>daysBetween(p.password_changed_at, today) > threshold).map(p=>p.id));
  const staleCount = staleIds.size;

  // 多维度合并：同记录命中弱密码+长期未换，扣分只算一次（取最大单条权重）
  // weakCount 中与 staleIds 重叠的部分退回 stale 单条权重（1.5）的扣分
  const weakIdSet = new Set(passwords.filter(p=>p.strength==='weak').map(p=>p.id));
  const overlapCount = [...weakIdSet].filter(id=>staleIds.has(id)).length;

  const weakRatio = weakCount / total;
  const dupRatio = dupGroupCount / total;
  const staleRatio = staleCount / total;

  let weakPenalty   = Math.min(weakCount * 5, 40) + Math.min(weakRatio * 100, 30);
  let dupPenalty    = Math.min(dupGroupCount * 4, 20) + Math.min(dupRatio * 100, 15);
  let stalePenalty  = Math.min(staleCount * 1.5, 15) + Math.min(staleRatio * 100, 10);
  // 重叠退回：弱密码和长期未换重叠的记录，从 stalePenalty 退回单条权重 1.5
  stalePenalty = Math.max(0, stalePenalty - overlapCount * 1.5);

  const score = Math.max(0, Math.min(100, Math.round(100 - weakPenalty - dupPenalty - stalePenalty)));

  let grade, gradeText, title, color;
  if(score >= 90){      grade='excellent'; gradeText=t('security.grade.excellent'); title=t('security.hero.title.excellent'); color='var(--success)'; }
  else if(score >= 70){ grade='good';      gradeText=t('security.grade.good');      title=t('security.hero.title.good');      color='var(--accent)'; }
  else if(score >= 50){ grade='fair';      gradeText=t('security.grade.fair');      title=t('security.hero.title.fair');      color='#f59e0b'; }
  else {                grade='risk';      gradeText=t('security.grade.risk');      title=t('security.hero.title.risk');      color='#ef4444'; }

  // hero 描述
  const parts = [];
  if(weakCount > 0) parts.push(t('security.hero.weak').replace('{n}', weakCount));
  if(dupGroupCount > 0) parts.push(t('security.hero.dup').replace('{n}', dupGroupCount));
  if(staleCount > 0) parts.push(t('security.hero.stale').replace('{n}', staleCount));
  const desc = parts.length === 0
    ? t('security.hero.clean')
    : t('security.hero.desc').replace('{issues}', parts.join('、'));

  const pending=passwords.filter(p=>['pending','checking','failed'].includes(p.strength)).length;
  const failed=passwords.filter(p=>p.strength==='failed').length;
  if(pending) return {score:null, grade:'none', gradeText:t('common.strength.pending'),
    title:state.lang==='en'?'Password checks are not complete':'密码强度尚未全部检测',
    desc:state.lang==='en'?`${pending} pending, including ${failed} failed. Confirmed issues are shown below.`:`有 ${pending} 条待检测，其中 ${failed} 条失败；已确认的问题显示在下方。`,
    weakCount,dupGroupCount,staleCount,color:'var(--text-weak)',weakPenalty,dupPenalty,stalePenalty};
  return {score, grade, gradeText, title, desc, weakCount, dupGroupCount, staleCount, color, weakPenalty, dupPenalty, stalePenalty};
}

/* 更新健康分 hero 区（分数 / 进度环 / 等级徽章 / 标题 / 描述 / 颜色） */
function updateHealthHero(hero){
  const scoreNum = $('.score-num');
  const scoreLabel = $('.score-label');
  const progressCircle = $('.score-ring .progress');
  const gradStop = document.querySelector('#scoreGrad stop:last-child');
  const gradStopFirst = document.querySelector('#scoreGrad stop:first-child');
  const heroGrade = $('.hero-grade');
  const heroTitle = $('.hero-info h2');
  const heroDesc = $('.hero-info p');

  if(hero.score === null){
    // 空库
    if(scoreNum) scoreNum.textContent = '--';
    if(scoreLabel) scoreLabel.textContent = t('security.score.label');
    if(progressCircle) progressCircle.setAttribute('stroke-dashoffset', '377');
    if(gradStop) gradStop.setAttribute('stop-color', '#cbd5e1');
    if(gradStopFirst) gradStopFirst.setAttribute('stop-color', '#cbd5e1');
    if(heroGrade){ heroGrade.textContent = hero.gradeText; heroGrade.style.color = hero.color; heroGrade.style.background = 'rgba(203,213,225,.15)'; }
    if(heroTitle) heroTitle.textContent = hero.title;
    if(heroDesc) heroDesc.textContent = hero.desc;
    return;
  }
  if(scoreNum) scoreNum.textContent = hero.score;
  if(scoreLabel) scoreLabel.textContent = t('security.score.label');
  // 进度环：circumference = 2πr = 2π*60 ≈ 377
  if(progressCircle){
    const offset = 377 * (1 - hero.score/100);
    progressCircle.setAttribute('stroke-dashoffset', offset.toFixed(1));
  }
  // 进度环渐变颜色随等级切换（首站=等级色，末站=accent）
  if(gradStopFirst) gradStopFirst.setAttribute('stop-color', hero.color);
  if(gradStop) gradStop.setAttribute('stop-color', 'var(--accent)');
  // 等级徽章
  if(heroGrade){
    heroGrade.textContent = hero.gradeText;
    heroGrade.style.color = hero.color;
    // 半透明背景配合等级色
    const bgRgb = hero.grade==='excellent' ? '40,167,69'
                : hero.grade==='good' ? '124,127,245'
                : hero.grade==='fair' ? '245,158,11'
                : '239,68,68';
    heroGrade.style.background = `rgba(${bgRgb},.12)`;
  }
  if(heroTitle) heroTitle.textContent = hero.title;
  if(heroDesc) heroDesc.textContent = hero.desc;
}

/* 原型与正式页面共用进度呈现；正式任务状态由原生回执提供。 */
function renderHealthRescanStatus(scan, action='', error=''){
  const start=$('#health-rescan-start');
  const cancel=$('#health-rescan-cancel');
  const progress=$('#health-rescan-progress');
  const message=$('#health-rescan-status');
  if(!start||!cancel||!progress||!message) return;
  const text=(zh,en)=>state.lang==='en'?en:zh;
  const active=Boolean(scan&&['RUNNING','CANCELLING'].includes(scan.state));
  const cancelling=action==='CANCEL'||scan?.state==='CANCELLING';
  start.textContent=action==='START' ? text('正在启动…','Starting…')
    : active&&error ? text('重试读取','Retry status') : text('重新全量体检','Run full check');
  start.disabled=!state.connected||Boolean(action)||active&&!error;
  cancel.hidden=!active;
  cancel.disabled=!state.connected||cancelling;
  cancel.textContent=cancelling ? text('正在取消…','Cancelling…') : text('取消体检','Cancel check');
  progress.hidden=!scan||scan.total===0;
  progress.max=scan?.total||1;
  progress.value=scan?.completed||0;
  progress.setAttribute('aria-label',text('全量体检进度','Full check progress'));
  let value=text('按需重新检测所有密码并更新评级。','Recheck all passwords and update their ratings when needed.');
  if(action==='START'||scan?.state==='RUNNING'&&scan.total===0){
    value=text('正在准备重新体检…','Preparing the full check…');
  }else if(scan){
    const stateText=cancelling ? text('正在取消','Cancelling') : {
      RUNNING:text('正在体检','Checking'),COMPLETED:text('体检完成','Check completed'),
      CANCELLED:text('已取消体检','Check cancelled'),FAILED:text('体检未完成','Check incomplete'),
    }[scan.state];
    value=scan.state==='COMPLETED'&&scan.total===0
      ? text('体检完成，密码库暂无记录。','Check completed. The vault is empty.')
      : stateText+' · '+text(`已检测 ${scan.completed} / ${scan.total} 条，已更新 ${scan.updated} 条`,
        `${scan.completed} / ${scan.total} checked, ${scan.updated} updated`);
    if(scan.skipped||scan.failed){
      value+=' · '+text(`未更新 ${scan.skipped+scan.failed} 条（跳过 ${scan.skipped}，失败 ${scan.failed}）`,
        `${scan.skipped+scan.failed} not updated (${scan.skipped} skipped, ${scan.failed} failed)`);
    }
  }
  if(error) value+=' · '+error;
  message.textContent=value;
  message.dataset.error=error?'true':'false';
}

let demoHealthRescan=null;
let demoHealthRescanTimer=0;
function startDemoHealthRescan(){
  if(!state.connected||demoHealthRescan?.state==='RUNNING') return;
  demoHealthRescan={state:passwords.length?'RUNNING':'COMPLETED',total:passwords.length,
    completed:0,updated:0,skipped:0,failed:0};
  const advance=()=>{
    demoHealthRescanTimer=0;
    if(!state.connected||demoHealthRescan?.state!=='RUNNING') return;
    demoHealthRescan.completed++;
    demoHealthRescan.updated++;
    if(demoHealthRescan.completed===demoHealthRescan.total) demoHealthRescan.state='COMPLETED';
    renderHealthRescanStatus(demoHealthRescan);
    if(demoHealthRescan.state==='RUNNING') demoHealthRescanTimer=setTimeout(advance,500);
  };
  renderHealthRescanStatus(demoHealthRescan);
  if(demoHealthRescan.state==='RUNNING') demoHealthRescanTimer=setTimeout(advance,500);
}
$('#health-rescan-start')?.addEventListener('click',startDemoHealthRescan);
$('#health-rescan-cancel')?.addEventListener('click',()=>{
  if(demoHealthRescan?.state!=='RUNNING') return;
  clearTimeout(demoHealthRescanTimer);demoHealthRescanTimer=0;
  demoHealthRescan.state='CANCELLED';
  renderHealthRescanStatus(demoHealthRescan);
});

function renderSecurity(){
  // 未连接空状态：体检需要数据库中的密码记录
  if(!state.connected){
    clearTimeout(demoHealthRescanTimer);demoHealthRescanTimer=0;demoHealthRescan=null;
    renderHealthRescanStatus(null);
    updateHealthHero({score:0,grade:'none',title:t('startup.empty.security'),desc:''});
    $('#weak-issues').innerHTML = '';
    $('#dup-issues').innerHTML = '';
    $('#stale-issues').innerHTML = '';
    const fb = $('#fix-banner'); if(fb) fb.style.setProperty('display','none','important');
    return;
  }
  // 1. 计算并更新健康分 hero 区（分数 / 进度环 / 等级 / 标题 / 描述 / 颜色）
  renderHealthRescanStatus(demoHealthRescan);
  updateHealthHero(calcHealthScore());
  // 2. 渲染各类 issue 卡片
  const weakList = passwords.filter(p=>p.strength==='weak');
  $('#weak-issue-count').textContent = t('security.count.items').replace('{n}', weakList.length);
  $('#weak-issues').innerHTML = weakList.map(p=>`
    <div class="issue-row">
      <div class="platform-icon ${platformColorClass(p.platform)}">${platformIcon(p.platform)}</div>
      <div class="info">
        <div class="name">${escapeHtml(p.platform)}</div>
        <div class="desc">${t('security.desc.weak')}</div>
      </div>
      <button class="btn btn-ghost btn-sm" data-pdm-onclick="viewIssue(${p.id})">${t('security.button.fix')}</button>
    </div>
  `).join('') || '<div class="pdm-inline-8008da88de">'+t('security.empty.weak')+'</div>';

  // 重复密码检测
  const dupMap = getDuplicateGroups();
  const dupIds = Object.keys(dupMap).map(Number);
  const dupGroups = {};
  dupIds.forEach(id=>{
    const g = dupMap[id];
    if(!dupGroups[g]) dupGroups[g] = [];
    dupGroups[g].push(passwords.find(p=>p.id===id));
  });
  const groupCount = Object.keys(dupGroups).length;
  $('#dup-issue-count').textContent = t('security.count.group').replace('{n}', groupCount);
  $('#dup-issues').innerHTML = Object.values(dupGroups).map(items=>{
    const preview = items.slice(0,3);
    const more = items.length-preview.length;
    const moreText = more>0 ? (state.lang==='en'?` and ${more} more`:` 等 ${more} 项`) : '';
    const totalText = more>0 ? (state.lang==='en'?` · ${items.length} records total`:` · 共 ${items.length} 条记录`) : '';
    return `<div class="issue-row">
      <div class="platform-icon pdm-inline-7e2d119a49"><svg class="svg-fill" width="14" height="14" viewBox="0 0 256 256" aria-hidden="true"><path d="M224,48V96a8,8,0,0,1-8,8H168a8,8,0,0,1-5.66-13.66L180.65,72a79.48,79.48,0,0,0-54.72-22.09h-.45A79.52,79.52,0,0,0,69.59,72.71,8,8,0,0,1,58.41,61.27,96,96,0,0,1,192,60.7l18.36-18.36A8,8,0,0,1,224,48ZM186.41,183.29A80,80,0,0,1,75.35,184l18.31-18.31A8,8,0,0,0,88,152H40a8,8,0,0,0-8,8v48a8,8,0,0,0,13.66,5.66L64,195.3a95.42,95.42,0,0,0,66,26.76h.53a95.36,95.36,0,0,0,67.07-27.33,8,8,0,0,0-11.18-11.44Z"/></svg></div>
      <div class="info">
        <div class="name">${preview.map(p=>escapeHtml(p.platform)).join(t('security.dup.join'))}${moreText} ${t('security.desc.dupName')}</div>
        <div class="desc">${t('security.desc.dup')}${totalText}</div>
      </div>
      <button class="btn btn-ghost btn-sm" data-pdm-onclick="viewDuplicateIssue()">${t('security.button.view')}</button>
    </div>`;
  }).join('') || '<div class="pdm-inline-8008da88de">'+t('security.empty.dup')+'</div>';

  // 长期未更换检测（使用 password_changed_at 而非 updated_at）
  const threshold = parseInt($('#stale-num')?.value || 180);
  const today = new Date();
  const staleList = passwords.filter(p=>{
    const days = daysBetween(p.password_changed_at, today);
    return days > threshold;
  });
  $('#stale-issue-count').textContent = t('security.count.items').replace('{n}', staleList.length);
  $('#stale-issues').innerHTML = staleList.map(p=>{
    const days = daysBetween(p.password_changed_at, today);
    return `
    <div class="issue-row">
      <div class="platform-icon pdm-inline-cc1dfa662a"><svg class="svg-fill" width="14" height="14" viewBox="0 0 256 256" aria-hidden="true"><path d="M128,24A104,104,0,1,0,232,128,104.11,104.11,0,0,0,128,24Zm56,112H128a8,8,0,0,1-8-8V72a8,8,0,0,1,16,0v48h48a8,8,0,0,1,0,16Z"/></svg></div>
      <div class="info">
        <div class="name">${escapeHtml(p.platform)} · ${t('security.name.stale').replace('{n}', days)}</div>
        <div class="desc">${t('security.desc.stale').replace('{n}', threshold)}</div>
      </div>
      <button class="btn btn-ghost btn-sm" data-pdm-onclick="viewIssue(${p.id})">${t('security.button.fix')}</button>
    </div>`;
  }).join('') || '<div class="pdm-inline-8008da88de">'+t('security.empty.stale')+'</div>';

  // 同步刷新"逐个引导修复"按钮的可用态
  const fixBtn = $('.fix-all-btn');
  if(fixBtn){
    const hasIssues = collectSecurityIssues().length > 0;
    fixBtn.disabled = !hasIssues;
    fixBtn.classList.toggle('disabled', !hasIssues);
  }
}

/* 计算两个日期之间的天数差（两端归一化到本地午夜，规避夏令时漂移） */
function daysBetween(from, to){
  const a = new Date(from); a.setHours(0,0,0,0);
  const b = new Date(to);   b.setHours(0,0,0,0);
  return Math.floor((b - a) / 86400000);
}

/* 查看重复密码：跳转到密码库并激活重复筛选 */
function viewDuplicateIssue(){
  navigateTo('vault');
  state.viewMode = 'list';
  $$('.view-switcher .btn-icon').forEach(b=>b.classList.toggle('active',b.dataset.view==='list'));
  setFilter('duplicate');
  showToast(t('toast.dup.shown'),'info');
}

function viewIssue(id){
  const p = passwords.find(x=>x.id===id);
  if(!p){showToast(t('toast.notFound'),'error');return}
  navigateTo('vault');
  state.filter = 'all';
  state.viewMode = 'list';
  $$('.view-switcher .btn-icon').forEach(b=>b.classList.toggle('active',b.dataset.view==='list'));
  state.expandedId = p.id;
  setTimeout(()=>{
    renderVault();
    const el = document.querySelector(`.list-item[data-id="${p.id}"]`);
    if(el){el.scrollIntoView({behavior:'smooth',block:'center'});el.style.boxShadow='0 0 0 2px var(--accent)';setTimeout(()=>el.style.boxShadow='',2000)}
    showToast(t('toast.located.prefix')+p.platform+t('toast.located.suffix'),'info');
    // 自动打开编辑对话框
    setTimeout(()=>openEditPasswordDialog(p.id),800);
  },100);
}

/* 一键修复改为逐个引导修复 */
function fixAll(){
  const issues = collectSecurityIssues();
  if(issues.length===0){
    showToast(t('toast.noIssues'),'info');
    return;
  }
  state.fixQueue = issues;
  state.fixIndex = 0;
  state.fixResults = {};
  showFixGuide();
}

/* 收集所有安全问题（弱密码+重复密码+长期未更换）
   按 id 合并多维度问题到同一引导项，避免同记录被重复引导；
   types 数组保留所有命中维度，引导对话框徽章同时展示 */
function collectSecurityIssues(){
  const map = new Map(); // id -> {id, types:[]}
  const push = (id, type) => {
    if(!map.has(id)) map.set(id, {id, types:[]});
    const entry = map.get(id);
    if(!entry.types.includes(type)) entry.types.push(type);
  };
  // 弱密码
  passwords.filter(p=>p.strength==='weak').forEach(p=>push(p.id,'weak'));
  // 重复密码
  const dupMap = getDuplicateGroups();
  Object.keys(dupMap).map(Number).forEach(id=>push(id,'duplicate'));
  // 长期未更换（使用 password_changed_at 而非 updated_at）
  const threshold = parseInt($('#stale-num')?.value || 180);
  const today = new Date();
  passwords.forEach(p=>{
    if(daysBetween(p.password_changed_at, today) > threshold) push(p.id,'stale');
  });
  // 排序：多问题优先（让用户优先处理综合性问题），其次按 id
  return Array.from(map.values()).sort((a,b)=>{
    if(a.types.length !== b.types.length) return b.types.length - a.types.length;
    return a.id - b.id;
  });
}

/* 显示引导修复进度对话框 */
function showFixGuide(){
  if(!state.fixQueue || state.fixIndex>=state.fixQueue.length){
    showFixCompleteDialog();
    return;
  }
  const issue = state.fixQueue[state.fixIndex];
  const p = passwords.find(x=>x.id===issue.id);
  if(!p){state.fixIndex++;showFixGuide();return}
  const total = state.fixQueue.length;
  const current = state.fixIndex+1;
  const isMulti = issue.types.length > 1;
  const badgesHtml = issue.types.map(type => {
    return `<span class="pdm-security-issue-pill pdm-security-issue-${type}">${t('security.issue.'+type)}</span>`;
  }).join(' ');
  const multiHintHtml = isMulti ? `
    <div class="pdm-inline-0bc9a9c252">
      ${t('fix.guide.multiIssue').replace('{n}', issue.types.length)}
    </div>
  ` : '';
  const html = `
    <div class="modal-header">
      <div class="modal-title"><svg class="svg-fill" width="16" height="16" viewBox="0 0 256 256" aria-hidden="true"><path d="M232,96a72,72,0,0,1-100.94,66L79,222.22c-.12.14-.26.29-.39.42a32,32,0,0,1-45.26-45.26c.14-.13.28-.27.43-.39L94,124.94a72.07,72.07,0,0,1,83.54-98.78,8,8,0,0,1,3.93,13.19L144,80l5.66,26.35L176,112l40.65-37.52a8,8,0,0,1,13.19,3.93A72.6,72.6,0,0,1,232,96Z"/></svg> ${t('fix.modal.title')}</div>
      <button class="modal-close" data-pdm-onclick="closeModal()">✕</button>
    </div>
    <div class="modal-body">
      <div class="pdm-inline-10532f003b">
        <div class="pdm-inline-d061091441">${t('fix.progress.label')} <strong class="pdm-inline-be74bc7ba3">${current} / ${total}</strong></div>
        <div class="pdm-inline-42a6ced8b6">${badgesHtml}</div>
        ${multiHintHtml}
        <div class="pdm-inline-f8689d220b">${escapeHtml(p.platform)}</div>
        <div class="pdm-inline-2ddc165c05">${t('fix.guide.hint')}</div>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-sm" data-pdm-onclick="abandonFix()">${t('fix.button.abandon')}</button>
      <div class="modal-footer-right">
        <button class="btn btn-sm" data-pdm-onclick="prevFix()" ${state.fixIndex===0?'disabled':''}>${t('fix.button.prev')}</button>
        <button class="btn btn-sm" data-pdm-onclick="skipFix()">${t('fix.button.skip')}</button>
        <button class="btn btn-primary btn-sm" data-pdm-onclick="goFixCurrent(${p.id})">${t('fix.button.goto')}</button>
      </div>
    </div>
  `;
  openModal(html);
  renderFixBanner();
}

/* 显示完成对话框（含统计） */
function showFixCompleteDialog(){
  const total = state.fixQueue ? state.fixQueue.length : 0;
  const results = Object.values(state.fixResults||{});
  const skipped = results.filter(x=>x==='skipped').length;
  const done = results.filter(x=>x==='done').length;
  const html = `
    <div class="modal-header">
      <div class="modal-title">${t('fix.progress.label')}</div>
      <button class="modal-close" data-pdm-onclick="closeModal()">✕</button>
    </div>
    <div class="modal-body">
      <div class="pdm-inline-670b19889e">
        <div class="pdm-inline-f11bfb69de">✓</div>
        <div class="pdm-inline-30e294142f">${t('fix.progress.complete')}</div>
        <div class="pdm-inline-db0d356a5d">${t('fix.progress.summary').replace('{total}',total).replace('{done}',done).replace('{skipped}',skipped)}</div>
      </div>
    </div>
    <div class="modal-footer">
      <div class="modal-footer-right">
        <button class="btn btn-primary btn-sm" data-pdm-onclick="closeFixGuide()">${t('fix.button.finish')}</button>
      </div>
    </div>
  `;
  openModal(html);
  state.fixQueue = null;
  renderFixBanner();
}

/* 跳转到当前问题记录并打开编辑 */
function goFixCurrent(id){
  closeModal();
  navigateTo('vault');
  state.filter='all';
  state.viewMode='list';
  $$('.view-switcher .btn-icon').forEach(b=>b.classList.toggle('active',b.dataset.view==='list'));
  state.expandedId = id;
  setTimeout(()=>{
    renderVault();
    const el = document.querySelector(`.list-item[data-id="${id}"]`);
    if(el){el.scrollIntoView({behavior:'smooth',block:'center'});el.style.boxShadow='0 0 0 2px var(--accent)';setTimeout(()=>el.style.boxShadow='',2000)}
    openEditPasswordDialog(id);
  },100);
}

/* 跳过当前问题 */
function skipFix(){
  state.fixResults[state.fixIndex] = 'skipped';
  state.fixIndex++;
  showFixGuide();
}

/* 上一个问题（首个时禁用） */
function prevFix(){
  if(state.fixIndex > 0){
    const previousIndex = state.fixIndex - 1;
    delete state.fixResults[previousIndex];
    state.fixIndex = previousIndex;
    showFixGuide();
  }
}

/* 关闭引导修复 */
function closeFixGuide(){
  closeModal();
  state.fixQueue = null;
  state.fixResults = {};
  renderFixBanner();
}

/* 编辑对话框内"跳过此项"按钮：直接跳过当前 issue 回到引导 */
function skipCurrentInDialog(){
  closeModal();
  skipFix();
}

/* 放弃引导（密码库横幅上的按钮） */
function abandonFix(){
  closeFixGuide();
  showToast(t('fix.toast.abandoned'),'info');
}

/* 渲染/刷新密码库顶部的"返回引导"横幅 */
function renderFixBanner(){
  const banner = $('#fix-banner');
  if(!banner) return;
  if(!state.fixQueue || state.fixIndex >= state.fixQueue.length){
    banner.style.setProperty('display','none','important');
    return;
  }
  const remaining = state.fixQueue.length - state.fixIndex;
  banner.style.setProperty('display','flex','important');
  banner.innerHTML = `
    <span class="fix-banner-icon"><svg class="svg-fill" width="16" height="16" viewBox="0 0 256 256" aria-hidden="true"><path d="M232,96a72,72,0,0,1-100.94,66L79,222.22c-.12.14-.26.29-.39.42a32,32,0,0,1-45.26-45.26c.14-.13.28-.27.43-.39L94,124.94a72.07,72.07,0,0,1,83.54-98.78,8,8,0,0,1,3.93,13.19L144,80l5.66,26.35L176,112l40.65-37.52a8,8,0,0,1,13.19,3.93A72.6,72.6,0,0,1,232,96Z"/></svg></span>
    <span class="fix-banner-text"><strong>${t('fix.banner.title')}</strong> · ${t('fix.banner.remaining').replace('{n}', remaining)}</span>
    <span class="fix-banner-actions">
      <button class="btn btn-sm" data-pdm-onclick="abandonFix()">${t('fix.banner.abandon')}</button>
      <button class="btn btn-primary btn-sm" data-pdm-onclick="closeModal();showFixGuide()">${t('fix.banner.continue')}</button>
    </span>
  `;
}

/* 编辑保存后检查是否处于引导流程，显示进度提示 */
function onPasswordSaved(recordId){
  if(state.fixQueue && state.fixIndex < state.fixQueue.length &&
     state.fixQueue[state.fixIndex].id===recordId){
    state.fixResults[state.fixIndex] = 'done';
    state.fixIndex++;
    const total = state.fixQueue.length;
    const done = Object.values(state.fixResults||{}).filter(x=>x==='done').length;
    const skipped = Object.values(state.fixResults||{}).filter(x=>x==='skipped').length;
    const finished = done + skipped >= total;
    if(finished){
      showFixCompleteDialog();
      return;
    }
    const html = `
      <div class="modal-header">
        <div class="modal-title">${t('fix.progress.label')}</div>
        <button class="modal-close" data-pdm-onclick="closeModal()">✕</button>
      </div>
      <div class="modal-body">
        <div class="pdm-inline-670b19889e">
          <div class="pdm-inline-f11bfb69de">✓</div>
          <div class="pdm-inline-30e294142f">${t('fix.progress.fixed').replace('{done}',done).replace('{total}',total)}</div>
          <div class="pdm-inline-db0d356a5d">${t('fix.progress.continue')}</div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-sm" data-pdm-onclick="closeModal()">${t('fix.button.back')}</button>
        <div class="modal-footer-right">
          <button class="btn btn-primary btn-sm" data-pdm-onclick="closeModal();showFixGuide()">${t('fix.button.continue')}</button>
        </div>
      </div>
    `;
    openModal(html);
    renderFixBanner();
  }
}

const GENERATOR_CHARSETS={
  lower:'abcdefghijklmnopqrstuvwxyz',upper:'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
  digit:'0123456789',symbol:'!@#$%^&*()[]'
};
const GENERATOR_AMBIGUOUS='0O1lI';

function generatorPolicy(length){
  const raw=String(length ?? $('#gen-length')?.value ?? '20');
  const parsed=/^[0-9]+$/.test(raw)?Number(raw):Number.NaN;
  return {length:parsed,useLower:state.genCharset.lower,useUpper:state.genCharset.upper,
    useDigits:state.genCharset.digit,useSymbols:state.genCharset.symbol,
    avoidAmbiguous:state.genAvoidAmbiguous};
}
function generatorPolicyError(policy){
  if(!Number.isSafeInteger(policy.length)||policy.length<1||policy.length>1024) return 'tool.gen.error.length';
  const selected=['useLower','useUpper','useDigits','useSymbols'].filter(key=>policy[key]).length;
  if(!selected) return 'tool.gen.error.needCharset';
  return policy.length<selected?'tool.gen.error.tooShort':'';
}
function generatePasswordValue(policy){
  if(generatorPolicyError(policy)) return '';
  const names=[['useLower','lower'],['useUpper','upper'],['useDigits','digit'],['useSymbols','symbol']];
  const sets=names.filter(([flag])=>policy[flag]).map(([,name])=>
    [...GENERATOR_CHARSETS[name]].filter(char=>!policy.avoidAmbiguous||!GENERATOR_AMBIGUOUS.includes(char)).join(''));
  const all=sets.join('');
  const password=sets.map(rand);
  for(let index=password.length;index<policy.length;index++) password.push(rand(all));
  return password.sort(()=>Math.random()-.5).join('');
}
function generateStrongPassword(len){
  return generatePasswordValue({...generatorPolicy(len),useLower:true,useUpper:true,useDigits:true,useSymbols:true});
}
function rand(s){return s[Math.floor(Math.random()*s.length)]}

/* ============================================================
   工具
   ============================================================ */
function switchTool(t){
  $$('.tool-tab').forEach(x=>x.classList.toggle('active',x.dataset.tool===t));
  $$('.tool-panel').forEach(x=>x.classList.remove('active'));
  $('#tool-'+t).classList.add('active');
}

/* 字符集勾选切换：更新 state.genCharset + UI 勾选态。
   持久化策略：同 syncGenLength，仅连接后写 settings.json（generator.charset.{lower,upper,digit,symbol}），
   未连接时仅改内存不持久化。Win 端：if(state.connected) config.set('generator.charset.'+k, state.genCharset[k]); */
function toggleCharset(el){
  const k = el.dataset.charset;
  state.genCharset[k] = !state.genCharset[k];
  el.classList.toggle('checked',state.genCharset[k]);
  el.querySelector('.check-box').textContent = state.genCharset[k]?'✓':'';
  /* Win 端：if(state.connected) config.set('generator.charset.'+k, state.genCharset[k]); */
}

function toggleGeneratorAvoid(checked){
  state.genAvoidAmbiguous=Boolean(checked);
  const item=$('#gen-avoid-item');
  item?.classList.toggle('checked',state.genAvoidAmbiguous);
  const mark=item?.querySelector('.check-box');
  if(mark) mark.textContent=state.genAvoidAmbiguous?'✓':'';
}

function generatePassword(){
  const policy=generatorPolicy();
  const error=generatorPolicyError(policy);
  if(error){showToast(t(error),'error');return}
  const pw=generatePasswordValue(policy);
  state.genPassword = pw;
  $('#gen-output').textContent = pw;
  showToast(t('toast.gen.generated'),'success');
}

function copyGenerated(){
  if(!state.genPassword){showToast(t('toast.gen.needGenFirst'),'error');return}
  copyText(state.genPassword,t('vault.detail.password'));
}

function saveGenerated(){
  if(!state.genPassword){showToast(t('toast.gen.needGenFirst'),'error');return}
  // 打开新增密码对话框并预填当前生成的密码，由用户补全平台/账号等信息后落库
  openAddPasswordDialog(state.genPassword);
}

/* 恢复生成器默认配置：长度=20、字符集四项全开，并立即触发生成。
   持久化策略：内部调 syncGenLength(20) + 修改 state.genCharset，遵循同样的"仅连接后持久化"规则。
   未连接时恢复默认只影响当前会话内存，不覆盖 settings.json 里的原主偏好。 */
function resetGenConfig(){
  syncGenLength(20);
  ['lower','upper','digit','symbol'].forEach(k=>{
    state.genCharset[k] = true;
    const item = document.querySelector(`.check-item[data-charset="${k}"]`);
    if(item){
      item.classList.add('checked');
      const box = item.querySelector('.check-box');
      if(box) box.textContent = '✓';
    }
  });
  state.genAvoidAmbiguous=false;
  const avoid=$('#gen-avoid');
  if(avoid) avoid.checked=false;
  toggleGeneratorAvoid(false);
  generatePassword();
}

function toggleCheckPassword(){
  toggleStaticPasswordVisibility('check-input','check-eye');
}

// 条长显示猜测成本的数量级；10¹⁸次为显示上限，不是安全保证。
function strengthBarPercent(guesses){
  const count = Number(guesses);
  if (!(count > 1)) return 0;
  if (count >= 1e18) return 100;
  return Math.log10(count) / 18 * 100;
}

function checkStrength(){
  const pw = $('#check-input').value;
  if(!pw){
    $('#strength-fill').style.width='0';
    $('#strength-rating').textContent='—';
    $('#suggestions').innerHTML='';
    return;
  }

  /* 读取平台/账号上下文（可选，用于 zxcvbn user_inputs 上下文匹配） */
  const platform = ($('#check-platform')?.value || '').trim();
  const account = ($('#check-account')?.value || '').trim();

  /* 核心评估算法（基于 zxcvbn：熵估算 + 中文字典 + user_inputs 上下文） */
  const result = evaluateStrength(pw, platform, account);

  const colorMap = {
    weak:'var(--strength-weak)',
    fair:'var(--strength-fair)',
    strong:'var(--strength-strong)'
  };
  const percent = strengthBarPercent(result.guesses);
  const color = colorMap[result.rating];

  const fill = $('#strength-fill');
  fill.style.width = percent+'%';
  fill.style.background = color;
  const ratingEl = $('#strength-rating');
  /* 强度评级文字按当前语言显示（弱/中/强 或 Weak/Fair/Strong） */
  ratingEl.textContent = t('tool.check.level.' + result.rating);
  ratingEl.style.color = color;

  /* 第 2 层：破解时间预估（4 种攻击场景平等展示，不高亮主场景）
     label 用 t() 翻译，val 用 translateCrackTime() 翻译 zxcvbn 英文原值 */
  const ct = result.crackTimes || {};
  const crackTimeRows = [
    {labelKey:'tool.check.crackTime.online_throttling',   val:ct.online_throttling_100_per_hour},
    {labelKey:'tool.check.crackTime.online_no_throttling', val:ct.online_no_throttling_10_per_second},
    {labelKey:'tool.check.crackTime.offline_slow',         val:ct.offline_slow_hashing_1e4_per_second},
    {labelKey:'tool.check.crackTime.offline_fast',         val:ct.offline_fast_hashing_1e10_per_second},
  ].filter(r => r.val);
  const crackTimeHtml = crackTimeRows.length ? `
    <div class="strength-section-title">${t('tool.check.crackTime.title')}</div>
    ${crackTimeRows.map(r=>`
      <div class="suggestion crack-time-row">
        <span class="crack-time-label">${t(r.labelKey)}</span>
        <span class="crack-time-val">${escapeHtml(translateCrackTime(r.val))}</span>
      </div>
    `).join('')}
  ` : '';

  /* 第 3 层-A：风险提示（zxcvbn sequence 命中 + warning + 降级提示，按当前语言显示） */
  const risksHtml = result.risks && result.risks.length ? `
    <div class="suggestion-warn-divider">${t('tool.check.risks.title')}</div>
    ${result.risks.map(r=>`
      <div class="suggestion suggestion-warn">
        <span class="warn">⚠</span>
        <span>${escapeHtml(r[state.lang] || r.zh)}</span>
      </div>
    `).join('')}
  ` : '';

  /* 第 3 层-B：改进建议（zxcvbn suggestions 翻译，按当前语言显示） */
  const suggHtml = result.suggestions && result.suggestions.length ? `
    <div class="suggestion-sugg-divider">${t('tool.check.suggestions.title')}</div>
    ${result.suggestions.map(s=>`
      <div class="suggestion suggestion-tip">
        <span class="tip">•</span>
        <span>${escapeHtml(s[state.lang] || s.zh)}</span>
      </div>
    `).join('')}
  ` : '';

  $('#suggestions').innerHTML = crackTimeHtml + risksHtml + suggHtml;
}

/* ============================================================
   设置 / 主题
   ============================================================ */
const systemThemeQuery = matchMedia('(prefers-color-scheme: light)');

function setTheme(mode, userInitiated=false){
  const previousMode = state.theme;
  state.theme = mode;
  $$('#theme-segment button').forEach((b,i)=>{
    b.classList.toggle('active',['light','dark','auto'][i]===mode);
  });
  const isDark = mode==='dark' || (mode==='auto' && !systemThemeQuery.matches);
  document.documentElement.classList.toggle('light',!isDark);
  $('#theme-btn').innerHTML = svgIcon(isDark?'moon':'sun',16);
  syncThemeAccessibility();
  if(userInitiated && previousMode!==mode){
    const toastKey = mode==='auto' ? 'toast.theme.auto' : (mode==='dark' ? 'toast.theme.dark' : 'toast.theme.light');
    showToast(t(toastKey),'info');
  }
}

function toggleTheme(){
  const next = state.theme==='dark'?'light':'dark';
  setTheme(next,true);
}

/* 共享浏览器原型用媒体查询模拟原生 S05；系统变化只刷新 AUTO 的有效主题且保持静默。 */
function applyDemoSystemThemeChange(){
  /* 产品候选只消费原生 S05；matchMedia 仅供无 Bridge 的共享原型模拟。 */
  if(window.pdmM4) return;
  if(state.theme==='auto') setTheme('auto',false);
}
if(typeof systemThemeQuery.addEventListener==='function'){
  systemThemeQuery.addEventListener('change',applyDemoSystemThemeChange);
}else if(typeof systemThemeQuery.addListener==='function'){
  systemThemeQuery.addListener(applyDemoSystemThemeChange);
}

/* ============================================================
   Quick Bar
   ============================================================ */
let quickBarHideTimer = null;

function openQuickBar(){
  // 守卫：未连接数据库时拒绝打开（与全局热键 if(state.connected) 守卫对齐）
  // 原因：QuickBar 数据源为 state.passwords（已解密内存列表），未连接时为空；
  // 若放任打开，用户会看到空结果却不知原因，且易误以为"数据已解密可见"。
  if(!state.connected){
    showToast(t('startup.dependent.disabled.tip'),'warning');
    return;
  }
  state.quickBarVisible = true;
  $('#quickbar-overlay').classList.add('visible');
  const input = $('#quickbar-input');
  input.value = '';
  setTimeout(()=>input.focus(),50);
  handleQuickBarInput('');
  resetQuickBarHide();
}

function closeQuickBar(){
  state.quickBarVisible = false;
  $('#quickbar-overlay').classList.remove('visible');
  if(quickBarHideTimer){clearTimeout(quickBarHideTimer);quickBarHideTimer=null}
}

function clearQuickBarSearch(){
  const input = $('#quickbar-input');
  if(!input) return;
  input.value = '';
  handleQuickBarInput('');
  input.focus({preventScroll:true});
}

function resetQuickBarHide(){
  if(quickBarHideTimer) clearTimeout(quickBarHideTimer);
  quickBarHideTimer = setTimeout(
    ()=>{if(state.quickBarVisible)closeQuickBar()},
    state.quickBarAutohideSec*1000,
  );
}

function syncQuickBarAutohide(val){
  let value = parseInt(val);
  if(isNaN(value)) value = 30;
  value = Math.max(10,Math.min(600,value));
  state.quickBarAutohideSec = value;
  const slider = $('#quickbar-timeout-slider');
  const number = $('#quickbar-timeout-num');
  const label = $('#quickbar-autohide-label');
  if(slider) slider.value = value;
  if(number) number.value = value;
  if(label){
    label.textContent = state.lang==='zh'
      ? `${value} 秒无操作自动隐藏`
      : `Auto-hide after ${value}s of inactivity`;
  }
  if(state.quickBarVisible) resetQuickBarHide();
}

function handleQuickBarInput(v){
  resetQuickBarHide();
  const clearButton = $('.quickbar-clear');
  if(clearButton) clearButton.hidden = v.length === 0;
  const results = $('#quickbar-results');
  // 命令模式
  const cmdMatch = v.trim().match(/^gen\s*(\d*)$/i);
  if(cmdMatch){
    const len = Number(cmdMatch[1]||'20');
    if(!Number.isSafeInteger(len)||len<4||len>1024){
      results.innerHTML = `<div class="quickbar-hint">${t('quickbar.cmd.range')}</div>`;
      state.quickBarResults = [];
      return;
    }
    results.innerHTML = `
      <div class="qb-command" data-pdm-onclick="quickBarGenerate(${len})">
        <span class="pdm-inline-d7db16a373"><svg class="svg-fill" width="16" height="16" viewBox="0 0 256 256" aria-hidden="true"><path d="M192,32H64A32,32,0,0,0,32,64V192a32,32,0,0,0,32,32H192a32,32,0,0,0,32-32V64A32,32,0,0,0,192,32ZM92,176a12,12,0,1,1,12-12A12,12,0,0,1,92,176Zm0-72a12,12,0,1,1,12-12A12,12,0,0,1,92,104Zm36,36a12,12,0,1,1,12-12A12,12,0,0,1,128,140Zm36,36a12,12,0,1,1,12-12A12,12,0,0,1,164,176Zm0-72a12,12,0,1,1,12-12A12,12,0,0,1,164,104Z"/></svg></span>
        <span>${t('quickbar.cmd.generate').replace('{n}', len)}</span>
      </div>
      <div class="quickbar-hint" id="quickbar-command-hint">${t('quickbar.cmd.hint')}</div>
    `;
    state.quickBarResults = [{type:'cmd',len}];
    return;
  }

  if([...v].length>128||new TextEncoder().encode(v).length>512){
    results.innerHTML = `<div class="quickbar-hint">${t('quickbar.query.limit')}</div>`;
    state.quickBarResults = [];
    return;
  }
  const q = v.trim().toLowerCase();
  let list = passwords;
  if(q) list = passwords.filter(p=>settingsFieldMatches(p.platform,q)||settingsFieldMatches(p.account,q));
  const total = list.length;
  const collator = new Intl.Collator(state.lang==='zh'?'zh-CN-u-co-pinyin':'en',{sensitivity:'base'});
  list = [...list].sort((a,b)=>Number(b.is_favorite)-Number(a.is_favorite)||
    collator.compare(a.platform,b.platform)||a.account.localeCompare(b.account)||a.id-b.id).slice(0,20);

  state.quickBarResults = list;
  state.quickBarIndex = 0;

  if(list.length===0 && q){
    results.innerHTML = `<div class="quickbar-hint">${t('quickbar.hint.notfound').replace('{q}', escapeHtml(v))}</div>`;
    return;
  }
  if(list.length===0){
    results.innerHTML = `<div class="quickbar-hint">${t('quickbar.hint.empty')}</div>`;
    return;
  }

  results.innerHTML = list.map((p,i)=>`
    <div class="qb-item ${i===0?'highlight':''}" data-id="${p.id}" data-idx="${i}">
      <div class="platform-icon ${platformColorClass(p.platform)}">${platformIcon(p.platform)}</div>
      <div class="info">
        <div class="name">${escapeHtml(p.platform)} <span class="fav-star ${p.is_favorite?'active':''} pdm-inline-b4cff472d0">${p.is_favorite?svgIcon('star',14):'<svg class="svg-fill fav-star-empty" width="14" height="14" viewBox="0 0 256 256" aria-hidden="true"><path d="' + SVG_ICONS_FILL.star + '"/></svg>'}</span></div>
        <div class="sub">${escapeHtml(p.account)}</div>
      </div>
      <div class="actions">
        <button class="btn-icon qb-copy-btn" data-field="account" data-id="${p.id}" data-pdm-onclick="event.stopPropagation();quickBarCopyByData(this)" title="${t('vault.copy.account')}"><svg class="svg-fill" width="15" height="15" viewBox="0 0 256 256" aria-hidden="true"><path d="M230.93,220a8,8,0,0,1-6.93,4H32a8,8,0,0,1-6.92-12c15.23-26.33,38.7-45.21,66.09-54.16a72,72,0,1,1,73.66,0c27.39,8.95,50.86,27.83,66.09,54.16A8,8,0,0,1,230.93,220Z"/></svg></button>
        <button class="btn-icon qb-copy-btn" data-field="password" data-id="${p.id}" data-pdm-onclick="event.stopPropagation();quickBarCopyByData(this)" title="${t('vault.copy.password')}"><svg class="svg-fill" width="15" height="15" viewBox="0 0 256 256" aria-hidden="true"><path d="M216.57,39.43A80,80,0,0,0,83.91,120.78L28.69,176A15.86,15.86,0,0,0,24,187.31V216a16,16,0,0,0,16,16H72a8,8,0,0,0,8-8V208H96a8,8,0,0,0,8-8V184h16a8,8,0,0,0,5.66-2.34l9.56-9.57A79.73,79.73,0,0,0,160,176h.1A80,80,0,0,0,216.57,39.43ZM180,92a16,16,0,1,1,16-16A16,16,0,0,1,180,92Z"/></svg></button>
      </div>
    </div>
  `).join('')+(total>list.length
    ?`<div class="quickbar-hint">${t('quickbar.results.more').replace('{n}',total)}</div>`:'');

  // 整项点击 = 复制密码（不关闭，让用户继续复制账号）
  // 通过触发密码按钮的视觉反馈，让用户清楚看到"复制了哪个字段"
  $$('.qb-item').forEach(el=>{
    el.onclick = ()=>{
      const pwdBtn = el.querySelector('.qb-copy-btn[data-field="password"]');
      quickBarCopyByData(pwdBtn);
    };
  });
}

/* 复制视觉反馈：按钮临时显示对勾 + 变绿，1.2s 后恢复
   设计意图：用户复制账号后往往还要复制密码，反馈必须明确"刚复制的是哪个字段"，
   避免用户重复点同一按钮或忘记已复制哪个。*/
function markCopied(btn){
  if(!btn) return;
  if(btn._copiedTimer) clearTimeout(btn._copiedTimer);
  if(!btn.dataset.originalHtml) btn.dataset.originalHtml = btn.innerHTML;
  btn.classList.add('copied');
  btn.innerHTML = svgIcon('check',15);
  btn._copiedTimer = setTimeout(()=>{
    btn.classList.remove('copied');
    if(btn.dataset.originalHtml){
      btn.innerHTML = btn.dataset.originalHtml;
      delete btn.dataset.originalHtml;
    }
    btn._copiedTimer = null;
  },1200);
}

/* QuickBar 复制封装：复制 + 视觉反馈 + 重置自动隐藏（不关闭浮层）
   与 closeQuickBar 解耦——用户可连续复制账号和密码，无需重新唤出搜索。*/
function quickBarCopy(text, label, btn){
  copyText(text, label);
  markCopied(btn);
  resetQuickBarHide();
}

/* 通过按钮 data-* 属性取数据并复制（避免内联 onclick 拼接字符串的转义陷阱）*/
function quickBarCopyByData(btn){
  if(!btn) return;
  const p = passwords.find(x=>String(x.id)===String(btn.dataset.id));
  if(!p) return;
  const field = btn.dataset.field;
  const text = field==='account' ? p.account : p.password;
  const label = field==='account' ? t('vault.detail.account') : t('vault.detail.password');
  quickBarCopy(text, label, btn);
}

function quickBarGenerate(len){
  len = Number(len);
  if(!Number.isSafeInteger(len)||len<4||len>1024) return;
  const pw = generateStrongPassword(len);
  if(!pw) return;
  try{navigator.clipboard && navigator.clipboard.writeText(pw)}catch(e){}
  startClipboardCountdown();
  const hint = $('#quickbar-command-hint');
  if(hint){
    hint.textContent=t('quickbar.cmd.copied');
    setTimeout(()=>{if(hint.isConnected)hint.textContent=t('quickbar.cmd.hint')},2000);
  }
  $('#quickbar-input')?.focus({preventScroll:true});
  resetQuickBarHide();
}

function handleQuickBarKey(e){
  if(e.isComposing || e.keyCode===229) return;
  resetQuickBarHide();
  const results = state.quickBarResults;
  if(e.key==='Enter'){
    e.preventDefault();
    // 命令模式
    if(results.length===1 && results[0].type==='cmd'){
      quickBarGenerate(results[0].len);
      return;
    }
    // 搜索模式：复制后不关闭，让用户继续复制另一字段
    const p = results[state.quickBarIndex];
    if(p){
      const field = e.ctrlKey ? 'account' : 'password';
      const text = e.ctrlKey ? p.account : p.password;
      const label = e.ctrlKey ? t('vault.detail.account') : t('vault.detail.password');
      // 找到高亮项对应按钮，触发视觉反馈
      const item = $$('.qb-item')[state.quickBarIndex];
      const btn = item ? item.querySelector(`.qb-copy-btn[data-field="${field}"]`) : null;
      quickBarCopy(text, label, btn);
    }
  }else if(e.key==='ArrowDown'){
    e.preventDefault();
    state.quickBarIndex = Math.min(results.length-1,state.quickBarIndex+1);
    updateQuickBarHighlight();
  }else if(e.key==='ArrowUp'){
    e.preventDefault();
    state.quickBarIndex = Math.max(0,state.quickBarIndex-1);
    updateQuickBarHighlight();
  }else if(e.key==='Escape'){
    closeQuickBar();
  }
}

function updateQuickBarHighlight(){
  $$('.qb-item').forEach((el,i)=>el.classList.toggle('highlight',i===state.quickBarIndex));
}

/* ============================================================
   全局快捷键
   ============================================================ */
/* 热键字符串解析：'Alt+P' → {alt:true, ctrl:false, shift:false, main:'p'}
   主键统一转小写比较（KeyboardEvent.key 对字母区分大小写，'P' 与 'p' 需归一）
   Win 端 RegisterHotKey 用 MOD_ALT/MOD_CONTROL/MOD_SHIFT + VK code，解析逻辑同理 */
function parseHotkey(str){
  if(!str || typeof str!=='string') return null;
  const parts = str.split('+').map(s=>s.trim());
  const main = parts.pop();
  return {
    ctrl: parts.includes('Ctrl'),
    alt: parts.includes('Alt'),
    shift: parts.includes('Shift'),
    main: main.toLowerCase()
  };
}

/* 热键匹配：判断当前 keydown 事件是否命中 state.quickBarHotkey
   主键匹配规则：e.key 转小写 === parsed.main（字母/数字/符号统一）
   修饰键匹配：必须与配置完全一致（避免 Ctrl+P 误命中 Alt+P）*/
function matchHotkey(e, parsed){
  if(!parsed) return false;
  const mainMatch = (typeof e.key==='string') && e.key.toLowerCase()===parsed.main;
  if(!mainMatch) return false;
  return e.ctrlKey===parsed.ctrl && e.altKey===parsed.alt && e.shiftKey===parsed.shift;
}

/* 热键主键合法性校验：录制时只接受有意义的主键，拒绝单独按修饰键
   允许：字母 a-z / 数字 0-9 / F1-F12 / ` - = [ ] \ ; ' , . / Space Tab Enter Backspace */
function isHotkeyMainKey(key){
  if(!key || typeof key!=='string') return false;
  const k = key.toLowerCase();
  if(/^[a-z0-9]$/.test(k)) return true;            // 字母数字
  if(/^f([1-9]|1[0-2])$/.test(k)) return true;     // F1-F12
  return ['`','-','=','[',']','\\',';',"'",',','.','/',' ','tab','enter','backspace'].includes(k);
}

/* 格式化热键字符串为本地化显示：'Alt+P' → 'Alt + P'（更易读）
   仅显示用，存储仍用紧凑格式 */
function formatHotkeyDisplay(str){
  if(!str) return '';
  return str.split('+').map(s=>s.trim()).join(' + ');
}

/* 已知冲突热键表 —— 用于录制时检测冲突并警告用户
   来源：Windows 11 系统 + 1Password/KeePass/Bitwarden + 输入法 + QQ/微信/Snipaste
   ⚠️ 此表为静态参考，无法覆盖所有软件（用户可能装了其他全局热键软件），
   Win 端 RegisterHotKey 失败时也会提示"热键被占用"——双重保险 */
const HOTKEY_CONFLICTS = {
  // Windows 系统
  'Alt+Tab': 'Windows 任务切换',
  'Alt+F4': 'Windows 关闭窗口',
  'Alt+Space': 'Windows 窗口菜单',
  'Ctrl+Alt+Del': 'Windows 安全选项',
  'Win+L': 'Windows 锁屏',
  'Win+D': 'Windows 显示桌面',
  'Win+E': 'Windows 资源管理器',
  'Win+R': 'Windows 运行',
  'Win+S': 'Windows 搜索',
  'Win+V': 'Windows 剪贴板历史',
  'Win+Shift+S': 'Windows 截图',
  'Win+Space': 'Windows 输入法切换',
  'Win+Tab': 'Windows 任务视图',
  // 输入法
  'Ctrl+Space': '输入法中英切换（常见）',
  'Ctrl+Shift': '输入法切换（部分输入法）',
  // 1Password
  'Ctrl+Shift+Space': '1Password Quick Access',
  // KeePass
  'Ctrl+Alt+A': 'KeePass Auto-Type',
  // Bitwarden
  'Ctrl+Shift+L': 'Bitwarden 自动填充',
  'Ctrl+Shift+9': 'Bitwarden 生成密码',
  // QQ
  'Ctrl+Alt+A': 'QQ 截图',
  'Ctrl+Alt+Z': 'QQ 提取消息',
  'Ctrl+Alt+O': 'QQ 翻译',
  // 微信
  'Alt+A': '微信截图',
  // Snipaste
  'F1': 'Snipaste 截图',
  'F3': 'Snipaste 贴图',
};

/* 检测热键冲突：返回 {conflict: boolean, desc?: string} */
function checkHotkeyConflict(hotkey){
  if(!hotkey) return {conflict:false};
  const conflict = HOTKEY_CONFLICTS[hotkey];
  return conflict ? {conflict:true, desc:conflict} : {conflict:false};
}

/* 开始热键录制：切按钮为录制态，监听下一次按键
   - state.hotkeyRecording = 'recording' 让全局 keydown 监听器转入录制分支
   - 按钮文本变"按下组合键…(Esc 取消)"，加 .recording 类高亮 */
function startHotkeyRecording(){
  state.hotkeyRecording = 'recording';
  const btn = $('#quickbar-hotkey-btn');
  const display = $('#quickbar-hotkey-display');
  if(btn){
    btn.classList.add('recording');
    btn.textContent = t('settings.hotkey.recording');
  }
  if(display){
    display.classList.add('recording');
    display.textContent = t('settings.hotkey.recording');
  }
}

/* 取消录制：恢复按钮显示当前热键 */
function cancelHotkeyRecording(){
  state.hotkeyRecording = null;
  resetHotkeyDisplay();
}

/* 重置热键显示区为当前 state.quickBarHotkey */
function resetHotkeyDisplay(){
  const btn = $('#quickbar-hotkey-btn');
  const display = $('#quickbar-hotkey-display');
  const disp = formatHotkeyDisplay(state.quickBarHotkey);
  if(btn){
    btn.classList.remove('recording');
    btn.textContent = t('settings.hotkey.modify');
  }
  if(display){
    display.classList.remove('recording');
    display.textContent = disp;
  }
}

/* 录制时按键处理：
   - Esc → 取消录制
   - 仅修饰键（Ctrl/Alt/Shift/Win/Meta）单独按 → 忽略，等主键
   - 合法主键 → 组装 hotkey 字符串，冲突检测，保存
   - 不合法主键 → 提示并继续录制 */
function handleHotkeyRecordingKey(e){
  // Esc 取消
  if(e.key==='Escape'){
    e.preventDefault();
    cancelHotkeyRecording();
    showToast(t('settings.hotkey.canceled'),'info');
    return;
  }
  // 修饰键单独按下，忽略等待主键
  if(['Control','Alt','Shift','Meta','AltGraph'].includes(e.key)) return;

  e.preventDefault();

  // 主键合法性
  if(!isHotkeyMainKey(e.key)){
    showToast(t('settings.hotkey.invalid').replace('{key}', escapeHtml(e.key)),'warning');
    return; // 继续录制
  }

  // 至少需要一个修饰键（避免单字母键被注册为全局热键，会破坏正常打字）
  if(!e.ctrlKey && !e.altKey && !e.shiftKey && !e.metaKey){
    showToast(t('settings.hotkey.need_modifier'),'warning');
    return;
  }

  // 组装热键字符串（修饰键顺序固定：Ctrl+Alt+Shift+主键，便于比较）
  const parts = [];
  if(e.ctrlKey) parts.push('Ctrl');
  if(e.altKey) parts.push('Alt');
  if(e.shiftKey) parts.push('Shift');
  if(e.metaKey) parts.push('Win');
  // 主键归一：字母转大写显示，符号/功能键保留原值
  let mainKey = e.key;
  if(/^[a-z]$/.test(mainKey)) mainKey = mainKey.toUpperCase();
  else if(mainKey===' ') mainKey = 'Space';
  else mainKey = mainKey.charAt(0).toUpperCase() + mainKey.slice(1);
  parts.push(mainKey);
  const hotkey = parts.join('+');

  // 冲突检测
  const check = checkHotkeyConflict(hotkey);
  if(check.conflict){
    // 冲突时仍保存（用户可选择覆盖其他软件），但弹 warning 提示
    showToast(t('settings.hotkey.conflict').replace('{key}', formatHotkeyDisplay(hotkey)).replace('{app}', check.desc),'warning');
  } else {
    showToast(t('settings.hotkey.saved').replace('{key}', formatHotkeyDisplay(hotkey)),'success');
  }

  saveHotkey(hotkey);
}

/* 保存热键：更新 state + 同步顶栏按钮 title + 同步设置显示
   Win 端：写 settings.json + UnregisterHotKey(旧) + RegisterHotKey(新) */
function saveHotkey(hotkey){
  state.quickBarHotkey = hotkey;
  state.hotkeyRecording = null;
  // 同步顶栏按钮 title
  const btn = $('#topbar-quickbar-btn');
  if(btn){
    const title = t('topbar.button.quickbar').replace('{key}', formatHotkeyDisplay(hotkey));
    btn.setAttribute('title', title);
  }
  resetHotkeyDisplay();
}

if(!PDM_IS_M4_ISOLATED){
  document.addEventListener('keydown',e=>{
    if(e.isComposing || e.keyCode===229) return;
    // 录制模式优先：捕获任意键，不走 QuickBar 唤出逻辑
    if(state.hotkeyRecording==='recording'){
      handleHotkeyRecordingKey(e);
      return;
    }
    // QuickBar 全局热键：从 state 读取，支持用户自定义
    const parsed = parseHotkey(state.quickBarHotkey);
    if(parsed && matchHotkey(e, parsed)){
      e.preventDefault();
      if(state.quickBarVisible) closeQuickBar();
      else if(state.connected) openQuickBar();
    }
    if(e.key==='Escape' && state.quickBarVisible) closeQuickBar();
  });

  // Quick Bar 鼠标移动重置隐藏
  $('#quickbar-overlay').addEventListener('mousemove',resetQuickBarHide);
  $('#quickbar-timeout-slider').addEventListener(
    'input',
    event=>syncQuickBarAutohide(event.target.value),
  );
  $('#quickbar-timeout-num').addEventListener(
    'input',
    event=>syncQuickBarAutohide(event.target.value),
  );
  $('#quickbar-timeout-num').addEventListener(
    'blur',
    ()=>clampNumInput('quickbar-timeout-num',10,600),
  );
}

/* ============================================================
   窗口标题栏控制
   ============================================================ */
function windowMinimize(){
  const app = $('#main-app');
  if(app){
    app.style.transition='opacity .2s';
    app.style.opacity='0.2';
    setTimeout(()=>app.style.opacity='1',400);
  }
  showToast(t('toast.minimized'),'info');
}
function setWindowMaximizeControlState(maximized){
  const button = document.querySelector('[data-pdm-window-control="maximize"]');
  if(!button) return false;
  const isMaximized = Boolean(maximized);
  const key = isMaximized
    ? 'titlebar.button.restore'
    : 'titlebar.button.maximize';
  const label = t(key);
  button.setAttribute('data-pdm-window-state', isMaximized ? 'maximized' : 'normal');
  button.setAttribute('data-i18n-title', key);
  button.title = label;
  button.setAttribute('aria-label', label);
  return true;
}
function windowMaximize(){
  state.windowMaximized = !state.windowMaximized;
  setWindowMaximizeControlState(state.windowMaximized);
  showToast(state.windowMaximized?t('toast.maximized'):t('toast.restored'),'info');
}
function windowClose(){
  /* 产品决策：不再显示退出确认对话框。原型无法操作系统托盘或真正退出，
     因此只按“关闭按钮行为”的当前段控件给出对应模拟反馈。 */
  const minimize = $('#tray-close-segment button.active') === $('#tray-close-segment button:first-child');
  if(minimize) windowMinimize();
  else simulateWindowExit();
}
function simulateWindowExit(){
  closeModal();
  showToast(t('toast.exited'),'info');
}

/* ============================================================
   滑块+输入框联动
   ============================================================ */
/* 密码生成器长度联动 */
/* 生成器长度同步：滑块/数字框双向联动 + 标签数值更新。
   持久化策略：仅连接后写入 settings.json（generator.length），未连接时仅改内存/UI 不持久化。
   设计理由：未连接 = 未身份验证，但生成器是工具页入口功能，未连接时应完全可用（调整长度/字符集/生成/复制），
   只是配置修改不落盘，避免他人临时调整覆盖原主偏好。连接后用户调整才持久化。
   Win 端实现：if(state.connected) config.set('generator.length', v)。 */
function syncGenLength(val,fromInput){
  let v = parseInt(val);
  if(isNaN(v)) v = 20;
  v = Math.max(1,Math.min(1024,v));
  $('#gen-length').value = Math.min(128,v);
  $('#gen-length-num').value = v;
  $('#gen-length-val').textContent = v;
  /* Win 端：if(state.connected) config.set('generator.length', v); */
}
function clampGenLength(){
  const inp = $('#gen-length-num');
  let v = parseInt(inp.value);
  if(isNaN(v)||v<1) v=1;
  if(v>1024) v=1024;
  inp.value = v;
  syncGenLength(v);
}
/* 倒计时时长联动 */
function syncClipCountdown(val,fromInput){
  let v = parseInt(val);
  if(isNaN(v)) v = 30;
  v = Math.max(5,Math.min(60,v));
  $('#clip-slider').value = v;
  const numEl = $('#clip-num');
  if(fromInput){numEl.value = v}else{numEl.value = v}
}
/* 长期未更换阈值联动 */
function syncStaleThreshold(val,fromInput){
  let v = parseInt(val);
  if(isNaN(v)) v = 180;
  v = Math.max(30,Math.min(365,v));
  $('#stale-slider').value = v;
  $('#stale-num').value = v;
  // 阈值变化后刷新体检
  if(state.connected) renderSecurity();
}
/* 通用数字输入钳制 */
function clampNumInput(id,min,max){
  const inp = $('#'+id);
  let v = parseInt(inp.value);
  if(isNaN(v)||v<min) v=min;
  if(v>max) v=max;
  inp.value = v;
  if(id==='clip-num') syncClipCountdown(v);
  if(id==='stale-num') syncStaleThreshold(v);
  if(id==='quickbar-timeout-num') syncQuickBarAutohide(v);
}

/* ============================================================
   一键生成密码填入（列表/分屏详情）
   ============================================================ */
function regeneratePassword(id){
  const p = passwords.find(x=>x.id===id);
  if(!p) return;
  // 改为打开编辑对话框并预填新密码（用户可保存或取消，避免直接修改无确认）
  openEditPasswordDialog(id);
  fillModalGeneratedPassword('mf-password');
}

/* 强度评估（用于密码记录的 strength 标签：添加/编辑/生成保存时调用）
   直接复用 evaluateStrength 核心算法，保证检测页评级与列表标签一致
   传入 platform/account 用于 user_inputs 上下文匹配（如 Taobao2024! 在淘宝平台上下文下判弱） */
function evalStrength(pw, platform='', account=''){
  if(!pw) return 'weak';
  return evaluateStrength(pw, platform, account).rating;
}

/* ============================================================
   模态对话框系统
   ============================================================ */
function openModal(html,opts={}){
  closeModal();
  const returnFocus = document.activeElement;
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.id = 'active-modal';
  const modal = document.createElement('div');
  modal.className = 'modal'+(opts.wide?' wide':'');
  modal.innerHTML = html;
  overlay.appendChild(modal);
  // 点击遮罩关闭（除关闭确认等关键对话框）
  if(opts.closeOnBackdrop!==false){
    let backdropPointerId = null;
    let backdropPressStarted = false;
    let backdropReleaseEnded = false;
    const resetBackdropPointer = ()=>{
      backdropPointerId = null;
      backdropPressStarted = false;
      backdropReleaseEnded = false;
    };
    overlay.addEventListener('pointerdown',e=>{
      backdropPointerId = e.pointerId;
      backdropPressStarted = (
        e.isPrimary
        && e.button===0
        && e.target===overlay
      );
      backdropReleaseEnded = false;
    });
    overlay.addEventListener('pointerup',e=>{
      if(e.pointerId!==backdropPointerId) return;
      backdropReleaseEnded = backdropPressStarted && e.target===overlay;
    });
    overlay.addEventListener('pointercancel',e=>{
      if(e.pointerId===backdropPointerId) resetBackdropPointer();
    });
    overlay.addEventListener('click',e=>{
      const shouldClose = (
        e.target===overlay
        && backdropPressStarted
        && backdropReleaseEnded
      );
      resetBackdropPointer();
      if(shouldClose) closeModal();
    });
  }
  overlay._keyHandler = e=>{
    if(e.isComposing || e.keyCode===229) return;
    if(e.key==='Tab'){
      const focusable = Array.from(modal.querySelectorAll(
        'button:not(:disabled),input:not(:disabled),textarea:not(:disabled),'
        +'select:not(:disabled),[tabindex]:not([tabindex="-1"])'
      )).filter(element=>element.getClientRects().length>0);
      if(focusable.length){
        const first = focusable[0];
        const last = focusable[focusable.length-1];
        if(e.shiftKey && (document.activeElement===first || !modal.contains(document.activeElement))){
          last.focus();e.preventDefault();return;
        }
        if(!e.shiftKey && (document.activeElement===last || !modal.contains(document.activeElement))){
          first.focus();e.preventDefault();return;
        }
      }
    }
    if(e.key==='Escape'){
      closeModal();e.preventDefault();return;
    }
    if(e.key!=='Enter') return;
    const target = e.target;
    if(target instanceof HTMLTextAreaElement) return;
    if(target instanceof HTMLButtonElement){
      if(!target.disabled) target.click();
      e.preventDefault();return;
    }
    if(target instanceof HTMLInputElement){
      const primary = modal.querySelector('.modal-footer .btn-primary:not(:disabled)');
      if(primary) primary.click();
      e.preventDefault();
    }
  };
  document.addEventListener('keydown',overlay._keyHandler);
  overlay._returnFocus = returnFocus;
  document.getElementById('canvas-frame').appendChild(overlay);
  window.renderUpdates?.();
  syncOpenModalAccessibility(overlay);
  // 自动聚焦第一个输入框
  overlay._focusTimer = setTimeout(()=>{
    overlay._focusTimer = 0;
    const first = opts.initialFocusSelector
      ? modal.querySelector(opts.initialFocusSelector)
      : modal.querySelector('input:not([type=checkbox]),textarea');
    if(first && overlay.isConnected) first.focus();
  },100);
  return overlay;
}

function syncOpenModalAccessibility(overlay=$('#active-modal')){
  const modal=overlay?.querySelector('.modal');
  if(!modal) return;
  modal.setAttribute('role','dialog');
  modal.setAttribute('aria-modal','true');
  const title=modal.querySelector('.modal-title');
  if(title){
    if(!title.id) title.id='active-modal-title';
    modal.setAttribute('aria-labelledby',title.id);
  }
  const close=modal.querySelector('.modal-close');
  if(close){
    const label=t('dialog.button.close');
    close.setAttribute('aria-label',label);
    close.title=label;
  }
  modal.querySelectorAll('.modal-field-label').forEach((label,index)=>{
    const field=label.closest('.modal-field');
    const control=field?.querySelector('input,textarea,select');
    if(!control) return;
    if(!control.id) control.id=`active-modal-field-${index}`;
    if(!label.id) label.id=`${control.id}-label`;
    label.htmlFor=control.id;
    field.setAttribute('role','group');
    field.setAttribute('aria-labelledby',label.id);
  });
  modal.querySelectorAll('.modal-field-error,.modal-form-error,.note-form-feedback').forEach(error=>{
    error.setAttribute('role','status');
    error.setAttribute('aria-live','polite');
    error.setAttribute('aria-atomic','true');
  });
  modal.querySelectorAll(
    '[data-pdm-onclick^="toggleModalPwVisibility"],'
    +'[data-pdm-backup-action="toggle-password"]'
  ).forEach(button=>{
    const input=button.closest('.password-field-wrap')?.querySelector('input');
    if(input instanceof HTMLInputElement) syncModalPasswordAccessibility(input,button);
  });
  modal.querySelectorAll('[data-pdm-onclick^="fillModalGeneratedPassword"]').forEach(button=>{
    const label=t('dialog.generate');
    button.setAttribute('aria-label',label);
    button.title=label;
  });
  modal.querySelectorAll('.modal-fav-toggle').forEach(button=>
    button.setAttribute('aria-pressed',String(button.classList.contains('active'))));
}
function closeModal(){
  const m = $('#active-modal');
  if(m){
    if(m.dataset.pdmBackupLayout==='true'){
      IE_STATE.picker?.dispose(); IE_STATE.picker=null; IE_STATE.exportSelection=[];
    }
    const returnToTransfer = m.dataset.ieTransfer === 'true';
    const returnFocus = m._returnFocus;
    if(m._focusTimer){clearTimeout(m._focusTimer);m._focusTimer=0}
    if(m._keyHandler) document.removeEventListener('keydown',m._keyHandler);
    m.remove();
    if(returnToTransfer){
      clearIEDemoReads(); IE_STATE.conflicts=[]; IE_STATE.previewReady=false; IE_STATE.sourceKind='FILE';
      queueMicrotask(()=>window.PdmTransferDemo?.open());
    }
    if(returnFocus && document.contains(returnFocus) && typeof returnFocus.focus==='function'){
      returnFocus.focus({preventScroll:true});
    }
  }
  window.renderUpdates?.();
}

/* 模态框密码可见性切换 */
function toggleModalPwVisibility(inputId,btn){
  const input = $('#'+inputId);
  if(!input) return;
  if(input.type==='password'){input.type='text';btn.innerHTML=svgIcon('eye-closed',16)}else{input.type='password';btn.innerHTML=svgIcon('eye',16)}
  syncModalPasswordAccessibility(input,btn);
}
function syncModalPasswordAccessibility(input,btn){
  const visible=input.type==='text';
  const label=t(visible?'common.password.hide':'common.password.show');
  btn.setAttribute('aria-label',label);
  btn.setAttribute('aria-pressed',String(visible));
  btn.title=label;
}
/* 模态框一键生成密码填入 */
function fillModalGeneratedPassword(inputId){
  const input = $('#'+inputId);
  if(!input) return;
  const policy=generatorPolicy();
  const error=generatorPolicyError(policy);
  if(error){
    showToast(t(error),'error');
    return;
  }
  const pw=generatePasswordValue(policy);
  const inputType = input.type;
  input.value = pw;
  input.type = inputType;
  // 同步眼睛按钮
  const wrap = input.closest('.password-field-wrap');
  if(wrap){
    const eyeBtn = wrap.querySelector('.pw-action-btn');
    if(eyeBtn){
      eyeBtn.innerHTML = svgIcon(input.type==='text'?'eye-closed':'eye',16);
      syncModalPasswordAccessibility(input,eyeBtn);
    }
  }
  showToast(t('toast.gen.generatedNew'),'success');
}

/* ---------- 新增密码记录对话框 ---------- */
function openAddPasswordDialog(presetPassword){
  const html = `
    <div class="modal-header">
      <div class="modal-title" data-i18n="dialog.pwd.title.add">${t('dialog.pwd.title.add')}</div>
      <button class="modal-close" data-pdm-onclick="closeModal()">✕</button>
    </div>
    <div class="modal-body">
      <div class="modal-field modal-field-inline-error">
        <label class="modal-field-label"><span data-i18n="dialog.pwd.label.platform">${t('dialog.pwd.label.platform')}</span> <span class="required">*</span></label>
        <input type="text" class="modal-field-input" id="mf-platform" placeholder="${t('dialog.pwd.placeholder.platform')}" data-i18n-placeholder="dialog.pwd.placeholder.platform" data-pdm-oninput="clearFieldError('mf-platform')">
        <div class="modal-field-error" id="mf-platform-err"></div>
      </div>
      <div class="modal-field">
        <label class="modal-field-label" data-i18n="dialog.pwd.label.account">${t('dialog.pwd.label.account')}</label>
        <input type="text" class="modal-field-input" id="mf-account" placeholder="${t('dialog.pwd.placeholder.account')}" data-i18n-placeholder="dialog.pwd.placeholder.account">
      </div>
      <div class="modal-field">
        <label class="modal-field-label" data-i18n="dialog.pwd.label.password">${t('dialog.pwd.label.password')}</label>
        <div class="modal-field-row">
          <div class="password-field-wrap">
            <input type="password" class="modal-field-input" id="mf-password" placeholder="${t('dialog.pwd.placeholder.password')}" data-i18n-placeholder="dialog.pwd.placeholder.password">
            <div class="pw-actions">
              <button type="button" class="pw-action-btn" data-pdm-onclick="toggleModalPwVisibility('mf-password',this)" title="${t('dialog.toggle.visible')}"><svg class="svg-fill" width="16" height="16" viewBox="0 0 256 256" aria-hidden="true"><path d="M247.31,124.76c-.35-.79-8.82-19.58-27.65-38.41C194.57,61.26,162.88,48,128,48S61.43,61.26,36.34,86.35C17.51,105.18,9,124,8.69,124.76a8,8,0,0,0,0,6.5c.35.79,8.82,19.57,27.65,38.4C61.43,194.74,93.12,208,128,208s66.57-13.26,91.66-38.34c18.83-18.83,27.3-37.61,27.65-38.4A8,8,0,0,0,247.31,124.76ZM128,168a40,40,0,1,1,40-40A40,40,0,0,1,128,168Z"/></svg></button>
              <button type="button" class="pw-action-btn" data-pdm-onclick="fillModalGeneratedPassword('mf-password')" title="${t('dialog.generate')}"><svg class="svg-fill" width="16" height="16" viewBox="0 0 256 256" aria-hidden="true"><path d="M192,32H64A32,32,0,0,0,32,64V192a32,32,0,0,0,32,32H192a32,32,0,0,0,32-32V64A32,32,0,0,0,192,32ZM92,176a12,12,0,1,1,12-12A12,12,0,0,1,92,176Zm0-72a12,12,0,1,1,12-12A12,12,0,0,1,92,104Zm36,36a12,12,0,1,1,12-12A12,12,0,0,1,128,140Zm36,36a12,12,0,1,1,12-12A12,12,0,0,1,164,176Zm0-72a12,12,0,1,1,12-12A12,12,0,0,1,164,104Z"/></svg></button>
            </div>
          </div>
        </div>
      </div>
      <div class="modal-field">
        <label class="modal-field-label" data-i18n="dialog.pwd.label.notes">${t('dialog.pwd.label.notes')}</label>
        <textarea class="modal-field-input" id="mf-notes" placeholder="${t('dialog.pwd.placeholder.notes')}" data-i18n-placeholder="dialog.pwd.placeholder.notes"></textarea>
      </div>
      <div class="modal-field">
        <label class="modal-field-label" data-i18n="dialog.pwd.label.totp">${t('dialog.pwd.label.totp')}</label>
        <input type="text" class="modal-field-input pdm-inline-82cece3ff4" id="mf-totp" placeholder="${t('dialog.pwd.placeholder.totp')}" data-i18n-placeholder="dialog.pwd.placeholder.totp">
        <div class="modal-field-error" id="mf-totp-err" aria-hidden="true"></div>
      </div>
      <div class="modal-field editor-recovery">
        <label class="modal-field-label" for="mf-recovery">${t('dialog.pwd.label.recovery')}</label>
        <textarea class="modal-field-input" id="mf-recovery" rows="3" autocomplete="off" spellcheck="false" aria-describedby="mf-recovery-hint"></textarea>
        <div class="modal-field-hint" id="mf-recovery-hint">${t('dialog.pwd.recovery.empty')}</div>
      </div>
      <div class="modal-form-error" id="mf-save-err" aria-hidden="true"></div>
    </div>
    <div class="modal-footer">
      <button type="button" class="modal-fav-toggle" id="mf-favorite" data-pdm-onclick="toggleModalFav(this)"><svg class="svg-fill" width="15" height="15" viewBox="0 0 256 256" aria-hidden="true"><path d="M234.29,114.85l-45,38.83L203,211.75a16.4,16.4,0,0,1-24.5,17.82L128,198.49,77.47,229.57A16.4,16.4,0,0,1,53,211.75l13.76-58.07-45-38.83A16.46,16.46,0,0,1,31.08,86l59-4.76,22.76-55.08a16.36,16.36,0,0,1,30.27,0l22.75,55.08,59,4.76a16.46,16.46,0,0,1,9.37,28.86Z"/></svg><span data-i18n="dialog.label.favorite">${t('dialog.label.favorite')}</span></button>
      <div class="modal-footer-right">
        <button class="btn btn-sm" data-pdm-onclick="closeModal()" data-i18n="dialog.button.cancel">${t('dialog.button.cancel')}</button>
        <button class="btn btn-primary btn-sm" id="mf-save" data-pdm-onclick="saveNewPassword()" data-i18n="dialog.button.save">${t('dialog.button.save')}</button>
      </div>
    </div>
  `;
  openModal(html);
  const modal = $('#active-modal');
  if(modal) modal.dataset.pdmM4Create = 'true';
  // 预填密码（来自生成器"保存为记录"按钮）
  if(presetPassword){
    const pwInput = $('#mf-password');
    if(pwInput){pwInput.value = presetPassword;}
  }
}

function clearFieldError(id){
  const err = $('#'+id+'-err');
  if(err) err.classList.remove('show');
}

function parseDemoRecovery(text){
  if([...text].length>8192||new TextEncoder().encode(text).length>32768) return null;
  const codes=[],seen=new Set();
  for(const line of text.split(/\r?\n/)){
    const value=line.trim();
    if(!value) continue;
    if(/[\u0000-\u001f\u007f]/.test(value)||[...value].length>1024||
       new TextEncoder().encode(value).length>4096||seen.has(value)||codes.length>=128) return null;
    seen.add(value); codes.push({value,used:false});
  }
  return codes;
}

function saveNewPassword(){
  const platform = $('#mf-platform').value.trim();
  const account = $('#mf-account').value.trim();
  const password = $('#mf-password').value;
  const notes = $('#mf-notes').value.trim();
  const totp_secret = $('#mf-totp').value.trim() || null;
  const recovery_codes=parseDemoRecovery($('#mf-recovery').value);
  if(!recovery_codes){$('#mf-save-err').textContent=t('dialog.pwd.recovery.invalid');$('#mf-recovery').focus();return}
  const is_favorite = $('#mf-favorite').classList.contains('active');
  if(!platform){
    const err = $('#mf-platform-err');
    err.textContent = t('dialog.pwd.error.platformEmpty');
    err.classList.add('show');
    $('#mf-platform').focus();
    return;
  }
  if(passwords.some(p=>p.platform.toLowerCase()===platform.toLowerCase())){
    const err = $('#mf-platform-err');
    err.textContent = t('dialog.pwd.error.platformExists');
    err.classList.add('show');
    $('#mf-platform').focus();
    return;
  }
  const newId = Math.max(0,...passwords.map(p=>p.id))+1;
  const todayStr = new Date().toISOString().slice(0,10);
  passwords.unshift({
    id:newId,platform,account,password,notes,totp_secret,recovery_codes,
    updated_at:todayStr,
    password_changed_at:todayStr,
    strength:evalStrength(password||''),is_favorite
  });
  closeModal();
  renderVault();
  renderSecurity();
  showToast(t('toast.pwd.added'),'success');
}

/* ---------- 编辑密码记录对话框 ---------- */
function openEditPasswordDialog(id){
  const p = passwords.find(x=>x.id===id);
  if(!p){showToast(t('toast.notFound'),'error');return}
  // 检测是否处于引导修复流程中（当前 issue 正是该 id）
  const inFixFlow = !!(state.fixQueue && state.fixQueue[state.fixIndex] && state.fixQueue[state.fixIndex].id===id);
  const skipBtnHtml = inFixFlow
    ? `<button class="btn btn-sm" data-pdm-onclick="skipCurrentInDialog()">${t('fix.button.skipThis')}</button>`
    : '';
  const html = `
    <div class="modal-header">
      <div class="modal-title"><svg class="svg-fill" width="18" height="18" viewBox="0 0 256 256" aria-hidden="true"><path d="M227.31,73.37,182.63,28.68a16,16,0,0,0-22.63,0L36.69,152A15.86,15.86,0,0,0,32,163.31V208a16,16,0,0,0,16,16H92.69A15.86,15.86,0,0,0,104,219.31L227.31,96a16,16,0,0,0,0-22.63ZM51.31,160l90.35-90.35,16.68,16.69L68,176.68ZM48,179.31,76.69,208H48Zm48,25.38L79.31,188l90.35-90.35h0l16.68,16.69Z"/></svg> ${t('dialog.pwd.title.edit')}</div>
      <button class="modal-close" data-pdm-onclick="closeModal()">✕</button>
    </div>
    <div class="modal-body">
      <div class="modal-field modal-field-inline-error">
        <label class="modal-field-label">${t('dialog.pwd.label.platform')} <span class="required">*</span></label>
        <input type="text" class="modal-field-input" id="mf-platform" value="${escapeHtml(p.platform)}" data-pdm-oninput="clearFieldError('mf-platform')">
        <div class="modal-field-error" id="mf-platform-err"></div>
      </div>
      <div class="modal-field">
        <label class="modal-field-label">${t('dialog.pwd.label.account')}</label>
        <input type="text" class="modal-field-input" id="mf-account" value="${escapeHtml(p.account)}">
      </div>
      <div class="modal-field">
        <label class="modal-field-label">${t('dialog.pwd.label.password')}</label>
        <div class="modal-field-row">
          <div class="password-field-wrap">
            <input type="password" class="modal-field-input" id="mf-password" value="${escapeHtml(p.password)}">
            <div class="pw-actions">
              <button type="button" class="pw-action-btn" data-pdm-onclick="toggleModalPwVisibility('mf-password',this)" title="${t('dialog.toggle.visible')}"><svg class="svg-fill" width="16" height="16" viewBox="0 0 256 256" aria-hidden="true"><path d="M247.31,124.76c-.35-.79-8.82-19.58-27.65-38.41C194.57,61.26,162.88,48,128,48S61.43,61.26,36.34,86.35C17.51,105.18,9,124,8.69,124.76a8,8,0,0,0,0,6.5c.35.79,8.82,19.57,27.65,38.4C61.43,194.74,93.12,208,128,208s66.57-13.26,91.66-38.34c18.83-18.83,27.3-37.61,27.65-38.4A8,8,0,0,0,247.31,124.76ZM128,168a40,40,0,1,1,40-40A40,40,0,0,1,128,168Z"/></svg></button>
              <button type="button" class="pw-action-btn" data-pdm-onclick="fillModalGeneratedPassword('mf-password')" title="${t('dialog.generate')}"><svg class="svg-fill" width="16" height="16" viewBox="0 0 256 256" aria-hidden="true"><path d="M192,32H64A32,32,0,0,0,32,64V192a32,32,0,0,0,32,32H192a32,32,0,0,0,32-32V64A32,32,0,0,0,192,32ZM92,176a12,12,0,1,1,12-12A12,12,0,0,1,92,176Zm0-72a12,12,0,1,1,12-12A12,12,0,0,1,92,104Zm36,36a12,12,0,1,1,12-12A12,12,0,0,1,128,140Zm36,36a12,12,0,1,1,12-12A12,12,0,0,1,164,176Zm0-72a12,12,0,1,1,12-12A12,12,0,0,1,164,104Z"/></svg></button>
            </div>
          </div>
        </div>
      </div>
      <div class="modal-field">
        <label class="modal-field-label">${t('dialog.pwd.label.notes')}</label>
        <textarea class="modal-field-input" id="mf-notes">${escapeHtml(p.notes)}</textarea>
      </div>
      <div class="modal-field">
        <label class="modal-field-label">${t('dialog.pwd.label.totp')}</label>
        <input type="text" class="modal-field-input pdm-inline-82cece3ff4" id="mf-totp" data-pdm-totp-action="KEEP" placeholder="${t('dialog.pwd.placeholder.totpReplace')}">
        <div class="modal-field-error" id="mf-totp-err" aria-hidden="true"></div>
        <div class="modal-field-hint" id="mf-totp-hint">${t(p.totp_secret?'dialog.pwd.totp.enabledHint':'dialog.pwd.totp.disabledHint')}</div>
        ${p.totp_secret?`<button type="button" class="modal-inline-action" id="mf-totp-remove" data-pdm-onclick="togglePrototypeEditTotpRemoval()">${t('dialog.pwd.totp.remove')}</button>`:''}
      </div>
      <div class="modal-field editor-recovery">
        <label class="modal-field-label" for="mf-recovery">${t('dialog.pwd.label.recovery')}</label>
        <textarea class="modal-field-input" id="mf-recovery" rows="3" autocomplete="off" spellcheck="false" data-pdm-recovery-action="KEEP" aria-describedby="mf-recovery-hint" data-pdm-oninput="syncDemoRecoveryEdit()"></textarea>
        <div class="modal-field-hint" id="mf-recovery-hint">${(p.recovery_codes?.length?t('dialog.pwd.recovery.keep').replace('{n}',String(p.recovery_codes.length)):t('dialog.pwd.recovery.empty'))}</div>
        ${p.recovery_codes?.length?`<button type="button" class="modal-inline-action" id="mf-recovery-remove" data-pdm-onclick="toggleDemoRecoveryRemoval()">${t('dialog.pwd.recovery.remove')}</button>`:''}
        <div class="modal-field-hint" id="mf-recovery-confirm" hidden>
          ${t('dialog.pwd.recovery.confirm')}
          <button type="button" class="btn btn-sm" data-pdm-onclick="saveEditPassword(${id},true)">${t('dialog.button.save')}</button>
          <button type="button" class="btn btn-sm" data-pdm-onclick="hideDemoRecoveryConfirm()">${t('dialog.button.cancel')}</button>
        </div>
      </div>
      <div class="modal-form-error" id="mf-save-err" aria-hidden="true"></div>
      <div class="modal-edit-actions" id="mf-edit-actions" hidden>
        <button type="button" class="btn btn-sm" id="mf-edit-reload" hidden>${t('dialog.pwd.action.reloadLatest')}</button>
        <button type="button" class="btn btn-sm" id="mf-edit-retry" hidden>${t('dialog.pwd.action.retryAuthorization')}</button>
      </div>
    </div>
    <div class="modal-footer">
      <button type="button" class="modal-fav-toggle ${p.is_favorite?'active':''}" id="mf-favorite" data-pdm-onclick="toggleModalFav(this)"><svg class="svg-fill" width="15" height="15" viewBox="0 0 256 256" aria-hidden="true"><path d="M234.29,114.85l-45,38.83L203,211.75a16.4,16.4,0,0,1-24.5,17.82L128,198.49,77.47,229.57A16.4,16.4,0,0,1,53,211.75l13.76-58.07-45-38.83A16.46,16.46,0,0,1,31.08,86l59-4.76,22.76-55.08a16.36,16.36,0,0,1,30.27,0l22.75,55.08,59,4.76a16.46,16.46,0,0,1,9.37,28.86Z"/></svg><span data-i18n="dialog.label.favorite">${t('dialog.label.favorite')}</span></button>
      <div class="modal-footer-right">
        ${skipBtnHtml}
        <button class="btn btn-sm" data-pdm-onclick="closeModal()">${t('dialog.button.cancel')}</button>
        <button class="btn btn-primary btn-sm" id="mf-save" data-pdm-onclick="saveEditPassword(${id})">${t('dialog.button.save')}</button>
      </div>
    </div>
  `;
  openModal(html);
  const modal = $('#active-modal');
  if(modal) modal.dataset.pdmM4Edit = 'true';
}

function togglePrototypeEditTotpRemoval(){
  const input = $('#mf-totp');
  const hint = $('#mf-totp-hint');
  const button = $('#mf-totp-remove');
  if(!input || !button) return;
  const removing = input.dataset.pdmTotpAction !== 'CLEAR';
  input.dataset.pdmTotpAction = removing ? 'CLEAR' : 'KEEP';
  if(removing) input.value = '';
  button.textContent = t(removing?'dialog.pwd.totp.undoRemove':'dialog.pwd.totp.remove');
  if(hint) hint.textContent = t(removing?'dialog.pwd.totp.removeHint':'dialog.pwd.totp.enabledHint');
}

function syncDemoRecoveryEdit(){
  const input=$('#mf-recovery');
  if(!input) return;
  input.dataset.pdmRecoveryAction=input.value.trim()?'REPLACE':'KEEP';
  const confirm=$('#mf-recovery-confirm');
  if(confirm) confirm.hidden=true;
}
function hideDemoRecoveryConfirm(){
  const confirm=$('#mf-recovery-confirm');
  if(confirm) confirm.hidden=true;
}
function toggleDemoRecoveryRemoval(){
  const input=$('#mf-recovery'),button=$('#mf-recovery-remove');
  if(!input||!button) return;
  const remove=input.dataset.pdmRecoveryAction!=='CLEAR';
  input.value='';
  input.dataset.pdmRecoveryAction=remove?'CLEAR':'KEEP';
  button.textContent=t(remove?'dialog.pwd.recovery.undo':'dialog.pwd.recovery.remove');
  const confirm=$('#mf-recovery-confirm');
  if(confirm) confirm.hidden=true;
}

function saveEditPassword(id,recoveryConfirmed=false){
  const p = passwords.find(x=>x.id===id);
  if(!p){closeModal();return}
  const platform = $('#mf-platform').value.trim();
  const account = $('#mf-account').value.trim();
  const password = $('#mf-password').value;
  const notes = $('#mf-notes').value.trim();
  const totpInput = $('#mf-totp');
  const totpReplacement = totpInput.value.trim();
  const totp_secret = totpReplacement
    ? totpReplacement
    : (totpInput.dataset.pdmTotpAction==='CLEAR' ? null : p.totp_secret);
  const recoveryInput=$('#mf-recovery');
  const recoveryAction=recoveryInput.value.trim()?'REPLACE':recoveryInput.dataset.pdmRecoveryAction;
  const recoveryCodes=recoveryAction==='REPLACE'?parseDemoRecovery(recoveryInput.value):
    recoveryAction==='CLEAR'?[]:p.recovery_codes;
  if(!recoveryCodes){$('#mf-save-err').textContent=t('dialog.pwd.recovery.invalid');recoveryInput.focus();return}
  if(p.recovery_codes?.length&&recoveryAction!=='KEEP'&&!recoveryConfirmed){
    $('#mf-recovery-confirm').hidden=false;
    $('#mf-recovery-confirm button').focus();
    return;
  }
  const is_favorite = $('#mf-favorite').classList.contains('active');
  if(!platform){
    const err = $('#mf-platform-err');
    err.textContent = t('dialog.pwd.error.platformEmpty');
    err.classList.add('show');
    $('#mf-platform').focus();
    return;
  }
  if(passwords.some(x=>x.id!==id && x.platform.toLowerCase()===platform.toLowerCase())){
    const err = $('#mf-platform-err');
    err.textContent = t('dialog.pwd.error.platformExists');
    err.classList.add('show');
    $('#mf-platform').focus();
    return;
  }
  // 检测密码本身是否变化：只有密码字段变更才刷新 password_changed_at
  const passwordChanged = password !== p.password;
  p.platform = platform;
  p.account = account;
  p.password = password;
  p.notes = notes;
  p.totp_secret = totp_secret;
  p.recovery_codes = recoveryCodes;
  p.is_favorite = is_favorite;
  p.strength = evalStrength(password||'',platform,account);
  const todayStr = new Date().toISOString().slice(0,10);
  p.updated_at = todayStr;
  if(passwordChanged) p.password_changed_at = todayStr;
  closeModal();
  renderVault();
  renderSecurity();
  showToast(t('toast.pwd.updated'),'success');
  // 触发引导修复进度检查
  onPasswordSaved(id);
}

/* ---------- 新增记事对话框 ---------- */
function openAddNoteDialog(){
  if(!canLeaveNotesCardEdit()) return;
  const html = `
    <div class="modal-header">
      <div class="modal-title" data-i18n="dialog.note.title.add">${t('dialog.note.title.add')}</div>
      <button class="modal-close" data-pdm-onclick="closeModal()">✕</button>
    </div>
    <div class="modal-body">
      <div class="modal-field">
        <label class="modal-field-label"><span data-i18n="dialog.note.label.title">${t('dialog.note.label.title')}</span> <span class="required">*</span></label>
        <input type="text" class="modal-field-input" id="nf-title" placeholder="${t('dialog.note.placeholder.title')}" data-i18n-placeholder="dialog.note.placeholder.title" data-pdm-oninput="clearFieldError('nf-title')">
        <div class="modal-field-error" id="nf-title-err"></div>
      </div>
      <div class="modal-field">
        <label class="modal-field-label" data-i18n="dialog.note.label.content">${t('dialog.note.label.content')}</label>
        <div class="text-scroll-wrap">
          <textarea class="modal-field-input pdm-inline-c16b16dade" id="nf-content" placeholder="${t('dialog.note.placeholder.content')}" data-i18n-placeholder="dialog.note.placeholder.content" data-pdm-oninput="updateLongTextHint(this,'nf-content-scroll-hint')" data-pdm-onscroll="updateLongTextHint(this,'nf-content-scroll-hint')"></textarea>
          <div class="text-scroll-hint" id="nf-content-scroll-hint"><span class="text-scroll-message"></span><span class="text-scroll-position"></span></div>
        </div>
      </div>
    </div>
    <div class="modal-footer">
      <button type="button" class="modal-fav-toggle" id="nf-favorite" data-pdm-onclick="toggleModalFav(this)"><svg class="svg-fill" width="15" height="15" viewBox="0 0 256 256" aria-hidden="true"><path d="M234.29,114.85l-45,38.83L203,211.75a16.4,16.4,0,0,1-24.5,17.82L128,198.49,77.47,229.57A16.4,16.4,0,0,1,53,211.75l13.76-58.07-45-38.83A16.46,16.46,0,0,1,31.08,86l59-4.76,22.76-55.08a16.36,16.36,0,0,1,30.27,0l22.75,55.08,59,4.76a16.46,16.46,0,0,1,9.37,28.86Z"/></svg><span data-i18n="dialog.label.favorite">${t('dialog.label.favorite')}</span></button>
      <div class="modal-footer-right">
        <button class="btn btn-sm" data-pdm-onclick="closeModal()" data-i18n="dialog.button.cancel">${t('dialog.button.cancel')}</button>
        <button class="btn btn-primary btn-sm" data-pdm-onclick="saveNewNote()" data-i18n="dialog.button.save">${t('dialog.button.save')}</button>
      </div>
    </div>
  `;
  openModal(html,{wide:true});
  requestAnimationFrame(()=>updateLongTextHint($('#nf-content'),'nf-content-scroll-hint'));
}

function saveNewNote(){
  const title = $('#nf-title').value.trim();
  const content = $('#nf-content').value;
  const is_favorite = $('#nf-favorite').classList.contains('active');
  if(!title){
    const err = $('#nf-title-err');
    err.textContent = t('dialog.note.error.titleEmpty');
    err.classList.add('show');
    $('#nf-title').focus();
    return;
  }
  const newId = Math.max(0,...notes.map(n=>n.id))+1;
  notes.push({
    id:newId,title,content,
    updated_at:new Date().toISOString().slice(0,10),
    is_favorite
  });
  closeModal();
  renderNotes();
  showToast(t('toast.note.dialogAdded'),'success');
}

/* ---------- 修改数据库密码对话框 ---------- */
function openChangeDbPasswordDialog(){
  const html = `
    <div class="modal-header">
      <div class="modal-title"><svg class="svg-fill" width="18" height="18" viewBox="0 0 256 256" aria-hidden="true"><path d="M216.57,39.43A80,80,0,0,0,83.91,120.78L28.69,176A15.86,15.86,0,0,0,24,187.31V216a16,16,0,0,0,16,16H72a8,8,0,0,0,8-8V208H96a8,8,0,0,0,8-8V184h16a8,8,0,0,0,5.66-2.34l9.56-9.57A79.73,79.73,0,0,0,160,176h.1A80,80,0,0,0,216.57,39.43ZM180,92a16,16,0,1,1,16-16A16,16,0,0,1,180,92Z"/></svg> <span data-i18n="dialog.key.title">${t('dialog.key.title')}</span></div>
      <button class="modal-close" data-pdm-onclick="closeModal()">✕</button>
    </div>
    <div class="modal-body">
      <div class="pdm-inline-91b4c5df13" data-i18n="dialog.key.warning">
        ${t('dialog.key.warning')}
      </div>
      <div class="modal-field">
        <label class="modal-field-label" data-i18n="dialog.key.label.current">${t('dialog.key.label.current')}</label>
        <input type="password" class="modal-field-input" id="kf-current" placeholder="${t('dialog.key.placeholder.current')}" data-i18n-placeholder="dialog.key.placeholder.current" data-pdm-oninput="clearDbKeyErrors()">
        <div class="modal-field-error" id="kf-current-err"></div>
      </div>
      <div class="modal-field">
        <label class="modal-field-label" data-i18n="dialog.key.label.new">${t('dialog.key.label.new')}</label>
        <div class="password-field-wrap">
          <input type="password" class="modal-field-input" id="kf-new" placeholder="${t('dialog.key.placeholder.new')}" data-i18n-placeholder="dialog.key.placeholder.new" data-pdm-oninput="checkDbPasswordMatch();clearDbKeyErrors()">
          <div class="pw-actions">
            <button type="button" class="pw-action-btn" data-pdm-onclick="toggleModalPwVisibility('kf-new',this)" title="${t('dialog.toggle.visible')}"><svg class="svg-fill" width="16" height="16" viewBox="0 0 256 256" aria-hidden="true"><path d="M247.31,124.76c-.35-.79-8.82-19.58-27.65-38.41C194.57,61.26,162.88,48,128,48S61.43,61.26,36.34,86.35C17.51,105.18,9,124,8.69,124.76a8,8,0,0,0,0,6.5c.35.79,8.82,19.57,27.65,38.4C61.43,194.74,93.12,208,128,208s66.57-13.26,91.66-38.34c18.83-18.83,27.3-37.61,27.65-38.4A8,8,0,0,0,247.31,124.76ZM128,168a40,40,0,1,1,40-40A40,40,0,0,1,128,168Z"/></svg></button>
            <button type="button" class="pw-action-btn" data-pdm-onclick="fillModalGeneratedPassword('kf-new')" title="${t('dialog.generate')}"><svg class="svg-fill" width="16" height="16" viewBox="0 0 256 256" aria-hidden="true"><path d="M192,32H64A32,32,0,0,0,32,64V192a32,32,0,0,0,32,32H192a32,32,0,0,0,32-32V64A32,32,0,0,0,192,32ZM92,176a12,12,0,1,1,12-12A12,12,0,0,1,92,176Zm0-72a12,12,0,1,1,12-12A12,12,0,0,1,92,104Zm36,36a12,12,0,1,1,12-12A12,12,0,0,1,128,140Zm36,36a12,12,0,1,1,12-12A12,12,0,0,1,164,176Zm0-72a12,12,0,1,1,12-12A12,12,0,0,1,164,104Z"/></svg></button>
          </div>
        </div>
      </div>
      <div class="modal-field">
        <label class="modal-field-label" data-i18n="dialog.key.label.confirm">${t('dialog.key.label.confirm')}</label>
        <div class="password-field-wrap">
          <input type="password" class="modal-field-input" id="kf-confirm" placeholder="${t('dialog.key.placeholder.confirm')}" data-i18n-placeholder="dialog.key.placeholder.confirm" data-pdm-oninput="checkDbPasswordMatch();clearDbKeyErrors()">
          <div class="pw-actions">
            <button type="button" class="pw-action-btn" data-pdm-onclick="toggleModalPwVisibility('kf-confirm',this)" title="${t('dialog.toggle.visible')}"><svg class="svg-fill" width="16" height="16" viewBox="0 0 256 256" aria-hidden="true"><path d="M247.31,124.76c-.35-.79-8.82-19.58-27.65-38.41C194.57,61.26,162.88,48,128,48S61.43,61.26,36.34,86.35C17.51,105.18,9,124,8.69,124.76a8,8,0,0,0,0,6.5c.35.79,8.82,19.57,27.65,38.4C61.43,194.74,93.12,208,128,208s66.57-13.26,91.66-38.34c18.83-18.83,27.3-37.61,27.65-38.4A8,8,0,0,0,247.31,124.76ZM128,168a40,40,0,1,1,40-40A40,40,0,0,1,128,168Z"/></svg></button>
          </div>
        </div>
      </div>
      <div class="match-indicator empty" id="kf-indicator">${t('dialog.key.indicator.empty')}</div>
      <div class="modal-form-error pdm-inline-6aa34d7432" id="kf-form-error"></div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-sm" data-pdm-onclick="closeModal()" data-i18n="dialog.button.cancel">${t('dialog.button.cancel')}</button>
      <div class="modal-footer-right">
        <button class="btn btn-primary btn-sm" id="kf-confirm-btn" data-pdm-onclick="confirmChangeDbPassword()" data-i18n="dialog.button.confirm">${t('dialog.button.confirm')}</button>
      </div>
    </div>
  `;
  openModal(html,{closeOnBackdrop:false});
}

/* ─── 导入导出对话框（ImportExportDialog）───
   统一对话框：模式切换（导出/导入）+ 字段联动。
   - 导出：范围选择 + 路径 + 加密密码 + 确认密码 → 执行
   - 导入：路径 + 加密密码 → 预览 → 冲突解决 → 执行
   加密密码与数据库主密码解耦（用于跨库迁移）。
   原型的显式 visual-state 入口只演示公开资料、比较和决定，完成仅显示演示提示。
   Win 端落地：core/database.py 的 export/import 方法 + QFileDialog 选路径 + Argon2id 派生 + AES-256-GCM 加密。 */
function arrangeBackupWindow(overlay) {
  overlay.dataset.pdmBackupLayout = 'true';
  const body = overlay.querySelector('.modal-body');
  const setup = document.createElement('div'); setup.className = 'ie-setup';
  const preview = document.getElementById('ie-import-page');
  const exportPage = document.getElementById('ie-export-page');
  const previewButton = document.getElementById('ie-preview-btn');
  const stack = overlay.querySelector('.ie-mode-stack');
  const status = document.getElementById('ie-inline-status');
  for (const child of [...body.children]) {
    if (child !== stack && child !== status) setup.append(child);
  }
  setup.append(exportPage);
  previewButton.classList.add('btn-primary');
  overlay.querySelector('.modal-footer-right').prepend(previewButton);
  body.replaceChildren(setup, preview);
  body.classList.add('ie-body-layout');
  const actions = document.createElement('div'); actions.className = 'ie-fixed-actions';
  for (const id of ['ie-conflict-count','ie-bulk-actions','ie-pager']) {
    const part = document.createElement('div'); part.id = id; actions.append(part);
  }
  body.after(actions, status);
}

const IE_STATE = {
  mode: 'export',           /* 'export' | 'import' */
  sourceKind: 'FILE', sourceDisplayName: '',
  scope: 'all',             /* 仅导出：全部、密码、记事或自定义 */
  exportSelection: [], picker: null,
  path: '',
  password: '',
  confirmPw: '',
  previewReady: false,      /* 导入预览是否就绪 */
  conflicts: [],
  kind: 'PASSWORD', statusFilter: 'ALL', fieldFilter: 'ALL', activeId: 0,
  selected: new Set(), confirmation: false, batchMessage: '', revealed: new Set(), offsets: new Map(), timers: new Map(),
  added: 0, updated: 0, skipped: 0, totalPw: 0, totalNote: 0
};

function openDemoExportSelection(container,confirmed,onDone){
  const records=[
    ...passwords.map(item=>({kind:'PASSWORD',id:item.id,revision:item.updated_at,title:item.platform,detail:item.account})),
    ...notes.map(item=>({kind:'NOTE',id:item.id,revision:item.updated_at,title:item.title,detail:item.content.slice(0,160),searchContent:item.content})),
  ];
  const key=item=>`${item.kind}:${item.id}`;
  const selected=new Map(confirmed.map(item=>[key(item),{...item}]));
  let query='',kind='ALL',offset=0;
  const limit=20;
  const matching=()=>records.filter(item=>(kind==='ALL'||kind===item.kind)&&(!query.trim()||
    settingsFieldMatches(item.title,query.trim())||
    (item.kind==='PASSWORD'?settingsFieldMatches(item.detail,query.trim()):(item.searchContent||'').toLowerCase().includes(query.trim().toLowerCase()))));
  const view=window.PdmExportSelection.create(container,(action,value)=>{
    if(action==='cancel'||action==='done'){
      if(action==='done'&&!selected.size)return;
      const result=action==='done'?[...selected.values()]:null;
      view.dispose();selected.clear();onDone(result);return;
    }
    if(action==='query'){query=value.query;kind=value.kind;offset=0;}
    if(action==='toggle'){
      const item=records.find(item=>key(item)===key(value));
      if(item){if(value.selected)selected.set(key(item),{kind:item.kind,id:item.id,revision:item.revision});else selected.delete(key(item));}
    }
    if(action==='all'){
      const filtered=matching(),allSelected=filtered.length>0&&filtered.every(item=>selected.has(key(item)));
      for(const item of filtered){
        if(allSelected)selected.delete(key(item));
        else selected.set(key(item),{kind:item.kind,id:item.id,revision:item.revision});
      }
    }
    if(action==='clear')selected.clear();
    if(action==='previous')offset=Math.max(0,offset-limit);
    if(action==='next')offset+=limit;
    render();
  },state.lang==='en'?'EN':'ZH');
  function render(){
    const filtered=matching();offset=Math.min(offset,Math.max(0,Math.floor((filtered.length-1)/limit)*limit));
    view.project({query,kind,offset,limit,total:filtered.length,allSelected:filtered.length>0&&filtered.every(item=>selected.has(key(item))),...window.PdmExportSelection.counts([...selected.values()]),
      items:filtered.slice(offset,offset+limit).map(item=>({...item,selected:selected.has(key(item))}))});
  }
  render();return view;
}

function updateIEDemoExportSelection(){
  const custom=IE_STATE.scope==='custom';
  const summary=$('#ie-custom-selection');
  if(summary){
    summary.hidden=!custom;
    const counts=window.PdmExportSelection.counts(IE_STATE.exportSelection);
    summary.firstElementChild.textContent=ieDemoText(`密码 ${counts.passwordCount} · 记事 ${counts.noteCount}`,`${counts.passwordCount} passwords · ${counts.noteCount} notes`);
  }
  if(IE_STATE.mode==='export')$('#ie-execute-btn').disabled=custom&&!IE_STATE.exportSelection.length;
}

function chooseIEDemoExportSelection(previousScope=IE_STATE.scope){
  IE_STATE.scope='custom';updateIEDemoExportSelection();
  IE_STATE.picker=openDemoExportSelection($('#active-modal .modal'),IE_STATE.exportSelection,result=>{
    IE_STATE.picker=null;
    if(result!==null)IE_STATE.exportSelection=result;else IE_STATE.scope=previousScope;
    $('#ie-scope').value=IE_STATE.scope;updateIEDemoExportSelection();
  });
}

function openImportExportDialog(mode){
  clearIEDemoReads();
  IE_STATE.selected.clear();
  IE_STATE.kind='PASSWORD'; IE_STATE.statusFilter='ALL'; IE_STATE.fieldFilter='ALL'; IE_STATE.confirmation=false; IE_STATE.batchMessage='';
  IE_STATE.mode = mode;
  IE_STATE.sourceKind='FILE'; IE_STATE.sourceDisplayName='';
  IE_STATE.scope = 'all';
  IE_STATE.exportSelection=[];IE_STATE.picker=null;
  IE_STATE.path = '';
  IE_STATE.password = '';
  IE_STATE.confirmPw = '';
  IE_STATE.previewReady = false;
  IE_STATE.conflicts = [];
  const html = `
    <div class="modal-header">
      <div class="modal-title" id="ie-title">${mode==='export'?t('dialog.ie.title.export'):t('dialog.ie.title.import')}</div>
      <button class="modal-close" data-pdm-onclick="closeModal()">✕</button>
    </div>
    <div class="modal-body">
      <div class="segment" id="ie-mode-seg">
        <button class="${mode==='export'?'active':''}" type="button" data-pdm-onclick="switchIEMode('export')">${t('dialog.ie.mode.export')}</button>
        <button class="${mode==='import'?'active':''}" type="button" data-pdm-onclick="switchIEMode('import')">${t('dialog.ie.mode.import')}</button>
      </div>

      <div class="modal-field">
        <label class="modal-field-label">${t('dialog.ie.format.label')}</label>
        <div class="ie-format-info">
          <span class="ie-format-name">${t('dialog.ie.format.encrypted')}</span>
          <span class="modal-field-hint">${t('dialog.ie.format.encrypted.hint')}</span>
        </div>
      </div>

      <div class="modal-field">
        <label class="modal-field-label">${t('dialog.ie.path.label')}</label>
        <div class="modal-field-row">
          <input type="text" class="modal-field-input" id="ie-path" placeholder="${mode==='export'?t('dialog.ie.path.placeholder.export'):t('dialog.ie.path.placeholder.import')}" data-pdm-oninput="IE_STATE.path=this.value">
          <button class="btn btn-sm" data-pdm-onclick="browseIEFile()">${t('dialog.ie.browse')}</button>
        </div>
      </div>

      <div class="modal-field">
        <label class="modal-field-label">${t('dialog.ie.password.label')}</label>
        <div class="password-field-wrap">
          <input type="password" class="modal-field-input" id="ie-password" placeholder="${t(mode==='export'?'dialog.ie.password.placeholder.export':'dialog.ie.password.placeholder.import')}" data-pdm-oninput="IE_STATE.password=this.value;checkIEPasswordMatch()">
          <div class="pw-actions">
            <button type="button" class="pw-action-btn" data-pdm-onclick="toggleModalPwVisibility('ie-password',this)" title="${t('dialog.toggle.visible')}">${svgIcon('eye',16)}</button>
          </div>
        </div>
        <span class="modal-field-hint">${t('dialog.ie.password.hint')}</span>
      </div>

      <div class="ie-mode-stack">
        <div class="ie-mode-page ${mode==='export'?'active':''}" id="ie-export-page">
          <div class="modal-field" id="ie-confirm-field">
            <label class="modal-field-label">${t('dialog.ie.password.confirm.label')}</label>
            <div class="password-field-wrap">
              <input type="password" class="modal-field-input" id="ie-confirm" placeholder="${t('dialog.ie.password.confirm.placeholder')}" data-pdm-oninput="IE_STATE.confirmPw=this.value;checkIEPasswordMatch()">
              <div class="pw-actions">
                <button type="button" class="pw-action-btn" data-pdm-onclick="toggleModalPwVisibility('ie-confirm',this)" title="${t('dialog.toggle.visible')}">${svgIcon('eye',16)}</button>
              </div>
            </div>
            <div class="match-indicator empty" id="ie-match-indicator">${t('dialog.ie.password.indicator.empty')}</div>
          </div>

          <div class="modal-field" id="ie-scope-field">
            <label class="modal-field-label">${t('dialog.ie.scope.label')}</label>
            <select class="modal-field-input" id="ie-scope">
              <option value="all">${t('dialog.ie.scope.all')}</option>
              <option value="passwords">${t('dialog.ie.scope.passwords')}</option>
              <option value="notes">${t('dialog.ie.scope.notes')}</option>
              <option value="custom">${ieDemoText('自定义','Custom')}</option>
            </select>
            <div class="export-selection-summary" id="ie-custom-selection" hidden><span></span><button type="button" class="btn btn-sm" id="ie-select-records">${ieDemoText('选择记录','Choose records')}</button></div>
          </div>

          <div id="ie-export-warning" class="ie-warning-box">
            ${t('dialog.ie.warning.export')}
          </div>
        </div>

        <div class="ie-mode-page ${mode==='import'?'active':''}" id="ie-import-page">
          <div class="modal-field" id="ie-preview-field">
            <label class="modal-field-label">${t('dialog.ie.preview.label')}</label>
            <div id="ie-preview" class="ie-preview-box">
              <span class="ie-preview-empty">${t('dialog.ie.preview.empty')}</span>
            </div>
            <button id="ie-preview-btn" class="btn btn-sm pdm-inline-43a97fe494" type="button" data-pdm-onclick="previewIEImport()" data-i18n="dialog.ie.preview.button">${t('dialog.ie.preview.button')}</button>
          </div>
        </div>
      </div>
      <div class="ie-inline-status pdm-inline-6aa34d7432" id="ie-inline-status" role="status" aria-live="polite" aria-atomic="true"></div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-sm" data-pdm-onclick="closeModal()">${t('dialog.button.cancel')}</button>
      <div class="modal-footer-right">
        <button class="btn btn-primary btn-sm" id="ie-execute-btn" data-pdm-onclick="executeIEOperation()">${mode==='export'?t('dialog.ie.execute.export'):t('dialog.ie.execute.import')}</button>
      </div>
    </div>
  `;
  const overlay=openModal(html,{wide:true});
  overlay.classList.add('ie-window-preview');
  overlay.addEventListener('click',handleIEDemoAction);
  overlay.addEventListener('change',event=>{
    if(event.target.id==='ie-field-filter'&&IE_STATE.fieldFilter!==event.target.value){clearIEDemoReads();IE_STATE.fieldFilter=event.target.value;IE_STATE.confirmation=false;renderIEPreview();}
  });
  arrangeBackupWindow(overlay);
  $('#ie-scope').addEventListener('change',event=>{
    const previous=IE_STATE.scope;IE_STATE.scope=event.target.value;
    if(IE_STATE.scope==='custom')chooseIEDemoExportSelection(previous);else updateIEDemoExportSelection();
  });
  $('#ie-select-records').addEventListener('click',()=>chooseIEDemoExportSelection());
  switchIEMode(mode);
}

function openReceivedDemoComparison(displayName,scope){
  openImportExportDialog('import');
  IE_STATE.sourceKind='TRANSFER'; IE_STATE.sourceDisplayName=displayName;
  const overlay=$('#active-modal'); overlay.dataset.ieTransfer='true';
  prepareIEDemoComparison();
  if(scope!=='ALL')IE_STATE.conflicts=IE_STATE.conflicts.filter(item=>item.kind===(scope==='NOTES'?'NOTE':'PASSWORD'));
  IE_STATE.kind=scope==='NOTES'?'NOTE':'PASSWORD';IE_STATE.activeId=IE_STATE.conflicts[0]?.idx??-1;
  IE_STATE.totalPw=IE_STATE.conflicts.filter(item=>item.kind==='PASSWORD').length;
  IE_STATE.totalNote=IE_STATE.conflicts.filter(item=>item.kind==='NOTE').length;
  $('#ie-title').textContent=ieDemoText('比较接收的资料','Compare received contents');
  renderIEPreview();
  $('#ie-demo-back')?.focus({preventScroll:true});
}

/* 模式切换：导出/导入联动字段显示与按钮文案 */
function switchIEMode(mode){
  clearIEDemoReads();
  restoreIEDemoSetup();
  IE_STATE.mode = mode;
  $('#active-modal')?.classList.toggle('ie-export-mode',mode==='export');
  $('#active-modal')?.classList.remove('ie-review-mode');
  if($('#ie-preview-btn')) $('#ie-preview-btn').hidden=mode==='export';
  $('#ie-execute-btn').hidden=mode==='import';
  const segBtns = $$('#ie-mode-seg button');
  segBtns.forEach((btn,i)=>{btn.classList.toggle('active',(mode==='export'&&i===0)||(mode==='import'&&i===1))});
  $('#ie-export-page').classList.toggle('active',mode==='export');
  $('#ie-import-page').classList.toggle('active',mode==='import');
  $('#ie-path').placeholder = mode==='export'?t('dialog.ie.path.placeholder.export'):t('dialog.ie.path.placeholder.import');
  $('#ie-password').placeholder = mode==='export'?t('dialog.ie.password.placeholder.export'):t('dialog.ie.password.placeholder.import');
  $('#ie-execute-btn').textContent = mode==='export'?t('dialog.ie.execute.export'):t('dialog.ie.execute.import');
  $('#ie-title').textContent = mode==='export'?t('dialog.ie.title.export'):t('dialog.ie.title.import');
  /* 切换到导出时清空预览状态（避免脏状态） */
  if(mode==='export'){
    IE_STATE.previewReady = false;
    updateIEDemoExportSelection();
  }
}

/* 正式产品由 m4_runtime 以 C50/C52 接管；独立原型不伪造文件权限。 */
function browseIEFile(){
  showToast(t('dialog.ie.error.path'),'error');
}

/* 密码一致性检查（仅导出模式需确认密码） */
function checkIEPasswordMatch(){
  if(IE_STATE.mode !== 'export') return;
  const indicator = $('#ie-match-indicator');
  if(!indicator) return;
  const newPw = IE_STATE.password;
  const confirmPw = IE_STATE.confirmPw;
  if(!newPw && !confirmPw){
    indicator.className = 'match-indicator empty';
    indicator.textContent = t('dialog.ie.password.indicator.empty');
  }else if(newPw === confirmPw){
    indicator.className = 'match-indicator match';
    indicator.textContent = t('dialog.ie.password.indicator.match');
  }else{
    indicator.className = 'match-indicator mismatch';
    indicator.textContent = t('dialog.ie.password.indicator.mismatch');
  }
}

/* 正式产品由 m4_runtime 的 C53/C54 接管；独立原型不伪造解密结果。 */
function previewIEImport(){
  const previewBox = $('#ie-preview');
  if(!IE_STATE.path || !IE_STATE.password){
    previewBox.innerHTML = `<span class="ie-preview-error">${t('dialog.ie.preview.empty')}</span>`;
    return;
  }
  if(visualFixtureState==='dialog-ie-import-conflicts'){prepareIEDemoComparison();return;}
  previewBox.innerHTML = `<span class="ie-preview-error">${t('dialog.ie.error.preview')}</span>`;
}

/* 下列比较仅演示公开夹具，不读取文件，也不承担正式导入判断。 */
function ieDemoText(zh,en){return state.lang==='en'?en:zh;}

function clearIEDemoReads(resetOffsets=true){
  for(const timer of IE_STATE.timers.values()) clearTimeout(timer);
  IE_STATE.timers.clear(); IE_STATE.revealed.clear();
  if(resetOffsets)IE_STATE.offsets.clear();else for(const field of ['PASSWORD','TOTP','RECOVERY_CODES'])IE_STATE.offsets.delete(field);
}

function prepareIEDemoComparison(){
  clearIEDemoReads();
  const codes=Array.from({length:128},(_,index)=>({value:`PUBLIC-${String(index).padStart(3,'0')}-`+'A'.repeat(40),used:index%3===0}));
  const password=(name,account,value)=>({PLATFORM:name,ACCOUNT:account,PASSWORD:value,NOTES:'公开端到端夹具',
    TOTP:'',RECOVERY_CODES:[],FAVORITE:false,STRENGTH:'strong',PASSWORD_CHANGED_AT:'2026-01-02T03:04:05',UPDATED_AT:'2026-02-03T04:05:06'});
  const alpha=password('Public Alpha','alpha@example.invalid','public-alpha-password');
  alpha.TOTP='JBSWY3DPEHPK3PXP';alpha.RECOVERY_CODES=codes;
  const beta=password('Public Beta','beta@example.invalid','public-beta-password');
  const note=(title,content,order)=>({PLATFORM:title,NOTES:content,FAVORITE:false,CREATED_AT:'2026-01-02T03:04:05',UPDATED_AT:'2026-02-03T04:05:06',SORT_ORDER:order});
  const firstNote=note('Travel','Public first note',0),secondNote=note('TRAVEL','Public second note',1);
  const noteTargets=[{id:1,value:{...firstNote,NOTES:firstNote.NOTES+' current',UPDATED_AT:'2026-03-04T05:06:07'}},
    {id:2,value:{...secondNote,NOTES:secondNote.NOTES+' current',UPDATED_AT:'2026-03-04T05:06:07'}}];
  const rows=[
    {idx:0,sourceId:'password:0',kind:'PASSWORD',status:'CONFLICT',incoming:alpha,
      candidates:[{id:1,value:{...alpha,ACCOUNT:'changed@example.invalid',NOTES:'L'.repeat(9000),UPDATED_AT:'2026-03-04T05:06:07'}}]},
    {idx:1,sourceId:'password:1',kind:'PASSWORD',status:'CONFLICT',incoming:beta,
      candidates:[{id:2,value:{...beta,ACCOUNT:'changed@example.invalid',UPDATED_AT:'2026-03-04T05:06:07'}}]},
    {idx:2,sourceId:'note:0',kind:'NOTE',status:'CONFLICT',incoming:firstNote,candidates:noteTargets},
    {idx:3,sourceId:'note:1',kind:'NOTE',status:'CONFLICT',incoming:secondNote,candidates:noteTargets},
  ];
  IE_STATE.conflicts=rows.map(row=>({...row,action:row.status==='IDENTICAL'?'SKIP':'UNDECIDED',targetIndex:0,targetSelected:row.candidates.length===1}));
  IE_STATE.totalPw=2;IE_STATE.totalNote=2;IE_STATE.kind='PASSWORD';IE_STATE.activeId=0;
  IE_STATE.previewReady=true;IE_STATE.statusFilter='ALL';IE_STATE.fieldFilter='ALL';IE_STATE.selected.clear();IE_STATE.confirmation=false;IE_STATE.batchMessage='';
  renderIEPreview();
}

function ieDemoFields(kind,business=false){
  const fields=kind==='NOTE'?['PLATFORM','NOTES','FAVORITE']:['PLATFORM','ACCOUNT','PASSWORD','NOTES','TOTP','RECOVERY_CODES','FAVORITE'];
  return business?fields:fields.concat(kind==='NOTE'?['CREATED_AT','UPDATED_AT','SORT_ORDER']:['STRENGTH','PASSWORD_CHANGED_AT','UPDATED_AT']);
}

function ieDemoLabel(field,kind){
  const labels={PLATFORM:kind==='NOTE'?['标题','Title']:['名称','Name'],ACCOUNT:['账号','Account'],PASSWORD:['密码','Password'],
    NOTES:kind==='NOTE'?['正文','Content']:['备注','Notes'],TOTP:['动态口令密钥','Authenticator key'],RECOVERY_CODES:['恢复码','Recovery codes'],
    FAVORITE:['收藏','Favorite'],STRENGTH:['强度','Strength'],PASSWORD_CHANGED_AT:['密码修改时间','Password changed'],
    CREATED_AT:['创建时间','Created'],UPDATED_AT:['修改时间','Updated'],SORT_ORDER:['排序值','Sort order']};
  return ieDemoText(...labels[field]);
}

function ieDemoCurrent(item){return item.targetSelected?item.candidates[item.targetIndex]?.value:null;}
function ieDemoClearsRecovery(item){return item.kind==='PASSWORD'&&Boolean(ieDemoCurrent(item)?.RECOVERY_CODES?.length)&&!item.incoming.RECOVERY_CODES.length;}
function ieDemoDifferences(item){
  const current=ieDemoCurrent(item);
  return current?ieDemoFields(item.kind).filter(field=>JSON.stringify(current[field])!==JSON.stringify(item.incoming[field])):[];
}
function ieDemoMatches(item,withField=true){
  const status=IE_STATE.statusFilter;
  const match=status==='ALL'||status==='PENDING'&&item.status==='CONFLICT'&&item.action==='UNDECIDED'||
    status==='DIFFERENT'&&item.status==='CONFLICT'&&item.candidates.length>0||status==='SKIPPED'&&item.action==='SKIP';
  return match&&(!withField||IE_STATE.fieldFilter==='ALL'||ieDemoDifferences(item).includes(IE_STATE.fieldFilter));
}
function ieDemoDecision(action){return action==='KEEP'?ieDemoText('保留两份','Keep both'):t('dialog.ie.conflict.'+({OVERWRITE:'overwrite',SKIP:'skip',UNDECIDED:'undecided'}[action]));}
function ieDemoBatchDecision(action){return ieDemoText(...{OVERWRITE:['覆盖所选','Overwrite selected'],SKIP:['跳过所选','Skip selected'],KEEP:['所选保留两份','Keep both for selected']}[action]);}

function setIEDemoText(node,text){if(node&&node.textContent!==text)node.textContent=text;}

function restoreIEDemoSetup(){
  const actions=$('#active-modal .ie-fixed-actions');
  for(const id of ['ie-bulk-actions','ie-pager']){
    const node=$('#'+id);if(node&&actions){actions.append(node);node.replaceChildren();delete node.dataset.ieKind;}
  }
  $('#ie-conflict-count')?.replaceChildren();
  const consequence=$('#ie-final-consequence');if(consequence){consequence.replaceChildren();consequence.hidden=true;}
  const status=$('#ie-inline-status');if(status){status.classList.remove('ie-status-empty');status.hidden=true;}
  const preview=$('#ie-preview');if(preview)preview.innerHTML=`<span class="ie-preview-empty">${t('dialog.ie.preview.empty')}</span>`;
}

function renderIEPreview(){
  const box=$('#ie-preview');if(!box||!IE_STATE.previewReady)return;
  const modal=$('#active-modal'),kind=IE_STATE.kind;
  modal.classList.add('ie-review-mode');$('#ie-preview-btn').hidden=true;$('#ie-execute-btn').hidden=false;
  const status=$('#ie-inline-status');status.className='ie-inline-status';status.classList.toggle('ie-status-empty',!IE_STATE.batchMessage);status.hidden=false;status.style.removeProperty('display');setIEDemoText(status,IE_STATE.batchMessage);
  recomputeIEStats();
  const pending=IE_STATE.conflicts.filter(item=>item.kind===kind&&item.status==='CONFLICT'&&item.action==='UNDECIDED').length;
  $('#ie-execute-btn').disabled=(kind==='PASSWORD'?pending:IE_STATE.unresolved)>0;
  setIEDemoText($('#ie-execute-btn'),kind==='PASSWORD'&&IE_STATE.totalNote>0?ieDemoText('下一步：记事','Next: notes'):t('dialog.ie.execute.import'));
  let back=$('#ie-demo-back');
  if(!back){back=document.createElement('button');back.id='ie-demo-back';back.type='button';back.className='btn btn-sm';back.dataset.ieAction='back';$('#ie-execute-btn').before(back);}
  setIEDemoText(back,kind==='NOTE'&&IE_STATE.totalPw>0?ieDemoText('返回密码','Back to passwords'):IE_STATE.sourceKind==='TRANSFER'?
    ieDemoText('返回设备传输','Back to device transfer'):ieDemoText('返回文件与密码','Back to file and password'));back.hidden=false;
  const bulk=$('#ie-bulk-actions'),pager=$('#ie-pager');
  if(!box.querySelector('.ie-source-panel')){
    box.innerHTML=`<div class="ie-review-heading"><div id="ie-step-title" class="ie-preview-summary"></div><span class="ie-conflict-help">${ieDemoText('本次共 2 条密码、2 篇记事','2 passwords and 2 notes')}</span></div>
      <div class="ie-review-filters">${[['ALL','全部','All'],['PENDING','待处理','Pending'],['DIFFERENT','有差异','Different'],['SKIPPED','已跳过','Skipped']].map(([value,zh,en])=>`<button type="button" class="btn btn-sm" data-ie-action="filter" data-ie-value="${value}" data-ie-focus="filter:${value}">${ieDemoText(zh,en)}</button>`).join('')}
      <label class="ie-field-filter-label">${ieDemoText('差异字段','Changed field')}<select id="ie-field-filter" class="modal-field-input"></select></label></div>
      <div class="ie-uncompared-notice ie-notice-empty"><span></span><button type="button" class="btn btn-sm" data-ie-action="clear-field">${ieDemoText('清除字段筛选','Clear field filter')}</button></div>
      <div class="ie-comparison-workspace"><div class="ie-source-panel"><div id="ie-conflict-list" aria-label="${ieDemoText('本次来源资料','Incoming items')}"></div></div><div id="ie-comparison-detail"></div></div>`;
    const source=box.querySelector('.ie-source-panel');source.prepend(bulk);source.append(pager);
  }
  let consequence=$('#ie-final-consequence');
  if(IE_STATE.sourceKind==='TRANSFER'){
    let source=$('#ie-source-device');if(!source){source=document.createElement('p');source.id='ie-source-device';source.className='ie-transfer-source';box.querySelector('.ie-review-heading').after(source);}
    setIEDemoText(source,ieDemoText('来源设备：','Source device: ')+IE_STATE.sourceDisplayName);
    setIEDemoText(box.querySelector('.ie-review-heading .ie-conflict-help'),ieDemoText(`本次共 ${IE_STATE.totalPw} 条密码、${IE_STATE.totalNote} 篇记事`,`${IE_STATE.totalPw} passwords and ${IE_STATE.totalNote} notes`));
  }
  if(!consequence){consequence=document.createElement('div');consequence.id='ie-final-consequence';consequence.className='ie-conflict-help recovery-backup-warning';$('#ie-conflict-count').after(consequence);}
  setIEDemoText($('#ie-step-title'),ieDemoText(kind==='PASSWORD'?'核对密码':'核对记事',kind==='PASSWORD'?'Review passwords':'Review notes'));
  box.querySelectorAll('[data-ie-action="filter"]').forEach(button=>{
    const active=button.dataset.ieValue===IE_STATE.statusFilter;button.classList.toggle('active',active);button.setAttribute('aria-pressed',String(active));
  });
  const fieldFilter=$('#ie-field-filter');
  if(fieldFilter.dataset.ieKind!==kind){
    fieldFilter.innerHTML=['ALL',...ieDemoFields(kind,true)].map(field=>`<option value="${field}">${field==='ALL'?ieDemoText('全部字段','All fields'):ieDemoLabel(field,kind)}</option>`).join('');fieldFilter.dataset.ieKind=kind;
  }
  fieldFilter.value=IE_STATE.fieldFilter;
  const group=IE_STATE.conflicts.filter(item=>item.kind===kind),items=group.filter(item=>ieDemoMatches(item));
  const unknown=group.filter(item=>ieDemoMatches(item,false)&&item.candidates.length>1&&!item.targetSelected).length;
  const notice=box.querySelector('.ie-uncompared-notice');notice.classList.toggle('ie-notice-empty',!unknown);
  setIEDemoText(notice.querySelector('span'),unknown?ieDemoText(`${unknown} 项需先选择比较目标。`,`${unknown} items need a comparison target.`):'');
  notice.querySelector('button').hidden=!unknown||IE_STATE.fieldFilter==='ALL';
  if(!items.some(item=>item.idx===IE_STATE.activeId))IE_STATE.activeId=items[0]?.idx??-1;
  const active=items.find(item=>item.idx===IE_STATE.activeId),list=$('#ie-conflict-list'),visible=new Set(items.map(item=>String(item.idx)));
  list.querySelectorAll('.ie-conflict-item').forEach(row=>{if(!visible.has(row.dataset.ieId))row.remove();});
  if(items.length)list.querySelector('.ie-preview-empty')?.remove();
  items.forEach((item,index)=>{
    let row=list.querySelector(`.ie-conflict-item[data-ie-id="${item.idx}"]`);
    if(!row){
      row=document.createElement('div');row.className='ie-conflict-item';row.dataset.ieId=String(item.idx);row.dataset.pdmBackupConflictId=item.sourceId;row.dataset.pdmBackupKind=kind;
      row.innerHTML=`${item.status==='CONFLICT'?`<button type="button" class="ie-item-check" role="checkbox" aria-label="${ieDemoText('选择此项','Select item')}" data-ie-action="select" data-ie-id="${item.idx}" data-ie-focus="select:${item.idx}"></button>`:''}
        <button type="button" class="ie-item-open" data-ie-action="inspect" data-ie-id="${item.idx}" data-ie-focus="item:${item.idx}"><span class="ie-conflict-platform"></span><span class="ie-conflict-tag"></span></button>`;
    }
    if(list.children[index]!==row)list.insertBefore(row,list.children[index]||null);
    row.classList.toggle('active',item.idx===IE_STATE.activeId);row.querySelector('.ie-item-open').setAttribute('aria-current',String(item.idx===IE_STATE.activeId));
    const check=row.querySelector('.ie-item-check');if(check){const checked=IE_STATE.selected.has(item.idx);check.setAttribute('aria-checked',String(checked));setIEDemoText(check,checked?'✓':'');}
    setIEDemoText(row.querySelector('.ie-conflict-platform'),item.incoming.PLATFORM);
    const tag=row.querySelector('.ie-conflict-tag');tag.className=`ie-conflict-tag ${item.status==='CONFLICT'?item.action.toLowerCase():item.status.toLowerCase()}`;
    setIEDemoText(tag,item.status==='NEW'?ieDemoText('将新增','New'):item.status==='IDENTICAL'?ieDemoText('相同 · 已跳过','Identical · skipped'):ieDemoDecision(item.action));
  });
  if(!items.length&&!list.querySelector('.ie-preview-empty')){const empty=document.createElement('div');empty.className='ie-preview-empty';empty.textContent=ieDemoText('当前筛选没有项目','No items match this filter');list.append(empty);}
  const detail=$('#ie-comparison-detail'),identity=active?`${active.idx}:${active.targetSelected?active.targetIndex:-1}:${state.lang}`:'';
  if(detail.dataset.ieIdentity!==identity){detail.innerHTML=active?renderIEDemoComparison(active):'';detail.dataset.ieIdentity=identity;detail.scrollTop=0;}
  else if(active)for(const field of ieDemoFields(active.kind))updateIEDemoField(active,field);
  const chosen=group.filter(item=>IE_STATE.selected.has(item.idx)),outside=chosen.filter(item=>!ieDemoMatches(item)).length;
  IE_STATE.confirmation=chosen.length>0;
  const selectedRecoveryCleared=chosen.filter(ieDemoClearsRecovery).length;
  const recoveryCleared=IE_STATE.conflicts.filter(item=>item.action==='OVERWRITE'&&ieDemoClearsRecovery(item)).length;
  setIEDemoText($('#ie-conflict-count'),ieDemoText(`新增 ${IE_STATE.added} · 覆盖 ${IE_STATE.updated} · 跳过 ${IE_STATE.skipped} · 待处理 ${IE_STATE.unresolved}`,`Add ${IE_STATE.added} · Overwrite ${IE_STATE.updated} · Skip ${IE_STATE.skipped} · Pending ${IE_STATE.unresolved}`));
  consequence.hidden=!recoveryCleared;setIEDemoText(consequence,recoveryCleared?ieDemoText(`本次覆盖将清空 ${recoveryCleared} 条记录的整组恢复码。`,`This import will remove all recovery codes from ${recoveryCleared} records.`):'');
  if(!$('#ie-selected-count')){
    bulk.innerHTML=`<div class="ie-selection-toolbar"><strong id="ie-selected-count"></strong><button type="button" class="btn btn-sm" data-ie-action="select-page">${ieDemoText('选中本页','Select page')}</button><button type="button" class="btn btn-sm" data-ie-action="clear-selection">${ieDemoText('清除选择','Clear selection')}</button></div>
      <div class="ie-batch-confirm" role="group"><div id="ie-selected-scope" class="ie-conflict-help"></div><div class="ie-conflict-help recovery-backup-warning" data-pdm-backup-recovery-warning="selection" hidden></div><div class="ie-conflict-actions">${['OVERWRITE','KEEP','SKIP'].map(action=>`<button type="button" class="btn btn-sm" data-ie-decision="${action}" data-pdm-onclick="resolveAllIEConflicts('${action}')">${ieDemoBatchDecision(action)}</button>`).join('')}</div></div>`;
  }
  setIEDemoText($('#ie-selected-count'),ieDemoText(`已选 ${chosen.length} 项`,`${chosen.length} selected`));
  bulk.querySelector('[data-ie-action="select-page"]').disabled=!items.some(item=>item.status==='CONFLICT');bulk.querySelector('[data-ie-action="clear-selection"]').disabled=!chosen.length;
  const confirmation=bulk.querySelector('.ie-batch-confirm');confirmation.classList.toggle('ie-batch-empty',!chosen.length);confirmation.setAttribute('aria-hidden',String(!chosen.length));confirmation.setAttribute('aria-label',ieDemoText('处理所选项目','Apply to selected items'));
  $('#ie-selected-scope').hidden=outside===0;
  setIEDemoText($('#ie-selected-scope'),outside?ieDemoText(`其中 ${outside} 项在当前筛选外`,`${outside} items outside this filter`):'');
  const recovery=bulk.querySelector('[data-pdm-backup-recovery-warning="selection"]');recovery.hidden=!selectedRecoveryCleared;
  setIEDemoText(recovery,selectedRecoveryCleared?ieDemoText(`覆盖将清空 ${selectedRecoveryCleared} 条记录的整组恢复码；跳过可保留。`,`Overwrite removes all recovery codes from ${selectedRecoveryCleared} records. Skip to keep them.`):'');
  confirmation.querySelectorAll('[data-ie-decision]').forEach(button=>{button.hidden=button.dataset.ieDecision==='KEEP'&&kind!=='NOTE';button.disabled=!chosen.length;});
  if(!pager.firstElementChild)pager.innerHTML=`<div class="ie-conflict-toolbar"><button class="btn btn-sm" disabled aria-label="${ieDemoText('上一页','Previous')}">←</button><span class="ie-conflict-help"></span><button class="btn btn-sm" disabled aria-label="${ieDemoText('下一页','Next')}">→</button></div>`;
  setIEDemoText(pager.querySelector('span'),ieDemoText(`${items.length} 项 · 第 1 页`,`${items.length} items · Page 1`));
}

function updateIEDemoField(item,field){
  const row=$(`#ie-comparison-detail [data-pdm-backup-field="${field}"]`);if(!row)return;
  const secret=['PASSWORD','TOTP','RECOVERY_CODES'].includes(field),visible=!secret||IE_STATE.revealed.has(field);
  const offsets=IE_STATE.offsets.get(field)||[0],chunk=ieDemoFieldChunk(item,field,offsets.at(-1)),current=ieDemoCurrent(item);
  row.querySelectorAll('.ie-conflict-value').forEach((target,index)=>setIEDemoText(target,index===0&&!current?
    ieDemoText(item.candidates.length?'请选择比较目标':'无目标记录',item.candidates.length?'Select a target':'No existing record'):
    visible?(chunk.values[index]||'—'):ieDemoText('已隐藏','Hidden')));
  const eye=row.querySelector('.ie-secret-toggle');
  if(eye){const pressed=String(visible);if(eye.getAttribute('aria-pressed')!==pressed)eye.innerHTML=svgIcon(visible?'eye-closed':'eye',16);eye.setAttribute('aria-pressed',pressed);eye.setAttribute('aria-label',visible?ieDemoText('隐藏两侧','Hide both sides'):ieDemoText('查看两侧','Read both sides'));}
  row.querySelector('[data-ie-action="field-previous"]').disabled=!visible||offsets.length===1;
  row.querySelector('[data-ie-action="field-next"]').disabled=!visible||chunk.done;
  setIEDemoText(row.querySelector('.ie-field-position'),visible&&(!chunk.done||offsets.length>1)?ieDemoText(`第 ${offsets.length} 片`,`Part ${offsets.length}`):'');
}

function ieDemoFieldChunk(item,field,offset){
  const current=ieDemoCurrent(item),pair=[current?.[field]??(field==='RECOVERY_CODES'?[]:''),item.incoming[field]];
  if(field==='RECOVERY_CODES'){
    const total=Math.max(...pair.map(value=>value.length));let end=total;
    while(end>offset&&pair.some(value=>JSON.stringify(value.slice(offset,end)).length>8192))end--;
    return {values:pair.map(value=>value.slice(offset,end).map((code,index)=>`${offset+index+1}. ${code.value} · ${ieDemoText(code.used?'已用':'未用',code.used?'Used':'Unused')}`).join('\n')),next:end,done:end===total};
  }
  const texts=pair.map(value=>field==='FAVORITE'&&typeof value==='boolean'?ieDemoText(value?'已收藏':'未收藏',value?'Favorite':'Not favorite'):
    field==='STRENGTH'&&value?t('common.strength.'+value):String(value));
  const total=Math.max(...texts.map(value=>Array.from(value).length)),end=Math.min(total,offset+8192);
  return {values:texts.map(value=>Array.from(value).slice(offset,end).join('')),next:end,done:end===total};
}

function renderIEDemoComparison(item){
  const fields=ieDemoFields(item.kind),diff=ieDemoDifferences(item),current=ieDemoCurrent(item);
  const actions=[];
  if(item.status==='CONFLICT'){
    if(item.candidates.length&&!item.targetSelected)actions.push(['SELECT_TARGET','选择首个目标','Select first target',false]);
    if(item.candidates.length>1&&item.targetSelected){actions.push(['PREVIOUS_TARGET','上个目标','Previous target',!item.targetIndex],['NEXT_TARGET','下个目标','Next target',item.targetIndex+1>=item.candidates.length]);}
    actions.push(['OVERWRITE','覆盖','Overwrite',!item.targetSelected||!item.candidates.length]);
    if(item.kind==='NOTE')actions.push(['KEEP','保留两份','Keep both',false]);
    actions.push(['SKIP','跳过','Skip',false]);
  }
  const decisions=new Set(['OVERWRITE','KEEP','SKIP']);
  const buttons=items=>items.map(([action,zh,en,disabled])=>`<button type="button" class="btn btn-sm" data-ie-focus="decision:${item.idx}:${action}" data-pdm-onclick="resolveIEConflict(${item.idx},'${action}')" ${disabled?'disabled':''}>${ieDemoText(zh,en)}</button>`).join('');
  const targets=actions.filter(([action])=>!decisions.has(action));
  return `<div data-pdm-backup-conflict-id="${item.sourceId}" data-pdm-demo-target-id="${item.targetSelected?item.candidates[item.targetIndex]?.id??'':''}">
    <div class="ie-comparison-heading"><strong>${escapeHtml(item.incoming.PLATFORM)}</strong><div class="ie-conflict-actions">${buttons(actions.filter(([action])=>decisions.has(action)))}</div></div>
    ${targets.length?`<div class="ie-comparison-targets ie-conflict-actions">${buttons(targets)}</div>`:''}
    ${item.status==='IDENTICAL'?`<div class="ie-conflict-help">${ieDemoText('业务内容相同，保留当前记录及其时间、排序。','Identical content. Keep the existing record, dates and order.')}</div>`:''}
    ${ieDemoClearsRecovery(item)?`<div class="ie-conflict-help recovery-backup-warning">${ieDemoText('覆盖会清空当前整组恢复码；跳过可保留。','Overwrite removes the existing recovery codes. Skip to keep them.')}</div>`:''}
    <div class="ie-comparison-columns"><div class="ie-conflict-side-title">${t('dialog.ie.conflict.current')}${current?` (${item.targetIndex+1}/${item.candidates.length})`:''}</div><div class="ie-conflict-side-title">${IE_STATE.sourceKind==='TRANSFER'?ieDemoText('接收资料','Received contents'):t('dialog.ie.conflict.incoming')}</div></div>
    ${fields.map((field,index)=>{
      const secret=['PASSWORD','TOTP','RECOVERY_CODES'].includes(field),visible=!secret||IE_STATE.revealed.has(field);
      const offsets=IE_STATE.offsets.get(field)||[0],offset=offsets.at(-1),chunk=ieDemoFieldChunk(item,field,offset);
      const referenceStart=index===ieDemoFields(item.kind,true).length?`<div class="ie-reference-group"><div class="ie-reference-title">${ieDemoText('参考信息','Reference information')}</div>`:'';
      return `${referenceStart}<section class="ie-comparison-field ${diff.includes(field)?'different':''} ${ieDemoFields(item.kind,true).includes(field)?'':'reference'}" data-pdm-backup-field="${field}"><div class="ie-field-heading"><span>${ieDemoLabel(field,item.kind)}${diff.includes(field)?ieDemoText(' · 不同',' · Different'):''}</span>
        ${secret?`<button type="button" class="ie-secret-toggle" aria-label="${visible?ieDemoText('隐藏两侧','Hide both sides'):ieDemoText('查看两侧','Read both sides')}" aria-pressed="${visible}" data-ie-focus="field:${field}" data-pdm-onclick="toggleIEConflictSecret(${item.idx},'${field}')">${svgIcon(visible?'eye-closed':'eye',16)}</button>`:''}</div>
        <div class="ie-conflict-compare">${chunk.values.map((value,index)=>`<div class="ie-conflict-value ${index?'incoming':'current'}">${index===0&&!current?ieDemoText(item.candidates.length?'请选择比较目标':'无目标记录',item.candidates.length?'Select a target':'No existing record'):visible?escapeHtml(value||'—'):ieDemoText('已隐藏','Hidden')}</div>`).join('')}</div>
        <div class="ie-field-navigation"><button type="button" class="btn btn-sm" data-ie-action="field-previous" data-ie-field="${field}" aria-label="${ieDemoText('上一片','Previous part')}" ${!visible||offsets.length===1?'disabled':''}>←</button><span class="ie-field-position">${visible&&(!chunk.done||offsets.length>1)?ieDemoText(`第 ${offsets.length} 片`,`Part ${offsets.length}`):''}</span><button type="button" class="btn btn-sm" data-ie-action="field-next" data-ie-field="${field}" aria-label="${ieDemoText('下一片','Next part')}" ${!visible||chunk.done?'disabled':''}>→</button></div></section>${index===fields.length-1?'</div>':''}`;
    }).join('')}</div>`;
}

function handleIEDemoAction(event){
  const target=event.target.closest('button');if(!target||target.disabled)return;
  if(target.dataset.pdmOnclick==='closeModal()')clearIEDemoReads();
  const action=target.dataset.ieAction;if(!action)return;
  event.preventDefault();
  if(action==='inspect'&&IE_STATE.activeId===Number(target.dataset.ieId)||
     action==='filter'&&IE_STATE.statusFilter===target.dataset.ieValue||
     action==='clear-field'&&IE_STATE.fieldFilter==='ALL')return;
  const group=IE_STATE.conflicts.filter(item=>item.kind===IE_STATE.kind),item=group.find(row=>row.idx===IE_STATE.activeId);
  if(['select','select-page','clear-selection','back'].includes(action))IE_STATE.batchMessage='';
  if(action==='select'){
    const id=Number(target.dataset.ieId);if(IE_STATE.selected.has(id))IE_STATE.selected.delete(id);else IE_STATE.selected.add(id);
    IE_STATE.confirmation=false;
  }else if(action==='select-page'){
    group.filter(row=>row.status==='CONFLICT'&&ieDemoMatches(row)).forEach(row=>IE_STATE.selected.add(row.idx));IE_STATE.confirmation=false;
  }else if(action==='clear-selection'){group.forEach(row=>IE_STATE.selected.delete(row.idx));IE_STATE.confirmation=false;
  }else if(action==='field-next'||action==='field-previous'){
    const field=target.dataset.ieField,offsets=IE_STATE.offsets.get(field)||[0],chunk=ieDemoFieldChunk(item,field,offsets.at(-1));
    if(action==='field-next'&&!chunk.done)offsets.push(chunk.next);else if(action==='field-previous'&&offsets.length>1)offsets.pop();
    IE_STATE.offsets.set(field,offsets);updateIEDemoField(item,field);return;
  }else{
    clearIEDemoReads();IE_STATE.confirmation=false;
    if(action==='inspect')IE_STATE.activeId=Number(target.dataset.ieId);
    else if(action==='filter')IE_STATE.statusFilter=target.dataset.ieValue;
    else if(action==='clear-field')IE_STATE.fieldFilter='ALL';
    else if(action==='back'){
      if(IE_STATE.sourceKind==='TRANSFER'&&(IE_STATE.kind==='PASSWORD'||IE_STATE.totalPw===0)){closeModal();return;}
      if(IE_STATE.kind==='PASSWORD'){
        IE_STATE.previewReady=false;switchIEMode('import');$('#ie-demo-back').hidden=true;
        $('#ie-conflict-count').textContent='';$('#ie-bulk-actions').replaceChildren();$('#ie-pager').replaceChildren();
        $('#ie-preview').innerHTML=`<span class="ie-preview-empty">${t('dialog.ie.preview.empty')}</span>`;return;
      }
      IE_STATE.kind='PASSWORD';IE_STATE.statusFilter='ALL';IE_STATE.fieldFilter='ALL';
    }
  }
  renderIEPreview();
}

function resolveIEConflict(idx,action){
  const item=IE_STATE.conflicts.find(row=>row.idx===idx);if(!item||item.status!=='CONFLICT')return;
  action=action.toUpperCase();clearIEDemoReads(action.endsWith('_TARGET'));IE_STATE.confirmation=false;IE_STATE.batchMessage='';
  if(action.endsWith('_TARGET')){
    if(action==='SELECT_TARGET')item.targetIndex=0;
    else item.targetIndex=Math.max(0,Math.min(item.candidates.length-1,item.targetIndex+(action==='NEXT_TARGET'?1:-1)));
    item.targetSelected=item.candidates.length>0;item.action='UNDECIDED';
  }else if(['SKIP','KEEP','OVERWRITE'].includes(action)&&!(action==='OVERWRITE'&&!item.targetSelected))item.action=action;
  renderIEPreview();
}

function resolveAllIEConflicts(action){
  if(!IE_STATE.confirmation)return;
  action=action.toUpperCase();clearIEDemoReads(false);
  let applied=0,remaining=0;
  for(const item of IE_STATE.conflicts.filter(row=>row.kind===IE_STATE.kind&&IE_STATE.selected.has(row.idx))){
    if(action==='OVERWRITE'&&item.candidates.length!==1){remaining++;continue;}
    item.action=action;IE_STATE.selected.delete(item.idx);applied++;
  }
  IE_STATE.batchMessage=ieDemoText(`本次批量已暂存 ${applied} 项决定，所选项目中 ${remaining} 项未更新，保留原决定。`,`This batch saved ${applied} decisions; ${remaining} selected items were unchanged and kept their previous decisions.`);
  if(IE_STATE.kind==='NOTE'&&action==='OVERWRITE'&&IE_STATE.conflicts.some(item=>item.kind==='NOTE'&&IE_STATE.selected.has(item.idx)&&item.candidates.length>1))IE_STATE.batchMessage=ieDemoText(`已暂存 ${applied} 项决定；${remaining} 项保留原决定。多候选记事请逐项选择目标并确认覆盖。`,`Saved ${applied} decisions; ${remaining} unchanged. For notes with multiple targets, choose a target and confirm overwrite individually.`);
  IE_STATE.confirmation=false;renderIEPreview();
}

function recomputeIEStats(){
  IE_STATE.added=0;IE_STATE.updated=0;IE_STATE.skipped=0;IE_STATE.unresolved=0;
  for(const item of IE_STATE.conflicts){
    if(item.status==='IDENTICAL'||item.action==='SKIP')IE_STATE.skipped++;
    else if(item.status==='NEW'||item.action==='KEEP')IE_STATE.added++;
    else if(item.action==='OVERWRITE')IE_STATE.updated++;
    else IE_STATE.unresolved++;
  }
}

function executeIEOperation(){
  if(IE_STATE.mode==='export'){
    if(IE_STATE.scope==='custom'&&!IE_STATE.exportSelection.length)return;
    if(!IE_STATE.path){showToast(t('dialog.ie.error.path'),'error');return;}
    if(!IE_STATE.password){showToast(t('dialog.ie.error.password'),'error');return;}
    if(IE_STATE.password!==IE_STATE.confirmPw){showToast(t('dialog.ie.error.mismatch'),'error');return;}
    showToast(t('dialog.ie.error.preview'),'error');return;
  }
  if(!IE_STATE.previewReady){showToast(t('dialog.ie.error.preview'),'error');return;}
  const pending=IE_STATE.conflicts.filter(item=>item.kind===IE_STATE.kind&&item.status==='CONFLICT'&&item.action==='UNDECIDED').length;
  if(pending){showToast(t('dialog.ie.error.undecided').replace('{n}',pending),'error');return;}
  clearIEDemoReads();
  if(IE_STATE.kind==='PASSWORD'&&IE_STATE.totalNote>0){IE_STATE.kind='NOTE';IE_STATE.statusFilter='ALL';IE_STATE.fieldFilter='ALL';IE_STATE.batchMessage='';renderIEPreview();return;}
  recomputeIEStats();
  if(IE_STATE.sourceKind==='TRANSFER')delete $('#active-modal').dataset.ieTransfer;
  closeModal();
  showToast(ieDemoText(`演示完成：新增 ${IE_STATE.added}、覆盖 ${IE_STATE.updated}、跳过 ${IE_STATE.skipped}。`,`Demo complete: add ${IE_STATE.added}, overwrite ${IE_STATE.updated}, skip ${IE_STATE.skipped}.`),'info');
}

function toggleIEConflictSecret(idx,field){
  if(idx!==IE_STATE.activeId||!['PASSWORD','TOTP','RECOVERY_CODES'].includes(field))return;
  if(IE_STATE.revealed.has(field)){
    IE_STATE.revealed.delete(field);clearTimeout(IE_STATE.timers.get(field));IE_STATE.timers.delete(field);IE_STATE.offsets.delete(field);
  }else{
    IE_STATE.revealed.add(field);IE_STATE.offsets.set(field,[0]);
    IE_STATE.timers.set(field,setTimeout(()=>{IE_STATE.revealed.delete(field);IE_STATE.offsets.delete(field);IE_STATE.timers.delete(field);if($('#ie-preview')&&IE_STATE.previewReady&&IE_STATE.activeId===idx)updateIEDemoField(IE_STATE.conflicts.find(item=>item.idx===idx),field);},30000));
  }
  updateIEDemoField(IE_STATE.conflicts.find(item=>item.idx===idx),field);
}

function setIEBusy(busy){
  const status = $('#ie-inline-status');
  const execute = $('#ie-execute-btn');
  if(status){
    status.style.display = busy ? '' : 'none';
    status.className = 'ie-inline-status';
    status.textContent = busy
      ? t(IE_STATE.mode==='export'?'dialog.ie.progress.export':'dialog.ie.progress.import')
      : '';
    if(busy) status.scrollIntoView({block:'nearest'});
  }
  if(execute) execute.disabled = busy;
  $$('#modal .modal-close,#modal .modal-footer button,#ie-mode-seg button,#modal .modal-body input,#modal .modal-body select')
    .forEach(el=>el.disabled=busy);
}

function checkDbPasswordMatch(){
  const newPw = $('#kf-new').value;
  const confirmPw = $('#kf-confirm').value;
  const indicator = $('#kf-indicator');
  const btn = $('#kf-confirm-btn');
  if(!newPw && !confirmPw){
    indicator.className = 'match-indicator empty';
    indicator.dataset.i18n = 'dialog.key.indicator.empty';
    indicator.textContent = t('dialog.key.indicator.empty');
    btn.disabled = false;
    btn.style.opacity = '1';
    return;
  }
  if(newPw === confirmPw){
    indicator.className = 'match-indicator match';
    indicator.dataset.i18n = 'dialog.key.indicator.match';
    indicator.textContent = t('dialog.key.indicator.match');
    btn.disabled = false;
    btn.style.opacity = '1';
  }else{
    indicator.className = 'match-indicator mismatch';
    indicator.dataset.i18n = 'dialog.key.indicator.mismatch';
    indicator.textContent = t('dialog.key.indicator.mismatch');
    btn.disabled = true;
    btn.style.opacity = '0.5';
  }
}

function clearDbKeyErrors(){
  const currentError = $('#kf-current-err');
  const formError = $('#kf-form-error');
  if(currentError){ currentError.textContent=''; currentError.classList.remove('show'); }
  if(formError){ formError.textContent=''; formError.classList.remove('show'); formError.style.display='none'; }
}

function confirmChangeDbPassword(){
  const current = $('#kf-current').value;
  if(current !== 'Demo@Pass2026'){
    const error = $('#kf-current-err');
    $('#kf-current').value = '';
    error.textContent = t('dialog.key.error.current');
    error.classList.add('show');
    $('#kf-current').focus();
    return;
  }
  if($('#kf-new').value !== $('#kf-confirm').value) return;
  closeModal();
  showToast(t('toast.keyChanged'),'success');
}

/* ============================================================
   初始化
   ============================================================ */
function renderAll(){renderVault();renderNotes();renderSecurity()}

// 主题初始化。视觉夹具可显式传 ?stage1-theme=light；正常打开仍默认深色。
const visualFixtureParams = new URLSearchParams(location.search);
if(visualFixtureParams.get('stage1-headless') === '1'){
  document.documentElement.classList.add('pdm-visual-static');
}
const stage1FixtureTheme = visualFixtureParams.get('stage1-theme');
setTheme(stage1FixtureTheme === 'light' ? 'light' : 'dark');

/* 未连接态初始化：禁用数据库依赖按钮 + 设置"当前数据库"为"未连接"。
   原型初始 state.connected=false，需在 DOM 就绪后立即调用，避免按钮可点击但实际无数据库。
   连接后由 connectDatabase() 调 updateDbDependentUI(true) 启用。 */
updateDbDependentUI(false);
updateCurrentDbInfo(null);

/* 阶段 3 的真实默认态截图夹具。仅显式 query 参数生效；正常打开原型仍保留
   公开演示路径、演示密码和演示背景数据。真实态使用调用方传入的默认路径、
   空主密码，并通过未连接分支重渲染背景计数，避免把演示数据误当产品默认值。 */
const visualFixtureState = visualFixtureParams.get('visual-state') || visualFixtureParams.get('stage3-state');
if(document.body.classList.contains('design-host')&&['updates-idle','updates-checking','updates-available','updates-empty-notes','updates-current','updates-ahead','updates-none','updates-failed'].includes(visualFixtureState)){
  const fixtureStatus={'updates-idle':'IDLE','updates-checking':'CHECKING','updates-available':'UPDATE_AVAILABLE','updates-empty-notes':'UPDATE_AVAILABLE','updates-current':'UP_TO_DATE','updates-ahead':'UP_TO_DATE','updates-none':'NO_RELEASE','updates-failed':'FAILED'}[visualFixtureState];
  const available=['UPDATE_AVAILABLE','FAILED'].includes(fixtureStatus);
  Object.assign(demoUpdateState,{status:fixtureStatus,available,lastAttemptMs:fixtureStatus==='IDLE'?0:1792368000000,
    releaseVersion:available?'1.2.0':visualFixtureState==='updates-ahead'?'0.9.0':fixtureStatus==='UP_TO_DATE'?window.PDM_HELP_CONTENT.version:'',releaseTag:available?'windows-v1.2.0':'',publishedAt:available?'2026-10-19T00:00:00Z':'',
    releaseNotes:available&&visualFixtureState!=='updates-empty-notes'?'公开演示版本说明。\n改善差异比较与导入操作体验。':'',resultAtMs:available?1792368000000:0,error:fixtureStatus==='FAILED'?'TIMEOUT':'NONE'});
  navigateTo('settings');
  document.getElementById('settings-group-updates').scrollIntoView({block:'start'});
}
const visualFixtureDbPath = visualFixtureParams.get('visual-db-path') || visualFixtureParams.get('stage3-db-path') || '';
const stage3FixtureState = visualFixtureState;
const NOTES_CARDS_VISUAL_STATES = new Set(['notes-cards','notes-cards-reading','notes-cards-editing']);
const isPrototypeHost = location.pathname.endsWith('/docs/platforms/windows/prototype.html');
/* 正常设计原型改用卡片；带其他 visual-state 的历史夹具继续保留各自的旧结构。 */
if(isPrototypeHost && (!visualFixtureState || NOTES_CARDS_VISUAL_STATES.has(visualFixtureState))){
  document.documentElement.dataset.pdmNotesCards = 'true';
}
if([
  'startup-default-path-empty-password',
  'startup-recent-empty',
  'startup-recent-one',
  'startup-recent-five',
  'startup-recent-hover',
  'startup-selected-existing',
  'startup-selected-missing',
  'startup-connecting',
  'startup-password-error',
  'startup-locked',
  'startup-path-not-found',
  'startup-parent-unwritable',
  'startup-corrupt',
  'startup-minimized-tools',
  'startup-lock-return-clean',
].includes(stage3FixtureState)){
  const fixturePath = visualFixtureDbPath;
  $('#db-path').value = fixturePath;
  $('#db-password').value = '';
  state.connected = false;
  renderAll();
  if([
    'startup-recent-empty',
    'startup-selected-existing',
    'startup-selected-missing',
    'startup-connecting',
    'startup-password-error',
    'startup-locked',
    'startup-path-not-found',
    'startup-parent-unwritable',
    'startup-corrupt',
    'startup-minimized-tools',
    'startup-lock-return-clean',
  ].includes(stage3FixtureState)){
    recents.splice(0, recents.length);
    renderRecents();
  }else if(stage3FixtureState === 'startup-recent-one'){
    recents.splice(1);
    renderRecents();
  }else if(stage3FixtureState === 'startup-recent-hover'){
    recents[0] = {
      ...recents[0],
      name:'family-password-manager-primary-database.db',
      path:'C:\\Users\\demo\\Documents\\Personal\\Archive\\2026\\Very Long Database Folder\\family-password-manager-primary-database.db',
    };
    renderRecents();
    const firstRecent = $('.recent-item');
    if(firstRecent) firstRecent.classList.add('stage3-hover');
  }
  if(stage3FixtureState === 'startup-connecting'){
    const startupCard = $('.startup-card');
    startupCard.classList.add('is-connecting');
    ['#db-path','#db-password','.browse-btn','.eye-btn','.connect-btn'].forEach(selector=>{
      $(selector).disabled = true;
    });
    $('.connect-btn').dataset.i18n = 'connection.connecting';
    $('.connect-btn').textContent = t('connection.connecting');
  }else if(stage3FixtureState === 'startup-password-error'){
    const feedback = $('#connection-feedback');
    feedback.className = 'connection-feedback error';
    feedback.textContent = t('connection.error.invalid_password').replace('{n}', '2');
  }else if(stage3FixtureState === 'startup-locked'){
    const startupCard = $('.startup-card');
    startupCard.classList.add('is-locked');
    const feedback = $('#connection-feedback');
    feedback.className = 'connection-feedback error';
    feedback.textContent = t('connection.error.locked_too_many');
  }else if([
    'startup-path-not-found',
    'startup-parent-unwritable',
    'startup-corrupt',
  ].includes(stage3FixtureState)){
    const errorKey = {
      'startup-path-not-found':'connection.error.path_not_found',
      'startup-parent-unwritable':'connection.error.permission_denied',
      'startup-corrupt':'connection.error.corrupt_or_unreadable',
    }[stage3FixtureState];
    const feedback = $('#connection-feedback');
    feedback.className = 'connection-feedback error';
    feedback.textContent = t(errorKey);
  }else if(stage3FixtureState === 'startup-minimized-tools'){
    navigateTo('tools');
    /* 顶栏初始节点仍带 connect 的 data-i18n；夹具显式同步最终导航语义。 */
    $('#topbar-title').dataset.i18n = 'topbar.title.tools';
    $('#topbar-title').textContent = t('topbar.title.tools');
  }else if(stage3FixtureState === 'startup-lock-return-clean'){
    /* 先注入上次会话残留，再走真实 lockApp()，证明锁定边界会清理。 */
    const feedback = $('#connection-feedback');
    feedback.className = 'connection-feedback error';
    feedback.textContent = 'STALE FEEDBACK MUST NOT SURVIVE';
    $('#db-password').value = 'stale-secret';
    $('#db-password').type = 'text';
    state.connected = true;
    $('#startup-page').classList.add('hidden');
    lockApp();
  }
}

function applyNotesCardsVisualFixture(fixtureState){
  notes.splice(0,notes.length,...NOTES_CARDS_FIXTURE.map(note=>({...note})));
  state.connected = true;
  state.startupMinimized = false;
  state.noteFilter = 'all';
  state.search = '';
  state.expandedId = null;
  state.notesCardOpenId = fixtureState === 'notes-cards-reading' || fixtureState === 'notes-cards-editing' ? 103 : null;
  state.notesCardEditId = fixtureState === 'notes-cards-editing' ? 103 : null;
  state.notesCardDraft = null;
  document.documentElement.dataset.pdmNotesCards = 'true';
  $('#startup-page').classList.add('hidden');
  $('#startup-page').classList.remove('minimized');
  $('#startup-minimized-bar')?.classList.remove('show');
  $('#status-dot').classList.add('connected');
  $('#status-text').removeAttribute('data-i18n');
  $('#status-text').innerHTML = `${t('status.connect.prefix')}<strong class="pdm-inline-1552366efe">notes-cards-demo.db</strong>`;
  $('#page-settings')?.classList.add('connected');
  updateDbDependentUI(true);
  updateCurrentDbInfo('notes-cards-demo.db');
  navigateTo('notes');
}

if(NOTES_CARDS_VISUAL_STATES.has(visualFixtureState)){
  applyNotesCardsVisualFixture(visualFixtureState);
}

const notesCardsResizeObserver = new ResizeObserver(()=>{
  if(isNotesCardsDemo() && state.connected && notesCardsColumnCount() !== state.notesCardsColumns) renderNotes();
  else layoutNotesCards($('#notes-list'));
});
// 观察尺寸由窗口决定的滚动视口，避免重分列改变列表高度后触发观察循环。
notesCardsResizeObserver.observe($('.content'));
document.fonts?.ready?.then(()=>layoutNotesCards($('#notes-list')));

/* M4.1 设计基准。该夹具只由显式 visual-state URL 触发；生产
   pdm://app 资源路由拒绝 query，因此不能把它变成 Bridge 或数据权威。 */
function applyM4VisualFixture(fixtureState){
  document.documentElement.dataset.pdmLaunchMode = 'm4-isolated';
  document.documentElement.dataset.pdmM4State =
    fixtureState === 'm4-empty-vault' ? 'unlocked' : 'locked';
  passwords.splice(0,passwords.length);
  notes.splice(0,notes.length);
  recents.splice(0,recents.length);
  state.connected = fixtureState === 'm4-empty-vault';
  state.startupMinimized = false;
  state.currentNav = 'vault';
  state.expandedId = null;
  state.splitSelectedId = null;
  state.passwordVisible = {};
  state.autoLock.enabled = false;
  stopIdleCheck();
  if(state.clipboardTimer){
    clearInterval(state.clipboardTimer);
    state.clipboardTimer = null;
  }

  const path = $('#db-path');
  const password = $('#db-password');
  const startup = $('#startup-page');
  const bar = $('#startup-minimized-bar');
  const card = $('.startup-card');
  const connect = $('.connect-btn');
  const eye = $('#startup-eye');
  const feedback = $('#connection-feedback');
  path.value = visualFixtureDbPath;
  path.readOnly = true;
  path.setAttribute('aria-readonly','true');
  password.value = '';
  setStaticPasswordVisibility('db-password','startup-eye',false);
  renderRecents();
  feedback.className = 'connection-feedback';
  feedback.textContent = '';
  card.classList.remove('is-connecting','is-locked');
  connect.dataset.i18n = 'startup.button.connect';
  connect.textContent = t('startup.button.connect');
  if(bar) bar.classList.remove('show');

  if(state.connected){
    startup.classList.add('hidden');
    startup.classList.remove('minimized');
    updateDbDependentUI(false);
    navigateTo('vault');
    renderVault();
    $('#status-dot').classList.add('connected');
    const statusText = $('#status-text');
    statusText.removeAttribute('data-i18n');
    statusText.replaceChildren(
      document.createTextNode(t('status.connect.prefix'))
    );
    const strong = document.createElement('strong');
    strong.className = 'pdm-inline-1552366efe';
    strong.textContent = 'm4_empty.db';
    statusText.append(strong);
    updateCurrentDbInfo('m4_empty.db');
  }else{
    startup.classList.remove('hidden','minimized');
    updateDbDependentUI(false);
    updateCurrentDbInfo(null);
    navigateTo('vault');
    renderVault();
    const title = $('#topbar-title');
    title.dataset.i18n = 'topbar.title.connect';
    title.textContent = t('topbar.title.connect');
    $('#status-dot').classList.remove('connected');
    const statusText = $('#status-text');
    statusText.dataset.i18n = 'status.disconnected';
    statusText.textContent = t('status.disconnected');
  }

  const busy = fixtureState === 'm4-connecting';
  if(busy){
    card.classList.add('is-connecting');
    connect.dataset.i18n = 'connection.connecting';
    connect.textContent = t('connection.connecting');
  }
  document.querySelectorAll(
    'button,input,select,textarea,[data-pdm-onclick]'
  ).forEach(control=>{
    let enabled = false;
    if(control.matches('.titlebar-ctrl')){
      enabled = true;
    }else if(
      !state.connected
      && (
        control.id === 'db-path'
        || control.id === 'db-password'
        || control.matches('.browse-btn')
        || control.matches('.eye-btn')
      )
    ){
      enabled = !busy;
    }else if(
      state.connected
      && control.matches('[data-pdm-onclick="lockApp()"]')
    ){
      enabled = true;
    }
    if(
      control instanceof HTMLButtonElement
      || control instanceof HTMLInputElement
      || control instanceof HTMLSelectElement
      || control instanceof HTMLTextAreaElement
    ){
      control.disabled = !enabled;
    }
    control.dataset.pdmM4Disabled = enabled ? 'false' : 'true';
    control.setAttribute(
      'aria-disabled',
      enabled ? 'false' : 'true'
    );
    if(control.hasAttribute('tabindex')){
      control.tabIndex = enabled ? 0 : -1;
    }
  });
}

if([
  'm4-startup-locked',
  'm4-connecting',
  'm4-empty-vault',
  'm4-lock-return',
].includes(stage3FixtureState)){
  applyM4VisualFixture(stage3FixtureState);
}

/* 阶段 3 / 9.3 主窗口框架夹具。使用公开演示数据进入真实 connectDatabase()
   分支，再固定导航、搜索或剪贴板状态；不会改变普通打开原型的行为。 */
if(['shell-vault','shell-notes-search','shell-status-countdown'].includes(stage3FixtureState)){
  $('#db-path').value = visualFixtureDbPath || 'C:\\Users\\demo\\Documents\\ui_verify.db';
  $('#db-password').value = '';
  connectDatabase();
  setTimeout(()=>{
    // 视觉回归夹具固定连接点在脉冲动画的满不透明帧，避免截图时刻造成像素漂移。
    $('#status-dot').style.animation = 'none';
    $('#status-dot').style.opacity = '1';
    if(stage3FixtureState === 'shell-notes-search'){
      navigateTo('notes');
      setGlobalSearchValue('WiFi');
      handleSearch('WiFi');
    }else{
      navigateTo('vault');
    }
    if(stage3FixtureState === 'shell-status-countdown'){
      if(state.clipboardTimer){clearInterval(state.clipboardTimer);state.clipboardTimer=null}
      state.clipboardSeconds = 4;
      updateClipboardStatus();
    }
    $('#toast-container').innerHTML = '';
  },350);
}

if(['recovery-codes','recovery-codes-split'].includes(visualFixtureState)){
  passwords.splice(0,passwords.length,{
    id:1,platform:'招商银行',account:'public@example.invalid',password:'Public-Recovery-42!',notes:'',
    recovery_codes:[{value:'PUBLIC-RC-0001',used:false},{value:'PUBLIC-RC-0002',used:false}],
    updated_at:'2026-10-03',password_changed_at:'2026-10-03',strength:'strong',is_favorite:false,
  });
  $('#db-path').value=visualFixtureDbPath||'C:\\Public\\recovery-demo.db';
  $('#db-password').value='';
  connectDatabase();
  setTimeout(()=>{
    state.viewMode=visualFixtureState==='recovery-codes-split'?'split':'list';
    $$('.view-switcher .btn-icon').forEach(button=>{
      const active=button.dataset.view===state.viewMode;
      button.classList.toggle('active',active);
      button.setAttribute('aria-pressed',String(active));
    });
    state.expandedId=state.viewMode==='list'?1:null;
    state.splitSelectedId=state.viewMode==='split'?1:null;
    clearDemoRecovery();
    renderVault();
    $('#status-dot').style.animation='none';
    $('#status-dot').style.opacity='1';
    $('#toast-container').replaceChildren();
    document.documentElement.classList.add('pdm-visual-static');
  },350);
}

/* 阶段 4 对话框确定性夹具。只在显式 visual-state 下打开真实原型对话框；
   普通演示不受影响。10.1 保留公共骨架三态，10.2 保留密码对话框八态，
   10.3 追加记事新增、inline 编辑、失败与删除确认态；10.4 追加改密
   默认、匹配、清空、不匹配和两类可恢复错误态；10.5 追加导入导出
   默认/冲突/损坏/进度与修复引导主步骤/继续/完成态。 */
if([
  'dialog-skeleton-standard',
  'dialog-skeleton-wide-en',
  'dialog-skeleton-overflow',
  'dialog-password-add-default',
  'dialog-password-edit-prefill',
  'dialog-password-validation',
  'dialog-password-long-visible-en',
  'dialog-password-favorite-totp',
  'dialog-password-regenerated',
  'dialog-password-save-failure',
  'dialog-password-delete-confirm',
  'dialog-note-add-default',
  'dialog-note-validation',
  'dialog-note-long-favorite-en',
  'dialog-note-save-failure',
  'dialog-note-inline-prefill',
  'dialog-note-inline-validation',
  'dialog-note-delete-confirm',
  'dialog-key-default',
  'dialog-key-match',
  'dialog-key-clear',
  'dialog-key-mismatch',
  'dialog-key-current-error',
  'dialog-key-reencrypt-error',
  'dialog-ie-export-default',
  'dialog-ie-import-conflicts',
  'dialog-ie-damaged-error',
  'dialog-ie-export-progress',
  'dialog-fix-guide',
  'dialog-fix-progress',
  'dialog-fix-complete',
  'dialog-ie-export-default-en',
  'dialog-fix-guide-en',
].includes(visualFixtureState)){
  const stage4EnglishFixture = [
    'dialog-skeleton-wide-en','dialog-password-long-visible-en','dialog-note-long-favorite-en',
    'dialog-ie-export-default-en','dialog-fix-guide-en'
  ].includes(visualFixtureState);
  if(stage4EnglishFixture) setLang('en');
  $('#db-path').value = visualFixtureDbPath || 'C:\\Users\\demo\\Documents\\ui_verify.db';
  $('#db-password').value = '';
  connectDatabase();
  setTimeout(()=>{
    setLang(stage4EnglishFixture ? 'en' : 'zh');
    $('#status-dot').style.animation = 'none';
    $('#status-dot').style.opacity = '1';
    navigateTo('vault');
    $('#toast-container').innerHTML = '';
    if(['dialog-skeleton-standard','dialog-password-add-default'].includes(visualFixtureState)){
      openAddPasswordDialog();
    }else if(visualFixtureState === 'dialog-skeleton-wide-en'){
      openAddNoteDialog();
    }else if(visualFixtureState === 'dialog-skeleton-overflow'){
      const rows = Array.from({length:24},(_,index)=>
        `<div class="stage4-overflow-line pdm-inline-0e55dca444">`+
        `${String(index+1).padStart(2,'0')} · 这是确定性的长正文验证内容；正文必须独立滚动，标题区和操作区始终可见。</div>`
      ).join('');
      openModal(`
        <div class="modal-header">
          <div class="modal-title">固定标题区 · 长内容滚动验证</div>
          <button class="modal-close" data-pdm-onclick="closeModal()">✕</button>
        </div>
        <div class="modal-body">
          <input class="modal-field-input" placeholder="正文首字段（随正文滚动）">
          ${rows}
        </div>
        <div class="modal-footer">
          <div class="modal-footer-right">
            <button class="btn btn-sm" data-pdm-onclick="closeModal()">取消</button>
            <button class="btn btn-primary btn-sm" data-pdm-onclick="closeModal()">继续</button>
          </div>
        </div>
      `,{wide:true});
      const body = document.querySelector('#active-modal .modal-body');
      if(body) body.scrollTop = 0;
    }else if(visualFixtureState === 'dialog-password-edit-prefill'){
      openEditPasswordDialog(1);
    }else if(visualFixtureState === 'dialog-password-validation'){
      openAddPasswordDialog();
      saveNewPassword();
    }else if(visualFixtureState === 'dialog-password-long-visible-en'){
      openEditPasswordDialog(1);
      $('#mf-platform').value = 'Enterprise Identity and Privacy Management Platform — Extremely Long Record Name';
      $('#mf-account').value = 'security-and-privacy-team+long-account@example.test';
      $('#mf-password').value = 'Stage4-Long-Visible-Password-With-Spaces-42!';
      $('#mf-password').type = 'text';
      $('#mf-notes').value = Array.from({length:14},(_,i)=>`Long note line ${String(i+1).padStart(2,'0')} — deterministic overflow content.`).join('\n');
      $('#mf-notes').scrollTop = 0;
    }else if(visualFixtureState === 'dialog-password-favorite-totp'){
      openEditPasswordDialog(1);
    }else if(visualFixtureState === 'dialog-password-regenerated'){
      openEditPasswordDialog(1);
      $('#mf-password').value = 'Stage4-Generated-Password-42!';
      $('#mf-password').type = 'text';
    }else if(visualFixtureState === 'dialog-password-save-failure'){
      openAddPasswordDialog();
      $('#mf-platform').value = '数据库失败演示';
      const totpField = $('#mf-totp').closest('.modal-field');
      totpField.insertAdjacentHTML('beforeend',`<div class="modal-form-error">${t('dialog.pwd.error.save_failed')}</div>`);
    }else if(visualFixtureState === 'dialog-password-delete-confirm'){
      openPasswordDeleteConfirm(1);
    }else if(visualFixtureState === 'dialog-note-add-default'){
      navigateTo('notes');
      openAddNoteDialog();
    }else if(visualFixtureState === 'dialog-note-validation'){
      navigateTo('notes');
      openAddNoteDialog();
      saveNewNote();
    }else if(visualFixtureState === 'dialog-note-long-favorite-en'){
      navigateTo('notes');
      openAddNoteDialog();
      $('#nf-title').value = 'Offline recovery checklist — encrypted personal archive';
      $('#nf-content').value = Array.from({length:30},(_,i)=>
        `Recovery step ${String(i+1).padStart(2,'0')} — deterministic long-form encrypted note content.`
      ).join('\n');
      updateLongTextHint($('#nf-content'),'nf-content-scroll-hint');
      $('#nf-favorite').classList.add('active');
      $('#nf-content').scrollTop = 0;
    }else if(visualFixtureState === 'dialog-note-save-failure'){
      navigateTo('notes');
      openAddNoteDialog();
      $('#nf-title').value = '数据库失败后保留的记事';
      $('#nf-content').value = '正文仍完整保留，可在原地重试。';
      $('#nf-favorite').classList.add('active');
      $('#nf-content').closest('.modal-field').insertAdjacentHTML(
        'beforeend', `<div class="modal-form-error">${t('dialog.note.error.save_failed')}</div>`
      );
    }else if(visualFixtureState === 'dialog-note-inline-prefill'){
      navigateTo('notes');
      notes.splice(1);
      state.expandedId = notes[0].id + 1000;
      renderNotes();
    }else if(visualFixtureState === 'dialog-note-inline-validation'){
      navigateTo('notes');
      notes.splice(1);
      state.expandedId = notes[0].id + 1000;
      renderNotes();
      $('#note-title-1').value = '   ';
      updateNoteSaveBtnState(1);
      saveNote(1);
    }else if(visualFixtureState === 'dialog-note-delete-confirm'){
      navigateTo('notes');
      notes.splice(1);
      state.expandedId = null;
      renderNotes();
      deleteNote(1);
    }else if(visualFixtureState.startsWith('dialog-key-')){
      navigateTo('settings');
      openChangeDbPasswordDialog();
      if(visualFixtureState !== 'dialog-key-default') $('#kf-current').value='Demo@Pass2026';
      if(visualFixtureState === 'dialog-key-match'){
        $('#kf-new').value='New-Database-Key-2026!';
        $('#kf-confirm').value='New-Database-Key-2026!';
        checkDbPasswordMatch();
      }else if(visualFixtureState === 'dialog-key-mismatch'){
        $('#kf-new').value='New-Database-Key-2026!';
        $('#kf-confirm').value='Different-Key-2026!';
        checkDbPasswordMatch();
      }else if(visualFixtureState === 'dialog-key-current-error'){
        $('#kf-current').value='Wrong-Current-Key';
        $('#kf-new').value='New-Database-Key-2026!';
        $('#kf-confirm').value='New-Database-Key-2026!';
        checkDbPasswordMatch();
        confirmChangeDbPassword();
      }else if(visualFixtureState === 'dialog-key-reencrypt-error'){
        $('#kf-new').value='New-Database-Key-2026!';
        $('#kf-confirm').value='New-Database-Key-2026!';
        checkDbPasswordMatch();
        $('#kf-form-error').textContent=t('dialog.key.error.failed');
        $('#kf-form-error').classList.add('show');
        $('#kf-form-error').style.display='block';
      }
    }else if(visualFixtureState.startsWith('dialog-ie-')){
      const ieFixtureState=visualFixtureState.replace(/-en$/,'');
      navigateTo('settings');
      openImportExportDialog('export');
      if(ieFixtureState === 'dialog-ie-export-default'){
        // 默认清洁导出态。
      }else if(ieFixtureState === 'dialog-ie-export-progress'){
        $('#ie-path').value='C:\\Users\\demo\\Documents\\pdm_backup_20260719.pdmbackup.json';
        IE_STATE.path=$('#ie-path').value;
        $('#ie-password').value='Stage4-Backup-Key-2026!';
        $('#ie-confirm').value='Stage4-Backup-Key-2026!';
        IE_STATE.password=$('#ie-password').value;
        IE_STATE.confirmPw=$('#ie-confirm').value;
        checkIEPasswordMatch();
        setIEBusy(true);
      }else{
        switchIEMode('import');
        $('#ie-path').value='C:\\Users\\demo\\Documents\\pdm_backup_20260718.pdmbackup.json';
        IE_STATE.path=$('#ie-path').value;
        $('#ie-password').value='Stage4-Backup-Key-2026!';
        IE_STATE.password=$('#ie-password').value;
        if(ieFixtureState === 'dialog-ie-damaged-error'){
          const status=$('#ie-inline-status');
          status.style.display='';
          status.className='ie-inline-status error';
          status.textContent='文件格式不正确，无法解析';
        }else{
          prepareIEDemoComparison();
        }
      }
    }else if(['dialog-fix-guide','dialog-fix-guide-en'].includes(visualFixtureState)){
      navigateTo('security');
      state.fixQueue=[
        {id:2,types:['weak']},
        {id:1,types:['weak','duplicate','stale']},{id:3,types:['duplicate']},{id:4,types:['stale']}
      ];
      state.fixIndex=1; state.fixResults={0:'done'};
      showFixGuide();
    }else if(visualFixtureState === 'dialog-fix-progress'){
      navigateTo('vault');
      state.fixQueue=[
        {id:1,types:['weak']},{id:2,types:['stale']},
        {id:3,types:['duplicate']},{id:4,types:['weak']}
      ];
      state.fixIndex=1; state.fixResults={0:'done'};
      onPasswordSaved();
    }else if(visualFixtureState === 'dialog-fix-complete'){
      navigateTo('vault');
      state.fixQueue=[{id:1},{id:2},{id:3},{id:4}];
      state.fixIndex=4;
      state.fixResults={0:'done',1:'done',2:'done',3:'skipped'};
      showFixCompleteDialog();
    }
    /* 确定性视觉夹具不保留光标闪烁、过渡或入场动画；真实产品交互不受影响。 */
    document.documentElement.classList.add('pdm-visual-static');
    if(document.activeElement && document.activeElement.blur) document.activeElement.blur();
  },350);
}

/* M4.5-08 候选产品视觉总比对夹具。
   这些夹具只在独立 Chromium 设计宿主收到显式 visual-state URL 时生效；
   pdm://app 的固定资源路由拒绝 query，因此候选产品仍只能经 Bridge/core/
   native 状态机到达同态。夹具只使用公开、固定的数据，并保留未裁剪画布。 */
const M45_PARITY_PREFIX = 'm4-parity-';
const M45_PARITY_STATES = new Set([
  'm4_1_01_startup_locked','m4_1_02_connecting',
  'm4_1_03_empty_vault','m4_1_04_lock_return',
  'm4_2_01_recent_cancel','m4_2_02_wrong_password_retry',
  'm4_2_03_locked_target','m4_2_04_corrupt_database',
  'm4_2_05_alternate_empty','m4_2_06_lock_return_recents',
  'm4_3_02_masked','m4_3_02_revealed','m4_3_02_clipboard',
  'm4_3_02_empty','m4_3_02_clipboard_error','m4_3_02_locked',
  'm4_3_03_create_dialog','m4_3_03_save_failure',
  'm4_3_03_platform_conflict','m4_3_03_created',
  'm4_3_04_name_selected','m4_3_04_split_name_selected',
  'm4_3_05_edit_dialog','m4_3_05_platform_conflict',
  'm4_3_05_revision_conflict','m4_3_06_delete_confirm',
  'm4_3_06_delete_success','m4_3_06_delete_failure',
  'm4_3_07_vault_list_dark_zh','m4_3_07_search_filter_sort_light_en',
  'm4_3_07_split_detail_dark_zh','m4_4_01_note_list_dark_zh',
  'm4_4_01_note_long_modal_dark_zh','m4_4_01_note_saved_detail_light_en',
  'm4_4_02_change_key_auth_dark_zh',
  'm4_4_02_change_key_committing_dark_zh',
  'm4_4_02_change_key_unchanged_dark_zh',
  'm4_5_01_locked_settings_dark_zh',
  'm4_5_01_locked_settings_auto_light_en',
  'm4_5_01_connected_vault_dark_zh','m4_5_01_restart_settings_light_en',
  'm4_5_02_connected_settings_to_tray_dark_zh',
  'm4_5_02_connected_settings_exit_light_en',
  '01_auto_lock_policy_enabled_zh_dark','02_auto_locked_zh_dark',
  '03_suspend_locked_visible_zh_dark','04_suspend_locked_tray_restore_zh_dark',
  '01_100_startup_zh_dark','02_125_vault_zh_dark',
  '03_150_notes_en_light','04_150_note_modal_en_light',
  '01_zh_dark_secret_before_failure','03_zh_dark_rebuilt_locked',
  '04_en_light_note_before_failure','04_en_light_settings',
]);

function m45ParityReplace(target, values){
  target.splice(0,target.length,...values.map(value=>({...value})));
}

function m45ParityCommonPasswords(){
  return [
    {id:1,platform:'GitHub',account:'alice@example.com',password:'M4-Shared-Public-Secret!',notes:'主账号，仅用于临时验收',updated_at:'2026-08-02',password_changed_at:'2026-08-02',strength:'strong',is_favorite:true},
    {id:2,platform:'GitLab',account:'bob@example.com',password:'M4-Shared-Public-Secret!',notes:'共享密码重复组',updated_at:'2026-07-29',password_changed_at:'2026-07-29',strength:'strong',is_favorite:false},
    {id:3,platform:'Bank',account:'finance-user',password:'weak',notes:'财务账号',updated_at:'2026-07-30',password_changed_at:'2026-07-30',strength:'weak',is_favorite:false},
    {id:4,platform:'邮箱',account:'unicode@example.cn',password:'Mailbox-Public-2026!',notes:'中文平台名',updated_at:'2026-08-03',password_changed_at:'2026-08-03',strength:'strong',is_favorite:true},
    {id:5,platform:'Archive',account:'',password:'',notes:'',updated_at:'2026-08-01',password_changed_at:'2026-08-01',strength:'weak',is_favorite:false},
  ];
}

function m45ParityCommonNotes(){
  const longBody = Array.from({length:30},(_,index)=>
    `恢复步骤 ${String(index+1).padStart(2,'0')}：离线检查、校验并记录结果。`
  ).join('\n')+'\nPRIVATE-FIXTURE-TAIL-MUST-NOT-BATCH-RETURN';
  return [
    {id:1,title:'离线恢复清单',content:longBody,updated_at:'2026-07-31',is_favorite:true},
    {id:2,title:'短记事',content:'第一行\n第二行',updated_at:'2026-08-01',is_favorite:false},
    {id:3,title:'空正文',content:'',updated_at:'2026-08-02',is_favorite:true},
    {id:4,title:'Unicode Café',content:'正文搜索标记 résumé 与 数据完整性',updated_at:'2026-08-03',is_favorite:false},
  ];
}

function m45ParityDataset(kind){
  if(kind==='create') return [
    {id:1,platform:'Straße',account:'existing@example.invalid',password:'Existing-Public-2026!',notes:'Unicode casefold fixture',updated_at:'2026-08-03',password_changed_at:'2026-08-03',strength:'strong',is_favorite:false},
    {id:2,platform:'Existing',account:'',password:'',notes:'',updated_at:'2026-08-02',password_changed_at:'2026-08-02',strength:'weak',is_favorite:true},
  ];
  if(kind==='edit') return [
    {id:1,platform:'Edit Target',account:'initial@example.invalid',password:'Initial-Public-2026!',notes:'initial public notes',totp_secret:'JBSWY3DPEHPK3PXP',updated_at:'2026-08-03',password_changed_at:'2026-08-03',strength:'strong',is_favorite:true},
    {id:2,platform:'Straße',account:'conflict@example.invalid',password:'Conflict-Public-2026!',notes:'Unicode casefold fixture',updated_at:'2026-08-02',password_changed_at:'2026-08-02',strength:'strong',is_favorite:false},
  ];
  if(kind==='delete') return ['Delete Target','Revision Target','Failure Target','Replay Target','Lock Ticket Target'].map((platform,index)=>({
    id:index+1,platform,account:`public-${index+1}@example.invalid`,
    password:`Public-Delete-${index+1}-2026!`,notes:`public delete fixture ${index+1}`,
    updated_at:`2026-08-0${5-index}`,password_changed_at:`2026-08-0${5-index}`,
    strength:'strong',is_favorite:false,
  }));
  return m45ParityCommonPasswords();
}

function m45ParityM4305Record(stage){
  const record=passwords.find(value=>value.id===1);
  if(!record) return;
  if(stage==='platform_conflict'){
    Object.assign(record,{
      platform:'Edit Target',account:'account-only@example.invalid',
      password:'x',notes:'account and notes changed',totp_secret:'',
      updated_at:'2026-08-05',password_changed_at:'2026-08-05',
      strength:'weak',is_favorite:true,
    });
    return;
  }
  Object.assign(record,{
    platform:'Edit Target Renamed',account:'concurrent-account',
    password:'dirty-secret',notes:'concurrent-notes',
    totp_secret:'GEZDGNBVGY3TQOJQ',updated_at:'2026-08-05',
    password_changed_at:'2026-08-05',strength:'weak',is_favorite:false,
  });
}

function m45ParityDbName(fixtureId){
  const prefixes=[
    ['m4_3_02_','m4_secret_copy.db'],
    ['m4_3_03_','m4_create.db'],
    ['m4_3_04_','m4_vault_name.db'],
    ['m4_3_05_','m4_edit.db'],
    ['m4_3_06_','m4_delete.db'],
    ['m4_3_07_','m4_vault_read_rebind.db'],
    ['m4_4_01_','m4_note_long_body.db'],
    ['m4_4_02_','c49_product.db'],
    ['m4_5_01_','m4_settings.db'],
    ['m4_5_02_','m4_close.db'],
    ['01_auto_lock_','m4_lock.db'],
    ['02_auto_locked_','m4_lock.db'],
    ['03_suspend_locked_','m4_lock.db'],
    ['04_suspend_locked_','m4_lock.db'],
    ['01_100_startup_','m4_dpi.db'],
    ['02_125_vault_','m4_dpi.db'],
    ['03_150_notes_','m4_dpi.db'],
    ['04_150_note_modal_','m4_dpi.db'],
    ['01_zh_dark_secret_','m4_renderer.db'],
    ['03_zh_dark_rebuilt_','m4_renderer.db'],
    ['04_en_light_note_','m4_renderer.db'],
    ['04_en_light_settings','m4_native_quickbar.db'],
  ];
  const match=prefixes.find(([prefix])=>fixtureId.startsWith(prefix));
  return match?match[1]:'m4_visual_parity.db';
}

function m45ParitySuppressDeferredTotpDetail(){
  /* M4.3-05 only integrates hasTotp editing intent. C21/C22 detail-code
     display remains deferred, so its parity states must not project the
     prototype-only live TOTP row behind the editor. */
  document.querySelectorAll('.detail-value.totp').forEach(value=>{
    value.closest('.detail-row')?.remove();
  });
}

function m45ParityProjectDisconnectedSettings(){
  state.connected=false;
  $('#page-settings')?.classList.remove('connected');
  $('#status-dot')?.classList.remove('connected');
  const status=$('#status-text');
  if(status) status.textContent=t('status.disconnected');
  updateDbDependentUI(false);
  updateCurrentDbInfo(null);
  navigateTo('settings');
}

function m45ParityProjectChangeKeySubmitting(){
  document.documentElement.classList.add('pdm-parity-change-key-submitting');
  document.querySelectorAll(
    'button,input,select,textarea,[data-pdm-onclick],[data-pdm-recent-action]'
  ).forEach(control=>{
    if(
      control.matches('.titlebar-ctrl,#theme-btn,#lang-segment button')
      || control.closest('#theme-segment')
      || control.id==='lang-segment'
    ) return;
    if(
      control instanceof HTMLButtonElement
      || control instanceof HTMLInputElement
      || control instanceof HTMLSelectElement
      || control instanceof HTMLTextAreaElement
    ) control.disabled=true;
    control.dataset.pdmM4Disabled='true';
    control.setAttribute('aria-disabled','true');
    if(control.hasAttribute('tabindex')) control.tabIndex=-1;
  });
}

function m45ParityConnect(kind='common',withNotes=false,dbName='m4_visual_parity.db'){
  m45ParityReplace(passwords,m45ParityDataset(kind));
  m45ParityReplace(notes,withNotes?m45ParityCommonNotes():[]);
  state.passwords=passwords;
  state.notes=notes;
  state.connected=true;
  state.startupMinimized=false;
  state.currentNav='vault';
  state.viewMode='list';
  state.sortMode='updated';
  state.filter='all';
  state.noteFilter='all';
  state.search='';
  state.expandedId=null;
  state.splitSelectedId=null;
  state.passwordVisible={};
  $('#startup-page').classList.add('hidden');
  $('#startup-page').classList.remove('minimized');
  $('#startup-minimized-bar')?.classList.remove('show');
  $('#page-settings')?.classList.add('connected');
  $('#status-dot').classList.add('connected');
  $('#status-dot').style.animation='none';
  $('#status-dot').style.opacity='1';
  $('#status-text').innerHTML=`${t('status.connect.prefix')}<strong class="pdm-inline-1552366efe">${escapeHtml(dbName)}</strong>`;
  updateDbDependentUI(true);
  updateCurrentDbInfo(dbName);
  navigateTo('vault');
  renderAll();
  $('#toast-container').innerHTML='';
}

function m45ParitySelectText(selector,text=''){
  const node=Array.from(document.querySelectorAll(selector)).find(value=>
    !text || value.textContent===text
  );
  if(!node) return;
  const range=document.createRange();
  range.selectNodeContents(node);
  const selection=window.getSelection();
  selection.removeAllRanges();
  selection.addRange(range);
}

function m45ParityFieldError(anchorSelector,id,text){
  const anchor=document.querySelector(anchorSelector);
  if(!anchor) return null;
  let error=document.querySelector('#'+id);
  if(!error){
    error=document.createElement('div');
    error.id=id;
    error.className='modal-field-error show';
    anchor.insertAdjacentElement('afterend',error);
  }
  error.textContent=text;
  error.classList.add('show');
  return error;
}

function m45ParityAppendToast(container,text,type='success'){
  while(container.children.length>=MAX_VISIBLE_TOASTS){
    dismissToast(container.firstElementChild);
  }
  const toast=document.createElement('div');
  toast.className='toast '+type;
  const icon=(
    type==='success' ? svgIcon('check',16) :
    type==='error' ? '✕' :
    type==='warning' ? svgIcon('warning',16) :
    svgIcon('info',16)
  );
  toast.innerHTML=`<span class="toast-icon">${icon}</span><span>${escapeHtml(text)}</span>`;
  toast.style.animation='none';
  container.appendChild(toast);
}

function m45ParityToast(text,type='success'){
  const container=$('#toast-container');
  if(container) m45ParityAppendToast(container,text,type);
}

function m45ParityMarkDisabled(control){
  if(!control) return;
  document.documentElement.classList.add('pdm-parity-current-capabilities');
  if(
    control instanceof HTMLButtonElement
    || control instanceof HTMLInputElement
    || control instanceof HTMLSelectElement
    || control instanceof HTMLTextAreaElement
  ) control.disabled=true;
  control.dataset.pdmM4Disabled='true';
  control.setAttribute('aria-disabled','true');
  if(control.hasAttribute('tabindex')) control.tabIndex=-1;
}

function m45ParityBlurAfterDeferredModalFocus(){
  setTimeout(()=>document.activeElement?.blur(),180);
}

function m45ParityProjectCurrentSettingsCapabilities(){
  m45ParityMarkDisabled($('#global-search'));
  [
    'settings.autofill.name',
    'settings.view.default.name',
    'settings.sidebar.text.name',
    'settings.clipboard.clear.name',
    'settings.clipboard.duration.name',
    'settings.db.ie.name',
    'settings.security.stale.name',
  ].forEach(key=>{
    const row=document.querySelector(`[data-i18n="${key}"]`)?.closest('.setting-row');
    row?.querySelectorAll(
      'button,input,select,textarea,[data-pdm-onclick]'
    ).forEach(m45ParityMarkDisabled);
  });
}

function m45ParityProjectCurrentNoteDetailCapabilities(noteId){
  const title=$(`#note-title-${noteId}`);
  const content=$(`#note-content-${noteId}`);
  [title,content].forEach(control=>{
    if(!control) return;
    control.readOnly=true;
    control.setAttribute('aria-readonly','true');
  });
  const detail=content?.closest('.note-detail-inner');
  detail?.querySelectorAll('.note-actions button').forEach(m45ParityMarkDisabled);
}

function m45ParityLock(toastKey){
  lockApp();
  /* The product H06 boundary clears the native clipboard without routing the
     demo-only "clipboard cleared" feedback through the renderer.  Keep the
     design fixture on that same public frame before adding the actual lock
     reason Toast. */
  restoreClipboardStatus();
  $('#toast-container').innerHTML='';
  setTimeout(()=>{
    $('#toast-container').innerHTML='';
    if(toastKey) m45ParityToast(t(toastKey),'info');
  },310);
}

function m45ParityLockedDatabase(dbName,toastKey,explicitPath=''){
  const dbPath=explicitPath || visualFixtureDbPath || `C:\\M4-Visual\\databases\\${dbName}`;
  recents.splice(0,recents.length,{
    name:dbName,path:dbPath,last_connected:Date.now(),icon:'database'
  });
  renderRecents();
  const path=$('#db-path');
  if(path){path.value=dbPath;path.scrollLeft=0;}
  m45ParityLock(toastKey);
}

function m45ParityStartupDatabase(dbName){
  const dbPath=visualFixtureDbPath || `C:\\M4-Visual\\databases\\${dbName}`;
  recents.splice(0,recents.length);
  renderRecents();
  const path=$('#db-path');
  if(path){path.value=dbPath;path.scrollLeft=0;}
  state.connected=false;
  m45ParityLock();
}

function m45ParitySetTrayCloseBehavior(behavior){
  const buttons=Array.from(document.querySelectorAll('#tray-close-segment button'));
  buttons.forEach((button,index)=>{
    button.classList.toggle('active',behavior==='tray'?index===0:index===1);
  });
}

function m45ParityScrollSettingsGroup(selector){
  document.fonts.ready.then(()=>{
    requestAnimationFrame(()=>requestAnimationFrame(()=>{
      const target=document.querySelector(selector)?.closest('.settings-group');
      const content=document.querySelector('.content');
      if(!target || !content) return;
      const contentRect=content.getBoundingClientRect();
      const targetRect=target.getBoundingClientRect();
      const targetDocumentTop=targetRect.top-contentRect.top+content.scrollTop;
      const maximum=content.scrollHeight-content.clientHeight;
      const desired=Math.min(targetDocumentTop,maximum);
      content.scrollTop=Math.round(desired*window.devicePixelRatio)/window.devicePixelRatio;
    }));
  });
}

function m45ParityFocusSettingsControl(selector){
  requestAnimationFrame(()=>{
    const target=document.querySelector(selector);
    target?.focus();
    /* Qt WebEngine's programmatic focus settles eight logical pixels farther
       into the shared scroller than desktop Chrome on this 1200x800 canvas. */
    const content=document.querySelector('.content');
    if(content) content.scrollTop+=8;
    target?.blur();
  });
}

function m45ParityNavigateConnectedSettings(dbName){
  navigateTo('settings');
  updateCurrentDbInfo(dbName);
  m45ParityProjectCurrentSettingsCapabilities();
}

function m45ParityM42Path(name){
  const primary=visualFixtureDbPath || 'C:\\M4-Visual\\databases\\m4_existing.db';
  return primary.replace(/m4_existing\.db$/i,name);
}

function applyM45ParityM41(fixtureId){
  setLang('zh');
  const createdPath=visualFixtureDbPath || 'C:\\M4-Visual\\databases\\m4_created.db';
  const defaultPath=createdPath.replace(/m4_created\.db$/i,'pdm.db');
  if(fixtureId==='m4_1_03_empty_vault'){
    m45ParityConnect('common',false,'m4_created.db');
    passwords.splice(0,passwords.length);
    notes.splice(0,notes.length);
    state.passwords=passwords;
    state.notes=notes;
    renderAll();
    document.documentElement.classList.add('pdm-visual-static');
    if(document.activeElement?.blur) document.activeElement.blur();
    return;
  }
  applyM4VisualFixture(
    fixtureId==='m4_1_02_connecting' ? 'm4-connecting' : 'm4-startup-locked'
  );
  const path=$('#db-path');
  path.readOnly=false;
  path.removeAttribute('aria-readonly');
  path.value=fixtureId==='m4_1_01_startup_locked' ? defaultPath : createdPath;
  path.scrollLeft=0;
  if(fixtureId==='m4_1_04_lock_return'){
    recents.splice(0,recents.length,{
      name:'m4_created.db',path:createdPath,last_connected:Date.now(),icon:'database'
    });
    renderRecents();
    m45ParityToast('密码库已手动锁定','info');
    setTimeout(()=>path.focus({preventScroll:true}),140);
  }
  const connect=$('.connect-btn');
  if(fixtureId!=='m4_1_02_connecting'){
    connect.disabled=false;
    connect.dataset.pdmM4Disabled='false';
    connect.setAttribute('aria-disabled','false');
  }
  document.documentElement.classList.add('pdm-visual-static');
  if(document.activeElement?.blur) document.activeElement.blur();
}

function applyM45ParityM42(fixtureId){
  setLang('zh');
  if(fixtureId==='m4_2_05_alternate_empty'){
    m45ParityConnect('common',false,'m4_alternate.db');
    passwords.splice(0,passwords.length);
    notes.splice(0,notes.length);
    state.passwords=passwords;
    state.notes=notes;
    renderAll();
    document.documentElement.classList.add('pdm-visual-static');
    if(document.activeElement?.blur) document.activeElement.blur();
    return;
  }

  applyM4VisualFixture('m4-startup-locked');
  const path=$('#db-path');
  path.readOnly=false;
  path.removeAttribute('aria-readonly');
  const initialPath=m45ParityM42Path('pdm.db');
  const primaryPath=m45ParityM42Path('m4_existing.db');
  const alternatePath=m45ParityM42Path('m4_alternate.db');
  const corruptPath=m45ParityM42Path('m4_corrupt.db');
  recents.splice(0,recents.length,
    {name:'m4_existing.db',path:primaryPath,last_connected:Date.now(),icon:'database'},
    {name:'m4_alternate.db',path:alternatePath,last_connected:Date.now(),icon:'database'}
  );
  if(fixtureId==='m4_2_06_lock_return_recents'){
    recents.reverse();
  }
  renderRecents();
  path.value=(
    fixtureId==='m4_2_01_recent_cancel' ? initialPath :
    fixtureId==='m4_2_04_corrupt_database' ? corruptPath :
    fixtureId==='m4_2_06_lock_return_recents' ? alternatePath :
    primaryPath
  );
  path.scrollLeft=0;
  const feedback=$('#connection-feedback');
  feedback.className='connection-feedback';
  feedback.textContent='';
  if(fixtureId==='m4_2_02_wrong_password_retry'){
    feedback.classList.add('error');
    feedback.textContent='主密码错误，还可尝试 2 次。';
  }else if(fixtureId==='m4_2_03_locked_target'){
    feedback.classList.add('error');
    feedback.textContent='密码错误次数过多，该数据库已锁定 24 小时。';
  }else if(fixtureId==='m4_2_04_corrupt_database'){
    feedback.classList.add('error');
    feedback.textContent='数据库文件已损坏、无法读取或在选择后发生变化。';
  }else if(fixtureId==='m4_2_06_lock_return_recents'){
    m45ParityToast('密码库已手动锁定','info');
    setTimeout(()=>path.focus({preventScroll:true}),140);
  }
  const connect=$('.connect-btn');
  connect.disabled=false;
  connect.dataset.pdmM4Disabled='false';
  connect.setAttribute('aria-disabled','false');
  document.querySelectorAll('[data-pdm-recent-action]').forEach(button=>{
    button.dataset.pdmM4Disabled='false';
    button.setAttribute('aria-disabled','false');
  });
  document.documentElement.classList.add('pdm-visual-static');
  if(document.activeElement?.blur) document.activeElement.blur();
}

function applyM45ParityFixture(fixtureId){
  if(fixtureId.startsWith('m4_1_')){
    applyM45ParityM41(fixtureId);
    return;
  }
  if(fixtureId.startsWith('m4_2_')){
    applyM45ParityM42(fixtureId);
    return;
  }
  const english=/(?:^|_)en(?:_|$)/.test(fixtureId);
  setLang(english?'en':'zh');
  const withNotes=fixtureId.includes('note') || fixtureId.includes('notes');
  let dataset='common';
  if(fixtureId.startsWith('m4_3_03_')) dataset='create';
  else if(fixtureId.startsWith('m4_3_05_')) dataset='edit';
  else if(fixtureId.startsWith('m4_3_06_')) dataset='delete';
  m45ParityConnect(dataset,withNotes,m45ParityDbName(fixtureId));

  if(fixtureId==='m4_3_02_masked' || fixtureId==='m4_5_01_connected_vault_dark_zh' || fixtureId==='02_125_vault_zh_dark'){
    state.expandedId=1; renderVault();
    if(fixtureId==='02_125_vault_zh_dark'){
      const input=$('#global-search');
      setGlobalSearchValue('PDM-M4.5-04-PUBLIC-VAULT-FOCUS');
      setTimeout(()=>input.focus({preventScroll:true}),140);
    }
  }else if(fixtureId==='m4_3_02_revealed'){
    state.expandedId=1; state.passwordVisible[1]=true; renderVault();
  }else if(fixtureId==='01_zh_dark_secret_before_failure'){
    state.expandedId=1; state.passwordVisible[1]=true; renderVault();
    m45ParityToast(t('vault.detail.password')+t('toast.copied.suffix'));
  }else if(fixtureId==='m4_3_02_clipboard'){
    state.expandedId=1; renderVault();
    m45ParityToast(t('vault.detail.account')+t('toast.copied.suffix'));
    m45ParityToast(t('vault.detail.password')+t('toast.copied.suffix'));
  }else if(fixtureId==='m4_3_02_empty'){
    state.expandedId=5; renderVault();
  }else if(fixtureId==='m4_3_02_clipboard_error'){
    state.expandedId=1; renderVault();
    m45ParityToast(state.lang==='zh'?'剪贴板暂时不可用，请稍后重试。':'The clipboard is temporarily unavailable. Try again.','error');
  }else if(fixtureId==='m4_3_02_locked'){
    m45ParityLockedDatabase('m4_secret_copy.db',undefined,visualFixtureDbPath);
    setTimeout(()=>{
      $('#toast-container').innerHTML='';
      m45ParityToast('密码库已手动锁定','info');
    },320);
  }else if(fixtureId==='m4_3_03_create_dialog'){
    openAddPasswordDialog();
  }else if(fixtureId==='m4_3_03_save_failure'){
    navigateTo('tools');
    openAddPasswordDialog();
    $('#mf-platform').value='Retry Entry';
    $('#mf-account').value='public-retry-account';
    $('#mf-password').value='Retry-Public-2026!';
    $('#mf-notes').value='public retry notes';
    $('#mf-favorite').classList.add('active');
    m45ParityFieldError('#mf-totp','mf-save-err',t('dialog.pwd.error.save_failed'));
    $('#mf-save').disabled=true;
    m45ParityToast(t('toast.gen.generatedNew'));
    m45ParityToast(t('toast.gen.generated'));
    m45ParityBlurAfterDeferredModalFocus();
  }else if(fixtureId==='m4_3_03_platform_conflict'){
    navigateTo('tools');
    openAddPasswordDialog();
    $('#mf-platform').value='  STRASSE  ';
    $('#mf-account').value='different-account';
    $('#mf-password').value='Conflict-Public-2026!';
    $('#mf-notes').value='public conflict notes';
    $('#mf-totp').value='JBSW Y3DP-EHPK 3PXP';
    m45ParityFieldError('#mf-platform','mf-platform-err',t('dialog.pwd.error.duplicate'));
    $('#mf-save').disabled=true;
    m45ParityToast(t('toast.gen.generatedNew'));
    m45ParityToast(t('toast.gen.generated'));
    m45ParityToast(t('toast.pwd.added'));
    m45ParityBlurAfterDeferredModalFocus();
  }else if(fixtureId==='m4_3_03_created'){
    navigateTo('tools');
    $('#gen-output').textContent='';
    m45ParityMarkDisabled(document.querySelector('[data-pdm-onclick="copyGenerated()"]'));
    m45ParityMarkDisabled(document.querySelector('[data-pdm-onclick="saveGenerated()"]'));
    m45ParityToast(t('toast.pwd.added'));
    m45ParityToast(t('toast.pwd.added'));
    m45ParityToast(t('toast.pwd.added'));
  }else if(fixtureId==='m4_3_04_name_selected'){
    renderVault(); m45ParitySelectText('.platform-name-text','GitHub');
  }else if(fixtureId==='m4_3_04_split_name_selected'){
    switchView('split'); state.splitSelectedId=null; renderVault();
    m45ParitySelectText('.split-name-text','GitHub');
    m45ParityToast(t('toast.theme.dark'),'info');
    m45ParityToast(t('toast.theme.light'),'info');
  }else if(fixtureId==='m4_3_05_edit_dialog'){
    state.expandedId=1; renderVault(); openEditPasswordDialog(1);
    m45ParitySuppressDeferredTotpDetail();
    m45ParityBlurAfterDeferredModalFocus();
  }else if(fixtureId==='m4_3_05_platform_conflict'){
    m45ParityM4305Record('platform_conflict');
    state.expandedId=1; renderVault(); openEditPasswordDialog(1);
    m45ParitySuppressDeferredTotpDetail();
    $('#mf-platform').value='  STRASSE  ';
    $('#mf-account').value='dirty-account';
    $('#mf-password').value='dirty-secret';
    $('#mf-notes').value='dirty-notes';
    $('#mf-totp').value='GEZDGNBVGY3TQOJQ';
    $('#mf-favorite').classList.remove('active');
    m45ParityFieldError('#mf-platform','mf-platform-err',t('dialog.pwd.error.duplicate'));
    $('#mf-save').disabled=true;
    m45ParityBlurAfterDeferredModalFocus();
  }else if(fixtureId==='m4_3_05_revision_conflict'){
    m45ParityM4305Record('revision_conflict');
    state.expandedId=null; renderVault(); openEditPasswordDialog(1);
    m45ParitySuppressDeferredTotpDetail();
    $('#mf-platform').value='Unsaved Local';
    $('#mf-account').value='unsaved-account';
    $('#mf-password').value='unsaved-password';
    $('#mf-notes').value='unsaved-notes';
    m45ParityFieldError('#mf-totp','mf-save-err',t('dialog.pwd.error.revision_conflict'));
    $('#mf-edit-actions').hidden=false;
    $('#mf-edit-reload').hidden=false;
    $('#mf-edit-reload').disabled=false;
    $('#mf-save').disabled=true;
    m45ParityBlurAfterDeferredModalFocus();
  }else if(fixtureId==='m4_3_06_delete_confirm'){
    state.expandedId=1; renderVault(); openPasswordDeleteConfirm(1);
  }else if(fixtureId==='m4_3_06_delete_success'){
    passwords.splice(0,1); renderVault();
    m45ParityToast(t('toast.deleted.prefix')+'Delete Target');
  }else if(fixtureId==='m4_3_06_delete_failure'){
    passwords.splice(0,1);
    const revision=passwords.find(value=>value.id===2);
    if(revision){
      revision.account='changed-before-confirm@example.invalid';
      revision.updated_at='2026-08-05';
    }
    state.expandedId=3; renderVault(); openPasswordDeleteConfirm(3);
    const body=document.querySelector('#active-modal .modal-body');
    const error=document.createElement('div');
    error.id='m4-delete-error';
    error.className='modal-form-error';
    error.textContent='无法访问该位置，请检查读取或写入权限后重试。';
    body?.append(error);
    m45ParityToast(t('toast.deleted.prefix')+'Delete Target');
    m45ParityToast('记录已发生变化，列表将自动刷新。','error');
    m45ParityBlurAfterDeferredModalFocus();
  }else if(fixtureId==='m4_3_07_vault_list_dark_zh'){
    renderVault();
  }else if(fixtureId==='m4_3_07_search_filter_sort_light_en'){
    state.search='git'; state.filter='duplicate'; state.sortMode='name'; renderVault();
    setGlobalSearchValue('git');
    document.querySelector('#filter-chips [data-filter="duplicate"]')?.classList.add('active');
    const sortLabel=document.querySelector('#sort-trigger-label');
    if(sortLabel) sortLabel.textContent=t('vault.sort.name');
  }else if(fixtureId==='m4_3_07_split_detail_dark_zh'){
    selectSort('name');
    switchView('split');
    selectSplit(1);
    Array.from(document.querySelectorAll('.split-item')).find(item=>
      item.querySelector('.split-name-text')?.textContent==='GitHub'
    )?.focus();
  }else if(fixtureId==='m4_4_01_note_list_dark_zh'){
    navigateTo('notes'); renderNotes();
  }else if(fixtureId==='m4_4_01_note_long_modal_dark_zh'){
    navigateTo('notes'); state.expandedId=1001; renderNotes();
    const detail=$('#note-content-1');
    if(detail){detail.scrollTop=detail.scrollHeight;updateLongTextHint(detail,'note-scroll-hint-1');}
    openAddNoteDialog();
    $('#nf-title').value='  新增长正文  ';
    $('#nf-content').value='  保留开头空白\n'+Array.from({length:32},(_,index)=>`新增步骤 ${String(index+1).padStart(2,'0')}：只在临时加密库中验证长正文。`).join('\n')+'\nPRIVATE-CREATED-TAIL-MUST-ROUNDTRIP  ';
    $('#nf-favorite').classList.add('active');
    setTimeout(()=>{
      const area=$('#nf-content');
      area.scrollTop=(area.scrollHeight-area.clientHeight)/2;
      updateLongTextHint(area,'nf-content-scroll-hint');
      area.focus({preventScroll:true});
    },140);
  }else if(fixtureId==='m4_4_01_note_saved_detail_light_en'){
    notes.push({id:5,title:'新增长正文',content:'  保留开头空白\n'+Array.from({length:32},(_,index)=>`新增步骤 ${String(index+1).padStart(2,'0')}：只在临时加密库中验证长正文。`).join('\n')+'\nPRIVATE-CREATED-TAIL-MUST-ROUNDTRIP  ',updated_at:'2026-08-03',is_favorite:true});
    navigateTo('notes'); state.expandedId=1005; renderNotes();
    m45ParityToast(t('toast.note.dialogAdded'));
    requestAnimationFrame(()=>{
      const area=$('#note-content-5');
      if(area){area.scrollTop=(area.scrollHeight-area.clientHeight)/2;updateLongTextHint(area,'note-scroll-hint-5');}
    });
  }else if(fixtureId.startsWith('m4_4_02_change_key_')){
    navigateTo('settings'); openChangeDbPasswordDialog();
    $('#kf-current').value='M4-C49-Public-Old-2026!';
    $('#kf-new').value='M4-C49-Public-Final-2026!';
    $('#kf-confirm').value='M4-C49-Public-Final-2026!';
    checkDbPasswordMatch();
    if(fixtureId.includes('auth_')){
      m45ParityFieldError('#kf-current','kf-current-err',t('dialog.key.error.current'));
      $('#kf-current').value='';
    }else if(fixtureId.includes('committing_')){
      $('#kf-confirm-btn').disabled=true;
      $('#kf-confirm-btn').textContent='正在提交原子更改…';
      m45ParityProjectChangeKeySubmitting();
    }else if(fixtureId.includes('unchanged_')){
      $('#kf-form-error').textContent=t('dialog.key.error.unchanged');
      $('#kf-form-error').classList.add('show');
      $('#kf-form-error').style.display='block';
      setTimeout(()=>document.activeElement?.blur(),140);
    }
  }else if(fixtureId==='m4_5_01_locked_settings_dark_zh' || fixtureId==='m4_5_01_locked_settings_auto_light_en'){
    m45ParityProjectDisconnectedSettings();
    setTheme(fixtureId.includes('auto_')?'auto':'dark');
  }else if(fixtureId==='m4_5_01_restart_settings_light_en'){
    m45ParityProjectDisconnectedSettings(); setTheme('light');
  }else if(fixtureId==='m4_5_02_connected_settings_to_tray_dark_zh'){
    m45ParityNavigateConnectedSettings('m4_close.db'); setTheme('dark');
    m45ParitySetTrayCloseBehavior('tray');
    m45ParityToast('设置未保存，原设置未改变，请重试。','error');
    m45ParityFocusSettingsControl('#tray-close-segment');
  }else if(fixtureId==='m4_5_02_connected_settings_exit_light_en'){
    m45ParityNavigateConnectedSettings('m4_close.db'); setTheme('light');
    m45ParitySetTrayCloseBehavior('exit');
    m45ParityFocusSettingsControl('#tray-close-segment');
  }else if(fixtureId==='01_auto_lock_policy_enabled_zh_dark'){
    m45ParityNavigateConnectedSettings('m4_lock.db'); setTheme('dark');
    state.autoLock.enabled=true; state.autoLock.timeout=1;
    const toggle=$('#autolock-toggle'); toggle?.classList.add('on');
    if($('#autolock-num')) $('#autolock-num').value='1';
    m45ParityScrollSettingsGroup('#autolock-toggle');
  }else if(fixtureId==='02_auto_locked_zh_dark'){
    m45ParityLockedDatabase('m4_lock.db','toast.autolocked');
  }else if(fixtureId==='03_suspend_locked_visible_zh_dark' || fixtureId==='04_suspend_locked_tray_restore_zh_dark'){
    m45ParityLockedDatabase('m4_lock.db','toast.suspendLocked');
  }else if(fixtureId==='01_100_startup_zh_dark'){
    m45ParityStartupDatabase('m4_dpi.db');
  }else if(fixtureId==='03_150_notes_en_light'){
    navigateTo('notes'); state.expandedId=1001; renderNotes();
    m45ParityProjectCurrentNoteDetailCapabilities(1);
    requestAnimationFrame(()=>{
      const area=$('#note-content-1');
      if(area){area.scrollTop=0;updateLongTextHint(area,'note-scroll-hint-1');}
    });
  }else if(fixtureId==='04_150_note_modal_en_light'){
    navigateTo('notes'); state.expandedId=1001; renderNotes(); openAddNoteDialog();
    $('#nf-title').value='M4.5-04 Public DPI Draft';
    $('#nf-content').value=Array.from({length:28},(_,index)=>`M4.5-04 public DPI line ${String(index+1).padStart(2,'0')}`).join('\n');
    requestAnimationFrame(()=>{
      const area=$('#nf-content');
      area.scrollTop=(area.scrollHeight-area.clientHeight)/2;
      updateLongTextHint(area,'nf-content-scroll-hint');
    });
    setTimeout(()=>document.activeElement?.blur(),160);
  }else if(fixtureId==='03_zh_dark_rebuilt_locked'){
    m45ParityLockedDatabase(
      'm4_renderer.db',
      undefined,
      'C:\\M4-Isolated\\databases\\m4_renderer.db'
    );
  }else if(fixtureId==='04_en_light_note_before_failure'){
    navigateTo('notes'); state.expandedId=1001; renderNotes(); openAddNoteDialog();
    $('#nf-title').value='M4.5-05 Public Renderer Draft';
    $('#nf-content').value=Array.from(
      {length:28},
      (_,index)=>`M4.5-05 public renderer line ${String(index+1).padStart(2,'0')}`
    ).join('\n');
    setTimeout(()=>{
      const area=$('#nf-content');
      area.scrollTop=Math.floor((area.scrollHeight-area.clientHeight)/2);
      updateLongTextHint(area,'nf-content-scroll-hint');
      document.activeElement?.blur();
    },140);
  }else if(fixtureId==='04_en_light_settings'){
    m45ParityNavigateConnectedSettings('m4_native_quickbar.db'); setTheme('light');
    m45ParitySetTrayCloseBehavior('exit');
    const toggle=$('#quickbar-toggle');
    toggle?.classList.add('on');
    toggle?.setAttribute('aria-checked','true');
    syncQuickBarAutohide(45);
    state.quickBarHotkey='Ctrl+Alt+A';
    resetHotkeyDisplay();
    document.fonts.ready.then(()=>{
      requestAnimationFrame(()=>{
        const row=$('#quickbar-hotkey-row');
        const content=document.querySelector('.content');
        if(!row || !content) return;
        /* Avoid the two Chromium shells' different scrollIntoView rounding:
           center the same row in the real scrollport, then align to one
           physical pixel.  This changes scroll only, never candidate DOM. */
        const contentRect=content.getBoundingClientRect();
        const rowRect=row.getBoundingClientRect();
        const rowDocumentTop=rowRect.top-contentRect.top+content.scrollTop;
        const centered=rowDocumentTop+rowRect.height/2-content.clientHeight/2;
        content.scrollTop=Math.round(centered*window.devicePixelRatio)/window.devicePixelRatio;
      });
    });
  }

  document.documentElement.classList.add('pdm-visual-static');
  if(document.activeElement && document.activeElement.blur) document.activeElement.blur();
}

if(visualFixtureState?.startsWith(M45_PARITY_PREFIX)){
  const parityId=visualFixtureState.slice(M45_PARITY_PREFIX.length);
  if(M45_PARITY_STATES.has(parityId)){
    setTimeout(()=>applyM45ParityFixture(parityId),350);
  }
}

// 标尺刻度生成
buildRulers();

(() => {
  // 显示字段不是可编辑控件；Ctrl+A 必须限定在当前字段，不能落到文档全选。
  const TEXT_DISPLAY_SELECTOR = [
    '#gen-output', '.detail-value > .text',
    '.platform-name-text', '.platform-account', '.split-name-text',
    '.note-card-title', '.note-card-preview', '.note-card-body',
    '#page-settings .db-info', '.setting-name', '.setting-desc',
  ].join(',');

  function textDisplayFor(node) {
    const element = node instanceof Element ? node : node?.parentElement;
    return element?.closest(TEXT_DISPLAY_SELECTOR) || null;
  }

  document.addEventListener('keydown', (event) => {
    if (
      event.defaultPrevented || event.isComposing || event.keyCode === 229 ||
      !event.ctrlKey || event.altKey || event.shiftKey || event.metaKey ||
      event.key.toLowerCase() !== 'a'
    ) return;
    const active = document.activeElement;
    // 输入、只读输入及数值框保留浏览器原生的框内全选。
    if (
      (active instanceof HTMLInputElement && !active.disabled &&
        !['button', 'checkbox', 'color', 'file', 'hidden', 'image', 'radio',
          'range', 'reset', 'submit'].includes(active.type)) ||
      (active instanceof HTMLTextAreaElement && !active.disabled) ||
      active?.isContentEditable
    ) return;
    event.preventDefault();
    const selection = window.getSelection();
    const focusedDisplay = textDisplayFor(active);
    const anchorDisplay = textDisplayFor(selection?.anchorNode);
    const display = focusedDisplay || (
      (active === document.body || active === document.documentElement ||
        active?.id === 'main-app') &&
      anchorDisplay === textDisplayFor(selection?.focusNode) ? anchorDisplay : null
    );
    if (
      !selection || !display?.isConnected || !display.getClientRects().length ||
      getComputedStyle(display).visibility !== 'visible'
    ) return;
    const range = document.createRange();
    range.selectNodeContents(display);
    selection.removeAllRanges();
    selection.addRange(range);
  });
})();
