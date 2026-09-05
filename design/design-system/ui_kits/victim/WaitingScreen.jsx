const NS = window.ChainwatchDesignSystem_f0e832;
const { AddressLabel, WarningBlock } = NS;

function SafetyNotice() {
  return (
    <WarningBlock style={{ marginTop: 'var(--space-16)' }}>
      Chainwatch will never contact you first, never ask for payment, and never ask for your keys or seed phrase. Nobody legitimate will offer to recover your funds for an upfront fee.
    </WarningBlock>
  );
}

function VictimShell({ background, children }) {
  return (
    <div style={{ background, minHeight: '100vh', padding: 'var(--space-16) var(--space-8)', fontFamily: 'var(--font-sans)', boxSizing: 'border-box' }}>
      <div style={{ maxWidth: 560, margin: '0 auto' }}>
        {children}
        <SafetyNotice />
      </div>
    </div>
  );
}

function WaitingScreen({ address }) {
  return (
    <VictimShell background="var(--surface-raised)">
      <AddressLabel address={address} />
      <p style={{ fontSize: 'var(--text-body-size)', lineHeight: 'var(--text-body-lh)', color: 'var(--text-primary)', margin: 'var(--space-6) 0 var(--space-2)' }}>
        No movement since you started watching, 3 days ago.
      </p>
      <p style={{ fontSize: 'var(--text-label-size)', color: 'var(--text-muted)', margin: 0 }}>
        Checked 12 seconds ago
      </p>
    </VictimShell>
  );
}

window.WaitingScreen = WaitingScreen;
window.VictimShell = VictimShell;
