/**
 * Chart preferences types matching backend Pydantic schemas
 */

export interface PlotlyLayoutTemplate {
  font?: Record<string, any>;
  title?: Record<string, any>;
  colorway?: string[];
  plot_bgcolor?: string;
  paper_bgcolor?: string;
  hovermode?: string;
  logo_url?: string; // URL or base64 data URI for logo
  logo_position?: {
    x?: number;
    y?: number;
    sizex?: number;
    sizey?: number;
    xanchor?: string;
    yanchor?: string;
  };
}

export interface PlotlyDataTemplate {
  bar?: Array<Record<string, any>>;
  scatter?: Array<Record<string, any>>;
  line?: Array<Record<string, any>>;
}

export interface CustomTemplateDefinition {
  layout?: PlotlyLayoutTemplate;
  data?: PlotlyDataTemplate;
}

export interface ChartTemplateConfig {
  type: "builtin" | "custom";
  name?: string; // For builtin templates
  custom_definition?: CustomTemplateDefinition;
  created_at: string;
  updated_at: string;
}

export interface SavedTemplate {
  id: string;
  name: string;
  description?: string;
  template_definition: CustomTemplateDefinition;
  thumbnail?: string;
  created_at: string;
  updated_at: string;
}

export interface UserChartPreferences {
  chart_template: ChartTemplateConfig;
  saved_templates: SavedTemplate[];
  available_builtin_templates: string[];
}

export interface UpdateChartPreferencesRequest {
  chart_template: ChartTemplateConfig;
}

export interface SaveTemplateRequest {
  name: string;
  description?: string;
  template_definition: CustomTemplateDefinition;
  thumbnail?: string;
}

// Builtin Plotly templates
export const BUILTIN_PLOTLY_TEMPLATES = [
  "plotly",
  "plotly_white",
  "plotly_dark",
  "ggplot2",
  "seaborn",
  "simple_white",
  "presentation",
  "xgridoff",
  "ygridoff",
  "gridon",
  "none"
] as const;

export type BuiltinPlotlyTemplate = typeof BUILTIN_PLOTLY_TEMPLATES[number];

// Template metadata for UI display
export interface TemplateMetadata {
  name: string;
  displayName: string;
  description: string;
  useCase: string;
}

export const TEMPLATE_METADATA: Record<string, TemplateMetadata> = {
  plotly: {
    name: "plotly",
    displayName: "Plotly",
    description: "Default colorful theme",
    useCase: "General purpose"
  },
  plotly_white: {
    name: "plotly_white",
    displayName: "Plotly White",
    description: "Clean white background",
    useCase: "Professional reports"
  },
  plotly_dark: {
    name: "plotly_dark",
    displayName: "Plotly Dark",
    description: "Dark theme",
    useCase: "Presentations, dashboards"
  },
  ggplot2: {
    name: "ggplot2",
    displayName: "ggplot2",
    description: "Mimics ggplot2 (R) style",
    useCase: "Data science"
  },
  seaborn: {
    name: "seaborn",
    displayName: "Seaborn",
    description: "Mimics seaborn (Python) style",
    useCase: "Statistical analysis"
  },
  simple_white: {
    name: "simple_white",
    displayName: "Simple White",
    description: "Minimal styling",
    useCase: "Clean, simple charts"
  },
  presentation: {
    name: "presentation",
    displayName: "Presentation",
    description: "High contrast for slides",
    useCase: "PowerPoint, slides"
  },
  xgridoff: {
    name: "xgridoff",
    displayName: "X Grid Off",
    description: "No vertical gridlines",
    useCase: "Clean look"
  },
  ygridoff: {
    name: "ygridoff",
    displayName: "Y Grid Off",
    description: "No horizontal gridlines",
    useCase: "Clean look"
  },
  gridon: {
    name: "gridon",
    displayName: "Grid On",
    description: "Full gridlines",
    useCase: "Precision reading"
  },
  none: {
    name: "none",
    displayName: "None",
    description: "No styling",
    useCase: "Complete custom control"
  }
};
