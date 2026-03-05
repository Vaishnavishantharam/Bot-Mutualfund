// Vercel serverless: proxy GET /api/last-updated to backend
const BACKEND = process.env.BACKEND_URL || '';

export default async function handler(req, res) {
  if (!BACKEND) {
    return res.status(200).json({ last_updated: '' });
  }
  try {
    const url = BACKEND.replace(/\/$/, '') + '/api/last-updated';
    const response = await fetch(url);
    const data = await response.json().catch(() => ({}));
    res.status(response.status).json(data);
  } catch (e) {
    res.status(200).json({ last_updated: '' });
  }
}
