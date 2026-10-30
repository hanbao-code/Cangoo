/* 正式窗口与公开原型共用视图；设备、配对及完成状态始终由调用方投影。 */
(() => {
  'use strict';

  const TEXT = {
    ZH: {
      title:'设备传输', subtitle:'在两台设备间传送资料，接收后比较并导入。',
      sendSubtitle:'发送当前密码库的副本，由对方比较后导入。', receiveSubtitle:'接收另一台设备的资料，比较后再导入当前密码库。',
      steps:['选择设备','配对连接','发送资料','传输结果'],
      role:'这台设备要做什么？', send:'发送资料', sendHint:'发送当前已解锁密码库的副本',
      receive:'接收资料', receiveHint:'接收后比较，确认后再导入',
      transport:'连接方式', lan:'同一局域网', lanHint:'两台设备连接同一 Wi-Fi 或局域网',
      bluetooth:'蓝牙', bluetoothHint:'先在系统设置中完成两台设备的配对',
      setupHint:'请先在另一台设备打开小仓，并解锁需要使用的密码库。',
      find:'查找附近设备', wait:'等待发送方', nearby:'选择接收设备',
      nearbyHint:'请让对方选择“接收资料”和“局域网”，并点击开始等待。',
      nearbyBluetooth:'选择已配对设备', nearbyBluetoothHint:'请让对方在小仓选择“接收资料”和“蓝牙”，并点击开始等待。列表中的设备可能暂时不在线。',
      empty:'暂未找到设备。确认对方已开始等待；仍未找到时，可输入对方地址连接。', retry:'重新查找', restart:'重新开始',
      emptyBluetooth:'没有已配对设备。请先在系统蓝牙设置中配对，再重新查找。',
      manual:'未找到设备？输入地址连接', manualHint:'在接收端的“等待发送方”页面查看地址，只需填写地址，无需端口。',
      address:'接收端地址', connectAddress:'连接', addressBusy:'查找中', addressSearching:'正在查找这个地址上的小仓…',
      invalidAddress:'请输入当前局域网中接收设备的有效 IPv4 地址。',
      addressNotFound:'未找到设备。请核对地址后重试，或重新查找附近设备；网络不允许互访时可改用蓝牙。',
      localAddress:'这台设备的地址', localAddressHint:'请选择与发送端处于同一网络的地址。通常先尝试 Wi-Fi 或有线网络。',
      addressWifi:'Wi-Fi', addressEthernet:'有线网络', addressOther:'其他连接', otherAddresses:'其他网络地址（{count}）',
      noLocalAddress:'未找到可用的局域网地址。请检查网络连接，或改用蓝牙。',
      networkTitle:'局域网授权', networkAllow:'允许本地设备连接', networkRevoke:'撤销局域网授权', networkCheck:'重新检查',
      networkPolicy:'仅调整此小仓的局域网规则。小仓日常以普通权限运行，授权或撤销时由 Windows 确认。',
      securityPromptHint:'安全软件询问时，请核对本次操作后仅允许本次。',
      networkRequired:'点击“允许本地设备连接”以启用局域网传输。',
      networkChecking:'正在读取局域网授权状态…',
      networkAuthorizing:'请在 Windows 提示中确认授权。',
      networkRevoking:'请在 Windows 提示中确认撤销授权。',
      networkReady:'已允许此小仓的局域网连接。',
      networkBlocked:'Windows 规则或策略仍阻止连接，请检查小仓规则或改用蓝牙。',
      networkFailed:'未能确认授权，请重试或改用蓝牙。',
      networkRequiredError:'请先允许本地设备连接，再开始局域网传输。',
      waiting:'等待发送方连接', waitingHint:'请在发送端选择这台设备，并输入下面的配对码。',
      copyCode:'复制配对码', copied:'已复制', copyFailed:'复制失败，请重试。',
      pairingLabel:'临时配对码', pairingExpiry:'配对码10分钟内有效，成功配对后失效。等待时仍按正常规则锁库。',
      inputCode:'输入接收端的配对码', inputCodeHint:'请输入接收端显示的8位数字。接收端没有配对码时，请先升级两端小仓。',
      invalidCode:'请输入8位数字配对码。', pairingFailed:'配对未完成。请核对接收端仍在等待及配对码后重试。', pair:'配对连接',
      connecting:'正在配对连接', connectingHint:'正在验证配对码，请稍候。',
      peer:'对方设备', verify:'是否允许这台设备发送资料？', verifyHint:'设备名称仅供辨认。确认后等待对方发送，收齐资料再比较导入。',
      approve:'允许发送', waitingApproval:'配对成功，等待接收端确认。',
      receiveReview:'等待对方发送', receiveReviewHint:'请在对方设备选择资料并发送。', receiveNote:'收齐并校验后，将打开差异比较，由你决定导入哪些资料。',
      localFrom:'本机密码库（发送）', peerFrom:'对方密码库（发送）', localTo:'本机密码库（接收）', peerTo:'对方密码库（接收）', receiveScope:'本次接收范围',
      review:'确认这次传输', reviewHint:'资料只会沿下面的方向发送。', from:'发送密码库', to:'接收密码库',
      scope:'传输哪些资料？', all:'全部', passwords:'仅密码', notes:'仅记事', custom:'自定义', chooseRecords:'选择记录',
      reviewNote:'发送端资料保持不变。接收端完整接收后，可逐项比较并决定如何导入。',
      preparing:'正在准备所选资料…', start:'发送资料', awaitingOffer:'等待发送方选择范围并发送资料。',
      awaitingAccept:'正在等待接收端准备完成…', accepted:'等待发送方传输资料。', ready:'接收端已确认，可以发送资料。',
      transferring:'正在传输资料', transferringHint:'请让两台设备保持在前台，直到接收完成。',
      transferNote:'传输期间暂停软件自动锁库。主动锁库、切库、退出，或系统锁屏、睡眠会终止本次传输。',
      checking:'正在校验接收的资料…', checkingTitle:'正在校验资料', receiptTitle:'等待对方校验完成', receipt:'资料已发送，正在等待对方确认完整接收。',
      sent:'对方已完整接收', sentHint:'你现在可以离开。对方将继续比较和导入。',
      received:'资料已完整接收', receivedHint:'即将打开差异比较。发送端现在可以离开。',
      failed:'未确认传输完成', cancelled:'本次传输已取消', cancelledHint:'需要时可重新开始，并使用新的配对码。',
      cancel:'取消', close:'关闭', continue:'继续',
      protected:'已配对连接', selected:'已选择', unavailable:'此连接方式暂不可用。请检查系统网络、蓝牙及相关权限后重试。',
      lockMonitor:'无法监测 Windows 锁屏状态，暂不能开始设备传输。请重新打开小仓后重试。',
      connectFailed:'未能连接到设备。请确认对方仍在附近，并已在小仓中开始等待接收，再重试。',
      disconnected:'连接已断开，请重新开始。', authFailed:'配对码不正确或认证未通过。请核对接收端配对码后重试。', upgrade:'两台设备都需要升级到支持配对码的版本。',
      timeout:'等待超时。请确认对方已准备好，再重新连接。',
      limit:'本次范围超出传输上限，请选择更小的范围后重试。', invalid:'接收的资料未通过校验，未进入导入。请重新传输。',
      internal:'本次操作未完成，请关闭后重新开始。', session:'当前密码库已锁定或切换，请解锁后重新开始。',
      selectionChanged:'所选记录已修改或删除，请重新选择并核对。', stale:'本次连接已结束，请重新开始。', busy:'上一项操作仍在处理，请稍后再试。',
    },
    EN: {
      title:'Device transfer', subtitle:'Transfer contents between devices, then compare and import.',
      sendSubtitle:'Send a copy of your vault for the other device to compare and import.', receiveSubtitle:'Receive contents from another device, then compare and import into your vault.',
      steps:['Choose device','Pair devices','Send contents','Transfer result'],
      role:'What should this device do?', send:'Send contents', sendHint:'Send a copy of the currently unlocked vault',
      receive:'Receive contents', receiveHint:'Compare first, then confirm what to import',
      transport:'Connection', lan:'Local network', lanHint:'Connect both devices to the same Wi-Fi or LAN',
      bluetooth:'Bluetooth', bluetoothHint:'Pair the two devices in system settings first',
      setupHint:'Open Cangoo on the other device and unlock the vault you want to use.',
      find:'Find nearby devices', wait:'Wait for sender', nearby:'Choose the receiving device',
      nearbyHint:'On the other device, choose Receive contents and Local network, then start waiting.',
      nearbyBluetooth:'Choose a paired device', nearbyBluetoothHint:'On the other device, choose Receive contents and Bluetooth, then start waiting. Listed devices may be offline.',
      empty:'No device found yet. Check that the other device has started waiting, or connect by entering its address.', retry:'Search again', restart:'Start again',
      emptyBluetooth:'No paired devices. Pair the devices in system Bluetooth settings, then search again.',
      manual:'Device not found? Connect by address', manualHint:'Find the address on the receiving device’s Wait for sender screen. Enter the address only, without a port.',
      address:'Receiving device address', connectAddress:'Connect', addressBusy:'Searching', addressSearching:'Looking for Cangoo at this address…',
      invalidAddress:'Enter a valid IPv4 address for the receiving device on your local network.',
      addressNotFound:'Device not found. Check the address and retry or search again. Try Bluetooth if this network blocks access.',
      localAddress:'This device’s address', localAddressHint:'Choose an address on the same network as the sender. Usually, try Wi-Fi or Ethernet first.',
      addressWifi:'Wi-Fi', addressEthernet:'Ethernet', addressOther:'Other connection', otherAddresses:'Other network addresses ({count})',
      noLocalAddress:'No local network address is available. Check the network connection, or use Bluetooth.',
      networkTitle:'Local network access', networkAllow:'Allow local device connections', networkRevoke:'Revoke local network access', networkCheck:'Check again',
      networkPolicy:'Only this copy’s LAN rules change. Cangoo runs normally; Windows confirms permission changes.',
      securityPromptHint:'If security software asks, verify this action and allow once.',
      networkRequired:'Allow local device connections to enable LAN transfers.',
      networkChecking:'Checking local network access…',
      networkAuthorizing:'Confirm access in the Windows prompt.',
      networkRevoking:'Confirm removal of access in the Windows prompt.',
      networkReady:'LAN access is allowed for this copy of Cangoo.',
      networkBlocked:'Windows blocks access. Check Cangoo’s rules or use Bluetooth.',
      networkFailed:'Could not confirm access. Try again, or use Bluetooth.',
      networkRequiredError:'Allow local device connections before starting a local network transfer.',
      waiting:'Waiting for the sender', waitingHint:'Select this device on the sender and enter the code below.',
      copyCode:'Copy pairing code', copied:'Copied', copyFailed:'Could not copy. Please try again.',
      pairingLabel:'Temporary pairing code', pairingExpiry:'Valid for 10 minutes, until pairing succeeds. Normal vault locking still applies while waiting.',
      inputCode:'Enter the receiver’s pairing code', inputCodeHint:'Enter the 8 digits shown on the receiver. If it has no code, update Cangoo on both devices first.',
      invalidCode:'Enter an 8-digit pairing code.', pairingFailed:'Pairing did not finish. Check that the receiver is waiting and verify its code, then retry.', pair:'Pair devices',
      connecting:'Pairing devices', connectingHint:'Checking the pairing code. Please wait.',
      peer:'Other device', verify:'Allow this device to send contents?', verifyHint:'Device names are labels only. After approval, wait for the sender, then compare the complete copy before importing.',
      approve:'Allow sending', waitingApproval:'Paired. Waiting for the receiver’s approval.',
      receiveReview:'Waiting for the sender', receiveReviewHint:'Choose contents and start sending on the other device.', receiveNote:'After receiving and checking the complete copy, compare it and choose what to import.',
      localFrom:'Your vault · sending', peerFrom:'Other vault · sending', localTo:'Your vault · receiving', peerTo:'Other vault · receiving', receiveScope:'Receiving',
      review:'Confirm this transfer', reviewHint:'Contents will be sent in the direction shown below.', from:'Sending vault', to:'Receiving vault',
      scope:'What would you like to send?', all:'Everything', passwords:'Passwords only', notes:'Notes only', custom:'Custom', chooseRecords:'Choose records',
      reviewNote:'The sending vault stays unchanged. After receiving the complete copy, the other device can compare and choose what to import.',
      preparing:'Preparing the selected contents…', start:'Send contents', awaitingOffer:'Waiting for the sender to select and send contents.',
      awaitingAccept:'Waiting for the receiver to be ready…', accepted:'Waiting for the sender to transfer contents.', ready:'The receiver approved. You can send contents.',
      transferring:'Transferring contents', transferringHint:'Keep both apps in the foreground until receiving is complete.',
      transferNote:'Automatic app locking is paused during transfer. Locking or switching vaults, quitting, screen lock or sleep ends the transfer.',
      checking:'Checking the received contents…', checkingTitle:'Checking received contents', receiptTitle:'Waiting for the other device to finish checking', receipt:'Contents sent. Waiting for confirmation of a complete, checked copy.',
      sent:'The other device has the complete copy', sentHint:'You can leave now. The other device can continue comparing and importing.',
      received:'Complete copy received', receivedHint:'Opening the comparison. The sending device can leave now.',
      failed:'Transfer completion not confirmed', cancelled:'Transfer cancelled', cancelledHint:'Start again with a new pairing code when ready.',
      cancel:'Cancel', close:'Close', continue:'Continue',
      protected:'Devices paired', selected:'Selected', unavailable:'This connection is unavailable. Check the network, Bluetooth and permissions, then retry.',
      lockMonitor:'Windows screen lock monitoring is unavailable, so device transfer cannot start. Reopen Cangoo and retry.',
      connectFailed:'Could not connect. Check that the other device is nearby and has started waiting to receive in Cangoo, then retry.',
      disconnected:'The connection was lost. Start again.', authFailed:'The code is incorrect or authentication failed. Check the receiver’s code and retry.', upgrade:'Update Cangoo on both devices to a version that supports pairing codes.',
      timeout:'The wait timed out. Check that the other device is ready, then reconnect.',
      limit:'This selection exceeds the transfer limit. Choose a smaller scope and try again.', invalid:'The received contents did not pass validation and were not opened for import. Send them again.',
      internal:'The operation did not finish. Close this window and start again.', session:'The vault was locked or switched. Unlock it and start again.',
      selectionChanged:'Selected records changed or were removed. Choose and review them again.', stale:'This connection has ended. Please start again.', busy:'The previous action is still processing. Please try again shortly.',
    },
  };
  const PHASES = ['IDLE','DISCOVERING','WAITING','PAIRING_CODE','CONNECTING','WAIT_APPROVAL','REVIEW','TRANSFERRING','VERIFYING_PAYLOAD','WAIT_RECEIPT','RECEIVED','SENT','FAILED','CANCELLED'];
  const ERROR_KEYS = {REVISION_CONFLICT:'selectionChanged',COPY_FAILED:'copyFailed',UNAVAILABLE:'unavailable',LOCK_MONITOR_UNAVAILABLE:'lockMonitor',LAN_ACCESS_REQUIRED:'networkRequiredError',INVALID_ADDRESS:'invalidAddress',ADDRESS_NOT_FOUND:'addressNotFound',CONNECT_FAILED:'connectFailed',DISCONNECTED:'disconnected',AUTH_FAILED:'authFailed',INVALID_PAIRING_CODE:'invalidCode',UPGRADE_REQUIRED:'upgrade',TIMEOUT:'timeout',LIMIT_EXCEEDED:'limit',INVALID_DATA:'invalid',INTERNAL_FAILURE:'internal',SESSION_REQUIRED:'session',STALE_FLOW:'stale',REQUEST_BUSY:'busy',INVALID_ARGUMENT:'internal',CANCELLED:'cancelledHint'};
  const NETWORK_ACCESS = {DEVELOPMENT:'',CHECKING:'networkChecking',REQUIRED:'networkRequired',AUTHORIZING:'networkAuthorizing',REVOKING:'networkRevoking',READY:'networkReady',BLOCKED:'networkBlocked',FAILED:'networkFailed'};
  const SCOPES = ['ALL','PASSWORDS','NOTES','CUSTOM'];
  const SCOPE_KEYS = ['all','passwords','notes','custom'];
  const STATE_KEYS = ['flowId','revision','pageEpoch','sessionEpoch','phase','role','transport','scope','peers','pairingCode',
    'receiverAccepted','offerReady','preparing','peerDeviceName','localVaultName',
    'peerVaultName','transferredBytes','totalBytes','errorCode','networkAccess','effectiveTheme','language','uiFontScale',
    'localAddresses','manualAddress','manualSearching','passwordCount','noteCount'];
  function normalizeState(value) {
    if (!value || typeof value !== 'object' || Array.isArray(value) ||
        Object.keys(value).length !== STATE_KEYS.length || !STATE_KEYS.every(key => Object.hasOwn(value,key))) return null;
    if (typeof value.flowId !== 'string' || !/^[a-f0-9]{32}$/.test(value.flowId) || !PHASES.includes(value.phase) ||
        !['SEND','RECEIVE'].includes(value.role) || !['LAN','BLUETOOTH'].includes(value.transport) ||
        !SCOPES.includes(value.scope) || !['ZH','EN'].includes(value.language) ||
        !['LIGHT','DARK'].includes(value.effectiveTheme) || !['90','100','110','125'].includes(value.uiFontScale) ||
        !['NONE',...Object.keys(ERROR_KEYS)].includes(value.errorCode) || !Object.hasOwn(NETWORK_ACCESS,value.networkAccess)) return null;
    for (const key of ['revision','pageEpoch','sessionEpoch','transferredBytes','totalBytes']) {
      if (!Number.isSafeInteger(value[key]) || value[key] < (key.endsWith('Epoch') ? 1 : 0)) return null;
    }
    if (!['passwordCount','noteCount'].every(key => Number.isSafeInteger(value[key]) && value[key] >= 0) || value.passwordCount + value.noteCount > 100000 ||
        value.totalBytes > 67108864 || value.transferredBytes > value.totalBytes ||
        !['receiverAccepted','offerReady','preparing','manualSearching'].every(key => typeof value[key] === 'boolean')) return null;
    const bounded = (text,limit) => typeof text === 'string' && !text.includes('\0') && Array.from(text).length <= limit;
    const address = text => typeof text === 'string' && /^(?:0|[1-9]\d{0,2})(?:\.(?:0|[1-9]\d{0,2})){3}$/.test(text) && text.split('.').every(part => Number(part) <= 255);
    if (!bounded(value.peerDeviceName,64) || !bounded(value.localVaultName,256) || !bounded(value.peerVaultName,256) ||
        typeof value.pairingCode !== 'string' || (value.pairingCode !== '' && !/^[0-9]{8}$/.test(value.pairingCode)) ||
        (value.pairingCode !== '' && (value.role !== 'RECEIVE' || value.phase !== 'WAITING')) ||
        !Array.isArray(value.localAddresses) || value.localAddresses.length > 64 ||
        (value.manualAddress !== '' && !address(value.manualAddress)) ||
        !Array.isArray(value.peers) || value.peers.length > 64) return null;
    const addressIds = new Set();
    for (const item of value.localAddresses) {
      if (!item || typeof item !== 'object' || Array.isArray(item) || Object.keys(item).length !== 5 ||
          !['address','interfaceIndex','name','kind','preferred'].every(key => Object.hasOwn(item,key)) ||
          !address(item.address) || !Number.isInteger(item.interfaceIndex) || item.interfaceIndex < 1 || item.interfaceIndex > 4294967295 ||
          !bounded(item.name,128) || /[\u0000-\u001f\u007f-\u009f]/.test(item.name) ||
          !['WIFI','ETHERNET','OTHER'].includes(item.kind) || typeof item.preferred !== 'boolean') return null;
      const id = `${item.interfaceIndex}/${item.address}`;
      if (addressIds.has(id)) return null;
      addressIds.add(id);
    }
    const peerIds = new Set();
    for (const peer of value.peers) {
      if (!peer || Object.keys(peer).length !== 3 || typeof peer.peerId !== 'string' || !/^[a-f0-9]{32}$/.test(peer.peerId) ||
          !bounded(peer.name,64) || typeof peer.legacy !== 'boolean' || peerIds.has(peer.peerId)) return null;
      peerIds.add(peer.peerId);
    }
    return Object.freeze({...value,localAddresses:Object.freeze(value.localAddresses.map(item => Object.freeze({...item}))),peers:value.peers.map(peer => Object.freeze({...peer}))});
  }
  const markup = `
    <header class="transfer-header">
      <h1 class="transfer-title" id="transfer-title" data-transfer-slot="title"></h1>
      <p class="transfer-subtitle" data-transfer-slot="subtitle"></p>
      <ol class="transfer-steps" aria-label=""><li class="transfer-step"><span class="transfer-step-number">1</span><span></span></li><li class="transfer-step"><span class="transfer-step-number">2</span><span></span></li><li class="transfer-step"><span class="transfer-step-number">3</span><span></span></li><li class="transfer-step"><span class="transfer-step-number">4</span><span></span></li></ol>
    </header>
    <div class="transfer-body">
      <section class="transfer-panel" data-transfer-panel="IDLE">
        <h2 class="transfer-heading" data-transfer-text="role"></h2>
        <div class="transfer-choices transfer-field" role="group" data-transfer-group="role">
          <button type="button" class="transfer-choice" data-transfer-role="SEND"><span data-transfer-text="send"></span><small data-transfer-text="sendHint"></small></button>
          <button type="button" class="transfer-choice" data-transfer-role="RECEIVE"><span data-transfer-text="receive"></span><small data-transfer-text="receiveHint"></small></button>
        </div>
        <fieldset class="transfer-field"><legend class="transfer-label" data-transfer-text="transport"></legend>
          <div class="transfer-choices"><button type="button" class="transfer-choice" data-transfer-transport="LAN"><span data-transfer-text="lan"></span><small data-transfer-text="lanHint"></small></button><button type="button" class="transfer-choice" data-transfer-transport="BLUETOOTH"><span data-transfer-text="bluetooth"></span><small data-transfer-text="bluetoothHint"></small></button></div>
        </fieldset>
        <section class="transfer-network" aria-labelledby="transfer-network-title" hidden>
          <h3 id="transfer-network-title" class="transfer-label" data-transfer-text="networkTitle"></h3>
          <div class="transfer-network-row"><p class="transfer-network-description" data-transfer-slot="networkHint" role="status" aria-live="polite"></p><button type="button" class="btn btn-ghost" data-transfer-action="revokeNetwork" data-transfer-text="networkRevoke"></button></div>
        </section>
        <p class="transfer-note" data-transfer-text="setupHint"></p>
      </section>
      <section class="transfer-panel" data-transfer-panel="DISCOVERING" hidden><h2 class="transfer-heading" data-transfer-slot="nearbyTitle"></h2><p class="transfer-description" data-transfer-slot="nearbyHint"></p><div class="transfer-peer-list"></div><p class="transfer-empty" data-transfer-slot="empty"></p></section>
      <details class="transfer-panel transfer-manual" hidden>
        <summary data-transfer-text="manual"></summary>
        <form class="transfer-address-form" novalidate>
          <p class="transfer-description" id="transfer-address-hint" data-transfer-text="manualHint"></p>
          <label class="transfer-label" for="transfer-address" data-transfer-text="address"></label>
          <div class="transfer-address-row"><input class="input" id="transfer-address" type="text" inputmode="decimal" maxlength="15" placeholder="192.168.1.10" autocomplete="off" spellcheck="false" aria-describedby="transfer-address-hint transfer-address-status"><button type="submit" class="btn" data-transfer-action="manualConnect"></button></div>
          <p class="transfer-address-status" id="transfer-address-status" role="status" aria-live="polite"></p>
        </form>
      </details>
      <section class="transfer-panel" data-transfer-panel="WAITING CONNECTING" hidden><h2 class="transfer-heading" data-transfer-slot="waitingTitle"></h2><p class="transfer-description" data-transfer-slot="waitingHint"></p><div class="transfer-pairing-row"><div class="transfer-pairing-code" data-transfer-slot="pairingCode" role="status"></div><button type="button" class="btn btn-ghost" data-transfer-action="copyPairingCode"></button></div><p class="transfer-description" data-transfer-slot="pairingExpiry"></p><section class="transfer-local-address" hidden><h3 class="transfer-label" data-transfer-text="localAddress"></h3><p class="transfer-description" data-transfer-slot="localAddressHint"></p><ul class="transfer-address-list" data-transfer-slot="preferredAddresses"></ul><details class="transfer-other-addresses" hidden><summary data-transfer-slot="otherAddressTitle"></summary><ul class="transfer-address-list" data-transfer-slot="otherAddresses"></ul></details></section><p class="transfer-note" data-transfer-text="setupHint"></p></section>
      <section class="transfer-panel" data-transfer-panel="PAIRING_CODE" hidden>
        <h2 class="transfer-heading" data-transfer-text="inputCode"></h2>
        <p class="transfer-description" id="transfer-code-hint" data-transfer-text="inputCodeHint"></p>
        <form class="transfer-code-form" novalidate><label class="transfer-label" for="transfer-code" data-transfer-text="pairingLabel"></label><input class="input transfer-code-input" id="transfer-code" type="text" inputmode="numeric" maxlength="9" autocomplete="off" spellcheck="false" aria-describedby="transfer-code-hint"></form>
      </section>
      <section class="transfer-panel" data-transfer-panel="WAIT_APPROVAL" hidden>
        <div class="transfer-context"><span class="transfer-context-dot" aria-hidden="true"></span><span data-transfer-text="peer"></span><span class="transfer-context-name" data-transfer-slot="peer"></span></div>
        <h2 class="transfer-heading" data-transfer-slot="approvalTitle"></h2><p class="transfer-description" data-transfer-slot="approvalHint"></p>
      </section>
      <section class="transfer-panel" data-transfer-panel="REVIEW" hidden>
        <div class="transfer-context"><span class="transfer-context-dot" aria-hidden="true"></span><span data-transfer-text="protected"></span><span class="transfer-context-name" data-transfer-slot="reviewPeer"></span></div>
        <h2 class="transfer-heading" data-transfer-slot="reviewTitle"></h2><p class="transfer-description" data-transfer-slot="reviewHint"></p>
        <div class="transfer-route"><div class="transfer-vault"><p class="transfer-vault-label" data-transfer-slot="fromLabel"></p><p class="transfer-vault-name" data-transfer-slot="from"></p></div><span class="transfer-route-arrow" aria-hidden="true">→</span><div class="transfer-vault"><p class="transfer-vault-label" data-transfer-slot="toLabel"></p><p class="transfer-vault-name" data-transfer-slot="to"></p></div></div>
        <fieldset class="transfer-field transfer-scope-field"><legend class="transfer-label" data-transfer-slot="scopeLabel"></legend><div class="transfer-scope"><button type="button" class="btn" data-transfer-scope="ALL" data-transfer-text="all"></button><button type="button" class="btn" data-transfer-scope="PASSWORDS" data-transfer-text="passwords"></button><button type="button" class="btn" data-transfer-scope="NOTES" data-transfer-text="notes"></button><button type="button" class="btn" data-transfer-scope="CUSTOM" data-transfer-text="custom" hidden></button></div><div class="export-selection-summary" data-transfer-custom hidden><span></span><button type="button" class="btn btn-sm" data-transfer-action="chooseRecords" data-transfer-text="chooseRecords"></button></div><p data-transfer-slot="scopeValue" hidden></p></fieldset>
        <p class="transfer-description" data-transfer-slot="reviewCounts" hidden></p><p class="transfer-note" data-transfer-slot="reviewNote"></p>
      </section>
      <section class="transfer-panel" data-transfer-panel="TRANSFERRING VERIFYING_PAYLOAD WAIT_RECEIPT" hidden><h2 class="transfer-heading" data-transfer-slot="transferTitle"></h2><p class="transfer-description" data-transfer-text="transferringHint"></p><p class="transfer-description" data-transfer-slot="transferCounts" hidden></p><div class="transfer-progress"><div class="transfer-progress-track" role="progressbar" aria-valuemin="0" aria-valuemax="100"><div class="transfer-progress-fill"></div></div><div class="transfer-progress-label"><span data-transfer-slot="bytes"></span><span data-transfer-slot="percent"></span></div></div><p class="transfer-note" data-transfer-text="transferNote"></p></section>
      <section class="transfer-panel transfer-result" data-transfer-panel="RECEIVED SENT FAILED CANCELLED" hidden><div class="transfer-result-mark" aria-hidden="true">✓</div><h2 class="transfer-heading" data-transfer-slot="resultTitle"></h2><p class="transfer-description" data-transfer-slot="resultHint"></p><p class="transfer-description" data-transfer-slot="resultCounts" hidden></p></section>
    </div>
    <footer class="transfer-footer"><p class="transfer-status" role="status" aria-live="polite" aria-atomic="true"></p><div class="transfer-actions"><button type="button" class="btn btn-ghost" data-transfer-action="cancel"></button><button type="button" class="btn btn-primary" data-transfer-action="primary"></button></div></footer>`;

  function create(container, onAction, openSelection = null) {
    container.classList.add('transfer-window');
    container.setAttribute('aria-labelledby','transfer-title');
    // 仅首次装入固定本地模板；投影不得重建面板或设备行。
    container.innerHTML = markup;
    const nodes = Object.fromEntries(Array.from(container.querySelectorAll('[data-transfer-slot]'), node => [node.dataset.transferSlot, node]));
    const primary = container.querySelector('[data-transfer-action="primary"]');
    const cancel = container.querySelector('[data-transfer-action="cancel"]');
    const status = container.querySelector('.transfer-status');
    const peerList = container.querySelector('.transfer-peer-list');
    const manual = container.querySelector('.transfer-manual');
    const addressForm = container.querySelector('.transfer-address-form');
    const addressInput = container.querySelector('#transfer-address');
    const addressStatus = container.querySelector('.transfer-address-status');
    const addressButton = container.querySelector('[data-transfer-action="manualConnect"]');
    const codeForm = container.querySelector('.transfer-code-form');
    const codeInput = container.querySelector('#transfer-code');
    const copyCode = container.querySelector('[data-transfer-action="copyPairingCode"]');
    const otherAddresses = container.querySelector('.transfer-other-addresses');
    const peerNodes = new Map();
    const addressNodes = new Map();
    let language = 'ZH';
    let current = null;
    let draft = {role:'SEND',transport:'LAN',scope:'ALL'};
    let pending = false;
    let error = '';
    let addressError = '';
    let copied = false;
    let alive = true;
    let actionVersion = 0;
    let selection = [], picker = null;

    function text(node, value) { if (node.textContent !== value) node.textContent = value; }
    function words() { return TEXT[language]; }
    function renderPeers(peers) {
      const ids = new Set(peers.map(peer => peer.peerId));
      for (const [id,node] of peerNodes) if (!ids.has(id)) { node.remove(); peerNodes.delete(id); }
      peers.forEach((peer,index) => {
        let node = peerNodes.get(peer.peerId);
        if (!node) {
          node = document.createElement('button'); node.type = 'button'; node.className = 'transfer-peer';
          node.dataset.transferPeer = peer.peerId;
          const name = document.createElement('span'); name.className = 'transfer-peer-name'; node.append(name);
          const arrow = document.createElement('span'); arrow.className = 'transfer-peer-arrow'; arrow.textContent = '›'; arrow.setAttribute('aria-hidden','true'); node.append(arrow);
          peerNodes.set(peer.peerId,node);
        }
        text(node.firstElementChild,peer.name);
        if (peerList.children[index] !== node) peerList.insertBefore(node,peerList.children[index] || null);
        node.setAttribute('aria-disabled',String(pending || Boolean(current.manualAddress)));
      });
      peerList.hidden = peers.length === 0;
      container.querySelector('.transfer-empty').hidden = peers.length !== 0;
    }

    function renderAddresses(addresses) {
      const ids = new Set(addresses.map(item => `${item.interfaceIndex}/${item.address}`));
      for (const [id,node] of addressNodes) if (!ids.has(id)) { node.remove(); addressNodes.delete(id); }
      const hasPreferred = addresses.some(item => item.preferred);
      const groups = [addresses.filter(item => !hasPreferred || item.preferred),addresses.filter(item => hasPreferred && !item.preferred)];
      [nodes.preferredAddresses,nodes.otherAddresses].forEach((list,group) => {
        groups[group].forEach((item,index) => {
          const id = `${item.interfaceIndex}/${item.address}`;
          let node = addressNodes.get(id);
          if (!node) {
            node = document.createElement('li'); node.className = 'transfer-local-row'; node.dataset.transferAddress = id;
            const info = document.createElement('div'); info.className = 'transfer-address-info';
            const kind = document.createElement('span'); kind.className = 'transfer-address-kind';
            const name = document.createElement('span'); name.className = 'transfer-address-name'; info.append(kind,name);
            const value = document.createElement('p'); value.className = 'transfer-address-value'; node.append(info,value);
            addressNodes.set(id,node);
          }
          text(node.firstElementChild.firstElementChild,words()[{WIFI:'addressWifi',ETHERNET:'addressEthernet',OTHER:'addressOther'}[item.kind]]);
          text(node.firstElementChild.lastElementChild,item.name);
          node.firstElementChild.lastElementChild.hidden = !item.name;
          text(node.lastElementChild,item.address);
          if (list.children[index] !== node) list.insertBefore(node,list.children[index] || null);
        });
        list.hidden = groups[group].length === 0;
      });
      otherAddresses.hidden = groups[1].length === 0;
      text(nodes.otherAddressTitle,addresses.length ? words().otherAddresses.replace('{count}',String(groups[1].length)) : '');
    }

    function render() {
      if (!current || !alive) return;
      const w = words(), s = current, phase = s.phase;
      const finished = ['RECEIVED','SENT','FAILED','CANCELLED'].includes(phase);
      const receiving = s.role === 'RECEIVE';
      text(nodes.title,phase === 'IDLE' ? w.title : receiving ? w.receive : w.send);
      text(nodes.subtitle,phase === 'IDLE' ? w.subtitle : receiving ? w.receiveSubtitle : w.sendSubtitle);
      for (const node of container.querySelectorAll('[data-transfer-text]')) text(node,w[node.dataset.transferText]);
      for (const panel of container.querySelectorAll('[data-transfer-panel]')) panel.hidden = !panel.dataset.transferPanel.split(' ').includes(phase);
      const step = ['IDLE','DISCOVERING','WAITING','CONNECTING'].includes(phase) ? 0 : ['PAIRING_CODE','WAIT_APPROVAL'].includes(phase) ? 1 : phase === 'REVIEW' ? 2 : 3;
      container.querySelectorAll('.transfer-step').forEach((node,index) => {
        node.classList.toggle('active',index === step); node.classList.toggle('complete',index < step);
        if (index === step) node.setAttribute('aria-current','step'); else node.removeAttribute('aria-current');
        text(node.lastElementChild,index === 2 && receiving ? w.receive : w.steps[index]);
      });
      container.querySelector('.transfer-steps').setAttribute('aria-label',w.title);
      container.querySelector('[data-transfer-group="role"]').setAttribute('aria-label',w.role);
      for (const key of ['role','transport','scope']) container.querySelectorAll(`[data-transfer-${key}]`).forEach(node => {
        node.setAttribute('aria-pressed',String(node.dataset['transfer'+key[0].toUpperCase()+key.slice(1)] === draft[key]));
        node.setAttribute('aria-disabled',String(pending || s.preparing || s.manualSearching));
      });
      renderPeers(phase === 'DISCOVERING' ? s.peers : []);
      const networkBusy = ['CHECKING','AUTHORIZING','REVOKING'].includes(s.networkAccess);
      const needsNetwork = draft.transport === 'LAN' && !['DEVELOPMENT','READY'].includes(s.networkAccess);
      const showNetworkAccess = phase === 'IDLE' && draft.transport === 'LAN' && s.networkAccess !== 'DEVELOPMENT';
      container.querySelector('.transfer-network').hidden = !showNetworkAccess;
      text(nodes.networkHint,w.networkPolicy);
      const revoke = container.querySelector('[data-transfer-action="revokeNetwork"]');
      revoke.disabled = networkBusy || s.networkAccess === 'REQUIRED';
      revoke.setAttribute('aria-disabled',String(revoke.disabled || pending || s.manualSearching));
      const showManual = ['IDLE','DISCOVERING'].includes(phase) && draft.role === 'SEND' && draft.transport === 'LAN';
      manual.hidden = !showManual;
      if (!showManual) { manual.open = false; addressInput.value = ''; addressError = ''; }
      addressInput.readOnly = pending || s.manualSearching;
      text(addressButton,s.manualSearching ? w.addressBusy : w.connectAddress);
      addressButton.setAttribute('aria-disabled',String(pending || s.manualSearching || needsNetwork));
      addressButton.setAttribute('aria-busy',String(s.manualSearching));
      addressInput.setAttribute('aria-invalid',String(addressError === 'INVALID_ADDRESS'));
      text(addressStatus,addressError ? w[ERROR_KEYS[addressError]] : needsNetwork ? w.networkRequiredError : s.manualSearching ? w.addressSearching : '');
      addressStatus.classList.toggle('error',Boolean(addressError));
      const showLocalAddresses = phase === 'WAITING' && s.role === 'RECEIVE' && s.transport === 'LAN';
      container.querySelector('.transfer-local-address').hidden = !showLocalAddresses;
      text(nodes.localAddressHint,s.localAddresses.length ? w.localAddressHint : w.noLocalAddress);
      renderAddresses(showLocalAddresses ? s.localAddresses : []);
      if (!showLocalAddresses) otherAddresses.open = false;
      text(nodes.nearbyTitle,s.transport === 'BLUETOOTH' ? w.nearbyBluetooth : w.nearby);
      text(nodes.nearbyHint,s.transport === 'BLUETOOTH' ? w.nearbyBluetoothHint : w.nearbyHint);
      text(nodes.empty,s.transport === 'BLUETOOTH' ? w.emptyBluetooth : w.empty);
      text(nodes.waitingTitle,phase === 'CONNECTING' ? w.connecting : w.waiting);
      text(nodes.waitingHint,phase === 'CONNECTING' ? w.connectingHint : w.waitingHint);
      const enteringCode = phase === 'PAIRING_CODE';
      if (!enteringCode) codeInput.value = '';
      codeInput.readOnly = pending;
      codeInput.setAttribute('aria-invalid',String(error === 'INVALID_PAIRING_CODE'));
      const showingCode = phase === 'WAITING' && receiving && s.pairingCode.length === 8;
      text(nodes.pairingCode,showingCode ? s.pairingCode.slice(0,4) + ' ' + s.pairingCode.slice(4) : '');
      container.querySelector('.transfer-pairing-row').hidden = !showingCode;
      text(copyCode,copied ? w.copied : w.copyCode);
      copyCode.setAttribute('aria-disabled',String(pending || !showingCode));
      nodes.pairingCode.setAttribute('aria-label',w.pairingLabel);
      text(nodes.pairingExpiry,phase === 'WAITING' ? w.pairingExpiry : '');
      text(nodes.peer,phase === 'WAIT_APPROVAL' ? s.peerDeviceName : '');
      text(nodes.approvalTitle,s.role === 'RECEIVE' ? w.verify : w.waitingApproval);
      text(nodes.approvalHint,s.role === 'RECEIVE' ? w.verifyHint : '');
      const review = phase === 'REVIEW';
      text(nodes.reviewTitle,receiving ? w.receiveReview : w.review);
      text(nodes.reviewHint,receiving ? w.receiveReviewHint : w.reviewHint);
      text(nodes.fromLabel,receiving ? w.peerFrom : w.localFrom);
      text(nodes.toLabel,receiving ? w.localTo : w.peerTo);
      text(nodes.scopeLabel,receiving ? w.receiveScope : w.scope);
      text(nodes.reviewNote,receiving ? w.receiveNote : w.reviewNote);
      text(nodes.reviewPeer,review ? s.peerDeviceName : '');
      text(nodes.from,review ? (s.role === 'SEND' ? s.localVaultName : s.peerVaultName) : '');
      text(nodes.to,review ? (s.role === 'SEND' ? s.peerVaultName : s.localVaultName) : '');
      const canChooseScope = review && s.role === 'SEND' && !s.offerReady;
      container.querySelector('.transfer-scope').hidden = !canChooseScope;
      const scopeKnown = review && (!receiving || s.offerReady);
      container.querySelector('.transfer-scope-field').hidden = !scopeKnown;
      nodes.scopeValue.hidden = canChooseScope || !scopeKnown;
      text(nodes.scopeValue,scopeKnown ? w[SCOPE_KEYS[SCOPES.indexOf(s.scope)]] : '');
      container.querySelector('[data-transfer-scope="CUSTOM"]').hidden = typeof openSelection !== 'function';
      const custom = container.querySelector('[data-transfer-custom]');
      custom.hidden = !canChooseScope || draft.scope !== 'CUSTOM';
      if (!custom.hidden) {
        const counts = window.PdmExportSelection.counts(selection);
        text(custom.firstElementChild,language === 'ZH' ? `密码 ${counts.passwordCount} · 记事 ${counts.noteCount}` : `${counts.passwordCount} passwords · ${counts.noteCount} notes`);
      }
      const percent = s.totalBytes > 0 ? Math.min(100,Math.floor(s.transferredBytes * 100 / s.totalBytes)) : 0;
      for (const key of ['reviewCounts','transferCounts','resultCounts']) {
        nodes[key].hidden = !s.offerReady;
        text(nodes[key],s.offerReady ? language === 'ZH' ? `密码 ${s.passwordCount} · 记事 ${s.noteCount}` :
          `${s.passwordCount} passwords · ${s.noteCount} notes` : '');
      }
      const transferring = ['TRANSFERRING','VERIFYING_PAYLOAD','WAIT_RECEIPT'].includes(phase);
      text(nodes.transferTitle,phase === 'WAIT_RECEIPT' ? w.receiptTitle : phase === 'VERIFYING_PAYLOAD' ? w.checkingTitle : w.transferring);
      const track = container.querySelector('.transfer-progress-track');
      track.setAttribute('aria-valuenow',String(percent)); track.setAttribute('aria-label',w.transferring);
      container.querySelector('.transfer-progress-fill').style.width = percent + '%';
      text(nodes.bytes,transferring ? `${(s.transferredBytes/1048576).toFixed(1)} / ${(s.totalBytes/1048576).toFixed(1)} MB` : '');
      text(nodes.percent,percent + '%');
      const resultKey = phase === 'SENT' ? 'sent' : phase === 'RECEIVED' ? 'received' : phase === 'CANCELLED' ? 'cancelled' : 'failed';
      text(nodes.resultTitle,finished ? w[resultKey] : '');
      text(nodes.resultHint,finished ? (phase === 'FAILED' ? w[ERROR_KEYS[s.errorCode] || 'internal'] : w[resultKey+'Hint']) : '');
      container.querySelector('.transfer-result').classList.toggle('failed',phase === 'FAILED');
      text(container.querySelector('.transfer-result-mark'),phase === 'FAILED' ? '!' : phase === 'CANCELLED' ? '−' : '✓');
      let primaryText = w.continue, blocked = false, message = showNetworkAccess ? [w[NETWORK_ACCESS[s.networkAccess]],w.securityPromptHint].filter(Boolean).join(' ') : '';
      if (phase === 'IDLE') {
        primaryText = needsNetwork ? s.networkAccess === 'BLOCKED' ? w.networkCheck : w.networkAllow : draft.role === 'SEND' ? w.find : w.wait;
        blocked = draft.transport === 'LAN' && networkBusy;
      }
      else if (phase === 'DISCOVERING') primaryText = w.retry;
      else if (enteringCode) { primaryText = w.pair; blocked = !/^[0-9]{8}$/.test(codeInput.value.replace(/ /g,'')); }
      else if (phase === 'WAIT_APPROVAL') { primaryText = s.role === 'RECEIVE' ? w.approve : w.wait; blocked = s.role === 'SEND'; }
      else if (review) {
        primaryText = s.role === 'SEND' ? w.start : w.wait;
        blocked = s.role === 'RECEIVE' || s.offerReady || !s.peerVaultName || draft.scope === 'CUSTOM' && window.PdmExportSelection.counts(selection).passwordCount + window.PdmExportSelection.counts(selection).noteCount === 0;
        message = s.role === 'RECEIVE' ? w.awaitingOffer : s.offerReady ? w.awaitingAccept : w.ready;
      } else if (phase === 'FAILED' || phase === 'CANCELLED') primaryText = w.restart;
      else if (finished) primaryText = w.close;
      else { blocked = true; primaryText = transferring ? w.continue : w.wait; }
      if (phase === 'VERIFYING_PAYLOAD') message = w.checking;
      if (phase === 'WAIT_RECEIPT') message = w.receipt;
      if (s.preparing) message = w.preparing;
      text(primary,primaryText); primary.disabled = blocked; primary.setAttribute('aria-disabled',String(blocked || pending || s.preparing || s.manualSearching));
      text(cancel,finished ? w.close : w.cancel); cancel.hidden = ['SENT','RECEIVED'].includes(phase);
      text(status,error ? w[ERROR_KEYS[error] || 'internal'] : enteringCode && ['CONNECT_FAILED','DISCONNECTED','TIMEOUT'].includes(s.errorCode) ? w.pairingFailed : s.errorCode !== 'NONE' ? w[ERROR_KEYS[s.errorCode] || 'internal'] : message);
      status.classList.toggle('error',Boolean(error || s.errorCode !== 'NONE'));
      container.setAttribute('aria-busy',String(pending));
    }

    function dispatch(action, value) {
      if (!alive || !current || (pending && action !== 'cancel' && action !== 'close')) return;
      const version = ++actionVersion;
      const observed = current;
      pending = true; error = ''; addressError = '';
      if (action === 'copyPairingCode') copied = false;
      render();
      Promise.resolve().then(() => alive && version === actionVersion ? onAction(action,value,observed) : null).then(result => {
        if (!alive || version !== actionVersion) return;
        if (action === 'copyPairingCode' && (current.flowId !== observed.flowId || current.phase !== 'WAITING' || current.pairingCode !== observed.pairingCode)) return;
        if (result?.accepted === true && action === 'copyPairingCode') copied = true;
        if (!result || result.accepted !== true) {
          const code = result?.errorCode || 'INTERNAL_FAILURE';
          if (action === 'manualConnect' && ['INVALID_ADDRESS','ADDRESS_NOT_FOUND'].includes(code)) addressError = code;
          else error = code;
        }
      }).catch(() => {
        if (alive && version === actionVersion && (action !== 'copyPairingCode' || (current.phase === 'WAITING' && current.pairingCode === observed.pairingCode))) error = 'INTERNAL_FAILURE';
      }).finally(() => {
        if (alive && version === actionVersion) { pending = false; render(); }
      });
    }
    function click(event) {
      const button = event.target.closest('button');
      if (!button || !container.contains(button) || button.disabled || button.getAttribute('aria-disabled') === 'true') return;
      if (button.dataset.transferRole && current?.phase === 'IDLE') draft.role = button.dataset.transferRole;
      else if (button.dataset.transferTransport && current?.phase === 'IDLE') draft.transport = button.dataset.transferTransport;
      else if (button.dataset.transferScope && current?.phase === 'REVIEW' && current.role === 'SEND' && !current.offerReady && !current.preparing) {
        if (button.dataset.transferScope === 'CUSTOM') return chooseRecords();
        draft.scope = button.dataset.transferScope;
      }
      else if (button.dataset.transferAction === 'chooseRecords') return chooseRecords();
      else if (button.dataset.transferPeer && current?.phase === 'DISCOVERING') return dispatch('peer',button.dataset.transferPeer);
      else if (button.dataset.transferAction === 'copyPairingCode' && current?.phase === 'WAITING' && current.role === 'RECEIVE') return dispatch('copyPairingCode');
      else if (button.dataset.transferAction === 'revokeNetwork' && current?.phase === 'IDLE') return dispatch('revokeNetwork');
      else if (button.dataset.transferAction === 'cancel') return dispatch(['FAILED','CANCELLED'].includes(current?.phase) ? 'close' : 'cancel');
      else if (button.dataset.transferAction === 'primary' && current) {
        if (current.phase === 'IDLE' && draft.transport === 'LAN' && !['DEVELOPMENT','READY'].includes(current.networkAccess)) return dispatch('authorizeNetwork');
        if (current.phase === 'IDLE' || current.phase === 'DISCOVERING') return dispatch('begin',{...draft});
        if (current.phase === 'PAIRING_CODE') return submitCode();
        if (current.phase === 'WAIT_APPROVAL') return dispatch('approve');
        if (current.phase === 'REVIEW') return dispatch('send',draft.scope === 'CUSTOM' ? {scope:'CUSTOM',selection} : draft.scope);
        if (['FAILED','CANCELLED'].includes(current.phase)) return dispatch('restart');
        if (['SENT','RECEIVED'].includes(current.phase)) return dispatch('close');
      }
      render();
    }
    function chooseRecords() {
      if (typeof openSelection !== 'function' || picker || current?.phase !== 'REVIEW' || current.role !== 'SEND' || current.offerReady || current.preparing) return;
      const previous = draft.scope; draft.scope = 'CUSTOM'; render();
      picker = openSelection(container,selection,result => {
        picker = null;
        if (result !== null) selection = result; else draft.scope = previous;
        render();
      });
    }
    function submitAddress(event) {
      event.preventDefault();
      if (manual.hidden || pending || current?.manualSearching || addressButton.getAttribute('aria-disabled') === 'true') return;
      dispatch('manualConnect',addressInput.value.trim());
    }
    function submitCode(event) {
      event?.preventDefault();
      if (current?.phase !== 'PAIRING_CODE' || pending) return;
      const code = codeInput.value.replace(/ /g,'');
      if (!/^[0-9]{8}$/.test(code)) { error = 'INVALID_PAIRING_CODE'; render(); return; }
      codeInput.value = '';
      dispatch('pairingCode',code);
    }
    function editCode() { if (error === 'INVALID_PAIRING_CODE') error = ''; render(); }
    function editAddress() { if (addressError) { addressError = ''; render(); } }
    container.addEventListener('click',click);
    addressForm.addEventListener('submit',submitAddress);
    addressInput.addEventListener('input',editAddress);
    codeForm.addEventListener('submit',submitCode);
    codeInput.addEventListener('input',editCode);
    return {
      project(value) {
        value = normalizeState(value);
        if (!alive || !value) return false;
        if (current && (value.revision < current.revision || value.pageEpoch !== current.pageEpoch || value.sessionEpoch !== current.sessionEpoch)) return false;
        const keepManual = current && !manual.hidden && ['IDLE','DISCOVERING'].includes(value.phase) && value.role === 'SEND' && value.transport === 'LAN';
        if (!current || value.flowId !== current.flowId) {
          picker?.dispose(); picker = null; selection = [];
          draft = {role:value.role,transport:value.transport,scope:value.scope}; error = '';
          addressError = '';
          if (!keepManual) { addressInput.value = value.manualAddress; manual.open = Boolean(value.manualAddress); }
          actionVersion++; pending = false;
        }
        if (value.errorCode !== current?.errorCode && ['INVALID_ADDRESS','ADDRESS_NOT_FOUND'].includes(value.errorCode)) addressError = value.errorCode;
        const leavingSelection = Boolean(picker) && value.phase !== 'REVIEW';
        if (value.offerReady) draft.scope = value.scope;
        if (value.phase !== 'REVIEW') { picker?.dispose(); picker = null; selection = []; }
        if (error === 'LAN_ACCESS_REQUIRED' && value.networkAccess === 'READY') error = '';
        if (value.flowId !== current?.flowId || value.phase !== current?.phase || value.pairingCode !== current?.pairingCode) copied = false;
        const panel = container.querySelector('[data-transfer-panel]:not([hidden])');
        const focusCode = value.phase === 'PAIRING_CODE' && current?.phase !== 'PAIRING_CODE';
        current = value; render();
        if (leavingSelection) primary.focus({preventScroll:true});
        if (focusCode) codeInput.focus({preventScroll:true});
        if (panel !== container.querySelector('[data-transfer-panel]:not([hidden])') && !(keepManual && manual.open)) container.querySelector('.transfer-body').scrollTop = 0;
        return true;
      },
      appearance(value) {
        if (!['ZH','EN'].includes(value.language)) return;
        language = value.language; picker?.appearance(language); render();
      },
      dispose() {
        picker?.dispose(); picker = null; selection = [];
        alive = false; actionVersion++; current = null; draft = null; peerNodes.clear(); addressNodes.clear();
        container.removeEventListener('click',click); addressForm.removeEventListener('submit',submitAddress);
        codeInput.value = '';
        codeForm.removeEventListener('submit',submitCode); codeInput.removeEventListener('input',editCode);
        addressInput.removeEventListener('input',editAddress); container.replaceChildren();
      },
    };
  }
  window.PdmDirectTransfer = Object.freeze({create});

  const host = document.getElementById('transfer-app');
  if (!host) return;
  let bridge = null, live = true, revision = -1, lastState = null;
  const view = create(host,action,(container,selected,done) => window.PdmExportSelection.openNative(container,bridge,
    lastState.pageEpoch,lastState.sessionEpoch,lastState.language,selected,done));
  function action(kind,value,observed) {
    if (!live || !bridge) return {accepted:false,errorCode:'SESSION_REQUIRED'};
    if (kind === 'close') { bridge.requestCloseV1(); return {accepted:true,errorCode:'OK'}; }
    const methods = {copyPairingCode:'copyPairingCodeV1',begin:'beginV1',manualConnect:'connectAddressV1',peer:'choosePeerV1',pairingCode:'submitPairingCodeV1',approve:'approvePeerV1',send:'sendV1',cancel:'cancelV1',authorizeNetwork:'authorizeNetworkV1',revokeNetwork:'revokeNetworkV1',restart:'restartV1'};
    const name = methods[kind];
    if (!name || typeof bridge[name] !== 'function') return {accepted:false,errorCode:'INTERNAL_FAILURE'};
    const args = [observed.flowId];
    if (kind === 'begin') args.push(value.role,value.transport);
    else if (kind === 'send') args.push(typeof value === 'object' ? value.scope : value);
    else if (kind === 'peer' || kind === 'pairingCode' || kind === 'manualConnect') args.push(value);
    return new Promise(resolve => bridge[name](...args,ack => {
      if (!ack || Object.keys(ack).length !== 2 || typeof ack.accepted !== 'boolean' || typeof ack.errorCode !== 'string') {
        resolve({accepted:false,errorCode:'INTERNAL_FAILURE'}); return;
      }
      resolve(ack);
    }));
  }
  function project(raw) {
    const next = normalizeState(raw);
    if (!live || !next || next.revision < revision) return false;
    if (!view.project(next)) return false;
    revision = next.revision; lastState = next;
    document.documentElement.classList.toggle('light',next.effectiveTheme === 'LIGHT');
    document.documentElement.lang = next.language === 'EN' ? 'en' : 'zh-CN';
    document.documentElement.style.setProperty('--pdm-ui-font-scale',String(Number(next.uiFontScale) / 100));
    document.title = TEXT[next.language].title;
    view.appearance(next);
    return true;
  }
  function key(event) {
    if (!event.isComposing && event.key === 'Escape' && live && bridge) { event.preventDefault(); bridge.requestCloseV1(); }
  }
  document.addEventListener('keydown',key);
  window.addEventListener('pagehide',() => { live = false; bridge = null; view.dispose(); document.removeEventListener('keydown',key); },{once:true});
  if (typeof QWebChannel === 'function' && window.qt?.webChannelTransport) {
    new QWebChannel(window.qt.webChannelTransport,channel => {
      if (!live) return;
      bridge = channel.objects.pdmDirectTransferV1;
      if (!bridge) return;
      bridge.stateChangedV1.connect(project);
      bridge.initializeV1(initial => { if(project(initial)) bridge.presentReadyV1(); });
    });
  }
})();
