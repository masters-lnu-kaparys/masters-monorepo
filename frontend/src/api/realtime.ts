type Connection = {
  start(): Promise<void>;
  stop(): Promise<void>;
  onreconnecting(callback: () => void): void;
  onreconnected(callback: () => void): void;
  onclose(callback: () => void): void;
};

/** Initial failures and exhausted reconnects need their own bounded retry loop. */
export function maintainConnection(connection: Connection, status: (online: boolean) => void,
  retryMs = 5000, schedule = globalThis.setTimeout, cancel = globalThis.clearTimeout) {
  let disposed = false;
  let starting = false;
  let timer: ReturnType<typeof setTimeout> | undefined;
  function retry() {
    if (!disposed && timer === undefined) timer = schedule(() => { timer = undefined; void start(); }, retryMs);
  }
  async function start() {
    if (disposed || starting) return;
    starting = true;
    try {
      await connection.start();
      if (disposed) await connection.stop();
      else status(true);
    } catch {
      if (!disposed) { status(false); retry(); }
    } finally { starting = false; }
  }
  connection.onreconnecting(() => { if (!disposed) status(false); });
  connection.onreconnected(() => { if (!disposed) status(true); });
  connection.onclose(() => { if (!disposed) { status(false); retry(); } });
  void start();
  return () => {
    disposed = true;
    if (timer !== undefined) cancel(timer);
    void connection.stop().catch(() => {});
  };
}
