// Vercel serverless: proxy GET /api/health to backend, or return ok if no backend
const BACKEND = process.env.BACKEND_URL || '';

export default async function handler(req, res) {
  if (!BACKEND) {
    return res.status(200).json({ status: 'ok', backend: false });
  }
  try {
    const url = BACKEND.replace(/\/$/, '') + '/api/health';
    const response = await fetch(url);
    const data = await response.json().catch(() => ({}));
    res.status(response.status).json(data);
  } catch (e) {
    res.status(502).json({ status: 'error', message: e.message });
  }
}
