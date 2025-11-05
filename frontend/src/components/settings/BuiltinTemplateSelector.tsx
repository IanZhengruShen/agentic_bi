'use client';

/**
 * Builtin Template Selector Component
 *
 * Displays grid of Plotly's builtin templates for selection.
 */

import { Card } from '@/components/ui/card';
import { TEMPLATE_METADATA } from '@/types/chartPreferences.types';
import { CheckCircle2 } from 'lucide-react';

interface BuiltinTemplateSelectorProps {
  availableTemplates: string[];
  selectedTemplate?: string;
  onSelectTemplate: (templateName: string) => void;
}

export function BuiltinTemplateSelector({
  availableTemplates,
  selectedTemplate,
  onSelectTemplate,
}: BuiltinTemplateSelectorProps) {
  return (
    <div className="space-y-4">
      <div className="text-sm text-gray-600">
        Choose from 11 professional Plotly templates. Click a template to preview it.
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {availableTemplates.map((templateName) => {
          const metadata = TEMPLATE_METADATA[templateName];
          const isSelected = selectedTemplate === templateName;

          if (!metadata) return null;

          return (
            <Card
              key={templateName}
              className={`
                p-4 cursor-pointer transition-all duration-200 hover:shadow-lg
                ${isSelected ? 'ring-2 ring-blue-500 shadow-lg' : 'hover:ring-1 hover:ring-gray-300'}
              `}
              onClick={() => onSelectTemplate(templateName)}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <h4 className="font-semibold text-gray-900 mb-1">
                    {metadata.displayName}
                  </h4>
                  <p className="text-xs text-gray-500">{metadata.description}</p>
                </div>
                {isSelected && (
                  <CheckCircle2 className="h-5 w-5 text-blue-600 flex-shrink-0 ml-2" />
                )}
              </div>

              {/* Preview placeholder - will be replaced with actual chart preview */}
              <div className="h-32 bg-gradient-to-br from-gray-100 to-gray-200 rounded-md flex items-center justify-center">
                <div className="text-center">
                  <div className="text-3xl mb-2">📊</div>
                  <div className="text-xs text-gray-600 font-medium">
                    {metadata.useCase}
                  </div>
                </div>
              </div>

              <div className="mt-3 text-xs text-gray-500">
                <span className="inline-block px-2 py-1 bg-gray-100 rounded">
                  {templateName}
                </span>
              </div>
            </Card>
          );
        })}
      </div>

      {availableTemplates.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          No templates available
        </div>
      )}
    </div>
  );
}
