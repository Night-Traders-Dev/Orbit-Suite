const API_BASE = 'https://oliver-butler-oasis-builder.trycloudflare.com/api/address';

document.addEventListener('DOMContentLoaded', () => {
  const input   = document.getElementById('addressInput');
  const btn     = document.getElementById('fetchBtn');
  const status  = document.getElementById('status');
  const output  = document.getElementById('output');

  // load saved address
  chrome.storage.local.get(['lastAddress'], ({ lastAddress }) => {
    if (lastAddress) input.value = lastAddress;
  });

  // Enter key submits
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter') btn.click();
  });

  btn.addEventListener('click', async () => {
    const address = input.value.trim();
    resetStatus();
    output.innerHTML = '';

    if (!address) {
      showStatus('Please enter a wallet address.', 'error');
      return;
    }

    chrome.storage.local.set({ lastAddress: address });
    btn.disabled = true;
    showStatus('Fetching…');

    try {
      const res  = await fetch(`${API_BASE}/${address}`);
      if (!res.ok) throw new Error(`Status ${res.status}`);
      const data = await res.json();

      showStatus('Success!', 'success');
      renderWallet(data, address);
    }
    catch (err) {
      showStatus(`Error: ${err.message}`, 'error');
    }
    finally {
      btn.disabled = false;
    }
  });

  /* Helpers */

  function resetStatus() {
    status.textContent = '';
    status.className = '';
  }

  function showStatus(msg, type = '') {
    status.textContent = msg;
    if (type) status.classList.add(type);  // 'success' or 'error'
  }

  // Build the wallet UI
  function renderWallet(data, userAddress) {
    // 0) Wallet header
    const hdr = document.createElement('div');
    hdr.className = 'wallet-header';
    hdr.textContent = userAddress;
    output.appendChild(hdr);

    // 1) Balance Card
    const [free = 0, locked = 0] = data.balance || [];
    const balCard = document.createElement('div');
    balCard.className = 'balance-card';
    balCard.innerHTML = `
      <div class="bal-row">
        <div class="bal-label">Available</div>
        <div class="bal-value">${free.toLocaleString()}</div>
      </div>
      <div class="bal-row locked">
        <div class="bal-label">Locked</div>
        <div class="bal-value">${locked.toLocaleString()}</div>
      </div>
    `;
    output.appendChild(balCard);

    // 2) Transactions List
    const txs = data.last_10_transactions || [];
    const txContainer = document.createElement('div');
    txContainer.className = 'tx-container';
    const header = document.createElement('h3');
    header.textContent = 'Last 10 Transactions';
    txContainer.appendChild(header);

    txs.forEach(tx => {
      const item = document.createElement('div');
      item.className = 'tx-item';

      // safely grab nested props
      const noteType = tx.note?.type || {};
      const xfer     = noteType.token_transfer;
      const gas      = noteType.gas;

      // determine icon + title
      let icon = '🔔',
          title = `Amt ${tx.amount}`;

      if (xfer) {
        icon = xfer.sender === userAddress ? '🔽' : '🔼';
        title = `${xfer.token_symbol} ${xfer.amount} — ${xfer.note}`;
      }
      else if (gas) {
        icon = '⛽';
        title = `Gas ${gas.fee}`;
      }

      // human date
      const date = new Date((tx.timestamp || 0) * 1000)
        .toLocaleString([], { dateStyle:'short', timeStyle:'short' });

      item.innerHTML = `
        <div class="tx-icon">${icon}</div>
        <div class="tx-details">
          <div class="tx-title">${title}</div>
          <div class="tx-meta">
            <span>From: ${truncate(tx.sender)}</span>
            <span>To: ${truncate(tx.recipient)}</span>
            <span>${date}</span>
          </div>
        </div>
      `;
      txContainer.appendChild(item);
    });

    output.appendChild(txContainer);
  }

  // e.g. ORB.ABCDEF…1234
  function truncate(addr, pre=6, post=4) {
    if (!addr || addr.length <= pre + post + 1) return addr || '';
    return addr.slice(0, pre) + '…' + addr.slice(-post);
  }
});