// Vercel serverless: proxy POST /api/query to backend (set BACKEND_URL in Vercel env)
const BACKEND = process.env.BACKEND_URL || '';

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'Method not allowed' });
  }
  if (!BACKEND) {
    return res.status(503).json({ error: 'Backend not configured. Set BACKEND_URL in Vercel.' });
  }
  try {
    const url = BACKEND.replace(/\/$/, '') + '/api/query';
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req.body || {}),
    });
    const data = await response.json().catch(() => ({}));
    res.status(response.status).json(data);
  } catch (e) {
    res.status(502).json({ error: 'Backend unreachable', message: e.message });
  }
}
