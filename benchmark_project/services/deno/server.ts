// determinism
const SEED = 12345;
const rng = (seed: number) => {
    let t = seed += 0x6D2B79F5;
    t = Math.imul(t ^ t >>> 15, t | 1);
    t ^= t + Math.imul(t ^ t >>> 7, t | 61);
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
};

const port = Number(Deno.env.get("PORT")) || 3002;

Deno.serve({
    port,
    handler: async (req) => {
        const url = new URL(req.url);

        // -- OTel Simulation --
        let span: any = null;
        if (Deno.env.get("OTEL_ENABLED") === 'true') {
            span = {
                traceId: crypto.randomUUID(),
                spanId: crypto.randomUUID(),
                start: performance.now(),
                attributes: {
                    'http.method': req.method,
                    'http.url': req.url,
                    'host': url.host,
                }
            };
        }

        const handleResponse = (res: Response) => {
            if (span) {
                span.end = performance.now();
                span.duration = span.end - span.start;
                span.attributes['http.status_code'] = res.status;
                // Simulate export serialization cost
                JSON.stringify(span);
            }
            return res;
        };

        // -- W3: WebSocket upgrade --
        if (url.pathname === '/ws') {
            const { socket, response } = Deno.upgradeWebSocket(req);

            socket.addEventListener("open", () => {
                // console.log("a client connected!");
            });

            // Use BroadcastChannel for pub/sub across isolates if needed, 
            // but for single instance benchmark, we can simple use a global set?
            // Or just a BroadcastChannel is cleaner for Deno.
            const bc = new BroadcastChannel("benchmark");

            socket.addEventListener("message", (event) => {
                // Broadcast to others via BC
                bc.postMessage(event.data);
            });

            bc.onmessage = (event) => {
                if (socket.readyState === WebSocket.OPEN) {
                    socket.send(event.data);
                }
            };

            socket.addEventListener("close", () => {
                bc.close();
            });

            return handleResponse(response);
        }

        // -- W1: REST API --

        // 1. Health check
        if (url.pathname === '/health') {
            return handleResponse(Response.json({ status: 'ok' }));
        }

        // 2. Item by ID
        const itemMatch = url.pathname.match(/^\/item\/(\d+)$/);
        if (itemMatch) {
            const id = itemMatch[1];
            return handleResponse(Response.json({
                id,
                name: `Item ${id}`,
                description: `This is the description for item ${id}. It contains some text to make the payload larger.`,
                price: (rng(Number(id) || SEED) * 100).toFixed(2),
                tags: ['benchmark', 'deno', 'native'],
                stock: Math.floor(rng(Number(id) || SEED) * 1000)
            }));
        }

        // 3. Rank (JSON processing)
        if (url.pathname === '/rank' && req.method === 'POST') {
            try {
                const body = await req.json();
                const items = body.items;
                if (!items || !Array.isArray(items)) {
                    return handleResponse(new Response(JSON.stringify({ error: 'Invalid input' }), { status: 400 }));
                }
                const sorted = items.sort((a: any, b: any) => b.score - a.score);
                return handleResponse(Response.json({ sorted }));
            } catch (e) {
                return handleResponse(new Response(JSON.stringify({ error: 'Invalid JSON' }), { status: 400 }));
            }
        }

        return handleResponse(new Response('Not Found', { status: 404 }));
    }
});
