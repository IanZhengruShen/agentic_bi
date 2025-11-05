'use client';

import dynamic from 'next/dynamic';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChart3 } from 'lucide-react';
import { ChartConfig } from '@/types/chart.types';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface PlotlyChartProps {
  figure: any;
  title?: string;
  chartId?: string; // Unique ID for tracking
  config?: ChartConfig; // Auto-applied from user preferences (PR#15)
}

export default function PlotlyChart({
  figure,
  title,
  chartId,
  config,
}: PlotlyChartProps) {
  if (!figure || !figure.data) {
    return null;
  }

  // Apply custom config if provided (from user/company preferences)
  const enhancedLayout = {
    ...figure.layout,
    autosize: true,
    responsive: true,
    margin: { l: 50, r: 50, t: 50, b: 50 },
    // Apply custom layout from user preferences (if provided)
    ...(config?.layout && {
      showlegend: config.layout.showLegend,
      legend: config.layout.legendPosition ? {
        orientation: 'h',
        x: 0,
        y: config.layout.legendPosition === 'bottom' ? -0.2 : 1.1,
      } : undefined,
      font: {
        size: config.layout.fontSize || 12,
        family: config.layout.fontFamily || 'Inter, sans-serif',
      },
    }),
  };

  // Apply custom colors if provided (from user preferences)
  const enhancedData = figure.data.map((trace: any, idx: number) => ({
    ...trace,
    marker: {
      ...trace.marker,
      ...(config?.advanced?.customColors && {
        color: config.advanced.customColors[idx % config.advanced.customColors.length],
      }),
    },
  }));

  return (
    <Card className="shadow-sm">
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center">
          <BarChart3 size={18} className="mr-2" />
          {title || figure.layout?.title?.text || 'Visualization'}
        </CardTitle>
      </CardHeader>

      <CardContent>
        <div className="w-full" data-chart-id={chartId}>
          <Plot
            data={enhancedData}
            layout={enhancedLayout}
            config={{
              responsive: true,
              displayModeBar: true, // Plotly's native toolbar with download
              displaylogo: false,
              toImageButtonOptions: {
                format: 'png',
                filename: `chart_${chartId || Date.now()}`,
                height: config?.export?.height || 800,
                width: config?.export?.width || 1200,
                scale: config?.export?.dpi || 2,
              },
              modeBarButtonsToRemove: ['lasso2d', 'select2d'],
            }}
            style={{ width: '100%', height: '400px' }}
            useResizeHandler={true}
          />
        </div>
      </CardContent>
    </Card>
  );
}
