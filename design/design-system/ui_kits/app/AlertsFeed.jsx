const NS = window.ChainwatchDesignSystem_f0e832;
const { SeverityBadge, LiveIndicator, Input, Select, AddressLabel } = NS;

const ALERTS = [
  { id: 1, addr: 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh', sev: 'critical', desc: 'wallet swept, no change output', time: '2m ago' },
  { id: 2, addr: '3FZbgi29cpjq2GjdwV8eyHuJJnkLtktZc5', sev: 'high', desc: 'fan-in from 14 sources in 1 hour', time: '11m ago' },
  { id: 3, addr: '1BoatSLRHtKNngkdXEeobR76b53LETtpyT', sev: 'medium', desc: 'output dormant 5 years before spend', time: '38m ago' },
  { id: 4, addr: 'bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq', sev: 'medium', desc: 'inbound from address with no prior history', time: '1h ago' },
  { id: 5, addr: '3M219KR5vEneNb47ewrPfWyb5jQ2DjxRP6', sev: 'low', desc: 'first transaction on address', time: '3h ago' },
];

function AlertsFeed({ onSelect }) {
  return (
    <div style={{ fontFamily: 'var(--font-sans)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-6)' }}>
        <h1 style={{ fontSize: 'var(--text-display-size)', fontWeight: 600, margin: 0, color: 'var(--text-primary)' }}>alerts</h1>
        <LiveIndicator secondsAgo={4} />
      </div>
      <div style={{ display: 'flex', gap: 'var(--space-3)', marginBottom: 'var(--space-6)' }}>
        <Input placeholder="search address or tx id" style={{ flex: 1 }} />
        <Select options={[{ value: 'all', label: 'all severities' }, { value: 'critical', label: 'critical' }, { value: 'high', label: 'high' }]} />
      </div>
      <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-card)', overflow: 'hidden' }}>
        <div style={{ background: 'var(--surface-raised)', display: 'flex', padding: 'var(--table-cell-pad-v) var(--table-cell-pad-h)', fontSize: 'var(--text-label-size)', color: 'var(--text-secondary)', fontWeight: 500 }}>
          <div style={{ flex: 2 }}>address</div>
          <div style={{ flex: 1 }}>severity</div>
          <div style={{ flex: 3 }}>description</div>
          <div style={{ flex: 1, textAlign: 'right' }}>seen</div>
        </div>
        {ALERTS.map((a) => (
          <div
            key={a.id}
            onClick={() => onSelect(a)}
            style={{ display: 'flex', alignItems: 'center', height: 'var(--table-row-height)', padding: '0 var(--table-cell-pad-h)', borderBottom: '1px solid var(--border)', cursor: 'pointer' }}
            onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--surface-raised)')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
          >
            <div style={{ flex: 2 }}><AddressLabel address={a.addr} head={6} tail={4} /></div>
            <div style={{ flex: 1 }}><SeverityBadge severity={a.sev} /></div>
            <div style={{ flex: 3, fontSize: 'var(--text-body-small-size)', color: 'var(--text-primary)' }}>{a.desc}</div>
            <div style={{ flex: 1, textAlign: 'right', fontSize: 'var(--text-label-size)', color: 'var(--text-muted)' }}>{a.time}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

window.AlertsFeed = AlertsFeed;
