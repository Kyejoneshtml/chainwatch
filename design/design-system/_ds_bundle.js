/* @ds-bundle: {"format":4,"namespace":"ChainwatchDesignSystem_f0e832","components":[{"name":"ConfirmationBadge","sourcePath":"components/badges/ConfirmationBadge.jsx"},{"name":"SeverityBadge","sourcePath":"components/badges/SeverityBadge.jsx"},{"name":"Button","sourcePath":"components/core/Button.jsx"},{"name":"Card","sourcePath":"components/core/Card.jsx"},{"name":"Statement","sourcePath":"components/core/Statement.jsx"},{"name":"AddressDiff","sourcePath":"components/data/AddressDiff.jsx"},{"name":"AddressLabel","sourcePath":"components/data/AddressLabel.jsx"},{"name":"DataTable","sourcePath":"components/data/DataTable.jsx"},{"name":"MonetaryAmount","sourcePath":"components/data/MonetaryAmount.jsx"},{"name":"ConfidenceIndicator","sourcePath":"components/feedback/ConfidenceIndicator.jsx"},{"name":"EmptyState","sourcePath":"components/feedback/EmptyState.jsx"},{"name":"InvalidatedState","sourcePath":"components/feedback/InvalidatedState.jsx"},{"name":"LiveIndicator","sourcePath":"components/feedback/LiveIndicator.jsx"},{"name":"SkeletonBlock","sourcePath":"components/feedback/SkeletonBlock.jsx"},{"name":"WarningBlock","sourcePath":"components/feedback/WarningBlock.jsx"},{"name":"Input","sourcePath":"components/forms/Input.jsx"},{"name":"Select","sourcePath":"components/forms/Select.jsx"}],"sourceHashes":{"components/badges/ConfirmationBadge.jsx":"3745957ef8e0","components/badges/SeverityBadge.jsx":"b49beb2b26fd","components/core/Button.jsx":"886f89dd0c64","components/core/Card.jsx":"a7a8d321659f","components/core/Statement.jsx":"47cb52086ded","components/data/AddressDiff.jsx":"1a6727ba30cf","components/data/AddressLabel.jsx":"f69819386374","components/data/DataTable.jsx":"e63c59acf4aa","components/data/MonetaryAmount.jsx":"a2474a628750","components/data/tableUnitContext.js":"00b5c309e0fd","components/feedback/ConfidenceIndicator.jsx":"4e04dac76ecb","components/feedback/EmptyState.jsx":"bae2075679ec","components/feedback/InvalidatedState.jsx":"9f803b66437d","components/feedback/LiveIndicator.jsx":"32cbd9ad846c","components/feedback/SkeletonBlock.jsx":"a791d71ab05f","components/feedback/WarningBlock.jsx":"9a4a95800d46","components/forms/Input.jsx":"1fe50b07af8d","components/forms/Select.jsx":"c3434028cac3","doc-page.js":"371bab66f42d","ui_kits/app/AddressOverview.jsx":"0fc5b2afac37","ui_kits/app/AlertsFeed.jsx":"4b516eaad837","ui_kits/app/CaseDetail.jsx":"28b55e04e137","ui_kits/victim/ActionScreen.jsx":"c4a6c97e0fe5","ui_kits/victim/MovementScreen.jsx":"efc0e92fffd2","ui_kits/victim/TraceTimeline.jsx":"16127e3e4b0b","ui_kits/victim/WaitingScreen.jsx":"4379afcd0df1"},"inlinedExternals":[],"unexposedExports":[{"name":"tableUnitContext","sourcePath":"components/data/tableUnitContext.js"}]} */

(() => {

const __ds_ns = (window.ChainwatchDesignSystem_f0e832 = window.ChainwatchDesignSystem_f0e832 || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/badges/ConfirmationBadge.jsx
try { (() => {
function ConfirmationBadge({
  confirmations = 0
}) {
  if (confirmations === 0) {
    return /*#__PURE__*/React.createElement("span", {
      style: {
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        fontFamily: 'var(--font-sans)',
        fontSize: 'var(--text-label-size)',
        color: 'var(--text-secondary)'
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        width: 8,
        height: 8,
        borderRadius: 'var(--radius-full)',
        border: '1.5px solid var(--text-secondary)',
        display: 'inline-block'
      }
    }), "unconfirmed");
  }
  return /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 6,
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--text-mono-small-size)',
      color: 'var(--text-primary)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 8,
      height: 8,
      borderRadius: 'var(--radius-full)',
      background: 'var(--text-secondary)',
      display: 'inline-block'
    }
  }), confirmations, " confirmations");
}
Object.assign(__ds_scope, { ConfirmationBadge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/badges/ConfirmationBadge.jsx", error: String((e && e.message) || e) }); }

// components/badges/SeverityBadge.jsx
try { (() => {
const SEVERITY = {
  critical: {
    text: 'var(--severity-critical-text)',
    tint: 'var(--severity-critical-tint)',
    shape: 'filled'
  },
  high: {
    text: 'var(--severity-high-text)',
    tint: 'var(--severity-high-tint)',
    shape: 'filled'
  },
  medium: {
    text: 'var(--severity-medium-text)',
    tint: 'var(--severity-medium-tint)',
    shape: 'open'
  },
  low: {
    text: 'var(--severity-low-text)',
    tint: 'var(--severity-low-tint)',
    shape: 'open-hairline'
  }
};
function Indicator({
  shape,
  color
}) {
  const base = {
    width: 8,
    height: 8,
    borderRadius: 'var(--radius-full)',
    display: 'inline-block',
    flex: 'none'
  };
  if (shape === 'filled') return /*#__PURE__*/React.createElement("span", {
    style: {
      ...base,
      background: color
    }
  });
  if (shape === 'open') return /*#__PURE__*/React.createElement("span", {
    style: {
      ...base,
      border: `1.5px solid ${color}`
    }
  });
  return /*#__PURE__*/React.createElement("span", {
    style: {
      ...base,
      border: `1px solid var(--border-strong)`
    }
  });
}
function SeverityBadge({
  severity = 'medium',
  label
}) {
  const s = SEVERITY[severity];
  return /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 6,
      background: s.tint,
      color: s.text,
      fontFamily: 'var(--font-sans)',
      fontSize: 'var(--text-label-size)',
      fontWeight: 500,
      borderRadius: 'var(--radius-badge)',
      padding: '4px 8px',
      border: severity === 'low' ? '1px solid var(--border)' : 'none'
    }
  }, /*#__PURE__*/React.createElement(Indicator, {
    shape: s.shape,
    color: s.text
  }), label || severity);
}
Object.assign(__ds_scope, { SeverityBadge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/badges/SeverityBadge.jsx", error: String((e && e.message) || e) }); }

// components/core/Button.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function Button({
  variant = 'primary',
  size = 'default',
  disabled = false,
  children,
  onClick,
  style,
  ...rest
}) {
  const base = {
    fontFamily: 'var(--font-sans)',
    fontSize: 'var(--text-body-size)',
    fontWeight: 500,
    height: 36,
    padding: '0 16px',
    borderRadius: 'var(--radius-control)',
    border: '1px solid transparent',
    cursor: disabled ? 'not-allowed' : 'pointer',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    transition: 'background-color .12s ease, border-color .12s ease, opacity .12s ease'
  };
  const variants = {
    primary: {
      background: 'var(--text-primary)',
      color: '#FFFFFF',
      borderColor: 'var(--text-primary)'
    },
    secondary: {
      background: '#FFFFFF',
      color: 'var(--text-primary)',
      borderColor: 'var(--border)'
    },
    destructive: {
      background: '#FFFFFF',
      color: 'var(--severity-critical-text)',
      borderColor: 'var(--severity-critical-text)'
    }
  };
  const disabledStyle = {
    background: 'var(--surface-sunken)',
    color: 'var(--text-muted)',
    borderColor: 'transparent'
  };
  return /*#__PURE__*/React.createElement("button", _extends({
    style: {
      ...base,
      ...(disabled ? disabledStyle : variants[variant]),
      ...style
    },
    disabled: disabled,
    onClick: onClick,
    onMouseEnter: e => {
      if (disabled) return;
      if (variant === 'primary') e.currentTarget.style.opacity = '0.85';
      if (variant === 'secondary') e.currentTarget.style.borderColor = 'var(--border-strong)';
      if (variant === 'destructive') e.currentTarget.style.background = 'var(--severity-critical-tint)';
    },
    onMouseLeave: e => {
      if (disabled) return;
      e.currentTarget.style.opacity = '1';
      if (variant === 'secondary') e.currentTarget.style.borderColor = 'var(--border)';
      if (variant === 'destructive') e.currentTarget.style.background = '#FFFFFF';
    },
    onFocus: e => {
      e.currentTarget.style.outline = '2px solid var(--text-primary)';
      e.currentTarget.style.outlineOffset = '2px';
    },
    onBlur: e => {
      e.currentTarget.style.outline = 'none';
    }
  }, rest), children);
}
Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Button.jsx", error: String((e && e.message) || e) }); }

// components/core/Card.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function Card({
  children,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      background: 'var(--surface-page)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-card)',
      padding: 'var(--space-6)',
      ...style
    }
  }, rest), children);
}
Object.assign(__ds_scope, { Card });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Card.jsx", error: String((e && e.message) || e) }); }

// components/core/Statement.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function Statement({
  children,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("p", _extends({
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 'var(--text-statement-size)',
      lineHeight: 'var(--text-statement-lh)',
      fontWeight: 'var(--text-statement-weight)',
      color: 'var(--text-primary)',
      margin: '0 0 var(--space-12)',
      maxWidth: '32ch',
      textWrap: 'pretty',
      ...style
    }
  }, rest), children);
}
Object.assign(__ds_scope, { Statement });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Statement.jsx", error: String((e && e.message) || e) }); }

