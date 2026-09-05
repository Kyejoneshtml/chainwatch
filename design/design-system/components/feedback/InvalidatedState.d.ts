export interface InvalidatedStateProps {
  /** The withdrawn alert or row content — rendered struck through. */
  children: React.ReactNode;
  /** Plain-language reason. Defaults to the reorganization explanation. */
  explanation?: string;
}
