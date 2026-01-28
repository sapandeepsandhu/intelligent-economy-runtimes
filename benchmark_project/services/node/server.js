const fastify = require('fastify')({ logger: false });
const WebSocket = require('ws');

// determinism
const SEED = 12345;
const rng = (seed) => {
  let t = seed += 0x6D2B79F5;
  t = Math.imul(t ^ t >>> 15, t | 1);
  t ^= t + Math.imul(t ^ t >>> 7, t | 61);
  return ((t ^ t >>> 14) >>> 0) / 4294967296;
};

// -- OTel Simulation --
if (process.env.OTEL_ENABLED === 'true') {
  // Simulate heavy instrumentation overhead:
  // 1. Create span object
  // 2. Add attributes
  // 3. Serialize (simulate export)
  fastify.addHook('onRequest', async (request, reply) => {
    request.span = {
      traceId: Math.random().toString(36).substring(2, 15),
      spanId: Math.random().toString(36).substring(2, 15),
      start: process.hrtime.bigint(),
      attributes: {
        'http.method': request.method,
        'http.url': request.url,
        'host': request.headers.host,
        'user_agent': request.headers['user-agent']
      }
    };
  });

  fastify.addHook('onResponse', async (request, reply) => {
    if (request.span) {
      request.span.end = process.hrtime.bigint();
      request.span.duration = request.span.end - request.span.start;
      request.span.attributes['http.status_code'] = reply.statusCode;
      // Simulate export serialization cost
      JSON.stringify(request.span);
    }
  });
}

// -- W1: REST API --

// 1. Health check
fastify.get('/health', async (request, reply) => {
  return { status: 'ok' };
});

// 2. Item by ID (Simulate DB fetch)
fastify.get('/item/:id', async (request, reply) => {
  const { id } = request.params;
  return {
    id,
    name: `Item ${id}`,
    description: `This is the description for item ${id}. It contains some text to make the payload larger.`,
    price: (rng(Number(id) || SEED) * 100).toFixed(2),
    tags: ['benchmark', 'node', 'fastify'],
    stock: Math.floor(rng(Number(id) || SEED) * 1000)
  };
});

// 3. Rank (JSON processing)
fastify.post('/rank', async (request, reply) => {
  const { items } = request.body;
  if (!items || !Array.isArray(items)) {
    return reply.code(400).send({ error: 'Invalid input' });
  }
  // Sort items by score descending
  const sorted = items.sort((a, b) => b.score - a.score);
  return { sorted };
});

// -- W3: WebSockets --
// We will attach WS server to the same HTTP server
const start = async () => {
  try {
    const port = process.env.PORT || 3000;
    await fastify.ready();
    const server = fastify.server;

    const wss = new WebSocket.Server({ server });

    wss.on('connection', (ws) => {
      ws.on('message', (message) => {
        // Echo or Broadcast? W3 says pub-sub: N publishers, M subscribers.
        // For simplicity in this benchmark:
        // - If message starts with "sub", we verify subscription (noop here)
        // - If message starts with "pub", we broadcast to all clients
        // - Or just broadcast everything to everyone (simple chat room logic)

        // Broadcast to all connected clients
        wss.clients.forEach((client) => {
          if (client.readyState === WebSocket.OPEN) {
            client.send(message);
          }
        });
      });
    });

    await fastify.listen({ port, host: '0.0.0.0' });
    console.log(`Node.js server running on port ${port}`);
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();
