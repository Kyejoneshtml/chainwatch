export interface ButtonProps {
  /** Visual style. Destructive is an outline, never a filled red button. */
  variant?: 'primary' | 'secondary' | 'destructive';
  disabled?: boolean;
  children: React.ReactNode;
  onClick?: () => void;
}