// components/data/AddressDiff.jsx
try { (() => {
/** Longest shared prefix / suffix length between two strings. */
function sharedAffixes(a, b) {
  let lead = 0;
  while (lead < a.length && lead < b.length && a[lead] === b[lead]) lead++;
  let tail = 0;
  while (tail < a.length - lead && tail < b.length - lead && a[a.length - 1 - tail] === b[b.length - 1 - tail]) tail++;
  return {
    lead,
    tail
  };
}
function AddressDiff({
  address,
  against,
  style
}) {
  const {
    lead,
    tail
  } = sharedAffixes(address, against || '');
  const poisoningRisk = against && lead >= 4 && tail >= 4;
  const mid = poisoningRisk ? address.slice(lead, address.length - tail) : '';
  const base = {
    fontFamily: 'var(--font-mono)',
    fontSize: 'var(--text-mono-body-size)',
    color: 'var(--text-primary)',
    wordBreak: 'break-all',
    ...style
  };
  if (!poisoningRisk) return /*#__PURE__*/React.createElement("span", {
    style: base
  }, address);
  return /*#__PURE__*/React.createElement("span", {
    style: base
  }, address.slice(0, lead), /*#__PURE__*/React.createElement("span", {
    style: {
      fontWeight: 600,
      borderBottom: '1px solid var(--text-primary)'
    }
  }, mid), tail ? address.slice(address.length - tail) : '');
}
Object.assign(__ds_scope, { AddressDiff });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/AddressDiff.jsx", error: String((e && e.message) || e) }); }

// components/data/AddressLabel.jsx
try { (() => {
const {
  useState
} = React;
function truncateMiddle(str, head = 8, tail = 6) {
  if (!str || str.length <= head + tail + 1) return str;
  return `${str.slice(0, head)}…${str.slice(-tail)}`;
}
function AddressLabel({
  address,
  head = 8,
  tail = 6
}) {
  const [copied, setCopied] = useState(false);
  return /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 6,
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--text-mono-body-size)',
      color: 'var(--text-primary)'
    }
  }, truncateMiddle(address, head, tail), /*#__PURE__*/React.createElement("button", {
    "aria-label": "copy address",
    onClick: () => {
      navigator.clipboard && navigator.clipboard.writeText(address);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    },
    style: {
      border: 'none',
      background: 'none',
      padding: 2,
      cursor: 'pointer',
      color: copied ? 'var(--text-primary)' : 'var(--text-muted)',
      display: 'inline-flex',
      lineHeight: 0
    }
  }, /*#__PURE__*/React.createElement("svg", {
    width: "13",
    height: "13",
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "2",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }, /*#__PURE__*/React.createElement("rect", {
    x: "9",
    y: "9",
    width: "13",
    height: "13",
    rx: "2"
  }), /*#__PURE__*/React.createElement("path", {
    d: "M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"
  }))));
}
Object.assign(__ds_scope, { AddressLabel });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/AddressLabel.jsx", error: String((e && e.message) || e) }); }

// components/data/tableUnitContext.js
try { (() => {
// Shared context: DataTable sets this so MonetaryAmount drops its unit suffix inside a table,
// where the column header already carries the unit. Deliberately camelCase so it stays off the
// public component namespace.
const tableUnitContext = React.createContext(false);
Object.assign(__ds_scope, { tableUnitContext });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/tableUnitContext.js", error: String((e && e.message) || e) }); }

// components/data/DataTable.jsx
try { (() => {
function DataTable({
  columns,
  rows,
  renderCell
}) {
  return /*#__PURE__*/React.createElement(__ds_scope.tableUnitContext.Provider, {
    value: true
  }, /*#__PURE__*/React.createElement("table", {
    style: {
      width: '100%',
      borderCollapse: 'collapse',
      fontFamily: 'var(--font-sans)'
    }
  }, /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", {
    style: {
      background: 'var(--surface-raised)'
    }
  }, columns.map(c => /*#__PURE__*/React.createElement("th", {
    key: c.key,
    style: {
      textAlign: c.align || 'left',
      fontSize: 'var(--text-label-size)',
      fontWeight: 500,
      color: 'var(--text-secondary)',
      padding: 'var(--table-cell-pad-v) var(--table-cell-pad-h)',
      borderBottom: '1px solid var(--border)'
    }
  }, c.label)))), /*#__PURE__*/React.createElement("tbody", null, rows.map((row, i) => /*#__PURE__*/React.createElement("tr", {
    key: i,
    style: {
      height: 'var(--table-row-height)'
    },
    onMouseEnter: e => e.currentTarget.style.background = 'var(--surface-raised)',
    onMouseLeave: e => e.currentTarget.style.background = 'transparent'
  }, columns.map(c => /*#__PURE__*/React.createElement("td", {
    key: c.key,
    style: {
      textAlign: c.align || 'left',
      fontSize: 'var(--text-body-small-size)',
      color: 'var(--text-primary)',
      padding: 'var(--table-cell-pad-v) var(--table-cell-pad-h)',
      borderBottom: '1px solid var(--border)'
    }
  }, renderCell ? renderCell(row, c) : row[c.key])))))));
}
Object.assign(__ds_scope, { DataTable });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/DataTable.jsx", error: String((e && e.message) || e) }); }

// components/data/MonetaryAmount.jsx
try { (() => {
function thinSpaceThousands(n) {
  return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, '\u2009');
}
function MonetaryAmount({
  value,
  unit = 'btc',
  muted = false,
  showUnit
}) {
  const inTable = React.useContext(__ds_scope.tableUnitContext);
  const withUnit = showUnit !== undefined ? showUnit : !inTable;
  const isZeroOrDust = unit === 'btc' ? Number(value) < 0.00000100 : Number(value) < 1000;
  const color = muted || isZeroOrDust ? 'var(--text-muted)' : 'var(--text-primary)';
  const display = unit === 'btc' ? Number(value).toFixed(8) : thinSpaceThousands(Math.round(Number(value)));
  return /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--text-mono-body-size)',
      fontVariantNumeric: 'tabular-nums',
      color,
      display: 'inline-block',
      textAlign: 'right'
    }
  }, display, withUnit ? unit === 'btc' ? ' BTC' : ' sats' : '');
}
Object.assign(__ds_scope, { MonetaryAmount });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/MonetaryAmount.jsx", error: String((e && e.message) || e) }); }

// components/feedback/ConfidenceIndicator.jsx
try { (() => {
function ConfidenceIndicator({
  label,
  percent
}) {
  return /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 'var(--text-body-small-size)',
      color: 'var(--text-secondary)'
    }
  }, label, typeof percent === 'number' ? ` (${Math.round(percent)}%)` : '');
}
Object.assign(__ds_scope, { ConfidenceIndicator });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/ConfidenceIndicator.jsx", error: String((e && e.message) || e) }); }

// components/feedback/EmptyState.jsx
try { (() => {
function EmptyState({
  message
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      padding: 'var(--space-8) 0',
      textAlign: 'center'
    }
  }, /*#__PURE__*/React.createElement("p", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 'var(--text-body-size)',
      color: 'var(--text-secondary)',
      margin: 0
    }
  }, message));
}
Object.assign(__ds_scope, { EmptyState });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/EmptyState.jsx", error: String((e && e.message) || e) }); }

// components/feedback/InvalidatedState.jsx
try { (() => {
function InvalidatedState({
  children,
  explanation = 'This block was replaced by the network. This movement did not occur.'
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      textDecoration: 'line-through',
      color: 'var(--text-muted)'
    }
  }, children), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--text-body-small-size)',
      color: 'var(--text-muted)',
      marginTop: 'var(--space-1)'
    }
  }, explanation));
}
Object.assign(__ds_scope, { InvalidatedState });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/InvalidatedState.jsx", error: String((e && e.message) || e) }); }

// components/feedback/LiveIndicator.jsx
try { (() => {
function LiveIndicator({
  secondsAgo = 0
}) {
  const text = secondsAgo < 1 ? 'updated just now' : secondsAgo < 60 ? `updated ${Math.round(secondsAgo)}s ago` : `updated ${Math.round(secondsAgo / 60)}m ago`;
  return /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 6,
      fontFamily: 'var(--font-sans)',
      fontSize: 'var(--text-label-size)',
      color: 'var(--text-muted)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 6,
      height: 6,
      borderRadius: 'var(--radius-full)',
      background: 'var(--text-primary)',
      display: 'inline-block'
    }
  }), text);
}
Object.assign(__ds_scope, { LiveIndicator });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/LiveIndicator.jsx", error: String((e && e.message) || e) }); }

// components/feedback/SkeletonBlock.jsx
try { (() => {
function SkeletonBlock({
  width = '100%',
  height = 16
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      width,
      height,
      background: 'var(--surface-raised)',
      borderRadius: 4,
      animation: 'cw-skeleton-pulse 1.8s ease-in-out infinite'
    }
  });
}
Object.assign(__ds_scope, { SkeletonBlock });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/SkeletonBlock.jsx", error: String((e && e.message) || e) }); }

// components/feedback/WarningBlock.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function WarningBlock({
  children,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      background: 'var(--surface-raised)',
      border: '1px solid var(--border-strong)',
      borderRadius: 'var(--radius-card)',
      padding: 'var(--space-4)',
      fontFamily: 'var(--font-sans)',
      fontSize: 'var(--text-body-small-size)',
      lineHeight: 1.5,
      color: 'var(--text-primary)',
      ...style
    }
  }, rest), children);
}
Object.assign(__ds_scope, { WarningBlock });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/WarningBlock.jsx", error: String((e && e.message) || e) }); }

// components/forms/Input.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function Input({
  placeholder,
  value,
  onChange,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("input", _extends({
    placeholder: placeholder,
    value: value,
    onChange: onChange,
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 'var(--text-body-size)',
      color: 'var(--text-primary)',
      height: 36,
      padding: '0 12px',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-control)',
      outline: 'none',
      ...style
    },
    onFocus: e => {
      e.currentTarget.style.borderColor = 'var(--border-strong)';
      e.currentTarget.style.outline = '2px solid var(--text-primary)';
      e.currentTarget.style.outlineOffset = '2px';
    },
    onBlur: e => {
      e.currentTarget.style.borderColor = 'var(--border)';
      e.currentTarget.style.outline = 'none';
    }
  }, rest));
}
Object.assign(__ds_scope, { Input });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Input.jsx", error: String((e && e.message) || e) }); }

// components/forms/Select.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function Select({
  options = [],
  value,
  onChange,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("select", _extends({
    value: value,
    onChange: onChange,
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 'var(--text-body-size)',
      color: 'var(--text-primary)',
      height: 36,
      padding: '0 12px',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-control)',
      outline: 'none',
      background: '#FFFFFF',
      ...style
    },
    onFocus: e => {
      e.currentTarget.style.outline = '2px solid var(--text-primary)';
      e.currentTarget.style.outlineOffset = '2px';
    },
    onBlur: e => {
      e.currentTarget.style.outline = 'none';
    }
  }, rest), options.map(o => /*#__PURE__*/React.createElement("option", {
    key: o.value,
    value: o.value
  }, o.label)));
}
Object.assign(__ds_scope, { Select });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Select.jsx", error: String((e && e.message) || e) }); }

