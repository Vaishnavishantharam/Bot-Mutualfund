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
    chatMessages.appendChild(wrap);
    chatMessages.scrollTop = chatMessages.scrollHeight;
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
    chatMessages.appendChild(wrap);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function hideTyping() {
    const el = document.getElementById('typing-indicator');
    if (el) el.remove();
  }

  function setLoading(loading) {
    welcomeSend.disabled = loading;
    chatSend.disabled = loading;
  }

  function sendQuery(queryText) {
    if (!queryText.trim()) return;
    appendMessage('user', queryText.trim(), null);
    chatInput.value = '';
    welcomeInput.value = '';
    showTyping();
    setLoading(true);
    fetch(API_BASE + '/api/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: queryText.trim() })
    })
      .then(function (r) {
        if (!r.ok) throw new Error(r.statusText || 'Request failed');
        return r.json();
      })
      .then(function (data) {
        hideTyping();
        appendMessage('assistant', data.answer || 'No answer returned.', data.citation_url, data.source);
      })
      .catch(function (err) {
        hideTyping();
        appendMessage('assistant', 'Sorry, something went wrong. Please try again. (' + (err.message || 'Error') + ')', null);
      })
      .finally(function () {
        setLoading(false);
      });
  }

  welcomeSend.addEventListener('click', function () {
    var q = welcomeInput.value.trim();
    if (q) {
      showScreen('chat');
      sendQuery(q);
    }
  });
  welcomeInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
      var q = welcomeInput.value.trim();
      if (q) {
        showScreen('chat');
        sendQuery(q);
      }
    }
  });

  chatSend.addEventListener('click', function () {
    var q = chatInput.value.trim();
    if (q) sendQuery(q);
  });
  chatInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
      var q = chatInput.value.trim();
      if (q) sendQuery(q);
    }
  });

  backToWelcome.addEventListener('click', function (e) {
    e.preventDefault();
    showScreen('welcome');
  });

  navRefresh.addEventListener('click', function (e) {
    e.preventDefault();
    chatMessages.innerHTML = '';
    showScreen('chat');
  });

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

  // Start on welcome
  showScreen('welcome');
})();
