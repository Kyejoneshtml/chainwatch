export interface SeverityBadgeProps {
  severity?: 'critical' | 'high' | 'medium' | 'low';
  /** Defaults to the severity name (sentence case). */
  label?: string;
}