// doc-page.js
try { (() => {
// @ds-adherence-ignore -- omelette starter scaffold (raw elements/hex/px by design)
// Copied omelette starter. Re-running copy_starter_component with this kind overwrites this file with the latest version (page content is unaffected).
/* BEGIN USAGE */
/**
 * <doc-page> — paged-document shell for printable HTML.
 *
 * FIRST, decide how the document paginates — up front, before building:
 *
 * - FLOWING document (the default): write the whole document as one
 *   normal HTML flow inside <doc-page>; the browser's print engine
 *   splits it onto pages at export. Use for long-form documents with a
 *   single text flow: reports, memos, letters, essays.
 * - EXPLICIT pagination: a fixed set of pre-paginated pages, one
 *   <section class="page"> child per page. Use when the user asks for a
 *   specific page count, or the design implies one: a one-page resume, a
 *   two-sided flier, a poster, a certificate, a brochure — any richly
 *   laid-out document without a single text flow.
 * - If in doubt, ask the user as part of the build.
 *
 * PAGE SIZING — paper differs by country (letter vs A4), so the printed
 * sheet is not one fixed truth:
 * - FLOWING documents pin NO paper size: the print engine paginates
 *   onto the user's real paper, and the content reflows to it.
 * - EXPLICITLY PAGINATED documents print each page at a FIXED page box
 *   with overflow hidden — letter by default, size="a4" for a clearly
 *   metric user, the user's chosen paper when they export. Design each
 *   page to FILL that box, fitting letter and A4 alike without overlap.
 * - width/height pin an explicit fixed size, ONLY when the user gives
 *   one.
 * Never write your own @page rule or hard-code paper dimensions in the
 * content.
 *
 * Sizing modes (attributes):
 *   (none)                      — portrait: flowing docs use the user's
 *           paper; explicitly paginated pages use the named size box
 *           (letter unless size="a4")
 *   orientation="landscape"     — the same, landscape
 *   width / height              — explicit fixed size, ONLY when the user
 *           gives one (e.g. width="22in" height="30in" for a 22×30
 *           poster): the page IS the design's size, printed at true
 *           dimensions (or scaled onto the user's paper at print time).
 *           Any absolute CSS length: px/in/mm/cm/pt/pc.
 * The component announces the chosen mode to the host app at runtime (a
 * meta tag it injects), so the print path can inject the user's true
 * paper size.
 *
 * On screen the document renders on a desk background: a flowing
 * document as one tall scrolling sheet (Google Docs' pageless view);
 * explicitly paginated documents as one card per page.
 *
 * EXPLICIT pagination usage:
 *   <style>doc-page:not(:defined){visibility:hidden}</style>
 *   <doc-page>
 *     <section class="page" id="p1">…one page's design…</section>
 *     <section class="page" id="p2">…</section>
 *   </doc-page>
 *   <script src="doc-page.js"></script>
 * How the page box works, concretely: each .page prints as ONE full-bleed
 * sheet at a FIXED physical size — letter by default (set size="a4" for
 * a clearly metric user), the user's chosen paper when they export —
 * with overflow hidden. Nothing scrolls and nothing reflows onto a next
 * sheet: content that misses the box is CLIPPED. Design each page to
 * FILL that page box, and to fit it — letter and A4 alike — without
 * overlap. Each page is a size container; don't size anything in
 * viewport units (they track the window, not the page), and never set
 * width or height on the .page section itself (the component sizes the
 * page box; an authored height like 100% is meaningless at print and is
 * overridden). The component owns the page box, the screen card chrome,
 * and the page breaks (never add your own break-before/after). Don't mix
 * .page sections with flowing content or header/footer slots in the same
 * document.
 *
 * FLOWING usage:
 *   <style>doc-page:not(:defined){visibility:hidden}</style>
 *   <doc-page margin="0.75in">
 *     <h1>Title</h1>
 *     <p>…body…</p>
 *   </doc-page>
 *   <script src="doc-page.js"></script>
 * There is no manual page-splitting — the browser's print engine
 * paginates at export. Standard break-hygiene rules (`break-inside:
 * avoid` on figures, code blocks, images and table rows; `orphans/
 * widows: 3`) are applied so paragraphs and groups split cleanly. On
 * screen and at print, headings default to `text-wrap: balance` and
 * body text to `text-wrap: pretty`; the defaults have zero specificity,
 * so any text-wrap you declare wins.
 *
 * Other attributes:
 *   size    — letter | a4 | legal (default letter). Flowing documents:
 *           preview proportion only — it does NOT pin their printed
 *           paper (the print dialog's paper governs); leave it alone
 *           there. Explicitly paginated documents: it sets the page box
 *           the cards and the pinned @page share (the export dialog's
 *           choice overrides both at print) — set size="a4" for a
 *           clearly metric user. Scaled-fit: names the sheet the fit is
 *           computed against, same a4-for-metric-users advice.
 *   content-width / content-height — the design's own fixed dimensions
 *           (CSS lengths), for scaling a fixed-size design ONTO the
 *           named sheet: content lays out at exactly this size, and the
 *           component scales it to fit that sheet's printable area
 *           (centered horizontally, top-aligned; the export dialog
 *           re-fits to the user's actual paper choice where available).
 *           Both must be set; they do not change the page box. For pages
 *           WITHOUT running header/footer slots.
 *   margin  — printable inset on every page of a FLOWING document
 *           (default 0.75in); margin="0" makes pages full-bleed.
 *           Explicitly paginated pages are always full-bleed.
 *
 * Running header/footer (flowing documents only): give an element
 * `slot="header"` or `slot="footer"` and it repeats on every printed
 * page via `position: fixed`. To keep body text from sliding under it,
 * the component prints inside a single-cell table whose <thead>/<tfoot>
 * are spacers sized to the header/footer height — browsers repeat
 * thead/tfoot on every page, so each sheet's content starts below the
 * header and ends above the footer. On screen the header/footer render
 * once at the top/bottom of the sheet.
 *
 * At print the component injects `@page { margin: 0 }` (which leaves
 * Chrome no margin box to draw its date/URL/page-count header in) and
 * moves the visual margin onto the sheet's own padding. It also marks
 * the document as owning its print CSS (a
 * `meta[name="omelette-owns-print"]` it injects at runtime), so the
 * PDF export never injects page-geometry CSS of its own on top.
 *
 * Print best practices for the content you author:
 * - Multi-column text: use CSS columns (`column-count` +
 *   `column-gap`), never side-by-side flex/grid columns — only real
 *   CSS columns flow and break across pages. `column-span: all` lets
 *   a heading span the columns; `hyphens: auto` (needs `lang` on
 *   the html element) keeps narrow columns readable.
 * - Page breaks in flowing documents: `break-before: page` on an
 *   element that must start a new page (a chapter, an appendix). Add
 *   your own kept-together blocks (callouts, stat tiles, cards) to a
 *   `break-inside: avoid` rule, and keep each one shorter than a page.
 * - Extend `orphans: 3; widows: 3` to any custom text blocks you add
 *   (p and li are covered by default).
 * - Give long tables a <thead> — browsers repeat it on every printed
 *   page.
 * - No `position: fixed`/`sticky` and no viewport units in content:
 *   fixed elements stamp every printed page (running headers/footers go
 *   in the component's slots) and `100vh` mis-sizes at print.
 *
 * Author content as static HTML so the user can click-to-edit any text
 * directly. Do not set width/padding/background on the document body —
 * the component owns the sheet box.
 */
/* END USAGE */

(() => {
  const PAPER = {
    letter: ['8.5in', '11in'],
    a4: ['210mm', '297mm'],
    legal: ['8.5in', '14in']
  };
  const CSS_LENGTH = /^\d+(\.\d+)?(px|in|mm|cm|pt|pc)$/;
  // Unitless "0" is a valid CSS length and the natural way to write
  // margin="0"; normalise it to 0px so max()/calc() (which reject a bare
  // number) keep working.
  const safeLen = (v, fb) => {
    v = (v || '').trim();
    return v === '0' ? '0px' : CSS_LENGTH.test(v) ? v : fb;
  };
  // WebKit (Safari and every iOS browser shell) never repeats a table's
  // thead/tfoot on printed pages (WebKit bug 17205), so the spacer-borne
  // vertical margins of a FLOWING document reach only the first page
  // there. Engine check, not browser check: vendor is 'Apple Computer,
  // Inc.' exactly for WebKit and 'Google Inc.' for Blink.
  const WK_PRINT = /apple/i.test(navigator.vendor || '');
  // CSS length → px number (CSS absolute units are exact: 1in = 96px).
  // Returns NaN for anything safeLen would reject — callers gate on it.
  const PX_PER = {
    px: 1,
    in: 96,
    mm: 96 / 25.4,
    cm: 96 / 2.54,
    pt: 96 / 72,
    pc: 16
  };
  const toPx = v => {
    const m = /^(\d+(?:\.\d+)?)(px|in|mm|cm|pt|pc)$/.exec((v || '').trim());
    return m ? parseFloat(m[1]) * PX_PER[m[2]] : NaN;
  };
  const stylesheet = `
    :host {
      position: relative;
      display: block;
      /* When the viewport is narrower than the page, grow to wrap the
       * sheet (plus this padding) instead of staying viewport-width, so
       * the desk background and right margin reach the sheet's far edge
       * in the horizontal scroll. */
      min-width: max-content;
      min-height: 100vh;
      background: #f5f5f4;
      padding: 48px 24px;
      box-sizing: border-box;
      font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
      --doc-page-w: 8.5in;
      --doc-page-h: 11in;
      --doc-page-margin: 0.75in;
      --doc-hdr-h: 0px;
      --doc-ftr-h: 0px;
      --doc-hdr-pad: 0px;
      --doc-ftr-pad: 0px;
    }
    .sheet {
      width: var(--doc-page-w);
      margin: 0 auto;
      background: #fff;
      box-shadow: 0 2px 10px rgba(20, 20, 19, 0.12);
      border-radius: 7px;
      box-sizing: border-box;
      padding: var(--doc-page-margin);
    }
    .frame { width: 100%; border-collapse: collapse; }
    /* Scaled-fit mode (content-width/content-height): the inner .fit box
     * lays the content out at its authored fixed size and scales it onto
     * the printable area; .fit-box reserves the scaled footprint in flow
     * (transforms don't affect layout) and centers it. Without the mode,
     * both divs are unstyled block pass-throughs. */
    /* Explicit pagination: direct .page children are the pages. The sheet
     * becomes a transparent stack and each page carries the card look on
     * screen; at print each page is exactly one full-bleed sheet. The
     * ::slotted defaults are deliberately weak (document CSS wins), so
     * authored page styling can override any of this. */
    .sheet.paginated {
      background: transparent;
      box-shadow: none;
      border-radius: 0;
      padding: 0;
    }
    .paginated ::slotted(.page) {
      position: relative;
      display: block;
      width: 100%;
      aspect-ratio: var(--doc-page-ar);
      container-type: size;
      overflow: hidden;
      box-sizing: border-box;
      background: #fff;
      border-radius: 7px;
      box-shadow: 0 2px 10px rgba(0, 0, 0, 0.25);
      print-color-adjust: exact;
      -webkit-print-color-adjust: exact;
      break-inside: avoid;
    }
    .paginated ::slotted(.page:not(:first-child)) { margin-top: 1rem; }
    @media print {
      .sheet.paginated { padding: 0; }
      /* The flowing-document vertical inset lives on the repeating
       * thead/tfoot spacers, not the sheet padding — they must go too,
       * or each full-sheet .page is pushed ~margin down and spills onto
       * a second sheet. Paginated pages are full-bleed by definition
       * (content owns its insets). */
      .sheet.paginated .hdr-space,
      .sheet.paginated .ftr-space { height: 0; }
      .paginated ::slotted(.page) {
        border-radius: 0 !important;
        box-shadow: none !important;
        margin: 0 !important;
        /* Physical page-box sizing, no viewport units: Safari resolves
         * 100vh against the window, not the page box, so a vh-sized card
         * paginates wrong there. --doc-page-w/h are the named size by
         * default and are overridden to the user's chosen paper by the
         * export path, so every card is exactly one sheet either way.
         * Width + height (same source values as @page size) rather than
         * width + aspect-ratio: the ratio is a 6-decimal rounding of the
         * same division, and a few millionths of overflow would spill a
         * blank sheet after every page. The screen-only aspect-ratio
         * (preview proportions) must not leak into print. cqh typography
         * tracks the same box.
         *
         * Every declaration is !important: per CSS Scoping, unimportant
         * shadow ::slotted rules LOSE to the document context, so a page
         * section's authored inline style would silently beat this print
         * geometry. A model-authored height:100% did exactly that — the
         * percentage resolves as auto in the all-auto print ancestry, the
         * base rule's size containment turns auto into ZERO, and
         * overflow:hidden then paints nothing: a blank PDF with perfect
         * page boxes. At print the component's geometry is the design's
         * whole contract, so it must win over any authored sizing. */
        aspect-ratio: auto !important;
        width: var(--doc-page-w) !important;
        height: var(--doc-page-h) !important;
        overflow: hidden !important;
      }
      .paginated ::slotted(.page:not(:first-child)) {
        break-before: page !important;
        margin-top: 0 !important;
      }
    }
    .fit-mode .fit-box {
      width: calc(var(--doc-fit-w) * var(--doc-fit-scale));
      height: calc(var(--doc-fit-h) * var(--doc-fit-scale));
      margin: 0 auto;
      break-inside: avoid;
    }
    .fit-mode .fit {
      width: var(--doc-fit-w);
      height: var(--doc-fit-h);
      transform: scale(var(--doc-fit-scale));
      transform-origin: top left;
    }
    .frame td, .frame th { padding: 0; text-align: left; font-weight: inherit; }
    .hdr-space { height: var(--doc-hdr-h); }
    .ftr-space { height: var(--doc-ftr-h); }
    ::slotted([slot="header"]),
    ::slotted([slot="footer"]) { display: block; box-sizing: border-box; }
    @media print {
      :host { background: none; padding: 0; min-width: 0; min-height: 0; }
      .sheet {
        width: auto; margin: 0; box-shadow: none; border-radius: 0;
        padding: 0 var(--doc-page-margin);
      }
      /* The thead/tfoot spacers repeat on every page, so they carry the
       * vertical page margin (which the sheet's own padding cannot, since
       * that padding is consumed once on the first/last page). The running
       * header/footer are fixed inside that band. */
      /* The 0.35in is breathing room between a running header/footer and
       * the body; without one the spacer is exactly the page margin, so a
       * margin="0" full-bleed document gets truly full-bleed pages. */
      .hdr-space { height: max(var(--doc-page-margin), calc(var(--doc-hdr-h) + var(--doc-hdr-pad))); }
      .ftr-space { height: max(var(--doc-page-margin), calc(var(--doc-ftr-h) + var(--doc-ftr-pad))); }
      /* WebKit flowing documents: @page carries the vertical margin (see
       * _syncPrintPageRule), so the spacers keep only whatever a running
       * header/footer needs BEYOND it — page 1 would otherwise double its
       * top inset. Paginated sheets already zero their spacers above. */
      .sheet.wk-print:not(.paginated) .hdr-space { height: max(0px, calc(max(var(--doc-page-margin), calc(var(--doc-hdr-h) + var(--doc-hdr-pad))) - var(--doc-page-margin))); }
      .sheet.wk-print:not(.paginated) .ftr-space { height: max(0px, calc(max(var(--doc-page-margin), calc(var(--doc-ftr-h) + var(--doc-ftr-pad))) - var(--doc-page-margin))); }
      ::slotted([slot="header"]) {
        position: fixed; top: 0; left: 0; right: 0; margin: 0;
        padding: calc(var(--doc-page-margin) * 0.45) var(--doc-page-margin) 0;
      }
      ::slotted([slot="footer"]) {
        position: fixed; bottom: 0; left: 0; right: 0; margin: 0;
        padding: 0 var(--doc-page-margin) calc(var(--doc-page-margin) * 0.45);
      }
    }
  `;
  class DocPage extends HTMLElement {
    static get observedAttributes() {
      return ['size', 'width', 'height', 'margin', 'orientation', 'content-width', 'content-height'];
    }
    constructor() {
      super();
      this._root = this.attachShadow({
        mode: 'open'
      });
      this._mo = typeof MutationObserver === 'function' ? new MutationObserver(() => this._scheduleMeasure()) : null;
    }

    /** The named paper's [w, h], swapped when orientation="landscape".
     *  Only the named size swaps — explicit width/height are exact values
     *  the author already oriented. */
    _paperSize() {
      const named = PAPER[(this.getAttribute('size') || '').toLowerCase()] || PAPER.letter;
      const landscape = (this.getAttribute('orientation') || '').trim().toLowerCase() === 'landscape';
      return landscape ? [named[1], named[0]] : named;
    }
    get pageWidth() {
      return safeLen(this.getAttribute('width'), this._paperSize()[0]);
    }
    get pageHeight() {
      return safeLen(this.getAttribute('height'), this._paperSize()[1]);
    }
    get pageMargin() {
      return safeLen(this.getAttribute('margin'), '0.75in');
    }

    /** Scaled-fit mode's content box [w, h] as CSS lengths, or null when
     *  the mode is off (either attribute missing/invalid/zero — a partial
     *  declaration falls back to normal flow rather than guessing). */
    _contentFit() {
      const w = safeLen(this.getAttribute('content-width'), null);
      const h = safeLen(this.getAttribute('content-height'), null);
      if (!w || !h) return null;
      const wPx = toPx(w),
        hPx = toPx(h);
      return wPx > 0 && hPx > 0 ? [w, h, wPx, hPx] : null;
    }
    connectedCallback() {
      if (!this._sheet) this._render();
      this._syncSize();
      this._syncPrintPageRule();
      this._ensureTextWrapDefaults();
      this._ensureOwnsPrintMeta();
      this._syncFixedSizeMeta();
      this._syncPrintSizingMeta();
      if (this._mo) this._mo.observe(this, {
        subtree: true,
        childList: true,
        characterData: true,
        attributes: true
      });
      this._onResize = () => this._scheduleMeasure();
      window.addEventListener('resize', this._onResize);
      if (document.fonts && document.fonts.ready) {
        document.fonts.ready.then(() => this._scheduleMeasure());
      }
      this._scheduleMeasure();
    }
    disconnectedCallback() {
      window.removeEventListener('resize', this._onResize);
      if (this._mo) this._mo.disconnect();
      if (this._raf) {
        cancelAnimationFrame(this._raf);
        this._raf = null;
      }
      // Drop the head rules when the last doc-page leaves, so a deleted
      // document's @page geometry and text-wrap defaults can't apply to
      // whatever replaces it.
      const survivor = document.querySelector('doc-page');
      if (!survivor) {
        ['doc-page-print', 'doc-page-text-wrap', 'doc-page-owns-print', 'doc-page-fixed-size', 'doc-page-print-sizing'].forEach(id => {
          const tag = document.getElementById(id);
          if (tag) tag.remove();
        });
        // A live deck-stage deferred its own print-sizing meta to ours —
        // hand the page-global meta over so the deck isn't left unmarked.
        const deck = document.querySelector('deck-stage');
        if (deck && typeof deck._ensurePrintSizingMeta === 'function') {
          deck._ensurePrintSizingMeta();
        }
      } else {
        // A departed owner hands each page-global meta to whatever
        // doc-page remains (or it's removed).
        if (typeof survivor._syncFixedSizeMeta === 'function') {
          survivor._syncFixedSizeMeta();
        }
        if (typeof survivor._syncPrintSizingMeta === 'function') {
          survivor._syncPrintSizingMeta();
        }
      }
    }
    attributeChangedCallback() {
      if (!this._sheet) return;
      this._syncSize();
      this._syncPrintPageRule();
      this._syncFixedSizeMeta();
      this._syncPrintSizingMeta();
      this._scheduleMeasure();
    }
    _render() {
      this._root.innerHTML = `
        <style>${stylesheet}</style>
        <style id="vars"></style>
        <div class="sheet" data-screen-label="Document">
          <table class="frame" role="presentation">
            <thead><tr><th><div class="hdr-space"><slot name="header"></slot></div></th></tr></thead>
            <tbody><tr><td class="body"><div class="fit-box"><div class="fit"><slot></slot></div></div></td></tr></tbody>
            <tfoot><tr><td><div class="ftr-space"><slot name="footer"></slot></div></td></tr></tfoot>
          </table>
        </div>`;
      this._sheet = this._root.querySelector('.sheet');
      this._vars = this._root.getElementById('vars');
    }

    /** Runtime sizing lives in a shadow <style> :host rule, never on the
     *  light-DOM host element, so serialize-persist can't write it back. */
    _syncSize(hdrH, ftrH) {
      // Scaled-fit mode: content at its authored size, scaled onto the
      // printable area (page minus margins on both axes). The factor is a
      // plain number var so calc(length * number) stays valid; 4 decimals
      // keeps the shadow style stable across re-measures. Upscaling is
      // allowed — print transforms are vector, so text and CSS stay crisp
      // (raster images soften, which the catalog bullet warns about).
      const fit = this._contentFit();
      let fitVars = '';
      if (fit) {
        const marginPx = toPx(this.pageMargin) || 0;
        const availW = toPx(this.pageWidth) - 2 * marginPx;
        const availH = toPx(this.pageHeight) - 2 * marginPx;
        const scale = Math.min(availW / fit[2], availH / fit[3]);
        if (scale > 0 && Number.isFinite(scale)) {
          fitVars = '--doc-fit-w:' + fit[0] + ';' + '--doc-fit-h:' + fit[1] + ';' + '--doc-fit-scale:' + scale.toFixed(4) + ';';
        }
      }
      this._sheet.classList.toggle('fit-mode', !!fitVars);
      // Numeric w/h ratio for the paginated page cards' aspect-ratio —
      // aspect-ratio takes a number, not a length ratio, so compute it
      // here (CSS length division isn't portable). 6 decimals keeps the
      // shadow style stable across re-syncs.
      const arW = toPx(this.pageWidth);
      const arH = toPx(this.pageHeight);
      const ar = arW > 0 && arH > 0 ? (arW / arH).toFixed(6) : '0.772727';
      this._vars.textContent = ':host{' + fitVars + '--doc-page-ar:' + ar + ';' + '--doc-page-w:' + this.pageWidth + ';' + '--doc-page-h:' + this.pageHeight + ';' + '--doc-page-margin:' + this.pageMargin + ';' + '--doc-hdr-h:' + (hdrH || 0) + 'px;' + '--doc-ftr-h:' + (ftrH || 0) + 'px;' + '--doc-hdr-pad:' + (hdrH ? '0.35in' : '0px') + ';' + '--doc-ftr-pad:' + (ftrH ? '0.35in' : '0px') + '}';
    }

    /** @page is a no-op inside shadow DOM, so the rule lives in <head>.
     *  Re-appended on every sync so it stays last in source order — the
     *  @page cascade is source-order per descriptor, so this rule wins
     *  over any other @page rule in the document.
     *
     *  The @page SIZE is pinned where the page box IS part of the design:
     *  explicit-fixed-size mode (width + height authored), scaled-fit
     *  mode (the named sheet the fit targets), and explicit pagination
     *  (the named size the cards share — so card and sheet agree on
     *  every print path, and the export path's chosen paper overrides
     *  BOTH with one later rule). For FLOWING documents no paper size is
     *  emitted at all — the true size comes from the user's preference,
     *  injected by the export path or chosen in the print dialog — so a
     *  flowing document never fights the paper it lands on.
     *  margin: 0 is emitted in every mode: it leaves Chrome no margin box
     *  to draw its date/URL/page-count header in, and the visual margin
     *  lives on the sheet's own padding. */
    _syncPrintPageRule() {
      const id = 'doc-page-print';
      let tag = document.getElementById(id);
      if (!tag) {
        tag = document.createElement('style');
        tag.id = id;
      }
      document.head.appendChild(tag);
      // Three print-geometry regimes:
      // - true-size: the page IS the design — pin its exact size.
      // - scaled-fit (content-width/height): the fit factor is computed
      //   against the NAMED paper's printable area, so that paper must
      //   stay pinned or the scaled content overflows a smaller sheet
      //   (the export path re-fits and re-pins at print time on top).
      // - default modes: no paper size — but landscape still needs the
      //   paper-agnostic 'size: landscape' keyword, because the size
      //   descriptor is what carries orientation; without it a landscape
      //   document prints portrait whenever nothing injects a size.
      const landscape = (this.getAttribute('orientation') || '').trim().toLowerCase() === 'landscape';
      // Explicit pagination pins the page box to the SAME values that
      // size the cards (the named size by default, the export path's
      // chosen paper when its later rule overrides both) — card and
      // sheet agree on every print path, and a mismatched real paper
      // shrinks-to-fit in the dialog instead of clipping a Letter card
      // on A4. Declared before the paginated read below so both derive
      // from one check.
      const paginatedNow = this.querySelector(':scope > .page') !== null;
      const sizeDescriptor = this._trueSizePx() ? 'size: ' + this.pageWidth + ' ' + this.pageHeight + '; ' : this._contentFit() ? 'size: ' + this.pageWidth + ' ' + this.pageHeight + '; ' : paginatedNow ? 'size: ' + this.pageWidth + ' ' + this.pageHeight + '; ' : landscape ? 'size: landscape; ' : '';
      // WebKit never repeats the thead/tfoot spacers that carry a flowing
      // document's vertical page margins (see WK_PRINT above), so pages
      // after the first print edge-to-edge there. Carry the VERTICAL
      // margins on @page for WebKit instead, and the shadow print CSS
      // trims the first-page spacers by the same amount (.sheet.wk-print
      // rules). Horizontal inset stays on the sheet's own padding in
      // every engine. Blink keeps margin: 0 (a nonzero margin there
      // re-opens the box Chrome draws its header furniture in). One cost,
      // learned in testing: Safari's own date/URL headers are a USER
      // dialog setting ("Print headers and footers") that renders in the
      // margin area when room exists — margin: 0 only suppressed it by
      // leaving no room, and no CSS controls it. The export dialog's
      // Safari guide teaches turning the setting off for flowing
      // documents. Explicitly paginated and fixed-size documents keep
      // margin: 0 everywhere: their pages ARE the sheet.
      const wkFlowing = WK_PRINT && !paginatedNow && !this._trueSizePx() && !this._contentFit();
      const marginDescriptor = wkFlowing ? 'margin: ' + this.pageMargin + ' 0; ' : 'margin: 0; ';
      // Shadow-internal marker (never serialized), kept in lockstep with
      // the @page decision above: the print CSS trims the first-page
      // spacers ONLY while @page actually carries the margins — a
      // true-size or scaled-fit sheet keeps margin: 0 and must keep its
      // spacers too. Re-synced here so attribute changes and pagination
      // flips move both together.
      if (this._sheet) this._sheet.classList.toggle('wk-print', wkFlowing);
      tag.textContent = '@page { ' + sizeDescriptor + marginDescriptor + '} ' + '@media print { html, body { margin: 0 !important; padding: 0 !important; background: none !important; height: auto !important; overflow: visible !important; } ' + 'h1,h2,h3,h4,h5,h6 { break-after: avoid; } ' + 'figure,pre,blockquote,img,svg,tr { break-inside: avoid; } ' + 'p,li { orphans: 3; widows: 3; } ' + '* { -webkit-print-color-adjust: exact; print-color-adjust: exact; ' + 'backdrop-filter: none !important; -webkit-backdrop-filter: none !important; } ' + '*, *::before, *::after { animation-delay: -99s !important; animation-duration: .001s !important; ' + 'animation-iteration-count: 1 !important; animation-fill-mode: both !important; ' + 'animation-play-state: running !important; transition-duration: 0s !important; } }';
    }

    /** Typographic defaults for document text: balance headings, avoid
     *  widowed/orphaned words in body copy (browsers without text-wrap
     *  support drop the declarations). Zero-specificity via :where() so
     *  any text-wrap authored on those elements wins; document-level so the
     *  rules reach the slotted (light DOM) content — shadow styles can't.
     *  data-omelette-injected marks the tag for the host editor to strip
     *  at serialize, so it is never written back as authored source. */
    _ensureTextWrapDefaults() {
      if (document.getElementById('doc-page-text-wrap')) return;
      const tag = document.createElement('style');
      tag.id = 'doc-page-text-wrap';
      tag.setAttribute('data-omelette-injected', '');
      tag.textContent = ':where(h1,h2,h3,h4,h5,h6){text-wrap:balance}' + ':where(p,li,blockquote,figcaption){text-wrap:pretty}';
      document.head.appendChild(tag);
    }

    /** Declares that this document owns its print CSS. The instant-PDF
     *  export checks for the meta by NAME PRESENCE alone (content is
     *  ignored) and skips its automatic print-CSS injections, so the
     *  component's @page geometry is never overridden by a heuristic.
     *  data-omelette-injected keeps it out of serialized source. */
    _ensureOwnsPrintMeta() {
      if (document.getElementById('doc-page-owns-print')) return;
      const tag = document.createElement('meta');
      tag.id = 'doc-page-owns-print';
      tag.name = 'omelette-owns-print';
      tag.content = 'true';
      tag.setAttribute('data-omelette-injected', '');
      document.head.appendChild(tag);
    }

    /** This page's valid true-size page box (explicit width AND height)
     *  as [w, h] px ints, or null when the mode is off. */
    _trueSizePx() {
      if (!safeLen(this.getAttribute('width'), null) || !safeLen(this.getAttribute('height'), null)) return null;
      const w = Math.round(toPx(this.pageWidth));
      const h = Math.round(toPx(this.pageHeight));
      return w > 0 && h > 0 ? [w, h] : null;
    }

    /** True-size pages (explicit width AND height) also declare the page
     *  box as the preview size: the in-app preview reads
     *  meta[name="omelette-fixed-size"] (content "W,H" in px ints) and
     *  scales the sheet into view — without it an 18in poster previews at
     *  true size with scrollbars. Never overrides an author-set meta
     *  (only the component's own id is managed). The meta is page-global
     *  while doc-page instances are not, so every sync recomputes the
     *  page-wide owner — the first connected true-size doc-page — and a
     *  non-true-size sibling's sync can never delete the owner's meta.
     *  Removed when no true-size page remains (the owner's disconnect
     *  re-syncs via any survivor) or when an author-set meta exists. */
    _syncFixedSizeMeta() {
      const id = 'doc-page-fixed-size';
      const own = document.getElementById(id);
      const authored = document.querySelector('meta[name="omelette-fixed-size"]:not([data-omelette-injected])');
      // The page-wide owner, not this instance: an upgraded true-size page
      // anywhere in the document keeps the meta alive and sized.
      let box = null;
      for (const el of document.querySelectorAll('doc-page')) {
        box = typeof el._trueSizePx === 'function' ? el._trueSizePx() : null;
        if (box) break;
      }
      if (!box || authored) {
        if (own) own.remove();
        return;
      }
      const tag = own || document.createElement('meta');
      tag.id = id;
      tag.name = 'omelette-fixed-size';
      tag.content = box[0] + ',' + box[1];
      tag.setAttribute('data-omelette-injected', '');
      if (!own) document.head.appendChild(tag);
    }

    /** This page's print-sizing mode: 'fixed' when an explicit width AND
     *  height are authored (the page is the design's own size), else the
     *  default paper in the authored orientation. */
    _printSizingMode() {
      if (this._trueSizePx()) return 'fixed';
      const landscape = (this.getAttribute('orientation') || '').trim().toLowerCase() === 'landscape';
      return landscape ? 'default-landscape' : 'default-portrait';
    }

    /** Announces the print-sizing mode to the host app:
     *  meta[name="omelette-print-sizing"] with content 'default-portrait',
     *  'default-landscape', or 'fixed' (fixed pages also carry the
     *  omelette-fixed-size meta with the page box in px). The export path
     *  probes it to decide what true paper size to inject at print time —
     *  in the default modes the component emits no paper size of its own.
     *  Same page-global ownership rules as the fixed-size meta above:
     *  first connected doc-page owns it, an authored meta is never
     *  overridden, removed when no doc-page remains. */
    _syncPrintSizingMeta() {
      const id = 'doc-page-print-sizing';
      const own = document.getElementById(id);
      const authored = document.querySelector('meta[name="omelette-print-sizing"]:not([data-omelette-injected])');
      // A fixed page wins outright (mirroring the fixed-size loop above,
      // so the two metas can never contradict each other in a mixed
      // multi-page document); otherwise the first page's mode holds.
      let mode = null;
      for (const el of document.querySelectorAll('doc-page')) {
        if (typeof el._printSizingMode !== 'function') continue;
        const m = el._printSizingMode();
        if (m === 'fixed') {
          mode = m;
          break;
        }
        if (mode === null) mode = m;
      }
      if (!mode || authored) {
        if (own) own.remove();
        return;
      }
      // A deck-stage that connected first injected its own meta and
      // defers to any existing one — take it over, or the document ends
      // up with two conflicting injected metas (a doc-page page is the
      // document; the deck re-ensures its meta if every doc-page leaves).
      const deckMeta = document.getElementById('deck-stage-print-sizing');
      if (deckMeta) deckMeta.remove();
      const tag = own || document.createElement('meta');
      tag.id = id;
      tag.name = 'omelette-print-sizing';
      tag.content = mode;
      tag.setAttribute('data-omelette-injected', '');
      if (!own) document.head.appendChild(tag);
    }
    _scheduleMeasure() {
      if (this._raf) return;
      this._raf = requestAnimationFrame(() => {
        this._raf = null;
        this._measure();
      });
    }

    /** Slot heights feed the print spacers (--doc-hdr-h / --doc-ftr-h), so
     *  they re-measure on content mutation, resize, and font load. The
     *  same pass detects explicit pagination (direct .page children) and
     *  toggles the sheet between the flowing-document card and the
     *  page-per-card stack — content edits can add or remove pages at any
     *  time, so this tracks the same mutations the measurement does. */
    _measure() {
      const hdr = this.querySelector(':scope > [slot="header"]');
      const ftr = this.querySelector(':scope > [slot="footer"]');
      const wasPaginated = this._sheet.classList.contains('paginated');
      this._sheet.classList.toggle('paginated', this.querySelector(':scope > .page') !== null);
      // The WebKit @page margin is flowing-only, so a pagination flip
      // must re-emit the rule (content edits can add or remove .page
      // sections at any time).
      if (this._sheet.classList.contains('paginated') !== wasPaginated) {
        this._syncPrintPageRule();
      }
      this._syncSize(hdr ? hdr.offsetHeight : 0, ftr ? ftr.offsetHeight : 0);
    }
  }
  if (!customElements.get('doc-page')) {
    customElements.define('doc-page', DocPage);
  }
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "doc-page.js", error: String((e && e.message) || e) }); }

// ui_kits/app/AddressOverview.jsx
try { (() => {
const NS = window.ChainwatchDesignSystem_f0e832;
const {
  Button,
  Card,
  AddressLabel,
  MonetaryAmount,
  SeverityBadge,
  ConfirmationBadge,
  LiveIndicator
} = NS;
const TX = [{
  date: '2026-08-09',
  dir: 'in',
  addr: '3FZbgi29cpjq2GjdwV8eyHuJJnkLtktZc5',
  amt: 0.42100000,
  conf: 3
}, {
  date: '2026-08-09',
  dir: 'out',
  addr: '1BoatSLRHtKNngkdXEeobR76b53LETtpyT',
  amt: 0.00000320,
  conf: 0
}, {
  date: '2026-08-07',
  dir: 'in',
  addr: 'bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq',
  amt: 0.05000000,
  conf: 210
}, {
  date: '2026-08-02',
  dir: 'out',
  addr: '3M219KR5vEneNb47ewrPfWyb5jQ2DjxRP6',
  amt: 4.80000000,
  conf: 412
}, {
  date: '2026-07-30',
  dir: 'in',
  addr: 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
  amt: 1.00000000,
  conf: 890
}];
const FACTORS = [{
  sev: 'critical',
  label: 'wallet swept in a single transaction, no change output returned',
  delta: '+35'
}, {
  sev: 'high',
  label: 'fan-in from 14 sources within 1 hour',
  delta: '+22'
}, {
  sev: 'medium',
  label: 'output dormant 5 years before being spent',
  delta: '+9'
}];
const OVERALL_SEVERITY = FACTORS.some(f => f.sev === 'critical') ? 'critical' : FACTORS.some(f => f.sev === 'high') ? 'high' : 'medium';
const SPARK = [20, 35, 15, 60, 40, 80, 30, 55, 25, 70, 45, 90, 20, 38, 60, 33, 15, 50, 65, 28];
function Stat({
  label,
  children
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      textAlign: 'right'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--text-label-size)',
      color: 'var(--text-secondary)',
      marginBottom: 4
    }
  }, label), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--text-mono-body-size)',
      fontVariantNumeric: 'tabular-nums',
      color: 'var(--text-primary)'
    }
  }, children));
}
function SectionTitle({
  children
}) {
  return /*#__PURE__*/React.createElement("h2", {
    style: {
      fontSize: 'var(--text-label-size)',
      textTransform: 'lowercase',
      color: 'var(--text-secondary)',
      fontWeight: 500,
      margin: '0 0 var(--space-4)'
    }
  }, children);
}
function AddressOverview({
  onBack
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)'
    }
  }, /*#__PURE__*/React.createElement("button", {
    onClick: onBack,
    style: {
      border: 'none',
      background: 'none',
      color: 'var(--text-primary)',
      textDecoration: 'underline',
      fontSize: 'var(--text-body-small-size)',
      cursor: 'pointer',
      padding: 0,
      marginBottom: 'var(--space-6)'
    }
  }, "\u2190 back"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: 'var(--space-12)'
    }
  }, /*#__PURE__*/React.createElement(AddressLabel, {
    address: "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
  }), /*#__PURE__*/React.createElement(Button, {
    variant: "primary"
  }, "watch this address")), /*#__PURE__*/React.createElement("div", {
    style: {
      marginBottom: 'var(--space-12)'
    }
  }, /*#__PURE__*/React.createElement(SectionTitle, null, "overview"), /*#__PURE__*/React.createElement(Card, {
    style: {
      display: 'grid',
      gridTemplateColumns: 'repeat(6, 1fr)',
      gap: 'var(--space-6)'
    }
  }, /*#__PURE__*/React.createElement(Stat, {
    label: "balance"
  }, "0.42100000"), /*#__PURE__*/React.createElement(Stat, {
    label: "total received"
  }, "3.88000000"), /*#__PURE__*/React.createElement(Stat, {
    label: "total sent"
  }, "3.45900000"), /*#__PURE__*/React.createElement(Stat, {
    label: "tx count"
  }, "128"), /*#__PURE__*/React.createElement(Stat, {
    label: "first seen"
  }, "2019-03-11"), /*#__PURE__*/React.createElement(Stat, {
    label: "last seen"
  }, "2026-08-09"))), /*#__PURE__*/React.createElement("div", {
    style: {
      marginBottom: 'var(--space-12)'
    }
  }, /*#__PURE__*/React.createElement(SectionTitle, null, "risk"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 'var(--space-6)'
    }
  }, /*#__PURE__*/React.createElement(Card, {
    style: {
      width: 160,
      flex: 'none',
      textAlign: 'center'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--text-label-size)',
      color: 'var(--text-secondary)',
      marginBottom: 4
    }
  }, "risk score"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 40,
      fontWeight: 600,
      color: 'var(--severity-critical-text)',
      fontFamily: 'var(--font-mono)'
    }
  }, "78"), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 'var(--space-2)'
    }
  }, /*#__PURE__*/React.createElement(SeverityBadge, {
    severity: OVERALL_SEVERITY,
    label: OVERALL_SEVERITY + " risk"
  }))), /*#__PURE__*/React.createElement(Card, {
    style: {
      flex: 1
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--text-label-size)',
      color: 'var(--text-secondary)',
      marginBottom: 'var(--space-2)'
    }
  }, "contributing factors"), FACTORS.map((f, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: 'var(--space-2) 0',
      borderBottom: i < FACTORS.length - 1 ? '1px solid var(--border)' : 'none'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 'var(--space-3)'
    }
  }, /*#__PURE__*/React.createElement(SeverityBadge, {
    severity: f.sev
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--text-body-small-size)',
      color: 'var(--text-primary)'
    }
  }, f.label)), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--text-mono-small-size)',
      color: 'var(--text-secondary)'
    }
  }, f.delta)))))), /*#__PURE__*/React.createElement("div", {
    style: {
      marginBottom: 'var(--space-12)'
    }
  }, /*#__PURE__*/React.createElement(SectionTitle, null, "activity"), /*#__PURE__*/React.createElement(Card, {
    style: {
      display: 'flex',
      alignItems: 'flex-end',
      gap: 4,
      height: 90
    }
  }, SPARK.map((h, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      flex: 1,
      height: `${h}%`,
      background: 'var(--surface-raised)',
      borderTop: '2px solid var(--border-strong)'
    }
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--text-label-size)',
      color: 'var(--text-muted)',
      marginTop: 'var(--space-2)'
    }
  }, "transaction volume over time")), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: 'var(--space-4)'
    }
  }, /*#__PURE__*/React.createElement(SectionTitle, null, "transactions"), /*#__PURE__*/React.createElement(LiveIndicator, {
    secondsAgo: 30
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-card)',
      overflow: 'hidden'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      background: 'var(--surface-raised)',
      fontSize: 'var(--text-label-size)',
      color: 'var(--text-secondary)',
      fontWeight: 500,
      padding: 'var(--table-cell-pad-v) var(--table-cell-pad-h)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }, "date"), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }, "direction"), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 3
    }
  }, "counterparty"), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      textAlign: 'right'
    }
  }, "confirmations"), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      textAlign: 'right'
    }
  }, "amount (btc)")), TX.map((t, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      display: 'flex',
      alignItems: 'center',
      height: 'var(--table-row-height)',
      padding: '0 var(--table-cell-pad-h)',
      borderBottom: i < TX.length - 1 ? '1px solid var(--border)' : 'none'
    },
    onMouseEnter: e => e.currentTarget.style.background = 'var(--surface-raised)',
    onMouseLeave: e => e.currentTarget.style.background = 'transparent'
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--text-mono-small-size)',
      color: 'var(--text-primary)'
    }
  }, t.date), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      fontSize: 'var(--text-body-small-size)',
      color: 'var(--text-secondary)'
    }
  }, t.dir), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 3
    }
  }, /*#__PURE__*/React.createElement(AddressLabel, {
    address: t.addr,
    head: 6,
    tail: 4
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      textAlign: 'right',
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--text-mono-small-size)',
      color: t.conf === 0 ? 'var(--text-secondary)' : 'var(--text-primary)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'flex-end',
      gap: 6
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 8,
      height: 8,
      borderRadius: 'var(--radius-full)',
      display: 'inline-block',
      flex: 'none',
      background: t.conf === 0 ? 'transparent' : 'var(--text-secondary)',
      border: t.conf === 0 ? '1.5px solid var(--text-secondary)' : 'none'
    }
  }), t.conf === 0 ? 'unconfirmed' : t.conf), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      textAlign: 'right',
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--text-mono-body-size)',
      fontVariantNumeric: 'tabular-nums',
      color: t.amt < 0.000001 ? 'var(--text-muted)' : 'var(--text-primary)'
    }
  }, Number(t.amt).toFixed(8)), "            "))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'flex-end',
      gap: 'var(--space-2)',
      marginTop: 'var(--space-4)',
      fontSize: 'var(--text-body-small-size)',
      color: 'var(--text-secondary)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      cursor: 'pointer'
    }
  }, "\u2190 prev"), /*#__PURE__*/React.createElement("span", {
    style: {
      border: '1px solid var(--border-strong)',
      borderRadius: 'var(--radius-control)',
      padding: '2px 10px',
      color: 'var(--text-primary)'
    }
  }, "1"), /*#__PURE__*/React.createElement("span", {
    style: {
      padding: '2px 10px',
      cursor: 'pointer'
    }
  }, "2"), /*#__PURE__*/React.createElement("span", {
    style: {
      padding: '2px 10px',
      cursor: 'pointer'
    }
  }, "3"), /*#__PURE__*/React.createElement("span", {
    style: {
      cursor: 'pointer'
    }
  }, "next \u2192"))));
}
window.AddressOverview = AddressOverview;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/app/AddressOverview.jsx", error: String((e && e.message) || e) }); }

