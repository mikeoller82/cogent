#!/usr/bin/env bun
/**
 * Cbencent TUI — thin bootstrap entry point.
 *
 * Handles --help and --version before loading OpenTUI. This avoids
 * triggering OpenTUI's platform-native .so loading (which uses a
 * relative path from the build bundle that depends on CWD).
 *
 * The main OpenTUI app is deferred via await import() in the runner/
 * module so that trivial CLI flags exit fast without native binary
 * resolution.
 */

const args = process.argv.slice(2);

if (args.includes('--help') || args.includes('-h')) {
  console.log(`
\x1b[35m╔═══╗╔═╗╔═╗╔═══╗╔═══╗╔╗──╔═══╗\x1b[0m
\x1b[35m╚══╗║║║╚╝║║║╔═╗║║╔══╝║║──║╔══╝\x1b[0m
\x1b[35m──╔╝║║║╔╗║║║╚═╝║║╚══╗║║──║╚══╗\x1b[0m
\x1b[35m╚═╝─╚╝╚╝╚╝╚╝═══╝╚═══╝╚╝──╚═══╝\x1b[0m
\x1b[38;5;245mCogent — AI co-worker  |  Terminal User Interface\x1b[0m

\x1b[1mUSAGE\x1b[0m
  cogent [options]

\x1b[1mOPTIONS\x1b[0m
  \x1b[36m-u, --url <url>\x1b[0m     Server URL (default: http://localhost:8000)
  \x1b[36m-s, --server\x1b[0m        Auto-start the Cogent backend server
  \x1b[36m-h, --help\x1b[0m          Show this help message
  \x1b[36m-v, --version\x1b[0m       Show version

\x1b[1mCOMMANDS (inside TUI)\x1b[0m
  /help     Show available commands
  /clear    Clear the conversation
  /connect  Reconnect to server
  /quit     Exit Cogent

\x1b[1mEXAMPLES\x1b[0m
  cogent                              Start TUI, connect to default server
  cogent -u http://10.0.0.5:8000      Connect to remote server
`);
  process.exit(0);
}

if (args.includes('--version') || args.includes('-v')) {
  console.log('Cogent TUI v0.1');
  process.exit(0);
}

// Ensure CWD matches bundle location for OpenTUI .so loading
process.chdir(new URL('.', import.meta.url).pathname);
// Defer OpenTUI import so native .so loading only happens when actually
// rendering the TUI.
await import('./runner/main.js');
