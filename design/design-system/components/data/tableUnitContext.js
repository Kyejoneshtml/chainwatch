import React from 'react';

// Shared context: DataTable sets this so MonetaryAmount drops its unit suffix inside a table,
// where the column header already carries the unit. Deliberately camelCase so it stays off the
// public component namespace.
export const tableUnitContext = React.createContext(false);
