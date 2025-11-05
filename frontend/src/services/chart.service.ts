import { ChartConfig, ChartTemplate, ColorScheme, DEFAULT_COLOR_SCHEMES } from '@/types/chart.types';

/**
 * Chart service layer
 * PR#14: Basic structure
 * PR#15: Full implementation with API calls
 */

class ChartService {
  // Get available color schemes
  getColorSchemes(): ColorScheme[] {
    return DEFAULT_COLOR_SCHEMES;
  }

  // Apply color scheme to chart config
  applyColorScheme(config: ChartConfig, schemeId: string): ChartConfig {
    const scheme = DEFAULT_COLOR_SCHEMES.find((s) => s.id === schemeId);
    if (!scheme) return config;

    return {
      ...config,
      colorScheme: scheme,
      advanced: {
        ...config.advanced,
        customColors: scheme.colors,
      },
    };
  }

  // Validate chart config (PR#15 will expand this)
  validateConfig(config: ChartConfig): boolean {
    // Basic validation for now
    return true;
  }

  // Generate chart ID
  generateChartId(): string {
    return `chart_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  // Save template (PR#15 will make API call)
  async saveTemplate(template: ChartTemplate): Promise<void> {
    // PR#14: Store in localStorage
    const templates = this.getTemplates();
    templates.push(template);
    if (typeof window !== 'undefined') {
      localStorage.setItem('chart_templates', JSON.stringify(templates));
    }
  }

  // Load templates (PR#15 will make API call)
  getTemplates(): ChartTemplate[] {
    // PR#14: Load from localStorage
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('chart_templates');
      return stored ? JSON.parse(stored) : [];
    }
    return [];
  }

  // Delete template (PR#15 will make API call)
  async deleteTemplate(templateId: string): Promise<void> {
    // PR#14: Delete from localStorage
    const templates = this.getTemplates().filter((t) => t.id !== templateId);
    if (typeof window !== 'undefined') {
      localStorage.setItem('chart_templates', JSON.stringify(templates));
    }
  }

  // Export chart config as JSON (useful for debugging and sharing)
  exportConfig(config: ChartConfig): string {
    return JSON.stringify(config, null, 2);
  }

  // Import chart config from JSON
  importConfig(json: string): ChartConfig | null {
    try {
      return JSON.parse(json);
    } catch {
      return null;
    }
  }
}

export const chartService = new ChartService();
