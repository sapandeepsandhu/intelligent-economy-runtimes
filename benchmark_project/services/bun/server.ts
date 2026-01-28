// determinism
const SEED = 12345;
const rng = (seed: number) => {
    let t = seed += 0x6D2B79F5;
    t = Math.imul(t ^ t >>> 15, t | 1);
    t ^= t + Math.imul(t ^ t >>> 7, t | 61);
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
};

const port = Number(process.env.PORT) || 3001;

Bun.serve({
    port,
    fetch(req, server) {
        const url = new URL(req.url);

        // -- OTel Simulation --
        let span: any = null;
        if (process.env.OTEL_ENABLED === 'true') {
            span = {
                traceId: Math.random().toString(36).substring(2, 15),
                spanId: Math.random().toString(36).substring(2, 15),
                start: process.hrtime.bigint(),
                attributes: {
                    'http.method': req.method,
                    'http.url': req.url,
                    'host': url.host,
                }
            };
        }

        const handleResponse = (res: Response) => {
            if (span) {
                span.end = process.hrtime.bigint();
                span.attributes['http.status_code'] = res.status;
                // Simulate export serialization cost
                JSON.stringify(span);
            }
            return res;
        };

        // -- W3: WebSocket upgrade --
        if (url.pathname === '/ws') {
            const success = server.upgrade(req);
            if (success) return undefined;
            return handleResponse(new Response('WebSocket upgrade failed', { status: 500 }));
        }

        // -- W1: REST API --

        // 1. Health check
        if (url.pathname === '/health') {
            return handleResponse(Response.json({ status: 'ok' }));
        }

        // 2. Item by ID
        // Match /item/:id
        const itemMatch = url.pathname.match(/^\/item\/(\d+)$/);
        if (itemMatch) {
            const id = itemMatch[1];
            return handleResponse(Response.json({
                id,
                name: `Item ${id}`,
                description: `This is the description for item ${id}. It contains some text to make the payload larger.`,
                price: (rng(Number(id) || SEED) * 100).toFixed(2),
                tags: ['benchmark', 'bun', 'native'],
                stock: Math.floor(rng(Number(id) || SEED) * 1000)
            }));
        }

        // 3. Rank (JSON processing)
        if (url.pathname === '/rank' && req.method === 'POST') {
            return req.json().then(body => {
                const items = body.items;
                if (!items || !Array.isArray(items)) {
                    return handleResponse(new Response(JSON.stringify({ error: 'Invalid input' }), { status: 400 }));
                }
                const sorted = items.sort((a: any, b: any) => b.score - a.score);
                return handleResponse(Response.json({ sorted }));
            });
        }

        return handleResponse(new Response('Not Found', { status: 404 }));
    },
    websocket: {
        message(ws, message) {
            // Broadcast to all
            // Bun's publish is native
            // We need to subscribe them to a topic first? 
            // Or we can just iterate?
            // Bun has pub/sub built-in with 'publish'.
            // Creating a "global" topic for this benchmark.
            ws.publish("benchmark", message);
        },
        open(ws) {
            ws.subscribe("benchmark");
        },
        close(ws) {
            ws.unsubscribe("benchmark");
        }
    }
});

console.log(`Bun server running on port ${port}`);
