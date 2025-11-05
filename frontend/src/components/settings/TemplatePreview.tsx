'use client';

/**
 * Template Preview Component
 *
 * Shows a live preview of the selected chart template using a sample bar chart.
 */

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import type { ChartTemplateConfig } from '@/types/chartPreferences.types';

// Dynamically import Plotly to avoid SSR issues
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface TemplatePreviewProps {
  template: ChartTemplateConfig | null;
}

export function TemplatePreview({ template }: TemplatePreviewProps) {
  const [plotlyFigure, setPlotlyFigure] = useState<any>(null);

  useEffect(() => {
    // Sample data for preview
    const sampleData = {
      x: ['Q1', 'Q2', 'Q3', 'Q4'],
      y: [15, 25, 30, 20],
      type: 'bar',
      name: 'Sales',
    };

    // Base figure
    let figure: any = {
      data: [sampleData],
      layout: {
        title: 'Sample Chart Preview',
        xaxis: { title: 'Quarter' },
        yaxis: { title: 'Revenue ($k)' },
        margin: { t: 50, r: 20, b: 50, l: 50 },
        autosize: true,
      },
    };

    // Apply template styling
    if (template) {
      if (template.type === 'builtin' && template.name) {
        // Apply builtin template
        figure.layout.template = template.name;
      } else if (template.type === 'custom' && template.custom_definition) {
        // Apply custom template layout settings
        const customLayout = template.custom_definition.layout || {};

        if (customLayout.font) {
          figure.layout.font = customLayout.font;
        }
        if (customLayout.colorway) {
          figure.layout.colorway = customLayout.colorway;
        }
        if (customLayout.plot_bgcolor) {
          figure.layout.plot_bgcolor = customLayout.plot_bgcolor;
        }
        if (customLayout.paper_bgcolor) {
          figure.layout.paper_bgcolor = customLayout.paper_bgcolor;
        }
        if (customLayout.hovermode) {
          figure.layout.hovermode = customLayout.hovermode;
        }

        // Apply logo if provided
        if (customLayout.logo_url && customLayout.logo_position) {
          figure.layout.images = [
            {
              source: customLayout.logo_url,
              xref: 'paper',
              yref: 'paper',
              x: customLayout.logo_position.x,
              y: customLayout.logo_position.y,
              sizex: customLayout.logo_position.sizex,
              sizey: customLayout.logo_position.sizey,
              xanchor: customLayout.logo_position.xanchor || 'right',
              yanchor: customLayout.logo_position.yanchor || 'bottom',
              layer: 'above',
            },
          ];
        }
      }
    } else {
      // Default template
      figure.layout.template = 'plotly_white';
    }

    setPlotlyFigure(figure);
  }, [template]);

  if (!plotlyFigure) {
    return (
      <div className="h-64 flex items-center justify-center bg-gray-100 rounded-lg">
        <div className="text-gray-500">Loading preview...</div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <Plot
          data={plotlyFigure.data}
          layout={{
            ...plotlyFigure.layout,
            width: undefined, // Let it be responsive
            height: 300,
          }}
          config={{
            responsive: true,
            displayModeBar: false,
          }}
          style={{ width: '100%', height: '300px' }}
        />
      </div>

      {/* Template Info */}
      <div className="text-xs text-gray-600">
        {template ? (
          <div>
            {template.type === 'builtin' ? (
              <div>
                <strong>Template:</strong> {template.name}
              </div>
            ) : (
              <div>
                <strong>Template:</strong> Custom
              </div>
            )}
          </div>
        ) : (
          <div className="text-gray-500">No template selected</div>
        )}
      </div>
    </div>
  );
}
