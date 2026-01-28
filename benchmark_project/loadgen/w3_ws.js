import ws from 'k6/ws';
import { check, sleep } from 'k6';
import { randomString } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

export const options = {
    scenarios: {
        w3_ws: {
            executor: 'constant-vus',
            vus: 50,
            duration: '1m',
            tags: { workload: 'w3_ws' },
        },
    },
};

const RUNTIMES = {
    node: 'ws://localhost:3000',
    bun: 'ws://localhost:3001',
    deno: 'ws://localhost:3002',
};

const TARGET = __ENV.TARGET || 'node';
const BASE_URL = RUNTIMES[TARGET];

export default function () {
    const url = `${BASE_URL}/ws`; // or root for node?
    // Node: ws://host:port/
    // Bun: ws://host:port/ws (based on my implementation)
    // Deno: ws://host:port/ws

    // Adjust URL based on implementation details:
    // node server.js attaches wss to server, path is likely root or /?
    // bun server.ts checks pathname === '/ws'
    // deno server.ts checks pathname === '/ws'

    let finalUrl = url;
    if (TARGET === 'node') finalUrl = BASE_URL; // Node generic execution was root
    else finalUrl = `${BASE_URL}/ws`;

    const res = ws.connect(finalUrl, {}, function (socket) {
        socket.on('open', function open() {
            // console.log('connected');

            // Subscribe (implicit in my server code for bun/deno, node broadcasts all)

            // Publish loop
            socket.setInterval(function timeout() {
                const payload = JSON.stringify({
                    type: 'pub',
                    msg: randomString(100),
                    ts: Date.now()
                });
                socket.send(payload);
            }, 1000); // 1 msg/sec per VU
        });

        socket.on('message', function (message) {
            // Measure latency if possible?
            // k6 metrics track ws_session_duration.
            // Latency is hard to measure without a echoed timestamp.
            // Assuming server echoes or broadcasts.
            check(message, { 'received message': (m) => m && m.length > 0 });
        });

        socket.on('close', function () {
            // console.log('disconnected');
        });

        // Maintain connection for duration
        sleep(60);
    });

    check(res, { 'status is 101': (r) => r && r.status === 101 });
}
