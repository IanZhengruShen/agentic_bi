'use client';

/**
 * Saved Templates Grid Component
 *
 * Displays user's saved custom templates with options to apply or delete.
 */

import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Trash2, Clock, Edit } from 'lucide-react';
import { toast } from 'sonner';
import type { SavedTemplate, ChartTemplateConfig } from '@/types/chartPreferences.types';
import { deleteCustomTemplate, createCustomTemplateConfig } from '@/services/chartPreferences.service';

interface SavedTemplatesGridProps {
  savedTemplates: SavedTemplate[];
  onSelectTemplate: (template: ChartTemplateConfig) => void;
  onRefresh: () => void;
  onEdit: (template: SavedTemplate) => void;
}

export function SavedTemplatesGrid({
  savedTemplates,
  onSelectTemplate,
  onRefresh,
  onEdit,
}: SavedTemplatesGridProps) {
  const handleApplyTemplate = (saved: SavedTemplate) => {
    const template = createCustomTemplateConfig(saved.template_definition);
    onSelectTemplate(template);
    toast.success(`Applied template: ${saved.name}`);
  };

  const handleDeleteTemplate = async (saved: SavedTemplate) => {
    const confirmed = confirm(`Delete template "${saved.name}"?`);
    if (!confirmed) return;

    try {
      await deleteCustomTemplate(saved.id);
      toast.success('Template deleted');
      onRefresh();
    } catch (error) {
      console.error('Failed to delete template:', error);
      toast.error('Failed to delete template');
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  if (savedTemplates.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-400 text-6xl mb-4">📋</div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          No saved templates yet
        </h3>
        <p className="text-gray-600 text-sm">
          Create custom templates in the "Custom Creator" tab and save them for reuse.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="text-sm text-gray-600">
        Your saved custom templates ({savedTemplates.length})
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {savedTemplates.map((saved) => {
          const layout = saved.template_definition.layout || {};
          const colorway = layout.colorway || [];

          return (
            <Card key={saved.id} className="p-4">
              <div className="mb-3">
                <h4 className="font-semibold text-gray-900 mb-1">{saved.name}</h4>
                {saved.description && (
                  <p className="text-sm text-gray-600">{saved.description}</p>
                )}
                <div className="flex items-center gap-1 text-xs text-gray-500 mt-2">
                  <Clock className="h-3 w-3" />
                  <span>Created {formatDate(saved.created_at)}</span>
                </div>
              </div>

              {/* Color Palette Preview */}
              {colorway.length > 0 && (
                <div className="mb-3">
                  <div className="text-xs text-gray-600 mb-1">Color Palette</div>
                  <div className="flex gap-1">
                    {colorway.slice(0, 6).map((color, i) => (
                      <div
                        key={i}
                        className="h-6 flex-1 rounded"
                        style={{ backgroundColor: color }}
                        title={color}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Template Details */}
              <div className="mb-3 text-xs text-gray-600 space-y-1">
                {layout.font && (
                  <div>Font: {layout.font.family || 'Default'}, {layout.font.size || 12}px</div>
                )}
                {layout.plot_bgcolor && layout.paper_bgcolor && (
                  <div>Backgrounds: Plot {layout.plot_bgcolor}, Paper {layout.paper_bgcolor}</div>
                )}
              </div>

              {/* Actions */}
              <div className="flex gap-2">
                <Button
                  size="sm"
                  className="flex-1 bg-blue-600 hover:bg-blue-700"
                  onClick={() => handleApplyTemplate(saved)}
                >
                  Apply
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onEdit(saved)}
                  title="Edit template"
                >
                  <Edit className="h-4 w-4" />
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleDeleteTemplate(saved)}
                  title="Delete template"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
