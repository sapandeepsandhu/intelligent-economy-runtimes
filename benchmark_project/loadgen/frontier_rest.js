import http from 'k6/http';
import { check, sleep } from 'k6';
import { randomIntBetween } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

// Configuration injected via stats
const VUS = __ENV.VUS ? parseInt(__ENV.VUS) : 10;
const DURATION = __ENV.DURATION || '30s';

export const options = {
    scenarios: {
        frontier_sweep: {
            executor: 'constant-vus',
            vus: VUS,
            duration: DURATION,
            gracefulStop: '5s',
        },
    },
    summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(90)', 'p(95)', 'p(99)'],
};

const RUNTIMES = {
    node: 'http://localhost:3000',
    bun: 'http://localhost:3001',
    deno: 'http://localhost:3002',
};

// Default to node if not provided
const TARGET = __ENV.TARGET || 'node';
const BASE_URL = RUNTIMES[TARGET];

export default function () {
    // We mix endpoints to simulate realistic traffic:
    // 80% Item Fetch (Read)
    // 20% Rank (Write/CPU)

    if (Math.random() < 0.8) {
        // Read
        const id = randomIntBetween(1, 1000);
        const res = http.get(`${BASE_URL}/item/${id}`);
        check(res, { 'status is 200': (r) => r.status === 200 });
    } else {
        // Write/Compute
        const payload = JSON.stringify({
            items: Array.from({ length: 10 }, (_, i) => ({ id: i, score: Math.random() }))
        });
        const params = { headers: { 'Content-Type': 'application/json' } };
        const res = http.post(`${BASE_URL}/rank`, payload, params);
        check(res, { 'status is 200': (r) => r.status === 200 });
    }
}
