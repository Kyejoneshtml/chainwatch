/**
 * @startingPoint section="Components" subtitle="Dense scanning table with hairline rows" viewport="700x260"
 */
export interface Column {
  key: string;
  label: string;
  align?: 'left' | 'right' | 'center';
}
export interface DataTableProps {
  columns: Column[];
  rows: Record<string, any>[];
  /** Custom cell renderer, e.g. to drop in AddressLabel/MonetaryAmount/SeverityBadge per column. */
  renderCell?: (row: Record<string, any>, column: Column) => React.ReactNode;
}
