const NS = window.ChainwatchDesignSystem_f0e832;
const { SeverityBadge, ConfirmationBadge, AddressLabel, MonetaryAmount, DataTable, Button, Card } = NS;

const TX = [
  { txid: 'f4a1c9e2b7d3a6f01e5c8b9d2a4f6e8c1b3d5a7f9e0c2b4d6a8f0e2c4b6a8d0e', addr: 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh', amt: 0.42100000, conf: 0 },
  { txid: 'a2b4c6d8e0f2a4b6c8d0e2f4a6b8c0d2e4f6a8b0c2d4e6f8a0b2c4d6e8f0a2b4', addr: '3FZbgi29cpjq2GjdwV8eyHuJJnkLtktZc5', amt: 0.00000320, conf: 3 },
  { txid: 'c6d8e0f2a4b6c8d0e2f4a6b8c0d2e4f6a8b0c2d4e6f8a0b2c4d6e8f0a2b4c6d8', addr: '1BoatSLRHtKNngkdXEeobR76b53LETtpyT', amt: 1.00000000, conf: 210 },
];

function CaseDetail({ alert, onBack }) {
  return (
    <div style={{ fontFamily: 'var(--font-sans)' }}>
      <button onClick={onBack} style={{ border: 'none', background: 'none', color: 'var(--text-primary)', textDecoration: 'underline', fontSize: 'var(--text-body-small-size)', cursor: 'pointer', padding: 0, marginBottom: 'var(--space-4)' }}>&larr; back to alerts</button>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-8)' }}>
        <div>
          <h1 style={{ fontSize: 'var(--text-h1-size)', fontWeight: 600, margin: '0 0 8px', color: 'var(--text-primary)' }}>case review</h1>
          <AddressLabel address={alert.addr} />
        </div>
        <SeverityBadge severity={alert.sev} />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 'var(--space-6)', marginBottom: 'var(--space-8)' }}>
        <Card>
          <div style={{ fontSize: 'var(--text-label-size)', color: 'var(--text-secondary)', marginBottom: 4 }}>total exposure</div>
          <MonetaryAmount value={1.4210032} unit="btc" />
        </Card>
        <Card>
          <div style={{ fontSize: 'var(--text-label-size)', color: 'var(--text-secondary)', marginBottom: 4 }}>linked addresses</div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-mono-body-size)' }}>7</div>
        </Card>
        <Card>
          <div style={{ fontSize: 'var(--text-label-size)', color: 'var(--text-secondary)', marginBottom: 4 }}>flagged since</div>
          <div style={{ fontSize: 'var(--text-body-small-size)', color: 'var(--text-primary)' }}>2 hours ago</div>
        </Card>
      </div>
      <h2 style={{ fontSize: 'var(--text-h2-size)', fontWeight: 600, marginBottom: 'var(--space-4)', color: 'var(--text-primary)' }}>transactions</h2>
      <DataTable
        columns={[{ key: 'txid', label: 'transaction' }, { key: 'addr', label: 'counterparty' }, { key: 'conf', label: 'confirmations' }, { key: 'amt', label: 'amount', align: 'right' }]}
        rows={TX}
        renderCell={(row, col) => {
          if (col.key === 'txid') return <AddressLabel address={row.txid} head={8} tail={6} />;
          if (col.key === 'addr') return <AddressLabel address={row.addr} head={6} tail={4} />;
          if (col.key === 'conf') return <ConfirmationBadge confirmations={row.conf} />;
          return <MonetaryAmount value={row.amt} />;
        }}
      />
      <div style={{ display: 'flex', gap: 'var(--space-3)', marginTop: 'var(--space-8)' }}>
        <Button variant="primary">escalate case</Button>
        <Button variant="secondary">mark reviewed</Button>
        <Button variant="destructive">dismiss</Button>
      </div>
    </div>
  );
}
window.CaseDetail = CaseDetail;
