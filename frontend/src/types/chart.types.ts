/**
 * Chart configuration and customization types
 * Created in PR#14, used in PR#15 for user/company chart preferences
 *
 * Design: Charts automatically apply user/company preferences stored in settings.
 * Users configure chart style once in Settings, and all charts use those preferences.
 */

// Chart customization options (configured in user settings)
export interface ChartConfig {
  // Chart type preference
  type?: 'bar' | 'line' | 'pie' | 'scatter' | 'heatmap' | 'table';

  // Color scheme preference
  colorScheme?: ColorScheme;

  // Layout preferences
  layout?: {
    showLegend?: boolean;
    legendPosition?: 'top' | 'bottom' | 'left' | 'right';
    showGrid?: boolean;
    fontSize?: number;
    fontFamily?: string;
  };

  // Export preferences
  export?: {
    width?: number;
    height?: number;
    dpi?: number;
  };

  // Advanced preferences
  advanced?: {
    showDataLabels?: boolean;
    enableAnimation?: boolean;
    enableZoom?: boolean;
    customColors?: string[];
  };
}

export interface ColorScheme {
  id: string;
  name: string;
  colors: string[];
  background?: string;
  textColor?: string;
}

// Pre-defined color schemes (can be extended in PR#15)
export const DEFAULT_COLOR_SCHEMES: ColorScheme[] = [
  {
    id: 'default',
    name: 'Default',
    colors: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'],
  },
  {
    id: 'professional',
    name: 'Professional',
    colors: ['#1e40af', '#047857', '#b45309', '#991b1b', '#6d28d9', '#9f1239'],
  },
  {
    id: 'pastel',
    name: 'Pastel',
    colors: ['#93c5fd', '#6ee7b7', '#fcd34d', '#fca5a5', '#c4b5fd', '#f9a8d4'],
  },
];

// Chart style template (for users to save and share preferences)
export interface ChartTemplate {
  id: string;
  name: string;
  description?: string;
  config: ChartConfig;
  thumbnail?: string;
  createdAt: Date;
  updatedAt: Date;
}
