export interface AddressLabelProps {
  /** Full address or transaction id string. */
  address: string;
  /** Characters shown before the ellipsis. */
  head?: number;
  /** Characters shown after the ellipsis — kept legible because trailing characters matter as much as leading ones. */
  tail?: number;
}