// ui_kits/app/AlertsFeed.jsx
try { (() => {
const NS = window.ChainwatchDesignSystem_f0e832;
const {
  SeverityBadge,
  LiveIndicator,
  Input,
  Select,
  AddressLabel
} = NS;
const ALERTS = [{
  id: 1,
  addr: 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
  sev: 'critical',
  desc: 'wallet swept, no change output',
  time: '2m ago'
}, {
  id: 2,
  addr: '3FZbgi29cpjq2GjdwV8eyHuJJnkLtktZc5',
  sev: 'high',
  desc: 'fan-in from 14 sources in 1 hour',
  time: '11m ago'
}, {
  id: 3,
  addr: '1BoatSLRHtKNngkdXEeobR76b53LETtpyT',
  sev: 'medium',
  desc: 'output dormant 5 years before spend',
  time: '38m ago'
}, {
  id: 4,
  addr: 'bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq',
  sev: 'medium',
  desc: 'inbound from address with no prior history',
  time: '1h ago'
}, {
  id: 5,
  addr: '3M219KR5vEneNb47ewrPfWyb5jQ2DjxRP6',
  sev: 'low',
  desc: 'first transaction on address',
  time: '3h ago'
}];
function AlertsFeed({
  onSelect
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: 'var(--space-6)'
    }
  }, /*#__PURE__*/React.createElement("h1", {
    style: {
      fontSize: 'var(--text-display-size)',
      fontWeight: 600,
      margin: 0,
      color: 'var(--text-primary)'
    }
  }, "alerts"), /*#__PURE__*/React.createElement(LiveIndicator, {
    secondsAgo: 4
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 'var(--space-3)',
      marginBottom: 'var(--space-6)'
    }
  }, /*#__PURE__*/React.createElement(Input, {
    placeholder: "search address or tx id",
    style: {
      flex: 1
    }
  }), /*#__PURE__*/React.createElement(Select, {
    options: [{
      value: 'all',
      label: 'all severities'
    }, {
      value: 'critical',
      label: 'critical'
    }, {
      value: 'high',
      label: 'high'
    }]
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-card)',
      overflow: 'hidden'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      background: 'var(--surface-raised)',
      display: 'flex',
      padding: 'var(--table-cell-pad-v) var(--table-cell-pad-h)',
      fontSize: 'var(--text-label-size)',
      color: 'var(--text-secondary)',
      fontWeight: 500
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 2
    }
  }, "address"), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }, "severity"), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 3
    }
  }, "description"), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      textAlign: 'right'
    }
  }, "seen")), ALERTS.map(a => /*#__PURE__*/React.createElement("div", {
    key: a.id,
    onClick: () => onSelect(a),
    style: {
      display: 'flex',
      alignItems: 'center',
      height: 'var(--table-row-height)',
      padding: '0 var(--table-cell-pad-h)',
      borderBottom: '1px solid var(--border)',
      cursor: 'pointer'
    },
    onMouseEnter: e => e.currentTarget.style.background = 'var(--surface-raised)',
    onMouseLeave: e => e.currentTarget.style.background = 'transparent'
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 2
    }
  }, /*#__PURE__*/React.createElement(AddressLabel, {
    address: a.addr,
    head: 6,
    tail: 4
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }, /*#__PURE__*/React.createElement(SeverityBadge, {
    severity: a.sev
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 3,
      fontSize: 'var(--text-body-small-size)',
      color: 'var(--text-primary)'
    }
  }, a.desc), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      textAlign: 'right',
      fontSize: 'var(--text-label-size)',
      color: 'var(--text-muted)'
    }
  }, a.time)))));
}
window.AlertsFeed = AlertsFeed;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/app/AlertsFeed.jsx", error: String((e && e.message) || e) }); }

