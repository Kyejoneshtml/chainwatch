const NS2 = window.ChainwatchDesignSystem_f0e832;
const { Statement, Button } = NS2;

function MovementScreen({ txid, onAdvance }) {
  return (
    <VictimShell background="var(--surface-page)">
      <Statement style={{ marginBottom: 'var(--space-4)' }}>Your funds moved 4 hours ago.</Statement>
      <p style={{ fontSize: 'var(--text-body-size)', lineHeight: 'var(--text-body-lh)', color: 'var(--text-primary)', margin: '0 0 var(--space-6)' }}>
        0.42 BTC left this address in one transaction.
      </p>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-mono-small-size)', color: 'var(--text-secondary)', wordBreak: 'break-all', marginBottom: 'var(--space-8)' }}>
        {txid}
      </div>
      <Button variant="primary" onClick={onAdvance}>see where it went</Button>
    </VictimShell>
  );
}

window.MovementScreen = MovementScreen;
