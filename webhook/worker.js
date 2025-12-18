/**
 * Cloudflare Worker: Athlete Intake Webhook
 * 
 * Receives form submissions from athlete-questionnaire.html
 * Validates data, then triggers GitHub Actions via repository_dispatch
 * 
 * SETUP:
 * 1. Create a Cloudflare Worker at dash.cloudflare.com
 * 2. Paste this code
 * 3. Add environment variables:
 *    - GITHUB_TOKEN: Personal Access Token with repo scope
 *    - ALLOWED_ORIGINS: Comma-separated allowed origins (e.g., "https://wattgod.github.io,http://localhost:3000")
 * 4. Deploy and copy the worker URL
 * 5. Update athlete-questionnaire.html with the worker URL
 */

// Disposable email domains to block
const DISPOSABLE_DOMAINS = [
  '10minutemail.com', 'guerrillamail.com', 'mailinator.com', 'tempmail.com',
  'throwaway.email', 'fakeinbox.com', 'trashmail.com', 'maildrop.cc',
  'yopmail.com', 'temp-mail.org', 'getnada.com', 'mohmal.com'
];

export default {
  async fetch(request, env) {
    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return handleCORS(request, env);
    }

    // Only allow POST
    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }

    // Check origin
    const origin = request.headers.get('Origin');
    const allowedOrigins = (env.ALLOWED_ORIGINS || 'https://wattgod.github.io').split(',');
    
    if (!allowedOrigins.some(allowed => origin?.startsWith(allowed.trim()))) {
      return new Response('Forbidden', { status: 403 });
    }

    try {
      const data = await request.json();
      
      // Validate submission
      const validation = validateSubmission(data);
      if (!validation.valid) {
        return jsonResponse({ error: validation.error }, 400, origin);
      }

      // Generate athlete ID from email
      const athleteId = generateAthleteId(data.email);

      // Trigger GitHub Actions
      const githubResponse = await triggerGitHubAction(env.GITHUB_TOKEN, {
        athlete_id: athleteId,
        email: data.email,
        name: data.name,
        coaching_tier: data.coaching_tier,
        data: data
      });

      if (!githubResponse.ok) {
        const error = await githubResponse.text();
        console.error('GitHub API error:', error);
        return jsonResponse({ error: 'Failed to process submission' }, 500, origin);
      }

      return jsonResponse({
        success: true,
        message: 'Intake received! Check your email within 24 hours.',
        athlete_id: athleteId
      }, 200, origin);

    } catch (error) {
      console.error('Worker error:', error);
      return jsonResponse({ error: 'Invalid request' }, 400, origin);
    }
  }
};

function validateSubmission(data) {
  // Required fields
  const required = ['name', 'email', 'coaching_tier'];
  for (const field of required) {
    if (!data[field]) {
      return { valid: false, error: `Missing required field: ${field}` };
    }
  }

  // Email format
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(data.email)) {
    return { valid: false, error: 'Invalid email format' };
  }

  // Check for disposable email
  const emailDomain = data.email.split('@')[1].toLowerCase();
  if (DISPOSABLE_DOMAINS.includes(emailDomain)) {
    return { valid: false, error: 'Please use a non-disposable email address' };
  }

  // Honeypot check
  if (data.website) {
    return { valid: false, error: 'Bot detected' };
  }

  // Coaching tier validation
  if (!['min', 'mid', 'max'].includes(data.coaching_tier)) {
    return { valid: false, error: 'Invalid coaching tier' };
  }

  return { valid: true };
}

function generateAthleteId(email) {
  // Create URL-safe athlete ID from email
  const base = email.split('@')[0]
    .toLowerCase()
    .replace(/[^a-z0-9]/g, '-')
    .replace(/-+/g, '-')
    .substring(0, 20);
  
  // Add short hash for uniqueness
  const hash = Array.from(email)
    .reduce((acc, char) => ((acc << 5) - acc) + char.charCodeAt(0), 0)
    .toString(36)
    .replace('-', '')
    .substring(0, 4);
  
  return `${base}-${hash}`;
}

async function triggerGitHubAction(token, payload) {
  return fetch('https://api.github.com/repos/wattgod/athlete-profiles/dispatches', {
    method: 'POST',
    headers: {
      'Accept': 'application/vnd.github.v3+json',
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      'User-Agent': 'Gravel-God-Intake-Worker'
    },
    body: JSON.stringify({
      event_type: 'athlete-intake',
      client_payload: payload
    })
  });
}

function jsonResponse(data, status, origin) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': origin || '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type'
    }
  });
}

function handleCORS(request, env) {
  const origin = request.headers.get('Origin');
  return new Response(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': origin || '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
      'Access-Control-Max-Age': '86400'
    }
  });
}

