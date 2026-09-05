const NS4 = window.ChainwatchDesignSystem_f0e832;
const { Statement, Button } = NS4;

const CONTENTS = [
  'A timeline of every movement, with dates and times',
  'The transaction identifiers, so each movement can be checked independently',
  'The path the funds took, hop by hop',
  'The addresses the funds reached, and what we know about them',
  'How certain we are about each inference, stated for every step',
];

function ActionScreen({ onGenerate }) {
  return (
    <VictimShell background="var(--surface-page)">
      <Statement style={{ marginBottom: 'var(--space-6)' }}>You can take this to the police.</Statement>

      <p style={{ fontSize: 'var(--text-body-size)', lineHeight: 'var(--text-body-lh)', color: 'var(--text-primary)', margin: '0 0 var(--space-4)', textWrap: 'pretty' }}>
        Fraud in the UK is reported to Action Fraud, the national reporting centre. Most people reporting stolen cryptocurrency have nothing concrete to give them.
      </p>
      <p style={{ fontSize: 'var(--text-body-size)', lineHeight: 'var(--text-body-lh)', color: 'var(--text-primary)', margin: '0 0 var(--space-12)', textWrap: 'pretty' }}>
        A report containing this trace gives them specific movements, times and destinations to act on. That is worth doing, and it is honest to say it does not mean your funds will be recovered — most stolen cryptocurrency is not. What a trace can do is make your report one that can be investigated rather than filed.
      </p>

      <Button variant="primary" onClick={onGenerate} style={{ height: 52, padding: '0 32px', fontSize: 'var(--text-h3-size)', borderRadius: 'var(--radius-card)' }}>
        generate report
      </Button>

      <div style={{ marginTop: 'var(--space-8)' }}>
        <div style={{ fontSize: 'var(--text-label-size)', color: 'var(--text-secondary)', marginBottom: 'var(--space-3)' }}>the report contains</div>
        <ul style={{ margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
          {CONTENTS.map((c) => (
            <li key={c} style={{ listStyle: 'none', display: 'flex', gap: 'var(--space-3)', fontSize: 'var(--text-body-small-size)', lineHeight: 1.5, color: 'var(--text-primary)' }}>
              <span style={{ width: 6, height: 6, borderRadius: 'var(--radius-full)', background: 'var(--text-muted)', flex: 'none', marginTop: 7 }} />
              <span style={{ textWrap: 'pretty' }}>{c}</span>
            </li>
          ))}
        </ul>
      </div>
    </VictimShell>
  );
}

window.ActionScreen = ActionScreen;
