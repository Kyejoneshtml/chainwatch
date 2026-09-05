const NS = window.ChainwatchDesignSystem_f0e832;
const { Button, Card, AddressLabel, MonetaryAmount, SeverityBadge, ConfirmationBadge, LiveIndicator } = NS;

const TX = [
  { date: '2026-08-09', dir: 'in', addr: '3FZbgi29cpjq2GjdwV8eyHuJJnkLtktZc5', amt: 0.42100000, conf: 3 },
  { date: '2026-08-09', dir: 'out', addr: '1BoatSLRHtKNngkdXEeobR76b53LETtpyT', amt: 0.00000320, conf: 0 },
  { date: '2026-08-07', dir: 'in', addr: 'bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq', amt: 0.05000000, conf: 210 },
  { date: '2026-08-02', dir: 'out', addr: '3M219KR5vEneNb47ewrPfWyb5jQ2DjxRP6', amt: 4.80000000, conf: 412 },
  { date: '2026-07-30', dir: 'in', addr: 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh', amt: 1.00000000, conf: 890 },
];

const FACTORS = [
  { sev: 'critical', label: 'wallet swept in a single transaction, no change output returned', delta: '+35' },
  { sev: 'high', label: 'fan-in from 14 sources within 1 hour', delta: '+22' },
  { sev: 'medium', label: 'output dormant 5 years before being spent', delta: '+9' },
];
const OVERALL_SEVERITY = FACTORS.some(f => f.sev === 'critical') ? 'critical' : FACTORS.some(f => f.sev === 'high') ? 'high' : 'medium';

const SPARK = [20, 35, 15, 60, 40, 80, 30, 55, 25, 70, 45, 90, 20, 38, 60, 33, 15, 50, 65, 28];

function Stat({ label, children }) {
  return (
    <div style={{ textAlign: 'right' }}>
      <div style={{ fontSize: 'var(--text-label-size)', color: 'var(--text-secondary)', marginBottom: 4 }}>{label}</div>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-mono-body-size)', fontVariantNumeric: 'tabular-nums', color: 'var(--text-primary)' }}>{children}</div>
    </div>
  );
}

function SectionTitle({ children }) {
  return <h2 style={{ fontSize: 'var(--text-label-size)', textTransform: 'lowercase', color: 'var(--text-secondary)', fontWeight: 500, margin: '0 0 var(--space-4)' }}>{children}</h2>;
}

