/**
 * Cogent TUI main runner.
 *
 * Loaded by cli.tsx after argv parsing. All OpenTUI imports live here
 * so --help and --version don't trigger native binary loading.
 *
 * This module is imported via await import() from the entrypoint to
 * defer native-module side effects until after early-exit flags are
 * handled. This is a valid exception to the no-dynamic-import rule:
 * OpenTUI's createCliRenderer() eagerly loads a platform-native .so
 * at module-evaluation time, and the build-time bundler crams the .so
 * into dist/ but uses a relative path that fails when CWD differs.
 * Deferring avoids that crash for trivial flags.
 */

import { createRoot } from '@opentui/react';
import { createCliRenderer } from '@opentui/core';
import { App } from '../App';
import { spawn } from 'bun';
import { resolve } from 'path';
interface CliArgs {
  baseUrl: string;
  startServer: boolean;
}

function parseArgs(): CliArgs {
  const args = process.argv.slice(2);
  const parsed: CliArgs = {
    baseUrl: 'http://localhost:8000',
    startServer: false,
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--url':
      case '-u':
        parsed.baseUrl = args[++i] || parsed.baseUrl;
        break;
      case '--server':
      case '-s':
        parsed.startServer = true;
        break;
    }
  }

  return parsed;
}

/** Check MongoDB is reachable on default port. */
async function checkMongoDB(): Promise<boolean> {
  try {
    const sock = await Bun.connect({
      hostname: '127.0.0.1',
      port: 27017,
      socket: { open() {}, close() {}, data() {}, drain() {}, error() {} },
    });
    sock.end();
    return true;
  } catch {
    return false;
  }
}

/** Poll for the server port to accept TCP connections. */
async function waitForServer(proc: import('bun').Subprocess, timeoutMs = 30_000): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    // If the process already exited, abort immediately
    if (proc.killed || (proc.exitCode !== null && proc.exitCode !== 0)) {
      throw new Error(`Server process exited with code ${proc.exitCode}`);
    }

    try {
      const sock = await Bun.connect({
        hostname: '127.0.0.1',
        port: 8000,
        socket: { open() {}, close() {}, data() {}, drain() {}, error() {} },
      });
      sock.end();
      return;
    } catch {
      // Port not yet open
    }
    const { promise, resolve } = Promise.withResolvers<void>();
    setTimeout(resolve, 500);
    await promise;
  }
  throw new Error(`Backend server didn't start within ${timeoutMs / 1000}s`);
}

/** Kill any process holding the given TCP port. */
function killPort(port: number): void {
  try {
    Bun.spawnSync(['fuser', '-k', `${port}/tcp`]);
  } catch {
    // fall back to lsof
  }
  try {
    const result = Bun.spawnSync(['lsof', '-ti', `:${port}`]);
    const pids = result.stdout.toString().trim();
    if (pids) {
      for (const pid of pids.split('\n')) {
        Bun.spawnSync(['kill', pid.trim()]);
      }
    }
  } catch {
    // best effort
  }
}

async function startBackendServer(): Promise<() => void> {
  // Verify MongoDB is running before attempting to start the server
  const mongoUp = await checkMongoDB();
  if (!mongoUp) {
    console.error('');
    console.error('  MongoDB is not running on localhost:27017.');
    console.error('  Start it with:  sudo systemctl start mongod');
    console.error('');
    throw new Error('MongoDB not available');
  }

  // Kill anything stale on port 8000
  killPort(8000);
  await Bun.sleep(500);

  const controller = new AbortController();
  const backendDir = resolve(import.meta.dir, '../../backend');
  const uvicornPath = resolve(backendDir, '.venv/bin/uvicorn');

  const proc = spawn({
    cmd: [uvicornPath, 'server:app', '--host', '0.0.0.0', '--port', '8000', '--log-level', 'warning'],
    cwd: backendDir,
    signal: controller.signal,
    stdio: ['ignore', 'inherit', 'inherit'],
  });

  proc.exited.then((code) => {
    if (code !== 0 && code !== null) {
      console.error(`Backend server exited with code ${code}`);
    }
  });

  try {
    await waitForServer(proc);
    return () => controller.abort();
  } catch (err) {
    controller.abort();
    throw err;
  }
}

async function main(): Promise<void> {
  const args = parseArgs();
  let stopServer: (() => void) | undefined;

  if (args.startServer) {
    console.error('Starting Cogent server...');
    try {
      stopServer = await startBackendServer();
      console.error('Cogent server is ready.');
    } catch (err) {
      console.error('Failed to start server:', err);
      process.exit(1);
    }
  }

  const renderer = await createCliRenderer({
    exitOnCtrlC: true,
    exitSignals: ['SIGINT', 'SIGTERM', 'SIGQUIT'],
    clearOnShutdown: true,
    screenMode: 'alternate-screen',
    backgroundColor: '#0d1117',
    targetFps: 30,
  });

  const root = createRoot(renderer);
  root.render(<App baseUrl={args.baseUrl} />);

  const cleanup = () => {
    stopServer?.();
    root.unmount();
  };

  process.on('SIGINT', cleanup);
  process.on('SIGTERM', cleanup);
  process.on('SIGQUIT', cleanup);
}

main().catch((err) => {
  console.error('Failed to start Cogent TUI:', err);
  process.exit(1);
});
