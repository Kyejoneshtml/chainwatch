export interface AddressDiffProps {
  /** The address to render. */
  address: string;
  /** The other address it appears alongside. Diffing only engages when the two share 4+ leading and 4+ trailing characters. */
  against: string;
}