// ui_kits/app/CaseDetail.jsx
try { (() => {
const NS = window.ChainwatchDesignSystem_f0e832;
const {
  SeverityBadge,
  ConfirmationBadge,
  AddressLabel,
  MonetaryAmount,
  DataTable,
  Button,
  Card
} = NS;
const TX = [{
  txid: 'f4a1c9e2b7d3a6f01e5c8b9d2a4f6e8c1b3d5a7f9e0c2b4d6a8f0e2c4b6a8d0e',
  addr: 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
  amt: 0.42100000,
  conf: 0
}, {
  txid: 'a2b4c6d8e0f2a4b6c8d0e2f4a6b8c0d2e4f6a8b0c2d4e6f8a0b2c4d6e8f0a2b4',
  addr: '3FZbgi29cpjq2GjdwV8eyHuJJnkLtktZc5',
  amt: 0.00000320,
  conf: 3
}, {
  txid: 'c6d8e0f2a4b6c8d0e2f4a6b8c0d2e4f6a8b0c2d4e6f8a0b2c4d6e8f0a2b4c6d8',
  addr: '1BoatSLRHtKNngkdXEeobR76b53LETtpyT',
  amt: 1.00000000,
  conf: 210
}];
function CaseDetail({
  alert,
  onBack
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-sans)'
    }
  }, /*#__PURE__*/React.createElement("button", {
    onClick: onBack,
    style: {
      border: 'none',
      background: 'none',
      color: 'var(--text-primary)',
      textDecoration: 'underline',
      fontSize: 'var(--text-body-small-size)',
      cursor: 'pointer',
      padding: 0,
      marginBottom: 'var(--space-4)'
    }
  }, "\u2190 back to alerts"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'flex-start',
      marginBottom: 'var(--space-8)'
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h1", {
    style: {
      fontSize: 'var(--text-h1-size)',
      fontWeight: 600,
      margin: '0 0 8px',
      color: 'var(--text-primary)'
    }
  }, "case review"), /*#__PURE__*/React.createElement(AddressLabel, {
    address: alert.addr
  })), /*#__PURE__*/React.createElement(SeverityBadge, {
    severity: alert.sev
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: '1fr 1fr 1fr',
      gap: 'var(--space-6)',
      marginBottom: 'var(--space-8)'
    }
  }, /*#__PURE__*/React.createElement(Card, null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--text-label-size)',
      color: 'var(--text-secondary)',
      marginBottom: 4
    }
  }, "total exposure"), /*#__PURE__*/React.createElement(MonetaryAmount, {
    value: 1.4210032,
    unit: "btc"
  })), /*#__PURE__*/React.createElement(Card, null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--text-label-size)',
      color: 'var(--text-secondary)',
      marginBottom: 4
    }
  }, "linked addresses"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--text-mono-body-size)'
    }
  }, "7")), /*#__PURE__*/React.createElement(Card, null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--text-label-size)',
      color: 'var(--text-secondary)',
      marginBottom: 4
    }
  }, "flagged since"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--text-body-small-size)',
      color: 'var(--text-primary)'
    }
  }, "2 hours ago"))), /*#__PURE__*/React.createElement("h2", {
    style: {
      fontSize: 'var(--text-h2-size)',
      fontWeight: 600,
      marginBottom: 'var(--space-4)',
      color: 'var(--text-primary)'
    }
  }, "transactions"), /*#__PURE__*/React.createElement(DataTable, {
    columns: [{
      key: 'txid',
      label: 'transaction'
    }, {
      key: 'addr',
      label: 'counterparty'
    }, {
      key: 'conf',
      label: 'confirmations'
    }, {
      key: 'amt',
      label: 'amount',
      align: 'right'
    }],
    rows: TX,
    renderCell: (row, col) => {
      if (col.key === 'txid') return /*#__PURE__*/React.createElement(AddressLabel, {
        address: row.txid,
        head: 8,
        tail: 6
      });
      if (col.key === 'addr') return /*#__PURE__*/React.createElement(AddressLabel, {
        address: row.addr,
        head: 6,
        tail: 4
      });
      if (col.key === 'conf') return /*#__PURE__*/React.createElement(ConfirmationBadge, {
        confirmations: row.conf
      });
      return /*#__PURE__*/React.createElement(MonetaryAmount, {
        value: row.amt
      });
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 'var(--space-3)',
      marginTop: 'var(--space-8)'
    }
  }, /*#__PURE__*/React.createElement(Button, {
    variant: "primary"
  }, "escalate case"), /*#__PURE__*/React.createElement(Button, {
    variant: "secondary"
  }, "mark reviewed"), /*#__PURE__*/React.createElement(Button, {
    variant: "destructive"
  }, "dismiss")));
}
window.CaseDetail = CaseDetail;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/app/CaseDetail.jsx", error: String((e && e.message) || e) }); }

