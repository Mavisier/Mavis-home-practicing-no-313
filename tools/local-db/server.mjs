// Optional local development only. Compose uses native PostgreSQL instead.
import { mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { PGlite } from '@electric-sql/pglite';
import { PGLiteSocketServer } from '@electric-sql/pglite-socket';
import { vector } from '@electric-sql/pglite-pgvector';

const path = fileURLToPath(new URL('../../.local/pglite', import.meta.url));
await mkdir(path, { recursive: true });
const db = await PGlite.create({ dataDir: path, extensions: { vector } });
// The socket wrapper defaults to one client. Allow the API, tests and migration
// CLI to connect together; PGlite still serializes queries within one process.
const server = new PGLiteSocketServer({ db, host: '127.0.0.1', port: 55432, maxConnections: 16 });
await server.start();
console.log('Local development PostgreSQL/PGlite listening at 127.0.0.1:55432');
console.log('This is a single-process development database, not the Compose deployment.');
let closing = false;
async function shutdown() {
  if (closing) return;
  closing = true;
  await server.stop();
  await db.close();
  process.exit(0);
}
process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
