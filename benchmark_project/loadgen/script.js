import http from 'k6/http';
import { check, sleep } from 'k6';
import ws from 'k6/ws';
import { randomIntBetween } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

export const options = {
    scenarios: {
        w1_rest: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '30s', target: 50 }, // Warmup/Ramp
                { duration: '1m', target: 50 },  // Steady state
                { duration: '10s', target: 0 },  // Cooldown
            ],
            gracefulStop: '5s',
            tags: { workload: 'w1' },
            exec: 'w1_rest',
        },
        // W3 WebSocket ignored for now in simple pilot, or add specific scenario
        // w3_ws: { ... }
    },
};

const RUNTIMES = {
    node: 'http://localhost:3000',
    bun: 'http://localhost:3001',
    deno: 'http://localhost:3002',
};

// Default to node if not provided
const TARGET = __ENV.TARGET || 'node';
const BASE_URL = RUNTIMES[TARGET];

export function w1_rest() {
    // 1. Health check (light)
    const resHealth = http.get(`${BASE_URL}/health`);
    check(resHealth, { 'health status is 200': (r) => r.status === 200 });

    // 2. Item fetch (DB simulation)
    const id = randomIntBetween(1, 1000);
    const resItem = http.get(`${BASE_URL}/item/${id}`);
    check(resItem, { 'item status is 200': (r) => r.status === 200 });

    // 3. Rank (CPU/JSON)
    const payload = JSON.stringify({
        items: Array.from({ length: 20 }, (_, i) => ({ id: i, score: Math.random() }))
    });
    const params = { headers: { 'Content-Type': 'application/json' } };
    const resRank = http.post(`${BASE_URL}/rank`, payload, params);
    check(resRank, { 'rank status is 200': (r) => r.status === 200 });

    sleep(1);
}

// TODO: W3 and W4 implementation