// ui_kits/victim/ActionScreen.jsx
try { (() => {
const NS4 = window.ChainwatchDesignSystem_f0e832;
const {
  Statement,
  Button
} = NS4;
const CONTENTS = ['A timeline of every movement, with dates and times', 'The transaction identifiers, so each movement can be checked independently', 'The path the funds took, hop by hop', 'The addresses the funds reached, and what we know about them', 'How certain we are about each inference, stated for every step'];
function ActionScreen({
  onGenerate
}) {
  return /*#__PURE__*/React.createElement(VictimShell, {
    background: "var(--surface-page)"
  }, /*#__PURE__*/React.createElement(Statement, {
    style: {
      marginBottom: 'var(--space-6)'
    }
  }, "You can take this to the police."), /*#__PURE__*/React.createElement("p", {
    style: {
      fontSize: 'var(--text-body-size)',
      lineHeight: 'var(--text-body-lh)',
      color: 'var(--text-primary)',
      margin: '0 0 var(--space-4)',
      textWrap: 'pretty'
    }
  }, "Fraud in the UK is reported to Action Fraud, the national reporting centre. Most people reporting stolen cryptocurrency have nothing concrete to give them."), /*#__PURE__*/React.createElement("p", {
    style: {
      fontSize: 'var(--text-body-size)',
      lineHeight: 'var(--text-body-lh)',
      color: 'var(--text-primary)',
      margin: '0 0 var(--space-12)',
      textWrap: 'pretty'
    }
  }, "A report containing this trace gives them specific movements, times and destinations to act on. That is worth doing, and it is honest to say it does not mean your funds will be recovered \u2014 most stolen cryptocurrency is not. What a trace can do is make your report one that can be investigated rather than filed."), /*#__PURE__*/React.createElement(Button, {
    variant: "primary",
    onClick: onGenerate,
    style: {
      height: 52,
      padding: '0 32px',
      fontSize: 'var(--text-h3-size)',
      borderRadius: 'var(--radius-card)'
    }
  }, "generate report"), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 'var(--space-8)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--text-label-size)',
      color: 'var(--text-secondary)',
      marginBottom: 'var(--space-3)'
    }
  }, "the report contains"), /*#__PURE__*/React.createElement("ul", {
    style: {
      margin: 0,
      padding: 0,
      display: 'flex',
      flexDirection: 'column',
      gap: 'var(--space-2)'
    }
  }, CONTENTS.map(c => /*#__PURE__*/React.createElement("li", {
    key: c,
    style: {
      listStyle: 'none',
      display: 'flex',
      gap: 'var(--space-3)',
      fontSize: 'var(--text-body-small-size)',
      lineHeight: 1.5,
      color: 'var(--text-primary)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 6,
      height: 6,
      borderRadius: 'var(--radius-full)',
      background: 'var(--text-muted)',
      flex: 'none',
      marginTop: 7
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      textWrap: 'pretty'
    }
  }, c))))));
}
window.ActionScreen = ActionScreen;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/victim/ActionScreen.jsx", error: String((e && e.message) || e) }); }

