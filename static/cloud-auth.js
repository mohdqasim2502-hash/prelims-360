// Authentication/session bridge for Prelims 360° cloud database.
window.loggedIn = false;
window.openAuth = function () {
  const modal = document.getElementById('auth');
  if (modal && !modal.open) modal.showModal();
};
async function cloudRequest(url, options={}) {
  const response = await fetch(url, {
    credentials: 'same-origin',
    headers: {'Content-Type':'application/json', ...(options.headers||{})},
    ...options
  });
  const data = await response.json().catch(()=>({error:'Unexpected server response'}));
  if (!response.ok) throw new Error(data.error || 'Request failed');
  return data;
}
window.authAction = async function(mode) {
  const username = document.getElementById('username').value.trim();
  const password = document.getElementById('password').value;
  const msg = document.getElementById('authMsg');
  msg.textContent = 'Please wait…';
  try {
    const result = await cloudRequest('/api/'+mode, {
      method:'POST', body:JSON.stringify({username,password})
    });
    window.loggedIn = true;
    msg.textContent = 'Signed in as '+result.username;
    document.getElementById('auth').close();
    updateAuthButton(result.username);
    if (typeof render === 'function') render();
    if (typeof toast === 'function') toast('Cloud sync active. Welcome, '+result.username);
  } catch(error) {
    msg.textContent = error.message;
    if (mode === 'register' && /already has an account/i.test(error.message)) {
      msg.textContent = error.message+' Use Sign in with the same username and password.';
    }
  }
};
function updateAuthButton(username) {
  const button = document.getElementById('authButton');
  if (!button) return;
  if (username) {
    button.textContent = 'Sign out · '+username;
    button.onclick = async () => {
      try {
        await cloudRequest('/api/logout',{method:'POST',body:'{}'});
        window.loggedIn = false;
        button.textContent = 'Sign in';
        button.onclick = window.openAuth;
        if (typeof render === 'function') render();
        if (typeof toast === 'function') toast('Signed out');
      } catch(e) { if (typeof toast === 'function') toast(e.message); }
    };
  } else {
    button.textContent = 'Sign in';
    button.onclick = window.openAuth;
  }
}
window.addEventListener('DOMContentLoaded', async () => {
  try {
    const me = await cloudRequest('/api/me');
    window.loggedIn = !!me.logged_in;
    updateAuthButton(me.logged_in ? me.username : null);
    if (me.logged_in && typeof render === 'function') render();
  } catch(e) {
    updateAuthButton(null);
    console.error('Session check failed:',e);
  }
});
