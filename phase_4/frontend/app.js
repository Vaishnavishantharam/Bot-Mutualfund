(function () {
  const API_BASE = ''; // same origin when served by backend
  const welcomeScreen = document.getElementById('welcome-screen');
  const chatScreen = document.getElementById('chat-screen');
  const welcomeInput = document.getElementById('welcome-input');
  const welcomeSend = document.getElementById('welcome-send');
  const chatMessages = document.getElementById('chat-messages');
  const chatInput = document.getElementById('chat-input');
  const chatSend = document.getElementById('chat-send');
  const backToWelcome = document.getElementById('back-to-welcome');
  const navRefresh = document.getElementById('nav-refresh');
  const startingUpBanner = document.getElementById('starting-up-banner');

  var serviceReady = false;
  var isLoading = false;

  function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(function (el) {
      el.classList.remove('active');
    });
    const screen = screenId === 'welcome' ? welcomeScreen : chatScreen;
    if (screen) screen.classList.add('active');
    document.querySelectorAll('.nav-item').forEach(function (el) {
      el.classList.toggle('active', el.getAttribute('data-screen') === screenId);
    });
  }

  function appendMessage(role, text, citationUrl, responseSource) {
    const wrap = document.createElement('div');
    wrap.className = 'message ' + role;
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? '👤' : '💰';
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.textContent = text;
    if (citationUrl && role === 'assistant') {
      const source = document.createElement('div');
      source.className = 'message-source';
      source.innerHTML = 'Source: <a href="' + escapeHtml(citationUrl) + '" target="_blank" rel="noopener">View scheme</a>';
      bubble.appendChild(source);
    }
    if (role === 'assistant' && responseSource) {
      const badge = document.createElement('div');
      badge.className = 'message-badge';
      badge.textContent = responseSource === 'llm' ? 'Answered by LLM' : 'Answered from corpus (no LLM)';
      bubble.appendChild(badge);
    }
    wrap.appendChild(avatar);
    wrap.appendChild(bubble);
    if (chatMessages) { chatMessages.appendChild(wrap); chatMessages.scrollTop = chatMessages.scrollHeight; }
  }

  function escapeHtml(s) {
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
  }

  function showTyping() {
    const wrap = document.createElement('div');
    wrap.className = 'message assistant';
    wrap.id = 'typing-indicator';
    wrap.innerHTML = '<div class="message-avatar">💰</div><div class="message-bubble message-typing">Thinking…</div>';
    if (chatMessages) { chatMessages.appendChild(wrap); chatMessages.scrollTop = chatMessages.scrollHeight; }
  }

  function hideTyping() {
    const el = document.getElementById('typing-indicator');
    if (el) el.remove();
  }

  function setLoading(loading) {
    isLoading = loading;
    if (welcomeSend) welcomeSend.disabled = loading || !serviceReady;
    if (chatSend) chatSend.disabled = loading || !serviceReady;
  }

  function setServiceReady(ready) {
    serviceReady = ready;
    if (startingUpBanner) startingUpBanner.style.display = ready ? 'none' : 'block';
    if (welcomeSend) welcomeSend.disabled = !ready || isLoading;
    if (chatSend) chatSend.disabled = !ready || isLoading;
    if (welcomeInput) welcomeInput.disabled = !ready;
    if (chatInput) chatInput.disabled = !ready;
  }

  function pollReady() {
    var maxAttempts = 24;
    var attempt = 0;
    function check() {
      attempt++;
      var controller = new AbortController();
      var t = setTimeout(function () { controller.abort(); }, 12000);
      fetch(API_BASE + '/api/ready', { method: 'GET', signal: controller.signal })
        .then(function (r) { clearTimeout(t); return r.ok ? r.json() : {}; })
        .then(function (data) {
          if (data && data.pipeline_ready) {
            setServiceReady(true);
            return;
          }
          if (attempt < maxAttempts) setTimeout(check, 5000);
          else setServiceReady(true);
        })
        .catch(function () {
          clearTimeout(t);
          if (attempt < maxAttempts) setTimeout(check, 5000);
          else setServiceReady(true);
        });
    }
    check();
  }

  function sendQuery(queryText) {
    if (!queryText.trim()) return;
    appendMessage('user', queryText.trim(), null);
    chatInput.value = '';
    welcomeInput.value = '';
    showTyping();
    setLoading(true);
    // Backend cold start (Render etc.) can take 60–90s; use 2 min timeout
    var timeoutMs = 120000;
    var timeoutId = setTimeout(function () {
      var el = document.getElementById('typing-indicator');
      if (el) {
        var bubble = el.querySelector('.message-typing');
        if (bubble) bubble.textContent = 'Taking longer than usual (server may be waking up). Please wait…';
      }
    }, 15000);
    var controller = new AbortController();
    var fetchTimeout = setTimeout(function () { controller.abort(); }, timeoutMs);
    fetch(API_BASE + '/api/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: queryText.trim() }),
      signal: controller.signal
    })
      .then(function (r) {
        clearTimeout(timeoutId);
        clearTimeout(fetchTimeout);
        if (!r.ok) {
          if (r.status === 503) {
            return r.json().then(function (d) {
              throw new Error(d.detail || 'Service is warming up. Please retry in 30 seconds.');
            });
          }
          throw new Error(r.statusText || 'Request failed');
        }
        return r.json();
      })
      .then(function (data) {
        hideTyping();
        appendMessage('assistant', data.answer || 'No answer returned.', data.citation_url, data.source);
      })
      .catch(function (err) {
        clearTimeout(timeoutId);
        clearTimeout(fetchTimeout);
        hideTyping();
        var msg = err.name === 'AbortError'
          ? 'The request took too long (server may be starting). Try again in a moment — the second try is usually faster.'
          : (err.message || 'Sorry, something went wrong. Please try again.');
        appendMessage('assistant', msg, null);
      })
      .finally(function () {
        setLoading(false);
      });
  }

  // Show welcome screen first so user never sees a blank page if something below throws
  showScreen('welcome');

  if (welcomeSend) {
    welcomeSend.addEventListener('click', function () {
      var q = welcomeInput ? welcomeInput.value.trim() : '';
      if (q) { showScreen('chat'); sendQuery(q); }
    });
  }
  if (welcomeInput) {
    welcomeInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        var q = welcomeInput.value.trim();
        if (q) { showScreen('chat'); sendQuery(q); }
      }
    });
  }

  if (chatSend) {
    chatSend.addEventListener('click', function () {
      var q = chatInput ? chatInput.value.trim() : '';
      if (q) sendQuery(q);
    });
  }
  if (chatInput) {
    chatInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        var q = chatInput.value.trim();
        if (q) sendQuery(q);
      }
    });
  }

  if (backToWelcome) {
    backToWelcome.addEventListener('click', function (e) {
      e.preventDefault();
      showScreen('welcome');
    });
  }

  if (navRefresh) {
    navRefresh.addEventListener('click', function (e) {
      e.preventDefault();
      if (chatMessages) chatMessages.innerHTML = '';
      showScreen('chat');
    });
  }

  document.querySelectorAll('.nav-item[data-screen]').forEach(function (el) {
    el.addEventListener('click', function (e) {
      e.preventDefault();
      showScreen(el.getAttribute('data-screen'));
    });
  });

  // Fetch and display last_updated from backend (schemes.json / scheduler)
  function loadLastUpdated() {
    var el = document.getElementById('welcome-last-updated');
    if (!el) return;
    fetch(API_BASE + '/api/last-updated')
      .then(function (r) { return r.ok ? r.json() : {}; })
      .then(function (data) {
        var lu = (data && data.last_updated) || '';
        if (lu) {
          try {
            var d = new Date(lu);
            if (!isNaN(d.getTime())) {
              el.textContent = 'Data last updated: ' + d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
              el.style.display = '';
              return;
            }
          } catch (e) {}
          el.textContent = 'Data last updated: ' + lu;
          el.style.display = '';
        } else {
          el.style.display = 'none';
        }
      })
      .catch(function () { el.style.display = 'none'; });
  }
  loadLastUpdated();

  // Enable UI immediately; serverless backend is fast enough, and errors are handled per-request.
  setServiceReady(true);
})();
