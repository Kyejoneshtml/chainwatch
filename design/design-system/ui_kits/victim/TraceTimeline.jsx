const NS3 = window.ChainwatchDesignSystem_f0e832;
const { Button, ConfidenceIndicator } = NS3;

const EVENTS = [
  {
    kind: 'past',
    sentence: 'Your funds left your wallet',
    time: '14:32',
    relative: '4 hours ago',
    detail: '0.42 BTC in one transaction',
    addresses: ['bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh'],
  },
  {
    kind: 'past',
    sentence: 'Split across 3 addresses',
    time: '14:33',
    detail: '0.31 BTC, 0.08 BTC, 0.03 BTC',
    addresses: [
      '3FZbgi29cpjq2GjdwV8eyHuJJnkLtktZc5',
      'bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq',
      '3M219KR5vEneNb47ewrPfWyb5jQ2DjxRP6',
    ],
  },
  {
    kind: 'past',
    sentence: 'Largest amount moved again',
    time: '16:10',
    detail: '0.31 BTC to a single address',
    addresses: ['1BoatSLRHtKNngkdXEeobR76b53LETtpyT'],
    inference: { label: 'This address appears to belong to an exchange', percent: 78 },
  },
  {
    kind: 'unresolved',
    sentence: 'One smaller amount could not be followed',
    time: '16:14',
    detail: '0.03 BTC passed through a service that does not publish its records. We cannot say where it went next.',
    addresses: ['3M219KR5vEneNb47ewrPfWyb5jQ2DjxRP6'],
  },
  {
    kind: 'current',
    sentence: 'Nothing further in 2 hours',
    time: 'now',
    detail: 'The trail currently ends here. If these funds move again, this page updates and you will be told.',
  },
];

function Marker({ kind, isLast }) {
  const filled = kind === 'past' || kind === 'unresolved';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 'none', width: 12 }}>
      <span
        style={{
          width: 10,
          height: 10,
          borderRadius: 'var(--radius-full)',
          flex: 'none',
          marginTop: 6,
          background: filled ? 'var(--text-primary)' : 'transparent',
          border: filled ? 'none' : '1.5px solid var(--text-primary)',
          boxSizing: 'border-box',
        }}
      />
      {!isLast ? <span style={{ flex: 1, width: 1, background: 'var(--border-strong)', marginTop: 4 }} /> : null}
    </div>
  );
}

function Entry({ event, isLast }) {
  return (
    <li style={{ display: 'flex', gap: 'var(--space-4)', listStyle: 'none' }}>
      <Marker kind={event.kind} isLast={isLast} />
      <div style={{ paddingBottom: isLast ? 0 : 'var(--space-8)', flex: 1 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 'var(--space-4)' }}>
          <span style={{ fontSize: 'var(--text-h3-size)', lineHeight: 'var(--text-h3-lh)', fontWeight: 600, color: 'var(--text-primary)' }}>{event.sentence}</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-mono-small-size)', fontVariantNumeric: 'tabular-nums', color: 'var(--text-muted)', flex: 'none' }}>
            {event.time}{event.relative ? `, ${event.relative}` : ''}
          </span>
        </div>
        <p style={{ fontSize: 'var(--text-body-size)', lineHeight: 'var(--text-body-lh)', color: event.kind === 'unresolved' ? 'var(--text-secondary)' : 'var(--text-primary)', margin: 'var(--space-1) 0 0', textWrap: 'pretty' }}>
          {event.detail}
        </p>
        {event.inference ? (
          <div style={{ marginTop: 'var(--space-2)' }}>
            <ConfidenceIndicator label={event.inference.label} percent={event.inference.percent} />
          </div>
        ) : null}
        {event.addresses ? (
          <div style={{ marginTop: 'var(--space-3)', display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
            {event.addresses.map((a) => (
              <div key={a} style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-mono-small-size)', color: 'var(--text-secondary)', wordBreak: 'break-all' }}>{a}</div>
            ))}
          </div>
        ) : null}
      </div>
    </li>
  );
}

function TraceTimeline({ onReport }) {
  return (
    <VictimShell background="var(--surface-page)">
      <h1 style={{ fontSize: 'var(--text-h1-size)', lineHeight: 'var(--text-h1-lh)', fontWeight: 600, color: 'var(--text-primary)', margin: '0 0 var(--space-8)' }}>
        Where your funds went
      </h1>
      <ol style={{ margin: 0, padding: 0 }}>
        {EVENTS.map((e, i) => (
          <Entry key={i} event={e} isLast={i === EVENTS.length - 1} />
        ))}
      </ol>
      <div style={{ marginTop: 'var(--space-12)' }}>
        <Button variant="primary" onClick={onReport}>generate report</Button>
      </div>
    </VictimShell>
  );
}

window.TraceTimeline = TraceTimeline;