// ui_kits/victim/MovementScreen.jsx
try { (() => {
const NS2 = window.ChainwatchDesignSystem_f0e832;
const {
  Statement,
  Button
} = NS2;
function MovementScreen({
  txid,
  onAdvance
}) {
  return /*#__PURE__*/React.createElement(VictimShell, {
    background: "var(--surface-page)"
  }, /*#__PURE__*/React.createElement(Statement, {
    style: {
      marginBottom: 'var(--space-4)'
    }
  }, "Your funds moved 4 hours ago."), /*#__PURE__*/React.createElement("p", {
    style: {
      fontSize: 'var(--text-body-size)',
      lineHeight: 'var(--text-body-lh)',
      color: 'var(--text-primary)',
      margin: '0 0 var(--space-6)'
    }
  }, "0.42 BTC left this address in one transaction."), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--text-mono-small-size)',
      color: 'var(--text-secondary)',
      wordBreak: 'break-all',
      marginBottom: 'var(--space-8)'
    }
  }, txid), /*#__PURE__*/React.createElement(Button, {
    variant: "primary",
    onClick: onAdvance
  }, "see where it went"));
}
window.MovementScreen = MovementScreen;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/victim/MovementScreen.jsx", error: String((e && e.message) || e) }); }

// ui_kits/victim/TraceTimeline.jsx
try { (() => {
const NS3 = window.ChainwatchDesignSystem_f0e832;
const {
  Button,
  ConfidenceIndicator
} = NS3;
const EVENTS = [{
  kind: 'past',
  sentence: 'Your funds left your wallet',
  time: '14:32',
  relative: '4 hours ago',
  detail: '0.42 BTC in one transaction',
  addresses: ['bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh']
}, {
  kind: 'past',
  sentence: 'Split across 3 addresses',
  time: '14:33',
  detail: '0.31 BTC, 0.08 BTC, 0.03 BTC',
  addresses: ['3FZbgi29cpjq2GjdwV8eyHuJJnkLtktZc5', 'bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq', '3M219KR5vEneNb47ewrPfWyb5jQ2DjxRP6']
}, {
  kind: 'past',
  sentence: 'Largest amount moved again',
  time: '16:10',
  detail: '0.31 BTC to a single address',
  addresses: ['1BoatSLRHtKNngkdXEeobR76b53LETtpyT'],
  inference: {
    label: 'This address appears to belong to an exchange',
    percent: 78
  }
}, {
  kind: 'unresolved',
  sentence: 'One smaller amount could not be followed',
  time: '16:14',
  detail: '0.03 BTC passed through a service that does not publish its records. We cannot say where it went next.',
  addresses: ['3M219KR5vEneNb47ewrPfWyb5jQ2DjxRP6']
}, {
  kind: 'current',
  sentence: 'Nothing further in 2 hours',
  time: 'now',
  detail: 'The trail currently ends here. If these funds move again, this page updates and you will be told.'
}];
function Marker({
  kind,
  isLast
}) {
  const filled = kind === 'past' || kind === 'unresolved';
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      flex: 'none',
      width: 12
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 10,
      height: 10,
      borderRadius: 'var(--radius-full)',
      flex: 'none',
      marginTop: 6,
      background: filled ? 'var(--text-primary)' : 'transparent',
      border: filled ? 'none' : '1.5px solid var(--text-primary)',
      boxSizing: 'border-box'
    }
  }), !isLast ? /*#__PURE__*/React.createElement("span", {
    style: {
      flex: 1,
      width: 1,
      background: 'var(--border-strong)',
      marginTop: 4
    }
  }) : null);
}
function Entry({
  event,
  isLast
}) {
  return /*#__PURE__*/React.createElement("li", {
    style: {
      display: 'flex',
      gap: 'var(--space-4)',
      listStyle: 'none'
    }
  }, /*#__PURE__*/React.createElement(Marker, {
    kind: event.kind,
    isLast: isLast
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      paddingBottom: isLast ? 0 : 'var(--space-8)',
      flex: 1
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'baseline',
      gap: 'var(--space-4)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--text-h3-size)',
      lineHeight: 'var(--text-h3-lh)',
      fontWeight: 600,
      color: 'var(--text-primary)'
    }
  }, event.sentence), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--text-mono-small-size)',
      fontVariantNumeric: 'tabular-nums',
      color: 'var(--text-muted)',
      flex: 'none'
    }
  }, event.time, event.relative ? `, ${event.relative}` : '')), /*#__PURE__*/React.createElement("p", {
    style: {
      fontSize: 'var(--text-body-size)',
      lineHeight: 'var(--text-body-lh)',
      color: event.kind === 'unresolved' ? 'var(--text-secondary)' : 'var(--text-primary)',
      margin: 'var(--space-1) 0 0',
      textWrap: 'pretty'
    }
  }, event.detail), event.inference ? /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 'var(--space-2)'
    }
  }, /*#__PURE__*/React.createElement(ConfidenceIndicator, {
    label: event.inference.label,
    percent: event.inference.percent
  })) : null, event.addresses ? /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 'var(--space-3)',
      display: 'flex',
      flexDirection: 'column',
      gap: 'var(--space-1)'
    }
  }, event.addresses.map(a => /*#__PURE__*/React.createElement("div", {
    key: a,
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--text-mono-small-size)',
      color: 'var(--text-secondary)',
      wordBreak: 'break-all'
    }
  }, a))) : null));
}
function TraceTimeline({
  onReport
}) {
  return /*#__PURE__*/React.createElement(VictimShell, {
    background: "var(--surface-page)"
  }, /*#__PURE__*/React.createElement("h1", {
    style: {
      fontSize: 'var(--text-h1-size)',
      lineHeight: 'var(--text-h1-lh)',
      fontWeight: 600,
      color: 'var(--text-primary)',
      margin: '0 0 var(--space-8)'
    }
  }, "Where your funds went"), /*#__PURE__*/React.createElement("ol", {
    style: {
      margin: 0,
      padding: 0
    }
  }, EVENTS.map((e, i) => /*#__PURE__*/React.createElement(Entry, {
    key: i,
    event: e,
    isLast: i === EVENTS.length - 1
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 'var(--space-12)'
    }
  }, /*#__PURE__*/React.createElement(Button, {
    variant: "primary",
    onClick: onReport
  }, "generate report")));
}
window.TraceTimeline = TraceTimeline;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/victim/TraceTimeline.jsx", error: String((e && e.message) || e) }); }

// ui_kits/victim/WaitingScreen.jsx
try { (() => {
const NS = window.ChainwatchDesignSystem_f0e832;
const {
  AddressLabel,
  WarningBlock
} = NS;
function SafetyNotice() {
  return /*#__PURE__*/React.createElement(WarningBlock, {
    style: {
      marginTop: 'var(--space-16)'
    }
  }, "Chainwatch will never contact you first, never ask for payment, and never ask for your keys or seed phrase. Nobody legitimate will offer to recover your funds for an upfront fee.");
}
function VictimShell({
  background,
  children
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      background,
      minHeight: '100vh',
      padding: 'var(--space-16) var(--space-8)',
      fontFamily: 'var(--font-sans)',
      boxSizing: 'border-box'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 560,
      margin: '0 auto'
    }
  }, children, /*#__PURE__*/React.createElement(SafetyNotice, null)));
}
function WaitingScreen({
  address
}) {
  return /*#__PURE__*/React.createElement(VictimShell, {
    background: "var(--surface-raised)"
  }, /*#__PURE__*/React.createElement(AddressLabel, {
    address: address
  }), /*#__PURE__*/React.createElement("p", {
    style: {
      fontSize: 'var(--text-body-size)',
      lineHeight: 'var(--text-body-lh)',
      color: 'var(--text-primary)',
      margin: 'var(--space-6) 0 var(--space-2)'
    }
  }, "No movement since you started watching, 3 days ago."), /*#__PURE__*/React.createElement("p", {
    style: {
      fontSize: 'var(--text-label-size)',
      color: 'var(--text-muted)',
      margin: 0
    }
  }, "Checked 12 seconds ago"));
}
window.WaitingScreen = WaitingScreen;
window.VictimShell = VictimShell;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/victim/WaitingScreen.jsx", error: String((e && e.message) || e) }); }

__ds_ns.ConfirmationBadge = __ds_scope.ConfirmationBadge;

__ds_ns.SeverityBadge = __ds_scope.SeverityBadge;

__ds_ns.Button = __ds_scope.Button;

__ds_ns.Card = __ds_scope.Card;

__ds_ns.Statement = __ds_scope.Statement;

__ds_ns.AddressDiff = __ds_scope.AddressDiff;

__ds_ns.AddressLabel = __ds_scope.AddressLabel;

__ds_ns.DataTable = __ds_scope.DataTable;

__ds_ns.MonetaryAmount = __ds_scope.MonetaryAmount;

__ds_ns.ConfidenceIndicator = __ds_scope.ConfidenceIndicator;

__ds_ns.EmptyState = __ds_scope.EmptyState;

__ds_ns.InvalidatedState = __ds_scope.InvalidatedState;

__ds_ns.LiveIndicator = __ds_scope.LiveIndicator;

__ds_ns.SkeletonBlock = __ds_scope.SkeletonBlock;

__ds_ns.WarningBlock = __ds_scope.WarningBlock;

__ds_ns.Input = __ds_scope.Input;

__ds_ns.Select = __ds_scope.Select;

})();
