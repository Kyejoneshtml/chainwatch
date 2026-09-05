export interface MonetaryAmountProps {
  value: number | string;
  unit?: 'btc' | 'sats';
  /** Force the muted treatment even above the dust threshold. */
  muted?: boolean;
  /**
   * Whether to append "BTC" / "sats" after the figure.
   * Defaults to true for standalone figures and false inside a DataTable, where the
   * column header carries the unit. Pass explicitly to override either default.
   */
  showUnit?: boolean;
}