function AddressOverview({ onBack }) {
  return (
    <div style={{ fontFamily: 'var(--font-sans)' }}>
      <button onClick={onBack} style={{ border: 'none', background: 'none', color: 'var(--text-primary)', textDecoration: 'underline', fontSize: 'var(--text-body-small-size)', cursor: 'pointer', padding: 0, marginBottom: 'var(--space-6)' }}>&larr; back</button>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-12)' }}>
        <AddressLabel address="bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh" />
        <Button variant="primary">watch this address</Button>
      </div>

      <div style={{ marginBottom: 'var(--space-12)' }}>
        <SectionTitle>overview</SectionTitle>
        <Card style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 'var(--space-6)' }}>
          <Stat label="balance">0.42100000</Stat>
          <Stat label="total received">3.88000000</Stat>
          <Stat label="total sent">3.45900000</Stat>
          <Stat label="tx count">128</Stat>
          <Stat label="first seen">2019-03-11</Stat>
          <Stat label="last seen">2026-08-09</Stat>
        </Card>
      </div>

      <div style={{ marginBottom: 'var(--space-12)' }}>
        <SectionTitle>risk</SectionTitle>
        <div style={{ display: 'flex', gap: 'var(--space-6)' }}>
          <Card style={{ width: 160, flex: 'none', textAlign: 'center' }}>
            <div style={{ fontSize: 'var(--text-label-size)', color: 'var(--text-secondary)', marginBottom: 4 }}>risk score</div>
            <div style={{ fontSize: 40, fontWeight: 600, color: 'var(--severity-critical-text)', fontFamily: 'var(--font-mono)' }}>78</div>
            <div style={{ marginTop: 'var(--space-2)' }}><SeverityBadge severity={OVERALL_SEVERITY} label={OVERALL_SEVERITY + " risk"} /></div>
          </Card>
          <Card style={{ flex: 1 }}>
            <div style={{ fontSize: 'var(--text-label-size)', color: 'var(--text-secondary)', marginBottom: 'var(--space-2)' }}>contributing factors</div>
            {FACTORS.map((f, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 'var(--space-2) 0', borderBottom: i < FACTORS.length - 1 ? '1px solid var(--border)' : 'none' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                  <SeverityBadge severity={f.sev} />
                  <span style={{ fontSize: 'var(--text-body-small-size)', color: 'var(--text-primary)' }}>{f.label}</span>
                </div>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-mono-small-size)', color: 'var(--text-secondary)' }}>{f.delta}</span>
              </div>
            ))}
          </Card>
        </div>
      </div>

      <div style={{ marginBottom: 'var(--space-12)' }}>
        <SectionTitle>activity</SectionTitle>
        <Card style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height: 90 }}>
          {SPARK.map((h, i) => (
            <div key={i} style={{ flex: 1, height: `${h}%`, background: 'var(--surface-raised)', borderTop: '2px solid var(--border-strong)' }} />
          ))}
        </Card>
        <div style={{ fontSize: 'var(--text-label-size)', color: 'var(--text-muted)', marginTop: 'var(--space-2)' }}>transaction volume over time</div>
      </div>

      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-4)' }}>
          <SectionTitle>transactions</SectionTitle>
          <LiveIndicator secondsAgo={30} />
        </div>
        <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-card)', overflow: 'hidden' }}>
          <div style={{ display: 'flex', background: 'var(--surface-raised)', fontSize: 'var(--text-label-size)', color: 'var(--text-secondary)', fontWeight: 500, padding: 'var(--table-cell-pad-v) var(--table-cell-pad-h)' }}>
            <div style={{ flex: 1 }}>date</div>
            <div style={{ flex: 1 }}>direction</div>
            <div style={{ flex: 3 }}>counterparty</div>
            <div style={{ flex: 1, textAlign: 'right' }}>confirmations</div>
            <div style={{ flex: 1, textAlign: 'right' }}>amount (btc)</div>
          </div>
          {TX.map((t, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', height: 'var(--table-row-height)', padding: '0 var(--table-cell-pad-h)', borderBottom: i < TX.length - 1 ? '1px solid var(--border)' : 'none' }}
              onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--surface-raised)')}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
            >
              <div style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: 'var(--text-mono-small-size)', color: 'var(--text-primary)' }}>{t.date}</div>
              <div style={{ flex: 1, fontSize: 'var(--text-body-small-size)', color: 'var(--text-secondary)' }}>{t.dir}</div>
              <div style={{ flex: 3 }}><AddressLabel address={t.addr} head={6} tail={4} /></div>
              <div style={{ flex: 1, textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: 'var(--text-mono-small-size)', color: t.conf === 0 ? 'var(--text-secondary)' : 'var(--text-primary)', display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 6 }}>
                <span style={{ width: 8, height: 8, borderRadius: 'var(--radius-full)', display: 'inline-block', flex: 'none', background: t.conf === 0 ? 'transparent' : 'var(--text-secondary)', border: t.conf === 0 ? '1.5px solid var(--text-secondary)' : 'none' }} />
                {t.conf === 0 ? 'unconfirmed' : t.conf}
              </div>
              <div style={{ flex: 1, textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: 'var(--text-mono-body-size)', fontVariantNumeric: 'tabular-nums', color: t.amt < 0.000001 ? 'var(--text-muted)' : 'var(--text-primary)' }}>{Number(t.amt).toFixed(8)}</div>            </div>
          ))}
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-2)', marginTop: 'var(--space-4)', fontSize: 'var(--text-body-small-size)', color: 'var(--text-secondary)' }}>
          <span style={{ cursor: 'pointer' }}>&larr; prev</span>
          <span style={{ border: '1px solid var(--border-strong)', borderRadius: 'var(--radius-control)', padding: '2px 10px', color: 'var(--text-primary)' }}>1</span>
          <span style={{ padding: '2px 10px', cursor: 'pointer' }}>2</span>
          <span style={{ padding: '2px 10px', cursor: 'pointer' }}>3</span>
          <span style={{ cursor: 'pointer' }}>next &rarr;</span>
        </div>
      </div>
    </div>
  );
}
window.AddressOverview = AddressOverview;
