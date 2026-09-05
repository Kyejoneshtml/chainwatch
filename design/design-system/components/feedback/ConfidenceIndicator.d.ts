export interface ConfidenceIndicatorProps {
  /** The interpretation, e.g. "Likely change". Required — a bare percentage is never shown alone. */
  label: string;
  /** 0–100. Rendered in parentheses after the label. */
  percent?: number;
}
