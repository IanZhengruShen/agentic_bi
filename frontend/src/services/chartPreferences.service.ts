/**
 * Chart Preferences Service
 *
 * Handles API calls for user chart styling preferences.
 */

import apiClient from '@/lib/api-client';
import type {
  UserChartPreferences,
  UpdateChartPreferencesRequest,
  SaveTemplateRequest,
  SavedTemplate,
  ChartTemplateConfig,
} from '@/types/chartPreferences.types';

const CHART_PREFERENCES_BASE_URL = '/api/user/chart';

/**
 * Get user's chart preferences
 */
export const getChartPreferences = async (): Promise<UserChartPreferences> => {
  const response = await apiClient.get<UserChartPreferences>(
    `${CHART_PREFERENCES_BASE_URL}/preferences`
  );
  return response.data;
};

/**
 * Update user's chart template preference
 */
export const updateChartPreferences = async (
  chartTemplate: ChartTemplateConfig
): Promise<UserChartPreferences> => {
  const request: UpdateChartPreferencesRequest = {
    chart_template: chartTemplate,
  };

  const response = await apiClient.put<UserChartPreferences>(
    `${CHART_PREFERENCES_BASE_URL}/preferences`,
    request
  );
  return response.data;
};

/**
 * Save a custom template
 */
export const saveCustomTemplate = async (
  request: SaveTemplateRequest
): Promise<SavedTemplate> => {
  const response = await apiClient.post<SavedTemplate>(
    `${CHART_PREFERENCES_BASE_URL}/templates`,
    request
  );
  return response.data;
};

/**
 * Delete a saved custom template
 */
export const deleteCustomTemplate = async (templateId: string): Promise<void> => {
  await apiClient.delete(`${CHART_PREFERENCES_BASE_URL}/templates/${templateId}`);
};

/**
 * Helper: Create a builtin template config
 */
export const createBuiltinTemplateConfig = (
  templateName: string
): ChartTemplateConfig => {
  return {
    type: 'builtin',
    name: templateName,
    custom_definition: undefined,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
};

/**
 * Helper: Create a custom template config
 */
export const createCustomTemplateConfig = (
  customDefinition: any
): ChartTemplateConfig => {
  return {
    type: 'custom',
    name: undefined,
    custom_definition: customDefinition,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
};
